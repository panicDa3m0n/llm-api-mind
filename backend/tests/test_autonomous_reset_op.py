import json
import sys

from sqlmodel import Session

from app.ops.reset_autonomous_chronology import APPROVAL_TOKEN, main
from app.storage import repositories
from app.storage.db import create_db_engine, init_db
from app.storage.models import utc_now


def test_reset_command_reports_applied_state_after_transaction(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    database_path = tmp_path / "production.db"
    backup_path = tmp_path / "backup.db"
    backup_path.touch()
    database_url = f"sqlite:///{database_path}"
    engine = create_db_engine(database_url)
    init_db(engine)
    with Session(engine) as db:
        original = repositories.get_or_create_autonomous_session(
            db,
            profile_id="owner",
        )
        repositories.schedule_autonomous_activation(
            db,
            profile_id="owner",
            session_id=original.id,
            scheduled_at=utc_now(),
            schedule_key="reset-op-pending",
        )
        original_id = original.id

    monkeypatch.setenv("ENVIRONMENT", "mobile_test")
    monkeypatch.setenv("DATABASE_ROLE", "production")
    monkeypatch.setenv("CODEX_TEST", "false")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("USER_PROFILE_ID", "owner")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "reset-autonomous-chronology",
            "--expected-session-id",
            original_id,
            "--backup-reference",
            str(backup_path),
            "--apply",
            "--approval-token",
            APPROVAL_TOKEN,
        ],
    )

    assert main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["mode"] == "applied"
    assert result["archived_session_id"] == original_id
    assert result["new_session_id"] != original_id
    assert result["after"]["active_session"]["provider_history_items"] == 0
    assert result["after"]["activation_counts"] == {"pending": 1}
