"""Database role selection, validation, and read-only inspection.

The backend can run against several SQLite files, but they do not have the
same ownership or mutation policy. Keeping that distinction here prevents a
test runner, an import side effect, or a deployment from treating a laboratory
snapshot as the production database.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_KNOWN_ROLES = frozenset({"production", "laboratory", "test", "preliminary"})
_PRODUCTION_ENVIRONMENTS = frozenset({"prod", "production"})
_LABORATORY_ENVIRONMENTS = frozenset({"dev", "development", "local"})
_TEST_ENVIRONMENTS = frozenset({"pytest", "test", "testing"})
_PRELIMINARY_ENVIRONMENTS = frozenset({"preliminary", "preliminary-regression"})
_STATE_TABLES = (
    "memories",
    "memory_facts",
    "sessions",
    "messages",
    "events",
    "focus_records",
    "intention_records",
    "affect_states",
)


@dataclass(frozen=True)
class DatabaseSelection:
    """Resolved database role and the selected runtime connection strings."""

    role: str
    codex_test: bool
    database_url: str
    seed_database_url: str


def resolve_database_role(settings: Any) -> str:
    """Resolve the intended ownership role without opening a database."""

    configured_role = str(getattr(settings, "database_role", "auto") or "auto")
    configured_role = configured_role.strip().lower()
    if configured_role != "auto":
        if configured_role not in _KNOWN_ROLES:
            allowed = ", ".join(sorted(_KNOWN_ROLES))
            raise ValueError(f"Unknown database role {configured_role!r}; expected {allowed}.")
        return configured_role

    environment = str(getattr(settings, "environment", "local") or "local")
    environment = environment.strip().lower()
    codex_test = bool(getattr(settings, "codex_test", False))
    if environment in _PRODUCTION_ENVIRONMENTS:
        if codex_test:
            raise ValueError(
                "Production environment cannot enable CODEX_TEST without an explicit "
                "non-production DATABASE_ROLE."
            )
        return "production"
    if codex_test:
        return "test"
    if environment in _LABORATORY_ENVIRONMENTS:
        return "laboratory"
    if environment in _TEST_ENVIRONMENTS:
        return "test"
    if environment in _PRELIMINARY_ENVIRONMENTS:
        return "preliminary"
    raise ValueError(
        "DATABASE_ROLE must be set explicitly when ENVIRONMENT is "
        f"{environment!r}. This avoids guessing whether its database is production, "
        "laboratory, test, or preliminary."
    )


def active_database_url(settings: Any) -> str:
    """Return the connection string selected for this backend process."""

    if bool(getattr(settings, "codex_test", False)):
        return str(getattr(settings, "codex_test_database_url"))
    return str(getattr(settings, "database_url"))


def codex_seed_database_url(settings: Any) -> str:
    """Return the source used only when an isolated Codex test DB is missing."""

    return str(
        getattr(settings, "codex_test_seed_database_url", None)
        or getattr(settings, "database_url")
    )


def database_selection(settings: Any) -> DatabaseSelection:
    """Return the selected database plus its declared ownership role."""

    return DatabaseSelection(
        role=resolve_database_role(settings),
        codex_test=bool(getattr(settings, "codex_test", False)),
        database_url=active_database_url(settings),
        seed_database_url=codex_seed_database_url(settings),
    )


def validate_database_configuration(settings: Any) -> DatabaseSelection:
    """Reject role combinations that could blur production and disposable state."""

    selection = database_selection(settings)
    if selection.role == "production" and selection.codex_test:
        raise ValueError("Production database role cannot use CODEX_TEST isolation.")

    if selection.role == "preliminary":
        if not selection.codex_test:
            raise ValueError("Preliminary regression role requires CODEX_TEST isolation.")
        target_path = sqlite_file_path(selection.database_url)
        if target_path is None or "preliminary" not in target_path.name:
            raise ValueError(
                "Preliminary regression target must be a SQLite file whose name contains "
                "'preliminary'."
            )

    if not selection.codex_test:
        return selection

    target_path = sqlite_file_path(selection.database_url)
    seed_path = sqlite_file_path(selection.seed_database_url)
    if target_path is not None and seed_path is not None:
        if target_path.resolve() == seed_path.resolve():
            raise ValueError("Codex test database must be different from the seed database.")
    return selection


def sqlite_file_path(database_url: str) -> Path | None:
    """Return a SQLite file path without opening or creating it."""

    if not database_url.startswith("sqlite:///"):
        return None
    sqlite_path = database_url.removeprefix("sqlite:///")
    if not sqlite_path or sqlite_path == ":memory:":
        return None
    return Path(sqlite_path)


def safe_database_url(database_url: str) -> str:
    """Keep SQLite paths visible while redacting non-SQLite connection secrets."""

    if sqlite_file_path(database_url) is not None:
        return database_url
    if "://" not in database_url:
        return database_url
    scheme, _separator, _rest = database_url.partition("://")
    return f"{scheme}://<redacted>"


def database_preflight_report(settings: Any) -> dict[str, Any]:
    """Inspect the selected database read-only for deploy/evaluation preflight."""

    selection = validate_database_configuration(settings)
    report: dict[str, Any] = {
        "role": selection.role,
        "codex_test": selection.codex_test,
        "database_url": safe_database_url(selection.database_url),
        "seed_database_url": safe_database_url(selection.seed_database_url),
        "isolation": "seed_copy" if selection.codex_test else "direct",
    }
    path = sqlite_file_path(selection.database_url)
    if path is None:
        report["database"] = {"kind": "non_sqlite_or_memory"}
        return report
    report["database"] = _inspect_sqlite_database(path)
    return report


def _inspect_sqlite_database(path: Path) -> dict[str, Any]:
    resolved_path = path.resolve()
    if not resolved_path.exists():
        return {"kind": "sqlite", "path": str(path), "exists": False}

    uri = f"file:{resolved_path}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        counts = {
            table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in _STATE_TABLES
            if table in tables
        }
    return {
        "kind": "sqlite",
        "path": str(path),
        "exists": True,
        "size_bytes": resolved_path.stat().st_size,
        "integrity": integrity,
        "table_count": len(tables),
        "state_counts": counts,
    }
