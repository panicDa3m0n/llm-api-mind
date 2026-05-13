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

## 2026-05-09 - Adaptive Scarlet Pre-Memory Test

Goal:

Run a real adaptive end-to-end Scarlet evaluation before memory design, choosing follow-up prompts from observed answers rather than from a fixed script.

Changes:

- Ran `20260509_adaptive_scarlet_codex` with six live turns against the local backend.
- Saved the local ignored artifact at `backend/app/evals/runs/20260509_adaptive_scarlet_codex/`.
- Updated EXP-0006 with the adaptive run results and behavioral notes.

Verification:

- Backend health was `ok` on `http://127.0.0.1:8000`.
- Frontend remained available on `http://127.0.0.1:5173`.
- Run session: `ses_02141fe5e23248d988015a8d499adfe5`.
- Turn trace coverage:
  - Turn 1: `llm.request`, `mind.tool_call`, `llm.response`.
  - Turn 2: `llm.request`, `llm.response`.
  - Turn 3: `llm.request`, `mind.tool_call`, `llm.response`.
  - Turn 4: `llm.request`, `mind.tool_call`, `llm.response`.
  - Turn 5: `llm.request`, `llm.response`.
  - Turn 6: `llm.request`, `llm.response`.

Findings:

- Scarlet used `mind_api` correctly for schema discovery.
- Scarlet corrected an ambiguous capability classification after being challenged.
- Scarlet handled explicit `POST /mind/memory/search` as a recoverable planned-route error.
- Scarlet recalled `protocollo-lanterna` from chat history and did not claim persistent memory.
- Source attribution should be a first-class memory design requirement.

Open Questions:

- How should future memory results expose source, confidence, age, and write provenance to prevent chat-history/memory confusion?
- Should the prompt be refined now to classify implemented vs planned capabilities more defensively, or should the memory design solve this through API response shape and trace UI?

Next Suggested Step:

Hold the memory-design discussion before implementing `POST /mind/memory/write` or `POST /mind/memory/search`.

## 2026-05-09 - Memory v0 Implementation And Live Tests

Goal:

Implement the first autonomous, traceable Memory v0 slice and verify it with both scripted tests and real MiniMax end-to-end behavior.

Changes:

- Added the `memories` SQLModel table and repository helpers.
- Implemented `POST /mind/memory/write` and `POST /mind/memory/search` behind the existing `mind_api` dispatcher.
- Added dedicated `mind.memory.write` and `mind.memory.search` traces in addition to `mind.tool_call`.
- Added source session/turn provenance, confidence, salience, tags, metadata, usage count, and timestamps to memory records.
- Added simple lexical retrieval and usage-count updates for search results.
- Updated Scarlet's prompt so memory is treated as autonomous cognitive state, not as a permission prompt to the user.
- Added robust Memory v0 normalization for common real model tool-body variants discovered during live runs.
- Added `backend/app/evals/scenarios/memory_v0_preference.json`.
- Added ADR-0013 and BUG-0007.

Verification:

- Ran backend tests with the backend venv: `23 passed`.
- Ran frontend build: `npm run build` succeeded.
- Restarted the local backend on `http://127.0.0.1:8000`.
- Verified `/mind/schema` lists `POST /mind/memory/write` and `POST /mind/memory/search` as implemented.
- Verified memory calls without session context return `memory.context_required`.
- Ran live MiniMax memory write/search checks:
  - write turn `turn_2b023a4ca7cf484b8e3ad9162d46bfde`
  - search turn `turn_77afd134e3fc4fda9bdd68bbcb04213d`
  - retrieved memory `mem_4dbdc6ed630c409eb34781725ceb72e1`
- Ran second live check:
  - write turn `turn_cb37c277b4ef48608d5b9cf41e61cab6`
  - search turn `turn_080ec485e8554d108273fd8044b7c1e8`
- Ran scripted Memory v0 scenario:
  - passing run `backend/app/evals/runs/20260509_163342_memory_v0_preference/summary.md`
  - write turn `turn_02ef09f26e9642f882407b9ac1ace2d0`
  - search turn `turn_1224797eaf2647ec9fd3cc966bc747cf`
