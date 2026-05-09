from typing import Any


MIND_API_TOOL_SCHEMA: dict[str, Any] = {
    "name": "mind_api",
    "description": (
        "Primary interface to Scarlet's cognitive API. Use it to inspect "
        "available schemas and request traceable cognitive support."
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
        "status": "implemented",
        "purpose": (
            "Autonomously write a reusable, sourceable memory candidate after "
            "the v0 policy accepts it."
        ),
        "body_schema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": [
                        "project_fact",
                        "user_preference",
                        "decision",
                        "correction",
                        "task_context",
                        "behavioral_pattern",
                        "episodic",
                    ],
                },
                "content": {
                    "type": "string",
                    "description": "Sourceable memory content to reuse later.",
                },
                "reason_for_storage": {
                    "type": "string",
                    "description": "Why Scarlet decided this belongs in memory.",
                },
                "expected_future_use": {
                    "type": "string",
                    "description": "When this memory is expected to help.",
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0.7,
                },
                "salience": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0.7,
                },
                "scope": {
                    "type": "string",
                    "enum": ["project", "user", "session"],
                    "default": "project",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "metadata": {
                    "type": "object",
                },
            },
            "required": ["type", "content", "reason_for_storage"],
        },
    },
    {
        "method": "POST",
        "path": "/mind/memory/search",
        "status": "implemented",
        "purpose": (
            "Search Scarlet's active memories and return sourceable results "
            "with provenance, confidence, salience, and relevance scores."
        ),
        "body_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "project_fact",
                            "user_preference",
                            "decision",
                            "correction",
                            "task_context",
                            "behavioral_pattern",
                            "episodic",
                        ],
                    },
                },
                "scope": {
                    "type": ["string", "null"],
                    "enum": ["project", "user", "session", None],
                    "default": "project",
                },
                "top_k": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 5,
                },
                "include_low_confidence": {
                    "type": "boolean",
                    "default": False,
                },
            },
            "required": ["query"],
        },
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
