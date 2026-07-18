import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlmodel import Session

from app.evals import frozen_baseline
from app.config import Settings
from app.evals.behavioral_evidence import (
    _evaluate_rule,
    describe_state_changes,
    extract_turn_evidence,
    snapshot_cognitive_state,
)
from app.evals.behavioral_suite import (
    _answer_text,
    _evaluation_settings,
    _final_turn,
    _first_turn_id,
    _git_commit,
    _parse_args,
    _pending_layer,
    _provider_max_tokens,
    _runtime_configuration_receipt,
    _resolve,
    _resolve_scenario_session,
    _scenario_digest,
    _verify_starting_condition,
    _write_pending_summary,
    load_behavioral_suite,
    main,
)
from app.evals.frozen_baseline import (
    assert_frozen_baseline,
    prepare_disposable_copy,
    sha256_file,
    verify_frozen_references,
)
from app.storage.db import create_db_engine, init_db
from app.storage.models import (
    AffectState,
    ChatSession,
    FocusRecord,
    IntentionRecord,
    MemoryFact,
    MemoryRecord,
)


BACKEND_ROOT = Path(__file__).resolve().parents[1]
CATALOG = BACKEND_ROOT / "app/evals/scenarios/behavioral-v1/suite.json"
BASELINE = BACKEND_ROOT / "data/preliminary-rework-v1.db"


def test_turn_evidence_extracts_only_structured_model_evidence() -> None:
    events = [
        {"type": "noise", "data": "not-a-mapping"},
        {
            "type": "memory_context",
            "data": {
                "selected": [{"id": "mem_one"}, {"content": "missing id"}, "bad"],
                "candidate_count": 7,
            },
        },
        {
            "type": "runtime_context",
            "data": {"blocks": [{"type": "session_context"}, "bad"]},
        },
    ]
    traces = [
        {
            "id": "trace_one",
            "kind": "mind.tool_call",
            "payload": {
                "tool_name": "mind_shell",
                "arguments": {"command": "  memory search zero  "},
                "result": {"ok": True},
                "status": "completed",
                "latency_ms": 17,
            },
        },
        {"id": 4, "kind": "mind.tool_call", "payload": {"arguments": {}}},
        {"id": "trace_two", "kind": "llm.response", "payload": "bad"},
        {
            "id": "trace_affect",
            "kind": "organ.affect",
            "payload": {"mode": "shadow", "model_facing": False},
        },
    ]

    evidence = extract_turn_evidence(events=events, traces=traces)

    assert evidence["memory"] == {"selected_ids": ["mem_one"], "candidate_count": 7}
    assert evidence["runtime"]["block_types"] == ["session_context"]
    assert evidence["shell_commands"] == ["memory search zero"]
    assert evidence["tool_calls"] == [
        {
            "trace_id": "trace_one",
            "tool_name": "mind_shell",
            "arguments": {"command": "  memory search zero  "},
            "result": {"ok": True},
            "status": "completed",
            "latency_ms": 17,
        }
    ]
    assert evidence["organ_traces"]["organ.affect"] == [
        {
            "trace_id": "trace_affect",
            "payload": {"mode": "shadow", "model_facing": False},
        }
    ]
    assert evidence["trace_ids"] == ["trace_one", "trace_two", "trace_affect"]


def test_state_snapshot_and_change_description_cover_all_organs(tmp_path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'state.db'}")
    init_db(engine)
    before = snapshot_cognitive_state(engine, profile_id="local-user")
    with Session(engine) as db:
        db.add(
            MemoryRecord(
                memory_type="lesson",
                content="A bounded evaluator lesson.",
                reason_for_storage="Fixture evidence.",
            )
        )
        db.add(FocusRecord(focus_object="Inspect evidence", reason="Fixture"))
        db.add(IntentionRecord(desire="Keep evaluating", reason="Fixture"))
        db.add(
            AffectState(
                emotion="curiosity",
                mode="model",
                intensity=0.4,
                valence=0.2,
                activation=0.3,
                prototype_version="fixture-v1",
            )
        )
        db.commit()
    after = snapshot_cognitive_state(engine, profile_id="local-user")

    assert after["focus"]["records"][0]["focus_object"] == "Inspect evidence"
    assert after["volition"]["records"][0]["origin"] == "scarlet"
    assert after["affect"]["latest"]["emotion"] == "curiosity"
    assert describe_state_changes(before, after) == [
        "memory.write",
        "focus.write",
        "volition.write",
        "affect.write",
    ]
    mode_after = json.loads(json.dumps(after))
    mode_after["mode"]["preferred_tag"] = "scouting"
    assert describe_state_changes(after, mode_after) == ["mode.change"]
    engine.dispose()


