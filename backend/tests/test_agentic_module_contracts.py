import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.agentic_modules.contracts import (
    AGENTIC_MODULE_MANIFEST_VERSION,
    AGENTIC_MODULE_PORT_VERSION,
    AgenticModuleManifest,
    CommandPortResult,
    ContextPortBudget,
    ContextPortRequest,
    CoreCompatibility,
    PortCallContext,
    compare_semver,
)
from app.agentic_modules.validation import build_activation_plan


FIXTURES = Path(__file__).parent / "fixtures" / "agentic_modules"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _manifest(
    module_id: str,
    *,
    version: str = "1.0.0",
    modes: list[str] | None = None,
    dependencies: list[dict] | None = None,
) -> AgenticModuleManifest:
    return AgenticModuleManifest.model_validate(
        {
            "module_id": module_id,
            "display_name": module_id,
            "description": f"Fixture for {module_id}",
            "module_version": version,
            "core_compatibility": {"minimum_core_version": "1.52.0"},
            "mode_tags": modes or ["interactive"],
            "capabilities": [
                {
                    "kind": "context",
                    "capability_id": f"{module_id}.context",
                    "produces_block_types": [f"{module_id}.context"],
                }
            ],
            "permissions": ["context.contribute"],
            "dependencies": dependencies or [],
            "runtime": {"entrypoint": ["python", "-m", module_id]},
        }
    )


def test_valid_manifest_fixture_and_json_schema_are_public_and_strict() -> None:
    manifest = AgenticModuleManifest.model_validate(
        _fixture("context_observer.valid.json")
    )
    schema = AgenticModuleManifest.model_json_schema()

    assert manifest.schema_version == AGENTIC_MODULE_MANIFEST_VERSION
    assert manifest.capabilities[0].port_version == AGENTIC_MODULE_PORT_VERSION
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) >= {
        "module_id",
        "module_version",
        "core_compatibility",
        "mode_tags",
        "capabilities",
        "runtime",
    }


def test_manifest_rejects_direct_database_permission() -> None:
    with pytest.raises(ValidationError) as exc_info:
        AgenticModuleManifest.model_validate(_fixture("database_access.invalid.json"))

    assert "database.read" in str(exc_info.value)


def test_manifest_rejects_capability_without_required_permission() -> None:
    payload = _fixture("context_observer.valid.json")
    payload["permissions"].remove("context.contribute")

    with pytest.raises(ValidationError, match="undeclared permissions"):
        AgenticModuleManifest.model_validate(payload)


def test_semver_precedence_and_exclusive_core_range() -> None:
    compatibility = CoreCompatibility(
        minimum_core_version="1.52.0",
        maximum_core_version_exclusive="2.0.0",
    )

    assert compare_semver("1.52.0-alpha.1", "1.52.0") < 0
    assert compare_semver("1.52.1", "1.52.0") > 0
    assert compatibility.supports("1.52.0") is True
    assert compatibility.supports("1.99.9") is True
    assert compatibility.supports("2.0.0") is False
    with pytest.raises(ValueError, match="leading zeroes"):
        compare_semver("1.52.0-alpha.01", "1.52.0")


def test_required_core_contract_version_is_enforced() -> None:
    manifest = _manifest("cloud.honeylabs.contract-consumer")
    manifest.core_compatibility.required_contracts = {
        "agentic-module-port": "agentic-module-port-v2"
    }

    plan = build_activation_plan(
        [manifest],
        core_version="1.52.0",
        active_mode_tag="interactive",
    )

    assert plan.registry_valid is False
    assert plan.states[0].status == "blocked"
    assert plan.diagnostics[0].code == "module.contract_incompatible"


def test_explicit_empty_core_contract_catalog_does_not_use_defaults() -> None:
    manifest = AgenticModuleManifest.model_validate(
        _fixture("context_observer.valid.json")
    )

    plan = build_activation_plan(
        [manifest],
        core_version="1.52.0",
        active_mode_tag="interactive",
        available_contracts={},
    )

    assert plan.registry_valid is False
    assert plan.available_contracts == {}
    assert plan.diagnostics[0].code == "module.contract_incompatible"


def test_port_envelopes_reject_unknown_fields_and_inconsistent_results() -> None:
    call_context = PortCallContext(
        request_id="request-1",
        module_id="cloud.honeylabs.context-observer",
        core_version="1.52.0",
        active_mode_tag="interactive",
        session_id="session-1",
        turn_id="turn-1",
        deadline_at=datetime.now(timezone.utc),
    )
    request = ContextPortRequest(
        context=call_context,
        budget=ContextPortBudget(max_tokens=2000, max_items=5),
    )

    assert request.context.protocol_version == AGENTIC_MODULE_PORT_VERSION
    with pytest.raises(ValidationError):
        ContextPortRequest.model_validate(
            {
                **request.model_dump(mode="json"),
                "database_path": "/private/core.db",
            }
        )
    with pytest.raises(ValidationError, match="error details"):
        CommandPortResult(status="error")


