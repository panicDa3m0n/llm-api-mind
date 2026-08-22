"""Public scheduler entrypoints for Scarlet's autonomous cognition.

The provider lifecycle lives in ``autonomy_activation`` and its internal
mechanics live in ``autonomy_support``.  This facade intentionally preserves
the stable entrypoints used by the application, API, and tests.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.runtime.autonomy_activation import (
    ProviderFactory,
    run_autonomous_activation,
)
from app.runtime.autonomy_support import (
    AutonomousYieldToHuman,
    cancel_pending_periodic_activations,
)
from app.runtime.cognitive_workspace import run_cognitive_workspace_tick
from app.runtime.preferences import load_runtime_preferences
from app.storage import repositories
from app.storage.models import utc_now


logger = logging.getLogger(__name__)


def run_due_autonomous_activations(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
    now: Any | None = None,
) -> list[dict[str, Any]]:
    """Run all currently due autonomous activations in scheduler order."""

    if not settings.autonomous_activation_enabled:
        return []
    current = now or utc_now()
    with Session(engine) as db:
        preferences = load_runtime_preferences(db, settings)
        autonomous_session = repositories.get_or_create_autonomous_session(
            db,
            profile_id=preferences.profile_id,
        )
        if settings.cognitive_workspace_mode == "active":
            cancel_pending_periodic_activations(
                db,
                profile_id=preferences.profile_id,
                session_id=autonomous_session.id,
            )
        else:
            repositories.ensure_next_periodic_activation(
                db,
                profile_id=preferences.profile_id,
                session_id=autonomous_session.id,
                interval_seconds=settings.autonomous_activation_interval_seconds,
                from_time=current,
            )
    run_cognitive_workspace_tick(
        engine,
        settings=settings,
        provider_factory=provider_factory,
        now=current,
    )
    with Session(engine) as db:
        due = repositories.list_due_autonomous_activations(
            db,
            now=current,
            limit=settings.autonomous_activation_batch_size,
        )
    return [
        run_autonomous_activation(
            engine,
            settings=settings,
            provider_factory=provider_factory,
            activation_id=item.id,
            now=current,
        )
        for item in due
    ]


def start_autonomous_activation_worker(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
) -> Callable[[], None]:
    """Start the persisted activation worker and return its stop callback."""

    if not settings.autonomous_activation_enabled:
        return lambda: None

    with Session(engine) as db:
        preferences = load_runtime_preferences(db, settings)
        autonomous_session = repositories.get_or_create_autonomous_session(
            db,
            profile_id=preferences.profile_id,
        )
        if settings.cognitive_workspace_mode == "active":
            cancel_pending_periodic_activations(
                db,
                profile_id=preferences.profile_id,
                session_id=autonomous_session.id,
            )
        else:
            repositories.ensure_next_periodic_activation(
                db,
                profile_id=preferences.profile_id,
                session_id=autonomous_session.id,
                interval_seconds=settings.autonomous_activation_interval_seconds,
            )

    stop_event = threading.Event()

    def loop() -> None:
        while not stop_event.wait(
            settings.autonomous_activation_worker_interval_seconds
        ):
            try:
                run_due_autonomous_activations(
                    engine,
                    settings=settings,
                    provider_factory=provider_factory,
                )
            except Exception:
                logger.exception("Autonomous activation worker batch failed.")

    thread = threading.Thread(
        target=loop,
        name="scarlet-autonomous-cognition",
        daemon=True,
    )
    thread.start()

    def stop() -> None:
        stop_event.set()
        thread.join(timeout=2)

    return stop


__all__ = [
    "AutonomousYieldToHuman",
    "run_autonomous_activation",
    "run_due_autonomous_activations",
    "start_autonomous_activation_worker",
]