@pytest.mark.parametrize(
    ("value", "rule", "expected"),
    [
        ("x", "x", True),
        ("x", {"equals": "x"}, True),
        ("x", {"one_of": ["x", "y"]}, True),
        (["x", "y"], {"contains": ["x"], "excludes": ["z"]}, True),
        (3, {"min": 2, "max": 4}, True),
        (None, {"min": 1}, False),
        ("x", {}, False),
    ],
)
def test_objective_rule_operators(value, rule, expected) -> None:
    passed, detail = _evaluate_rule(value, rule)

    assert passed is expected
    assert detail


def test_frozen_baseline_guards_inventory_and_disposable_copy(
    tmp_path,
    monkeypatch,
) -> None:
    baseline = _create_frozen_fixture(tmp_path / "preliminary-fixture-baseline.db")
    baseline_hash = sha256_file(baseline)
    monkeypatch.setattr(frozen_baseline, "BASELINE_LFS_OID", baseline_hash)
    monkeypatch.setattr(
        frozen_baseline,
        "BASELINE_COUNTS",
        {
            "memories": 3,
            "memory_facts": 3,
            "sessions": 3,
            "messages": 0,
            "focus_records": 0,
            "intention_records": 0,
            "affect_states": 0,
        },
    )

    assert_frozen_baseline(baseline)
    run_db = tmp_path / "behavioral-fixture.db"
    prepare_disposable_copy(
        baseline_db=baseline,
        run_db=run_db,
        marker="behavioral-",
    )
    assert sha256_file(run_db) == baseline_hash

    engine = create_db_engine(f"sqlite:///{run_db}")
    with Session(engine) as db:
        verified = verify_frozen_references(db)
    assert verified["counts"] == frozen_baseline.BASELINE_COUNTS
    assert set(verified["references"]) == {
        "zero_luce_active",
        "zero_luce_deprecated",
        "episodic_bridge",
    }
    engine.dispose()

    with pytest.raises(RuntimeError, match="unsafe evaluator database target"):
        prepare_disposable_copy(
            baseline_db=baseline,
            run_db=tmp_path / "wrong.sqlite",
            marker="behavioral-",
        )
    with pytest.raises(RuntimeError, match="must differ"):
        prepare_disposable_copy(
            baseline_db=baseline,
            run_db=baseline,
            marker="preliminary-",
        )
    with pytest.raises(RuntimeError, match="missing"):
        assert_frozen_baseline(tmp_path / "missing.db")


def test_suite_helpers_preserve_chain_and_answer_contract(tmp_path) -> None:
    suite = load_behavioral_suite(CATALOG)
    focus_create = next(item for item in suite.scenarios if item.id == "BEH-0004")
    focus_close = next(item for item in suite.scenarios if item.id == "BEH-0005")
    client = _SessionClient()

    created = _resolve_scenario_session(
        client=client,
        scenario=focus_create,
        scenario_sessions={},
    )
    continued = _resolve_scenario_session(
        client=client,
        scenario=focus_close,
        scenario_sessions={focus_create.id: created},
    )

    assert created == "ses_fixture"
    assert continued == created
    assert client.payload == {"title": "Conversazione con Scarlet"}

    no_prerequisite = focus_close.model_copy(
        update={
            "starting_condition": focus_close.starting_condition.model_copy(
                update={"prerequisite_scenario_ids": []}
            )
        }
    )
    with pytest.raises(RuntimeError, match="needs a prerequisite session"):
        _resolve_scenario_session(
            client=client,
            scenario=no_prerequisite,
            scenario_sessions={},
        )

    events = [
        {"type": "text_delta", "data": {"text": "fallback"}},
        {"type": "turn_complete", "data": {"turn_id": "turn_final"}},
    ]
    complete = _final_turn(events)
    assert _first_turn_id(events) == "turn_final"
    assert _answer_text(events, complete) == "fallback"
    complete["assistant_message"] = {"content": "persisted answer"}
    assert _answer_text(events, complete) == "persisted answer"
    assert _final_turn([]) == {}
    assert _first_turn_id([{"data": "bad"}]) is None

    pending = _pending_layer("Needs review")
    assert pending.status == "inconclusive"
    assert pending.evaluator == "pending"
    assert len(_scenario_digest(focus_create)) == 64

    record = _minimal_record()
    _write_pending_summary(tmp_path, suite, [record])
    summary = (tmp_path / "summary.pending.md").read_text(encoding="utf-8")
    assert "Objective technical passes: `1/1`" in summary
    assert "Qualitative review: `pending`" in summary


