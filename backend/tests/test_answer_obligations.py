import json

from app.llm.provider import LLMExecutedToolCall, LLMTextResult
from app.runtime.answer_obligations import (
    NATIVE_FINAL_MARKER,
    AnswerObligationManifest,
    AnswerObligation,
    augment_with_tool_evidence,
    compile_answer_obligations,
    correction_instruction,
    gpt_action_policy,
    strip_native_final_marker,
    validate_answer_semantics,
)


class FakeAnswerValidator:
    def __init__(self, findings: list[dict]) -> None:
        self.findings = findings

    def generate_text(self, **_kwargs) -> LLMTextResult:
        return LLMTextResult(
            model="answer-validator-test",
            text=json.dumps({"findings": self.findings}),
            usage={"input_tokens": 10, "output_tokens": 5},
        )


def test_native_manifest_compiles_structural_conflict_and_source_obligations() -> None:
    manifest = compile_answer_obligations(
        transport="native",
        memory_context={
            "trace_id": "trace_memory",
            "conflicts": [
                {
                    "classification": "atomic_fact_conflict",
                    "entity": "project",
                    "predicate": "status",
                    "memory_ids": ["mem_a", "mem_b"],
                }
            ],
        },
        metacognitive_context={
            "trace_id": "trace_meta",
            "lessons": [{"id": "source_sensitive_claim_guard"}],
        },
    )

    assert [item.id for item in manifest.obligations] == [
        "answer.final_boundary",
        "memory.active_conflict_disclosure",
        "evidence.source_sensitive_claim",
    ]
    assert manifest.obligations[0].validation_kind == "structural"
    assert all(item.severity == "hard" for item in manifest.obligations)


def test_tool_evidence_adds_failed_action_and_capability_obligations() -> None:
    manifest = AnswerObligationManifest(transport="gpt_bridge")
    tool_call = LLMExecutedToolCall(
        provider_tool_use_id="toolu_help",
        tool_name="mind_shell",
        arguments={"command": "help memory", "intent": "Inspect capabilities."},
        result={
            "ok": False,
            "error_code": "mind.command_unavailable",
            "error_message": "Command unavailable.",
        },
        status="error",
        tool_call_id="tool_1",
        trace_id="trace_tool",
    )

    augmented = augment_with_tool_evidence(manifest, [tool_call])

    assert [item.id for item in augmented.semantic] == [
        "action.outcome.toolu_help",
        "capability.current_state.toolu_help",
    ]
    policy, required, recommended = gpt_action_policy(augmented)
    assert policy["action_required"] is False
    assert [item["id"] for item in policy["answer_obligations"]] == [
        "action.outcome.toolu_help",
        "capability.current_state.toolu_help",
    ]
    assert required == []
    assert recommended == []


def test_semantic_validator_fails_closed_for_hard_unknown() -> None:
    manifest = compile_answer_obligations(
        transport="gpt_bridge",
        memory_context={
            "trace_id": "trace_memory",
            "conflicts": [{"memory_ids": ["mem_a", "mem_b"]}],
        },
        metacognitive_context=None,
    )
    provider = FakeAnswerValidator(
        [
            {
                "obligation_id": "memory.active_conflict_disclosure",
                "status": "unknown",
                "reason": "The draft does not establish how it handles the conflict.",
            }
        ]
    )

    validation = validate_answer_semantics(
        provider=provider,
        manifest=manifest,
        answer="La decisione e definitiva.",
        max_tokens=1024,
    )

    assert validation.accepted is False
    assert validation.hard_failure_ids == ["memory.active_conflict_disclosure"]
    assert validation.validator_status == "completed"


def test_semantic_validator_accepts_natural_conflict_disclosure() -> None:
    manifest = compile_answer_obligations(
        transport="gpt_bridge",
        memory_context={
            "trace_id": "trace_memory",
            "conflicts": [{"memory_ids": ["mem_a", "mem_b"]}],
        },
        metacognitive_context=None,
    )
    provider = FakeAnswerValidator(
        [
            {
                "obligation_id": "memory.active_conflict_disclosure",
                "status": "pass",
                "reason": "The draft explicitly keeps both versions unresolved.",
            }
        ]
    )

    validation = validate_answer_semantics(
        provider=provider,
        manifest=manifest,
        answer="Ho due versioni attive incompatibili; non ne scelgo una senza fonte.",
        max_tokens=1024,
    )

    assert validation.accepted is True
    assert validation.hard_failure_ids == []


def test_native_final_marker_is_stripped_only_at_the_final_boundary() -> None:
    public, accepted = strip_native_final_marker(
        f"Risposta completa.\n{NATIVE_FINAL_MARKER}\n"
    )
    assert accepted is True
    assert public == "Risposta completa."

    unchanged, accepted = strip_native_final_marker(
        f"Cito {NATIVE_FINAL_MARKER} ma continuo a scrivere."
    )
    assert accepted is False
    assert unchanged.endswith("continuo a scrivere.")


def test_warning_and_advisory_findings_are_traced_without_blocking() -> None:
    manifest = AnswerObligationManifest(
        transport="gpt_bridge",
        obligations=[
            AnswerObligation(
                id="style.warning",
                severity="warning",
                validation_kind="semantic",
                requirement="Prefer a concise answer when practical.",
            ),
            AnswerObligation(
                id="style.advisory",
                severity="advisory",
                validation_kind="semantic",
                requirement="Acknowledge uncertainty when useful.",
            ),
        ],
    )
    provider = FakeAnswerValidator(
        [
            {
                "obligation_id": "style.warning",
                "status": "fail",
                "reason": "The draft is verbose.",
            },
            {
                "obligation_id": "style.advisory",
                "status": "unknown",
                "reason": "No uncertainty is present.",
            },
        ]
    )

    validation = validate_answer_semantics(
        provider=provider,
        manifest=manifest,
        answer="Una risposta volutamente molto lunga.",
        max_tokens=1024,
    )

    assert validation.accepted is True
    assert validation.hard_failure_ids == []
    assert [item.status for item in validation.findings] == ["fail", "unknown"]


def test_structural_recovery_repeats_unassessed_hard_semantic_obligations() -> None:
    manifest = AnswerObligationManifest(
        transport="native",
        obligations=[
            AnswerObligation(
                id="answer.final_boundary",
                severity="hard",
                validation_kind="structural",
                requirement="End with the private final marker.",
            ),
            AnswerObligation(
                id="action.outcome.failed",
                severity="hard",
                validation_kind="semantic",
                requirement="Do not claim the failed action succeeded.",
            ),
        ],
    )

    instruction = correction_instruction(
        manifest=manifest,
        validation=None,
        structural_failure=True,
    )

    assert "answer.final_boundary" in instruction
    assert "action.outcome.failed" in instruction
