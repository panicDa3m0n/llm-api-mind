# Scarlet Stream V2 Contract

Last updated: 2026-07-24
Schema: `scarlet-stream-v2`
Contract introduced: V1.51.0; current app target: V1.56.0
Linear issue: SCA-47

## 1. Purpose

Scarlet Stream V2 is the stable Product UI event port for web and future
Android clients. It lets a client render a live turn, reconnect, replay missed
events, and reconstruct the same persisted state without understanding MiniMax,
Qwen, Anthropic, or any other provider-native block format.

The contract is additive. The V1 NDJSON endpoint remains available during
migration, but new clients should use V2.

## 2. Source Of Truth

Every V2 line is a projection of one persisted `CognitiveEvent`. Provider
deltas such as token text, partial thinking, and partial tool JSON are useful
for diagnostics but are transient and are not V2 events. Completed public
notes, completed answers, tool lifecycle, messages, errors, and turn terminal
state are persisted before they enter V2.

Native traces remain complete and separately inspectable. V2 carries event
evidence needed by a Product UI and developer lens; it does not copy full
provider requests, responses, or trace payloads into the client stream.
Projection uses an event-family allowlist. In particular, full tool results
and full runtime-context blocks remain behind their linked tool/trace APIs;
V2 carries compact operation, result-summary, count, lifecycle, and link data.
During development, `llm.thinking.captured` is an explicit diagnostic
exception: V2 preserves its completed provider text together with model
step/index, phase, sequence, and trace links. Clients may hide it locally, but
must not relabel it as a public note or Scarlet-authored answer. Transient
thinking deltas remain trace-only.

## 3. Event Envelope

Every NDJSON line and replay item has exactly this top-level shape:

```json
{
  "schema_version": "scarlet-stream-v2",
  "event_id": "evt_...",
  "seq": 42,
  "session_id": "ses_...",
  "turn_id": "turn_...",
  "event_type": "assistant.note.emitted",
  "phase": "completed",
  "timestamp": "2026-07-19T12:00:00+00:00",
  "visibility": "public",
  "links": {
    "parent_event_id": null,
    "trace_id": "trace_...",
    "tool_call_id": null,
    "message_id": null
  },
  "payload": {
    "text": "Controllo la fonte prima di risponderti."
  }
}
```

Field semantics:

| Field | Contract |
|---|---|
| `schema_version` | Always `scarlet-stream-v2` for this contract. |
| `event_id` | Durable idempotency key copied from the persisted event. |
| `seq` | Monotonic session-global cursor. It is not provider step order and not turn-local. |
| `session_id` | Owning canonical chat session. |
| `turn_id` | Owning turn when applicable; may be null for session events. |
| `event_type` | Provider-independent runtime event type. |
| `phase` | `created`, `streaming`, `executing`, `completed`, `persisted`, or `failed`. |
| `timestamp` | Persisted event timestamp in ISO 8601. |
| `visibility` | `public`, `debug`, or `private`; clients decide which surfaces render it. |
| `links` | Compact persisted links to parent event, trace, tool call, and message. |
| `payload` | Event-specific structured data. Message events are enriched with the persisted message. |

The client must not infer chronology from timestamps. It orders by `seq` and
deduplicates by `event_id`.

## 4. Endpoints

### Live turn

```txt
POST /api/chat/sessions/{session_id}/turn/stream-v2
Content-Type: application/json
Response: application/x-ndjson
X-Scarlet-Stream-Schema: scarlet-stream-v2
X-Scarlet-Turn-ID: turn_...
```

The request body is the existing `ChatTurnRequest`. The response emits only
persisted V2 events. A successful turn includes `turn.completed`; a failed
turn includes `turn.failed`. Stream closure alone is never proof of success.

### Replay and reconnect

An interrupted live consumer reconnects to the same active or terminal turn:

```txt
GET /api/chat/sessions/{session_id}/turns/{turn_id}/stream-v2?after_seq=42
```

The initiating POST runs independently from the HTTP consumer. Closing the
response therefore does not cancel the native turn. The GET emits only durable
events after the exclusive cursor and stops at `turn.completed` or
`turn.failed`. Product clients retain the returned turn id, deduplicate by
`event_id`, and retry this GET at most five times.

