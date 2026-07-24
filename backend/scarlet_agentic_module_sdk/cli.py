"""Command-line interface for Agentic Module development and conformance."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Sequence

from scarlet_agentic_module_sdk.conformance import run_conformance, validate_manifest
from scarlet_agentic_module_sdk.scaffold import scaffold_module
from scarlet_agentic_module_sdk.schema import contract_schemas


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.operation == "scaffold":
        destination = scaffold_module(
            Path(args.target),
            module_id=args.module_id,
            display_name=args.display_name,
            minimum_core_version=args.minimum_core_version,
        )
        print(json.dumps({"ok": True, "module_directory": str(destination)}))
        return 0
    if args.operation == "validate":
        manifest, diagnostics = validate_manifest(Path(args.module_directory))
        payload = {
            "ok": manifest is not None
            and not any(item.status == "failed" for item in diagnostics),
            "module_id": manifest.module_id if manifest is not None else None,
            "diagnostics": [item.model_dump(mode="json") for item in diagnostics],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["ok"] else 1
    if args.operation == "conformance":
        report = asyncio.run(
            run_conformance(
                Path(args.module_directory),
                core_version=args.core_version,
                active_mode_tag=args.mode,
            )
        )
        print(report.model_dump_json(indent=2))
        return 0 if report.ok else 1
    if args.operation == "schema":
        output = Path(args.output).expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        for filename, schema in contract_schemas().items():
            (output / filename).write_text(
                json.dumps(schema, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        print(json.dumps({"ok": True, "output": str(output)}))
        return 0
    parser.error("unknown operation")
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scarlet-agentic-module")
    commands = parser.add_subparsers(dest="operation", required=True)

    scaffold = commands.add_parser("scaffold", help="create a conformance fixture")
    scaffold.add_argument("target")
    scaffold.add_argument("--module-id", required=True)
    scaffold.add_argument("--display-name")
    scaffold.add_argument("--minimum-core-version", default="1.53.0")

    validate = commands.add_parser("validate", help="validate one module manifest")
    validate.add_argument("module_directory")

    conformance = commands.add_parser(
        "conformance", help="exercise lifecycle and declared ports"
    )
    conformance.add_argument("module_directory")
    conformance.add_argument("--core-version", default="1.56.1")
    conformance.add_argument("--mode", default="interactive")

    schema = commands.add_parser("schema", help="export versioned JSON Schemas")
    schema.add_argument("--output", required=True)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
