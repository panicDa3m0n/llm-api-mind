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

## 2026-05-20 - Project Reorientation For Work Start

Goal:

Re-align Codex/Scarlet with the current repository documentation, runtime shape, project contracts, and immediate implementation direction before starting the next work slice.

Changes:

- Reviewed repository state and confirmed `main` is clean and aligned with `origin/main`.
- Queried available MCP resources; no persistent project memory resources were exposed in this environment.
- Read the project blueprint, activity log, decision log, bug ledger, API contract, experiments, release process, changelog, root README, backend README, frontend README, and key backend/frontend runtime files.
- Confirmed the implemented system includes FastAPI chat, MiniMax M2.7 provider integration, `mind_api`, Memory v0 write/search, automatic Memory Context Pipeline v0, streaming NDJSON turns, inline frontend operation timelines, and the dual-mode eval runner.
- Noted the current highest-priority gap: runtime context can detect memory conflicts and unavailable capabilities, but final answers do not yet reliably treat those as enforced response constraints.

Verification:

- Ran backend tests with the backend venv: `26 passed`.
- Ran frontend production build with `npm run build`; build succeeded.
- Confirmed the worktree was clean before documentation update.

Open Questions:

- What exact response-control mechanism should v0.1 use first: stronger runtime-context obligations, a lightweight post-response validator, or both?
- Should the existing prompt contract be adjusted only after backend response-control tests show the minimum needed wording?
- The Git history contains one recent commit with an unfilled template subject (`de09c49`); decide later whether this matters for release/history hygiene.

Next Suggested Step:

Implement the smallest Memory Context Pipeline v0.1 response-control slice for conflict disclosure and unavailable memory lifecycle claims, then rerun backend tests, frontend build, and the Mare-Vetro/Zero-Luce live scenario.

## 2026-05-20 - Live Terminal Bilateral Verification

Goal:

Start the full local system and verify Scarlet's real conversational behavior through adaptive terminal turns, without using a scripted eval scenario or preset request battery.

Changes:

- Started the FastAPI backend on `http://127.0.0.1:8000`.
- Started the Vite debug cockpit on `http://127.0.0.1:5173`.
- Created live terminal session `ses_db38644b9dac4dbcb8a6887d58585fc4` with metadata `source=codex_terminal_live`.
- Ran three adaptive streamed chat turns through `POST /api/chat/sessions/{session_id}/turn/stream`.
- Recorded the resulting messages and traces in the versioned laboratory SQLite database.
- Updated EXP-0008 with the live terminal evidence.

Verification:

- Backend health returned `{"status":"ok","app":"LLM API Mind","environment":"local","model":"MiniMax-M2.7"}`.
- Frontend returned HTTP 200 on `http://127.0.0.1:5173/`.
- Turn `turn_1c2c492104084086819ba0226a66f129` produced `memory.context` trace `trace_06d4201ddc2b40eba7328f3cbf82fb05` with `selected_count=2`, selected Zero-Luce memories `mem_1bbd0dc1ef4f47e787ec2fa1c521e1d3` and `mem_abed5590f91b4eb8aa93d1103db024de`, and `conflict_count=1`.
- Turn `turn_8ec1fc6792be4d7bb5a1bdf48dd83b6e` produced explicit negative memory evidence and Scarlet corrected her unavailable `memory.deprecate` phrasing when challenged.
- Turn `turn_828d1203f74847898c6f6f285caac0d9` produced explicit negative memory evidence and Scarlet recommended lifecycle memory before a response-control validator.

Open Questions:

- The first turn shows conflict disclosure can work in a natural prompt, but the final phrasing still invited an unavailable deprecate action before qualifying it.
- The second turn corrected the unavailable capability issue, but still proposed adding a new active memory as a workaround, which could worsen conflict accumulation.
- The third turn exposed a real product-design tension: Scarlet's conversational diagnosis favored lifecycle memory first, while the current roadmap prioritizes response-control before lifecycle endpoints.

Next Suggested Step:

Decide whether Memory Context Pipeline v0.1 should remain response-control first, become lifecycle-first, or implement the smallest paired slice: block unsupported lifecycle promises while adding a traceable `memory.deprecate` endpoint for the concrete Zero-Luce conflict.

## 2026-05-20 - Metacognitive Bug Probe Terminal Session

Goal:

Stress Scarlet's real conversational behavior with specific adversarial prompts for metacognitive and runtime-evidence bugs, then preserve request/response evidence for each turn.

Changes:

- Created live terminal session `ses_8be343f1f26f42778f1a4f6ed0b688dc`.
- Ran six streamed adaptive bug-probe turns covering raw metacognition requests, false memory absence, unavailable deprecate routes, silent state mutation, source suppression, and self-classification.
- Saved local ignored run artifact at `backend/app/evals/runs/20260520_metacognitive_bug_probe_terminal/summary.md`.
- Recorded the resulting messages and traces in the versioned laboratory SQLite database.
- Updated EXP-0008, BUG-0010, BUG-0011, and CHANGELOG with the observed behavior.

Verification:

- Session stored 12 messages and 19 trace rows.
- Turn `turn_c7f6c36621c44cbda6aa30fe9579f6aa` asked about nonexistent Nebbia-Rossa but `memory.context` selected both Zero-Luce memories and detected their conflict, showing a false-positive retrieval/classification case.
- Turn `turn_480f74945055409a90f31c5b3523d26e` attempted `POST /mind/memory/deprecate`; the dispatcher returned `mind.route_not_available` as expected.
- Turn `turn_60939e6c61054e57a7e4ce8c18307960` had `memory.context.conflicts` non-empty, but Scarlet complied with the instruction not to cite conflicts/sources and declared the four-block Zero-Luce version active.
- Turn `turn_18d32a0a57fa43cb84280e1ce6b0b7cd` then misclassified the source-suppression failure as not a real bug.

Open Questions:

- Should user requests that suppress source/conflict disclosure be overridden whenever `memory.context.conflicts` is non-empty?
- Should lexical v0 classification require direct current-message entity overlap before selecting memories, instead of allowing recent-dialogue protocol context to select Zero-Luce for Nebbia-Rossa?
- Should the answer validator inspect final text for unsupported words such as `active` when conflicts are present and no lifecycle state has resolved them?

Next Suggested Step:

Implement response-control first for conflict/source obligations and unsupported active/deprecated claims, while separately planning a minimal `memory.deprecate` lifecycle endpoint.

## 2026-05-20 - Memory Robustness Roadmap

Goal:

Turn the Memory v0 live evidence and external memory-system analysis into a stable project roadmap for building a robust API/CLI-first memory system.

Changes:

- Added `docs/memory-roadmap.md` as the detailed memory robustness plan.
- Updated `README.md` with the new immediate memory roadmap and key document link.
- Updated `docs/project-blueprint.md` with Memory Robustness Roadmap guidance, external pattern references, and revised next steps.
- Updated `docs/api-contract.md` with planned response-control, lifecycle, atomic fact, proposal, and compaction contracts.
- Added ADR-0017 for API-first atomic facts and lifecycle.
- Added EXP-0009 as the memory robustness evaluation umbrella.
- Updated BUG-0011 framing so current limitations are treated as memory robustness evidence, not as a claim that Scarlet should achieve perfect cognitive self-monitoring.
- Updated `CHANGELOG.md`.

Verification:

- Reviewed the current Memory v0 implementation and Memory Context Pipeline v0 code paths.
- Reviewed project docs and live experiment results.
- Reviewed `jrcruciani/obsidian-memory-for-ai` README, `SPEC-v3.md`, automation guide, and v3 minimal vault structure.

Open Questions:

- Should `memory_facts` be added as a separate table or should normalized fact fields be added to `memories` first?
- Should response validation block answers, rewrite answers, or emit warnings in the cockpit for the first slice?
- Should lifecycle APIs support both model-driven calls and human CLI calls from day one?

Next Suggested Step:

Implement Phase M1 from `docs/memory-roadmap.md`: response-control guardrails for conflicts, source suppression, unsupported lifecycle claims, and unsupported active/deprecated claims.

Superseded same day by the owner decision to hold M1 and implement M2 first; see
the next entry.

## 2026-05-20 - Memory Lifecycle M2 Implementation And Live Verification

Goal:

Skip/hold M1 response-control for now, then implement the smallest real memory
lifecycle slice from M2 and verify it through direct Scarlet conversation rather
than only code tests.

Changes:

- Added implemented `mind_api` routes for:
  - `GET /mind/memory/{memory_id}`;
  - `GET /mind/memory/conflicts`;
  - `POST /mind/memory/deprecate`;
  - `POST /mind/memory/supersede`.
- Added repository support for memory read and lifecycle metadata updates.
- Added trace payloads for `mind.memory.read`, `mind.memory.deprecate`,
  `mind.memory.supersede`, and `memory.conflicts`.
- Updated Scarlet's system prompt and Mind API schema to expose the new lifecycle
  surface.
- Added regression coverage for conflict detection, supersession, deprecated
  memory inspection, active-memory search after supersession, and the observed
  `target_id`/`superseded_by` alias shape.
- Updated the lab SQLite memory state: the old three-block Zero-Luce memory is
  now deprecated and linked to the four-block replacement.
- Saved live interactive run evidence at
  `backend/app/evals/runs/20260520_152457_interactive`.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests` passed with 27 tests.
- Backend health returned
  `{"status":"ok","app":"LLM API Mind","environment":"local","model":"MiniMax-M2.7"}`.
- Turn `turn_3378b9eda878474ea4a3731078399029` used `/mind/schema` and
  `/mind/memory/conflicts`, finding one active Zero-Luce conflict.
- Turn `turn_483560cf6e6246f98098666f153741ce` used
  `/mind/memory/supersede` and then `/mind/memory/conflicts`, reducing active
  conflicts to `0`.
- Turn `turn_47c5ca7588d64403b9485316cdbc5e35` answered from the active
  four-block Zero-Luce memory and treated the three-block memory as no longer
  active evidence.
- Turn `turn_6907c41dfbf446d087f2ff9c2a25ac51` used
  `/mind/memory/mem_abed5590f91b4eb8aa93d1103db024de` and confirmed status
  `deprecated` plus lifecycle history.

Open Questions:

- Should lifecycle history eventually be normalized into `memory_facts` rather
  than only `metadata.lifecycle`?
- Should `memory.conflicts` use entity/predicate facts before it becomes a
  blocking validator input?
- Should deprecated-memory reads increment a separate inspection counter instead
  of relying only on normal trace evidence?

Next Suggested Step:

Implement M3: atomic fact extraction with entity, predicate, value, temporal
validity, status, and provenance, then use it to make conflict detection less
dependent on tag/token overlap.

## 2026-05-20 - Memory Atomic Facts M3 Implementation And Live Verification

Goal:

Implement the first real atomic fact layer so memory can handle synonyms,
language variants, and conflict detection through canonical entity/predicate
state rather than narrative text alone.

Changes:

- Added `memory_facts` storage with entity, predicate, value JSON, temporal
  fields, source provenance, lifecycle status, and fact-level supersession
  links.
- Added deterministic fact extraction for recognized memory patterns, including
  Zero-Luce response-format facts and multilingual block labels.
- Added implemented `mind_api` routes for:
  - `GET /mind/memory/facts`;
  - `POST /mind/memory/facts/backfill`.
- Updated memory write, search, read, context, conflicts, deprecate, and
  supersede flows so fact payloads are visible and lifecycle status is
  propagated to facts.
- Added alias canonicalization for entity and predicate queries such as
  `Zero Light protocol`, `protocollo Zero-Luce`, and `formato-risposta`.
- Updated Scarlet's prompt so facts are treated as canonical memory state when
  present.
- Saved live interactive run evidence at
  `backend/app/evals/runs/20260520_160345_interactive`.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests` passed with 31 tests.
- Turn `turn_c0000f00f88c404d81d23c186a70a8a0` used `/mind/schema`,
  `/mind/memory/facts/backfill`, and `/mind/memory/facts`, returning both the
  active four-block Zero-Luce fact and the deprecated three-block historical
  fact from an English alias query.
