from sqlmodel import Session

from app.config import Settings
from app.mind.agent_modes import (
    AGENT_MODE_VALUES,
    MODE_CAPABILITIES,
    agent_mode_registry,
    mode_routing_decision,
    resolve_agent_mode,
    route_context_blocks,
    set_preferred_agent_mode,
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
    scouting = next(item for item in registry["modes"] if item["tag"] == "scouting")
    assert interactive["manually_resumable"] is False
    assert scouting["implemented_runtime"] is True
    assert "during autonomous cognition" in scouting["purpose"]


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
        "persistent_posture_for_autonomous_cycles"
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
    assert idle_state["active_runtime_implemented"] is True
    assert interactive_state["active_tag"] == "interactive"
    assert interactive_state["active_runtime_implemented"] is True
    assert interactive_state["resume_tag"] == "scouting"
    assert interactive_state["resume_runtime_implemented"] is True


def test_mode_routing_filters_only_automatic_context_blocks() -> None:
    blocks = [
        {"id": "session", "type": "session_context"},
        {"id": "message", "type": "message_context"},
        {"id": "affect", "type": "affective_context"},
        {"id": "state", "type": "scarlet_state"},
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
    assert decision["included_block_ids"] == ["session", "state"]
    assert decision["excluded_block_ids"] == ["message", "affect"]
    assert decision["routing_applied"] is True
    assert decision["on_demand_shell_commands_remain_available"] is True
    assert [item["delivery_disposition"] for item in decision["block_decisions"]] == [
        "included",
        "excluded",
        "excluded",
        "included",
    ]


def test_mode_routing_receipts_distinguish_policy_from_actual_delivery() -> None:
    blocks = [
        {"id": "session", "type": "session_context"},
        {"id": "message", "type": "message_context"},
        {"id": "affect", "type": "affective_context"},
        {"id": "future", "type": "future_context"},
    ]

    expected = {
        "off": {
            "ids": ["session", "message", "affect", "future"],
            "excluded": [],
            "would_exclude": [],
        },
        "shadow": {
            "ids": ["session", "message", "affect", "future"],
            "excluded": [],
            "would_exclude": ["message_context", "affective_context"],
        },
        "active": {
            "ids": ["session", "future"],
            "excluded": ["message_context", "affective_context"],
            "would_exclude": [],
        },
    }

    for routing_mode, receipt in expected.items():
        routed, decision = route_context_blocks(
            blocks,
            active_tag="idle",
            routing_mode=routing_mode,
        )
        assert [block["id"] for block in routed] == receipt["ids"]
        assert decision["included_block_ids"] == receipt["ids"]
        assert decision["excluded_block_types"] == receipt["excluded"]
        assert decision["would_exclude_block_types"] == receipt["would_exclude"]
        assert decision["ineligible_block_types"] == [
            "message_context",
            "affective_context",
        ]
        assert decision["unregistered_block_types"] == ["future_context"]
        assert all(item["reason"] for item in decision["block_decisions"])


def test_mode_routing_inventory_covers_every_registered_context_block() -> None:
    context_specs = [
        spec for spec in MODE_CAPABILITIES if spec.context_block_type is not None
    ]
    blocks = [
        {"id": f"block-{index}", "type": spec.context_block_type}
        for index, spec in enumerate(context_specs)
    ]

    for active_tag in AGENT_MODE_VALUES:
        decision = mode_routing_decision(
            active_tag=active_tag,
            routing_mode="active",
            blocks=blocks,
        )
        assert len(decision["block_decisions"]) == len(context_specs)
        for spec, block_decision in zip(
            context_specs, decision["block_decisions"], strict=True
        ):
            expected = active_tag in spec.mode_tags
            assert block_decision["capability"] == spec.capability
            assert block_decision["required_mode_tags"] == list(spec.mode_tags)
            assert block_decision["delivered"] is expected
            assert block_decision["eligibility"] == (
                "eligible" if expected else "ineligible"
            )


def test_mode_routing_preserves_duplicate_blocks_by_input_identity() -> None:
    blocks = [
        {"id": "affect-primary", "type": "affective_context"},
        {"id": "affect-secondary", "type": "affective_context"},
    ]

    routed, decision = route_context_blocks(
        blocks,
        active_tag="idle",
        routing_mode="active",
    )

    assert routed == []
    assert decision["excluded_block_ids"] == ["affect-primary", "affect-secondary"]
    assert [item["input_index"] for item in decision["block_decisions"]] == [0, 1]


def test_mode_routing_rejects_invalid_registry_inputs() -> None:
    try:
        mode_routing_decision(active_tag="dream", routing_mode="active")
    except ValueError as exc:
        assert str(exc) == "Unsupported active agent mode: dream"
    else:
        raise AssertionError("unknown active mode should fail")

    try:
        mode_routing_decision(active_tag="idle", routing_mode="maybe")
    except ValueError as exc:
        assert str(exc) == "Unsupported agent mode routing: maybe"
    else:
        raise AssertionError("unknown routing mode should fail")


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


def test_mode_store_primitive_rejects_system_owned_interactive_mode(db_engine) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        try:
            set_preferred_agent_mode(
                db,
                profile_id="local-user",
                mode="interactive",
                reason="internal caller must not bypass ownership",
            )
        except ValueError as exc:
            assert str(exc) == "Agent mode is not resumable: interactive"
        else:
            raise AssertionError("interactive must remain system-owned")
        state = resolve_agent_mode(db, profile_id="local-user")
    assert state["active_tag"] == "idle"


def test_manual_memory_retrieval_remains_available_with_scouting_resume_mode(
    db_engine,
) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        source = repositories.create_chat_session(db, title="Source")
        source_turn = repositories.create_turn(
            db, session_id=source.id, model="MiniMax-M3"
        )
        source_message = repositories.add_message(
            db,
            session_id=source.id,
            turn_id=source_turn.id,
            role="user",
            content="The durable anchor is Aurora Sette.",
        )
        repositories.add_memory(
            db,
            memory_type="project_fact",
            scope="project",
            content="The durable anchor is Aurora Sette.",
            reason_for_storage="Mode routing retrieval control.",
            source_session_id=source.id,
            source_turn_id=source_turn.id,
            source_message_id=source_message.id,
        )
        set_preferred_agent_mode(
            db,
            profile_id="local-user",
            mode="scouting",
            reason="Resume exploratory posture.",
        )
        later = repositories.create_chat_session(db, title="Later session")
        later_turn = repositories.create_turn(
            db, session_id=later.id, model="MiniMax-M3"
        )
        later_session_id = later.id
        later_turn_id = later_turn.id

    response = dispatch_mind_shell(
        MindShellRequest(
            command='memory search "Aurora Sette" --top 5',
            intent="Recover the sourceable anchor on demand.",
        ),
        context=_context(
            db_engine,
            session_id=later_session_id,
            turn_id=later_turn_id,
        ),
    )

    assert response.ok is True
    assert response.result["data"]["memories"][0]["content"] == (
        "The durable anchor is Aurora Sette."
    )
    with Session(db_engine) as db:
        state = resolve_agent_mode(
            db,
            profile_id="local-user",
            system_mode="interactive",
            system_reason="Later human turn",
        )
    assert state["active_tag"] == "interactive"
    assert state["resume_tag"] == "scouting"
