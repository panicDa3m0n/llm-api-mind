from datetime import timedelta

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.llm.provider import (
    LLMMessage,
    LLMStreamEvent,
    LLMTextResult,
    LLMToolRunner,
    LLMToolUse,
)
from app.mind.contracts import MindAPIContext
from app.mind.relevance_rerank import MemoryRerankEntry, MemoryRerankPlan
from app.mind.shell import MindShellRequest, dispatch_mind_shell
from app.runtime.autonomy import (
    run_autonomous_activation,
    run_due_autonomous_activations,
)
from app.storage import repositories
from app.storage.db import init_db
from app.storage.models import utc_now


class FakeAutonomyProvider:
    seen_messages: list[list[LLMMessage]] = []
    seen_systems: list[str | None] = []

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_text(self, *, prompt: str, system=None, max_tokens=None):
        return LLMTextResult(model="MiniMax-M3", text="unused")

    def generate_chat(self, *, messages, system=None, max_tokens=None):
        return LLMTextResult(model="MiniMax-M3", text="unused")

    def generate_chat_with_tools(
        self,
        *,
        messages,
        system=None,
        max_tokens=None,
        tools,
        tool_runner,
        max_tool_calls=None,
    ):
        raise AssertionError("Autonomous runtime must use streaming.")

    def stream_chat_with_tools(
        self,
        *,
        messages,
        system=None,
        max_tokens=None,
        tools,
        tool_runner: LLMToolRunner,
        max_tool_calls=None,
    ):
        self.__class__.seen_messages.append(messages)
        self.__class__.seen_systems.append(system)
        yield LLMStreamEvent(
            type="thinking_captured",
            data={"text": "Valuto se la mia memoria richiede attenzione."},
        )
        yield LLMStreamEvent(
            type="assistant_note",
            data={
                "text": "Controllo prima quali funzioni cognitive sono disponibili."
            },
        )
        executed = tool_runner(
            LLMToolUse(
                id="toolu_autonomy_help",
                name="mind_shell",
                input={
                    "command": "help",
                    "intent": "Orientarmi nel ciclo autonomo.",
                },
            )
        )
        result = LLMTextResult(
            model=self.settings.minimax_model,
            text=(
                "Checkpoint interno: ho verificato il mio spazio cognitivo; "
                "non emerge un intervento necessario."
            ),
            usage={"input_tokens": 100, "output_tokens": 20},
            provider_message_id="provider_autonomy_1",
            raw_content=[
                {
                    "type": "text",
                    "text": (
                        "Checkpoint interno: ho verificato il mio spazio "
                        "cognitivo; non emerge un intervento necessario."
                    ),
                }
            ],
            raw_provider_messages=[
                {
                    "id": "provider_autonomy_note",
                    "stop_reason": "tool_use",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Controllo prima quali funzioni cognitive "
                                "sono disponibili."
                            ),
                        },
                        {
                            "type": "tool_use",
                            "id": "toolu_autonomy_help",
                            "name": "mind_shell",
                            "input": {
                                "command": "help",
                                "intent": "Orientarmi nel ciclo autonomo.",
                            },
                        },
                    ],
                },
                {
                    "id": "provider_autonomy_1",
                    "stop_reason": "end_turn",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Checkpoint interno: ho verificato il mio "
                                "spazio cognitivo; non emerge un intervento "
                                "necessario."
                            ),
                        }
                    ],
                },
            ],
            stop_reason="end_turn",
            tool_calls=[executed],
        )
        yield LLMStreamEvent(
            type="assistant_answer",
            data={"text": result.text},
        )
        yield LLMStreamEvent(
            type="final_result",
            data={"result": result.model_dump(mode="json")},
        )


class NonTerminalAutonomyProvider:
    """Provider fixture that proves autonomous turns use native finality."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def stream_chat_with_tools(self, **_kwargs):
        result = LLMTextResult(
            model=self.settings.minimax_model,
            text="Checkpoint non terminale.",
            stop_reason="max_tokens",
            provider_message_id="provider_autonomy_non_terminal",
            raw_content=[{"type": "text", "text": "Checkpoint non terminale."}],
        )
        yield LLMStreamEvent(
            type="final_result",
            data={"result": result.model_dump(mode="json")},
        )


class EmptyTerminalAutonomyProvider:
    """Provider fixture that proves private checkpoints cannot be empty."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def stream_chat_with_tools(self, **_kwargs):
        result = LLMTextResult(
            model=self.settings.minimax_model,
            text="",
            stop_reason="end_turn",
            provider_message_id="provider_autonomy_empty_terminal",
            raw_content=[{"type": "thinking", "thinking": "Nessun checkpoint."}],
        )
        yield LLMStreamEvent(
            type="final_result",
            data={"result": result.model_dump(mode="json")},
        )


