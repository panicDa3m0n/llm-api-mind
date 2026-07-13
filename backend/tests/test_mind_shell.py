from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.mind.command_registry import validate_shell_command
from app.mind.memory import MindAPIContext
from app.mind.shell import MindShellRequest, dispatch_mind_shell
from app.storage import repositories
from app.storage.db import init_db


def _context(db_engine: Engine, *, session_id: str | None = None) -> MindAPIContext:
    return MindAPIContext(
        engine=db_engine,
        session_id=session_id,
        settings=Settings(
            app_name="Test Mind",
            environment="test",
            minimax_api_key="test-key",
        ),
    )


def _session(db_engine: Engine) -> str:
    init_db(db_engine)
    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(db, title="Shell test")
        return chat_session.id


def test_mind_shell_help_returns_command_catalog(db_engine: Engine) -> None:
    response = dispatch_mind_shell(
        MindShellRequest(command="help memory", intent="Inspect memory commands."),
        context=_context(db_engine),
    )

    assert response.ok is True
    assert response.result["operation"] == "mind_shell.help"
    commands = response.result["catalog"]["commands"]
    assert commands[0]["namespace"] == "memory"
    assert any("memory search" in item for item in commands[0]["commands"])
    assert response.result["schema"]["schema_command"] == "help"


