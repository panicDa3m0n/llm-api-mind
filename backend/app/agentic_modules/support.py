"""Pure collection helpers shared by module discovery and validation."""

from __future__ import annotations


def duplicate_values(values: list[str]) -> set[str]:
    """Return values that occur more than once, preserving no ordering contract."""

    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates
