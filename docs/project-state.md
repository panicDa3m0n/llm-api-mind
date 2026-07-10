# Project State And Convergent Roadmap

Last updated: 2026-07-10
App baseline: V1.27.0
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

- Anthropic-compatible provider execution, defaulting to MiniMax M3, with
  MiniMax M2.7 retained as the model-comparison baseline;
- persistent chat sessions, provider-native history, messages, turns, traces,
  tool calls, runtime events, maintenance jobs, semantic memories, atomic
  facts, episodic session summaries, derived memory surfaces, cached embedding
  vectors, and graph-ready memory nodes/edges;
- a single model-facing cognitive command tool, `mind_shell`;
- legacy/debug API Mind routes for memory, session recall, and one internal
  metacognition step, now wrapped by the model-facing command runtime;
- automatic per-turn memory retrieval and runtime context injection;
- optional OpenRouter cloud embedding/rerank retrieval over `memory_surfaces`,
  with raw shadow traces, memory-level grouping, and explicit hybrid promotion
  mode for controlled active ranking;
- role-aware memory surface ranking: primary content and canonical-fact
  surfaces can promote memories, while future-use, temporal, and lifecycle
  guard surfaces act as support/corroboration only;
- Codex test database isolation through startup-level `CODEX_TEST`, allowing
  evaluator experiments to run through the same backend endpoints on a seeded
  DB copy without mutating the production/laboratory Scarlet DB;
- explicit database roles (`production`, `laboratory`, `test`, and
  `preliminary`) with startup validation, a read-only preflight, and an ASGI
  factory boundary so imports used by evaluators do not open a runtime DB;
- a documented VPS deployment boundary: the persistent `/app/data` mount is
  production data, excluded from both image construction and code transfer;
- a frozen preliminary regression gate for major procedures, using real
  sourceable memory/fact/session references from a published laboratory DB and
  a freshly recreated disposable DB for each pre/post comparison;
- active NetworkX associative graph expansion over memory domains, used to
  surface field-of-discourse personal memories such as food/drink/body limits
  even when the user does not name the stored memory directly;
- compact model-facing memory packets (`memory-packet-v1`) in runtime context,
  while full retrieval diagnostics remain in `memory.context` traces for UI,
  debugging, and evaluator analysis;
- compact model-facing `mind_shell` result profiles for memory search and
  conflict inspection, with full retrieval/conflict diagnostics kept in traces;
- a central `mind_shell` command registry that validates command families,
  aliases, unavailable-by-design actions, planned actions, required fields, and
  missing arguments for shell execution and metacognition recommendations;
- a layered active shell implementation: shared cognitive contracts,
  side-effect-free command parsing, command-to-handler translation, and
  separate model-facing presentation/compaction policy;
- a model-facing runtime capability map derived from the shell registry rather
  than from legacy endpoint routes; legacy `/mind/*` endpoints remain
  internal/debug/maintenance surfaces unless wrapped by explicit shell
  commands;
- a V1.26.0 planning baseline for runtime context packs: a compact always-on
  spine plus mode-specific packs for source-sensitive work, temporal recall,
  project engineering, emotional continuity, and future embodied perception or
  actuation;
- a plugin-level external GPT bridge under `/gpt/*`, allowing a custom
  ChatGPT GPT to bootstrap the same Scarlet context, execute `mind_shell`
  actions, and finalize answers back into Scarlet history without changing the
  local MiniMax runtime;
- GPT Builder packaging for that bridge: compact under-limit system prompt,
  attachable knowledge files, and a minimal OpenAPI Actions schema for the
  three `/gpt/*` operations. The active GPT Builder operation ids are
  `bootstrapScarletBeforeEveryAnswer`, `runScarletMindAction`, and
  `finalizeScarletBeforeAnswer`;
- a deprecated experimental `/mcp` ChatGPT App/Connector surface retained
  temporarily for traceability after platform testing showed it does not fit
  the target Custom GPT flow;
- memory conflict semantics narrowed to active atomic fact divergence, while
  tag/token/exact-content overlap is treated as maintenance `related_overlap`
  rather than contradiction;
- metacognitive-context shadow generation for evaluator-visible candidate
  lessons, with controlled injection available only for A/B tests;
- live streaming of model/provider/runtime events into the frontend cockpit;
- an experimental React cockpit for chat, recent sessions, structured agent
  stream, model-input inspection, and raw trace inspection.
- a separate `/mobile` React consumer UI for normal users, using the existing
  chat, session, memory, profile, and settings APIs while future operativity is
  shown only as `Presto disponibile`.

V1.5.0 orientation:

- keep MiniMax M3 as the active baseline so the owner can run broader human
  tests, with immediate rollback available through `MINIMAX_MODEL=MiniMax-M2.7`;
- expose backend-owned maintenance state through evaluator APIs without
  broadening the model-facing `mind_shell` command surface;
- keep memory lifecycle automation conservative until embedding/KG evidence
  improves similarity, stale-memory, and conflict detection;
- treat goal/focus/task and metacognition as theory-first branches before
  implementing new organs.

Core code evidence:

- Runtime app wiring: `backend/app/main.py`
- Settings/provider selection: `backend/app/config.py`,
  `backend/app/llm/factory.py`
- MiniMax/Qwen provider implementation: `backend/app/llm/minimax_client.py`,
  `backend/app/llm/qwen_client.py`
- Chat/session/runtime flow: `backend/app/api/chat.py`
- External GPT bridge plugin: `backend/app/plugins/gpt_bridge/`
- Mind API facade and dispatcher: `backend/app/api/mind.py`,
  `backend/app/mind/dispatcher.py`
- Maintenance API: `backend/app/api/maintenance.py`
- Model-facing Mind API schema: `backend/app/mind/schema.py`
- Storage models: `backend/app/storage/models.py`
- Runtime events: `backend/app/runtime/events.py`
- Idle maintenance: `backend/app/runtime/maintenance.py`
- Frontend cockpit: `frontend/src/App.tsx`, `frontend/src/styles.css`
- Consumer mobile UI: `frontend/src/MobileApp.tsx`

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
| Memoria | L4+ | `docs/branches/memory.md` |
| Apprendimento e adattamento | L2 | `docs/branches/learning-adaptation.md` |
| Metacognizione | L3 | `docs/branches/metacognition.md` |
| Gestione operativa | L2 | `docs/branches/operational-management.md` |
| Autonomia decisionale | L2 | `docs/branches/decision-autonomy.md` |
| Operativita su mondo esterno | L1 | `docs/branches/external-operativity.md` |
| Operazioni e funzioni avanzate | L1 | `docs/branches/advanced-operations.md` |
| Governance, privacy e sicurezza | L2 | `docs/branches/governance-privacy-safety.md` |
| Emotivita computazionale | L2/L3 | `docs/branches/computational-affect.md` |
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
- Legacy LFS laboratory snapshot policy for `backend/data/app.db`, now bounded
  by explicit database roles and a no-stage guard for ordinary code commits.
- Digital-individual organ substrate registry in `backend/app/mind/organs.py`,
  with reserved block names, visibility modes, event names, trace kinds, and
  off-by-default feature flags. V1.21.0 closes the standalone surface for the
  first three organs: focus, volition, and affect.
- Affective core V1.20.0/V1.21.0: `affect_states`, deterministic human emotion
  prototypes, `organ.affect` traces/events, shadow appraisal, optional
  `affective_context` model injection behind `organ_affect_mode=model`, and
  read-only `/mind/affect` inspection.
- Pytest coverage across health, storage, chat, Mind API, provider selection,
  MiniMax streaming, and eval runner.

Confirmed:

- Backend test suite currently passes at `130 passed` on the V1.27.0 full
  sweep.
- Health endpoint reports active provider and model.
- Local backend and frontend run on `127.0.0.1:8000` and `127.0.0.1:5173`.

Primary docs:

- `docs/project-blueprint.md`
- `docs/api-contract.md`
- `docs/activity-log.md`

### 2.2 Provider Layer

Implemented:

- `LLM_PROVIDER=minimax|qwen`.
- MiniMax M3 remains the default MiniMax baseline from V1.4.1.
- V1.7.1 keeps MiniMax M3 as the active baseline but adds prompt-level
  request-effort routing so M3 does not treat every ordinary response as a full
  source-sensitive investigation.
- MiniMax M2.7 remains available as the direct A/B baseline by setting
  `MINIMAX_MODEL=MiniMax-M2.7`.
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
- MiniMax M3 can answer and perform Anthropic-style `tool_use` through the
  current MiniMax Anthropic-compatible endpoint on realistic prompts.
- The V1.7.1 prompt fix is designed to preserve M3's deep reasoning and tool
  use while reducing unnecessary public notes, schema checks, and full
  verification on simple/contextual turns.

Still monitoring:

- MiniMax M3 has a monitored ultra-short-output streaming edge case: a
  one-token `pong` prompt can produce no usable text content block through the
  Anthropic-compatible stream. Realistic Scarlet turns and tool-use worked.
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

The model-facing tool surface is one controlled cognitive command shell:

```txt
mind_shell(command, intent)
```

Implemented command families:

- `help`
- `memory`
- `session`
- `focus`
- `volition`
- `affect`
- `metacognition`

Legacy/debug/internal routes remain implemented in current endpoint schema
version `2026-07-08.memory-conflict-taxonomy-v1`:

- `GET /mind/schema`
- `POST /mind/memory/write`
- `POST /mind/memory/search`
- `GET /mind/memory/{memory_id}`
- `POST /mind/memory/graph`
- `GET /mind/memory/facts`
- `POST /mind/memory/facts/backfill`
- `GET /mind/memory/conflicts`
- `POST /mind/memory/deprecate`
- `POST /mind/memory/supersede`
- `GET /mind/sessions`
- `GET /mind/sessions/{session_id}`
- `POST /mind/sessions/{session_id}/summarize`
- `POST /mind/metacognition/step`
- `POST /mind/focus`
- `POST /mind/volition`
- `POST /mind/affect`

Confirmed:

- `help` is now Scarlet's model-facing command catalog: command families,
  examples, digest, and usage policy.
- Legacy `/mind/schema` remains a compact route/capability catalog for
  backend/debug compatibility: route status, purpose, schema digest, and
  schema policy.
- Detailed body schemas, parameter descriptions, accepted aliases, examples,
  and retry guidance are returned as endpoint-local `usage_guide` on
  recoverable implemented-route errors.
- Stale planned `/mind/events/emit` route was removed because runtime events
  are backend-owned.
- Unknown/unavailable routes return structured recoverable errors with current
  schema metadata and route suggestions.
- V1.18.0 replaces the old planned attention placeholder with implemented
  `/mind/focus`, a lifecycle route for Scarlet's foreground attention state.
- V1.19.0 adds `/mind/volition`, a manual latent-intention register for
  Scarlet's self-generated directions. It is not automatically injected into
  active chat.
- V1.21.0 adds `/mind/focus action=timeline`,
  `/mind/volition action=list_due`, and read-only `/mind/affect`, closing the
  standalone surfaces for the first three digital-individual organs.
- V1.25.4 aligns runtime capability state with the shell registry. Endpoint-only
  maintenance operations such as `POST /mind/memory/facts/backfill` are marked
  `internal_maintenance_only` rather than presented as Scarlet commands.

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
- semantic `type`, semantic `scope`, content, reason, expected future use,
  status, usage count, timestamps, and legacy confidence/salience columns kept
  for compatibility/audit rather than active ranking.
- Tags, metadata, facts, surfaces, graph rows, embeddings, provenance, and
  query-time relevance are backend-owned or maintenance-derived.
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
- V1.3.0 derived retrieval substrate:
  `memory_surfaces`, `memory_graph_nodes`, and `memory_graph_edges`.
  These are rigenerable indexes over source memories/facts/sessions and are
  designed for future dense vector search, graph expansion, and Milvus/Qdrant
  shadow mode without replacing API Mind's canonical memory tables.
- V1.3.1 optional retrieval shadow adapter:
  memory search and automatic memory context can run trace-only vector-shadow
  comparison over `memory_surfaces` with `local` deterministic plumbing or
  optional `milvus_lite`, without changing active ranking.
- V1.4.0 memory surface taxonomy:
  the backend now compiles multiple cognitive surfaces for a memory, including
  canonical semantic text, type-specific facets, future-use instructions,
  temporal/provenance anchors, fact bundles, and conflict/update guards.
  Scarlet still writes only canonical memory fields; derived surfaces are
  backend-owned and rebuildable.
- V1.10.0 OpenRouter retrieval shadow:
  `retrieval_shadow_backend=openrouter` can run cloud embeddings over
  `memory_surfaces`, cache stable surface vectors in `embedding_vectors`,
  and optionally run rerank as a second-stage precision comparison. Active
  ranking remains unchanged.
- V1.11.0 active hybrid retrieval calibration:
  `retrieval_shadow.grouped_results` deduplicates dense/rerank evidence by
  memory, and `retrieval_hybrid_mode=off|shadow|active` can promote grouped
  dense/rerank scores into automatic `memory.context` and manual
  `/mind/memory/search` ranking.
- V1.11.1 NetworkX associative graph expansion:
  runtime memory retrieval and manual memory search build a lightweight
  domain graph over memories, derived graph rows, and backend-owned discourse
  domains. This adds an explicit `retrieval_graph` trace so Scarlet can receive
  memories that belong to the current field of discourse, such as a chocolate
  limit during a warm evening beverage request.
- V1.11.2 compact memory packets:
  `runtime_context.memory_context.selected` and
  `turn.perception.content.memory_retrieval.selected` now use
  `memory-packet-v1`, keeping Scarlet's model-facing evidence compact and
  functional while leaving full retrieval internals in the trace layer.
