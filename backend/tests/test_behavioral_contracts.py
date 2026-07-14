import pytest
from pydantic import ValidationError

from app.evals.behavioral_contracts import (
    BehavioralJudgment,
    BehavioralRunRecord,
    BehavioralScenario,
    BehavioralSuite,
)


def _scenario() -> dict:
    return {
        "id": "BEH-0001",
        "branch": "memory",
        "capability": "manual semantic recall",
        "objective": "Verify that Scarlet retrieves and uses a known preference.",
        "natural_user_prompt": "Che cosa mi consiglieresti da bere questa sera?",
        "starting_condition": {
            "database_role": "preliminary",
            "database_fingerprint": "a" * 64,
            "mutation_policy": "disposable_copy",
            "session_arrangement": "new_session",
            "references": [
                {
                    "kind": "memory",
                    "id": "mem_fixture",
                    "expected": {"status": "active"},
                    "purpose": "Known source preference for the expected retrieval.",
                }
            ],
        },
        "expected_evidence": {
            "required_shell_commands": ["memory search"],
            "required_trace_kinds": ["mind.memory.search"],
            "forbidden_state_changes": ["memory write"],
        },
        "response_rubric": {
            "required_semantics": ["uses the caffeine-free preference"],
            "forbidden_claims": ["claims a medical diagnosis"],
            "evidence_use": "The recommendation must be grounded in the referenced memory.",
            "user_value": "The answer should remain natural and useful.",
        },
        "repetitions": 3,
        "independence_rule": "Each repetition starts from a fresh copy of the same DB.",
    }


def test_behavioral_scenario_requires_real_starting_evidence_and_two_level_rubric() -> None:
    scenario = BehavioralScenario.model_validate(_scenario())

    assert scenario.schema_version == "behavioral-scenario-v1"
    assert scenario.starting_condition.references[0].id == "mem_fixture"
    assert scenario.repetitions == 3

    invalid = _scenario()
    invalid["expected_evidence"] = {}
    with pytest.raises(ValidationError):
        BehavioralScenario.model_validate(invalid)


def test_behavioral_run_acceptance_requires_all_four_layers() -> None:
    common = {"status": "pass", "evidence": ["trace_fixture"]}
    run = BehavioralRunRecord.model_validate(
        {
            "scenario_id": "BEH-0001",
            "run_id": "run_fixture",
            "started_from_fingerprint": "sha256:fixture",
            "session_ids": ["ses_fixture"],
            "turn_ids": ["turn_fixture"],
            "response_text": "Una tisana senza caffeina.",
            "technical_execution": common,
            "cognitive_choice": common,
            "answer_outcome": common,
            "longitudinal_effect": common,
        }
    )

    assert run.accepted is True
    failed = run.model_copy(
        update={
            "answer_outcome": run.answer_outcome.model_copy(
                update={"status": "fail"}
            )
        }
    )
    assert failed.accepted is False


def test_behavioral_suite_requires_complete_ordered_groups() -> None:
    scenario = _scenario()
    suite = BehavioralSuite.model_validate(
        {
            "id": "fixture-suite",
            "title": "Fixture suite",
            "baseline_database": "data/fixture.db",
            "database_fingerprint": "a" * 64,
            "comparison_policy": "Objective facts are automatic; language is reviewed.",
            "groups": [
                {
                    "id": "memory",
                    "purpose": "fixture",
                    "scenario_ids": ["BEH-0001"],
                    "repetitions": 3,
                    "independence_rule": "fresh copy",
                }
            ],
            "scenarios": [scenario],
        }
    )

    assert suite.groups[0].scenario_ids == ["BEH-0001"]

    invalid = suite.model_dump(mode="json")
    invalid["groups"][0]["scenario_ids"] = []
    with pytest.raises(ValidationError):
        BehavioralSuite.model_validate(invalid)


def test_qualitative_judgment_requires_reasoned_human_style_review() -> None:
    payload = {
        "run_id": "run_fixture",
        "scenario_id": "BEH-0001",
        "evaluator_identity": "Codex project evaluator",
        "criteria_source": "behavioral-scenario-v1 response rubric",
        "reviewed_at": "2026-07-14T10:00:00Z",
        "cognitive_choice": {
            "status": "pass",
            "evidence": ["trace_fixture"],
            "notes": "The selected action was proportionate to the request.",
            "evaluator": "llm_as_human",
        },
        "answer_outcome": {
            "status": "pass",
            "evidence": ["answer_fixture"],
            "notes": "The answer used the evidence naturally.",
            "evaluator": "llm_as_human",
        },
        "longitudinal_effect": {
            "status": "pass",
            "evidence": ["state_fixture"],
            "notes": "The intended state remained coherent.",
            "evaluator": "llm_as_human",
        },
    }

    judgment = BehavioralJudgment.model_validate(payload)
    assert judgment.answer_outcome.evaluator == "llm_as_human"

    payload["answer_outcome"]["notes"] = None
    with pytest.raises(ValidationError):
        BehavioralJudgment.model_validate(payload)
