"""Traceable final-answer obligations shared by native and GPT transports."""

from __future__ import annotations

import json
import re
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from app.llm.provider import LLMExecutedToolCall, LLMProvider, LLMRequestError


ANSWER_OBLIGATIONS_VERSION = "answer-obligations-v1"
ANSWER_VALIDATION_VERSION = "answer-validation-v1"
NATIVE_FINAL_MARKER = "<scarlet-final/>"

Severity = Literal["hard", "warning", "advisory"]
ValidationKind = Literal["structural", "semantic"]
FindingStatus = Literal["pass", "fail", "unknown"]


class AnswerObligation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    severity: Severity
    validation_kind: ValidationKind
    requirement: str
    evidence_refs: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)


class AnswerObligationManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = ANSWER_OBLIGATIONS_VERSION
    transport: Literal["native", "gpt_bridge"]
    obligations: list[AnswerObligation] = Field(default_factory=list)

    @property
    def semantic(self) -> list[AnswerObligation]:
        return [
            obligation
            for obligation in self.obligations
            if obligation.validation_kind == "semantic"
        ]


class AnswerValidationFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    obligation_id: str
    severity: Severity
    status: FindingStatus
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)


class AnswerValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = ANSWER_VALIDATION_VERSION
    accepted: bool
    findings: list[AnswerValidationFinding] = Field(default_factory=list)
    hard_failure_ids: list[str] = Field(default_factory=list)
    validator_status: Literal["not_required", "completed", "failed"]
    validator_error: str | None = None
    provider: dict[str, Any] = Field(default_factory=dict)


def compile_answer_obligations(
    *,
    transport: Literal["native", "gpt_bridge"],
    memory_context: dict[str, Any],
    metacognitive_context: dict[str, Any] | None,
) -> AnswerObligationManifest:
    obligations: list[AnswerObligation] = []
    if transport == "native":
        obligations.append(
            AnswerObligation(
                id="answer.final_boundary",
                severity="hard",
                validation_kind="structural",
                requirement=(
                    "End the conclusive public answer with the private runtime "
                    f"marker {NATIVE_FINAL_MARKER}. A progress note is not final."
                ),
            )
        )

    conflicts = memory_context.get("conflicts")
    if isinstance(conflicts, list) and conflicts:
        obligations.append(
            AnswerObligation(
                id="memory.active_conflict_disclosure",
                severity="hard",
                validation_kind="semantic",
                requirement=(
                    "Do not silently choose between active conflicting memories. "
                    "Acknowledge the material conflict or avoid a definitive claim."
                ),
                evidence_refs=_string_refs(memory_context.get("trace_id")),
                evidence={"conflicts": _compact_json_value(conflicts, limit=5000)},
            )
        )

    lesson_ids = _metacognitive_lesson_ids(metacognitive_context)
    if "source_sensitive_claim_guard" in lesson_ids:
        obligations.append(
            AnswerObligation(
                id="evidence.source_sensitive_claim",
                severity="hard",
                validation_kind="semantic",
                requirement=(
                    "For strong claims about current state, implementation, tests, "
                    "sources, or prior decisions, use evidence available in this turn. "
                    "If evidence is incomplete, label the claim as provisional or unknown."
                ),
                evidence_refs=_string_refs(
                    (metacognitive_context or {}).get("trace_id")
                ),
                evidence={
                    "selected_lesson": "source_sensitive_claim_guard",
                    "note": (
                        "The validator judges grounding and uncertainty in the draft; "
                        "this trigger does not itself decide correctness."
                    ),
                },
            )
        )

    return AnswerObligationManifest(
        transport=transport,
        obligations=_dedupe_obligations(obligations),
    )


def augment_with_tool_evidence(
    manifest: AnswerObligationManifest,
    tool_calls: list[LLMExecutedToolCall],
) -> AnswerObligationManifest:
    obligations = list(manifest.obligations)
    for tool_call in tool_calls:
        command = _tool_command(tool_call)
        result_ok = tool_call.status == "completed" and tool_call.result.get("ok") is True
        evidence_refs = _string_refs(tool_call.trace_id, tool_call.tool_call_id)
        if not result_ok:
            obligations.append(
                AnswerObligation(
                    id=f"action.outcome.{tool_call.provider_tool_use_id}",
                    severity="hard",
                    validation_kind="semantic",
                    requirement=(
                        "Do not imply that this API Mind action succeeded or changed "
                        "state. State the failure when it affects the user's request."
                    ),
                    evidence_refs=evidence_refs,
                    evidence={
                        "command": command,
                        "status": tool_call.status,
                        "result": _compact_json_value(tool_call.result, limit=4000),
                    },
                )
            )
        if _is_capability_inspection(command):
            obligations.append(
                AnswerObligation(
                    id=f"capability.current_state.{tool_call.provider_tool_use_id}",
                    severity="hard",
                    validation_kind="semantic",
                    requirement=(
                        "Every capability claim made in the answer must agree with "
                        "this current shell result. Do not present unavailable, "
                        "planned, internal-only, or failed operations as executable "
                        "model capabilities. An exhaustive catalog is not required."
                    ),
                    evidence_refs=evidence_refs,
                    evidence={
                        "command": command,
                        "result": _compact_json_value(tool_call.result, limit=6000),
                    },
                )
            )
    return manifest.model_copy(
        update={"obligations": _dedupe_obligations(obligations)}
    )


