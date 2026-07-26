"""Validate repository-local Codex skill structure and maintenance contracts."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / ".agents" / "skills"
REQUIRED_SKILLS = {
    "scarlet-cognitive-change",
    "scarlet-e2e-evaluation",
    "scarlet-project-stewardship",
    "scarlet-runtime-debugging",
    "scarlet-vps-android-release",
}
REQUIRED_HEADINGS = {
    "## Authoritative Sources",
    "## Maintenance Contract",
}
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    if not text.startswith("---\n"):
        return {}, ["missing opening YAML frontmatter delimiter"]
    try:
        _, raw_frontmatter, _ = text.split("---\n", 2)
    except ValueError:
        return {}, ["missing closing YAML frontmatter delimiter"]
    fields: dict[str, str] = {}
    for line_number, line in enumerate(raw_frontmatter.splitlines(), start=2):
        if not line.strip():
            continue
        if ":" not in line:
            errors.append(f"frontmatter line {line_number} is not key: value")
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            errors.append(f"frontmatter line {line_number} has an empty field")
            continue
        if key in fields:
            errors.append(f"duplicate frontmatter field: {key}")
            continue
        fields[key] = value
    return fields, errors


def validate_skill(path: Path) -> tuple[str | None, list[str]]:
    relative_path = path.relative_to(ROOT)
    text = path.read_text(encoding="utf-8")
    fields, errors = parse_frontmatter(text)
    name = fields.get("name")
    description = fields.get("description")
    if name is None:
        errors.append("missing frontmatter name")
    elif not NAME_PATTERN.fullmatch(name):
        errors.append(f"invalid skill name: {name}")
    elif name != path.parent.name:
        errors.append(
            f"frontmatter name {name} does not match directory {path.parent.name}"
        )
    if description is None:
        errors.append("missing frontmatter description")
    elif len(description) < 40:
        errors.append("description is too short to define useful trigger boundaries")
    for heading in sorted(REQUIRED_HEADINGS):
        if heading not in text:
            errors.append(f"missing required heading: {heading}")
    if "Update this skill" not in text:
        errors.append("maintenance contract must explicitly require skill updates")
    return name, [f"{relative_path}: {error}" for error in errors]


def main() -> int:
    if not SKILLS_ROOT.is_dir():
        print("project skill validation failed: .agents/skills is missing")
        return 1
    skill_paths = sorted(SKILLS_ROOT.glob("*/SKILL.md"))
    errors: list[str] = []
    names: list[str] = []
    for skill_path in skill_paths:
        name, skill_errors = validate_skill(skill_path)
        errors.extend(skill_errors)
        if name is not None:
            names.append(name)
    duplicates = sorted(name for name in set(names) if names.count(name) > 1)
    for name in duplicates:
        errors.append(f"duplicate skill name: {name}")
    missing = sorted(REQUIRED_SKILLS - set(names))
    for name in missing:
        errors.append(f"missing required project skill: {name}")
    if not (SKILLS_ROOT / "README.md").is_file():
        errors.append(".agents/skills/README.md: missing skill index")
    if errors:
        for error in errors:
            print(f"project skill error: {error}", file=sys.stderr)
        print(f"project skill validation failed with {len(errors)} error(s)")
        return 1
    print(
        "project skill validation passed: "
        f"{len(skill_paths)} skills, {len(set(names))} unique names"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
