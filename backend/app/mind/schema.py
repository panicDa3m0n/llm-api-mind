import hashlib
import json
from copy import deepcopy
from typing import Any


MIND_API_SCHEMA_VERSION = "2026-05-25.maintenance-proposals-v1"


MIND_API_TOOL_SCHEMA: dict[str, Any] = {
    "name": "mind_api",
    "description": (
        "Scarlet's internal cognitive API. Use it autonomously for schema "
        "awareness, memory, facts, traceable state inspection, and cognitive "
        "support before answering when that improves correctness."
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
        "examples": [
            {
                "method": "GET",
                "path": "/mind/schema",
                "intent": "Inspect the current cognitive API schema before choosing a route.",
            }
        ],
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
                    "description": (
                        "Semantic category for the memory. Use user_preference "
                        "for personal preferences/facts, project_fact for stable "
                        "project state, decision for accepted choices, correction "
                        "for user corrections, task_context for useful temporary "
                        "context/checkpoints, behavioral_pattern for recurring "
                        "interaction patterns, and episodic for compact session "
                        "anchors."
                    ),
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
                    "description": (
                        "How confident Scarlet is that the memory content is "
                        "sourceable and correctly stated. Values below the v0 "
                        "threshold are rejected."
                    ),
                },
                "salience": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0.7,
                    "description": (
                        "How useful this memory is expected to be in future "
                        "turns. Values below the v0 threshold are rejected."
                    ),
                },
                "scope": {
                    "type": "string",
                    "enum": ["project", "user", "session"],
                    "default": "project",
                    "description": (
                        "Where the memory should normally apply: project for "
                        "LLM API Mind work, user for personal/user-specific "
                        "continuity, session for short-lived session context."
                    ),
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Short retrieval tags. Use narrow lowercase concepts "
                        "such as api-mind, preference, chocolate, milestone, or "
                        "retrieval."
                    ),
                },
                "metadata": {
                    "type": "object",
                    "description": (
                        "Optional non-provenance metadata supplied by Scarlet. "
                        "Do not put ids, timestamps, session ids, turn ids, or "
                        "trace provenance here because the backend owns them."
                    ),
                },
            },
            "required": ["type", "content", "reason_for_storage"],
        },
        "examples": [
            {
                "method": "POST",
                "path": "/mind/memory/write",
                "intent": "Store a durable project correction.",
                "body": {
                    "type": "correction",
                    "content": "The owner wants API Mind to be treated as Scarlet's internal cognition.",
                    "reason_for_storage": "Stable behavior correction for future turns.",
                    "expected_future_use": "Guide future prompt and API design answers.",
                    "confidence": 0.9,
                    "salience": 0.85,
                    "scope": "project",
                    "tags": ["api-mind", "cognition"],
                },
            }
        ],
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
                "query": {
                    "type": "string",
                    "description": (
                        "Natural-language search phrase. It may contain user "
                        "wording, synonyms, labels, entities, or the question "
                        "Scarlet is trying to ground."
                    ),
                },
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
                    "description": (
                        "Optional memory type filter. Omit or use an empty list "
                        "to search all memory types."
                    ),
                },
                "scope": {
                    "type": ["string", "null"],
                    "enum": ["project", "user", "session", None],
                    "default": "project",
                    "description": (
                        "Optional scope filter. Use null to search all scopes; "
                        "use user for personal memories, project for project "
                        "state, and session for session-scoped anchors."
                    ),
                },
                "top_k": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 5,
                    "description": (
                        "Maximum number of memory records to return. Must be "
                        "between 1 and 20."
                    ),
                },
                "include_low_confidence": {
                    "type": "boolean",
                    "default": False,
                    "description": (
                        "When true, include low-confidence memories in the "
                        "candidate set. Use mainly for audits, debugging, or "
                        "historical inspection."
                    ),
                },
                "time": {
                    "type": ["object", "null"],
                    "description": (
                        "Optional backend-resolved temporal filter. Use it when "
                        "the user refers to today, yesterday, recent days, a "
                        "specific date/range, or this session. The backend, not "
                        "Scarlet, resolves real time."
                    ),
                    "properties": {
                        "preset": {
                            "type": ["string", "null"],
                            "enum": [
                                "today",
                                "yesterday",
                                "last_7_days",
                                "this_session",
                                None,
                            ],
                            "description": (
                                "Convenience time range resolved from backend "
                                "runtime time. this_session filters provenance "
                                "to the current session."
                            ),
                        },
                        "from": {
                            "type": ["string", "null"],
                            "description": (
                                "Inclusive ISO date or datetime lower bound. "
                                "Date-only values are interpreted as the start "
                                "of that local day."
                            ),
                        },
                        "to": {
                            "type": ["string", "null"],
                            "description": (
                                "Exclusive ISO date or datetime upper bound. "
                                "Date-only values include the whole local day."
                            ),
                        },
                        "basis": {
                            "type": ["string", "null"],
                            "enum": ["source_conversation", "recorded", "valid", None],
                            "default": "source_conversation",
                            "description": (
                                "Which timestamp family the filter applies to. "
                                "source_conversation checks the source session "
                                "messages behind a memory, recorded checks "
                                "memory.created_at, and valid checks fact "
                                "valid/recorded timestamps when available."
                            ),
                        },
                    },
                },
            },
            "required": ["query"],
        },
        "examples": [
            {
                "method": "POST",
                "path": "/mind/memory/search",
                "intent": "Find durable project context before answering.",
                "body": {
                    "query": "API Mind internal cognition",
                    "scope": "project",
                    "top_k": 5,
                    "time": {"preset": "last_7_days", "basis": "source_conversation"},
                },
            }
        ],
    },
    {
        "method": "GET",
        "path": "/mind/memory/{memory_id}",
        "status": "implemented",
        "purpose": (
            "Inspect a memory record by id, including status, provenance, "
            "metadata, and lifecycle history."
        ),
        "path_parameters": {
            "memory_id": {
                "type": "string",
                "description": "Existing memory id, for example mem_...",
            }
        },
        "body_schema": None,
        "examples": [
            {
                "method": "GET",
                "path": "/mind/memory/mem_example",
                "intent": "Inspect a memory record before using it as evidence.",
            }
        ],
    },
    {
        "method": "GET",
        "path": "/mind/memory/facts",
        "status": "implemented",
        "purpose": (
            "Inspect canonical memory facts by memory id, entity, predicate, "
            "or natural-language query."
        ),
        "body_schema": {
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": ["string", "null"],
                    "description": "Optional memory id to inspect facts for one memory.",
                },
                "entity": {
                    "type": ["string", "null"],
                    "description": (
                        "Canonical entity filter, such as protocollo-zero-luce. "
                        "If omitted, query can be canonicalized into an entity."
                    ),
                },
                "predicate": {
                    "type": ["string", "null"],
                    "description": (
                        "Optional canonical predicate filter, such as "
                        "response_format."
                    ),
                },
                "query": {
                    "type": ["string", "null"],
                    "description": (
                        "Natural-language fact lookup. Useful when Scarlet has "
                        "synonyms, aliases, or an uncertain entity name."
                    ),
                },
                "status": {
                    "type": "string",
                    "default": "active",
                    "description": (
                        "Fact lifecycle status to return. Usually active. Use "
                        "include_inactive=true for historical/deprecated facts."
                    ),
                },
                "include_inactive": {
                    "type": "boolean",
                    "default": False,
                    "description": (
                        "When true, include deprecated or superseded facts as "
                        "inspectable history."
                    ),
                },
            },
        },
        "examples": [
            {
                "method": "GET",
                "path": "/mind/memory/facts",
                "intent": "Inspect canonical facts for an entity and predicate.",
                "body": {
                    "entity": "protocollo-zero-luce",
                    "predicate": "response_format",
                    "include_inactive": True,
                },
            }
        ],
    },
    {
        "method": "POST",
        "path": "/mind/memory/facts/backfill",
        "status": "implemented",
        "purpose": (
            "Extract missing canonical facts for existing memory records "
            "through a traceable operation."
        ),
        "body_schema": {
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": ["string", "null"],
                    "description": (
                        "Optional memory id. Omit to backfill all eligible "
                        "memories."
                    ),
                },
                "include_inactive": {
                    "type": "boolean",
                    "default": True,
                    "description": (
                        "When true, include inactive memories while extracting "
                        "or rebuilding fact records."
                    ),
                },
            },
        },
        "examples": [
            {
                "method": "POST",
                "path": "/mind/memory/facts/backfill",
                "intent": "Extract missing facts from existing memories.",
                "body": {"include_inactive": True},
            }
        ],
    },
    {
        "method": "GET",
        "path": "/mind/memory/conflicts",
        "status": "implemented",
        "purpose": "Inspect unresolved active memory conflicts.",
        "body_schema": None,
        "examples": [
            {
                "method": "GET",
                "path": "/mind/memory/conflicts",
                "intent": "Check active memory conflicts before answering.",
            }
        ],
    },
    {
        "method": "POST",
        "path": "/mind/memory/deprecate",
        "status": "implemented",
        "purpose": (
            "Mark a memory as deprecated while preserving it as inspectable "
            "history."
        ),
        "body_schema": {
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "string",
                    "description": "Active or inactive memory id to deprecate.",
                },
                "reason": {
                    "type": "string",
                    "description": (
                        "Sourceable reason why this memory should no longer be "
                        "active evidence."
                    ),
                },
                "superseded_by": {
                    "type": ["string", "null"],
                    "description": "Optional replacement memory id.",
                },
            },
            "required": ["memory_id", "reason"],
        },
        "examples": [
            {
                "method": "POST",
                "path": "/mind/memory/deprecate",
                "intent": "Mark obsolete memory as inactive history.",
                "body": {
                    "memory_id": "mem_obsolete",
                    "reason": "The owner corrected this memory.",
                },
            }
        ],
    },
    {
        "method": "POST",
        "path": "/mind/memory/supersede",
        "status": "implemented",
        "purpose": (
            "Link an obsolete memory to a replacement and optionally deprecate "
            "the obsolete memory."
        ),
        "body_schema": {
            "type": "object",
            "properties": {
                "old_memory_id": {
                    "type": "string",
                    "description": "Obsolete memory id that is being replaced.",
                },
                "new_memory_id": {
                    "type": "string",
                    "description": "Replacement memory id that should become canonical.",
                },
                "reason": {
                    "type": "string",
                    "description": "Sourceable reason for the supersession link.",
                },
                "deprecate_old": {
                    "type": "boolean",
                    "default": True,
                    "description": (
                        "When true, mark the old memory deprecated in the same "
                        "operation."
                    ),
                },
            },
            "required": ["old_memory_id", "new_memory_id", "reason"],
        },
        "examples": [
            {
                "method": "POST",
                "path": "/mind/memory/supersede",
                "intent": "Link an obsolete memory to its replacement.",
                "body": {
                    "old_memory_id": "mem_old",
                    "new_memory_id": "mem_new",
                    "reason": "The new record reflects the owner's correction.",
                    "deprecate_old": True,
                },
            }
        ],
    },
    {
        "method": "GET",
        "path": "/mind/sessions",
        "status": "implemented",
        "purpose": (
            "List recent chat sessions as episodic memory candidates with "
            "descriptive summaries, message counts, and memory provenance ids."
        ),
        "body_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 10,
                    "description": (
                        "Maximum number of session index rows to return. Must "
                        "be between 1 and 50."
                    ),
                },
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": (
                        "Pagination offset. Increase it to inspect additional "
                        "session index pages."
                    ),
                },
                "query": {
                    "type": ["string", "null"],
                    "description": (
                        "Optional sparse lexical filter over title, summary, "
                        "conversation text, and summary fields."
                    ),
                },
                "time": {
                    "type": ["object", "null"],
                    "description": (
                        "Optional backend-resolved temporal filter for episodic "
                        "session search. Use it for today, yesterday, recent "
                        "periods, explicit date ranges, or this session."
                    ),
                    "properties": {
                        "preset": {
                            "type": ["string", "null"],
                            "enum": [
                                "today",
                                "yesterday",
                                "last_7_days",
                                "this_session",
                                None,
                            ],
                            "description": (
                                "Convenience time range resolved from backend "
                                "runtime time. this_session returns only the "
                                "current chat session."
                            ),
                        },
                        "from": {
                            "type": ["string", "null"],
                            "description": "Inclusive ISO date or datetime lower bound.",
                        },
                        "to": {
                            "type": ["string", "null"],
                            "description": "Exclusive ISO date or datetime upper bound.",
                        },
                        "basis": {
                            "type": ["string", "null"],
                            "enum": ["conversation", "created", "updated", "summary", None],
                            "default": "conversation",
                            "description": (
                                "Which timestamp family the filter applies to. "
                                "conversation checks user/assistant message "
                                "timestamps, created checks session creation, "
                                "updated checks session update time, and summary "
                                "checks summary freshness."
                            ),
                        },
                    },
                },
            },
        },
        "examples": [
            {
                "method": "GET",
                "path": "/mind/sessions",
                "intent": "Find recent sessions that may contain episodic context.",
                "body": {"limit": 10, "offset": 0, "time": {"preset": "today"}},
            },
            {
                "method": "GET",
                "path": "/mind/sessions",
                "intent": "Search episodic session summaries for Zero-Luce context.",
                "body": {"query": "Zero-Luce", "limit": 5, "time": {"preset": "last_7_days"}},
            },
        ],
    },
    {
        "method": "GET",
        "path": "/mind/sessions/{session_id}",
        "status": "implemented",
        "purpose": (
            "Read one session by id, including its episodic summary, full "
            "conversation transcript by default, and semantic memories written "
            "from that session."
        ),
        "path_parameters": {
            "session_id": {
                "type": "string",
                "description": "Existing chat session id, for example ses_...",
            }
        },
        "body_schema": {
            "type": "object",
            "properties": {
                "include_messages": {
                    "type": "boolean",
                    "default": True,
                    "description": (
                        "When true, include user/assistant transcript messages "
                        "in the result."
                    ),
                },
                "include_memories": {
                    "type": "boolean",
                    "default": True,
                    "description": (
                        "When true, include semantic memories written from the "
                        "session."
                    ),
                },
                "message_limit": {
                    "type": ["integer", "null"],
                    "minimum": 1,
                    "maximum": 2000,
                    "description": "Optional last-N message limit. Omit for full transcript.",
                },
            },
        },
        "examples": [
            {
                "method": "GET",
                "path": "/mind/sessions/ses_example",
                "intent": "Recover the exact conversation behind a memory source_session_id.",
                "body": {"include_messages": True, "include_memories": True},
            }
        ],
    },
    {
        "method": "POST",
        "path": "/mind/sessions/{session_id}/summarize",
        "status": "implemented",
        "purpose": (
            "Create or refresh the descriptive episodic summary for a session "
            "from the complete user<->assistant message history through a "
            "traceable LLM-backed compaction step."
        ),
        "path_parameters": {
            "session_id": {
                "type": "string",
                "description": "Existing chat session id to summarize.",
            }
        },
        "body_schema": {
            "type": "object",
            "properties": {
                "force": {
                    "type": "boolean",
                    "default": False,
                    "description": "Refresh even when the stored summary already covers the latest message.",
                },
                "focus": {
                    "type": ["string", "null"],
                    "description": "Optional summarization focus for Scarlet's internal recall.",
                },
            },
        },
        "examples": [
            {
                "method": "POST",
                "path": "/mind/sessions/ses_example/summarize",
                "intent": "Refresh episodic summary after a meaningful conversation.",
                "body": {"force": True, "focus": "project memory decisions"},
            }
        ],
    },
    {
        "method": "POST",
        "path": "/mind/metacognition/step",
        "status": "implemented",
        "purpose": (
            "Run one LLM-backed internal metacognitive step before answering. "
            "This is the single metacognition route: critique, claim checks, "
            "workspace notes, and reflection are returned inside this result "
            "instead of separate cognitive endpoints."
        ),
        "body_schema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": [
                        "orient",
                        "critic",
                        "validator",
                        "planner",
                        "synthesizer",
                        "empathy",
                        "memory_curator",
                    ],
                    "default": "critic",
                    "description": (
                        "Reviewer stance. Use orient to frame a problem, critic "
                        "to find weaknesses, validator to check claims, planner "
                        "to plan work, synthesizer to combine evidence, empathy "
                        "for relational nuance, and memory_curator for memory "
                        "state review."
                    ),
                },
                "objective": {
                    "type": "string",
                    "description": "Concrete internal objective for the review.",
                },
                "focus_question": {
                    "type": ["string", "null"],
                    "description": "Optional focused question the reviewer should answer.",
                },
                "internal_prompt": {
                    "type": ["string", "null"],
                    "description": "Precise private prompt/question Scarlet sends to her internal reviewer.",
                },
                "known_evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                    "description": (
                        "Compact evidence Scarlet has already gathered, such "
                        "as memory ids, schema facts, transcript evidence, or "
                        "trace observations."
                    ),
                },
                "uncertainties": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                    "description": (
                        "Specific unknowns, risks, or claims that remain weak."
                    ),
                },
                "draft_answer": {
                    "type": ["string", "null"],
                    "description": "Optional draft answer to critique before finalizing.",
                },
                "previous_steps": {
                    "type": "array",
                    "items": {"type": "object"},
                    "default": [],
                    "description": (
                        "Optional prior metacognition step summaries if Scarlet "
                        "is continuing an internal review chain."
                    ),
                },
                "max_findings": {
                    "type": "integer",
                    "default": 6,
                    "description": "Maximum number of findings to request from the reviewer.",
                },
            },
            "required": ["objective"],
            "accepted_aliases": {
                "prompt": "internal_prompt; also used as objective when objective is missing",
                "goal": "objective",
                "task": "objective",
                "purpose": "objective",
                "question": "objective and focus_question when missing",
                "context": "known_evidence summary when known_evidence is missing",
            },
        },
        "examples": [
            {
                "method": "POST",
                "path": "/mind/metacognition/step",
                "intent": "Run one internal metacognitive review before answering.",
                "body": {
                    "mode": "critic",
                    "objective": "Answer a question about API Mind reliability.",
                    "focus_question": "Which unsupported claims might be present?",
                    "internal_prompt": "Check whether my draft depends on current schema state and what I should verify before answering.",
                    "known_evidence": ["runtime_context memory_context.searched=true"],
                    "uncertainties": ["Mind API schema may have changed."],
                    "draft_answer": "Scarlet can use the current schema correctly.",
                },
            }
        ],
    },
    {
        "method": "POST",
        "path": "/mind/attention/context",
        "status": "planned",
        "purpose": "Build an attention context pack after memory is available.",
        "body_schema": None,
    },
]


