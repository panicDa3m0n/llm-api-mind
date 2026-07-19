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

__all__ = [
    "AGENTIC_MODULE_MANIFEST_VERSION",
    "AGENTIC_MODULE_PORT_VERSION",
    "AgenticModuleManifest",
    "ModuleActivationPlan",
    "build_activation_plan",
]
