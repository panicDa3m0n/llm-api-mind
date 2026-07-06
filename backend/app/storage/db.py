from collections.abc import Generator
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine


def active_database_url(settings: Any) -> str:
    """Return the database URL selected for this backend process."""

    if bool(getattr(settings, "codex_test", False)):
        return str(getattr(settings, "codex_test_database_url"))
    return str(getattr(settings, "database_url"))


def database_runtime_info(settings: Any) -> dict[str, Any]:
    """Expose safe database-selection metadata for health/debug surfaces."""

    database_url = active_database_url(settings)
    return {
        "profile": "codex_test" if bool(getattr(settings, "codex_test", False)) else "prod",
        "codex_test": bool(getattr(settings, "codex_test", False)),
        "database_url": _safe_database_url(database_url),
        "seed_database_url": _safe_database_url(_codex_seed_database_url(settings)),
    }


def prepare_runtime_database(settings: Any) -> str:
    """Prepare the selected database and return the URL to open.

    In codex-test mode, the test database is initialized once from the configured
    seed database. Later writes stay isolated in the test database.
    """

    database_url = active_database_url(settings)
    if not bool(getattr(settings, "codex_test", False)):
        return database_url

    target_path = _sqlite_file_path(database_url)
    seed_path = _sqlite_file_path(_codex_seed_database_url(settings))
    if target_path is None or seed_path is None:
        return database_url
    if target_path.resolve() == seed_path.resolve():
        raise ValueError(
            "Codex test database must be different from the seed database."
        )
    if target_path.exists():
        return database_url
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if not seed_path.exists():
        raise FileNotFoundError(f"Codex test seed database not found: {seed_path}")
    shutil.copy2(seed_path, target_path)
    return database_url


def create_db_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite:///"):
        sqlite_path = database_url.removeprefix("sqlite:///")
        if sqlite_path and sqlite_path != ":memory:":
            Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
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


def _codex_seed_database_url(settings: Any) -> str:
    return str(
        getattr(settings, "codex_test_seed_database_url", None)
        or getattr(settings, "database_url")
    )


def _sqlite_file_path(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite:///"):
        return None
    sqlite_path = database_url.removeprefix("sqlite:///")
    if not sqlite_path or sqlite_path == ":memory:":
        return None
    return Path(sqlite_path)


def _safe_database_url(database_url: str) -> str:
    sqlite_path = _sqlite_file_path(database_url)
    if sqlite_path is not None:
        return database_url
    if "://" not in database_url:
        return database_url
    scheme, _separator, _rest = database_url.partition("://")
    return f"{scheme}://<redacted>"


def _migrate_sqlite_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if "sessions" not in inspector.get_table_names():
        return

    session_columns = {column["name"] for column in inspector.get_columns("sessions")}
    if "provider_history_json" not in session_columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE sessions "
                    "ADD COLUMN provider_history_json JSON NOT NULL DEFAULT '[]'"
                )
            )
    with engine.begin() as connection:
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
