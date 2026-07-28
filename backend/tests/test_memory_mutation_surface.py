from app.mind import memory
from app.mind import memory_lifecycle
from app.mind import memory_proposals
from app.mind import memory_relations
from app.mind import memory_write


def test_memory_facade_reexports_mutation_owners() -> None:
    expected = {
        "MemoryWriteBody": memory_write.MemoryWriteBody,
        "MemoryFactsBackfillBody": memory_write.MemoryFactsBackfillBody,
        "handle_memory_write": memory_write.handle_memory_write,
        "handle_memory_facts_backfill": memory_write.handle_memory_facts_backfill,
        "MemoryDeprecateBody": memory_lifecycle.MemoryDeprecateBody,
        "MemorySupersedeBody": memory_lifecycle.MemorySupersedeBody,
        "handle_memory_deprecate": memory_lifecycle.handle_memory_deprecate,
        "handle_memory_supersede": memory_lifecycle.handle_memory_supersede,
        "handle_memory_conflicts": memory_relations.handle_memory_conflicts,
        "create_memory_proposal_from_review_candidate": (
            memory_proposals.create_memory_proposal_from_review_candidate
        ),
        "memory_proposal_payload": memory_proposals.memory_proposal_payload,
    }

    for name, owner in expected.items():
        assert getattr(memory, name) is owner