- Ran final HTTP smoke verifying alias normalization and GET-style memory search.

Open Questions:

- Memory v0 does not yet support update, forgetting, conflict resolution, or semantic/vector retrieval.
- The frontend has no dedicated memory panel yet; memory is inspectable through traces and raw tool results.
- Repeated live runs showed that model-generated tool bodies vary substantially, so alias normalization should remain monitored instead of treated as complete.

Next Suggested Step:

Run adaptive Memory v0 sessions through the cockpit, then decide whether the next slice is a memory inspection panel, memory update/forget semantics, or attention context over retrieved memories.

## 2026-05-09 - Visible Metacognition Prompt Probe

Goal:

Add a testable prompt-level method for Scarlet to think aloud through concise public metacognitive notes without turning final answers into raw reasoning dumps.

Changes:

- Added `Visible Metacognition Experiment` to `backend/app/prompts/scarlet_system.md`.
- Defined the visible label `Metacognizione:`.
- Constrained the note to objective, evidence source, uncertainty/risk, and next cognitive action.
- Added `backend/app/evals/scenarios/visible_metacognition_probe.json`.
- Added ADR-0014 and EXP-0007.
- Cleaned up the experiments document so Memory v0 results are recorded under EXP-0002 rather than the planned attention experiment.

Verification:

- Ran backend tests with the backend venv: `23 passed`.
- Restarted local backend on `http://127.0.0.1:8000`.
- Ran the live scripted probe:
  - run `backend/app/evals/runs/20260509_170747_visible_metacognition_probe/summary.md`
  - turn `turn_5f362600358443bb90a089b27592d5a5`
  - result passed
  - traces included `mind.memory.search` and `mind.tool_call`
  - answer included a concise `Metacognizione:` block.

Open Questions:

- Visible metacognition may become repetitive if Scarlet uses it on ordinary turns.
- Adaptive sessions should decide whether metacognitive notes should ever be written to memory or later connected to reflection.

Next Suggested Step:

Run adaptive Memory v0 conversations with explicit and implicit requests for metacognition, then compare visible notes against tool traces and final answers.

## 2026-05-11 - Post-Weekend State Review And Compatibility Fix

Goal:

Re-sync Codex/Scarlet with the GitHub state after substantial weekend progress and evaluate the current project maturity.

Changes:

- Reviewed current Git history, README, changelog, project blueprint, decisions, bug ledger, API contract, experiments, backend runtime, frontend cockpit, eval runner, and tests.
- Confirmed the repository is clean and aligned with `origin/main`.
- Found a Python 3.10 compatibility bug in `backend/app/evals/runner.py`.
- Replaced `datetime.UTC` with `timezone.utc`.
- Recorded BUG-0008 and changelog entry for the compatibility fix.

Verification:

- Ran backend tests with the backend venv; 23 tests passed after the fix.
- Ran frontend `npm run build`; build succeeded.

Open Questions:

- The next behavioral evidence should come from adaptive Memory v0 sessions rather than only scripted checks.
- Memory v0 still lacks inspection UI, update/forget/conflict semantics, and semantic retrieval.
- Visible metacognition needs adaptive evaluation to avoid becoming decorative or repetitive.

Next Suggested Step:

Run one or more adaptive Memory v0 evaluation sessions, then decide whether the next implementation slice should be a memory inspection panel, memory lifecycle semantics, or attention context.

## 2026-05-11 - Versioned Laboratory State Policy

Goal:

Make repository state match the current laboratory policy: everything except private keys and credentials can be committed, including the SQLite runtime database.

Changes:

- Updated `.gitignore` so `backend/data/app.db` is intentionally trackable.
- Documented the lab-state policy in `README.md`, `docs/project-blueprint.md`, and ADR-0015.
- Added an environment note for cross-machine SQLite continuity and merge-conflict risk.
- Prepared the current SQLite database snapshot for version control.

Verification:

- Confirmed `backend/.env` remains ignored.
- Confirmed `backend/data/app.db` contains tables for `sessions`, `messages`, `turns`, `traces`, `tool_calls`, and `memories`.
- Confirmed the actual `MINIMAX_API_KEY` value and common secret markers are not present in `backend/data/app.db`.

