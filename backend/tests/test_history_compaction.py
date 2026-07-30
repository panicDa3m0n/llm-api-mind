from copy import deepcopy
from hashlib import sha256

from sqlmodel import Session

from app.config import Settings
from app.llm.provider import LLMMessage, LLMTextResult
from app.runtime.history_compaction import (
    build_chronology_source_map,
    build_history_partition_plan,
)
from app.runtime.history_runtime import (
    _sanitize_unverified_source_ids,
    generate_history_compaction,
    route_history_for_model,
)
from app.runtime.maintenance import (
    run_maintenance_job,
    schedule_history_compaction,
)
from app.storage import repositories
from app.storage.db import init_db


def _block(text: str) -> list[dict[str, str]]:
    return [{"type": "text", "text": text}]


class FakeHistoryCompactionProvider:
    prompts: list[str] = []

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        self.__class__.prompts.append(prompt)
        return LLMTextResult(
            model=self.settings.minimax_model,
            text=f"compacted-generation-{len(self.prompts)}",
            usage={"input_tokens": 120, "output_tokens": 12},
            provider_message_id=f"provider_compaction_{len(self.prompts)}",
            stop_reason="end_turn",
        )


def _active_settings() -> Settings:
    return Settings(
        environment="test",
        minimax_api_key="test-key",
        minimax_model="MiniMax-M3",
        minimax_max_tokens=500,
        maintenance_enabled=True,
        context_window_tokens=2_000,
        context_operational_input_limit_tokens=1_000,
        context_compaction_trigger_tokens=400,
        history_compaction_target_tokens=150,
        history_compaction_verbatim_tokens=250,
        history_compaction_safety_tokens=50,
        history_compaction_mode="active",
    )


def _add_completed_turn(
    db: Session,
    *,
    session_id: str,
    history: list[dict],
    user_text: str,
    assistant_text: str,
) -> str:
    turn = repositories.create_turn(
        db,
        session_id=session_id,
        model="MiniMax-M3",
    )
    user_message = {"role": "user", "content": _block(user_text)}
    assistant_message = {"role": "assistant", "content": _block(assistant_text)}
    repositories.add_message(
        db,
        session_id=session_id,
        turn_id=turn.id,
        role="user",
        content=user_text,
    )
    repositories.add_message(
        db,
        session_id=session_id,
        turn_id=turn.id,
        role="assistant",
        content=assistant_text,
    )
    repositories.add_trace(
        db,
        session_id=session_id,
        turn_id=turn.id,
        kind="llm.request",
        payload={"provider_messages": history + [user_message]},
    )
    repositories.add_trace(
        db,
        session_id=session_id,
        turn_id=turn.id,
        kind="llm.response",
        payload={"tool_calls": []},
    )
    repositories.complete_turn(db, turn_id=turn.id)
    history.extend([user_message, assistant_message])
    return turn.id


def test_source_map_preserves_exact_turn_boundaries_without_mutation(db_engine) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(db, title="Source map")
        history: list[dict] = []
        turn_ids = [
            _add_completed_turn(
                db,
                session_id=chat_session.id,
                history=history,
                user_text=f"question-{index}",
                assistant_text=f"answer-{index}-" + ("x" * (index * 40)),
            )
            for index in range(1, 4)
        ]
        repositories.update_chat_session_provider_history(
            db,
            session_id=chat_session.id,
            provider_history=history,
        )
        before = deepcopy(history)

        source_map = build_chronology_source_map(
            db,
            session_id=chat_session.id,
            chars_per_token=2.0,
        )
        stored = repositories.get_chat_session(db, chat_session.id)

    assert source_map["status"] == "complete"
    assert source_map["mapping_verified"] is True
    assert [unit["turn_id"] for unit in source_map["turns"]] == turn_ids
    assert all(unit["request_trace_id"] for unit in source_map["turns"])
    assert all(unit["message_ids"] for unit in source_map["turns"])
    assert stored is not None
    assert stored.provider_history_json == before


