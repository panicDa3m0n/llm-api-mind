import asyncio
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlmodel import Session

from app.agentic_modules.contracts import (
    ContextInputBlock,
    ContextPortBudget,
    ModuleEvent,
)
from app.agentic_modules.host import AgenticModuleHost
from app.agentic_modules.registry import (
    ApprovedModule,
    discover_modules,
)
from app.agentic_modules.telemetry import (
    InMemoryModuleTelemetry,
    RepositoryModuleTelemetry,
)
from app.storage import repositories
from app.storage.db import init_db


WORKER = (
    Path(__file__).parent / "fixtures" / "agentic_modules" / "conformance_worker.py"
)


def _install_module(
    root: Path,
    module_id: str,
    *,
    behavior: str = "normal",
    timeout: float = 0.2,
    dependencies: list[dict] | None = None,
    context_read: bool = True,
) -> ApprovedModule:
    directory = root / module_id.replace(".", "-")
    directory.mkdir(parents=True)
    shutil.copy2(WORKER, directory / "worker.py")
    payload = {
        "module_id": module_id,
        "display_name": module_id,
        "description": f"Conformance fixture {module_id}",
        "module_version": "1.0.0",
        "core_compatibility": {
            "minimum_core_version": "1.53.0",
            "required_contracts": {
                "agentic-module-port": "agentic-module-port-v1",
                "agentic-module-lifecycle": "agentic-module-lifecycle-v1",
            },
        },
        "mode_tags": ["interactive"],
        "capabilities": [
            {
                "kind": "context",
                "capability_id": "fixture.context",
                "produces_block_types": ["fixture.observation"],
                "max_contributions": 2,
            },
            {
                "kind": "prompt",
                "capability_id": "fixture.prompt",
                "slots": ["turn_context"],
                "max_characters": 1000,
            },
            {
                "kind": "command",
                "capability_id": "fixture.command",
                "namespace": module_id.replace(".", "_"),
                "commands": ["echo"],
            },
            {
                "kind": "event",
                "capability_id": "fixture.event",
                "subscribes_to": ["turn.started"],
                "publishes": ["fixture.observed"],
            },
        ],
        "permissions": [
            *(["context.read"] if context_read else []),
            "context.contribute",
            "prompt.contribute",
            "command.register",
            "event.subscribe",
            "event.publish",
        ],
        "dependencies": dependencies or [],
        "runtime": {
            "entrypoint": [sys.executable, "worker.py", behavior],
        },
        "timeouts": {
            "startup_seconds": 1.0,
            "call_seconds": timeout,
            "health_seconds": 0.5,
            "shutdown_seconds": 0.5,
        },
    }
    raw = json.dumps(payload, indent=2, sort_keys=True).encode()
    manifest_path = directory / "agentic-module.json"
    manifest_path.write_bytes(raw)
    return ApprovedModule(
        module_id=module_id,
        manifest_sha256=hashlib.sha256(raw).hexdigest(),
    )


def test_registry_is_approved_pinned_and_deterministic(tmp_path: Path) -> None:
    root = tmp_path / "modules"
    second = _install_module(root, "cloud.honeylabs.second")
    first = _install_module(root, "cloud.honeylabs.first")

    registry = discover_modules([root], approvals=[second, first])

    assert [item.manifest.module_id for item in registry.modules] == [
        "cloud.honeylabs.first",
        "cloud.honeylabs.second",
    ]
    assert registry.diagnostics == ()

    manifest = root / "cloud-honeylabs-first" / "agentic-module.json"
    manifest.write_text(manifest.read_text() + "\n", encoding="utf-8")
    tampered = discover_modules([root], approvals=[second, first])
    assert [item.manifest.module_id for item in tampered.modules] == [
        "cloud.honeylabs.second"
    ]
    assert tampered.diagnostics[0].code == "registry.manifest_digest_mismatch"


def test_registry_rejects_unapproved_module(tmp_path: Path) -> None:
    root = tmp_path / "modules"
    _install_module(root, "cloud.honeylabs.unapproved")

    registry = discover_modules([root], approvals=[])

    assert registry.modules == ()
    assert registry.diagnostics[0].code == "registry.module_not_approved"


