# Orchestrator v4 — Standalone developer handbook

**What this file is:** Onboarding and operations reference for **this repository**. The Python package is **`orchestrator_v4`**; on disk, `bootstrap.py`, `core/`, `infrastructure/`, and `presentation/` live at the **repository root** (your clone folder name may differ, e.g. `orchestrator_v4standalone`). It describes **current behavior**, how to run and verify it, and **optional follow-ups**.

**Current status (post-migration):** This tree was lifted out of a larger repository, then edited, deleted-from, and **resynced to GitHub** (including a replaced `main` history at one point). **Regression coverage is not complete** until you re-run the verification checklist below and any automated tests you rely on. Unknown breakage is possible—if the code disagrees with this doc, **trust the code** and update the doc (or fix the bug).

**What this file is not:** A Cursor execution plan. For agent-driven multi-step work, use **`.cursor/plans/`** for new plans (optional **`archive/`** subfolder for executed history); see [`.cursor/plans/README.md`](.cursor/plans/README.md). Agent-facing contract: **[`AGENTS.md`](AGENTS.md)**.

**Goal:** Run and configure the app from the **repository root** without a parent monorepo: local **`.env`**, **`run_dev.py`**, and correct import root for **`python -m orchestrator_v4.…`**.

---

## Quick start

1. Open this folder as the **workspace / repository root** (the directory that contains `bootstrap.py`, `core/`, `run_dev.py`, …).
2. Put secrets in **`.env`** at that root (at minimum `GEMINI_API_KEY=…` if you use live Gemini).
3. From the repository root: **`python run_dev.py`** (web UI, default port **5001**) or **`python run_dev.py --smoke`** (bootstrap smoke).
4. First run: if **`.venv`** is missing, **`run_dev.py`** expects **`uv`** on `PATH` and will create **`.venv`** and install **`requirements.txt`**. Otherwise create a venv yourself and install deps, then run again.

---

## Python layout (why `run_dev.py` exists)

- The importable package name is **`orchestrator_v4`**, mapped to **this directory** via `pyproject.toml` (`package-dir`). On disk you see `core/`, `presentation/`, … at the **repository root**, not a nested `orchestrator_v4/` folder.
- For **`python -m orchestrator_v4.…`** to resolve, the child process **`cwd`** must be the directory **that setuptools considers the package parent**—**`run_dev.py`** sets that up (see its docstring).
- **`run_dev.py`** runs **`python -m orchestrator_v4.presentation.app`** (or **`python -m orchestrator_v4.bootstrap_smoke`** with **`--smoke`**). It uses the **`.venv`** interpreter at the repo root when present. For this **flat** `package-dir` layout it also runs **`uv pip install -e .`** (when **`uv`** is on `PATH`) so **`import orchestrator_v4`** resolves the same way as a nested folder layout. **PyInstaller** or other frozen entrypoints are **out of scope** for this standalone repo unless you add them here.

---

## Dependencies

**File:** [`requirements.txt`](requirements.txt) in this folder.

Stack: Flask, `google-genai`, `python-dotenv` (and transitive deps).

**Optional editable install:** [`pyproject.toml`](pyproject.toml) mirrors those dependencies for **`pip install -e .`** or **`uv sync`** from the **repository root** (handy for tooling or importing the package from another venv). **Portability:** you do **not** need an editable install for day-to-day dev—**`run_dev.py`** plus **`requirements.txt`** (or **`uv`** creating **`.venv`**) remains the supported path and sets the correct import root for **`python -m orchestrator_v4.…`**.

**Without `uv`:** Create **`.venv`**, activate, **`pip install -r requirements.txt`**, then **`python run_dev.py`**. Generic advice: **`.venv`** often breaks if copied to a different path or machine—recreate when that happens. **Sandbox workflow:** if you copy this **whole repository folder** including **`.venv`**, see **[`AGENTS.md`](AGENTS.md)** so tooling aligns with deliberate whole-folder sync.

---

## Environment files

| Location | Role |
|----------|------|
| **`.env`** (repository root) | Primary dev secrets and overrides. Loaded by **`bootstrap.py`** (dev) via **`_src_dir()`**. Also read/written by Settings API key UI (`set_key` / `dotenv_values`). |
| **Next to frozen `.exe`** | Frozen/PyInstaller: **`load_dotenv`** next to executable. |

**Launcher:** **`run_dev.py`** applies a small stdlib **`.env`** parse into the parent process environment before spawning the child so keys are visible even when running with a bare system Python before **`.venv`** exists.

**Common env vars:** `GEMINI_API_KEY`, `ORCHESTRATOR_DB_PATH`, `ORCHESTRATOR_PROMPTS_ROOT`, `ORCHESTRATOR_ROUTER_MODEL`, `ORCHESTRATOR_AGENT_MODEL`, `ORCHESTRATOR_PORT`, `ORCHESTRATOR_HOST`, `FLASK_DEBUG`, etc.