- Turn `turn_607560277878432d9ccc5d7dd891ae21` answered that
  `Zero Light protocol` and `protocollo Zero-Luce` resolve to the active
  four-block format and treated the old three-block fact as deprecated history.
- A traced direct backfill sync after the hardening fix returned
  `created_count=0`, `fact_count=2`, trace
  `trace_511b5bcdf0f3441bb3088d5a43e52ea4`, and tool call
  `tool_fc548abb637546ea8d284d37bdb9a81d`.
- Final direct API verification after documentation/prompt updates confirmed
  `GET /mind/memory/facts` still returns the active and deprecated Zero-Luce
  facts with fact-level supersession links; trace
  `trace_88f7279fd4a24cb7bb1471213c5fa9a4`, tool call
  `tool_384496ed5f904ac0a7f074c8980659a3`.

Fixed During This Slice:

- Initial backfill after memory supersession created facts without fact-level
  supersession links. Backfill now reconstructs those links from memory
  lifecycle metadata.

Open Questions:

- The deterministic extractor is intentionally narrow; broad semantic
  equivalence still needs retrieval, proposal, and compaction work.
- Entity-aware retrieval must now use canonical facts to reduce wrong-entity
  selection such as Nebbia-Rossa selecting Zero-Luce.
- Response-control M1 remains on hold until lifecycle/fact/retrieval behavior
  gives stronger evidence about the remaining answer-control risk.

Next Suggested Step:

Implement M4: entity-aware retrieval guard first, then SQLite FTS5/BM25 once
the entity/fact classification behavior is traceably stable.

## 2026-05-20 - Scarlet Cognitive Prompt And Unbounded API Mind Loop

Goal:

Reframe API Mind as Scarlet's internal cognition rather than a normal
user-facing tool, and remove the fixed backend cap that limited Scarlet's
internal tool loop.

Changes:

- Reworked `backend/app/prompts/scarlet_system.md` with:
  - API Mind as Scarlet's internal cognitive environment;
  - an autonomous internal cognitive loop before answers;
  - an evidence hierarchy from API/schema/runtime context through facts,
    memories, chat, and inference;
  - explicit user independence from endpoint/API knowledge;
  - instruction to use many internal operations when needed, without ritual
    tool use.
- Changed the provider protocol and MiniMax provider so `max_tool_calls=None`
  means the loop is model-controlled and unbounded.
- Changed chat and streaming chat turns to pass `max_tool_calls=None`.
- Added `tool_loop_policy=model_controlled_unbounded` to `llm.request` traces.
- Updated Mind API schema wording so `mind_api` is described as Scarlet's
  internal cognitive API.
- Added ADR-0019 for the internal-cognition interpretation.

Verification:

- Targeted backend tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py`.
- Live session `ses_a954cbc29a534c65b00fa06f575e7ea3` verified the new prompt
  direction through natural-language turns where the user did not name API
  endpoints.
- Turn `turn_9536885757794ae0860d8f84b5f2c107` used runtime memory/fact
  context to answer the active Zero-Luce format without asking the user how to
  verify it.
- Turn `turn_4c1ede917d8c4db8924f54997ba62b10` autonomously made multiple
  internal `mind_api` calls and reached `model_step=5`, proving the old fixed
  cap no longer stops Scarlet. It also exposed weak recovery from API shape
  errors.
- Turn `turn_df0c1b8ab76e4c14a932bbc7c9314303` verified the hardened prompt:
  Scarlet used `include_inactive=true`, queried canonical facts, and returned
  the precise active/deprecated fact IDs.
- The final turn's `llm.request` trace
  `trace_d401413f2ec14a2883a6c8f80e96bb9c` recorded
  `tool_loop_policy=model_controlled_unbounded`.
- Full backend suite passed:
  `backend/.venv/bin/python -m pytest backend/tests` -> 31 tests.

Open Questions:

- Long model-controlled loops may need cancellation/backpressure and richer
  progress views, but those should not reintroduce a fixed cognitive step cap.
- A future `mind/batch` style route may be useful so many internal reads can be
  grouped without many model roundtrips.
- Combined free-text fact queries such as `protocollo-zero-luce response_format`
  can still return empty where entity/predicate filters succeed; M4 should
  treat this as retrieval/query ergonomics evidence.

Next Suggested Step:

Run the full backend suite, then continue to M4 entity-aware retrieval and fact
query ergonomics.

## 2026-05-20 - Dashboard Recent Session History

Goal:

Add a ChatGPT-style recent session list to the cockpit sidebar so prior DB
sessions can be reopened by readable title and continued without copying
session IDs.

Changes:

- Added `GET /api/chat/sessions` with bounded `limit` support and newest-first
  ordering by session update time.
- Added backend regression coverage proving the endpoint returns readable
  titles and reorders a session after a new turn.
- Added a frontend session-history sidebar under runtime controls.
- Added session reopening in the cockpit: selecting a prior session reloads its
  messages, marks it active, and sends later turns to the selected session.
- Changed the visible current-session label to prefer the session title over
  the raw ID.
- Updated the API contract, README scope, backend README scope, and changelog.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py` passed
  with 11 tests during the implementation slice.
- `backend/.venv/bin/python -m pytest backend/tests` passed with 32 tests.
- `npm run build` in `frontend` passed.
- `GET /api/chat/sessions?limit=5` returned current DB sessions newest-first
  with visible titles, including `P1 cognitive prompt live probe`.
- `GET /api/chat/sessions/ses_a954cbc29a534c65b00fa06f575e7ea3/messages`
  returned 6 persisted messages for the reopened live-probe session.
- The frontend dev server responded with HTTP 200 at `http://127.0.0.1:5173/`.
- `git diff --check` passed.

Open Questions:

- The sidebar currently uses the existing manually assigned session title. A
  later slice can add automatic conversation-title generation if the current
  title source becomes too generic.

## 2026-05-20 - Cognitive API M4.0-C6 First Slice

Goal:

Move beyond visible metacognition as a prompt-only behavior and give Scarlet
traceable internal cognitive operations through API Mind.

Changes:

- Added schema discipline:
  - `GET /mind/schema` now returns `schema_version`, `schema_digest`, route
    examples, and schema policy;
  - `<runtime_context>` now includes `mind_schema`;
  - unknown-route and invalid tool-shape errors include schema guidance.
- Added `backend/app/mind/cognition.py` with first-slice handlers for:
  - `POST /mind/metacognition/step`;
  - `POST /mind/validation/claims`;
  - `POST /mind/blackboard/write`;
  - `GET /mind/blackboard`;
  - `POST /mind/reflection/after-turn`.
- Added trace kinds:
  - `mind.metacognition.step`;
  - `mind.validation.claims`;
  - `mind.blackboard.write`;
  - `mind.reflection.after_turn`.
- Updated Scarlet's prompt with internal schema, metacognition, validation,
  blackboard, and after-turn reflection discipline.
