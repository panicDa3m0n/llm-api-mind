# Runtime And UI Block Registry

Last updated: 2026-07-11
System version assessed: V1.29.0
Status: active diagnostic map

This document maps the blocks used by Scarlet's runtime, model request, stream,
trace store, and frontend UI. It exists so future optimization work can decide
what should be model-facing, what should remain only visible to human
evaluators, and what is currently redundant.

For the field-level review of every automatic local/GPT packet, manual shell
boundary, and trace/UI-only payload, use `docs/context-packet-inventory.md`.
This registry remains the compact map of block lifecycle and UI rendering.

## 1. Model-Facing Request Order

Every Scarlet turn is ultimately sent to MiniMax through the Anthropic-compatible
Messages API from `backend/app/llm/minimax_client.py`.

The effective request is:

```txt
tools
system = Scarlet prompt + <runtime_context>{...}</runtime_context>
messages = provider-native conversation history + current user message
max_tokens / stream / model / thinking config
```

The full model request is persisted as a `llm.request` trace in
`backend/app/api/chat.py`.

Before the model request, V1.9.0 may also create a `metacognitive.context`
trace. In default `shadow` mode this trace is not part of the model request. In
controlled `inject` mode it becomes a `metacognitive_context` block inside
`runtime_context.blocks`.

### 1.1 Tool Schema

Model-facing: yes.
Source: `backend/app/mind/schema.py`.
UI: sidebar tab `Modello`, section `Schema tool disponibili`.

Scarlet receives one tool:

```txt
mind_shell(command, intent)
```

Purpose:

- keep Scarlet's external cognitive surface small;
- let the backend own route and handler complexity;
- allow schema changes without exposing many direct model tools.

Assessment:

- Correct and central.
- Not redundant.

Example:

```json
{
  "name": "mind_shell",
  "input_schema": {
    "required": ["command"]
  }
}
```

### 1.2 System Prompt

Model-facing: yes.
Source: `backend/app/prompts/scarlet_system.md`.
Trace field: `llm.request.payload.base_system`.
UI: sidebar tab `Modello`, section `System prompt + runtime context`.

Purpose:

- define Scarlet's identity, source hierarchy, API Mind autonomy, memory policy,
  public notes, and response style;
- explain how to read runtime blocks and provider-visible continuity.

Assessment:

- Correct and necessary.
- Potential risk is prompt growth, not structural redundancy.

### 1.3 Runtime Context Envelope

Model-facing: yes, appended to the system prompt.
Source: `backend/app/mind/context.py`.
Trace fields:

```txt
llm.request.payload.runtime_context
llm.request.payload.runtime_context_present
llm.request.payload.runtime_context_trace_id
```

UI:

- center chat: `Contesto iniziale di Scarlet`;
- sidebar tab `Modello`: parsed model-facing runtime context;
- sidebar tab `Eventi`: `runtime.context.built`.

Purpose:

- give Scarlet reliable external-world and session data before she answers;
- separate evidence from user instructions;
- provide session, message, user, memory, runtime event, API Mind, and dynamic
  state surfaces.

Current canonical payload:

```txt
runtime_context.blocks
```

Default block list in shadow mode:

```txt
session_context
message_context
scarlet_state
```

Controlled A/B block list in inject mode:

```txt
session_context
message_context
scarlet_state
metacognitive_context
```

Current compatibility mirrors:

```txt
memory_context
mind_shell
temporal_context
recent_runtime_events
capabilities
```

Assessment:

- `runtime_context.blocks` is correct and should remain canonical.
- V1.11.2 adds `rendering_profile=compact-model-facing-v1` so traces can
  distinguish compact model-facing memory packets from full debug traces.
- V1.26.0 planning adds context packs as a future routing layer above the
  existing blocks. Packs are not implemented blocks yet; they will classify
  which block bundle should be present for a turn.
- Top-level compatibility mirrors are useful for the current prompt and tests,
  but are redundant with block content. They are the primary future payload
  optimization candidate.
- Do not remove them until prompt behavior and tests prove Scarlet reads only
  canonical blocks reliably.

### 1.3.1 Planned Context Pack Metadata

Model-facing: not implemented yet.
Source: planned router, see `docs/runtime-context-packs.md`.
Trace target: future `runtime.context` metadata.

Purpose:

- record which context pack the backend selected or would have selected;
- keep an always-on spine separate from mode-specific context;
- make context budget/degradation visible before changing live model input;
- prepare future embodied modes without injecting raw sensory streams.

Initial planned shape:

```json
{
  "context_pack": {
    "pack_id": "source_sensitive",
    "spine_version": "runtime-spine-v1",
    "included_blocks": ["message_context", "memory_context"],
    "omitted_blocks": ["raw_retrieval_shadow"],
    "mode_reason": "User asked about prior evidence reliability.",
    "shadow": true
  }
}
```