def test_registry_rejects_ambiguous_operator_approval(tmp_path: Path) -> None:
    root = tmp_path / "modules"
    approval = _install_module(root, "cloud.honeylabs.ambiguous")

    registry = discover_modules([root], approvals=[approval, approval])

    assert registry.modules == ()
    assert {item.code for item in registry.diagnostics} == {
        "registry.duplicate_approval",
        "registry.module_not_approved",
    }


def test_real_host_lifecycle_ports_composition_and_receipts(tmp_path: Path) -> None:
    async def scenario() -> None:
        root = tmp_path / "modules"
        approval = _install_module(root, "cloud.honeylabs.fixture")
        registry = discover_modules([root], approvals=[approval])
        telemetry = InMemoryModuleTelemetry()
        host = AgenticModuleHost(
            registry,
            core_version="1.53.0",
            telemetry=telemetry,
        )
        plan = await host.activate("interactive")
        assert plan.ordered_active_modules == ["cloud.honeylabs.fixture"]
        assert host.running_module_ids == ["cloud.honeylabs.fixture"]
        assert (await host.health())["cloud.honeylabs.fixture"].status == "healthy"

        context = await host.contribute_context(
            budget=ContextPortBudget(max_tokens=100, max_items=3),
            inputs=[
                ContextInputBlock(
                    block_id="input-1",
                    block_type="turn.message",
                    content={"text": "hello"},
                )
            ],
        )
        assert context.contributions[0].contribution.block_type == "fixture.observation"

        prompt = await host.contribute_prompt(
            slots=["turn_context"],
            max_characters=100,
        )
        assert prompt.contributions[0].contribution.text.startswith("Fixture")

        command = await host.invoke_command(
            namespace="cloud_honeylabs_fixture",
            command="echo",
            arguments={"value": 7},
        )
        assert command.output == {"echo": {"value": 7}}

        event = await host.dispatch_event(
            ModuleEvent(
                event_id="event-1",
                event_type="turn.started",
                occurred_at=datetime.now(timezone.utc),
            )
        )
        assert [item.event_type for item in event.publications] == ["fixture.observed"]
        await host.stop()
        assert host.running_module_ids == []
        lifecycle = [
            item.status
            for item in telemetry.receipts
            if item.operation == "lifecycle.start"
        ]
        assert lifecycle == ["started", "succeeded"]
        assert any(
            item.operation == "context.contribute" and item.status == "succeeded"
            for item in telemetry.receipts
        )

    asyncio.run(scenario())


def test_context_composition_uses_stable_activation_order(tmp_path: Path) -> None:
    async def scenario() -> None:
        root = tmp_path / "modules"
        second = _install_module(root, "cloud.honeylabs.second")
        first = _install_module(root, "cloud.honeylabs.first")
        host = AgenticModuleHost(
            discover_modules([root], approvals=[second, first]),
            core_version="1.53.0",
        )
        await host.activate("interactive")
        result = await host.contribute_context(
            budget=ContextPortBudget(max_tokens=100, max_items=5)
        )
        assert [item.module_id for item in result.contributions] == [
            "cloud.honeylabs.first",
            "cloud.honeylabs.second",
        ]
        await host.stop()

    asyncio.run(scenario())


@pytest.mark.parametrize("behavior", ["timeout", "invalid", "crash"])
def test_module_failure_is_confined_and_healthy_module_continues(
    tmp_path: Path,
    behavior: str,
) -> None:
    async def scenario() -> None:
        root = tmp_path / "modules"
        broken = _install_module(
            root,
            "cloud.honeylabs.a-broken",
            behavior=behavior,
            timeout=0.05,
        )
        healthy = _install_module(root, "cloud.honeylabs.z-healthy")
        dependent = _install_module(
            root,
            "cloud.honeylabs.b-dependent",
            dependencies=[
                {
                    "module_id": "cloud.honeylabs.a-broken",
                    "minimum_version": "1.0.0",
                }
            ],
        )
        registry = discover_modules([root], approvals=[broken, dependent, healthy])
        telemetry = InMemoryModuleTelemetry()
        host = AgenticModuleHost(
            registry,
            core_version="1.53.0",
            telemetry=telemetry,
        )
        await host.activate("interactive")
        batch = await host.contribute_context(
            budget=ContextPortBudget(max_tokens=100, max_items=5)
        )
        assert [item.module_id for item in batch.contributions] == [
            "cloud.honeylabs.z-healthy"
        ]
        assert host.running_module_ids == ["cloud.honeylabs.z-healthy"]
        failed = [
            item
            for item in telemetry.receipts
            if item.module_id == "cloud.honeylabs.a-broken"
            and item.operation == "context.contribute"
            and item.status == "failed"
        ]
        assert len(failed) == 1
        await host.stop()

    asyncio.run(scenario())


