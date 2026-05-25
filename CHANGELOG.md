# Changelog

All meaningful project changes are tracked here.

This project uses a practical changelog rather than a release-only log: each meaningful commit should map to an entry under `Unreleased` or a dated release section.

## Unreleased

### Added

- Added V1.0.1 project governance:
  - `docs/project-documentation.md` as the main documentation index;
  - `docs/development-process.md` for scoped versioned implementation;
  - `docs/branches/` with vertical documents for Scarlet's agentic operating
    branches;
  - ADR-0036 for branch documentation and the V1.0.1 development protocol.
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
- Added ADR-0015 documenting that the current laboratory SQLite state is versioned in Git while secrets remain excluded.
- Added ADR-0016 and EXP-0008 for Memory Context Pipeline v0, the planned automatic per-turn memory retrieval and runtime-context phase.
- Added the first Memory Context Pipeline v0 runtime slice:
  - automatic `memory.context` traces before `llm.request`;
  - backend-generated `<runtime_context>` injection;
- Added stratified runtime context blocks:
  - `runtime.context` trace and `runtime.context.built` event;
  - `session_context`, `message_context`, and `scarlet_state` blocks inside
    `<runtime_context>`;
  - streamed `runtime_context` event for the cockpit;
  - frontend rendering for runtime-context block summaries.
  - human-readable cockpit cards for runtime context, automatic memory,
    session recall, schema, metacognition, public notes, and API Mind
    results, with raw JSON moved behind closed code/detail toggles;
  - lexical v0 relevance guard with `selected`, `near_miss`, `excluded`, and conflicts;
  - streaming `memory_context` events for the cockpit.
- Added `docs/memory-roadmap.md` as the detailed roadmap for robust API/CLI-first memory.
- Added ADR-0017 for evolving memory toward response-control, lifecycle APIs, atomic facts, retrieval quality, compaction, and CLI/debug views.
- Added EXP-0009 as the memory robustness evaluation umbrella.
- Added the Memory Lifecycle M2 slice:
  - implemented `GET /mind/memory/{memory_id}`;
  - implemented `GET /mind/memory/conflicts`;
  - implemented `POST /mind/memory/deprecate`;
  - implemented `POST /mind/memory/supersede`;
  - added traceable lifecycle metadata and conflict inspection;
  - added regression coverage for supersession, deprecation, active search after repair, and lifecycle aliases.
- Added the Memory Atomic Facts M3 slice:
  - added the `memory_facts` table;
  - implemented `GET /mind/memory/facts`;
  - implemented `POST /mind/memory/facts/backfill`;
  - added deterministic entity/predicate/value extraction for recognized memory patterns;
  - added multilingual/alias canonicalization for Zero-Luce response-format facts;
  - added fact-aware search, read, context, conflict, deprecate, and supersede payloads;
  - added regression coverage for alias queries, fact conflicts, backfill traces, and fact-level supersession links.
- Added a prompt-level `Manual Memory Retrieval Cues` slice so Scarlet treats
  natural continuity, temporal, personal, project, uncertainty, source-sensitive,
  and synonym/language-drift phrases as triggers for manual semantic or
  episodic retrieval when automatic memory context is not enough.
- Added endpoint-local `usage_guide` responses for recoverable Mind API errors
  and changed `/mind/schema` into a compact route/capability catalog rather
  than a full parameter manual.
- Added temporal and sparse memory retrieval:
  - backend-resolved `time` filters for `POST /mind/memory/search` and
    `GET /mind/sessions`;
  - SQLite FTS5/BM25 sparse search documents for memories and sessions;
  - automatic memory context now traces `fts5_sparse_v1` retrieval stages;
  - entity-support guards so wrong-entity lexical matches stay in `near_miss`
    instead of becoming selected memory evidence.
- Added ADR-0019 for treating API Mind as Scarlet's internal cognition rather than a user-operated tool.
- Added dashboard recent-session history:
  - implemented `GET /api/chat/sessions` for newest persisted sessions;
  - added a ChatGPT-style sidebar history that shows session titles rather than
    raw IDs;
  - added session reopening so the cockpit reloads persisted messages and
    sends new turns into the selected session.
