from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from app.config import Settings
from app.main import create_app


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
        "model": "MiniMax-M2.7",
    }