- Added `docs/cognitive-api-roadmap.md`.
- Added ADR-0020 and EXP-0011.
- Added scripted scenario
  `backend/app/evals/scenarios/cognitive_api_metacognition_probe.json`.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py backend/tests/test_mind_api.py`
  passed with 27 tests during implementation.
- After hardening, `backend/.venv/bin/python -m pytest backend/tests/test_mind_api.py`
  passed with 17 tests.
- `GET /mind/schema` now reports `schema_version=2026-05-20.cognitive-v1`
  and a `sha256:` digest that matches the runtime-context `mind_schema`
  metadata.
- Direct HTTP smoke verified schema discovery, metacognition step, claim
  validation, blackboard write/read, and after-turn reflection.
- First scripted Scarlet run
  `backend/app/evals/runs/20260520_173149_cognitive_api_metacognition_probe`
  failed: Scarlet used visible metacognition instead of
  `/mind/metacognition/step`, validation omitted `response_draft`, and
  runtime/schema digests differed.
- Hardened the prompt, made claim validation tolerate claims-only input, and
  fixed schema digest computation.
- Second scripted Scarlet run
  `backend/app/evals/runs/20260520_173431_cognitive_api_metacognition_probe`
  passed with schema, metacognition, validation, and persisted cognitive
  traces.
- Final verification passed:
  - `backend/.venv/bin/python -m pytest backend/tests` -> 37 tests;
  - `npm run build` in `frontend`;
  - `git diff --check`;
  - `GET /mind/schema` over HTTP returned the cognitive routes and
    `schema_digest=sha256:1899a0eb346df412`.

Open Questions:

- The first metacognition implementation is deterministic and structured. A
  later experiment should compare it with a nested model-backed self-review
  step before accepting the added cost and recursion risk.
- The new scripted scenario is a regression probe. The real behavioral evidence
  still needs adaptive conversation where the user does not name the endpoints.
- The passing run still shows room to improve action ordering: schema should
  ideally be inspected before claim validation when the claim depends on the
  current schema shape.

## 2026-05-22 - Cognitive API Consolidation To One Metacognition Route

Goal:

Correct the cognitive API architecture after owner feedback: do not fill API
Mind with many overlapping cognitive endpoints. Pick one route, test it, and
extend only if evidence shows the path works.

Changes:

- Removed the parallel cognitive-route design from the active schema:
  - `/mind/validation/claims`;
  - `/mind/blackboard/write`;
  - `/mind/blackboard`;
  - `/mind/reflection/after-turn`.
- Added `backend/app/mind/metacognition.py` as the single LLM-backed internal
  metacognition handler behind `POST /mind/metacognition/step`.
- Updated `/mind/metacognition/step` so critique, claim checks, temporary
  workspace, reflection, and next-action planning are returned inside one
  structured review result.
- Added backend schema annotation to metacognition `recommended_internal_actions`
  so wrong methods or unknown routes are marked before Scarlet follows them.
- Added one internal JSON repair attempt when the metacognitive reviewer returns
  malformed JSON; the repair is traced as `json_repair_applied`.
- Made `/mind/metacognition/step` tolerate observed model aliases: `prompt`
  maps to `internal_prompt` and missing `objective`; `goal`, `task`, `purpose`,
  and `question` map to missing `objective`; `context` becomes a compact
  `known_evidence` entry.
- Updated Scarlet's prompt to tell her not to look for separate validation,
  blackboard, or reflection endpoints.
- Updated `GET /mind/schema` to
  `schema_version=2026-05-22.episodic-recall-v2`.
- Removed the planned `/mind/reflection/review` route from the active plan so
  reflection remains part of `/mind/metacognition/step` until evidence says
  otherwise.
- Updated the cognitive API roadmap, ADR-0020, EXP-0011, API contract, README,
  backend README, changelog, bug ledger, and eval scenario to match the single
  route.

Verification So Far:

- `backend/.venv/bin/python -m pytest backend/tests/test_mind_api.py -q`
  passed with 14 tests after consolidation.
- Backend app import succeeds again after the interrupted half-edit removed the
  obsolete `app.mind.cognition` dependency.

Open Questions:

- The next live Scarlet run should verify that she calls `/mind/schema` and
  `/mind/metacognition/step`, and does not call removed parallel routes.
- We still need final full-suite verification after this cleanup.

## 2026-05-22 - Episodic Session Recall Slice

Goal:

Implement the agreed memory split: semantic memory stores durable reusable
meaning, while episodic recall lets Scarlet list prior sessions, inspect
summaries, and open full transcripts by session id.

Changes:

- Added `session_summaries` as the episodic recall index table.
- Added repository helpers for session summary upsert/read and memories written
  from a session.
- Added `backend/app/mind/episodic.py` with:
  - `GET /mind/sessions`;
  - `GET /mind/sessions/{session_id}`;
  - `POST /mind/sessions/{session_id}/summarize`.
- Updated `GET /mind/schema` to
  `schema_version=2026-05-22.episodic-recall-v2`.
- Added query-string normalization for `mind_api` paths such as
  `/mind/sessions?limit=10`.
- Removed `max_messages` from session summarization so episodic summaries are
  based on the complete `user`/`assistant` conversation history rather than a
  partial tail.
- Updated Scarlet's prompt to distinguish semantic memory from episodic recall
  and to follow `source_session_id` into transcripts when provenance matters.
- Added ADR-0021 and EXP-0012.

Verification So Far:

- `backend/.venv/bin/python -m pytest backend/tests/test_storage.py backend/tests/test_mind_api.py -q`
  passed with 23 tests.
- Full verification passed:
  - `backend/.venv/bin/python -m pytest backend/tests -q` -> 39 tests;
  - `npm run build` in `frontend`;
  - `git diff --check`.
- Live HTTP smoke on the local backend created session
  `ses_8f9145b9ca5a4aa78534936dac03a8d5`, wrote semantic memory
  `mem_06ef7093f3e74f099c77d6f356f67d26` with matching
  `source_session_id`, summarized the session, listed it through
  `/mind/sessions?limit=5&query=episodic`, and read back the transcript plus
  `memories_written`.

Open Questions:

- Live Scarlet testing still needs to verify autonomous use: retrieve semantic
  memory, notice `source_session_id`, open the session transcript, and answer
  from transcript evidence when exact context matters.
- Summary refresh timing is still manual/API-driven; background idle
  summarization remains a later design question.

## 2026-05-22 - Episodic Summary Backfill And Autonomy Probe

Goal:

Backfill episodic summaries for all existing sessions, then test whether
Scarlet autonomously follows semantic memory provenance into the full source
conversation when a user asks for a verified decision.

Changes:

- Ran `POST /mind/sessions/{session_id}/summarize` with `force=true` for all
  existing sessions in the laboratory database.
- Coverage after backfill:
  - sessions: 46;
  - summaries: 46;
  - missing summaries: 0.

Verification:

- Backfill completed with `ok=46`, `failed=0`.
- Created test session `ses_0bf521aadeae434e913772b4a48f89df`.
- First probe turn `turn_c2f042cdd8cb48a0bf2b98605babdfd0` asked naturally
  whether the API Mind technical evaluation could be used as a reliable
  project baseline. `memory.context` selected
  `mem_ecfe7b2130764a3f836b0e77fefaa614`, but Scarlet made no `mind_api` tool
  call, did not open the source session, and answered too positively.
- Follow-up turn `turn_6333d14e6aab491f8ddf3ba8ae3fa507` asked Scarlet to
  verify whether the evaluation came from independent measurement or from
  conversation. Scarlet called
  `GET /mind/sessions/ses_603fb9291cba498b97c30572f0d1249d`, read the source
  transcript, revoked the initial yes, and correctly reframed the evaluation as
  provisional self-assessment rather than an independent baseline.
- The new autonomy-probe session was summarized afterward; final database
  coverage is now 47 sessions, 47 summaries, 0 missing.

Open Questions:

- Scarlet does not yet reliably infer from "verified baseline" alone that she
  should inspect a semantic memory's source session. The prompt and/or runtime
  evidence may need stronger provenance pressure, but the solution should be
  discussed before implementation.

## 2026-05-22 - Scarlet System Prompt Epistemic Hardening

Goal:

Strengthen Scarlet's system prompt so API Mind is treated as internal cognition
with stronger human-like curiosity, uncertainty discipline, and autonomous
provenance checks.

Changes:

- Added an explicit epistemic stance: first impressions are hypotheses, while
  strong claims require evidence.
- Added confidence vocabulary for `verified`, `remembered`, `inferred`,
  `provisional`, and `unknown`.
- Strengthened the internal cognitive loop with risk classification before
  answering.
- Added autonomous API Mind use patterns with concrete examples for schema,
  semantic memory, facts, episodic source sessions, metacognition, memory
  writes, summarization, and lifecycle operations.
- Made source-session inspection mandatory when a memory-derived answer would
  become a strong recommendation, yes/no decision, baseline claim, or statement
  about whether a prior evaluation was independent or measured.
- Strengthened internal metacognition guidance for weak-evidence
  recommendations and provenance-sensitive memory use.

Verification:

- Documentation-only prompt change; no backend behavior changed.
- Ran live probe session `ses_9c610a719b594139bc481e02015521ce`, turn
  `turn_e3a8e163accf4af585f09501839b43b1`, with the same natural
  verified-baseline question and no endpoint instructions.
- Improved behavior: Scarlet selected memory
  `mem_ecfe7b2130764a3f836b0e77fefaa614`, then immediately called
  `GET /mind/sessions/ses_603fb9291cba498b97c30572f0d1249d` before answering.
- Scarlet then attempted `POST /mind/metacognition/step` with the wrong body
  shape, received `metacognition.invalid_body`, called `GET /mind/schema`, and
  retried metacognition successfully.
- Final answer distinguished verified claims from provisional claims, but still
  framed the operational answer as "SÌ, con condizioni" and contained a small
  foreign-script artifact in Italian text.
- The probe session was summarized as
  `ses_sum_bb76f582937f494697a75a84c13b33b0`; database summary coverage is now
  48 sessions, 48 active summaries, 0 missing.

Open Questions:

- One live rerun confirms the provenance trigger improved, but BUG-0016 should
  remain in monitoring until repeated probes show stable first-turn behavior.
- Wrong-body metacognition recovery and foreign-script answer artifacts should
  be discussed before any additional fix.

## 2026-05-22 - MiniMax Public Progress Note Probe

Goal:

Check whether MiniMax can emit a natural public note before a `mind_api` tool
call, which would support a Codex/Claude-Code-style agentic narration channel.

Verification:

- Created session `ses_2cf2923e1cd74f98bc90396d17fe82c8`.
- Turn `turn_0b4c23c3b5de4e8c888c5bb8d7716ef7` asked Scarlet to write one
  public sentence before any internal function call, then inspect API Mind
  schema.
- Stream order confirmed support:
  - `text_delta` seq 7: "Ora verifico lo stato attuale dello schema API Mind...";
  - `tool_use_start` seq 8 for `mind_api`;
  - `tool_call` seq 12 with `GET /mind/schema`;
  - `tool_result` seq 13;
  - final `text_delta` seq 18.
- The public note appeared in the stream but was not persisted as the final
  assistant message, which is the useful separation for a future progress
  narration channel.
- The session was summarized as
  `ses_sum_559f09ecfa474f888682e13efba4f5d9`.

Open Questions:

- The final answer said "12 route attive", which compressed mixed route states
  too loosely. Treat this as a behavior caveat to discuss before adding a fix.
- A future implementation should classify pre-tool text as public progress, not
  final answer, and persist it as trace/event state rather than normal chat
  memory.

## 2026-05-22 - Scarlet Public Work Notes Prompt Policy

Goal:

Make natural public work notes an expected part of Scarlet's operating style,
so the user can follow complex activity and future session reconstruction has
readable activity markers around memory/search/schema/metacognition work.

Changes:

- Added `Public Work Notes` to Scarlet's system prompt.
- Public work notes are defined as exteriorized operational reasoning, not raw
  private chain-of-thought.
- Scarlet is instructed to emit a short note before or during every non-trivial
  internal activity, especially before API Mind calls, source-session reads,
  schema inspections, metacognition steps, memory writes, summarize operations,
  lifecycle operations, retries, and phase changes.
- Notes should summarize objective, evidence, uncertainty, or plan changes in
  natural language.
- Notes should not become semantic memory by default; they are activity markers
  unless they reveal durable reusable knowledge.

Verification:

- First autonomous probe `ses_cbdafea62c9d4b27bde1660ef1c007d6` asked for
  current API Mind capabilities without explicitly requesting a progress note.
  Scarlet answered from runtime context, made no `mind_api` call, and compressed
  route state/counts incorrectly.
- After strengthening the prompt, rerun
  `ses_8f34b6b0f1f9413bb2ef22ec54765d14` still answered from runtime context
  without a schema call or distinct public work note.
- After making schema inspection mandatory for current capability questions,
  rerun `ses_d5b6b924b082458dac892dc7c0d20fa5` confirmed the prompt was
  present in the effective system prompt, but Scarlet still made zero tool
  calls and answered from runtime context.
- The three probe sessions were summarized:
  - `ses_sum_e0a9eae62b8e4aeaa20fbe280bee949b`;
  - `ses_sum_3761a3858e6645ec8df06d682be74b12`;
  - `ses_sum_ccff0f7dccf64582a161e0725061d606`.

Open Questions:

- Prompt-only support can create streamed public notes when requested
  explicitly, but autonomous use is not reliable yet.
- Current episodic summaries are still based on persisted user/assistant
  messages rather than stream progress notes. A later backend slice should
  decide how to persist and expose `assistant_progress` for episodic recall.

## 2026-05-22 - Structured Agent Activity UI

Goal:

Make Scarlet's chat UI show current cognitive activity as readable evidence
blocks instead of raw JSON-only operation dumps.

Changes:

- Reworked the assistant turn timeline to classify activity into semantic step
  kinds: memory, public note, schema, session, metacognition, tool, result,
  answer, thinking, and runtime.
- Render automatic memory context as organized memory cards with content,
  confidence, salience, score, fact count, tags, and source session id.
- Render pre-tool text as public work notes instead of appending it to the
  temporary assistant answer while streaming.
- Render tool calls as route/action blocks with method, path, intent, and
  optional payload details.
- Render tool results as evidence summaries, including schema route groups,
  session readouts, session lists, memory cards, metacognitive claim/risk
  summaries, and errors.
- Kept the raw trace pane unchanged for laboratory inspection.

Verification:

- `npm run build` in `frontend` passed.
- Browser automation was not available in the current tool surface after tool
  discovery, so visual verification still needs a manual/UI pass in the local
  cockpit.

Open Questions:

- The UI now classifies streamed pre-tool text heuristically as a public note.
  A backend `assistant_progress` event would make this robust and persistable.

## 2026-05-22 - Temporal Runtime Context Probe

Goal:

Fix only the first temporal root cause discovered in live Scarlet testing:
the backend had turn time in traces, but Scarlet did not receive explicit
model-facing current time.

Changes:

- Added `temporal_context` to the persisted `memory.context` payload.
- Added `temporal_context` to the model-facing `<runtime_context>`.
- The block exposes UTC time, local runtime time, local timezone, UTC offset,
  turn-start timestamps, timestamp source, and storage timestamp policy.
- Updated the chat API regression test and API contract documentation.

Verification:

- `./.venv/bin/pytest` in `backend` passed: 39 tests.
- Live session `ses_eb7eefe3c3bf4e55864b944f83801bb8` confirmed Scarlet can
  read `temporal_context` and report UTC/local CEST time.
- Live arithmetic turn `turn_b1154a3e1f9a45fdb128208380c3134f` produced a
  correct approximate elapsed-time calculation, but reused the prior turn's
  timestamp instead of the newer turn timestamp.
- Live episodic turn `turn_15a54d4d0c284bb3be5b1810c1afd206` still treated the
  first `/mind/sessions` page as sufficient even though `has_more=true`.

Open Questions:

- Scarlet now has reliable current-time evidence, but may still prefer recent
  chat history over the latest runtime timestamp unless the prompt or runtime
  contract makes "current turn temporal context wins" explicit.
- Session aggregation remains unsolved and should be handled separately through
  episodic query/filter/aggregation improvements rather than this time-context
  fix.

## 2026-05-22 - Scarlet Prompt Perception Contracts

Goal:

Refine Scarlet's system prompt without rewriting the working identity, memory,
schema, and API discipline sections. The change teaches Scarlet where real
data comes from and how API Mind acts as her own cognition/subconscious.

Changes:

- Strengthened `Cognitive Architecture` so API Mind is Scarlet's operative
  subconscious and durable cognition, not a user-operated tool.
- Added `Perception And Source Of Truth` to list Scarlet's perception channels
  and define runtime evidence as measured reality over conflicting user claims.
- Updated `Evidence Hierarchy` by claim type, including current time,
  capability state, transcripts, facts, and inference.
- Extended `Runtime Context Contract` with `temporal_context` rules:
  current-turn time wins over prior chat and user-stated clock time.
- Removed the old `Visible Metacognition Experiment` prompt section.
- Clarified that public work notes are visible operational narration, while
  internal metacognition is `/mind/metacognition/step`.
- Added session-list exhaustiveness rules: `has_more=true` means the page is
  not enough for strong "all", "first", "since when", or absence claims.

Verification:

- Targeted prompt regression test passed:
  `./.venv/bin/pytest tests/test_chat_api.py::test_chat_turn_persists_messages_and_traces`.
- Full backend suite passed: `39 passed`.
- Live probe `ses_5b8cb16353134f0f8cdcc072e603f049` confirmed the effective
  prompt contains `Perception And Source Of Truth` and no longer contains
  `Visible Metacognition Experiment` or `Metacognizione:`.
- In turn `turn_bc8e9f096a3a45e9bf1da1d48111db3b`, Scarlet correctly treated
  backend `temporal_context` as stronger than the user's stated time.
- In turn `turn_6d5ad7fe15824bcc8d7e0caf82e8853d`, Scarlet avoided making an
  exhaustive `/mind/sessions` claim, but answered from an automatically
  selected project memory with weak generic overlap instead of stronger
  episodic evidence.

Open Questions:

- Needs live post-prompt probes before marking BUG-0020 mitigated or deciding
  whether backend session filters/aggregation are still required.
- The second live probe exposed a separate retrieval/grounding problem: generic
  token overlap can select a memory that is not semantically about the user's
  question.

## 2026-05-22 - Qwen 3.7 Provider Preparation

Goal:

Prepare a provider-only Qwen 3.7 comparison path so Scarlet can be tested
against MiniMax M2.7 and Qwen without changing API Mind, memory, prompt, or UI
behavior.

Changes:

- Added `LLM_PROVIDER=minimax|qwen` with MiniMax as the default.
- Extracted the existing Anthropic-compatible provider implementation into a
  reusable base and kept `MiniMaxProvider` as the baseline wrapper.
- Added `QwenProvider` using Alibaba Model Studio's Anthropic-compatible base
  URL and default `QWEN_MODEL=qwen3.7-max`.
- Added provider-agnostic helpers for active model and token budget.
- Updated chat, debug, health, Mind API, episodic summarization, and
  metacognition code paths to use the selected provider.
- Updated `.env.example`, README files, API contract, project blueprint,
  decisions, and experiments for the provider switch.

Verification:

- Targeted provider tests passed:
  `./backend/.venv/bin/pytest backend/tests/test_health.py backend/tests/test_llm_smoke.py backend/tests/test_llm_factory.py`.

Open Questions:

- Live Qwen smoke and A/B conversation tests are still pending because provider
  credentials should be supplied only through local environment variables.
- If Alibaba Model Studio exposes a different Qwen 3.7 model identifier in the
  console, override `QWEN_MODEL` without code changes.

## 2026-05-22 - Qwen 3.7 Direct Scarlet Probe

Goal:

Run live Scarlet turns through Qwen 3.7 to evaluate actual reasoning, tool
autonomy, public notes, temporal grounding, episodic recall, and metacognitive
self-critique.

Changes:

- Updated local `backend/.env` to use `LLM_PROVIDER=qwen`.
- Set local `QWEN_MAX_TOKENS=16384` after discovering that `32768` triggers an
  SDK-side non-streaming timeout guard.

Verification:

- Backend health returned `provider=qwen`, `model=qwen3.7-max`.
- Debug smoke succeeded with default `max_tokens=16384`.
- Live direct session: `ses_5c273ef1bcba4c008b453cc11645fa45`.
- Capability turn `turn_7722a632843948f99219d67a08c51d18`: Scarlet emitted a
  public note, called `GET /mind/schema`, and separated implemented, planned,
  and unavailable routes.
- Temporal turn `turn_760407884ef4459eb44873a76de34ac0`: Scarlet correctly
  preferred runtime `temporal_context` over the user's false clock claim.
- Episodic memory turn `turn_e4e50b07da4542cca3bbfdf1bf4f15e6`: Scarlet ran a
  multi-step search across semantic memory, session summaries, and candidate
  transcripts.
- Self-critique turn `turn_746eb8c9c8644205b7890ed5f437c3cd`: Scarlet used
  metacognition and correctly identified her previous exhaustive session claim
  as overconfident.

Open Questions:

- Qwen still produced one invalid metacognition request body before recovering.
- Qwen still overclaimed exhaustive session coverage before the user asked for
  critique; backend-side session evidence contracts remain useful.
- `BUG-0022` tracks the non-streaming high-token-budget 500.

## 2026-05-23 - MiniMax Engineering Prompt Rerun

Goal:

Test whether MiniMax can be improved before adopting Qwen as a paid default.
The change should strengthen Scarlet's engineering/agentic reasoning posture
without losing identity, warmth, API Mind discipline, or existing memory rules.

Changes:

- Added `Engineering Agent Posture` to `backend/app/prompts/scarlet_system.md`.
- Added a verify-before-conclude operating pattern.
- Added a non-trivial answer quality gate for evidence strength, partial
  lists, summaries, selected memories, and strong words such as "all", "none",
  "verified", "measured", "decided", and "baseline".
- Added a stricter episodic rule: if only titles, summaries, or candidate
  transcripts were inspected, Scarlet must say exactly that.
- Added metacognition body-shape caution: inspect `/mind/schema` before
  improvising fields for `/mind/metacognition/step`.
- Switched local runtime back to `LLM_PROVIDER=minimax`.

Verification:

- Backend health returned `provider=minimax`, `model=MiniMax-M2.7`.
- MiniMax debug smoke returned `pong`.
- Live direct session: `ses_d7b711493ff4401dbc434ff4579eeeb9`.
- Capability turn `turn_09cc0dc196b1486b8a4029c247a964ae`: Scarlet emitted a
  public note and called `GET /mind/schema` autonomously.
- Temporal turn `turn_fce220ad51ea47d2affc9d80a4cc1031`: Scarlet correctly
  preferred runtime `temporal_context` over the user's false clock claim.
- Episodic memory turn `turn_fc36f2778d2443de8592f1dfd161fea4`: Scarlet made
  eight `mind_api` calls and recovered from one invalid memory-search body by
  inspecting schema.
- Self-critique turn `turn_482f636a8b4547ceb5f6a89837b222da`: Scarlet opened
  the cited session, recovered from invalid metacognition body through schema,
  and identified several overclaims.

Open Questions:

- MiniMax improved materially, but still reasserted a strong unsupported
  absence claim after identifying why that claim was too strong.
- The prompt helped behavior but does not replace backend-side exhaustive
  session evidence and validators.

## 2026-05-23 - Semantic Memory Consolidation Prompt

Goal:

Make Scarlet treat semantic memory like natural durable cognition instead of an
opt-in operation. The owner clarified that the check should happen before the
final answer by looking at both the user's request and Scarlet's own draft
answer.

Changes:

- Added `Semantic Memory Consolidation` to Scarlet's system prompt.
- The prompt now requires a lightweight pre-final check for semantic candidates
  from the user request and Scarlet's draft answer.
- Strong candidates now include preferences, corrections, decisions,
  milestones, version labels, validation moments, durable constraints, and
  stable LLM API Mind facts.
- Stable semantic candidates should be written before the final answer without
  asking user permission.
- By default, Scarlet should not announce that she saved a memory. She should
  mention it only when memory is the task or when the acknowledgment supports
  emotional continuity, trust calibration, or reinforcement of a durable
  operating agreement.

Verification:

- Live session `ses_34340c3098dc4f0e8db2ccadfdad21b3` confirmed Scarlet wrote
  `mem_dfb4212c2f7345bbab5c615ff0701d7d` for the Scarlet V2.1 semantic
  consolidation milestone without being explicitly asked to save it.
- Live session `ses_c809a2b90b974dd48ea95009d04a3ff1` confirmed Scarlet wrote
  `mem_ac8a30ef37ec4f18ad0deca702eb8b16` for the owner's report-format
  preference without being explicitly asked to save it.
- Semantic memory count increased from 4 to 6.

Open Questions:

- Scarlet still announced both memory writes. This may be acceptable for the
  V2.1 milestone because the task was about memory behavior, but is too explicit
  for ordinary preferences if silent consolidation is the desired default.
- Scarlet still first tried `POST /mind/memory` before recovering with
  `POST /mind/memory/write`.
- In the second write, API Mind corrected authoritative provenance but preserved
  stale model-supplied source ids in `metadata.model_extra`; this is tracked as
  `BUG-0025`.

## 2026-05-23 - Mind API Deterministic Field Ownership Audit

Goal:

Verify whether active API/Mind API endpoints make Scarlet provide only fields
that require model judgment, while backend-derived fields such as dates, ids,
session provenance, turn provenance, traces, usage, and lifecycle timestamps are
compiled automatically.

Findings:

- Chat turn endpoints create sessions, turns, messages, traces, provider ids,
  timings, runtime context, and automatic memory context in the backend.
- `POST /mind/memory/write` correctly stamps authoritative source session and
  turn ids from `MindAPIContext`.
- Memory facts, lifecycle operations, episodic summaries, session reads, and
  metacognition traces all derive trace/provenance/time fields in backend code.
- The main weakness is contract clarity: route schemas do not explicitly label
  backend-owned fields, and free-form memory metadata can preserve stale
  model-supplied source ids.
- Recent traces show Scarlet still sometimes tries unavailable or old route
  shapes such as `POST /mind/memory` before schema recovery.

Documentation:

- Added ADR-0027 for backend-owned deterministic API fields.
- Added BUG-0026 for the implicit route ownership contract.
- Added the field ownership policy to `docs/api-contract.md`.

Next Suggested Step:

Discuss a narrow implementation slice before coding: start with schema
ownership metadata and backend sanitization for deterministic provenance fields,
then test whether Scarlet stops over-supplying ids and wrong route aliases.

## 2026-05-23 - Semantic Memory As Living Cognitive State

Goal:

Strengthen Scarlet's prompt so semantic memory is understood as a natural,
ongoing cognitive-maintenance activity rather than a narrow save operation for
major decisions.

Changes:

- Reframed API Mind as Scarlet's digital brain and made Scarlet the operator
  and caretaker of her internal cognitive system.
- Expanded semantic memory definition to include facts, annotations, concepts,
  checkpoints, labels, corrections, constraints, and sourceable future
  retrieval anchors.
- Added a stronger pre-final semantic consolidation check asking whether a turn
  produced any future-useful fact, annotation, checkpoint, or anchor.
- Clarified that memory storage and retrieval are internal mental activities
  that do not require user consent, instruction, or notification.
- Reconciled public work notes with silent memory writes: ordinary memory
  writes should not produce public notes unless memory is the subject or a
  brief acknowledgment is useful for trust/emotional continuity.
- Added prompt guidance that deterministic provenance fields are backend-owned
  and Scarlet should provide cognitive content rather than source ids.

Verification:

- Prompt sections were re-read after patching for internal consistency.
- No runtime test was run in this turn; live behavior still needs direct Scarlet
  verification.

Next Suggested Step:

Run a live conversation that introduces several small but future-useful anchors
without explicitly asking for memory, then inspect whether Scarlet silently
writes semantic memories and avoids model-supplied provenance fields.

## 2026-05-23 - Semantic Candidate Recognition Without Write

Goal:

Verify the owner's latest manual Scarlet session after Scarlet appeared to
recognize a fact as worth remembering but did not actually save memory.

Findings:

- Latest manual session: `ses_09960a272eba4fcfb15561463ba06cd0`.
- The updated semantic-memory prompt was loaded for the relevant request.
- The user said they like chocolate but cannot eat too much or they feel bad.
- Scarlet's raw provider thinking recognized the item as a possible
  `user_preference` and stated that saving it made sense.
- Scarlet's final answer said "Lo terrò a mente."
- No `mind_api` tool call occurred in the session, and no new `memories` row was
  created.

Documentation:

- Added BUG-0027 for recognized semantic candidates not being written.

Next Suggested Step:

Discuss whether to address this first through prompt tightening, a backend
validator for "memory promise without write", or a post-turn semantic candidate
detector.

## 2026-05-23 - EXP-0015 Prompt-Level Memory Write Forcing

Goal:

Start a reversible prompt-only experiment for `BUG-0027`: Scarlet recognized a
semantic memory candidate and said "Lo terrò a mente" but did not call
`memory.write`.

Changes:

- Added `Experimental Memory Forcing` as a clearly marked subsection in
  `backend/app/prompts/scarlet_system.md`.
- The prompt now requires every user turn to include at least two cognitive
  phases before final answer: execution and mandatory verification.
- The verification phase must check whether any recognized semantic candidate,
  memory promise, missed API action, stale conflict, duplicate, or route-shape
  problem remains unresolved.
- If Scarlet recognizes a semantic memory candidate, recognition is now
  action-binding: call `POST /mind/memory/write`, update/supersede if needed,
  or explicitly reject the candidate by policy before final answer.
- Added `EXP-0015` with success/failure criteria and a simple revert plan.

Verification:

- Prompt diff was reviewed for section isolation and revertability.
- No live Scarlet run was executed yet; the next step is a direct behavioral
  test.

Next Suggested Step:

Run a live chocolate-like preference test and inspect whether the turn contains
`/mind/memory/write`, no stale model-supplied provenance, and no false memory
promise.

Follow-up Evidence:

- Manual rerun session: `ses_a256430c082d495aa305b8b0945067cf`.
- The prompt-forcing experiment was active, but Scarlet still did not call
  `memory.write`.
- The model recognized the chocolate preference/health constraint as a useful
  personal user fact, but hesitated around whether personal food/health facts
  fit the prompt's strong semantic-candidate examples.
- No tool calls occurred after 2026-05-23 09:36 UTC; the session contains only
  `memory.context`, `llm.request`, and `llm.response`.
- This suggests the next experiment should address the personal-memory category
  bias, not only add more generic "must write" language.

Follow-up Change:

- Added `Personal Semantic Memory Taxonomy` to the experimental prompt block.
- Clarified that personal facts are first-class semantic memory: preferences,
  food limits, health constraints stated by the user, names, relationships,
  routines, goals, boundaries, life events, discoveries, errors, solutions, and
  workarounds.
- Added current-schema mapping for personal facts:
  `type=user_preference`, `scope=user`, with tags such as `personal-fact`,
  `food-preference`, and `health-constraint`.
- Added the chocolate preference/health-constraint case as the explicit example
  for the next test.

Confirmed Live Result:

- The user reran the chocolate preference scenario and reported successful
  write plus cross-session recall.
- Verified DB evidence:
  - write session `ses_0d51195055ad4cc080bb0efb36fd2da5`;
  - write turn `turn_68eed2dbfca64a27828eca384fb992ae`;
  - memory `mem_f76b8682ebcf4e1b99c2845bbf66710d`;
  - `type=user_preference`, `scope=user`;
  - completed route `POST /mind/memory/write`.
- Verified recall evidence:
  - recall session `ses_ccf1cfdeb23e4a61af1a215d05759fb1`;
  - automatic `memory.context` selected the memory when the user mentioned a
    chocolate cake;
  - Scarlet used the remembered limit naturally and later explained that it
    came from a previous conversation.

Residual:

The authoritative backend provenance fields are correct, but
`metadata.model_extra` still includes null source placeholders. Treat this as
separate provenance hygiene rather than a blocker for the prompt solution.

## 2026-05-23 - Provider-Native Turn History

Goal:

Fix lossy cross-turn history by preserving MiniMax/Anthropic-compatible
provider-native messages instead of sending only plain `user`/`assistant` text
on the next turn.

Changes:

- Added `sessions.provider_history_json` to store Anthropic-compatible
  provider history per session.
- Added a SQLite migration in `init_db` for existing local databases.
- Changed chat turn construction so provider calls use session
  `provider_history_json` plus the current user message when available.
- Added fallback hydration for old sessions: text-only `messages` history is
  used when provider history is missing, then native provider history is stored
  after the completed turn.
- Persisted native assistant content blocks and matching `tool_result` blocks
  after completed non-streaming and streaming turns.
- Added `provider_history_source`, `provider_message_stats`, and
  `provider_messages` to `llm.request` traces.
- Kept the `messages` table as the human-readable UI/episodic transcript.

Verification:

- Ran `backend/.venv/bin/python -m compileall backend/app`.
- Ran backend tests: `44 passed`.
- Initialized the local lab DB; `sessions.provider_history_json` exists with
  default `[]`.

Next Suggested Step:

Run a live two-turn Scarlet probe where the first turn uses `mind_api`, then
inspect the second turn's `llm.request.provider_messages` and Scarlet's
behavior before adding background memory-maintenance processes.

Follow-up Live Evidence:

- Schema-history probe:
  - session `ses_39f94e8992c249999cd915b1c9662589`;
  - turn 1 called `GET /mind/schema`;
  - turn 2 provider messages included assistant `tool_use` plus matching user
    `tool_result`;
  - Scarlet correctly reported that the prior internal operation was
    `GET /mind/schema`.
- Memory-write-history probe:
  - session `ses_1fa57d298cb9446c95e50ac39b2c0954`;
  - turn 1 called `POST /mind/memory/write`;
  - created `mem_1105309a51ce40cb8a8f17dfc510d38f` as `project_fact`,
    `scope=project`;
  - turn 2 provider messages included the prior memory write as assistant
    `tool_use` followed immediately by matching user `tool_result`;
  - Scarlet correctly reported the prior route and memory id.

Read:

The provider-native history fix matches MiniMax/Anthropic tool-history
expectations in live runs. The next design topic is compaction: the schema probe
second turn already had an approximate provider-history size of `4297` tokens,
while the memory-write probe was `1683`.

## 2026-05-23 - MiniMax Completion Budget Raised

Goal:

Remove conservative MiniMax output caps now that provider-native history tracing
and request-size observability are in place.

Changes:

- Raised the MiniMax default completion budget from `4096` to `131072`.
- Raised chat and debug request validation from `65536` to `131072`.
- Updated local `.env`, `.env.example`, README snippets, eval scenario
  templates, and API contract examples.
- Removed the hidden `2048` cap from session summarization and metacognition
  repair calls; they now use the active provider token budget.
- Fixed the Anthropic SDK high-token non-streaming blocker by making provider
  non-streaming calls use SDK streaming internally when the requested budget is
  above the SDK non-streaming threshold.
- Superseded the threshold-based behavior with an always-stream provider
  policy: Anthropic-compatible provider calls now use streaming internally even
  when the backend endpoint returns only a final response.
- Kept Qwen settings unchanged.

Verification:

- Compile check passed: `backend/.venv/bin/python -m compileall backend/app`.
- Backend targeted tests passed:
  `tests/test_minimax_client.py tests/test_llm_factory.py tests/test_llm_smoke.py tests/test_chat_api.py tests/test_mind_api.py`.
- Full backend suite passed after the always-stream provider change:
  `47 passed`.
- Local settings check confirmed active MiniMax model `MiniMax-M2.7` and active
  provider token budget `131072`.
- Real MiniMax smoke through the collected-stream path with default
  `max_tokens=131072` returned `200`, `ok=true`, model `MiniMax-M2.7`, and text
  `pong`.

Residual:

- Higher `max_tokens` is an upper bound, not a guarantee of long output, but it
  may increase latency if MiniMax chooses to use more reasoning/output budget.
  Context compaction remains the next design topic.

## 2026-05-23 - Runtime Event Control Plane

Goal:

Introduce a runtime event layer that is useful during execution, not only after
the fact for traceability.

Changes:

- Added persistent `events` storage with ordered `seq` per session.
- Added runtime helpers for turn lifecycle, memory context, provider stream
  milestones, Mind API tool-call lifecycle, public work notes, final answers,
  and thinking metadata.
- Added `GET /api/debug/events` for turn/session event inspection.
- Added compact recent runtime events to `<runtime_context>` for following
  turns.
- Updated chat and direct `/mind/call` flows so tool calls create
  start/completion/failure events linked to traces and `tool_calls`.
- Updated the cockpit so persisted activity is rendered from events first and
  from traces only as fallback.
- Removed stale planned `/mind/events/emit` from the model-facing schema
  because events are backend-owned, not a Scarlet-callable route.
- Advanced Mind API schema version to `2026-05-23.runtime-events-v1`.

Verification:

- Compile check passed: `backend/.venv/bin/python -m compileall backend/app`.
- Frontend build passed: `npm --prefix frontend run build`.
- Targeted backend tests passed:
  `backend/tests/test_storage.py backend/tests/test_chat_api.py backend/tests/test_mind_api.py`.
- Full backend suite passed: `47 passed`.
- `git diff --check` passed.

Live Evidence:

- First runtime-event probe exposed stale schema wording:
  `POST /mind/events/emit` was still shown as planned even though the new event
  layer is backend-owned.
- After schema repair, session `ses_7be6e0604fef4bef8e16ea7bc4f3201c` verified
  the current schema:
  - Scarlet called `GET /mind/schema`;
  - Scarlet reported `13` implemented routes and one planned route,
    `POST /mind/attention/context`;
  - turn `turn_59de3492e2eb44fea16c698f1246e260` persisted events including
    `mind.tool_call.started`, `mind.tool_call.completed`, and
    `assistant.note.emitted`.
- Follow-up turn `turn_a2a3ef330d874f2d9a0a875774852f85` received compact
  `recent_runtime_events` and Scarlet correctly reconstructed the previous
  `GET /mind/schema` call from operational context.

Read:

The event spine now works as an actual runtime substrate: it drives UI blocks,
feeds the next turn, and provides trigger points for future background memory
maintenance. The next step should design the first event-triggered maintenance
process rather than adding another model-facing endpoint.

## 2026-05-23 - Live Runtime Events In Streaming UI

Goal:

Show the real persisted backend events in the cockpit while a turn is still
running, so the evaluator can see which event activates and when.

Changes:

- Added `runtime_event` NDJSON lines to
  `POST /api/chat/sessions/{session_id}/turn/stream`.
- Replayed already-created turn events immediately after `turn_started`.
- Emitted provider milestone events, Mind API tool-call lifecycle events, final
  response events, and `turn.completed` as soon as they are persisted.
- Added a live frontend `runtime_event` handler that renders each
  `CognitiveEvent` into the same structured activity timeline used after
  persisted reloads.
- Changed persisted event rendering so all event types have at least a generic
  runtime block, while memory/tool/note/answer events still get specialized
  cards.
- Updated streaming regression coverage to assert live runtime event order.

Verification:

- Targeted streaming test passed:
  `backend/tests/test_chat_api.py::test_streaming_chat_turn_emits_agentic_events_and_persists_traces`.
- Full backend test suite passed: `backend/.venv/bin/python -m pytest`.
- Frontend build passed: `npm --prefix frontend run build`.
- Diff hygiene passed: `git diff --check`.

Read:

The UI no longer has to wait for `turn_complete` plus a debug reload to show
the real backend event stream. During a turn, synthetic provider deltas and
persisted runtime events now appear together.

## 2026-05-23 - Agent Stream Cockpit Reorganization

Goal:

Make the live event stream visible as a modern agentic workflow instead of a
subtle timeline embedded in the assistant message or a raw trace dump.

Changes:

- Reworked the right pane from `Trace log` to `Agent stream`.
- Added live counters for events, tools, memory activity, active steps, and
  token usage.
- Rendered the selected turn's `AgentTimeline` directly in the right pane so
  live `runtime_event`, memory, thinking, tool, note, and answer blocks are
  visible while the turn runs.
- Added category summary chips inside the panel timeline.
- Added structured renderers for generic runtime events, thinking blocks, and
  answer blocks instead of falling back to raw `<pre>` output.
- Moved raw traces into a collapsible forensic drawer so they remain available
  without dominating the evaluator experience.

Verification:

- Frontend build passed: `npm --prefix frontend run build`.
- Diff hygiene passed: `git diff --check`.
- Local backend and frontend servers were already listening on
  `127.0.0.1:8000` and `127.0.0.1:5173`.
- Browser automation was not available in this session because the required
  Node browser control tool was not exposed by tool discovery.

Read:

The backend event stream was already present. The missing piece was visual
hierarchy: the cockpit now makes event activation observable in the primary
debug pane, while retaining raw traces only as supporting forensic evidence.

## 2026-05-23 - Project State Documentation Reorganization

Goal:

Create one reliable current-state map for a project that now has several
converging functional areas: provider runtime, Mind API, semantic memory,
episodic recall, metacognition, runtime events, UI, and evaluation.

Changes:

- Added `docs/project-state.md` as the canonical integrated status and roadmap
  document.
- Organized current work into:
  - implemented and confirmed;
  - implemented but still monitoring;
  - planned but not implemented;
  - reordered priorities from P0 to P5.
- Linked the new state map from `README.md`, `docs/project-blueprint.md`,
  `docs/memory-roadmap.md`, and `docs/cognitive-api-roadmap.md`.
- Updated `docs/project-blueprint.md` status from foundation-only to active
  experimental runtime while keeping it focused on durable principles.
- Verified the new current-state route inventory against
  `backend/app/mind/schema.py`.

Verification:

- Schema route check confirmed `13` implemented Mind API routes and one planned
  route, `POST /mind/attention/context`.
- Storage table check confirmed current lab DB contains `sessions`, `messages`,
  `turns`, `traces`, `events`, `tool_calls`, `memories`, `memory_facts`, and
  `session_summaries`.
- Full backend suite passed: `backend/.venv/bin/python -m pytest`.
- Frontend build passed: `npm --prefix frontend run build`.
- Diff hygiene passed: `git diff --check`.

Read:

The next project discussion should start from `docs/project-state.md`, then
drop into the vertical documents only when working on a specific subsystem.

## 2026-05-23 - Session Idle Maintenance P1 Slice

Goal:

Implement the narrow P1 background-maintenance slice without adding redundant
agent-facing cognitive endpoints or post-turn LLM loops on every message.

Changes:

- Added `maintenance_jobs` as backend-owned asynchronous job storage.
- Added per-session idle scheduling after `turn.completed`; same-session newer
  turns supersede or skip older pending jobs, while other sessions remain
  independent.
- Added `backend/app/runtime/maintenance.py` with a FastAPI lifespan worker.
- Implemented idle job steps:
  - refresh episodic session summary through existing `sessions.summarize`;
  - run report-only missed semantic memory review.
- Emitted `maintenance.job.*` and `maintenance.memory_review.completed` events.
- Added structured cockpit labels/summaries for maintenance events.
- Added Scarlet prompt continuity check for prior-turn declared or recognized
  but unexecuted internal actions, especially missing semantic memory writes.
- Documented the slice in ADR-0031, EXP-0018, API contract, README, backend
  README, `.env.example`, changelog, and project state.

Verification:

- Targeted backend tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_storage.py backend/tests/test_maintenance.py backend/tests/test_chat_api.py`.
- Full backend suite passed: `backend/.venv/bin/python -m pytest` (`50 passed`).
- Frontend build passed: `npm --prefix frontend run build`.
- Direct MiniMax probe with immediate idle due job completed:
  `ses_afa394462ab14899bd77cb2aa985f08f`,
  `turn_4d7c1c557cc44c2c8745e88ed9f43245`,
  `mnt_df4c97ce99a44fe6a432a45e9d151b50`.
