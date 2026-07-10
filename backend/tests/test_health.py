import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.config import Settings
from app.main import create_app
from app.storage.db import create_db_engine, init_db, prepare_runtime_database
from app.storage.models import ChatSession


def test_health_returns_runtime_status(db_engine: Engine) -> None:
    settings = Settings(
        app_name="Test Mind",
        environment="test",
        minimax_model="MiniMax-M2.7",
    )
    client = TestClient(create_app(settings, db_engine=db_engine))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "Test Mind",
        "environment": "test",
        "provider": "minimax",
        "model": "MiniMax-M2.7",
        "database": {
            "profile": "test",
            "role": "test",
            "codex_test": False,
            "database_url": "sqlite:///./data/app.db",
            "seed_database_url": "sqlite:///./data/app.db",
            "isolation": "direct",
        },
    }


def test_codex_test_database_is_seeded_and_isolated(tmp_path) -> None:
    source_path = tmp_path / "prod.db"
    target_path = tmp_path / "codex-test.db"
    source_url = f"sqlite:///{source_path}"
    target_url = f"sqlite:///{target_path}"

    source_engine = create_db_engine(source_url)
    init_db(source_engine)
    with Session(source_engine) as db:
        db.add(ChatSession(title="Prod seed session"))
        db.commit()

    settings = Settings(
        app_name="Test Mind",
        environment="test",
        database_url=source_url,
        codex_test=True,
        codex_test_database_url=target_url,
        maintenance_enabled=False,
    )
    client = TestClient(create_app(settings))

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["database"] == {
        "profile": "test",
        "role": "test",
        "codex_test": True,
        "database_url": target_url,
        "seed_database_url": source_url,
        "isolation": "seed_copy",
    }
    assert target_path.exists()

    sessions = client.get("/api/chat/sessions")
    assert sessions.status_code == 200
    assert [session["title"] for session in sessions.json()] == ["Prod seed session"]

    created = client.post("/api/chat/sessions", json={"title": "Codex only"})
    assert created.status_code == 200

    with Session(source_engine) as db:
        source_sessions = db.exec(select(ChatSession)).all()
    assert [session.title for session in source_sessions] == ["Prod seed session"]

    target_engine = create_db_engine(target_url)
    with Session(target_engine) as db:
        target_titles = [session.title for session in db.exec(select(ChatSession)).all()]
    assert sorted(target_titles) == ["Codex only", "Prod seed session"]


def test_codex_test_database_rejects_source_target_alias(tmp_path) -> None:
    database_path = tmp_path / "same.db"
    database_url = f"sqlite:///{database_path}"
    source_engine = create_db_engine(database_url)
    init_db(source_engine)

    settings = Settings(
        database_url=database_url,
        codex_test=True,
        codex_test_database_url=database_url,
    )

    with pytest.raises(ValueError, match="must be different"):
        prepare_runtime_database(settings)
