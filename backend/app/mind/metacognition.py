import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlmodel import Session
from sqlmodel import select

from app.llm.factory import active_provider_max_tokens
from app.llm.provider import LLMConfigurationError, LLMRequestError
from app.mind.memory import MemoryOperationResult, MindAPIContext
from app.mind.schema import MIND_API_ROUTES
from app.storage import repositories
from app.storage.models import CognitiveEvent, Message, ToolCall, Trace, Turn


MetacognitionMode = Literal[
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
]
RetrospectionScope = Literal["none", "previous"]
RetrospectionDetail = Literal["digest", "excerpt", "raw"]

RETROSPECTION_MODES = {
    "review_previous_turn",
    "detect_reasoning_drift",
    "explain_tool_choice",
    "recover_open_loops",
    "compare_answer_to_reasoning",
    "extract_reasoning_digest",
    "memory_from_reasoning",
}


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
  "reasoning_digest": "optional compact summary of previous internal reasoning",
  "drift_findings": [{"finding": "...", "severity": "low|medium|high", "evidence": "..."}],
  "open_loops": ["..."],
  "tool_use_assessment": [{"tool": "...", "assessment": "...", "needed": true}],
  "memory_candidates_from_reasoning": ["..."],
  "should_continue": true,
  "next_focus_question": "short question or null",
  "public_summary": "optional compact visible metacognition summary"
}

Keep the object compact and operational. Prefer schema, trace, memory, fact, or
runtime-context checks when claims depend on current backend state.
Recommended internal actions must use exactly one route/method pair from the
provided available_mind_api_routes list. Do not invent endpoints or methods.

When a retrospection_pack is provided, treat prior thinking as evidence of
Scarlet's earlier process, not evidence that external facts are true. Use it to
detect drift, lost assumptions, open loops, unnecessary tools, missed memory
candidates, and mismatch between user request, reasoning, actions, and final
answer.
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
    turn_scope: RetrospectionScope = "none"
    detail: RetrospectionDetail = "digest"

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

        reasoning_scope = normalized.pop("reasoning_scope", None)
        if isinstance(reasoning_scope, str) and "turn_scope" not in normalized:
            normalized["turn_scope"] = reasoning_scope

        reasoning_detail = normalized.pop("reasoning_detail", None)
        if isinstance(reasoning_detail, str) and "detail" not in normalized:
            normalized["detail"] = reasoning_detail

        if (
            normalized.get("mode") in RETROSPECTION_MODES
            and "turn_scope" not in normalized
        ):
            normalized["turn_scope"] = "previous"

        for list_field in ("known_evidence", "uncertainties", "previous_steps"):
            if list_field in normalized:
                normalized[list_field] = _normalize_model_list_wrapper(
                    normalized.get(list_field)
                )

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

    retrospection_pack = _build_retrospection_pack(request, context)
    prompt = _build_review_prompt(
        request,
        intent=intent,
        retrospection_pack=retrospection_pack,
    )
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
                "retrospection_pack": _trace_safe_retrospection_pack(
                    retrospection_pack
                ),
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
            "retrospection_pack": _trace_safe_retrospection_pack(retrospection_pack),
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
            "retrospection": _result_retrospection_payload(retrospection_pack),
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


def _build_review_prompt(
    request: MetacognitionStepBody,
    *,
    intent: str,
    retrospection_pack: dict[str, Any] | None,
) -> str:
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
        "turn_scope": request.turn_scope,
        "detail": request.detail,
        "retrospection_pack": retrospection_pack,
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


