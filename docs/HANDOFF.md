# Handoff — Orchestrator v4 standalone

Session-agnostic snapshot for the next maintainer or a fresh AI context. If this doc fights the code, **trust the code** and fix the doc.

**New conversation:** Cursor does not carry task memory across chats. For work-in-progress (for example the daily driver parchment plan), open the plan file or **`@`-mention it** in the first message so the agent loads the checklist and YAML status. This file is a map only; it does not auto-attach to new threads.

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
| [README.md](../README.md) | GitHub-facing quick start, "Using the application" strip, link hub |
| [USER-GUIDE.md](USER-GUIDE.md) | Hands-on operator walkthrough — sessions, routing, stage tracking, settings |
| [DEV-STANDALONE.md](../DEV-STANDALONE.md) | Deep runbook: env, SQLite, ports, verification checklist, post-migration honesty |
| [DEBUG_INTERVIEW_CHAT.md](DEBUG_INTERVIEW_CHAT.md) | Paste into a fresh chat: stub vs echo vs routing, what shipped, env, files, logs to capture |
| [AGENTS.md](../AGENTS.md) | Short agent/human contract + where rules live |
| [monorepo-agents-rescue-checklist.md](monorepo-agents-rescue-checklist.md) | Optional diff against old monorepo `AGENTS.md` — what to ignore vs rescue |
| [../.cursor/rules/](../.cursor/rules/) | Cursor project rules (`.mdc`) |
| [../.cursor/plans/README.md](../.cursor/plans/README.md) | Where active Cursor plans live; skills note |
| [BUTTON_UI_FEEDBACK_PLAN.md](../.cursor/plans/BUTTON_UI_FEEDBACK_PLAN.md) | Button press + optional UI sounds (static only); YAML tracks completion |
| [DAILY_DRIVER_PARCHMENT_JOURNAL_PLAN.md](../.cursor/plans/DAILY_DRIVER_PARCHMENT_JOURNAL_PLAN.md) | Daily driver parchment + fonts + grain — checklist + YAML track the same slices; **shipped** when both are fully completed |

---

## 6. Cursor rules (`.mdc` inventory)

All under `.cursor/rules/`. **`alwaysApply: true`** on architecture, conduct, safety — they load every chat. Layer rules use **`globs`** so they attach when you edit matching paths.

| File | Role |
|------|------|
| `orchestrator-architecture.mdc` | Layers, import direction, vertical vs horizontal slices, repo-wide naming principle |
| `orchestrator-conduct.mdc` | Workflow + coding behavior, including planning names before file adds or renames |
| `orchestrator-safety.mdc` | Deletes, scope, secrets, no drive-by refactors |
| `orchestrator-layer-core.mdc` | `core/**` — no I/O, no outer imports |
| `orchestrator-layer-infrastructure.mdc` | `infrastructure/**` — adapters only |
| `orchestrator-presentation.mdc` | `presentation/**` — thin HTTP/JS glue plus local naming examples |
| `orchestrator-doc-style.mdc` | Plain-language style for README, DEV-STANDALONE, and plans |

---

## 7. Screaming architecture / UI

- **Idea:** Names should shout **interview orchestration**, not “generic web app.” The naming principle is now **repo-wide** in `orchestrator-architecture.mdc`; `orchestrator-presentation.mdc` just gives local `presentation/` examples.
- **Rule of thumb:** Settle file names in the **plan** when a task adds or renames files. During implementation, rename JS modules **when you touch that feature** and update `presentation/static/app.js` and `presentation/static/index.html` in the same change.
- **Cross-cutting shell:** `api.js`, `ui.js`, `state.js`, `utils.js` may keep short names but carry a **short header** stating they are shared shell, not feature modules.

---

## 8. Deferred / optional

- Bulk rename of `sessions.js`, `chat.js`, `reports.js`, `settings*.js` — only when you are already editing those areas.
- Copy old **`.cursor/plans/archive/`** from a backup monorepo into this repo — optional history only.
- **Pytest is wired** (`[project.optional-dependencies] dev`, `[tool.pytest.ini_options]`, [tests/test_core_entities.py](../tests/test_core_entities.py)) — grow coverage over time; smoke is still not full regression.
- Mine old monorepo **`AGENTS.md`** using **`docs/monorepo-agents-rescue-checklist.md`** — do not paste huge legacy blocks into slim `AGENTS.md`.

