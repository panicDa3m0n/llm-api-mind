"""Versioned contracts for evidence-grounded Scarlet behavior evaluations.

The contracts deliberately separate objective runtime observations from
qualitative judgment. Exact IDs, traces, commands, and persisted state can be
checked mechanically. Cognitive usefulness and natural-language quality must
be judged against an explicit rubric and supporting evidence.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


BEHAVIORAL_SCENARIO_VERSION = "behavioral-scenario-v1"
BEHAVIORAL_SUITE_VERSION = "behavioral-suite-v1"

BEHAVIORAL_RUNTIME_CONFIGURATION_VALUES: dict[str, set[Any]] = {
    "model_context_profile": {"legacy", "v2_shadow", "v2"},
    "organ_focus_mode": {"off", "model"},
    "organ_volition_mode": {"off", "manual", "model"},
    "organ_affect_mode": {"off", "shadow", "model"},
    "metacognitive_context_mode": {"off", "shadow", "inject"},
    "metacognitive_context_max_lessons": {1, 2, 3, 4, 5},
    "agent_mode_default": {"idle", "interactive", "scouting"},
    "agent_mode_routing": {"off", "shadow", "active"},
}


def validate_behavioral_runtime_configuration(
    configuration: dict[str, Any],
) -> dict[str, Any]:
    """Keep evaluation variants cognitive, explicit, and non-sensitive."""
    unknown = sorted(set(configuration) - set(BEHAVIORAL_RUNTIME_CONFIGURATION_VALUES))
    if unknown:
        raise ValueError(
            "Behavioral runtime configuration contains unsafe or unsupported "
            f"settings: {unknown}"
        )
    invalid = {
        key: value
        for key, value in configuration.items()
        if value not in BEHAVIORAL_RUNTIME_CONFIGURATION_VALUES[key]
    }
    if invalid:
        raise ValueError(
            "Behavioral runtime configuration contains invalid values: "
            f"{invalid}"
        )
    return configuration


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
        "mode",
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
    forbidden_shell_commands: list[str] = Field(default_factory=list)
    required_trace_kinds: list[str] = Field(default_factory=list)
    required_event_types: list[str] = Field(default_factory=list)
    required_state: dict[str, Any] = Field(default_factory=dict)
    forbidden_state_changes: list[str] = Field(default_factory=list)


class ResponseRubric(BaseModel):
    required_semantics: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    evidence_use: str
    user_value: str


class BehavioralScenarioGroup(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    purpose: str
    scenario_ids: list[str] = Field(min_length=1)
    repetitions: int = Field(default=3, ge=1, le=20)
    independence_rule: str
    runtime_configuration: dict[str, Any] = Field(default_factory=dict)

    @field_validator("runtime_configuration")
    @classmethod
    def validate_runtime_configuration(
        cls, configuration: dict[str, Any]
    ) -> dict[str, Any]:
        return validate_behavioral_runtime_configuration(configuration)


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
                evidence.forbidden_shell_commands,
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


class BehavioralSuite(BaseModel):
    schema_version: Literal["behavioral-suite-v1"] = BEHAVIORAL_SUITE_VERSION
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str
    baseline_database: str
    database_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    configuration: dict[str, Any] = Field(default_factory=dict)
    comparison_policy: str
    groups: list[BehavioralScenarioGroup] = Field(min_length=1)
    scenarios: list[BehavioralScenario] = Field(min_length=1)

    @field_validator("configuration")
    @classmethod
    def validate_runtime_configuration(
        cls, configuration: dict[str, Any]
    ) -> dict[str, Any]:
        return validate_behavioral_runtime_configuration(configuration)

    @model_validator(mode="after")
    def validate_scenario_graph(self) -> "BehavioralSuite":
        scenario_by_id = {scenario.id: scenario for scenario in self.scenarios}
        if len(scenario_by_id) != len(self.scenarios):
            raise ValueError("Behavioral scenario IDs must be unique.")

        grouped_ids = [
            scenario_id
            for group in self.groups
            for scenario_id in group.scenario_ids
        ]
        if len(grouped_ids) != len(set(grouped_ids)):
            raise ValueError("Each behavioral scenario must belong to one group.")
        if set(grouped_ids) != set(scenario_by_id):
            raise ValueError("Behavioral groups must cover every scenario exactly once.")

        group_by_scenario = {
            scenario_id: group
            for group in self.groups
            for scenario_id in group.scenario_ids
        }
        for scenario in self.scenarios:
            if scenario.starting_condition.database_fingerprint != self.database_fingerprint:
                raise ValueError(
                    f"{scenario.id} does not use the suite database fingerprint."
                )
            group = group_by_scenario[scenario.id]
            if scenario.repetitions != group.repetitions:
                raise ValueError(
                    f"{scenario.id} repetitions differ from group {group.id}."
                )
            seen: set[str] = set()
            for candidate in group.scenario_ids:
                if candidate == scenario.id:
                    break
                seen.add(candidate)
            missing = set(scenario.starting_condition.prerequisite_scenario_ids) - seen
            if missing:
                raise ValueError(
                    f"{scenario.id} prerequisites must appear earlier in its group: "
                    f"{sorted(missing)}"
                )
        return self


class EvaluationLayerResult(BaseModel):
    status: Literal["pass", "fail", "inconclusive"]
    evidence: list[str] = Field(default_factory=list)
    notes: str | None = None
    evaluator: Literal["deterministic", "human", "llm_as_human", "pending"] = (
        "deterministic"
    )


class BehavioralJudgment(BaseModel):
    schema_version: Literal["behavioral-judgment-v1"] = "behavioral-judgment-v1"
    run_id: str
    scenario_id: str
    evaluator_identity: str
    criteria_source: str
    reviewed_at: datetime
    cognitive_choice: EvaluationLayerResult
    answer_outcome: EvaluationLayerResult
    longitudinal_effect: EvaluationLayerResult

    @model_validator(mode="after")
    def require_qualitative_evaluator(self) -> "BehavioralJudgment":
        for layer in (
            self.cognitive_choice,
            self.answer_outcome,
            self.longitudinal_effect,
        ):
            if layer.evaluator not in {"human", "llm_as_human"}:
                raise ValueError(
                    "Qualitative judgments require a human or llm_as_human evaluator."
                )
            if not layer.notes:
                raise ValueError("Every qualitative judgment needs a rationale.")
        return self


class BehavioralRunRecord(BaseModel):
    schema_version: Literal["behavioral-run-v1"] = "behavioral-run-v1"
    scenario_id: str
    run_id: str
    group_id: str | None = None
    repetition: int = Field(default=1, ge=1)
    started_from_fingerprint: str
    scenario_definition_digest: str | None = None
    provider: str | None = None
    model: str | None = None
    completed_at: datetime | None = None
    session_ids: list[str]
    turn_ids: list[str]
    response_text: str
    technical_execution: EvaluationLayerResult
    cognitive_choice: EvaluationLayerResult
    answer_outcome: EvaluationLayerResult
    longitudinal_effect: EvaluationLayerResult
    raw_trace_ids: list[str] = Field(default_factory=list)
    observed_state_changes: list[str] = Field(default_factory=list)
    runtime_configuration: dict[str, Any] = Field(default_factory=dict)

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
