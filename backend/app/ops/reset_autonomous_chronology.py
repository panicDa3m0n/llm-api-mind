"""Guarded archival reset for Scarlet's active autonomous chronology."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from app.config import Settings
from app.storage import repositories
from app.storage.database_boundary import database_preflight_report
from app.storage.db import create_db_engine, prepare_runtime_database
from app.storage.models import AutonomousActivation, utc_now


APPROVAL_TOKEN = "RESET_ACTIVE_AUTONOMOUS_CHRONOLOGY"


def _state(db: Session, *, profile_id: str) -> dict[str, Any]:
    active = repositories.get_autonomous_session(db, profile_id=profile_id)
    if active is None:
        return {
            "profile_id": profile_id,
            "active_session": None,
            "activation_counts": {},
        }
    rows = list(
        db.exec(
            select(AutonomousActivation).where(
                AutonomousActivation.session_id == active.id
            )
        ).all()
    )
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    return {
        "profile_id": profile_id,
        "active_session": {
            "id": active.id,
            "kind": active.kind,
            "provider_history_items": len(active.provider_history_json),
        },
        "activation_counts": counts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-id")
    parser.add_argument("--expected-session-id", required=True)
    parser.add_argument("--backup-reference", required=True)
    parser.add_argument("--approval-token")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    settings = Settings()
    preflight = database_preflight_report(settings)
    if preflight["role"] != "production":
        raise SystemExit(
            "Autonomous chronology reset requires DATABASE_ROLE=production."
        )
    backup_reference = Path(args.backup_reference)
    if not backup_reference.is_absolute():
        raise SystemExit("--backup-reference must be an absolute VPS backup path.")

    profile_id = args.profile_id or settings.user_profile_id
    engine = create_db_engine(prepare_runtime_database(settings))
    with Session(engine) as db:
        before = _state(db, profile_id=profile_id)
        active = before["active_session"]
        if active is None:
            raise SystemExit(f"No active autonomous session for {profile_id!r}.")
        if active["id"] != args.expected_session_id:
            raise SystemExit(
                "Active autonomous session changed: "
                f"expected {args.expected_session_id}, received {active['id']}."
            )

        if not args.apply:
            print(
                json.dumps(
                    {
                        "operation": "autonomy.chronology.reset",
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

        archived_at = utc_now()
        archived = repositories.archive_autonomous_session(
            db,
            profile_id=profile_id,
            expected_session_id=args.expected_session_id,
            reason="owner_requested_clean_autonomous_restart",
            archived_at=archived_at,
        )
        active = repositories.get_or_create_autonomous_session(
            db,
            profile_id=profile_id,
        )
        next_activation = repositories.ensure_next_periodic_activation(
            db,
            profile_id=profile_id,
            session_id=active.id,
            interval_seconds=settings.autonomous_activation_interval_seconds,
            from_time=archived_at,
        )
        after = _state(db, profile_id=profile_id)

    print(
        json.dumps(
            {
                "operation": "autonomy.chronology.reset",
                "mode": "applied",
                "backup_reference": str(backup_reference),
                "archived_session_id": archived.id,
                "new_session_id": active.id,
                "next_activation_id": next_activation.id,
                "next_activation_at": next_activation.scheduled_at.isoformat(),
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
