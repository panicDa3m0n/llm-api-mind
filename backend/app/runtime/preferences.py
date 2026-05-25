from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlmodel import Session

from app.config import Settings
from app.storage import repositories


SUPPORTED_LANGUAGES = {
    "it": "Italiano",
    "en": "English",
}

SUPPORTED_COUNTRIES = {
    "IT": "Italia",
    "GB": "Regno Unito",
    "US": "Stati Uniti",
    "JP": "Giappone",
}

SETTING_RUNTIME_TIMEZONE = "runtime_timezone"
SETTING_RUNTIME_LANGUAGE = "runtime_language"
SETTING_RUNTIME_COUNTRY = "runtime_country_code"
SETTING_USER_PROFILE_ID = "user_profile_id"
SETTING_USER_DISPLAY_NAME = "user_display_name"
SETTING_USER_PRIVACY_SCOPE = "user_privacy_scope"


@dataclass(frozen=True)
class RuntimePreferences:
    timezone: str
    language: str
    language_label: str
    country_code: str
    country_label: str
    profile_id: str
    user_display_name: str
    privacy_scope: str
    source: str

    def as_payload(self) -> dict[str, Any]:
        return {
            "timezone": self.timezone,
            "language": self.language,
            "language_label": self.language_label,
            "country_code": self.country_code,
            "country_label": self.country_label,
            "profile_id": self.profile_id,
            "user_display_name": self.user_display_name,
            "privacy_scope": self.privacy_scope,
            "source": self.source,
        }


def load_runtime_preferences(db: Session, settings: Settings) -> RuntimePreferences:
    stored = _stored_values(db)
    timezone = _valid_timezone(
        str(stored.get(SETTING_RUNTIME_TIMEZONE) or settings.runtime_timezone)
    )
    language = _valid_language(
        str(stored.get(SETTING_RUNTIME_LANGUAGE) or settings.runtime_language)
    )
    country_code = _valid_country_code(
        str(stored.get(SETTING_RUNTIME_COUNTRY) or settings.runtime_country_code)
    )
    profile_id = _clean_profile_id(
        str(stored.get(SETTING_USER_PROFILE_ID) or settings.user_profile_id)
    )
    user_display_name = _clean_display_name(
        str(stored.get(SETTING_USER_DISPLAY_NAME) or settings.user_display_name)
    )
    privacy_scope = _clean_privacy_scope(
        str(stored.get(SETTING_USER_PRIVACY_SCOPE) or settings.user_privacy_scope)
    )
    language_label = SUPPORTED_LANGUAGES.get(language, settings.runtime_language_label)
    country_label = SUPPORTED_COUNTRIES.get(country_code, settings.runtime_country_label)
    source = "dashboard_settings" if stored else "environment_defaults"
    return RuntimePreferences(
        timezone=timezone,
        language=language,
        language_label=language_label,
        country_code=country_code,
        country_label=country_label,
        profile_id=profile_id,
        user_display_name=user_display_name,
        privacy_scope=privacy_scope,
        source=source,
    )


def save_runtime_preferences(
    db: Session,
    settings: Settings,
    *,
    timezone: str | None = None,
    language: str | None = None,
    country_code: str | None = None,
    profile_id: str | None = None,
    user_display_name: str | None = None,
    privacy_scope: str | None = None,
) -> RuntimePreferences:
    current = load_runtime_preferences(db, settings)
    next_timezone = _valid_timezone(timezone or current.timezone)
    next_language = _valid_language(language or current.language)
    next_country_code = _valid_country_code(country_code or current.country_code)
    next_profile_id = _clean_profile_id(profile_id or current.profile_id)
    next_user_display_name = _clean_display_name(
        user_display_name if user_display_name is not None else current.user_display_name
    )
    next_privacy_scope = _clean_privacy_scope(privacy_scope or current.privacy_scope)
    repositories.upsert_app_setting(
        db,
        key=SETTING_RUNTIME_TIMEZONE,
        value=next_timezone,
    )
    repositories.upsert_app_setting(
        db,
        key=SETTING_RUNTIME_LANGUAGE,
        value=next_language,
    )
    repositories.upsert_app_setting(
        db,
        key=SETTING_RUNTIME_COUNTRY,
        value=next_country_code,
    )
    repositories.upsert_app_setting(
        db,
        key=SETTING_USER_PROFILE_ID,
        value=next_profile_id,
    )
    repositories.upsert_app_setting(
        db,
        key=SETTING_USER_DISPLAY_NAME,
        value=next_user_display_name,
    )
    repositories.upsert_app_setting(
        db,
        key=SETTING_USER_PRIVACY_SCOPE,
        value=next_privacy_scope,
    )
    return load_runtime_preferences(db, settings)


def runtime_preference_options() -> dict[str, Any]:
    return {
        "languages": [
            {"code": code, "label": label}
            for code, label in SUPPORTED_LANGUAGES.items()
        ],
        "timezones": [
            {"id": "Europe/Rome", "label": "Italia - Europe/Rome"},
            {"id": "UTC", "label": "UTC"},
            {"id": "Europe/London", "label": "Europe/London"},
            {"id": "America/New_York", "label": "America/New_York"},
            {"id": "Asia/Tokyo", "label": "Asia/Tokyo"},
        ],
        "countries": [
            {"code": code, "label": label}
            for code, label in SUPPORTED_COUNTRIES.items()
        ],
        "privacy_scopes": [
            {
                "id": "local_single_user",
                "label": "Profilo locale singolo",
            },
            {
                "id": "private_user_profile",
                "label": "Profilo utente privato",
            },
        ],
    }


def _stored_values(db: Session) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for setting in repositories.list_app_settings(db):
        values[setting.key] = setting.value_json.get("value")
    return values


def _valid_timezone(value: str) -> str:
    normalized = value.strip() or "Europe/Rome"
    try:
        ZoneInfo(normalized)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unsupported timezone: {normalized}") from exc
    return normalized


def _valid_language(value: str) -> str:
    normalized = value.strip().casefold() or "it"
    if normalized not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {normalized}")
    return normalized


def _valid_country_code(value: str) -> str:
    normalized = value.strip().upper() or "IT"
    if normalized not in SUPPORTED_COUNTRIES:
        raise ValueError(f"Unsupported country code: {normalized}")
    return normalized


def _clean_profile_id(value: str) -> str:
    normalized = value.strip().casefold().replace(" ", "-") or "local-user"
    allowed = "".join(
        char for char in normalized if char.isalnum() or char in {"-", "_"}
    )
    return (allowed or "local-user")[:80]


def _clean_display_name(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        return "Utente locale"
    return normalized[:80]


def _clean_privacy_scope(value: str) -> str:
    normalized = value.strip().casefold() or "local_single_user"
    if normalized not in {"local_single_user", "private_user_profile"}:
        raise ValueError(f"Unsupported privacy scope: {normalized}")
    return normalized
