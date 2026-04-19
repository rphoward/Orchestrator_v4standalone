# Monorepo `AGENTS.md` rescue checklist (optional)

Use this if you still have a copy of the old monorepo (e.g. `orchestrator4-main`) and want to mine **`AGENTS.md`** for anything missing from the slim standalone **[`AGENTS.md`](../AGENTS.md)**.

| Monorepo section / topic | Relevant to this standalone repo? | Where it landed (if anywhere) |
|--------------------------|-----------------------------------|-------------------------------|
| v3 vs v4, `orchestrator_v3/` | No | Dropped — no v3 tree here |
| KB pipeline `/extract`, `/reindex`, `DocTools/`, `Docs/` | No | Dropped — not in this repo |
| Two-root `.env` (repo root + package) | Mostly no | Single **`.env`** at repo root — see **`DEV-STANDALONE.md`** |
| `run_dev.py`, smoke, standalone handbook | Yes | **`DEV-STANDALONE.md`**, **`README.md`**, **`AGENTS.md`** §3 |
| Sandbox “paste whole folder including `.venv`” | Yes | **`DEV-STANDALONE.md`** + **`AGENTS.md`** tone |
| Cursor rules vs user rules | Partially | **`AGENTS.md`** §2; architecture in **`.cursor/rules/`** |
| PyInstaller / `orchestrator4_entry.py` | Only if you add shipping | Not in standalone today — do not paste blindly |
| Voice (home-lab, ship, push back on real risks) | Yes | **`AGENTS.md`** §1; **`orchestrator-conduct.mdc`** |

**How to use:** Open old `AGENTS.md` side by side with current **`AGENTS.md`**. If a bullet is still true for *this* tree, add **one** line or a link to `DEV-STANDALONE.md`—do not paste whole sections.
