from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from app.config import Settings
from app.llm.factory import active_provider_model
from app.llm.provider import LLMMessage, LLMTextResult
from app.main import create_app


class FakeProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        return LLMTextResult(
            model=active_provider_model(self.settings),
            text=f"fake:{prompt}:{max_tokens}",
            usage={"input_tokens": 1, "output_tokens": 1},
        )

    def generate_chat(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        return LLMTextResult(
            model=active_provider_model(self.settings),
            text=f"fake:{messages[-1].content}:{max_tokens}",
            usage={"input_tokens": 1, "output_tokens": 1},
        )


def test_llm_smoke_test_uses_configured_provider(db_engine: Engine) -> None:
    settings = Settings(
        app_name="Test Mind",
        environment="test",
        minimax_api_key="test-key",
        minimax_model="MiniMax-M2.7",
    )
    client = TestClient(
        create_app(
            settings,
            llm_provider_factory=lambda settings: FakeProvider(settings),
            db_engine=db_engine,
        )
    )

    response = client.post(
        "/api/debug/llm-smoke-test",
        json={"prompt": "ping", "max_tokens": 8},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["model"] == "MiniMax-M2.7"
    assert body["text"] == "fake:ping:8"
    assert body["max_tokens"] == 8
    assert body["usage"] == {"input_tokens": 1, "output_tokens": 1}
    assert isinstance(body["latency_ms"], int)


def test_llm_smoke_test_uses_configured_default_token_budget(
    db_engine: Engine,
) -> None:
    settings = Settings(
        app_name="Test Mind",
        environment="test",
        minimax_api_key="test-key",
        minimax_model="MiniMax-M3",
        minimax_max_tokens=4096,
        auxiliary_minimax_model="MiniMax-M2.7",
        auxiliary_minimax_max_tokens=6144,
    )
    client = TestClient(
        create_app(
            settings,
            llm_provider_factory=lambda settings: FakeProvider(settings),
            db_engine=db_engine,
        )
    )

    response = client.post("/api/debug/llm-smoke-test", json={"prompt": "ping"})

    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "MiniMax-M2.7"
    assert body["text"] == "fake:ping:6144"
    assert body["max_tokens"] == 6144


def test_llm_smoke_test_uses_auxiliary_minimax_when_scarlet_uses_qwen(
    db_engine: Engine,
) -> None:
    settings = Settings(
        app_name="Test Mind",
        environment="test",
        llm_provider="qwen",
        qwen_api_key="test-key",
        qwen_model="qwen3.7-max",
        qwen_max_tokens=8192,
    )
    client = TestClient(
        create_app(
            settings,
            llm_provider_factory=lambda settings: FakeProvider(settings),
            db_engine=db_engine,
        )
    )

    response = client.post("/api/debug/llm-smoke-test", json={"prompt": "ping"})

    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "MiniMax-M2.7"
    assert body["text"] == "fake:ping:131072"
    assert body["max_tokens"] == 131072


def test_llm_smoke_test_requires_minimax_key(db_engine: Engine) -> None:
    settings = Settings(
        app_name="Test Mind",
        environment="test",
        minimax_api_key=None,
        minimax_model="MiniMax-M2.7",
    )
    client = TestClient(create_app(settings, db_engine=db_engine))

    response = client.post("/api/debug/llm-smoke-test", json={"prompt": "ping"})

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "llm.not_configured",
        "message": "MINIMAX_API_KEY is not configured.",
        "recoverable": True,
    }


def test_llm_smoke_test_requires_auxiliary_minimax_key_when_scarlet_uses_qwen(
    db_engine: Engine,
) -> None:
    settings = Settings(
        app_name="Test Mind",
        environment="test",
        llm_provider="qwen",
        minimax_api_key=None,
        qwen_api_key=None,
        qwen_model="qwen3.7-max",
    )
    client = TestClient(create_app(settings, db_engine=db_engine))

    response = client.post("/api/debug/llm-smoke-test", json={"prompt": "ping"})

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "llm.not_configured",
        "message": "MINIMAX_API_KEY is not configured.",
        "recoverable": True,
    }
