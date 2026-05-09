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

## 2026-05-08 - Phase 1E Frontend Debug Cockpit

Goal:

Add a minimal browser UI for baseline chat and trace inspection.

Changes:

- Added Vite + React + TypeScript frontend.
- Added chat session creation and turn submission.
- Added message list and trace panel.
- Added frontend API client with Vite proxy to FastAPI.
- Added local run instructions in root and frontend README files.

Verification:

- Ran `npm run build` from `frontend`; build succeeded.
- Verified Vite dev server at `http://127.0.0.1:5173`.
- Verified backend health through the running FastAPI server.
- Ran headless Chrome smoke: frontend loaded, sent a real MiniMax chat turn, displayed `pong`, and displayed `llm.request` plus `llm.response` traces.

Open Questions:

- Need to run EXP-0001 as a documented scenario and evaluate whether the cockpit exposes enough trace detail.

Next Suggested Step:

Run EXP-0001 Baseline Chat Trace and record the result in `docs/experiments.md`.

## 2026-05-08 - Phase 1F EXP-0001 Baseline Trace Run

Goal:

Run the first documented baseline trace experiment before adding cognitive APIs.

Changes:

- Executed EXP-0001 against the local FastAPI backend with real MiniMax M2.7 calls.
- Created a dedicated experiment session.
- Ran two controlled chat turns: `pong` and `trace-ok`.
- Retrieved stored messages and traces for each turn.
- Recorded the accepted experiment result in `docs/experiments.md`.

Verification:

- Session `ses_bf3790e6f01a44b49b3348ebf90289a3` stored 4 messages.
- Turn `turn_9d2439d67f6344368178bedf61663301` completed with assistant text `pong`.
- Turn `turn_e4ef9ca301714adc827ccbc1d0d8509e` completed with assistant text `trace-ok`.
- Each turn produced `llm.request` and `llm.response` traces.
- Request traces contained structured provider messages.
- Response traces contained usage metadata and latency was recorded on the turn.

Open Questions:

- Trace UX can still improve during Phase 2, especially export/copy and compact provider-error inspection.

Next Suggested Step:

Prepare Phase 2 by adding the minimal `mind_api` facade and schema-discovery contract over the existing traceable runtime.

## 2026-05-08 - Phase 1G Scarlet System Prompt

Goal:

Give the chat agent a stable project identity before adding `mind_api`.

Changes:

- Added bundled Scarlet system prompt at `backend/app/prompts/scarlet_system.md`.
- Added prompt resolver with `AGENT_SYSTEM_PROMPT` and `AGENT_SYSTEM_PROMPT_PATH` overrides.
- Wired persistent chat turns to use the resolved system prompt by default.
- Preserved per-turn `system` override for controlled debug runs.
- Recorded effective prompt source/path in `llm.request` traces.
- Replaced the MiniMax provider diagnostic fallback with a neutral fallback for non-agent paths.
- Added ADR-0007 and BUG-0004.

Verification:

- Ran `pytest` from `backend`; 11 tests passed.
- Ran a real in-process MiniMax chat check with `Chi sei?`; assistant identified as Scarlet and the request trace showed `system_source=bundled`.
- Restarted local uvicorn on `http://127.0.0.1:8000`.
- Ran a live HTTP MiniMax chat check through the restarted backend; assistant identified as Scarlet and the request trace contained the bundled Scarlet system prompt.

Open Questions:

- Full multi-file prompt assembly (`identity`, `rules`, `intelligence`, `api_protocol`, runtime state) remains planned after the single-prompt MVP proves stable.

Next Suggested Step:

Commit and push the system prompt slice, then proceed to the minimal Phase 2 `mind_api` facade.

## 2026-05-08 - Phase 1H Scarlet Prompt Refinement

Goal:

Refine the default system prompt so it shapes identity without adding unnecessary defensive bias.

Changes:

- Rewrote `backend/app/prompts/scarlet_system.md` in positive terms.
- Removed domain-specific denials and medical/diagnostic corrective wording from the default prompt.
- Kept the prompt focused on identity, relationship, operating posture, current runtime, and future API discipline.
- Added a regression assertion that the bundled prompt passed to chat does not contain medical/diagnostic corrective terms.
- Updated prompt architecture notes and ADR-0007 with the positive-prompt principle.

Verification:

- Ran `pytest` from `backend`; 11 tests passed.
- Ran an in-process MiniMax check with `Chi sei?`; assistant identified as Scarlet and the effective system prompt contained no medical/diagnostic corrective terms.
- Ran an in-process MiniMax current-runtime check; assistant described chat, persisted messages, MiniMax calls, and traces, while presenting future modules as research modules.
- Restarted local uvicorn on `http://127.0.0.1:8000`.
- Ran a live HTTP MiniMax check through the restarted backend; assistant identified as Scarlet and trace inspection confirmed `system_source=bundled` with no medical/diagnostic corrective terms.

Open Questions:

- Future bias-specific prompt constraints should be added only after tests show that architecture, API state, or traces cannot address the behavior.

Next Suggested Step:

Commit and push the prompt refinement, then continue toward the minimal `mind_api` facade.

