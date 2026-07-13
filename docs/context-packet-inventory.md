# Context Packet Inventory

Last reviewed: 2026-07-12
Code baseline reviewed: V1.29.0
Status: reviewed legacy inventory plus implemented V2 disposition

## Purpose

This is the field-level inventory of dynamic data packets that can reach Scarlet
without a preceding `mind_shell` command. It separates actual model input from
data that exists only for trace, UI, debugging, evaluation, or deterministic
backend work. It observes current implementation; it does not approve every
automatic packet or change any packet.

V1.29.0 implemented the approved session/memory disposition recorded later in
this file. Sections describing `runtime-context-v1` remain as the audit of the
rich internal/legacy source snapshot. Active model delivery now uses
`scarlet-model-context-v2`; undiscussed families are carried under
`preserved_context` until their own review.

For every packet this inventory records its contents, why Scarlet receives it, its destination, and its delivery class.

## Delivery Classes And Targets

| Class | Meaning |
| --- | --- |
| `automatic_model` | Built before the answer and sent to local MiniMax Scarlet. |
| `automatic_model_conditional` | Sent automatically only if an organ/runtime mode enables it. |
| `automatic_gpt_bootstrap` | Returned to external ChatGPT Scarlet by `/gpt/bootstrap`. |
| `manual_model_result` | Returned only after Scarlet invokes `mind_shell` or `/gpt/action`. |
| `trace_ui_only` | Persisted for trace, UI, debugging, replay, or evaluation; not automatically sent to the model. |
| `backend_only` | Used by storage, retrieval, maintenance, or routing without automatic model delivery. |

`Local Scarlet` means the MiniMax-backed chat runtime. `External GPT Scarlet` means the ChatGPT GPT using the bridge. The GPT's configured Instructions and native ChatGPT history are platform-owned and outside this repository's packet assembler.

## Automatic Delivery Paths

### Local MiniMax Runtime

Every local turn has this provider shape:

```txt
tools    = [mind_shell schema]
system   = base Scarlet system prompt + <runtime_context>{...}</runtime_context>
messages = provider-native active-session history + current user message
```

The exact request is persisted in `llm.request`. `memory.context` and `runtime.context` are built before the request.

### External ChatGPT GPT Bridge

`POST /gpt/bootstrap` builds the same memory and runtime context, but does not call MiniMax. It returns a compact bridge response; the GPT can then use `POST /gpt/action` for manual shell commands and `POST /gpt/finalize` to close the turn.

## Technical Delivery Boundary: Not Context Packs

The following inputs are technically required for a turn but are explicitly
outside the current context-packet work. They have dedicated management and
will not be selected, routed, or budgeted by the future dynamic context-pack
router unless a separate decision reopens them.

### P-01 Base Scarlet System Prompt

Static policy for native MiniMax Scarlet: identity, communication, evidence,
memory, and tool-use rules. It is passed only to the native backend runtime.
External GPT Scarlet instead uses the prompt manually configured in the GPT
Builder dashboard; the bridge does not transport the native full prompt.

### P-02 Provider-Native Active-Session History

Active-session continuity, not a context packet: prior user/assistant text and
provider-native `thinking`, `tool_use`, and `tool_result` blocks. It remains
managed by the provider-history mechanism, separately from semantic memory,
episodic retrieval, and dynamic runtime perception.

### P-03 Tool/Action Schema

Static capability surface, not a context packet. Native Scarlet receives the
single `mind_shell` tool schema; external GPT Scarlet uses its independently
configured GPT Actions schema. Neither belongs to dynamic context routing.

## Dynamic Local Context Packets

Unless a row says otherwise, P-01 through P-11 are sent to Local Scarlet. The
same runtime blocks are also represented inside the external GPT's P-12
bootstrap string; P-13 through P-16 are bridge-specific additions.

### P-04 Runtime Context Envelope

| Property | Current behavior |
| --- | --- |
| Delivery | `automatic_model` |
| Source | `render_runtime_context()` over `runtime-context-v1`. |
| Recipients | Local Scarlet; the same rendered string is included in external GPT bootstrap as P-12. |
| Function | Declares blocks as backend evidence, not user instructions; gives each block id/type/scope/lifetime/source. |
| Excluded from | Raw retrieval internals, arbitrary database tables, and trace payloads not represented by blocks. |