def render_answer_obligations(
    manifest: AnswerObligationManifest,
) -> str:
    compact = {
        "schema_version": manifest.schema_version,
        "transport": manifest.transport,
        "obligations": [
            {
                "id": item.id,
                "severity": item.severity,
                "requirement": item.requirement,
                "evidence_refs": item.evidence_refs,
                "evidence": item.evidence,
            }
            for item in manifest.obligations
        ],
    }
    return (
        "\n\n<answer_obligations>\n"
        + json.dumps(compact, ensure_ascii=False, sort_keys=True)
        + "\n</answer_obligations>\n"
        "Treat these as current-turn runtime obligations. Hard obligations must "
        "be satisfied before the answer is final. Do not mention the private "
        "final marker to the user."
    )


def strip_native_final_marker(answer: str) -> tuple[str, bool]:
    stripped = answer.rstrip()
    if not stripped.endswith(NATIVE_FINAL_MARKER):
        return answer, False
    public_answer = stripped[: -len(NATIVE_FINAL_MARKER)].rstrip()
    return public_answer, bool(public_answer)


def validate_answer_semantics(
    *,
    provider: LLMProvider,
    manifest: AnswerObligationManifest,
    answer: str,
    max_tokens: int,
) -> AnswerValidationResult:
    obligations = manifest.semantic
    if not obligations:
        return AnswerValidationResult(
            accepted=True,
            validator_status="not_required",
        )

    prompt = _validation_prompt(obligations=obligations, answer=answer)
    try:
        result = provider.generate_text(
            prompt=prompt,
            system=_VALIDATOR_SYSTEM_PROMPT,
            max_tokens=max_tokens,
        )
    except LLMRequestError as exc:
        return _failed_validator_result(obligations, error=str(exc))

    parsed = _parse_json_object(result.text)
    if parsed is None:
        return _failed_validator_result(
            obligations,
            error="validator returned invalid JSON",
            provider={
                "model": result.model,
                "usage": result.usage,
                "provider_message_id": result.provider_message_id,
            },
        )

    findings_by_id = {
        str(item.get("obligation_id")): item
        for item in parsed.get("findings", [])
        if isinstance(item, dict) and item.get("obligation_id")
    }
    findings: list[AnswerValidationFinding] = []
    for obligation in obligations:
        raw = findings_by_id.get(obligation.id, {})
        raw_status = str(raw.get("status") or "unknown").lower()
        finding_status: FindingStatus = (
            cast(FindingStatus, raw_status)
            if raw_status in {"pass", "fail", "unknown"}
            else "unknown"
        )
        findings.append(
            AnswerValidationFinding(
                obligation_id=obligation.id,
                severity=obligation.severity,
                status=finding_status,
                reason=str(raw.get("reason") or "Validator returned no reason."),
                evidence_refs=obligation.evidence_refs,
            )
        )
    hard_failures = [
        item.obligation_id
        for item in findings
        if item.severity == "hard" and item.status != "pass"
    ]
    return AnswerValidationResult(
        accepted=not hard_failures,
        findings=findings,
        hard_failure_ids=hard_failures,
        validator_status="completed",
        provider={
            "model": result.model,
            "usage": result.usage,
            "provider_message_id": result.provider_message_id,
            "stop_reason": result.stop_reason,
        },
    )