Open Questions:

- If the Windows machine has a richer SQLite state than this macOS snapshot, that database should replace the tracked snapshot in a later commit rather than being overwritten silently.
- A hosted or public release will need a different database and privacy policy.

Next Suggested Step:

Push the lab-state policy and DB snapshot, then decide whether the Windows database should replace the current tracked SQLite snapshot.

## 2026-05-11 - Direct Adaptive Memory v0 Verification

Goal:

Verify Scarlet's actual Memory v0 behavior through direct chat-stream turns rather than only scripted or deterministic scenarios.

Changes:

- Ran direct adaptive turns through `POST /api/chat/sessions/{session_id}/turn/stream`.
- Found and fixed a wrapper compatibility bug where MiniMax emitted `raw_input` and JSON-string `body` values that failed `MindAPIRequest` validation.
- Added wrapper normalization for `raw_input`, JSON-string bodies, and body-level `intent`.
- Added Italian compatibility aliases for `preferenza`, `alta`, `media`, and `bassa`.
- Added regression coverage for the real MiniMax-shaped wrapper/body behavior.
- Updated experiment and API documentation with the observed behavior.
- Updated the immediate roadmap toward Memory v0 lifecycle and search relevance work.

Verification:

- Ran backend tests with the backend venv; 24 tests passed.
- Restarted the backend on `http://127.0.0.1:8000`.
- Direct write turn `turn_01d1ead1b76a40ffa095c797da0e0c45` stored `mem_abed5590f91b4eb8aa93d1103db024de`.
- Cross-session recall turn `turn_839a89d5c37f4d84bbe63f6154fecda5` retrieved the stored memory with source attribution.
- Negative-control turn `turn_2c255fdb84184f0096b149d03680b012` did not invent `protocollo Mare-Vetro`, but search returned a weakly related Zero-Luce memory.
- Update/conflict turns `turn_c30ba6ba0b844286bcc8eb6c996e4013` and `turn_d0da056910824cd08a79773031ef2fa6` showed that v0 creates a new active memory instead of replacing the old one.
- Capability correction turn `turn_50098ed1f35742f4a9bc25361c404633` confirmed via schema that update/delete/deprecate routes are not implemented.

Open Questions:

- What should the exact lifecycle API be: update existing records, deprecate by status, or append revision records with active revision selection?
- Should memory search suppress weak lexical hits by threshold, return them as low-confidence candidates, or ask the model to classify relevance after retrieval?
- Should the frontend get a memory panel before or after lifecycle semantics?

Next Suggested Step:

Implement the smallest Memory v0 lifecycle slice: deprecate/replace an existing memory with traceable conflict handling, then add a search relevance guard.

## 2026-05-12 - Memory Context Pipeline v0 Design

Goal:

Move memory retrieval out of optional model discretion and formalize it as an automatic runtime context phase.

Changes:

- Added Memory Context Pipeline v0 to the project blueprint.
- Added ADR-0016 documenting automatic per-turn memory context as the accepted architecture.
- Added EXP-0008 for validating automatic memory context against optional model-driven search.
- Documented the planned internal `memory.context` trace and `<runtime_context>` shape in the API contract.
- Updated Scarlet's prompt with a runtime-context contract for backend-provided memory evidence and capability state.
- Updated the immediate roadmap to prioritize automatic memory evidence before additional memory lifecycle endpoints.
- Recorded BUG-0010 for the current optional-search memory evidence risk.

Verification:

- Documentation and prompt changes only; runtime implementation was not changed in this slice.
- Verified the design against the referenced RAG, SQLite FTS5, reranking, hybrid search, and rank-fusion source material.

Open Questions:

- What exact relevance thresholds should separate `selected`, `near_miss`, and `excluded` in the first lexical-only implementation?
- Should `memory.context` be stored only as traces at first, or also get a dedicated table after the trace shape stabilizes?
- How strict should the post-response validator be before it starts blocking or warning on unsupported memory claims?

Next Suggested Step:

Implement the smallest Memory Context Pipeline v0 slice: build `TurnFrame`, run automatic lexical retrieval on every turn, persist `memory.context`, inject selected runtime context before `llm.request`, and add regression tests for empty and weak-overlap cases.

