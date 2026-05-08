from fastapi import FastAPI

from app.api.debug import ProviderFactory, build_debug_router
from app.api.system import build_system_router
from app.config import Settings, get_settings
from app.llm.minimax_client import MiniMaxProvider


def create_app(
    settings: Settings | None = None,
    llm_provider_factory: ProviderFactory | None = None,
) -> FastAPI:
    runtime_settings = settings or get_settings()
    app = FastAPI(
        title=runtime_settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.include_router(build_system_router(runtime_settings))
    app.include_router(
        build_debug_router(
            runtime_settings,
            provider_factory=llm_provider_factory or MiniMaxProvider,
        )
    )

    return app


app = create_app()
