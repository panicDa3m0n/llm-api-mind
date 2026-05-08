# Activity Log

This file preserves project continuity across IDE-agent sessions.

Use it to record meaningful work, verification, open questions, and the next suggested step. Do not log every tiny edit, but do log changes that affect direction, architecture, APIs, experiments, prompts, or debugging knowledge.

## 2026-05-08 - Project Documentation Foundation

Goal:

Create a project memory foundation so future work can continue without relying only on conversational memory.

Changes:

- Created `docs/project-blueprint.md` as the main project blueprint.
- Created `AGENTS.md` as the short operational protocol for the IDE agent.
- Created companion documentation registries:
  - `docs/activity-log.md`
  - `docs/decisions.md`
  - `docs/bug-ledger.md`
  - `docs/experiments.md`
  - `docs/api-contract.md`
- Updated `docs/project-blueprint.md` so the current next steps now reflect the completed documentation foundation.

Verification:

- Confirmed `docs/project-blueprint.md` exists and is readable.
- Repository is not currently initialized as a Git repository; `git status` fails until Git is initialized.

Open Questions:

- Decide whether to initialize Git immediately before backend implementation.
- Decide whether the first backend scaffold should use plain SQLAlchemy or SQLModel.

Next Suggested Step:

Initialize or intentionally defer Git, then scaffold the minimal FastAPI backend with configuration and a health endpoint.

## 2026-05-08 - Git And Release Discipline

Goal:

Set up local project tracking so repository history, changelog entries, and roadmap progress stay connected.

Changes:

- Added `README.md`.
- Added `CHANGELOG.md`.
- Added `.gitignore`.
- Added `.gitmessage`.
- Added `docs/release-process.md`.
- Updated `AGENTS.md` with changelog and commit-memory rules.
- Added ADR-0003 for Git history, changelog, and agent commit identity.

Verification:

- Local Git initialization completed on branch `main`.
- Repository-local Git author configured as `Scarlet Codex <scarlet-codex@users.noreply.github.com>`.
- Commit template configured from `.gitmessage`.
- Foundation files were captured in the initial local commit.

Open Questions:

- Remote GitHub repository creation is blocked in this environment because `gh` is not installed and the GitHub connector does not expose repository creation.
- Preferred remote target is documented as `panicDa3m0n/llm-api-mind`, private by default.
- Local Git is older and does not support newer commands such as `git init -b` or `git branch --show-current`; use compatible commands when needed.

Next Suggested Step:

Initialize local Git on `main`, configure repository-local Scarlet author metadata, make the foundation commit, then connect to GitHub after the remote repository exists.

## 2026-05-08 - GitHub Remote Connection

Goal:

Connect the local repository to the GitHub remote provided by the project owner.

Changes:

- Confirmed `origin` points to `https://github.com/panicDa3m0n/llm-api-mind.git`.
- Confirmed the remote repository is reachable and currently has no refs.
- Attempted to push `main` to `origin`.
- Recorded the local HTTPS authentication blocker.

Verification:

- `git remote -v` shows `origin` set to the GitHub repository.
- `git ls-remote https://github.com/panicDa3m0n/llm-api-mind.git` returned no refs, consistent with an empty repository.
- `GIT_TERMINAL_PROMPT=0 git push -u origin main` failed because local Git credentials are not available.
- SSH access check to `git@github.com` failed with `Permission denied (publickey)`, so SSH push is not currently available.

Open Questions:

- The local environment needs GitHub authentication for HTTPS push, or an authorized GitHub SSH key.

Next Suggested Step:

Authenticate local GitHub access, then run `git push -u origin main`.

## 2026-05-08 - Phase 1A Backend Scaffold

Goal:

Start Phase 1 with the smallest useful backend slice: FastAPI config, health endpoint, env template, and a test.

Changes:

- Added `backend/pyproject.toml`.
- Added `backend/.env.example`.
- Added `backend/README.md`.
- Added `backend/app/config.py`.
- Added `backend/app/main.py`.
- Added `backend/tests/test_health.py`.
- Updated `.gitignore` so nested `.env.example` files remain trackable.
- Documented `GET /health` in `docs/api-contract.md`.
- Added ADR-0004 to record SQLModel as the MVP storage choice.
- Marked GitHub HTTPS push authentication as resolved after the human owner pushed `main`.

