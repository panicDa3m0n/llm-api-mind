# Runtime And UI Block Registry

Last updated: 2026-07-28
System version assessed: V1.65.0 target pending protected deployment over the
V1.50.1 Core
Status: active diagnostic map

This registry distinguishes the exact document delivered to Scarlet from the
richer evidence used by backend, traces, maintenance, and UI.

## 1. Technical Turn Inputs

These are required delivery surfaces, not dynamic context packs:

| Surface | Native MiniMax | External GPT | Authority |
|---|---|---|---|
| Static system policy | repository Scarlet prompt | prompt pasted in GPT Builder | identity and operating policy |
| Active-session history | canonical provider history, or a validated compacted chronology plus exact tail | ChatGPT history plus compact bridge provider hints | same-session continuity; canonical native history remains authoritative |
| Cognitive tool schema | one `mind_shell` tool | three GPT Actions | callable transport |

They have dedicated lifecycle and are not selected by the future dynamic
context router.

V1.65 changes no block payload or audience. It makes the native human and
autonomous adapters emit their common context/accounting/response/turn receipts
through one kernel; autonomous records remain private and are not reclassified
as human-chat blocks.

## 2. Active Dynamic Model Document

Schema:

```txt
scarlet-model-context-v2
```

Native MiniMax receives its JSON inside `<runtime_context>`. GPT bootstrap
returns that canonical rendered runtime string once; it no longer duplicates
the same document under `context.model_context`. Every document is persisted
in a `model.context` trace.

### 2.1 Session Area

```json
{
  "turn_origin": {
    "origin": "human_interaction",
    "session_id": "ses_...",
    "session_kind": "human_dialogue",
    "turn_id": "turn_...",
    "turn_trigger": "human_message",
    "turn_actor": "user",
    "message_id": "msg_...",
    "message_role": "user"
  },
  "current_session": {
    "id": "ses_...",
    "title": "...",
    "created_at": "..."
  },
  "user": {"name": "..."},
  "agent_mode": {
    "active_tag": "interactive",
    "active_runtime_implemented": true,
    "source": "system_condition",
    "resume_tag": "scouting",
    "resume_runtime_implemented": false
  },
  "now": "...",
  "timezone": {
    "id": "Europe/Rome",
    "name": "CEST",
    "utc_offset": "+02:00",
    "social_day_boundary": "05:00"
  },
  "location": "Italia",
  "previous_sessions": [
    {
      "id": "ses_...",
      "last_message_at": "...",
      "turn_count": 12,
      "summary": "..."
    }
  ],
  "autonomous_session": {
    "id": "ses_...",
    "kind": "scarlet_autonomous",
    "last_activity_at": "...",
    "turn_count": 8,
    "latest_checkpoint": "..."
  }
}
```

Model-facing fields are intentionally minimal. Profile id, privacy scope,
storage timestamps, raw session metadata, summary diagnostics, and maintenance
timestamps remain systemic. Human and autonomous turns receive this same V2
shape. Provider histories remain separate; `turn_origin` classifies the
current lifecycle and the autonomous-session hint makes internal chronology
navigable from human dialogue.

For a workspace-triggered autonomous turn only, the activation envelope may
also include a compact `workspace` object. It contains selected provisional
candidate hooks, exact source refs, and linked episode/wake ids. It does not
replace any V2 block. Full receipts, alternate candidates, appraiser output,
and arbitration diagnostics remain trace/UI-only.

### 2.2 Memory Area

```json
{
  "relevant": [],
  "recent_user": [],
  "recent_general": []
}
```

Each hook contains exactly:

```json
{
  "id": "mem_...",
  "content": "...",
  "created_at": "...",
  "updated_at": "...",
  "source_session_id": "ses_...",
  "source_session_kind": "human_dialogue",
  "source_turn_id": "turn_...",
  "source_turn_trigger": "human_message",
  "source_turn_actor": "user",
  "source_message_id": "msg_...",
  "source_message_role": "user",
  "source_provenance_status": "complete",
  "source_origin": "human_interaction"
}
```

The lists are deduplicated in priority order. Facts, scores, KG paths,
classifications, lifecycle diagnostics, reason/future-use fields, near misses,
and excluded candidates are not opened automatically. Source ids and compact
origin labels are model-facing because they distinguish human dialogue from
autonomous cognition and support exact navigation.

### 2.3 Preserved Context

`preserved_context` is an explicit allowlist for optional dynamic organs:

| Type | Source condition | Current model use |
|---|---|---|
| `focus_context` | focus mode `model` and active focus | compact current focus plus source navigation |
| `affective_context` | affect mode `model` and non-neutral appraisal | compact response posture without debug scoring |
| `metacognitive_context` | metacognitive mode `inject` and selected lessons | trigger ids plus compact operating lessons |

The default config disables focus and affect model injection and keeps
metacognitive lessons in shadow mode, so `preserved_context` is normally empty.
`scarlet_state`, duplicated recent dialogue, generic runtime events, and API
Mind capability catalogs remain in rich traces or on-demand surfaces and are
never projected automatically.

Every `model.context` trace includes `projection_audit`, with one decision per
reviewed family. The audit records source presence, final disposition,
included/excluded field paths, cognitive function, reason, and relevant shell
commands. It is visible to diagnostics and evaluation but is not embedded in
the model document.

V1.59.0 also records `projection_audit.context_family_routing`. This semantic
shadow receipt classifies the already delivered V2 areas by subject, observer,
evidence kind, mode eligibility, activation contract, and policy dependencies.
It does not route or add future sensor/device families and explicitly reports
that current model context is unchanged.

Volition is never injected automatically.

