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
| [BUTTON_UI_FEEDBACK_PLAN.md](../.cursor/plans/BUTTON_UI_FEEDBACK_PLAN.md) | Button press + optional UI sounds (static only); YAML tracks completion |
| [DAILY_DRIVER_PARCHMENT_JOURNAL_PLAN.md](../.cursor/plans/DAILY_DRIVER_PARCHMENT_JOURNAL_PLAN.md) | Daily driver parchment + fonts + grain (not executed until YAML completed) |

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
- **Pytest is wired** (`[project.optional-dependencies] dev`, `[tool.pytest.ini_options]`, [tests/test_core_entities.py](../tests/test_core_entities.py)) — grow coverage over time; smoke is still not full regression.
- Mine old monorepo **`AGENTS.md`** using **`docs/monorepo-agents-rescue-checklist.md`** — do not paste huge legacy blocks into slim `AGENTS.md`.

---

## 9. Recent landings (update when you ship)

Use this as the **session bridge**: what changed recently on the static UI and tests. If it drifts, delete stale bullets.

**Button press + optional UI sounds (presentation static only)**

- [presentation/static/style.css](../presentation/static/style.css) — `:focus-visible`, `:active` press (filter + reduced-motion transform on primary/send), secondary/icon press, light tab press; `.settings-interface-strip` for the Settings chrome row.
- [presentation/static/index.html](../presentation/static/index.html) — **Interface** row between Settings header and tab bar: checkbox **`id="uiSoundsEnabled"`**, label `for=`; cache-bust query on `style.css` / `app.js` as needed.
- [presentation/static/modules/interview_ui_press_feedback.js](../presentation/static/modules/interview_ui_press_feedback.js) — `initUiFeedback()`, localStorage key **`orchestrator_v4_ui_sounds_enabled`**, Web Audio click on delegated `pointerdown` when enabled.
- [presentation/static/app.js](../presentation/static/app.js) — imports shell + calls `initUiFeedback()` early in `DOMContentLoaded`.
- Plan truth: [.cursor/plans/BUTTON_UI_FEEDBACK_PLAN.md](../.cursor/plans/BUTTON_UI_FEEDBACK_PLAN.md) — YAML `status` should be `completed` when the slice is merged; if the file still says `pending`, reconcile or treat the plan as stale.

**Tests**

- From repo root: `uv pip install -e ".[dev]"` then `uv run pytest` (or `pytest` in the same env). Two smoke tests on core entities today — expand when you touch behavior.

**Next UI (not executed in this handoff snapshot)**

- **Next aesthetic (planned, not assumed shipped):** [.cursor/plans/DAILY_DRIVER_PARCHMENT_JOURNAL_PLAN.md](../.cursor/plans/DAILY_DRIVER_PARCHMENT_JOURNAL_PLAN.md) — daily driver parchment, warm card, Fraunces + IBM Plex Sans, paper grain. Execute only after explicit go-ahead; confirm with `style.css` `:root` and `index.html` Tailwind `themeBg` / `themeSurface` if unsure whether it merged.

---

## 10. Verify now

From repo root:

```powershell
python run_dev.py --smoke
```

Expect exit code **0**. For UI: `python run_dev.py` then `http://127.0.0.1:5001` (unless `ORCHESTRATOR_PORT`). You need **`.env`** with `GEMINI_API_KEY` for live Gemini; **`uv`** on PATH if you want auto `.venv` creation (see `DEV-STANDALONE.md`).

After Python changes, also run **`uv run pytest`** (or `pytest`) so the small test suite stays green.

---

## 11. Stale warning again

This file is a **map**, not a test suite. When behavior or paths change, update **`docs/HANDOFF.md`** and the **README** docs table so the next handoff stays honest.
