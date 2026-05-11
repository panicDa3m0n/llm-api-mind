# Changelog

All meaningful project changes are tracked here.

This project uses a practical changelog rather than a release-only log: each meaningful commit should map to an entry under `Unreleased` or a dated release section.

## Unreleased

### Added

- Created the project governance foundation:
  - `AGENTS.md`
  - `docs/project-blueprint.md`
  - `docs/activity-log.md`
  - `docs/decisions.md`
  - `docs/bug-ledger.md`
  - `docs/experiments.md`
  - `docs/api-contract.md`
- Added Git and release discipline:
  - `.gitignore`
  - `.gitmessage`
  - `docs/release-process.md`
- Added Phase 1A backend scaffold:
  - FastAPI app factory;
  - typed environment configuration;
  - `GET /health`;
  - backend `.env.example`;
  - pytest health endpoint smoke test;
  - ADR-0004 documenting SQLModel as the MVP storage choice.
- Added Phase 1B MiniMax provider smoke support:
  - Anthropic-compatible MiniMax provider wrapper;
  - `POST /api/debug/llm-smoke-test`;
  - unit tests for provider injection and missing key handling;
  - real MiniMax smoke verification path;
  - ADR-0005 documenting the Anthropic-compatible MiniMax SDK choice.
- Added Phase 1C storage foundation:
  - `sessions`, `messages`, `turns`, and `traces` SQLModel tables;
  - DB initialization helper;
  - repository functions for session/message/turn/trace round trips;
  - storage tests.
- Added ADR-0006 documenting the generous MiniMax output budget policy.
- Added Phase 1D persistent chat API:
  - session creation;
  - chat turn execution through MiniMax;
  - message persistence;
  - turn request/response traces;
  - trace fetch endpoint;
  - chat endpoint tests including missing-provider-key handling.
- Added Phase 1E frontend/debug cockpit:
  - Vite React app;
  - persistent chat UI;
  - trace panel;
  - MiniMax usage metrics;
  - frontend build workflow.
- Added a configurable Scarlet system prompt for persistent chat turns.
- Added Phase 2A Mind API facade:
  - `GET /mind/schema`;
  - `POST /mind/call`;
  - `mind_api` tool schema and dispatcher;
  - persistent `tool_calls` table;
  - optional `mind.tool_call` traces linked to sessions and turns.
- Added Phase 2B MiniMax tool-loop support for `mind_api` during persistent chat turns.
- Added streaming chat turns through `POST /api/chat/sessions/{session_id}/turn/stream`.
- Added a structured frontend agent timeline for provider thinking blocks, tool input, tool calls, tool results, and streamed final answers.
- Added per-turn inline chat timelines so each assistant message shows the ordered model/tool/final-answer operations that produced it.
- Added a dual-mode evaluation runner with scripted regression scenarios and adaptive interactive sessions.
- Added Memory v0:
  - persistent `memories` table;
  - implemented `POST /mind/memory/write`;
  - implemented `POST /mind/memory/search`;
  - traceable `mind.memory.write` and `mind.memory.search` records;
  - simple write policy, deduplication, lexical retrieval, source metadata, and usage counters.
- Added a `memory_v0_preference` evaluation scenario for memory write/search regression checks.
- Added a visible metacognition prompt experiment with the `Metacognizione:` public self-monitoring note.
- Added a `visible_metacognition_probe` evaluation scenario.

### Changed

- Updated project next steps to start from Git/repository setup and backend scaffolding.
- Connected the local repository configuration to `https://github.com/panicDa3m0n/llm-api-mind.git` and documented the remaining HTTPS push authentication blocker.
- Confirmed local `main` is synchronized with `origin/main` after the human owner completed the push.
- Confirmed non-interactive HTTPS push works from the local development environment.
- Replaced the temporary smoke-test token budget with configurable `MINIMAX_MAX_TOKENS=4096`, aligned with MiniMax M2.7 agentic usage instead of token-saving assumptions.
- Extended the provider abstraction from single-prompt generation to chat-history generation.
- Updated project status and local run instructions now that backend and frontend are runnable together.
- Accepted EXP-0001 Baseline Chat Trace after a real two-turn MiniMax run with stored messages and request/response traces.
- Updated chat tracing so `llm.request` records the effective system prompt source.
- Refined the default Scarlet prompt to use positive identity and operating-posture guidance instead of domain-specific denials.
- Expanded Scarlet's prompt with feminine identity and human-like conversational presence guidance.
- Restored `backend/.env.example` as a tracked placeholder template after local workspace recreation.
- Updated chat request/response traces to include tool schema, `mind.tool_call` events, normalized tool-call metadata, and raw provider tool-loop messages.
- Updated Scarlet's bundled prompt to describe `mind_api` schema discovery as an available runtime capability.
- Accepted EXP-0004 after a live MiniMax turn used `mind_api` and produced `llm.request`, `mind.tool_call`, and `llm.response` traces.
- Accepted EXP-0005 after a live MiniMax streaming turn emitted intermediate agentic events and persisted the expected traces.
- Updated streaming events to include a turn-local sequence and turn identifier so clients can render exact operation order inside the correct chat turn.
- Moved the structured agent timeline from the debug pane into the assistant message while keeping raw trace logs in the debug pane.
- Updated the immediate roadmap to evaluate the current system before designing memory, with scripted checks treated as regression evidence and interactive sessions treated as behavioral evidence.
- Recorded the first adaptive Scarlet pre-memory evaluation run and its source-attribution findings.
- Updated Scarlet's prompt with Memory v0 discipline: autonomous write/search decisions, source attribution, and required memory search when the user asks about persistent memory.
- Made Memory v0 tolerant of common model-shaped input aliases such as `pref`, `standard_preference`, `nota_operativa`, `why`, `reason`, `use`, `use_during`, qualitative confidence/salience, `limit`, and GET-style memory search.
- Documented ADR-0014 for using concise visible metacognition instead of raw reasoning dumps.
- Cleaned up the experiments document so Memory v0 results are recorded under EXP-0002.

### Fixed

- Initialized project tracking plan for the previously uninitialized Git repository state.
- Resolved the GitHub push blocker for the initial repository setup.
- Fixed detached SQLModel ORM object usage in the chat turn endpoint.
- Fixed chat provider initialization errors so missing MiniMax configuration returns structured `503 llm.not_configured`.
- Fixed the generic diagnostic-assistant fallback that could make the agent misidentify itself.
- Fixed detached SQLModel ORM usage in the new Mind API call endpoint by keeping scalar values across session boundaries.
- Fixed inline streaming timeline attachment by including `turn_id` on every NDJSON event.
- Fixed overly brittle Memory v0 validation discovered during live MiniMax runs by normalizing common semantic aliases and preserving harmless extra model fields in memory metadata.
- Fixed Python 3.10 compatibility in the evaluation runner by replacing `datetime.UTC` with `timezone.utc`.

## Release Notes Policy

Each release section should answer:

- What changed?
- Why did it change?
- Which roadmap phase, experiment, or decision does it support?
- How was it verified?