- Added Cognitive API single-metacognition slice:
  - schema version/digest, route examples, and schema policy in `GET /mind/schema`;
  - `mind_schema` reference in chat runtime context;
  - LLM-backed `POST /mind/metacognition/step`;
  - backend schema annotation on metacognition recommended actions;
  - one internal JSON repair retry for malformed metacognition reviews;
  - alias normalization for common metacognition inputs such as `prompt`,
    `goal`, and `context`;
  - `mind.metacognition.step` traces;
  - `docs/cognitive-api-roadmap.md`;
  - `cognitive_api_metacognition_probe` scripted eval scenario;
  - ADR-0020 and EXP-0011 for the one-route metacognition experiment.
- Added Episodic Session Recall:
  - `session_summaries` table;
  - implemented `GET /mind/sessions`;
  - implemented `GET /mind/sessions/{session_id}`;
  - implemented `POST /mind/sessions/{session_id}/summarize`;
  - added `mind.sessions.summarize` traces;
  - connected semantic memory provenance through `source_session_id` to full
    transcript recall;
  - updated Scarlet's prompt with semantic-vs-episodic memory discipline;
  - added ADR-0021 and EXP-0012.
- Removed `max_messages` from episodic session summarization so summaries are
  generated from the complete `user`/`assistant` message history instead of a
  partial tail.
- Backfilled episodic summaries for all 46 pre-existing laboratory sessions,
  summarized the new autonomy-probe session afterward for final 47/47 coverage,
  and recorded that Scarlet can follow `source_session_id` on a
  provenance-focused follow-up, but does not yet do so reliably on the first
  natural verified-baseline question.
- Hardened Scarlet's system prompt with explicit epistemic curiosity,
  confidence categories, autonomous API Mind use examples, and mandatory
  source-session checks for memory-derived baseline or recommendation claims.
- Recorded a post-hardening live probe where Scarlet opened the source session
  on the first natural verified-baseline question, recovered from one
  metacognition body-shape error through `/mind/schema`, and exposed a new
  monitored Italian foreign-script artifact.
- Added Scarlet's public work notes prompt policy so non-trivial internal
  activity should be narrated with concise natural progress notes instead of
  remaining silent until the final answer.
- Recorded autonomous public-work-note probes showing prompt-only compliance is
  not yet reliable: MiniMax can emit public notes when asked, but Scarlet still
  answered some current capability questions from runtime context without the
  expected schema call.
- Reworked the debug cockpit assistant timeline to render structured activity
  blocks for automatic memory context, public notes, tool calls, tool results,
  schema/session/metacognition evidence, and final answers instead of relying
  on raw JSON blocks inside the chat.
- Added a switchable LLM provider layer for MiniMax/Qwen comparison:
  - `LLM_PROVIDER=minimax|qwen`;
  - Qwen provider wrapper for Alibaba Model Studio's Anthropic-compatible API;
  - provider-agnostic active model and token budget helpers;
  - health/debug/chat/Mind API/summarization/metacognition wiring;
  - regression coverage for provider selection and Qwen missing-key behavior.
- Added a runtime event spine for agentic execution:
  - `events` table and repository helpers;
  - ordered turn, memory-context, model-request, tool-call, public-note, and
    final-answer events;
  - `GET /api/debug/events` for turn/session event inspection;
  - compact recent events in the next turn's runtime context;
  - cockpit rendering from structured events before falling back to traces;
  - regression coverage for chat, stream, direct Mind API, and storage events.
- Added `docs/project-state.md` as the canonical current-state and convergent
  roadmap map across provider runtime, memory, episodic recall, metacognition,
  events, UI, evaluation, planned work, and priority ordering.
