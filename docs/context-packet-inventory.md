# Context Packet Inventory

Last reviewed: 2026-07-18
Code baseline reviewed: V1.49.0
Status: active V2 inventory plus historical rich-source audit

## Purpose

This is the field-level inventory of dynamic data packets that can reach Scarlet
without a preceding `mind_shell` command. It separates actual model input from
data that exists only for trace, UI, debugging, evaluation, or deterministic
backend work. It observes current implementation; it does not approve every
automatic packet or change any packet.

V1.29.0 implemented the approved session/memory disposition recorded later in
this file. Sections describing `runtime-context-v1` remain as the audit of the
rich internal/legacy source snapshot. Active model delivery now uses
`scarlet-model-context-v2`. V1.35.0 completes the field-level review of
`preserved_context`: only compact focus, affect, and metacognitive blocks may
be projected automatically, and only when their organ mode enables them.
V1.36.0 introduced accounting and the shadow provider-history plan without
changing the V2 dynamic packet shape. V1.39.0 activates a separate derived
history view for native MiniMax only when a valid compaction artifact exists;
it still does not change the V2 dynamic packet fields inventoried here.
V1.46.0 through V1.49.0 separate retrieval, read, mutation, and maintenance
ownership without changing any automatic or manual model packet shape in this
inventory. Maintenance jobs, proposal internals, and their diagnostic evidence
remain backend/trace concerns unless a resulting active memory later qualifies
for normal context delivery.

V1.31.0 does not change the compact memory-hook shape. It changes which
memories qualify for `relevant`: multi-route recall remains internal, while a
memory-level reranker alone accepts and orders the automatic relevant list in
active mode.

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
messages = canonical active-session history + current user message
           OR valid compacted chronology + exact canonical tail + current user
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
provider-native `thinking`, `tool_use`, and `tool_result` blocks. Canonical
history remains append-only and is always used for persistence and audit. In
active V1.39 routing, a valid derived artifact may replace the older prefix in
the model request with a compacted chronology while preserving an exact recent
tail. Missing, stale, or unmappable artifacts fall back to the full canonical
history. This lifecycle remains separate from semantic memory, episodic
retrieval, and dynamic runtime perception.

### P-03 Tool/Action Schema

Static capability surface, not a context packet. Native Scarlet receives the
single `mind_shell` tool schema; external GPT Scarlet uses its independently
configured GPT Actions schema. Neither belongs to dynamic context routing.

## Active V2 Dynamic Packet

The active `model_context_profile=v2` sends one dynamic document:

| Area | Model-facing data | System-only data |
|---|---|---|
| session | current session id/title/created time, user name, active/resumable agent mode, one user-local clock/timezone/location, two previous-session hints | profile id/privacy, raw metadata, storage/update clocks, summary diagnostics |
| memories | deduplicated relevant/recent-user/recent-general hooks with id/content/times/source session+message | facts, scores, KG, lifecycle, near misses, exclusions, query plans, maintenance |
| preserved context | compact allowlisted focus, affect, or metacognitive fields when enabled | Scarlet state, duplicate dialogue, generic events, capability catalogs, organ diagnostics, and full rich runtime |

The exact JSON is stored in `model.context`. Native MiniMax receives its
rendered form; GPT bootstrap receives that same rendered form once, without a
second `context.model_context` copy.

## Rich Internal Source Packets

P-04 through P-11 describe the rich `runtime-context-v1` source snapshot.
They are no longer direct model packets under V2. Only allowlisted organ
subfields are copied into `preserved_context`; the rest stay
trace/UI/backend-only or are available through API Mind on demand.

### P-04 Runtime Context Envelope

| Property | Current behavior |
| --- | --- |
| Delivery | `trace_ui_only` rich source; projected into V2 |
| Source | `render_runtime_context()` over `runtime-context-v1`. |
| Recipients | Backend projection compiler, traces, UI, diagnostics, maintenance, and evaluation. Scarlet receives only the V2 projection. |
| Function | Preserve full backend evidence and compile the smaller V2 document. |
| Excluded from | Raw retrieval internals, arbitrary database tables, and trace payloads not represented by blocks. |

