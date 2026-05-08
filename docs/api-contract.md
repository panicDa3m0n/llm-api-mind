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
POST /api/chat/sessions
POST /api/chat/sessions/{session_id}/turn
GET  /api/chat/sessions/{session_id}/messages
GET  /api/debug/traces/{turn_id}
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
