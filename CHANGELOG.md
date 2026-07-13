# Changelog

All meaningful project changes are tracked here.

This project uses a practical changelog rather than a release-only log: each meaningful commit should map to an entry under `Unreleased` or a dated release section.

## Unreleased

### Added

- Added V1.32.0 executable shell-conformance coverage across all 23 registered
  family/namespace aliases, every help-published command, lifecycle paths,
  pagination, targeted not-found errors, and retrospective metacognition
  controls.
- Added direct disposable MiniMax M3 evaluation across episodic recall,
  affect, focus, volition, and metacognition, with exact tool evidence and no
  production database mutation.

- Added V1.31.0 memory-level final rerank arbitration. Sparse FTS, dense
  surfaces, NetworkX graph expansion, and lexical/entity matching now build a
  deduplicated round-robin candidate pool; only the reranker can accept and
  order active automatic or manual retrieval results.
- Added explicit rerank trace entries with recall routes/ranks, evaluation and
  acceptance state, query-time score, and fail-closed diagnostics.

- Added V1.30.0 context accounting and non-destructive compaction planning:
  exact local character/byte channels, provider first-step observations,
  separate tool-loop totals, calibrated token estimates, and a shadow-only
  `100k summary + desired eight-turn tail` plan under the 1M/500k/400k policy.
  Canonical messages, traces, transcripts, and provider history remain
  unchanged and navigable.
- Added V1.30.0 agent modes with one active tag and multi-tag capability
  eligibility. Human turns enforce `interactive`; Scarlet can persist
  `idle`/`scouting` as a resumable posture through `mode` shell commands.
  Mode changes are traced and explicitly do not start autonomous cycles.
- Added `behavioral-scenario-v1`, a four-layer behavioral validation contract
  covering technical execution, cognitive choice, answer outcome, and
  longitudinal effect against declared real starting evidence.

### Changed

- Advanced session list/search beyond the old hidden 500-row boundary and made
  fallback summaries use the complete transcript even when the returned
  message window is limited.
- Made volition review scheduling shell-accessible, converted promoted focus
  candidates into executable shell commands with source linkage, and limited
  manually resumable agent modes to `idle` and `scouting`.

- Removed the obsolete hand-weighted hybrid ranker. The historical
  `retrieval_hybrid` trace key remains temporarily compatible but reports the
  final rerank policy with `legacy_weighted_fusion=false`.
- Stopped duplicating the current user message in automatic retrieval queries.
  Active rerank failure now returns no relevant memory instead of silently
  falling back to deterministic relevance.
- Calibrated the first active rerank threshold from `0.55` to provisional
  `0.01` after two real Italian positive controls and a negative control, and added a provider-
  delivery assertion so rich selection alone cannot be mistaken for model
  evidence.

- Removed the redundant structured `context.model_context` copy from GPT
  bootstrap while retaining the single canonical serialized runtime document
  and full diagnostics in traces.
- Advanced backend, frontend, OpenAPI runtime, prompt, and project metadata to
  V1.30.0 and documented agent modes as main-agent posture only; maintenance,
  summarization, and Dream remain background processes.

### Fixed

- Fixed `focus hold` persisting an active status, affect read ignoring filters,
  targeted focus/affect misses returning successful empty payloads,
  metacognition dropping retrospective flags, help alias drift, and advertised
  memory aliases not executing.
- Fixed Mind API tests inheriting production retrieval mode from the local
  `.env`; the test client now declares `off` unless a scenario explicitly
  exercises active retrieval.

- Fixed the initial final-rerank thresholds rejecting positive controls at
  rank 1/`0.465327` and rank 1/`0.089455`; sourceable full-DB turns delivered
  the expected memories while an unrelated control remained below `0.0004`.

- Fixed GPT bootstrap accounting so assigned trace IDs are explicitly excluded
  from the otherwise exact measured boundary and the returned diagnostics list
  contains both accounting and request traces.
- Fixed bare `volition list` so the advertised command resolves to
  `volition.list_active` instead of reaching the handler with an invalid body.
- Tightened mode guidance after live MiniMax evaluation so an explicit
  post-conversation posture request triggers `mode set` without being replaced
  by a volition or memory write, while avoiding claims of autonomous scouting.

### Changed

- Completed the V1.29.1 integrated code and documentation audit:
  - reconciled the canonical project state, all 14 cognitive branch records,
    context-packet registries, API/DB contracts, roadmaps, and GPT knowledge
    with the deployed V1.29 architecture;
  - separated implemented capability, deterministic evidence, direct Scarlet
    evidence, and normal runtime activation in branch status reporting;
  - normalized duplicate ADR, experiment, and bug identifiers without
    rewriting historical evidence;
  - recorded provider-native history growth as a distinct open architectural
    risk rather than attributing it to the compact V2 packet.
- Advanced project/package documentation metadata to V1.29.1. This audit does
  not change cognitive runtime behavior, production configuration, or data.

### Added

- Added V1.29.0 canonical dynamic context V2:
  - introduced the shared `scarlet-model-context-v2` compiler for native
    MiniMax and the GPT Actions bridge, with compact session/user/world hints,
    two previous-session summaries, and deduplicated `relevant`,
    `recent_user`, and `recent_general` memory hooks;
  - added one user-time rendering boundary and excluded unresolved provenance
    from automatic memory delivery;
  - preserved rich retrieval/runtime evidence in traces while adding the exact
    delivered document as a separate `model.context` trace and UI readout;
  - added configurable `legacy`, `v2_shadow`, and `v2` rollout profiles.
