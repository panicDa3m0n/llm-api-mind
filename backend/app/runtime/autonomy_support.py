"""Shared internal helpers for persisted autonomous activations.

The helpers in this module keep the autonomous adapter's lifecycle mechanics
separate from provider execution.  They deliberately preserve the existing
events, activation states, and context payloads.
"""

from __future__ import annotations

import json
import time
from datetime import timedelta
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.api.chat_provider_history import valid_provider_history
from app.config import Settings
from app.llm.provider import LLMMessage
from app.mind.context_time import render_user_time
from app.runtime.autonomy_schedule import coalesce_autonomous_activation
from app.runtime.events import record_event
from app.storage import repositories
from app.storage.models import AutonomousActivation, ChatSession, Message, utc_now


class AutonomousYieldToHuman(RuntimeError):
    """Stop an internal cycle when a human turn takes foreground priority."""


def cancel_pending_periodic_activations(
    db: Session,
    *,
    profile_id: str,
    session_id: str,
) -> None:
    """Retire legacy periodic wakes while the active workspace owns wakes."""

    pending = repositories.list_autonomous_activations(
        db,
        profile_id=profile_id,
        session_id=session_id,
        status="pending",
        limit=100,
    )
    for activation in pending:
        if activation.trigger_kind != "periodic":
            continue
        cancelled = repositories.complete_autonomous_activation(
            db,
            activation_id=activation.id,
            status="cancelled",
            turn_id=None,
            active_mode=None,
            outcome={
                "reason": "periodic_wake_retired_by_active_workspace",
            },
        )
        record_event(
            db,
            session_id=session_id,
            turn_id=None,
            event_type="autonomy.activation.cancelled",
            payload={
                "activation_id": cancelled.id,
                "reason": "periodic_wake_retired_by_active_workspace",
            },
            source="cognitive_workspace",
            actor="backend",
            visibility="private",
        )


def has_active_human_turn(
    engine: Engine,
    *,
    settings: Settings,
) -> bool:
    """Return whether a recent human turn has foreground priority."""

    active_since = utc_now() - timedelta(
        seconds=settings.autonomous_activation_human_turn_freshness_seconds
    )
    with Session(engine) as db:
        return repositories.has_active_human_turn(
            db,
            active_since=active_since,
        )


def defer_started_activation(
    engine: Engine,
    *,
    settings: Settings,
    activation_id: str,
    turn_id: str | None,
    started_perf: float,
    reason: str,
) -> dict[str, Any]:
    """Persist a yielded activation and coalesce a later retry unchanged."""

    with Session(engine) as db:
        activation = db.get(AutonomousActivation, activation_id)
        if activation is None:
            return {
                "activation_id": activation_id,
                "turn_id": turn_id,
                "status": "deferred",
                "reason": reason,
            }
        latency_ms = int((time.perf_counter() - started_perf) * 1000)
        if turn_id is not None:
            repositories.complete_turn(
                db,
                turn_id=turn_id,
                status="deferred",
                latency_ms=latency_ms,
            )
            record_event(
                db,
                session_id=activation.session_id,
                turn_id=turn_id,
                event_type="autonomy.activation.deferred",
                payload={
                    "activation_id": activation.id,
                    "reason": "human_turn_started",
                    "detail": reason,
                    "latency_ms": latency_ms,
                },
                source="autonomy",
                actor="backend",
                visibility="private",
                status="deferred",
            )
        deferred = repositories.complete_autonomous_activation(
            db,
            activation_id=activation.id,
            status="deferred",
            turn_id=turn_id,
            active_mode=None,
            outcome={
                "reason": "human_turn_started",
                "detail": reason,
                "latency_ms": latency_ms,
            },
        )
        coalesce_autonomous_activation(
            db,
            profile_id=deferred.profile_id,
            session_id=deferred.session_id,
            trigger_kind="deferred_human_active",
            candidate_id=deferred.candidate_id,
            episode_id=deferred.episode_id,
            wake_condition_id=deferred.wake_condition_id,
            workspace=deferred.workspace_json,
            min_gap_seconds=settings.autonomous_activation_min_gap_seconds,
            now=(
                utc_now()
                + timedelta(seconds=settings.autonomous_activation_defer_seconds)
            ),
        )
    return {
        "activation_id": activation_id,
        "turn_id": turn_id,
        "status": "deferred",
        "reason": "human_turn_started",
    }


def autonomous_provider_messages(
    provider_history_value: Any,
    history: list[Message],
    current_activation: Message,
) -> list[LLMMessage]:
    """Build canonical history for an autonomous turn from persisted state."""

    provider_history = valid_provider_history(provider_history_value)
    if provider_history:
        return [
            LLMMessage(role=item["role"], content=item["content"])
            for item in [
                *provider_history,
                {
                    "role": "user",
                    "content": [{"type": "text", "text": current_activation.content}],
                },
            ]
        ]
    messages: list[LLMMessage] = []
    for message in history:
        if message.id == current_activation.id:
            messages.append(LLMMessage(role="user", content=message.content))
        elif message.role == "activation":
            messages.append(LLMMessage(role="user", content=message.content))
        elif message.role == "assistant":
            messages.append(LLMMessage(role="assistant", content=message.content))
    return messages


