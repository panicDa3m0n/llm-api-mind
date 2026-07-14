"""Read-only database-role preflight for deploy and evaluation procedures."""

from __future__ import annotations

import argparse
import json

from app.config import Settings
from app.storage.database_boundary import database_preflight_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expect-role",
        choices=("production", "laboratory", "test", "preliminary"),
        help="Fail unless the resolved runtime database role matches this value.",
    )
    parser.add_argument(
        "--require-existing",
        action="store_true",
        help="Fail when the selected SQLite database does not exist yet.",
    )
    args = parser.parse_args()

    report = database_preflight_report(Settings())
    if args.expect_role and report["role"] != args.expect_role:
        raise SystemExit(
            f"Expected database role {args.expect_role!r}, received {report['role']!r}."
        )
    database = report.get("database", {})
    if args.require_existing and database.get("kind") == "sqlite" and not database.get(
        "exists", False
    ):
        raise SystemExit("Selected SQLite database does not exist.")

    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
