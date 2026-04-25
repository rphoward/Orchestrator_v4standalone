# Next-session handoff — diagnose chat "echo"

One-page brief for a fresh Cursor chat. Read [docs/HANDOFF.md](HANDOFF.md) for the project map; read this file for the immediate task.

---

## What just shipped

- Daily-driver parchment (Fraunces + IBM Plex Sans, warm parchment palette, grain) — see [.cursor/plans/DAILY_DRIVER_PARCHMENT_JOURNAL_PLAN.md](../.cursor/plans/DAILY_DRIVER_PARCHMENT_JOURNAL_PLAN.md).
- Font-chain fix — Tailwind config extended so `font-sans` maps to `"IBM Plex Sans"` first; `.section-label` weight 800 → 700 to avoid fake-bold. Stylesheet bumped to `?v=23`. See [.cursor/plans/PARCHMENT_FOLLOWUP_LOGS_AND_HANDOFF_PLAN.md](../.cursor/plans/PARCHMENT_FOLLOWUP_LOGS_AND_HANDOFF_PLAN.md).
- Targeted Gemini diagnostic logs at `INFO` — no behavior change, just visibility.

## Open bug — one sentence

A consultant sends a message in the main chat; the agent reply appears to "echo" the user's input instead of routing to a prompt. No repro was captured before these logs landed.

## Repro (fastest path)

1. From repo root: `python run_dev.py`. App at `http://127.0.0.1:5001` (or your `ORCHESTRATOR_PORT`). You need `.env` with `GEMINI_API_KEY`.
2. Open or start a session.
3. Send one short message like `"hello, the founder wants to talk about brand identity"`.
4. Watch the terminal running `run_dev.py`. Copy the full block of lines matching these logger names:
   - `orchestrator_v4.core.use_cases.conduct_interview_turn`
   - `orchestrator_v4.infrastructure.ai.gemini_interview_llm_gateway`

Paste that block into the new chat as evidence.

## What the logs say

For a healthy turn you will see, in order:

```
INFO ...conduct_interview_turn: ... target_agent_id=<n> agent_entry.model=<str> thinking_level=<str> include_thoughts=<bool> system_prompt_len=<n>
INFO ...gemini_interview_llm_gateway: route_intent call model=gemini-3.1-flash-lite-preview current_agent_id=<n> agent_hint_ids=[1,2,3,4]
INFO ...gemini_interview_llm_gateway: route_intent raw response.text[:200]='{"agent_id": 1, "workflow_status": "STAY", "reason": "..."}' (total_len=...)
INFO ...gemini_interview_llm_gateway: route_intent parsed target_agent_id=<n> status=STAY reason='Routed by AI'
INFO ...gemini_interview_llm_gateway: get_response call agent_id=<n> model='gemini-3.1-flash-lite-preview' thinking_level='LOW' include_thoughts=False ...
INFO ...gemini_interview_llm_gateway: get_response response candidates=1 thought_parts=0 text_parts=1 response.text_len=<big> non_thought_final_len=<big> non_thought_head='<the reply>...'
```

## Decision tree (pick exactly one fix, then keep it small)

1. **`thought_parts > 0` and `text_parts == 0` (or `response.text_len == 0`)** — The model returned only thinking, no final text. Fix in [infrastructure/ai/gemini_interview_llm_gateway.py](../infrastructure/ai/gemini_interview_llm_gateway.py) `get_response`: when `include_thoughts=True`, return `non_thought_final` instead of `response.text` (or raise if both are empty). Consider lowering agent 4 `include_thoughts` default until the Gemini 3.1 Flash-Lite preview stabilizes.
2. **`route_intent raw response.text[:200]` is not JSON** — Flash-Lite is returning prose despite `response_mime_type="application/json"`. Fix in [infrastructure/ai/gemini_generate_config.py](../infrastructure/ai/gemini_generate_config.py) `build_router_generate_config`: add a `response_schema` constraining `{agent_id, workflow_status, reason}`, or tighten the prompt directive. Keep router model as `gemini-3.1-flash-lite-preview`.
3. **`agent_entry.model` is something like `gemini-3.0-flash` or an empty-but-stale string** — Legacy per-agent override from an old DB. Two options: (a) open Settings → Agent Config and reset the agent model to the active registry default; (b) for a full clean, delete `orchestrator.db` (you will lose sessions — confirm first). Code path is fine because `get_response` already falls back to `self._agent_model` on an empty override.
4. **Router `STAY` with reason `"Routing failed (API error); ..."`** — Gemini router call blew up. Look one line above for the `WARNING route_intent Gemini call failed` traceback; that names the real cause (model 404, auth, quota).
5. **Router returns a normal JSON and the agent response `non_thought_head` is genuinely the user's text** — Prompt regression. Check that the agent's prompt body loaded (the smoke also prints `LoadInterviewPromptBody (agent N, first 120 chars)`). If `system_prompt_len=0`, walk `core.use_cases.initialize_interview_session` and the prompt file path resolver.

If none of the above matches, copy the log block into the chat and ask for a targeted fix rather than guessing.

## Files to open first

- [docs/HANDOFF.md](HANDOFF.md) — project map.
- [infrastructure/ai/gemini_interview_llm_gateway.py](../infrastructure/ai/gemini_interview_llm_gateway.py) — where both fixes for cases 1 and 2 live.
- [core/use_cases/conduct_interview_turn.py](../core/use_cases/conduct_interview_turn.py) — the pre-gateway log line (case 3).
- [infrastructure/ai/gemini_policy_constants.py](../infrastructure/ai/gemini_policy_constants.py) — model IDs; verified current as of April 2026.
- [infrastructure/persistence/sqlite_model_registry_store.py](../infrastructure/persistence/sqlite_model_registry_store.py) — registry seed + router model plumbing.
- [presentation/app.py](../presentation/app.py) — `basicConfig` block that makes these logs visible.

## Guardrails

- Do not change model IDs or routing control flow without evidence. The purpose of this pass was to install evidence, not to fix blind.
- Do not touch [proposedgemini_interview_llm_gateway.py](proposedgemini_interview_llm_gateway.py) in this folder; it is an unused sketch.
- After the real fix: bump `presentation/static/index.html` `style.css?v=` if you edit CSS (you likely won't), run `python run_dev.py --smoke` and `pytest -q`, and append a bullet to **Recent landings** in [docs/HANDOFF.md](HANDOFF.md).

## One more thing

The font-chain fix changed how `font-sans` resolves. If the user reports *any* new visual regression outside the daily driver, open [presentation/static/index.html](../presentation/static/index.html) first and check whether a specific area wants to opt out of `"IBM Plex Sans"` (e.g. the code blocks inside `.md-fence` already set a monospace stack and are unaffected).
