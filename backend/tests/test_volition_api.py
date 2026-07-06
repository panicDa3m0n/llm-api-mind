from datetime import datetime, timedelta, timezone

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


def test_volition_create_review_promote_and_resolve(db_engine: Engine) -> None:
    client = make_client(db_engine)
    session = client.post("/api/chat/sessions", json={"title": "Volition"}).json()
    with Session(db_engine) as db:
        turn = repositories.create_turn(db, session_id=session["id"], model="MiniMax-M3")
        message = repositories.add_message(
            db,
            session_id=session["id"],
            turn_id=turn.id,
            role="user",
            content="Scarlet nota un filo interno che vorrebbe riprendere.",
        )
        focus = repositories.create_focus_record(
            db,
            owner_profile_id="local-user",
            focus_object="Studiare volizione senza task manager",
            focus_type="research",
            reason="Serve come foreground durante il test volition.",
            source_session_id=session["id"],
            source_turn_id=turn.id,
            source_message_id=message.id,
        )
        turn_id = turn.id
        message_id = message.id
        focus_id = focus.id

    created = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/volition",
            "body": {
                "action": "create",
                "desire": (
                    "Capire se le intenzioni latenti migliorano la continuita "
                    "di Scarlet senza invadere le normali chat."
                ),
                "origin": "scarlet",
                "horizon": "short_term",
                "intensity": 0.72,
                "autonomy_level": "self_generated",
                "reason": (
                    "E una direzione interna di ricerca, non un task utente "
                    "e non una memoria semantica."
                ),
                "next_possible_reflection": (
                    "Rivedere questa intenzione dopo test di chat reali."
                ),
                "links": [
                    {
                        "target_type": "focus",
                        "target_id": focus_id,
                        "relation": "emerged_during",
                    }
                ],
            },
            "intent": "Create a latent self-generated intention.",
        },
    ).json()

    assert created["ok"] is True
    intention = created["result"]["intention"]
    assert intention["source_session_id"] == session["id"]
    assert intention["source_turn_id"] == turn_id
    assert intention["source_message_id"] == message_id
    assert intention["source_focus_id"] == focus_id
    assert intention["status"] == "active"
    assert intention["links"][0]["target_type"] == "focus"
    assert created["result"]["volition_policy"]["automatic_chat_injection"] is False

    intention_id = intention["id"]
    searched = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/volition",
            "body": {
                "action": "search",
                "query": "intenzioni latenti",
                "limit": 5,
            },
            "intent": "Search the latent intention archive.",
        },
    ).json()

    assert searched["ok"] is True
    assert searched["result"]["items"][0]["id"] == intention_id

    reviewed = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/volition",
            "body": {
                "action": "review",
                "intention_id": intention_id,
                "status": "active",
                "reason": "La direzione resta utile ma non deve diventare focus subito.",
            },
            "intent": "Review the latent intention.",
        },
    ).json()

    assert reviewed["ok"] is True
    assert reviewed["result"]["intention"]["review_count"] == 1

    promoted = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/volition",
            "body": {
                "action": "promote_to_focus_candidate",
                "intention_id": intention_id,
                "reason": "Ora potrebbe diventare attenzione foreground.",
            },
            "intent": "Prepare a focus candidate from volition.",
        },
    ).json()

    assert promoted["ok"] is True
    assert promoted["result"]["applied"] is False
    assert promoted["result"]["focus_candidate"]["path"] == "/mind/focus"
    with Session(db_engine) as db:
        active_focus = repositories.get_active_focus(db, owner_profile_id="local-user")
    assert active_focus is not None
    assert active_focus.id == focus_id

    resolved = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/volition",
            "body": {
                "action": "resolve",
                "intention_id": intention_id,
                "resolution": "Il registro intenzionale e stato verificato.",
            },
            "intent": "Resolve the latent intention.",
        },
    ).json()

    assert resolved["ok"] is True
    assert resolved["result"]["closed_intention"]["status"] == "resolved"

    with Session(db_engine) as db:
        events = repositories.list_events_for_turn(db, turn_id=turn_id)
        traces = repositories.list_traces_for_session(
            db,
            session_id=session["id"],
            limit=20,
        )
    event_types = [event.type for event in events]
    assert "organ.volition.created" in event_types
    assert "organ.volition.reviewed" in event_types
    assert "organ.volition.closed" in event_types
    assert "organ.volition" in [trace.kind for trace in traces]


