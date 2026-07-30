"""Persistence for sourceable cognitive candidates, episodes, and wake rules."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.storage.models import (
    AutonomousWakeCondition,
    ChatSession,
    CognitiveArbitration,
    CognitiveCandidate,
    CognitiveCandidateSource,
    CognitiveEpisode,
    CognitiveEpisodeCandidate,
    CognitiveEpisodeExpectation,
    CognitiveEpisodeStep,
    CognitiveEvent,
    CognitiveSignalCursor,
    CognitiveSignalReceipt,
    PerceptionEvent,
    utc_now,
)


OPEN_CANDIDATE_STATUSES = {
    "proposed",
    "source_checked",
    "eligible",
    "selected",
    "suspended",
}
OPEN_EPISODE_STATUSES = {"active", "suspended"}
OPEN_WAKE_STATUSES = {"pending"}


def get_signal_cursor(
    db: Session,
    *,
    profile_id: str,
    source_kind: str,
) -> CognitiveSignalCursor | None:
    return db.exec(
        select(CognitiveSignalCursor).where(
            CognitiveSignalCursor.profile_id == profile_id,
            CognitiveSignalCursor.source_kind == source_kind,
        )
    ).first()


def advance_signal_cursor(
    db: Session,
    *,
    profile_id: str,
    source_kind: str,
    observed_at: datetime,
    source_id: str,
) -> CognitiveSignalCursor:
    cursor = get_signal_cursor(
        db,
        profile_id=profile_id,
        source_kind=source_kind,
    )
    if cursor is None:
        cursor = CognitiveSignalCursor(
            profile_id=profile_id,
            source_kind=source_kind,
        )
    if cursor.last_observed_at is None or (
        observed_at,
        source_id,
    ) >= (
        cursor.last_observed_at,
        cursor.last_source_id or "",
    ):
        cursor.last_observed_at = observed_at
        cursor.last_source_id = source_id
    cursor.updated_at = utc_now()
    db.add(cursor)
    db.commit()
    db.refresh(cursor)
    return cursor


def get_signal_receipt(
    db: Session,
    *,
    profile_id: str,
    source_kind: str,
    source_key: str,
    registry_version: str,
) -> CognitiveSignalReceipt | None:
    return db.exec(
        select(CognitiveSignalReceipt).where(
            CognitiveSignalReceipt.profile_id == profile_id,
            CognitiveSignalReceipt.source_kind == source_kind,
            CognitiveSignalReceipt.source_key == source_key,
            CognitiveSignalReceipt.registry_version == registry_version,
        )
    ).first()


def create_signal_receipt(
    db: Session,
    *,
    profile_id: str,
    source_kind: str,
    source_key: str,
    source_type: str,
    policy: str,
    disposition: str,
    registry_version: str,
    observed_at: datetime,
    details: dict[str, Any] | None = None,
    candidate_id: str | None = None,
    episode_id: str | None = None,
) -> CognitiveSignalReceipt:
    existing = get_signal_receipt(
        db,
        profile_id=profile_id,
        source_kind=source_kind,
        source_key=source_key,
        registry_version=registry_version,
    )
    if existing is not None:
        return existing
    receipt = CognitiveSignalReceipt(
        profile_id=profile_id,
        source_kind=source_kind,
        source_key=source_key,
        source_type=source_type,
        policy=policy,
        disposition=disposition,
        registry_version=registry_version,
        candidate_id=candidate_id,
        episode_id=episode_id,
        observed_at=observed_at,
        details_json=details or {},
    )
    db.add(receipt)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = get_signal_receipt(
            db,
            profile_id=profile_id,
            source_kind=source_kind,
            source_key=source_key,
            registry_version=registry_version,
        )
        if existing is None:
            raise
        return existing
    db.refresh(receipt)
    return receipt


def update_signal_receipt(
    db: Session,
    *,
    receipt_id: str,
    disposition: str,
    candidate_id: str | None = None,
    episode_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> CognitiveSignalReceipt:
    receipt = db.get(CognitiveSignalReceipt, receipt_id)
    if receipt is None:
        raise ValueError(f"Cognitive signal receipt not found: {receipt_id}")
    receipt.disposition = disposition
    receipt.candidate_id = candidate_id
    receipt.episode_id = episode_id
    if details is not None:
        receipt.details_json = details
    receipt.processed_at = utc_now()
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt


def list_signal_receipts(
    db: Session,
    *,
    profile_id: str,
    disposition: str | None = None,
    limit: int = 100,
) -> list[CognitiveSignalReceipt]:
    statement = select(CognitiveSignalReceipt).where(
        CognitiveSignalReceipt.profile_id == profile_id
    )
    if disposition is not None:
        statement = statement.where(
            CognitiveSignalReceipt.disposition == disposition
        )
    return list(
        db.exec(
            statement.order_by(
                CognitiveSignalReceipt.observed_at,
                CognitiveSignalReceipt.id,
            ).limit(limit)
        ).all()
    )


def list_unprocessed_events(
    db: Session,
    *,
    profile_id: str,
    registry_version: str,
    limit: int,
) -> list[tuple[CognitiveEvent, ChatSession]]:
    cursor = get_signal_cursor(
        db,
        profile_id=profile_id,
        source_kind="event",
    )
    receipt_exists = (
        select(CognitiveSignalReceipt.id)
        .where(
            CognitiveSignalReceipt.profile_id == profile_id,
            CognitiveSignalReceipt.source_kind == "event",
            CognitiveSignalReceipt.source_key == CognitiveEvent.id,
            CognitiveSignalReceipt.registry_version == registry_version,
        )
        .exists()
    )
    statement = (
        select(CognitiveEvent, ChatSession)
        .join(ChatSession, ChatSession.id == CognitiveEvent.session_id)
        .where(ChatSession.profile_id == profile_id)
        .where(CognitiveEvent.type != "cognition.signal.dispositioned")
        .where(~receipt_exists)
    )
    if cursor is not None and cursor.last_observed_at is not None:
        statement = statement.where(
            (CognitiveEvent.created_at > cursor.last_observed_at)
            | (
                (CognitiveEvent.created_at == cursor.last_observed_at)
                & (CognitiveEvent.id > (cursor.last_source_id or ""))
            )
        )
    statement = (
        statement.order_by(
            CognitiveEvent.created_at,
            CognitiveEvent.id,
        )
        .limit(limit)
    )
    return list(db.exec(statement).all())


def list_unprocessed_perception_events(
    db: Session,
    *,
    profile_id: str,
    registry_version: str,
    limit: int,
) -> list[PerceptionEvent]:
    cursor = get_signal_cursor(
        db,
        profile_id=profile_id,
        source_kind="perception",
    )
    receipt_exists = (
        select(CognitiveSignalReceipt.id)
        .where(
            CognitiveSignalReceipt.profile_id == profile_id,
            CognitiveSignalReceipt.source_kind == "perception",
            CognitiveSignalReceipt.source_key == PerceptionEvent.id,
            CognitiveSignalReceipt.registry_version == registry_version,
        )
        .exists()
    )
    statement = (
        select(PerceptionEvent)
        .where(PerceptionEvent.profile_id == profile_id)
        .where(~receipt_exists)
    )
    if cursor is not None and cursor.last_observed_at is not None:
        statement = statement.where(
            (PerceptionEvent.received_at > cursor.last_observed_at)
            | (
                (PerceptionEvent.received_at == cursor.last_observed_at)
                & (PerceptionEvent.id > (cursor.last_source_id or ""))
            )
        )
    statement = (
        statement.order_by(PerceptionEvent.received_at, PerceptionEvent.id)
        .limit(limit)
    )
    return list(db.exec(statement).all())


def latest_event_for_profile(
    db: Session,
    *,
    profile_id: str,
) -> CognitiveEvent | None:
    return db.exec(
        select(CognitiveEvent)
        .join(ChatSession, ChatSession.id == CognitiveEvent.session_id)
        .where(ChatSession.profile_id == profile_id)
        .order_by(CognitiveEvent.created_at.desc(), CognitiveEvent.id.desc())
        .limit(1)
    ).first()


def list_events_for_profile_since(
    db: Session,
    *,
    profile_id: str,
    observed_after: datetime,
    limit: int = 500,
) -> list[CognitiveEvent]:
    return list(
        db.exec(
            select(CognitiveEvent)
            .join(ChatSession, ChatSession.id == CognitiveEvent.session_id)
            .where(ChatSession.profile_id == profile_id)
            .where(CognitiveEvent.created_at >= observed_after)
            .order_by(CognitiveEvent.created_at, CognitiveEvent.id)
            .limit(limit)
        ).all()
    )


def latest_perception_event_for_profile(
    db: Session,
    *,
    profile_id: str,
) -> PerceptionEvent | None:
    return db.exec(
        select(PerceptionEvent)
        .where(PerceptionEvent.profile_id == profile_id)
        .order_by(PerceptionEvent.received_at.desc(), PerceptionEvent.id.desc())
        .limit(1)
    ).first()


def get_candidate(
    db: Session,
    candidate_id: str,
) -> CognitiveCandidate | None:
    return db.get(CognitiveCandidate, candidate_id)


def get_candidate_by_fingerprint(
    db: Session,
    *,
    profile_id: str,
    exact_fingerprint: str,
) -> CognitiveCandidate | None:
    return db.exec(
        select(CognitiveCandidate).where(
            CognitiveCandidate.profile_id == profile_id,
            CognitiveCandidate.exact_fingerprint == exact_fingerprint,
        )
    ).first()


def create_candidate(
    db: Session,
    *,
    profile_id: str,
    candidate_kind: str,
    context_family: str,
    claim: str,
    why_now: str,
    cognitive_question: str,
    expected_transformation: str,
    uncertainty: str,
    exact_fingerprint: str,
    sources: list[dict[str, Any]],
    appraisal_model: str | None = None,
    appraisal_trace_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    not_before: datetime | None = None,
    expires_at: datetime | None = None,
) -> tuple[CognitiveCandidate, bool]:
    existing = get_candidate_by_fingerprint(
        db,
        profile_id=profile_id,
        exact_fingerprint=exact_fingerprint,
    )
    if existing is not None:
        return existing, False
    candidate = CognitiveCandidate(
        profile_id=profile_id,
        candidate_kind=candidate_kind,
        context_family=context_family,
        claim=claim,
        why_now=why_now,
        cognitive_question=cognitive_question,
        expected_transformation=expected_transformation,
        uncertainty=uncertainty,
        exact_fingerprint=exact_fingerprint,
        appraisal_model=appraisal_model,
        appraisal_trace_id=appraisal_trace_id,
        metadata_json=metadata or {},
        not_before=not_before,
        expires_at=expires_at,
    )
    db.add(candidate)
    for source in sources:
        db.add(
            CognitiveCandidateSource(
                candidate_id=candidate.id,
                source_kind=str(source["source_kind"]),
                source_id=str(source["source_id"]),
                relation=str(source.get("relation") or "supports"),
                observed_at=source.get("observed_at"),
                metadata_json=dict(source.get("metadata") or {}),
            )
        )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = get_candidate_by_fingerprint(
            db,
            profile_id=profile_id,
            exact_fingerprint=exact_fingerprint,
        )
        if existing is None:
            raise
        return existing, False
    db.refresh(candidate)
    return candidate, True


def list_candidate_sources(
    db: Session,
    *,
    candidate_id: str,
) -> list[CognitiveCandidateSource]:
    return list(
        db.exec(
            select(CognitiveCandidateSource)
            .where(CognitiveCandidateSource.candidate_id == candidate_id)
            .order_by(
                CognitiveCandidateSource.created_at,
                CognitiveCandidateSource.id,
            )
        ).all()
    )


def list_eligible_candidates(
    db: Session,
    *,
    profile_id: str,
    now: datetime | None = None,
    limit: int = 20,
) -> list[CognitiveCandidate]:
    current = now or utc_now()
    statement = (
        select(CognitiveCandidate)
        .where(CognitiveCandidate.profile_id == profile_id)
        .where(CognitiveCandidate.status.in_(OPEN_CANDIDATE_STATUSES))
        .where(
            (CognitiveCandidate.not_before.is_(None))
            | (CognitiveCandidate.not_before <= current)
        )
        .where(
            (CognitiveCandidate.deferred_until.is_(None))
            | (CognitiveCandidate.deferred_until <= current)
        )
        .where(
            (CognitiveCandidate.expires_at.is_(None))
            | (CognitiveCandidate.expires_at > current)
        )
        .order_by(
            CognitiveCandidate.deferral_count.desc(),
            CognitiveCandidate.created_at,
            CognitiveCandidate.id,
        )
        .limit(limit)
    )
    return list(db.exec(statement).all())


def list_candidates(
    db: Session,
    *,
    profile_id: str,
    status: str | None = None,
    limit: int = 50,
) -> list[CognitiveCandidate]:
    statement = select(CognitiveCandidate).where(
        CognitiveCandidate.profile_id == profile_id
    )
    if status is not None:
        statement = statement.where(CognitiveCandidate.status == status)
    return list(
        db.exec(
            statement.order_by(
                CognitiveCandidate.updated_at.desc(),
                CognitiveCandidate.id.desc(),
            ).limit(limit)
        ).all()
    )


def update_candidate(
    db: Session,
    *,
    candidate_id: str,
    status: str | None = None,
    deferred_until: datetime | None = None,
    clear_deferred_until: bool = False,
    increment_deferral: bool = False,
    selected_episode_id: str | None = None,
    resolution: str | None = None,
) -> CognitiveCandidate:
    candidate = get_candidate(db, candidate_id)
    if candidate is None:
        raise ValueError(f"Cognitive candidate not found: {candidate_id}")
    if status is not None:
        candidate.status = status
    if deferred_until is not None:
        candidate.deferred_until = deferred_until
    elif clear_deferred_until:
        candidate.deferred_until = None
    if increment_deferral:
        candidate.deferral_count += 1
    if selected_episode_id is not None:
        candidate.selected_episode_id = selected_episode_id
    if resolution is not None:
        candidate.resolution = resolution
    if status in {"resolved", "rejected", "invalidated"}:
        candidate.resolved_at = utc_now()
    candidate.updated_at = utc_now()
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def reconsider_candidate(
    db: Session,
    *,
    candidate_id: str,
    sources: list[dict[str, Any]],
    appraisal_model: str | None,
    appraisal_trace_id: str | None,
    metadata: dict[str, Any] | None = None,
) -> CognitiveCandidate:
    """Re-open a parked candidate only with newly attached source evidence."""

    candidate = get_candidate(db, candidate_id)
    if candidate is None:
        raise ValueError(f"Cognitive candidate not found: {candidate_id}")
    if candidate.status != "parked":
        raise ValueError(f"Cognitive candidate is not parked: {candidate_id}")

    existing_sources = {
        (item.source_kind, item.source_id, item.relation)
        for item in list_candidate_sources(db, candidate_id=candidate.id)
    }
    added = 0
    for source in sources:
        source_kind = str(source["source_kind"])
        source_id = str(source["source_id"])
        relation = str(source.get("relation") or "supports")
        identity = (source_kind, source_id, relation)
        if identity in existing_sources:
            continue
        db.add(
            CognitiveCandidateSource(
                candidate_id=candidate.id,
                source_kind=source_kind,
                source_id=source_id,
                observed_at=source.get("observed_at"),
                metadata_json=dict(source.get("metadata") or {}),
                relation=relation,
            )
        )
        existing_sources.add(identity)
        added += 1
    if not added:
        raise ValueError(
            "Reconsidering a parked candidate requires newly attached source evidence."
        )
    candidate.status = "proposed"
    candidate.deferred_until = None
    candidate.appraisal_model = appraisal_model
    candidate.appraisal_trace_id = appraisal_trace_id
    candidate.metadata_json = {
        **candidate.metadata_json,
        "last_reconsideration": metadata or {},
    }
    candidate.updated_at = utc_now()
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def create_arbitration(
    db: Session,
    *,
    profile_id: str,
    mode: str,
    status: str,
    model: str,
    pool_fingerprint: str,
    candidate_ids: list[str],
    selected_ids: list[str],
    decision: dict[str, Any],
    trace_id: str | None,
) -> CognitiveArbitration:
    arbitration = CognitiveArbitration(
        profile_id=profile_id,
        mode=mode,
        status=status,
        model=model,
        pool_fingerprint=pool_fingerprint,
        candidate_ids_json=candidate_ids,
        selected_ids_json=selected_ids,
        decision_json=decision,
        trace_id=trace_id,
    )
    db.add(arbitration)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = get_arbitration_by_pool(
            db,
            profile_id=profile_id,
            mode=mode,
            pool_fingerprint=pool_fingerprint,
        )
        if existing is None:
            raise
        return existing
    db.refresh(arbitration)
    return arbitration


def get_arbitration_by_pool(
    db: Session,
    *,
    profile_id: str,
    mode: str,
    pool_fingerprint: str,
) -> CognitiveArbitration | None:
    return db.exec(
        select(CognitiveArbitration).where(
            CognitiveArbitration.profile_id == profile_id,
            CognitiveArbitration.mode == mode,
            CognitiveArbitration.pool_fingerprint == pool_fingerprint,
        )
    ).first()


def list_arbitrations(
    db: Session,
    *,
    profile_id: str,
    limit: int = 20,
) -> list[CognitiveArbitration]:
    return list(
        db.exec(
            select(CognitiveArbitration)
            .where(CognitiveArbitration.profile_id == profile_id)
            .order_by(
                CognitiveArbitration.created_at.desc(),
                CognitiveArbitration.id.desc(),
            )
            .limit(limit)
        ).all()
    )


def create_episode(
    db: Session,
    *,
    profile_id: str,
    question: str,
    expected_transformation: str,
    candidate_ids: list[str],
    source_session_id: str | None,
    source_turn_id: str | None,
    focus_id: str | None = None,
    started_by: str = "scarlet",
    metadata: dict[str, Any] | None = None,
) -> CognitiveEpisode:
    episode = CognitiveEpisode(
        profile_id=profile_id,
        question=question,
        expected_transformation=expected_transformation,
        focus_id=focus_id,
        started_by=started_by,
        source_session_id=source_session_id,
        source_turn_id=source_turn_id,
        metadata_json=metadata or {},
    )
    db.add(episode)
    for candidate_id in candidate_ids:
        candidate = get_candidate(db, candidate_id)
        if candidate is None:
            db.rollback()
            raise ValueError(f"Cognitive candidate not found: {candidate_id}")
        if candidate.profile_id != profile_id:
            db.rollback()
            raise ValueError(
                f"Cognitive candidate belongs to another profile: {candidate_id}"
            )
        db.add(
            CognitiveEpisodeCandidate(
                episode_id=episode.id,
                candidate_id=candidate_id,
            )
        )
        candidate.status = "selected"
        candidate.selected_episode_id = episode.id
        candidate.updated_at = utc_now()
        db.add(candidate)
    db.commit()
    db.refresh(episode)
    return episode


def get_episode(db: Session, episode_id: str) -> CognitiveEpisode | None:
    return db.get(CognitiveEpisode, episode_id)


def list_episodes(
    db: Session,
    *,
    profile_id: str,
    status: str | None = None,
    limit: int = 20,
) -> list[CognitiveEpisode]:
    statement = select(CognitiveEpisode).where(
        CognitiveEpisode.profile_id == profile_id
    )
    if status is not None:
        statement = statement.where(CognitiveEpisode.status == status)
    return list(
        db.exec(
            statement.order_by(
                CognitiveEpisode.updated_at.desc(),
                CognitiveEpisode.id.desc(),
            ).limit(limit)
        ).all()
    )


def list_episode_candidates(
    db: Session,
    *,
    episode_id: str,
) -> list[CognitiveEpisodeCandidate]:
    return list(
        db.exec(
            select(CognitiveEpisodeCandidate)
            .where(CognitiveEpisodeCandidate.episode_id == episode_id)
            .order_by(CognitiveEpisodeCandidate.created_at)
        ).all()
    )


def add_episode_step(
    db: Session,
    *,
    episode_id: str,
    activation_id: str | None,
    turn_id: str | None,
    progress_summary: str,
    next_step: str | None,
    state_deltas: list[dict[str, Any]],
    source_refs: list[str],
    no_progress: bool,
) -> CognitiveEpisodeStep:
    episode = get_episode(db, episode_id)
    if episode is None:
        raise ValueError(f"Cognitive episode not found: {episode_id}")
    step = CognitiveEpisodeStep(
        episode_id=episode_id,
        activation_id=activation_id,
        turn_id=turn_id,
        progress_summary=progress_summary,
        next_step=next_step,
        state_deltas_json=state_deltas,
        source_refs_json=source_refs,
        no_progress=no_progress,
    )
    episode.last_progress_at = None if no_progress else utc_now()
    episode.updated_at = utc_now()
    db.add(step)
    db.add(episode)
    db.commit()
    db.refresh(step)
    return step


def list_episode_steps(
    db: Session,
    *,
    episode_id: str,
    limit: int = 20,
) -> list[CognitiveEpisodeStep]:
    return list(
        db.exec(
            select(CognitiveEpisodeStep)
            .where(CognitiveEpisodeStep.episode_id == episode_id)
            .order_by(
                CognitiveEpisodeStep.created_at.desc(),
                CognitiveEpisodeStep.id.desc(),
            )
            .limit(limit)
        ).all()
    )


def update_episode(
    db: Session,
    *,
    episode_id: str,
    status: str | None = None,
    suspended_until: datetime | None = None,
    resume_condition: str | None = None,
    resolution: str | None = None,
    stop_reason: str | None = None,
) -> CognitiveEpisode:
    episode = get_episode(db, episode_id)
    if episode is None:
        raise ValueError(f"Cognitive episode not found: {episode_id}")
    if status is not None:
        episode.status = status
    episode.suspended_until = suspended_until
    if resume_condition is not None:
        episode.resume_condition = resume_condition
    if resolution is not None:
        episode.resolution = resolution
    if stop_reason is not None:
        episode.stop_reason = stop_reason
    if status in {"resolved", "abandoned", "invalidated"}:
        episode.closed_at = utc_now()
    episode.updated_at = utc_now()
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return episode


def create_expectation(
    db: Session,
    *,
    episode_id: str,
    claim: str,
    observable_outcome: str,
    due_at: datetime | None,
) -> CognitiveEpisodeExpectation:
    expectation = CognitiveEpisodeExpectation(
        episode_id=episode_id,
        claim=claim,
        observable_outcome=observable_outcome,
        due_at=due_at,
    )
    db.add(expectation)
    db.commit()
    db.refresh(expectation)
    return expectation


def list_expectations(
    db: Session,
    *,
    episode_id: str,
) -> list[CognitiveEpisodeExpectation]:
    return list(
        db.exec(
            select(CognitiveEpisodeExpectation)
            .where(CognitiveEpisodeExpectation.episode_id == episode_id)
            .order_by(CognitiveEpisodeExpectation.created_at)
        ).all()
    )


def resolve_expectation(
    db: Session,
    *,
    expectation_id: str,
    status: str,
    evaluation: str,
    outcome_refs: list[str],
) -> CognitiveEpisodeExpectation:
    expectation = db.get(CognitiveEpisodeExpectation, expectation_id)
    if expectation is None:
        raise ValueError(f"Episode expectation not found: {expectation_id}")
    expectation.status = status
    expectation.evaluation = evaluation
    expectation.outcome_refs_json = outcome_refs
    expectation.resolved_at = utc_now()
    expectation.updated_at = utc_now()
    db.add(expectation)
    db.commit()
    db.refresh(expectation)
    return expectation


def get_wake_condition(
    db: Session,
    condition_id: str,
) -> AutonomousWakeCondition | None:
    return db.get(AutonomousWakeCondition, condition_id)


def get_wake_condition_by_key(
    db: Session,
    condition_key: str,
) -> AutonomousWakeCondition | None:
    return db.exec(
        select(AutonomousWakeCondition).where(
            AutonomousWakeCondition.condition_key == condition_key
        )
    ).first()


def create_wake_condition(
    db: Session,
    *,
    profile_id: str,
    kind: str,
    condition_key: str,
    predicate: dict[str, Any],
    episode_id: str | None = None,
    candidate_id: str | None = None,
    not_before: datetime | None = None,
    deadline: datetime | None = None,
) -> tuple[AutonomousWakeCondition, bool]:
    existing = get_wake_condition_by_key(db, condition_key)
    if existing is not None:
        return existing, False
    condition = AutonomousWakeCondition(
        profile_id=profile_id,
        episode_id=episode_id,
        candidate_id=candidate_id,
        kind=kind,
        condition_key=condition_key,
        predicate_json=predicate,
        not_before=not_before,
        deadline=deadline,
    )
    db.add(condition)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = get_wake_condition_by_key(db, condition_key)
        if existing is None:
            raise
        return existing, False
    db.refresh(condition)
    return condition, True


def list_pending_wake_conditions(
    db: Session,
    *,
    profile_id: str,
    now: datetime | None = None,
    limit: int = 100,
) -> list[AutonomousWakeCondition]:
    current = now or utc_now()
    statement = (
        select(AutonomousWakeCondition)
        .where(AutonomousWakeCondition.profile_id == profile_id)
        .where(AutonomousWakeCondition.status.in_(OPEN_WAKE_STATUSES))
        .where(
            (AutonomousWakeCondition.not_before.is_(None))
            | (AutonomousWakeCondition.not_before <= current)
        )
        .order_by(
            AutonomousWakeCondition.deadline,
            AutonomousWakeCondition.created_at,
        )
        .limit(limit)
    )
    return list(db.exec(statement).all())


def list_wake_conditions(
    db: Session,
    *,
    profile_id: str,
    status: str | None = None,
    limit: int = 100,
) -> list[AutonomousWakeCondition]:
    statement = select(AutonomousWakeCondition).where(
        AutonomousWakeCondition.profile_id == profile_id
    )
    if status is not None:
        statement = statement.where(AutonomousWakeCondition.status == status)
    return list(
        db.exec(
            statement.order_by(
                AutonomousWakeCondition.updated_at.desc(),
                AutonomousWakeCondition.id.desc(),
            ).limit(limit)
        ).all()
    )


def update_wake_condition(
    db: Session,
    *,
    condition_id: str,
    status: str,
    matched_event_id: str | None = None,
    matched_at: datetime | None = None,
) -> AutonomousWakeCondition:
    condition = get_wake_condition(db, condition_id)
    if condition is None:
        raise ValueError(f"Wake condition not found: {condition_id}")
    condition.status = status
    condition.matched_event_id = matched_event_id
    condition.last_evaluated_at = utc_now()
    condition.matched_at = matched_at
    condition.updated_at = utc_now()
    db.add(condition)
    db.commit()
    db.refresh(condition)
    return condition