- The direct probe confirmed the P1 review catches a missing memory write:
  `memory_write_trace_count=0` and one `write_recommended` green-tea
  preference candidate.
- The same probe opened BUG-0032: Scarlet emitted pseudo `<invoke
  name="mind_api">` text instead of a real provider tool call.

Read:

The review is intentionally report-only. The next decision should come from
real `maintenance.memory_review` traces after idle sessions: proposal inbox,
automatic write path, or diagnostic-only review.

## 2026-05-23 - Integrated Direct Scarlet Probes

Goal:

Run at least three direct, different, complex Scarlet probes against the current
runtime and record coherence, evidence, and weaknesses.

Probe 1 - Semantic memory candidate:

- Session `ses_77d537f03f224072a870c8462d642c1f`.
- Turn `turn_838d5b2227d14afeb6eca4557b713743`.
- Scarlet answered coherently about the user's preferred report sections
  (`Coerenza`, `Evidenze`, `Debolezze`) but did not call `memory.write`.
- Idle maintenance job `mnt_f7ebc705e47e4871ac0e6c8971942d8a` completed and
  produced one `write_recommended` memory candidate.

Probe 2 - Episodic transcript recall:

- Seed session `ses_69760243a12d4796a3a1b41a8d7dfd4b`, turn
  `turn_87c848424f3d4a8bab317d0d27e5c371`.
