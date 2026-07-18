from datetime import datetime, timezone

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.config import Settings
from app.mind.agent_modes import route_context_blocks
from app.mind.context_projection import (
    compile_model_context_v2,
    compile_model_context_v2_with_audit,
)
from app.mind.context_sessions import MISSING_SUMMARY, STALE_SUMMARY
from app.mind.contracts import MindAPIContext
from app.mind.memory import handle_memory_read
from app.runtime.maintenance import session_summary_audit
from app.runtime.memory_provenance import (
    memory_provenance_audit,
    repair_exact_source_messages,
)
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
            last_message_id=repositories.list_messages(db, session_id=older_session.id)[
                -1
            ].id,
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


def test_v2_preserved_families_use_explicit_field_allowlists_and_audit() -> None:
    engine = _engine()
    init_db(engine)
    with Session(engine) as db:
        current = repositories.create_chat_session(db, title="Current")
        document, audit = compile_model_context_v2_with_audit(
            db,
            chat_session=current,
            rich_memory_context={"selected": []},
            legacy_runtime_payload={"blocks": _preserved_source_blocks()},
            now=datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc),
            preferences=_preferences(),
            settings=_settings(),
        )

    assert [block["type"] for block in document["preserved_context"]] == [
        "focus_context",
        "affective_context",
        "metacognitive_context",
    ]
    by_type = {block["type"]: block for block in document["preserved_context"]}
    assert set(by_type["focus_context"]) == {
        "id",
        "type",
        "scope",
        "lifetime",
        "source",
        "content",
    }
    focus = by_type["focus_context"]["content"]["current_focus"]
    assert set(focus) == {
        "id",
        "object",
        "type",
        "status",
        "intensity",
        "duration_policy",
        "reason",
        "source_session_id",
        "source_turn_id",
        "source_message_id",
        "created_at",
        "updated_at",
    }
    assert focus["created_at"].endswith("+02:00")
    assert "recent_transitions" not in by_type["focus_context"]["content"]

    affect = by_type["affective_context"]["content"]
    assert set(affect) == {
        "state_id",
        "current_emotion",
        "intensity",
        "felt_quality",
        "activation",
        "valence",
        "persistence",
        "attention_tendency",
        "action_tendency",
        "relational_posture",
        "causes",
    }
    assert "intensity_score" not in affect
    assert "debug_summary" not in affect

    metacognition = by_type["metacognitive_context"]["content"]
    assert metacognition["triggers"] == [{"id": "source_sensitive"}]
    assert set(metacognition["lessons"][0]) == {
        "id",
        "title",
        "lesson",
        "recommended_action",
        "risk_if_overused",
    }

    decisions = {item["family"]: item for item in audit["families"]}
    assert audit["schema_version"] == "preserved-context-projection-v1"
    assert audit["included_block_types"] == [
        "focus_context",
        "affective_context",
        "metacognitive_context",
    ]
    assert decisions["scarlet_state"]["disposition"] == "trace_ui_only"
    assert decisions["scarlet_state"]["included_in_model"] is False
    assert decisions["recent_dialogue"]["source_present"] is True
    assert decisions["recent_runtime_events"]["included_in_model"] is False
    assert decisions["api_mind"]["disposition"] == "on_demand"
    assert decisions["api_mind"]["on_demand_commands"] == [
        "help",
        "help <family>",
    ]
    assert (
        "content.recent_transitions"
        in decisions["focus_context"]["excluded_source_fields"]
    )
    assert (
        "content.debug_summary.dominant_variables"
        in decisions["affective_context"]["excluded_source_fields"]
    )


def test_v2_projection_cannot_restore_blocks_excluded_by_active_mode_routing() -> None:
    engine = _engine()
    init_db(engine)
    source_blocks = _preserved_source_blocks()
    routed_blocks, routing = route_context_blocks(
        source_blocks,
        active_tag="idle",
        routing_mode="active",
    )

    with Session(engine) as db:
        current = repositories.create_chat_session(db, title="Current")
        document, audit = compile_model_context_v2_with_audit(
            db,
            chat_session=current,
            rich_memory_context={"selected": []},
            legacy_runtime_payload={"blocks": routed_blocks},
            now=datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc),
            preferences=_preferences(),
            settings=_settings(),
            agent_mode={
                "active_tag": "idle",
                "active_runtime_implemented": True,
                "source": "test",
                "resume_tag": None,
                "resume_runtime_implemented": None,
            },
        )

    assert routing["excluded_block_types"] == [
        "affective_context",
        "metacognitive_context",
        "message_context",
    ]
    assert [block["type"] for block in document["preserved_context"]] == [
        "focus_context"
    ]
    assert audit["included_block_types"] == ["focus_context"]
    by_family = {item["family"]: item for item in audit["families"]}
    assert by_family["affective_context"]["source_present"] is False
    assert by_family["metacognitive_context"]["source_present"] is False