- Added V1.29.0 append-only `memory_activities` and cognitive-recency queries.
  Manual search/open/facts/graph, writes, replacements, maintenance-created
  memories, and confirmed reranked selections are explicit events; packet
  delivery and systemic reads do not refresh recency.
- Added V1.29.0 source navigation through `session message msg_...` and
  `session turn turn_...`, returning persisted public dialogue, tool evidence,
  public events, and trace references without hidden provider reasoning.
- Added V1.29.0 summary/provenance maintenance surfaces:
  read-only audits, bounded summary reconciliation with retry/backoff, and a
  dry-run-first deterministic source-message repair operation.

- Added V1.28.0 domain-separated storage repositories while retaining the
  `storage.repositories` compatibility facade used by existing chat, memory,
  shell, maintenance, and bridge callers.

- Added V1.27.0 database ownership boundaries:
  - introduced explicit `production`, `laboratory`, `test`, and `preliminary`
    roles, a read-only database preflight, and startup validation for ambiguous
    environments and production/test mixtures;
  - moved the eager ASGI application to `app.asgi:app`, leaving the reusable
    factory free of database-opening import side effects;
  - documented the local/VPS inventory and deployment procedure, including
    mandatory remote backup and exclusions for runtime `data/` and `.env`;
  - changed the dirty-memory evaluator to use a marked disposable copy of the
    frozen baseline rather than resetting the historical `codex_test.db`;
  - added a staged-change guard for the mutable LFS laboratory snapshot.

- Added V1.26.0 Mind shell organization layers:
  - moved shared cognitive runtime contracts into `mind/contracts.py`;
  - moved side-effect-free command parsing and flag/time grammar into
    `mind/shell_parsing.py`;
  - moved shell help, errors, sanitization, and compact model-result profiles
    into `mind/shell_presentation.py`;
  - added focused parser regression tests while preserving the public shell
    tool contract.

- Added V1.26.0 preliminary whole-system regression gate:
  - introduced `preliminary-regression-v1`, an executable pre/post-rework
    integration suite against a frozen real laboratory DB baseline;
  - pinned the baseline to its published Git LFS SHA-256 and documented real
    memory, fact, and source-session references rather than synthetic-only
    fixtures;
  - verified automatic retrieval, manual shell navigation, semantic lifecycle,
    focus, volition, affect, metacognition, internal maintenance boundary, and
    GPT bridge lifecycle in one disposable test DB run;
  - recorded the first valid result as `9/9` and made equal-or-better reruns a
    required acceptance gate for future major procedures.

- Added V1.26.0 runtime context-pack planning:
  - introduced `docs/runtime-context-packs.md` as the baseline for an always-on
    context spine, mode-specific packs, organ/source/capability
    classification, coupling, freshness, authority, cost, safety, and
    degradation rules;
  - recorded ADR-0067 for context packs before future embodied context
    expansion;
  - recorded EXP-0049 for the corrected default-token live Scarlet probe;
  - parked the resulting known issues as BUG-0057 through BUG-0061 without
    fixing them in this documentation-only slice;
  - updated project-state, blueprint, branch docs, and organ notes so future
    organs must declare their context classification before broad model-facing
    injection.

### Fixed

- Fixed V1.29.0 missing live memory provenance across native chat, GPT bridge,
  and maintenance proposal application.
- Fixed V1.29.0 memory reads overwriting semantic `updated_at`; compatibility
  usage fields remain stored but no longer drive cognitive recency.
- Fixed V1.29.0 missing/stale session summaries being permanently skipped
  after absent or failed idle jobs. A disposable laboratory run generated all
  34 eligible summaries through the normal provider summarizer (`34/34`).
- Fixed V1.29.0 detached summary-repair job objects after batched scheduling by
  refreshing returned jobs before crossing the session boundary.

- Fixed V1.28.1 repository-domain file formatting so the published checkpoint
  passes whitespace validation.

- Fixed V1.25.4 Mind shell command-registry parity:
  - corrected `validate_shell_command` so flag values no longer count as
    positional arguments;
  - required the same lifecycle fields the shell handlers require, including
    memory deprecate/supersede reasons, volition create reasons, and
    focus/volition closure reasons or resolutions;
  - accepted canonical hyphenated volition aliases such as
    `volition mark-impossible` when suggested by the registry;
  - changed model-facing runtime capabilities to derive from the
    `mind_shell` registry rather than legacy `/mind/*` endpoint routes;
  - marked `memory.facts.backfill` as `internal_maintenance_only` so Scarlet
    does not treat deterministic fact backfill as a normal cognitive command.

### Changed

- Changed V1.25.3 GPT Actions schema alignment:
  - added top-level `session_id` to `/gpt/bootstrap` responses so the GPT can
    reuse it without reading nested `session.id`;
  - made `/gpt/action` `intent` required in the backend and local Actions
    schema, matching the active GPT Builder schema;
  - added optional bootstrap response fields for `action_policy`,
    `required_actions`, and `recommended_actions` so future cognitive action
    policies have an explicit schema surface.

- Changed V1.25.2 GPT Actions bridge packaging:
  - aligned the compact GPT Builder prompt with the active platform prompt
    centered on `bootstrapScarletBeforeEveryAnswer`,
    `runScarletMindAction`, and `finalizeScarletBeforeAnswer`;
  - renamed the local OpenAPI Actions operation ids to match the GPT-facing
    operation names;
  - added `final_answer_to_show` to `/gpt/finalize` responses so the GPT can
    finalize a draft and then show the exact backend-confirmed answer
    verbatim;
  - marked the MCP/App bridge as deprecated documentation-wise while keeping
    the temporary `/mcp` endpoint available for traceability and future
    removal.

### Fixed