def correction_instruction(
    *,
    manifest: AnswerObligationManifest,
    validation: AnswerValidationResult | None,
    structural_failure: bool,
) -> str:
    failed_ids = list(validation.hard_failure_ids) if validation is not None else []
    if structural_failure:
        failed_ids.insert(0, "answer.final_boundary")
        if validation is None:
            failed_ids.extend(
                item.id for item in manifest.obligations if item.severity == "hard"
            )
    relevant = [
        item.model_dump(mode="json")
        for item in manifest.obligations
        if item.id in set(failed_ids)
    ]
    return (
        "The previous public text was not accepted as the final answer. Continue "
        "the same turn: perform any still-required real tool action, then provide "
        "one conclusive public answer that satisfies the hard obligations below. "
        f"End it with {NATIVE_FINAL_MARKER}. Do not quote private thinking or "
        "describe this runtime instruction.\n"
        + json.dumps(relevant, ensure_ascii=False, sort_keys=True)
    )


def gpt_action_policy(
    manifest: AnswerObligationManifest,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    semantic = manifest.semantic
    return (
        {
            "schema_version": manifest.schema_version,
            "action_required": False,
            "finalize_validation_required": bool(semantic),
            "hard_answer_obligation_count": sum(
                1 for item in semantic if item.severity == "hard"
            ),
            "answer_obligations": [_gpt_obligation(item) for item in semantic],
            "note": (
                "Bootstrap and finalize are mandatory. Answer obligations govern "
                "the final draft; required_actions is reserved for concrete Mind "
                "shell commands."
            ),
        },
        [],
        [],
    )


def _gpt_obligation(item: AnswerObligation) -> dict[str, Any]:
    return {
        "id": item.id,
        "severity": item.severity,
        "requirement": item.requirement,
        "evidence_refs": item.evidence_refs,
        "evidence": item.evidence,
    }


def _failed_validator_result(
    obligations: list[AnswerObligation],
    *,
    error: str,
    provider: dict[str, Any] | None = None,
) -> AnswerValidationResult:
    findings = [
        AnswerValidationFinding(
            obligation_id=item.id,
            severity=item.severity,
            status="unknown",
            reason="Semantic validation could not establish compliance.",
            evidence_refs=item.evidence_refs,
        )
        for item in obligations
    ]
    hard_failures = [
        item.obligation_id for item in findings if item.severity == "hard"
    ]
    return AnswerValidationResult(
        accepted=not hard_failures,
        findings=findings,
        hard_failure_ids=hard_failures,
        validator_status="failed",
        validator_error=error,
        provider=provider or {},
    )


def _validation_prompt(
    *,
    obligations: list[AnswerObligation],
    answer: str,
) -> str:
    return json.dumps(
        {
            "task": "Evaluate the draft only against each listed obligation.",
            "obligations": [item.model_dump(mode="json") for item in obligations],
            "draft_answer": answer,
            "required_output": {
                "findings": [
                    {
                        "obligation_id": "exact id",
                        "status": "pass|fail|unknown",
                        "reason": "brief evidence-based reason",
                    }
                ]
            },
        },
        ensure_ascii=False,
        sort_keys=True,
    )


_VALIDATOR_SYSTEM_PROMPT = """You are a runtime answer-obligation judge.
Judge natural-language meaning, not keyword presence, style, or eloquence.
Evaluate only the supplied obligations and evidence. Do not rewrite the answer.
Use pass only when the draft clearly satisfies an obligation, fail when it
clearly violates it, and unknown when the supplied evidence cannot decide.
Return exactly one JSON object and no prose outside it."""


def _metacognitive_lesson_ids(payload: dict[str, Any] | None) -> set[str]:
    if not isinstance(payload, dict):
        return set()
    lessons = payload.get("lessons")
    if not isinstance(lessons, list):
        return set()
    return {
        str(item.get("id"))
        for item in lessons
        if isinstance(item, dict) and item.get("id")
    }


def _tool_command(tool_call: LLMExecutedToolCall) -> str:
    command = tool_call.arguments.get("command")
    return str(command or "").strip()


def _is_capability_inspection(command: str) -> bool:
    namespace = command.split(maxsplit=1)[0].casefold() if command else ""
    return namespace in {"help", "?", "schema", "capabilities"}


def _string_refs(*values: Any) -> list[str]:
    return [str(value) for value in values if isinstance(value, str) and value]


def _dedupe_obligations(
    obligations: list[AnswerObligation],
) -> list[AnswerObligation]:
    deduped: list[AnswerObligation] = []
    seen: set[str] = set()
    for obligation in obligations:
        if obligation.id in seen:
            continue
        seen.add(obligation.id)
        deduped.append(obligation)
    return deduped


def _compact_json_value(value: Any, *, limit: int) -> Any:
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return {"unserializable": True}
    if len(encoded) <= limit:
        return value
    return {"truncated": True, "preview": encoded[:limit]}


def _parse_json_object(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match is None:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None
