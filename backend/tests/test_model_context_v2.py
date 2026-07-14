from datetime import datetime, timezone

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.config import Settings
from app.mind.context_projection import compile_model_context_v2
from app.mind.context_sessions import MISSING_SUMMARY, STALE_SUMMARY
from app.mind.contracts import MindAPIContext
from app.mind.memory import handle_memory_read
from app.runtime.maintenance import memory_provenance_audit, session_summary_audit
from app.runtime.preferences import RuntimePreferences
from app.storage import repositories
from app.storage.db import init_db


def _engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _preferences() -> RuntimePreferences:
    return RuntimePreferences(
        timezone="Europe/Rome",
        language="it",
        language_label="Italiano",
        country_code="IT",
        country_label="Italia",
        profile_id="local-user",
        user_display_name="Mario",
        privacy_scope="local_single_user",
        source="test",
    )


def _settings() -> Settings:
    return Settings(environment="test", model_context_profile="v2")


def _source_memory(db: Session, *, scope: str, content: str):
    session = repositories.create_chat_session(db, title=f"Source {content}")
    turn = repositories.create_turn(db, session_id=session.id, model="test")
    message = repositories.add_message(
        db,
        session_id=session.id,
        turn_id=turn.id,
        role="user",
        content=f"Evidence for {content}",
    )
    repositories.add_message(
        db,
        session_id=session.id,
        turn_id=turn.id,
        role="assistant",
        content="Persisted answer",
    )
    repositories.complete_turn(db, turn_id=turn.id)
    memory = repositories.add_memory(
        db,
        memory_type="user_preference" if scope == "user" else "project_fact",
        scope=scope,
        content=content,
        reason_for_storage="Contract fixture",
        source_session_id=session.id,
        source_turn_id=turn.id,
        source_message_id=message.id,
    )
    return memory, session, turn, message


def test_v2_session_packet_uses_last_message_time_and_summary_fallbacks() -> None:
    engine = _engine()
    init_db(engine)
    with Session(engine) as db:
        current = repositories.create_chat_session(db, title="Current")
        old, _, _, _ = _source_memory(db, scope="project", content="old")
        older_session = repositories.get_chat_session(db, old.source_session_id)
        assert older_session is not None
        repositories.upsert_session_summary(
            db,
            session_id=older_session.id,
            summary="Current summary",
            last_message_id=repositories.list_messages(
                db, session_id=older_session.id
            )[-1].id,
        )
        missing_memory, missing_session, _, _ = _source_memory(
            db, scope="project", content="missing"
        )
        stale_memory, stale_session, _, _ = _source_memory(
            db, scope="project", content="stale"
        )
        repositories.upsert_session_summary(
            db,
            session_id=stale_session.id,
            summary="Old summary",
            last_message_id=stale_memory.source_message_id,
        )
        rich = {"selected": []}
        settings = _settings().model_copy(
            update={"model_context_previous_sessions_limit": 5}
        )
        document = compile_model_context_v2(
            db,
            chat_session=current,
            rich_memory_context=rich,
            legacy_runtime_payload={"blocks": []},
            now=datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc),
            preferences=_preferences(),
            settings=settings,
        )

    by_id = {item["id"]: item for item in document["session"]["previous_sessions"]}
    assert by_id[missing_session.id]["summary"] == MISSING_SUMMARY
    assert by_id[stale_session.id]["summary"] == STALE_SUMMARY
    assert document["session"]["now"].endswith("+02:00")
    assert document["session"]["timezone"] == {
        "id": "Europe/Rome",
        "name": "CEST",
        "utc_offset": "+02:00",
    }
    assert set(document["session"]["current_session"]) == {
        "id",
        "title",
        "created_at",
    }
    assert all("updated_at" not in item for item in by_id.values())


