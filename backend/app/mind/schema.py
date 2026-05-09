from typing import Any


MIND_API_TOOL_SCHEMA: dict[str, Any] = {
    "name": "mind_api",
    "description": (
        "Primary interface to Scarlet's cognitive API. Use it to inspect "
        "available schemas and, later, request traceable cognitive support."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "enum": ["GET", "POST"],
            },
            "path": {
                "type": "string",
            },
            "body": {
                "type": "object",
            },
            "intent": {
                "type": "string",
                "description": "Short natural language reason for the call.",
            },
        },
        "required": ["method", "path", "intent"],
    },
}


MIND_API_ROUTES: list[dict[str, Any]] = [
    {
        "method": "GET",
        "path": "/mind/schema",
        "status": "implemented",
        "purpose": "Inspect the currently available Mind API tool schema and routes.",
        "body_schema": None,
    },
    {
        "method": "POST",
        "path": "/mind/events/emit",
        "status": "planned",
        "purpose": "Emit traceable cognitive events after the event store exists.",
        "body_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "payload": {"type": "object"},
            },
            "required": ["type", "payload"],
        },
    },
    {
        "method": "POST",
        "path": "/mind/memory/write",
        "status": "planned",
        "purpose": "Write memory after the Phase 3 memory experiment begins.",
        "body_schema": None,
    },
    {
        "method": "POST",
        "path": "/mind/memory/search",
        "status": "planned",
        "purpose": "Search memory after the Phase 3 memory experiment begins.",
        "body_schema": None,
    },
    {
        "method": "POST",
        "path": "/mind/attention/context",
        "status": "planned",
        "purpose": "Build an attention context pack after memory is available.",
        "body_schema": None,
    },
    {
        "method": "POST",
        "path": "/mind/reflection/review",
        "status": "planned",
        "purpose": "Run structured reflection after failure experiments begin.",
        "body_schema": None,
    },
]


def build_mind_schema() -> dict[str, Any]:
    return {
        "tool": MIND_API_TOOL_SCHEMA,
        "routes": MIND_API_ROUTES,
        "response_shape": {
            "ok": "boolean",
            "result": "object",
            "cognitive_hint": "string | null",
            "suggested_next_actions": "string[]",
            "confidence": "number",
            "trace_id": "string | null",
            "error": "object | null",
        },
    }
