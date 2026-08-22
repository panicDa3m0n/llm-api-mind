"""Deterministic validation and activation planning for Agentic Modules."""

from __future__ import annotations

from collections import deque
from typing import Literal

from pydantic import Field

from app.agentic_modules.support import duplicate_values
from scarlet_agentic_module_sdk.contracts import (
    DEFAULT_CORE_MODULE_CONTRACTS,
    AgenticModuleManifest,
    ContractModel,
    validate_semver,
)
from app.mind.agent_modes import AGENT_MODE_VALUES


class ModuleDiagnostic(ContractModel):
    severity: Literal["error", "warning"]
    code: str
    message: str
    module_id: str | None = None
    dependency_id: str | None = None


class ModuleActivationState(ContractModel):
    module_id: str
    status: Literal["active", "inactive", "blocked"]
    reasons: list[str] = Field(default_factory=list)


class ModuleActivationPlan(ContractModel):
    core_version: str
    available_contracts: dict[str, str]
    active_mode_tag: str
    known_mode_tags: list[str]
    registry_valid: bool
    ordered_active_modules: list[str]
    states: list[ModuleActivationState]
    diagnostics: list[ModuleDiagnostic]


def build_activation_plan(
    manifests: list[AgenticModuleManifest],
    *,
    core_version: str,
    active_mode_tag: str,
    known_mode_tags: tuple[str, ...] = AGENT_MODE_VALUES,
    available_contracts: dict[str, str] | None = None,
) -> ModuleActivationPlan:
    """Validate a module set and select modules for one agent-mode tag.

    Invalid modules fail closed without preventing unrelated valid modules from
    being planned. Required dependencies participate in ordering and blocking;
    absent optional dependencies produce warnings only.
    """

    validate_semver(core_version)
    contracts = dict(
        DEFAULT_CORE_MODULE_CONTRACTS
        if available_contracts is None
        else available_contracts
    )
    known_tags = tuple(dict.fromkeys(known_mode_tags))
    diagnostics: list[ModuleDiagnostic] = []
    blocked: dict[str, list[str]] = {}
    manifest_order = [manifest.module_id for manifest in manifests]

    duplicates = duplicate_values(manifest_order)
    for module_id in sorted(duplicates):
        _block(
            blocked,
            diagnostics,
            module_id=module_id,
            code="module.duplicate_id",
            message=f"Module id {module_id!r} is declared more than once.",
        )

    by_id = {manifest.module_id: manifest for manifest in manifests}
    known_tag_set = set(known_tags)
    if active_mode_tag not in known_tag_set:
        diagnostics.append(
            ModuleDiagnostic(
                severity="error",
                code="mode.unknown_active_tag",
                message=f"Active agent-mode tag {active_mode_tag!r} is not registered.",
            )
        )

    for manifest in manifests:
        unknown_tags = sorted(set(manifest.mode_tags) - known_tag_set)
        if unknown_tags:
            _block(
                blocked,
                diagnostics,
                module_id=manifest.module_id,
                code="module.unknown_mode_tag",
                message=f"Unknown agent-mode tags: {', '.join(unknown_tags)}.",
            )
        if not manifest.core_compatibility.supports(core_version):
            _block(
                blocked,
                diagnostics,
                module_id=manifest.module_id,
                code="module.core_incompatible",
                message=(
                    f"Module {manifest.module_version} does not support Core "
                    f"{core_version}."
                ),
            )
        for (
            contract_name,
            required_version,
        ) in manifest.core_compatibility.required_contracts.items():
            available_version = contracts.get(contract_name)
            if available_version != required_version:
                _block(
                    blocked,
                    diagnostics,
                    module_id=manifest.module_id,
                    code="module.contract_incompatible",
                    message=(
                        f"Contract {contract_name!r} requires {required_version!r}; "
                        f"Core provides {available_version!r}."
                    ),
                )

        for dependency in manifest.dependencies:
            target = by_id.get(dependency.module_id)
            if target is None:
                severity: Literal["error", "warning"] = (
                    "warning" if dependency.optional else "error"
                )
                diagnostics.append(
                    ModuleDiagnostic(
                        severity=severity,
                        code=(
                            "dependency.missing_optional"
                            if dependency.optional
                            else "dependency.missing_required"
                        ),
                        module_id=manifest.module_id,
                        dependency_id=dependency.module_id,
                        message=f"Dependency {dependency.module_id!r} is not installed.",
                    )
                )
                if not dependency.optional:
                    blocked.setdefault(manifest.module_id, []).append(
                        "dependency.missing_required"
                    )
                continue
            if not dependency.accepts(target.module_version):
                severity = "warning" if dependency.optional else "error"
                diagnostics.append(
                    ModuleDiagnostic(
                        severity=severity,
                        code=(
                            "dependency.optional_version_incompatible"
                            if dependency.optional
                            else "dependency.required_version_incompatible"
                        ),
                        module_id=manifest.module_id,
                        dependency_id=dependency.module_id,
                        message=(
                            f"Installed dependency version {target.module_version} is "
                            "outside the declared range."
                        ),
                    )
                )
                if not dependency.optional:
                    blocked.setdefault(manifest.module_id, []).append(
                        "dependency.required_version_incompatible"
                    )

    required_graph = {
        manifest.module_id: [
            dependency.module_id
            for dependency in manifest.dependencies
            if not dependency.optional and dependency.module_id in by_id
        ]
        for manifest in manifests
    }
    cycle_members = _cycle_members(required_graph)
    for module_id in sorted(cycle_members):
        _block(
            blocked,
            diagnostics,
            module_id=module_id,
            code="dependency.required_cycle",
            message="Module participates in a required-dependency cycle.",
        )

    eligible = {
        manifest.module_id
        for manifest in manifests
        if active_mode_tag in manifest.mode_tags
    }
    for manifest in manifests:
        if manifest.module_id not in eligible:
            continue
        for dependency in manifest.dependencies:
            if dependency.optional or dependency.module_id not in by_id:
                continue
            if active_mode_tag not in by_id[dependency.module_id].mode_tags:
                _block(
                    blocked,
                    diagnostics,
                    module_id=manifest.module_id,
                    dependency_id=dependency.module_id,
                    code="dependency.inactive_for_mode",
                    message=(
                        f"Required dependency {dependency.module_id!r} is not enabled "
                        f"for agent mode {active_mode_tag!r}."
                    ),
                )

    changed = True
    while changed:
        changed = False
        for module_id in manifest_order:
            if module_id not in eligible or module_id in blocked:
                continue
            for dependency_id in required_graph.get(module_id, []):
                if dependency_id in blocked:
                    _block(
                        blocked,
                        diagnostics,
                        module_id=module_id,
                        dependency_id=dependency_id,
                        code="dependency.required_blocked",
                        message=f"Required dependency {dependency_id!r} is blocked.",
                    )
                    changed = True
                    break

    active = [
        module_id
        for module_id in manifest_order
        if module_id in eligible and module_id not in blocked
    ]
    ordered_active = _topological_order(active, required_graph, manifest_order)
    states = []
    for module_id in dict.fromkeys(manifest_order):
        if module_id in blocked:
            states.append(
                ModuleActivationState(
                    module_id=module_id,
                    status="blocked",
                    reasons=list(dict.fromkeys(blocked[module_id])),
                )
            )
        elif module_id in eligible and active_mode_tag in known_tag_set:
            states.append(ModuleActivationState(module_id=module_id, status="active"))
        else:
            states.append(
                ModuleActivationState(
                    module_id=module_id,
                    status="inactive",
                    reasons=["mode.not_selected"],
                )
            )

    return ModuleActivationPlan(
        core_version=core_version,
        available_contracts=contracts,
        active_mode_tag=active_mode_tag,
        known_mode_tags=list(known_tags),
        registry_valid=not any(item.severity == "error" for item in diagnostics),
        ordered_active_modules=(
            ordered_active if active_mode_tag in known_tag_set else []
        ),
        states=states,
        diagnostics=diagnostics,
    )


