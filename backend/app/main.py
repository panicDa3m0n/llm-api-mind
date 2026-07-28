from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine

from app.api.chat import build_chat_router, build_trace_router
from app.api.autonomy import build_autonomy_router
from app.api.dashboard import build_dashboard_router
from app.api.device_exploration import build_device_exploration_router
from app.api.debug import ProviderFactory, build_debug_router
from app.api.maintenance import build_maintenance_router
from app.api.mind import build_mind_router
from app.api.system import build_system_router
from app.config import Settings, get_settings
from app.llm.factory import build_llm_provider
from app.plugins.gpt_bridge import build_gpt_bridge_router
from app.runtime.maintenance import start_maintenance_worker
from app.runtime.autonomy import start_autonomous_activation_worker
from app.storage.database_boundary import validate_database_configuration
from app.storage.db import create_db_engine, init_db, prepare_runtime_database


def create_app(
    settings: Settings | None = None,
    llm_provider_factory: ProviderFactory | None = None,
    db_engine: Engine | None = None,
) -> FastAPI:
    runtime_settings = settings or get_settings()
    validate_database_configuration(runtime_settings)
    engine = db_engine or create_db_engine(prepare_runtime_database(runtime_settings))
    provider_factory = llm_provider_factory or build_llm_provider
    init_db(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.stop_maintenance_worker = start_maintenance_worker(
            engine,
            settings=runtime_settings,
            provider_factory=provider_factory,
        )
        app.state.stop_autonomous_activation_worker = (
            start_autonomous_activation_worker(
                engine,
                settings=runtime_settings,
                provider_factory=provider_factory,
            )
        )
        try:
            yield
        finally:
            stop_autonomy = getattr(
                app.state,
                "stop_autonomous_activation_worker",
                None,
            )
            if stop_autonomy is not None:
                stop_autonomy()
                app.state.stop_autonomous_activation_worker = None
            stop = getattr(app.state, "stop_maintenance_worker", None)
            if stop is not None:
                stop()
                app.state.stop_maintenance_worker = None

    app = FastAPI(
        title=runtime_settings.app_name,
        version="1.65.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://localhost",
            "http://localhost",
            "capacitor://localhost",
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=[
            "X-Scarlet-Stream-Schema",
            "X-Scarlet-Turn-ID",
        ],
    )

    app.include_router(build_system_router(runtime_settings))
    app.include_router(
        build_autonomy_router(
            engine,
            runtime_settings,
            provider_factory=provider_factory,
        )
    )
    app.include_router(build_device_exploration_router(engine, runtime_settings))
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
    app.include_router(
        build_maintenance_router(
            engine,
            runtime_settings,
            provider_factory=provider_factory,
        )
    )
    app.include_router(build_trace_router(engine))
    app.include_router(
        build_mind_router(
            engine,
            runtime_settings,
            provider_factory=provider_factory,
        )
    )
    app.include_router(
        build_gpt_bridge_router(
            engine,
            runtime_settings,
            provider_factory=provider_factory,
        )
    )

    return app
