"""Versioned contracts for evidence-grounded Scarlet behavior evaluations."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


BEHAVIORAL_SCENARIO_VERSION = "behavioral-scenario-v1"


class EvidenceReference(BaseModel):
    kind: Literal[
        "memory",
        "fact",
        "session",
        "message",
        "turn",
        "focus",
        "intention",
        "affect",
        "trace",
        "event",
        "setting",
    ]
    id: str
    expected: dict[str, Any] = Field(default_factory=dict)
    purpose: str


class StartingCondition(BaseModel):
    database_role: Literal["laboratory", "test", "preliminary"]
    database_fingerprint: str
    mutation_policy: Literal["read_only", "disposable_copy"]
    session_arrangement: Literal[
        "new_session",
        "same_session",
        "continued_session",
        "separate_sessions",
    ]
    prerequisite_scenario_ids: list[str] = Field(default_factory=list)
    references: list[EvidenceReference] = Field(default_factory=list)
    configuration: dict[str, Any] = Field(default_factory=dict)


class ExpectedEvidence(BaseModel):
    required_shell_commands: list[str] = Field(default_factory=list)
    required_trace_kinds: list[str] = Field(default_factory=list)
    required_event_types: list[str] = Field(default_factory=list)
    required_state: dict[str, Any] = Field(default_factory=dict)
    forbidden_state_changes: list[str] = Field(default_factory=list)


class ResponseRubric(BaseModel):
    required_semantics: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    evidence_use: str
    user_value: str


class BehavioralScenario(BaseModel):
    schema_version: Literal["behavioral-scenario-v1"] = BEHAVIORAL_SCENARIO_VERSION
    id: str = Field(pattern=r"^BEH-[0-9]{4}$")
    branch: str
    capability: str
    objective: str
    natural_user_prompt: str
    starting_condition: StartingCondition
    expected_evidence: ExpectedEvidence
    response_rubric: ResponseRubric
    repetitions: int = Field(default=3, ge=1, le=20)
    independence_rule: str

    @model_validator(mode="after")
    def require_evaluable_expectation(self) -> "BehavioralScenario":
        evidence = self.expected_evidence
        has_technical_expectation = any(
            (
                evidence.required_shell_commands,
                evidence.required_trace_kinds,
                evidence.required_event_types,
                evidence.required_state,
                evidence.forbidden_state_changes,
            )
        )
        has_behavioral_expectation = bool(
            self.response_rubric.required_semantics
            or self.response_rubric.forbidden_claims
        )
        if not has_technical_expectation or not has_behavioral_expectation:
            raise ValueError(
                "A behavioral scenario needs both technical evidence and a "
                "response-level acceptance rubric."
            )
        return self


class EvaluationLayerResult(BaseModel):
    status: Literal["pass", "fail", "inconclusive"]
    evidence: list[str] = Field(default_factory=list)
    notes: str | None = None


class BehavioralRunRecord(BaseModel):
    schema_version: Literal["behavioral-run-v1"] = "behavioral-run-v1"
    scenario_id: str
    run_id: str
    started_from_fingerprint: str
    session_ids: list[str]
    turn_ids: list[str]
    response_text: str
    technical_execution: EvaluationLayerResult
    cognitive_choice: EvaluationLayerResult
    answer_outcome: EvaluationLayerResult
    longitudinal_effect: EvaluationLayerResult
    raw_trace_ids: list[str] = Field(default_factory=list)
    observed_state_changes: list[str] = Field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return all(
            layer.status == "pass"
            for layer in (
                self.technical_execution,
                self.cognitive_choice,
                self.answer_outcome,
                self.longitudinal_effect,
            )
        )
