from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.config import Settings
from app.evals import model_facing_memory_gate as gate


def _evidence(*, delivered: bool, completed: bool = True) -> dict[str, Any]:
    hook = {
        "id": gate.TARGET.memory_id,
        "content": "Protocollo Zero-Luce",
        "created_at": "2026-07-01T12:00:00+02:00",
        "updated_at": "2026-07-01T12:00:00+02:00",
        "source_session_id": gate.TARGET.source_session_id,
        "source_message_id": "msg_source",
    }
    document = {
        "schema_version": "scarlet-model-context-v2",
        "memories": {
            "relevant": [hook] if delivered else [],
            "recent_user": [],
            "recent_general": [],
        },
    }
    runtime_context = json.dumps(document)
    traces: dict[str, list[dict[str, Any]]] = {
        "memory.context": [
            {
                "id": "trace_memory",
                "payload": {
                    "selected": [{"id": gate.TARGET.memory_id}],
                    "candidate_count": 1,
                },
            }
        ],
        "model.context": [
            {"id": "trace_model", "payload": {"document": document}}
        ],
        "llm.request": [
            {
                "id": "trace_request",
                "payload": {
                    "model_context_profile": "v2",
                    "model_context_trace_id": "trace_model",
                    "runtime_context": runtime_context,
                    "system": f"You are Scarlet.\n{runtime_context}",
                },
            }
        ],
    }
    messages = [{"id": "msg_user", "role": "user", "content": gate.PROMPT}]
    event_types = ["turn.started"]
    if completed:
        messages.append(
            {"id": "msg_assistant", "role": "assistant", "content": "Risposta."}
        )
        event_types.append("turn.completed")
        status = "completed"
        error = None
    else:
        status = "failed"
        error = {"code": "llm.incomplete_response"}
        traces["llm.error"] = [
            {
                "id": "trace_error",
                "payload": {"code": "llm.incomplete_response"},
            }
        ]
    return {
        "session_id": "ses_gate",
        "turn_id": "turn_gate",
        "turn_status": status,
        "turn_error": error,
        "messages": messages,
        "traces": traces,
        "event_types": event_types,
    }


def test_controlled_providers_expose_final_boundary_difference() -> None:
    settings = Settings(environment="test")
    provider = gate.ModelFacingGateProvider(settings)
    gate.ModelFacingGateProvider.reset_observations()

    result = provider.generate_chat_with_tools(
        messages=[],
        system="system packet",
        tools=[],
        tool_runner=None,
    )
    assert result.text.endswith("<scarlet-final/>")
    assert gate.ModelFacingGateProvider.observed_systems == ["system packet"]
    streamed = list(
        provider.stream_chat_with_tools(
            messages=[],
            system="stream packet",
            tools=[],
            tool_runner=None,
        )
    )
    assert streamed[-1].type == "final_result"

    judge = provider.generate_text(
        prompt=json.dumps({"obligations": [{"id": "answer.final_boundary"}]}),
        system="runtime answer-obligation judge",
    )
    assert json.loads(judge.text)["findings"][0]["status"] == "pass"
    review = provider.generate_text(prompt="{}", system="metacognition")
    assert json.loads(review.text)["should_continue"] is False

    incomplete = gate.IncompleteGateProvider(settings)
    gate.IncompleteGateProvider.reset_observations()
    failed = incomplete.generate_chat(messages=[], system="negative")
    assert "<scarlet-final/>" not in failed.text
    assert failed.stop_reason == "max_tokens"


def test_delivery_oracle_distinguishes_projection_and_completion() -> None:
    pre = _evidence(delivered=False)
    stream_complete = [{"type": "turn_complete", "data": {}}]
    gate._assert_completed_turn(pre, stream_complete)
    gate._assert_rich_selection(pre)
    gate._assert_memory_absent_from_model(pre, ["system without target"])
    assert gate._evidence_summary(pre)["model_memory_ids"] == []

    post = _evidence(delivered=True)
    system = post["traces"]["llm.request"][0]["payload"]["system"]
    delivered = gate._assert_model_delivery(
        post,
        stream_complete,
        [system],
        expected_source_message_id="msg_source",
    )
    assert delivered["turn_status"] == "completed"
    assert delivered["source_message_id"] == "msg_source"

    failed = _evidence(delivered=True, completed=False)
    rejected = gate._assert_gate_rejects_incomplete_turn(failed, [])
    assert rejected["gate_rejected"] is True
    assert rejected["assistant_message_count"] == 0


def test_delivery_oracle_rejects_wrong_or_missing_evidence() -> None:
    evidence = _evidence(delivered=True)
    with pytest.raises(AssertionError, match="missing trace"):
        gate._trace(evidence, "missing trace")

    evidence["traces"]["memory.context"][0]["payload"]["selected"] = []
    with pytest.raises(AssertionError):
        gate._assert_rich_selection(evidence)

    failed = _evidence(delivered=True, completed=False)
    failed["turn_status"] = "completed"
    failed["messages"].append(
        {"id": "msg_bad", "role": "assistant", "content": "Unexpected"}
    )
    failed["event_types"].append("turn.completed")
    failed["traces"].pop("llm.error")
    with pytest.raises(AssertionError, match="accepted an incomplete"):
        gate._assert_gate_rejects_incomplete_turn(
            failed,
            [{"type": "turn_complete"}],
        )


