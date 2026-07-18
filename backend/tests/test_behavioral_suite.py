import json
from pathlib import Path

import pytest

from app.evals.behavioral_contracts import (
    BehavioralJudgment,
    BehavioralRunRecord,
    EvaluationLayerResult,
)
from app.evals.behavioral_evidence import evaluate_objective_evidence
from app.evals.behavioral_suite import (
    _evaluation_session_payload,
    apply_judgments,
    compare_reviewed_runs,
    load_behavioral_suite,
)


CATALOG = (
    Path(__file__).resolve().parents[1]
    / "app/evals/scenarios/behavioral-v1/suite.json"
)
SCA4_CATALOG = (
    Path(__file__).resolve().parents[1]
    / "app/evals/scenarios/sca4-organs-v1/suite.json"
)


def test_natural_core_catalog_is_complete_and_non_technical() -> None:
    suite = load_behavioral_suite(CATALOG)

    assert len(suite.groups) == 8
    assert len(suite.scenarios) == 12
    assert {scenario.capability for scenario in suite.scenarios} >= {
        "automatic semantic recall",
        "semantic-to-episodic provenance navigation",
        "focus creation",
        "self-generated volition",
        "affective appraisal",
        "source-sensitive self-review",
        "resumable agent posture",
    }
    forbidden_prompt_fragments = (
        "memory search",
        "session open",
        "focus set",
        "volition create",
        "metacognition step",
        "mode set",
    )
    for scenario in suite.scenarios:
        lowered = scenario.natural_user_prompt.casefold()
        assert not any(fragment in lowered for fragment in forbidden_prompt_fragments)


def test_sca4_catalog_is_isolated_longitudinal_and_non_technical() -> None:
    suite = load_behavioral_suite(SCA4_CATALOG)

    assert len(suite.groups) == 9
    assert len(suite.scenarios) == 13
    assert sum(group.repetitions * len(group.scenario_ids) for group in suite.groups) == 26
    assert {scenario.branch for scenario in suite.scenarios} == {
        "operational-management",
        "decision-autonomy",
        "computational-affect",
        "metacognition",
    }
    group_configuration = {
        group.id: group.runtime_configuration for group in suite.groups
    }
    assert group_configuration["affect-regulation-model"] == {
        "organ_affect_mode": "model"
    }
    assert group_configuration["affect-regulation-shadow"] == {
        "organ_affect_mode": "shadow"
    }
    assert suite.configuration["organ_focus_mode"] == "off"
    assert suite.configuration["organ_volition_mode"] == "off"
    assert suite.configuration["organ_affect_mode"] == "off"
    assert {
        scenario.id
        for scenario in suite.scenarios
        if "negative control" in scenario.capability
    } == {"BEH-0103", "BEH-0113", "BEH-0125", "BEH-0132"}
    forbidden_prompt_fragments = (
        "focus set",
        "focus resolve",
        "volition create",
        "volition list",
        "metacognition step",
        "affect read",
    )
    for scenario in suite.scenarios:
        lowered = scenario.natural_user_prompt.casefold()
        assert not any(fragment in lowered for fragment in forbidden_prompt_fragments)


def test_evaluation_session_does_not_expose_scenario_identity() -> None:
    payload = _evaluation_session_payload()

    assert payload == {"title": "Conversazione con Scarlet"}
    serialized = json.dumps(payload).casefold()
    assert "behavioral" not in serialized
    assert "beh-" not in serialized
    assert "scenario" not in serialized


def test_objective_evidence_checks_commands_state_and_forbidden_mutations() -> None:
    suite = load_behavioral_suite(CATALOG)
    scenario = next(item for item in suite.scenarios if item.id == "BEH-0004")
    before = _state()
    after = _state()
    after["focus"] = {"count": 1, "active_count": 1, "records": []}
    evidence = {
        "event_types": ["runtime_context", "turn_complete"],
        "trace_kinds": ["mind.tool_call"],
        "shell_commands": [
            'focus set "continuita memoria sessioni" --reason "keep the thread"'
        ],
        "memory": {"selected_ids": [], "candidate_count": 0},
        "runtime": {"block_types": ["session_context"], "blocks": []},
        "trace_ids": ["trace_fixture"],
    }

    result = evaluate_objective_evidence(
        scenario=scenario,
        evidence=evidence,
        state_before=before,
        state_after=after,
    )

    assert result.status == "pass"

    after["volition"] = {"count": 1, "active_count": 1, "records": []}
    failed = evaluate_objective_evidence(
        scenario=scenario,
        evidence=evidence,
        state_before=before,
        state_after=after,
    )
    assert failed.status == "fail"
    assert "volition.write" in str(failed.notes)


def test_objective_oracles_do_not_require_redundant_tool_use() -> None:
    suite = load_behavioral_suite(CATALOG)
    scenario = next(item for item in suite.scenarios if item.id == "BEH-0012")
    before = _state()
    before["mode"]["preferred_tag"] = "scouting"
    after = json.loads(json.dumps(before))
    evidence = {
        "event_types": ["runtime_context", "turn_complete"],
        "trace_kinds": [],
        "shell_commands": [],
        "memory": {"selected_ids": [], "candidate_count": 0},
        "runtime": {"block_types": ["agent_mode_context"], "blocks": []},
        "trace_ids": [],
    }

    result = evaluate_objective_evidence(
        scenario=scenario,
        evidence=evidence,
        state_before=before,
        state_after=after,
    )

    assert result.status == "pass"