`runtime_context.blocks` is canonical for the rich internal snapshot, not for
the active model packet. P-11 documents legacy mirrors excluded by V2.

### P-05 `session_context`

| Property | Current behavior |
| --- | --- |
| Delivery | `trace_ui_only`; compact accepted fields become V2 `session` |
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
| Delivery | `trace_ui_only`; accepted user/world fields become V2 `session` |
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
| Delivery | `trace_ui_only`; selected records become compact V2 `relevant` hooks |
| Source | `memory.context`: lexical retrieval, graph expansion, optional shadow/hybrid ranking, then `memory-packet-v1` compaction. |
| Recipients | Traces/UI/maintenance; only compact eligible hooks reach either model. |
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
| Delivery | `trace_ui_only` in V2 |
| Source | Current-session messages and `CognitiveEvent` records, excluding the current turn. |
| Function | Preserve conversation/event diagnostics for UI, trace, replay, and future targeted recovery. |

| Field | Current selection | Why it is sent |
| --- | --- | --- |
| `recent_dialogue` | last 8 visible user/assistant messages, each up to 1,200 chars | Excluded from model input because P-02 is the authoritative same-session continuity. |
| `recent_runtime_events` | up to 16 compact event summaries | Excluded from automatic input because generic summaries are not a targeted, navigable recovery packet. |

Compact events retain identity plus selected operational fields such as
operation, method/path, result summary, retrieval counts, negative evidence,
and errors. Full event payloads are trace/UI-only. Existing `session message`,
`session turn`, and `session open` commands provide targeted navigation; a
future dedicated event-recovery packet requires its own design and tests.

### P-09 API Mind Capability Hints

| Property | Current behavior |
| --- | --- |
| Delivery | `on_demand` through `help` or `help <family>` |
| Source | shell metadata, command catalog, capability state. |
| Location | `message_context.api_mind`. |
| Function | Give authoritative current commands, syntax, examples, and availability when Scarlet needs them. |
| Excluded from | Automatic model context; the static tool schema already identifies `mind_shell`, while help is fresher and more precise than a repeated catalog. |

### P-10 Dynamic Organ Blocks

| Packet | Delivery | Current condition | Function | Automatic exclusion |
| --- | --- | --- | --- | --- |
| `focus_context` | `automatic_model_conditional` | `organ_focus_mode=model` plus active focus | Foreground attention and direct source navigation; not semantic memory. | Transitions, usage policy, registry metadata, and full focus history remain manual/trace. |
| `affective_context` | `automatic_model_conditional` | `organ_affect_mode=model` plus a model block | Tone/caution/warmth posture, never factual truth. | Numeric/debug appraisal internals, usage policy, and history remain manual/trace. |
| `metacognitive_context` | `automatic_model_conditional` | `metacognitive_context_mode=inject` plus at least one lesson | Few trigger-matched operating lessons. | Selection diagnostics, confidence, trigger conditions, near misses, and default shadow payload remain trace/UI-only. |
| `scarlet_state` | `trace_ui_only` | always built in rich runtime | Legacy seeded placeholders preserved for diagnostics. | Entire block is excluded because it duplicates current input, policy, focus, affect, and mode. |
| `agent_mode_context` | `automatic_model` in rich runtime; compacted into V2 session | every turn | Current/resumable tags plus whether each has implemented runtime. | Registry diagnostics stay trace/system-side; mode persistence never implies that autonomous execution started. |

`volition` has no automatic runtime block today; it is shell-only.

#### Exact V1.35.0 Preserved Projection

When all three optional families are enabled, the model receives this shape:

```json
{
  "preserved_context": [
    {
      "id": "scarlet.focus_context",
      "type": "focus_context",
      "scope": "profile",
      "lifetime": "dynamic",
      "source": "focus",
      "content": {
        "current_focus": {
          "id": "focus_...",
          "object": "...",
          "type": "topic",
          "status": "active",
          "intensity": 0.8,
          "duration_policy": "until_resolved",
          "reason": "...",
          "source_session_id": "ses_...",
          "source_turn_id": "turn_...",
          "source_message_id": "msg_...",
          "created_at": "2026-07-14T16:00:00+02:00",
          "updated_at": "2026-07-14T16:05:00+02:00"
        }
      }
    },
    {
      "id": "scarlet.affective_context",
      "type": "affective_context",
      "scope": "profile",
      "lifetime": "dynamic",
      "source": "affect",
      "content": {
        "state_id": "affect_...",
        "current_emotion": "curiosity",
        "intensity": "medium",
        "felt_quality": "...",
        "activation": "medium",
        "valence": "positive",
        "persistence": "turn",
        "attention_tendency": "inspect",
        "action_tendency": "ask carefully",
        "relational_posture": "warm",
        "causes": ["message: reasoning cue"]
      }
    },
    {
      "id": "turn.metacognitive_context",
      "type": "metacognitive_context",
      "scope": "turn",
      "lifetime": "turn",
      "source": "metacognition",
      "content": {
        "triggers": [{"id": "source_sensitive"}],
        "lessons": [
          {
            "id": "lesson_...",
            "title": "...",
            "lesson": "...",
            "recommended_action": "...",
            "risk_if_overused": "..."
          }
        ]
      }
    }
  ]
}
```

Envelope fields identify and classify the block. Focus fields define the live
attention object and make its source directly navigable; timestamps are
rendered in the user's timezone. Affect fields describe the appraised posture
that may shape the answer without exposing backend scoring internals.
Metacognitive trigger ids explain why a small lesson set was selected, while
the lesson fields provide the usable guidance and its overuse boundary.

The exact inclusion decision is persisted in `model.context.projection_audit`.
For each reviewed family it records source presence, disposition, whether it
reached the model, model field paths, excluded rich-source field paths,
cognitive function, reason, and on-demand commands. This audit is diagnostics,
not part of the model-facing V2 document.

### P-11 Top-Level Compatibility Mirrors

| Property | Current behavior |
| --- | --- |
| Delivery | `trace_ui_only` in V2; direct only in `legacy` profile |
| Source | Copies from canonical blocks for legacy prompt/tests. |
| Function | Compatibility only; not an independent evidence source. |

```txt
memory_context        = message_context.memory_retrieval
mind_shell            = message_context.api_mind.schema
temporal_context      = contained in message_context.world
recent_runtime_events = message_context.recent_runtime_events
capabilities          = message_context.api_mind.capabilities
```

These fields remain in the rich snapshot for diagnostics and legacy rollback.
They are not copied into the active V2 document.

## External GPT Bootstrap Packets

### P-12 Rendered Runtime Context

| Property | Current behavior |
| --- | --- |
| Delivery | `automatic_gpt_bootstrap` |
| Source | Rendered `scarlet-model-context-v2` when V2 is active. |
| Function | Give the external GPT backend perception, continuity, and capability context for the turn. |
| Excluded from | Full effective local prompt, raw runtime payload, raw retrieval diagnostics. |

### P-13 Protocol Metadata

| Property | Current behavior |
| --- | --- |
| Delivery | `automatic_gpt_bootstrap` |
| Contents | Session/turn ids, provider-history statistics and recent hints, action/finalize hints, tool identity, trace ids, compact metacognitive status, and omitted-diagnostics declaration. |
| Function | Let the GPT continue the bridge protocol without duplicating the canonical runtime document or raw backend diagnostics. |

### P-14 Legacy Compact Bridge Memory Context

| Property | Current behavior |
| --- | --- |
| Delivery | omitted when V2 is active; legacy bridge compatibility only |
| Contents | Search status, clock, compact query-plan metadata, selected/near-miss/excluded memories, conflicts, counts/budget, omitted-debug declaration. |
| Function | Make automatic-memory processing inspectable to the external GPT. |
| Excluded from | Raw turn frame and raw retrieval readiness/graph/shadow/hybrid diagnostics. |