def test_source_map_normalizes_legacy_string_content_without_changing_history(
    db_engine,
) -> None:
    """A legacy trace must not permanently block later shared compaction."""

    init_db(db_engine)
    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(
            db,
            title="Legacy autonomous chronology",
            kind="scarlet_autonomous",
        )
        first_turn = repositories.create_turn(
            db,
            session_id=chat_session.id,
            model="MiniMax-M3",
        )
        first_user = {"role": "user", "content": _block("legacy activation")}
        first_assistant = {
            "role": "assistant",
            "content": _block("legacy checkpoint"),
        }
        repositories.add_trace(
            db,
            session_id=chat_session.id,
            turn_id=first_turn.id,
            kind="llm.request",
            payload={
                "provider_messages": [
                    {"role": "user", "content": "legacy activation"}
                ]
            },
        )
        repositories.complete_turn(db, turn_id=first_turn.id)

        second_turn = repositories.create_turn(
            db,
            session_id=chat_session.id,
            model="MiniMax-M3",
        )
        second_user = {"role": "user", "content": _block("current activation")}
        second_assistant = {
            "role": "assistant",
            "content": _block("current checkpoint"),
        }
        repositories.add_trace(
            db,
            session_id=chat_session.id,
            turn_id=second_turn.id,
            kind="llm.request",
            payload={
                "canonical_provider_messages": [
                    first_user,
                    first_assistant,
                    second_user,
                ]
            },
        )
        repositories.complete_turn(db, turn_id=second_turn.id)
        canonical = [first_user, first_assistant, second_user, second_assistant]
        repositories.update_chat_session_provider_history(
            db,
            session_id=chat_session.id,
            provider_history=canonical,
        )

        source_map = build_chronology_source_map(
            db,
            session_id=chat_session.id,
            chars_per_token=2.0,
        )
        stored = repositories.get_chat_session(db, chat_session.id)

    assert source_map["status"] == "complete"
    assert [item["turn_id"] for item in source_map["turns"]] == [
        first_turn.id,
        second_turn.id,
    ]
    assert stored is not None
    assert stored.provider_history_json == canonical


def test_source_map_treats_a_new_session_as_complete_empty_history(db_engine) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(db, title="New session")

        source_map = build_chronology_source_map(
            db,
            session_id=chat_session.id,
            chars_per_token=2.0,
        )

    assert source_map["status"] == "complete"
    assert source_map["mapping_verified"] is True
    assert source_map["turns"] == []
    assert source_map["canonical_estimated_tokens"] == 0


def test_partition_selects_newest_complete_turns_by_token_cost(db_engine) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(db, title="Token tail")
        history: list[dict] = []
        turn_ids = [
            _add_completed_turn(
                db,
                session_id=chat_session.id,
                history=history,
                user_text=f"question-{index}",
                assistant_text="x" * size,
            )
            for index, size in enumerate([500, 300, 40, 40], start=1)
        ]
        repositories.update_chat_session_provider_history(
            db,
            session_id=chat_session.id,
            provider_history=history,
        )
        source_map = build_chronology_source_map(
            db,
            session_id=chat_session.id,
            chars_per_token=2.0,
        )

    newest_two_cost = sum(
        int(unit["estimated_tokens"]) for unit in source_map["turns"][-2:]
    )
    next_older_cost = int(source_map["turns"][-3]["estimated_tokens"])
    plan = build_history_partition_plan(
        source_map=source_map,
        external_context_tokens=100,
        provider_history_tokens=900,
        trigger_tokens=800,
        operational_limit_tokens=1_000,
        model_window_tokens=2_000,
        summary_max_tokens=150,
        verbatim_max_tokens=newest_two_cost,
        safety_tokens=50,
        mode="shadow",
    )

    assert newest_two_cost < newest_two_cost + next_older_cost
    assert plan["areas"]["verbatim_chronology"]["selected_turn_ids"] == turn_ids[-2:]
    assert plan["areas"]["compacted_summary"]["input_turn_ids"] == turn_ids[:-2]
    assert plan["status"] == "would_recompact"
    assert plan["canonical_history_mutation"] == "none"


