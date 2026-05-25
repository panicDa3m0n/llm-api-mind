import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlmodel import Session

from app.llm.factory import active_provider_max_tokens
from app.llm.provider import LLMConfigurationError, LLMRequestError
from app.mind.memory import MemoryOperationResult, MindAPIContext
from app.mind.schema import MIND_API_ROUTES
from app.storage import repositories


MetacognitionMode = Literal[
    "orient",
    "critic",
    "validator",
    "planner",
    "synthesizer",
    "empathy",
    "memory_curator",
]


METACOGNITION_SYSTEM_PROMPT = """You are Scarlet's internal metacognitive reviewer.

You are not speaking to the user. You are returning a private, structured
cognitive result to Scarlet through API Mind.

Do not expose raw chain-of-thought. Do not write a final user-facing answer.
Return only one JSON object with this shape:

{
  "review_summary": "short operational summary",
  "risks": [{"risk": "...", "severity": "low|medium|high", "mitigation": "..."}],
  "claim_checks": [{"claim": "...", "support": "supported|needs_evidence|unsupported|inference", "confidence": 0.0, "recommended_action": "..."}],
  "missing_evidence": ["..."],
  "recommended_internal_actions": [{"method": "GET|POST", "path": "/mind/...", "reason": "..."}],
  "should_continue": true,
  "next_focus_question": "short question or null",
  "public_summary": "optional compact visible metacognition summary"
}

Keep the object compact and operational. Prefer schema, trace, memory, fact, or
runtime-context checks when claims depend on current backend state.
Recommended internal actions must use exactly one route/method pair from the
provided available_mind_api_routes list. Do not invent endpoints or methods.
"""


METACOGNITION_REPAIR_SYSTEM_PROMPT = """You repair malformed internal JSON.

Return only one valid JSON object matching the requested metacognition review
shape. Preserve the meaning of the malformed review when possible. Do not add
markdown, prose, or code fences.
"""


class MetacognitionStepBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: MetacognitionMode = "critic"
    objective: str = Field(min_length=8, max_length=2000)
    focus_question: str | None = Field(default=None, max_length=2000)
    internal_prompt: str | None = Field(default=None, max_length=4000)
    known_evidence: list[str] = Field(default_factory=list, max_length=40)
    uncertainties: list[str] = Field(default_factory=list, max_length=40)
    draft_answer: str | None = Field(default=None, max_length=12000)
    previous_steps: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    max_findings: int = Field(default=6, ge=1, le=12)

    @model_validator(mode="before")
    @classmethod
    def normalize_model_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)

        prompt = normalized.pop("prompt", None)
        if isinstance(prompt, str):
            if "internal_prompt" not in normalized:
                normalized["internal_prompt"] = prompt
            if "objective" not in normalized:
                normalized["objective"] = prompt[:2000]

        objective_alias: tuple[str, str] | None = None
        for alias in ("goal", "task", "purpose", "question"):
            alias_value = normalized.pop(alias, None)
            if objective_alias is None and isinstance(alias_value, str):
                objective_alias = (alias, alias_value)
        if objective_alias is not None:
            alias, alias_value = objective_alias
            if "objective" not in normalized:
                normalized["objective"] = alias_value[:2000]
            if "focus_question" not in normalized and alias == "question":
                normalized["focus_question"] = alias_value[:2000]
            elif "internal_prompt" not in normalized:
                normalized["internal_prompt"] = alias_value[:4000]

        context = normalized.pop("context", None)
        if "known_evidence" not in normalized and context not in (None, {}, []):
            normalized["known_evidence"] = [_context_summary(context)]

        if "objective" not in normalized and isinstance(
            normalized.get("focus_question"), str
        ):
            normalized["objective"] = normalized["focus_question"]

        return normalized


