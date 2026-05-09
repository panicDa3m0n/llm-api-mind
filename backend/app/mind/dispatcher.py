from typing import Any, Literal

from pydantic import BaseModel, Field

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


class MindAPIResponse(BaseModel):
    ok: bool
    result: dict[str, Any] = Field(default_factory=dict)
    cognitive_hint: str | None = None
    suggested_next_actions: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    trace_id: str | None = None
    error: MindAPIError | None = None


def dispatch_mind_api(request: MindAPIRequest) -> MindAPIResponse:
    method = request.method.upper()
    path = _normalize_path(request.path)

    if method == "GET" and path == "/mind/schema":
        return MindAPIResponse(
            ok=True,
            result=build_mind_schema(),
            cognitive_hint=(
                "Use this schema to choose only implemented Mind API routes. "
                "Memory, attention, events, and reflection are still planned."
            ),
            suggested_next_actions=[
                "Call implemented routes only",
                "Continue without cognitive state for planned routes",
            ],
            confidence=1.0,
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