Assessment:

- Planned only.
- First slice should be trace-only shadow metadata.
- It must not replace canonical `runtime_context.blocks`.

### 1.4 Provider-Native Messages

Model-facing: yes.
Source: `_provider_messages_for_turn()` in `backend/app/api/chat.py`.
Trace field: `llm.request.payload.provider_messages`.
UI: sidebar tab `Modello`, section `Cronologia provider-native`.

Purpose:

- preserve same-session continuity in Anthropic-compatible form;
- keep assistant `thinking`, `text`, `tool_use`, and `tool_result` blocks
  visible to the next turn when the provider exposes them;
- avoid flattening tool history into plain text.

Assessment:

- Correct and essential.
- Not the same as episodic session recall. This is active-session continuity.

Example:

```json
[
  {"role": "user", "content": [{"type": "text", "text": "Cosa stavamo facendo?"}]},
  {"role": "assistant", "content": [{"type": "thinking", "thinking": "..."}]},
  {"role": "assistant", "content": [{"type": "tool_use", "name": "mind_shell"}]},
  {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "..."}]}
]
```

## 2. Canonical Runtime Blocks

These blocks live inside `runtime_context.blocks`. They are model-facing and
also shown to human evaluators.

### 2.1 `session_context`

Event timing: built before each model request.
Scope: session.
Lifetime: stable continuity context for the chat session.

Contains:

- current session id, title, timestamps, summary hints;
- previous session summaries;
- memories from the previous session when available.

Example for humans:

```txt
Current session: "Chat 06/16 14:30"
Previous sessions: "Yesterday we discussed MiniMax M3 behavior."
Previous session memories: "User prefers Italian defaults."
```

Function:

- help Scarlet orient herself at session start;
- give lightweight episodic continuity without loading full transcripts.

Assessment:

- Correct.
- Not redundant with provider history because it can include previous sessions,
  not only the current active conversation.

### 2.2 `message_context`

Event timing: built before each model request.
Scope: turn.
Lifetime: current-message perception.

Contains:

- current user message metadata;
- world/temporal context from runtime settings;
- active user profile;
- automatic semantic-memory retrieval;
- recent dialogue summary;
- recent runtime events;
- API Mind capability hints.

Example for humans:

```txt
Now: Europe/Rome platform time.
User: local-user, Italian platform language.
Automatic memories: 2 selected, 14 near misses.
Recent dialogue: last user/assistant exchanges.
API Mind: schema available, memory search available.
```

Function:

- give Scarlet the best available turn-level perception;
- make automatic memory retrieval visible and auditable.

Assessment:

- Correct.
- Some subfields overlap with top-level compatibility mirrors. Keep the block;
  trim mirrors later if tests allow it.

#### Selected Memory Packets

From V1.11.2, selected memories in model-facing runtime context use
`memory-packet-v1`.

Location:

```txt
runtime_context.memory_context.selected
runtime_context.blocks[].content.memory_retrieval.selected
```

Contains:

- `claim`: compact remembered claim;
- provenance/source ids;
- confidence and salience;
- compact facts;
- cognitive subject;
- cognitive domains;
- validity status/range hints;
- sensitivity class;
- retrieval routes and compact turn-level reason.

Does not contain:

- raw `signals`;
- full embedding/rerank/shadow payloads;
- hybrid weights and thresholds;
- arbitrary metadata;
- long diagnostic paths.

Function:

- give Scarlet enough memory evidence to answer, personalize, and decide when
  to open a source session;
- keep detailed diagnostics available in `memory.context` traces without
  flooding the model-facing packet.

Assessment:

- Correct direction for MiniMax M3's larger context: use the context window for
  relevant structured evidence, not repeated debug machinery.
- Compatibility mirrors still duplicate the compact packet for now; remove only
  after prompt/runtime tests prove Scarlet reads canonical blocks reliably.

### 2.3 `scarlet_state`

Event timing: built before each model request.
Scope: dynamic.
Lifetime: backend-seeded dynamic state until state APIs exist.

Contains:

- current focus hints;
- mood/affective placeholder data;
- state placeholders for future self-management APIs.

Function:

- reserve a structured place for future dynamic Scarlet state without forcing
  every new cognitive variable into the prompt.

Assessment:

- Correct as an architectural placeholder.
- Low-information today, but useful as a stable extension point.

### 2.4 `metacognitive_context`

Event timing: built before each model request only when
`metacognitive_context_mode=inject`.
Scope: turn.
Lifetime: current-message cognitive regulation.

Contains:

- selection policy;
- trigger ids and confidence;
- up to a small configured number of candidate metacognitive lessons;
- recommended action, anti-conditions, cost impact, and overuse risk.

