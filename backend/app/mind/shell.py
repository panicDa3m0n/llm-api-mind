import json
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.mind.command_registry import canonical_command_action, validate_shell_command
from app.mind.contracts import MindAPIContext
from app.mind.dispatcher import MindAPIRequest, MindAPIResponse
from app.mind.schema import MIND_SHELL_TOOL_SCHEMA
from app.mind.shell_parsing import (
    ParsedCommand,
    ShellParseError,
    copy_flags as _copy_flags,
    first_arg_or_flag as _first_arg_or_flag,
    flag_bool as _flag_bool,
    flag_float as _flag_float,
    flag_int as _flag_int,
    flag_string as _flag_string,
    flag_values as _flag_values,
    joined_args as _joined_args,
    normalize_token as _normalize_token,
    parse_command as _parse_command,
    time_filter as _time_filter,
)
from app.mind.shell_presentation import (
    dispatch_api_as_shell as _dispatch_api_as_shell,
    help_response as _help_response,
    shell_error as _shell_error,
)


class MindShellRequest(BaseModel):
    command: str = Field(min_length=1, max_length=4000)
    intent: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="before")
    @classmethod
    def normalize_model_tool_input(cls, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return {"command": value}
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        raw_input = normalized.get("raw_input")
        if isinstance(raw_input, str):
            try:
                raw_input = json.loads(raw_input)
            except json.JSONDecodeError:
                raw_input = {"command": raw_input}
        if isinstance(raw_input, dict):
            unwrapped = dict(raw_input)
            for key, item in normalized.items():
                if key != "raw_input" and key not in unwrapped:
                    unwrapped[key] = item
            normalized = unwrapped

        if "command" not in normalized:
            for alias in ("cmd", "input", "query"):
                if alias in normalized:
                    normalized["command"] = normalized.pop(alias)
                    break
        return normalized


def dispatch_mind_shell(
    request: MindShellRequest,
    context: MindAPIContext | None = None,
) -> MindAPIResponse:
    try:
        parsed = _parse_command(request.command)
    except ShellParseError as exc:
        return _shell_error(
            code=exc.code,
            message=exc.message,
            parsed=None,
            namespace=None,
            actions=exc.actions,
        )
    intent = request.intent or _default_intent(parsed)

    if parsed.namespace in {"help", "?", "schema", "capabilities"}:
        return _help_response(parsed)

    if parsed.namespace in {"memory", "mem", "remember"}:
        return _memory_command(parsed, context=context, intent=intent)
    if parsed.namespace in {"session", "sessions", "episodic"}:
        return _session_command(parsed, context=context, intent=intent)
    if parsed.namespace in {"focus", "attention"}:
        return _focus_command(parsed, context=context, intent=intent)
    if parsed.namespace in {"volition", "intention", "intentions"}:
        return _volition_command(parsed, context=context, intent=intent)
    if parsed.namespace in {"affect", "emotion", "emotions"}:
        return _affect_command(parsed, context=context, intent=intent)
    if parsed.namespace in {"mode", "operating-mode"}:
        return _mode_command(parsed, context=context, intent=intent)
    if parsed.namespace in {"perception", "sense", "senses", "sensor"}:
        return _perception_command(parsed, context=context, intent=intent)
    if parsed.namespace in {"episode", "episodes", "inquiry", "inquiries"}:
        return _episode_command(parsed, context=context, intent=intent)
    if parsed.namespace in {"lab", "research", "research-lab"}:
        return _research_lab_command(parsed, context=context, intent=intent)
    if parsed.namespace in {"metacognition", "meta", "reflect"}:
        return _metacognition_command(parsed, context=context, intent=intent)

    return _shell_error(
        code="shell.unknown_namespace",
        message=f"Unknown mind shell namespace: {parsed.namespace}",
        parsed=parsed,
        namespace=None,
        actions=["help", "help memory", "help session", "help mode"],
    )


def _memory_command(
    parsed: ParsedCommand,
    *,
    context: MindAPIContext | None,
    intent: str,
) -> MindAPIResponse:
    action = parsed.action or "search"
    if action in {"search", "find"}:
        query = _joined_args(parsed) or _flag_string(parsed, "query", "q")
        if not query:
            return _shell_error(
                code="shell.memory_search_missing_query",
                message="memory search requires a natural-language query.",
                parsed=parsed,
                namespace="memory",
                actions=['memory search "what to find" --top 5'],
            )
        body: dict[str, Any] = {
            "query": query,
            "top_k": _flag_int(parsed, 5, "top", "top-k", "limit"),
        }
        scope = _flag_string(parsed, "scope")
        if scope is not None:
            body["scope"] = scope
        memory_type = _flag_values(parsed, "type", "types")
        if memory_type:
            body["types"] = memory_type
        time_filter = _time_filter(parsed, default_basis="source_conversation")
        if time_filter is not None:
            body["time"] = time_filter
        if _flag_bool(parsed, False, "include-low-confidence", "low-confidence"):
            body["include_low_confidence"] = True
        return _dispatch_api_as_shell(
            parsed,
            target="memory.search",
            api_request=MindAPIRequest(
                method="POST",
                path="/mind/memory/search",
                body=body,
                intent=intent,
            ),
            context=context,
        )
    if action in {"write", "save", "store"}:
        content = _flag_string(parsed, "content") or _joined_args(parsed)
        memory_type = _flag_string(parsed, "type")
        reason = _flag_string(parsed, "reason", "why")
        missing = [
            name
            for name, value in {
                "--type": memory_type,
                "--content": content,
                "--reason": reason,
            }.items()
            if not value
        ]
        if missing:
            return _shell_error(
                code="shell.memory_write_missing_fields",
                message="memory write needs type, content, and reason.",
                parsed=parsed,
                namespace="memory",
                actions=[
                    'memory write --type user_preference --scope user --content "..." --reason "..."',
                    "help memory",
                ],
                details={"missing": missing},
            )
        body = {
            "type": memory_type,
            "content": content,
            "reason_for_storage": reason,
        }
        future_use = _flag_string(parsed, "future-use", "future", "expected-future-use")
        if future_use is not None:
            body["expected_future_use"] = future_use
        scope = _flag_string(parsed, "scope")
        if scope is not None:
            body["scope"] = scope
        return _dispatch_api_as_shell(
            parsed,
            target="memory.write",
            api_request=MindAPIRequest(
                method="POST",
                path="/mind/memory/write",
                body=body,
                intent=intent,
            ),
            context=context,
        )
    if action in {"open", "read", "inspect", "show", "get"}:
        memory_id = _first_arg_or_flag(parsed, "id", "memory-id")
        if not memory_id:
            return _shell_error(
                code="shell.memory_open_missing_id",
                message="memory open requires a memory id.",
                parsed=parsed,
                namespace="memory",
                actions=["memory open mem_..."],
            )
        return _dispatch_api_as_shell(
            parsed,
            target="memory.open",
            api_request=MindAPIRequest(
                method="GET",
                path=f"/mind/memory/{memory_id}",
                body={},
                intent=intent,
            ),
            context=context,
        )
    if action == "graph":
        memory_id = _first_arg_or_flag(parsed, "id", "memory-id")
        if not memory_id:
            return _shell_error(
                code="shell.memory_graph_missing_id",
                message="memory graph requires a memory id.",
                parsed=parsed,
                namespace="memory",
                actions=["memory graph mem_... --depth 2"],
            )
        return _dispatch_api_as_shell(
            parsed,
            target="memory.graph",
            api_request=MindAPIRequest(
                method="POST",
                path="/mind/memory/graph",
                body={
                    "memory_id": memory_id,
                    "depth": _flag_int(parsed, 1, "depth", "hops"),
                    "limit": _flag_int(parsed, 30, "limit", "top"),
                    "include_inactive": _flag_bool(parsed, False, "include-inactive"),
                },
                intent=intent,
            ),
            context=context,
        )
    if action == "facts":
        body: dict[str, Any] = {
            "include_inactive": _flag_bool(parsed, False, "include-inactive"),
        }
        for key, flag_names in {
            "memory_id": ("memory-id", "id"),
            "entity": ("entity",),
            "predicate": ("predicate",),
            "query": ("query", "q"),
            "status": ("status",),
        }.items():
            value = _flag_string(parsed, *flag_names)
            if value is not None:
                body[key] = value
        if "query" not in body and parsed.args:
            body["query"] = _joined_args(parsed)
        return _dispatch_api_as_shell(
            parsed,
            target="memory.facts",
            api_request=MindAPIRequest(
                method="GET",
                path="/mind/memory/facts",
                body=body,
                intent=intent,
            ),
            context=context,
        )
    if action == "proposals":
        return _dispatch_api_as_shell(
            parsed,
            target="memory.proposals.list",
            api_request=MindAPIRequest(
                method="GET",
                path="/mind/memory/proposals",
                body={
                    "status": _flag_string(parsed, "status") or "open",
                    "limit": _flag_int(parsed, 10, "limit", "top"),
                    "offset": _flag_int(parsed, 0, "offset"),
                },
                intent=intent,
            ),
            context=context,
        )
    if action == "proposal":
        proposal_id = _first_arg_or_flag(parsed, "id", "proposal-id")
        if not proposal_id:
            return _shell_error(
                code="shell.memory_proposal_missing_id",
                message="memory proposal requires a proposal id.",
                parsed=parsed,
                namespace="memory",
                actions=["memory proposals --status open --limit 10"],
            )
        return _dispatch_api_as_shell(
            parsed,
            target="memory.proposal.read",
            api_request=MindAPIRequest(
                method="GET",
                path=f"/mind/memory/proposals/{proposal_id}",
                body={},
                intent=intent,
            ),
            context=context,
        )
    if action in {
        "proposal-accept",
        "proposal-reject",
        "proposal-duplicate",
        "proposal-supersede",
    }:
        proposal_id = parsed.args[0] if parsed.args else _flag_string(
            parsed,
            "id",
            "proposal-id",
        )
        target_memory_id = (
            parsed.args[1]
            if len(parsed.args) >= 2
            else _flag_string(parsed, "target", "memory-id")
        )
        reason = _flag_string(parsed, "reason", "why")
        if not proposal_id or not reason:
            return _shell_error(
                code="shell.memory_proposal_decision_missing_fields",
                message=(
                    f"memory {action} requires a proposal id and reason."
                ),
                parsed=parsed,
                namespace="memory",
                actions=[f'memory {action} prop_... --reason "..."'],
            )
        decision = action.removeprefix("proposal-")
        if decision in {"duplicate", "supersede"} and not target_memory_id:
            return _shell_error(
                code="shell.memory_proposal_target_missing",
                message=(
                    f"memory {action} requires a target memory id selected "
                    "after source inspection."
                ),
                parsed=parsed,
                namespace="memory",
                actions=[
                    f'memory {action} prop_... mem_... --reason "..."'
                ],
            )
        body = {
            "proposal_id": proposal_id,
            "decision": decision,
            "reason": reason,
        }
        if target_memory_id is not None:
            body["target_memory_id"] = target_memory_id
        _copy_flags(
            parsed,
            body,
            {
                "type": ("type",),
                "scope": ("scope",),
                "content": ("content",),
                "expected_future_use": ("future-use", "expected-future-use"),
            },
        )
        return _dispatch_api_as_shell(
            parsed,
            target="memory.proposal.decide",
            api_request=MindAPIRequest(
                method="POST",
                path="/mind/memory/proposals/decide",
                body=body,
                intent=intent,
            ),
            context=context,
        )
    if action == "conflicts":
        return _dispatch_api_as_shell(
            parsed,
            target="memory.conflicts",
            api_request=MindAPIRequest(
                method="GET",
                path="/mind/memory/conflicts",
                body={},
                intent=intent,
            ),
            context=context,
        )
    if action == "deprecate":
        memory_id = _first_arg_or_flag(parsed, "id", "memory-id")
        reason = _flag_string(parsed, "reason", "why")
        if not memory_id or not reason:
            return _shell_error(
                code="shell.memory_deprecate_missing_fields",
                message="memory deprecate requires memory id and reason.",
                parsed=parsed,
                namespace="memory",
                actions=['memory deprecate mem_... --reason "..."'],
            )
        return _dispatch_api_as_shell(
            parsed,
            target="memory.deprecate",
            api_request=MindAPIRequest(
                method="POST",
                path="/mind/memory/deprecate",
                body={"memory_id": memory_id, "reason": reason},
                intent=intent,
            ),
            context=context,
        )
    if action == "supersede":
        old_memory_id = parsed.args[0] if len(parsed.args) >= 1 else _flag_string(parsed, "old")
        new_memory_id = parsed.args[1] if len(parsed.args) >= 2 else _flag_string(parsed, "new")
        reason = _flag_string(parsed, "reason", "why")
        if not old_memory_id or not new_memory_id or not reason:
            return _shell_error(
                code="shell.memory_supersede_missing_fields",
                message="memory supersede requires old id, new id, and reason.",
                parsed=parsed,
                namespace="memory",
                actions=['memory supersede mem_old mem_new --reason "..."'],
            )
        return _dispatch_api_as_shell(
            parsed,
            target="memory.supersede",
            api_request=MindAPIRequest(
                method="POST",
                path="/mind/memory/supersede",
                body={
                    "old_memory_id": old_memory_id,
                    "new_memory_id": new_memory_id,
                    "reason": reason,
                    "deprecate_old": not _flag_bool(parsed, False, "keep-old-active"),
                },
                intent=intent,
            ),
            context=context,
        )
    validation = validate_shell_command(parsed.raw)
    if validation.get("schema_status") in {"unavailable_by_design", "planned"}:
        suggested = validation.get("suggested_action") or "help memory"
        return _shell_error(
            code="shell.memory_action_unavailable",
            message=(
                f"Memory action '{action}' is "
                f"{validation.get('schema_status')} in the current Mind shell."
            ),
            parsed=parsed,
            namespace="memory",
            actions=[str(suggested), "help memory"],
            details={"command_validation": validation},
        )
    return _shell_error(
        code="shell.memory_unknown_action",
        message=f"Unknown memory action: {action}",
        parsed=parsed,
        namespace="memory",
        actions=["help memory"],
    )


def _session_command(
    parsed: ParsedCommand,
    *,
    context: MindAPIContext | None,
    intent: str,
) -> MindAPIResponse:
    action = parsed.action or "list"
    if action in {"list", "search", "find"}:
        body: dict[str, Any] = {
            "limit": _flag_int(parsed, 10, "limit", "top"),
            "offset": _flag_int(parsed, 0, "offset"),
        }
        query = _flag_string(parsed, "query", "q") or _joined_args(parsed)
        if query:
            body["query"] = query
        time_filter = _time_filter(parsed, default_basis="conversation")
        if time_filter is not None:
            body["time"] = time_filter
        return _dispatch_api_as_shell(
            parsed,
            target="session.list",
            api_request=MindAPIRequest(
                method="GET",
                path="/mind/sessions",
                body=body,
                intent=intent,
            ),
            context=context,
        )
    if action in {"open", "read", "inspect", "show", "get"}:
        session_id = _first_arg_or_flag(parsed, "id", "session-id")
        if not session_id:
            return _shell_error(
                code="shell.session_open_missing_id",
                message="session open requires a session id.",
                parsed=parsed,
                namespace="session",
                actions=["session open ses_... --limit 200"],
            )
        body = {
            "include_messages": not _flag_bool(parsed, False, "summary-only"),
            "include_memories": not _flag_bool(parsed, False, "no-memories"),
        }
        limit = _flag_int(parsed, 0, "limit", "message-limit")
        if limit > 0:
            body["message_limit"] = limit
        return _dispatch_api_as_shell(
            parsed,
            target="session.open",
            api_request=MindAPIRequest(
                method="GET",
                path=f"/mind/sessions/{session_id}",
                body=body,
                intent=intent,
            ),
            context=context,
        )
    if action == "message":
        message_id = _first_arg_or_flag(parsed, "id", "message-id")
        if not message_id:
            return _shell_error(
                code="shell.session_message_missing_id",
                message="session message requires a message id.",
                parsed=parsed,
                namespace="session",
                actions=["session message msg_..."],
            )
        return _dispatch_api_as_shell(
            parsed,
            target="session.message",
            api_request=MindAPIRequest(
                method="GET",
                path=f"/mind/sessions/messages/{message_id}",
                intent=intent,
            ),
            context=context,
        )
    if action == "turn":
        turn_id = _first_arg_or_flag(parsed, "id", "turn-id")
        if not turn_id:
            return _shell_error(
                code="shell.session_turn_missing_id",
                message="session turn requires a turn id.",
                parsed=parsed,
                namespace="session",
                actions=["session turn turn_..."],
            )
        return _dispatch_api_as_shell(
            parsed,
            target="session.turn",
            api_request=MindAPIRequest(
                method="GET",
                path=f"/mind/sessions/turns/{turn_id}",
                intent=intent,
            ),
            context=context,
        )
    if action == "summarize":
        session_id = _first_arg_or_flag(parsed, "id", "session-id")
        if not session_id:
            return _shell_error(
                code="shell.session_summarize_missing_id",
                message="session summarize requires a session id.",
                parsed=parsed,
                namespace="session",
                actions=["session summarize ses_... --force"],
            )
        return _dispatch_api_as_shell(
            parsed,
            target="session.summarize",
            api_request=MindAPIRequest(
                method="POST",
                path=f"/mind/sessions/{session_id}/summarize",
                body={
                    "force": _flag_bool(parsed, False, "force"),
                    "focus": _flag_string(parsed, "focus"),
                },
                intent=intent,
            ),
            context=context,
        )
    return _shell_error(
        code="shell.session_unknown_action",
        message=f"Unknown session action: {action}",
        parsed=parsed,
        namespace="session",
        actions=["help session"],
    )


def _focus_command(
    parsed: ParsedCommand,
    *,
    context: MindAPIContext | None,
    intent: str,
) -> MindAPIResponse:
    action = parsed.action or "read"
    action = {"open": "read", "inspect": "read", "show": "read", "get": "read", "current": "read"}.get(action, action)
    if action in {"set", "shift"}:
        focus_object = _joined_args(parsed) or _flag_string(parsed, "object")
        if not focus_object:
            return _shell_error(
                code="shell.focus_missing_object",
                message=f"focus {action} requires an object.",
                parsed=parsed,
                namespace="focus",
                actions=[f'focus {action} "what Scarlet is holding" --reason "..."'],
            )
        body: dict[str, Any] = {
            "action": action,
            "object": focus_object,
            "reason": _flag_string(parsed, "reason", "why") or intent,
        }
        source_intention_id = _flag_string(parsed, "source-intention-id")
        if source_intention_id is not None:
            body["metadata"] = {
                "source_intention_id": source_intention_id,
                "source_intention_status": _flag_string(
                    parsed,
                    "source-intention-status",
                ),
            }
    else:
        body = {"action": action}
    _copy_flags(
        parsed,
        body,
        {
            "focus_id": ("id", "focus-id"),
            "object": ("object",),
            "type": ("type",),
            "duration_policy": ("duration", "duration-policy"),
            "reason": ("reason", "why"),
            "resolution": ("resolution",),
            "impossible_reason": ("impossible-reason", "reason"),
            "status": ("status",),
            "query": ("query", "q"),
        },
    )
    if parsed.args and action in {"update", "hold", "defer", "resolve", "impossible"}:
        body.setdefault("focus_id", parsed.args[0])
    if action in {"list", "search", "timeline"}:
        body["limit"] = _flag_int(parsed, 10, "limit", "top")
        body["offset"] = _flag_int(parsed, 0, "offset")
        if action == "search" and "query" not in body:
            body["query"] = _joined_args(parsed)
        if action == "search" and not body.get("query"):
            return _shell_error(
                code="shell.focus_search_missing_query",
                message="focus search requires a query.",
                parsed=parsed,
                namespace="focus",
                actions=['focus search "query" --limit 10'],
            )
    intensity = _flag_float(parsed, None, "intensity")
    if intensity is not None:
        body["intensity"] = intensity
    return _dispatch_api_as_shell(
        parsed,
        target=f"focus.{action}",
        api_request=MindAPIRequest(
            method="POST",
            path="/mind/focus",
            body=body,
            intent=intent,
        ),
        context=context,
    )


def _volition_command(
    parsed: ParsedCommand,
    *,
    context: MindAPIContext | None,
    intent: str,
) -> MindAPIResponse:
    action = parsed.action or "list_active"
    if action == "list":
        list_kind = _normalize_token(parsed.args[0]) if parsed.args else "active"
        if list_kind in {"active", "open"}:
            action = "list_active"
            parsed = ParsedCommand(
                parsed.raw,
                parsed.namespace,
                parsed.action,
                parsed.args[1:] if parsed.args else [],
                parsed.flags,
            )
        elif list_kind in {"due", "review"}:
            action = "list_due"
            parsed = ParsedCommand(
                parsed.raw,
                parsed.namespace,
                parsed.action,
                parsed.args[1:],
                parsed.flags,
            )
    action = {
        "list-active": "list_active",
        "list_active": "list_active",
        "list-due": "list_due",
        "list_due": "list_due",
        "open": "read",
        "show": "read",
        "get": "read",
        "promote": "promote_to_focus_candidate",
        "promote-to-focus-candidate": "promote_to_focus_candidate",
        "impossible": "mark_impossible",
        "mark-impossible": "mark_impossible",
    }.get(action, action)
    body: dict[str, Any] = {"action": action}
    if action == "create":
        desire = _joined_args(parsed) or _flag_string(parsed, "desire")
        reason = _flag_string(parsed, "reason", "why")
        if not desire or not reason:
            return _shell_error(
                code="shell.volition_create_missing_fields",
                message="volition create requires desire and reason.",
                parsed=parsed,
                namespace="volition",
                actions=['volition create "what I want to keep exploring" --reason "..."'],
            )
        body["desire"] = desire
        body["reason"] = reason
    elif action in {
        "read",
        "update",
        "defer",
        "review",
        "promote_to_focus_candidate",
        "resolve",
        "mark_impossible",
        "deprecate",
    }:
        intention_id = _first_arg_or_flag(parsed, "id", "intention-id")
        if not intention_id:
            return _shell_error(
                code="shell.volition_missing_id",
                message=f"volition {action} requires an intention id.",
                parsed=parsed,
                namespace="volition",
                actions=["volition read int_..."],
            )
        body["intention_id"] = intention_id
    elif action in {"search", "list_active", "list_due"}:
        body["limit"] = _flag_int(parsed, 10, "limit", "top")
        body["offset"] = _flag_int(parsed, 0, "offset")
        if action == "search":
            body["query"] = _joined_args(parsed) or _flag_string(parsed, "query", "q")
            if not body["query"]:
                return _shell_error(
                    code="shell.volition_search_missing_query",
                    message="volition search requires a query.",
                    parsed=parsed,
                    namespace="volition",
                    actions=['volition search "query" --limit 10'],
                )
        if action == "list_due":
            body["include_unscheduled"] = _flag_bool(parsed, False, "include-unscheduled")
    _copy_flags(
        parsed,
        body,
        {
            "origin": ("origin",),
            "horizon": ("horizon",),
            "autonomy_level": ("autonomy", "autonomy-level"),
            "reason": ("reason", "why"),
            "next_possible_reflection": ("next-reflection",),
            "next_review_at": ("next-review-at",),
            "resolution": ("resolution",),
            "impossible_reason": ("impossible-reason", "reason"),
            "status": ("status",),
            "query": ("query", "q"),
        },
    )
    intensity = _flag_float(parsed, None, "intensity")
    if intensity is not None:
        body["intensity"] = intensity
    raw_review_interval = _flag_string(parsed, "review-interval-seconds")
    if raw_review_interval is not None:
        try:
            body["review_interval_seconds"] = int(raw_review_interval)
        except ValueError:
            return _shell_error(
                code="shell.volition_invalid_review_interval",
                message="review interval must be an integer number of seconds.",
                parsed=parsed,
                namespace="volition",
                actions=["Use --review-interval-seconds 3600"],
            )
    candidate_id = _flag_string(parsed, "candidate-id")
    if candidate_id is not None and action in {"create", "update", "review"}:
        body["links"] = [
            {
                "target_type": "candidate",
                "target_id": candidate_id,
                "relation": "endorsed_from",
            }
        ]
    return _dispatch_api_as_shell(
        parsed,
        target=f"volition.{action}",
        api_request=MindAPIRequest(
            method="POST",
            path="/mind/volition",
            body=body,
            intent=intent,
        ),
        context=context,
    )


def _affect_command(
    parsed: ParsedCommand,
    *,
    context: MindAPIContext | None,
    intent: str,
) -> MindAPIResponse:
    action = parsed.action or "read"
    body: dict[str, Any] = {
        "action": {
            "history": "list",
            "states": "list",
            "show": "read",
            "get": "read",
            "current": "read",
        }.get(action, action)
    }
    _copy_flags(
        parsed,
        body,
        {
            "affect_id": ("id", "affect-id"),
            "emotion": ("emotion",),
            "mode": ("mode",),
            "status": ("status",),
        },
    )
    body["limit"] = _flag_int(parsed, 10, "limit", "top")
    body["offset"] = _flag_int(parsed, 0, "offset")
    return _dispatch_api_as_shell(
        parsed,
        target=f"affect.{body['action']}",
        api_request=MindAPIRequest(
            method="POST",
            path="/mind/affect",
            body=body,
            intent=intent,
        ),
        context=context,
    )


def _mode_command(
    parsed: ParsedCommand,
    *,
    context: MindAPIContext | None,
    intent: str,
) -> MindAPIResponse:
    action = parsed.action or "read"
    action = {"show": "read", "get": "read", "current": "read"}.get(action, action)
    body: dict[str, Any] = {"action": action}
    if action == "set":
        mode = _first_arg_or_flag(parsed, "mode", "tag")
        reason = _flag_string(parsed, "reason", "why")
        if not mode or not reason:
            return _shell_error(
                code="shell.mode_set_missing_fields",
                message="mode set requires a mode tag and reason.",
                parsed=parsed,
                namespace="mode",
                actions=['mode set idle --reason "..."', 'mode set scouting --reason "..."'],
            )
        body.update({"mode": mode, "reason": reason})
    return _dispatch_api_as_shell(
        parsed,
        target=f"mode.{action}",
        api_request=MindAPIRequest(
            method="POST",
            path="/mind/mode",
            body=body,
            intent=intent,
        ),
        context=context,
    )


def _metacognition_command(
    parsed: ParsedCommand,
    *,
    context: MindAPIContext | None,
    intent: str,
) -> MindAPIResponse:
    action = parsed.action or "step"
    if action != "step":
        return _shell_error(
            code="shell.metacognition_unknown_action",
            message="metacognition currently supports only step.",
            parsed=parsed,
            namespace="metacognition",
            actions=["help metacognition"],
        )
    objective = _flag_string(parsed, "objective") or _joined_args(parsed)
    if not objective:
        return _shell_error(
            code="shell.metacognition_missing_objective",
            message="metacognition step requires an objective.",
            parsed=parsed,
            namespace="metacognition",
            actions=['metacognition step --objective "what to review" --mode critic'],
        )
    body: dict[str, Any] = {
        "objective": objective,
        "mode": _flag_string(parsed, "mode") or "critic",
        "known_evidence": _flag_values(parsed, "evidence", "known-evidence"),
        "uncertainties": _flag_values(parsed, "uncertainty", "uncertainties"),
        "max_findings": _flag_int(parsed, 6, "max-findings", "limit"),
    }
    _copy_flags(
        parsed,
        body,
        {
            "focus_question": ("question", "focus-question"),
            "internal_prompt": ("prompt", "internal-prompt"),
            "draft_answer": ("draft", "draft-answer"),
            "turn_scope": ("turn-scope", "reasoning-scope"),
            "detail": ("detail", "reasoning-detail"),
        },
    )
    return _dispatch_api_as_shell(
        parsed,
        target="metacognition.step",
        api_request=MindAPIRequest(
            method="POST",
            path="/mind/metacognition/step",
            body=body,
            intent=intent,
        ),
        context=context,
    )


def _perception_command(
    parsed: ParsedCommand,
    *,
    context: MindAPIContext | None,
    intent: str,
) -> MindAPIResponse:
    action = parsed.action or "status"
    action = {
        "list": "status",
        "available": "status",
        "show": "read",
        "get": "read",
        "inspect": "read",
    }.get(action, action)
    body: dict[str, Any] = {"action": action}
    if action == "open":
        channel = _first_arg_or_flag(parsed, "channel")
        if not channel:
            return _shell_error(
                code="shell.perception_channel_required",
                message="perception open requires a channel.",
                parsed=parsed,
                namespace="perception",
                actions=["perception status", "perception open notifications --limit 10"],
            )
        body["channel"] = channel
        body["limit"] = _flag_int(parsed, 10, "limit", "top")
    elif action == "read":
        event_id = _first_arg_or_flag(parsed, "id", "event-id")
        if not event_id:
            return _shell_error(
                code="shell.perception_event_required",
                message="perception read requires an event id.",
                parsed=parsed,
                namespace="perception",
                actions=["perception read per_..."],
            )
        body["event_id"] = event_id
    return _dispatch_api_as_shell(
        parsed,
        target=f"perception.{action}",
        api_request=MindAPIRequest(
            method="POST",
            path="/mind/perception",
            body=body,
            intent=intent,
        ),
        context=context,
    )


def _research_lab_command(
    parsed: ParsedCommand,
    *,
    context: MindAPIContext | None,
    intent: str,
) -> MindAPIResponse:
    action = canonical_command_action("lab", parsed.action) or parsed.action or "status"
    body: dict[str, Any] = {"action": action.replace("-", "_")}
    if action == "python":
        code = _flag_string(parsed, "code")
        if not code:
            return _shell_error(
                code="shell.lab_code_required",
                message="lab python requires code through --code.",
                parsed=parsed,
                namespace="lab",
                actions=['lab python --code "from sympy import symbols; print(symbols(\'x\'))"'],
            )
        body = {
            "action": "python",
            "code": code,
            "source_ids": _flag_values(parsed, "source", "source-id"),
        }
    elif action == "web":
        subaction = parsed.args[0].casefold() if parsed.args else ""
        url = parsed.args[1] if len(parsed.args) > 1 else _flag_string(parsed, "url")
        if subaction != "open" or not url:
            return _shell_error(
                code="shell.lab_web_open_required",
                message="lab web requires `open` followed by one public HTTPS URL.",
                parsed=parsed,
                namespace="lab",
                actions=['lab web open "https://example.org"'],
            )
        body = {"action": "web_open", "url": url}
    elif action == "run":
        run_id = _first_arg_or_flag(parsed, "id", "run-id")
        if not run_id:
            return _shell_error(
                code="shell.lab_run_required",
                message="lab run requires a run id.",
                parsed=parsed,
                namespace="lab",
                actions=["lab run labrun_..."],
            )
        body = {"action": "run", "run_id": run_id}
    elif action == "source":
        source_id = _first_arg_or_flag(parsed, "id", "source-id")
        if not source_id:
            return _shell_error(
                code="shell.lab_source_required",
                message="lab source requires a source id.",
                parsed=parsed,
                namespace="lab",
                actions=["lab source labsrc_..."],
            )
        body = {"action": "source", "source_id": source_id}
    elif action == "artifact":
        artifact_id = _first_arg_or_flag(parsed, "id", "artifact-id")
        if not artifact_id:
            return _shell_error(
                code="shell.lab_artifact_required",
                message="lab artifact requires an artifact id.",
                parsed=parsed,
                namespace="lab",
                actions=["lab artifact labart_..."],
            )
        body = {"action": "artifact", "artifact_id": artifact_id}
    return _dispatch_api_as_shell(
        parsed,
        target=f"lab.{body['action']}",
        api_request=MindAPIRequest(
            method="POST",
            path="/mind/lab",
            body=body,
            intent=intent,
        ),
        context=context,
    )


def _episode_command(
    parsed: ParsedCommand,
    *,
    context: MindAPIContext | None,
    intent: str,
) -> MindAPIResponse:
    action = parsed.action or "list"
    action = {
        "inspect": "read",
        "show": "read",
        "get": "read",
    }.get(action, action)
    body: dict[str, Any] = {
        "action": action.replace("-", "_"),
        "limit": _flag_int(parsed, 20, "limit", "top"),
    }
    first = parsed.args[0] if parsed.args else None
    if action == "list":
        status = _flag_string(parsed, "status")
        if status is not None:
            body["status"] = status
    elif action == "read":
        body["episode_id"] = first or _flag_string(parsed, "id", "episode-id")
    elif action == "open":
        body["candidate_ids"] = [
            *parsed.args,
            *_flag_values(parsed, "candidate", "candidate-id"),
        ]
        body["question"] = _flag_string(parsed, "question")
        body["expected_transformation"] = _flag_string(
            parsed,
            "expected-transformation",
            "transformation",
        )
    elif action == "checkpoint":
        body.update(
            {
                "episode_id": first
                or _flag_string(parsed, "id", "episode-id"),
                "progress": _flag_string(parsed, "progress"),
                "next_step": _flag_string(parsed, "next", "next-step"),
                "source_refs": _flag_values(parsed, "source", "source-ref"),
                "no_progress": _flag_bool(parsed, False, "no-progress"),
            }
        )
    elif action in {"suspend", "resume", "resolve", "abandon"}:
        body.update(
            {
                "episode_id": first
                or _flag_string(parsed, "id", "episode-id"),
                "reason": _flag_string(parsed, "reason", "why"),
                "resolution": _flag_string(parsed, "resolution")
                or (
                    _flag_string(parsed, "reason", "why")
                    if action == "abandon"
                    else None
                ),
                "resume_at": _flag_string(parsed, "resume-at", "at"),
                "resume_event": _flag_string(
                    parsed,
                    "resume-event",
                    "event-type",
                ),
            }
        )
    elif action == "reject":
        body.update(
            {
                "candidate_id": first
                or _flag_string(parsed, "candidate", "candidate-id"),
                "reason": _flag_string(parsed, "reason", "why"),
            }
        )
    elif action == "expectation-add":
        body.update(
            {
                "episode_id": first
                or _flag_string(parsed, "id", "episode-id"),
                "claim": _flag_string(parsed, "claim"),
                "observable_outcome": _flag_string(
                    parsed,
                    "observable-outcome",
                    "outcome",
                ),
                "due_at": _flag_string(parsed, "due-at", "at"),
            }
        )
    elif action == "expectation-resolve":
        body.update(
            {
                "expectation_id": first
                or _flag_string(parsed, "expectation", "expectation-id"),
                "status": _flag_string(parsed, "status"),
                "evaluation": _flag_string(parsed, "evaluation"),
                "outcome_refs": _flag_values(
                    parsed,
                    "outcome-ref",
                    "source",
                ),
            }
        )
    elif action == "wake-add":
        body.update(
            {
                "episode_id": _flag_string(parsed, "episode", "episode-id"),
                "at": _flag_string(parsed, "at"),
                "event_type": _flag_string(parsed, "event-type"),
            }
        )
    elif action == "wake-cancel":
        body["condition_id"] = first or _flag_string(
            parsed,
            "condition",
            "condition-id",
        )
    return _dispatch_api_as_shell(
        parsed,
        target=f"episode.{action}",
        api_request=MindAPIRequest(
            method="POST",
            path="/mind/episode",
            body=body,
            intent=intent,
        ),
        context=context,
    )



def _default_intent(parsed: ParsedCommand) -> str:
    if parsed.namespace in {"help", "schema", "capabilities"}:
        return "Inspect current Mind shell capabilities."
    return f"Use Mind shell command {parsed.namespace} {parsed.action or ''}".strip()


__all__ = [
    "MIND_SHELL_TOOL_SCHEMA",
    "MindShellRequest",
    "dispatch_mind_shell",
]