Verification:

- Created a local ignored venv at `backend/.venv`.
- Installed backend dev dependencies with `python3 -m pip install -e ".[dev]"`.
- Ran `pytest` from `backend`; 1 test passed.
- Pushed commit `35cefb4` to `origin/main` from this environment.

Open Questions:

- None for this slice.

Next Suggested Step:

Install backend dev dependencies, run the health test, then add the MiniMax provider client after the user inserts `MINIMAX_API_KEY` into `backend/.env`.

## 2026-05-08 - Phase 1B MiniMax Provider Smoke

Goal:

Add the first real LLM provider integration and verify that MiniMax M2.7 is reachable from the backend.

Changes:

- Added the Anthropic-compatible MiniMax provider wrapper.
- Added `POST /api/debug/llm-smoke-test`.
- Added unit tests for provider injection and missing MiniMax key handling.
- Added API contract documentation for the smoke endpoint.
- Added backend README smoke-test instructions.
- Added ADR-0005 for the Anthropic-compatible MiniMax SDK choice.

Verification:

- Installed updated backend dependencies including the Anthropic SDK.
- Ran `pytest` from `backend`; 3 tests passed.
- Ran a real MiniMax smoke call with `max_tokens=128`; response returned `text: pong`.
- Observed that `max_tokens=32` can return an empty text response because M2.7 may spend the output budget before final text. This was later superseded by the project policy to use a generous configurable default.

Open Questions:

- None for this slice.

Next Suggested Step:

Add SQLite schema for sessions, messages, turns, and traces.

## 2026-05-08 - Phase 1C Storage Schema And Token Budget Policy

Goal:

Correct the MiniMax token-budget policy and add the SQLite persistence foundation for baseline chat tracing.

Changes:

- Added `MINIMAX_MAX_TOKENS=4096` to backend settings and `.env.example`.
- Updated the LLM smoke endpoint to use the configured default when `max_tokens` is omitted.
- Added `max_tokens` to the LLM smoke response for observability.
- Added SQLModel storage tables for `sessions`, `messages`, `turns`, and `traces`.
- Added storage DB helpers and repository functions.
- Added tests for default MiniMax token budget and storage round-trip behavior.
- Added ADR-0006 for the generous MiniMax output budget policy.
- Documented the MVP storage schema in `docs/api-contract.md`.

Verification:

- Ran `pytest` from `backend`; 6 tests passed.
- Ran a real MiniMax smoke call without explicit `max_tokens`; response returned `text: pong` and `max_tokens: 4096`.

Open Questions:

- None for this slice.

Next Suggested Step:

Implement persistent chat endpoints on top of the SQLite schema.

## 2026-05-08 - Phase 1D Persistent Chat Endpoints

Goal:

Implement the baseline chat API on top of the SQLite schema so every turn stores messages and request/response traces.

Changes:

- Added `POST /api/chat/sessions`.
- Added `POST /api/chat/sessions/{session_id}/turn`.
- Added `GET /api/chat/sessions/{session_id}/messages`.
- Added `GET /api/debug/traces/{turn_id}`.
- Added provider `generate_chat()` support so MiniMax receives persisted chat history instead of a flattened prompt.
- Wired database initialization into `create_app()`.
- Added chat API tests with provider fakes, missing-provider-key handling, and in-memory SQLite.
- Recorded BUG-0002 for detached ORM instances across SQLModel session boundaries.
- Recorded BUG-0003 for provider initialization errors escaping chat endpoint handling.

Verification:

- Ran `pytest` from `backend`; 10 tests passed.
- Ran a real MiniMax chat turn through the persistent endpoint using an in-memory DB; response returned `assistant: pong`, two trace IDs, and trace kinds `llm.request` and `llm.response`.

Open Questions:

- The first baseline trace experiment still needs a human-readable debug cockpit or a CLI/scripted scenario runner.

Next Suggested Step:

Add a minimal frontend chat/debug cockpit or a temporary CLI experiment runner for EXP-0001.
