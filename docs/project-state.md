# Project State And Convergent Roadmap

Last updated: 2026-05-25  
App baseline: V1.1.1
Status: canonical current-state map

This document is the high-level map for the current project state. It does not
replace the detailed contracts, decisions, experiments, or roadmaps. It links
them into one view so the project can keep moving without losing track of which
parts are implemented, which parts are experimentally confirmed, and which
ideas are still planned.

From V1.0.1 onward, project planning is organized around agentic branches, not
only around technical subsystems. Technical systems such as traces, evals,
events, schemas, providers, and UI remain essential infrastructure, but the
primary roadmap asks which branch of Scarlet's operation they improve.

Primary branch index:

```txt
docs/project-documentation.md
docs/branches/README.md
```

## 1. Current System Shape

The project has moved beyond the original foundation milestone. The current
system is a local agentic runtime for Scarlet with:

- Anthropic-compatible provider execution, defaulting to MiniMax M2.7;
- persistent chat sessions, provider-native history, messages, turns, traces,
  tool calls, runtime events, maintenance jobs, semantic memories, atomic
  facts, and episodic session summaries;
- a single model-facing cognitive tool, `mind_api`;
- schema-discoverable API Mind routes for memory, session recall, and one
  internal metacognition step;
- automatic per-turn memory retrieval and runtime context injection;
- live streaming of model/provider/runtime events into the frontend cockpit;
- an experimental React cockpit for chat, recent sessions, structured agent
  stream, and raw trace inspection.

Core code evidence:

- Runtime app wiring: `backend/app/main.py`
- Settings/provider selection: `backend/app/config.py`,
  `backend/app/llm/factory.py`
- MiniMax/Qwen provider implementation: `backend/app/llm/minimax_client.py`,
  `backend/app/llm/qwen_client.py`
- Chat/session/runtime flow: `backend/app/api/chat.py`
- Mind API facade and dispatcher: `backend/app/api/mind.py`,
  `backend/app/mind/dispatcher.py`
- Maintenance API: `backend/app/api/maintenance.py`
- Model-facing Mind API schema: `backend/app/mind/schema.py`
- Storage models: `backend/app/storage/models.py`
- Runtime events: `backend/app/runtime/events.py`
- Idle maintenance: `backend/app/runtime/maintenance.py`
- Frontend cockpit: `frontend/src/App.tsx`, `frontend/src/styles.css`

## 1.1 Agentic Branch Map

The current branch model is canonical from V1.0.1 onward.

Maturity scale:

```txt
L0 Idea
L1 Planned
L2 Implemented prototype
L3 Tested implementation
L4 Validated in direct Scarlet use
L5 Mature lab-core
```

| Branch | Level | Canonical doc |
|---|---:|---|
| Comunicazione Agente-Utente | L3/L4 | `docs/branches/communication.md` |
| Gestione flussi utente | L1/L2 | `docs/branches/user-flows.md` |
| Percezione e contesto | L4 | `docs/branches/perception-context.md` |
| Identita e relazione | L2/L3 | `docs/branches/identity-relationship.md` |
| Memoria | L4 | `docs/branches/memory.md` |
| Apprendimento e adattamento | L2 | `docs/branches/learning-adaptation.md` |
| Metacognizione | L2/L3 | `docs/branches/metacognition.md` |
| Gestione operativa | L2 | `docs/branches/operational-management.md` |
| Autonomia decisionale | L2 | `docs/branches/decision-autonomy.md` |
| Operativita su mondo esterno | L1 | `docs/branches/external-operativity.md` |
| Operazioni e funzioni avanzate | L1 | `docs/branches/advanced-operations.md` |
| Governance, privacy e sicurezza | L2 | `docs/branches/governance-privacy-safety.md` |
| Emotivita computazionale | L1/L2 | `docs/branches/computational-affect.md` |
| Multi-agente e sub-processi | L1 | `docs/branches/multi-agent-subprocesses.md` |