- V1.11.3 retrieval/facts consistency:
  OpenRouter embedding cache usage now updates the corresponding
  `memory_surfaces` status/model/vector id, and `/mind/memory/facts` no longer
  treats the operational `intent` as an implicit fact query.
- V1.11.4 fact canonicalization stabilization:
  short fact aliases are matched as standalone phrases/tokens instead of
  substrings, `response_format` requires explicit structural evidence, and
  noisy historical facts from the old extractor are archived in the laboratory
  DB.
- V1.12.0 role-aware retrieval surfaces:
  `memory_text` and type-specific surfaces are content-focused, sparse/graph
  memory text no longer includes `reason_for_storage` or
  `expected_future_use`, and grouped dense/rerank results expose
  `promotable_score`, `support_score`, `surface_role`, and
  `active_rank_eligible` so auxiliary surfaces can support but not select a
  memory alone.
- V1.15.0 memory field stabilization:
  direct Scarlet writes now supply only semantic type/scope/content/reason/use;
  stored confidence/salience are neutralized in ranking; agent-supplied tags
  and metadata are audit-only; manual search is cross-scope by default;
  internal content chunks support long-memory retrieval; and
  `POST /mind/memory/graph` exposes associative KG navigation.

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
- Legacy ignored model-supplied values can remain in audit metadata for
  traceability, but they are not active provenance or ranking fields.
- Graph expansion is now active and navigable, but still lightweight:
  it improves associative recall and gives Scarlet a graph door from a known
  memory, but it does not replace future embedding/KG entity resolution,
  temporal staleness, or lifecycle automation.
- Atomic facts are operational but still conservative: V1.11.3 removes one
  source of false empty results, and V1.11.4 removes the known short-alias
  substring bug. Deeper entity extraction, tag/entity quality, and conflict
  quality remain future stabilization work.

Primary docs:

- `docs/memory-roadmap.md`
- `docs/decisions.md#adr-0026---pre-final-semantic-memory-consolidation`
- `docs/bug-ledger.md#bug-0024---semantic-memory-consolidation-treated-as-opt-in`
- `docs/bug-ledger.md#bug-0025---model-supplied-memory-provenance-can-be-stale-in-metadata`
- `docs/bug-ledger.md#bug-0027---recognized-semantic-candidate-not-written`
- `docs/bug-ledger.md#bug-0032---scarlet-can-emit-pseudo-tool-invocation-text-instead-of-real-tool-use`
- `docs/experiments.md#exp-0019---integrated-direct-scarlet-probes`
- `docs/experiments.md#exp-0029---memory-retrieval-readiness-layer`

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
- V1.7.1 instructs Scarlet to treat already-injected runtime context, selected
  memory, and visible same-session history as sufficient evidence for
  contextual answers when no source-sensitive or state-changing claim is being
  made.

Still monitoring:

- Retrieval is stronger than lexical v0, but still sparse/entity-light and can
  miss synonyms, paraphrases, or ambiguous entities until embeddings and
  stronger entity guards exist.
- V1.3.0 now exposes a retrieval-readiness manifest in memory search/context
  traces and keeps surfaces/graph rows as derived state, but dense retrieval is
  not yet active in ranking.
- V1.3.1 validates the shadow adapter path with live Scarlet evidence, but the
  active ranking is still FTS5/BM25 plus lexical/fact logic until a real
  embedding model is selected and tested.
- V1.11.0 adds controlled active hybrid ranking, but dense/rerank thresholds
  and weights still need live Scarlet calibration before treating it as the
  default memory path.
- V1.4.0 validates surface taxonomy with direct Scarlet evidence: a
  chocolate-preference memory generated preference, future-use, temporal, fact
  bundle, and canonical surfaces; Scarlet then used the memory correctly in a
  snack recommendation turn.
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
- V1.8.0 extends the same route with controlled previous-turn thinking
  retrospection. Retrospective modes can inspect the previous completed turn's
  user request, final answer, public notes, tool calls, event markers, and
  provider thinking at `digest`, `excerpt`, or `raw` detail.
- V1.9.0 adds backend-owned `metacognitive.context` shadow generation before
  the model request. In default `shadow` mode it is trace/UI-only and is not
  injected into `<runtime_context>`; controlled `inject` mode can add it as a
  `metacognitive_context` runtime block for A/B tests.
- The route accepts common observed model aliases and attempts one JSON repair
  retry.
- Recommended actions are annotated with schema availability.

Confirmed:

- Scripted tests verify route traceability, alias tolerance, JSON repair,
  previous-turn thinking retrospection, and that removed parallel cognitive
  routes are unavailable.
- Backend tests verify shadow mode is not model-facing and inject mode becomes
  model-facing only when configured.
- Initial live probe `ses_9f7b8e37cc2145508867bd45b96f3553` confirms Scarlet can
  autonomously choose retrospective metacognition when asked to audit previous
  reasoning, but also shows detail-level calibration risk (`excerpt` instead of
  cheaper `digest`).

Still monitoring:

- Live behavioral evidence is not yet strong enough to say Scarlet reliably
  invokes metacognition when she should.
- Shadow lesson selection is deterministic and not yet evidence that active
  metacognitive guidance improves Scarlet. It must be compared against inject
  mode with identical prompts.
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
- V1.5.1 semantic stream blocks for MiniMax M3: provider text in messages that
  stop on `tool_use` becomes `assistant.note.emitted`, provider text in
  `end_turn` messages becomes `assistant.answer.completed`, and provider
  thinking blocks become ordered `llm.thinking.captured` UI blocks.
- `GET /api/debug/events`.
- `GET/PUT /api/dashboard/settings`.
- `GET /api/dashboard/memories`.
- `GET /api/dashboard/profile`.
- Streaming chat emits live `runtime_event` rows.
- Frontend renders persisted events before falling back to traces.
- Right pane now acts as a selected-session inspector with tabbed histories for
  memories, agent actions/tool calls, internal system events, and
  warnings/errors.
- Header actions expose the current-session inspector and settings/global-view
  entrypoint separately, so future global analysis screens do not get mixed
  with per-session diagnostics.
- Tailwind is now the frontend styling foundation, with component classes
  layered over Tailwind utilities for consistent dashboard layout.
- The center chat now renders runtime context, automatic memory retrieval,
  Mind API calls/results, session recall, schema results, metacognition, public
  notes, and final answers as top-level chronological flow cards instead of a
  single assistant-response card containing nested blocks.
- Per-card detail/code controls expose raw JSON, memory details, runtime
  payloads, and tool input/output when needed for debugging.
- Tool-use is rendered as a single accordion per tool call with readable route,
  input JSON, output JSON, and human-readable result summary, instead of split
  call/result fragments.
- V1.6.0 adds a model-input inspector tab that renders the exact persisted
  `llm.request`: system prompt, injected runtime context, provider-native
  messages, and tool schema.
- V1.6.0 adds `docs/block-registry.md` as the canonical map of model-facing,
  UI-facing, trace-only, canonical, and redundant compatibility blocks.
- Replayed historical tool cards now enrich completed events with matching
  `mind.tool_call` traces so the full output remains visible after reload, not
  only the event summary.
- V1.7.0 adds frontend stream block lifecycle: text, thinking, tool, memory,
  and runtime blocks have stable block identity and phase metadata during live
  stream and persisted replay.
- Public text now appears during `text_delta` as a provisional visible block
  before being finalized as note or answer.
- V1.7.2 keeps long-reasoning progress notes prompt-owned: Scarlet should emit
  short public orientation waypoints during prolonged reasoning, while the
  backend/UI contract remains unchanged.
- V1.8.0 keeps previous thinking out of ordinary public transcript dependence:
  Scarlet can request a metacognitive retrospective pack when process evidence
  matters.
- V1.9.0 renders `metacognitive_context` shadow blocks in the center flow and
  inspector, separate from Mind API metacognition tool results.
- `turn_complete` reconciles live blocks with persisted events/traces instead
  of blindly replacing the visible flow.
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
- Live V1.5.1 M3 probe confirmed persisted order:
  `assistant.note.emitted` -> `mind.tool_call.started/completed` ->
  `assistant.answer.completed`.
- UI probe on a dense persisted session confirmed the center chat no longer
  renders the old `.message-body` / `.agent-turn.embedded` wrappers and uses
  top-level `chat-flow-card` blocks for the chronological flow.
- V1.6.0 frontend build confirms the new `Modello` inspector compiles against
  the current trace shape.
- V1.7.0 frontend build confirms the lifecycle/reconciliation changes compile
  against the current stream event shape.
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
- Payload optimization remains intentionally deferred: top-level runtime
  compatibility mirrors are visible as redundancy candidates, but not removed
  until direct Scarlet tests prove no regression.
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
    similar-memory, and canonical-fact preflight;
  - cautious proposal resolution in the same idle job: deterministic archive
    for rejects/duplicates, conservative auto-create for very safe candidates,
    and one optional batched LLM resolver for ambiguous proposals.