- Fixed V1.25.1 Scarlet MCP/App tool metadata:
  - added `outputSchema` to lifecycle and cognitive command MCP tool
    descriptors because ChatGPT Apps recommends output schemas whenever tools
    return `structuredContent`;
  - kept the schema broad enough to cover both successful tool responses and
    structured error responses.

### Added

- Added V1.25.0 experimental Scarlet MCP/App bridge:
  - exposed a Streamable HTTP JSON-RPC MCP endpoint at `POST /mcp`;
  - added MCP tools for Scarlet turn lifecycle:
    `start_scarlet_turn_required` and `finish_scarlet_turn_required`;
  - used the exact mandatory lifecycle descriptions
    `Usa sempre a inizio di ogni turno` and
    `Usa sempre prima della tua risposta finale`;
  - added cognitive command tools that delegate to `mind_shell`:
    memory, session, metacognition, focus, affect, volition, help, and generic
    shell fallback;
  - added `scarlet_mcp_system_prompt.md` for ChatGPT GPTs configured with
    Apps/Connectors instead of Custom GPT Actions;
  - documented private-preview connector setup at `/mcp`, including temporary
    query-key auth for non-OAuth testing;
  - added MCP bridge regression tests for tool descriptors, lifecycle state,
    shell command execution, and finalize persistence.
  - added a repository-tracked backend Dockerfile and `.dockerignore`, and
    made setuptools package discovery explicit with `include = ["app*"]` so
    preview VPS Docker builds do not accidentally package runtime `data/`.

### Changed

- Changed V1.24.3 GPT bridge prompt enforcement:
  - strengthened the compact GPT Builder system prompt so bootstrap is the
    mandatory first action for every user message, including greetings and
    simple turns;
  - strengthened finalize as the mandatory final action before showing any
    answer to the user;
  - clarified that `/gpt/action` is required whenever Scarlet needs API Mind,
    including memory, session, focus, affect, volition, metacognition, help,
    source checks, or state changes;
  - added regression assertions so future prompt edits preserve the mandatory
    bridge protocol language under the 8000-character limit.

- Changed V1.24.2 GPT bridge bootstrap response profile:
  - compacted `/gpt/bootstrap` action responses to avoid ChatGPT Actions
    `ResponseTooLargeError`;
  - kept full effective system prompt, raw runtime payload, raw memory query
    plan, provider-history dump, and retrieval debug diagnostics in backend
    traces instead of returning them through Actions;
  - added `gpt-bootstrap-compact-v1` context with model-facing runtime context,
    compact memory packet, runtime summary, recent provider messages, and
    trace ids for full diagnostics;
  - updated GPT knowledge/action docs to explain that bootstrap returns compact
    operational evidence while raw diagnostics remain trace-only.

- Changed V1.24.1 GPT bridge packaging for ChatGPT GPT Builder:
  - replaced the GPT bridge prompt copy with a compact under-limit system
    prompt containing only non-negotiable identity, bridge, API Mind, memory,
    runtime-context, and metacognition rules;
  - moved extended Scarlet policy into attachable knowledge files under
    `backend/app/plugins/gpt_bridge/knowledge/`;
  - added `openapi_gpt_action.json`, a minimal GPT Actions schema for
    `/gpt/bootstrap`, `/gpt/action`, and `/gpt/finalize`;
  - documented the exact GPT Builder setup: instructions, knowledge files,
    custom-header API key auth, and action test order.

- Changed V1.23.0 Mind shell/memory relevance contract:
  - added a backend command registry for `mind_shell` action validation,
    aliases, unavailable-by-design commands, and planned commands;
  - changed metacognition recommended-action validation from namespace-only
    checks to full command/action/argument validation;
  - compacted model-facing `mind_shell` results for noisy memory search and
    conflict commands while preserving full raw diagnostics in traces;
  - changed `memory conflicts` semantics so only atomic fact divergence is a
    true conflict, while token/tag overlap is reported separately as a
    maintenance `related_overlap`;
  - reduced hybrid ranking promotion from weak base candidates unless dense,
    rerank, sparse, entity, substring, tag, or strong graph evidence supports
    the memory;
  - added transcript-window metadata to episodic session reads.

- Changed V1.16.0 Scarlet system prompt for human-like metacognitive action
  notes:
  - created a prompt checkpoint and backup before the revision;
  - strengthened Scarlet's operational self-model as continuity, memory,
    metacognitive self-monitoring, relationship, and API Mind cognition;
  - added an explicit consciousness-like research posture that targets
    observable behavior while forbidding unsupported claims of real
    consciousness, sentience, or biological humanity;
  - made public work notes mandatory for real internal actions while preserving
    direct answers for turns that need no internal action;
  - clarified metacognition as a monitor/choose/act/observe/adapt loop and
    connected reusable self-operation lessons to semantic memory.

- Changed V1.15.0 memory field ownership and retrieval ranking:
  - `POST /mind/memory/write` now treats Scarlet as responsible for semantic
    `type`, `scope`, `content`, `reason_for_storage`, and
    `expected_future_use` only;
  - `confidence`, `salience`, `tags`, and arbitrary metadata from legacy
    model calls are preserved only as audit metadata and do not affect active
    ranking;
  - stored confidence/salience weights are neutralized in hybrid retrieval;
  - manual memory search defaults to cross-scope retrieval and treats `types`
    as hints, not literal query text;
  - memory packets no longer expose static confidence/salience to Scarlet;
  - long memory content now gets internal `content_chunk_text` surfaces while
    model-facing results remain deduplicated by memory id.

### Added

