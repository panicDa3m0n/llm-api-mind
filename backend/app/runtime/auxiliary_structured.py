"""Shared parsing and one-repair lifecycle for auxiliary structured calls."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import ValidationError

from app.llm.provider import LLMProvider, LLMTextResult


StructuredResult = TypeVar("StructuredResult")


def run_auxiliary_structured_call(
    *,
    provider: LLMProvider,
    prompt: str,
    system: str,
    max_tokens: int,
    schema_name: str,
    parser: Callable[[Any], StructuredResult],
    repair_system: str,
) -> tuple[LLMTextResult, StructuredResult | None, LLMTextResult | None]:
    """Call an auxiliary model and make one source-preserving JSON repair.

    The caller owns the task prompt, schema, model selection, trace, and the
    meaning of the parsed object. This helper owns only the repeated provider
    protocol: one generation, fenced-JSON parsing, then one repair attempt.
    """

    result = provider.generate_text(
        prompt=prompt,
        system=system,
        max_tokens=max_tokens,
    )
    parsed = parse_structured_json(result.text, parser)
    repaired: LLMTextResult | None = None
    if parsed is None:
        repaired = provider.generate_text(
            prompt=structured_repair_prompt(
                malformed=result.text,
                schema_name=schema_name,
            ),
            system=repair_system,
            max_tokens=max_tokens,
        )
        parsed = parse_structured_json(repaired.text, parser)
    return result, parsed, repaired


def parse_structured_json(
    text: str,
    parser: Callable[[Any], StructuredResult],
) -> StructuredResult | None:
    """Parse a JSON object, accepting one common fenced-code wrapper."""

    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        return parser(json.loads(cleaned))
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
        return None


def structured_repair_prompt(*, malformed: str, schema_name: str) -> str:
    """Return the existing schema-labelled repair envelope verbatim in shape."""

    return json.dumps(
        {
            "schema": schema_name,
            "malformed_output": malformed,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