- Added session idle maintenance:
  - `maintenance_jobs` table and repository helpers;
  - backend worker through FastAPI lifespan;
  - per-session idle scheduling after `turn.completed`;
  - stale-job supersession/skip behavior when a newer turn exists;
  - summary refresh plus report-only missed semantic memory review;
  - `maintenance.job.*` and `maintenance.memory_review.completed` events;
  - structured cockpit labels for maintenance events;
  - ADR-0031 and EXP-0018.
- Recorded direct MiniMax P1 probe evidence where idle maintenance caught a
  missed semantic memory write, plus BUG-0032 for pseudo tool-call markup in
  final assistant text.
- Recorded EXP-0019 with three integrated direct Scarlet probes across semantic
  memory, episodic recall, streaming runtime events, schema inspection, conflict
  inspection, and idle maintenance review.
- Opened BUG-0033 for runtime-context overinterpretation when Scarlet compares
  non-equivalent fields such as capability count and schema route count.
- Recorded EXP-0020 with natural conversation probes that do not force tool use,
  confirming personal memory personalization, project-continuity retrieval,
  and autonomous memory write on a real preference.
- Opened BUG-0034 for invalid natural `GET /mind/memory` calls and BUG-0035
  for stale memory overriding current runtime state.
- Recorded EXP-0024 runtime-context block comprehension probes, confirming
  Scarlet receives the block payload before provider calls, can use time,
  block identity, recent-session context, and user-profile memories, while
  exposing monitoring items around language hints and retrieval/profile
  divergence.
- Added dashboard runtime preferences and Tailwind cockpit rework:
  - `GET/PUT /api/dashboard/settings`;
  - `GET /api/dashboard/memories`;
  - `GET /api/dashboard/profile`;
  - persistent `app_settings`;
  - configured single-clock runtime context using `temporal_context.now`;
  - platform language setting replacing automatic `language_hint`;
  - operational active profile id, user privacy scope, and configured
    country/locale injected into `message_context`;
  - Tailwind-based dashboard tabs for Agent Stream, Memorie, Profilo, and
    Impostazioni;
  - viewport-bounded shell with internal scrolling for session history, chat,
    dashboard lists, agent stream, and trace drawers.

### Changed

- Set app metadata baseline to V1.0.1 for backend and frontend packages.
- Updated project next steps to start from Git/repository setup and backend scaffolding.
- Connected the local repository configuration to `https://github.com/panicDa3m0n/llm-api-mind.git` and documented the remaining HTTPS push authentication blocker.
- Confirmed local `main` is synchronized with `origin/main` after the human owner completed the push.
- Confirmed non-interactive HTTPS push works from the local development environment.
- Replaced the temporary smoke-test token budget with configurable `MINIMAX_MAX_TOKENS`, aligned with MiniMax M2.7 agentic usage instead of token-saving assumptions.
- Raised the MiniMax M2.7 default completion budget to `MINIMAX_MAX_TOKENS=131072` and lifted chat/debug request validation to the documented maximum completion budget.
- Routed Anthropic-compatible provider calls through SDK streaming internally for both streaming and non-streaming backend response shapes, so Scarlet's runtime has one agentic execution path.
- Treated events as an internal runtime control plane rather than adding a new
  model-facing Mind API endpoint; traces remain the deep forensic layer.
- Streamed persisted `CognitiveEvent` rows as live `runtime_event` updates so
  the cockpit can show exactly which backend events activate during a turn.
- Reworked the cockpit's right pane from a raw trace-first view into a live
  agent stream with event/tool/memory/active counters, structured timeline
  cards, collapsible thinking, readable runtime-event metadata, and raw traces
  moved into a forensic drawer.
- Added a previous-turn continuity check to Scarlet's prompt so missed memory
  promises or recognized semantic candidates can be repaired at the beginning
  of a later turn.
- Updated README, blueprint, memory roadmap, and cognitive API roadmap to point
  to `docs/project-state.md` for integrated current-state orientation.