Before V2 projection, the agent-mode router emits one ordered decision per rich
context block. Each decision records block id/type, capability and status,
required mode tags, eligibility, actual delivery, disposition, and reason.
`off` delivers all blocks, `shadow` delivers all and records
`would_exclude`, and `active` excludes registered ineligible blocks.
Unregistered blocks fail open and are explicitly reported for registry review.
These receipts remain trace/UI evidence; they are not duplicated into Scarlet's
model document.

## 3. Rich Internal Evidence

The backend still builds `runtime-context-v1` and a rich `memory.context`
snapshot before projecting V2. This is intentional: V2 is a model projection,
not a reduction in system observability.

Rich evidence includes:

- turn frame and query plan;
- selected, near-miss, excluded, conflict, and negative-evidence data;
- sparse, graph, shadow, hybrid, vector, and reranker diagnostics;
- full event summaries and capability map;
- legacy blocks and compatibility mirrors;
- affect/focus/metacognitive construction diagnostics.

Destinations:

| Trace/block | Model-facing | UI/debug | Maintenance/eval |
|---|---:|---:|---:|
| `model.context` | exact delivered V2 | yes | yes |
| `context.accounting.preflight` | no; request measurement | yes | yes |
| `context.accounting.observed` | no; provider measurement | yes | yes |
| `memory.context` | only through compact V2 projection | yes | yes |
| `runtime.context` | only preserved V2 projection | yes | yes |
| `llm.request` | request itself | yes | yes |
| historical `answer.obligations` | no; retired in V1.64 | yes | audit only |
| historical `answer.validation` | no; retired in V1.64 | yes | audit only |
| raw KG/vector/rerank payloads | no | yes | yes |
| maintenance jobs | no | evaluator UI/API | yes |
| memory proposals | only when Scarlet calls proposal shell commands | evaluator UI/API | yes |

`memory.proposals.review_ready` is a private completed event admitted to the
Cognitive Workspace as an appraisal candidate. It exposes proposal
availability and source hooks; it does not force a wake or place proposal
content in ordinary model context.

`cognition.signal.dispositioned` is an observable workspace receipt, not a
signal source. It is deliberately excluded from event ingestion so receipt
telemetry cannot recursively manufacture more receipts.

## 4. Stream And Historical UI Blocks

`scarlet-stream-v2` is the durable Product UI event contract. Every V2 item
projects one persisted `CognitiveEvent` with a durable event id and
session-global sequence. `scarlet-live-v1` wraps those same events and may
interleave connection-local provider text, thinking, and tool-input frames for
smooth composition. Frames are never persisted or replayed; interruption
falls back to V2 from the last durable cursor.

The developer cockpit displays:

- initial context and automatic memory activity;
- provider thinking;
- public note/text;
- shell call and result;
- runtime event;
- final answer;
- exact model input inspector.

The mobile view converts the same flow into consumer-readable blocks and hides
raw diagnostics behind the developer surface.

Product Chat currently projects:

- an immediate UI-owned orientation placeholder after message submission,
  replaced as soon as canonical context evidence arrives;
- `memory.context.built`, `memory.recent_context.built`,
  `session.continuity.built`, and `runtime.context.built` as distinct compact
  context blocks;
- thinking and text frames into stable model-step/content-index blocks;
- `mind.tool_use.started` through `mind.tool_call.completed` into one
  in-place tool block, using the model-authored `mind_shell.intent` when
  available;
- `answer.validation.started` as a waiting block during the blocking semantic
  check; and
- accepted answer, persisted message, failure, and terminal events from V2.

The orientation placeholder describes only the verified transport state. It is
not model speech, hidden cognition, or durable evidence.

Live lifecycle:

```txt
created -> streaming -> captured/executing -> completed -> persisted
```

Failed blocks remain inspectable. V2 replay reconstructs messages, public
notes, tool lifecycle, final answers, and errors from canonical events. Full
provider details remain available through traces for the developer lens; a
Product UI does not infer semantics from provider-native blocks.

## 5. Manual Shell Results

Manual results are new evidence returned after a command; they are not
automatic context packets.

| Family | Compact model result | Full diagnostics |
|---|---|---|
| memory | memory/fact/provenance/graph or lifecycle result | traces/retrieval internals |
| session | index, exact message/turn, transcript or summary | traces/storage |
| focus | current/history/lifecycle | organ trace/events |
| volition | intentions/links/lifecycle | organ trace/events |
| affect | state/history/prototypes | appraisal trace/events |
| mode | active/resumable posture and registry | mode trace/events/settings |
| metacognition | structured review and valid recommendations | metacognition trace |
| help | command catalog and syntax | command registry/schema |

## 6. Current Risks

1. Native provider history now has guarded active compaction. Recursive
   artifacts are append-only, model routing uses `compacted chronology + exact
   tail + current`, and any invalid artifact falls back to canonical history.
2. GPT total model input remains partly unobservable because ChatGPT owns its
   manual prompt, native history, Actions serialization, and token accounting.
3. Future organ registry entries can look implemented unless code/tests/default
   activation are checked separately.
4. Frontend renderers still contain compatibility support for old runtime
   blocks and must not be used as proof that those blocks reach the model.
5. Semantic answer judgment is stochastic evidence. Active mode fails closed,
   but validator latency and false positives require monitoring.

## 7. Next Registry Work

- keep new optional organ families behind explicit field allowlists and audit;
- monitor recursive summary quality and validate the V1.36 token partition
  across additional compaction cycles;
- monitor the accepted V1.42 mode-routing and continuity scenarios when mode
  semantics or block tags change;
- monitor answer-obligation validator quality and GPT correction behavior;
- update this registry before changing active compaction budgets or hard-gating
  any cognitive command by mode.