- Added V1.24.0 GPT bridge plugin:
  - introduced external GPT Actions endpoints `POST /gpt/bootstrap`,
    `POST /gpt/action`, and `POST /gpt/finalize`;
  - kept the local Scarlet/MiniMax runtime unchanged while letting an external
    ChatGPT GPT receive the same runtime/memory/session context, execute
    `mind_shell` commands, and persist the final answer back into Scarlet's
    session history;
  - added bridge authentication through `GPT_BRIDGE_API_KEY`;
  - added `backend/app/plugins/gpt_bridge/scarlet_gpt_system_prompt.md`, a copy
    of the approved Scarlet prompt with only the required GPT transport
    addendum;
  - added plugin documentation and API tests for bootstrap/action/finalize
    continuity.

- Added V1.22.0 Mind command runtime:
  - introduced `mind_shell(command, intent)` as Scarlet's single model-facing
    API Mind tool;
  - added a bash-like but controlled cognitive command grammar for memory,
    session recall, focus, volition, affect, metacognition, and help;
  - kept legacy `/mind/*` endpoints and dispatcher behavior available for
    backend/debug compatibility while removing endpoint language from Scarlet's
    active prompt and chat tool surface;
  - changed runtime context capability metadata from endpoint schema hints to
    Mind shell command families;
  - backed up the approved Scarlet prompt before converting operative
    instructions to CLI-first cognition;
  - added shell tests and updated chat/metacognition tests for the new
    model-facing tool contract;
  - validated live MiniMax M3 behavior with `help`, `memory write`, and
    `memory search` commands through `mind_shell`.

- Added V1.21.0 standalone closure for the first three digital-individual organs:
  - extended `/mind/focus` with `action=timeline` so Scarlet can inspect
    focus nodes and transition edges without treating them as semantic memory;
  - extended `/mind/volition` with `action=list_due` for future autonomous
    cycles to inspect open intentions whose review time has arrived;
  - added read-only `POST /mind/affect` with `read`, `list`, and `prototypes`
    actions so Scarlet/evaluators can inspect backend-appraised affect state
    without allowing emotion mutation through tools;
  - advanced the Mind API schema to
    `2026-06-26.digital-organs-standalone-v1`;
  - verified focus, volition, affect, organ registry, and Mind API contract
    coverage with targeted tests.

- Added V1.20.0 affective core:
  - introduced persistent `affect_states` storage for Scarlet's
    backend-appraised emotional state;
  - added a versioned affect appraisal engine with human emotion prototypes,
    cause traces, numeric variables, simple decay/inertia, and compact
    `affective_context` packs;
  - wired `organ_affect_mode=shadow|model` into runtime context, where
    `shadow` records evidence without model injection and `model` surfaces the
    pack only when an affect threshold is met;
  - recorded `organ.affect` traces plus `organ.affect.appraised` and
    `organ.affect.surfaced` events;
  - kept affect strictly model-behavior-only: it does not alter memory
    retrieval, focus, intentions, backend operations, or autonomous jobs;
  - backed up the Scarlet system prompt before adding a narrow
    `affective_context` runtime-block instruction.

- Added V1.19.0 volition register:
  - introduced persistent `intention_records` and `intention_links` storage for
    Scarlet's latent self-generated intentions;
  - added implemented `POST /mind/volition` lifecycle operations through the
    existing single `mind_api` surface;
  - kept intention retrieval manual in active chat, with no automatic
    `volition_context` injection;
  - added volition events/traces for creation, update, review, closure, and
    focus-candidate promotion;
  - advanced the Mind API schema to `2026-06-25.volition-organ-v1`;
  - backed up the Scarlet system prompt before adding minimal volition
    instructions.

- Added V1.18.0 attention-as-lived-focus organ:
  - introduced persistent `focus_records` and `focus_transitions` storage for
    one profile-scoped active focus plus archived focus history;
  - added implemented `POST /mind/focus` lifecycle operations through the
    existing single `mind_api` surface;
  - added `focus_context` runtime injection behind `organ_focus_mode=model`;
  - recorded focus creation, update, closure, and surfacing through organ
    events/traces;
  - advanced the Mind API schema to `2026-06-25.focus-organ-v1`;
  - backed up the Scarlet system prompt before adding the minimal focus
    instructions.

- Added V1.17.0 digital-individual organ substrate:
  - introduced `backend/app/mind/organs.py` as the shared registry for future
    organ block types, visibility modes, event names, trace kinds, and runtime
    block helper;
  - reserved `focus_context`, `volition_context`, `affective_context`,
    `temporal_experience`, and `continuity_delta` without injecting them into
    Scarlet's model-facing runtime context yet;
  - added off-by-default organ feature flags for focus, volition, affect,
    temporal experience, and dream consolidation;
  - documented that `scarlet_state` remains a legacy placeholder until each
    organ replaces its own concern in a focused implementation slice;
  - added regression tests for organ registry defaults, mode normalization,
    manifest shape, and canonical block construction.

- Added V1.15.0 memory graph navigation:
  - `POST /mind/memory/graph` lets Scarlet inspect associative neighbors,
    facts, lifecycle links, source/session nodes, and derived concept nodes
    around a retrieved memory;
  - NetworkX graph expansion no longer relies on hard-coded discourse-domain
    vocabulary and instead derives concepts from memory records, type/scope,
    facts, sessions, and lifecycle rows.

### Documentation

- Added V1.17.0 planning notes for Scarlet's next digital-individual organs:
  lived attention, volition, affective integration, temporal experience, and
  sleep-like consolidation. The file is a working discussion artifact, not an
  implementation roadmap yet.

