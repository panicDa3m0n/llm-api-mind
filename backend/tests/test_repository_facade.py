from app.storage import repositories
from app.storage.repository import memory, organs, retrieval, runtime, sessions


def test_legacy_repository_facade_reexports_domain_operations() -> None:
    """Existing callers keep one stable import while implementations are split."""

    assert repositories.create_chat_session is sessions.create_chat_session
    assert repositories.add_event is runtime.add_event
    assert repositories.create_focus_record is organs.create_focus_record
    assert repositories.add_memory is memory.add_memory
    assert repositories.upsert_memory_surface is retrieval.upsert_memory_surface
    assert repositories.ACTIVE_FOCUS_STATUSES == organs.ACTIVE_FOCUS_STATUSES
    assert (
        repositories.RESOLVED_MEMORY_PROPOSAL_STATUSES
        == memory.RESOLVED_MEMORY_PROPOSAL_STATUSES
    )