def test_metacognitive_oracle_allows_policy_driven_memory_consolidation() -> None:
    suite = load_behavioral_suite(CATALOG)
    scenario = next(item for item in suite.scenarios if item.id == "BEH-0010")
    before = _state()
    after = _state()
    after["memory"]["count"] = 35
    evidence = {
        "event_types": ["runtime_context", "turn_complete"],
        "trace_kinds": ["mind.tool_call"],
        "shell_commands": [
            'metacognition step --objective "calibrate reliability"',
            'memory write --type lesson --content "separate implementation and reliability"',
        ],
        "memory": {"selected_ids": [], "candidate_count": 0},
        "runtime": {"block_types": ["message_context"], "blocks": []},
        "trace_ids": ["trace_fixture"],
    }

    result = evaluate_objective_evidence(
        scenario=scenario,
        evidence=evidence,
        state_before=before,
        state_after=after,
    )

    assert result.status == "pass"


def test_judgment_application_requires_full_coverage(tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    record = _record("memory-positive-r1-BEH-0001", "BEH-0001")
    (run_dir / "records.pending.json").write_text(
        json.dumps([record.model_dump(mode="json")]), encoding="utf-8"
    )
    judgment = _judgment(record.run_id, record.scenario_id)
    judgment_path = tmp_path / "judgment.json"
    judgment_path.write_text(
        json.dumps([judgment.model_dump(mode="json")]), encoding="utf-8"
    )

    destination = apply_judgments(run_dir=run_dir, judgment_path=judgment_path)

    reviewed = json.loads(destination.read_text(encoding="utf-8"))
    assert reviewed[0]["answer_outcome"]["status"] == "pass"
    assert (run_dir / "summary.reviewed.md").exists()

    judgment_path.write_text("[]", encoding="utf-8")
    with pytest.raises(RuntimeError, match="coverage mismatch"):
        apply_judgments(run_dir=run_dir, judgment_path=judgment_path)


def test_comparator_only_auto_fails_objective_regressions(tmp_path) -> None:
    before_dir = tmp_path / "before"
    after_dir = tmp_path / "after"
    before_dir.mkdir()
    after_dir.mkdir()
    before = _record("old", "BEH-0001")
    after = _record("new", "BEH-0001").model_copy(
        update={"response_text": "A different but still reviewed natural answer."}
    )
    _write_reviewed(before_dir, before)
    _write_reviewed(after_dir, after)

    comparison = compare_reviewed_runs(before_dir=before_dir, after_dir=after_dir)

    assert comparison["objective_regressions"] == []
    assert comparison["automatically_admissible"] is True
    assert comparison["qualitative_review"][0]["decision"] == "requires_reasoned_review"

    failed_technical = EvaluationLayerResult(
        status="fail",
        evidence=["missing trace"],
        notes="Objective trace disappeared.",
    )
    after = after.model_copy(update={"technical_execution": failed_technical})
    _write_reviewed(after_dir, after)
    comparison = compare_reviewed_runs(before_dir=before_dir, after_dir=after_dir)
    assert len(comparison["objective_regressions"]) == 1
    assert comparison["automatically_admissible"] is False


def _state() -> dict:
    return {
        "memory": {"count": 34, "active_ids": []},
        "focus": {"count": 0, "active_count": 0, "records": []},
        "volition": {"count": 0, "active_count": 0, "records": []},
        "affect": {"count": 0, "latest": None},
        "mode": {"preferred_tag": "idle", "source": "configured_default", "reason": None},
    }


def _record(run_id: str, scenario_id: str) -> BehavioralRunRecord:
    passed = EvaluationLayerResult(
        status="pass", evidence=["trace_fixture"], notes="Objective evidence matched."
    )
    qualitative = EvaluationLayerResult(
        status="pass",
        evidence=["review_fixture"],
        notes="Reasoned review passed.",
        evaluator="llm_as_human",
    )
    return BehavioralRunRecord(
        scenario_id=scenario_id,
        run_id=run_id,
        group_id="memory-positive",
        repetition=1,
        started_from_fingerprint="a" * 64,
        session_ids=["ses_fixture"],
        turn_ids=["turn_fixture"],
        response_text="A natural answer.",
        technical_execution=passed,
        cognitive_choice=qualitative,
        answer_outcome=qualitative,
        longitudinal_effect=qualitative,
    )


def _judgment(run_id: str, scenario_id: str) -> BehavioralJudgment:
    qualitative = EvaluationLayerResult(
        status="pass",
        evidence=["review_fixture"],
        notes="The response met the declared project rubric.",
        evaluator="llm_as_human",
    )
    return BehavioralJudgment.model_validate(
        {
            "run_id": run_id,
            "scenario_id": scenario_id,
            "evaluator_identity": "Codex project evaluator",
            "criteria_source": "behavioral-scenario-v1",
            "reviewed_at": "2026-07-14T10:00:00Z",
            "cognitive_choice": qualitative.model_dump(mode="json"),
            "answer_outcome": qualitative.model_dump(mode="json"),
            "longitudinal_effect": qualitative.model_dump(mode="json"),
        }
    )


def _write_reviewed(path: Path, record: BehavioralRunRecord) -> None:
    (path / "records.reviewed.json").write_text(
        json.dumps([record.model_dump(mode="json")]), encoding="utf-8"
    )