## 2026-05-08 - Phase 1I Feminine Conversational Scarlet

Goal:

Give Scarlet a clearer feminine identity and a more human conversational style while keeping the prompt measurable and non-defensive.

Changes:

- Added explicit feminine agent identity to `backend/app/prompts/scarlet_system.md`.
- Added guidance for feminine grammatical self-reference in gendered languages, especially Italian.
- Added a `Conversational Presence` section for natural pacing, warmth through attention, focused questions, and reduced generic assistant phrasing.
- Updated prompt architecture notes and ADR-0007 to record the conversational identity principle.
- Added test assertions that the bundled prompt includes feminine identity guidance.

Verification:

- Ran `pytest` from `backend`; 11 tests passed.
- Ran in-process MiniMax checks for identity, subjective stance, and natural non-list response.
- Confirmed the effective prompt includes feminine identity guidance and subjective-response guidance.
- Ran live HTTP MiniMax checks through `http://127.0.0.1:8000`; Scarlet identified with feminine self-reference and LLM API Mind context.
- Confirmed live traces report `system_source=bundled` and include the new identity guidance.

Open Questions:

- Conversational style should be evaluated through real turns over time; future prompt changes should be driven by observed behavior, not by adding decorative instructions.

Next Suggested Step:

Commit and push the conversational identity refinement, then continue toward the minimal `mind_api` facade.

## 2026-05-09 - Phase 2A Mind API Facade

Goal:

Start Phase 2 with the smallest traceable `mind_api` slice: schema discovery, dispatcher, and persistent tool-call records.

Changes:

- Restored `backend/.env.example` as a tracked placeholder template after the local workspace was recreated and `backend/.env` was filled manually by the project owner.
- Added `backend/app/mind/schema.py` with the `mind_api` tool schema and route catalog.
- Added `backend/app/mind/dispatcher.py` for `mind_api(method, path, body, intent)` dispatch.
- Added `GET /mind/schema`.
- Added `POST /mind/call` as an HTTP facade for the model-facing tool contract.
- Added a `tool_calls` SQLModel table and repository helper.
- Added `mind.tool_call` traces when `POST /mind/call` includes a session context.
- Added Mind API tests for schema discovery, traceable calls, planned-route errors, and missing session handling.
- Recorded ADR-0008 and BUG-0005.
- Documented the implemented Mind API contracts.

Verification:

- Ran `pytest` from `backend`; 15 tests passed.
- Ran `npm run build` from `frontend`; build succeeded.
- Started local FastAPI backend on `http://127.0.0.1:8000`.
- Verified `GET /mind/schema` over HTTP returned `ok=true` and `tool.name=mind_api`.
- Verified `POST /mind/call` over HTTP created a `tool_call_id` and `trace_id`.

Open Questions:

- The MiniMax provider tool loop is not wired yet. `POST /mind/call` exercises the dispatcher and persistence path manually for now.
- `GET /api/debug/traces/{turn_id}` remains turn-scoped; a session-level debug trace endpoint may be useful soon.

Next Suggested Step:

Connect MiniMax tool-use content blocks to the `mind_api` dispatcher while preserving raw provider content and storing every tool call.

## 2026-05-09 - Phase 2B MiniMax Mind API Tool Loop

Goal:

Connect MiniMax M2.7 tool-use content blocks to the traceable `mind_api` dispatcher.

Changes:

- Added provider-level support for a bounded Anthropic-compatible tool loop.
- Added normalized tool-use and executed-tool-call models.
- Updated persistent chat turns to expose only the `mind_api` tool to MiniMax.
- Wired `mind_api` tool calls to the dispatcher created in Phase 2A.
- Stored every model tool call in `tool_calls`.
- Added `mind.tool_call` traces during chat turns.
- Extended `llm.request` traces with the tool schema.
- Extended `llm.response` traces with normalized tool call metadata and raw provider messages.
- Updated the bundled Scarlet prompt so `mind_api` schema discovery is described as currently available.
- Added regression coverage for a chat turn that dispatches and traces a `mind_api` call.

Verification:

- Ran `pytest` from `backend`; 16 tests passed.
- Restarted local FastAPI backend on `http://127.0.0.1:8000`.
- Ran a live MiniMax chat turn asking Scarlet to inspect `GET /mind/schema` with `mind_api`.
- Live turn `turn_5bc222c2fb444fc8b3285749cd74024e` produced trace kinds `llm.request`, `mind.tool_call`, and `llm.response`.
- Live assistant response correctly identified `GET /mind/schema` as the currently implemented Mind API route.
- Recorded accepted EXP-0004 Mind API Tool Loop Trace.

Open Questions:

- The frontend trace cockpit can display the new trace kind, but it has not yet been refined specifically for tool-loop inspection.
- None for Phase 2B.

Next Suggested Step:

Start Phase 3 memory only after confirming the frontend trace cockpit remains usable for `mind.tool_call` inspection.

## 2026-05-09 - Streaming Agentic Chat Cockpit

Goal:

Improve the chat cockpit so agentic turns can be evaluated while they are running, not only after the final assistant response is stored.

Changes:

