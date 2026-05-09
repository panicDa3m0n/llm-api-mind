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
- `tool_calls`: structured model-facing tool calls, arguments, results, status, and latency.

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

`system` is optional. When omitted or blank, the backend loads the configured agent system prompt. The default prompt is `backend/app/prompts/scarlet_system.md`. It can be replaced with `AGENT_SYSTEM_PROMPT` or `AGENT_SYSTEM_PROMPT_PATH`.

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
- `503 agent.system_prompt_error`: the configured agent system prompt could not be loaded.
- `503 llm.not_configured`: `MINIMAX_API_KEY` is missing.
- `502 llm.provider_error`: MiniMax request failed.

Trace Behavior:

Creates at least:

- `llm.request`
- `llm.response`

When the model uses `mind_api`, the turn also creates one `mind.tool_call` trace per tool invocation.

`llm.request` stores the effective system prompt plus:

- `system_present`
- `system_source`: `bundled`, `environment`, `configured_path`, or `request`
- `system_path` when loaded from a file
- `tools`: currently the single `mind_api` tool schema

If the provider fails, creates:

- `llm.error`

`llm.response` stores final text, usage, raw final content, normalized tool call metadata, and raw provider messages from the tool loop when tools were used.

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

## Implemented Mind API

### GET /mind/schema

Status: implemented

Purpose:

Return the current `mind_api` tool schema, implemented routes, planned routes, and standard response shape. This is the schema-discovery entry point for Phase 2.

Request:

No request body.

Response:

```json
{
  "ok": true,
  "result": {
    "tool": {
      "name": "mind_api",
      "description": "Primary interface to Scarlet's cognitive API...",
      "input_schema": {
        "type": "object",
        "required": ["method", "path", "intent"]
      }
    },
    "routes": [
      {
        "method": "GET",
        "path": "/mind/schema",
        "status": "implemented"
      }
    ],
    "response_shape": {}
  },
  "cognitive_hint": "This is the currently available Mind API surface.",
  "suggested_next_actions": ["Use POST /mind/call to exercise mind_api"],
  "confidence": 1.0,
  "trace_id": null,
  "error": null
}
```

Errors:

No custom errors yet.

Trace Behavior:

No persistent trace is created by direct schema discovery because no session or turn context is required.

Example:

```txt
GET /mind/schema
```

### POST /mind/call

Status: implemented

Purpose:

Exercise the internal `mind_api(method, path, body, intent)` dispatcher through HTTP while the MiniMax tool loop is still being built. This provides the Phase 2 facade and records tool calls before cognitive modules are added.

Request:

```json
{
  "method": "GET",
  "path": "/mind/schema",
  "body": {},
  "intent": "Inspect available cognitive API routes before acting.",
  "session_id": "ses_...",
  "turn_id": "turn_..."
}
```

`session_id` and `turn_id` are optional. When `session_id` is supplied, it must refer to an existing chat session. `turn_id` is used only for trace linkage.

Response:

```json
{
  "ok": true,
  "result": {},
  "cognitive_hint": "Use this schema to choose only implemented Mind API routes...",
  "suggested_next_actions": ["Call implemented routes only"],
  "confidence": 1.0,
  "trace_id": "trace_...",
  "error": null,
  "tool_call_id": "tool_..."
}
```

Structured route errors return `200` with `ok=false` so the model can recover from planned or unavailable routes:

```json
{
  "ok": false,
  "error": {
    "code": "mind.route_not_available",
    "message": "POST /mind/memory/search is not implemented in the current Mind API.",
    "recoverable": true
  },
  "suggested_next_actions": [
    "Call GET /mind/schema",
    "Continue without this cognitive support"
  ],
  "tool_call_id": "tool_..."
}
```

Errors:

- `404 session.not_found`: a supplied `session_id` does not exist.
- `422 validation_error`: method, path, or intent is missing or invalid.

Trace Behavior:

Every call creates a `tool_calls` row with arguments, result, status, and latency. If `session_id` is supplied, the endpoint also creates a `mind.tool_call` trace linked to the session and optional turn.

Example:

```txt
POST /mind/call
```

## Planned Mind API

```txt
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
