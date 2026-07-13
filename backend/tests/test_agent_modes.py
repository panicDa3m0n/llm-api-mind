from sqlmodel import Session

from app.config import Settings
from app.mind.agent_modes import (
    agent_mode_registry,
    resolve_agent_mode,
    route_context_blocks,
)
from app.mind.contracts import MindAPIContext
from app.mind.shell import MindShellRequest, dispatch_mind_shell
from app.storage import repositories
from app.storage.db import init_db


def _context(db_engine, *, session_id: str, turn_id: str | None = None):
    return MindAPIContext(
        engine=db_engine,
        session_id=session_id,
        turn_id=turn_id,
        settings=Settings(environment="test", maintenance_enabled=False),
    )


def test_mode_registry_uses_agent_tags_and_excludes_background_processes() -> None:
    registry = agent_mode_registry()
    focus = next(
        item
        for item in registry["capabilities"]
        if item["capability"] == "organ.focus"
    )

    assert {item["tag"] for item in registry["modes"]} == {
        "idle",
        "interactive",
        "scouting",
    }
    assert set(focus["mode_tags"]) == {"idle", "interactive", "scouting"}
    assert registry["background_processes_are_agent_modes"] is False
    assert registry["routing_scope"] == "automatic_model_context_v1"
    assert registry["manually_resumable_tags"] == ["idle", "scouting"]
    interactive = next(
        item for item in registry["modes"] if item["tag"] == "interactive"
    )
    assert interactive["manually_resumable"] is False


def test_mode_shell_persists_preference_and_system_interaction_overrides_it(
    db_engine,
) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(db, title="Modes")
        turn = repositories.create_turn(
            db,
            session_id=chat_session.id,
            model="MiniMax-M3",
        )
        session_id = chat_session.id
        turn_id = turn.id

    selected = dispatch_mind_shell(
        MindShellRequest(
            command='mode set scouting --reason "Study the environment later"',
            intent="Select the posture to resume after this exchange.",
        ),
        context=_context(db_engine, session_id=session_id, turn_id=turn_id),
    )

    assert selected.ok is True
    assert selected.result["data"]["change"]["preferred_tag"] == "scouting"
    assert selected.result["data"]["execution_started"] is False
    assert selected.result["data"]["runtime_effect"] == (
        "persistent_posture_only_no_autonomous_cycle"
    )
    assert selected.result["data"]["agent_mode"]["active_tag"] == "interactive"
    assert selected.result["data"]["agent_mode"]["resume_tag"] == "scouting"

    with Session(db_engine) as db:
        idle_state = resolve_agent_mode(db, profile_id="local-user")
        interactive_state = resolve_agent_mode(
            db,
            profile_id="local-user",
            system_mode="interactive",
            system_reason="Human turn",
        )
    assert idle_state["active_tag"] == "scouting"
    assert idle_state["active_runtime_implemented"] is False
    assert interactive_state["active_tag"] == "interactive"
    assert interactive_state["active_runtime_implemented"] is True
    assert interactive_state["resume_tag"] == "scouting"
    assert interactive_state["resume_runtime_implemented"] is False


def test_mode_routing_filters_only_automatic_context_blocks() -> None:
    blocks = [
        {"type": "session_context"},
        {"type": "message_context"},
        {"type": "affective_context"},
        {"type": "scarlet_state"},
    ]

    routed, decision = route_context_blocks(
        blocks,
        active_tag="idle",
        routing_mode="active",
    )

    assert [block["type"] for block in routed] == [
        "session_context",
        "scarlet_state",
    ]
    assert decision["ineligible_block_types"] == [
        "message_context",
        "affective_context",
    ]


def test_mode_shell_rejects_persisting_system_owned_interactive_mode(
    db_engine,
) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(db, title="Mode ownership")
        session_id = chat_session.id

    response = dispatch_mind_shell(
        MindShellRequest(
            command='mode set interactive --reason "persist human exchange"'
        ),
        context=_context(db_engine, session_id=session_id),
    )

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == "mode.set_not_resumable"
    with Session(db_engine) as db:
        state = resolve_agent_mode(db, profile_id="local-user")
    assert state["active_tag"] == "idle"