def test_single_turn_may_exceed_partition_but_not_physical_window() -> None:
    source_map = {
        "status": "complete",
        "canonical_history_sha256": "history-digest",
        "legacy_prefix": {"estimated_tokens": 0},
        "turns": [
            {
                "turn_id": "turn_large",
                "estimated_tokens": 600,
                "sha256": "turn-digest",
            }
        ],
    }

    plan = build_history_partition_plan(
        source_map=source_map,
        external_context_tokens=50,
        provider_history_tokens=600,
        trigger_tokens=400,
        operational_limit_tokens=500,
        model_window_tokens=1_000,
        summary_max_tokens=100,
        verbatim_max_tokens=100,
        safety_tokens=25,
        mode="shadow",
    )

    assert plan["status"] == "single_turn_exceeds_operational_partition"
    assert plan["single_turn_exception"]["turn_id"] == "turn_large"
    assert plan["single_turn_exception_active_growth_tokens"] == 0
    assert plan["areas"]["verbatim_chronology"]["selected_turn_ids"] == [
        "turn_large"
    ]


def test_single_turn_beyond_physical_window_fails_closed() -> None:
    source_map = {
        "status": "complete",
        "canonical_history_sha256": "history-digest",
        "legacy_prefix": {"estimated_tokens": 0},
        "turns": [
            {
                "turn_id": "turn_impossible",
                "estimated_tokens": 1_100,
                "sha256": "turn-digest",
            }
        ],
    }

    plan = build_history_partition_plan(
        source_map=source_map,
        external_context_tokens=50,
        provider_history_tokens=1_100,
        trigger_tokens=400,
        operational_limit_tokens=500,
        model_window_tokens=1_000,
        summary_max_tokens=100,
        verbatim_max_tokens=100,
        safety_tokens=25,
        mode="shadow",
    )

    assert plan["status"] == "single_turn_exceeds_physical_model_window"
    assert plan["physical_window_failure"]["turn_id"] == "turn_impossible"
    assert plan["areas"]["verbatim_chronology"]["selected_turn_ids"] == []


def test_source_map_fails_closed_when_request_trace_is_missing(db_engine) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(db, title="Missing trace")
        turn = repositories.create_turn(
            db,
            session_id=chat_session.id,
            model="MiniMax-M3",
        )
        repositories.complete_turn(db, turn_id=turn.id)
        repositories.update_chat_session_provider_history(
            db,
            session_id=chat_session.id,
            provider_history=[
                {"role": "user", "content": _block("question")},
                {"role": "assistant", "content": _block("answer")},
            ],
        )

        source_map = build_chronology_source_map(
            db,
            session_id=chat_session.id,
            chars_per_token=2.0,
        )

    assert source_map["status"] == "unavailable"
    assert source_map["reason"] == "llm_request_trace_missing"
    assert source_map["mapping_verified"] is False


def test_compaction_summary_removes_only_unverified_opaque_source_ids() -> None:
    valid_id = "turn_1234abcd"
    invalid_id = "turn_deadbeef"
    summary, invalid = _sanitize_unverified_source_ids(
        f"Keep {valid_id}; reject {invalid_id}; retain ordinary prose.",
        source_text=f'{{"turn_id":"{valid_id}"}}',
    )

    assert valid_id in summary
    assert invalid_id not in summary
    assert "[invalid_source_id_removed]" in summary
    assert invalid == [invalid_id]


def test_active_compaction_does_not_reschedule_from_canonical_size_alone(
    db_engine,
) -> None:
    init_db(db_engine)
    settings = _active_settings()
    source_map = {
        "status": "complete",
        "canonical_history_sha256": "canonical-digest",
        "canonical_estimated_tokens": 500,
    }
    with Session(db_engine) as db:
        scheduled = schedule_history_compaction(
            db,
            settings=settings,
            session_id="ses_missing",
            trigger_turn_id="turn_missing",
            trigger_event_id=None,
            source_map=source_map,
            external_context_tokens=100,
            chars_per_token=2.0,
            model_history_tokens=100,
        )

    assert scheduled is None


