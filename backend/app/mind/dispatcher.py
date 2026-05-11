import json
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.mind.memory import (
    MemoryOperationResult,
    MindAPIContext,
    handle_memory_search,
    handle_memory_write,
)
from app.mind.schema import build_mind_schema


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
    error: MindAPIError | None = None


def dispatch_mind_api(
    request: MindAPIRequest,
    context: MindAPIContext | None = None,
) -> MindAPIResponse:
    method = request.method.upper()
    path = _normalize_path(request.path)

    if method == "GET" and path == "/mind/schema":
        return MindAPIResponse(
            ok=True,
            result=build_mind_schema(),
            cognitive_hint=(
                "Use this schema to choose implemented Mind API routes. "
                "Memory write/search are available in v0; attention, events, "
                "and reflection are still planned."
            ),
            suggested_next_actions=[
                "Call implemented routes only",
                "Use memory write/search when persistent context is relevant",
                "Continue without cognitive state for planned routes",
            ],
            confidence=1.0,
        )

    if method == "POST" and path == "/mind/memory/write":
        return _memory_response(
            handle_memory_write(request.body, context, intent=request.intent)
        )

    if method in {"GET", "POST"} and path == "/mind/memory/search":
        return _memory_response(
            handle_memory_search(request.body, context, intent=request.intent)
        )

    return MindAPIResponse(
        ok=False,
        error=MindAPIError(
            code="mind.route_not_available",
            message=f"{method} {path} is not implemented in the current Mind API.",
            recoverable=True,
        ),
        suggested_next_actions=[
            "Call GET /mind/schema",
            "Continue without this cognitive support",
        ],
        confidence=1.0,
    )


def _normalize_path(path: str) -> str:
    normalized = path.strip()
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized


def _memory_response(result: MemoryOperationResult) -> MindAPIResponse:
    return MindAPIResponse(
        ok=result.ok,
        result=result.result,
        cognitive_hint=result.cognitive_hint,
        suggested_next_actions=result.suggested_next_actions,
        confidence=result.confidence,
        error=MindAPIError(
            code=result.error_code,
            message=result.error_message or "",
            recoverable=result.error_recoverable,
        )
        if result.error_code is not None
        else None,
    )