def _settings() -> Settings:
    return Settings(
        agent_system_prompt="You are Scarlet.",
        autonomous_activation_enabled=True,
        autonomous_activation_interval_seconds=600,
        maintenance_enabled=False,
        history_compaction_mode="off",
        cognitive_workspace_mode="off",
    )


def test_scheduler_creates_one_exclusive_session_and_waits_for_interval(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    now = utc_now()

    results = run_due_autonomous_activations(
        db_engine,
        settings=_settings(),
        provider_factory=FakeAutonomyProvider,
        now=now,
    )

    assert results == []
    with Session(db_engine) as db:
        autonomous = repositories.get_autonomous_session(
            db,
            profile_id="local-user",
        )
        assert autonomous is not None
        assert autonomous.kind == "scarlet_autonomous"
        assert repositories.list_chat_sessions(db, limit=None) == []
        scheduled = repositories.list_autonomous_activations(
            db,
            profile_id="local-user",
            limit=10,
        )
        assert len(scheduled) == 1
        delta = scheduled[0].scheduled_at.replace(
            tzinfo=now.tzinfo
        ) - now
        assert delta == timedelta(seconds=600)


def test_archived_autonomous_chronology_is_preserved_but_not_listed_as_active(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    settings = _settings()
    now = utc_now()
    with Session(db_engine) as db:
        original = repositories.get_or_create_autonomous_session(
            db,
            profile_id=settings.user_profile_id,
        )
        completed = repositories.schedule_autonomous_activation(
            db,
            profile_id=settings.user_profile_id,
            session_id=original.id,
            scheduled_at=now - timedelta(minutes=10),
            schedule_key="archive-completed",
        )
        repositories.complete_autonomous_activation(
            db,
            activation_id=completed.id,
            status="completed",
            turn_id=None,
            active_mode="idle",
        )
        pending = repositories.schedule_autonomous_activation(
            db,
            profile_id=settings.user_profile_id,
            session_id=original.id,
            scheduled_at=now + timedelta(minutes=10),
            schedule_key="archive-pending",
        )

        archived = repositories.archive_autonomous_session(
            db,
            profile_id=settings.user_profile_id,
            expected_session_id=original.id,
            reason="test_reset",
            archived_at=now,
        )
        replacement = repositories.get_or_create_autonomous_session(
            db,
            profile_id=settings.user_profile_id,
        )
        next_activation = repositories.ensure_next_periodic_activation(
            db,
            profile_id=settings.user_profile_id,
            session_id=replacement.id,
            interval_seconds=600,
            from_time=now,
        )

        assert archived.kind == "scarlet_autonomous_archive"
        assert archived.autonomy_key.endswith(original.id)
        assert replacement.id != original.id
        assert replacement.provider_history_json == []
        assert db.get(type(pending), pending.id).status == "cancelled"
        active_rows = repositories.list_autonomous_activations(
            db,
            profile_id=settings.user_profile_id,
            session_id=replacement.id,
            limit=10,
        )
        assert [item.id for item in active_rows] == [next_activation.id]
        archived_rows = repositories.list_autonomous_activations(
            db,
            profile_id=settings.user_profile_id,
            session_id=archived.id,
            limit=10,
        )
        assert {item.id for item in archived_rows} == {completed.id, pending.id}


def test_autonomous_cycle_persists_private_chronology_and_tool_actions(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    settings = _settings()
    now = utc_now()
    with Session(db_engine) as db:
        autonomous = repositories.get_or_create_autonomous_session(
            db,
            profile_id=settings.user_profile_id,
        )
        activation = repositories.schedule_autonomous_activation(
            db,
            profile_id=settings.user_profile_id,
            session_id=autonomous.id,
            scheduled_at=now,
            trigger_kind="manual_lab",
            schedule_key="test-autonomy-cycle",
        )

    result = run_autonomous_activation(
        db_engine,
        settings=settings,
        provider_factory=FakeAutonomyProvider,
        activation_id=activation.id,
        now=now,
    )

    assert result["status"] == "completed"
    assert result["tool_call_count"] == 1
    with Session(db_engine) as db:
        stored = repositories.list_autonomous_activations(
            db,
            profile_id=settings.user_profile_id,
            limit=10,
        )
        completed = next(item for item in stored if item.id == activation.id)
        assert completed.status == "completed"
        assert completed.turn_id is not None
        messages = repositories.list_messages_for_turn(
            db,
            turn_id=completed.turn_id,
        )
        assert [item.role for item in messages] == ["activation", "assistant"]
        assert messages[-1].metadata_json["visibility"] == "internal_cognition"
        events = repositories.list_events_for_turn(
            db,
            turn_id=completed.turn_id,
        )
        event_types = {item.type for item in events}
        assert "llm.thinking.captured" in event_types
        assert "assistant.note.emitted" in event_types
        assert "mind.tool_call.started" in event_types
        assert "mind.tool_call.completed" in event_types
        assert "turn.started" in event_types
        assert "turn.completed" in event_types
        assert "autonomy.activation.completed" in event_types
        notes = [item for item in events if item.type == "assistant.note.emitted"]
        assert all(item.visibility == "private" for item in notes)
        autonomous = repositories.get_autonomous_session(
            db,
            profile_id=settings.user_profile_id,
        )
        assert autonomous is not None
        assert [item["role"] for item in autonomous.provider_history_json] == [
            "user",
            "assistant",
            "user",
            "assistant",
        ]
        traces = repositories.list_traces_for_turn(
            db,
            turn_id=completed.turn_id,
        )
        trace_kinds = {item.kind for item in traces}
        assert {
            "context.accounting.preflight",
            "context.accounting.observed",
            "llm.request",
            "llm.response",
        } <= trace_kinds
        request_trace = next(item for item in traces if item.kind == "llm.request")
        response_trace = next(item for item in traces if item.kind == "llm.response")
        assert request_trace.payload_json["finality_contract"] == {
            "provider_terminal_stop_reason": "end_turn",
            "response_required": True,
            "response_visibility": "private",
            "semantic_validation": False,
        }
        assert response_trace.payload_json["finality_contract"] == {
            "accepted": True,
            "source": "provider_stop_reason",
            "response_visibility": "private",
            "semantic_validation": False,
        }

    delivered_system = FakeAutonomyProvider.seen_systems[-1] or ""
    assert "<runtime_context>" in delivered_system
    assert "<autonomous_runtime_context>" not in delivered_system
    assert '"schema_version": "scarlet-model-context-v2"' in delivered_system
    assert '"origin": "autonomous_cognition"' in delivered_system
    assert '"session_kind": "scarlet_autonomous"' in delivered_system


def test_autonomous_cycle_rejects_non_terminal_provider_result(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    settings = _settings()
    now = utc_now()
    with Session(db_engine) as db:
        autonomous = repositories.get_or_create_autonomous_session(
            db,
            profile_id=settings.user_profile_id,
        )
        activation = repositories.schedule_autonomous_activation(
            db,
            profile_id=settings.user_profile_id,
            session_id=autonomous.id,
            scheduled_at=now,
            trigger_kind="manual_lab",
            schedule_key="test-autonomy-non-terminal",
        )

    result = run_autonomous_activation(
        db_engine,
        settings=settings,
        provider_factory=NonTerminalAutonomyProvider,
        activation_id=activation.id,
        now=now,
    )

    assert result["status"] == "failed"
    with Session(db_engine) as db:
        stored = db.get(type(activation), activation.id)
        assert stored is not None
        assert stored.status == "failed"
        assert stored.turn_id is not None
        turn = repositories.get_turn(db, stored.turn_id)
        assert turn is not None
        assert turn.status == "failed"
        events = repositories.list_events_for_turn(db, turn_id=stored.turn_id)
        assert "turn.failed" in {item.type for item in events}
        assert "autonomy.activation.failed" in {item.type for item in events}
        error_trace = next(
            item
            for item in repositories.list_traces_for_turn(db, turn_id=stored.turn_id)
            if item.kind == "llm.error"
        )
    assert error_trace.payload_json["details"]["provider_details"][
        "reason"
    ] == "non_terminal_provider_result"


def test_autonomous_cycle_rejects_empty_terminal_checkpoint(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    settings = _settings()
    now = utc_now()
    with Session(db_engine) as db:
        autonomous = repositories.get_or_create_autonomous_session(
            db,
            profile_id=settings.user_profile_id,
        )
        activation = repositories.schedule_autonomous_activation(
            db,
            profile_id=settings.user_profile_id,
            session_id=autonomous.id,
            scheduled_at=now,
            trigger_kind="manual_lab",
            schedule_key="test-autonomy-empty-terminal",
        )

    result = run_autonomous_activation(
        db_engine,
        settings=settings,
        provider_factory=EmptyTerminalAutonomyProvider,
        activation_id=activation.id,
        now=now,
    )

    assert result["status"] == "failed"
    with Session(db_engine) as db:
        stored = db.get(type(activation), activation.id)
        assert stored is not None
        assert stored.status == "failed"
        assert stored.turn_id is not None
        turn = repositories.get_turn(db, stored.turn_id)
        assert turn is not None
        assert turn.status == "failed"
        messages = repositories.list_messages(db, session_id=stored.session_id)
        error_trace = next(
            item
            for item in repositories.list_traces_for_turn(db, turn_id=stored.turn_id)
            if item.kind == "llm.error"
        )
    assert [message.role for message in messages] == ["activation"]
    assert error_trace.payload_json["details"]["provider_details"][
        "reason"
    ] == "empty_terminal_result"


def test_autonomous_cycle_uses_shared_memory_rerank_with_human_continuity(
    db_engine: Engine,
    monkeypatch,
) -> None:
    init_db(db_engine)
    settings = _settings().model_copy(
        update={"retrieval_hybrid_mode": "active"}
    )
    now = utc_now()
    with Session(db_engine) as db:
        human = repositories.create_chat_session(
            db,
            title="Musica serale",
            profile_id=settings.user_profile_id,
        )
        human_turn = repositories.create_turn(
            db,
            session_id=human.id,
            model="test",
        )
        source = repositories.add_message(
            db,
            session_id=human.id,
            turn_id=human_turn.id,
            role="user",
            content="La sera ascolto spesso jazz mentre preparo la cena.",
        )
        repositories.add_message(
            db,
            session_id=human.id,
            turn_id=human_turn.id,
            role="assistant",
            content="È un rituale serale che ti accompagna volentieri.",
        )
        repositories.complete_turn(db, turn_id=human_turn.id)
        memory = repositories.add_memory(
            db,
            memory_type="user_preference",
            scope="user",
            content="L'utente ascolta spesso jazz mentre prepara la cena.",
            reason_for_storage="Continuity fixture",
            source_session_id=human.id,
            source_turn_id=human_turn.id,
            source_message_id=source.id,
        )
        memory_id = memory.id
        autonomous = repositories.get_or_create_autonomous_session(
            db,
            profile_id=settings.user_profile_id,
        )
        activation = repositories.schedule_autonomous_activation(
            db,
            profile_id=settings.user_profile_id,
            session_id=autonomous.id,
            scheduled_at=now,
            trigger_kind="manual_lab",
            schedule_key="test-autonomy-shared-retrieval",
        )

    def accept_first_candidate(*, query, candidates, settings, selected_limit):
        assert "jazz" in query.casefold()
        assert candidates
        entries = [
            MemoryRerankEntry(
                memory=item.memory,
                memory_id=item.memory.id,
                score=0.9 if item.memory.id == memory_id else 0.1,
                rank=1 if item.memory.id == memory_id else None,
                accepted=item.memory.id == memory_id,
                evaluated=True,
                routes=item.routes,
                route_ranks=item.route_ranks,
            )
            for item in candidates
        ]
        return MemoryRerankPlan(
            status={
                "mode": "active",
                "active": True,
                "ok": True,
                "status": "completed",
            },
            entries=entries,
        )

    monkeypatch.setattr(
        "app.mind.memory_recall.run_memory_relevance_rerank",
        accept_first_candidate,
    )
    result = run_autonomous_activation(
        db_engine,
        settings=settings,
        provider_factory=FakeAutonomyProvider,
        activation_id=activation.id,
        now=now,
    )

    assert result["status"] == "completed"
    delivered_system = FakeAutonomyProvider.seen_systems[-1] or ""
    assert "L'utente ascolta spesso jazz mentre prepara la cena." in delivered_system
    assert '"source_origin": "human_interaction"' in delivered_system
    with Session(db_engine) as db:
        trace = next(
            item
            for item in repositories.list_traces_for_turn(
                db,
                turn_id=result["turn_id"],
            )
            if item.kind == "memory.context"
        )
    assert [item["id"] for item in trace.payload_json["selected"]] == [memory_id]


def test_started_autonomous_cycle_yields_when_human_turn_takes_priority(
    db_engine: Engine,
    monkeypatch,
) -> None:
    init_db(db_engine)
    settings = _settings()
    now = utc_now()
    with Session(db_engine) as db:
        autonomous = repositories.get_or_create_autonomous_session(
            db,
            profile_id=settings.user_profile_id,
        )
        activation = repositories.schedule_autonomous_activation(
            db,
            profile_id=settings.user_profile_id,
            session_id=autonomous.id,
            scheduled_at=now,
            trigger_kind="manual_lab",
            schedule_key="test-autonomy-yield",
        )

    checks = iter([False, False, True])
    monkeypatch.setattr(
        repositories,
        "has_active_human_turn",
        lambda db, *, active_since: next(checks, True),
    )

    result = run_autonomous_activation(
        db_engine,
        settings=settings,
        provider_factory=FakeAutonomyProvider,
        activation_id=activation.id,
        now=now,
    )

    assert result["status"] == "deferred"
    assert result["reason"] == "human_turn_started"
    with Session(db_engine) as db:
        stored = db.get(type(activation), activation.id)
        assert stored is not None
        assert stored.status == "deferred"
        assert stored.turn_id is not None
        events = repositories.list_events_for_turn(
            db,
            turn_id=stored.turn_id,
        )
        assert events[-1].type == "autonomy.activation.deferred"
        scheduled = repositories.list_autonomous_activations(
            db,
            profile_id=settings.user_profile_id,
            limit=10,
        )
        assert any(
            item.trigger_kind == "deferred_human_active"
            and item.status == "pending"
            for item in scheduled
        )


def test_stale_started_human_turn_does_not_block_autonomous_cognition(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    now = utc_now()
    with Session(db_engine) as db:
        human_session = repositories.create_chat_session(db, title="Stale turn")
        turn = repositories.create_turn(db, session_id=human_session.id)
        turn.started_at = now - timedelta(hours=7)
        db.add(turn)
        db.commit()

        assert (
            repositories.has_active_human_turn(
                db,
                active_since=now - timedelta(hours=6),
            )
            is False
        )

        turn.started_at = now
        db.add(turn)
        db.commit()
        assert (
            repositories.has_active_human_turn(
                db,
                active_since=now - timedelta(hours=6),
            )
            is True
        )


def test_perception_is_an_availability_index_with_session_cursor(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    settings = _settings()
    observed_at = utc_now()
    with Session(db_engine) as db:
        autonomous = repositories.get_or_create_autonomous_session(
            db,
            profile_id=settings.user_profile_id,
        )
        event, created = repositories.add_perception_event(
            db,
            profile_id=settings.user_profile_id,
            channel="notifications",
            event_type="notification.received",
            source="android.test",
            source_event_key="notification:test:1",
            observed_at=observed_at,
            payload={"app": "Calendar", "title": "Promemoria"},
            navigation={"device_observation_id": "dev_obs_test"},
        )
        assert created is True
        event_id = event.id
        session_id = autonomous.id

    context = MindAPIContext(
        engine=db_engine,
        session_id=session_id,
        settings=settings,
    )
    status = dispatch_mind_shell(
        MindShellRequest(command="perception status"),
        context=context,
    )
    assert status.ok is True
    assert status.result["data"]["scope"] == "external_observation_channels"
    assert "autonomous_cognition" in status.result["data"]["excludes"]
    assert status.result["data"]["channels"][0]["unseen_count"] == 1

    opened = dispatch_mind_shell(
        MindShellRequest(command="perception open notifications --limit 5"),
        context=context,
    )
    assert opened.ok is True
    assert opened.result["data"]["events"][0]["id"] == event_id

    after = dispatch_mind_shell(
        MindShellRequest(command="perception status"),
        context=context,
    )
    assert after.result["data"]["channels"][0]["unseen_count"] == 0


def test_perception_cursor_drains_bounded_batches_without_skipping_late_events(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    settings = _settings()
    now = utc_now()
    with Session(db_engine) as db:
        autonomous = repositories.get_or_create_autonomous_session(
            db,
            profile_id=settings.user_profile_id,
        )
        for index, observed_at in enumerate(
            (now, now - timedelta(hours=1), now + timedelta(minutes=1)),
            start=1,
        ):
            repositories.add_perception_event(
                db,
                profile_id=settings.user_profile_id,
                channel="notifications",
                event_type="notification.received",
                source="android.test",
                source_event_key=f"notification:ordered:{index}",
                observed_at=observed_at,
                payload={"index": index},
            )
        session_id = autonomous.id

    context = MindAPIContext(
        engine=db_engine,
        session_id=session_id,
        settings=settings,
    )
    delivered: list[int] = []
    for _ in range(3):
        opened = dispatch_mind_shell(
            MindShellRequest(
                command="perception open notifications --limit 1"
            ),
            context=context,
        )
        assert opened.ok is True
        delivered.append(opened.result["data"]["events"][0]["payload"]["index"])

    assert delivered == [1, 2, 3]
    after = dispatch_mind_shell(
        MindShellRequest(command="perception status"),
        context=context,
    )
    assert after.result["data"]["channels"][0]["unseen_count"] == 0