def reconcile_workspace_activation(
    db: Session,
    *,
    activation: AutonomousActivation,
) -> None:
    """Resolve or park workspace candidates after an activation finishes."""

    candidate_ids = [
        item
        for item in activation.workspace_json.get("selected_candidate_ids", [])
        if isinstance(item, str)
    ]
    if activation.candidate_id is not None:
        candidate_ids.insert(0, activation.candidate_id)
    candidate_ids = list(dict.fromkeys(candidate_ids))
    if not candidate_ids:
        return
    volition_links = repositories.list_intention_links_by_targets(
        db,
        target_type="candidate",
        target_ids=candidate_ids,
    )
    volition_by_candidate = {
        item.target_id: item.intention_id for item in volition_links
    }
    for candidate_id in candidate_ids:
        candidate = repositories.get_candidate(db, candidate_id)
        if candidate is None or candidate.status in {
            "selected",
            "resolved",
            "rejected",
            "invalidated",
        }:
            continue
        intention_id = volition_by_candidate.get(candidate.id)
        if intention_id is not None:
            repositories.update_candidate(
                db,
                candidate_id=candidate.id,
                status="resolved",
                resolution=f"endorsed_as_volition:{intention_id}",
            )
            record_event(
                db,
                session_id=activation.session_id,
                turn_id=activation.turn_id,
                event_type="cognition.candidate.endorsed_as_volition",
                payload={
                    "candidate_id": candidate.id,
                    "intention_id": intention_id,
                    "activation_id": activation.id,
                },
                source="cognitive_workspace",
                actor="backend",
                visibility="private",
            )
            continue
        repositories.update_candidate(
            db,
            candidate_id=candidate.id,
            status="parked",
            clear_deferred_until=True,
        )
        record_event(
            db,
            session_id=activation.session_id,
            turn_id=activation.turn_id,
            event_type="cognition.candidate.parked",
            payload={
                "candidate_id": candidate.id,
                "activation_id": activation.id,
                "reason": "no_explicit_episode_or_volition_decision",
                "reentry": "new_source_backed_appraisal_only",
            },
            source="cognitive_workspace",
            actor="backend",
            visibility="private",
        )


def autonomous_activation_envelope(
    *,
    activation: AutonomousActivation,
    now: Any,
    timezone_id: str,
) -> str:
    """Render the persisted activation message delivered to Scarlet."""

    base = (
        "[SCARLET INTERNAL COGNITIVE ACTIVATION]\n"
        f"Activation id: {activation.id}\n"
        f"Trigger: {activation.trigger_kind}\n"
        f"Runtime time: {render_user_time(now, timezone_id=timezone_id)}\n"
        "Origin: autonomous_cognition. This is not a human message. Use the "
        "same runtime context and API Mind available in interactive turns, "
        "then leave one concise internal checkpoint instead of a user-facing "
        "answer."
    )
    if not activation.workspace_json:
        return base
    workspace = json.dumps(
        activation.workspace_json,
        ensure_ascii=False,
        sort_keys=True,
    )
    return (
        f"{base}\n\n"
        "[COGNITIVE WORKSPACE - PROVISIONAL]\n"
        f"{workspace}\n"
        "This packet proposes attention; it does not establish facts or command "
        "an outcome. Inspect its source references. Use episode commands to open, "
        "resume, checkpoint, suspend, resolve, or reject the proposed work."
    )


def autonomous_retrieval_dialogue(
    db: Session,
    *,
    autonomous_session: ChatSession,
    profile_id: str,
    privacy_scope: str,
) -> list[dict[str, Any]]:
    """Provide the shared retriever with recent source-labelled continuity."""

    candidates: list[Message] = []
    human_states = repositories.list_session_summary_states(
        db,
        exclude_session_id=autonomous_session.id,
        kind="human_dialogue",
        profile_id=None if privacy_scope == "local_single_user" else profile_id,
        limit=2,
    )
    for state in human_states:
        human_messages = repositories.list_messages(
            db,
            session_id=state.chat_session.id,
        )
        candidates.extend(
            message
            for message in human_messages[-4:]
            if message.role in {"user", "assistant"}
        )
    autonomous_messages = repositories.list_messages(
        db,
        session_id=autonomous_session.id,
    )
    candidates.extend(
        message
        for message in autonomous_messages[-6:]
        if message.role == "assistant"
    )
    candidates.sort(key=lambda item: (item.created_at, item.id))
    return [
        {
            "id": message.id,
            "session_id": message.session_id,
            "turn_id": message.turn_id,
            "role": message.role,
            "content": message.content[:1200],
            "source_origin": (
                "autonomous_cognition"
                if message.session_id == autonomous_session.id
                else "human_interaction"
            ),
        }
        for message in candidates[-8:]
    ]
