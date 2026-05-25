from collections.abc import Generator
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine


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
