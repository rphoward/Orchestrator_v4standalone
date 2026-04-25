---
name: Stage tracking cleanup audit
overview: "Audit of hybrid stage tracking + observability finds one clear presentation-layer misplacement, large duplicate blocks in the two conduct-turn use cases, and two root-level prototype scripts that are not wired into the app. The smallest cleanup slice is: relocate stage-tracking config HTTP without changing URLs, extract one shared post-reply stage-tracking helper for both use cases, move the prototype scripts into docs/ (do not delete) with a short DEV-STANDALONE note, then run pytest and smoke. Todos (st-01 through st-15) are the contract: one per pass, in order, no batching. Architecture and workflow decisions in this file + governing rules are authoritative so the implementer is not choosing strategy while stressed with code."
todos:
  - id: st-01-grep
    content: "Grep repo for stage-tracking in presentation: `stage-tracking`, `_stage_tracking`, `gemini_connection_routes`. Note every file that references the helpers or route (expect tests + gemini_connection_routes + app.py)."
    status: completed
  - id: st-02-new-routes-file
    content: "Create `presentation/interview_stage_tracking_settings_routes.py`. Copy from `gemini_connection_routes.py` ONLY: `_stage_tracking_settings_payload`, `_stage_tracking_request_value`, and the `@app.route(\"/api/config/stage-tracking\", ...)` block. Rename register fn to `register_interview_stage_tracking_settings_routes(app)`. Imports: Flask, jsonify, request, bootstrap, `json_body_dict` + `validation_error_response` from `http_helpers` (same as gemini file). No infrastructure imports."
    status: completed
  - id: st-03-wire-app
    content: "Edit `presentation/app.py`: import `register_interview_stage_tracking_settings_routes`, call it on `app` (same style as other `register_*`). Pick a sensible order next to other config routes."
    status: completed
  - id: st-04-trim-gemini
    content: "Edit `presentation/gemini_connection_routes.py`: delete the two `_stage_tracking_*` helpers and the `/api/config/stage-tracking` route only. Leave all Gemini/model routes unchanged."
    status: completed
  - id: st-05-grep-again
    content: "Grep again for `_stage_tracking` / `stage-tracking` under `presentation/` and `tests/`. Fix any broken imports (only expected breakage: tests that imported helpers from gemini_connection_routes)."
    status: completed
  - id: st-06-fix-api-contract-test
    content: "Edit `tests/test_stage_tracking_api_contract.py`: import the new module instead of `gemini_connection_routes` for `_stage_tracking_settings_payload` and `register_*` in the Flask app test. Run `pytest tests/test_stage_tracking_api_contract.py -q` until green."
    status: completed
  - id: st-07-read-duplicate-block
    content: "Open `conduct_interview_turn.py` and `conduct_manual_interview_turn.py`. Find the **byte-identical** stretch after the assistant line is appended: from `settings = self._stage_tracking_settings_store.read()` through `st_log = append_capped_stage_tracking_log(...)`. In the middle you will see `next_current = earliest_unfinished_stage(...)`, then the **New Session** rename (`session_renamed` / `new_name`), then `ep` / `StageTrackingTurnSnapshot` / `st_log` — all of that is duplicated. It ends **immediately before** `self._turn_store.update_session_state`. Note line numbers; do not edit yet."
    status: completed
  - id: st-08-add-finalize-module
    content: "Add `core/use_cases/finalize_chat_turn_stage_tracking.py` with one function (or a frozen `@dataclass` result type) holding **only** that duplicated stretch: settings read through `st_log` (including New Session rename + snapshot). Return values the two callers need for `update_session_state` and HTTP results: at minimum `new_flags`, `stage_progress_json`, `next_current`, `new_name`, `session_renamed` (or equivalent for the `name=` arg), `st_log`, and `stage_tracking` as the public dict (`stage_snapshot.to_public_dict()`). Parameters: `ctx`, `acting_agent_id`, `messages_full`, `user_input`, `turn_endpoint` (`\"auto\"` | `\"manual\"`), `settings_store`, `stage_completion_judge`, `logger`. Imports: `core/*` only (entities, ports, `stage_tracking_judge_runner`). Wire `InterviewStageCompletionJudge` as the port type."
    status: completed
  - id: st-09-wire-auto-turn
    content: "In `conduct_interview_turn.py`, delete the duplicated stretch and call the helper with `turn_endpoint=\"auto\"`, `acting_agent_id=target_agent_id`, `user_input=text`. Keep everything **before** `settings = ...` (routing, LLM, `messages_full`) and everything **after** the stretch (`update_session_state`, `InterviewTurnResult`, imports) in this file."
    status: completed
  - id: st-10-wire-manual-turn
    content: "In `conduct_manual_interview_turn.py`, same as `st-09` with `turn_endpoint=\"manual\"` and `acting_agent_id=agent_id`. Preserve manual-only preamble (routing log, etc.) and `ManualInterviewTurnResult` assembly."
    status: completed
  - id: st-11-pytest-stage-tracking
    content: "Run `pytest tests/test_stage_tracking_turns.py tests/test_stage_progress.py tests/test_stage_tracking_settings_use_cases.py -q`. Fix any failures before continuing."
    status: completed
  - id: st-12-move-proposed-to-docs
    content: "**Do not delete.** Move `proposedpierce_holt.py` and `proposedgemini_interview_llm_gateway.py` from repo root into `docs/` (same filenames is fine, e.g. `docs/proposedpierce_holt.py`). They are reference sketches only — nothing in `orchestrator_v4` or tests imports them. After the move, grep the repo for `proposedpierce_holt` / `proposedgemini` to ensure no broken paths or docs links still point at the old root location; fix links if any."
    status: completed
  - id: st-13-dev-standalone-bullet
    content: "Add one short bullet to `DEV-STANDALONE.md` (plain English, orchestrator-doc-style): the two old root prototype `.py` files now live under `docs/` for historical reference; the running app is only what ships under `orchestrator_v4` / `bootstrap`."
    status: completed
  - id: st-14-full-pytest-smoke
    content: "From repo root: `pytest -q` then `python run_dev.py --smoke`. List touched files and any remaining risks in the PR or session note."
    status: completed
  - id: st-15-optional-flask-get-log
    content: "Optional: tiny Flask test_client GET `/api/sessions/1/stage-tracking` monkeypatching `bootstrap.read_session_stage_tracking_log` — assert 200 and JSON shape. Skip if timeboxed."
    status: completed
