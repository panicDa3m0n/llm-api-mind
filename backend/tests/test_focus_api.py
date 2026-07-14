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


def test_focus_set_and_shift_keep_one_active_focus(db_engine: Engine) -> None:
    client = make_client(db_engine)
    session = client.post("/api/chat/sessions", json={"title": "Focus"}).json()
    with Session(db_engine) as db:
        turn = repositories.create_turn(db, session_id=session["id"], model="MiniMax-M3")
        message = repositories.add_message(
            db,
            session_id=session["id"],
            turn_id=turn.id,
            role="user",
            content="Teniamo il focus sulla progettazione dell'organo attenzione.",
        )
        turn_id = turn.id
        message_id = message.id

    first = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/focus",
            "body": {
                "action": "set",
                "object": "Progettazione dell'organo focus",
                "type": "research",
                "intensity": 0.8,
                "duration_policy": "until_resolved",
                "reason": "Scarlet deve tenere stabile il filo attentivo.",
            },
            "intent": "Set foreground focus.",
        },
    ).json()

    assert first["ok"] is True
    active = first["result"]["active_focus"]
    assert active["object"] == "Progettazione dell'organo focus"
    assert active["type"] == "research"
    assert active["source_session_id"] == session["id"]
    assert active["source_turn_id"] == turn_id
    assert active["source_message_id"] == message_id
    assert first["result"]["focus_policy"]["does_not_filter_memory_by_default"] is True

    second = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/focus",
            "body": {
                "action": "shift",
                "object": "Verifica test focus",
                "type": "verification",
                "reason": "Il lavoro si sposta dalla progettazione alla verifica.",
            },
            "intent": "Shift foreground focus.",
        },
    ).json()

    assert second["ok"] is True
    assert second["result"]["previous_focus"]["status"] == "superseded"
    assert second["result"]["transition"]["relation"] == "shifted_to"
    with Session(db_engine) as db:
        active_focus = repositories.get_active_focus(db, owner_profile_id="local-user")
        all_active = repositories.list_focus_records(
            db,
            owner_profile_id="local-user",
            status="active",
            limit=10,
        )
    assert active_focus is not None
    assert active_focus.focus_object == "Verifica test focus"
    assert len(all_active) == 1

    timeline = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/focus",
            "body": {"action": "timeline", "limit": 10},
            "intent": "Inspect focus movement history.",
        },
    ).json()

    assert timeline["ok"] is True
    assert timeline["result"]["operation"] == "focus.timeline"
    assert len(timeline["result"]["nodes"]) >= 2
    assert {
        edge["relation"] for edge in timeline["result"]["edges"]
    } >= {"started", "shifted_to"}
    assert timeline["result"]["focus_policy"]["separate_from_memory_retrieval"] is True


def test_focus_error_returns_usage_guide(db_engine: Engine) -> None:
    client = make_client(db_engine)
    session = client.post("/api/chat/sessions", json={"title": "Focus error"}).json()

    response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "method": "POST",
            "path": "/mind/focus",
            "body": {"action": "set"},
            "intent": "Trigger focus shape guidance.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "focus.missing_object"
    assert body["usage_guide"]["method"] == "POST"
    assert body["usage_guide"]["path"] == "/mind/focus"
    assert body["usage_guide"]["parameters"]["object"]["description"]
    assert body["suggested_next_actions"][0].startswith("Use usage_guide")


def test_focus_hold_persists_held_foreground_status(db_engine: Engine) -> None:
    client = make_client(db_engine)
    session = client.post("/api/chat/sessions", json={"title": "Focus hold"}).json()

    created = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "method": "POST",
            "path": "/mind/focus",
            "body": {"action": "set", "object": "Hold lifecycle evidence"},
            "intent": "Set focus before holding it.",
        },
    ).json()
    focus_id = created["result"]["active_focus"]["id"]

    held = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "method": "POST",
            "path": "/mind/focus",
            "body": {"action": "hold", "focus_id": focus_id, "reason": "Keep it foreground."},
            "intent": "Hold foreground focus.",
        },
    ).json()

    assert held["ok"] is True
    assert held["result"]["active_focus"]["status"] == "held"
    with Session(db_engine) as db:
        current = repositories.get_active_focus(db, owner_profile_id="local-user")
    assert current is not None
    assert current.id == focus_id
    assert current.status == "held"


def test_focus_context_runtime_block_is_model_facing_when_enabled(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        session = repositories.create_chat_session(db, title="Focus runtime")
        turn = repositories.create_turn(db, session_id=session.id, model="MiniMax-M3")
        message = repositories.add_message(
            db,
            session_id=session.id,
            turn_id=turn.id,
            role="user",
            content="Continuiamo dal focus attivo.",
        )
        focus = repositories.create_focus_record(
            db,
            owner_profile_id="local-user",
            focus_object="Stabilizzare l'organo focus",
            focus_type="implementation",
            reason="Verificare che il runtime lo renda visibile come stato separato.",
            source_session_id=session.id,
            source_turn_id=turn.id,
            source_message_id=message.id,
        )
        focus_id = focus.id
        turn_id = turn.id
        runtime = build_runtime_context_payload(
            db,
            chat_session=session,
            turn_id=turn.id,
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
            recent_events=[],
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
            settings=Settings(organ_focus_mode="model"),
        )

    block_types = [block["type"] for block in runtime["blocks"]]
    assert block_types == [
        "session_context",
        "agent_mode_context",
        "message_context",
        "focus_context",
        "scarlet_state",
    ]
    focus_block = runtime["blocks"][3]
    assert focus_block["content"]["current_focus"]["id"] == focus_id
    assert focus_block["content"]["current_focus"]["object"] == (
        "Stabilizzare l'organo focus"
    )
    assert focus_block["content"]["usage"]["does_not_limit_memory_retrieval"] is True
    assert runtime["blocks"][4]["content"]["focus"].startswith("See focus_context")

    with Session(db_engine) as db:
        events = repositories.list_events_for_turn(db, turn_id=turn_id)
    assert "organ.focus.surfaced" in [event.type for event in events]