Each branch document tracks philosophy, evidence, current state, prior work,
and future evolutions. Update branch docs when a change affects Scarlet's real
operating behavior, not merely when internal implementation files move.

## 2. Implemented And Confirmed

### 2.1 Foundation Runtime

Implemented:

- FastAPI app with `/health`, chat, debug, and Mind API routers.
- SQLite storage initialized through `init_db`, with migration support for
  existing laboratory databases.
- Repository-versioned lab database policy for `backend/data/app.db`.
- Pytest coverage across health, storage, chat, Mind API, provider selection,
  MiniMax streaming, and eval runner.

Confirmed:

- Backend test suite currently passes at `55 passed`.
- Health endpoint reports active provider and model.
- Local backend and frontend run on `127.0.0.1:8000` and `127.0.0.1:5173`.

Primary docs:

- `docs/project-blueprint.md`
- `docs/api-contract.md`
- `docs/activity-log.md`

### 2.2 Provider Layer

Implemented:

- `LLM_PROVIDER=minimax|qwen`.
- MiniMax remains default.
- Qwen is available as an A/B comparison provider without changing Scarlet,
  API Mind, memory, traces, or UI.
- All Anthropic-compatible provider calls use SDK streaming internally. External
  backend endpoints may still return either a collected response or a live
  stream.
- MiniMax default completion budget is `131072`.

Confirmed:

- MiniMax high-token smoke test passed after moving non-streaming code paths to
  collected streaming.
- Provider-native tool history now persists across turns.

Still monitoring:

- Qwen comparison exists for experimentation, but current working baseline is
  MiniMax because it is the cost-free provider for the owner.

Primary docs:

- `docs/decisions.md#adr-0024---switchable-anthropic-compatible-llm-providers`
- `docs/decisions.md#adr-0029---provider-streaming-as-default-execution-path`
- `docs/bug-ledger.md#bug-0029---anthropic-sdk-blocks-high-non-streaming-minimax-calls`

### 2.3 Provider-Native Multi-Turn History

Implemented:

- `sessions.provider_history_json` stores Anthropic-compatible content blocks.
- Future turns send provider-native history plus the current user message.
- Human-readable `messages` remain the transcript for UI and episodic recall.
- Old sessions without provider history fall back to text reconstruction and
  are hydrated after a completed turn.

Confirmed:

- Live probes verified that prior `GET /mind/schema` and
  `POST /mind/memory/write` tool-use/tool-result blocks are visible in the next
  provider request.
- Regression tests assert provider history includes assistant `tool_use` and
  matching user `tool_result` blocks.

Primary docs:

- `docs/decisions.md#adr-0028---provider-native-session-history`
- `docs/bug-ledger.md#bug-0028---provider-native-tool-history-dropped-across-turns`

### 2.4 Mind API Surface

Implemented:

The model-facing tool surface is still one tool:

```txt
mind_api(method, path, body, intent)
```

Implemented routes in current schema version
`2026-05-25.maintenance-proposals-v1`:

- `GET /mind/schema`
- `POST /mind/memory/write`
- `POST /mind/memory/search`
- `GET /mind/memory/{memory_id}`
- `GET /mind/memory/facts`
- `POST /mind/memory/facts/backfill`
- `GET /mind/memory/conflicts`
- `POST /mind/memory/deprecate`
- `POST /mind/memory/supersede`
- `GET /mind/sessions`
- `GET /mind/sessions/{session_id}`
- `POST /mind/sessions/{session_id}/summarize`
- `POST /mind/metacognition/step`

Planned route still exposed:

- `POST /mind/attention/context`

Confirmed:

- Schema is now a compact route/capability catalog: route status, purpose,
  schema digest, and schema policy.
- Detailed body schemas, parameter descriptions, accepted aliases, examples,
  and retry guidance are returned as endpoint-local `usage_guide` on
  recoverable implemented-route errors.