### Secrets vs model overrides

| Variable | Role |
|----------|------|
| **`GEMINI_API_KEY`** | Authentication only so the SDK can call Google—not “which model.” |
| **`ORCHESTRATOR_ROUTER_MODEL`** | If set (non-empty), overrides SQLite for the **router** model id used by the live gateway. |
| **`ORCHESTRATOR_AGENT_MODEL`** | If set, overrides SQLite/registry for the **default agent fallback** model id when a turn has no explicit model. |

Leave the two **`ORCHESTRATOR_*_MODEL`** vars unset to use **Settings** and the stored registry/router rows.

**Router / default generation models (detail):** Non-empty **`ORCHESTRATOR_ROUTER_MODEL`** or **`ORCHESTRATOR_AGENT_MODEL`** override SQLite/registry for those resolution paths. Otherwise the live **`GeminiInterviewLlmGateway`** uses **`model_registry_store.get_router_model()`** and **`get_default_active_model_id()`**. **`bootstrap.rebind_llm_gateway()`** runs on startup, after **`apply_gemini_api_key`**, after **`PUT /api/config/router-model`**, and after **`PUT /api/models`** (registry bulk save).

---

## Model registry

- Stored in SQLite (seed and edits via Settings). **No** automatic sync that rewrites your registry from Google; API model IDs must match names Google documents for Gemini.
- Edit the registry in-app; use **`PUT /api/models`** for bulk replace when importing config.
- **Consistency:** if Settings has stored a **router model** id in SQLite, a bulk save **rejects** when that id is **not** in the new `models` list (HTTP 400 with a clear message). Either add the router’s model to the list or change the router first.

### Preflight: Check names with Google

