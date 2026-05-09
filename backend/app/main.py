from fastapi import FastAPI
from sqlalchemy.engine import Engine

from app.api.chat import build_chat_router, build_trace_router
from app.api.debug import ProviderFactory, build_debug_router
from app.api.mind import build_mind_router
from app.api.system import build_system_router
from app.config import Settings, get_settings
from app.llm.minimax_client import MiniMaxProvider
from app.storage.db import create_db_engine, init_db


def create_app(
    settings: Settings | None = None,
    llm_provider_factory: ProviderFactory | None = None,
    db_engine: Engine | None = None,
) -> FastAPI:
    runtime_settings = settings or get_settings()
    engine = db_engine or create_db_engine(runtime_settings.database_url)
    init_db(engine)

    app = FastAPI(
        title=runtime_settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.include_router(build_system_router(runtime_settings))
    app.include_router(
        build_chat_router(
            runtime_settings,
            engine,
            provider_factory=llm_provider_factory or MiniMaxProvider,
        )
    )
    app.include_router(
        build_debug_router(
            runtime_settings,
            provider_factory=llm_provider_factory or MiniMaxProvider,
        )
    )
    app.include_router(build_trace_router(engine))
    app.include_router(build_mind_router(engine))

    return app


app = create_app()
