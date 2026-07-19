"""Public contracts for optional Agentic Modules."""

from app.agentic_modules.contracts import (
    AGENTIC_MODULE_MANIFEST_VERSION,
    AGENTIC_MODULE_PORT_VERSION,
    AgenticModuleManifest,
)
from app.agentic_modules.validation import (
    ModuleActivationPlan,
    build_activation_plan,
)
from app.agentic_modules.host import AgenticModuleHost
from app.agentic_modules.registry import (
    ApprovedModule,
    ModuleRegistry,
    discover_modules,
)

__all__ = [
    "AGENTIC_MODULE_MANIFEST_VERSION",
    "AGENTIC_MODULE_PORT_VERSION",
    "AgenticModuleManifest",
    "AgenticModuleHost",
    "ApprovedModule",
    "ModuleActivationPlan",
    "ModuleRegistry",
    "build_activation_plan",
    "discover_modules",
]