def _block(
    blocked: dict[str, list[str]],
    diagnostics: list[ModuleDiagnostic],
    *,
    module_id: str,
    code: str,
    message: str,
    dependency_id: str | None = None,
) -> None:
    reasons = blocked.setdefault(module_id, [])
    if code in reasons:
        return
    reasons.append(code)
    diagnostics.append(
        ModuleDiagnostic(
            severity="error",
            code=code,
            module_id=module_id,
            dependency_id=dependency_id,
            message=message,
        )
    )


def _cycle_members(graph: dict[str, list[str]]) -> set[str]:
    state: dict[str, int] = {}
    stack: list[str] = []
    stack_index: dict[str, int] = {}
    members: set[str] = set()

    def visit(node: str) -> None:
        state[node] = 1
        stack_index[node] = len(stack)
        stack.append(node)
        for dependency in graph.get(node, []):
            if dependency not in graph:
                continue
            dependency_state = state.get(dependency, 0)
            if dependency_state == 0:
                visit(dependency)
            elif dependency_state == 1:
                members.update(stack[stack_index[dependency] :])
        stack.pop()
        stack_index.pop(node, None)
        state[node] = 2

    for node in graph:
        if state.get(node, 0) == 0:
            visit(node)
    return members


def _topological_order(
    active: list[str],
    graph: dict[str, list[str]],
    manifest_order: list[str],
) -> list[str]:
    active_set = set(active)
    indegree = {module_id: 0 for module_id in active}
    dependents: dict[str, list[str]] = {module_id: [] for module_id in active}
    for module_id in active:
        for dependency_id in graph.get(module_id, []):
            if dependency_id not in active_set:
                continue
            indegree[module_id] += 1
            dependents[dependency_id].append(module_id)

    order_index = {module_id: index for index, module_id in enumerate(manifest_order)}
    queue = deque(
        sorted(
            (module_id for module_id, degree in indegree.items() if degree == 0),
            key=order_index.__getitem__,
        )
    )
    result: list[str] = []
    while queue:
        module_id = queue.popleft()
        result.append(module_id)
        for dependent in sorted(dependents[module_id], key=order_index.__getitem__):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                queue.append(dependent)
    return result