def test_active_routing_uses_valid_artifact_and_keeps_canonical_history(
    db_engine,
) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(db, title="Active route")
        history: list[dict] = []
        turn_ids = [
            _add_completed_turn(
                db,
                session_id=chat_session.id,
                history=history,
                user_text=f"question-{index}",
                assistant_text=f"answer-{index}-" + ("x" * 250),
            )
            for index in range(1, 4)
        ]
        repositories.update_chat_session_provider_history(
            db,
            session_id=chat_session.id,
            provider_history=history,
        )
        source_map = build_chronology_source_map(
            db,
            session_id=chat_session.id,
            chars_per_token=2.0,
        )
        first_unit = source_map["turns"][0]
        summary = "The first turn established an exact project decision."
        artifact = repositories.create_history_compaction(
            db,
            session_id=chat_session.id,
            summary=summary,
            summary_sha256=sha256(summary.encode()).hexdigest(),
            source_history_sha256=source_map["canonical_history_sha256"],
            covered_through_turn_id=turn_ids[0],
            covered_turn_ids=[turn_ids[0]],
            covered_sources=[
                {
                    "turn_id": turn_ids[0],
                    "sha256": first_unit["sha256"],
                    "estimated_tokens": first_unit["estimated_tokens"],
                }
            ],
            source_estimated_tokens=first_unit["estimated_tokens"],
            summary_estimated_tokens=20,
            trigger_turn_id=turn_ids[-1],
            model="MiniMax-M3",
            provider_message_id="provider_compaction",
            metadata={
                "legacy_prefix_sha256": source_map["legacy_prefix"]["sha256"]
            },
        )
        canonical = [
            LLMMessage(role=item["role"], content=item["content"])
            for item in history
        ] + [LLMMessage(role="user", content="current-question")]
        canonical_snapshot = deepcopy(canonical)

        routed = route_history_for_model(
            db,
            session_id=chat_session.id,
            canonical_messages=canonical,
            chars_per_token=2.0,
            mode="active",
        )
        stored = repositories.get_chat_session(db, chat_session.id)

    assert routed.payload["status"] == "derived_history_active"
    assert routed.payload["artifact_id"] == artifact.id
    assert routed.payload["verbatim_turn_ids"] == turn_ids[1:]
    assert routed.model_messages[-1].content == "current-question"
    assert summary in routed.system_appendix
    assert turn_ids[0] in routed.system_appendix
    assert "<source_manifest>" in routed.system_appendix
    assert canonical == canonical_snapshot
    assert stored is not None
    assert stored.provider_history_json == history


def test_active_routing_falls_back_when_artifact_source_digest_is_stale(
    db_engine,
) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(db, title="Stale route")
        history: list[dict] = []
        turn_id = _add_completed_turn(
            db,
            session_id=chat_session.id,
            history=history,
            user_text="question",
            assistant_text="answer",
        )
        repositories.update_chat_session_provider_history(
            db,
            session_id=chat_session.id,
            provider_history=history,
        )
        source_map = build_chronology_source_map(
            db,
            session_id=chat_session.id,
            chars_per_token=2.0,
        )
        unit = source_map["turns"][0]
        summary = "valid summary text"
        repositories.create_history_compaction(
            db,
            session_id=chat_session.id,
            summary=summary,
            summary_sha256=sha256(summary.encode()).hexdigest(),
            source_history_sha256=source_map["canonical_history_sha256"],
            covered_through_turn_id=turn_id,
            covered_turn_ids=[turn_id],
            covered_sources=[
                {
                    "turn_id": turn_id,
                    "sha256": "stale-digest",
                    "estimated_tokens": unit["estimated_tokens"],
                }
            ],
            source_estimated_tokens=unit["estimated_tokens"],
            summary_estimated_tokens=10,
            trigger_turn_id=turn_id,
            model="MiniMax-M3",
            provider_message_id=None,
            metadata={
                "legacy_prefix_sha256": source_map["legacy_prefix"]["sha256"]
            },
        )
        canonical = [
            LLMMessage(role=item["role"], content=item["content"])
            for item in history
        ] + [LLMMessage(role="user", content="current")]

        routed = route_history_for_model(
            db,
            session_id=chat_session.id,
            canonical_messages=canonical,
            chars_per_token=2.0,
            mode="active",
        )

    assert routed.payload["status"] == "canonical_fallback_artifact_invalid"
    assert routed.payload["reason"] == "covered_source_digest_mismatch"
    assert routed.model_messages == canonical
    assert routed.system_appendix == ""


