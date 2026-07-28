"""Legacy memory-fact audit helpers.

The first fact pipeline inferred propositions from memory types, tags, and
phrases. Those records remain readable for migration and provenance audits, but
they are not active semantic evidence. New facts require an explicit semantic
authority marker supplied by a future Scarlet-owned confirmation path.
"""

import json
import re
import unicodedata
from typing import Any

from app.storage.models import MemoryFact


PREDICATE_ALIASES = {
    "answer_format": "response_format",
    "formato-risposta": "response_format",
    "formato_risposta": "response_format",
    "response-format": "response_format",
}

KNOWN_ENTITY_ALIASES = {
    "protocollo-zero-luce": {
        "protocollo zero luce",
        "protocollo zero-luce",
        "zero luce",
        "zero-luce",
        "zero light",
        "zero light protocol",
        "zero-light",
        "zeroluce",
    },
    "sal-updates": {
        "aggiornamento sal",
        "sal",
        "sal report",
        "sal summary",
        "sal updates",
        "status update",
        "status updates",
    },
}


def canonicalize_entity(value: str | None) -> str | None:
    """Normalize an explicit legacy-fact query without inferring a new fact."""

    if not value:
        return None
    normalized = normalize_text(value)
    for canonical, aliases in KNOWN_ENTITY_ALIASES.items():
        if normalized == canonical.replace("-", " ") or normalized in aliases:
            return canonical
    return slugify(normalized)


def canonicalize_predicate(value: str | None) -> str | None:
    """Normalize an explicit legacy-fact predicate query."""

    if not value:
        return None
    normalized = slugify(value)
    return PREDICATE_ALIASES.get(normalized, normalized)


def fact_is_authoritative(fact: MemoryFact) -> bool:
    metadata = fact.metadata_json or {}
    return (
        metadata.get("semantic_authority") == "scarlet"
        and metadata.get("semantic_status") == "confirmed"
    )


def fact_search_text(facts: list[MemoryFact]) -> str:
    """Return search text only for explicitly confirmed future propositions."""

    parts: list[str] = []
    for fact in facts:
        if not fact_is_authoritative(fact):
            continue
        parts.extend([fact.entity, fact.predicate])
        aliases = fact.metadata_json.get("aliases")
        if isinstance(aliases, list):
            parts.extend(str(alias) for alias in aliases)
        parts.append(json.dumps(fact.value_json, ensure_ascii=True, sort_keys=True))
    return " ".join(parts)


def fact_payload(fact: MemoryFact) -> dict[str, Any]:
    authoritative = fact_is_authoritative(fact)
    return {
        "id": fact.id,
        "memory_id": fact.memory_id,
        "entity": fact.entity,
        "predicate": fact.predicate,
        "value": fact.value_json,
        "status": fact.status,
        "confidence": fact.confidence,
        "salience": fact.salience,
        "source_trace_id": fact.source_trace_id,
        "source_session_id": fact.source_session_id,
        "source_turn_id": fact.source_turn_id,
        "supersedes_fact_id": fact.supersedes_fact_id,
        "superseded_by_fact_id": fact.superseded_by_fact_id,
        "metadata": fact.metadata_json,
        "semantic_status": (
            "confirmed_proposition"
            if authoritative
            else "legacy_heuristic_proposition"
        ),
        "authoritative": authoritative,
        "valid_from": _isoformat(fact.valid_from),
        "valid_to": _isoformat(fact.valid_to),
        "recorded_at": _isoformat(fact.recorded_at),
    }


def slugify(value: str) -> str:
    normalized = normalize_text(value)
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def normalize_text(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return " ".join(ascii_value.casefold().replace("-", " ").split())


def _isoformat(value: Any) -> str | None:
    if value is None:
        return None
    return value.isoformat()
