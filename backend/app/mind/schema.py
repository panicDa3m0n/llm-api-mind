import hashlib
import json
from copy import deepcopy
from typing import Any


MIND_API_SCHEMA_VERSION = "2026-07-27.autonomous-perception-v1"
MIND_SHELL_SCHEMA_VERSION = "2026-07-27.autonomous-perception-v1"


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


MIND_SHELL_TOOL_SCHEMA: dict[str, Any] = {
    "name": "mind_shell",
    "description": (
        "Scarlet's internal cognitive command shell. Use concise commands to "
        "navigate memory, sessions, focus, volition, affect, agent mode, perception, metacognition, "
        "and capability help without exposing endpoint mechanics to the user."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": (
                    "One cognitive shell command, for example: "
                    "memory search \"cioccolato\" --top 5"
                ),
            },
            "intent": {
                "type": "string",
                "description": (
                    "Short natural-language reason for why Scarlet is using "
                    "the command now."
                ),
            },
        },
        "required": ["command"],
    },
}


MIND_SHELL_COMMANDS: list[dict[str, Any]] = [
    {
        "namespace": "help",
        "purpose": "Inspect available cognitive command families and examples.",
        "commands": [
            "help",
            "help memory",
            "help session",
            "help focus",
            "help volition",
            "help affect",
            "help mode",
            "help perception",
            "help metacognition",
        ],
    },
    {
        "namespace": "memory",
        "purpose": "Search, write, inspect, and maintain semantic memories.",
        "commands": [
            "memory search \"query\" --top 5",
            "memory write --type user_preference --scope user --content \"...\" --reason \"...\" --future-use \"...\"",
            "memory open mem_...",
            "memory graph mem_... --depth 2 --limit 30",
            "memory facts --query \"entity or question\"",
            "memory conflicts",
            "memory deprecate mem_... --reason \"...\"",
            "memory supersede mem_old mem_new --reason \"...\"",
        ],
    },
    {
        "namespace": "session",
        "purpose": "Navigate episodic chat sessions, summaries, and transcripts.",
        "commands": [
            "session list --query \"topic or date\" --limit 5",
            "session open ses_... --limit 200",
            "session message msg_...",
            "session turn turn_...",
            "session summarize ses_... --force",
        ],
    },
    {
        "namespace": "focus",
        "purpose": "Read and mutate Scarlet's single foreground focus state.",
        "commands": [
            "focus read",
            "focus list --status active --limit 10",
            "focus search \"query\" --limit 10",
            "focus set \"object\" --type investigation --reason \"...\" --intensity 0.7",
            "focus update --id foc_... --object \"...\" --reason \"...\"",
            "focus hold --id foc_... --reason \"...\"",
            "focus shift \"new object\" --reason \"...\"",
            "focus defer --id foc_... --reason \"...\"",
            "focus resolve --id foc_... --resolution \"...\"",
            "focus impossible --id foc_... --reason \"...\"",
            "focus timeline --limit 10",
        ],
    },
    {
        "namespace": "volition",
        "purpose": "Manage Scarlet's latent self-generated intentions.",
        "commands": [
            "volition list active --limit 10",
            "volition list due --limit 10",
            "volition search \"query\" --limit 10",
            "volition create \"desire\" --reason \"...\" --horizon long --intensity 0.6 --next-review-at \"2026-07-14T10:00:00+02:00\" --review-interval-seconds 86400",
            "volition read int_...",
            "volition update int_... --reason \"...\"",
            "volition defer int_... --reason \"...\" --next-review-at \"2026-07-14T10:00:00+02:00\"",
            "volition review int_... --reason \"...\" --review-interval-seconds 86400",
            "volition promote int_... --reason \"...\"",
            "volition resolve int_... --resolution \"...\"",
            "volition impossible int_... --reason \"...\"",
            "volition deprecate int_... --reason \"...\"",
        ],
    },
    {
        "namespace": "affect",
        "purpose": "Read backend-appraised affect state and emotion prototypes.",
        "commands": [
            "affect read",
            "affect list --limit 10",
            "affect prototypes",
        ],
    },
    {
        "namespace": "mode",
        "purpose": "Inspect or select Scarlet's foreground agent operating posture.",
        "commands": [
            "mode read",
            "mode list",
            "mode set idle --reason \"...\"",
            "mode set scouting --reason \"...\"",
        ],
    },
    {
        "namespace": "perception",
        "purpose": (
            "Inspect available sensory channels and open source-labelled "
            "observations without mutating the append-only ledger."
        ),
        "commands": [
            "perception status",
            "perception open notifications --limit 10",
            "perception read per_...",
        ],
    },
    {
        "namespace": "metacognition",
        "purpose": "Run one internal metacognitive step when deeper self-review matters.",
        "commands": [
            "metacognition step --objective \"...\" --mode critic --question \"...\"",
            "metacognition step --objective \"...\" --mode memory_curator --draft \"...\"",
            "metacognition step --objective \"...\" --mode review_previous_turn --turn-scope previous --detail digest",
        ],
    },
]


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
            "backend shape policy accepts it. Backend owns provenance, tags, "
            "metadata, and retrieval scores."
        ),
        "body_schema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "description": (
                        "Short natural semantic category for the memory. Prefer "
                        "stable labels such as user_preference, project_fact, "
                        "decision, correction, task_context, behavioral_pattern, "
                        "episodic, lesson, workflow, or other precise labels "
                        "when those fit. The backend accepts free labels and "
                        "uses them as semantic retrieval surfaces, not rigid "
                        "truth enums."
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
                "scope": {
                    "type": "string",
                    "default": "general",
                    "description": (
                        "Cognitive area/purpose of the memory, not privacy or "
                        "authorization. Use labels such as user, project, "
                        "session, metacognitive, workflow, preference, or a "
                        "more precise free label. Future user isolation belongs "
                        "to backend user ids, not this field."
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
                    "scope": "project",
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
            "with provenance and query-time relevance scores."
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
                    "items": {"type": "string"},
                    "description": (
                        "Optional semantic type hints. They are appended to the "
                        "retrieval query and should not be used as a rigid "
                        "filter unless Scarlet intentionally wants to narrow "
                        "the search by label."
                    ),
                },
                "scope": {
                    "type": ["string", "null"],
                    "default": None,
                    "description": (
                        "Optional exact cognitive scope filter. Omit or use "
                        "null to search all scopes. Scope is not a privacy or "
                        "authorization boundary."
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
                    "scope": None,
                    "top_k": 5,
                    "time": {"preset": "last_7_days", "basis": "source_conversation"},
                },
            }
        ],
    },
    {
        "method": "POST",
        "path": "/mind/memory/graph",
        "status": "implemented",
        "purpose": (
            "Navigate the derived memory knowledge graph around a memory id. "
            "Use it when a retrieved memory may need associative context, "
            "nearby memories, lifecycle links, facts, or session/entity "
            "connections beyond direct semantic search."
        ),
        "body_schema": {
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "string",
                    "description": "Memory id to use as graph root, for example mem_...",
                },
                "depth": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 3,
                    "default": 1,
                    "description": "Maximum graph hops to inspect from the memory root.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 30,
                    "description": "Maximum graph nodes/edges to return.",
                },
                "include_inactive": {
                    "type": "boolean",
                    "default": False,
                    "description": (
                        "When true, include inactive/deprecated graph nodes and "
                        "edges as inspectable history."
                    ),
                },
            },
            "required": ["memory_id"],
        },
        "examples": [
            {
                "method": "POST",
                "path": "/mind/memory/graph",
                "intent": "Inspect associative context around a retrieved memory.",
                "body": {"memory_id": "mem_example", "depth": 2, "limit": 30},
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
            "workspace notes, reflection, and previous-turn thinking "
            "retrospection are returned inside this result instead of separate "
            "cognitive endpoints."
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
                        "review_previous_turn",
                        "detect_reasoning_drift",
                        "explain_tool_choice",
                        "recover_open_loops",
                        "compare_answer_to_reasoning",
                        "extract_reasoning_digest",
                        "memory_from_reasoning",
                    ],
                    "default": "critic",
                    "description": (
                        "Reviewer stance. Use orient to frame a problem, critic "
                        "to find weaknesses, validator to check claims, planner "
                        "to plan work, synthesizer to combine evidence, empathy "
                        "for relational nuance, and memory_curator for memory "
                        "state review. Use review_previous_turn, "
                        "detect_reasoning_drift, explain_tool_choice, "
                        "recover_open_loops, compare_answer_to_reasoning, "
                        "extract_reasoning_digest, or memory_from_reasoning "
                        "when Scarlet needs controlled access to previous-turn "
                        "thinking as process evidence."
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
                "turn_scope": {
                    "type": "string",
                    "enum": ["none", "previous"],
                    "default": "none",
                    "description": (
                        "Which stored turn to package for retrospection. Use "
                        "previous to inspect the previous completed turn's user "
                        "message, final answer, public notes, tool calls, events, "
                        "and provider thinking. Retrospective modes default to "
                        "previous when this field is omitted."
                    ),
                },
                "detail": {
                    "type": "string",
                    "enum": ["digest", "excerpt", "raw"],
                    "default": "digest",
                    "description": (
                        "How much prior thinking to include in the internal "
                        "retrospection pack. Prefer digest for normal use, "
                        "excerpt for debugging drift, and raw only for explicit "
                        "deep inspection because it is token-heavy."
                    ),
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
                "reasoning_scope": "turn_scope",
                "reasoning_detail": "detail",
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
            },
            {
                "method": "POST",
                "path": "/mind/metacognition/step",
                "intent": "Retrospect previous thinking to detect drift before answering.",
                "body": {
                    "mode": "detect_reasoning_drift",
                    "objective": "Compare the previous turn's request, reasoning, tool actions, and final answer.",
                    "focus_question": "Did my final answer lose an important assumption or action from the previous reasoning?",
                    "turn_scope": "previous",
                    "detail": "digest",
                    "known_evidence": [
                        "User asked whether Scarlet can inspect prior reasoning."
                    ],
                },
            }
        ],
    },
    {
        "method": "POST",
        "path": "/mind/focus",
        "status": "implemented",
        "purpose": (
            "Manage Scarlet's current foreground focus as a profile-scoped "
            "attention state. Focus is separate from semantic memory and does "
            "not filter memory retrieval by default."
        ),
        "body_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "set",
                        "update",
                        "hold",
                        "shift",
                        "defer",
                        "resolve",
                        "impossible",
                        "read",
                        "list",
                        "search",
                        "timeline",
                    ],
                    "description": (
                        "Lifecycle operation. set creates or replaces the "
                        "active focus; shift intentionally moves from the "
                        "current focus to a new one; update/hold keep the same "
                        "focus; defer/resolve/impossible archive it; read/list/"
                        "search inspect active or historical focus records; "
                        "timeline inspects focus records and transition edges "
                        "as Scarlet's foreground-attention movement history."
                    ),
                },
                "focus_id": {
                    "type": ["string", "null"],
                    "description": (
                        "Optional focus id. Omit it for operations that target "
                        "the current active focus."
                    ),
                },
                "object": {
                    "type": ["string", "null"],
                    "description": (
                        "The thing Scarlet is intentionally holding in the "
                        "foreground. Required for set and shift."
                    ),
                },
                "type": {
                    "type": ["string", "null"],
                    "description": (
                        "Short natural focus category, such as conversation, "
                        "research, relationship, debugging, memory_review, "
                        "decision, or another precise free label."
                    ),
                },
                "intensity": {
                    "type": ["number", "null"],
                    "minimum": 0,
                    "maximum": 1,
                    "description": (
                        "How strongly this focus should remain foregrounded. "
                        "It is a focus-state value, not a memory score."
                    ),
                },
                "duration_policy": {
                    "type": ["string", "null"],
                    "description": (
                        "Natural duration hint such as this_turn, until_resolved, "
                        "until_interrupted, later_today, or another explicit policy."
                    ),
                },
                "reason": {
                    "type": ["string", "null"],
                    "description": (
                        "Why Scarlet is setting, holding, shifting, deferring, "
                        "or closing this focus."
                    ),
                },
                "resolution": {
                    "type": ["string", "null"],
                    "description": "Required for resolve unless reason explains the resolution.",
                },
                "impossible_reason": {
                    "type": ["string", "null"],
                    "description": (
                        "Required for impossible unless reason explains why "
                        "the focus cannot be completed now."
                    ),
                },
                "status": {
                    "type": ["string", "null"],
                    "enum": [
                        "active",
                        "held",
                        "deferred",
                        "resolved",
                        "impossible",
                        "superseded",
                        None,
                    ],
                    "description": "Optional list/search status filter.",
                },
                "query": {
                    "type": ["string", "null"],
                    "description": (
                        "Optional focus archive search phrase. This is simple "
                        "archive lookup, not semantic memory retrieval."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 10,
                    "description": "Maximum focus archive rows to return.",
                },
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Pagination offset for list/search.",
                },
                "metadata": {
                    "type": "object",
                    "default": {},
                    "description": (
                        "Optional compact debug metadata. Backend owns profile "
                        "id and source provenance."
                    ),
                },
            },
            "required": ["action"],
        },
        "examples": [
            {
                "method": "POST",
                "path": "/mind/focus",
                "intent": "Set Scarlet's current foreground focus.",
                "body": {
                    "action": "set",
                    "object": "Complete the focus organ design without touching memory retrieval.",
                    "type": "research",
                    "intensity": 0.75,
                    "duration_policy": "until_resolved",
                    "reason": "This is the thread Scarlet should keep foregrounded.",
                },
            },
            {
                "method": "POST",
                "path": "/mind/focus",
                "intent": "Resolve the active focus after finishing the thread.",
                "body": {
                    "action": "resolve",
                    "resolution": "The focus organ slice was completed and verified.",
                },
            },
            {
                "method": "POST",
                "path": "/mind/focus",
                "intent": "Inspect how Scarlet's foreground focus moved over time.",
                "body": {
                    "action": "timeline",
                    "limit": 10,
                },
            },
        ],
    },
    {
        "method": "POST",
        "path": "/mind/volition",
        "status": "implemented",
        "purpose": (
            "Manage Scarlet's latent self-generated intentions. Volition is "
            "separate from memory, focus, and tasks; normal active chat does "
            "not receive automatic intention retrieval in this first slice."
        ),
        "body_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "create",
                        "read",
                        "list_active",
                        "list_due",
                        "search",
                        "update",
                        "defer",
                        "review",
                        "promote_to_focus_candidate",
                        "resolve",
                        "mark_impossible",
                        "deprecate",
                    ],
                    "description": (
                        "Lifecycle operation. create stores a latent intention; "
                        "read/list_active/list_due/search inspect the register; "
                        "list_due returns open intentions whose review time has "
                        "arrived; update/defer/review maintain open intentions; "
                        "resolve/mark_impossible/deprecate close them; "
                        "promote_to_focus_candidate returns a /mind/focus "
                        "candidate without changing active focus."
                    ),
                },
                "intention_id": {
                    "type": ["string", "null"],
                    "description": (
                        "Target intention id. Required for read, update, defer, "
                        "review, promote_to_focus_candidate, resolve, "
                        "mark_impossible, and deprecate."
                    ),
                },
                "desire": {
                    "type": ["string", "null"],
                    "description": (
                        "The latent self-generated direction Scarlet wants to "
                        "keep alive. Required for create."
                    ),
                },
                "origin": {
                    "type": ["string", "null"],
                    "description": (
                        "Natural origin label such as scarlet, user_inspired, "
                        "metacognitive, session_close, or autonomous_cycle."
                    ),
                },
                "horizon": {
                    "type": ["string", "null"],
                    "description": (
                        "Natural time horizon such as this_session, later_today, "
                        "short_term, long_term, or open_ended."
                    ),
                },
                "intensity": {
                    "type": ["number", "null"],
                    "minimum": 0,
                    "maximum": 1,
                    "description": (
                        "How strongly the intention matters to Scarlet's "
                        "continuity. This is not a memory relevance score."
                    ),
                },
                "autonomy_level": {
                    "type": ["string", "null"],
                    "description": (
                        "How self-owned the intention is, such as "
                        "self_generated, user_influenced, maintenance_seeded, "
                        "or autonomous_cycle."
                    ),
                },
                "reason": {
                    "type": ["string", "null"],
                    "description": (
                        "Why this is a real internal direction rather than a "
                        "task, memory, or answer requirement. Required for "
                        "create and deprecate."
                    ),
                },
                "next_possible_reflection": {
                    "type": ["string", "null"],
                    "description": (
                        "Optional next internal reflection Scarlet or a future "
                        "autonomous cycle could run."
                    ),
                },
                "next_review_at": {
                    "type": ["string", "null"],
                    "description": "Optional ISO datetime for future review scheduling.",
                },
                "review_interval_seconds": {
                    "type": ["integer", "null"],
                    "minimum": 1,
                    "description": "Optional repeat-review interval hint.",
                },
                "resolution": {
                    "type": ["string", "null"],
                    "description": "Required for resolve unless reason explains closure.",
                },
                "impossible_reason": {
                    "type": ["string", "null"],
                    "description": (
                        "Required for mark_impossible unless reason explains "
                        "why the intention cannot continue."
                    ),
                },
                "status": {
                    "type": ["string", "null"],
                    "enum": [
                        "active",
                        "deferred",
                        "in_review",
                        "resolved",
                        "impossible",
                        "deprecated",
                        None,
                    ],
                    "description": (
                        "Optional status for search/update/review. Use "
                        "dedicated close actions for terminal statuses."
                    ),
                },
                "query": {
                    "type": ["string", "null"],
                    "description": (
                        "Optional archive search phrase. This is simple lookup, "
                        "not semantic memory retrieval."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 10,
                    "description": "Maximum intention rows to return.",
                },
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Pagination offset for list/search.",
                },
                "include_unscheduled": {
                    "type": "boolean",
                    "default": False,
                    "description": (
                        "Only for list_due. When true, also include open "
                        "intentions that do not yet have next_review_at, useful "
                        "for future autonomous cycles that want a fuller queue."
                    ),
                },
                "links": {
                    "type": "array",
                    "default": [],
                    "description": (
                        "Optional links to related internal evidence. Items use "
                        "target_type, target_id, relation, and optional metadata. "
                        "Use only when there is a real source link."
                    ),
                },
                "metadata": {
                    "type": "object",
                    "default": {},
                    "description": (
                        "Optional compact debug metadata. Backend owns profile "
                        "id and source provenance."
                    ),
                },
            },
            "required": ["action"],
        },
        "examples": [
            {
                "method": "POST",
                "path": "/mind/volition",
                "intent": "Store a latent internal intention.",
                "body": {
                    "action": "create",
                    "desire": "Understand whether my public notes help the owner follow my internal work without making simple chats heavy.",
                    "origin": "scarlet",
                    "horizon": "short_term",
                    "intensity": 0.68,
                    "autonomy_level": "self_generated",
                    "reason": "This is an internal research direction about my own behavior, not a user task.",
                    "next_possible_reflection": "Review future chats where notes either helped or became too verbose.",
                },
            },
            {
                "method": "POST",
                "path": "/mind/volition",
                "intent": "Inspect open latent intentions.",
                "body": {
                    "action": "list_active",
                    "limit": 5,
                },
            },
            {
                "method": "POST",
                "path": "/mind/volition",
                "intent": "Inspect intentions whose review moment has arrived.",
                "body": {
                    "action": "list_due",
                    "limit": 5,
                    "include_unscheduled": False,
                },
            },
            {
                "method": "POST",
                "path": "/mind/volition",
                "intent": "Convert an intention into a focus candidate without applying it automatically.",
                "body": {
                    "action": "promote_to_focus_candidate",
                    "intention_id": "intent_example",
                    "reason": "This latent direction is now relevant enough to become foreground attention.",
                },
            },
        ],
    },
    {
        "method": "POST",
        "path": "/mind/mode",
        "status": "implemented",
        "purpose": (
            "Inspect Scarlet's current agent-only operating posture, list the "
            "mode registry, or persist the posture that resumes outside a "
            "system-enforced human interaction. Background maintenance and "
            "Dream are not agent modes."
        ),
        "body_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "list", "set"],
                },
                "mode": {
                    "type": ["string", "null"],
                    "enum": ["idle", "interactive", "scouting", None],
                },
                "reason": {"type": ["string", "null"]},
            },
            "required": ["action"],
        },
        "examples": [
            {
                "method": "POST",
                "path": "/mind/mode",
                "intent": "Inspect Scarlet's current operating posture.",
                "body": {"action": "read"},
            },
            {
                "method": "POST",
                "path": "/mind/mode",
                "intent": "Keep scouting as the posture to resume after this exchange.",
                "body": {
                    "action": "set",
                    "mode": "scouting",
                    "reason": "Continue studying the environment after the conversation.",
                },
            },
        ],
    },
    {
        "method": "POST",
        "path": "/mind/perception",
        "status": "implemented",
        "purpose": (
            "Inspect the perception availability index, open unread events from "
            "one channel, or read one source-labelled observation."
        ),
        "body_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "open", "read"],
                },
                "channel": {"type": ["string", "null"]},
                "event_id": {"type": ["string", "null"]},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "required": ["action"],
        },
        "examples": [
            {
                "method": "POST",
                "path": "/mind/perception",
                "intent": "See which sensory channels have new evidence.",
                "body": {"action": "status"},
            },
            {
                "method": "POST",
                "path": "/mind/perception",
                "intent": "Inspect recent notification observations.",
                "body": {
                    "action": "open",
                    "channel": "notifications",
                    "limit": 10,
                },
            },
        ],
    },
    {
        "method": "POST",
        "path": "/mind/affect",
        "status": "implemented",
        "purpose": (
            "Inspect Scarlet's backend-appraised affect state and affective "
            "prototypes. Affect is read-only from Mind API: Scarlet can read "
            "what the backend appraised, but cannot choose or mutate emotions "
            "through this endpoint."
        ),
        "body_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "list", "prototypes"],
                    "description": (
                        "read returns the latest or targeted affect state; list "
                        "returns affect history with optional filters; "
                        "prototypes returns the backend emotion prototypes."
                    ),
                },
                "affect_id": {
                    "type": ["string", "null"],
                    "description": (
                        "Optional affect state id for read. Omit it to read "
                        "the latest stored state for Scarlet's profile."
                    ),
                },
                "emotion": {
                    "type": ["string", "null"],
                    "description": (
                        "Optional list filter, such as curiosity, tenderness, "
                        "frustration, caution, relief, enthusiasm, or sadness."
                    ),
                },
                "mode": {
                    "type": ["string", "null"],
                    "description": (
                        "Optional list filter for appraisal mode, usually "
                        "shadow or model."
                    ),
                },
                "status": {
                    "type": ["string", "null"],
                    "description": "Optional list/read filter for affect lifecycle status.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 10,
                    "description": "Maximum affect states to return for list.",
                },
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Pagination offset for list.",
                },
            },
            "required": ["action"],
        },
        "examples": [
            {
                "method": "POST",
                "path": "/mind/affect",
                "intent": "Inspect Scarlet's current backend-appraised affective state.",
                "body": {
                    "action": "read",
                },
            },
            {
                "method": "POST",
                "path": "/mind/affect",
                "intent": "Inspect recent frustration states for calibration.",
                "body": {
                    "action": "list",
                    "emotion": "frustration",
                    "limit": 5,
                },
            },
            {
                "method": "POST",
                "path": "/mind/affect",
                "intent": "Inspect the backend affect prototypes.",
                "body": {
                    "action": "prototypes",
                },
            },
        ],
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


