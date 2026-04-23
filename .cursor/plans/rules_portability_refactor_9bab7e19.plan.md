---
name: rules-portability-refactor
overview: "Split `.cursor/rules/` into a domain-neutral `global/` kernel and a small `local/` companion that supplies this project's nouns (package name, framework, domain vocabulary, screaming-rename table). Goal: ~95% of the rule text travels into the next similarly shaped project without editing; only `local/` is rewritten per project. Also add three small global rules that codify conventions already in use but currently undocumented (plan/slice shape, test discipline, logging convention)."
todos:
  - id: slice-1
    content: "Slice 1: scaffold .cursor/rules/global/ and .cursor/rules/local/ with READMEs"
    status: pending
  - id: slice-2
    content: "Slice 2: write local/project-vocabulary.mdc — ubiquitous language = domain terms + architecture vocabulary (port, adapter, use case, entity, layers); see body YAML"
    status: pending
  - id: slice-3
    content: "Slice 3: move orchestrator-architecture.mdc -> global/architecture-layers.mdc and strip nouns"
    status: pending
  - id: slice-4
    content: "Slice 4: move orchestrator-layer-core.mdc -> global/layer-core.mdc and neutralize the one vocab line"
    status: pending
  - id: slice-5
    content: "Slice 5: move orchestrator-layer-infrastructure.mdc -> global/layer-infrastructure.mdc; neutralize package + example names"
    status: pending
  - id: slice-6
    content: "Slice 6: move orchestrator-layer-presentation.mdc -> global/layer-presentation.mdc; replace Flask + package name refs with vocabulary pointers"
    status: pending
  - id: slice-7
    content: "Slice 7: split orchestrator-screaming-presentation.mdc into global/screaming-architecture.mdc (principle) and local/screaming-rename-table.mdc (project table)"
    status: pending
  - id: slice-8
    content: "Slice 8: move safety/conduct/doc-style into global/ with the few remaining vocabulary leaks neutralized"
    status: pending
  - id: slice-9
    content: "Slice 9: write new global/plan-slice-shape.mdc codifying the .cursor/plans/*.plan.md convention"
    status: pending
  - id: slice-10
    content: "Slice 10: write new global/test-discipline.mdc (fake stubs per port, table tests for boundary-defense functions)"
    status: pending
  - id: slice-11
    content: "Slice 11: write new global/logging-convention.mdc (one INFO per adapter call, sentinel-on-transient)"
    status: pending
  - id: slice-12
    content: "Slice 12: delete the eight legacy .cursor/rules/orchestrator-*.mdc files"
    status: pending
  - id: slice-13
    content: "Slice 13: update AGENTS.md §2 (rule paths); §1 voice line — domain + architecture vocabulary first-class; link local/project-vocabulary.mdc"
    status: pending
  - id: slice-14
    content: "Slice 14: verify each moved file's globs frontmatter still attaches by reading the Cursor rule panel on a matching file"
    status: pending
  - id: portability-test
    content: "Run the portability test: grep for orchestrator/interview/session/gemini/sqlite/flask under global/ and expect zero hits"
    status: pending
  - id: verify-app
    content: Run pytest -q and python run_dev.py --smoke to confirm application code is untouched
    status: pending
isProject: false
---


# Rules portability refactor (deferred — for a later session)

## Why

Current `.cursor/rules/*.mdc` are ~70% portable. Principles are sound but names leak: `orchestrator_v4` package name, `Flask`, `SQLite`, `Gemini`, domain nouns (`interview, session, turn, agent roster`), and a full rename table inside `orchestrator-screaming-presentation.mdc`. Copying the set into the next similarly shaped project forces edits across almost every file.

