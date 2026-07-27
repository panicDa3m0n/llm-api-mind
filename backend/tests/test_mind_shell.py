import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.llm.provider import LLMTextResult
from app.mind.command_registry import COMMAND_FAMILIES, validate_shell_command
from app.mind.memory import MindAPIContext
from app.mind.schema import MIND_SHELL_COMMANDS
from app.mind.shell import MindShellRequest, dispatch_mind_shell
from app.storage import repositories
from app.storage.db import init_db
from app.storage.models import ChatSession


class FakeShellSessionSummaryProvider:
    calls = 0

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        self.__class__.calls += 1
        return LLMTextResult(
            model=self.settings.minimax_model,
            text=json.dumps(
                {
                    "summary": "Scarlet ha verificato la navigazione episodica.",
                    "topics": ["session shell"],
                    "decisions": ["Usare gli id per rileggere le fonti."],
                    "open_questions": [],
                    "notable_context": ["Il transcript resta la fonte esatta."],
                }
            ),
            usage={"input_tokens": 10, "output_tokens": 20},
            provider_message_id="session_shell_summary",
            stop_reason="end_turn",
        )


class FakeShellMetacognitionProvider:
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
            text=json.dumps(
                {
                    "review_summary": "Shell metacognition verified.",
                    "risks": [],
                    "claim_checks": [],
                    "missing_evidence": [],
                    "recommended_internal_actions": [],
                    "should_continue": False,
                    "next_focus_question": None,
                    "public_summary": "Verifica completata.",
                }
            ),
            usage={"input_tokens": 10, "output_tokens": 20},
            provider_message_id="metacognition_shell",
            stop_reason="end_turn",
        )


