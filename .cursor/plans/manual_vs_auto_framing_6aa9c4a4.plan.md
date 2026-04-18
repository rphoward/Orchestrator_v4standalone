---
name: Manual vs auto refactor
overview: Extract shared roster/turn helpers from four use cases into one core module; add routing-log, stage evaluation, and full session-state updates to manual turns (same depth heuristic as routed turns); fix misleading "Routed to" UI label on manual sends. This plan is kept as a replayable record, so symbol anchors matter more than line numbers.
todos:
  - id: t01-create-roster-helpers-module
    content: "Create file `orchestrator_v4/core/entities/agent_roster_helpers.py`. Move into it these four functions (typed versions from conduct_interview_turn.py): `roster_agent_name`, `system_prompt_for_agent`, `agent_entry_for_id`, `count_user_chat`. Drop the leading underscore since they are now public. Keep signatures identical except remove underscore prefix."
    status: completed
  - id: t02-rewire-conduct-interview-turn
    content: "In `orchestrator_v4/core/use_cases/conduct_interview_turn.py`: delete the four local `_roster_agent_name`, `_system_prompt_for_agent`, `_agent_entry_for_id`, `_count_user_chat` definitions. Add `from orchestrator_v4.core.entities.agent_roster_helpers import roster_agent_name, system_prompt_for_agent, agent_entry_for_id, count_user_chat`. Update all call sites in the file to use the new names (no underscore)."
    status: completed
  - id: t03-rewire-conduct-manual-interview-turn
    content: "In `orchestrator_v4/core/use_cases/conduct_manual_interview_turn.py`: delete the four local helper definitions. Add the same import from `agent_roster_helpers`. Update all call sites in the file to use the new names (no underscore)."
    status: completed
  - id: t04-rewire-initialize-interview-session
    content: "In `orchestrator_v4/core/use_cases/initialize_interview_session.py`: delete local `_system_prompt_for_agent` and `_agent_entry`. Add import of `system_prompt_for_agent` and `agent_entry_for_id` from `agent_roster_helpers`. Replace call sites: `_system_prompt_for_agent(...)` becomes `system_prompt_for_agent(...)`, `_agent_entry(...)` becomes `agent_entry_for_id(...)`."
    status: completed
  - id: t05-rewire-finalize-interview-session
    content: "In `orchestrator_v4/core/use_cases/finalize_interview_session.py`: delete local `_system_prompt_for_agent` and `_agent_entry`. Add same import. Replace call sites same as t04."
    status: completed
  - id: t06-add-routing-log-to-manual-turn
    content: "In `conduct_manual_interview_turn.py`, after `agent_name = roster_agent_name(ctx.agents, agent_id)` and before the first `self._turn_store.append_messages(...)`, add `self._turn_store.append_routing_log(session_id, RoutingLogAppend(input_text=text, agent_id=agent_id, agent_name=agent_name, reason='Manual override'))`. Add `RoutingLogAppend` to the import from `orchestrator_v4.core.entities.interview_turn`."
    status: completed
  - id: t07-manual-turn-stage-and-session-state
    content: "In `conduct_manual_interview_turn.py` after the second `append_messages` (assistant) and before `return ManualInterviewTurnResult`: (1) import `evaluate_stage_completion` from `orchestrator_v4.core.entities.stage_evaluator`; (2) build `messages_full` by mirroring the routed block in `conduct_interview_turn.py` (search `messages_full`, `evaluate_stage_completion`, `update_session_state`), but use `agent_id` as the active agent; (3) call `new_flags = evaluate_stage_completion(agent_id, tuple(messages_full), ctx.stage_flags())`; (4) set `next_current = agent_id`; (5) apply the same `New Session` rename rule as routed turns; (6) call `self._turn_store.update_session_state(session_id, current_agent_id=next_current, stage_flags=new_flags, name=new_name if session_renamed else None)`."
    status: completed
  - id: t08-expand-manual-interview-turn-result
    content: "In `orchestrator_v4/core/entities/interview_turn.py`, extend `ManualInterviewTurnResult` with: `routing_reason: str = 'Manual override'` and `session_renamed: str | None = None` (mirror routed `InterviewTurnResult` fields needed by the UI). In `conduct_manual_interview_turn.py`, pass `routing_reason='Manual override'` and `session_renamed=session_renamed` (variable from t07 rename block; use `None` if rename block not run) into `ManualInterviewTurnResult(...)`."
    status: completed
  - id: t09-fix-ui-routed-to-label
    content: "In `orchestrator_v4/presentation/static/modules/chat.js`, use `result.routing_reason` — if it equals `Manual override`, display prefix `Manual →` before the agent name; else `Routed to:`. Keep the existing `routeReason` text for the reason line."
    status: completed
  - id: t10-smoke-test
    content: "Run `python run_dev.py --smoke` from `orchestrator_v4/`. Manually test: (1) routed turn — routing log, stage dots, rename 'New Session' still work; (2) manual turn — routing log shows 'Manual override', card prefix 'Manual →', `current_agent_id` updated; (3) after two user chat messages to the same agent in manual mode, verify the corresponding stage dot can flip to complete (same >=2 user chat heuristic as routed); (4) toggle back to auto — router uses updated `current_agent_id` and stage flags from DB; (5) confirm the manual-turn HTTP response actually includes `routing_reason` and `session_renamed` for the UI."
    status: completed
isProject: false
---

# Manual/auto turn refactor -- granular execution plan

## Status note