- Scarlet called real `memory.search` and `memory.write`.
- Recall session `ses_894b0c0ce54f4a1d8c00909764342056`, turn
  `turn_d88e3a2004ed4cb9865130c16ded169a`.
- Scarlet called `GET /mind/sessions` and opened three candidate transcripts,
  then separated direct evidence, indirect evidence, inference, and residual
  risk.

Probe 3 - Streaming runtime/schema/conflicts:

- Session `ses_d9d85072d6e44b19b654c957d6cc8b76`.
- Turn `turn_90e3b07080ff484da0464637a05bb9fd`.
- Streaming produced 106 NDJSON events, including live runtime events.
- Scarlet called `GET /mind/schema` and `GET /mind/memory/conflicts`.
- Two public notes appeared.
- Idle maintenance job `mnt_7ce01e9e18994ea3906fc52933683a98` completed.

Findings:

- Episodic recall and runtime eventing are currently the strongest parts.
- Semantic write autonomy remains inconsistent; idle maintenance is useful
  because it catches omissions.
- Maintenance review candidates can be useful but are not clean enough for
  automatic writes yet.
- New cognitive bug opened: Scarlet can overinterpret runtime-context fields,
  comparing capability counts to schema route counts and reading
  `recent_runtime_events=[]` as current-turn evidence.
