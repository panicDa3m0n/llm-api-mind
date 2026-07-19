"""Deterministic scaffold for a non-product Agentic Module fixture."""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

from scarlet_agentic_module_sdk.contracts import AgenticModuleManifest


def scaffold_module(
    target: Path,
    *,
    module_id: str,
    display_name: str | None = None,
    minimum_core_version: str = "1.53.0",
) -> Path:
    """Create a complete fixture module in a new or empty directory."""

    destination = target.expanduser().resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f"Scaffold target is not empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    namespace = module_id.replace(".", "_").replace("-", "_")
    block_type = f"{module_id}.observation"
    event_type = f"{module_id}.observed"
    manifest = AgenticModuleManifest.model_validate(
        {
            "module_id": module_id,
            "display_name": display_name or module_id,
            "description": "Generated Agentic Module conformance fixture.",
            "module_version": "0.1.0",
            "core_compatibility": {
                "minimum_core_version": minimum_core_version,
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
                    "produces_block_types": [block_type],
                    "max_contributions": 1,
                },
                {
                    "kind": "prompt",
                    "capability_id": "fixture.prompt",
                    "slots": ["turn_context"],
                    "max_characters": 500,
                },
                {
                    "kind": "command",
                    "capability_id": "fixture.command",
                    "namespace": namespace,
                    "commands": ["echo"],
                },
                {
                    "kind": "event",
                    "capability_id": "fixture.event",
                    "subscribes_to": ["turn.started"],
                    "publishes": [event_type],
                },
            ],
            "permissions": [
                "context.contribute",
                "prompt.contribute",
                "command.register",
                "event.subscribe",
                "event.publish",
            ],
            "runtime": {"entrypoint": ["run-module"]},
            "timeouts": {
                "startup_seconds": 5,
                "call_seconds": 5,
                "health_seconds": 2,
                "shutdown_seconds": 2,
            },
        }
    )
    (destination / "agentic-module.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (destination / "module.py").write_text(
        _module_source(block_type=block_type, event_type=event_type),
        encoding="utf-8",
    )
    launcher = destination / "run-module"
    launcher.write_text(
        f"#!{sys.executable}\nfrom module import main\nmain()\n",
        encoding="utf-8",
    )
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
    (destination / "README.md").write_text(
        _readme(module_id=module_id),
        encoding="utf-8",
    )
    return destination


def _module_source(*, block_type: str, event_type: str) -> str:
    return f'''"""Generated protocol fixture; replace handlers with module behavior."""

from scarlet_agentic_module_sdk import AgenticModule, serve
from scarlet_agentic_module_sdk.contracts import (
    CommandPortResult,
    ContextContribution,
    ContextPortResult,
    EventPortResult,
    ModuleEvent,
    PromptContribution,
    PromptPortResult,
)


class FixtureModule(AgenticModule):
    def contribute_context(self, request, *, capability_id):
        return ContextPortResult(contributions=[ContextContribution(
            contribution_id="fixture-context",
            block_type="{block_type}",
            content={{"source": "generated-fixture"}},
            estimated_tokens=8,
            priority=50,
        )])

    def contribute_prompt(self, request, *, capability_id):
        return PromptPortResult(contributions=[PromptContribution(
            contribution_id="fixture-prompt",
            slot="turn_context",
            text="Generated fixture contribution.",
            priority=50,
        )])

    def invoke_command(self, request, *, capability_id):
        return CommandPortResult(status="success", output={{"echo": request.arguments}})

    def handle_event(self, request, *, capability_id):
        return EventPortResult(publications=[ModuleEvent(
            event_id="fixture-event",
            event_type="{event_type}",
            occurred_at=request.event.occurred_at,
            payload={{"source_event": request.event.event_id}},
        )])


def main():
    serve(FixtureModule())
'''


def _readme(*, module_id: str) -> str:
    return f"""# {module_id}

This directory was generated by the Scarlet Agentic Module SDK. It is a
protocol fixture, not a cognitive product module.

Validate and exercise it with:

```bash
scarlet-agentic-module validate .
scarlet-agentic-module conformance .
```

The Core operator must still review the package and approve the exact manifest
SHA-256 before installation. The SDK does not grant database, provider,
secret, filesystem, or Core-internal access.
"""
