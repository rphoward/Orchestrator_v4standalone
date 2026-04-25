---
name: parchment followup logs + handoff
overview: >-
  Fix the daily-driver font chain so IBM Plex Sans actually paints body copy, audit
  the sidebar bottom buttons and Settings labels, add targeted Gemini diagnostic
  logs so a fresh session can identify the chat "echo" cause in one turn, and write
  a short next-session handoff that points directly at those logs.
todos:
  - id: font-tailwind-extend
    content: Extend tailwind.config.theme.extend.fontFamily in index.html so font-sans = IBM Plex Sans first, plus a display family.
    status: completed
  - id: font-audit-sidebar-settings
    content: Audit sidebar bottom buttons and Settings modal labels; only trim weight/size if anything still reads off after the font-sans fix.
    status: completed
  - id: font-cache-bust
    content: Bump style.css?v=22 to ?v=23 on the stylesheet link in index.html.
    status: completed
  - id: logs-gateway-router
    content: "Add INFO logs in route_intent: router model, raw text head, parsed RoutingDecision."
    status: completed
  - id: logs-gateway-response
    content: "Add INFO logs in get_response: effective model, thinking args, candidates count, parts breakdown (thought vs text), final text head."
    status: completed
  - id: logs-turn-agent-entry
    content: Add one INFO log in conduct_interview_turn.py showing agent_entry.model / thinking_level / temperature / include_thoughts.
    status: completed
  - id: logging-dev-level
    content: Confirm (or set) orchestrator logger INFO in dev via presentation/app.py basicConfig; do not change prod behavior.
    status: completed
  - id: handoff-next-session
    content: Create docs/NEXT_SESSION_HANDOFF.md with repro steps, log interpretation, decision tree, files to open.
    status: completed
  - id: handoff-link-from-main
    content: Add a one-line link to NEXT_SESSION_HANDOFF.md from docs/HANDOFF.md under Recent landings.
    status: completed
  - id: verify-smoke-pytest
    content: Run python run_dev.py --smoke and pytest; both must pass.
    status: completed
---

# Parchment followup — logs + handoff

## Why

The daily-driver parchment work landed, but two follow-ups surfaced:

- `<body>` carries Tailwind's `font-sans` utility. Class specificity beats our element-level `body { font-family: var(--font-body) }` in [presentation/static/style.css](../../presentation/static/style.css). Result: only `.t-display*` elements render in Fraunces; everything else (sidebar buttons, `.section-label`, threads, Settings modal) renders in Tailwind's default `ui-sans-serif, system-ui, sans-serif` — not IBM Plex Sans. That is the weight/shape mismatch the user reported at the sidebar bottom.
- A chat turn "echoes" the user text. Model IDs in [infrastructure/ai/gemini_policy_constants.py](../../infrastructure/ai/gemini_policy_constants.py) match current Google naming (`gemini-3.1-flash-lite-preview`, `gemini-3.1-pro-preview`), so a static read cannot prove the cause. Plausible suspects, ranked: agent 4's `include_thoughts=True` returning only thought parts with an empty final, a legacy per-agent `model` string in SQLite, or a silent router parse failure falling to STAY.

## What shipped

### Font chain
- `tailwind.config.theme.extend.fontFamily.sans = ['"IBM Plex Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif']` and `fontFamily.display = ['Fraunces', 'serif']` added in [presentation/static/index.html](../../presentation/static/index.html).
- `.section-label` dropped `font-weight: 800` → `700` in [presentation/static/style.css](../../presentation/static/style.css) to avoid fake-bold on IBM Plex Sans (we only load weights 400;500;600;700).
- `style.css?v=22` → `?v=23`.
- Bottom sidebar buttons and Settings modal labels left as-is — they now render in IBM Plex Sans at their Tailwind-assigned weights and read consistently.

### Gemini diagnostic logs
- [infrastructure/ai/gemini_interview_llm_gateway.py](../../infrastructure/ai/gemini_interview_llm_gateway.py)
  - `route_intent`: logs router model, hint keys, raw `response.text[:200]`, parsed `RoutingDecision` (`target_agent_id`, `workflow_status`, `reason`).
  - `get_response`: logs effective model, `thinking_level`, `include_thoughts`, `temperature`, history length. After the call: candidate count, thought-part count, text-part count, `response.text` length, `len(non_thought_final)`, first 200 chars of non-thought final text. Empty response still raises but logs a warning first.
- [core/use_cases/conduct_interview_turn.py](../../core/use_cases/conduct_interview_turn.py) — one INFO line after agent resolution showing `agent_entry.model`, `thinking_level`, `temperature`, `include_thoughts`, and `system_prompt_len` so we see what the gateway was handed.
- [presentation/app.py](../../presentation/app.py) — `logging.basicConfig(level=logging.INFO, format=...)` and `getLogger('orchestrator_v4').setLevel(INFO)` so our lines surface in the dev console. `basicConfig` is a no-op if handlers exist, so it does not fight Flask.

### Handoff
- [docs/NEXT_SESSION_HANDOFF.md](../../docs/NEXT_SESSION_HANDOFF.md) — one-page brief for a fresh session: repro, how to read the logs, decision tree, files to open.
- [docs/HANDOFF.md](../../docs/HANDOFF.md) — one-line link to the next-session handoff under **Recent landings**.

## Out of scope (intentionally deferred)

- Do NOT change Gemini model IDs, `include_thoughts` defaults, or routing logic in this pass. Logs first; the targeted fix is the next session's job.
- Do NOT touch [proposedgemini_interview_llm_gateway.py](../../docs/proposedgemini_interview_llm_gateway.py); unused sketch.
- No JS behavior changes; no Flask route changes; no Tailwind build migration.

## Verify (done in this pass)

- `python run_dev.py --smoke` — exit 0 (orchestrator smoke prints plus new INFO logs did not break it).
- `pytest -q` — 2 tests pass.
- Browser visual pass: next session should send one turn and grab the log output.

## Completion rule

When every YAML `status` above is `completed` (they are) and the three files under **Gemini diagnostic logs** carry the new `_LOG.info` calls, this plan is done. Hand the next chat the link at the top of [docs/HANDOFF.md](../../docs/HANDOFF.md).
