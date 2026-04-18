"""SQLite ``config`` table adapter for model registry + router model (v3 parity)."""

from __future__ import annotations

import json
from typing import cast

from orchestrator_v4.core.entities.model_registry_entry import ModelRegistryEntry
from orchestrator_v4.core.ports.model_registry_store import ModelRegistryStore
from orchestrator_v4.infrastructure.ai.gemini_policy_constants import (
    DEFAULT_FLASH_LITE_MODEL_ID,
    DEFAULT_PRO_MODEL_ID,
)
from orchestrator_v4.infrastructure.persistence.sqlite_orchestrator_connection import (
    open_orchestrator_db,
)

_CONFIG_MODEL_REGISTRY = "model_registry"
_CONFIG_ROUTER_MODEL = "router_model"

_DEFAULT_REGISTRY: dict[str, list[ModelRegistryEntry]] = {
    "models": [
        {
            "id": DEFAULT_FLASH_LITE_MODEL_ID,
            "label": "Gemini 3.1 Flash-Lite (router + agents 1–4)",
            "supports_thinking": True,
            "default_thinking": "LOW",
            "temperature_range": [0.0, 2.0],
            "default_temperature": 1.0,
            "max_output_tokens": 65536,
            "context_window": 1000000,
            "requires_thought_signatures": False,
            "include_thoughts_supported": True,
            "media_resolution_supported": False,
            "output_modalities": ["text"],
            "status": "active",
            "notes": "Default fast path; first active registry entry for fallbacks.",
        },
        {
            "id": DEFAULT_PRO_MODEL_ID,
            "label": "Gemini 3.1 Pro (synthesizer / agent 5)",
            "supports_thinking": True,
            "default_thinking": "HIGH",
            "temperature_range": [0.0, 2.0],
            "default_temperature": 1.0,
            "max_output_tokens": 65536,
            "context_window": 1000000,
            "requires_thought_signatures": False,
            "include_thoughts_supported": True,
            "media_resolution_supported": False,
            "output_modalities": ["text"],
            "status": "active",
            "notes": "Heavier model for grand synthesis.",
        },
    ]
}


def _validate_models(models: list[ModelRegistryEntry]) -> None:
    """Raise ``ValueError`` with a user-facing message when validation fails."""
    if not isinstance(models, list):
        raise ValueError("'models' must be a list")
    for model in models:
        if not isinstance(model, dict):
            raise ValueError("Each model entry must be an object")
        mid = (model.get("id") or "").strip()
        if not mid:
            raise ValueError("Every model must have a non-empty 'id' field")
        status = str(model.get("status", "active")).lower().strip()
        if status not in ("active", "deprecated", "unlisted"):
            raise ValueError(
                f"Invalid status for model '{mid}'. Use 'active', 'deprecated', or 'unlisted'."
            )
        if "temperature_range" in model and not isinstance(model["temperature_range"], list):
            raise ValueError(f"temperature_range for model '{mid}' must be a list")
        if "default_temperature" in model:
            try:
                float(model["default_temperature"])
            except (ValueError, TypeError):
                raise ValueError(
                    f"default_temperature for model '{mid}' must be a number"
                ) from None


def _default_model_id_from_registry(models: list[ModelRegistryEntry]) -> str:
    for m in models:
        if isinstance(m, dict) and str(m.get("status", "active")).lower().strip() == "active":
            rid = (m.get("id") or "").strip()
            if rid:
                return rid
    return DEFAULT_FLASH_LITE_MODEL_ID


class SqliteModelRegistryStore(ModelRegistryStore):
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def _config_get(self, conn, key: str) -> str | None:
        row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
        return row[0] if row and row[0] is not None else None

    def _config_set(self, conn, key: str, value: str) -> None:
        conn.execute(
            """
            INSERT INTO config (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )

    def get_models(self) -> list[ModelRegistryEntry]:
        with open_orchestrator_db(self._db_path) as conn:
            raw = self._config_get(conn, _CONFIG_MODEL_REGISTRY)
        if not raw or not raw.strip():
            payload = json.dumps(_DEFAULT_REGISTRY, indent=2)
            with open_orchestrator_db(self._db_path) as conn:
                self._config_set(conn, _CONFIG_MODEL_REGISTRY, payload)
                conn.commit()
            return list(_DEFAULT_REGISTRY["models"])
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        models = data.get("models", [])
        if not isinstance(models, list):
            return []
        return cast(list[ModelRegistryEntry], models)

    def save_models(self, models: list[ModelRegistryEntry]) -> None:
        _validate_models(models)
        new_ids = {
            (m.get("id") or "").strip()
            for m in models
            if isinstance(m, dict) and (m.get("id") or "").strip()
        }
        payload = json.dumps({"models": models}, indent=2)
        with open_orchestrator_db(self._db_path) as conn:
            raw_router = self._config_get(conn, _CONFIG_ROUTER_MODEL)
            if raw_router and raw_router.strip():
                rid = raw_router.strip()
                if rid not in new_ids:
                    raise ValueError(
                        f'Router model "{rid}" is not in the new registry. '
                        "Include it in the models list, or set the router in Settings "
                        "to a model that stays in the list before saving the registry."
                    )
            self._config_set(conn, _CONFIG_MODEL_REGISTRY, payload)
            conn.commit()

    def get_router_model(self) -> str:
        models = self.get_models()
        fallback = _default_model_id_from_registry(models)
        with open_orchestrator_db(self._db_path) as conn:
            raw = self._config_get(conn, _CONFIG_ROUTER_MODEL)
        if raw and raw.strip():
            return raw.strip()
        return fallback

    def set_router_model(self, model_id: str) -> None:
        with open_orchestrator_db(self._db_path) as conn:
            self._config_set(conn, _CONFIG_ROUTER_MODEL, model_id)
            conn.commit()

    def get_default_active_model_id(self) -> str:
        return _default_model_id_from_registry(self.get_models())
