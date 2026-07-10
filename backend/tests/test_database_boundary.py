import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import Settings
from app.storage.database_boundary import (
    database_preflight_report,
    resolve_database_role,
    validate_database_configuration,
)


def test_database_role_defaults_are_environment_aware() -> None:
    assert resolve_database_role(Settings(environment="local")) == "laboratory"
    assert resolve_database_role(Settings(environment="test")) == "test"
    assert resolve_database_role(Settings(environment="production")) == "production"
    assert resolve_database_role(
        Settings(environment="mobile_test", database_role="production")
    ) == "production"


def test_unknown_environment_requires_an_explicit_database_role() -> None:
    with pytest.raises(ValueError, match="DATABASE_ROLE must be set explicitly"):
        resolve_database_role(Settings(environment="mobile_test"))


def test_production_role_rejects_codex_test_isolation(tmp_path) -> None:
    with pytest.raises(ValueError, match="Production database role"):
        validate_database_configuration(
            Settings(
                environment="mobile_test",
                database_role="production",
                codex_test=True,
                database_url=f"sqlite:///{tmp_path / 'production.db'}",
                codex_test_database_url=f"sqlite:///{tmp_path / 'test.db'}",
            )
        )


def test_preliminary_role_requires_a_marked_isolated_target(tmp_path) -> None:
    source_url = f"sqlite:///{tmp_path / 'source.db'}"
    with pytest.raises(ValueError, match="name contains 'preliminary'"):
        validate_database_configuration(
            Settings(
                database_role="preliminary",
                codex_test=True,
                database_url=source_url,
                codex_test_database_url=f"sqlite:///{tmp_path / 'run.db'}",
            )
        )

    selection = validate_database_configuration(
        Settings(
            database_role="preliminary",
            codex_test=True,
            database_url=source_url,
            codex_test_database_url=f"sqlite:///{tmp_path / 'preliminary-run.db'}",
        )
    )
    assert selection.role == "preliminary"


def test_preflight_never_creates_a_missing_database(tmp_path) -> None:
    database_path = tmp_path / "missing.db"
    report = database_preflight_report(
        Settings(
            environment="test",
            database_url=f"sqlite:///{database_path}",
        )
    )

    assert report["role"] == "test"
    assert report["database"] == {
        "kind": "sqlite",
        "path": str(database_path),
        "exists": False,
    }
    assert not database_path.exists()


def test_importing_app_factory_does_not_open_the_runtime_database(tmp_path) -> None:
    database_path = tmp_path / "import-must-not-create.db"
    backend_root = Path(__file__).resolve().parents[1]
    environment = os.environ | {
        "ENVIRONMENT": "test",
        "DATABASE_ROLE": "test",
        "DATABASE_URL": f"sqlite:///{database_path}",
        "CODEX_TEST": "false",
    }

    completed = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=backend_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert not database_path.exists()