def handle_metacognition_step(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str,
) -> MemoryOperationResult:
    if context is None or context.session_id is None:
        return _context_required()
    if context.settings is None or context.provider_factory is None:
        return _provider_unavailable("Metacognition requires an LLM provider in context.")

    try:
        request = MetacognitionStepBody.model_validate(body)
    except ValidationError as exc:
        return _validation_error(exc)

    prompt = _build_review_prompt(request, intent=intent)
    try:
        provider = context.provider_factory(context.settings)
        result = provider.generate_text(
            prompt=prompt,
            system=METACOGNITION_SYSTEM_PROMPT,
            max_tokens=active_provider_max_tokens(context.settings),
        )
    except LLMConfigurationError as exc:
        return _provider_unavailable(str(exc))
    except LLMRequestError as exc:
        return MemoryOperationResult(
            ok=False,
            result={"operation": "metacognition.step"},
            cognitive_hint="The internal metacognitive LLM call failed.",
            suggested_next_actions=[
                "Continue without this metacognitive step if the answer is low risk",
                "Retry metacognition after the provider recovers",
            ],
            confidence=1.0,
            error_code="metacognition.provider_error",
            error_message=str(exc),
        )

    repair_result: Any | None = None
    parsed = _parse_review(result.text)
    if parsed is None:
        try:
            repair_result = provider.generate_text(
                prompt=_build_repair_prompt(result.text),
                system=METACOGNITION_REPAIR_SYSTEM_PROMPT,
                max_tokens=active_provider_max_tokens(context.settings),
            )
            parsed = _parse_review(repair_result.text)
        except (LLMConfigurationError, LLMRequestError):
            repair_result = None

    if parsed is None:
        trace_id = _add_trace(
            context,
            {
                "operation": "metacognition.step",
                "intent": intent,
                "input": request.model_dump(mode="json"),
                "provider": _provider_payload(result),
                "repair_provider": _provider_payload(repair_result)
                if repair_result is not None
                else None,
                "parse_error": "review_not_json",
            },
        )
        return MemoryOperationResult(
            ok=False,
            result={
                "operation": "metacognition.step",
                "raw_review": result.text,
                "trace_ids": [trace_id],
            },
            cognitive_hint=(
                "The metacognitive reviewer returned non-JSON output. Treat it "
                "as unusable and inspect schema before retrying."
            ),
            suggested_next_actions=[
                "Retry /mind/metacognition/step",
                "Continue only if the final answer can be grounded without it",
            ],
            confidence=0.4,
            error_code="metacognition.invalid_review",
            error_message="Metacognition review was not valid JSON.",
        )

    normalized = _normalize_review(parsed, request)
    json_repair_applied = repair_result is not None
    trace_id = _add_trace(
        context,
        {
            "operation": "metacognition.step",
            "intent": intent,
            "input": request.model_dump(mode="json"),
            "review": normalized,
            "provider": _provider_payload(result),
            "repair_provider": _provider_payload(repair_result)
            if repair_result is not None
            else None,
            "json_repair_applied": json_repair_applied,
        },
    )
    return MemoryOperationResult(
        ok=True,
        result={
            "mode": request.mode,
            "review": normalized,
            "trace_ids": [trace_id],
            "model": (repair_result or result).model,
            "usage": (repair_result or result).usage,
            "json_repair_applied": json_repair_applied,
        },
        cognitive_hint=(
            "Use this one metacognitive result to decide whether to call other "
            "existing API Mind routes, revise the draft, continue the loop, or "
            "answer. Do not call separate validation/blackboard/reflection endpoints."
        ),
        suggested_next_actions=[
            "Run recommended existing Mind API actions when they reduce risk",
            "Revise unsupported claims before answering",
            "Call /mind/metacognition/step again only if the next_focus_question is still unresolved",
        ],
        confidence=0.86,
    )


def _build_review_prompt(request: MetacognitionStepBody, *, intent: str) -> str:
    payload = {
        "intent": intent,
        "mode": request.mode,
        "objective": request.objective,
        "focus_question": request.focus_question,
        "internal_prompt": request.internal_prompt,
        "known_evidence": request.known_evidence,
        "uncertainties": request.uncertainties,
        "draft_answer": request.draft_answer,
        "previous_steps": request.previous_steps,
        "max_findings": request.max_findings,
        "available_mind_api_routes": _route_summaries(),
    }
    return (
        "Review this cognitive situation for Scarlet. Return only JSON in the "
        "specified schema.\n\n"
        + json.dumps(payload, ensure_ascii=True, indent=2)
    )


def _build_repair_prompt(raw_review: str) -> str:
    return (
        "Repair this malformed internal metacognition review into valid JSON "
        "matching the required review schema. Return only JSON.\n\n"
        + raw_review
    )


def _context_summary(context: Any) -> str:
    if isinstance(context, str):
        return context[:1000]
    try:
        return json.dumps(context, ensure_ascii=True, sort_keys=True)[:1000]
    except TypeError:
        return str(context)[:1000]


