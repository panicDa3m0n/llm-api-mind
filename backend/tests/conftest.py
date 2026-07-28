import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine


@pytest.fixture(autouse=True)
def isolate_retrieval_from_local_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep ordinary tests independent from a developer's active reranker.

    Production and local development can enable the OpenRouter-backed final
    reranker through ``backend/.env``. Unit and integration tests that do not
    explicitly model that external service must exercise the deterministic
    baseline instead of accidentally failing closed because a real provider is
    configured but unavailable. Tests that cover active retrieval pass their
    settings explicitly, so their constructor arguments retain precedence.
    """

    monkeypatch.setenv("RETRIEVAL_SHADOW_ENABLED", "false")
    monkeypatch.setenv("RETRIEVAL_SHADOW_BACKEND", "none")
    monkeypatch.setenv("RETRIEVAL_SHADOW_RERANK_ENABLED", "false")
    monkeypatch.setenv("RETRIEVAL_HYBRID_MODE", "off")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")


@pytest.fixture
def db_engine() -> Engine:
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
