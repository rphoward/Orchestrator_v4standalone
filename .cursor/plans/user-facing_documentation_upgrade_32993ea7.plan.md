---
name: User-facing documentation upgrade
overview: Add operator-oriented docs and README links, written to match orchestrator-doc-style.mdc and an atomic tutorial shape (README + USER-GUIDE). Optional small rule tweak so docs/*.md and tutorial style are explicit.
todos:
  - id: add-user-guide
    content: Create docs/USER-GUIDE.md — atomic sections (one idea each), UI words first, What to do / What you see; DEV-STANDALONE links for depth; For developers appendix for ids/paths only
    status: pending
  - id: readme-section
    content: README — short atomic tutorial strip (numbered try-this steps) + doc table row; body uses screen names not #ids; link USER-GUIDE
    status: pending
  - id: cross-links
    content: HANDOFF map; DEV-STANDALONE one operator pointer paragraph; optional AGENTS.md table row
    status: pending
  - id: doc-style-globs
    content: "Optional: extend orchestrator-doc-style.mdc globs to docs/**/*.md (and USER-GUIDE) so Cursor loads the same human-doc rules when editing operator docs"
    status: pending
  - id: stale-debug-doc
    content: "Optional: fix docs/DEBUG_INTERVIEW_CHAT.md module paths to match presentation/static/modules/"
    status: pending
---

# User-facing documentation upgrade (revised)

## Alignment with `.cursor/rules`

### [orchestrator-doc-style.mdc](.cursor/rules/orchestrator-doc-style.mdc)

| Rule | Plan compliance |
|------|-------------------|
| Actions as steps (“what to do” / “what you should see”) | **Met** if USER-GUIDE and README “Using the application” are written as **numbered try-this steps** with an expected visible outcome each time—not only feature lists. |
| UI words over code words in human-facing body | **Partial risk** in the earlier outline (it named `#autoRoutingToggle`, etc.). **Requirement:** main text uses **labels users see** (e.g. “Auto-routing” checkbox, “Routing Intelligence Log”, “Stage tracking (debug)” nested row). Reserve **HTML ids / file paths** for a final **“For developers”** subsection or table column only. |
| Concrete examples | **Met** with short scenarios (e.g. “type a short reply like `ok`” → gate `short_or_test_like` in debug copy is optional; at minimum “open a session named …”). |
| Checklists | **Met** if DEV checklist additions use **do / see** columns or bullet pairs per doc-style. |

**Glob gap:** `orchestrator-doc-style.mdc` currently applies to `README.md`, `DEV-STANDALONE.md`, `.cursor/plans/**` only. New **`docs/USER-GUIDE.md`** would not auto-match unless globs are extended—add optional todo **doc-style-globs** so operator docs get the same guardrails in Cursor.

### [orchestrator-conduct.mdc](.cursor/rules/orchestrator-conduct.mdc)

- **Informal American English, short bullets:** README strip and USER-GUIDE should match.
- **Repo vocabulary** (session, turn, agent roster, interview): use those words; introduce “stage pointer” once in plain English then reuse consistently.
- **Docs / behavior:** This work documents existing behavior only—no requirement to change DEV behavior sections beyond a short cross-link unless facts drift.

## Tutorial shape (Jim Butterworth / No Starch–style, without naming authors in the repo)

Your preference—**atomic**, **hands-on**, **one new idea per short section**, reader builds understanding by doing—fits the existing **doc-style** rule (“describe actions as steps”, concrete examples) but is **not spelled out** in the rule file today.

**Implementation guidance (no new author names in prose):**

1. **README** “Using the application”: **6–10 numbered steps** max on the landing page (install is already separate). Each step = one user action + one sentence on what appears. Link **“Full walkthrough → [docs/USER-GUIDE.md](docs/USER-GUIDE.md)** for longer flow.
2. **USER-GUIDE**: **Short sections** with a stable pattern: **Goal** (one line) → **Do** (steps) → **You should see** → **Optional: why** (link to DEV-STANDALONE anchor). Avoid long conceptual front-matter before the first click.
3. **No duplicate deep rules** in README—keep hybrid/judge details in DEV-STANDALONE; USER-GUIDE summarizes in one screen and links down.

## Optional rule amendment (reflect your tutorial preference)

Add 3–5 bullets under **Style rules** in [orchestrator-doc-style.mdc](.cursor/rules/orchestrator-doc-style.mdc), for example:

- Prefer **short atomic sections** (one main idea per heading).
- For **README** and **getting-started** docs, prefer a **numbered try-this flow** over abstract capability lists.
- Keep **deep architecture and API contracts** in DEV-STANDALONE (or linked docs), not in the first-page tutorial.

Extend **globs** to include `docs/**/*.md` (or `docs/USER-GUIDE.md` only if you want minimal scope).

## Deliverables (unchanged intent, tightened style)

1. **`docs/USER-GUIDE.md`** — Operator walkthrough per above; DEV links; **For developers** appendix for ids/modules if needed.
2. **`README.md`** — Atomic numbered “Using the application” strip + doc table row.
3. **`DEV-STANDALONE.md`** — One short paragraph + link to USER-GUIDE (bidirectional); optional checklist bullets **do / see**.
4. **`docs/HANDOFF.md`** — Documentation map row.
5. **`AGENTS.md`** — Optional one row in the instructions table for USER-GUIDE.
6. **Optional:** `DEBUG_INTERVIEW_CHAT.md` path fixes; **orchestrator-doc-style.mdc** globs + tutorial bullets.

## Out of scope

- Rewriting full hybrid semantics into README.
- Token/cost accounting.