- Stale planned `/mind/events/emit` route was removed because runtime events
  are backend-owned.
- Unknown/unavailable routes return structured recoverable errors with current
  schema metadata and route suggestions.

Primary docs:

- `docs/api-contract.md#implemented-mind-api`
- `docs/cognitive-api-roadmap.md`
- `docs/decisions.md#adr-0030---runtime-events-as-the-agent-control-plane`
- `docs/decisions.md#adr-0032---mind-schema-catalog-and-endpoint-local-error-guides`

### 2.5 Semantic Memory

Implemented:

- Memory write/search/read/conflicts/deprecate/supersede.
- Source provenance on memory records:
  `source_session_id`, `source_turn_id`, `source_message_id`.
- `confidence`, `salience`, `scope`, type, status, tags, usage count, and
  metadata.
- Backend-owned deterministic fields for ids, timestamps, provenance, traces,
  and lifecycle metadata.
- Temporal filters on manual memory search, with backend-resolved ranges such
  as today, yesterday, last seven days, explicit ISO ranges, and current
  session.
- SQLite FTS5/BM25 sparse retrieval over derived memory search documents.
- Prompt policy for autonomous semantic memory consolidation.
- Memory proposal inbox for missed-memory review candidates, with candidate
  evidence, similar-memory preflight, suggested lifecycle action, and future
  embedding/graph slots.

Confirmed:

- Memory write/search works across sessions.
- Lifecycle conflict repair works for Zero-Luce.
- Scarlet can now write personal semantic facts such as the chocolate
  preference/health limit and retrieve them in another session.
- Integrated direct probes show memory write remains inconsistent: Scarlet can
  adopt a durable preference in the answer while not calling `memory.write`;
  idle maintenance catches the omission as a proposal candidate without writing
  active memory automatically.

Still monitoring:

- Autonomous memory write is improved but still not guaranteed in every case.
- Scarlet may over-announce memory writes even when the target UX is silent.
- Direct P1 probe showed Scarlet can emit pseudo tool-call markup in final text
  instead of a real provider `tool_use`, leaving no `mind.memory.write` trace.
- Model-supplied provenance can still be preserved inside metadata unless a
  sanitizer is added.

Primary docs:

- `docs/memory-roadmap.md`
- `docs/decisions.md#adr-0026---pre-final-semantic-memory-consolidation`
- `docs/bug-ledger.md#bug-0024---semantic-memory-consolidation-treated-as-opt-in`
- `docs/bug-ledger.md#bug-0025---model-supplied-memory-provenance-can-be-stale-in-metadata`
- `docs/bug-ledger.md#bug-0027---recognized-semantic-candidate-not-written`
- `docs/bug-ledger.md#bug-0032---scarlet-can-emit-pseudo-tool-invocation-text-instead-of-real-tool-use`
- `docs/experiments.md#exp-0019---integrated-direct-scarlet-probes`

### 2.6 Atomic Memory Facts

Implemented:

- `memory_facts` table.
- Deterministic fact extraction for recognized patterns.
- Fact inspection and backfill.
- Fact-aware conflict detection and lifecycle propagation.
- Entity/predicate alias handling for known Zero-Luce/SAL style cases.

Confirmed:

- Zero-Luce memories map to canonical `protocollo-zero-luce` +
  `response_format`.
- Fact backfill can reconstruct facts and supersession links from older
  memories.
- Fact conflict resolution works through memory supersession/deprecation.

Current limit:

- Fact extraction is intentionally narrow. It is not yet a general semantic
  parser.

Primary docs:

- `docs/memory-roadmap.md#phase-m3---atomic-fact-layer`
- `docs/api-contract.md#get-mindmemoryfacts-through-mind_api`

### 2.7 Episodic Memory

Implemented:

- `session_summaries` table.
- `GET /mind/sessions` as a paginated episodic index.
- `GET /mind/sessions/{session_id}` for summaries, full transcripts, and
  memories written from the session.
- `GET /mind/sessions` supports backend-resolved temporal filters and FTS5/BM25
  sparse search over title, summaries, and conversation text.
- `POST /mind/sessions/{session_id}/summarize` as LLM-backed summarization over
  the complete user/assistant message history.
- Semantic memories link to episodic source sessions through
  `source_session_id`.
- Per-session idle maintenance now schedules summary refresh after a completed
  turn. If another turn arrives in the same session before the idle window
  expires, the older pending job is superseded or skipped.

Confirmed:

- Existing lab sessions were backfilled with summaries.
- Scarlet can search sessions by date/topic and recover prior conversations.
- Follow-up probes showed Scarlet can open source transcripts from memory
  provenance and correct a weaker initial conclusion.

Still monitoring:

- Scarlet does not always open the source transcript on the first natural
  source-sensitive question.
- Session lists are paginated and must not be treated as exhaustive evidence.
- The first automatic trigger is idle-based, not a full session lifecycle or
  explicit close/open model.

Primary docs:

- `docs/memory-roadmap.md#phase-m35---episodic-session-recall`
- `docs/api-contract.md#get-mindsessions-through-mind_api`
- `docs/bug-ledger.md#bug-0020---session-list-first-page-can-be-treated-as-exhaustive`
- `docs/bug-ledger.md#bug-0023---minimax-can-reassert-unsupported-absence-after-identifying-it`

### 2.8 Runtime Context And Automatic Memory Retrieval

Implemented:

- Every chat turn builds a `memory.context` trace.
- Every chat turn now also builds a block-based `runtime.context` trace.
- The model-facing system prompt is composed with backend-generated
  `<runtime_context>`.
- Runtime context is stratified into `session_context`, `message_context`, and
  `scarlet_state` blocks while preserving legacy top-level fields for
  compatibility.
- `session_context` includes current-session identity, recent previous session
  summaries, and the latest memories sourced from the previous session.
- `message_context` includes current-message perception, temporal world data,
  active user-scope memory hints, automatic memory retrieval, recent dialogue,
  recent runtime events, and API Mind schema/capability metadata.
- `scarlet_state` is a backend-seeded operational state block for focus,
  posture, active goal, and open loops until dedicated state APIs exist.
- Temporal context is backend-owned and is Scarlet's only operational clock.
  It now exposes one configured runtime time (`temporal_context.now`) instead
  of separate local/UTC clocks. Default timezone is `Europe/Rome`.
- Platform language is backend-owned and exposed through
  `message_context.current_message.language`; default language is Italian and
  no automatic language heuristic is currently used.
- `message_context.world.location` exposes the configured country/timezone
  locale. It is valid for local calendar and time reasoning, but not exact
  physical presence.
- `message_context.user_profile.identity` exposes the active operational user
  profile for recognition, personalization, and future multi-user separation.
- `message_context.user_profile.privacy` exposes the active memory/privacy
  boundary for user-scope facts.
- Dashboard runtime settings can override timezone, language, country, active
  profile id, privacy scope, and local user display name for future turns.

Confirmed:

- Automatic memory context fixed basic cross-session recall cases.
- Temporal runtime context improved Scarlet's handling of current time.
- Recent runtime events let Scarlet reconstruct prior internal API operations.
- Natural conversation probes confirmed personal memory can be used without
  explicit tool prompting, e.g. the chocolate-limit memory shaped dessert
  advice.
- Backend tests confirm the new `runtime.context` trace is emitted before
  `llm.request`, and streaming turns emit a `runtime_context` block alongside
  the existing `memory_context` event.
- Direct block-comprehension probe on 2026-05-25 confirmed:
  - `runtime.context` is appended to the effective system prompt before the
    provider request;
  - Scarlet can read current time/language/block identities directly from
    runtime context without tool calls;
  - Scarlet opens source sessions when recent-session summaries are only
    navigation hints;
  - Scarlet can use `user_profile` memories for personalization even when
    automatic retrieval selects a different memory.
