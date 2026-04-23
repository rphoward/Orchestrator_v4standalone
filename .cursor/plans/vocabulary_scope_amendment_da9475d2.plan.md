---
name: Vocabulary scope amendment
overview: Pin an explicit contract in `local/project-vocabulary.mdc` (and aligned wording in global rules) that this project’s ubiquitous language includes both product/domain terms and the Clean Architecture / ports-and-adapters vocabulary, so agents do not second-guess words like “port” or “use case.”
todos:
  - id: slice-2-vocab-scope
    content: In Slice 2, add explicit ubiquitous-language scope paragraph + architecture term list to local/project-vocabulary.mdc
    status: pending
  - id: cross-slice-wording
    content: When executing Slices 3–4 (and optional global README), replace domain-only pointers with domain+architecture vocabulary wording
    status: pending
  - id: agents-voice-line
    content: In Slice 13, add half-sentence in AGENTS.md §1 that architecture vocabulary is first-class; link project-vocabulary.mdc
    status: pending
isProject: false
---

# Ubiquitous language: domain + architecture vocabulary (plan amendment)

## Intent

When [`rules_portability_refactor_9bab7e19.plan.md`](rules_portability_refactor_9bab7e19.plan.md) lands **Slice 2** (`local/project-vocabulary.mdc`), the file must **state scope in one clear sentence** before any lists:

- **Ubiquitous language for this repo = domain/product words we use in the UI and transcripts *plus* the structural vocabulary we commit to in code and rules** (layers, ports, adapters, use cases, entities). These architecture words are **not** “optional jargon” to paraphrase away; they are part of the shared language for this project.

That single pre-answer removes the edge case where weaker models treat DDD/Clean-Architecture terms as foreign and start renaming or hedging (“the interface thing”) in places you do not want.

## Concrete edits (when the deferred refactor runs)

### 1) Expand Slice 2 — `local/project-vocabulary.mdc`

Keep existing sections (**Package**, **Presentation framework**, **Domain nouns**, **Adapter stack**). Add two short blocks:

**Ubiquitous language scope (read first)**

- One paragraph: domain + architecture vocabulary are both first-class; use them in plans, rules, commits, and layer discussions without substituting vague synonyms.
- Explicit list (canonical spellings the repo already uses in paths and docs): **`core`**, **`infrastructure`**, **`presentation`**, **`bootstrap`** (composition root), **`use case` / `use_case`**, **`entity`**, **`port`**, **`adapter`**, **`gateway`** (if you use that noun for outbound ports), **`vertical slice`**, **`horizontal layer`**, **`Protocol`** (typed port in Python). Add **`bootstrap.py`** only as “this repo’s composition root filename” under Package if you want zero ambiguity.

**Domain nouns** (unchanged idea)

- Keep: interview, session, turn, agent roster, prompt, model registry, verbs (route, finalize, export, initialize).

**Non-goal**

- Do **not** try to teach Clean Architecture inside this file; only **license** the vocabulary so global rules and agents use it confidently.

### 2) Tighten cross-slice wording so nothing contradicts Slice 2

When neutralizing globals per the parent plan, replace phrases like **“domain nouns from `local/project-vocabulary.mdc`”** with **“vocabulary from `local/project-vocabulary.mdc` (domain + architecture)”** in:

- Slice 3 (`global/architecture-layers.mdc`) example-domain wording.
- Slice 4 (`global/layer-core.mdc`) the line that currently maps interview-domain words to the vocabulary file.

Optional one-line in [`global/README.md`](../rules/global/README.md) (Slice 1): “`local/project-vocabulary.mdc` may include both product language and approved structural terms; `global/` stays noun-free for *this* project’s names, not for generic CS words.”

### 3) [`AGENTS.md`](../../AGENTS.md) section 1 (Slice 13 or a micro-follow)

Where voice says “Use words already in the codebase,” add a half-sentence pointer: **domain terms and layer/port vocabulary both count** — with a link to `local/project-vocabulary.mdc` once paths exist.

## Portability test

**No change** to the existing grep test (project-specific strings stay out of `global/`). Architecture words like `port` / `core` may appear in `global/` as generic pattern language; that is correct and unrelated to the orchestrator-specific noun ban.

## Verification

Same as parent plan: `pytest -q`, `python run_dev.py --smoke`, skim AGENTS + one global rule for the updated pointer phrasing.