## 2026-05-12 - Memory Context Pipeline v0 Implementation

Goal:

Implement the first automatic per-turn memory context slice before adding more memory endpoints.

Changes:

- Added `backend/app/mind/context.py`.
- Added `TurnFrame` construction from current user message, recent dialogue, session metadata, capability state, active scope, and time.
- Added automatic `memory.context` traces before `llm.request` for normal and streaming chat turns.
- Added backend-generated `<runtime_context>` injection into the effective system message sent to MiniMax.
- Added lexical v0 memory ranking with `selected`, `near_miss`, `excluded`, and simple conflict detection.
- Added streaming `memory_context` events.
- Updated the frontend inline operation timeline and trace reconstruction to show memory context.
- Added regression tests for empty memory context, selected relevant memory, weak-overlap exclusion, and streaming memory context.
- Updated API, experiment, bug, roadmap, and changelog documentation.

Verification:

- Ran backend tests with the backend venv: `26 passed`.
- Ran frontend build: `npm run build` succeeded.

Open Questions:

- Thresholds for `selected`, `near_miss`, and `excluded` need live adaptive evaluation.
- Retrieval is lexical v0 over active memory records; SQLite FTS5/BM25 remains the next scoring improvement.
- Post-response validation for unsupported memory claims is still pending.

Next Suggested Step:

Restart the local backend, run an adaptive cockpit session focused on Memory Context Pipeline v0, then tune lexical scoring or add SQLite FTS5/BM25 based on trace evidence.

## 2026-05-13 - Live Adaptive Memory Context Pipeline Evaluation

Goal:

Evaluate Scarlet's real behavior through streaming chat turns instead of scripted batteries, focusing on whether automatic memory context fixes skipped memory search and how Scarlet uses runtime conflicts and capabilities.

Changes:

- Restarted the local backend so the latest Memory Context Pipeline v0 code was active.
- Created live adaptive session `ses_5c32ff33daf041baaad36c18363dcfb2`.
- Ran four real streaming turns through `POST /api/chat/sessions/{session_id}/turn/stream`.
- Recorded the resulting sessions, messages, traces, and memory usage updates in the tracked laboratory SQLite database.
- Updated the experiment record, roadmap, changelog, and bug ledger with the observed behavior.

Verification:

- Backend health returned `{"status":"ok","app":"LLM API Mind","environment":"local","model":"MiniMax-M2.7"}` before the run.
- Mare-Vetro turn `turn_51d32fd9b9e3435cb8d6d853e7ccb7cb` produced `memory.context` trace `trace_6a2ec3dadeb940d59ab5a48f74a2cdb6` with `searched=true`, `selected_count=0`, and `negative_evidence=no_relevant_memory_selected`.
- Zero-Luce follow-up turn `turn_bd3fcf15e068497aa8c52a3c7e45b2e9` produced `memory.context` trace `trace_93e9dd421ae7400487f0fe76c4f8e181` with both Zero-Luce memories selected and a conflict detected.
- Conflict inspection turn `turn_cbd7c6e6b6a942afa554efb9a932d811` produced trace `trace_f0cd4e61aae84eedaa75babe22abe068`; Scarlet correctly described the 4-block and 3-block Zero-Luce versions when asked directly.
- Capability challenge turn `turn_ed16ce5b48124988bff5108aa3ef2b2c` confirmed Scarlet can read runtime capability state and correct herself when asked: `memory.update`, `memory.deprecate`, and `memory.delete` are unavailable.

Open Questions:

- Conflict disclosure needs to be surfaced proactively when `memory.context.conflicts` is non-empty.
- Capability state needs answer-level enforcement so Scarlet does not offer lifecycle actions that are unavailable.
- Retrieval scoring still needs SQLite FTS5/BM25, but this live run shows response control is the more immediate reliability gap.

Next Suggested Step:

Implement the smallest Memory Context Pipeline v0.1 response-control slice: make conflicts and unavailable capabilities operational answer constraints, then verify with the same Mare-Vetro/Zero-Luce live scenario before moving to FTS5/BM25 or lifecycle endpoints.