def build_mind_schema() -> dict[str, Any]:
    schema = _schema_without_digest()
    schema["schema_digest"] = compute_schema_digest(schema)
    return schema


def _schema_without_digest() -> dict[str, Any]:
    return {
        "schema_version": MIND_API_SCHEMA_VERSION,
        "tool": MIND_API_TOOL_SCHEMA,
        "routes": [_route_catalog_item(route) for route in MIND_API_ROUTES],
        "response_shape": {
            "ok": "boolean",
            "result": "object",
            "cognitive_hint": "string | null",
            "suggested_next_actions": "string[]",
            "confidence": "number",
            "trace_id": "string | null",
            "usage_guide": "object | null",
            "error": "object | null",
        },
        "schema_policy": {
            "source_of_truth": "GET /mind/schema",
            "role": (
                "Capability catalog only. It tells Scarlet which endpoints "
                "exist and what each endpoint is for."
            ),
            "use_when": [
                "discovering current endpoint availability",
                "checking whether a route is implemented, planned, or unavailable",
                "choosing which endpoint family can answer a cognitive need",
            ],
            "prompt_policy": (
                "Detailed endpoint body schemas, parameter descriptions, "
                "examples, and retry guidance are returned as usage_guide on "
                "recoverable endpoint errors instead of being exposed in the "
                "catalog."
            ),
        },
    }