def test_guarded_repair_uses_digest_and_exact_source(monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = {
        "count": 1,
        "digest_sha256": "digest",
        "memory_ids": [gate.TARGET.memory_id],
    }
    target_item = {
        "memory_id": gate.TARGET.memory_id,
        "provenance_class": "repairable_single_user_message",
        "proposed_source_message_id": "msg_source",
    }
    residual = {
        "items": [
            {
                "memory_id": gate.TARGET.memory_id,
                "provenance_class": "source_complete_valid",
            }
        ]
    }
    calls: list[dict[str, Any]] = []

    class FakeSession:
        def __enter__(self) -> object:
            return object()

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(gate, "Session", lambda engine: FakeSession())
    monkeypatch.setattr(
        gate,
        "memory_provenance_audit",
        lambda db: {
            "candidate_sets": {"exact_source_message_repair": candidate},
            "items": [target_item],
        },
    )

    def fake_repair(db: object, **kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        if kwargs.get("dry_run"):
            return {"candidate_set": candidate}
        return {"applied_count": 1, "residual_audit": residual}

    monkeypatch.setattr(gate, "repair_exact_source_messages", fake_repair)
    monkeypatch.setattr(
        gate.repositories,
        "get_memory",
        lambda db, memory_id: SimpleNamespace(
            source_message_id="msg_source",
            source_turn_id="turn_source",
        ),
    )
    result = gate._repair_disposable_provenance(object(), Path("baseline.db"))
    assert result["target_source_message_id"] == "msg_source"
    assert result["residual_target_provenance"] == "source_complete_valid"
    assert calls[1]["expected_candidate_digest"] == "digest"
    assert calls[1]["backup_reference"].startswith("immutable-baseline:")


def test_report_writer_persists_machine_and_human_evidence(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.db"
    run_db = tmp_path / "run.db"
    baseline.write_bytes(b"baseline")
    run_db.write_bytes(b"run")
    report = gate._report(
        baseline_db=baseline,
        run_db=run_db,
        results=[
            gate.CaseResult(
                name="case",
                objective="objective",
                passed=True,
                details={"evidence": True},
            )
        ],
    )
    assert report["summary"] == {"passed": 1, "failed": 0, "total": 1}
    output = gate._write_report(tmp_path, report)
    assert json.loads((output / "report.json").read_text())["suite_id"] == gate.SUITE_ID
    assert "Passed: `1/1`" in (output / "summary.md").read_text()


def test_main_records_complete_and_failed_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    baseline = tmp_path / "baseline.db"
    run_db = tmp_path / "preliminary-model-facing-memory-gate-run.db"
    baseline.write_bytes(b"baseline")
    run_db.write_bytes(b"run")

    class FakeSession:
        def __enter__(self) -> object:
            return object()

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        gate,
        "_parse_args",
        lambda: SimpleNamespace(
            baseline_db=str(baseline),
            run_db=str(run_db),
        ),
    )
    monkeypatch.setattr(gate, "assert_frozen_baseline", lambda path: None)
    monkeypatch.setattr(gate, "prepare_disposable_copy", lambda **kwargs: None)
    monkeypatch.setattr(gate, "prepare_runtime_database", lambda settings: settings)
    monkeypatch.setattr(gate, "create_db_engine", lambda settings: object())
    monkeypatch.setattr(gate, "init_db", lambda engine: None)
    monkeypatch.setattr(gate, "Session", lambda engine: FakeSession())
    monkeypatch.setattr(gate, "verify_frozen_references", lambda db: {"ok": True})
    monkeypatch.setattr(gate, "_client", lambda *args: object())
    monkeypatch.setattr(
        gate,
        "_run_turn",
        lambda client, suffix: (f"ses_{suffix}", []),
    )
    evidences = iter(
        [
            _evidence(delivered=False),
            _evidence(delivered=True),
            _evidence(delivered=True, completed=False),
        ]
    )
    monkeypatch.setattr(gate, "_turn_evidence", lambda *args: next(evidences))
    monkeypatch.setattr(gate, "_assert_completed_turn", lambda *args: {})
    monkeypatch.setattr(gate, "_assert_rich_selection", lambda *args: None)
    monkeypatch.setattr(gate, "_assert_memory_absent_from_model", lambda *args: None)
    monkeypatch.setattr(
        gate,
        "_repair_disposable_provenance",
        lambda *args: {"target_source_message_id": "msg_source"},
    )
    monkeypatch.setattr(gate, "_assert_model_delivery", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        gate,
        "_assert_gate_rejects_incomplete_turn",
        lambda *args: {"gate_rejected": True},
    )
    monkeypatch.setattr(gate, "sha256_file", lambda path: "hash")
    captured: dict[str, Any] = {}

    def fake_write(root: Path, report: dict[str, Any]) -> Path:
        captured.update(report)
        return tmp_path / "report"

    monkeypatch.setattr(gate, "_write_report", fake_write)
    assert gate.main() == 0
    assert captured["summary"] == {"passed": 5, "failed": 0, "total": 5}
    assert '"failed": 0' in capsys.readouterr().out

    monkeypatch.setattr(
        gate,
        "verify_frozen_references",
        lambda db: (_ for _ in ()).throw(RuntimeError("broken fixture")),
    )
    assert gate.main() == 1