def _preserved_source_blocks() -> list[dict]:
    envelope = {
        "scope": "profile",
        "lifetime": "dynamic",
        "source": "fixture",
        "visibility": "model",
    }
    return [
        {
            **envelope,
            "id": "scarlet.focus_context",
            "type": "focus_context",
            "content": {
                "organ": "focus",
                "registry_version": "fixture",
                "policy": "debug policy",
                "current_focus": {
                    "id": "focus_fixture",
                    "object": "Review context",
                    "type": "topic",
                    "status": "active",
                    "intensity": 0.8,
                    "duration_policy": "until_resolved",
                    "reason": "Keep the review bounded.",
                    "source_session_id": "ses_source",
                    "source_turn_id": "turn_source",
                    "source_message_id": "msg_source",
                    "created_at": "2026-07-12T10:00:00+00:00",
                    "updated_at": "2026-07-12T11:00:00+00:00",
                },
                "recent_transitions": [{"id": "transition_fixture"}],
                "usage": {"not_a_memory": True},
            },
        },
        {
            **envelope,
            "id": "scarlet.affective_context",
            "type": "affective_context",
            "content": {
                "organ": "affect",
                "registry_version": "fixture",
                "policy": "debug policy",
                "state_id": "affect_fixture",
                "current_emotion": "curiosity",
                "intensity": "medium",
                "intensity_score": 0.55,
                "felt_quality": "Open attention",
                "activation": "medium",
                "valence": "positive",
                "persistence": "turn",
                "attention_tendency": "inspect",
                "action_tendency": "ask carefully",
                "relational_posture": "warm",
                "causes": ["message: reasoning cue"],
                "usage": {"do_not_over_narrate": True},
                "debug_summary": {"dominant_variables": ["novelty"]},
            },
        },
        {
            "id": "turn.metacognitive_context",
            "type": "metacognitive_context",
            "scope": "turn",
            "lifetime": "turn",
            "source": "fixture",
            "content": {
                "policy": {"purpose": "debug policy"},
                "selection": {"selected_count": 1},
                "triggers": [{"id": "source_sensitive", "confidence": 0.84}],
                "lessons": [
                    {
                        "id": "source_guard",
                        "title": "Verify",
                        "lesson": "Check the source.",
                        "recommended_action": "Inspect evidence.",
                        "risk_if_overused": "Redundant checks.",
                        "trigger_conditions": ["verification"],
                        "confidence": 0.84,
                    }
                ],
            },
        },
        {
            "id": "scarlet.dynamic_state",
            "type": "scarlet_state",
            "scope": "session",
            "lifetime": "dynamic",
            "source": "fixture",
            "content": {
                "focus": "duplicated user message",
                "mood_expression": "curious_focused",
                "active_goal": "answer",
            },
        },
        {
            "id": "turn.perception",
            "type": "message_context",
            "scope": "turn",
            "lifetime": "turn",
            "source": "fixture",
            "content": {
                "recent_dialogue": [{"role": "user", "content": "duplicate"}],
                "recent_runtime_events": [{"type": "tool.completed"}],
                "api_mind": {"interface": "mind_shell", "capabilities": {}},
            },
        },
    ]


def test_manual_memory_read_records_activity_without_mutating_memory_timestamps() -> (
    None
):
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
        dry_run = memory_provenance_audit(db)
        assert dry_run["counts"]["repairable_single_user_message"] == 1
        assert repositories.get_memory(db, memory.id).source_message_id is None
        candidate = dry_run["candidate_sets"]["exact_source_message_repair"]
        applied = repair_exact_source_messages(
            db,
            dry_run=False,
            expected_candidate_digest=candidate["digest_sha256"],
            backup_reference="test-backup",
        )
        assert applied["applied_count"] == 1
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