---

## 9. Recent landings (update when you ship)

Use this as the **session bridge**: what changed recently on the static UI and tests. It does **not** replace opening [.cursor/plans/DAILY_DRIVER_PARCHMENT_JOURNAL_PLAN.md](../.cursor/plans/DAILY_DRIVER_PARCHMENT_JOURNAL_PLAN.md) in a new chat when that plan is active. If it drifts, delete stale bullets.

**Button press + optional UI sounds (presentation static only)**

- [presentation/static/style.css](../presentation/static/style.css) — `:focus-visible`, `:active` press (filter + reduced-motion transform on primary/send), secondary/icon press, light tab press; `.settings-interface-strip` for the Settings chrome row.
- [presentation/static/index.html](../presentation/static/index.html) — **Interface** row between Settings header and tab bar: checkbox **`id="uiSoundsEnabled"`**, label `for=`; cache-bust query on `style.css` / `app.js` as needed.
- [presentation/static/modules/interview_ui_press_feedback.js](../presentation/static/modules/interview_ui_press_feedback.js) — `initUiFeedback()`, localStorage key **`orchestrator_v4_ui_sounds_enabled`**, Web Audio click on delegated `pointerdown` when enabled.
- [presentation/static/app.js](../presentation/static/app.js) — imports shell + calls `initUiFeedback()` early in `DOMContentLoaded`.
- Plan truth: [.cursor/plans/BUTTON_UI_FEEDBACK_PLAN.md](../.cursor/plans/BUTTON_UI_FEEDBACK_PLAN.md) — YAML `status` should be `completed` when the slice is merged; if the file still says `pending`, reconcile or treat the plan as stale.

**Tests**

- From repo root: `uv pip install -e ".[dev]"` then `uv run pytest` (or `pytest` in the same env). Two smoke tests on core entities today — expand when you touch behavior.

**Daily driver — parchment journal (presentation static)**

- [.cursor/plans/DAILY_DRIVER_PARCHMENT_JOURNAL_PLAN.md](../.cursor/plans/DAILY_DRIVER_PARCHMENT_JOURNAL_PLAN.md) — **done** when plan YAML + checklist both show completed; Google Fonts preconnect + Fraunces / IBM Plex Sans, `--color-bg` / `--color-card` / `--color-border`, Tailwind `themeBg` / `themeSurface`, `.t-display` / `.t-display-italic`, `body::before` grain, `#nextQuestion` pull-quote sizing; `style.css?v=` bumped (e.g. 22) on ship.

**Parchment followup — font chain + Gemini diagnostic logs**

- [.cursor/plans/PARCHMENT_FOLLOWUP_LOGS_AND_HANDOFF_PLAN.md](../.cursor/plans/PARCHMENT_FOLLOWUP_LOGS_AND_HANDOFF_PLAN.md) — Tailwind `fontFamily.sans` extended to `"IBM Plex Sans"` (so `font-sans` actually paints body copy); `.section-label` 800 → 700; `style.css?v=23`. Added INFO logs in [infrastructure/ai/gemini_interview_llm_gateway.py](../infrastructure/ai/gemini_interview_llm_gateway.py) (`route_intent` + `get_response` parts breakdown) and [core/use_cases/conduct_interview_turn.py](../core/use_cases/conduct_interview_turn.py); [presentation/app.py](../presentation/app.py) uses `logging.basicConfig` so our lines show in dev.

**Next session — read this first**

- [docs/NEXT_SESSION_HANDOFF.md](NEXT_SESSION_HANDOFF.md) — one-page brief to diagnose the chat "echo" bug with the new logs (repro, decision tree, files to open). **Update (echo, case 1):** [infrastructure/ai/gemini_interview_llm_gateway.py](../infrastructure/ai/gemini_interview_llm_gateway.py) `get_response` now returns assembled non-thought `Part` text when `include_thoughts=True` (instead of `response.text` only) and raises if the model returns only thought parts; re-test a turn with agent 4 and watch the same INFO lines.

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