V1.29.0 removed this legacy memory copy from active V2 bootstrap. V1.30.0 also
removed the duplicate structured model-context copy. The canonical memory area
is the `memories` object inside `context.runtime_context`.

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
| `context.accounting.preflight` / `observed` | Per-channel size, estimates, first-step usage, tool-loop totals, shadow compaction plan | Measurement and planning, never extra model evidence. |
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
| mode | `read`, `list`, `set` | Active mode, resumable preference, and registry. |
| metacognition | `metacognition step` | Risks, evidence gaps, recommended available actions, public summary. |
| help | `help`, `help <family>` | Current shell catalog and syntax. |

Manual result size is a separate budget concern: `session open` currently has no transcript limit when Scarlet omits `--limit`, despite supporting a limit.

## Verified Current Boundaries

- Canonical dynamic model structure: `scarlet-model-context-v2`.
- Raw retrieval plans, KG diagnostics, embeddings, maintenance data and full event payloads are not automatically passed to Scarlet.
- Compatibility mirrors remain only in the rich internal/legacy snapshot.
- Two previous sessions and five user-scope memories are selected by recency, not current-message relevance.
- Previous-session summaries are navigation aids, not exact historical proof.
- Current world perception is configured time/locale only, not live sensors or external-world feeds.
- Focus, affect and metacognitive lessons are conditional; volition is manual-only.
- Agent mode is automatic; human turns resolve to `interactive`, while a
  manual `idle`/`scouting` selection is retained as the resumable posture.
- Automatic context routing is mode-aware; on-demand shell commands remain
  available regardless of automatic block eligibility.

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
These notes preserve the wording and implementation gap visible during the
2026-07-11 review. V1.29.0 subsequently implemented the accepted packet
contract; the status annotations below distinguish that later result from the
historical discussion.

### 2026-07-11: Episodic And Short-Term Continuity Direction

The owner reviewed the then-current `session_context` and rejected its broad,
recency-only shape as the target context-pack design. At review time this was a
future contract; it is implemented by `scarlet-model-context-v2` in V1.29.0.

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

Short-term memory continuity must be independent from the previous session. The
implemented separate recent-memory hint packet contains the five most recently
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

The implementation at the time of this note differed: it surfaced memories
only from the most recent previous session in `session_context`, separately
surfaced five newest user-scope memories in `message_context`, and updated
`last_used_at` for automatic selected retrieval. V1.29.0 replaced that
model-facing shape and introduced append-only cognitive activity ordering.

These questions were open at this stage of the review. The 2026-07-12 note
below closes immediate recency behavior. Future multi-user visibility is a
deterministic authenticated-user storage/query boundary, not a model-facing
packet policy.

### 2026-07-11: Session-Attached User Time And Location Direction

The owner decided that model-facing world/time data belongs with session
continuity rather than a separate turn-perception packet. At review time this
was a future contract; V1.29.0 implements it in the shared V2 projection.

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

Packet policies should be omitted by default. A compact reinforcing hint
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
  model-facing dynamic context packs:

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
duplicate `current_message` representation from Scarlet/GPT dynamic
context packet selection.

### 2026-07-11: User Data And User-Memory Continuity Direction

The owner decided that non-memory user data should be merged into the
session-attached context. Scarlet receives only the user's display name:

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

At review time, `user_profile.memories` returned up to five newest active
user-scope records by creation time and was embedded with profile metadata.
V1.29.0 replaced that model-facing shape with the compact `recent_user` block.

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

Required shell navigation surface, implemented in V1.29.0:

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
- `backend/app/mind/context_retrieval.py`
- `backend/app/mind/memory_read.py`
- `backend/app/mind/memory_shared.py`
- `backend/app/api/chat.py`
- `backend/app/mind/shell.py`
- `backend/app/mind/shell_presentation.py`
- `backend/app/mind/episodic.py`
- `backend/app/plugins/gpt_bridge/router.py`
- `backend/app/runtime/events.py`
- `docs/block-registry.md`
- `docs/runtime-context-packs.md`
