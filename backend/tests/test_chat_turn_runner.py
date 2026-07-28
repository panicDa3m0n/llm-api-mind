import json
import threading
from pathlib import Path

from sqlmodel import Session

from app.api.chat_native_turn import prepare_native_turn
from app.api.chat_live_stream import LiveTurnFeed, stream_live_turn_items
from app.api.chat_stream_v2 import stream_persisted_turn_events
from app.api.chat_turn_runner import start_native_turn_runner
from app.config import Settings
from app.llm.provider import LLMStreamEvent, LLMTextResult
from app.storage import repositories
from app.storage.db import create_db_engine, init_db


class BlockingProvider:
    started = threading.Event()
    release = threading.Event()

    def __init__(self, _settings: Settings) -> None:
        pass

    def stream_chat_with_tools(self, **_kwargs):
        type(self).started.set()
        assert type(self).release.wait(timeout=5)
        result = LLMTextResult(
            model="blocking-provider",
            text="Risposta completata dopo la riconnessione.",
            stop_reason="end_turn",
            provider_message_id="provider_resume",
            raw_content=[
                {
                    "type": "text",
                    "text": "Risposta completata dopo la riconnessione.",
                }
            ],
            raw_provider_messages=[
                {
                    "id": "provider_resume",
                    "model": "blocking-provider",
                    "stop_reason": "end_turn",
                    "content": [
                        {
                            "type": "text",
                            "text": "Risposta completata dopo la riconnessione.",
                        }
                    ],
                }
            ],
        )
        yield LLMStreamEvent(
            type="assistant_answer",
            data={
                "model_step": 1,
                "provider_message_id": result.provider_message_id,
                "stop_reason": "end_turn",
                "text": result.text,
            },
        )
        yield LLMStreamEvent(
            type="final_result",
            data={"result": result.model_dump(mode="json")},
        )


class IncrementalProvider:
    frame_emitted = threading.Event()
    release = threading.Event()

    def __init__(self, _settings: Settings) -> None:
        pass

    def stream_chat_with_tools(self, **_kwargs):
        yield LLMStreamEvent(
            type="thinking_start",
            data={"model_step": 1, "index": 0},
        )
        yield LLMStreamEvent(
            type="thinking_delta",
            data={"model_step": 1, "index": 0, "text": "Sto verificando."},
        )
        type(self).frame_emitted.set()
        assert type(self).release.wait(timeout=5)
        result = LLMTextResult(
            model="incremental-provider",
            text="Verifica completata.",
            stop_reason="end_turn",
            provider_message_id="provider_incremental",
            raw_content=[{"type": "text", "text": "Verifica completata."}],
            raw_provider_messages=[
                {
                    "id": "provider_incremental",
                    "model": "incremental-provider",
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": "Verifica completata."}],
                }
            ],
        )
        yield LLMStreamEvent(
            type="assistant_answer",
            data={
                "model_step": 1,
                "index": 0,
                "provider_message_id": result.provider_message_id,
                "stop_reason": "end_turn",
                "text": result.text,
            },
        )
        yield LLMStreamEvent(
            type="final_result",
            data={"result": result.model_dump(mode="json")},
        )


def test_turn_runner_survives_stream_consumer_disconnect(tmp_path: Path) -> None:
    BlockingProvider.started.clear()
    BlockingProvider.release.clear()
    database = tmp_path / "runner.db"
    engine = create_db_engine(f"sqlite:///{database}")
    init_db(engine)
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{database}",
        minimax_api_key="test-key",
        agent_system_prompt="You are Scarlet.",
        maintenance_enabled=False,
    )
    with Session(engine) as db:
        chat_session = repositories.create_chat_session(db, title="Resume test")

    prepared = prepare_native_turn(
        settings=settings,
        engine=engine,
        session_id=chat_session.id,
        message="Resta con me mentre torno online.",
        system_override=None,
        requested_max_tokens=None,
        stream=True,
    )
    runner = start_native_turn_runner(
        settings=settings,
        engine=engine,
        provider_factory=BlockingProvider,
        prepared=prepared,
    )
    assert runner is not None
    assert BlockingProvider.started.wait(timeout=5)

    first_connection = stream_persisted_turn_events(
        engine=engine,
        session_id=chat_session.id,
        turn_id=prepared.turn_id,
        poll_interval_seconds=0.01,
    )
    first_event = json.loads(next(first_connection))
    first_connection.close()

    BlockingProvider.release.set()
    runner.join(timeout=5)
    assert not runner.is_alive()

    resumed = [
        json.loads(line)
        for line in stream_persisted_turn_events(
            engine=engine,
            session_id=chat_session.id,
            turn_id=prepared.turn_id,
            after_seq=first_event["seq"],
            poll_interval_seconds=0.01,
        )
    ]
    assert resumed[-1]["event_type"] == "turn.completed"
    assert any(
        event["event_type"] == "message.assistant.persisted" for event in resumed
    )


def test_live_feed_delivers_a_frame_before_the_turn_finishes(tmp_path: Path) -> None:
    IncrementalProvider.frame_emitted.clear()
    IncrementalProvider.release.clear()
    database = tmp_path / "incremental.db"
    engine = create_db_engine(f"sqlite:///{database}")
    init_db(engine)
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{database}",
        minimax_api_key="test-key",
        agent_system_prompt="You are Scarlet.",
        maintenance_enabled=False,
    )
    with Session(engine) as db:
        chat_session = repositories.create_chat_session(db, title="Live test")
    prepared = prepare_native_turn(
        settings=settings,
        engine=engine,
        session_id=chat_session.id,
        message="Fammi vedere cosa succede.",
        system_override=None,
        requested_max_tokens=None,
        stream=True,
    )
    feed = LiveTurnFeed()
    runner = start_native_turn_runner(
        settings=settings,
        engine=engine,
        provider_factory=IncrementalProvider,
        prepared=prepared,
        line_sink=feed.publish,
        completion_sink=feed.finish,
    )
    assert runner is not None
    stream = stream_live_turn_items(
        feed=feed,
        engine=engine,
        session_id=chat_session.id,
        turn_id=prepared.turn_id,
        poll_interval_seconds=0.01,
    )

    before_release = []
    for line in stream:
        item = json.loads(line)
        before_release.append(item)
        if item["kind"] == "frame":
            break

    assert IncrementalProvider.frame_emitted.is_set()
    assert runner.is_alive()
    assert before_release[-1]["frame"]["frame_type"] == "thinking_delta"
    assert before_release[-1]["frame"]["payload"]["text"] == "Sto verificando."

    IncrementalProvider.release.set()
    remaining = [json.loads(line) for line in stream]
    runner.join(timeout=5)
    assert not runner.is_alive()
    terminal = next(
        item["event"]
        for item in remaining
        if item["kind"] == "event"
        and item["event"]["event_type"] == "turn.completed"
    )
    assert terminal["turn_id"] == prepared.turn_id
