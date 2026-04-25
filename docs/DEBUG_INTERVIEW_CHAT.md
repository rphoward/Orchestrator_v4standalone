# Paste this whole file into a fresh Cursor chat

## Repo / layout

- Path: **Orchestrator v4 standalone**, package name `orchestrator_v4`; flat layout (`pyproject.toml` maps package to `.`).
- Dev: **`python run_dev.py`** → `http://127.0.0.1:5001`

## Symptoms seen

- Replies mirroring founder text (**echo**).
- **stub-route** / **`echo:`** prefix → offline LLM stub (no `GEMINI_API_KEY` at process start).
- Routing “wrong” specialist (1–4): often **resumed session** (`sessions.current_agent_id`), not bug; or router JSON fallback; or **stage veto** blocking ADVANCE.

## Fixes already in tree

| Area | Change |
|------|--------|
| Stub visibility | `bootstrap.py` warns when `FakeInterviewLlmGateway`; `presentation/app.py` prints if no key |
| Echo (live Gemini) | `gemini_interview_llm_gateway.py`: prefer stitched **non-thought `Part`** text over `response.text` when parts exist |
| Thoughts-only | Same file: raise if `include_thoughts` and only thought parts |
| Router JSON | `gemini_generate_config.py`: **`response_schema`** `{agent_id, workflow_status, reason}` + `application/json` |
| Auto-Route UI | `presentation/static/modules/interview_chat_panel.js` / `interview_sessions_panel.js`: hide manual picker when auto on; snap thread to active stage pointer when toggling auto on |

## Env (must-have for live API)

`.env` at project root (same folder as `bootstrap.py`): **`GEMINI_API_KEY=…`** → restart **`python run_dev.py`**. Startup log must show **`LLM gateway: live Gemini API`**, not **`offline stub`**.

## Where logic lives

- Turn: `core/use_cases/conduct_interview_turn.py` (router → reply → persist `current_agent_id`)
- Manual turn: `core/use_cases/conduct_manual_interview_turn.py`
- Stage veto: `core/use_cases/conduct_interview_turn.py` + `core/entities/stage_evaluator.py` (**`apply_routing_veto`**, **`evaluate_stage_completion`**)
- Gateway: `infrastructure/ai/gemini_interview_llm_gateway.py`, `gemini_generate_config.py`
- Stub: `infrastructure/stubs/fake_interview_llm_gateway.py`
- Wiring: `bootstrap.py` **`rebind_llm_gateway`**
- Send HTTP: `presentation/interview_session_routes.py`

## Verify

```powershell
cd <repo>
pytest -q
python run_dev.py --smoke
```

## If bugs remain — collect once

After **one** auto-route send (`POST …/send`), paste terminal lines for:

`orchestrator_v4.infrastructure.ai.gemini_interview_llm_gateway` (**route_intent** + **get_response**)  
and  
`orchestrator_v4.core.use_cases.conduct_interview_turn`

Say: **new vs old session**, **Auto-Route on/off**, whether reply starts with **`echo:`**.

## Longer playbook

Same folder: **`docs/NEXT_SESSION_HANDOFF.md`** (echo decision tree).