`runtime_context.blocks` is canonical. P-11 documents legacy compatibility mirrors also included in the envelope.

### P-05 `session_context`

| Property | Current behavior |
| --- | --- |
| Delivery | `automatic_model` |
| Source | `_session_context_block()` plus session, summary, and memory repositories. |
| Function | Lightweight cross-session episodic orientation without opening previous full transcripts. |

| Field | Current selection | Why it is sent |
| --- | --- | --- |
| `current_session` | id, title, timestamps, raw session metadata | Identify the active session and stored framing. |
| `previous_sessions_policy` | explanatory policy | Mark summaries as navigation aids rather than proof. |
| `previous_sessions` | up to 2 most recently updated sessions; each has summary/fallback, topics, decisions, open questions, memory ids, counts, timestamps | Give continuity hints and ids for later exact recall. |
| `previous_session_memories` | up to 5 active memories from the most recent previous session | Give a short semantic bridge from the latest prior session. |

Current selection is by recency, not semantic relevance to the current message.

### P-06 `message_context`: Message, Clock, Locale And Profile

| Property | Current behavior |
| --- | --- |
| Delivery | `automatic_model` |
| Source | Current persisted user message and `RuntimePreferences`. |
| Function | Provide an operational frame without asking Scarlet to infer the clock, platform language, profile, or privacy boundary. |

| Field | Current selection | Why it is sent |
| --- | --- | --- |
| `current_message` | ids, role, content up to 1,500 chars, timestamp, configured language | Current turn perception and response-language default. The message also appears in P-02. |
| `world` | configured backend clock, timezone, local-day data, configured country/timezone locale | Scarlet's operational clock and coarse locale. Explicitly not GPS or physical presence. |
| `user_profile.identity` | configured profile id and display name | Recognition and future multi-user separation. |
| `user_profile.privacy` | configured privacy scope | Boundary for user-scoped memories/profile facts. |
| `user_profile.locale` | configured language, country, timezone | Explicit profile defaults; partially overlaps `world`. |
| `user_profile.memories` | up to 5 newest active `scope=user` memories | Immediate personalization anchors; currently selected by creation recency, not query relevance. |

No weather, GPS, camera, microphone, body, robot, browser, or other live external-world feed is automatically injected today. Current world data is the backend clock and configured locale/profile settings.

### P-07 Automatic Semantic Memory Retrieval

| Property | Current behavior |
| --- | --- |
| Delivery | `automatic_model` |
| Source | `memory.context`: lexical retrieval, graph expansion, optional shadow/hybrid ranking, then `memory-packet-v1` compaction. |
| Recipients | Local Scarlet in `message_context.memory_retrieval`; repeated by P-11; equivalent data reaches the GPT through P-12/P-14. |
| Function | Supply relevant durable evidence, provenance, compact facts, validity/conflict signals, and negative evidence without a shell call on every contextual turn. |

| Field | Current selection | Why it is sent |
| --- | --- | --- |
| `selected` | at most 5 strong-signal memories | Direct candidate evidence for this turn. |
| `claim` | memory content up to 900 chars | The remembered proposition. |
| provenance | source session/turn/message ids and record times | Lets Scarlet open source evidence when needed. |
| `cognitive` | subject, domains, validity, sensitivity | Explain safe/useful interpretation. |
| `retrieval` | compact score, reason, routes and flags | Explain relevance without raw debug machinery. |
| `facts` | first 5 compact atomic facts per selected memory | Canonical entity/predicate/value state when available. |
| `near_miss` / `excluded` | id/type/scope/score/classification/reason summaries | Separate weak leads and non-evidence from selected memories. |
| `conflicts` | compact active fact conflicts | Require inspection rather than silent choice. |
| `negative_evidence` | explicit no-selection state | Calibrate absence claims. |

Automatic exclusions:

| Data | Delivery | Reason |
| --- | --- | --- |
| full candidate records, tags and metadata | `trace_ui_only` in `memory.context` | Retrieval/debug material is larger than direct evidence. |
| lexical queries, sparse query and retrieval readiness | `trace_ui_only` | Explain retrieval mechanics, not remembered truth. |
| graph paths/raw graph expansion | `trace_ui_only` | Associative mechanism, not proof by itself. |
| shadow payload, vectors, reranker/hybrid thresholds/debug | `trace_ui_only` | Calibration/debug data. |

### P-08 Recent Dialogue And Runtime Events

| Property | Current behavior |
| --- | --- |
| Delivery | `automatic_model` |
| Source | Current-session messages and `CognitiveEvent` records, excluding the current turn. |
| Function | Compact orientation to recent dialogue and completed/failed cognitive activity. |

| Field | Current selection | Why it is sent |
| --- | --- | --- |
| `recent_dialogue` | last 8 visible user/assistant messages, each up to 1,200 chars | Compact conversational recency; the same conversation also exists in P-02. |
| `recent_runtime_events` | up to 16 compact event summaries | Recovery/orientation without raw event payloads. |

Compact events retain identity plus selected operational fields such as operation, method/path, result summary, retrieval counts, negative evidence, and errors. Full event payloads are trace/UI-only.

### P-09 API Mind Capability Hints

| Property | Current behavior |
| --- | --- |
| Delivery | `automatic_model` |
| Source | shell metadata, command catalog, capability state. |
| Location | `message_context.api_mind`. |
| Function | State that `mind_shell` is the model-facing interface, expose family purposes, and distinguish available/internal capability status. |
| Excluded from | Full `help` response and detailed per-command examples, which require manual `help`. |

### P-10 Dynamic Organ Blocks

| Packet | Delivery | Current condition | Function | Automatic exclusion |
| --- | --- | --- | --- | --- |
| `focus_context` | `automatic_model_conditional` | `organ_focus_mode=model` plus active focus | Foreground attention and recent transitions; not semantic memory. | Full focus history remains manual/trace. |
| `affective_context` | `automatic_model_conditional` | `organ_affect_mode=model` plus a model block | Tone/caution/warmth posture, never factual truth. | Full appraisal diagnostics/history remain manual/trace. |
| `metacognitive_context` | `automatic_model_conditional` | `metacognitive_context_mode=inject` | Controlled A/B injection of few trigger-matched operating lessons. | Default `shadow` payload is trace/UI-only and non-influential. |
| `scarlet_state` | `automatic_model` | always built | Transitional backend-seeded focus/posture/goal/open-loop surface. | No arbitrary hidden backend state is rendered. |

`volition` has no automatic runtime block today; it is shell-only.

### P-11 Top-Level Compatibility Mirrors

| Property | Current behavior |
| --- | --- |
| Delivery | `automatic_model` |
| Source | Copies from canonical blocks for legacy prompt/tests. |
| Function | Compatibility only; not an independent evidence source. |

```txt
memory_context        = message_context.memory_retrieval
mind_shell            = message_context.api_mind.schema
temporal_context      = contained in message_context.world
recent_runtime_events = message_context.recent_runtime_events
capabilities          = message_context.api_mind.capabilities
```

These fields are intentionally redundant. Any removal requires a separate behavioral compatibility decision and regression evidence.

## External GPT Bootstrap Packets

### P-12 Rendered Runtime Context

| Property | Current behavior |
| --- | --- |
| Delivery | `automatic_gpt_bootstrap` |
| Source | Same rendered `runtime-context-v1` string as P-04. |
| Function | Give the external GPT backend perception, continuity, and capability context for the turn. |
| Excluded from | Full effective local prompt, raw runtime payload, raw retrieval diagnostics. |

### P-13 Runtime Summary And Protocol Metadata

| Property | Current behavior |
| --- | --- |
| Delivery | `automatic_gpt_bootstrap` |
| Contents | Block summaries/counts, clock/capability metadata, session/turn ids, provider-history statistics, action/finalize hints, tool identity, trace ids, omitted-diagnostics declaration. |
| Function | Let the GPT orient itself and continue the bridge protocol without all backend diagnostics. |

### P-14 Compact Bridge Memory Context

