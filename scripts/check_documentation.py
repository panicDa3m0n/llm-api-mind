#!/usr/bin/env python3
"""Validate canonical Markdown links, file references, and record identifiers."""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\((?P<target>[^)]+)\)")
CODE_SPAN = re.compile(r"`(?P<content>[^`\n]+)`")
REPOSITORY_PATH = re.compile(
    r"(?P<path>"
    r"(?:docs|backend|frontend|scripts)/[A-Za-z0-9_.\-/]+"
    r"|(?:AGENTS|README|CHANGELOG)\.md"
    r")"
)
IDENTIFIER = re.compile(r"^##\s+(?P<id>(?:ADR|BUG|EXP)-\d+)\b", re.MULTILINE)
IDENTIFIER_FILES = (
    Path("docs/decisions.md"),
    Path("docs/bug-ledger.md"),
    Path("docs/experiments.md"),
)
SKIPPED_PARTS = {".git", ".venv", "node_modules", "dist", "build"}
SKIPPED_PATH_TOKENS = {"*", "<", ">", "{", "}"}
HISTORICAL_REFERENCE_PREFIXES = (
    "backend/app/evals/runs/",
    "backend/app/mind/cognition.py",
    "backend/app/mind/hybrid_retrieval.py",
    "backend/app/providers/minimax.py",
)


def markdown_files() -> list[Path]:
    roots = [ROOT / "AGENTS.md", ROOT / "README.md", ROOT / "CHANGELOG.md"]
    roots.extend((ROOT / "docs").rglob("*.md"))
    return sorted(
        path
        for path in roots
        if path.is_file() and not any(part in SKIPPED_PARTS for part in path.parts)
    )


def local_link_target(document: Path, raw_target: str) -> Path | None:
    target = unquote(raw_target.strip().strip("<>"))
    if not target or target.startswith(("#", "http://", "https://", "mailto:")):
        return None
    target = target.split("#", 1)[0]
    if not target:
        return None
    return (document.parent / target).resolve()


def repository_reference(raw_path: str) -> Path | None:
    candidate = raw_path.rstrip(".,:;")
    candidate = candidate.split("#", 1)[0]
    if not candidate or any(token in candidate for token in SKIPPED_PATH_TOKENS):
        return None
    if any(part in SKIPPED_PARTS for part in Path(candidate).parts):
        return None
    if candidate.startswith(HISTORICAL_REFERENCE_PREFIXES):
        return None
    if candidate.endswith((".env", ".db", ".sqlite", ".sqlite3")):
        return None
    return (ROOT / candidate).resolve()


def validate_paths() -> tuple[list[str], int, int]:
    errors: list[str] = []
    link_count = 0
    reference_count = 0
    for document in markdown_files():
        text = document.read_text(encoding="utf-8")
        relative_document = document.relative_to(ROOT)
        for match in MARKDOWN_LINK.finditer(text):
            target = local_link_target(document, match.group("target"))
            if target is None:
                continue
            link_count += 1
            if not target.exists():
                errors.append(
                    f"{relative_document}: missing Markdown target "
                    f"{match.group('target')}"
                )
        for span in CODE_SPAN.finditer(text):
            if span.group("content").startswith(("http://", "https://")):
                continue
            for match in REPOSITORY_PATH.finditer(span.group("content")):
                target = repository_reference(match.group("path"))
                if target is None:
                    continue
                reference_count += 1
                if not target.exists():
                    errors.append(
                        f"{relative_document}: missing repository reference "
                        f"{match.group('path')}"
                    )
    return errors, link_count, reference_count


def validate_identifiers() -> tuple[list[str], int]:
    errors: list[str] = []
    identifiers: list[str] = []
    for relative_path in IDENTIFIER_FILES:
        path = ROOT / relative_path
        if not path.exists():
            errors.append(f"{relative_path}: canonical identifier file is missing")
            continue
        identifiers.extend(IDENTIFIER.findall(path.read_text(encoding="utf-8")))
    duplicates = sorted(
        identifier for identifier, count in Counter(identifiers).items() if count > 1
    )
    for identifier in duplicates:
        errors.append(f"duplicate canonical identifier: {identifier}")
    return errors, len(identifiers)


def main() -> int:
    path_errors, link_count, reference_count = validate_paths()
    identifier_errors, identifier_count = validate_identifiers()
    errors = path_errors + identifier_errors
    if errors:
        for error in errors:
            print(f"documentation error: {error}", file=sys.stderr)
        print(f"documentation integrity failed with {len(errors)} error(s)")
        return 1
    print(
        "documentation integrity passed: "
        f"{len(markdown_files())} files, {link_count} local links, "
        f"{reference_count} repository references, "
        f"{identifier_count} canonical identifiers"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
