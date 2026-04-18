---
name: Fix datetime.now core violation
overview: Remove the single confirmed core-layer I/O violation — a direct `datetime.now()` call in `session_export_v3_format.py` — by accepting an optional timestamp parameter from the caller.
todos:
  - id: fix-signature
    content: "Add optional `exported_at: str | None = None` parameter to `build_v3_session_export_document`, use it instead of `datetime.now()`, remove unused datetime imports"
    status: pending
  - id: fix-caller
    content: In `presentation/interview_session_routes.py`, pass `exported_at=datetime.now(timezone.utc).isoformat()` at the call site; add datetime import
    status: pending
  - id: verify
    content: Run smoke test, grep core/ for datetime.now (expect zero hits), run any existing tests
    status: pending
isProject: false
---

# Fix `datetime.now()` I/O Violation in Core

## What is wrong

[`orchestrator_v4/core/use_cases/session_export_v3_format.py`](orchestrator_v4/core/use_cases/session_export_v3_format.py) line 65 calls `datetime.now(timezone.utc)` directly. Core must not perform I/O, and reading the system clock counts as I/O. This is the only confirmed core-layer violation in the codebase.

```python
# line 65, current
"exported_at": datetime.now(timezone.utc).isoformat(),
```

## What is NOT wrong (analysis rebuttal)

The LLM fields (`model`, `thinking_level`, `temperature`, `include_thoughts`) on `InterviewTurnAgentRosterEntry` are **not** an architecture violation for this project:

- This application's domain IS LLM interview orchestration. Those fields are user-configurable agent settings, visible in the UI, stored in the DB, and carried as data — not as I/O.
- The core port [`InterviewLlmGateway.get_response()`](orchestrator_v4/core/ports/interview_llm_gateway.py) already accepts all four as parameters. The vocabulary is already in core's port contract. The entity is just the data carrier.
- Removing them would break five use case files with no fix in the proposed Active Cluster. The "move retrieval to the gateway" alternative is architecturally worse (gateway would need a DB connection for config lookup).

**Do not touch `interview_turn.py` or create a `ClockPort`.** A `ClockPort` is overweight for a single call site.

## The fix (two files, three edits)

### Task 1 — Add optional `exported_at` parameter to the function

**File:** [`orchestrator_v4/core/use_cases/session_export_v3_format.py`](orchestrator_v4/core/use_cases/session_export_v3_format.py)

- Change the function signature from:
  ```python
  def build_v3_session_export_document(bundle: InterviewSessionReadBundle) -> dict:
  ```
  to:
  ```python
  def build_v3_session_export_document(
      bundle: InterviewSessionReadBundle,
      exported_at: str | None = None,
  ) -> dict:
  ```
- Replace line 65:
  ```python
  "exported_at": datetime.now(timezone.utc).isoformat(),
  ```
  with:
  ```python
  "exported_at": exported_at or "",
  ```
- Remove the `datetime` and `timezone` imports (lines 5-6) since they are no longer used in this file.

**Done looks like:** The function is a pure transform — same inputs always produce the same output. No stdlib `datetime` import remains in the file.

### Task 2 — Move the clock read to the presentation-layer caller

**File:** [`orchestrator_v4/presentation/interview_session_routes.py`](orchestrator_v4/presentation/interview_session_routes.py)

- Add `from datetime import datetime, timezone` to the imports.
- At the call site (around line 132), change:
  ```python
  export_doc = build_v3_session_export_document(bundle)
  ```
  to:
  ```python
  export_doc = build_v3_session_export_document(
      bundle,
      exported_at=datetime.now(timezone.utc).isoformat(),
  )
  ```

**Done looks like:** The `datetime.now()` call lives in presentation (where I/O is allowed). Core stays pure.

### Task 3 — Verify

- Run `python run_dev.py --smoke` from `orchestrator_v4/` to confirm the app boots.
- Grep `core/` for `datetime.now` — expect zero hits.
- If the project has tests, run them.

## Rejected alternatives

- **ClockPort ABC:** Adds a new file, a new interface, constructor injection, bootstrap wiring, and an infrastructure implementation — all for one call site. A plain parameter does the same job with zero new abstractions.
- **Stripping LLM fields from entity:** Breaks the app immediately, solves a non-problem (see rebuttal above), and the proposed deferred fix (gateway does its own config lookup) is a worse design than the current clean data flow.
