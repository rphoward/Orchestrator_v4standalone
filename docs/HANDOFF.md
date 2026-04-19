# Handoff — Orchestrator v4 standalone

Session-agnostic snapshot for the next maintainer or a fresh AI context. If this doc fights the code, **trust the code** and fix the doc.

---

## 1. Purpose

This repo is **Orchestrator v4** as a **standalone** Flask app: interview sessions, turns, agent roster, Gemini-backed routing. Layout is **Clean Architecture** at the **repository root**: `core/`, `infrastructure/`, `presentation/`, `bootstrap.py`. The Python package name is **`orchestrator_v4`**; setuptools maps it onto `.` via `pyproject.toml` (`[tool.setuptools] package-dir = { "orchestrator_v4" = "." }`), so there is **no** nested `orchestrator_v4/` folder on disk.

---

## 2. Paths that tripped us

- **This repo (canonical clone path we used):** `c:\Project\orchestrator_v4standalone` — note **`Project`** singular.
- **Backup monorepo copy (rules / history reference only):** `c:\Projects\orchestrator4-main` — **`Projects`** plural. Easy to open the wrong folder in another window.
- If your machine uses different paths, grep this file and update the lines above so future you is not misled.

---

## 3. Git / GitHub

- `main` on GitHub was **force-pushed** once so remote matched the real tree (old remote `main` was unrelated / tiny).
- History here is **not** the full old monorepo history. Do **`git fetch`** before scary resets. **`git reset --hard origin/main`** is only safe if you know `origin/main` is this product, not a stale clone.

---

## 4. Runtime sharp edges (already fixed in `run_dev.py`)

- **Flat package layout:** The launcher reads `pyproject.toml` with **`tomllib`**. If `package-dir` maps `orchestrator_v4` to `.`, the child process **`cwd`** is the **repo root**, not its parent. Nested-monorepo layout (`repo/orchestrator_v4/run_dev.py`) still uses parent as import root — see the docstring at the top of `run_dev.py`.
- **`python -m orchestrator_v4.*`:** On a flat tree you need the package on `sys.path`. After venv ensure, **`run_dev.py`** runs **`uv pip install -e .`** when `uv` is on `PATH` so editable install picks up the mapping. If smoke fails with `No module named 'orchestrator_v4'`, check `uv` and re-run `run_dev.py` once.

---

## 5. Documentation map

| File | Use |
|------|-----|
| [README.md](../README.md) | GitHub-facing quick start, link hub |
| [DEV-STANDALONE.md](../DEV-STANDALONE.md) | Deep runbook: env, SQLite, ports, verification checklist, post-migration honesty |
| [AGENTS.md](../AGENTS.md) | Short agent/human contract + where rules live |
| [monorepo-agents-rescue-checklist.md](monorepo-agents-rescue-checklist.md) | Optional diff against old monorepo `AGENTS.md` — what to ignore vs rescue |
| [../.cursor/rules/](../.cursor/rules/) | Cursor project rules (`.mdc`) |
| [../.cursor/plans/README.md](../.cursor/plans/README.md) | Where active Cursor plans live; skills note |

---

## 6. Cursor rules (`.mdc` inventory)

All under `.cursor/rules/`. **`alwaysApply: true`** on architecture, conduct, safety — they load every chat. Layer rules use **`globs`** so they attach when you edit matching paths.

| File | Role |
|------|------|
| `orchestrator-architecture.mdc` | Layers, import direction, vertical vs horizontal slices, naming pointer |
| `orchestrator-conduct.mdc` | Light workflow + “informal American English” for rule text |
| `orchestrator-safety.mdc` | Deletes, scope, secrets, no drive-by refactors |
| `orchestrator-layer-core.mdc` | `core/**` — no I/O, no outer imports |
| `orchestrator-layer-infrastructure.mdc` | `infrastructure/**` — adapters only |
| `orchestrator-layer-presentation.mdc` | `presentation/**` — thin HTTP/JS glue |
| `orchestrator-doc-style.mdc` | Plain-language style for README, DEV-STANDALONE, plans, screaming rule |
| `orchestrator-screaming-presentation.mdc` | “Screaming” names in `presentation/` — domain vocabulary, JS rename map, cross-cutting shell headers |

---

## 7. Screaming architecture / UI

- **Idea:** Names should shout **interview orchestration**, not “generic web app.” We **kept** horizontal layers; we fix naming **inside** `presentation/`, especially `presentation/static/modules/`.
- **Rule of thumb:** Rename JS modules **when you touch that feature**; update `presentation/static/app.js` and `presentation/static/index.html` in the same change. Full rename table lives in **`orchestrator-screaming-presentation.mdc`**.
- **Cross-cutting shell:** `api.js`, `ui.js`, `state.js`, `utils.js` may keep short names but carry a **short header** stating they are shared shell, not feature modules.

---

## 8. Deferred / optional

- Bulk rename of `sessions.js`, `chat.js`, `reports.js`, `settings*.js` — only when you are already editing those areas.
- Copy old **`.cursor/plans/archive/`** from a backup monorepo into this repo — optional history only.
- Run a **full regression** / add **pytest** when you are ready; smoke is not full coverage.
- Mine old monorepo **`AGENTS.md`** using **`docs/monorepo-agents-rescue-checklist.md`** — do not paste huge legacy blocks into slim `AGENTS.md`.

---

## 9. Verify now

From repo root:

```powershell
python run_dev.py --smoke
```

Expect exit code **0**. For UI: `python run_dev.py` then `http://127.0.0.1:5001` (unless `ORCHESTRATOR_PORT`). You need **`.env`** with `GEMINI_API_KEY` for live Gemini; **`uv`** on PATH if you want auto `.venv` creation (see `DEV-STANDALONE.md`).

---

## 10. Stale warning again

This file is a **map**, not a test suite. When behavior or paths change, update **`docs/HANDOFF.md`** and the **README** docs table so the next handoff stays honest.
