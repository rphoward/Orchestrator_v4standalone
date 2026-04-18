"""
Generative Language API helpers: list models for an API key, compare in-use ids, optional deprecations.md.

Uses stdlib ``urllib`` only (no extra deps). Intended for Settings preflight, not hot paths.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from typing import Any, Callable

from orchestrator_v4.core.entities.model_registry_entry import ModelRegistryEntry
from orchestrator_v4.infrastructure.ai.maintenance_extensions import merge_maintenance_signals
from orchestrator_v4.infrastructure.persistence.sqlite_model_registry_store import (
    SqliteModelRegistryStore,
)
from orchestrator_v4.infrastructure.persistence.sqlite_orchestrator_connection import (
    open_orchestrator_db,
)

_LOG = logging.getLogger(__name__)

_MODELS_LIST_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_DEPRECATIONS_MD_URL = "https://ai.google.dev/gemini-api/docs/deprecations.md"
_HTTP_TIMEOUT_SEC = 45.0
_PAGE_SIZE = 100

# Pipe-table row: first column has `model-id` in backticks
_ROW_MODEL_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|")


def fetch_model_id_set(api_key: str, urlopen: Callable[..., Any] | None = None) -> set[str]:
    """
    GET v1beta/models with pagination; union of stripped ``name`` (after models/) and ``baseModelId``.
    """
    opener = urlopen or urllib.request.urlopen
    out: set[str] = set()
    page_token: str | None = None
    while True:
        q: dict[str, str] = {"key": api_key, "pageSize": str(_PAGE_SIZE)}
        if page_token:
            q["pageToken"] = page_token
        url = f"{_MODELS_LIST_BASE}?{urllib.parse.urlencode(q)}"
        req = urllib.request.Request(url, method="GET")
        try:
            with opener(req, timeout=_HTTP_TIMEOUT_SEC) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            raise RuntimeError(
                f"Google returned HTTP {e.code} while listing models. {body[:500]}"
            ) from e
        except OSError as e:
            raise RuntimeError(f"Network error while listing models: {e}") from e

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError("Invalid JSON from models list endpoint.") from e

        if not isinstance(payload, dict):
            raise RuntimeError(
                "Invalid JSON from models list endpoint: expected a JSON object, got "
                f"{type(payload).__name__}."
            )

        for m in payload.get("models") or []:
            if not isinstance(m, dict):
                continue
            name = (m.get("name") or "").strip()
            if name.startswith("models/"):
                out.add(name.split("/", 1)[1].strip())
            elif name:
                out.add(name)
            base = (m.get("baseModelId") or "").strip()
            if base:
                out.add(base)

        page_token = (payload.get("nextPageToken") or "").strip() or None
        if not page_token:
            break
    return out


def compare_model_ids(needed: set[str], api_ids: set[str]) -> tuple[list[str], list[str]]:
    known = sorted(mid for mid in needed if mid in api_ids)
    unknown = sorted(mid for mid in needed if mid not in api_ids)
    return known, unknown


def collect_needed_model_ids(
    db_path: str,
) -> tuple[set[str], dict[str, list[str]]]:
    """
    Registry ids, each agent ``model``, effective router, effective agent fallback.
    Env ``ORCHESTRATOR_ROUTER_MODEL`` / ``ORCHESTRATOR_AGENT_MODEL`` match bootstrap.
    """
    store = SqliteModelRegistryStore(db_path)
    models: list[ModelRegistryEntry] = store.get_models()
    usages: dict[str, list[str]] = {}

    def add(mid: str, source: str) -> None:
        s = mid.strip()
        if not s:
            return
        usages.setdefault(s, []).append(source)

    for m in models:
        if not isinstance(m, dict):
            continue
        mid = (m.get("id") or "").strip()
        if not mid:
            continue
        label = (m.get("label") or mid).strip()
        add(mid, f"Model registry (label: {label})")

    with open_orchestrator_db(db_path) as conn:
        rows = conn.execute(
            "SELECT id, name, model FROM agents ORDER BY id"
        ).fetchall()

    for row in rows:
        aid = row["id"]
        name = (row["name"] or "").strip() or f"Agent {aid}"
        mid = (row["model"] or "").strip()
        if mid:
            add(mid, f"Agent {aid} — {name}")

    env_router = (os.environ.get("ORCHESTRATOR_ROUTER_MODEL") or "").strip()
    if env_router:
        add(env_router, "Router (ORCHESTRATOR_ROUTER_MODEL)")
    else:
        r = store.get_router_model()
        if r:
            add(r, "Router (Settings / SQLite)")

    env_agent = (os.environ.get("ORCHESTRATOR_AGENT_MODEL") or "").strip()
    if env_agent:
        add(env_agent, "Default agent model (ORCHESTRATOR_AGENT_MODEL)")
    else:
        fb = store.get_default_active_model_id()
        if fb:
            add(fb, "Default agent model (registry)")

    needed = set(usages.keys())
    return needed, usages


def fetch_deprecation_schedule_md(
    urlopen: Callable[..., Any] | None = None,
) -> dict[str, dict[str, str]]:
    """
    Fetch public deprecations.md and parse pipe tables into
    model_id -> {shutdown_raw, replacement_raw}.
    """
    opener = urlopen or urllib.request.urlopen
    req = urllib.request.Request(
        _DEPRECATIONS_MD_URL,
        method="GET",
        headers={"User-Agent": "Orchestrator4-model-verify/1.0"},
    )
    try:
        with opener(req, timeout=_HTTP_TIMEOUT_SEC) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except OSError as e:
        _LOG.warning("deprecations.md fetch failed: %s", e)
        return {}
    return parse_deprecation_pipe_tables(text)


def parse_deprecation_pipe_tables(md: str) -> dict[str, dict[str, str]]:
    schedule: dict[str, dict[str, str]] = {}
    for line in md.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if re.match(r"^\|\s*-+\s*\|", line):
            continue
        m = _ROW_MODEL_RE.match(line)
        if not m:
            continue
        model_id = m.group(1).strip()
        if not model_id or " " in model_id and "`" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        # | model | release | shutdown | replacement |
        if len(parts) < 5:
            continue
        shutdown = parts[3] if len(parts) > 3 else ""
        replacement = parts[4] if len(parts) > 4 else ""
        schedule[model_id] = {
            "shutdown_raw": shutdown,
            "replacement_raw": replacement,
        }
    return schedule


def _shutdown_is_amber(shutdown_raw: str, today: date) -> bool:
    s = (shutdown_raw or "").strip()
    if not s:
        return False
    low = s.lower()
    if "no shutdown date announced" in low:
        return False
    if "coming soon" in low:
        return True
    try:
        d = datetime.strptime(s, "%B %d, %Y").date()
    except ValueError:
        return False
    return d > today


def build_maintenance_warnings(
    needed: set[str],
    schedule: dict[str, dict[str, str]],
    usages: dict[str, list[str]],
    today: date | None = None,
) -> list[dict[str, Any]]:
    today = today or datetime.now(timezone.utc).date()
    out: list[dict[str, Any]] = []
    for mid in sorted(needed):
        row = schedule.get(mid)
        if not row:
            continue
        shutdown_raw = row.get("shutdown_raw") or ""
        if not _shutdown_is_amber(shutdown_raw, today):
            continue
        out.append(
            {
                "id": mid,
                "shutdown": shutdown_raw,
                "replacement": row.get("replacement_raw") or "",
                "sources": list(usages.get(mid, [])),
            }
        )
    return out


def run_model_verify(
    api_key: str,
    db_path: str,
    *,
    urlopen: Callable[..., Any] | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    checked_at = datetime.now(timezone.utc).isoformat()
    empty: dict[str, Any] = {
        "ok": False,
        "checked_at": checked_at,
        "known": [],
        "unknown": [],
        "usages": {},
        "maintenance_warnings": [],
    }

    if not (api_key or "").strip():
        empty["error"] = "No GEMINI_API_KEY configured. Save an API key in Settings first."
        return merge_maintenance_signals(empty)

    try:
        needed, usages = collect_needed_model_ids(db_path)
    except OSError as e:
        empty["error"] = f"Could not read orchestrator database: {e}"
        return merge_maintenance_signals(empty)

    try:
        api_ids = fetch_model_id_set(api_key.strip(), urlopen=urlopen)
    except RuntimeError as e:
        empty["error"] = str(e)
        empty["usages"] = {k: list(v) for k, v in usages.items()}
        return merge_maintenance_signals(empty)

    known, unknown = compare_model_ids(needed, api_ids)

    schedule = fetch_deprecation_schedule_md(urlopen=urlopen)
    maintenance = build_maintenance_warnings(needed, schedule, usages, today=today)

    result: dict[str, Any] = {
        "ok": len(unknown) == 0,
        "checked_at": checked_at,
        "known": known,
        "unknown": unknown,
        "usages": {k: list(v) for k, v in usages.items()},
        "maintenance_warnings": maintenance,
    }
    return merge_maintenance_signals(result)
