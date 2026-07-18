import json
from pathlib import Path

from fastapi import FastAPI
import pytest

from app.config import Settings
from app.evals import memory_rerank_calibration as calibration
from app.evals.memory_rerank_calibration import (
    CalibrationCase,
    CalibrationProbeProvider,
    _run_case,
    _validate_run_path,
    calibration_cases,
    run_calibration,
    threshold_analysis,
)
from app.mind.relevance_rerank import (
    MemoryRecallCandidate,
    run_memory_relevance_rerank,
)
from app.runtime.answer_obligations import NATIVE_FINAL_MARKER
from app.storage.models import MemoryRecord


class _ScoredReranker:
    scores: list[float] = []

    def __init__(self, **_: object) -> None:
        pass

    def rerank(self, **_: object) -> dict:
        return {
            "results": [
                {"index": index, "relevance_score": score}
                for index, score in enumerate(self.scores)
            ]
        }


def _run(*, groups: list[list[str]], scores: dict[str, float]) -> dict:
    return {
        "required_groups": groups,
        "rerank": {
            "entries": [
                {
                    "memory_id": memory_id,
                    "score": score,
                    "evaluated": True,
                }
                for memory_id, score in scores.items()
            ]
        },
    }


def test_calibration_cases_cover_positive_negative_graph_and_live_review() -> None:
    cases = calibration_cases()

    assert len(cases) == 16
    assert len({case.case_id for case in cases}) == len(cases)
    assert any(case.category == "negative" for case in cases)
    assert sum(case.category.startswith("negative_personal") for case in cases) == 5
    assert any(case.required_route == "graph" for case in cases)
    assert any(len(case.required_groups) > 1 for case in cases)
    assert sum(case.live_scarlet for case in cases) == 3


def test_calibration_probe_provider_supports_sync_tools_and_streaming() -> None:
    provider = CalibrationProbeProvider(Settings(minimax_model="test-model"))

    assert provider.generate_text(prompt="x").text.endswith(NATIVE_FINAL_MARKER)
    assert provider.generate_chat(messages=[]).model == "test-model"
    assert (
        provider.generate_chat_with_tools(
            messages=[],
            tools=[],
            tool_runner=None,
        ).stop_reason
        == "end_turn"
    )
    events = list(
        provider.stream_chat_with_tools(
            messages=[],
            tools=[],
            tool_runner=None,
        )
    )
    assert [event.type for event in events] == ["text_delta", "final_result"]

    judge = provider.generate_text(
        prompt='{"obligations":[{"id":"source.required"}]}',
        system="You are the runtime answer-obligation judge.",
    )
    assert json.loads(judge.text)["findings"][0]["status"] == "pass"


def test_calibration_orchestrates_repetitions_live_cases_and_source_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.db"
    source.write_bytes(b"immutable calibration source")
    run_db = tmp_path / "sca3-memory-rerank-run.db"
    output = tmp_path / "result.json"
    case = CalibrationCase(
        case_id="positive",
        category="test",
        query="query",
        required_groups=(("mem_expected",),),
        live_scarlet=True,
    )
    monkeypatch.setattr(
        calibration,
        "EXPECTED_SOURCE_SHA256",
        calibration._file_sha256(source),
    )
    monkeypatch.setattr(calibration, "_validate_source_references", lambda *_: None)
    calls: list[bool] = []

    def fake_run_case(**kwargs: object) -> dict:
        live = bool(kwargs["live_scarlet"])
        calls.append(live)
        return {
            "case_id": "positive",
            "required_groups": [["mem_expected"]],
            "passed": True,
            "rerank": {
                "entries": [
                    {
                        "memory_id": "mem_expected",
                        "score": 0.8,
                        "evaluated": True,
                    }
                ]
            },
        }

    monkeypatch.setattr(calibration, "_run_case", fake_run_case)

    artifact = run_calibration(
        source_db=source,
        run_db=run_db,
        output_path=output,
        repetitions=2,
        run_live_scarlet=True,
        settings=Settings(
            retrieval_hybrid_min_rerank_score=0.004,
            retrieval_hybrid_relative_rerank_floor=0.01,
        ),
        cases=(case,),
    )

    assert calls == [False, False, True]
    assert artifact["summary"]["probe_total"] == 2
    assert artifact["summary"]["live_total"] == 1
    assert artifact["source_database"]["unchanged"] is True
    assert output.exists()


