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
    resolve_native_final_boundary,
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


def _shell_attempt(
    *,
    provider_id: str,
    command: str,
    intent: str,
    ok: bool,
    target: str | None = None,
    recoverable: bool = True,
) -> LLMExecutedToolCall:
    result: dict = {
        "ok": ok,
        "result": {
            "operation": "mind_shell.command",
        },
    }
    if target is not None:
        result["result"]["target"] = target
    if not ok:
        result["error"] = {
            "code": "shell.invalid_command",
            "message": "The command needs correction.",
            "recoverable": recoverable,
        }
    return LLMExecutedToolCall(
        provider_tool_use_id=provider_id,
        tool_name="mind_shell",
        arguments={"command": command, "intent": intent},
        result=result,
        status="completed" if ok else "error",
        tool_call_id=f"call_{provider_id}",
        trace_id=f"trace_{provider_id}",
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


def test_tool_evidence_links_later_same_operation_success_without_erasing_failure() -> None:
    failed = _shell_attempt(
        provider_id="failed_write",
        command="memory write",
        intent="Remember the user's evaluation preference.",
        ok=False,
    )
    succeeded = _shell_attempt(
        provider_id="successful_write",
        command=(
            'memory write --type user_preference --scope user '
            '--content "Prefer observed behavior before scores" '
            '--reason "Future evaluations"'
        ),
        intent="Remember the user's evaluation preference.",
        ok=True,
        target="memory.write",
    )

    augmented = augment_with_tool_evidence(
        AnswerObligationManifest(transport="native"),
        [failed, succeeded],
    )

    assert [item.id for item in augmented.semantic] == [
        "action.outcome.failed_write"
    ]
    obligation = augmented.semantic[0]
    assert obligation.evidence_refs == [
        "trace_failed_write",
        "call_failed_write",
        "trace_successful_write",
        "call_successful_write",
    ]
    assert obligation.evidence["operation_key"] == "memory.write"
    assert obligation.evidence["recovery_decision"] == (
        "semantic_validator_required"
    )
    attempts = obligation.evidence["later_same_operation_attempts"]
    assert len(attempts) == 1
    assert attempts[0]["result_ok"] is True
    assert "only a recovery candidate" in obligation.requirement


def test_tool_evidence_rebuilds_stale_persisted_action_obligation() -> None:
    failed = _shell_attempt(
        provider_id="failed_write",
        command="memory write",
        intent="Remember a preference.",
        ok=False,
    )
    succeeded = _shell_attempt(
        provider_id="successful_write",
        command=(
            'memory write --type user_preference --content "X" '
            '--reason "Y"'
        ),
        intent="Remember a preference.",
        ok=True,
        target="memory.write",
    )
    persisted_after_failure = augment_with_tool_evidence(
        AnswerObligationManifest(transport="gpt_bridge"),
        [failed],
    )
    assert persisted_after_failure.semantic[0].evidence[
        "recovery_decision"
    ] == "no_recovery_candidate"

    rebuilt = augment_with_tool_evidence(
        persisted_after_failure,
        [failed, succeeded],
    )

    assert len(rebuilt.semantic) == 1
    assert rebuilt.semantic[0].evidence["recovery_decision"] == (
        "semantic_validator_required"
    )
    assert rebuilt.semantic[0].evidence_refs[-2:] == [
        "trace_successful_write",
        "call_successful_write",
    ]


def test_tool_evidence_rebuild_preserves_static_obligations() -> None:
    static = AnswerObligation(
        id="memory.active_conflict_disclosure",
        severity="hard",
        validation_kind="semantic",
        requirement="Disclose the active memory conflict.",
        evidence_refs=["memory_conflict_1"],
    )
    failed = _shell_attempt(
        provider_id="failed_write",
        command="memory write",
        intent="Remember a preference.",
        ok=False,
    )

    rebuilt = augment_with_tool_evidence(
        AnswerObligationManifest(
            transport="gpt_bridge",
            obligations=[static],
        ),
        [failed],
    )

    assert [item.id for item in rebuilt.semantic] == [
        "memory.active_conflict_disclosure",
        "action.outcome.failed_write",
    ]
    assert rebuilt.semantic[0] == static


def test_tool_evidence_keeps_same_operation_retry_as_semantic_candidate_only() -> None:
    failed = _shell_attempt(
        provider_id="failed_user_memory",
        command="memory write",
        intent="Remember the user's food preference.",
        ok=False,
    )
    different_intent = _shell_attempt(
        provider_id="project_memory",
        command=(
            'memory write --type project_fact --scope project '
            '--content "The API uses FastAPI" --reason "Project continuity"'
        ),
        intent="Remember a project implementation fact.",
        ok=True,
        target="memory.write",
    )
    manifest = augment_with_tool_evidence(
        AnswerObligationManifest(transport="native"),
        [failed, different_intent],
    )

    obligation = manifest.semantic[0]
    assert obligation.severity == "hard"
    assert obligation.evidence["recovery_decision"] == (
        "semantic_validator_required"
    )
    assert obligation.evidence["note"].startswith(
        "Same operation is a deterministic candidate-recall boundary"
    )

    validation = validate_answer_semantics(
        provider=FakeAnswerValidator(
            [
                {
                    "obligation_id": obligation.id,
                    "status": "fail",
                    "reason": "The later project memory does not recover the user memory.",
                }
            ]
        ),
        manifest=manifest,
        answer="La preferenza alimentare e stata salvata.",
        max_tokens=1024,
    )
    assert validation.accepted is False


def test_tool_evidence_does_not_link_different_or_nonrecoverable_attempts() -> None:
    different_operation = augment_with_tool_evidence(
        AnswerObligationManifest(transport="native"),
        [
            _shell_attempt(
                provider_id="failed_write",
                command="memory write",
                intent="Remember a preference.",
                ok=False,
            ),
            _shell_attempt(
                provider_id="search",
                command='memory search "preference"',
                intent="Search memory.",
                ok=True,
                target="memory.search",
            ),
        ],
    )
    assert different_operation.semantic[0].evidence["recovery_decision"] == (
        "no_recovery_candidate"
    )

    nonrecoverable = augment_with_tool_evidence(
        AnswerObligationManifest(transport="native"),
        [
            _shell_attempt(
                provider_id="denied_write",
                command="memory write",
                intent="Remember a preference.",
                ok=False,
                recoverable=False,
            ),
            _shell_attempt(
                provider_id="later_write",
                command=(
                    'memory write --type user_preference --content "X" '
                    '--reason "Y"'
                ),
                intent="Remember a preference.",
                ok=True,
                target="memory.write",
            ),
        ],
    )
    assert nonrecoverable.semantic[0].evidence["recovery_decision"] == (
        "no_recovery_candidate"
    )


def test_tool_evidence_requires_success_after_failure() -> None:
    manifest = augment_with_tool_evidence(
        AnswerObligationManifest(transport="native"),
        [
            _shell_attempt(
                provider_id="early_success",
                command=(
                    'memory write --type project_fact --content "X" '
                    '--reason "Y"'
                ),
                intent="Store X.",
                ok=True,
                target="memory.write",
            ),
            _shell_attempt(
                provider_id="later_failure",
                command="memory write",
                intent="Store Y.",
                ok=False,
            ),
        ],
    )

    assert manifest.semantic[0].evidence["recovery_decision"] == (
        "no_recovery_candidate"
    )


def test_recovered_capability_check_uses_later_current_result() -> None:
    manifest = augment_with_tool_evidence(
        AnswerObligationManifest(transport="gpt_bridge"),
        [
            _shell_attempt(
                provider_id="failed_help",
                command="help memory",
                intent="Inspect current memory commands.",
                ok=False,
            ),
            _shell_attempt(
                provider_id="successful_help",
                command="help memory",
                intent="Inspect current memory commands.",
                ok=True,
            ),
        ],
    )

    assert [item.id for item in manifest.semantic] == [
        "action.outcome.failed_help",
        "capability.current_state.successful_help",
    ]
    assert manifest.semantic[0].evidence["operation_key"] == "help.memory"


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


def test_native_final_boundary_uses_provider_end_turn_without_requiring_marker() -> None:
    public, accepted, marker_stripped, source = resolve_native_final_boundary(
        "Risposta completa.",
        stop_reason="end_turn",
    )

    assert public == "Risposta completa."
    assert accepted is True
    assert marker_stripped is False
    assert source == "provider_end_turn"


def test_native_final_boundary_rejects_non_terminal_or_empty_provider_output() -> None:
    truncated = resolve_native_final_boundary(
        "Risposta interrotta.",
        stop_reason="max_tokens",
    )
    empty = resolve_native_final_boundary("", stop_reason="end_turn")

    assert truncated == ("Risposta interrotta.", False, False, None)
    assert empty == ("", False, False, None)


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
                requirement="Return one non-empty provider terminal answer.",
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
