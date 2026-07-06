from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.runtime.preferences import (
    RuntimePreferences,
    load_runtime_preferences,
    runtime_preference_options,
    save_runtime_preferences,
)
from app.storage import repositories
from app.storage.db import database_runtime_info
from app.storage.models import MemoryRecord


class RuntimePreferencesResponse(BaseModel):
    timezone: str
    language: str
    language_label: str
    country_code: str
    country_label: str
    profile_id: str
    user_display_name: str
    privacy_scope: str
    source: str
    codex_test: bool
    database: dict[str, Any]
    options: dict[str, Any]


class RuntimePreferencesUpdate(BaseModel):
    timezone: str | None = Field(default=None, max_length=80)
    language: str | None = Field(default=None, max_length=20)
    country_code: str | None = Field(default=None, max_length=8)
    profile_id: str | None = Field(default=None, max_length=80)
    user_display_name: str | None = Field(default=None, max_length=80)
    privacy_scope: str | None = Field(default=None, max_length=80)


class DashboardMemoryResponse(BaseModel):
    id: str
    type: str
    scope: str
    status: str
    content: str
    reason_for_storage: str
    expected_future_use: str | None
    confidence: float
    salience: float
    usage_count: int
    source_session_id: str | None
    source_turn_id: str | None
    source_message_id: str | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None
    metadata: dict[str, Any]


class DashboardMemoriesResponse(BaseModel):
    total: int
    returned: int
    memories: list[DashboardMemoryResponse]


class UserProfileResponse(BaseModel):
    profile_id: str
    display_name: str
    language: str
    language_label: str
    country_code: str
    country_label: str
    timezone: str
    privacy_scope: str
    source: str
    memory_count: int
    top_memories: list[DashboardMemoryResponse]


def build_dashboard_router(settings: Settings, engine: Engine) -> APIRouter:
    router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

    @router.get("/settings", response_model=RuntimePreferencesResponse)
    def get_settings() -> RuntimePreferencesResponse:
        with Session(engine) as db:
            return _preferences_response(settings, load_runtime_preferences(db, settings))

    @router.put("/settings", response_model=RuntimePreferencesResponse)
    def update_settings(
        request: RuntimePreferencesUpdate,
    ) -> RuntimePreferencesResponse:
        with Session(engine) as db:
            try:
                preferences = save_runtime_preferences(
                    db,
                    settings,
                    timezone=request.timezone,
                    language=request.language,
                    country_code=request.country_code,
                    profile_id=request.profile_id,
                    user_display_name=request.user_display_name,
                    privacy_scope=request.privacy_scope,
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "dashboard.invalid_settings",
                        "message": str(exc),
                        "recoverable": True,
                    },
                ) from exc
            return _preferences_response(settings, preferences)

    @router.get("/memories", response_model=DashboardMemoriesResponse)
    def list_memories(
        scope: str | None = Query(default=None, pattern="^(user|project)$"),
        limit: int = Query(default=50, ge=1, le=200),
        include_low_confidence: bool = False,
    ) -> DashboardMemoriesResponse:
        with Session(engine) as db:
            memories = repositories.list_memories(
                db,
                scope=scope,
                include_low_confidence=include_low_confidence,
            )
            return DashboardMemoriesResponse(
                total=len(memories),
                returned=min(len(memories), limit),
                memories=[_memory_response(memory) for memory in memories[:limit]],
            )

    @router.get("/profile", response_model=UserProfileResponse)
    def get_profile() -> UserProfileResponse:
        with Session(engine) as db:
            preferences = load_runtime_preferences(db, settings)
            memories = repositories.list_memories(
                db,
                scope="user",
                include_low_confidence=False,
            )
            return UserProfileResponse(
                profile_id=preferences.profile_id,
                display_name=preferences.user_display_name,
                language=preferences.language,
                language_label=preferences.language_label,
                country_code=preferences.country_code,
                country_label=preferences.country_label,
                timezone=preferences.timezone,
                privacy_scope=preferences.privacy_scope,
                source=preferences.source,
                memory_count=len(memories),
                top_memories=[_memory_response(memory) for memory in memories[:8]],
            )

    return router


def _preferences_response(
    settings: Settings,
    preferences: RuntimePreferences,
) -> RuntimePreferencesResponse:
    return RuntimePreferencesResponse(
        **preferences.as_payload(),
        codex_test=settings.codex_test,
        database=database_runtime_info(settings),
        options=runtime_preference_options(),
    )


def _memory_response(memory: MemoryRecord) -> DashboardMemoryResponse:
    return DashboardMemoryResponse(
        id=memory.id,
        type=memory.memory_type,
        scope=memory.scope,
        status=memory.status,
        content=memory.content,
        reason_for_storage=memory.reason_for_storage,
        expected_future_use=memory.expected_future_use,
        confidence=memory.confidence,
        salience=memory.salience,
        usage_count=memory.usage_count,
        source_session_id=memory.source_session_id,
        source_turn_id=memory.source_turn_id,
        source_message_id=memory.source_message_id,
        tags=memory.tags_json,
        created_at=memory.created_at,
        updated_at=memory.updated_at,
        last_used_at=memory.last_used_at,
        metadata=memory.metadata_json,
    )
