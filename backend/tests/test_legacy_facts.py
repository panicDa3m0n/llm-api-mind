from datetime import datetime, timezone

from app.mind.facts import fact_payload, fact_search_text
from app.storage.models import MemoryFact


def _fact(*, metadata: dict[str, str]) -> MemoryFact:
    return MemoryFact(
        id="fact_test",
        memory_id="mem_test",
        entity="utente",
        predicate="user_preference",
        value_json={"kind": "text", "text": "Preferisce risposte concise."},
        status="active",
        confidence=0.9,
        salience=0.8,
        metadata_json=metadata,
        recorded_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
    )


def test_legacy_heuristic_fact_is_audit_only() -> None:
    fact = _fact(metadata={"extractor": "atomic_fact_v0"})

    payload = fact_payload(fact)

    assert payload["authoritative"] is False
    assert payload["semantic_status"] == "legacy_heuristic_proposition"
    assert fact_search_text([fact]) == ""


def test_explicit_scarlet_confirmation_can_become_searchable() -> None:
    fact = _fact(
        metadata={
            "semantic_authority": "scarlet",
            "semantic_status": "confirmed",
        }
    )

    payload = fact_payload(fact)

    assert payload["authoritative"] is True
    assert payload["semantic_status"] == "confirmed_proposition"
    assert "user_preference" in fact_search_text([fact])