- Backend tests now assert that runtime context includes configured locale,
  profile identity, and privacy scope before the model request.

Still monitoring:

- Retrieval is stronger than lexical v0, but still sparse/entity-light and can
  miss synonyms, paraphrases, or ambiguous entities until embeddings and
  stronger entity guards exist.
- Retrieval can select stale project memories strongly enough that Scarlet uses
  obsolete present-tense claims, such as saying no event store exists after
  runtime events were implemented.
- Automatic memory retrieval and user-profile hints can diverge: in
  `EXP-0024`, the snack prompt answered correctly from `user_profile`, while
  `memory_retrieval.selected` picked an unrelated creator memory.
- Memory context helps the model, but does not deterministically enforce final
  answer obligations.

Primary docs:

- `docs/api-contract.md#implemented-internal-runtime-context`
- `docs/experiments.md#exp-0008---memory-context-pipeline-v0`

### 2.9 Internal Metacognition

Implemented:

- One route: `POST /mind/metacognition/step`.
- LLM-backed reviewer returns structured review summary, risks, claim checks,
  missing evidence, recommended internal actions, continuation hint, and public
  summary.
- The route accepts common observed model aliases and attempts one JSON repair
  retry.
- Recommended actions are annotated with schema availability.

Confirmed:

- Scripted tests verify route traceability, alias tolerance, JSON repair, and
  that removed parallel cognitive routes are unavailable.

Still monitoring:

- Live behavioral evidence is not yet strong enough to say Scarlet reliably
  invokes metacognition when she should.
- The design decision remains: do not add more cognitive endpoints until the
  single route is proven insufficient.

Primary docs:

- `docs/cognitive-api-roadmap.md`
- `docs/decisions.md#adr-0025---engineering-agent-quality-gate-in-scarlet-prompt`

### 2.10 Runtime Events And Agentic UI

Implemented:

- `events` table as ordered runtime control plane.
- Event emission for turn lifecycle, persisted messages, memory context, model
  request/response, provider stream milestones, Mind API tool lifecycle, public
  notes, final answers, and private-thinking metadata.
- `GET /api/debug/events`.
- `GET/PUT /api/dashboard/settings`.
- `GET /api/dashboard/memories`.
- `GET /api/dashboard/profile`.
- Streaming chat emits live `runtime_event` rows.
- Frontend renders persisted events before falling back to traces.
- Right pane now acts as a dashboard with tabbed Agent Stream, Memory, Profile,
  and Settings/Impostazioni panels.
- Tailwind is now the frontend styling foundation, with component classes
  layered over Tailwind utilities for consistent dashboard layout.
- The chat timeline now renders runtime context, automatic memory retrieval,
  Mind API calls/results, session recall, schema results, metacognition, public
  notes, and final answers as human-readable cards before exposing JSON behind
  closed code/detail toggles.
- The left sidebar keeps recent sessions, active runtime settings, and session
  actions visible while the center remains the conversation surface.
- The UI is viewport-bounded: page-level overflow is hidden and high-volume
  areas such as session history, chat messages, dashboard lists, agent stream,
  and trace drawers scroll internally.
- The settings panel scrolls internally and now manages operational profile id,
  country/locale, timezone, platform language, display name, and memory privacy
  scope.

Confirmed:

- Runtime events are persisted, streamed, rendered, and compacted into the next
  turn's runtime context.
- Live probe showed Scarlet reconstructed a prior `GET /mind/schema` call from
  recent runtime events.
- Runtime events now drive the first backend maintenance scheduler through
  `turn.completed` and `maintenance.job.*` events.
- Browser-level Playwright smoke on 2026-05-24 loaded a persisted turn with
  runtime context blocks and confirmed no top-level raw JSON/pre blocks were
  visible in the operation body (`runtime_context` cards and code toggles were
  present).

Still monitoring:

