# Orchestrator v4 (standalone)

Flask-based interview orchestration with a **Clean Architecture** layout: `core/` (domain and use cases), `infrastructure/` (SQLite, Gemini, adapters), `presentation/` (HTTP and static UI). The installable package name is **`orchestrator_v4`**; in this repository the package root is the **repo root** (see `pyproject.toml`).

**Repository:** [github.com/rphoward/Orchestrator_v4standalone](https://github.com/rphoward/Orchestrator_v4standalone)

## Requirements

- Python **3.11+**
- Recommended: [`uv`](https://github.com/astral-sh/uv) on `PATH` (used by `run_dev.py` to create `.venv` when missing)

## Quick start

```powershell
cd c:\Project\orchestrator_v4standalone
python run_dev.py --smoke
python run_dev.py
```

Then open **http://127.0.0.1:5001** (unless you set `ORCHESTRATOR_PORT`).

Create **`.env`** at the repo root with at least `GEMINI_API_KEY=…` if you use live Gemini. See **[DEV-STANDALONE.md](DEV-STANDALONE.md)** for env tables, SQLite notes, model registry, and a full verification checklist.

## Docs and agent rules

| Doc | Purpose |
|-----|---------|
| [DEV-STANDALONE.md](DEV-STANDALONE.md) | Developer handbook and operations |
| [AGENTS.md](AGENTS.md) | Short agent/human contract for this repo |
| [docs/HANDOFF.md](docs/HANDOFF.md) | Maintainer / long-session context reload |
| [.cursor/rules/](.cursor/rules/) | Cursor project rules (architecture, layers, safety) |

## Status

This tree was **migrated** from a larger project and force-synced to GitHub; treat **regression coverage as incomplete** until you re-run smoke and manual checks described in `DEV-STANDALONE.md`.

## Packaging note

`pyproject.toml` sets `readme = "DEV-STANDALONE.md"` for package metadata. This `README.md` is the **GitHub landing** summary; keep the two complementary, not contradictory.