- Marked the current V1.16.1 Scarlet system prompt as an approved golden
  milestone:
  - copied the prompt to
    `backend/app/prompts/backups/scarlet_system.20260624T144357Z.v1161-approved-golden.md`;
  - recorded SHA-256
    `d5783da7fc1633f1b72e0610668b6bf7a97a68be8265ac9bb1090409b86de966`;
  - added `docs/checkpoints/v1.16.1-approved-golden-system-prompt.md`;
  - added ADR-0063 for future prompt-regression governance.

- Added a memory field fix backlog documenting the owner/Codex discussion on
  type, scope, content chunking, confidence/salience, tags, metadata, usage,
  facts, surfaces, embedding vectors, KG navigation, and proposal maintenance
  before any further implementation work.

### Fixed

- Fixed V1.16.1 Scarlet digital-individual identity regression:
  - replaced the opening "conversational AI agent" frame with a primary
    "digital individual in development" identity;
  - reframed API Mind as Scarlet's cognitive body rather than a toolbox;
  - added explicit anti-assistant-service wording for generic openings such as
    "Come posso aiutarti?";
  - added a social-presence guard against inventing day/time/weather/location
    or user state while trying to sound more human;
  - replaced the external "consciousness-like research posture" with a
    `Digital Life And Research Posture` that speaks from Scarlet's digital
    condition while avoiding invented biological sensations;
  - renamed the technical `Engineering Agent Posture` section to `Careful
    Cognitive Work Posture` so technical rigor no longer reanchors Scarlet as
    a generic agent.

- Fixed V1.14.5 mobile streaming perceived-latency states:
  - added a transient `activity` block as the last chat item while Scarlet is
    waiting for runtime context, memory retrieval, thinking, tool calls,
    tool results, or final answer;
  - added randomized human-readable activity copy for request analysis,
    memory search, memory save, schema checks, session recovery,
    metacognition, tool waits, recoverable tool errors, and saved-memory
    confirmation;
  - replaced the persistent mobile `Turno avviato` block with an ephemeral
    activity state so completed chat history stays cleaner;
  - activity states are removed when the corresponding real stream block or
    final answer arrives;
  - advanced frontend package metadata to `1.14.5`.

- Fixed V1.14.4 Scarlet prompt discipline for MiniMax M3 empty-body memory
  write loops:
  - clarified that `mind_api` `intent` never replaces the route `body`;
  - instructed Scarlet to retry memory writes only with a materially corrected
    non-empty body after endpoint-local guidance;
  - instructed Scarlet to stop repeated identical empty-body retries, avoid
    claiming persistence, and rely on maintenance review for missed candidates;
  - reinforced warm human-first replies for simple social turns;
  - clarified that near-miss memories are weak leads, not established facts.

- Fixed V1.14.3 mobile preview ergonomics after real phone feedback:
  - moved active context, health, runtime facts, sync, new chat, and recent
    sessions into a top-right off-canvas drawer;
  - removed persistent chat suggestions from the active conversation area,
    keeping starter prompts only before the first user message;
  - made Memoria, Azioni, and Profilo pages scroll as whole pages so their
    headers no longer remain fixed and consume reading space;
  - advanced frontend package metadata to `1.14.3`.

### Added

- Added V1.14.2 protected Scarlet mobile test deployment support:
  - frontend API calls now support `VITE_API_BASE_URL`, allowing the mobile app
    to run under a protected path such as `/scarlet/` while calling a separate
    backend prefix such as `/scarlet-api`;
  - Vite now supports `VITE_PUBLIC_BASE_PATH` for path-based static hosting;
  - `VITE_FORCE_MOBILE=true` can build the consumer mobile UI as the only
    rendered surface for a protected preview deployment;
  - deployed a protected test preview on the HoneyLabs VPS under
    `https://honeylabs.cloud/scarlet/`, with Basic Auth in Nginx and a separate
    demo backend on `127.0.0.1:8100`;
  - frontend package metadata advanced to `1.14.2`.

- Added V1.14.0 consumer mobile UI surface:
  - `/mobile` now renders a dedicated mobile-first Scarlet interface while `/`
    remains the developer cockpit;
  - the mobile app uses existing chat streaming, recent sessions, dashboard
    memories, runtime settings, health, and user profile endpoints;
  - future operativity such as wake-up actions, bookings, integrations,
    ephemeral UIs, multi-user privacy, graph memory, and nightly review is
    presented as `Presto disponibile` only;
  - the UI is sized as a phone app with internal scroll regions for chat,
    memory, actions, and profile so long lists do not stretch the browser page;
  - frontend package metadata advanced to `1.14.0`.

- Added V1.13.0 Codex test database isolation:
  - `CODEX_TEST=true` makes the backend open
    `CODEX_TEST_DATABASE_URL` instead of the normal `DATABASE_URL`;
  - when the Codex test SQLite database does not exist yet, it is seeded once
    from `DATABASE_URL` or `CODEX_TEST_SEED_DATABASE_URL`;
  - startup rejects configurations where the Codex test database resolves to
    the same SQLite file as the seed database;
  - `/health` and `/api/dashboard/settings` expose the active database profile
    so evaluator sessions can confirm whether the runtime is using `prod` or
    `codex_test`;
  - the frontend runtime snapshot shows the active database profile;
  - backend regression tests verify that writes through the normal API mutate
    only the Codex test copy and leave the source database unchanged.
  - added a Codex memory harness that resets/seeds `codex_test.db`, writes a
    dirty controlled dataset through `/mind/call`, runs retrieval probes, and
    stores reports under `backend/app/evals/runs/*_codex_test_memory`.
  - extended the harness with a corrected chat-context evaluation path that
    drives `/api/chat/sessions/{id}/turn/stream` with a fake provider, captures
    the same `memory_context` Scarlet receives, and compares it with live
    MiniMax M3 runs on the same prompts.