def _context(
    db_engine: Engine,
    *,
    session_id: str | None = None,
    provider_factory=None,
) -> MindAPIContext:
    return MindAPIContext(
        engine=db_engine,
        session_id=session_id,
        settings=Settings(
            app_name="Test Mind",
            environment="test",
            minimax_api_key="test-key",
        ),
        provider_factory=provider_factory,
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

    alias = dispatch_mind_shell(
        MindShellRequest(command="help mem"),
        context=_context(db_engine),
    )
    assert alias.ok is True
    assert alias.result["catalog"]["commands"][0]["namespace"] == "memory"

    unknown = dispatch_mind_shell(
        MindShellRequest(command="help nonsense"),
        context=_context(db_engine),
    )
    assert unknown.ok is False
    assert validate_shell_command("help nonsense")["call_is_available"] is False


def test_mind_shell_registry_and_help_examples_are_executable_contracts(
    db_engine: Engine,
) -> None:
    context = _context(db_engine)
    for canonical, family in COMMAND_FAMILIES.items():
        for surface in (canonical, *family.aliases):
            command = surface if canonical == "help" else f"help {surface}"
            validation = validate_shell_command(command)
            response = dispatch_mind_shell(
                MindShellRequest(command=command),
                context=context,
            )
            assert validation["call_is_available"] is True, command
            assert response.ok is True, command

    for family in MIND_SHELL_COMMANDS:
        for command in family["commands"]:
            validation = validate_shell_command(command)
            assert validation["call_is_available"] is True, command


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


def test_shell_exposes_autonomous_session_and_memory_provenance(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        autonomous = repositories.get_or_create_autonomous_session(
            db,
            profile_id="local-user",
        )
        turn = repositories.create_turn(
            db,
            session_id=autonomous.id,
            model="MiniMax-M3",
            trigger_kind="autonomous_activation",
            actor="scarlet",
        )
        source = repositories.add_message(
            db,
            session_id=autonomous.id,
            turn_id=turn.id,
            role="assistant",
            content="Ho collegato il rituale jazz alla preparazione della cena.",
        )
        memory = repositories.add_memory(
            db,
            memory_type="task_context",
            scope="general",
            content="Il rituale jazz è stato elaborato durante una cognizione autonoma.",
            reason_for_storage="Verificare la provenienza autonoma.",
            source_session_id=autonomous.id,
            source_turn_id=turn.id,
            source_message_id=source.id,
        )
        repositories.complete_turn(db, turn_id=turn.id)
        human = repositories.create_chat_session(db, title="Human shell")
        autonomous_id = autonomous.id
        human_id = human.id
        memory_id = memory.id

    context = _context(db_engine, session_id=human_id)
    opened = dispatch_mind_shell(
        MindShellRequest(command=f"session open {autonomous_id}"),
        context=context,
    )
    assert opened.ok is True
    assert opened.result["data"]["session"]["kind"] == "scarlet_autonomous"

    searched = dispatch_mind_shell(
        MindShellRequest(command='memory search "rituale jazz cognizione autonoma"'),
        context=context,
    )
    assert searched.ok is True
    found = next(
        item
        for item in searched.result["data"]["memories"]
        if item["id"] == memory_id
    )
    assert found["source"]["source_session_kind"] == "scarlet_autonomous"
    assert found["source"]["source_turn_trigger"] == "autonomous_activation"
    assert found["source"]["source_turn_actor"] == "scarlet"
    assert found["source"]["source_message_role"] == "assistant"
    assert found["source"]["source_provenance_status"] == "complete"
    assert found["source"]["source_origin"] == "autonomous_cognition"


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

    shown = dispatch_mind_shell(
        MindShellRequest(command=f"memory show {memory_id}"),
        context=context,
    )
    assert shown.ok is True
    assert shown.result["target"] == "memory.open"


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


def test_mind_shell_session_list_paginates_beyond_internal_history_size(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    now = repositories.utc_now()
    sessions = [
        ChatSession(
            title=f"Deep episodic history {index:03d}",
            created_at=now - timedelta(minutes=505 - index),
            updated_at=now - timedelta(minutes=505 - index),
        )
        for index in range(505)
    ]
    expected_tail_ids = [item.id for item in reversed(sessions[:5])]
    oldest_session_id = sessions[0].id
    calling_session_id = sessions[-1].id
    with Session(db_engine) as db:
        db.add_all(sessions)
        db.commit()

    response = dispatch_mind_shell(
        MindShellRequest(command="session list --limit 10 --offset 500"),
        context=_context(db_engine, session_id=calling_session_id),
    )

    assert response.ok is True
    assert response.result["data"]["count"] == 5
    assert response.result["data"]["has_more"] is False
    assert [item["id"] for item in response.result["data"]["sessions"]] == (
        expected_tail_ids
    )

    searched = dispatch_mind_shell(
        MindShellRequest(
            command='session list --query "Deep episodic history 000" --limit 5'
        ),
        context=_context(db_engine, session_id=calling_session_id),
    )

    assert searched.ok is True
    assert [item["id"] for item in searched.result["data"]["sessions"]] == [
        oldest_session_id
    ]


def test_mind_shell_session_open_fallback_uses_complete_transcript(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(
            db,
            title="Complete fallback evidence",
        )
        turn = repositories.create_turn(
            db,
            session_id=chat_session.id,
            model="MiniMax-M3",
        )
        first_message = repositories.add_message(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            role="user",
            content="La prima evidenza non deve sparire dal fallback.",
        )
        last_message = repositories.add_message(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            role="assistant",
            content="La finestra manuale puo restare compatta.",
        )
        session_id = chat_session.id
        first_message_content = first_message.content
        last_message_id = last_message.id

    response = dispatch_mind_shell(
        MindShellRequest(command=f"session open {session_id} --limit 1"),
        context=_context(db_engine, session_id=session_id),
    )

    assert response.ok is True
    data = response.result["data"]
    assert [message["id"] for message in data["messages"]] == [last_message_id]
    assert data["summary"]["status"] == "fallback"
    assert data["summary"]["message_count"] == 2
    assert data["summary"]["last_message_id"] == last_message_id
    assert first_message_content in data["summary"]["summary"]


def test_mind_shell_session_summarize_is_traceable_and_idempotent(
    db_engine: Engine,
) -> None:
    FakeShellSessionSummaryProvider.calls = 0
    init_db(db_engine)
    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(
            db,
            title="Session shell summary",
        )
        turn = repositories.create_turn(
            db,
            session_id=chat_session.id,
            model="MiniMax-M3",
        )
        repositories.add_message(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            role="user",
            content="Controlliamo tutti i comandi sessione.",
        )
        repositories.add_message(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            role="assistant",
            content="Uso gli id come ganci verso le fonti.",
        )
        session_id = chat_session.id

    context = _context(
        db_engine,
        session_id=session_id,
        provider_factory=FakeShellSessionSummaryProvider,
    )
    summarized = dispatch_mind_shell(
        MindShellRequest(command=f"session summarize {session_id} --force"),
        context=context,
    )

    assert summarized.ok is True
    assert summarized.result["target"] == "session.summarize"
    assert summarized.result["data"]["summary"]["status"] == "active"
    assert FakeShellSessionSummaryProvider.calls == 1

    repeated = dispatch_mind_shell(
        MindShellRequest(command=f"session summarize {session_id}"),
        context=context,
    )

    assert repeated.ok is True
    assert repeated.result["data"]["up_to_date"] is True
    assert FakeShellSessionSummaryProvider.calls == 1


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


def test_mind_shell_focus_lifecycle_matches_advertised_commands(
    db_engine: Engine,
) -> None:
    session_id = _session(db_engine)
    context = _context(db_engine, session_id=session_id)

    created = dispatch_mind_shell(
        MindShellRequest(
            command='focus set "Audit focus" --reason "direct shell verification"'
        ),
        context=context,
    )
    assert created.ok is True
    focus_id = created.result["data"]["active_focus"]["id"]

    held = dispatch_mind_shell(
        MindShellRequest(command=f'focus hold {focus_id} --reason "keep foreground"'),
        context=context,
    )
    assert held.ok is True
    assert held.result["data"]["active_focus"]["status"] == "held"

    searched = dispatch_mind_shell(
        MindShellRequest(command='focus search "Audit focus" --limit 1'),
        context=context,
    )
    assert searched.ok is True
    assert searched.result["data"]["count"] == 1
    assert searched.result["data"]["items"][0]["id"] == focus_id
    assert "has_more" in searched.result["data"]

    missing_query = dispatch_mind_shell(
        MindShellRequest(command="focus search"),
        context=context,
    )
    assert missing_query.ok is False
    assert missing_query.error is not None
    assert missing_query.error.code == "shell.focus_search_missing_query"

    resolved = dispatch_mind_shell(
        MindShellRequest(
            command=f'focus resolve {focus_id} --resolution "audit complete"'
        ),
        context=context,
    )
    assert resolved.ok is True
    assert resolved.result["data"]["closed_focus"]["status"] == "resolved"

    timeline = dispatch_mind_shell(
        MindShellRequest(command="focus timeline --limit 2"),
        context=context,
    )
    assert timeline.ok is True
    assert timeline.result["data"]["edge_count"] == 2
    assert timeline.result["data"]["has_more_edges"] is True


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


def test_mind_shell_volition_can_endorse_workspace_candidate(
    db_engine: Engine,
) -> None:
    session_id = _session(db_engine)
    context = _context(db_engine, session_id=session_id)
    with Session(db_engine) as db:
        candidate, created = repositories.create_candidate(
            db,
            profile_id="local-user",
            candidate_kind="endogenous_curiosity",
            context_family="memory_continuity",
            claim="A source-backed question may deserve durable attention.",
            why_now="A free cognitive window exposed the connection.",
            cognitive_question="Do I want to keep understanding this?",
            expected_transformation="A deliberate Scarlet-owned direction.",
            uncertainty="medium",
            exact_fingerprint="shell-volition-candidate-link",
            sources=[
                {
                    "source_kind": "session",
                    "source_id": session_id,
                    "observed_at": datetime.now(timezone.utc),
                }
            ],
            metadata={"origin": "endogenous_cognition"},
        )
        assert created is True

    response = dispatch_mind_shell(
        MindShellRequest(
            command=(
                'volition create "Comprendere questo filo nel tempo" '
                '--reason "Scelgo di mantenerlo come direzione interna" '
                f"--candidate-id {candidate.id}"
            ),
            intent="Endorse one provisional workspace seed as a volition.",
        ),
        context=context,
    )

    assert response.ok is True
    intention = response.result["data"]["intention"]
    assert len(intention["links"]) == 1
    assert intention["links"][0]["target_type"] == "candidate"
    assert intention["links"][0]["target_id"] == candidate.id
    assert intention["links"][0]["relation"] == "endorsed_from"


def test_mind_shell_volition_due_queue_and_focus_candidate_are_executable(
    db_engine: Engine,
) -> None:
    session_id = _session(db_engine)
    context = _context(db_engine, session_id=session_id)
    due_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()

    created = dispatch_mind_shell(
        MindShellRequest(
            command=(
                'volition create "Rivedere la coda volitiva" --reason "audit" '
                f'--next-review-at "{due_at}" --review-interval-seconds 3600'
            )
        ),
        context=context,
    )
    assert created.ok is True
    intention = created.result["data"]["intention"]
    assert intention["next_review_at"] is not None
    assert intention["review_interval_seconds"] == 3600

    due = dispatch_mind_shell(
        MindShellRequest(command="volition list due --limit 1"),
        context=context,
    )
    assert due.ok is True
    assert due.result["data"]["count"] == 1
    assert due.result["data"]["items"][0]["id"] == intention["id"]
    assert "has_more" in due.result["data"]

    promoted = dispatch_mind_shell(
        MindShellRequest(
            command=f'volition promote {intention["id"]} --reason "foreground audit"'
        ),
        context=context,
    )
    assert promoted.ok is True
    candidate = promoted.result["data"]["focus_candidate"]
    assert set(candidate).isdisjoint({"method", "path", "body"})
    assert candidate["command"].startswith("focus set")
    assert intention["id"] in candidate["command"]

    applied = dispatch_mind_shell(
        MindShellRequest(command=candidate["command"]),
        context=context,
    )
    assert applied.ok is True
    active_focus = applied.result["data"]["active_focus"]
    assert active_focus["metadata"]["source_intention_id"] == intention["id"]

    missing_query = dispatch_mind_shell(
        MindShellRequest(command="volition search"),
        context=context,
    )
    assert missing_query.ok is False
    assert missing_query.error is not None
    assert missing_query.error.code == "shell.volition_search_missing_query"


def test_mind_shell_affect_read_filters_and_pagination_are_explicit(
    db_engine: Engine,
) -> None:
    session_id = _session(db_engine)
    with Session(db_engine) as db:
        repositories.create_affect_state(
            db,
            owner_profile_id="local-user",
            session_id=session_id,
            turn_id=None,
            mode="shadow",
            emotion="curiosity",
            intensity=0.6,
            intensity_label="medium",
            valence=0.3,
            activation=0.5,
            prototype_version="test",
            variables={},
            causes=[],
            tendencies={},
            pack={},
        )
        repositories.create_affect_state(
            db,
            owner_profile_id="local-user",
            session_id=session_id,
            turn_id=None,
            mode="model",
            emotion="frustration",
            intensity=0.7,
            intensity_label="high",
            valence=-0.4,
            activation=0.7,
            prototype_version="test",
            variables={},
            causes=[],
            tendencies={},
            pack={},
        )
    context = _context(db_engine, session_id=session_id)

    filtered = dispatch_mind_shell(
        MindShellRequest(command="affect read --emotion curiosity"),
        context=context,
    )
    assert filtered.ok is True
    assert filtered.result["data"]["affect_state"]["emotion"] == "curiosity"

    listed = dispatch_mind_shell(
        MindShellRequest(command="affect list --limit 1"),
        context=context,
    )
    assert listed.ok is True
    assert listed.result["data"]["count"] == 1
    assert listed.result["data"]["has_more"] is True

    missing = dispatch_mind_shell(
        MindShellRequest(command="affect read --id affect_missing"),
        context=context,
    )
    assert missing.ok is False
    assert missing.error is not None
    assert missing.error.code == "affect.not_found"

    prototypes = dispatch_mind_shell(
        MindShellRequest(command="affect prototypes"),
        context=context,
    )
    assert prototypes.ok is True
    assert len(prototypes.result["data"]["items"]) >= 7


def test_mind_shell_targeted_focus_read_reports_missing_id(
    db_engine: Engine,
) -> None:
    session_id = _session(db_engine)
    response = dispatch_mind_shell(
        MindShellRequest(command="focus read --id focus_missing"),
        context=_context(db_engine, session_id=session_id),
    )

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == "focus.not_found"


def test_mind_shell_validation_errors_are_json_serializable(
    db_engine: Engine,
) -> None:
    session_id = _session(db_engine)
    response = dispatch_mind_shell(
        MindShellRequest(command="volition list --status all"),
        context=_context(db_engine, session_id=session_id),
    )

    assert response.ok is False
    payload = response.model_dump(mode="json")
    json.dumps(payload)
    validation = payload["result"]["data"]["validation_errors"][0]
    assert "ctx" not in validation
    assert validation["type"] == "value_error"


def test_mind_shell_mode_commands_preserve_system_and_resume_ownership(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(db, title="Mode shell")
        turn = repositories.create_turn(
            db,
            session_id=chat_session.id,
            model="MiniMax-M3",
        )
        session_id = chat_session.id
        turn_id = turn.id
    settings = Settings(environment="test", minimax_api_key="test-key")
    turn_context = MindAPIContext(
        engine=db_engine,
        session_id=session_id,
        turn_id=turn_id,
        settings=settings,
    )

    listed = dispatch_mind_shell(
        MindShellRequest(command="mode list"),
        context=turn_context,
    )
    assert listed.ok is True
    assert listed.result["data"]["registry"]["manually_resumable_tags"] == [
        "idle",
        "scouting",
    ]

    selected = dispatch_mind_shell(
        MindShellRequest(command='mode set Scouting --reason "resume audit"'),
        context=turn_context,
    )
    assert selected.ok is True
    assert selected.result["data"]["agent_mode"]["active_tag"] == "interactive"
    assert selected.result["data"]["agent_mode"]["resume_tag"] == "scouting"

    rejected = dispatch_mind_shell(
        MindShellRequest(
            command='mode set interactive --reason "invalid persistent chat"'
        ),
        context=turn_context,
    )
    assert rejected.ok is False
    assert rejected.error is not None
    assert rejected.error.code == "mode.set_not_resumable"


def test_mind_shell_metacognition_forwards_retrospection_controls(
    db_engine: Engine,
) -> None:
    FakeShellMetacognitionProvider.prompts = []
    session_id = _session(db_engine)
    context = _context(
        db_engine,
        session_id=session_id,
        provider_factory=FakeShellMetacognitionProvider,
    )

    response = dispatch_mind_shell(
        MindShellRequest(
            command=(
                'metacognition step --objective "Rivedere il processo precedente" '
                "--mode review_previous_turn --turn-scope previous --detail raw"
            )
        ),
        context=context,
    )

    assert response.ok is True
    prompt = json.loads(
        FakeShellMetacognitionProvider.prompts[-1].split("\n\n", 1)[1]
    )
    assert prompt["turn_scope"] == "previous"
    assert prompt["detail"] == "raw"
