# Stage-completion judge — executed

## What landed

1. **New core concepts.**
   - [`core/entities/stage_completion_verdict.py`](../../core/entities/stage_completion_verdict.py): `StageCompletionVerdict` value type + `STAGE_COMPLETION_CONFIDENCE_THRESHOLD = 0.75`.
   - [`core/ports/interview_stage_completion_judge.py`](../../core/ports/interview_stage_completion_judge.py): `InterviewStageCompletionJudge` Protocol; `judge_stage_completion(stage_id, messages, stage_flags_before) -> StageCompletionVerdict`.
   - [`core/entities/stage_evaluator.py`](../../core/entities/stage_evaluator.py): new pure `merge_stage_completion_verdict_into_flags` function with an explicit junk-defense rule list (`stage_id` in 1..4 only, never True -> False, confidence gate, synthesizer ignored). Old `evaluate_stage_completion` is kept as the fallback decision.
2. **Infrastructure.**
   - [`infrastructure/ai/gemini_stage_completion_judge.py`](../../infrastructure/ai/gemini_stage_completion_judge.py): Gemini adapter that loads the per-stage completion prompt via `CachedPromptFileReader`, calls the model with a structured-JSON schema, and parses with the same robust regex+`json.loads` pattern as the router. All model-side failures surface as `judge_error:` verdicts; the adapter does not raise for transient errors.
   - [`infrastructure/ai/gemini_generate_config.py`](../../infrastructure/ai/gemini_generate_config.py): new `build_stage_completion_judge_generate_config(system_instruction)` + response-schema constant.
   - [`infrastructure/stubs/fake_stage_completion_judge.py`](../../infrastructure/stubs/fake_stage_completion_judge.py): deterministic stub for offline dev and tests.
3. **Wiring.** [`bootstrap.py`](../../bootstrap.py) `rebind_llm_gateway()` now also rebuilds the stage-completion judge (live Gemini when keyed, offline stub with `default_reason="judge_error: offline stub"` otherwise) and threads it into both `ConductInterviewTurn` and `ConductManualInterviewTurn` constructors.
4. **Use cases.** Both turn use cases now call the judge after the assistant reply is persisted. If the verdict's reason starts with `judge_error:` or the call raises, they fall back to `evaluate_stage_completion` so offline and degraded-network behavior matches today. Agent 5 manual turns skip the judge entirely and never flip a stage flag.
5. **Runtime prompts.** New folder [`runtime/prompts/stage_completion/`](../../runtime/prompts/stage_completion/) with four per-stage placeholder bodies matching the stage filenames, plus the meta-prompt [`runtime/prompts/Domain Library/stage_completion_prompt_author.md`](../../runtime/prompts/Domain Library/stage_completion_prompt_author.md) for authoring the real per-stage bodies from each interview prompt.
6. **Tests.** 8 new pure-core tests in [`tests/test_core_entities.py`](../../tests/test_core_entities.py) cover the merge rule and the stub contract (including the offline `judge_error:` reason). `pytest -q` is 20/20. `python run_dev.py --smoke` exits 0.

## Architecture commitments honored

- `core/` imports nothing from `infrastructure` or `presentation`.
- New port is a `Protocol`; the adapter lives under `infrastructure/ai/`.
- Composition happens only in `bootstrap.py`; the Flask routes are untouched.
- No UI / presentation changes.
- Naming follows the domain-first rule in `.cursor/rules/orchestrator-*`: `InterviewStageCompletionJudge`, `StageCompletionVerdict`, `merge_stage_completion_verdict_into_flags`, `GeminiStageCompletionJudge`, `FakeStageCompletionJudge`.

## Non-goals kept out of scope

- No DB schema change. Verdicts are not persisted.
- No UI changes. Badge and dots continue to use `active_stage_pointer` from the turn result.
- No caching of verdicts. One judge call per turn for agents 1..4.
- No expansion of the turn result dataclasses on the wire.

## Manual verification checklist

1. `pytest -q` from repo root: **20/20 passing**.
2. `python run_dev.py --smoke`: **exit 0**.
3. Browser, `GEMINI_API_KEY` unset: start a fresh session, send two brand replies. The stage badge flips to 2 through the heuristic fallback (the stub's `judge_error: offline stub` reason triggers it).
4. Browser, `GEMINI_API_KEY` set: stage advancement now depends on the judge's verdict against [`runtime/prompts/stage_completion/1_brand_spine_completion.md`](../../runtime/prompts/stage_completion/1_brand_spine_completion.md) etc. The per-stage bodies are placeholders until they are authored from the meta-prompt.

## Next step (post-landing)

Run the meta-prompt in [`runtime/prompts/Domain Library/stage_completion_prompt_author.md`](../../runtime/prompts/Domain Library/stage_completion_prompt_author.md) against each of the four stage prompts (`runtime/prompts/1_brand_spine.md` etc.) and write the output into the matching `runtime/prompts/stage_completion/N_*.md` file. No code change required for that step — the adapter re-reads the file on every call (the shared `CachedPromptFileReader` supports explicit invalidation).
