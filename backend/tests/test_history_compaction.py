from copy import deepcopy

from sqlmodel import Session

from app.runtime.history_compaction import (
    build_chronology_source_map,
    build_history_partition_plan,
)
from app.storage import repositories
from app.storage.db import init_db


def _block(text: str) -> list[dict[str, str]]:
    return [{"type": "text", "text": text}]


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