The frontmatter todo statuses in this file are **historical** from the earlier coding session that carried out this refactor. They do **not** prove the current tree still matches the plan after later edits. Use the sections below as a **replay / reverification guide** when checking drift or replaying the work in a new branch.

## Context

Four use-case files duplicate roster-lookup helpers. `ConductManualInterviewTurn` does not write routing logs, does not run stage completion, does not call `update_session_state`, and returns a thinner result than routed turns. That causes routing-log gaps, stale `current_agent_id` and stage flags when switching back to auto-route, wrong stage dots after manual depth, and a misleading "Routed to:" label on manual sends.

## Files touched (complete list)

| File | What changes |
|------|-------------|
| `orchestrator_v4/core/entities/agent_roster_helpers.py` | **NEW** -- shared pure helpers |
| `orchestrator_v4/core/entities/interview_turn.py` | Extend `ManualInterviewTurnResult` with `routing_reason`, `session_renamed` |
| `orchestrator_v4/core/use_cases/conduct_interview_turn.py` | Delete 4 local helpers; import from `agent_roster_helpers` |
| `orchestrator_v4/core/use_cases/conduct_manual_interview_turn.py` | Import helpers; routing log; `messages_full` + `evaluate_stage_completion` + full `update_session_state`; expanded return |
| `orchestrator_v4/core/use_cases/initialize_interview_session.py` | Delete 2 local helpers; import from `agent_roster_helpers` |
| `orchestrator_v4/core/use_cases/finalize_interview_session.py` | Delete 2 local helpers; import from `agent_roster_helpers` |
| `orchestrator_v4/presentation/static/modules/chat.js` | Prefix "Manual →" vs "Routed to:" from `routing_reason` |

## Execution order

Execute **t01 through t10 in order**.

## Re-run / reverification guide

Use this section when the frontmatter says `completed` but you need to confirm the current code still matches the intended behavior.

1. Re-check the shared-helper extraction by symbol, not by prior todo status:
   - `agent_roster_helpers.py`
   - imports of `roster_agent_name`, `system_prompt_for_agent`, `agent_entry_for_id`, `count_user_chat`
2. Re-check manual-turn parity by symbol in `conduct_manual_interview_turn.py`:
   - `append_routing_log`
   - `messages_full`
   - `evaluate_stage_completion`
   - `update_session_state`
   - `routing_reason`
   - `session_renamed`
3. Re-check the presentation contract:
   - `chat.js` reads `result.routing_reason`
   - the manual-turn HTTP response actually includes `routing_reason` and `session_renamed`
4. Re-run the smoke/manual checks from `t10` if any of the files above changed since the original refactor.

### Phase 1: Extract shared helpers (t01-t05)

Same as before: create `agent_roster_helpers.py`, rewire all four use cases to import it.

### Phase 2: Manual turn parity (t06-t08)

**t06** -- Routing log line with reason `"Manual override"`.

**t07** -- After assistant message is persisted, build `messages_full`, run **`evaluate_stage_completion`** with the same inputs as the routed turn, then call **`update_session_state`** with `current_agent_id`, **`stage_flags=new_flags`**, and optional **`name`** for "New Session" rename. Use symbol anchors in `conduct_interview_turn.py` (`messages_full`, `evaluate_stage_completion`, `update_session_state`) rather than stale line numbers. Stage depth uses the existing heuristic in [stage_evaluator.py](orchestrator_v4/core/entities/stage_evaluator.py) (`>= 2` user `chat` lines for the active agent).

**t08** -- Add `routing_reason` and `session_renamed` to `ManualInterviewTurnResult` so `chat.js` can update title on first message in manual mode (same as routed).

### Phase 3: UI (t09)

**t09** -- Label prefix from `routing_reason`.

### Phase 4: Verify (t10)

**t10** -- Smoke + manual checks including **stage dots advancing after manual depth**.

## Design decisions (locked)

- **Two use cases stay separate.** Routed turn owns router + veto + routing log reason from LLM. Manual turn owns fixed agent + routing log reason `"Manual override"`.
- **Manual turns run the same `evaluate_stage_completion` + `update_session_state(..., stage_flags=...)` as routed turns** after building `messages_full`. Manual conversation depth counts toward stage completion; toggling auto/manual does not strand stage progress.
- **Manual turns update `current_agent_id`** to the chosen agent (via `next_current = agent_id`) so auto-route remerges with a coherent router context.
- **Manual turns apply the same "New Session" first-message rename** as routed turns (`session_renamed` + `name` in `update_session_state`).
- **Manual turns always write a routing log row** with reason `"Manual override"`.
- **`ManualInterviewTurnResult` includes `routing_reason` and `session_renamed`** for API/UI parity with routed responses where needed.
- **The `"Manual override"` value is part of the UI contract in this version.** Keep Python + API + JS in sync unless a later change replaces the string check with a dedicated boolean field.
- **The manual-turn HTTP response must actually include `routing_reason` and `session_renamed`.** Adding fields on `ManualInterviewTurnResult` alone is not enough if any route/serializer whitelists response keys.
- **Use symbol anchors, not line numbers, when replaying this plan.** Search by helper names or routed-turn symbols instead of trusting old offsets.

## Reference: routed turn pattern to mirror

Mirror the routed-turn block in `conduct_interview_turn.py` by searching for these symbols in order:

1. `messages_full = list(messages_after_user)`
2. `evaluate_stage_completion(`
3. `self._turn_store.update_session_state(`

Copy that structure into manual-turn handling, but use `agent_id` in place of routed `target_agent_id`.
