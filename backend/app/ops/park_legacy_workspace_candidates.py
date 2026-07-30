"""Guarded production reconciliation for the retired candidate retry loop."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from app.config import Settings
from app.runtime.events import record_event
from app.storage import repositories
from app.storage.database_boundary import database_preflight_report
from app.storage.db import create_db_engine, prepare_runtime_database
from app.storage.models import ChatSession, CognitiveCandidate, CognitiveEvent


APPROVAL_TOKEN = "PARK_LEGACY_WORKSPACE_CANDIDATES"
LEGACY_EVENT_TYPE = "cognition.candidate.suspended"
LEGACY_REASON = "no_explicit_episode_or_volition_decision"


def legacy_candidate_ids(db: Session, *, profile_id: str) -> list[str]:
    """Select only the exact pre-V1.65 fallback, never generic suspension."""

    rows = db.exec(
        select(CognitiveEvent)
        .join(ChatSession, ChatSession.id == CognitiveEvent.session_id)
        .where(ChatSession.profile_id == profile_id)
        .where(CognitiveEvent.type == LEGACY_EVENT_TYPE)
        .order_by(CognitiveEvent.created_at, CognitiveEvent.id)
    ).all()
    candidate_ids: list[str] = []
    for event in rows:
        payload = event.payload_json
        if payload.get("reason") != LEGACY_REASON:
            continue
        candidate_id = payload.get("candidate_id")
        if not isinstance(candidate_id, str) or candidate_id in candidate_ids:
            continue
        candidate = repositories.get_candidate(db, candidate_id)
        if candidate is not None and candidate.status == "suspended":
            candidate_ids.append(candidate_id)
    return candidate_ids


def reconcile_legacy_candidates(
    db: Session,
    *,
    profile_id: str,
    candidate_ids: list[str],
) -> list[str]:
    """Park exact legacy rows and leave all other candidate lifecycle intact."""

    autonomous_session = repositories.get_autonomous_session(db, profile_id=profile_id)
    if autonomous_session is None:
        raise ValueError(f"No active autonomous session for profile: {profile_id}")
    reconciled: list[str] = []
    for candidate_id in candidate_ids:
        candidate = repositories.get_candidate(db, candidate_id)
        if candidate is None or candidate.status != "suspended":
            continue
        repositories.update_candidate(
            db,
            candidate_id=candidate.id,
            status="parked",
            clear_deferred_until=True,
        )
        record_event(
            db,
            session_id=autonomous_session.id,
            event_type="cognition.candidate.parked_migration",
            payload={
                "candidate_id": candidate.id,
                "reason": "retire_legacy_no_explicit_decision_retry_loop",
                "previous_status": "suspended",
                "reentry": "new_source_backed_appraisal_only",
            },
            source="operator_migration",
            actor="backend",
            visibility="private",
        )
        reconciled.append(candidate.id)
    return reconciled


def _state(db: Session, *, profile_id: str) -> dict[str, Any]:
    candidate_ids = legacy_candidate_ids(db, profile_id=profile_id)
    parked_count = len(
        db.exec(
            select(CognitiveCandidate.id)
            .where(CognitiveCandidate.profile_id == profile_id)
            .where(CognitiveCandidate.status == "parked")
        ).all()
    )
    return {
        "profile_id": profile_id,
        "legacy_retry_candidate_ids": candidate_ids,
        "legacy_retry_candidate_count": len(candidate_ids),
        "parked_candidate_count": parked_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-id")
    parser.add_argument("--backup-reference", required=True)
    parser.add_argument("--approval-token")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    settings = Settings()
    preflight = database_preflight_report(settings)
    if preflight["role"] != "production":
        raise SystemExit(
            "Legacy candidate reconciliation requires DATABASE_ROLE=production."
        )
    backup_reference = Path(args.backup_reference)
    if not backup_reference.is_absolute():
        raise SystemExit("--backup-reference must be an absolute VPS backup path.")

    profile_id = args.profile_id or settings.user_profile_id
    engine = create_db_engine(prepare_runtime_database(settings))
    with Session(engine) as db:
        before = _state(db, profile_id=profile_id)
        if not args.apply:
            print(
                json.dumps(
                    {
                        "operation": "cognition.candidates.park_legacy_retry",
                        "mode": "dry_run",
                        "backup_reference": str(backup_reference),
                        "before": before,
                    },
                    ensure_ascii=True,
                    indent=2,
                )
            )
            return 0
        if args.approval_token != APPROVAL_TOKEN:
            raise SystemExit(
                f"--apply requires --approval-token {APPROVAL_TOKEN!r}."
            )
        reconciled_ids = reconcile_legacy_candidates(
            db,
            profile_id=profile_id,
            candidate_ids=before["legacy_retry_candidate_ids"],
        )
        after = _state(db, profile_id=profile_id)

    print(
        json.dumps(
            {
                "operation": "cognition.candidates.park_legacy_retry",
                "mode": "applied",
                "backup_reference": str(backup_reference),
                "reconciled_candidate_ids": reconciled_ids,
                "before": before,
                "after": after,
            },
            ensure_ascii=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