def build_mind_shell_catalog() -> dict[str, Any]:
    catalog = _shell_catalog_without_digest()
    catalog["schema_digest"] = compute_shell_schema_digest(catalog)
    return catalog


def _shell_catalog_without_digest() -> dict[str, Any]:
    return {
        "schema_version": MIND_SHELL_SCHEMA_VERSION,
        "tool": MIND_SHELL_TOOL_SCHEMA,
        "commands": deepcopy(MIND_SHELL_COMMANDS),
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
        "shell_policy": {
            "source_of_truth": "help",
            "role": (
                "Capability catalog for Scarlet's internal command shell. "
                "Commands are the model-facing language; endpoint paths are "
                "legacy backend details."
            ),
            "use_when": [
                "discovering available cognitive command families",
                "recovering after invalid command syntax",
                "checking concise examples before state-changing operations",
            ],
            "prompt_policy": (
                "The prompt teaches when to use cognition; the shell returns "
                "the current command catalog, examples, and recoverable "
                "usage guidance."
            ),
        },
    }


def compute_shell_schema_digest(catalog: dict[str, Any] | None = None) -> str:
    source = catalog or _shell_catalog_without_digest()
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


def shell_metadata() -> dict[str, str]:
    return {
        "schema_version": MIND_SHELL_SCHEMA_VERSION,
        "schema_digest": compute_shell_schema_digest(),
        "schema_command": "help",
    }


def shell_command_catalog(namespace: str | None = None) -> list[dict[str, Any]]:
    if namespace is None:
        return deepcopy(MIND_SHELL_COMMANDS)
    normalized = namespace.strip().casefold().replace("_", "-")
    return [
        deepcopy(item)
        for item in MIND_SHELL_COMMANDS
        if str(item.get("namespace", "")).casefold().replace("_", "-") == normalized
    ]


def shell_command_usage_guide(namespace: str | None = None) -> dict[str, Any]:
    commands = shell_command_catalog(namespace)
    if not commands and namespace is not None:
        commands = shell_command_catalog()
    return {
        "schema_version": MIND_SHELL_SCHEMA_VERSION,
        "schema_digest": compute_shell_schema_digest(),
        "requested_namespace": namespace,
        "commands": commands,
        "retry_guidance": (
            "Use one concise command string. Quote natural-language content "
            "with spaces. Use help or help <namespace> when unsure."
        ),
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