def test_suite_configuration_reference_checks_and_cli_validation(
    tmp_path,
    capsys,
    monkeypatch,
) -> None:
    baseline = _create_frozen_fixture(tmp_path / "preliminary-fixture-baseline.db")
    baseline_hash = sha256_file(baseline)
    monkeypatch.setattr(frozen_baseline, "BASELINE_LFS_OID", baseline_hash)
    catalog_payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    catalog_payload["baseline_database"] = str(baseline)
    catalog_payload["database_fingerprint"] = baseline_hash
    for scenario in catalog_payload["scenarios"]:
        scenario["starting_condition"]["database_fingerprint"] = baseline_hash
    catalog = tmp_path / "suite.json"
    catalog.write_text(json.dumps(catalog_payload), encoding="utf-8")
    suite = load_behavioral_suite(catalog)
    base = Settings()
    settings = _evaluation_settings(
        base,
        suite=suite,
        baseline_db=baseline,
        run_db=tmp_path / "behavioral-run.db",
    )
    assert settings.environment == "behavioral-evaluation"
    assert settings.codex_test is True
    assert settings.maintenance_enabled is False

    focus_group = next(group for group in suite.groups if group.id == "focus-lifecycle")
    configured_group = focus_group.model_copy(
        update={"runtime_configuration": {"organ_focus_mode": "off"}}
    )
    group_settings = _evaluation_settings(
        base,
        suite=suite,
        group=configured_group,
        baseline_db=baseline,
        run_db=tmp_path / "behavioral-run.db",
    )
    assert group_settings.organ_focus_mode == "off"
    receipt = _runtime_configuration_receipt(
        settings=group_settings,
        suite=suite,
        group=configured_group,
        baseline_db=baseline,
        run_db=tmp_path / "behavioral-run.db",
    )
    assert receipt["requested"]["group"] == {"organ_focus_mode": "off"}
    assert receipt["effective"]["organ_focus_mode"] == "off"
    assert receipt["evaluator_boundary"]["codex_test"] is True
    assert "api_key" not in json.dumps(receipt)
    assert _provider_max_tokens(settings) == settings.minimax_max_tokens
    qwen = Settings(**{**settings.model_dump(), "llm_provider": "qwen"})
    assert _provider_max_tokens(qwen) == qwen.qwen_max_tokens

    engine = create_db_engine(f"sqlite:///{baseline}")
    memory_scenario = next(item for item in suite.scenarios if item.id == "BEH-0001")
    _verify_starting_condition(memory_scenario, engine)
    changed = memory_scenario.model_copy(deep=True)
    changed.starting_condition.references[0].expected["status"] = "deprecated"
    with pytest.raises(RuntimeError, match="field status changed"):
        _verify_starting_condition(changed, engine)
    engine.dispose()

    assert _resolve(BACKEND_ROOT, CATALOG) == CATALOG
    assert _resolve(BACKEND_ROOT, Path("data/preliminary-rework-v1.db")) == BASELINE
    assert _git_commit(BACKEND_ROOT)
    assert _parse_args(["validate"]).command == "validate"
    assert main(["--catalog", str(catalog), "validate", "--backend-root", str(BACKEND_ROOT)]) == 0
    output = capsys.readouterr().out
    assert '"scenarios": 12' in output


def test_behavioral_runtime_configuration_rejects_unsafe_keys_and_values() -> None:
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    payload["configuration"]["database_url"] = "sqlite:///data/app.db"
    with pytest.raises(ValueError, match="unsafe or unsupported"):
        load_behavioral_suite_from_payload(payload)

    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    payload["groups"][0]["runtime_configuration"] = {
        "organ_affect_mode": "unbounded"
    }
    with pytest.raises(ValueError, match="invalid values"):
        load_behavioral_suite_from_payload(payload)


def load_behavioral_suite_from_payload(payload: dict):
    from app.evals.behavioral_contracts import BehavioralSuite

    return BehavioralSuite.model_validate(payload)


class _SessionResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return {"id": "ses_fixture"}


class _SessionClient:
    payload: dict[str, str] | None = None

    def post(self, path: str, *, json: dict[str, str]):
        assert path == "/api/chat/sessions"
        self.payload = json
        return _SessionResponse()


def _minimal_record():
    return SimpleNamespace(
        run_id="fixture-run",
        session_ids=["ses_fixture"],
        turn_ids=["turn_fixture"],
        observed_state_changes=[],
        technical_execution=SimpleNamespace(status="pass"),
    )


def _create_frozen_fixture(path: Path) -> Path:
    engine = create_db_engine(f"sqlite:///{path}")
    init_db(engine)
    with Session(engine) as db:
        for reference in frozen_baseline.FROZEN_REFERENCES.values():
            db.add(ChatSession(id=reference.source_session_id, title=reference.name))
            db.add(
                MemoryRecord(
                    id=reference.memory_id,
                    memory_type="project_fact",
                    status=reference.status,
                    content="; ".join(reference.required_terms),
                    reason_for_storage="Behavioral evaluator fixture.",
                    source_session_id=reference.source_session_id,
                )
            )
            if reference.fact_id is not None:
                db.add(
                    MemoryFact(
                        id=reference.fact_id,
                        memory_id=reference.memory_id,
                        entity="behavioral_fixture",
                        predicate="supports",
                        value_json={"reference": reference.name},
                        source_session_id=reference.source_session_id,
                    )
                )
        db.commit()
    engine.dispose()
    return path