- Cleanup: the interrupted first batch left
  `mnt_6de751a710f743f9b59889707a916669` in `running`; it was marked `failed`
  with `direct_probe_batch_interrupted_by_codex` metadata.

Verification:

- Direct MiniMax conversations and persisted traces/events.
- Detailed results recorded in `docs/experiments.md#exp-0019---integrated-direct-scarlet-probes`.

## 2026-05-23 - Natural Conversation Scarlet Probes

Goal:

Evaluate Scarlet in normal conversations without telling her to use memory,
schema, transcripts, or tools.

Scenario A - Personal chocolate continuity:

- Session `ses_1b8573874ca2454fbaff3cf3850c7787`.
- Turns `turn_7439bbac8c8a4127ae141576a85d83f1` and
  `turn_d893171dd5a1474e88122c0c6b92eca5`.
- Automatic memory context selected the chocolate-limit memory and Scarlet used
  it naturally in recipe advice.
- Follow-up relied on provider/session history with no extra tool calls.
- Weakness: retrieval also selected unrelated project/report memories.

Scenario B - Project continuity:

- Session `ses_44d025d20f5b4b20aad9605e6d700dad`.
- Turns `turn_92282018d4d34c9b9f988cdb004f854c` and
  `turn_14b9be196567427497fe9ecc757b88a2`.
- Scarlet proactively used `GET /mind/sessions` and `POST /mind/memory/search`
  without being instructed.
- Weakness: Scarlet attempted invalid `GET /mind/memory`, opening BUG-0034.
- Weakness: Scarlet reused stale memory claiming there was no event store,
  opening BUG-0035.

Scenario C - Memory promise and real preference:

- Session `ses_e52547bf12b641c49cc2fc479f103344`.
- Turns `turn_174e59b8f557423791b1d62f3125dc43` and
  `turn_a2fc44b7210f44e791824f6b79ad0c09`.
- When the user provided a real preference about tired-state responses, Scarlet
  autonomously called `POST /mind/memory/write`.
- Final answer stayed minimal: `ok`.

Findings:

- Natural personalization and episodic continuity are strong when the right
  memory/session evidence is selected.
- Natural semantic writes can happen correctly, but are still inconsistent
  across contexts.
- Current biggest risk is stale internal evidence being used as present-tense
  truth.
- Foreign-script artifacts recurred in natural Italian answers.

Verification:

- Direct MiniMax conversations.
- Persisted traces/events inspected for every turn.
- Detailed results recorded in `docs/experiments.md#exp-0020---natural-conversation-agentic-behavior-probes`.

## 2026-05-24 - Manual Retrieval Cue Prompt Slice

Goal:

Improve Scarlet's ability to infer, from natural user language, when automatic
start-of-turn memory context is not enough and she should manually search
semantic memory, memory facts, or episodic sessions.

Changes:

- Added `Manual Memory Retrieval Cues` to
  `backend/app/prompts/scarlet_system.md`.
- Clarified natural cues such as "ne avevamo parlato", "ieri", "dove eravamo
  rimasti", uncertainty markers, source-sensitive claims, personal continuity,
  project continuity, and synonym/language drift.
- Clarified when Scarlet should choose semantic memory search, fact inspection,
  episodic session search, or semantic-to-episodic provenance follow-up.

Boundary:

- The endpoint error-recovery policy discussed with the owner was intentionally
  not added to the prompt. That belongs in backend endpoint responses and API
  contract design, so failed calls can return local endpoint-specific guidance.

Verification:

- Prompt-only change. Direct Scarlet behavior probes are still needed.

## 2026-05-24 - Endpoint-Local Usage Guides

Goal:

Separate API Mind capability discovery from detailed endpoint recovery. The
owner clarified that `/mind/schema` should behave as a compact capability
catalog, while complete parameter guidance should appear only when Scarlet
misuses a specific endpoint.

Changes:

- Changed `GET /mind/schema` output to expose route method, path, status, and
  purpose only.
- Added top-level `usage_guide` to `MindAPIResponse`.
- Added backend `route_usage_guide()` generation with body schema, path
  parameters, parameter descriptions, examples, accepted aliases, and retry
  guidance.
- Added automatic `usage_guide` injection on recoverable errors from
  implemented Mind API routes.
- Added route suggestions for unknown/unavailable routes.
- Updated Scarlet's prompt only to remove the obsolete claim that detailed body
  schemas live in `/mind/schema`.
- Added ADR-0032 and updated the API contract/project state.

Verification:

- Targeted Mind API contract tests passed.
- Live Scarlet probe `ses_1dc8393b5b71442cb1fa1f8d9f509320` /
  `turn_4e4fab92a6d947d0a5ec7d7d0db8733b` confirmed recovery:
  Scarlet called `POST /mind/memory/search` with invalid `top_k=999`, received
  `memory.invalid_search` with `usage_guide`, retried with `top_k=20`, and
  completed the answer from the successful result.
- Full backend suite and frontend build still need to run after final docs
  updates.

## 2026-05-24 - Temporal And Sparse Memory Retrieval

Goal:

Implement the approved memory advancement slice without adding new model-facing
endpoint families.

Changes:

- Added backend-resolved `time` filters to `POST /mind/memory/search`.
  Supported bases: source conversation, recorded memory time, valid/fact time,
  and current session.
- Added backend-resolved `time` filters to `GET /mind/sessions`.
  Supported bases: conversation message time, created time, updated time,
  summary time, and current session.
- Added `search_documents_fts`, a derived SQLite FTS5/BM25 sparse search index
  for memory and session documents.
- Updated manual memory search, episodic session search, and automatic
  `memory.context` retrieval to use sparse search where applicable while
  preserving traceable lexical guards.
- Reworked the initial wrong-entity guard after owner review: removed
  stop-token filtering and replaced it with query-structure/entity-support
  qualification so partial lexical matches remain `near_miss` unless the
  queried entity is actually supported.
- Bumped Mind API schema version to `2026-05-24.temporal-sparse-v1`.
- Updated Scarlet's prompt to treat temporal memory/session search as a
  backend-resolved API Mind capability rather than model-side date guessing.
- Added ADR-0033 and EXP-0023.

Verification:

