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
- configurable Scarlet system prompt for the agent identity;
- SQLite persistence for sessions, messages, turns, and traces;
- traceable `mind_api` schema tool loop;
- Memory v0 write/search with sourceable records and dedicated traces;
- streaming React cockpit with inline ordered agent-turn timeline;
- scripted and interactive evaluation runner;
- accepted baseline, tool-loop, streaming trace, and initial Memory v0 experiments.

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
1. Run adaptive Memory v0 evaluation sessions with the eval runner and cockpit.
2. Use scripted memory scenarios as regression checks, not as the main behavioral signal.
3. Decide the next memory slice: inspection UI, update/forget/conflict semantics, or attention context.
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

Evaluation runner:

```bash
cd backend
python -m app.evals.runner scripted app/evals/scenarios/baseline_tool_schema.json
python -m app.evals.runner scripted app/evals/scenarios/memory_v0_preference.json
python -m app.evals.runner interactive --title "adaptive baseline"
```

## Secrets

Do not commit real API keys.

Expected future environment variables:

```txt
MINIMAX_API_KEY=
MINIMAX_BASE_URL=https://api.minimax.io/anthropic
MINIMAX_MODEL=MiniMax-M2.7
AGENT_SYSTEM_PROMPT_PATH=
DATABASE_URL=sqlite:///./data/app.db
```
