# Runtime And UI Block Registry

Last updated: 2026-07-13
System version assessed: V1.30.0
Status: active diagnostic map

This registry distinguishes the exact document delivered to Scarlet from the
richer evidence used by backend, traces, maintenance, and UI.

## 1. Technical Turn Inputs

These are required delivery surfaces, not dynamic context packs:

| Surface | Native MiniMax | External GPT | Authority |
|---|---|---|---|
| Static system policy | repository Scarlet prompt | prompt pasted in GPT Builder | identity and operating policy |
| Active-session history | provider-native session history | ChatGPT history plus compact bridge provider hints | same-session continuity |
| Cognitive tool schema | one `mind_shell` tool | three GPT Actions | callable transport |

They have dedicated lifecycle and are not selected by the future dynamic
context router.

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
    "utc_offset": "+02:00"
  },
  "location": "Italia",
  "previous_sessions": [
    {
      "id": "ses_...",
      "last_message_at": "...",
      "turn_count": 12,
      "summary": "..."
    }
  ]
}
```

Model-facing fields are intentionally minimal. Profile id, privacy scope,
storage timestamps, raw session metadata, summary diagnostics, and maintenance
timestamps remain systemic.

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
  "source_message_id": "msg_..."
}
```

The lists are deduplicated in priority order. Facts, scores, KG paths,
classifications, lifecycle diagnostics, reason/future-use fields, near misses,
excluded candidates, and raw provenance are not opened automatically.

### 2.3 Preserved Context

`preserved_context` is a compatibility area for dynamic families not yet
accepted or rejected individually:

| Type | Source condition | Current model use |
|---|---|---|
| `focus_context` | focus mode `model` and active focus | optional foreground state |
| `affective_context` | affect mode `model` and non-neutral appraisal | optional model posture |
| `metacognitive_context` | metacognitive mode `inject` | controlled A/B lessons |
| `scarlet_state` | legacy runtime builder | transitional state/policy |
| `undiscussed_context` | legacy message block | recent dialogue, events, capability hints |

The default config disables focus and affect model injection and keeps
metacognitive lessons in shadow mode. Scarlet state and undiscussed context
remain the principal V2 review targets.

Volition is never injected automatically.

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
| raw KG/vector/rerank payloads | no | yes | yes |
| maintenance jobs/proposals | no | evaluator UI/API | yes |

## 4. Stream And Historical UI Blocks

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

Live lifecycle:

```txt
created -> streaming -> captured/executing -> completed -> persisted
```

Failed blocks remain inspectable. Historical replay reconstructs provider and
tool blocks from persisted messages, traces, and events.

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

1. Provider-native history is now measured and shadow-planned but still has no
   active compaction/degradation policy.
2. `undiscussed_context` can reintroduce data that V2 removed from the
   reviewed session/memory spine.
3. GPT total model input remains partly unobservable because ChatGPT owns its
   manual prompt, native history, Actions serialization, and token accounting.
4. Future organ registry entries can look implemented unless code/tests/default
   activation are checked separately.
5. Frontend renderers still contain compatibility support for old runtime
   blocks and must not be used as proof that those blocks reach the model.

## 7. Next Registry Work

- decide every preserved family with the owner;
- accumulate long-session provider observations and validate the 100k plus
  desired eight-turn compaction shape;
- populate natural behavioral scenarios for mode routing and continuity;
- update this registry before promoting active compaction or hard-gating any
  cognitive command by mode.