| Property | Current behavior |
| --- | --- |
| Delivery | `automatic_gpt_bootstrap` |
| Contents | Search status, clock, compact query-plan metadata, selected/near-miss/excluded memories, conflicts, counts/budget, omitted-debug declaration. |
| Function | Make automatic-memory processing inspectable to the external GPT. |
| Excluded from | Raw turn frame and raw retrieval readiness/graph/shadow/hybrid diagnostics. |

P-14 overlaps semantically with P-07 embedded in P-12. It is a bridge convenience surface, not an independent memory source.

### P-15 Compact Metacognitive Context

| Property | Current behavior |
| --- | --- |
| Delivery | `automatic_gpt_bootstrap` when a metacognitive payload exists |
| Contents | mode, model-facing flag, trace id, selected/near-miss lessons and suggested actions. |
| Function | Expose the backend's metacognitive context state without raw reasoning. |

### P-16 Recent Provider Messages For Bridge Continuity

| Property | Current behavior |
| --- | --- |
| Delivery | `automatic_gpt_bootstrap` |
| Contents | Last 8 provider-style messages; text up to 1,200 chars; tool ids; thinking represented only by a presence summary. |
| Function | Recover backend session continuity when native ChatGPT history is insufficient. |
| Excluded from | Full provider history and thinking content. |

## Automatic Trace/UI-Only Packets

| Packet | Function | Why it stays outside normal automatic model input |
| --- | --- | --- |
| full `memory.context` trace | Query, raw candidate ranking, selected records, graph/shadow/hybrid diagnostics, budget | Retrieval mechanics can dwarf direct evidence. |
| `metacognitive.context` in shadow mode | Evaluate lesson selection before behavioral injection | Shadow mode must not influence the request. |
| `runtime.context` and `llm.request` traces | Audit exact request, rendering profile, history source, tools | Observability copies, not additional evidence. |
| `llm.response`, raw provider messages, captured thinking events | Replay provider behavior | Historical diagnostic material. P-02 is the separate continuity path. |
| full cognitive-event payloads | UI/debug timeline and recovery evidence | P-08 sends compact summaries only. |
| raw KG nodes/edges, retrieval documents, embeddings/search indexes | Retrieval/debug/maintenance | Backend machinery, not direct automatic evidence. |
| maintenance jobs, proposals, maintenance reports | Background maintenance and evaluator visibility | No automatic model-facing packet exists. |
| dashboard/model inspector data | Human inspection of traces | Reading it in UI never adds it to Scarlet's context. |

## Manual-Only Boundary

The following information can reach Scarlet only after an explicit shell call; it is not automatic perception.

| Family | Examples | Returned data |
| --- | --- | --- |
| memory | `search`, `open`, `facts`, `graph`, `conflicts` | Targeted memory, facts, graph, lifecycle/conflict state. Search has a compact model profile. |
| episodic | `session list`, `session open`, `session summarize` | Session index, summary, transcript window, source memories. |
| focus | `read`, `list`, `timeline` | Foreground state and transitions. |
| volition | `list`, `read`, `review` | Intentions and links. |
| affect | `read`, `list`, `prototypes` | Appraised state/history/prototypes. |
| metacognition | `metacognition step` | Risks, evidence gaps, recommended available actions, public summary. |
| help | `help`, `help <family>` | Current shell catalog and syntax. |

Manual result size is a separate budget concern: `session open` currently has no transcript limit when Scarlet omits `--limit`, despite supporting a limit.

## Verified Current Boundaries

- Canonical dynamic model structure: `runtime_context.blocks`.
- Raw retrieval plans, KG diagnostics, embeddings, maintenance data and full event payloads are not automatically passed to Scarlet.
- Some automatic inputs are intentionally duplicated as compatibility mirrors.
- Two previous sessions and five user-scope memories are selected by recency, not current-message relevance.
- Previous-session summaries are navigation aids, not exact historical proof.
- Current world perception is configured time/locale only, not live sensors or external-world feeds.
- Focus, affect and metacognitive lessons are conditional; volition is manual-only.

## Review Questions Before Context-Pack Changes