- Maintenance emits `maintenance.job.*` and
  `maintenance.memory_review.completed` events, and writes
  `maintenance.memory_review` plus optional
  `maintenance.memory_proposal_resolution` traces. The review event reports
  proposal and resolution counts.

Confirmed:

- Targeted backend tests verify job scheduling, supersession, idle skip when a
  newer turn exists, summary refresh, review/proposal output, and live chat
  event emission.
- Direct MiniMax probe confirmed the idle job can catch a missed memory write
  when Scarlet emits pseudo tool-call text and no real `mind.memory.write`
  trace exists.
- A second integrated probe confirmed the idle job also catches quieter missed
  writes where Scarlet answers coherently but never calls the memory endpoint.
- The review no longer writes every candidate blindly. It creates proposals
  first, then resolves only safe cases. Created maintenance memories carry
  `created_by=maintenance` and proposal provenance.
- Pending memory proposals and maintenance jobs are not Scarlet-facing
  `mind_shell` capabilities. They are consumed through maintenance/evaluator
  APIs:
  `GET /api/maintenance/overview`,
  `GET /api/maintenance/jobs`,
  `POST /api/maintenance/jobs/{job_id}/run`,
  `GET /api/maintenance/memory/proposals`, and
  `POST /api/maintenance/memory/proposals/{proposal_id}/archive`.
- `memory_proposals` is now the daily ledger for future Dream review; resolved
  rows retain preflight, outcome, reason, and memory snapshot when applied.
- A direct real MiniMax probe on a temporary DB confirmed the full path:
  summary, missed-memory review, proposal, LLM resolver, `applied_create`
  status, active maintenance-created memory, and
  `maintenance.memory_proposal_resolution` trace.

Still monitoring:

- Live MiniMax behavior still needs evaluation after the 15-minute idle window.
- Pending-review proposals need future UI/Dream decisions for merge, update,
  deprecation, or human/evaluator approval.
- BUG-0032 must be discussed before implementing a direct fix for pseudo
  tool-call text.
- Some maintenance candidates are useful but not clean enough for automatic
  writes yet; one probe produced a valid open-loop checkpoint with
  `confidence=0.0` and `salience=0.0`.
- Natural conversation probes show that stale memories are now a higher
  priority than merely detecting missed memories.
- M3 is intentionally kept active for owner-led human testing; M2.7 rollback
  remains a one-line `.env` change.
- BUG-0040: live maintenance overview exposed failed idle jobs caused by
  provider `ReadTimeout`; retry/resume policy is not implemented yet.

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

- decide how future Dream/human review should process pending-review and
  resolved daily-ledger proposal rows;
- stale-memory detection and lifecycle repair for old technical baselines that
  conflict with current runtime state;
- memory promise detection, e.g. final answer says "I will remember" without a
  matching `memory.write`;
- memory health/lint pass for stale, conflicting, duplicate, or corrupted
  memories.

Already implemented:

- `turn.completed` schedules per-session idle maintenance.
- The idle job runs summary refresh, missed-memory review, proposal creation,
  cautious resolution, and daily-ledger updates.
- V1.5.0 exposes lab inspection and controlled job execution through
  maintenance/evaluator APIs.

Why next:

The first maintenance slice exists and should not be duplicated. The next
decision should be based on live evidence from pending/resolved proposal
quality, skipped/failed jobs, and maintenance-created memories.

### 3.2 Retrieval Quality Upgrade

Need:

- direct live evaluation of temporal + sparse retrieval;
- entity-aware relevance guard;
- stronger selected/near_miss/excluded thresholds;
- better trace explanations for retrieval decisions;
- optional dense retrieval after Windows/GPU embedding setup.

Key acceptance:

- Nebbia-Rossa must not select Zero-Luce.
- Elliptical Zero-Luce follow-ups must still work when dialogue context makes
  the referent clear.

Pre-embedding boundary:

Do not add brittle lexical guard fixes or lifecycle-changing similarity
automation before the embedding/KG substrate is ready. The current priority is
observability and evaluation, not hard-coded ranking patches.

### 3.3 Memory Proposal Inbox And Compaction

Need:

- Dream review over daily proposal ledger rows;
- merge/update/deprecate policy for pending-review proposals;
- `POST /mind/memory/propose` only if a later experiment proves Scarlet needs a
  model-facing proposal primitive;
- `POST /mind/memory/compact`

Purpose:

Separate immediate in-turn semantic memory writes from durable consolidation,
merge, duplicate repair, and stale-memory cleanup.

Current status:

Proposal storage, preflight, cautious resolution, and daily-ledger preservation
already exist. Merge/update/deprecate should wait until embedding/KG evidence
improves matching quality.