- In **Settings → Model Registry**, **Check names with Google** calls the Generative Language API **`models.list`** using your saved **`GEMINI_API_KEY`**, and fetches Google’s public Markdown **[Gemini deprecations](https://ai.google.dev/gemini-api/docs/deprecations)** (`deprecations.md`) for maintenance hints.
- **Green:** every in-use model id (registry, each agent, effective router, default agent fallback—same env overrides as **`ORCHESTRATOR_ROUTER_MODEL`** / **`ORCHESTRATOR_AGENT_MODEL`**) appears in **`models.list`** for your key at **`checked_at`**. Preview IDs can disappear when Google rotates names—re-run the check after odd errors or doc updates.
- **Red:** an id you use was **not** in that list (typo, retired model, or key cannot see it). The panel lists **where** each id is used.
- **Amber:** Google’s table shows a **future shutdown date** or **Coming soon** for an id you still use. That is documentation, not a supported JSON API—if parsing fails, amber is skipped for that run. Plan migrations when it’s convenient, not panic.
- Last good result is cached in **`sessionStorage`** so **Settings → Agent Config** can show matching red/amber lines under **Effective configuration** and on the **Router** block without extra requests.
- **API:** **`POST /api/config/verify-model-ids`** returns JSON (`ok`, `known`, `unknown`, `usages`, `maintenance_warnings`, …). **`401`** if no API key is configured in the running app.

---

## Active stage pointer and auto-routing

**Core idea:** `sessions.current_agent_id` (in SQLite) holds the **active stage pointer** — the earliest unfinished stage in 1..4, recomputed from the four `stageN_complete` flags at the end of every turn (auto or manual). When all four flags are true the pointer stays at **4**. Agent 5 (Grand Synthesis) is the manual-only synthesizer and never becomes the pointer.

**Auto-routing veto ([`core/entities/stage_evaluator.py`](core/entities/stage_evaluator.py) `apply_sequential_stage_veto`):** the auto-router may target any agent from **1 up to and including the pointer** — so it can drift back to a finished stage when the consultant won't let go. It **cannot** target past the pointer; any such decision is rewritten to `STAY` on the pointer and the router's original intent is preserved in the `routing_logs.reason` string (`"Sequential stage veto: router wanted agent 3 (status=ADVANCE), forced to stage 2 (next unfinished)"`).

**Manual routing:** the consultant can target any agent 1..5 for one turn. A manual turn can still flip the targeted agent's stage flag (the pointer is always recomputed from flags, so manual forward-motion is earned honestly by the same 2-user-messages rule).

**UI identifiers (`presentation/static/index.html` + `interview_chat_panel.js` + `interview_sessions_panel.js`):** `activeStagePointerBadge` (the `Stage: N` chip), `stageStatusTrackerDots` (the four dots), `autoRoutingToggle` (the checkbox), `manualRoutingAgentPicker` (the tab row), `chooseManualRoutingAgent(n)` (the tab onclicks). Toggling the auto-routing checkbox either direction snaps the manual picker and open chat thread to the pointer.

---

## SQLite DB hygiene (`runtime/orchestrator.db`)

**What the file holds:** sessions, conversations, routing logs, agents (including per-agent model ids), prompt templates, **`config`** (model registry JSON, router model id, and other keys). Paths default under **`runtime/`** unless **`ORCHESTRATOR_DB_PATH`** points elsewhere.

| Situation | Suggestion |
|-----------|------------|
| **Fresh start / corrupted DB** | Stop the app, delete **`runtime/orchestrator.db`** (and keep **`runtime/prompts/`** as needed). Next launch recreates the file and seeds default agents; registry falls back to defaults until you configure again. |
| **Thinking defaults on existing DBs** | On each startup, **`ensure_orchestrator_database`** inserts **`config`** keys **`thinking_level_1`** … **`thinking_level_5`** only when a key is missing (agents 1–4 → **LOW**, agent 5 → **HIGH**). It never overwrites values you already set. Deleting **`orchestrator.db`** is still the full reset if you want a clean slate. |
| **Copying a DB from another machine or old backup** | Expect **stale router and registry** (and agent **`model`** columns) versus what you run today. Either accept that and fix in Settings, or delete the DB and re-seed, or run a one-way migration/script you trust. |
| **Sandbox / full-folder paste** | If you copy this repo including **`runtime/orchestrator.db`**, you are copying **someone else’s** session and config. For a clean demo, delete **`orchestrator.db`** or use an empty **`runtime/`**. |
| **Do not commit** | The file is gitignored; treat it as **local state**, not source of truth for the team. |

---

## Settings: API key endpoint

- **`GET` / `PUT /api/config/api-key`** — JSON **`masked_key`**; PUT body **`api_key`**. Writes **`GEMINI_API_KEY`** into package **`.env`** and calls **`bootstrap.apply_gemini_api_key`**, which **`rebind_llm_gateway()`** so turns use the new key without restart.
- Front-end: [`presentation/static/modules/settings_agent.js`](presentation/static/modules/settings_agent.js).

---

## Git

**File:** [`.gitignore`](.gitignore) — **`/.env`** and **`/.venv/`** so secrets and local venvs are not committed.

---

## Optional: Pylance / analysis

When the **workspace folder is this repository root**, `orchestrator_v4.*` imports are resolved via the **`package-dir`** layout in `pyproject.toml`. If your editor still flags imports, set **`python.analysis.extraPaths`** to **`["${workspaceFolder}"]`** in `.vscode/settings.json` (local only if not committed).

Runtime is unchanged; this only helps static analysis.

---

## Verification checklist

Re-run this list after **migrations, merges, or GitHub history changes** until you are confident nothing regressed.

1. **`.env`** at repository root contains **`GEMINI_API_KEY=…`** (if using live Gemini).
2. From the repository root: **`python run_dev.py --smoke`** exits **0**.
3. **`python run_dev.py`** → **`http://127.0.0.1:5001`** (unless **`ORCHESTRATOR_PORT`** set).
4. Settings → save API key updates **`.env`** and chat works without restart.
5. **`GET /api/config/api-key`** returns a masked placeholder when a key is set.
6. Change router model in Settings → next routing uses updated model (no restart), unless **`ORCHESTRATOR_ROUTER_MODEL`** overrides in env.
7. **Settings → Model Registry → Check names with Google** finishes without a key/network error (optional but good after editing model IDs).
8. (Optional) **`pip install -e .`** then **`python -c "import orchestrator_v4.presentation.app"`** succeeds.

---

## Follow-ups (optional, not blockers for local dev)

| Item | Notes |
|------|--------|
| **Packaging** | Frozen **PyInstaller** entry scripts are not part of this standalone repo unless you add them. Smoke path remains **`run_dev.py --smoke`** / **`bootstrap_smoke`**. |
| **`pyproject.toml`** | Done in-folder: optional **`pip install -e .`** / **`uv sync`**; **`run_dev.py`** remains the usual entry (see **Dependencies**). |
| **DB hygiene** | Documented above (**SQLite DB hygiene**). |
| **Strict registry validation** | Done: **`PUT /api/models`** rejects if persisted router id is missing from the new list. |

---

## Summary

**Standalone dev today:** **`run_dev.py`**, package-local **`.env`**, **`requirements.txt`**, **`.gitignore`**, SQLite-backed model registry (curated), router and gateway defaults wired to registry with env overrides, API key routes + live rebind, optional **Check names with Google** preflight (**`models.list`** + public deprecations doc—does not auto-sync the registry).

**For new feature work in Cursor:** keep this file as **reference**; put **step-by-step execution** in a **plan** or todo list so the agent does not confuse “documentation” with “tasks left to run.”
