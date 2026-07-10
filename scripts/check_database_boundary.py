"""Refuse accidental Git staging of the mutable laboratory SQLite snapshot."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


LABORATORY_SNAPSHOT = "backend/data/app.db"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument(
        "--staged",
        action="store_true",
        help="Inspect staged commit contents (the default).",
    )
    scope.add_argument(
        "--working-tree",
        action="store_true",
        help="Inspect unstaged changes instead of the staged commit contents.",
    )
    parser.add_argument(
        "--allow-laboratory-snapshot",
        action="store_true",
        help="Acknowledge an intentional, separately reviewed laboratory data release.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    command = ["git", "diff", "--name-only"]
    if not args.working_tree:
        command.append("--cached")
    completed = subprocess.run(
        command,
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    changed_paths = set(completed.stdout.splitlines())
    if LABORATORY_SNAPSHOT not in changed_paths:
        print("Database boundary check passed: no laboratory snapshot is selected.")
        return 0
    if args.allow_laboratory_snapshot:
        print("Laboratory snapshot explicitly acknowledged for this data release.")
        return 0
    scope = "working tree" if args.working_tree else "staged change"
    raise SystemExit(
        f"Refusing {scope} to {LABORATORY_SNAPSHOT}. Keep mutable laboratory data "
        "out of code commits, or rerun only for an explicitly reviewed data release "
        "with --allow-laboratory-snapshot."
    )


if __name__ == "__main__":
    raise SystemExit(main())
