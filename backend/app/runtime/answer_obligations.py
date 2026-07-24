"""Traceable final-answer obligations shared by native and GPT transports."""

from __future__ import annotations

import json
import re
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from app.llm.provider import LLMExecutedToolCall, LLMProvider, LLMRequestError
from app.mind.command_registry import validate_shell_command


ANSWER_OBLIGATIONS_VERSION = "answer-obligations-v3"
ANSWER_VALIDATION_VERSION = "answer-validation-v1"
_ACTION_ATTEMPT_CHAIN_LIMIT = 6

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
    obligations = [
        item
        for item in manifest.obligations
        if not _is_tool_derived_obligation(item)
    ]
    for index, tool_call in enumerate(tool_calls):
        command = _tool_command(tool_call)
        result_ok = _tool_result_ok(tool_call)
        evidence_refs = _string_refs(tool_call.trace_id, tool_call.tool_call_id)
        later_same_operation = _later_same_operation_attempts(
            tool_calls,
            failed_index=index,
        )
        recovery_candidates = (
            later_same_operation
            if _tool_failure_recoverable(tool_call)
            and any(_tool_result_ok(item) for item in later_same_operation)
            else []
        )
        if not result_ok:
            if recovery_candidates:
                evidence_refs = _string_refs(
                    *evidence_refs,
                    *[
                        ref
                        for candidate in recovery_candidates
                        for ref in (candidate.trace_id, candidate.tool_call_id)
                    ],
                )
            obligations.append(
                AnswerObligation(
                    id=f"action.outcome.{tool_call.provider_tool_use_id}",
                    severity="hard",
                    validation_kind="semantic",
                    requirement=_action_outcome_requirement(
                        has_recovery_candidates=bool(recovery_candidates)
                    ),
                    evidence_refs=evidence_refs,
                    evidence=_action_outcome_evidence(
                        tool_call,
                        recovery_candidates=recovery_candidates,
                    ),
                )
            )
        if _is_capability_inspection(command) and not (
            not result_ok and recovery_candidates
        ):
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
        "be satisfied before the answer is final."
    )


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
    validation: AnswerValidationResult,
) -> str:
    failed_ids = list(validation.hard_failure_ids)
    relevant = [
        item.model_dump(mode="json")
        for item in manifest.obligations
        if item.id in set(failed_ids)
    ]
    return (
        "The previous public text was not accepted as the final answer. Continue "
        "the same turn: perform any still-required real tool action, then provide "
        "one conclusive public answer that satisfies the hard obligations below. "
        "Do not describe this runtime instruction.\n"
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


def _tool_intent(tool_call: LLMExecutedToolCall) -> str:
    intent = tool_call.arguments.get("intent")
    return str(intent or "").strip()


def _tool_result_ok(tool_call: LLMExecutedToolCall) -> bool:
    return tool_call.status == "completed" and tool_call.result.get("ok") is True


def _tool_failure_recoverable(tool_call: LLMExecutedToolCall) -> bool:
    error = tool_call.result.get("error")
    return (
        not _tool_result_ok(tool_call)
        and isinstance(error, dict)
        and error.get("recoverable") is True
    )


def _tool_operation_key(tool_call: LLMExecutedToolCall) -> str | None:
    result = tool_call.result.get("result")
    if isinstance(result, dict):
        target = result.get("target")
        if isinstance(target, str) and target:
            return target.casefold()

        command_validation = result.get("command_validation")
        if isinstance(command_validation, dict):
            namespace = command_validation.get("canonical_namespace")
            action = command_validation.get("canonical_action")
            if isinstance(namespace, str) and namespace:
                return _operation_key(namespace, action)

    command = _tool_command(tool_call)
    if not command:
        return None
    validation = validate_shell_command(command)
    namespace = validation.get("canonical_namespace")
    action = validation.get("canonical_action")
    if not isinstance(namespace, str) or not namespace:
        return None
    return _operation_key(namespace, action)


def _operation_key(namespace: str, action: Any) -> str:
    normalized_namespace = namespace.casefold()
    normalized_action = str(action or "").casefold()
    return (
        f"{normalized_namespace}.{normalized_action}"
        if normalized_action
        else normalized_namespace
    )


def _later_same_operation_attempts(
    tool_calls: list[LLMExecutedToolCall],
    *,
    failed_index: int,
) -> list[LLMExecutedToolCall]:
    failed_key = _tool_operation_key(tool_calls[failed_index])
    if failed_key is None:
        return []
    matching = [
        item
        for item in tool_calls[failed_index + 1 :]
        if _tool_operation_key(item) == failed_key
    ]
    return matching[:_ACTION_ATTEMPT_CHAIN_LIMIT]


def _action_outcome_requirement(*, has_recovery_candidates: bool) -> str:
    if not has_recovery_candidates:
        return (
            "Do not imply that this API Mind action succeeded or changed state. "
            "State the failure when it affects the user's request."
        )
    return (
        "Judge the complete action-attempt chain, not the first failure alone. "
        "The initial attempt failed. A later same-operation attempt is only a "
        "recovery candidate: if its command, intent, and result prove that it "
        "materially completed the same intended action, the answer may state the "
        "final success without implying that the first attempt succeeded. If the "
        "later action is not materially equivalent, do not use it to overwrite "
        "the failed outcome. Mention the recovery only when it matters to the user."
    )


def _action_outcome_evidence(
    failed: LLMExecutedToolCall,
    *,
    recovery_candidates: list[LLMExecutedToolCall],
) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "operation_key": _tool_operation_key(failed),
        "initial_attempt": _tool_attempt_evidence(failed),
        "recovery_decision": (
            "semantic_validator_required"
            if recovery_candidates
            else "no_recovery_candidate"
        ),
    }
    if recovery_candidates:
        evidence["later_same_operation_attempts"] = [
            _tool_attempt_evidence(item) for item in recovery_candidates
        ]
        evidence["note"] = (
            "Same operation is a deterministic candidate-recall boundary, not "
            "proof of equivalent intent or successful recovery."
        )
    return evidence


def _tool_attempt_evidence(tool_call: LLMExecutedToolCall) -> dict[str, Any]:
    return {
        "provider_tool_use_id": tool_call.provider_tool_use_id,
        "tool_call_id": tool_call.tool_call_id,
        "trace_id": tool_call.trace_id,
        "command": _tool_command(tool_call),
        "intent": _tool_intent(tool_call),
        "status": tool_call.status,
        "result_ok": _tool_result_ok(tool_call),
        "result": _compact_json_value(tool_call.result, limit=4000),
    }


def _is_capability_inspection(command: str) -> bool:
    namespace = command.split(maxsplit=1)[0].casefold() if command else ""
    return namespace in {"help", "?", "schema", "capabilities"}


def _is_tool_derived_obligation(obligation: AnswerObligation) -> bool:
    return obligation.id.startswith(
        ("action.outcome.", "capability.current_state.")
    )


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
