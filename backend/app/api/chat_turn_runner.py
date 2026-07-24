"""Connection-independent execution for resumable native streaming turns."""

from __future__ import annotations

import threading
from collections.abc import Callable

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.api.chat_native_turn import (
    NativeTurnPreparation,
    record_failed_native_turn,
    stream_native_turn,
)
from app.config import Settings
from app.llm.provider import LLMProvider
from app.storage import repositories


ProviderFactory = Callable[[Settings], LLMProvider]


def start_native_turn_runner(
    *,
    settings: Settings,
    engine: Engine,
    provider_factory: ProviderFactory,
    prepared: NativeTurnPreparation,
) -> threading.Thread | None:
    """Run a turn beyond the lifetime of the initiating HTTP connection."""

    if engine.url.get_backend_name() == "sqlite" and engine.url.database in {
        None,
        "",
        ":memory:",
    }:
        # SQLAlchemy's in-memory test engine uses one StaticPool connection.
        # Concurrent polling would contend with writes on that same connection.
        _consume_native_turn(
            settings=settings,
            engine=engine,
            provider_factory=provider_factory,
            prepared=prepared,
        )
        return None

    thread = threading.Thread(
        target=_consume_native_turn,
        kwargs={
            "settings": settings,
            "engine": engine,
            "provider_factory": provider_factory,
            "prepared": prepared,
        },
        name=f"scarlet-turn-{prepared.turn_id}",
        daemon=True,
    )
    thread.start()
    return thread


def _consume_native_turn(
    *,
    settings: Settings,
    engine: Engine,
    provider_factory: ProviderFactory,
    prepared: NativeTurnPreparation,
) -> None:
    try:
        for _line in stream_native_turn(
            settings=settings,
            engine=engine,
            provider_factory=provider_factory,
            prepared=prepared,
        ):
            pass
    except BaseException as exc:
        # Native errors normally terminalize inside stream_native_turn. This guard
        # covers process-local implementation failures so a detached turn is not
        # left permanently in "started".
        with Session(engine) as db:
            turn = repositories.get_turn(db, prepared.turn_id)
            still_active = turn is not None and turn.status == "started"
        if still_active:
            record_failed_native_turn(
                engine,
                prepared=prepared,
                code="llm.runner_error",
                message=str(exc) or type(exc).__name__,
                details={
                    "exception_type": type(exc).__name__,
                    "recoverable": True,
                },
            )
