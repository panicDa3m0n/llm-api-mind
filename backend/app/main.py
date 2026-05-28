from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.engine import Engine

from app.api.chat import build_chat_router, build_trace_router
from app.api.dashboard import build_dashboard_router
from app.api.debug import ProviderFactory, build_debug_router
from app.api.maintenance import build_maintenance_router
from app.api.mind import build_mind_router
from app.api.system import build_system_router
from app.config import Settings, get_settings
from app.llm.factory import build_llm_provider
from app.runtime.maintenance import start_maintenance_worker
from app.storage.db import create_db_engine, init_db


def create_app(
    settings: Settings | None = None,
    llm_provider_factory: ProviderFactory | None = None,
    db_engine: Engine | None = None,
) -> FastAPI:
    runtime_settings = settings or get_settings()
    engine = db_engine or create_db_engine(runtime_settings.database_url)
    provider_factory = llm_provider_factory or build_llm_provider
    init_db(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.stop_maintenance_worker = start_maintenance_worker(
            engine,
            settings=runtime_settings,
            provider_factory=provider_factory,
        )
        try:
            yield
        finally:
            stop = getattr(app.state, "stop_maintenance_worker", None)
            if stop is not None:
                stop()
                app.state.stop_maintenance_worker = None

    app = FastAPI(
        title=runtime_settings.app_name,
        version="1.3.1",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.include_router(build_system_router(runtime_settings))
    app.include_router(build_dashboard_router(runtime_settings, engine))
    app.include_router(
        build_chat_router(
            runtime_settings,
            engine,
            provider_factory=provider_factory,
        )
    )
    app.include_router(
        build_debug_router(
            runtime_settings,
            provider_factory=provider_factory,
        )
    )
    app.include_router(build_maintenance_router(engine))
    app.include_router(build_trace_router(engine))
    app.include_router(
        build_mind_router(
            engine,
            runtime_settings,
            provider_factory=provider_factory,
        )
    )

    return app


app = create_app()