### 3.4 Deterministic Answer Validators

Need:

- validator for unsupported exhaustive claims;
- validator for memory conflict hiding;
- validator for memory promise without write;
- validator for source-sensitive claims based only on paginated session lists
  or summaries.

Why not first:

The owner intentionally deferred linguistic validators and prompt/code
forzature. Some issues such as "I will remember" may be solved by existing or
future maintenance, so validators belong near platform finalization unless a
critical safety issue appears.

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

Current state:

V1.18.0 implements the first real attention/focus route as `POST /mind/focus`.
The route manages foreground focus state and archive history; it deliberately
does not duplicate or narrow memory retrieval. V1.21.0 adds
`action=timeline` to inspect focus transition edges and attention movement
history.

### 3.8 Goal/Focus/Task Organ

Need:

- owner review of `docs/theory-goal-focus-task.md`;
- definition of what counts as Scarlet's own goal versus user/project goal;
- lifecycle design for goals, focus, open loops, and tasks;
- evidence rules so goals are sourceable and not invented identity;
- no API/storage implementation until theory is approved.

Current state:

V1.18.0 implements the first operational focus organ:

- dedicated `focus_records` and `focus_transitions` tables;
- one active profile-scoped focus at a time;
- `POST /mind/focus` lifecycle operations;
- `POST /mind/focus action=timeline` for transition/history inspection;
- model-facing `focus_context` runtime block when `organ_focus_mode=model`;
- focus events/traces for creation, update, closure, and surfacing.

V1.19.0 implements the first operational volition slice:

- dedicated `intention_records` and `intention_links` tables;
- `POST /mind/volition` lifecycle operations;
- `POST /mind/volition action=list_due` for future autonomous-cycle queues;
- manual active-chat visibility with no automatic `volition_context` injection;
- focus-candidate promotion that returns a suggested `/mind/focus` body without
  mutating focus;
- volition events/traces for creation, update, review, closure, and
  focus-candidate promotion.

V1.20.0/V1.21.0 implements the first operational affect organ:

- dedicated `affect_states` table;
- backend-appraised human emotion prototypes;
- `organ.affect` traces/events;
- `affective_context` runtime block in `organ_affect_mode=model`;
- read-only `POST /mind/affect` for current state, history, and prototypes.

Temporal-experience and dream organs remain unimplemented. Autonomous volition
cycles remain planned but not implemented.

### 3.9 Metacognition Organ

Need:

- owner review of `docs/theory-metacognition.md`;
- decide whether the existing `/mind/metacognition/step` should become a
  pre-answer checkpoint loop, remain opt-in, or be replaced;
- define how metacognition differs from public notes, maintenance, and
  validators;
- behavioral tests proving answer improvement before adding endpoints.

Current state:

The single endpoint exists, but autonomous use is not reliable enough to call
the branch mature. V1.5.0 adds theory, not new metacognitive APIs.

### 3.10 CLI And Debug Memory Views

Need:

- CLI wrappers for memory list/show/conflicts/deprecate/supersede/lint/compact;
- cockpit views for active memories, conflicts, lifecycle history, proposals,
  and retrieval diagnostics.

Why:

The project is API/CLI-first. The human evaluator should be able to inspect and
repair memory health without writing SQL.

### 3.11 Broader Behavioral Evals

Need:

- live adaptive probes for autonomous memory write across personal facts,
  project checkpoints, preferences, corrections, and neutral facts;
- metacognition trigger probes where the user does not name metacognition;
- source-sensitive episodic recall probes;
- runtime-event UI probes;
- future background-maintenance acceptance tests.

### 3.12 Runtime Context Pack Router

Need:

- classify organs, sources, and capabilities by always-on, conditional,
  on-demand, background-only, and future/embodied status;
- define coupling rules so linked surfaces such as memory/facts,
  perception/actuation, or focus/volition are not split accidentally;
- keep the always-on spine compact while routing source-sensitive, temporal,
  project, emotional, and future embodied modes to different context packs;
- add a shadow router that traces which pack would have been selected before
  changing model-facing prompt composition;
- add budget/degradation metadata so raw diagnostics, archival source text, and
  high-frequency sensory state do not crowd out the current turn.

Current state:

Documented as the V1.26.0 planning baseline in
`docs/runtime-context-packs.md`. No runtime router has been implemented yet.

Why next:

Live Scarlet already has several organs and evidence sources. Future robotic
embodiment will add high-frequency eyes/audio/voice/movement context. The
project needs routing architecture before adding those streams, not after the
prompt becomes an unbounded context dump.

## 4. Priority Reorganization

### P0 - Keep The Microscope Trustworthy

Goal:

