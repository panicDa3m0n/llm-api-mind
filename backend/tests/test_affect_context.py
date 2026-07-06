from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.main import create_app
from app.mind.context import build_runtime_context_payload
from app.runtime.preferences import RuntimePreferences
from app.storage import repositories
from app.storage.db import init_db


def make_client(db_engine: Engine) -> TestClient:
    settings = Settings(
        app_name="Test Mind",
        environment="test",
        minimax_api_key="test-key",
        minimax_model="MiniMax-M3",
        maintenance_enabled=False,
    )
    return TestClient(create_app(settings, db_engine=db_engine))


def test_affect_shadow_appraises_without_model_block(db_engine: Engine) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        session, turn, message = _session_turn_message(
            db,
            "Non funziona, continua a dare errore e si blocca.",
        )
        runtime = _runtime(
            db,
            session=session,
            turn_id=turn.id,
            message=message,
            settings=Settings(organ_affect_mode="shadow"),
        )

        traces = repositories.list_traces_for_turn(db, turn_id=turn.id)
        events = repositories.list_events_for_turn(db, turn_id=turn.id)
        states = repositories.list_affect_states(db, turn_id=turn.id)

    assert "affective_context" not in [block["type"] for block in runtime["blocks"]]
    assert [state.emotion for state in states] == ["frustration"]
    affect_trace = next(trace for trace in traces if trace.kind == "organ.affect")
    assert affect_trace.payload_json["mode"] == "shadow"
    assert affect_trace.payload_json["model_facing"] is False
    assert affect_trace.payload_json["system_boundary"] == {
        "affects_model_behavior_only": True,
        "changes_memory_retrieval": False,
        "changes_focus": False,
        "changes_intentions": False,
        "triggers_backend_actions": False,
    }
    assert "organ.affect.appraised" in [event.type for event in events]