def test_history_compaction_job_is_idempotent_and_recursively_supersedes(
    db_engine,
) -> None:
    FakeHistoryCompactionProvider.prompts = []
    settings = _active_settings()
    init_db(db_engine)
    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(db, title="Recursive")
        session_id = chat_session.id
        history: list[dict] = []
        turn_ids = [
            _add_completed_turn(
                db,
                session_id=session_id,
                history=history,
                user_text=f"question-{index}",
                assistant_text="x" * 300,
            )
            for index in range(1, 5)
        ]
        repositories.update_chat_session_provider_history(
            db,
            session_id=session_id,
            provider_history=history,
        )
        source_map = build_chronology_source_map(
            db,
            session_id=session_id,
            chars_per_token=2.0,
        )
        scheduled = schedule_history_compaction(
            db,
            settings=settings,
            session_id=session_id,
            trigger_turn_id=turn_ids[-1],
            trigger_event_id=None,
            source_map=source_map,
            external_context_tokens=100,
            chars_per_token=2.0,
        )
        duplicate = schedule_history_compaction(
            db,
            settings=settings,
            session_id=session_id,
            trigger_turn_id=turn_ids[-1],
            trigger_event_id=None,
            source_map=source_map,
            external_context_tokens=100,
            chars_per_token=2.0,
        )
        assert scheduled is not None
        assert duplicate is not None
        first_job_id = scheduled[0].id
        assert duplicate[0].id == first_job_id

    first_result = run_maintenance_job(
        db_engine,
        settings=settings,
        provider_factory=FakeHistoryCompactionProvider,
        job_id=first_job_id,
    )
    assert first_result["status"] == "completed", first_result

    with Session(db_engine) as db:
        first_artifact = repositories.get_latest_history_compaction(
            db,
            session_id=session_id,
        )
        assert first_artifact is not None
        first_artifact_id = first_artifact.id
        first_summary = first_artifact.summary
        _add_completed_turn(
            db,
            session_id=session_id,
            history=history,
            user_text="new-question",
            assistant_text="y" * 300,
        )
        repositories.update_chat_session_provider_history(
            db,
            session_id=session_id,
            provider_history=history,
        )
        source_map = build_chronology_source_map(
            db,
            session_id=session_id,
            chars_per_token=2.0,
        )

    second_result = generate_history_compaction(
        db_engine,
        settings=settings,
        provider_factory=FakeHistoryCompactionProvider,
        session_id=session_id,
        trigger_turn_id=turn_ids[-1],
        expected_history_sha256=source_map["canonical_history_sha256"],
        external_context_tokens=100,
        chars_per_token=2.0,
    )

    with Session(db_engine) as db:
        artifacts = repositories.list_history_compactions(
            db,
            session_id=session_id,
        )
        stored = repositories.get_chat_session(db, session_id)

    assert second_result["status"] == "generated"
    assert [artifact.status for artifact in artifacts] == ["superseded", "active"]
    assert artifacts[1].previous_compaction_id == first_artifact_id
    assert '"previous_compaction"' in FakeHistoryCompactionProvider.prompts[-1]
    assert first_summary in FakeHistoryCompactionProvider.prompts[-1]
    assert stored is not None
    assert stored.provider_history_json == history