- The cockpit still needs live evaluator feedback on whether the current
  organization is clear enough during real use, especially on narrow side-panel
  widths and dense runtime-context turns.
- Maintenance events are readable as cards, but the best compact phrasing for
  long-running maintenance results is still open.

Primary docs:

- `docs/decisions.md#adr-0030---runtime-events-as-the-agent-control-plane`
- `docs/decisions.md#adr-0031---session-idle-maintenance-as-the-first-background-process`
- `docs/experiments.md#exp-0017---runtime-event-control-plane`

### 2.11 Session Idle Maintenance

Implemented:

- `maintenance_jobs` storage for backend-owned asynchronous work.
- `memory_proposals` storage for review candidates that are not active memories.
- A per-session idle job is scheduled after `turn.completed`.
- The job due time defaults to `900` seconds through
  `MAINTENANCE_IDLE_SECONDS`.
- A newer turn in the same session supersedes older pending jobs; sessions do
  not cancel each other's jobs.
- The worker runs through the FastAPI lifespan and processes due jobs in
  batches.
- The current job performs:
  - `sessions.summarize` to refresh the episodic summary only when stale;
  - missed semantic memory review over the full user/assistant transcript and
    memories already written from that session;
  - proposal creation for write-recommended review candidates, with duplicate,
    similar-memory, and canonical-fact preflight.
- Maintenance emits `maintenance.job.*` and
  `maintenance.memory_review.completed` events, and writes a
  `maintenance.memory_review` trace. The review event reports proposal counts.

Confirmed:

- Targeted backend tests verify job scheduling, supersession, idle skip when a
  newer turn exists, summary refresh, review/proposal output, and live chat
  event emission.
- Direct MiniMax probe confirmed the idle job can catch a missed memory write
  when Scarlet emits pseudo tool-call text and no real `mind.memory.write`
  trace exists.
- A second integrated probe confirmed the idle job also catches quieter missed
  writes where Scarlet answers coherently but never calls the memory endpoint.
- The review deliberately does not write semantic memories automatically.
  Instead, it now creates pending memory proposals so future apply/merge
  decisions can be evaluated without polluting active memory.
- Pending memory proposals are not a Scarlet-facing `mind_api` capability.
  They are consumed through maintenance APIs:
  `GET /api/maintenance/memory/proposals` and
  `POST /api/maintenance/memory/proposals/{proposal_id}/archive`.

Still monitoring:

- Live MiniMax behavior still needs evaluation after the 15-minute idle window.
- Pending proposals need future UI/application decisions: evaluator approval,
  safe auto-apply thresholds, or Scarlet-assisted lifecycle actions.
- BUG-0032 must be discussed before implementing a direct fix for pseudo
  tool-call text.
- Some maintenance candidates are useful but not clean enough for automatic
  writes yet; one probe produced a valid open-loop checkpoint with
  `confidence=0.0` and `salience=0.0`.
- Natural conversation probes show that stale memories are now a higher
  priority than merely detecting missed memories.

### 2.12 Evaluation

Implemented:

- Scripted eval runner.
- Interactive eval runner.
- Stored runs under `backend/app/evals/runs/`.
- Current scenarios:
  - `baseline_tool_schema.json`
  - `memory_v0_preference.json`
  - `continuity_probe.json`
  - `visible_metacognition_probe.json`
  - `cognitive_api_metacognition_probe.json`

Confirmed:

- Scripted evals are useful for regression.
- Interactive terminal sessions are still the better tool for behavioral
  evidence because Scarlet's failures often appear only under adaptive probing.

Primary docs:

- `docs/experiments.md`
- `backend/README.md#evaluation-runner`
- `docs/experiments.md#exp-0019---integrated-direct-scarlet-probes`

## 3. Planned But Not Implemented

### 3.1 Memory Maintenance Beyond Idle Review

Need:

- decide how internal maintenance workers should apply, reject, merge, or
  escalate pending memory proposals after reading them in paged batches;