Function:

- support controlled A/B tests where Scarlet receives surgical lessons about
  her own operating behavior;
- measure whether these lessons reduce overthinking, missed memory
  commitments, and unsupported source-sensitive claims.

Assessment:

- Not model-facing by default.
- Experimental and should remain small. If it becomes a broad advice block, it
  risks worsening M3 behavior.

## 2.5 Shadow-Only Metacognitive Context

Trace: `metacognitive.context`.
Event: `metacognitive.context.shadowed`.
Stream event: `metacognitive_context`.
UI: center chat block and right-side event/model diagnostics.

Default mode:

```txt
metacognitive_context_mode=shadow
```

Purpose:

- show evaluators which metacognitive lessons would have been selected;
- collect evidence without changing Scarlet's prompt or model-facing context;
- prepare controlled `inject` comparisons.

Assessment:

- Correct first step for the metacognition branch.
- This is not a claim that Scarlet has active learned metacognition.

## 2.6 Digital-Individual Organ Block Substrate

Status: implemented as backend registry only, not model-facing by default.

Registry:

```txt
backend/app/mind/organs.py
```

Registry version:

```txt
2026-06-25.digital-organs-substrate-v1
```

Canonical organ block types:

| Organ | Block type | Default visibility | First policy |
| --- | --- | --- | --- |
| Attention/focus | `focus_context` | `model` | Separate from memory retrieval; must not narrow retrieval by default. V1.21.0 adds `/mind/focus action=timeline` for transition inspection. |
| Volition/intentions | `volition_context` | `manual` | No automatic active-chat retrieval. V1.21.0 adds `/mind/volition action=list_due` for future autonomous-cycle queues. |
| Affective integration | `affective_context` | `shadow` | Backend-appraised emotional state; shadow by default, model-facing only behind `organ_affect_mode=model`, read-only via `/mind/affect`, and never a backend retrieval/focus/intention controller. |
| Temporal experience | `temporal_experience` | `model` | Derived continuity signals; runtime clock remains factual source. |
| Sleep/dream | `continuity_delta` | `model` | Trace-backed changes from exploratory consolidation. |

Supported visibility modes:

```txt
off, shadow, model, manual, autonomous_only
```

Function:

- reserve stable names for the five digital-individual organs;
- prevent future organ work from overloading `scarlet_state`;
- keep future blocks separate from memory, session, and metacognitive context;
- make organ state traceable before it becomes behaviorally active.

Current behavior:

- `focus_context` can be injected when `organ_focus_mode=model` and an active
  focus exists; focus timeline inspection is available through API Mind but is
  not injected automatically;
- `volition_context` is reserved and remains manual: V1.19.0 implements
  `/mind/volition` and V1.21.0 adds due-intention listing, but intentions are
  not injected into normal active chat;
- `affective_context` can be appraised in shadow or injected in model mode when
  a real affect signal crosses threshold; `/mind/affect` exposes read-only
  state/prototype inspection;
- temporal and dream organ blocks are not injected by this substrate alone;
- feature flags default to `off`;
- `scarlet_state` remains a legacy placeholder for concerns that do not yet
  have a dedicated organ block. When `focus_context` is present, it supersedes
  `scarlet_state.focus`; when `affective_context` is present, it supersedes
  `scarlet_state.mood_expression`.

Assessment:

- Correct as a foundation and first three-organ standalone closure.
- Expose organ routes through `/mind/schema` only when the organ has an
  implemented route or model-facing behavior. `POST /mind/volition` is now
  exposed as a manual lifecycle route, not as an automatic runtime block.

## 3. Non-Canonical But Model-Facing Mirrors

The following fields are inside the model-facing runtime context today, but are
duplicates or condensed mirrors of canonical data:

| Field | Why it exists | Current assessment |
|---|---|---|
| `memory_context` | Backward-compatible direct memory surface | Useful but redundant with `message_context.memory_retrieval` |
| `mind_shell` | Fast shell digest/capability signal | Useful, but can move into canonical API Mind block later |
| `temporal_context` | Direct real-time source | Useful, but duplicated by `message_context.world` |
| `recent_runtime_events` | Compact operational hint surface | Useful, but also present under message context |
| `capabilities` | Shell command availability summary | Useful, but overlaps API Mind context; endpoint-only maintenance routes must be marked internal rather than model-facing |

Policy:

- keep them for now;
- mark them as payload optimization targets;
- remove only after direct Scarlet tests prove no regression.

## 4. Stream And Output Blocks

These are produced by MiniMax/backend during the turn and rendered in the center
chat flow.

### 4.1 Thinking

Model-facing on later turns: yes, when MiniMax exposes it in provider-native
assistant history.
UI: center chat accordion, sidebar actions/events/model messages.
Lifecycle:

```txt
thinking_start -> thinking_delta* -> thinking_captured -> persisted replay
```

Function:

- inspect provider-visible reasoning content;
- let evaluators understand why Scarlet made tool calls or claims.

Note:

- MiniMax does not guarantee a thinking block for every turn.
- The UI must preserve generated thinking, not synthesize missing thinking.

### 4.2 Public Note

Model-facing on later turns: yes, as provider assistant text if persisted in
provider-native history.
UI: center chat full visible block.
Lifecycle:

```txt
text_start -> text_delta* -> assistant_note -> persisted replay
```

Function:

- natural agentic progress communication to the user;
- useful episodic trace of what Scarlet said she was doing.

### 4.3 Tool Exchange

Model-facing on later turns: yes, as `tool_use`/`tool_result` blocks in
provider-native history.
UI:

- center chat accordion with readable route/status;
- details include full input and output;
- sidebar actions tab lists the same operations.
Lifecycle:

```txt
tool_use_start -> tool_input_delta* -> tool_call -> tool_result -> persisted replay
```

Function:

- expose API Mind calls clearly;
- keep user-facing flow understandable while retaining raw debug data.

V1.6.0 UI fix:

- replayed tool cards now enrich completed events from matching
  `mind.tool_call` traces so full output is available after session reload.

### 4.4 Final Answer

Model-facing on later turns: yes, as provider assistant text.
UI: center chat full visible block.
Lifecycle:

```txt
text_start -> text_delta* -> assistant_answer -> persisted replay
```

Function:

- final user-facing response after any notes/tools/thinking.

## 5. Trace-Only And UI-Only Surfaces

Not every visible or persisted block is re-injected directly into the model.

Trace-only or evaluator-only examples:

- `llm.request` trace;
- full raw `llm.response`;
- maintenance job events;
- proposal-resolution traces;
- frontend inspector groupings;
- dashboard memory cards outside the selected turn.

These are for observability, debugging, and future maintenance processes. They
should not be added to model input unless a specific behavior improvement is
defined and tested.

## 6. Frontend Display Map

Center chat:

```txt
User message
Memory context block
Runtime context block
Thinking accordion
Public note block
Tool exchange accordion
Final answer block
```

Right sidebar:

```txt
Memorie  -> memory-context and memory-tool history
Azioni   -> tool exchanges
Modello  -> exact llm.request input inspector
Eventi   -> runtime/system/maintenance events
Avvisi   -> failed/error steps
Settings/Profile -> global runtime controls
```

The `Modello` tab is the canonical human-readable place to inspect what Scarlet
actually received from the backend in that turn.

## 6.1 Stream Block Lifecycle

From V1.7.0, the frontend treats stream output as blocks with stable lifecycle
rather than disposable events.

Current block identity rules:

| Block | Stable identity |
|---|---|
| Thinking | `thinking-{model_step}-{content_block_index}` |
| Public text | `content-{model_step}-{content_block_index}` |
| Tool exchange | `tool-{provider_tool_use_id}` |
| Memory context | `memory-context-{trace_id}` |
| Runtime context | `runtime-context-{trace_id}` |
| Exact model context | `model-context-{trace_id}` |

Current lifecycle phases:

```txt
created
streaming
captured
executing
completed
persisted
failed
```

Frontend policy:

- live blocks are visible as soon as their provider/backend start event arrives;
- `text_delta` is rendered as a provisional public-text block instead of hidden
  runtime data;
- the same public-text block becomes either `assistant_note` or
  `assistant_answer` when MiniMax's final provider message reveals whether the
  message ended in tool use or final answer;
- tool input JSON is visible while it streams, then replaced by structured
  input when `tool_call` provides the complete arguments;
- `turn_complete` reconciles live blocks with persisted events/traces instead
  of blindly replacing the visible flow.

Purpose:

- make the cockpit feel like mature coding agents: operations appear as soon as
  they begin, mature while work happens, and remain in chronological order after
  persistence;
- avoid losing user-visible evidence between live stream and historical replay;
- keep all lifecycle behavior in the UI until backend block-level events are
  proven necessary.

## 7. Current Optimization Candidates

High-confidence candidates:

- the V2 session/memory spine has removed reviewed compatibility mirrors from
  active model input;
- large `tool_result` provider messages can dominate provider history in long
  sessions;
- preserved recent runtime events/capability/Scarlet-state blocks still need
  field-level owner review.

Deferred decisions:

- no provider-native history change in V1.29.0;
- no automatic removal of preserved context families before owner review;
- no context-pack router until V2 evidence supplies measured budgets.

Reason:

This slice builds the microscope first. Once the UI makes the real request
legible, we can remove or compress blocks based on evidence rather than
guesswork.
