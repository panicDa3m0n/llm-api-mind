from typing import Any

from fastapi import APIRouter

from app.config import Settings
from app.llm.factory import active_provider_model, active_provider_name
from app.storage.db import database_runtime_info


def build_system_router(settings: Settings) -> APIRouter:
    router = APIRouter(tags=["system"])

    @router.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "app": settings.app_name,
            "environment": settings.environment,
            "provider": active_provider_name(settings),
            "model": active_provider_model(settings),
            "database": database_runtime_info(settings),
        }

    return router