def _parse_review(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _normalize_review(
    parsed: dict[str, Any],
    request: MetacognitionStepBody,
) -> dict[str, Any]:
    return {
        "review_summary": _string(parsed.get("review_summary"))
        or "Metacognitive review completed.",
        "risks": _list_of_dicts(parsed.get("risks"))[: request.max_findings],
        "claim_checks": _list_of_dicts(parsed.get("claim_checks"))[: request.max_findings],
        "missing_evidence": _list_of_strings(parsed.get("missing_evidence"))[
            : request.max_findings
        ],
        "recommended_internal_actions": _normalize_recommended_actions(
            parsed.get("recommended_internal_actions"),
            request.max_findings,
        ),
        "should_continue": bool(parsed.get("should_continue", False)),
        "next_focus_question": _string(parsed.get("next_focus_question")),
        "public_summary": _string(parsed.get("public_summary")),
    }


def _add_trace(context: MindAPIContext, payload: dict[str, Any]) -> str:
    with Session(context.engine) as db:
        trace = repositories.add_trace(
            db,
            session_id=context.session_id or "",
            turn_id=context.turn_id,
            kind="mind.metacognition.step",
            payload=payload,
        )
        return trace.id


def _provider_payload(result: Any) -> dict[str, Any]:
    return {
        "model": result.model,
        "usage": result.usage,
        "provider_message_id": result.provider_message_id,
        "stop_reason": result.stop_reason,
        "raw_text": result.text,
    }


def _route_summaries() -> list[dict[str, str]]:
    return [
        {
            "method": str(route["method"]),
            "path": str(route["path"]),
            "status": str(route["status"]),
        }
        for route in MIND_API_ROUTES
    ]


def _normalize_recommended_actions(value: Any, limit: int) -> list[dict[str, Any]]:
    actions = _list_of_dicts(value)[:limit]
    normalized: list[dict[str, Any]] = []
    for action in actions:
        item = dict(action)
        method = _string(item.get("method"))
        path = _string(item.get("path"))
        if method is not None:
            method = method.upper()
            item["method"] = method
        if path is not None and not path.startswith("/"):
            path = f"/{path}"
            item["path"] = path

        route_match = _find_route(method=method, path=path)
        same_path_methods = _available_methods_for_path(path)
        if route_match is not None:
            item["schema_status"] = str(route_match["status"])
            item["call_is_available"] = route_match["status"] == "implemented"
        elif same_path_methods:
            item["schema_status"] = "wrong_method"
            item["call_is_available"] = False
            item["available_methods"] = same_path_methods
            if len(same_path_methods) == 1:
                item["suggested_method"] = same_path_methods[0]
        else:
            item["schema_status"] = "unknown_route"
            item["call_is_available"] = False
        normalized.append(item)
    return normalized


def _find_route(method: str | None, path: str | None) -> dict[str, Any] | None:
    if method is None or path is None:
        return None
    for route in MIND_API_ROUTES:
        if route["method"] == method and route["path"] == path:
            return route
    return None


def _available_methods_for_path(path: str | None) -> list[str]:
    if path is None:
        return []
    return sorted(
        {
            str(route["method"])
            for route in MIND_API_ROUTES
            if route["path"] == path
        }
    )


def _context_required() -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        result={"operation": "metacognition.step"},
        cognitive_hint="Metacognition requires session context so it can be traced.",
        suggested_next_actions=["Retry with a valid session_id", "Continue without metacognition for low-risk answers"],
        confidence=1.0,
        error_code="metacognition.context_required",
        error_message="Metacognition requires traceable session context.",
    )


def _provider_unavailable(message: str) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        result={"operation": "metacognition.step"},
        cognitive_hint="The internal LLM-backed metacognition provider is unavailable.",
        suggested_next_actions=[
            "Inspect schema and existing memory/fact evidence directly",
            "Continue without metacognition if the answer is low risk",
        ],
        confidence=1.0,
        error_code="metacognition.provider_unavailable",
        error_message=message,
    )


def _validation_error(exc: ValidationError) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        result={
            "operation": "metacognition.step",
            "validation_errors": exc.errors(),
            "expected_schema_hint": "Call GET /mind/schema for the metacognition body_schema.",
        },
        cognitive_hint="Retry the single metacognition endpoint with the schema body shape.",
        suggested_next_actions=["Call GET /mind/schema", "Retry /mind/metacognition/step"],
        confidence=1.0,
        error_code="metacognition.invalid_body",
        error_message=str(exc),
    )


def _string(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