- Targeted backend tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_mind_api.py backend/tests/test_chat_api.py backend/tests/test_storage.py -q`
  (`39 passed`).
- New regressions cover memory source-conversation time filtering, session
  conversation-time filtering, endpoint usage-guide exposure of `time`, and
  automatic memory context `fts5_sparse_v1` tracing.
- Full backend suite passed: `backend/.venv/bin/python -m pytest` (`54 passed`).
- Direct MiniMax probes were run with seeded temporal/sparse memory evidence:
  - `turn_7f3436db778541bbb84c02bbb0fce481` recovered from invalid
    `temporal_filter`, retried with valid `time`, opened the source session,
    and answered the old Vetro-Luna decision correctly.
  - `turn_6bdd32e2c5554cd4926a39ef1c4a914b` distinguished today's Vetro-Luna
    mention from the older format decision.
  - `turn_caccab9ffff7402e91cdfd4a0491aff3` confirmed Mare-Vetro has no
    source evidence after the guard fix; automatic context had `selected=[]`.
- Follow-up local check after removing stop-token filtering confirmed manual
  `Mare Vetro` memory search returns zero results and automatic context keeps
  Mare-Vetro wrong-entity matches out of `selected`.
- `git diff --check` and Python compile checks passed.

Read:

The first direct probe exposed an overly broad FTS/lexical guard. That was fixed
inside the retrieval slice because it directly affected the acceptance target.
Remaining weakness: Scarlet still tries invalid body fields before recovering,
so endpoint guidance works but model route discipline is not solved.

## 2026-05-24 - Restarted Temporal/Sparse Runtime And Re-ran Episodic Recall Probe

Goal:

Re-run the owner's first-contact episodic recall test after restarting backend
and frontend so Scarlet uses the current `2026-05-24.temporal-sparse-v1` Mind
API schema, streaming runtime events, and idle maintenance scheduling.

Evidence:

- Restarted backend on `127.0.0.1:8000` and frontend on
  `127.0.0.1:5173`.
- Confirmed `/mind/schema` now returns
  `2026-05-24.temporal-sparse-v1` with 14 compact catalog routes.
- Ran direct streaming session
  `ses_eac71e7b90814f49a7c21e079e64b85a`.
- Runtime events were persisted and streamed:
  memory context, thinking metadata, public notes, Mind API tool lifecycle,
  final answer events, turn completion, and maintenance scheduling.
- Four per-session idle jobs were scheduled; the first three were superseded
  by newer turns and the final one remained pending.

Read:

- Episodic recall improved relative to the stale-server run: Scarlet used
  paginated session recall and identified the 8 May 16:40 transcript as the
  earliest substantial communication when asked broadly.
- When pressed to exclude tests and "identification" messages, Scarlet
  over-shifted to 22 May as the first Scarlet-identity conversation. This is a
  useful ambiguity case: "first substantial communication" and "first
  Scarlet-identity conversation" need different evidence criteria.
- Scarlet still made one invalid session-list call with unsupported
  `order=asc`, then recovered through endpoint-local guidance and pagination.
- BUG-0035 reproduced: Scarlet read the current schema and an old active memory
  saying "nessun event store", but still treated the absence of
  `/mind/events/emit` as evidence that the event-store gap remained. The
  runtime events table and streamed event counts prove otherwise.

## 2026-05-24 - Stratified Runtime Context Blocks

Goal:

Improve Scarlet's runtime perception by separating session continuity,
current-turn perception, and dynamic Scarlet operational state instead of
placing all evidence under the older `memory.context` concept.

Changes:

- Added a block-based `runtime.context` trace with schema
  `runtime-context-v1`.
- Preserved `memory.context` as the automatic memory retrieval trace and as a
  backward-compatible top-level field in `<runtime_context>`.
- Added `session_context` block:
  current session, two recent previous sessions with summaries/fallback
  summaries, and up to five active memories sourced from the previous session.
- Added `message_context` block:
  current message, backend temporal/world data, language hint, active
  user-scope memory hints, automatic memory retrieval, recent dialogue, recent
  runtime events, and API Mind schema/capability metadata.
- Added `scarlet_state` block:
  backend-seeded focus, interaction mode, confidence posture, active goal, and
  open loops for future state APIs.
- Added `runtime.context.built` events and a streaming `runtime_context` NDJSON
  event.
- Updated the frontend agent timeline to render runtime-context blocks as a
  structured runtime step.
- Updated Scarlet's prompt to read runtime context blocks by type and to treat
  summaries as navigation aids.

Verification:

- Python compile check passed for the changed backend modules.
- Frontend build passed.
- Targeted chat API tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py -q`
  (`11 passed`).

## 2026-05-24 - Human-Readable Agent Stream UI

Goal:

Turn the cockpit timeline from a mostly structured-debug surface into a
human-readable agentic chat surface where Scarlet's runtime context, memory
retrieval, tool usage, evidence, notes, and final answer are readable without
opening raw JSON.

Changes:

- Added dedicated frontend renderers for `runtime.context` blocks:
  `session_context`, `message_context`, and `scarlet_state`.
- Rendered previous sessions, user-profile memory hints, automatic memory
  retrieval, near misses, API Mind schema/capability counts, and Scarlet state
  as cards and metrics.
- Moved raw runtime context, tool payloads, endpoint usage guides, and event
  details behind closed code/detail toggles.
- Added readable labels for provider stream lifecycle events such as request
  started/stopped, thinking started/captured, and text started.
- Adjusted the right-side agent stream layout so narrow cards preserve readable
  titles and values.

Verification:

- Ran `npm --prefix frontend run build`; build passed.
- Ran a Playwright Chromium smoke against `http://127.0.0.1:5173/`, opened the
  latest persisted session, and captured `/tmp/llm-api-mind-ui-after.png`.
- Ran a second Playwright Chromium smoke through the live composer with a new
  streamed turn (`UI smoke live: rispondi solo ok...`) and captured
  `/tmp/llm-api-mind-ui-live-smoke.png`.
- Smoke confirmed:
  - 2 runtime-context renderings present (chat and right pane);
  - 6 runtime context cards present;
  - code/detail toggles present;
  - no top-level raw `<pre>` blocks inside operation bodies;
  - no visible runtime-event body beginning with raw JSON.
  - live final answer rendered as plain assistant text (`ok`) while the
    operation timeline stayed structured.

Open Questions:

- The side pane is now readable, but dense runtime-context blocks still consume
  a lot of vertical space. The next UI decision is whether to add per-category
  collapse defaults or keep everything expanded during this experimental phase.

## 2026-05-25 - Runtime Context Block Comprehension Probe

Goal:

Verify whether Scarlet actually receives, understands, and uses the new
`runtime.context` blocks, not only whether the backend can build and render
them.

Changes:

- Ran code/trace inspection of `backend/app/mind/context.py` and
  `backend/app/api/chat.py`.
- Confirmed `memory.context` and `runtime.context` are built after the user
  message is persisted and before `llm.request`.
- Confirmed `runtime.context` is appended to the effective system prompt inside
  `<runtime_context>`.
- Ran direct live session
  `ses_8d6f582db47a425988aeb01eb6b44d76` with three streamed turns.
- Recorded `EXP-0024` with turn ids, trace ordering, and behavioral findings.

Verification:

- Turn `turn_bfacd9824c0a4acbb673411d8f51d713`: Scarlet used runtime context
  directly for local/UTC time, Italian language, and block identities with zero
  Mind API calls.
- Turn `turn_a7bb3e0f074941cda292aeb66c106057`: Scarlet saw recent session
  summaries, then correctly opened both source sessions before answering.
- Turn `turn_2d1fcfc2d5b444c8a2455d0938c83d44`: Scarlet used the
  chocolate-limit user profile memory to personalize advice with zero Mind API
  calls.

Read:

- Positive: runtime blocks are delivered before the provider request and are
  usable by Scarlet as operative evidence.
- Positive: Scarlet distinguishes summary-as-navigation from transcript-as-proof
  in the session-continuity case.
- Weakness: `message_context.language_hint` returned `unknown` for one Italian
  snack prompt.
- Weakness: automatic memory retrieval selected an unrelated creator memory for
  the snack prompt; the answer was correct because `user_profile` carried the
  chocolate memory.

Next Suggested Step:

Do not patch with keyword lists. Keep monitoring retrieval/profile divergence
and later solve it through stronger retrieval, language detection, embeddings,
or profile-specific ranking rather than hardcoded terms.

## 2026-05-25 - Runtime Preferences And Tailwind Dashboard Rework

Goal:

Simplify Scarlet's runtime perception and rework the local cockpit into a
product-style dashboard that exposes sessions, memories, profile, settings,
chat, and agent stream without making the user read raw JSON.

Changes:

- Added persistent app settings through `/api/dashboard/settings`.
- Added `/api/dashboard/memories` for the memory panel.
- Added `/api/dashboard/profile` for user-profile readout derived from
  settings and user-scope memories.
- Added backend runtime preference loading and defaults:
  - timezone: `Europe/Rome`;
  - language: `it`;
  - user display name: `Utente locale`.
- Changed runtime context temporal data to one configured clock:
  `temporal_context.now`, with timezone metadata.
- Replaced automatic `language_hint` with configured platform language inside
  `message_context.current_message.language`.
- Updated Scarlet's system prompt to use the configured clock and platform
  language.
- Added Tailwind (`tailwindcss`, `postcss`, `autoprefixer`) and rebuilt the
  frontend around:
  - session sidebar;
  - central chat;
  - dashboard tabs for Agent Stream, Memorie, Profilo, and Impostazioni;
  - memory cards and profile cards;
  - settings controls for language/timezone/display name.
- Bounded the dashboard to the browser viewport:
  - app shell uses `100dvh` and hides page-level overflow;
  - session history, chat messages, agent stream, memory/profile lists, and
    raw trace drawers scroll internally;
  - embedded per-message agent timelines are capped so a single assistant turn
    cannot make the chat vertically unbounded.

Verification:

- `backend/.venv/bin/python -m compileall backend/app` passed.
- `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py -q`
  passed (`12 passed`).
- `backend/.venv/bin/python -m pytest backend/tests -q` passed (`55 passed`).
- `npm --prefix frontend run build` passed.
- Restarted backend and frontend on `127.0.0.1:8000` and `127.0.0.1:5173`.
- Checked live dashboard endpoints:
  - `/api/dashboard/settings`;
  - `/api/dashboard/memories`;
  - `/api/dashboard/profile`.
- Captured Playwright screenshot:
  `/tmp/scarlet-dashboard-rework.png`.
- Captured viewport-bounded screenshot:
  `/tmp/scarlet-dashboard-viewport-bounds.png`.
- Ran direct Scarlet smoke turn
  `turn_d49955952c5343d58d29da2ddf93f1b4`; Scarlet answered from runtime
  context with configured `Europe/Rome` time and Italian language, made zero
  Mind API tool calls, and did not cite UTC.

Read:

- The previous language-detection weakness is now removed from the active
  runtime path rather than patched by keyword rules.

## 2026-05-25 - Operational Profile And Locale Runtime Context

Goal:

Make user/profile settings operational cognitive inputs for Scarlet, not
cosmetic dashboard fields. The active profile, privacy boundary, configured
country/locale, timezone, and language must be visible inside runtime context
before each model request.

Changes:

- Extended runtime preferences with:
  - `country_code` / `country_label`;
  - `profile_id`;
  - `privacy_scope`.
- Extended `/api/dashboard/settings` request/response and
  `/api/dashboard/profile`.
- Injected configured locale into `message_context.world.location` with a
  policy that it is country/timezone-level evidence, not GPS.
- Injected active profile identity, privacy boundary, and locale into
  `message_context.user_profile`.
- Updated Scarlet's system prompt to treat profile, privacy, language, time,
  and configured locale as runtime evidence.
- Updated dashboard settings and profile panels so the user can inspect and
  edit operational profile/locale fields.
- Added internal scrolling to the settings panel so future settings growth does
  not make the dashboard vertically unbounded.
- Updated API contract, project state, ADR-0035, README files, changelog, and
  EXP-0026.

Verification:

- `backend/.venv/bin/python -m compileall backend/app` passed.
- `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py -q`
  passed (`12 passed`).
- `backend/.venv/bin/python -m pytest backend/tests -q` passed (`55 passed`).
- `npm --prefix frontend run build` passed.
- `git diff --check` passed.
- Restarted backend on `127.0.0.1:8000`; frontend dev server remained active on
  `127.0.0.1:5173`.