def _build_retrospection_pack(
    request: MetacognitionStepBody,
    context: MindAPIContext,
) -> dict[str, Any] | None:
    scope = request.turn_scope
    if scope == "none" and request.mode in RETROSPECTION_MODES:
        scope = "previous"
    if scope == "none":
        return None

    if scope != "previous":
        return {
            "schema_version": "thinking-retrospection-pack-v1",
            "available": False,
            "reason": "unsupported_scope",
            "requested_scope": scope,
        }

    with Session(context.engine) as db:
        target_turn = _previous_completed_turn(db, context)
        if target_turn is None:
            return {
                "schema_version": "thinking-retrospection-pack-v1",
                "available": False,
                "reason": "no_previous_completed_turn",
                "requested_scope": scope,
                "detail": request.detail,
            }

        messages = list(
            db.exec(
                select(Message)
                .where(Message.turn_id == target_turn.id)
                .order_by(Message.created_at, Message.id)
            ).all()
        )
        traces = list(
            db.exec(
                select(Trace)
                .where(Trace.turn_id == target_turn.id)
                .order_by(Trace.created_at, Trace.id)
            ).all()
        )
        events = list(
            db.exec(
                select(CognitiveEvent)
                .where(CognitiveEvent.turn_id == target_turn.id)
                .order_by(
                    CognitiveEvent.seq,
                    CognitiveEvent.created_at,
                    CognitiveEvent.id,
                )
            ).all()
        )
        tool_calls = list(
            db.exec(
                select(ToolCall)
                .where(ToolCall.turn_id == target_turn.id)
                .order_by(ToolCall.created_at, ToolCall.id)
            ).all()
        )

    raw_provider_messages = _raw_provider_messages_from_traces(traces)
    thinking_blocks = _provider_blocks(raw_provider_messages, "thinking")
    text_blocks = _provider_blocks(raw_provider_messages, "text")
    tool_use_blocks = _provider_blocks(raw_provider_messages, "tool_use")

    user_messages = [message.content for message in messages if message.role == "user"]
    assistant_messages = [
        message.content for message in messages if message.role == "assistant"
    ]
    public_notes = [
        _string(event.payload_json.get("text"))
        for event in events
        if event.type == "assistant.note.emitted"
    ]
    public_notes = [note for note in public_notes if note]

    thinking_texts = [
        _string(block.get("thinking")) or ""
        for block in thinking_blocks
        if isinstance(block, dict)
    ]
    thinking_texts = [text for text in thinking_texts if text.strip()]

    pack = {
        "schema_version": "thinking-retrospection-pack-v1",
        "available": True,
        "scope": "previous",
        "detail": request.detail,
        "source_session_id": target_turn.session_id,
        "source_turn_id": target_turn.id,
        "turn_started_at": target_turn.started_at.isoformat(),
        "turn_completed_at": target_turn.completed_at.isoformat()
        if target_turn.completed_at
        else None,
        "user_messages": [_clip(text, 1200) for text in user_messages],
        "assistant_final_messages": [_clip(text, 1600) for text in assistant_messages],
        "public_notes": [_clip(note, 800) for note in public_notes],
        "tool_calls": [
            {
                "tool_call_id": tool_call.id,
                "tool_name": tool_call.tool_name,
                "status": tool_call.status,
                "arguments": _clip_json(tool_call.arguments_json, 1000),
                "result": _clip_json(tool_call.result_json, 1200),
            }
            for tool_call in tool_calls
        ],
        "provider_message_count": len(raw_provider_messages),
        "provider_text_block_count": len(text_blocks),
        "provider_tool_use_block_count": len(tool_use_blocks),
        "thinking_block_count": len(thinking_texts),
        "thinking_total_chars": sum(len(text) for text in thinking_texts),
        "thinking": _thinking_payload(thinking_texts, detail=request.detail),
        "event_markers": [
            {
                "type": event.type,
                "status": event.status,
                "seq": event.seq,
            }
            for event in events
            if event.type
            in {
                "llm.thinking.started",
                "llm.thinking.captured",
                "assistant.note.emitted",
                "assistant.answer.completed",
                "mind.tool_call.requested",
                "mind.tool_call.completed",
                "turn.completed",
            }
        ][:40],
        "source_policy": (
            "Prior thinking is process evidence. It can explain Scarlet's "
            "assumptions, drift, open loops, and tool choices, but it does not "
            "prove external facts."
        ),
    }
    return pack


def _previous_completed_turn(
    db: Session,
    context: MindAPIContext,
) -> Turn | None:
    current_turn: Turn | None = None
    if context.turn_id:
        current_turn = db.get(Turn, context.turn_id)

    statement = select(Turn).where(
        Turn.session_id == context.session_id,
        Turn.status == "completed",
    )
    if current_turn is not None:
        statement = statement.where(Turn.started_at < current_turn.started_at)
    elif context.turn_id:
        statement = statement.where(Turn.id != context.turn_id)
    statement = statement.order_by(Turn.started_at.desc(), Turn.id.desc()).limit(1)
    return db.exec(statement).first()