def test_activation_orders_required_dependencies_before_dependents() -> None:
    base = _manifest("cloud.honeylabs.base")
    dependent = _manifest(
        "cloud.honeylabs.dependent",
        dependencies=[
            {
                "module_id": base.module_id,
                "minimum_version": "1.0.0",
            }
        ],
    )

    plan = build_activation_plan(
        [dependent, base],
        core_version="1.52.0",
        active_mode_tag="interactive",
    )

    assert plan.registry_valid is True
    assert plan.ordered_active_modules == [base.module_id, dependent.module_id]
    assert {item.status for item in plan.states} == {"active"}


def test_missing_optional_dependency_warns_without_blocking() -> None:
    module = _manifest(
        "cloud.honeylabs.optional-consumer",
        dependencies=[
            {
                "module_id": "cloud.honeylabs.optional-provider",
                "minimum_version": "1.0.0",
                "optional": True,
            }
        ],
    )

    plan = build_activation_plan(
        [module],
        core_version="1.52.0",
        active_mode_tag="interactive",
    )

    assert plan.registry_valid is True
    assert plan.ordered_active_modules == [module.module_id]
    assert [item.code for item in plan.diagnostics] == ["dependency.missing_optional"]


def test_missing_required_dependency_blocks_only_its_consumer() -> None:
    independent = _manifest("cloud.honeylabs.independent")
    consumer = _manifest(
        "cloud.honeylabs.consumer",
        dependencies=[
            {
                "module_id": "cloud.honeylabs.missing",
                "minimum_version": "1.0.0",
            }
        ],
    )

    plan = build_activation_plan(
        [consumer, independent],
        core_version="1.52.0",
        active_mode_tag="interactive",
    )

    assert plan.registry_valid is False
    assert plan.ordered_active_modules == [independent.module_id]
    assert (
        next(
            item for item in plan.states if item.module_id == consumer.module_id
        ).status
        == "blocked"
    )


def test_duplicate_module_ids_are_rejected() -> None:
    first = _manifest("cloud.honeylabs.duplicate", version="1.0.0")
    second = _manifest("cloud.honeylabs.duplicate", version="1.1.0")

    plan = build_activation_plan(
        [first, second],
        core_version="1.52.0",
        active_mode_tag="interactive",
    )

    assert plan.registry_valid is False
    assert plan.ordered_active_modules == []
    assert plan.diagnostics[0].code == "module.duplicate_id"


def test_core_and_required_dependency_versions_fail_closed() -> None:
    old_module = _manifest("cloud.honeylabs.old-core")
    old_module.core_compatibility.minimum_core_version = "2.0.0"
    provider = _manifest("cloud.honeylabs.provider", version="1.0.0")
    consumer = _manifest(
        "cloud.honeylabs.version-consumer",
        dependencies=[
            {
                "module_id": provider.module_id,
                "minimum_version": "2.0.0",
            }
        ],
    )

    plan = build_activation_plan(
        [old_module, provider, consumer],
        core_version="1.52.0",
        active_mode_tag="interactive",
    )

    assert plan.registry_valid is False
    assert plan.ordered_active_modules == [provider.module_id]
    assert {item.code for item in plan.diagnostics} == {
        "module.core_incompatible",
        "dependency.required_version_incompatible",
    }


def test_required_dependency_cycle_is_rejected() -> None:
    first = _manifest(
        "cloud.honeylabs.first",
        dependencies=[
            {
                "module_id": "cloud.honeylabs.second",
                "minimum_version": "1.0.0",
            }
        ],
    )
    second = _manifest(
        "cloud.honeylabs.second",
        dependencies=[
            {
                "module_id": "cloud.honeylabs.first",
                "minimum_version": "1.0.0",
            }
        ],
    )

    plan = build_activation_plan(
        [first, second],
        core_version="1.52.0",
        active_mode_tag="interactive",
    )

    assert plan.registry_valid is False
    assert plan.ordered_active_modules == []
    assert {item.code for item in plan.diagnostics} == {"dependency.required_cycle"}


def test_background_process_name_is_not_an_agent_mode() -> None:
    manifest = AgenticModuleManifest.model_validate(
        _fixture("background_mode.invalid.json")
    )

    plan = build_activation_plan(
        [manifest],
        core_version="1.52.0",
        active_mode_tag="interactive",
    )

    assert plan.registry_valid is False
    assert plan.states[0].status == "blocked"
    assert plan.diagnostics[0].code == "module.unknown_mode_tag"


def test_required_dependency_must_share_the_selected_agent_mode() -> None:
    scouting_only = _manifest(
        "cloud.honeylabs.scouting-source",
        modes=["scouting"],
    )
    interactive = _manifest(
        "cloud.honeylabs.interactive-consumer",
        dependencies=[
            {
                "module_id": scouting_only.module_id,
                "minimum_version": "1.0.0",
            }
        ],
    )

    plan = build_activation_plan(
        [scouting_only, interactive],
        core_version="1.52.0",
        active_mode_tag="interactive",
    )

    assert plan.registry_valid is False
    assert plan.ordered_active_modules == []
    assert any(item.code == "dependency.inactive_for_mode" for item in plan.diagnostics)