def test_affect_model_injects_compact_pack_when_signal_exists(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        session, turn, message = _session_turn_message(
            db,
            "Fantastico, questa direzione mi piace davvero molto.",
        )
        runtime = _runtime(
            db,
            session=session,
            turn_id=turn.id,
            message=message,
            settings=Settings(organ_affect_mode="model"),
        )

        events = repositories.list_events_for_turn(db, turn_id=turn.id)

    block_types = [block["type"] for block in runtime["blocks"]]
    assert block_types == [
        "session_context",
        "message_context",
        "affective_context",
        "scarlet_state",
    ]
    affect_block = runtime["blocks"][2]
    assert affect_block["content"]["current_emotion"] == "enthusiasm"
    assert affect_block["content"]["usage"]["affects"] == "model_behavior_only"
    assert affect_block["content"]["usage"]["does_not_change_memory_retrieval"] is True
    assert affect_block["content"]["usage"]["does_not_change_focus"] is True
    assert affect_block["content"]["usage"]["does_not_change_intentions"] is True
    assert runtime["blocks"][3]["content"]["mood_expression"].startswith(
        "See affective_context"
    )
    assert "organ.affect.surfaced" in [event.type for event in events]


def test_affect_mind_api_is_read_only_and_exposes_state_and_prototypes(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    client = make_client(db_engine)
    with Session(db_engine) as db:
        session, turn, _message = _session_turn_message(
            db,
            "Sono curiosa di vedere lo stato affettivo.",
        )
        state = repositories.create_affect_state(
            db,
            owner_profile_id="local-user",
            session_id=session.id,
            turn_id=turn.id,
            mode="model",
            emotion="curiosity",
            intensity=0.48,
            intensity_label="medium",
            valence=0.35,
            activation=0.55,
            prototype_version="affect-prototypes-v1",
            variables={"curiosity": 0.48, "caution": 0.1},
            causes=[
                {
                    "source": "user_message",
                    "signal": "curiosity",
                    "strength": 0.48,
                }
            ],
            tendencies={
                "attention_tendency": "notice gaps",
                "action_tendency": "explore",
                "relational_posture": "present",
            },
            pack={
                "current_emotion": "curiosity",
                "usage": {"affects": "model_behavior_only"},
            },
            metadata={"test": True},
        )
        session_id = session.id
        turn_id = turn.id
        state_id = state.id

    read = client.post(
        "/mind/call",
        json={
            "session_id": session_id,
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/affect",
            "body": {"action": "read"},
            "intent": "Inspect current affective state.",
        },
    ).json()

    assert read["ok"] is True
    assert read["result"]["operation"] == "affect.read"
    assert read["result"]["affect_state"]["id"] == state_id
    assert read["result"]["affect_state"]["emotion"] == "curiosity"
    assert read["result"]["affect_policy"]["read_only"] is True
    assert read["result"]["affect_policy"]["scarlet_cannot_write_emotion_by_tool"] is True
    assert read["result"]["affect_policy"]["does_not_mutate_memory"] is True

    listed = client.post(
        "/mind/call",
        json={
            "session_id": session_id,
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/affect",
            "body": {"action": "list", "emotion": "curiosity", "limit": 5},
            "intent": "Inspect affective state history.",
        },
    ).json()

    assert listed["ok"] is True
    assert [item["id"] for item in listed["result"]["items"]] == [state_id]

    prototypes = client.post(
        "/mind/call",
        json={
            "session_id": session_id,
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/affect",
            "body": {"action": "prototypes"},
            "intent": "Inspect affective prototypes.",
        },
    ).json()

    assert prototypes["ok"] is True
    assert prototypes["result"]["operation"] == "affect.prototypes"
    prototype_names = {item["emotion"] for item in prototypes["result"]["items"]}
    assert {"curiosity", "frustration", "sadness"} <= prototype_names
    assert prototypes["result"]["affect_policy"]["backend_appraised"] is True


def test_affect_neutral_message_does_not_create_state_or_block(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        session, turn, message = _session_turn_message(db, "Ciao.")
        runtime = _runtime(
            db,
            session=session,
            turn_id=turn.id,
            message=message,
            settings=Settings(organ_affect_mode="model"),
        )

        traces = repositories.list_traces_for_turn(db, turn_id=turn.id)
        states = repositories.list_affect_states(db, turn_id=turn.id)

    assert "affective_context" not in [block["type"] for block in runtime["blocks"]]
    assert states == []
    affect_trace = next(trace for trace in traces if trace.kind == "organ.affect")
    assert affect_trace.payload_json["state"]["emotion"] is None


def test_recent_failures_can_drive_frustration_without_message_keywords(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        session, turn, message = _session_turn_message(db, "Va bene, continua.")
        runtime = _runtime(
            db,
            session=session,
            turn_id=turn.id,
            message=message,
            recent_events=[
                {
                    "type": "mind.tool_call.failed",
                    "status": "failed",
                    "source": "mind_api",
                },
                {
                    "type": "mind.tool_call.failed",
                    "status": "failed",
                    "source": "mind_api",
                },
            ],
            settings=Settings(organ_affect_mode="model"),
        )

    affect_block = next(
        block for block in runtime["blocks"] if block["type"] == "affective_context"
    )
    assert affect_block["content"]["current_emotion"] == "frustration"
    assert any(
        "recent_runtime_events" in cause
        for cause in affect_block["content"]["causes"]
    )


def _session_turn_message(db: Session, content: str):
    session = repositories.create_chat_session(db, title="Affect context")
    turn = repositories.create_turn(db, session_id=session.id, model="MiniMax-M3")
    message = repositories.add_message(
        db,
        session_id=session.id,
        turn_id=turn.id,
        role="user",
        content=content,
    )
    return session, turn, message


def _runtime(
    db: Session,
    *,
    session,
    turn_id: str,
    message,
    settings: Settings,
    recent_events: list[dict] | None = None,
) -> dict:
    return build_runtime_context_payload(
        db,
        chat_session=session,
        turn_id=turn_id,
        current_user_message=message,
        memory_context={
            "searched": True,
            "selected": [],
            "near_miss": [],
            "excluded": [],
            "conflicts": [],
            "negative_evidence": "no_relevant_memory_selected",
        },
        recent_dialogue=[],
        recent_events=recent_events or [],
        capabilities={},
        temporal_context={"now": "2026-06-25T10:00:00+02:00"},
        timestamp=datetime(2026, 6, 25, 8, 0, tzinfo=timezone.utc),
        runtime_preferences=RuntimePreferences(
            timezone="Europe/Rome",
            language="it",
            language_label="Italiano",
            country_code="IT",
            country_label="Italia",
            profile_id="local-user",
            user_display_name="Utente locale",
            privacy_scope="local_single_user",
            source="test",
        ),
        settings=settings,
    )