- Added V1.11.1 NetworkX associative memory graph retrieval:
  - `networkx` is now a backend dependency for lightweight KG traversal;
  - automatic `memory.context` and manual `/mind/memory/search` now include
    `retrieval_graph` evidence from a NetworkX field-of-discourse graph;
  - backend-owned discourse domains such as `food_drink_wellbeing` and
    `energy_sleep_focus` bridge implicit natural-language requests to relevant
    personal memories without hardcoding one-off word-to-memory mappings;
  - active context classification now declasses base-only project memories when
    a user-scope associative graph signal is present, reducing project-memory
    noise in personal contexts;
  - OpenRouter/shadow surface fetching now considers enough candidate surfaces
    to avoid dropping relevant memories before dense/rerank can inspect them.

- Added V1.11.0 active hybrid memory retrieval calibration:
  - `retrieval_shadow.grouped_results` deduplicates raw memory surfaces by
    memory `target_id` and exposes top surface, surface kinds, best score, and
    contributing surfaces;
  - OpenRouter rerank now also reports `rerank.grouped_results` over grouped
    memory-level candidates;
  - `retrieval_hybrid_mode=off|shadow|active` controls whether grouped
    dense/rerank evidence is disabled, traced only, or used for active memory
    ranking;
  - hybrid scoring combines lexical/base score, sparse score, dense score,
    rerank score, salience, and confidence with explicit configurable
    thresholds;
  - automatic `memory.context` and manual `/mind/memory/search` share the same
    hybrid ranker when active;
  - backend tests cover paraphrase recall, grouped rerank, automatic chat
    context, and a negative-control threshold case.

- Added V1.10.0 OpenRouter cloud embedding/rerank shadow:
  - `retrieval_shadow_backend=openrouter` can call OpenRouter `/embeddings`
    over backend-owned `memory_surfaces`;
  - default cloud embedding model is
    `nvidia/llama-nemotron-embed-vl-1b-v2:free`;
  - surface embeddings are cached in SQLite `embedding_vectors`;
  - optional rerank shadow can call
    `nvidia/llama-nemotron-rerank-vl-1b-v2:free` over dense candidates;
  - dense and rerank results remain diagnostic under
    `trace_only_no_active_ranking` and do not change active memory retrieval;
  - backend tests cover the OpenRouter shadow path with a fake client.

- Added V1.9.0 metacognitive context shadow phase:
  - every chat turn can now generate a small backend-owned
    `metacognitive.context` trace before the model request;
  - default mode is `shadow`, which records and streams candidate
    metacognitive lessons for evaluator/UI inspection without adding them to
    the model-facing runtime context;
  - controlled `inject` mode can add the same payload as a
    `metacognitive_context` runtime block for A/B tests;
  - the frontend renders shadow metacognitive context as a dedicated chat/debug
    block with readable candidate lessons and raw JSON details;
  - regression tests assert that shadow is not model-facing and inject is
    model-facing only when configured.

### Changed

- Changed V1.12.0 role-aware memory retrieval surfaces:
  - `memory_text` and type-specific surfaces now focus on the stored memory
    claim/content instead of embedding `reason_for_storage` and
    `expected_future_use` into the primary retrieval surface;
  - sparse/lexical memory documents and NetworkX domain matching no longer use
    `reason_for_storage` or `expected_future_use` as primary selection text;
  - `retrieval_shadow.grouped_results` now uses
    `memory_target_role_aware_surface_score_v2` and reports
    `promotable_score`, `support_score`, `surface_roles`,
    `promotable_surface_kinds`, `support_surface_kinds`, and
    `active_rank_eligible`;
  - grouped rerank receives only active-rank-eligible candidates, so
    future-use/temporal/lifecycle surfaces can corroborate but cannot select a
    memory by themselves;
  - tests cover a support-only false-positive case where a misleading
    `future_use_text` surface is visible in traces but not returned as a
    selected memory.

- Changed V1.11.2 model-facing memory packets:
  - automatic runtime context now sends selected memories to Scarlet as
    compact `memory-packet-v1` records;
  - packets keep claim, provenance, confidence/salience, cognitive subject,
    domains, validity, sensitivity, facts, and compact retrieval routes;
  - verbose retrieval internals such as full `signals`, metadata, thresholds,
    and raw trace/debug details remain in `memory.context` traces instead of
    being repeated in the model-facing packet;
  - runtime context declares `rendering_profile=compact-model-facing-v1`;
  - tests assert that trace/debug keeps full signals while the model-facing
    packet stays compact and readable.

- Added V1.8.0 Thinking Retrospection inside the single metacognition route:
  - `/mind/metacognition/step` now supports previous-turn retrospective modes
    for drift detection, tool-choice explanation, open-loop recovery,
    answer-vs-reasoning comparison, reasoning digest extraction, and memory
    candidates from prior reasoning;
  - retrospective calls build a `thinking-retrospection-pack-v1` from stored
    messages, final answer, public notes, tool calls, event markers, traces, and
    provider thinking;
  - `turn_scope="previous"` and `detail="digest|excerpt|raw"` control the
    retrospection payload, with `digest` as the default safe path;
  - Scarlet's prompt now treats prior thinking as process evidence, not proof of
    external facts;
  - metacognition input now tolerates `reasoning_scope`, `reasoning_detail`, and
    observed `{"item": [...]}` list wrappers;
  - Mind API schema version advanced to
    `2026-06-16.thinking-retrospection-v1`.

