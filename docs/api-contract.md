# API Contract

This file documents stable API contracts once they are implemented.

## Response Philosophy

Mind API responses should be useful to both code and the LLM agent.

Successful responses should follow this shape where practical:

```json
{
  "ok": true,
  "result": {},
  "cognitive_hint": "Short explanation of how this result may matter.",
  "suggested_next_actions": [],
  "confidence": 0.8,
  "trace_id": "trace_..."
}
```

Error responses should be structured and recoverable when possible:

```json
{
  "ok": false,
  "error": {
    "code": "namespace.error_name",
    "message": "Human-readable error.",
    "recoverable": true
  },
  "suggested_next_actions": [],
  "trace_id": "trace_..."
}
```

## Planned Chat And Debug API

```txt
GET  /api/debug/state/{session_id}
```

## Implemented System API

### GET /health

Status: implemented

Purpose:

Report basic backend runtime health without exposing secrets.

Request:

No request body.

Response:

```json
{
  "status": "ok",
  "app": "LLM API Mind",
  "environment": "local",
  "model": "MiniMax-M2.7"
}
```

Errors:

No custom errors yet.

Trace Behavior:

No persistent trace yet. This endpoint is a process health check, not an agent turn.

Example:

```txt
GET /health
```

### POST /api/debug/llm-smoke-test

Status: implemented

Purpose:

Verify that the backend can call the configured LLM provider. This is a development/debug endpoint, not an agent turn.

Request:

```json
{
  "prompt": "Reply with exactly: pong",
  "max_tokens": 4096
}
```

`max_tokens` is optional. When omitted, the backend uses `MINIMAX_MAX_TOKENS`, currently defaulting to `4096`.

Response:

```json
{
  "ok": true,
  "model": "MiniMax-M2.7",
  "text": "pong",
  "max_tokens": 4096,
  "latency_ms": 2556,
  "usage": {
    "input_tokens": 28,
    "output_tokens": 28
  }
}
```

Errors:

- `503 llm.not_configured`: `MINIMAX_API_KEY` is missing.
- `502 llm.provider_error`: the upstream provider request failed.

Trace Behavior:

No persistent trace yet. Provider latency and usage are returned in the response for manual inspection.

Example:

```txt
POST /api/debug/llm-smoke-test
```

## MVP Storage Schema

Status: implemented

Purpose:

Provide the persistence foundation for baseline chat tracing before cognitive modules are added.

Tables:

- `sessions`: conversation/project session container.
- `turns`: one user-to-assistant processing cycle, including model, status, latency, and error metadata.
- `messages`: user, assistant, system, or tool messages linked to sessions and optionally turns.
- `traces`: structured JSON trace events linked to sessions and optionally turns.

Trace Behavior:

Trace rows store JSON payloads. Full turn trace assembly will be implemented with the chat endpoints.

## Implemented Chat API

### POST /api/chat/sessions

Status: implemented

Purpose:

Create a persistent chat session.

Request:

```json
{
  "title": "Baseline trace",
  "metadata": {
    "source": "manual"
  }
}
```

Response:

```json
{
  "id": "ses_...",
  "title": "Baseline trace",
  "created_at": "2026-05-08T15:00:00Z",
  "updated_at": "2026-05-08T15:00:00Z",
  "metadata": {
    "source": "manual"
  }
}
```

Trace Behavior:

No turn trace is created by session creation.

### POST /api/chat/sessions/{session_id}/turn

Status: implemented

Purpose:

Persist a user message, call MiniMax with the session history, persist the assistant response, and store request/response traces.

Request:

```json
{
  "message": "Reply with exactly: pong",
  "system": null,
  "max_tokens": null
}
```

`max_tokens` is optional. When omitted, the backend uses `MINIMAX_MAX_TOKENS`.

Response:

```json
{
  "session": {
    "id": "ses_...",
    "title": "Baseline trace",
    "created_at": "2026-05-08T15:00:00Z",
    "updated_at": "2026-05-08T15:00:01Z",
    "metadata": {}
  },
  "turn_id": "turn_...",
  "status": "completed",
  "user_message": {
    "id": "msg_...",
    "role": "user",
    "content": "Reply with exactly: pong"
  },
  "assistant_message": {
    "id": "msg_...",
    "role": "assistant",
    "content": "pong"
  },
  "trace_ids": ["trace_...", "trace_..."],
  "model": "MiniMax-M2.7",
  "latency_ms": 1104,
  "usage": {
    "input_tokens": 26,
    "output_tokens": 16
  }
}
```

Errors:

- `404 session.not_found`: the session does not exist.
- `503 llm.not_configured`: `MINIMAX_API_KEY` is missing.
- `502 llm.provider_error`: MiniMax request failed.

Trace Behavior:

Creates at least:

- `llm.request`
- `llm.response`

If the provider fails, creates:

- `llm.error`

### GET /api/chat/sessions/{session_id}/messages

Status: implemented

Purpose:

Return persisted messages for a chat session in creation order.

Errors:

- `404 session.not_found`: the session does not exist.

### GET /api/debug/traces/{turn_id}

Status: implemented

Purpose:

Return trace rows linked to a turn.

Errors:

- `404 trace.not_found`: no traces exist for the turn.

## Planned Mind API

```txt
GET  /mind/schema
GET  /mind/state
POST /mind/events/emit
POST /mind/memory/write
POST /mind/memory/search
POST /mind/attention/context
POST /mind/reflection/review
```

## Contract Entry Template

```md
## METHOD /path

Status: planned | implemented | deprecated

Purpose:

Request:

Response:

Errors:

Trace Behavior:

Example:
```
