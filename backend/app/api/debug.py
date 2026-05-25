import time
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.config import Settings
from app.llm.factory import active_provider_max_tokens, build_llm_provider
from app.llm.provider import LLMConfigurationError, LLMProvider, LLMRequestError


class LLMSmokeTestRequest(BaseModel):
    prompt: str = Field(
        default="Reply with exactly: pong",
        min_length=1,
        max_length=1000,
    )
    max_tokens: int | None = Field(default=None, ge=1, le=131072)


class LLMSmokeTestResponse(BaseModel):
    ok: bool
    model: str
    text: str
    max_tokens: int
    latency_ms: int
    usage: dict[str, Any]


ProviderFactory = Callable[[Settings], LLMProvider]


def build_debug_router(
    settings: Settings,
    provider_factory: ProviderFactory = build_llm_provider,
) -> APIRouter:
    router = APIRouter(prefix="/api/debug", tags=["debug"])

    @router.post("/llm-smoke-test", response_model=LLMSmokeTestResponse)
    def llm_smoke_test(request: LLMSmokeTestRequest) -> LLMSmokeTestResponse:
        started = time.perf_counter()
        try:
            provider = provider_factory(settings)
            max_tokens = request.max_tokens or active_provider_max_tokens(settings)
            result = provider.generate_text(
                prompt=request.prompt,
                max_tokens=max_tokens,
            )
        except LLMConfigurationError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "llm.not_configured",
                    "message": str(exc),
                    "recoverable": True,
                },
            ) from exc
        except LLMRequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "llm.provider_error",
                    "message": str(exc),
                    "recoverable": True,
                },
            ) from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        return LLMSmokeTestResponse(
            ok=True,
            model=result.model,
            text=result.text,
            max_tokens=max_tokens,
            latency_ms=latency_ms,
            usage=result.usage,
        )

    return router
