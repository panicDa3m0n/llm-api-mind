# LLM API Mind

Experimental laboratory for testing whether an LLM can become more capable, coherent, and inspectable when supported by a modular cognitive API.

The project starts with a simple principle:

```txt
Build the microscope before the mind.
```

The first milestone is a local MiniMax M2.7 chat runtime where every turn is stored, inspectable, and ready for later cognitive API experiments.

## Current Status

The project has a working local baseline runtime:

- FastAPI backend;
- MiniMax M2.7 provider integration;
- SQLite persistence for sessions, messages, turns, and traces;
- minimal React debug cockpit.
- accepted EXP-0001 baseline trace run.

## Key Documents

- `AGENTS.md`: operating protocol for Codex/Scarlet as IDE agent.
- `docs/project-blueprint.md`: main project blueprint.
- `docs/activity-log.md`: continuity log.
- `docs/decisions.md`: architectural decisions.
- `docs/bug-ledger.md`: known bugs, fixes, and environment notes.
- `docs/experiments.md`: hypotheses, baselines, metrics, and results.
- `docs/api-contract.md`: planned and implemented API contracts.
- `docs/release-process.md`: commit, changelog, and release discipline.
- `CHANGELOG.md`: concrete history of meaningful changes.

## Immediate Roadmap

```txt
1. Add the minimal Phase 2 `mind_api` facade.
2. Add schema discovery for available API actions.
3. Add memory and attention only after `mind_api` is traceable.
```

## Local Run

Backend:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev -- --port 5173
```

Open:

```txt
http://127.0.0.1:5173
```

## Secrets

Do not commit real API keys.

Expected future environment variables:

```txt
MINIMAX_API_KEY=
MINIMAX_BASE_URL=https://api.minimax.io/anthropic
MINIMAX_MODEL=MiniMax-M2.7
DATABASE_URL=sqlite:///./data/app.db
```