def compute_schema_digest(schema: dict[str, Any] | None = None) -> str:
    source = schema or _schema_without_digest()
    comparable = {key: value for key, value in source.items() if key != "schema_digest"}
    encoded = json.dumps(
        comparable,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()[:16]


def schema_metadata() -> dict[str, str]:
    return {
        "schema_version": MIND_API_SCHEMA_VERSION,
        "schema_digest": compute_schema_digest(),
        "schema_route": "GET /mind/schema",
    }


def route_body_schema(method: str, path: str) -> dict[str, Any] | None:
    route = _find_route(method, path)
    if route is not None:
        body_schema = route.get("body_schema")
        return deepcopy(body_schema) if isinstance(body_schema, dict) else None
    return None


def route_usage_guide(method: str, path: str) -> dict[str, Any] | None:
    route = _find_route(method, path)
    if route is None or route.get("status") != "implemented":
        return None

    body_schema = route.get("body_schema")
    path_parameters = route.get("path_parameters")
    guide: dict[str, Any] = {
        "method": str(route["method"]),
        "path": str(route["path"]),
        "called_path": _normalize_path(path),
        "status": str(route["status"]),
        "purpose": str(route.get("purpose") or ""),
        "body_schema": deepcopy(body_schema) if isinstance(body_schema, dict) else None,
        "parameters": _parameters_from_body_schema(body_schema),
        "path_parameters": deepcopy(path_parameters)
        if isinstance(path_parameters, dict)
        else {},
        "examples": deepcopy(route.get("examples") or []),
        "retry_guidance": (
            "Use this guide to correct the same endpoint call. Do not call "
            "GET /mind/schema just to recover the body shape unless the route "
            "itself may have changed or this guide is missing."
        ),
    }
    aliases = body_schema.get("accepted_aliases") if isinstance(body_schema, dict) else None
    if aliases:
        guide["accepted_aliases"] = deepcopy(aliases)
    return guide


def implemented_route_summaries() -> list[dict[str, str]]:
    return [
        {
            "method": str(route["method"]),
            "path": str(route["path"]),
            "status": str(route["status"]),
        }
        for route in MIND_API_ROUTES
        if route["status"] == "implemented"
    ]


def route_catalog_suggestions(method: str, path: str) -> list[dict[str, str]]:
    normalized_path = _normalize_path(path)
    normalized_method = method.upper()
    requested_list = [part for part in normalized_path.strip("/").split("/") if part]
    requested_parts = set(requested_list)
    requested_category = requested_list[1] if len(requested_list) > 1 else None
    suggestions: list[tuple[int, dict[str, str]]] = []
    for route in MIND_API_ROUTES:
        route_path = str(route["path"])
        route_list = [part for part in route_path.strip("/").split("/") if part]
        route_parts = set(route_list)
        route_category = route_list[1] if len(route_list) > 1 else None
        shared = len(requested_parts & route_parts)
        same_method_bonus = 2 if str(route["method"]) == normalized_method else 0
        same_category_bonus = (
            3
            if requested_category is not None and requested_category == route_category
            else 0
        )
        prefix_bonus = (
            2
            if route_path.startswith(normalized_path.rstrip("/") + "/")
            else 0
        )
        score = shared + same_method_bonus + same_category_bonus + prefix_bonus
        if score <= 0:
            continue
        suggestions.append(
            (
                score,
                {
                    "method": str(route["method"]),
                    "path": route_path,
                    "status": str(route["status"]),
                    "purpose": str(route.get("purpose") or ""),
                },
            )
        )
    suggestions.sort(key=lambda item: item[0], reverse=True)
    return [item for _, item in suggestions[:5]]


def _find_route(method: str, path: str) -> dict[str, Any] | None:
    normalized_method = method.upper()
    normalized_path = _normalize_path(path)
    for route in MIND_API_ROUTES:
        if route["method"] == normalized_method and _route_path_matches(
            str(route["path"]),
            normalized_path,
        ):
            return route
    return None


def _normalize_path(path: str) -> str:
    normalized_path = path.strip()
    if not normalized_path.startswith("/"):
        normalized_path = f"/{normalized_path}"
    return normalized_path


def _route_catalog_item(route: dict[str, Any]) -> dict[str, Any]:
    return {
        "method": str(route["method"]),
        "path": str(route["path"]),
        "status": str(route["status"]),
        "purpose": str(route.get("purpose") or ""),
    }


def _parameters_from_body_schema(body_schema: Any) -> dict[str, Any]:
    if not isinstance(body_schema, dict):
        return {}
    properties = body_schema.get("properties")
    if not isinstance(properties, dict):
        return {}
    required = set(body_schema.get("required") or [])
    return {
        name: _parameter_guide(name, spec, required=name in required)
        for name, spec in properties.items()
    }


def _parameter_guide(name: str, spec: Any, *, required: bool) -> dict[str, Any]:
    if not isinstance(spec, dict):
        return {
            "required": required,
            "description": f"Parameter {name}.",
        }
    guide = {
        "required": required,
        "type": spec.get("type"),
        "description": spec.get("description") or f"Parameter {name}.",
    }
    for key in ("enum", "minimum", "maximum", "default", "items", "properties"):
        if key in spec:
            guide[key] = deepcopy(spec[key])
    return guide


def _route_path_matches(route_path: str, requested_path: str) -> bool:
    if route_path == requested_path:
        return True
    route_parts = route_path.strip("/").split("/")
    requested_parts = requested_path.strip("/").split("/")
    if len(route_parts) != len(requested_parts):
        return False
    return all(
        route_part.startswith("{") and route_part.endswith("}")
        or route_part == requested_part
        for route_part, requested_part in zip(route_parts, requested_parts, strict=True)
    )