isProject: false
---

# Stabilization audit and smallest cleanup slice

## Governing rules (`.cursor/rules` — not in the original task doc)

Implementation and doc edits stay inside these contracts:

- **[`orchestrator-architecture.mdc`](.cursor/rules/orchestrator-architecture.mdc):** Horizontal layers stay strict: `core/` never depends on `infrastructure/` or `presentation/`; `bootstrap.py` remains the only composition root. Vertical cleanup tightens boundaries (smaller handlers, clearer ports), no shortcuts across layers. Naming stays interview-domain (session, turn, stage tracking, roster).
- **[`orchestrator-layer-core.mdc`](.cursor/rules/orchestrator-layer-core.mdc):** Entities = shapes + pure rules; use cases = one runnable step, ports + entities only, no I/O. The extracted post-reply helper must live under `core/use_cases/` and import only `core/*` (same as today's duplicated block).
- **[`orchestrator-layer-infrastructure.mdc`](.cursor/rules/orchestrator-layer-infrastructure.mdc):** This slice should **not** need infrastructure edits; adapters keep implementing ports only, no `presentation` imports, avoid pulling in `core.use_cases` from adapters.
- **[`orchestrator-presentation.mdc`](.cursor/rules/orchestrator-presentation.mdc):** Routes stay thin: parse → `bootstrap` use case → JSON. **No** `orchestrator_v4.infrastructure` in route modules. **No** new top-level `helpers.py` / `utils.py` / `misc_routes.py` — use a file name that states the interview behavior (settled: **`interview_stage_tracking_settings_routes.py`** for `/api/config/stage-tracking` only). Prefer importing use-case results over `core.entities` in handlers when practical (today's payload helpers only read fields off the object returned by `Read`/`Update` use cases; keep that pattern). **Renaming `presentation/static/app.js` / `index.html`** applies when renaming a *static feature module*; this slice only adds a Python route module + `app.py` registration, so no static renames unless we later rename JS (not in scope).
- **[`orchestrator-conduct.mdc`](.cursor/rules/orchestrator-conduct.mdc):** Touch `DEV-STANDALONE.md` only for intentional operator-facing facts (scratch removal note counts). Informal American English, short bullets.
- **[`orchestrator-doc-style.mdc`](.cursor/rules/orchestrator-doc-style.mdc):** The new DEV-STANDALONE line is one atomic idea, plain wording, no unexplained jargon.
- **[`orchestrator-safety.mdc`](.cursor/rules/orchestrator-safety.mdc):** Moving two specific root files into `docs/` is scoped, not a bulk wipe. Do not use mass delete on directories.

---

## How to run this plan (lighter model — e.g. Composer 2)

Do **one todo at a time** (`st-01` … `st-15`). After each todo, run the mini-check in that todo if it says to run pytest.

**No compacting, no fake tracks:** The `st-XX` list is the real schedule. Do not merge several todos into one turn (“I’ll do st-01 through st-04 together”), do not invent parallel or staggered workstreams, and do not treat Batch A / B / C as separate execution lanes — they are only **headings** so a human can see which paths change. If one step is still heavy, stop after **st-07** and do **st-08** in a fresh pass (same spec: still no skipping or combining other todos). If something in this file conflicts with a shortcut the model invents, **this file and the Governing rules win**.

**Batch A — routes only (todos `st-01`–`st-06`):** touch only `presentation/gemini_connection_routes.py`, new `presentation/interview_stage_tracking_settings_routes.py`, `presentation/app.py`, `tests/test_stage_tracking_api_contract.py`. Goal: URLs and JSON unchanged; config stage-tracking no longer lives in the Gemini file.

**Batch B — duplicate logic (todos `st-07`–`st-11`):** touch `core/use_cases/finalize_chat_turn_stage_tracking.py` (new), `conduct_interview_turn.py`, `conduct_manual_interview_turn.py`. Goal: move-only refactor; `pytest` on stage-tracking tests green.

**Batch C — housekeeping + verify (todos `st-12`–`st-15`):** move two root prototypes into `docs/`, one `DEV-STANDALONE.md` bullet, full `pytest` + smoke. Optional Flask test last.

**If stuck:** re-read the **Governing rules** section and `.cursor/rules/orchestrator-presentation.mdc` + `orchestrator-layer-core.mdc` — the usual failure is importing `infrastructure` from a route, or importing `presentation` from `core/`.

---

## Audit (current state)

**Layering is mostly correct:** pure rules and DTOs live in [`core/entities/stage_progress.py`](core/entities/stage_progress.py) (settings normalization, compact `stage_progress` JSON, `should_run_stage_tracking_judge`, evidence heuristics), [`core/entities/stage_evaluator.py`](core/entities/stage_evaluator.py) (pointer, veto, heuristic flag merge), [`core/entities/stage_tracking_turn_snapshot.py`](core/entities/stage_tracking_turn_snapshot.py) (per-turn observability dict + capped log append). Judge execution is shared in [`core/use_cases/stage_tracking_judge_runner.py`](core/use_cases/stage_tracking_judge_runner.py). Report-time refresh is isolated in [`core/use_cases/refresh_stage_tracking_before_report.py`](core/use_cases/refresh_stage_tracking_before_report.py). Persistence adapters stay in `infrastructure/` (e.g. [`sqlite_stage_tracking_settings_store.py`](infrastructure/persistence/sqlite_stage_tracking_settings_store.py), turn store columns). Read-only observability use case: [`core/use_cases/read_session_stage_tracking_log.py`](core/use_cases/read_session_stage_tracking_log.py) — no judge port, no LLM.

**Redundant / misleading modules**

- Repo root [`proposedpierce_holt.py`](proposedpierce_holt.py) and [`proposedgemini_interview_llm_gateway.py`](proposedgemini_interview_llm_gateway.py): not imported by `orchestrator_v4` or tests; older sketch copies of ideas that now live in [`core/entities/pierce_holt_engine.py`](core/entities/pierce_holt_engine.py) and the real LLM gateway. **Plan:** move both files into [`docs/`](docs/) (keep the files; clear the root so operators are not confused). Not redundant in the sense of "delete safely" — treat as **archived reference**.

**Duplicated logic (primary fix — high impact, treat as delicate)**

- [`core/use_cases/conduct_interview_turn.py`](core/use_cases/conduct_interview_turn.py) and [`core/use_cases/conduct_manual_interview_turn.py`](core/use_cases/conduct_manual_interview_turn.py) share an ~85-line block after the assistant message is appended: read settings → hybrid `advance_stage_progress_json` → `should_run_stage_tracking_judge` → optional `apply_stage_completion_judge_detailed` + hybrid `record_stage_judge_attempt_json` → `earliest_unfinished_stage` → **New Session** rename → build `StageTrackingTurnSnapshot` → `append_capped_stage_tracking_log`. Same `update_session_state` arguments afterward. Only parameterization: `turn_endpoint` (`"auto"` vs `"manual"`) and the acting agent id (`target_agent_id` vs `agent_id`). **Critical:** keep `apply_stage_completion_judge_detailed(..., stage_flags_before=ctx.stage_flags(), ...)` exactly as today (same object as at call time as the local `flags_before` copy); do not substitute `flags_before` unless you have proven equivalence with tests.

**Oversized config / status**

- [`core/entities/stage_progress.py`](core/entities/stage_progress.py) (~297 lines) bundles settings DTO + normalization, compact progress serialization, and judge gating. It is cohesive and not an outlier; **splitting is optional** and only worth it if you want separate files for "persisted settings shape" vs "progress JSON" vs "gate" — that would touch many imports for marginal gain. **Recommendation: leave as one module** and document that boundary in a short module docstring or one comment at the top listing the three concerns (no file split in this slice).

**Unclear boundaries (presentation)**

- [`GET`/`PUT /api/config/stage-tracking`](presentation/gemini_connection_routes.py) lives inside [`presentation/gemini_connection_routes.py`](presentation/gemini_connection_routes.py) (`_stage_tracking_settings_payload`, `_stage_tracking_request_value`, first route in `register_gemini_connection_routes`). That couples **interview stage-tracking settings** to the **Gemini connection** vertical slice. The older plan [`.cursor/plans/hybrid-stage-tracking_a0e99380.plan.md`](.cursor/plans/hybrid-stage-tracking_a0e99380.plan.md) already named a dedicated `presentation/stage_tracking_settings_routes.py`-style module.

**Settings across layers**

- Acceptable: normalization in core entity module, port + SQLite adapter, thin use cases in [`core/use_cases/stage_tracking_settings.py`](core/use_cases/stage_tracking_settings.py), HTTP in presentation. After the move, **only the registration import** in [`presentation/app.py`](presentation/app.py) changes alongside the new route module.

**Tests vs your checklist**

| # | Requirement | Current coverage |
|---|----------------|------------------|
| 1 | Auto + hybrid early turn skips judge | [`test_auto_hybrid_early_turn_skips_judge`](tests/test_stage_tracking_turns.py) |
| 2 | Manual + hybrid updates progress | [`test_manual_hybrid_turn_writes_progress_for_selected_agent`](tests/test_stage_tracking_turns.py) |
| 3 | Semantic calls judge for agents 1–4 | [`test_semantic_mode_calls_judge_for_eligible_turn`](tests/test_stage_tracking_turns.py) (agent 3 only — **minor gap** if you want explicit 1 and 4; behavior is identical via `should_run_stage_tracking_judge`) |
| 4 | Agent 5 skips progress, judge, flags | [`test_manual_agent_five_skips_judge_progress_and_flags`](tests/test_stage_tracking_turns.py); auto path never routes to 5 as written (hints exclude 5; veto clamps past pointer) |
| 5 | Compact progress cannot complete stage alone | [`test_compact_progress_alone_cannot_mark_stage_complete`](tests/test_stage_tracking_turns.py) |
| 6 | Observability does not trigger LLM | [`ReadSessionStageTrackingLog`](core/use_cases/read_session_stage_tracking_log.py) has no gateway/judge; [`test_read_session_stage_tracking_log_is_read_only`](tests/test_stage_tracking_turns.py) checks idempotent reads. **Optional small add:** Flask `GET /api/sessions/<id>/stage-tracking` test client test (same URL) to lock the wire path — no bootstrap rebind to real Gemini needed if the route only calls `read_session_stage_tracking_log`. |
| 7–8 | Settings persist / invalid normalize | [`tests/test_stage_tracking_settings_use_cases.py`](tests/test_stage_tracking_settings_use_cases.py) |

**Non-goals (per your constraints)**

- No prompt edits, no model selection changes, no changes to [`InterviewStageCompletionJudge`](core/ports/interview_stage_completion_judge.py) or [`GeminiStageCompletionJudge`](infrastructure/ai/gemini_stage_completion_judge.py) contracts, no new product features.

---

## Smallest cleanup slice (proposed edits)

1. **Presentation boundary:** Add [`presentation/interview_stage_tracking_settings_routes.py`](presentation/interview_stage_tracking_settings_routes.py) with `register_interview_stage_tracking_settings_routes(app)` (name matches [`orchestrator-presentation.mdc`](.cursor/rules/orchestrator-presentation.mdc) "say the feature out loud" and aligns with the hybrid plan's intent for a dedicated module, without the generic word `config` as the file stem). Move `_stage_tracking_settings_payload`, `_stage_tracking_request_value`, and `GET`/`PUT /api/config/stage-tracking` out of [`gemini_connection_routes.py`](presentation/gemini_connection_routes.py). Register in [`presentation/app.py`](presentation/app.py). **Leave** `GET /api/sessions/<id>/stage-tracking` in [`interview_session_routes.py`](presentation/interview_session_routes.py) (session observability stays with session routes). **URLs and JSON unchanged** → no static UI edits required.

2. **Duplicate conduct-turn logic:** Add [`core/use_cases/finalize_chat_turn_stage_tracking.py`](core/use_cases/finalize_chat_turn_stage_tracking.py) with one function (or result dataclass) that holds the duplicated stretch from settings read through `st_log`, **including** the identical **New Session** rename block between `next_current` and the snapshot. Callers keep routing/LLM/`messages_full` above and `update_session_state` + return dataclass below. **No logic changes** — move-only refactor with identical control flow.

3. **Root prototype scripts:** **Move** (do not delete) [`proposedpierce_holt.py`](proposedpierce_holt.py) and [`proposedgemini_interview_llm_gateway.py`](proposedgemini_interview_llm_gateway.py) into [`docs/`](docs/) under the same or clear names. Add **one** plain-language bullet in [`DEV-STANDALONE.md`](DEV-STANDALONE.md) per [`orchestrator-doc-style.mdc`](.cursor/rules/orchestrator-doc-style.mdc): where the files went and that the runnable app is under `orchestrator_v4` / `bootstrap` only.

4. **Comments:** Add **only** where product rules are non-obvious after extraction — e.g. on the new helper: manual routing chooses agent only; stage tracking still runs post-reply; agent 5 ineligibility is enforced by `is_stage_tracking_eligible_agent`; observability path does not call the judge (if not already obvious from imports).

5. **Tests (minimal):** Update [`tests/test_stage_tracking_api_contract.py`](tests/test_stage_tracking_api_contract.py) to import/register from the **new** route module instead of `gemini_connection_routes`. Optionally add one Flask test for `GET /api/sessions/1/stage-tracking` returning `entries` without invoking export refresh (monkeypatch `bootstrap.read_session_stage_tracking_log` if you want zero DB). Run **`pytest -q`** and **`python run_dev.py --smoke`** from repo root.

---

## Risks

- **Extract helper (main risk):** Copy the duplicated block **line-for-line** into `finalize_chat_turn_stage_tracking.py`, then delete from both conduct files in one PR so `git diff` shows a pure move. Keep `stage_flags_before=ctx.stage_flags()` on the judge call (not a stale `flags_before` unless identical). Keep order: progress → gate → judge → `next_current` → rename → snapshot → log. Run `tests/test_stage_tracking_turns.py` after wiring **each** conduct file if you split `st-09`/`st-10` across commits.

- **Route move:** If anything else imported private helpers from `gemini_connection_routes` besides the API contract test, grep and update those imports.

- **Moved prototypes:** If any README or doc linked to the old root paths, update the path to `docs/...`.

---

## Verification (mandatory)

- `pytest -q`
- `python run_dev.py --smoke`
- List changed files and any remaining risks (e.g. optional semantic agents 1/4 tests not added).