def test_v2_memory_blocks_are_compact_deduplicated_and_activity_ordered() -> None:
    engine = _engine()
    init_db(engine)
    with Session(engine) as db:
        current = repositories.create_chat_session(db, title="Current")
        relevant, _, _, _ = _source_memory(db, scope="user", content="Relevant")
        recent_user, _, _, _ = _source_memory(db, scope="user", content="User recent")
        recent_general, _, _, _ = _source_memory(
            db, scope="project", content="General recent"
        )
        repositories.add_memory_activity(
            db,
            memory_id=recent_user.id,
            activity_kind="manual_read",
            source="test",
        )
        repositories.add_memory_activity(
            db,
            memory_id=recent_general.id,
            activity_kind="manual_search",
            source="test",
        )
        rich = {
            "selected": [
                {
                    "id": relevant.id,
                    "content": relevant.content,
                    "created_at": relevant.created_at.isoformat(),
                    "updated_at": relevant.updated_at.isoformat(),
                    "source_session_id": relevant.source_session_id,
                    "source_message_id": relevant.source_message_id,
                }
            ]
        }
        document = compile_model_context_v2(
            db,
            chat_session=current,
            rich_memory_context=rich,
            legacy_runtime_payload={"blocks": []},
            now=datetime.now(timezone.utc),
            preferences=_preferences(),
            settings=_settings(),
        )

    blocks = document["memories"]
    assert [item["id"] for item in blocks["relevant"]] == [relevant.id]
    assert recent_user.id in {item["id"] for item in blocks["recent_user"]}
    assert recent_general.id in {item["id"] for item in blocks["recent_general"]}
    all_items = blocks["relevant"] + blocks["recent_user"] + blocks["recent_general"]
    assert len({item["id"] for item in all_items}) == len(all_items)
    assert all(
        set(item)
        == {
            "id",
            "content",
            "created_at",
            "updated_at",
            "source_session_id",
            "source_message_id",
        }
        for item in all_items
    )


def test_manual_memory_read_records_activity_without_mutating_memory_timestamps() -> None:
    engine = _engine()
    init_db(engine)
    with Session(engine) as db:
        memory, session, turn, message = _source_memory(
            db, scope="project", content="Stable timestamp"
        )
        original_updated_at = memory.updated_at
        original_usage_count = memory.usage_count
        original_last_used_at = memory.last_used_at
        memory_id = memory.id
        session_id = session.id
        turn_id = turn.id
        message_id = message.id

    result = handle_memory_read(
        memory_id,
        MindAPIContext(
            engine=engine,
            session_id=session_id,
            turn_id=turn_id,
            source_message_id=message_id,
            settings=_settings(),
        ),
    )
    assert result.ok is True
    with Session(engine) as db:
        stored = repositories.get_memory(db, memory_id)
        activities = repositories.list_memory_activities(db, memory_id=memory_id)
        assert stored is not None
        assert stored.updated_at == original_updated_at
        assert stored.usage_count == original_usage_count
        assert stored.last_used_at == original_last_used_at
        assert activities[0].activity_kind == "manual_read"
        assert activities[0].message_id == message_id


def test_provenance_audit_repairs_only_unambiguous_source_turns() -> None:
    engine = _engine()
    init_db(engine)
    with Session(engine) as db:
        memory, _, _, message = _source_memory(
            db, scope="project", content="Legacy provenance"
        )
        memory.source_message_id = None
        db.add(memory)
        db.commit()
        dry_run = memory_provenance_audit(db, apply=False)
        assert dry_run["counts"]["repairable_single_user_message"] == 1
        assert repositories.get_memory(db, memory.id).source_message_id is None
        applied = memory_provenance_audit(db, apply=True)
        assert applied["repaired"] == 1
        assert repositories.get_memory(db, memory.id).source_message_id == message.id


def test_summary_audit_separates_empty_and_active_turns() -> None:
    engine = _engine()
    init_db(engine)
    with Session(engine) as db:
        repositories.create_chat_session(db, title="Empty")
        active = repositories.create_chat_session(db, title="Active")
        turn = repositories.create_turn(db, session_id=active.id, model="test")
        repositories.add_message(
            db,
            session_id=active.id,
            turn_id=turn.id,
            role="user",
            content="Still active",
        )
        report = session_summary_audit(db)
    assert report["counts"]["empty"] == 1
    assert report["counts"]["blocked_active_turn"] == 1
