# Cursor plans

- **Root (`plans/`):** Put **active** execution plans here (new work).
- **`archive/`:** Optional subfolder for executed or superseded plans. Do not treat archived files as the live contract—verify against code and manual checks.
- **Agent Skills (`.cursor/skills/`):** This repo does **not** ship a `skills/` tree under `.cursor/`. Use your **global** Cursor skills unless you intentionally copy a customized `SKILL.md` here for repo-specific behavior (avoid duplicating stock skills you already have globally).

See **[AGENTS.md](../../AGENTS.md)** and **[DEV-STANDALONE.md](../../DEV-STANDALONE.md)** for how this repo is run and documented. Optional: **[`docs/monorepo-agents-rescue-checklist.md`](../../docs/monorepo-agents-rescue-checklist.md)** if you are porting notes from the old monorepo `AGENTS.md`.