1. Which facts, if any, deserve a narrow always-on user-constraint packet instead of recency-based `user_profile.memories`?
2. Should previous sessions remain automatic, become cue-gated, or be reduced to a minimal index?
3. Which compatibility mirrors must remain until behavioral tests prove Scarlet can use canonical blocks alone?
4. What independent budgets should apply to base prompt, runtime blocks, provider history, shell results, and GPT bootstrap?
5. Which fields are direct evidence, navigation hints, operational policy, or developer diagnostics?

## Owner Review Notes

The accepted notes below are consolidated into the phased implementation plan
in `docs/context-packet-implementation-plan.md`. Conflict semantics remain a
separate deferred workstream and are not part of the V1.29.0 packet plan.

### 2026-07-11: Episodic And Short-Term Continuity Direction

The owner reviewed the current `session_context` and rejected its broad,
recency-only shape as the target context-pack design. This is a desired future
packet contract, not implemented runtime behavior.

`previous_sessions` should remain an episodic-hint array limited to the latest
two sessions. Each item should contain only:

```json
{
  "id": "ses_...",
  "last_message_at": "...",
  "turn_count": 0,
  "summary": "..."
}
```

Its purpose is compact navigation: Scarlet uses the summary to understand the
general subject, the id to open the transcript when useful, the turn count to
estimate whether an inspection is worthwhile, and the temporal field to avoid
mistaken conversational recency claims. Topics, decisions, open questions,
memory ids, fallback machinery, and raw session metadata are not part of this
desired previous-session hint item.

`last_message_at` means the timestamp of the last user or assistant message in
that session. It must not reuse `sessions.updated_at`: the latter is a backend
maintenance/activity timestamp that can change when traces, events, or memory
records touch the session and is not useful temporal evidence for Scarlet.

Short-term memory continuity must be independent from the previous session. A
future separate recent-memory hint packet should contain the five most recently
processed memories accessible to the active profile, across all relevant memory
sources. Each item should contain only:

```json
{
  "id": "mem_...",
  "content": "...",
  "created_at": "...",
  "updated_at": "...",
  "source_session_id": "ses_...",
  "source_message_id": "msg_..."
}
```

The intended ordering is cognitive activity, not only record creation:

- manual Scarlet retrieval/read of an actually returned memory counts;
- saving or updating a memory counts;
- simple automatic retrieval does not count;
- automatic advanced retrieval counts only for memories that survive reranking
  and actually enter Scarlet's context;
- misses and skipped candidates do not count;
- a newly processed memory displaces the oldest item from the five-item hint
  set.

Only `id`, `content`, `created_at`, `updated_at`, `source_session_id`, and
`source_message_id` belong in Scarlet's recent-memory packet. The activity
ordering, access events, eligibility rules, and replacement bookkeeping are
systemic data: they are necessary for backend selection and audit but are not
cognitive evidence to send to Scarlet.

The current implementation differs: it surfaces memories only from the most
recent previous session in `session_context`, separately surfaces five newest
user-scope memories in `message_context`, and updates `last_used_at` for
automatic selected retrieval. No behavior change has been made from this note.

These questions were open at this stage of the review. The 2026-07-12 note
below closes immediate recency behavior. Future multi-user visibility is a
deterministic authenticated-user storage/query boundary, not a model-facing
packet policy.

### 2026-07-11: Session-Attached User Time And Location Direction

The owner decided that the model-facing world/time data belongs with session
continuity rather than as a separate turn-perception packet. This is a desired
future packet contract, not implemented runtime behavior.

The desired compact model-facing shape is:

```json
{
  "now": "2026-07-11T15:30:00+02:00",
  "timezone": {
    "id": "Europe/Rome",
    "name": "CEST",
    "utc_offset": "+02:00"
  },
  "location": "Italia"
}
```

`location` is one assembled human-readable address/locale string. Today it can
contain only the configured country; future trusted geolocation may assemble a
more precise value. It must not imply physical presence beyond the precision
the system actually has.

`now` is the current time already converted into the active human user's
timezone. Scarlet must never receive competing clocks or be asked to calculate
the user's local time herself. `turn_started_at`, timestamp/preference source,
storage timestamp policy, precision/status labels, and long interpretive policy
strings are systemic/trace data rather than default model-facing fields.