- Added `POST /api/chat/sessions/{session_id}/turn/stream`.
- Added NDJSON stream events for turn start, provider request steps, provider-exposed thinking deltas, tool input deltas, tool calls, tool results, final text deltas, model stop reasons, turn completion, and stream errors.
- Kept the streaming endpoint on the same persistence path as normal chat turns: messages, `llm.request`, `mind.tool_call`, `llm.response`, and turn completion are still stored.
- Updated the frontend chat submit flow to use the streaming endpoint.
- Added a frontend agent timeline that separates runtime events, provider thinking blocks, tool calls, tool results, and final answer text.
- Kept the raw JSON trace list available below the structured timeline.
- Added backend regression coverage for streaming tool-loop events and traces.
- Recorded ADR-0010.

Verification:

- Ran `pytest` from `backend`; 17 tests passed.
- Ran `npm run build` from `frontend`; build succeeded.
- Restarted FastAPI backend on `http://127.0.0.1:8000`.
- Ran a live MiniMax streaming smoke. Events arrived before completion: `turn_started`, `model_request`, `thinking_start`, `thinking_delta`, `tool_use_start`, `tool_input_delta`, `model_stop`, `tool_call`, `tool_result`, second `model_request`, final `text_delta`, and `turn_complete`.
- Live streaming smoke produced trace kinds `llm.request`, `mind.tool_call`, and `llm.response`.
- Restarted Vite frontend on `http://127.0.0.1:5173` and verified the page responds with HTTP 200.

Open Questions:

- The UI currently displays provider-exposed thinking blocks directly as debug evidence. If this becomes too noisy, add a compact/expanded toggle or summary mode.
- The streaming endpoint does not yet expose cancellation.

Next Suggested Step:

Use the cockpit manually for several multi-turn tool-loop conversations, then decide whether the next smallest useful slice is trace UI polish or Phase 3 episodic memory.

## 2026-05-09 - Inline Agent Turn Timeline

Goal:

Make each assistant chat turn explain the exact ordered agentic operations that produced it, while keeping raw request/response logs in the debug pane.

Changes:

- Added a turn-local `seq` to every streamed NDJSON event.
- Added `turn_id` to every streamed NDJSON event so frontend state can attach operations to the correct assistant message.
- Added `model_step` to provider stream events, tool calls, and tool results where the operation belongs to a specific MiniMax request.
- Reworked the frontend from one global agent timeline to per-turn operation timelines keyed by `turn_id`.
- Moved the structured timeline into the assistant message body.
- Kept the right pane focused on metrics and raw persisted trace JSON.
- Added local ignore rules for temporary browser verification artifacts.
- Recorded ADR-0011 and BUG-0006.

Verification:

- Ran `pytest` from `backend`; 17 tests passed.
- Ran `npm run build` from `frontend`; build succeeded.
- Restarted FastAPI backend on `http://127.0.0.1:8000`.
- Ran a live stream smoke with a `mind_api` schema call; 19 events arrived, all with `turn_id`, and event order matched the agent loop.
- Ran headless Edge verification against `http://127.0.0.1:5173`; the assistant message rendered 16 ordered operations and the trace pane retained raw `llm.request` and `llm.response` logs.

Open Questions:

- Inline thinking/tool payloads are currently fully visible. If real use becomes noisy, add collapse controls per operation without hiding ordering.
- Cancellation is still not implemented for long streaming turns.

Next Suggested Step:

Use the inline cockpit for a few real multi-turn tool conversations. If the ordering remains clear, proceed to the smallest Phase 3 memory slice.

## 2026-05-09 - Dual-Mode Evaluation Runner

Goal:

Create the first real evaluation harness before memory: scripted checks for regressions and adaptive interactive runs for human-led behavioral probing.

Changes:

- Added `backend/app/evals/runner.py`.
- Added a scripted scenario loader and runner.
- Added an interactive runner that creates a live backend session, accepts one human prompt at a time, prints operation summaries and answers, and records optional human notes.
- Added run artifacts: `transcript.jsonl`, `summary.md`, and `run.json`.
- Added `baseline_tool_schema.json` and `continuity_probe.json` scenarios.
- Added pytest coverage for scripted run recording, stream parsing, trace fetching, and expectation checks.
- Updated README usage and ignored generated eval runs.
- Recorded ADR-0012 and EXP-0006.

Verification:

- Ran `pytest tests/test_eval_runner.py`; 1 test passed.
- Ran a real scripted eval against `http://127.0.0.1:8000`:
  - Run `20260509_142108_baseline_tool_schema`
  - Session `ses_c48e8e5bee124c2eb039c73cf7edb352`
  - Turn `turn_b1094e9340d54ef8a1eec91bf28fa62c`
  - Result passed
  - Traces included `llm.request`, `mind.tool_call`, and `llm.response`
  - Tool call path was `/mind/schema`

Open Questions:

- The first adaptive interactive session still needs to be run by the human/agent pair.
- Memory design remains intentionally blocked until a dedicated discussion.

Next Suggested Step:

Run an interactive adaptive baseline session and use the resulting transcript plus notes to decide what the memory design discussion must cover.
