# Active stage pointer + routing cleanup — executed

## What landed

1. **Active stage pointer** is now a single, explicit concept. `sessions.current_agent_id` means "earliest unfinished stage 1..4", recomputed from the four `stageN_complete` flags after every turn (auto or manual). When all four are true, the pointer stays at 4. Agent 5 (Grand Synthesis) is manual-only and never becomes the pointer.
2. **Auto-routing veto.** [`core/entities/stage_evaluator.py`](../../core/entities/stage_evaluator.py) replaced `apply_routing_veto` + `can_advance` with `apply_sequential_stage_veto(decision, stage_flags)`. Allowed targets: `1..pointer`. Forbidden: anything past the pointer. When vetoed, the decision is rewritten to `STAY` on the pointer and the router's original intent is kept in the `routing_logs.reason` string.
3. **Both turn use cases use the pointer as the source of `current_agent_id`.** [`core/use_cases/conduct_interview_turn.py`](../../core/use_cases/conduct_interview_turn.py) and [`core/use_cases/conduct_manual_interview_turn.py`](../../core/use_cases/conduct_manual_interview_turn.py) call `earliest_unfinished_stage(new_flags)` after stage completion is recomputed.
4. **Turn results ship the pointer to the UI.** `InterviewTurnResult` and `ManualInterviewTurnResult` in [`core/entities/interview_turn.py`](../../core/entities/interview_turn.py) gained `active_stage_pointer: int = 0`. No route edit needed — existing `jsonify(dataclasses.asdict(result))` ships it automatically.
5. **Auto-router hints exclude the synthesizer.** `conduct_interview_turn` now builds `agent_hints` only from non-synthesizer agents, so the router stops silently picking 5 and getting clamped.
6. **Presentation rename + screaming names.**
   - `sessions.js` -> `interview_sessions_panel.js`
   - `chat.js` -> `interview_chat_panel.js`
   - `autoRoute` -> `autoRoutingOn`; `selectedAgentId` -> `manualRoutingTargetAgentId`; `activeThreadId` -> `openChatThreadAgentId`; new `lastActiveStagePointer` mirror in [`presentation/static/modules/state.js`](../../presentation/static/modules/state.js).
   - Functions: `toggleAutoRoute` -> `toggleAutoRouting`; `selectAgent` -> `chooseManualRoutingAgent`; `updateStageBadge` -> `updateActiveStagePointerBadge`; `updateHeaderStageDots` -> `updateStageStatusTracker`; `syncActiveThreadToSessionCurrentAgent` -> `snapChatToActiveStagePointer`.
   - HTML ids: `currentStageBadge` -> `activeStagePointerBadge`; `headerStageDots` -> `stageStatusTrackerDots`; `autoRouteToggle` -> `autoRoutingToggle`; `manualSelector` -> `manualRoutingAgentPicker`. Cache-bust bumped to `?v=24`.
7. **Forward-motion lever.** Toggling the auto-routing checkbox either direction snaps the manual picker and open chat thread to the pointer, so turning auto on **or** off is always an explicit "come back to next unfinished" move.
8. **Tests.** 10 new pure core tests in [`tests/test_core_entities.py`](../../tests/test_core_entities.py) cover `earliest_unfinished_stage` and `apply_sequential_stage_veto`. `pytest -q` reports 12/12.

## Non-goals (still out of scope)

- No schema change. Column name `current_agent_id` kept; only its meaning is tightened.
- No `localStorage` for the auto-routing toggle or open thread.
- No rename of shell files `api.js`, `ui.js`, `state.js`, `utils.js` (cross-cutting policy).
- No prompt or model-id changes.

## Manual verification checklist

1. `python run_dev.py`, open the UI, hard-refresh.
2. Start "Acme Corp": **Stage: 1** badge; four pending dots.
3. Send two brand replies: first dot lights up, badge flips to **Stage: 2**.
4. While auto is on, drop a brand-flavored comment: reply should still come from agent 2 (the pointer). Routing log reason shows the veto text if the router disagreed.
5. Toggle **auto-routing** off: manual picker row appears with **Founder (2)** preselected, open thread is **Founder**.
6. Click **Customer (3)**, send a message. Agent 3 answers; badge still **Stage: 2**.
7. Toggle auto-routing back on: selection and open thread snap to agent 2.
8. `python run_dev.py --smoke` exits 0; `pytest -q` is 12/12.
