"""Deterministic discovery for operator-approved Agentic Modules."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from scarlet_agentic_module_sdk.contracts import AgenticModuleManifest, ContractModel


MODULE_MANIFEST_FILENAME = "agentic-module.json"
MAX_MANIFEST_BYTES = 1_000_000


class RegistryDiagnostic(ContractModel):
    severity: Literal["error", "warning"]
    code: str
    message: str
    manifest_path: str | None = None
    module_id: str | None = None


@dataclass(frozen=True)
class ApprovedModule:
    """Operator approval pinned to one exact manifest document."""

    module_id: str
    manifest_sha256: str


@dataclass(frozen=True)
class RegisteredModule:
    manifest: AgenticModuleManifest
    module_directory: Path
    manifest_path: Path
    manifest_sha256: str


@dataclass(frozen=True)
class ModuleRegistry:
    modules: tuple[RegisteredModule, ...]
    diagnostics: tuple[RegistryDiagnostic, ...]

    @property
    def manifests(self) -> list[AgenticModuleManifest]:
        return [item.manifest for item in self.modules]

    def get(self, module_id: str) -> RegisteredModule | None:
        return next(
            (item for item in self.modules if item.manifest.module_id == module_id),
            None,
        )


def discover_modules(
    roots: list[Path],
    *,
    approvals: list[ApprovedModule],
) -> ModuleRegistry:
    """Discover direct child installs under approved roots without executing code."""

    diagnostics: list[RegistryDiagnostic] = []
    duplicate_approvals = _duplicates([item.module_id for item in approvals])
    approval_map = {
        item.module_id: item
        for item in approvals
        if item.module_id not in duplicate_approvals
    }
    for module_id in sorted(duplicate_approvals):
        diagnostics.append(
            RegistryDiagnostic(
                severity="error",
                code="registry.duplicate_approval",
                message=f"Module id has more than one operator approval: {module_id}",
                module_id=module_id,
            )
        )
    discovered: list[RegisteredModule] = []
    candidates: list[Path] = []

    for raw_root in sorted(roots, key=lambda item: str(item)):
        root = raw_root.expanduser().resolve()
        if not root.is_dir():
            diagnostics.append(
                RegistryDiagnostic(
                    severity="error",
                    code="registry.root_unavailable",
                    message=f"Approved module root is unavailable: {root}",
                    manifest_path=str(root),
                )
            )
            continue
        candidates.extend(sorted(root.glob(f"*/{MODULE_MANIFEST_FILENAME}")))

    for manifest_path in candidates:
        result = _read_candidate(manifest_path, approval_map=approval_map)
        if isinstance(result, RegistryDiagnostic):
            diagnostics.append(result)
        else:
            discovered.append(result)

    duplicate_ids = _duplicates([item.manifest.module_id for item in discovered])
    if duplicate_ids:
        kept: list[RegisteredModule] = []
        for item in discovered:
            module_id = item.manifest.module_id
            if module_id in duplicate_ids:
                diagnostics.append(
                    RegistryDiagnostic(
                        severity="error",
                        code="registry.duplicate_module_id",
                        message=f"Approved module id is installed more than once: {module_id}",
                        manifest_path=str(item.manifest_path),
                        module_id=module_id,
                    )
                )
            else:
                kept.append(item)
        discovered = kept

    discovered.sort(key=lambda item: item.manifest.module_id)
    diagnostics.sort(
        key=lambda item: (
            item.module_id or "",
            item.manifest_path or "",
            item.code,
        )
    )
    return ModuleRegistry(tuple(discovered), tuple(diagnostics))


def manifest_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_candidate(
    manifest_path: Path,
    *,
    approval_map: dict[str, ApprovedModule],
) -> RegisteredModule | RegistryDiagnostic:
    display_path = str(manifest_path)
    if manifest_path.is_symlink() or manifest_path.parent.is_symlink():
        return RegistryDiagnostic(
            severity="error",
            code="registry.symlink_rejected",
            message="Module directories and manifests must not be symbolic links.",
            manifest_path=display_path,
        )
    try:
        raw = manifest_path.read_bytes()
    except OSError as exc:
        return _diagnostic("registry.manifest_unreadable", str(exc), display_path)
    if len(raw) > MAX_MANIFEST_BYTES:
        return _diagnostic(
            "registry.manifest_too_large",
            f"Manifest exceeds {MAX_MANIFEST_BYTES} bytes.",
            display_path,
        )
    try:
        payload: Any = json.loads(raw)
        manifest = AgenticModuleManifest.model_validate(payload)
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as exc:
        return _diagnostic("registry.manifest_invalid", str(exc), display_path)

    digest = hashlib.sha256(raw).hexdigest()
    approval = approval_map.get(manifest.module_id)
    if approval is None:
        return _diagnostic(
            "registry.module_not_approved",
            "Module id is not present in the operator approval set.",
            display_path,
            manifest.module_id,
        )
    if digest != approval.manifest_sha256:
        return _diagnostic(
            "registry.manifest_digest_mismatch",
            "Manifest bytes do not match the operator-approved SHA-256 digest.",
            display_path,
            manifest.module_id,
        )

    executable_error = _entrypoint_error(
        manifest.runtime.entrypoint[0],
        module_directory=manifest_path.parent.resolve(),
    )
    if executable_error is not None:
        return _diagnostic(
            "registry.entrypoint_invalid",
            executable_error,
            display_path,
            manifest.module_id,
        )
    return RegisteredModule(
        manifest=manifest,
        module_directory=manifest_path.parent.resolve(),
        manifest_path=manifest_path.resolve(),
        manifest_sha256=digest,
    )


def _entrypoint_error(value: str, *, module_directory: Path) -> str | None:
    executable = Path(value)
    resolved = executable if executable.is_absolute() else module_directory / executable
    try:
        resolved = resolved.resolve(strict=True)
    except OSError:
        return f"Entrypoint executable does not exist: {value}"
    if not resolved.is_file():
        return f"Entrypoint executable is not a file: {value}"
    return None


def _diagnostic(
    code: str,
    message: str,
    manifest_path: str,
    module_id: str | None = None,
) -> RegistryDiagnostic:
    return RegistryDiagnostic(
        severity="error",
        code=code,
        message=message,
        manifest_path=manifest_path,
        module_id=module_id,
    )


def _duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates
