# AGENTS.md — Orchestrator v4 (standalone)

## 1. Project identity and voice

- **What this is:** Flask interview orchestration (sessions, turns, agent roster, Gemini routing) using **Clean Architecture** at the repo root: `core/`, `infrastructure/`, `presentation/`, `bootstrap.py`. Python package name: **`orchestrator_v4`** (`pyproject.toml`).
- **Slices:** **Horizontal** = those layers (fixed dependency direction). **Vertical** = one feature cutting through layers (use case + port + adapter + HTTP)—must keep horizontal boundaries clean. Full map: **`.cursor/rules/orchestrator-architecture.mdc`** (always loaded).
- **Voice:** Plain English, workshop tone. Push back on real risks (secrets, data loss, scope). Use words already in the codebase; domain words and layer words both count.
- **Runbooks:** [`DEV-STANDALONE.md`](DEV-STANDALONE.md) for env, SQLite, ports, verification checklist.

## 2. Where instructions live

| Kind | Location |
|------|-----------|
| **Architecture + naming principle** | `.cursor/rules/orchestrator-architecture.mdc` |
| **Layer rules** | `orchestrator-layer-core.mdc`, `orchestrator-layer-infrastructure.mdc`, `orchestrator-presentation.mdc` |
| **Conduct + safety** | `orchestrator-conduct.mdc`, `orchestrator-safety.mdc` |
| **This file** | Short contract—no long architecture prose here |
| **Operations** | `DEV-STANDALONE.md` |
| **Operator UI walkthrough** | `docs/USER-GUIDE.md` |

## 3. Commands (repository root)

- **UI:** `python run_dev.py` → `http://127.0.0.1:5001` (unless `ORCHESTRATOR_PORT`).
- **Smoke:** `python run_dev.py --smoke` → exit **0**.
- **Deps / venv:** `requirements.txt`, `run_dev.py`, `DEV-STANDALONE.md`.
- **Secrets:** `.env` at repo root—never commit.

## 4. Hard constraints

Obey **`.cursor/rules/orchestrator-safety.mdc`** (destructive commands, scope, secrets, no drive-by refactors). Obey layer rules when touching `core/`, `infrastructure/`, or `presentation/`.

## 5. Verification

- Run `pytest` from repo root if a test tree exists.
- After bootstrap or wiring changes: `python run_dev.py --smoke`.
- Full regression not assumed—see checklist in `DEV-STANDALONE.md`.

## 6. Legacy monorepo AGENTS

Not copied here on purpose. If you diff against an old monorepo `AGENTS.md`, use **[`docs/monorepo-agents-rescue-checklist.md`](docs/monorepo-agents-rescue-checklist.md)** so you only pull over what still applies.