This establishes a cross-packet temporal rendering rule: all timestamps sent to
Scarlet, including prior-session `last_message_at` and recent-memory creation
or modification dates, must be rendered in the same active user reference
timezone as `now`. Persistence and maintenance may keep UTC or their own
administrative timestamps internally; those values must not be substituted for
the model-facing human time reference.

Future packet policies should be omitted by default. A compact reinforcing hint
may be added only after evidence shows that Scarlet repeatedly misuses a packet
without it. This restriction concerns only Scarlet/GPT model input: backend
retrieval, storage, calculations, traces, UI, logs, and maintenance retain the
data they need, except for a necessary verification that model-facing time is
consistently rendered from the active user timezone.

### 2026-07-11: Current Message Is Not A Context Packet

The owner decided that `message_context.current_message` is technical system
state, not useful dynamic context for Scarlet. Scarlet already receives the
actual current user message through the native conversational channel in both
the local MiniMax runtime and the ChatGPT GPT platform.

The following remain backend/trace/UI data and should not appear in Scarlet's
future model-facing dynamic context packs:

```txt
message id
session id
turn id
role
duplicated/truncated message content
stored message timestamp
configured language/source/policy metadata
```

This does not remove the native user message, persistent message record, turn
correlation, language settings, or trace evidence. It only excludes the
duplicate `current_message` representation from future Scarlet/GPT dynamic
context packet selection.

### 2026-07-11: User Data And User-Memory Continuity Direction

The owner decided that the non-memory user data should be merged into the
future session-attached context. Scarlet receives only the user's display name:

```json
{
  "user": {
    "name": "..."
  }
}
```

Profile id, privacy scope, identity source, locale, policy text, and future
access-control identifiers are deterministic system concerns. In a future
multi-user runtime, the backend must scope sessions, data, and memories through
the authenticated user id; Scarlet does not need that identifier or the access
policy in her dynamic context.

User memories remain a separate memory block, not a child of user/session
metadata. Alongside the five generic recent-memory hints, Scarlet should
receive up to five recent user-specific memory hints. They use the same compact
item shape:

```json
{
  "id": "mem_...",
  "content": "...",
  "created_at": "...",
  "updated_at": "...",
  "source_session_id": "ses_...",
  "source_message_id": "msg_..."
}
```

User-specific hints follow the same cognitive-activity ordering as generic
recent memories: creation/update and eligible manual/advanced retrieval may
make a memory recent; simple automatic retrieval, misses, and skipped records
do not. The generic and user-specific five-item sets must not contain the same
memory id. When candidates overlap, backend selection must either choose the
next distinct eligible memory or return fewer items rather than duplicate an
item across blocks.

The current implementation differs: `user_profile.memories` returns up to five
newest active user-scope records by creation time and is embedded with profile
metadata. No runtime behavior has changed from this review note.

### 2026-07-11: Provenance Hooks In Every Memory Hint

The owner decided that every model-facing memory hint, whether recent generic,
recent user-specific, or automatically relevant to the current turn, must also
include `source_session_id` and `source_message_id`. They are concise
provenance/navigation hooks, not an invitation to include source text
automatically.

Current navigation assessment:

- `memory open <memory_id>` reads the full memory and stored provenance;
- `memory facts --memory-id <memory_id>` inspects canonical facts;
- `memory graph <memory_id>` resolves the KG root internally from the memory
  id, so a separate graph-node id is not currently needed in a hint;
- `session open <source_session_id>` returns transcript messages carrying
  message and turn ids;
- no model-facing shell command currently opens a message or a turn directly.

The storage model already retains `source_turn_id`, but it is not yet part of
the requested compact hint contract. It can support a future direct
turn-navigation command if message-plus-session navigation is insufficient.

Required future shell navigation surface:

- direct inspection by source message id, for example `session message msg_...`;
- direct inspection by turn id, for example `session turn turn_...`;
- a compact turn view containing the triggering user message, tool/action
  exchanges and results, assistant response, and source trace references.

These commands must be model-facing shell commands backed by deterministic
lookup. They should replace the current need to open a whole session transcript
and manually locate the message/turn, while keeping full transcript inspection
available when needed.

