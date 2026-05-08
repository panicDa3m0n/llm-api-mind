# LLM API Mind

Experimental laboratory for testing whether an LLM can become more capable, coherent, and inspectable when supported by a modular cognitive API.

The project starts with a simple principle:

```txt
Build the microscope before the mind.
```

The first milestone is a local MiniMax M2.7 chat runtime where every turn is stored, inspectable, and ready for later cognitive API experiments.

## Current Status

Foundation documentation and repository workflow are being established.

Implementation has not started yet.

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
1. Complete Git/GitHub setup.
2. Scaffold FastAPI backend.
3. Add MiniMax provider client.
4. Add SQLite trace storage.
5. Implement minimal chat endpoints.
6. Add minimal debug UI.
7. Run EXP-0001 Baseline Chat Trace.
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