Fix: physical split into `global/` (no project nouns) and `local/` (this project's answers). All project-specific vocabulary lives in one file that global rules reference in the abstract.

Non-goal: changing application code. Codebase keeps its screaming names. Only the **rule text** travels.

## Proposed layout

```
.cursor/rules/
  global/
    architecture-layers.mdc          # from orchestrator-architecture.mdc, nouns stripped
    layer-core.mdc                   # from orchestrator-layer-core.mdc, nouns stripped
    layer-infrastructure.mdc         # from orchestrator-layer-infrastructure.mdc, nouns stripped
    layer-presentation.mdc           # from orchestrator-layer-presentation.mdc, nouns stripped
    screaming-architecture.mdc       # principle only, no rename table
    safety.mdc                       # from orchestrator-safety.mdc, unchanged
    conduct.mdc                      # from orchestrator-conduct.mdc, vocab line removed
    doc-style.mdc                    # from orchestrator-doc-style.mdc, examples neutralized
    plan-slice-shape.mdc             # NEW — codifies .cursor/plans/*.plan.md shape
    test-discipline.mdc              # NEW — fake stubs for ports, table-tests at boundaries
    logging-convention.mdc           # NEW — one INFO per adapter call, identity + outcome
    README.md                        # how the global/local split works; portability notes
  local/
    project-vocabulary.mdc           # THIS project: package, framework, ubiquitous language (domain + architecture), adapter stack
    screaming-rename-table.mdc       # THIS project: sessions.js -> interview_sessions_panel.js table
    README.md                        # points at global/ and names this project
```

All old `orchestrator-*.mdc` files go away after their content has moved.

## The one swap-out file (vocabulary)

```yaml
---
description: Project vocabulary — edited per project; referenced by all global rules.
alwaysApply: true
---

## Ubiquitous language scope (read first)
- One sentence: ubiquitous language for this repo includes both (a) product/domain words used in UI and transcripts and (b) the structural vocabulary we commit to in code and rules (Clean Architecture / ports-and-adapters). Words like port, adapter, use case, and layer folder names are first-class — do not paraphrase them into vague synonyms ("the interface thing") in plans or rules.
- Non-goal: this file does not teach Clean Architecture; it only licenses the vocabulary so agents use it confidently.

## Architecture vocabulary (first-class; not "meta-jargon")
- Layers and composition: core, infrastructure, presentation, bootstrap (composition root; this repo uses bootstrap.py).
- Roles: port, adapter, gateway (if used for outbound ports), use case / use_case, entity, value object (only if the codebase uses it).
- Shapes: vertical slice, horizontal layer, Protocol (typed port in Python).

## Package
- Python package: `orchestrator_v4`

## Presentation framework
- Flask + static JS modules

## Domain / product nouns (screaming UI + transcripts)
- primary: interview, session, turn, agent roster, prompt, model registry
- verbs: route, finalize, export, initialize

## Adapter stack
- SQLite for persistence
- Google Gemini for LLM
- local filesystem for prompt bodies
```

Every global rule that needs a project-specific noun says "the project package" / "the project vocabulary" / "the project adapter stack" and points at this file. When a global rule points at vocabulary for wording, say **vocabulary from `local/project-vocabulary.mdc` (domain + architecture)** — not "domain nouns only," which would contradict the scope block above.

## Data-flow sketch (how rules reference each other)

```mermaid
flowchart LR
    vocab["local/project-vocabulary.mdc"]
    rename["local/screaming-rename-table.mdc"]

    arch["global/architecture-layers.mdc"]
    core["global/layer-core.mdc"]
    infra["global/layer-infrastructure.mdc"]
    pres["global/layer-presentation.mdc"]
    scream["global/screaming-architecture.mdc"]

    safety["global/safety.mdc"]
    conduct["global/conduct.mdc"]
    doc["global/doc-style.mdc"]
    plans["global/plan-slice-shape.mdc"]
    tests["global/test-discipline.mdc"]
    logs["global/logging-convention.mdc"]

    arch --> vocab
    core --> vocab
    infra --> vocab
    pres --> vocab
    scream --> vocab
    scream --> rename
    doc --> vocab
```

## Atomic slices

### Slice 1 — scaffold folders + READMEs
New files:
- `.cursor/rules/global/README.md` — "portable rule kernel; do not put project-specific nouns here. Companion per-project specifics live under `../local/`. To port: copy this whole folder into a new project of similar shape and write a new `local/` set there." Optional closing line: "`local/project-vocabulary.mdc` may list both product language and approved structural terms; `global/` stays free of *this project's* names — not free of generic pattern words like port or core."
- `.cursor/rules/local/README.md` — "this project's answers to the questions global rules assume. Edit these first in a new project."

### Slice 2 — extract the vocabulary file
New: `.cursor/rules/local/project-vocabulary.mdc` with `alwaysApply: true` frontmatter and the content shown in "The one swap-out file" above (scope block + architecture vocabulary list must ship in this slice, not later).

### Slice 3 — move + neutralize architecture-layers
- Move `.cursor/rules/orchestrator-architecture.mdc` -> `.cursor/rules/global/architecture-layers.mdc`.
- Title "Orchestrator v4 — architecture (standalone repo)" -> "Clean architecture — layer map".
- Line 20 `orchestrator_v4` reference -> "the project package (see `local/project-vocabulary.mdc`)".
- Line 32 "(SQLite, Gemini, files)" -> "(the project adapter stack)".
- Example product words -> "vocabulary from `local/project-vocabulary.mdc` (domain + architecture)".

### Slice 4 — move + neutralize layer-core
- Move -> `.cursor/rules/global/layer-core.mdc`.
- "interview-domain words (session, turn, roster)" -> "vocabulary from `local/project-vocabulary.mdc` (domain + architecture)".
- Keep the typed-ports + junk-defense additions verbatim.

### Slice 5 — move + neutralize layer-infrastructure
- Move -> `.cursor/rules/global/layer-infrastructure.mdc`.
- Package-name occurrences -> "the project core package".
- `SqliteInterviewSessionTurnStore` example -> "`<Tech><Role>` naming (e.g. `SqlOrderRepository`, `HttpPaymentGateway`) — domain-free illustration".
- Keep the error-model subsection verbatim.

### Slice 6 — move + neutralize layer-presentation
- Move -> `.cursor/rules/global/layer-presentation.mdc`.
- "Flask" -> "the presentation framework (see `local/project-vocabulary.mdc`)".
- `from orchestrator_v4 import bootstrap` -> "`from <project_package> import bootstrap`".
- "SQLite stores or LLM clients" -> "infrastructure adapters".
- "`interview_session_routes`" -> "`<domain>_routes.py`".

### Slice 7 — split screaming-presentation
- Move the principle ("file names shout the product, not the framework") + the shell-file policy into `.cursor/rules/global/screaming-architecture.mdc`. No rename table. Text is framework-agnostic.
- Move the rename table (`sessions.js -> interview_sessions_panel.js`, etc.) verbatim into `.cursor/rules/local/screaming-rename-table.mdc`.

### Slice 8 — safety / conduct / doc-style
- `safety.mdc`: move unchanged -> `.cursor/rules/global/safety.mdc`.
- `conduct.mdc`: move, strip the `(session, turn, agent roster, interview)` line in "Words" to "Use vocabulary from `local/project-vocabulary.mdc` (domain + architecture)" -> `.cursor/rules/global/conduct.mdc`.
- `doc-style.mdc`: move, replace specific examples (`#welcomeSection`, "welcome screen", `Acme Corp`, temperature-clamp) with two domain-free placeholders like `#primaryActionButton` / "main screen" -> `.cursor/rules/global/doc-style.mdc`.

### Slice 9 — new global rule: plan-slice-shape
New: `.cursor/rules/global/plan-slice-shape.mdc`. Codify what `.cursor/plans/*.plan.md` already does:
- Header with `name`, `overview`, and `todos[]` frontmatter.
- Body sections: architecture commitments, data-flow diagram (mermaid), atomic slices naming exact file paths + exact edits, non-goals, verification.
- Slices are atomic and mechanical; a coder model should not need to re-derive intent.
- "Cross-slice awareness": later slices read what earlier slices actually landed and match that reality, not plan text.

### Slice 10 — new global rule: test-discipline
New: `.cursor/rules/global/test-discipline.mdc`:
- Every port has a Fake stub in `infrastructure/stubs/` for offline dev and tests.
- Pure boundary-defense functions (in `core/entities/`) have table tests covering: threshold boundaries, False-never-flips-to-True, out-of-range ids returning inputs unchanged, synthesizer / junk-ids ignored.
- Tests live at repo root `tests/` and run via `pytest -q`.

### Slice 11 — new global rule: logging-convention
New: `.cursor/rules/global/logging-convention.mdc`:
- Adapters log one `INFO` line per call with: method identity, model or store id, short outcome summary (counts + head of response).
- Transient failures use `WARNING` with `exc_info=True`, and the call returns a sentinel value the use case can route on. See `layer-infrastructure.mdc` error-model section.
- Pure core code does not log (no I/O in core).

### Slice 12 — delete old prefixed files
After the new set is in place and the two verification steps below pass, delete:
- `.cursor/rules/orchestrator-architecture.mdc`
- `.cursor/rules/orchestrator-layer-core.mdc`
- `.cursor/rules/orchestrator-layer-infrastructure.mdc`
- `.cursor/rules/orchestrator-layer-presentation.mdc`
- `.cursor/rules/orchestrator-screaming-presentation.mdc`
- `.cursor/rules/orchestrator-safety.mdc`
- `.cursor/rules/orchestrator-conduct.mdc`
- `.cursor/rules/orchestrator-doc-style.mdc`

### Slice 13 — update external references to renamed rule files
Files known to reference the old names:
- [AGENTS.md](AGENTS.md) section 2 (the "Where instructions live" table).
- [AGENTS.md](AGENTS.md) section 1 (voice): extend "Use words already in the codebase" with a half-sentence that **domain terms and layer/port vocabulary both count**, with a link to `.cursor/rules/local/project-vocabulary.mdc` once that path exists.
- [DEV-STANDALONE.md](DEV-STANDALONE.md) — none found today, but grep before finalizing.
- Any `.cursor/plans/*.plan.md` that named a rule file by path.

Update paths to `global/<new-name>.mdc` / `local/<new-name>.mdc`.

### Slice 14 — verify glob frontmatter still applies
Each moved rule keeps its existing frontmatter `globs:` (`core/**`, `infrastructure/**`, `presentation/**`). Those globs are project-agnostic so no edits needed — but confirm each moved file still attaches to the same folder by reading the frontmatter after move.

## Portability test (definition of done)

1. Copy `.cursor/rules/global/` into a scratch folder.
2. Run: `grep -ri -E "orchestrator|interview|session|gemini|sqlite|flask" .cursor/rules/global/` — expect zero hits.
3. Any hit is a failure; add one more neutralization pass on that file.

**Note:** Hits for generic pattern words (`port`, `core`, `adapter`, `use case`) under `global/` are not failures — the ban is on *this project's* names and product stack, not on structural vocabulary. `local/project-vocabulary.mdc` explicitly lists architecture terms so agents do not treat them as out-of-bounds.

## Optional follow-ups (out of scope here)

- Expand `logging-convention.mdc` with a sample `_LOG.info("route_intent call model=%s ...", ...)` snippet pattern — only if useful for the next project's onboarding.
- Add a `global/import-direction.mdc` if the architecture-layers file gets crowded; for now keep the one-rule-per-topic balance.

## Verification checklist for the session that executes this plan

1. Slices land in order; after each slice, confirm the moved file is readable and the frontmatter attaches (open a file matching the glob, check Cursor rule panel).
2. Run the portability test above after slice 12.
3. Run `pytest -q` and `python run_dev.py --smoke` — no application code changed, both should still pass.
4. Skim [AGENTS.md](AGENTS.md) to confirm rule references resolve.