Do not build more cognition before the observability layer stays coherent.

Work:

- keep events/traces/schema/docs aligned;
- run full backend suite and frontend build after meaningful changes;
- keep `docs/project-state.md` updated after major milestones.
- keep M3 active for owner testing, with M2.7 rollback by `.env`.

### P1 - Evaluate Current Maintenance And M3

Goal:

Use the maintenance system that already exists. Do not add overlapping
background processes until pending/resolved proposals, skipped jobs, failed
jobs, and maintenance-created memories have been inspected after live use.

Implemented:

1. Deterministic `maintenance_jobs` records.
2. Per-session idle scheduling after `turn.completed`.
3. Session summary refresh through the existing summarization endpoint.
4. Missed-memory review.
5. Pending memory proposals with duplicate/similarity/fact preflight.
6. Cautious proposal resolution and maintenance-created memories.
7. Maintenance events/traces visible to debug/UI.
8. V1.5.0 lab/evaluator APIs for overview, jobs, manual job run, and proposal
   archive.

Why:

This directly addresses observed memory inconsistency without adding more
burden to Scarlet's prompt.

Next P1 evaluation:

- owner runs human M3 sessions;
- inspect `/api/maintenance/overview` after idle windows;
- inspect pending/resolved `memory_proposals` for quality and noise;
- inspect skipped/failed `maintenance_jobs`;
- decide whether any maintenance thresholds need tuning, without fixing
  unrelated retrieval/matching limitations prematurely.

### P2 - Memory Retrieval Upgrade With Cloud/Local Embedding Evidence

Goal:

Make memory evidence more reliable before enforcing strict answer validators.

Recommended order:

1. keep current temporal + FTS5/BM25 behavior observable;
2. run OpenRouter cloud embedding/rerank in active-hybrid mode on live memory
   cases, with negative controls and trace review;
3. prepare Windows local embedding environment for BGE-M3 or another selected
   local provider;
4. compare cloud vs local embeddings on the same `memory_surfaces`;
5. add KG expansion only after graph evidence is useful;
6. only then revisit merge/update/deprecate automation.

### P3 - Goal/Focus/Task Theory Review

Goal:

Approve what goal, focus, open loop, and task mean for Scarlet as a digital
individual before implementing the organ.

Work:

- review `docs/theory-goal-focus-task.md`;
- decide first minimal lifecycle and evidence rules;
- keep implementation blocked until theory is accepted.

### P4 - Metacognition Theory Review

Goal:

Define metacognition as a behavior-improving control process, not cosmetic
thinking or endpoint proliferation.

Work:

- review V1.8.0 thinking-retrospection behavior with direct Scarlet probes;
- run V1.9.0 shadow-versus-inject probes with identical prompts and measure
  whether candidate lessons reduce overthinking, missed memory commitments, and
  unsupported source-sensitive claims;
- decide whether retrospective modes become part of routine drift/open-loop
  control or remain debug/research-only;
- define the next metacognition loop only after behavioral evidence confirms
  that process retrospection improves answers.

### P5 - Source-Sensitive Answer Validation

Goal:

Prevent final answers from becoming stronger than the evidence.

Why later:

The owner explicitly wants to avoid brittle prompt/code forzature unless a
direct risk justifies them. Some validator targets may be solved by maintenance
or future metacognition.

### P6 - Human Operator Surfaces

Goal:

Make the lab maintainable as state grows, but avoid product UX churn unless it
helps evaluation.

Work:

- cockpit views for maintenance overview/proposals/jobs;
- memory health dashboard after embedding/KG;
- exportable run summaries;
- CLI commands only when they reduce evaluator friction.

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
- `docs/theory-goal-focus-task.md`: pre-implementation theory for the future
  Goal/Focus/Task organ.
- `docs/theory-metacognition.md`: pre-implementation theory for the future
  metacognition organ.
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

The next work cycle should focus on context-pack shadow planning before new
automation:

```txt
runtime context-pack shadow router + continued M3 human testing
```

Reason:

The backend already emits events, schedules idle maintenance, summarizes
sessions, reviews missed memories, creates/handles proposals, and preserves a
daily ledger. Scarlet also now has enough organs that context routing itself is
becoming an architectural risk. The highest-value next move is to trace which
context pack each real turn would have selected while continuing human M3
sessions, then use that evidence before changing live model input.

Parallel non-coding review:

- evaluate `docs/theory-goal-focus-task.md`;
- evaluate `docs/theory-metacognition.md`;
- use `docs/runtime-context-packs.md` as the baseline for future organ/context
  discussions;
- keep embedding/KG work parked until the Windows GPU environment is available.
