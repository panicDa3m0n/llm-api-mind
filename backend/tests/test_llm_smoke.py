from fastapi.testclient import TestClient

from app.config import Settings
from app.llm.provider import LLMTextResult
from app.main import create_app


class FakeProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 256,
    ) -> LLMTextResult:
        return LLMTextResult(
            model=self.settings.minimax_model,
            text=f"fake:{prompt}:{max_tokens}",
            usage={"input_tokens": 1, "output_tokens": 1},
        )


def test_llm_smoke_test_uses_configured_provider() -> None:
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
    assert body["usage"] == {"input_tokens": 1, "output_tokens": 1}
    assert isinstance(body["latency_ms"], int)


def test_llm_smoke_test_requires_minimax_key() -> None:
    settings = Settings(
        app_name="Test Mind",
        environment="test",
        minimax_api_key=None,
        minimax_model="MiniMax-M2.7",
    )
    client = TestClient(create_app(settings))

    response = client.post("/api/debug/llm-smoke-test", json={"prompt": "ping"})

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "llm.not_configured",
        "message": "MINIMAX_API_KEY is not configured.",
        "recoverable": True,
    }