- stale-memory detection and lifecycle repair for old technical baselines that
  conflict with current runtime state;
- memory promise detection, e.g. final answer says "I will remember" without a
  matching `memory.write`;
- memory health/lint pass for stale, conflicting, duplicate, or corrupted
  memories.

Already implemented:

- `turn.completed` schedules per-session idle maintenance.
- The idle job runs summary refresh, missed-memory review, and pending proposal
  creation without auto-writing active memory.

Why next:

The first maintenance slice exists. The next decision should be based on live
evidence from pending proposal quality, not on adding more overlapping
processes.

### 3.2 Retrieval Quality Upgrade

Need:

- direct live evaluation of temporal + sparse retrieval;
- entity-aware relevance guard;
- stronger selected/near_miss/excluded thresholds;
- better trace explanations for retrieval decisions;
- optional dense retrieval only after sparse/entity behavior is stable.

Key acceptance:

- Nebbia-Rossa must not select Zero-Luce.
- Elliptical Zero-Luce follow-ups must still work when dialogue context makes
  the referent clear.

### 3.3 Memory Proposal Inbox And Compaction

Need:

- maintenance-worker apply/reject/merge policy for pending proposals;
- `POST /mind/memory/propose` only if a later experiment proves Scarlet needs a
  model-facing proposal primitive;
- `POST /mind/memory/compact`

Purpose:

Separate immediate in-turn semantic memory writes from durable consolidation,
merge, duplicate repair, and stale-memory cleanup.

### 3.4 Deterministic Answer Validators

Need:

- validator for unsupported exhaustive claims;
- validator for memory conflict hiding;
- validator for memory promise without write;
- validator for source-sensitive claims based only on paginated session lists
  or summaries.

Why not first:

The owner intentionally put early response-control M1 on hold until memory
state and conflict management became more real. That prerequisite is now mostly
true, but retrieval quality and background maintenance should still come first.

### 3.5 Per-Route Field Ownership Schema And Sanitization

Need:

- `agent_supplied_fields` and `backend_owned_fields` metadata in
  `GET /mind/schema`;
- sanitizer for backend-owned ids, timestamps, source ids, and provenance
  inside route bodies and nested metadata;
- response hints after state-changing operations explaining what API Mind
  attached automatically.

Why:

Scarlet should not have to invent deterministic fields. The backend should
make wrong ownership impossible or harmless.

### 3.6 Session Summary Lifecycle Refinement

Need:

- define whether the project also needs an explicit session "closed" concept
  beyond the implemented idle timer;
- attach summary freshness metadata to session listings.

Current state:

The summarization endpoint works and the first automatic idle trigger is
implemented. A broader lifecycle model is still undecided.

### 3.7 Attention Context

Need:

- design `POST /mind/attention/context`;
- decide what it does that runtime context and memory context do not already
  do;
- avoid duplicating memory retrieval or metacognition.

Current state:

Planned only. It remains in schema as one planned route.

### 3.8 CLI And Debug Memory Views

Need:

- CLI wrappers for memory list/show/conflicts/deprecate/supersede/lint/compact;
- cockpit views for active memories, conflicts, lifecycle history, proposals,
  and retrieval diagnostics.

Why:

The project is API/CLI-first. The human evaluator should be able to inspect and
repair memory health without writing SQL.

### 3.9 Broader Behavioral Evals

Need:

- live adaptive probes for autonomous memory write across personal facts,
  project checkpoints, preferences, corrections, and neutral facts;
- metacognition trigger probes where the user does not name metacognition;
- source-sensitive episodic recall probes;
- runtime-event UI probes;
- future background-maintenance acceptance tests.

## 4. Priority Reorganization

### P0 - Keep The Microscope Trustworthy

Goal:

Do not build more cognition before the observability layer stays coherent.

Work:

- keep events/traces/schema/docs aligned;
- run full backend suite and frontend build after meaningful changes;
- keep `docs/project-state.md` updated after major milestones.