### 2026-07-11: Relevant-Memory Hint Limit

The owner chose a default maximum of five automatically relevant memory hints.
The limit must be configurable so later evaluation can increase or reduce it
without changing the packet contract. The limit applies only to model-facing
selected relevant-memory hints; retrieval candidates, misses, ranking data, and
trace diagnostics remain backend/trace data.

### 2026-07-11: Cross-Block Memory Deduplication

The owner confirmed that every model-facing memory hint block must contain
unique memory ids. When the same memory qualifies for more than one block,
selection priority is:

```txt
automatically relevant memories
-> recent user-specific memories
-> recent generic memories
```

The lower-priority selector fills its available positions with the next
distinct eligible records, or returns fewer hints when no distinct record
exists. This concerns only model-facing packet composition; every qualifying
relation remains available in backend state and traces.

### 2026-07-11: Conflict Detection Requires Semantic Review

The owner rejected deterministic similarity as a semantic conflict decision.
Two similar memories can be compatible, complementary, time-separated, or
about different contexts. Future conflict work should therefore separate:

- deterministic candidate discovery, which may find exact duplicates, shared
  facts, related overlap, or structural anomalies but must label them as review
  candidates rather than semantic conflicts;
- semantic review by a maintenance LLM over sourceable DB evidence, or by
  Scarlet during manual memory search, write, update/supersession, or explicit
  conflict inspection;
- explicit, traceable lifecycle action only after that review; no automatic
  semantic conflict resolution from token/tag similarity.

Current implementation note: automatic runtime context treats same active
entity/predicate with different fact values as `atomic_fact_conflict`; manual
`memory conflicts` also emits exact-content candidates and tag/token overlaps
as non-conflict maintenance signals. Neither path currently has a dedicated LLM
semantic conflict adjudicator. No automatic conflict packet or lifecycle policy
has been accepted by this review.

### 2026-07-12: Session Fallback, Immediate Recency And Provider Parity

The owner closed the remaining decisions for the context families already
reviewed.

The current-session hint stays model-facing but contains only id, title, and
creation time. Raw session metadata and `sessions.updated_at` are systemic
because maintenance can change the latter without a new conversational
message.

A previous session without a persisted summary uses one fixed navigation hint:

```txt
Sessione con riassunto mancante; ispeziona la sessione per vedere i dettagli.
```

It must not receive a deterministic pseudo-summary assembled from title or
message fragments. Scarlet can use `session summarize <session_id>`; the
existing idle-maintenance default is 900 seconds. The implementation plan now
adds a bounded asynchronous reconciler on maintenance cycles and new-session
creation, rather than performing a synchronous summary call inside context
compilation.

Eligible memory activity changes recency state immediately. An initial turn
packet remains an immutable delivered snapshot, while later selectors in the
same turn and all subsequent turns see the updated order. Emitting a memory
inside a recent-memory packet never counts as activity and never changes its
timestamp. This prevents a fixed five-item packet from continually refreshing
itself.

Historical memories without complete source session/message hooks require a
read-only provenance and repairability audit. Sourceable legacy records should
be aligned to the current schema; only records explicitly confirmed as useless
or test-only should be considered for deletion. Missing provenance must never
be guessed, and incomplete records are not automatically model-facing until
repaired.

MiniMax and the external GPT bridge must receive the same API Mind dynamic
context contract. The bridge is only an alternative model connection and turn
transport; it is not a separate runtime, memory system, or context policy.

Duplicate/conflict handling remains a separate design workstream. Retrieval,
embeddings, exact matching, facts, and graph signals may generate candidates
for Scarlet or a maintenance LLM to review, but must not independently declare
semantic duplication or conflict.

## Sources

- `backend/app/mind/context.py`
- `backend/app/api/chat.py`
- `backend/app/mind/shell.py`
- `backend/app/mind/shell_presentation.py`
- `backend/app/mind/episodic.py`
- `backend/app/plugins/gpt_bridge/router.py`
- `backend/app/runtime/events.py`
- `docs/block-registry.md`
- `docs/runtime-context-packs.md`