- Removed stale planned `/mind/events/emit` from the model-facing Mind API
  schema and advanced the schema version to `2026-05-23.runtime-events-v1`.
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
- Changed repository ignore policy so `backend/data/app.db` is an intentional cross-machine laboratory artifact.
- Recorded direct adaptive Memory v0 verification and updated the immediate roadmap toward lifecycle semantics and search relevance filtering.
- Updated the immediate roadmap to prioritize automatic memory context evidence before adding more memory lifecycle endpoints.
- Updated Scarlet's prompt with a runtime-context contract for future backend-provided memory context and capability state.
- Updated the frontend operation timeline to show automatic memory context from streams and persisted traces.
- Recorded the first live adaptive Memory Context Pipeline v0 evaluation, confirming automatic memory context fixes the Zero-Luce follow-up recall case while exposing a new answer-control risk around memory conflicts and unavailable lifecycle capabilities.
- Updated the immediate roadmap toward a Memory Context Pipeline v0.1 response-control slice before additional memory lifecycle endpoints.
- Recorded a live terminal bilateral verification session showing proactive Zero-Luce conflict disclosure, partial correction of unavailable lifecycle-action phrasing, and a new design tension between response-control-first and lifecycle-first next steps.
- Recorded a metacognitive bug-probe terminal session showing wrong-entity memory selection for Nebbia-Rossa, source-suppression override of conflict disclosure, and unreliable self-classification of answer-control failures.
- Updated the memory roadmap after reviewing `jrcruciani/obsidian-memory-for-ai`, adapting atomic facts, controlled predicates, lifecycle, lint/views, inbox/compaction, and reflect-after-session ideas to the project's API/CLI-first design.
- Reframed current metacognitive probe findings as memory robustness limitations rather than claims of expected LLM cognitive perfection.
- Put response-control M1 on hold per owner direction and moved the immediate memory roadmap to M3 atomic facts after M2 lifecycle verification.
- Recorded live Memory Lifecycle M2 verification in `backend/app/evals/runs/20260520_152457_interactive`, including Zero-Luce conflict supersession and deprecated-memory inspection.
- Updated Scarlet's system prompt and Mind API schema to expose memory read, conflicts, deprecate, and supersede as implemented capabilities.
- Recorded live Memory Atomic Facts M3 verification in `backend/app/evals/runs/20260520_160345_interactive`, including backfill, English/Italian alias fact lookup, and deprecated fact handling.
- Updated the immediate memory roadmap to M4 entity-aware retrieval now that the first lifecycle and atomic fact layers are implemented.
- Updated Scarlet's system prompt to prefer canonical facts for entity, predicate, status, and value when memory payloads include facts.
- Reframed Scarlet's system prompt around API Mind as internal cognition: autonomous schema/memory/fact/conflict use before answers, user independence from endpoint knowledge, and an explicit evidence hierarchy.
- Hardened Scarlet's prompt so validation errors should trigger schema inspection instead of repeated request-shape guessing, and historical facts should use `include_inactive=true`.
- Changed chat turns to use `tool_loop_policy=model_controlled_unbounded` instead of the previous fixed MiniMax tool-call cap.
- Changed the dashboard current-session display to use the readable session
  title instead of making the session ID the primary visible label.
- Updated Scarlet's system prompt so visible metacognition is treated as a
  public summary layer, while internal metacognition goes through the single
  LLM-backed `/mind/metacognition/step` route.
- Consolidated cognitive API design by removing parallel validation,
  blackboard, and reflection routes from the current schema.
- Removed planned standalone reflection review from the active Mind API plan;
  reflection currently belongs inside `/mind/metacognition/step`.
- Added model-facing temporal runtime context so Scarlet receives backend
  turn-start time in UTC and local runtime time before each answer.
- Refined Scarlet's system prompt with perception/source-of-truth contracts:
  API Mind as operative subconscious, temporal context as the only operational
  clock, and paginated session lists as non-exhaustive evidence.
- Documented a new memory-context retrieval risk where generic token overlap can
  select a semantically weak memory for broad episodic questions.
- Strengthened Scarlet's system prompt with an engineering agent quality gate:
  verify before conclude, prefer more internal iterations for source-sensitive
  answers, avoid overclaiming from paginated lists/summaries, and inspect
  schema before improvising metacognition bodies.