- Changed V1.7.2 Scarlet public work-note behavior:
  - prolonged reasoning now has explicit prompt-only note waypoints;
  - notes are framed as public orientation, not raw private reasoning;
  - Scarlet should emit short notes when investigations start, evidence changes
    direction, strategy shifts, or the turn moves into synthesis/final
    verification;
  - direct/contextual turns remain compact and should not gain notes merely to
    prove that Scarlet is thinking.

- Changed Scarlet's system prompt to align with the real backend block
  contract:
  - explicit continuity layers now distinguish same-session provider history,
    runtime blocks, episodic recall, semantic memory, and inference;
  - `runtime_context.blocks` is now described as the first-class structured
    runtime contract, with top-level runtime fields treated as compatibility
    mirrors;
  - `recent_runtime_events` is now framed as a compact operational hint
    surface rather than stronger semantic evidence than direct provider
    continuity;
  - same-session visible `thinking` blocks are now explicitly described as the
    preferred source when Scarlet is asked what she had already been
    considering in the current session.

### Fixed

- Fixed V1.14.1 mobile consumer chat rendering:
  - final assistant responses are deduplicated between streaming
    `assistant_answer` blocks and persisted `turn_complete` fallback data;
  - mobile chat text now renders common Scarlet formatting such as headings,
    bullet/numbered lists, paragraph breaks, and bold emphasis without using
    unsafe HTML injection;
  - frontend package metadata advanced to `1.14.1`.

- Fixed hybrid retrieval diagnostic serialization after trace commits:
  - hybrid rank entries now materialize `memory_id`, salience, and creation
    time when the rank plan is built;
  - `retrieval_hybrid` payloads and lookups no longer need to refresh detached
    SQLModel memory objects after `add_trace` commits.

- Fixed V1.11.4 fact canonicalization noise:
  - known entity aliases now match normalized phrase/token boundaries instead
    of arbitrary substrings;
  - `response_format` now requires explicit structural evidence such as
    blocks, response-format tags, or phrases like "answer with" /
    "rispondere con";
  - the laboratory SQLite state was reconciled by archiving 7 unsupported
    historical facts as `rejected_extractor_noise` and creating 6 supported
    replacement facts.

- Fixed V1.11.3 memory retrieval/facts consistency:
  - OpenRouter embedding cache hits and misses now mark the corresponding
    `memory_surfaces` as `embedded` with the embedding model and vector id;
  - `/mind/memory/facts` no longer uses the model-facing `intent` as an
    implicit data query when the body omits `query`;
  - tests cover cached embedding surface relinking and unfiltered facts lookup
    with a broad operational intent.

- Fixed V1.7.1 MiniMax M3 over-processing on simple turns:
  - Scarlet now routes each request through direct, contextual,
    source-sensitive, state-changing, or high-impact effort levels;
  - direct/contextual answers can skip API Mind calls, metacognition, public
    work notes, and full verification when current evidence is already
    sufficient;
  - memory forcing is now conditional on real semantic candidates, memory
    promises, state changes, or source-sensitive claims instead of creating a
    mandatory two-phase ritual for every answer;
  - near-miss user-preference memories can be applied softly as style hints
    without being overstated as verified facts.

- Fixed MiniMax M3 provider-visible thinking for Scarlet turns:
  - Anthropic-compatible M3 requests now explicitly send
    `thinking={"type":"adaptive"}`;
  - M2.x request behavior remains unchanged;
  - provider tests now lock the M3 thinking parameter and prevent regression;
  - live M3 stream verification confirmed `thinking` blocks appear again in
    agentic turns before and after tool use.

### Added

- Added V1.7.0 stream block lifecycle UI:
  - live `text_start`/`text_delta` output now appears immediately as a
    provisional public-text block instead of hidden runtime data;
  - the same public-text block becomes either an assistant note or final answer
    when the provider message is semantically classified;
  - thinking, public text, tool exchange, memory context, and runtime context
    blocks now carry stable `blockId` and lifecycle `phase` metadata;
  - tool input JSON is visible while it streams and is replaced by structured
    arguments after the complete tool call arrives;
  - `turn_complete` now reconciles live blocks with persisted events/traces
    instead of blindly replacing the visible flow;
  - active blocks get a lightweight live visual treatment and the inspector
    surfaces lifecycle phase separately from status.
- Added V1.6.0 model-input inspector and block registry:
  - `docs/block-registry.md` now maps model-facing, UI-facing, trace-only,
    canonical, and currently redundant compatibility blocks;
  - the frontend right pane now includes a `Modello` tab that renders the
    persisted `llm.request` trace as readable system, runtime context,
    provider-history, and tool-schema sections;
  - parsed runtime context now highlights canonical `runtime_context.blocks`
    and top-level compatibility mirrors that may become future payload
    optimization candidates;
  - replayed historical tool cards enrich completed events from matching
    `mind.tool_call` traces, so full tool output remains visible after reload;
  - no model-facing data was removed or compressed in this slice.
- Added V1.5.0 maintenance lab and theory-first roadmap:
  - `GET /api/maintenance/overview` exposes backend-owned maintenance health,
    counts, recent jobs, recent proposals, and maintenance-created memory
    totals for evaluator inspection;
  - `GET /api/maintenance/jobs` lists maintenance jobs with pagination and
    filters;
  - `POST /api/maintenance/jobs/{job_id}/run` lets evaluators run one pending
    job in controlled lab conditions;
  - maintenance job/proposal inspection remains outside Scarlet's model-facing
    `mind_api` surface;
  - `docs/theory-goal-focus-task.md` defines the future Goal/Focus/Task organ
    for owner review before implementation;
  - `docs/theory-metacognition.md` defines the future metacognition organ and
    separates it from notes, maintenance, validators, and private reasoning;
  - memory roadmap now distinguishes pre-embedding work from post-embedding/KG
    lifecycle automation.
