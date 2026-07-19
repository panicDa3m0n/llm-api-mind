"""Versioned JSON Schema export for public Agentic Module contracts."""

from __future__ import annotations

from typing import Any

from scarlet_agentic_module_sdk.contracts import (
    AgenticModuleManifest,
    CommandPortRequest,
    CommandPortResult,
    ContextPortRequest,
    ContextPortResult,
    EventPortRequest,
    EventPortResult,
    HealthPortRequest,
    HealthPortResult,
    PromptPortRequest,
    PromptPortResult,
)


def contract_schemas() -> dict[str, dict[str, Any]]:
    """Return every public manifest and Port V1 schema by stable filename."""

    models = {
        "agentic-module-manifest-v1.schema.json": AgenticModuleManifest,
        "command-port-request-v1.schema.json": CommandPortRequest,
        "command-port-result-v1.schema.json": CommandPortResult,
        "context-port-request-v1.schema.json": ContextPortRequest,
        "context-port-result-v1.schema.json": ContextPortResult,
        "event-port-request-v1.schema.json": EventPortRequest,
        "event-port-result-v1.schema.json": EventPortResult,
        "health-port-request-v1.schema.json": HealthPortRequest,
        "health-port-result-v1.schema.json": HealthPortResult,
        "prompt-port-request-v1.schema.json": PromptPortRequest,
        "prompt-port-result-v1.schema.json": PromptPortResult,
    }
    return {name: model.model_json_schema() for name, model in models.items()}