- Switched the local runtime back to MiniMax for the post-prompt comparison and
  recorded live MiniMax evidence against the Qwen baseline.
- Documented BUG-0023: MiniMax can identify unsupported absence overclaims in
  self-critique and still reassert one in the final conclusion.
- Added pre-final semantic memory consolidation to Scarlet's prompt so stable
  preferences, corrections, decisions, milestones, validation moments, and
  durable constraints are written autonomously instead of treated as opt-in.
- Recorded live semantic-consolidation probes where Scarlet wrote a V2.1
  milestone and report-format preference autonomously, plus residual issues
  around write announcements, stale model-supplied provenance metadata, and the
  unavailable `/mind/memory` route attempt.
- Documented the Mind API deterministic-field ownership audit: backend should
  own ids, timestamps, trace/session/turn/message provenance, lifecycle
  timestamps, usage, and summary coverage, while Scarlet supplies only
  cognitive content, queries, selected ids, reasons, filters, and prompts.
- Strengthened Scarlet's semantic-memory prompt so memory is framed as a living
  internal cognitive state: facts, annotations, checkpoints, labels, concepts,
  constraints, and sourceable anchors may be written autonomously and silently
  when useful for future sessions.
- Documented a live semantic-memory residual where Scarlet recognized a
  chocolate preference as worth remembering and said "Lo terrò a mente" but did
  not call `memory.write`.
- Started `EXP-0015`, a reversible prompt-only memory-forcing experiment that
  requires every Scarlet turn to include an execution phase plus mandatory
  verification phase before final answer, and makes recognized semantic memory
  candidates action-binding through `POST /mind/memory/write`.
- Recorded the first `EXP-0015` rerun failure: Scarlet again recognized a
  chocolate preference/health constraint as useful personal memory but did not
  call `memory.write`, exposing a remaining project/agent-behavior memory bias
  in prompt/schema examples.
- Updated `EXP-0015` with a personal semantic memory taxonomy so Scarlet treats
  user personal facts, names, relationships, food/health constraints, life
  events, discoveries, errors, solutions, and workarounds as first-class
  semantic memory candidates.
- Confirmed the `EXP-0015` prompt solution in live use: Scarlet wrote the
  chocolate limit as a `user_preference` memory, then automatically retrieved it
  in a later session through `memory.context`.
- Added provider-native session history for MiniMax/Anthropic-compatible
  multi-turn continuity: chat sessions now persist `provider_history_json`,
  future turns send native content blocks instead of text-only reconstruction,
  and `llm.request` traces expose provider-history source and size stats.
- Recorded live `EXP-0016` probes confirming provider-native history preserves
  both `GET /mind/schema` and `POST /mind/memory/write` tool-use/tool-result
  sequences across turns.

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
- Fixed MiniMax-shaped `mind_api` wrapper handling by accepting `raw_input`, JSON-string `body` values, body-level `intent`, and Italian memory aliases observed in direct chat traces.
- Fixed Memory Lifecycle M2 response serialization so lifecycle handlers do not return detached SQLModel records after session close.
- Fixed the observed lifecycle alias gap by accepting `target_id` plus `superseded_by` for memory supersession.
- Fixed fact backfill after existing lifecycle operations so fact-level supersession links are rebuilt from memory lifecycle metadata.
- Fixed the trace-only time gap where turn time existed in `memory.context` but
  was not exposed inside the model-facing `<runtime_context>`.
- Removed the obsolete prompt-level `Visible Metacognition Experiment` block so
  public work notes and `/mind/metacognition/step` no longer compete as two
  different visible-metacognition concepts.
- Fixed lossy cross-turn provider history where tool-use/tool-result blocks
  were stored in traces but not rehydrated into the next MiniMax request.

## Release Notes Policy

Each release section should answer:

- What changed?
- Why did it change?
- Which roadmap phase, experiment, or decision does it support?
- How was it verified?
