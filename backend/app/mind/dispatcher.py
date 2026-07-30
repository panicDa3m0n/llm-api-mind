import json
from typing import Any, Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import BaseModel, Field, model_validator

from app.mind.contracts import MindAPIContext, MemoryOperationResult
from app.mind.memory import (
    handle_memory_conflicts,
    handle_memory_deprecate,
    handle_memory_facts,
    handle_memory_facts_backfill,
    handle_memory_graph,
    handle_memory_proposal_decide,
    handle_memory_proposal_list,
    handle_memory_proposal_read,
    handle_memory_read,
    handle_memory_search,
    handle_memory_supersede,
    handle_memory_write,
)
from app.mind.episodic import (
    handle_session_read,
    handle_session_message_read,
    handle_session_summarize,
    handle_session_turn_read,
    handle_sessions_list,
)
from app.mind.episode import handle_episode
from app.mind.affect import handle_affect
from app.mind.focus import handle_focus
from app.mind.metacognition import handle_metacognition_step
from app.mind.mode import handle_agent_mode
from app.mind.perception import handle_perception
from app.mind.research_lab import handle_research_lab
from app.mind.schema import (
    build_mind_schema,
    implemented_route_summaries,
    route_catalog_suggestions,
    route_body_schema,
    route_usage_guide,
    schema_metadata,
)
from app.mind.volition import handle_volition


class MindAPIError(BaseModel):
    code: str
    message: str
    recoverable: bool = True