def test_context_inputs_require_explicit_read_permission(tmp_path: Path) -> None:
    async def scenario() -> None:
        root = tmp_path / "modules"
        approval = _install_module(
            root,
            "cloud.honeylabs.write-only",
            context_read=False,
        )
        host = AgenticModuleHost(
            discover_modules([root], approvals=[approval]),
            core_version="1.53.0",
        )
        await host.activate("interactive")
        result = await host.contribute_context(
            budget=ContextPortBudget(max_tokens=100, max_items=3),
            inputs=[
                ContextInputBlock(
                    block_id="private-input",
                    block_type="turn.message",
                    content={"text": "must not cross the port"},
                )
            ],
        )
        assert result.contributions[0].contribution.content["input_count"] == 0
        await host.stop()

    asyncio.run(scenario())


def test_disabling_module_restores_empty_core_behavior(tmp_path: Path) -> None:
    async def scenario() -> None:
        root = tmp_path / "modules"
        approval = _install_module(root, "cloud.honeylabs.fixture")
        host = AgenticModuleHost(
            discover_modules([root], approvals=[approval]),
            core_version="1.53.0",
        )
        await host.activate("interactive")
        assert (
            await host.contribute_context(
                budget=ContextPortBudget(max_tokens=100, max_items=3)
            )
        ).contributions
        plan = await host.disable("cloud.honeylabs.fixture")
        assert plan is not None
        assert plan.ordered_active_modules == []
        result = await host.contribute_context(
            budget=ContextPortBudget(max_tokens=100, max_items=3)
        )
        assert result.contributions == []
        await host.stop()

    asyncio.run(scenario())


def test_repository_telemetry_persists_trace_and_event(
    tmp_path: Path,
    db_engine,
) -> None:
    init_db(db_engine)

    async def scenario(session_id: str, turn_id: str) -> None:
        root = tmp_path / "modules"
        approval = _install_module(root, "cloud.honeylabs.fixture")
        host = AgenticModuleHost(
            discover_modules([root], approvals=[approval]),
            core_version="1.53.0",
            telemetry=RepositoryModuleTelemetry(db_engine),
        )
        await host.activate(
            "interactive",
            session_id=session_id,
            turn_id=turn_id,
        )
        result = await host.contribute_context(
            budget=ContextPortBudget(max_tokens=100, max_items=3),
            session_id=session_id,
            turn_id=turn_id,
        )
        assert result.receipts[0].trace_id is not None
        assert result.receipts[0].event_id is not None
        await host.stop()

    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(db, title="Module telemetry")
        turn = repositories.create_turn(db, session_id=chat_session.id)
        session_id = chat_session.id
        turn_id = turn.id
    asyncio.run(scenario(session_id, turn_id))
    with Session(db_engine) as db:
        traces = repositories.list_traces_for_turn(db, turn_id=turn_id)
        events = repositories.list_events_for_turn(db, turn_id=turn_id)
    trace_kinds = [item.kind for item in traces]
    event_types = [item.type for item in events]
    assert "agentic_module.lifecycle.discover" in trace_kinds
    assert "agentic_module.lifecycle.validate" in trace_kinds
    assert "agentic_module.lifecycle.start" in trace_kinds
    assert "agentic_module.health" in trace_kinds
    assert trace_kinds.count("agentic_module.context.contribute") == 2
    assert "agentic_module.context.contribute.started" in event_types
    assert "agentic_module.context.contribute.succeeded" in event_types