def _raw_provider_messages_from_traces(traces: list[Trace]) -> list[dict[str, Any]]:
    for trace in reversed(traces):
        if trace.kind != "llm.response":
            continue
        messages = trace.payload_json.get("raw_provider_messages")
        if isinstance(messages, list):
            return [message for message in messages if isinstance(message, dict)]
    return []


def _provider_blocks(
    raw_provider_messages: list[dict[str, Any]],
    block_type: str,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for message in raw_provider_messages:
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == block_type:
                blocks.append(block)
    return blocks


def _thinking_payload(
    thinking_texts: list[str],
    *,
    detail: RetrospectionDetail,
) -> dict[str, Any]:
    joined = "\n\n--- thinking block ---\n\n".join(thinking_texts)
    if not joined:
        return {
            "available": False,
            "detail": detail,
            "items": [],
        }
    if detail == "raw":
        limit = 16000
    elif detail == "excerpt":
        limit = 6000
    else:
        limit = 2200
    return {
        "available": True,
        "detail": detail,
        "chars": len(joined),
        "truncated": len(joined) > limit,
        "items": [
            {
                "index": index,
                "chars": len(text),
                "text": _clip(text, limit // max(len(thinking_texts), 1)),
            }
            for index, text in enumerate(thinking_texts)
        ],
        "extractive_digest": _extractive_digest(joined, limit=limit),
    }


def _extractive_digest(text: str, *, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    head_size = max(600, int(limit * 0.65))
    tail_size = max(300, limit - head_size - 80)
    return (
        text[:head_size].rstrip()
        + "\n...[middle omitted by thinking-retrospection-pack]...\n"
        + text[-tail_size:].lstrip()
    )


def _trace_safe_retrospection_pack(
    pack: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if pack is None:
        return None
    return pack


def _result_retrospection_payload(
    pack: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if pack is None:
        return None
    thinking = pack.get("thinking")
    return {
        "available": bool(pack.get("available")),
        "schema_version": pack.get("schema_version"),
        "scope": pack.get("scope"),
        "detail": pack.get("detail"),
        "source_session_id": pack.get("source_session_id"),
        "source_turn_id": pack.get("source_turn_id"),
        "thinking_block_count": pack.get("thinking_block_count", 0),
        "thinking_total_chars": pack.get("thinking_total_chars", 0),
        "thinking_available": bool(thinking.get("available"))
        if isinstance(thinking, dict)
        else False,
        "tool_call_count": len(pack.get("tool_calls") or []),
        "public_note_count": len(pack.get("public_notes") or []),
        "source_policy": pack.get("source_policy"),
    }


def _context_summary(context: Any) -> str:
    if isinstance(context, str):
        return context[:1000]
    try:
        return json.dumps(context, ensure_ascii=True, sort_keys=True)[:1000]
    except TypeError:
        return str(context)[:1000]


def _normalize_model_list_wrapper(value: Any) -> Any:
    if isinstance(value, dict) and set(value.keys()) == {"item"}:
        return value.get("item")
    return value


def _clip(text: Any, limit: int) -> str:
    if text is None:
        return ""
    value = str(text)
    if len(value) <= limit:
        return value
    return value[: max(limit - 40, 0)].rstrip() + "...[truncated]"


def _clip_json(value: Any, limit: int) -> Any:
    try:
        encoded = json.dumps(value, ensure_ascii=True, sort_keys=True)
    except TypeError:
        return _clip(value, limit)
    if len(encoded) <= limit:
        return value
    return {
        "truncated": True,
        "json_preview": _clip(encoded, limit),
    }


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
        "reasoning_digest": _string(parsed.get("reasoning_digest")),
        "drift_findings": _list_of_dicts(parsed.get("drift_findings"))[
            : request.max_findings
        ],
        "open_loops": _list_of_strings(parsed.get("open_loops"))[
            : request.max_findings
        ],
        "tool_use_assessment": _list_of_dicts(parsed.get("tool_use_assessment"))[
            : request.max_findings
        ],
        "memory_candidates_from_reasoning": _list_of_strings(
            parsed.get("memory_candidates_from_reasoning")
        )[: request.max_findings],
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