class MindAPIRequest(BaseModel):
    method: Literal["GET", "POST"]
    path: str = Field(min_length=1, max_length=200)
    body: dict[str, Any] = Field(default_factory=dict)
    intent: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="before")
    @classmethod
    def normalize_model_tool_input(cls, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return value
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        raw_input = normalized.get("raw_input")
        if isinstance(raw_input, str):
            try:
                raw_input = json.loads(raw_input)
            except json.JSONDecodeError:
                raw_input = None
        if isinstance(raw_input, dict):
            unwrapped = dict(raw_input)
            for key, item in normalized.items():
                if key != "raw_input" and key not in unwrapped:
                    unwrapped[key] = item
            normalized = unwrapped

        body = normalized.get("body")
        if isinstance(body, str):
            try:
                parsed_body = json.loads(body)
            except json.JSONDecodeError:
                parsed_body = None
            if isinstance(parsed_body, dict):
                normalized["body"] = parsed_body

        body = normalized.get("body")
        if isinstance(body, dict):
            body = dict(body)
            if "intent" not in normalized and isinstance(body.get("intent"), str):
                normalized["intent"] = body.pop("intent")
            normalized["body"] = body

        return normalized


class MindAPIResponse(BaseModel):
    ok: bool
    result: dict[str, Any] = Field(default_factory=dict)
    cognitive_hint: str | None = None
    suggested_next_actions: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    trace_id: str | None = None
    usage_guide: dict[str, Any] | None = None
    error: MindAPIError | None = None


def dispatch_mind_api(
    request: MindAPIRequest,
    context: MindAPIContext | None = None,
) -> MindAPIResponse:
    method = request.method.upper()
    path, query_body = _normalize_path_and_query(request.path)
    body = {**query_body, **request.body}

    if method == "GET" and path == "/mind/schema":
        return MindAPIResponse(
            ok=True,
            result=build_mind_schema(),
            cognitive_hint=(
                "Use this schema to choose implemented Mind API routes. "
                "Semantic memory, episodic session recall, and the single "
                "LLM-backed metacognition route are available. Previous-turn "
                "thinking retrospection is part of the metacognition route. "
                "Runtime events are backend-owned rather than a model-facing "
                "route; focus is available as a dedicated foreground-attention "
                "state route; volition is available as a manual latent-intention "
                "register; affect is available as a read-only backend-appraised "
                "state route; agent mode is Scarlet's foreground operating "
                "posture; reflection stays inside the single metacognition route."
            ),
            suggested_next_actions=[
                "Call implemented routes only",
                "Use /mind/focus to set, inspect, shift, defer, resolve, or archive foreground focus",
                "Use /mind/volition to create, inspect, review, or close latent self-generated intentions",
                "Use /mind/affect to inspect current affect state or prototypes without mutating emotions",
                "Use /mind/mode to inspect or select Scarlet's agent operating posture",
                "Use memory lifecycle routes when persistent context conflicts",
                "Use session recall routes when a memory's source conversation matters",
            ],
            confidence=1.0,
        )

    if method == "POST" and path == "/mind/memory/write":
        return _memory_response(
            handle_memory_write(body, context, intent=request.intent),
            method=method,
            path=path,
        )

    if method in {"GET", "POST"} and path == "/mind/memory/search":
        return _memory_response(
            handle_memory_search(body, context, intent=request.intent),
            method=method,
            path=path,
        )

    if method == "GET" and path == "/mind/memory/conflicts":
        return _memory_response(
            handle_memory_conflicts(context),
            method=method,
            path=path,
        )

    if method == "GET" and path == "/mind/memory/facts":
        return _memory_response(
            handle_memory_facts(body, context, intent=request.intent),
            method=method,
            path=path,
        )

    if method == "POST" and path == "/mind/memory/facts/backfill":
        return _memory_response(
            handle_memory_facts_backfill(body, context, intent=request.intent),
            method=method,
            path=path,
        )

    if method in {"GET", "POST"} and path == "/mind/memory/graph":
        return _memory_response(
            handle_memory_graph(body, context, intent=request.intent),
            method=method,
            path=path,
        )

    if method == "POST" and path == "/mind/memory/deprecate":
        return _memory_response(
            handle_memory_deprecate(body, context, intent=request.intent),
            method=method,
            path=path,
        )

    if method == "POST" and path == "/mind/memory/supersede":
        return _memory_response(
            handle_memory_supersede(body, context, intent=request.intent),
            method=method,
            path=path,
        )

    if method == "GET" and path == "/mind/memory/proposals":
        return _memory_response(
            handle_memory_proposal_list(body, context),
            method=method,
            path=path,
        )

    if method == "POST" and path == "/mind/memory/proposals/decide":
        return _memory_response(
            handle_memory_proposal_decide(
                body,
                context,
                intent=request.intent,
            ),
            method=method,
            path=path,
        )

    if method == "GET" and path.startswith("/mind/memory/proposals/"):
        proposal_id = path.removeprefix("/mind/memory/proposals/").rstrip("/")
        if proposal_id:
            return _memory_response(
                handle_memory_proposal_read(proposal_id, context),
                method=method,
                path=path,
            )

    if method == "GET" and path == "/mind/sessions":
        return _operation_response(
            handle_sessions_list(body, context, intent=request.intent),
            method=method,
            path=path,
        )

    if path.startswith("/mind/sessions/"):
        suffix = path.removeprefix("/mind/sessions/")
        if method == "GET" and suffix.startswith("messages/"):
            message_id = suffix.removeprefix("messages/").rstrip("/")
            if message_id:
                return _operation_response(
                    handle_session_message_read(
                        message_id,
                        context,
                        intent=request.intent,
                    ),
                    method=method,
                    path=path,
                )
        if method == "GET" and suffix.startswith("turns/"):
            turn_id = suffix.removeprefix("turns/").rstrip("/")
            if turn_id:
                return _operation_response(
                    handle_session_turn_read(
                        turn_id,
                        context,
                        intent=request.intent,
                    ),
                    method=method,
                    path=path,
                )
        if method == "POST" and suffix.endswith("/summarize"):
            session_id = suffix.removesuffix("/summarize").rstrip("/")
            if session_id:
                return _operation_response(
                    handle_session_summarize(
                        session_id,
                        body,
                        context,
                        intent=request.intent,
                    ),
                    method=method,
                    path=path,
                )
        if method == "GET" and suffix:
            return _operation_response(
                handle_session_read(
                    suffix.rstrip("/"),
                    body,
                    context,
                    intent=request.intent,
                ),
                method=method,
                path=path,
            )

    if method == "POST" and path == "/mind/metacognition/step":
        return _operation_response(
            handle_metacognition_step(body, context, intent=request.intent),
            method=method,
            path=path,
        )

    if method == "POST" and path == "/mind/perception":
        return _operation_response(
            handle_perception(body, context, intent=request.intent),
            method=method,
            path=path,
        )

    if method == "POST" and path == "/mind/lab":
        return _operation_response(
            handle_research_lab(body, context, intent=request.intent),
            method=method,
            path=path,
        )

    if method == "POST" and path == "/mind/episode":
        return _operation_response(
            handle_episode(body, context, intent=request.intent),
            method=method,
            path=path,
        )

    if method == "POST" and path == "/mind/focus":
        return _operation_response(
            handle_focus(body, context, intent=request.intent),
            method=method,
            path=path,
        )

    if method == "POST" and path == "/mind/volition":
        return _operation_response(
            handle_volition(body, context, intent=request.intent),
            method=method,
            path=path,
        )

    if method == "POST" and path == "/mind/affect":
        return _operation_response(
            handle_affect(body, context, intent=request.intent),
            method=method,
            path=path,
        )

    if method == "POST" and path == "/mind/mode":
        return _operation_response(
            handle_agent_mode(body, context, intent=request.intent),
            method=method,
            path=path,
        )

    if method == "GET" and path.startswith("/mind/memory/"):
        memory_id = path.removeprefix("/mind/memory/")
        if memory_id.startswith("mem_"):
            return _memory_response(
                handle_memory_read(memory_id, context),
                method=method,
                path=path,
            )

    return MindAPIResponse(
        ok=False,
        error=MindAPIError(
            code="mind.route_not_available",
            message=f"{method} {path} is not implemented in the current Mind API.",
            recoverable=True,
        ),
        result={
            "schema": schema_metadata(),
            "expected_schema": route_body_schema(method, path),
            "implemented_routes": implemented_route_summaries(),
            "route_suggestions": route_catalog_suggestions(method, path),
        },
        suggested_next_actions=[
            "Call GET /mind/schema",
            "Continue without this cognitive support",
        ],
        confidence=1.0,
    )


def _normalize_path_and_query(path: str) -> tuple[str, dict[str, Any]]:
    raw = path.strip()
    parsed = urlsplit(raw if raw.startswith("/") else f"/{raw}")
    normalized = parsed.path
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    query: dict[str, Any] = {}
    for key, values in parse_qs(parsed.query, keep_blank_values=False).items():
        if not values:
            continue
        query[key] = values[0] if len(values) == 1 else values
    return normalized, query


def _memory_response(
    result: MemoryOperationResult,
    *,
    method: str | None = None,
    path: str | None = None,
) -> MindAPIResponse:
    return _operation_response(result, method=method, path=path)


def _operation_response(
    result: MemoryOperationResult,
    *,
    method: str | None = None,
    path: str | None = None,
) -> MindAPIResponse:
    guide = None
    if not result.ok and result.error_recoverable and method and path:
        guide = route_usage_guide(method, path)
    return MindAPIResponse(
        ok=result.ok,
        result=result.result,
        cognitive_hint=result.cognitive_hint,
        suggested_next_actions=_suggested_actions(result.suggested_next_actions, guide),
        confidence=result.confidence,
        usage_guide=guide,
        error=MindAPIError(
            code=result.error_code,
            message=result.error_message or "",
            recoverable=result.error_recoverable,
        )
        if result.error_code is not None
        else None,
    )


def _suggested_actions(
    actions: list[str],
    usage_guide: dict[str, Any] | None,
) -> list[str]:
    if usage_guide is None:
        return actions
    cleaned = [
        action
        for action in actions
        if action.strip().casefold() != "call get /mind/schema"
    ]
    lead = (
        "Use usage_guide to correct this endpoint call, then retry with valid parameters"
    )
    return [lead, *cleaned]