def test_mind_shell_opens_source_message_and_public_turn_bundle(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(db, title="Source navigation")
        turn = repositories.create_turn(
            db,
            session_id=chat_session.id,
            model="MiniMax-M3",
        )
        user_message = repositories.add_message(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            role="user",
            content="Ricordati che preferisco risposte concise.",
        )
        repositories.add_tool_call(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            tool_name="mind_shell",
            arguments={"command": "memory write ..."},
            result={"ok": True},
            status="completed",
        )
        repositories.add_message(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            role="assistant",
            content="Va bene, sarò concisa.",
        )
        repositories.complete_turn(db, turn_id=turn.id)
        session_id = chat_session.id
        turn_id = turn.id
        message_id = user_message.id

    context = _context(db_engine, session_id=session_id)
    message_result = dispatch_mind_shell(
        MindShellRequest(
            command=f"session message {message_id}",
            intent="Inspect the exact memory source message.",
        ),
        context=context,
    )
    assert message_result.ok is True
    assert message_result.result["data"]["message"]["id"] == message_id
    assert message_result.result["data"]["source"]["turn_id"] == turn_id

    turn_result = dispatch_mind_shell(
        MindShellRequest(
            command=f"session turn {turn_id}",
            intent="Inspect the complete public source turn.",
        ),
        context=context,
    )
    assert turn_result.ok is True
    data = turn_result.result["data"]
    assert [message["role"] for message in data["messages"]] == [
        "user",
        "assistant",
    ]
    assert data["tool_calls"][0]["tool_name"] == "mind_shell"
    assert all("payload" not in trace for trace in data["trace_references"])


def test_mind_shell_memory_write_and_search_use_command_arguments(
    db_engine: Engine,
) -> None:
    session_id = _session(db_engine)
    context = _context(db_engine, session_id=session_id)

    write = dispatch_mind_shell(
        MindShellRequest(
            command=(
                'memory write --type user_preference --scope user '
                '--content "L utente preferisce bevande calde senza caffeina la sera." '
                '--reason "Preferenza riusabile in consigli futuri" '
                '--future-use "Quando si parla di bevande o sonno"'
            ),
            intent="Store a reusable user preference.",
        ),
        context=context,
    )

    assert write.ok is True
    assert write.result["target"] == "memory.write"
    assert write.result["command"].startswith("memory write")
    data = write.result["data"]
    assert data["stored"] is True
    memory_id = data["memory_id"]
    assert memory_id.startswith("mem_")
    assert "/mind/" not in str(write.model_dump(mode="json"))

    search = dispatch_mind_shell(
        MindShellRequest(
            command='memory search "bevande calde senza caffeina sera" --top 5',
            intent="Recover relevant preference.",
        ),
        context=context,
    )

    assert search.ok is True
    assert search.result["target"] == "memory.search"
    assert search.result["data"]["model_output_profile"] == (
        "mind-shell-memory-search-compact-v1"
    )
    assert "retrieval_shadow" not in search.result["data"]
    assert "retrieval_graph" not in search.result["data"]
    assert "retrieval_summary" in search.result["data"]
    memories = search.result["data"]["memories"]
    assert [item["id"] for item in memories] == [memory_id]
    assert memories[0]["source"]


def test_mind_shell_missing_memory_write_fields_returns_shell_guide(
    db_engine: Engine,
) -> None:
    session_id = _session(db_engine)

    response = dispatch_mind_shell(
        MindShellRequest(command='memory write "Ricorda questa cosa"'),
        context=_context(db_engine, session_id=session_id),
    )

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == "shell.memory_write_missing_fields"
    assert response.usage_guide is not None
    assert response.usage_guide["commands"][0]["namespace"] == "memory"
    assert "memory write" in response.suggested_next_actions[0]
    assert "/mind/" not in str(response.model_dump(mode="json"))


def test_mind_shell_session_list_and_open(db_engine: Engine) -> None:
    session_id = _session(db_engine)
    context = _context(db_engine, session_id=session_id)

    listed = dispatch_mind_shell(
        MindShellRequest(command='session list --query "Shell" --limit 5'),
        context=context,
    )
    assert listed.ok is True
    assert listed.result["target"] == "session.list"
    assert listed.result["data"]["sessions"][0]["id"] == session_id

    opened = dispatch_mind_shell(
        MindShellRequest(command=f"session open {session_id} --limit 20"),
        context=context,
    )
    assert opened.ok is True
    assert opened.result["target"] == "session.open"
    assert opened.result["data"]["session"]["id"] == session_id
    assert opened.result["data"]["transcript_window"]["returned_count"] >= 0


def test_mind_shell_focus_volition_and_affect_commands(db_engine: Engine) -> None:
    session_id = _session(db_engine)
    context = _context(db_engine, session_id=session_id)

    focus = dispatch_mind_shell(MindShellRequest(command="focus get"), context=context)
    assert focus.ok is True
    assert focus.result["target"] == "focus.read"

    volition = dispatch_mind_shell(
        MindShellRequest(command="volition list active --limit 5"),
        context=context,
    )
    assert volition.ok is True
    assert volition.result["target"] == "volition.list_active"

    bare_volition_list = dispatch_mind_shell(
        MindShellRequest(command="volition list"),
        context=context,
    )
    assert bare_volition_list.ok is True
    assert bare_volition_list.result["target"] == "volition.list_active"
    bare_validation = validate_shell_command("volition list")
    assert bare_validation["call_is_available"] is True
    assert bare_validation["canonical_action"] == "list_active"

    affect = dispatch_mind_shell(
        MindShellRequest(command="affect prototypes"),
        context=context,
    )
    assert affect.ok is True
    assert affect.result["target"] == "affect.prototypes"


def test_mind_shell_memory_unavailable_action_is_classified(
    db_engine: Engine,
) -> None:
    session_id = _session(db_engine)
    response = dispatch_mind_shell(
        MindShellRequest(command='memory update mem_fake --content "new value"'),
        context=_context(db_engine, session_id=session_id),
    )

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == "shell.memory_action_unavailable"
    validation = response.result["details"]["command_validation"]
    assert validation["schema_status"] == "unavailable_by_design"
    assert validation["call_is_available"] is False
    assert "memory supersede" in response.suggested_next_actions[0]


def test_mind_shell_registry_rejects_incomplete_state_commands() -> None:
    rejected = {
        "memory deprecate --reason obsolete": "missing_required_argument",
        "memory deprecate mem_fake": "missing_required_argument",
        "memory supersede mem_old mem_new": "missing_required_argument",
        'volition create "understand this"': "missing_required_argument",
        "focus resolve focus_fake": "missing_required_argument",
        "volition deprecate intent_fake": "missing_required_argument",
    }

    for command, expected_status in rejected.items():
        validation = validate_shell_command(command)
        assert validation["schema_status"] == expected_status
        assert validation["call_is_available"] is False

    accepted = [
        'memory deprecate mem_fake --reason "obsolete"',
        'memory supersede mem_old mem_new --reason "newer memory"',
        'volition create "understand this" --reason "self-owned curiosity"',
        'focus resolve --resolution "done"',
        'volition mark-impossible intent_fake --reason "blocked"',
        'volition impossible intent_fake --reason "blocked"',
    ]

    for command in accepted:
        validation = validate_shell_command(command)
        assert validation["schema_status"] in {
            "implemented_command",
            "implemented_command_alias",
        }
        assert validation["call_is_available"] is True

    alias_validation = validate_shell_command(
        'volition impossible intent_fake --reason "blocked"'
    )
    suggested = alias_validation["suggested_command"]
    assert suggested == "volition mark-impossible"
    assert validate_shell_command(f'{suggested} intent_fake --reason "blocked"')[
        "call_is_available"
    ] is True


def test_mind_shell_accepts_registry_canonical_volition_alias(
    db_engine: Engine,
) -> None:
    session_id = _session(db_engine)
    context = _context(db_engine, session_id=session_id)
    created = dispatch_mind_shell(
        MindShellRequest(
            command='volition create "capire meglio i comandi shell" --reason "test"',
            intent="Create an intention to close through the canonical alias.",
        ),
        context=context,
    )
    assert created.ok is True
    intention_id = created.result["data"]["intention"]["id"]

    closed = dispatch_mind_shell(
        MindShellRequest(
            command=f'volition mark-impossible {intention_id} --reason "test chiuso"',
            intent="Close the intention using the registry canonical command.",
        ),
        context=context,
    )

    assert closed.ok is True
    assert closed.result["target"] == "volition.mark_impossible"