Session-wide replay and gap repair remain available through:

```txt
GET /api/chat/sessions/{session_id}/events?after_seq=42&limit=500
```

Response:

```json
{
  "schema_version": "scarlet-stream-v2",
  "session_id": "ses_...",
  "events": [],
  "cursor": {
    "requested_after_seq": 42,
    "next_after_seq": 42,
    "latest_seq": 42,
    "has_more": false
  }
}
```

`after_seq` is exclusive. A client repeats the request with
`next_after_seq` until `has_more=false`. The endpoint returns every canonical
session event, not only one turn, so gaps in the session-global sequence are
observable and repairable.

## 5. Reducer Contract

`backend/app/api/chat_stream_v2.py::reduce_stream_events` is the executable
reference reducer. A client implementation must preserve these rules:

1. validate `schema_version` and the envelope;
2. deduplicate exact repeats by `event_id`;
3. reject or surface the same `event_id` with different content;
4. order unseen events by `(seq, event_id)`;
5. apply only the next session-global sequence;
6. hold later events when a gap exists and replay from the last applied cursor;
7. treat only `turn.completed` and `turn.failed` as terminal;
8. rebuild user/assistant messages, public notes, tool state, final answer, and
   error state from canonical event types.

Retries are therefore idempotent. Replaying an already applied event does not
duplicate a note, tool, or answer. The reference result is reusable as its
next `state`: it retains pending events, fingerprints, the applied cursor, and
reduced turn state so a later page can fill a gap and immediately drain the
events that were already waiting beyond it.

## 6. Reconstruction Examples

### Normal turn

```txt
turn.started
message.user.persisted
...
assistant.answer.completed
message.assistant.persisted
turn.completed
```

The answer text is available in `assistant.answer.completed.payload.text` and
the canonical stored message in
`message.assistant.persisted.payload.message`.

### Turn With Public Note And Tool

```txt
assistant.note.emitted
mind.tool_call.started
mind.tool_call.requested
mind.tool_call.result_returned
mind.tool_call.completed
assistant.answer.completed
turn.completed
```

The UI may show public notes immediately, expose normalized tool state in the
developer lens, and wait for the terminal event before declaring success.

### Failed Turn

```txt
turn.started
message.user.persisted
...
turn.failed
```

`turn.failed.payload` includes the stable error code/message and the persisted
turn snapshot. No assistant answer is invented.

### Reconnect After A Missing Event

If the client applied sequence 41 and receives 43, it holds 43, requests
`after_seq=41`, applies 42 then 43, and advances its cursor. A dropped client
connection resumes the same running turn. A provider-side stream failure is
different: the runtime retries the current provider step from the last complete
provider-history boundary because the upstream protocol exposes no token
resume cursor. Transient partial deltas are not canonical V2 events, preventing
duplicate durable notes, thinking blocks, tool calls, or answers.

## 7. Visibility And Developer Evidence

Consumer views render authored `public` evidence plus an explicit
consumer-activity allowlist for context, memory, bounded thinking status, Mind
tool lifecycle, and relevant organ state. Allowlisted diagnostic events use
deterministic narration from stable lifecycle facts; their payload text does
not become Scarlet-authored speech. Unknown diagnostic events remain hidden.

The Product evidence inspector may expose sequence, phase, visibility, links,
bounded payloads, and grouped lifecycle receipts. Protected events remain
hidden by default. A local interface preference may reveal their existence and
metadata, but never captured-thinking text. The dedicated debug/trace APIs
remain the internal inspection boundary for complete evidence. Product clients
must not derive user-visible semantics from provider-native blocks.

`turn.failed` remains a bounded terminal exception: the Product UI may render
its allowlisted code/message even when the persisted event retains diagnostic
visibility. Other diagnostic families require their own exact allowlist entry;
private or validation detail is never included implicitly.

## 8. Compatibility

- V2 envelope fields are stable for additive evolution.
- New event types and payload fields may be added; clients ignore unknown
  event types while still advancing the cursor.
- Removing or changing a required field requires a new schema version.
- The V1 stream remains available until web and Android have migrated and a
  dedicated removal decision is accepted.
- GPT Actions remains a separate external adapter and does not gain native
  streaming through this contract.
