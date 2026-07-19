"""Public Python SDK for Scarlet Agentic Modules."""

from scarlet_agentic_module_sdk.client import (
    ModuleClientError,
    ModuleProcessClient,
    PortResponse,
)
from scarlet_agentic_module_sdk.conformance import (
    ConformanceDiagnostic,
    ConformanceReport,
    run_conformance,
    validate_manifest,
)
from scarlet_agentic_module_sdk.contracts import (
    AGENTIC_MODULE_LIFECYCLE_VERSION,
    AGENTIC_MODULE_MANIFEST_VERSION,
    AGENTIC_MODULE_PORT_VERSION,
    AgenticModuleManifest,
    CommandPortRequest,
    CommandPortResult,
    ContextPortRequest,
    ContextPortResult,
    EventPortRequest,
    EventPortResult,
    HealthPortRequest,
    HealthPortResult,
)
from scarlet_agentic_module_sdk.runtime import AgenticModule, ModuleProtocolError, serve
from scarlet_agentic_module_sdk.scaffold import scaffold_module

__all__ = [
    "AGENTIC_MODULE_LIFECYCLE_VERSION",
    "AGENTIC_MODULE_MANIFEST_VERSION",
    "AGENTIC_MODULE_PORT_VERSION",
    "AgenticModule",
    "AgenticModuleManifest",
    "CommandPortRequest",
    "CommandPortResult",
    "ConformanceDiagnostic",
    "ConformanceReport",
    "ContextPortRequest",
    "ContextPortResult",
    "EventPortRequest",
    "EventPortResult",
    "HealthPortRequest",
    "HealthPortResult",
    "ModuleProtocolError",
    "ModuleClientError",
    "ModuleProcessClient",
    "PortResponse",
    "run_conformance",
    "scaffold_module",
    "serve",
    "validate_manifest",
]

__version__ = "1.0.0"
