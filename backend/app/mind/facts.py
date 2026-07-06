import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.storage.models import MemoryFact, MemoryRecord


CONTROLLED_PREDICATES = {
    "communication_preference",
    "correction",
    "project_decision",
    "response_format",
    "runtime_capability",
    "task_constraint",
    "user_preference",
}

PREDICATE_ALIASES = {
    "answer_format": "response_format",
    "communication": "communication_preference",
    "decision": "project_decision",
    "formato-risposta": "response_format",
    "formato_risposta": "response_format",
    "format": "response_format",
    "preference": "user_preference",
    "preferenza": "user_preference",
    "response-format": "response_format",
    "response_format": "response_format",
}

KNOWN_ENTITY_ALIASES = {
    "protocollo-zero-luce": [
        "protocollo zero luce",
        "protocollo zero-luce",
        "zero luce",
        "zero-luce",
        "zero light",
        "zero light protocol",
        "zero-light",
        "zeroluce",
    ],
    "sal-updates": [
        "aggiornamento sal",
        "sal",
        "sal report",
        "sal summary",
        "sal updates",
        "status update",
        "status updates",
    ],
}

GENERIC_TAGS = {
    "formato",
    "formato-risposta",
    "memory",
    "memoria",
    "preferenza",
    "preferenza-utente",
    "protocol",
    "protocollo",
    "risposta",
    "user-preference",
}

RESPONSE_FORMAT_PHRASES = [
    "answer with",
    "answer using",
    "respond with",
    "respond using",
    "rispondi con",
    "rispondere con",
    "risposta con",
    "formato risposta",
    "formato di risposta",
    "response format",
    "answer format",
]

BLOCK_ALIASES = [
    ("Contesto", ["contesto", "context"]),
    ("Evidenza", ["evidenza", "evidence"]),
    ("Rischio", ["rischio", "risk"]),
    ("Prossima azione", ["prossima azione", "next action", "next step"]),
]


@dataclass(frozen=True)
class ExtractedMemoryFact:
    entity: str
    predicate: str
    value: dict[str, Any]
    confidence: float
    salience: float
    metadata: dict[str, Any]


def extract_memory_facts(memory: MemoryRecord) -> list[ExtractedMemoryFact]:
    entity = canonical_entity_for_memory(memory)
    predicate = canonical_predicate_for_memory(memory)
    if entity is None or predicate is None:
        return []

    aliases = aliases_for_entity(entity, memory)
    value = value_for_predicate(memory, predicate)
    return [
        ExtractedMemoryFact(
            entity=entity,
            predicate=predicate,
            value=value,
            confidence=memory.confidence,
            salience=memory.salience,
            metadata={
                "extractor": "atomic_fact_v0",
                "aliases": aliases,
                "source_memory_type": memory.memory_type,
                "source_tags": memory.tags_json,
            },
        )
    ]


def canonicalize_entity(value: str | None) -> str | None:
    if not value:
        return None
    normalized = normalize_text(value)
    for canonical, aliases in KNOWN_ENTITY_ALIASES.items():
        if normalized == canonical.replace("-", " ") or normalized in aliases:
            return canonical
    if normalized.startswith("protocollo "):
        suffix = normalized.removeprefix("protocollo ").strip()
        if suffix:
            return f"protocollo-{slugify(suffix)}"
    if normalized.startswith("protocol "):
        suffix = normalized.removeprefix("protocol ").strip()
        if suffix:
            return f"protocollo-{slugify(suffix)}"
    return slugify(normalized)


def canonicalize_predicate(value: str | None) -> str | None:
    if not value:
        return None
    normalized = slugify(value)
    return PREDICATE_ALIASES.get(normalized, normalized)


def canonical_entity_for_memory(memory: MemoryRecord) -> str | None:
    metadata = memory.metadata_json or {}
    for key in ("entity", "entity_slug", "subject"):
        value = metadata.get(key)
        if isinstance(value, str):
            return canonicalize_entity(value)

    haystack = normalize_text(_memory_text(memory))
    for canonical, aliases in KNOWN_ENTITY_ALIASES.items():
        if any(_contains_normalized_phrase(haystack, alias) for alias in aliases):
            return canonical

    protocol_match = re.search(
        r"\b(?:protocollo|protocol)\s+([a-z0-9]+(?:\s+[a-z0-9]+)?)",
        haystack,
    )
    if protocol_match:
        return canonicalize_entity(f"protocollo {protocol_match.group(1)}")

    for tag in memory.tags_json:
        normalized = slugify(tag)
        if normalized and normalized not in GENERIC_TAGS:
            return canonicalize_entity(normalized)
    return None


def canonical_predicate_for_memory(memory: MemoryRecord) -> str | None:
    metadata = memory.metadata_json or {}
    value = metadata.get("predicate")
    if isinstance(value, str):
        predicate = canonicalize_predicate(value)
        if predicate in CONTROLLED_PREDICATES:
            return predicate

    tags = {slugify(tag) for tag in memory.tags_json}
    if _has_response_format_signal(memory, tags=tags):
        return "response_format"
    if memory.memory_type == "decision":
        return "project_decision"
    if memory.memory_type == "correction":
        return "correction"
    if memory.memory_type == "task_context":
        return "task_constraint"
    if memory.memory_type == "user_preference":
        return "user_preference"
    if memory.memory_type == "project_fact":
        return "project_decision"
    return None