def test_run_case_reads_final_rerank_and_v2_evidence_from_http_trace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.db"
    source.write_bytes(b"source")
    run_db = tmp_path / "sca3-memory-rerank-case.db"
    memory_id = "mem_expected"
    app = FastAPI()

    @app.post("/api/chat/sessions")
    def create_session() -> dict:
        return {"id": "ses_test"}

    @app.post("/api/chat/sessions/{session_id}/turn")
    def create_turn(session_id: str) -> dict:
        return {
            "session": {"id": session_id},
            "turn_id": "turn_test",
            "assistant_message": {"content": "Grounded answer."},
        }

    @app.get("/api/debug/traces/{turn_id}")
    def traces(turn_id: str) -> list[dict]:
        assert turn_id == "turn_test"
        return [
            {
                "kind": "memory.context",
                "payload": {
                    "selected": [{"id": memory_id}],
                    "query_plan": {
                        "retrieval_rerank": {
                            "status": "completed",
                            "fail_closed": True,
                            "legacy_weighted_fusion": False,
                            "entries": [
                                {
                                    "memory_id": memory_id,
                                    "score": 0.8,
                                    "evaluated": True,
                                    "accepted": True,
                                    "recall_routes": ["graph"],
                                }
                            ],
                        },
                        "retrieval_shadow": {"status": "completed"},
                    },
                    "negative_evidence": None,
                },
            },
            {
                "kind": "model.context",
                "payload": {
                    "document": {
                        "memories": {
                            "relevant": [{"id": memory_id}],
                            "recent_user": [],
                            "recent_general": [],
                        }
                    }
                },
            },
        ]

    monkeypatch.setattr(calibration, "create_db_engine", lambda *_: object())
    monkeypatch.setattr(calibration, "init_db", lambda *_: None)
    monkeypatch.setattr(calibration, "create_app", lambda *_args, **_kwargs: app)
    case = CalibrationCase(
        case_id="trace_case",
        category="test",
        query="query",
        required_groups=((memory_id,),),
        required_route="graph",
    )

    result = _run_case(
        source_db=source,
        run_db=run_db,
        settings=Settings(),
        case=case,
        repetition=1,
        live_scarlet=False,
    )

    assert result["passed"] is True
    assert result["selected_ids"] == [memory_id]
    assert result["v2_memory_lanes"]["relevant"] == [memory_id]
    assert result["answer"] == "Grounded answer."


def test_threshold_analysis_maintains_threshold_only_inside_observed_gap() -> None:
    analysis = threshold_analysis(
        [
            _run(groups=[["positive"]], scores={"positive": 0.09}),
            _run(groups=[], scores={"negative": 0.0004}),
        ],
        current_threshold=0.004,
        relative_floor=0.01,
    )

    assert analysis["positive_floor"] == pytest.approx(0.09)
    assert analysis["negative_ceiling"] == pytest.approx(0.0004)
    assert analysis["observed_separation"] is True
    assert analysis["recommendation"] == "maintain_current_threshold"


def test_threshold_analysis_requires_review_when_scores_overlap() -> None:
    analysis = threshold_analysis(
        [
            _run(groups=[["positive"]], scores={"positive": 0.01}),
            _run(groups=[], scores={"negative": 0.02}),
        ],
        current_threshold=0.01,
        relative_floor=0.01,
    )

    assert analysis["observed_separation"] is False
    assert analysis["threshold_within_observed_separation"] is False
    assert analysis["recommendation"] == (
        "human_review_required_no_safe_numeric_change"
    )


@pytest.mark.parametrize(
    ("scores", "accepted_ids", "effective_threshold"),
    [
        ([0.8, 0.006, 0.0005], ["mem_0"], 0.008),
        ([0.02, 0.007, 0.0005], ["mem_0", "mem_1"], 0.004),
    ],
)
def test_final_reranker_uses_absolute_and_query_relative_floors(
    monkeypatch: pytest.MonkeyPatch,
    scores: list[float],
    accepted_ids: list[str],
    effective_threshold: float,
) -> None:
    _ScoredReranker.scores = scores
    monkeypatch.setattr(
        "app.mind.shadow_retrieval.OpenRouterRetrievalClient",
        _ScoredReranker,
    )
    candidates = [
        MemoryRecallCandidate(
            memory=MemoryRecord(
                id=f"mem_{index}",
                memory_type="project_fact",
                content=f"Memory {index}",
                reason_for_storage="Calibration test",
            ),
            document=f"Memory {index}",
            routes=("sparse",),
            route_ranks={"sparse": index + 1},
        )
        for index in range(len(scores))
    ]
    settings = Settings(
        openrouter_api_key="test-key",
        retrieval_shadow_enabled=True,
        retrieval_shadow_backend="openrouter",
        retrieval_shadow_rerank_enabled=True,
        retrieval_shadow_rerank_model="test/reranker",
        retrieval_hybrid_mode="active",
        retrieval_hybrid_min_rerank_score=0.004,
        retrieval_hybrid_relative_rerank_floor=0.01,
    )

    plan = run_memory_relevance_rerank(
        query="test query",
        candidates=candidates,
        settings=settings,
        selected_limit=5,
    )

    assert plan.status["acceptance_threshold"] == pytest.approx(effective_threshold)
    assert [entry.memory_id for entry in plan.entries if entry.accepted] == (
        accepted_ids
    )


def test_run_database_guard_rejects_source_and_unguarded_names(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.db"
    source.touch()

    with pytest.raises(RuntimeError, match="must contain"):
        _validate_run_path(source_db=source, run_db=tmp_path / "run.db")
    guarded_source = tmp_path / "sca3-memory-rerank-source.db"
    guarded_source.touch()
    with pytest.raises(RuntimeError, match="must differ"):
        _validate_run_path(source_db=guarded_source, run_db=guarded_source)