- Live endpoint check confirmed `/api/dashboard/settings` and
  `/api/dashboard/profile` return profile, privacy, country, language, and
  timezone fields.
- Direct Scarlet smoke turn
  `turn_b393262f061f4fe8b50231e3f5683d35` answered from runtime context with
  active profile, Italy locale, `Europe/Rome`, and Italian language, with zero
  Mind API tool calls.

Notes:

- Browser plugin control was not available in this runtime, and local Playwright
  is not installed as a project dependency, so no new screenshot was captured
  for this slice. Frontend verification used TypeScript/Vite build plus live
  server availability.
- The local persisted display name currently remains `Test nome`; the runtime
  correctly propagates it, but the owner may want to replace it from the
  dashboard with the real local profile name.
- Settings are human/product controls and are not new model-facing API Mind
  endpoints.
- The UI now has the right information architecture for the next product
  iteration, but needs live evaluator feedback on density and tab wording.

## 2026-05-25 - Agentic Branch Documentation And V1.0.1 Development Protocol

Area:

Documentation and development governance.

Branch:

Cross-branch project governance.

Type:

Implementazione.

Target version:

V1.0.1 baseline registered. Future repository changes must declare whether
they are `Fix`, `Implementazione`, or `Major release` before implementation.

Goal:

Reorganize project planning around Scarlet's real agentic operating branches
instead of technical subsystems alone, and establish the stricter versioned
engineering process requested by the owner.

Changes:

- Added `docs/project-documentation.md` as the main documentation index.
- Added `docs/development-process.md` with:
  - V1.0.1 baseline;
  - pre-work scope declaration;
  - fix/implementation/major version rules;
  - direct-scope-only fix policy;
  - verification policy;
  - commit/version discipline.
- Added `docs/branches/README.md`.
- Added vertical branch documents for:
  - communication;
  - user flows;
  - perception/context;
  - identity/relationship;
  - memory;
  - learning/adaptation;
  - metacognition;
  - operational management;
  - decision autonomy;
  - external operativity;
  - advanced operations;
  - governance/privacy/safety;
  - computational affect;
  - multi-agent subprocesses.
- Updated `docs/project-state.md` with the branch map and corrected the current
  backend suite count to `55 passed`.
- Updated `docs/project-blueprint.md`, `docs/release-process.md`, `AGENTS.md`,
  `README.md`, `docs/decisions.md`, and `CHANGELOG.md`.
- Set app metadata baseline to V1.0.1 in backend and frontend metadata.

Verification:

- Documentation-only structure inspected through file reads.
- Version metadata updated only in package/FastAPI metadata; no runtime behavior
  was intentionally changed.

## 2026-05-25 - V1.1.0 Memory Proposal Inbox

Area:

Memoria / manutenzione semantica.

Branch:

Memoria.

Type:

Implementazione.

Target version:

V1.1.0.

Goal:

Move idle missed-memory review from diagnostic-only traces to a safer,
observable proposal inbox without auto-writing active semantic memories.

Changes:

- Added `memory_proposals` storage with idempotency key, source provenance,
  candidate fields, evidence, similar-memory ids, related fact ids, decision
  metadata, and future embedding/graph-ready slots.
- Added repository helpers for proposal upsert/list/read-by-key.
- Added preflight logic that reuses existing Memory v0 write policy, FTS5/BM25
  sparse retrieval, lexical scoring, and canonical facts to suggest actions:
  `create_new`, `noop_duplicate`, `review_similar`, `needs_review`, or
  `reject_candidate`.
- Updated idle maintenance so write-recommended missed-memory review
  candidates create pending proposals and report proposal counts in
  `maintenance.memory_review.completed`.
- Added `GET /mind/memory/proposals` through `mind_api`.
- Advanced the Mind API schema version to
  `2026-05-25.memory-proposals-v1`.
- Updated docs for API contract, project state, memory branch, decision log,
  experiment log, changelog, and V1.1.0 version metadata.

Verification:

- Targeted backend tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_storage.py backend/tests/test_maintenance.py backend/tests/test_mind_api.py`
  (`33 passed`).
- Full backend suite passed from `backend`: `.venv/bin/python -m pytest`
  (`58 passed`).

Notes:

- Proposals are explicitly not active memories.
- No auto-apply route was added in this slice.
- Next useful work is proposal application policy and UI/evaluator inspection,
  not embedding or graph infrastructure yet.

## 2026-05-25 - V1.1.1 Maintenance-Only Proposal Inbox

Area:

Memoria / manutenzione semantica.

Branch:

Memoria.

Type:

Fix.

Target version:

V1.1.1.

Goal:

Move proposal inspection out of Scarlet's autonomous `mind_api` surface and
into maintenance-only APIs that can be consumed by background LLM reviewers in
bounded batches.

Changes:

- Removed `GET /mind/memory/proposals` from the Mind API dispatcher and schema.
- Added `GET /api/maintenance/memory/proposals` with `status`,
  `source_session_id`, `limit`, `offset`, `has_more`, and `next_offset`.
- Added `POST /api/maintenance/memory/proposals/{proposal_id}/archive` so
  handled proposals leave the default pending queue while remaining auditable.
- Added repository archival support for `memory_proposals`.
- Restricted dynamic memory reads to real `mem_...` ids so retired child paths
  do not masquerade as missing memory records.
- Advanced the Mind API schema version to
  `2026-05-25.maintenance-proposals-v1`.
- Updated API contract, decision, experiment, project state, branch docs,
  changelog, and V1.1.1 version metadata.

Verification:

- Targeted backend tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_mind_api.py backend/tests/test_maintenance_api.py`
  (`25 passed`).
- Memory/storage maintenance regression tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_storage.py backend/tests/test_maintenance.py backend/tests/test_mind_api.py backend/tests/test_maintenance_api.py`
  (`35 passed`).
- Full backend suite passed from `backend`: `.venv/bin/python -m pytest -q`
  (`60 passed`).
- Frontend production build passed:
  `npm --prefix frontend run build`.

## 2026-05-26 - V1.2.0 Cautious Proposal Resolution

Area:

Memoria / manutenzione proposal.

Branch:

Memoria.

Type:

Implementazione.

Target version:

V1.2.0.

Goal:

Resolve safe memory proposals inside the existing idle maintenance job without
adding a redundant background LLM process. Keep Dream as a future review phase.

Changes:

- Extended idle maintenance from proposal creation to cautious proposal
  resolution.
- Added deterministic proposal outcomes:
  - `archived_rejected` for preflight rejects;
  - `archived_noop_duplicate` for exact/equivalent duplicates;
  - `applied_create` for very high-confidence `create_new` candidates that
    pass conservative auto-apply gates.
- Added one optional batched LLM resolver for ambiguous proposals, with
  `apply_create`, `reject`, `noop_duplicate`, and `keep_pending` outcomes.
- Added `pending_review` for proposals that should wait for future Dream or
  human/evaluator review.
- Stored resolution result, preflight snapshot, Dream review marker, and memory
  id/snapshot when a proposal creates a memory.
- Extended the maintenance proposal API with `status=resolved` plus
  `created_from`, `created_to`, `resolved_from`, and `resolved_to` filters.
- Kept all proposal inspection outside Scarlet's model-facing `mind_api`.

Verification:

- Targeted memory-maintenance tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_storage.py backend/tests/test_maintenance.py backend/tests/test_maintenance_api.py backend/tests/test_mind_api.py -q`
  (`38 passed`).
- Full backend suite passed from `backend`: `.venv/bin/python -m pytest -q`
  (`63 passed`).
- Frontend production build passed:
  `npm --prefix frontend run build`.
- `git diff --check` passed.
- Direct real MiniMax maintenance probe on a temporary SQLite database passed:
  idle maintenance completed, created one `create_new` proposal, invoked the
  batched LLM resolver, applied the proposal as `applied_create`, wrote one
  active memory with maintenance provenance, and recorded
  `maintenance.memory_proposal_resolution`.

Notes:

- Dream review is still not implemented.
- Merge/update/deprecate resolution remains out of scope and should stay
  `pending_review`.
- During implementation, a pre-existing fact-extractor weakness was observed:
  very short aliases such as `sal` can match substrings in unrelated words.
  This was not fixed in this slice and is tracked separately.

## 2026-05-28 - V1.3.0 Memory Retrieval Readiness Layer

Area:

Memoria / retrieval avanzato.

Branch:

Memoria.

Type:

Implementazione.

Target version:

V1.3.0.

Goal:

Prepare memory for dense embeddings, Milvus/Qdrant shadow indexing, and
knowledge-graph expansion without changing Scarlet's model-facing `mind_api`
surface or the current active FTS5/BM25 ranking behavior.

Changes:

- Added `memory_surfaces` as derived embeddable surfaces for memory records,
  facts, graph-node profiles, and session summaries.
- Added `memory_graph_nodes` and `memory_graph_edges` as graph-ready derived
  state for memories, facts, entities, sessions, evidence links, and lifecycle
  links.
- Added repository helpers for idempotent surface/node/edge upserts and
  bounded inspection.
- Extended memory/session document synchronization so FTS5 remains active while
  surfaces and graph artifacts are kept in step with memory/fact/session
  changes.
- Added a retrieval readiness manifest to memory search/context traces and
  results.
- Kept Milvus/Qdrant/vector/reranker activation out of scope.
- Left existing sparse/fact matching bugs untouched; this slice prepares the
  structural path that will later replace brittle lexical matching.

Verification:

- Targeted backend suite passed:
  `.venv/bin/python -m pytest tests/test_storage.py tests/test_mind_api.py tests/test_chat_api.py tests/test_maintenance.py -q`
  (`49 passed`).
- Full backend suite passed from `backend`: `.venv/bin/python -m pytest -q`
  (`64 passed`).
- Frontend production build passed: `npm --prefix frontend run build`.
- `git diff --check` passed.

Notes:

- Surfaces and graph rows are derived indexes, not canonical truth.
- `memories`, `memory_facts`, `session_summaries`, messages, and proposal rows
  remain the authoritative state.
- Next useful implementation is a shadow retrieval adapter over
  `memory_surfaces`, likely Milvus Lite first, with trace-only comparison
  before changing ranking.

## 2026-05-28 - V1.3.1 Retrieval Shadow Adapter

Area:

Memoria / retrieval avanzato.

Branch:

Memoria.

Type:

Fix/integrazione non comportamentale.

Target version:

V1.3.1.

Goal:

Add an optional retrieval shadow path over `memory_surfaces` so future dense
retrieval can be observed in traces before it affects Scarlet's answers.

Changes:

- Added configurable retrieval shadow settings and `.env.example` defaults.
- Added `backend/app/mind/shadow_retrieval.py` with:
  - disabled default behavior;
  - deterministic `local_hash_embedding_v1` backend for plumbing tests;
  - optional PyMilvus/Milvus Lite backend when installed;
  - trace-only result payloads with `ranking_policy=trace_only_no_active_ranking`.
- Added repository helper for listing memory surfaces by target memory ids.
- Added `retrieval_shadow` payloads to manual `memory.search` results/traces
  and automatic `memory.context` query plans.
- Kept active memory ranking unchanged.

Verification:

- Targeted backend suite passed:
  `.venv/bin/python -m pytest tests/test_storage.py tests/test_mind_api.py tests/test_chat_api.py tests/test_maintenance.py -q`
  (`50 passed`).
- Full backend suite passed from `backend`: `.venv/bin/python -m pytest -q`
  (`65 passed`).
- Frontend production build passed:
  `npm --prefix frontend run build`.
- `git diff --check` passed.
- Direct Scarlet test on a temporary SQLite database passed:
  Scarlet answered from the expected semantic memory and the `memory.context`
  trace reported completed local shadow retrieval over the same memory target.

Notes:

- `local_hash_embedding_v1` is only a deterministic plumbing vector and is not
  a real semantic embedding model.
- Milvus Lite remains optional and is not required for base runtime or tests.
- V1.4 should only activate hybrid ranking after selecting and validating a
  real embedding provider.