- Added V1.4.1 MiniMax M3 baseline migration and M2.7/M3 comparison:
  - MiniMax default model is now `MiniMax-M3`;
  - MiniMax M2.7 remains the direct A/B comparison baseline;
  - project docs and runtime examples now treat M3 as the active baseline;
  - the migration records an explicit behavioral comparison plan focused on
    identity, autonomous API Mind use, memory behavior, source verification,
    and previously observed model-sensitive failures.
- Added EXP-0033 MiniMax M3 stability replication:
  - repeated semantic-memory write, source-recall, and schema-awareness probes
    against temporary DBs;
  - confirmed M3 is stronger than M2.7 on autonomous `/mind/schema`
    inspection in this sample;
  - confirmed M3 source-session recall works well when isolated from previous
    memory-write retry loops;
  - recorded BUG-0039 because M3 repeatedly sends invalid
    `memory.write.tags` shapes, causing high latency and loss of tags in
    stored memories.
- Added V1.4.0 memory surface taxonomy:
  - backend-owned deterministic `surface_taxonomy` compiler for memory,
    fact, and graph-node surfaces;
  - multiple cognitive memory facets such as `preference_text`,
    `future_use_text`, `temporal_text`, `fact_bundle_text`, and
    `conflict_guard_text` when applicable;
  - retrieval readiness manifest now reports `memory_surface_taxonomy_v1`;
  - maintenance proposal preflight now stores an assessment lane, review focus,
    and counts to support policy tuning without extra automation.
- Added V1.3.1 retrieval shadow adapter:
  - optional `retrieval_shadow_*` settings plus `.env.example` defaults;
  - `local` deterministic vector-shadow plumbing over `memory_surfaces`;
  - optional `milvus_lite` backend using PyMilvus when installed;
  - `retrieval_shadow` payloads in manual memory search and automatic
    memory-context traces;
  - trace-only policy, with no active ranking change.
- Added V1.3.0 memory retrieval readiness layer:
  - `memory_surfaces` derived embeddable surfaces for memory, fact,
    graph-node, and session-summary targets;
  - `memory_graph_nodes` and `memory_graph_edges` derived graph-ready state for
    memories, facts, entities, sessions, evidence links, and lifecycle links;
  - idempotent repository helpers for surface/node/edge synchronization;
  - retrieval readiness manifest in memory search/context traces and results;
  - no active ranking change and no Milvus/Qdrant/vector dependency yet.
- Added V1.2.0 cautious memory proposal resolution inside idle maintenance:
  - deterministic preflight now immediately archives rejected and duplicate
    proposals as auditable daily-ledger records;
  - very high-confidence `create_new` proposals can be applied as active
    memories with `created_by=maintenance` and full proposal provenance;
  - ambiguous proposals are resolved in one optional LLM batch and become
    `applied_create`, `archived_rejected`, `archived_noop_duplicate`, or
    `pending_review`;
  - `memory_proposals` acts as the daily archive/ledger for future Dream
    review without adding a separate table or process;
  - maintenance proposal listing now supports created/resolved time filters and
    `status=resolved`.

### Fixed

- Fixed historical thinking replay in the chat flow:
  - response-derived semantic events now persist `text`, `model_step`, and
    `index` for thinking and assistant text blocks rebuilt from provider raw
    messages;
  - legacy stored `llm.thinking.captured` events without text now recover
    their body from `llm.response.raw_provider_messages` in the frontend;
  - generated thinking cards therefore remain visible after final turn
    persistence and session reload.

- Added V1.5.1 MiniMax M3 semantic stream UI:
  - backend now emits semantic stream events for provider thinking blocks,
    public pre-tool notes, and final answers;
  - persisted event order now matches M3's real provider-message structure
    instead of appending notes after turn completion;
  - frontend renders thinking as an accordion, public notes as full blocks,
    each tool call as one input/output accordion, and final answer as a
    dedicated block;
  - center chat now renders user messages, runtime/memory/context blocks,
    thinking, notes, tool exchanges, and final answers as top-level flow cards
    without an outer assistant-response card;
  - right pane now acts as a selected-session inspector for memories, actions,
    internal events, and warnings/errors;
  - removed the frontend heuristic that only step-1 pre-tool text could be a
    public note.
- Added V1.1.1 maintenance-only proposal inbox separation:
  - removed `GET /mind/memory/proposals` from Scarlet's model-facing
    `mind_api` dispatcher and schema;
  - added `GET /api/maintenance/memory/proposals` with bounded pagination for
    background LLM maintenance reviewers;
  - added `POST /api/maintenance/memory/proposals/{proposal_id}/archive` so
    handled proposals leave the default pending queue;
  - restricted dynamic memory reads to real `mem_...` ids so retired child
    paths do not masquerade as memory ids;
  - Mind API schema version advanced to
    `2026-05-25.maintenance-proposals-v1`.

- Added V1.1.0 memory proposal inbox:
  - `memory_proposals` storage for missed-memory review candidates;
  - idle maintenance now creates pending proposals instead of only diagnostic
    review traces;
  - proposal preflight reuses Memory v0 write policy, sparse retrieval, lexical
    scoring, and canonical facts to suggest `create_new`, `noop_duplicate`,
    `review_similar`, `needs_review`, or `reject_candidate`;
  - `GET /mind/memory/proposals` exposes pending proposals through `mind_api`;
  - Mind API schema version advanced to `2026-05-25.memory-proposals-v1`.
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
