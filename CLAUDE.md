# Claude Code Instructions — Excel Mapping Engine

## Documentation Update Rule

**Every time a feature is added or changed, update the relevant docs as part of the same task — not as a follow-up.**

### Which file to update and when

| File | Update when |
|------|------------|
| `AGENTS.md` | Any change to design decisions, config fields, known keys, file structure, or branch conventions |
| `README.md` | Any user-facing change: new config param, new mode, new behaviour |
| `config/run_config.example.json` | Any new config field added |
| `tests/` | Any new behaviour must have a corresponding test |

### What goes where

- **`AGENTS.md`** — context for AI agents: real config values, design decisions, known source keys, architecture rationale. Keep it accurate and concise.
- **`README.md`** — context for human users: how to configure, how to run, what each param does.

### Commit rule

Doc updates must be committed **in the same commit as the code change**, not separately.

---

## Project Conventions

- Work on feature branches, merge to `main` via explicit user request
- Run `pytest tests/ -v` before every merge — all tests must pass
- Never hardcode paths — all config via `run_config.json`
- `run_config.json` is gitignored — `run_config.example.json` is the committed template
- Hebrew field names in config/source files are normal — treat as opaque strings