def test_volition_error_returns_usage_guide(db_engine: Engine) -> None:
    client = make_client(db_engine)
    session = client.post("/api/chat/sessions", json={"title": "Volition error"}).json()

    response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "method": "POST",
            "path": "/mind/volition",
            "body": {"action": "create", "reason": "Missing desire."},
            "intent": "Trigger volition shape guidance.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "volition.missing_desire"
    assert body["usage_guide"]["method"] == "POST"
    assert body["usage_guide"]["path"] == "/mind/volition"
    assert body["usage_guide"]["parameters"]["desire"]["description"]
    assert body["suggested_next_actions"][0].startswith("Use usage_guide")


def test_volition_list_due_returns_reviewable_open_intentions(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)
    session = client.post("/api/chat/sessions", json={"title": "Volition due"}).json()
    now = datetime.now(timezone.utc)
    with Session(db_engine) as db:
        turn = repositories.create_turn(db, session_id=session["id"], model="MiniMax-M3")
        message = repositories.add_message(
            db,
            session_id=session["id"],
            turn_id=turn.id,
            role="user",
            content="Prepara un registro intenzionale da rivedere.",
        )
        due = repositories.create_intention_record(
            db,
            owner_profile_id="local-user",
            desire="Rivedere una direzione arrivata a maturazione.",
            reason="Deve comparire nella coda delle intenzioni dovute.",
            next_review_at=now - timedelta(minutes=5),
            source_session_id=session["id"],
            source_turn_id=turn.id,
            source_message_id=message.id,
        )
        future = repositories.create_intention_record(
            db,
            owner_profile_id="local-user",
            desire="Rivedere una direzione non ancora matura.",
            reason="Non deve comparire finche il suo tempo non arriva.",
            next_review_at=now + timedelta(days=1),
            source_session_id=session["id"],
            source_turn_id=turn.id,
            source_message_id=message.id,
        )
        unscheduled = repositories.create_intention_record(
            db,
            owner_profile_id="local-user",
            desire="Rivedere una direzione senza schedulazione.",
            reason="Compare solo quando include_unscheduled e attivo.",
            source_session_id=session["id"],
            source_turn_id=turn.id,
            source_message_id=message.id,
        )
        turn_id = turn.id
        due_id = due.id
        future_id = future.id
        unscheduled_id = unscheduled.id

    due_only = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/volition",
            "body": {"action": "list_due", "limit": 10},
            "intent": "Inspect intentions due for review.",
        },
    ).json()

    assert due_only["ok"] is True
    due_ids = {item["id"] for item in due_only["result"]["items"]}
    assert due_id in due_ids
    assert future_id not in due_ids
    assert unscheduled_id not in due_ids
    assert due_only["result"]["include_unscheduled"] is False

    with_unscheduled = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/volition",
            "body": {
                "action": "list_due",
                "limit": 10,
                "include_unscheduled": True,
            },
            "intent": "Inspect due and unscheduled intentions.",
        },
    ).json()

    all_ids = {item["id"] for item in with_unscheduled["result"]["items"]}
    assert due_id in all_ids
    assert unscheduled_id in all_ids
    assert future_id not in all_ids
    assert with_unscheduled["result"]["volition_policy"]["automatic_chat_injection"] is False


def test_volition_is_not_injected_into_runtime_context(db_engine: Engine) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        session = repositories.create_chat_session(db, title="No volition injection")
        turn = repositories.create_turn(db, session_id=session.id, model="MiniMax-M3")
        message = repositories.add_message(
            db,
            session_id=session.id,
            turn_id=turn.id,
            role="user",
            content="Rispondi alla richiesta corrente.",
        )
        repositories.create_intention_record(
            db,
            owner_profile_id="local-user",
            desire="Restare curiosa sulle proprie intenzioni latenti.",
            reason="Dato di test per verificare che non venga iniettato.",
            source_session_id=session.id,
            source_turn_id=turn.id,
            source_message_id=message.id,
        )
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
            settings=Settings(organ_volition_mode="model"),
        )

    assert "volition_context" not in [block["type"] for block in runtime["blocks"]]
