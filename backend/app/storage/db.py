from collections.abc import Generator
import shutil
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.storage.database_boundary import (
    safe_database_url,
    sqlite_file_path,
    validate_database_configuration,
)


def database_runtime_info(settings: Any) -> dict[str, Any]:
    """Expose safe database-selection metadata for health/debug surfaces."""

    selection = validate_database_configuration(settings)
    return {
        "profile": selection.role,
        "role": selection.role,
        "codex_test": selection.codex_test,
        "database_url": safe_database_url(selection.database_url),
        "seed_database_url": safe_database_url(selection.seed_database_url),
        "isolation": "seed_copy" if selection.codex_test else "direct",
    }


def prepare_runtime_database(settings: Any) -> str:
    """Prepare the selected database and return the URL to open.

    In codex-test mode, the test database is initialized once from the configured
    seed database. Later writes stay isolated in the test database.
    """

    selection = validate_database_configuration(settings)
    if not selection.codex_test:
        return selection.database_url

    target_path = sqlite_file_path(selection.database_url)
    seed_path = sqlite_file_path(selection.seed_database_url)
    if target_path is None or seed_path is None:
        return selection.database_url
    if target_path.exists():
        return selection.database_url
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if not seed_path.exists():
        raise FileNotFoundError(f"Codex test seed database not found: {seed_path}")
    shutil.copy2(seed_path, target_path)
    return selection.database_url


def create_db_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite:///"):
        sqlite_path = database_url.removeprefix("sqlite:///")
        if sqlite_path and sqlite_path != ":memory:":
            sqlite_file_path(database_url).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )
    return create_engine(database_url)


def init_db(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)
    _migrate_sqlite_schema(engine)


def session_scope(engine: Engine) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def _migrate_sqlite_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if "sessions" not in inspector.get_table_names():
        return

    session_columns = {column["name"] for column in inspector.get_columns("sessions")}
    with engine.begin() as connection:
        if "provider_history_json" not in session_columns:
            connection.execute(
                text(
                    "ALTER TABLE sessions "
                    "ADD COLUMN provider_history_json JSON NOT NULL DEFAULT '[]'"
                )
            )
        if "kind" not in session_columns:
            connection.execute(
                text(
                    "ALTER TABLE sessions "
                    "ADD COLUMN kind VARCHAR NOT NULL DEFAULT 'human_dialogue'"
                )
            )
        if "profile_id" not in session_columns:
            connection.execute(
                text(
                    "ALTER TABLE sessions "
                    "ADD COLUMN profile_id VARCHAR NOT NULL DEFAULT 'local-user'"
                )
            )
        if "autonomy_key" not in session_columns:
            connection.execute(
                text("ALTER TABLE sessions ADD COLUMN autonomy_key VARCHAR")
            )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_sessions_autonomy_key "
                "ON sessions (autonomy_key)"
            )
        )

        turn_columns = {column["name"] for column in inspector.get_columns("turns")}
        if "trigger_kind" not in turn_columns:
            connection.execute(
                text(
                    "ALTER TABLE turns "
                    "ADD COLUMN trigger_kind VARCHAR NOT NULL DEFAULT 'human_message'"
                )
            )
        if "actor" not in turn_columns:
            connection.execute(
                text(
                    "ALTER TABLE turns "
                    "ADD COLUMN actor VARCHAR NOT NULL DEFAULT 'user'"
                )
            )

        if "perception_cursors" in inspector.get_table_names():
            perception_cursor_columns = {
                column["name"]
                for column in inspector.get_columns("perception_cursors")
            }
            if "last_received_at" not in perception_cursor_columns:
                connection.execute(
                    text(
                        "ALTER TABLE perception_cursors "
                        "ADD COLUMN last_received_at DATETIME"
                    )
                )

        if "autonomous_activations" in inspector.get_table_names():
            activation_columns = {
                column["name"]
                for column in inspector.get_columns("autonomous_activations")
            }
            for column_name, target_table in (
                ("candidate_id", "cognitive_candidates"),
                ("episode_id", "cognitive_episodes"),
                ("wake_condition_id", "autonomous_wake_conditions"),
            ):
                if column_name not in activation_columns:
                    connection.execute(
                        text(
                            "ALTER TABLE autonomous_activations "
                            f"ADD COLUMN {column_name} VARCHAR "
                            f"REFERENCES {target_table}(id)"
                        )
                    )
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS "
                        f"ix_autonomous_activations_{column_name} "
                        f"ON autonomous_activations ({column_name})"
                    )
                )
            if "workspace_json" not in activation_columns:
                connection.execute(
                    text(
                        "ALTER TABLE autonomous_activations "
                        "ADD COLUMN workspace_json JSON NOT NULL DEFAULT '{}'"
                    )
                )

        connection.execute(
            text(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS search_documents_fts
                USING fts5(
                    doc_id UNINDEXED,
                    kind UNINDEXED,
                    source_id UNINDEXED,
                    title,
                    body,
                    tags_text,
                    entities_text,
                    predicates_text,
                    scope UNINDEXED,
                    status UNINDEXED,
                    source_session_id UNINDEXED,
                    created_at UNINDEXED,
                    updated_at UNINDEXED,
                    metadata_json UNINDEXED,
                    tokenize = 'unicode61'
                )
                """
            )
        )