### P1 - Background Memory Maintenance

Goal:

Turn runtime events into the first real "subconscious" process without adding
duplicate cognitive paths.

Implemented first slice:

1. Deterministic `maintenance_jobs` records.
2. Per-session idle scheduling after `turn.completed`.
3. Session summary refresh through the existing summarization endpoint.
4. Missed-memory review.
5. Pending memory proposals with duplicate/similarity/fact preflight.
6. Maintenance events/traces visible to debug/UI.

Why:

This directly addresses observed memory inconsistency without adding more
burden to Scarlet's prompt.

Next P1 evaluation:

- wait for real idle jobs after live sessions;
- inspect pending `memory_proposals` for action quality and noise;
- inspect `maintenance.memory_review` traces for useful or noisy candidates;
- decide whether candidates should feed a proposal inbox, auto-write path, or
  remain diagnostics.

### P2 - Retrieval Quality And Memory Health

Goal:

Make memory evidence more reliable before enforcing strict answer validators.

Recommended order:

1. direct evaluation of temporal + FTS5/BM25 behavior;
2. entity-aware guard;
3. retrieval diagnostics in UI;
4. memory lint for conflicts/stale/duplicates;
5. proposal inbox and compaction.

### P3 - Source-Sensitive Answer Validation

Goal:

Prevent final answers from becoming stronger than the evidence.

Start after P1/P2 have enough event and retrieval evidence to feed validators.

Candidate validators:

- non-exhaustive session absence;
- conflict hidden in final answer;
- memory promise without write;
- "verified/baseline/all/none" claims without source receipt.

### P4 - Metacognition Deepening

Goal:

Improve how Scarlet uses the single metacognition route before considering
extra cognitive endpoints.

Work:

- mode-specific reviewer prompts;
- stricter output validation;
- optional continuation when `should_continue=true`;
- evaluate final-answer improvement against similar non-metacognitive turns.

### P5 - Human Operator Surfaces

Goal:

Make the lab maintainable as state grows.

Work:

- CLI memory commands;
- cockpit memory views;
- exportable run summaries;
- event-driven maintenance dashboard.

## 5. Documentation Structure Going Forward

Use docs this way:

- `docs/project-documentation.md`: main documentation index and branch map.
- `docs/project-state.md`: current integrated map and convergent roadmap.
- `docs/project-blueprint.md`: project philosophy, constraints, and durable
  architecture principles.
- `docs/development-process.md`: V1.0.1+ scoped implementation and versioning
  protocol.
- `docs/branches/`: vertical documents for Scarlet's agentic operating
  branches.
- `docs/api-contract.md`: exact implemented/planned API contracts.
- `docs/memory-roadmap.md`: detailed memory roadmap and memory-specific
  evidence.
- `docs/cognitive-api-roadmap.md`: schema/metacognition roadmap.
- `docs/experiments.md`: hypotheses, live probes, scripted runs, and results.
- `docs/decisions.md`: architectural decisions.
- `docs/bug-ledger.md`: bugs, root causes, fixes, and monitoring residuals.
- `docs/activity-log.md`: chronological work log.
- `CHANGELOG.md`: project-visible change history.

Update rule:

After any major feature slice, update:

1. `docs/project-state.md` for integrated status and priorities;
2. the relevant vertical roadmap;
3. `docs/activity-log.md`;
4. `CHANGELOG.md`;
5. `docs/decisions.md` only if an architectural decision changed;
6. `docs/bug-ledger.md` only if a bug was found, fixed, or reclassified.

## 6. Current Best Next Step

The next implementation discussion should focus on P1:

```txt
event-triggered background memory maintenance
```

Reason:

The backend now emits live ordered runtime events and the UI can show them.
That gives us the substrate for real background cognition. The highest-value
next move is to design a small maintenance process that watches completed
turns/sessions and produces traceable maintenance output without creating new
overlapping Mind API endpoints.
