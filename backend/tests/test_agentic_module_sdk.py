import asyncio
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.agentic_modules.contracts import AgenticModuleManifest as CoreManifest
from app.agentic_modules.host import AgenticModuleHost
from app.agentic_modules.registry import ApprovedModule, discover_modules
from scarlet_agentic_module_sdk import (
    AgenticModule,
    AgenticModuleManifest,
    run_conformance,
    scaffold_module,
    serve,
    validate_manifest,
)
from scarlet_agentic_module_sdk.cli import main
from scarlet_agentic_module_sdk.contracts import (
    ContextPortBudget,
    HealthPortRequest,
    PortCallContext,
)
from scarlet_agentic_module_sdk.schema import contract_schemas
from scarlet_agentic_module_sdk.client import resolve_entrypoint


def test_sdk_and_core_use_the_same_contract_class_and_versioned_schemas() -> None:
    assert AgenticModuleManifest is CoreManifest
    schemas = contract_schemas()
    assert set(schemas) == {
        "agentic-module-manifest-v1.schema.json",
        "command-port-request-v1.schema.json",
        "command-port-result-v1.schema.json",
        "context-port-request-v1.schema.json",
        "context-port-result-v1.schema.json",
        "event-port-request-v1.schema.json",
        "event-port-result-v1.schema.json",
        "health-port-request-v1.schema.json",
        "health-port-result-v1.schema.json",
        "prompt-port-request-v1.schema.json",
        "prompt-port-result-v1.schema.json",
    }
    assert (
        schemas["agentic-module-manifest-v1.schema.json"]["additionalProperties"]
        is False
    )


def test_module_runtime_returns_typed_result_and_structured_error() -> None:
    context = PortCallContext(
        request_id="request-health",
        module_id="cloud.honeylabs.fixture",
        core_version="1.55.0",
        active_mode_tag="interactive",
        deadline_at=datetime.now(timezone.utc),
    )
    requests = [
        {
            "protocol_version": "agentic-module-port-v1",
            "request_id": "request-health",
            "operation": "health",
            "capability_id": None,
            "payload": HealthPortRequest(context=context).model_dump(mode="json"),
        },
        {
            "protocol_version": "agentic-module-port-v1",
            "request_id": "request-unknown",
            "operation": "unknown",
            "capability_id": None,
            "payload": {},
        },
        {
            "protocol_version": "agentic-module-port-v1",
            "request_id": "request-stop",
            "operation": "lifecycle.stop",
            "capability_id": None,
            "payload": {},
        },
    ]
    source = io.StringIO("".join(json.dumps(item) + "\n" for item in requests))
    target = io.StringIO()

    serve(AgenticModule(), input_stream=source, output_stream=target)

    responses = [json.loads(line) for line in target.getvalue().splitlines()]
    assert responses[0]["result"]["status"] == "healthy"
    assert responses[1]["ok"] is False
    assert responses[1]["error"]["code"] == "operation.unknown"
    assert responses[2]["result"]["status"] == "stopped"


def test_manifest_diagnostics_are_localized(tmp_path: Path) -> None:
    module = tmp_path / "invalid"
    module.mkdir()
    (module / "agentic-module.json").write_text(
        json.dumps({"module_id": "INVALID"}),
        encoding="utf-8",
    )

    manifest, diagnostics = validate_manifest(module)

    assert manifest is None
    assert diagnostics
    assert any(item.location == "module_id" for item in diagnostics)
    assert all(item.code == "manifest.contract_invalid" for item in diagnostics)


def test_manifest_conformance_rejects_permissions_and_unknown_modes(
    tmp_path: Path,
) -> None:
    module = scaffold_module(
        tmp_path / "invalid-policy",
        module_id="cloud.honeylabs.invalid-policy",
    )
    manifest_path = module / "agentic-module.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["mode_tags"] = ["maintenance"]
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    manifest, diagnostics = validate_manifest(module)

    assert manifest is not None
    assert diagnostics[0].code == "manifest.unknown_mode_tag"
    assert diagnostics[0].location == "mode_tags"

    payload["mode_tags"] = ["interactive"]
    payload["permissions"].remove("context.contribute")
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    manifest, diagnostics = validate_manifest(module)

    assert manifest is None
    assert any(
        item.code == "manifest.contract_invalid" and item.location == "permissions"
        for item in diagnostics
    )


def test_scaffold_passes_standalone_conformance_without_patch(tmp_path: Path) -> None:
    module = scaffold_module(
        tmp_path / "fixture",
        module_id="cloud.honeylabs.generated-fixture",
    )
    manifest = AgenticModuleManifest.model_validate_json(
        (module / "agentic-module.json").read_text(encoding="utf-8")
    )
    assert resolve_entrypoint(module, manifest)[:2] == [
        sys.executable,
        str((module / "run-module").resolve()),
    ]

    report = asyncio.run(run_conformance(module))

    assert report.ok is True
    assert report.module_id == "cloud.honeylabs.generated-fixture"
    assert {item.step for item in report.diagnostics} >= {
        "manifest",
        "lifecycle.start",
        "health",
        "context.contribute",
        "prompt.contribute",
        "command.invoke",
        "event.handle",
        "protocol.error",
        "lifecycle.stop",
    }
    assert all(item.status == "passed" for item in report.diagnostics)
    assert all(
        item.request_id is not None
        for item in report.diagnostics
        if item.step != "manifest"
    )


def test_scaffold_runs_through_real_core_host_without_patch(tmp_path: Path) -> None:
    async def scenario() -> None:
        root = tmp_path / "modules"
        module = scaffold_module(
            root / "fixture",
            module_id="cloud.honeylabs.generated-host-fixture",
        )
        manifest_path = module / "agentic-module.json"
        approval = ApprovedModule(
            module_id="cloud.honeylabs.generated-host-fixture",
            manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        )
        registry = discover_modules([root], approvals=[approval])
        assert registry.diagnostics == ()
        host = AgenticModuleHost(registry, core_version="1.55.0")
        plan = await host.activate("interactive")
        assert plan.ordered_active_modules == [approval.module_id]
        context = await host.contribute_context(
            budget=ContextPortBudget(max_tokens=100, max_items=2)
        )
        assert context.contributions[0].module_id == approval.module_id
        command = await host.invoke_command(
            namespace="cloud_honeylabs_generated_host_fixture",
            command="echo",
            arguments={"value": 9},
        )
        assert command.output == {"echo": {"value": 9}}
        await host.stop()

    asyncio.run(scenario())


def test_cli_scaffold_validate_schema_and_conformance(
    tmp_path: Path,
    capsys,
) -> None:
    module = tmp_path / "cli-fixture"
    assert main(["scaffold", str(module), "--module-id", "cloud.honeylabs.cli"]) == 0
    assert main(["validate", str(module)]) == 0
    schemas = tmp_path / "schemas"
    assert main(["schema", "--output", str(schemas)]) == 0
    assert (schemas / "agentic-module-manifest-v1.schema.json").is_file()
    assert main(["conformance", str(module)]) == 0
    output = capsys.readouterr().out
    assert '"ok": true' in output.lower()
