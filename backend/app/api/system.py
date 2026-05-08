from fastapi import APIRouter

from app.config import Settings


def build_system_router(settings: Settings) -> APIRouter:
    router = APIRouter(tags=["system"])

    @router.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "app": settings.app_name,
            "environment": settings.environment,
            "model": settings.minimax_model,
        }

    return router