def value_for_predicate(memory: MemoryRecord, predicate: str) -> dict[str, Any]:
    if predicate == "response_format":
        blocks = _extract_blocks(memory)
        return {
            "kind": "ordered_blocks" if blocks else "text",
            "blocks": blocks,
            "block_count": len(blocks),
            "text": memory.content,
        }
    return {
        "kind": "text",
        "text": memory.content,
    }


def aliases_for_entity(entity: str, memory: MemoryRecord) -> list[str]:
    aliases = list(KNOWN_ENTITY_ALIASES.get(entity, []))
    for tag in memory.tags_json:
        normalized = normalize_text(tag)
        if normalized and normalized not in aliases:
            aliases.append(normalized)
    metadata = memory.metadata_json or {}
    raw_aliases = metadata.get("aliases")
    if isinstance(raw_aliases, list):
        for alias in raw_aliases:
            if isinstance(alias, str):
                normalized = normalize_text(alias)
                if normalized and normalized not in aliases:
                    aliases.append(normalized)
    return aliases[:20]


def fact_search_text(facts: list[MemoryFact]) -> str:
    parts: list[str] = []
    for fact in facts:
        parts.extend([fact.entity, fact.predicate])
        aliases = fact.metadata_json.get("aliases")
        if isinstance(aliases, list):
            parts.extend(str(alias) for alias in aliases)
        parts.append(json.dumps(fact.value_json, ensure_ascii=True, sort_keys=True))
    return " ".join(parts)


def fact_payload(fact: MemoryFact) -> dict[str, Any]:
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
        "valid_from": _isoformat(fact.valid_from),
        "valid_to": _isoformat(fact.valid_to),
        "recorded_at": _isoformat(fact.recorded_at),
    }


def extracted_fact_payload(fact: ExtractedMemoryFact) -> dict[str, Any]:
    return {
        "entity": fact.entity,
        "predicate": fact.predicate,
        "value": fact.value,
        "confidence": fact.confidence,
        "salience": fact.salience,
        "metadata": fact.metadata,
    }


def _extract_blocks(memory: MemoryRecord) -> list[str]:
    metadata = memory.metadata_json or {}
    for key in ("blocchi", "blocks"):
        value = metadata.get(key)
        if isinstance(value, list):
            blocks = [str(item).strip() for item in value if str(item).strip()]
            if blocks:
                return [_canonical_block_label(block) for block in blocks]

    haystack = normalize_text(memory.content)
    positions: list[tuple[int, str]] = []
    seen: set[str] = set()
    for canonical, aliases in BLOCK_ALIASES:
        for alias in aliases:
            index = haystack.find(alias)
            if index >= 0 and canonical not in seen:
                positions.append((index, canonical))
                seen.add(canonical)
                break
    return [label for _, label in sorted(positions)]


def _has_response_format_signal(memory: MemoryRecord, *, tags: set[str]) -> bool:
    metadata = memory.metadata_json or {}
    for key in ("blocchi", "blocks"):
        value = metadata.get(key)
        if isinstance(value, list) and any(str(item).strip() for item in value):
            return True
    if tags & {"formato-risposta", "response-format"}:
        return True

    haystack = normalize_text(_memory_text(memory))
    if any(_contains_normalized_phrase(haystack, phrase) for phrase in RESPONSE_FORMAT_PHRASES):
        return True
    tokens = set(haystack.split())
    return "blocchi" in tokens or "blocks" in tokens


def _canonical_block_label(value: str) -> str:
    normalized = normalize_text(value)
    for canonical, aliases in BLOCK_ALIASES:
        if normalized == normalize_text(canonical) or normalized in aliases:
            return canonical
    return value.strip()


def _memory_text(memory: MemoryRecord) -> str:
    metadata = memory.metadata_json or {}
    metadata_text = json.dumps(metadata, ensure_ascii=True, sort_keys=True)
    return " ".join(
        item
        for item in [
            memory.content,
            memory.reason_for_storage,
            memory.expected_future_use or "",
            memory.memory_type,
            memory.scope,
            " ".join(memory.tags_json),
            metadata_text,
        ]
        if item
    )


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


def _contains_normalized_phrase(haystack: str, phrase: str) -> bool:
    phrase_tokens = normalize_text(phrase).split()
    if not phrase_tokens:
        return False
    haystack_tokens = haystack.split()
    phrase_length = len(phrase_tokens)
    if phrase_length > len(haystack_tokens):
        return False
    for index in range(len(haystack_tokens) - phrase_length + 1):
        if haystack_tokens[index : index + phrase_length] == phrase_tokens:
            return True
    return False


def _isoformat(value: Any) -> str | None:
    if value is None:
        return None
    return value.isoformat()
