# Orchestrator v4 — Standalone developer handbook

**What this file is:** Onboarding and operations reference for the **`orchestrator_v4/`** tree. It describes **current behavior**, how to run and verify it, and **optional follow-ups**.

**What this file is not:** A Cursor execution plan. For agent-driven multi-step work, use **`.cursor/plans/`** for new plans (see **`archive/`** for executed history), or your task system; point the model at this doc only for context.

**Goal:** Run and configure the app **from inside `orchestrator_v4/`** without depending on a parent monorepo folder for secrets or manual `cd` to import the package.

---

## Quick start

1. On disk, keep layout **`…/something/orchestrator_v4/`** (folder name must stay **`orchestrator_v4`**).
2. Put secrets in **`orchestrator_v4/.env`** (at minimum `GEMINI_API_KEY=…` if you use live Gemini).
3. From **`orchestrator_v4/`**: **`python run_dev.py`** (web UI, default port **5001**) or **`python run_dev.py --smoke`** (bootstrap smoke).
4. First run: if **`.venv`** is missing, **`run_dev.py`** expects **`uv`** on `PATH` and will create **`.venv`** and install **`requirements.txt`**. Otherwise create a venv yourself and install deps, then run again.

---

## Python layout (why `run_dev.py` exists)

- The importable package is the folder **`orchestrator_v4`** (`bootstrap.py`, `core/`, `presentation/`, …).
- For **`python -m orchestrator_v4.…`** to resolve, the process **`cwd`** must be the directory **that contains** that folder (the **import root**).
- **`run_dev.py`** sets the child process **`cwd`** to that parent and runs **`python -m orchestrator_v4.presentation.app`** (or **`python -m orchestrator_v4.bootstrap_smoke`** with **`--smoke`**). It uses the **`.venv`** interpreter inside **`orchestrator_v4/`** when present. (**PyInstaller** uses repo-root **`orchestrator4_entry.py`**, not this smoke module.)

---

## Dependencies

**File:** [`requirements.txt`](requirements.txt) in this folder.

Stack: Flask, `google-genai`, `python-dotenv` (and transitive deps).

**Optional editable install:** [`pyproject.toml`](pyproject.toml) mirrors those dependencies for **`pip install -e .`** or **`uv sync`** from **`orchestrator_v4/`** (handy for tooling or importing the package from another venv). **Portability:** you do **not** need an editable install for day-to-day dev—**`run_dev.py`** plus **`requirements.txt`** (or **`uv`** creating **`.venv`**) remains the supported path and sets the correct import root for **`python -m orchestrator_v4.…`**.

**Without `uv`:** Create **`.venv`**, activate, **`pip install -r requirements.txt`**, then **`python run_dev.py`**. Generic advice: **`.venv`** often breaks if copied to a different path or machine—recreate when that happens. **Internal sandbox workflow:** if you deliberately paste the **whole `orchestrator_v4/`** folder including **`.venv`**, see root **`AGENTS.md`** (v4 folder / sandbox note) so agents align with that habit.

---

## Environment files

| Location | Role |
|----------|------|
| **`orchestrator_v4/.env`** | Primary dev secrets and overrides. Loaded by **`bootstrap.py`** (dev) via **`_src_dir()`**. Also read/written by Settings API key UI (`set_key` / `dotenv_values`). |
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

## SQLite DB hygiene (`runtime/orchestrator.db`)

**What the file holds:** sessions, conversations, routing logs, agents (including per-agent model ids), prompt templates, **`config`** (model registry JSON, router model id, and other keys). Paths default under **`runtime/`** unless **`ORCHESTRATOR_DB_PATH`** points elsewhere.

| Situation | Suggestion |
|-----------|------------|
| **Fresh start / corrupted DB** | Stop the app, delete **`runtime/orchestrator.db`** (and keep **`runtime/prompts/`** as needed). Next launch recreates the file and seeds default agents; registry falls back to defaults until you configure again. |
| **Thinking defaults on existing DBs** | On each startup, **`ensure_orchestrator_database`** inserts **`config`** keys **`thinking_level_1`** … **`thinking_level_5`** only when a key is missing (agents 1–4 → **LOW**, agent 5 → **HIGH**). It never overwrites values you already set. Deleting **`orchestrator.db`** is still the full reset if you want a clean slate. |
| **Copying a DB from another machine or old backup** | Expect **stale router and registry** (and agent **`model`** columns) versus what you run today. Either accept that and fix in Settings, or delete the DB and re-seed, or run a one-way migration/script you trust. |
| **Sandbox / full-folder paste** | If you paste **`orchestrator_v4/`** including **`runtime/orchestrator.db`**, you are copying **someone else’s** session and config. For a clean demo, delete **`orchestrator.db`** or use an empty **`runtime/`**. |
| **Do not commit** | The file is gitignored; treat it as **local state**, not source of truth for the team. |

---

## Settings: API key endpoint

- **`GET` / `PUT /api/config/api-key`** — JSON **`masked_key`**; PUT body **`api_key`**. Writes **`GEMINI_API_KEY`** into package **`.env`** and calls **`bootstrap.apply_gemini_api_key`**, which **`rebind_llm_gateway()`** so turns use the new key without restart.
- Front-end: [`presentation/static/modules/settings_agent.js`](presentation/static/modules/settings_agent.js).

---

## Git (standalone copy)

**File:** [`.gitignore`](.gitignore) — **`/.env`** and **`/.venv/`** so a mini-repo under **`orchestrator_v4/`** does not commit secrets or local venvs.

---

## Optional: Pylance when the workspace folder is only `orchestrator_v4`

Add **`.vscode/settings.json`** (not committed in all setups) with:

```json
{
  "python.analysis.extraPaths": ["${workspaceFolder}/.."]
}
```

Runtime is unchanged; this only helps analysis resolve **`orchestrator_v4.*`** imports.

---

## Verification checklist

1. **`orchestrator_v4/.env`** contains **`GEMINI_API_KEY=…`** (if using live Gemini).
2. From **`orchestrator_v4/`:** **`python run_dev.py --smoke`** exits **0**.
3. **`python run_dev.py`** → **`http://127.0.0.1:5001`** (unless **`ORCHESTRATOR_PORT`** set).
4. Settings → save API key updates **`.env`** and chat works without restart.
5. **`GET /api/config/api-key`** returns a masked placeholder when a key is set.
6. Change router model in Settings → next routing uses updated model (no restart), unless **`ORCHESTRATOR_ROUTER_MODEL`** overrides in env.
7. **Settings → Model Registry → Check names with Google** finishes without a key/network error (optional but good after editing model IDs).
8. (Optional) From **`orchestrator_v4/`:** **`pip install -e .`** then **`python -c "import orchestrator_v4.presentation.app"`** succeeds.

---

## Follow-ups (optional, not blockers for local dev)

| Item | Notes |
|------|--------|
| **Packaging** | README / monorepo docs already use **`orchestrator4_entry.py`** for PyInstaller. Smoke CLI is **`bootstrap_smoke.py`** (not an app entry). |
| **`pyproject.toml`** | Done in-folder: optional **`pip install -e .`** / **`uv sync`**; **`run_dev.py`** remains the usual entry (see **Dependencies**). |
| **DB hygiene** | Documented above (**SQLite DB hygiene**). |
| **Strict registry validation** | Done: **`PUT /api/models`** rejects if persisted router id is missing from the new list. |

---

## Summary

**Standalone dev today:** **`run_dev.py`**, package-local **`.env`**, **`requirements.txt`**, **`.gitignore`**, SQLite-backed model registry (curated), router and gateway defaults wired to registry with env overrides, API key routes + live rebind, optional **Check names with Google** preflight (**`models.list`** + public deprecations doc—does not auto-sync the registry).

**For new feature work in Cursor:** keep this file as **reference**; put **step-by-step execution** in a **plan** or todo list so the agent does not confuse “documentation” with “tasks left to run.”
