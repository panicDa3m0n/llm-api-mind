from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.mind.contracts import MindAPIContext
from app.mind.shell import MindShellRequest, dispatch_mind_shell
from app.storage import repositories
from app.storage.db import init_db


def _setup_turns(
    db_engine: Engine,
) -> tuple[MindAPIContext, str, str, str]:
    init_db(db_engine)
    with Session(db_engine) as db:
        source_session = repositories.create_chat_session(
            db,
            title="Proposal source",
        )
        source_turn = repositories.create_turn(
            db,
            session_id=source_session.id,
            model="MiniMax-M3",
        )
        source_message = repositories.add_message(
            db,
            session_id=source_session.id,
            turn_id=source_turn.id,
            role="user",
            content="Ricordati che preferisco una tisana senza caffeina la sera.",
        )
        decision_session = repositories.create_chat_session(
            db,
            title="Proposal decision",
        )
        decision_turn = repositories.create_turn(
            db,
            session_id=decision_session.id,
            model="MiniMax-M3",
        )
        source_session_id = source_session.id
        source_turn_id = source_turn.id
        source_message_id = source_message.id
        decision_session_id = decision_session.id
        decision_turn_id = decision_turn.id
    context = MindAPIContext(
        engine=db_engine,
        session_id=decision_session_id,
        turn_id=decision_turn_id,
        settings=Settings(
            app_name="Proposal review test",
            environment="test",
            minimax_api_key="test-key",
        ),
    )
    return context, source_session_id, source_turn_id, source_message_id


def _proposal(
    db_engine: Engine,
    *,
    source_session_id: str,
    source_turn_id: str,
    source_message_id: str,
    key: str,
    content: str,
) -> str:
    with Session(db_engine) as db:
        proposal, _ = repositories.upsert_memory_proposal(
            db,
            idempotency_key=key,
            source="maintenance.memory_review",
            proposed_action="needs_semantic_review",
            action_confidence=0.0,
            risk="medium",
            candidate_type="user_preference",
            candidate_scope="user",
            content=content,
            reason_for_storage="Preferenza personale utile in futuro.",
            expected_future_use="Quando Scarlet propone bevande serali.",
            source_session_id=source_session_id,
            source_turn_id=source_turn_id,
            source_message_ids=[source_message_id],
            decision={
                "reason": "Candidate awaits Scarlet's source-aware judgment."
            },
        )
        repositories.resolve_memory_proposal(
            db,
            proposal_id=proposal.id,
            status="pending_review",
            result={
                "resolution": {
                    "resolver": "llm_proposal_resolution",
                    "decision": {
                        "recommendation": "recommend_create",
                        "semantic_authority": False,
                    },
                }
            },
        )
        return proposal.id


def test_scarlet_accepts_proposal_with_source_and_decision_provenance(
    db_engine: Engine,
) -> None:
    context, source_session_id, source_turn_id, source_message_id = _setup_turns(
        db_engine
    )
    with Session(db_engine) as db:
        source_before = repositories.get_chat_session(db, source_session_id)
        assert source_before is not None
        source_updated_at = source_before.updated_at

    proposal_id = _proposal(
        db_engine,
        source_session_id=source_session_id,
        source_turn_id=source_turn_id,
        source_message_id=source_message_id,
        key="proposal:accept",
        content="L'utente preferisce una tisana senza caffeina la sera.",
    )

    listed = dispatch_mind_shell(
        MindShellRequest(command="memory proposals --status open --limit 10"),
        context=context,
    )
    assert listed.ok is True
    assert [item["id"] for item in listed.result["data"]["proposals"]] == [
        proposal_id
    ]

    opened = dispatch_mind_shell(
        MindShellRequest(command=f"memory proposal {proposal_id}"),
        context=context,
    )
    assert opened.ok is True
    proposal = opened.result["data"]["proposal"]
    assert proposal["source_session_id"] == source_session_id
    assert proposal["source_message_ids"] == [source_message_id]
    assert proposal["maintenance_recommendation"] == "recommend_create"

    accepted = dispatch_mind_shell(
        MindShellRequest(
            command=(
                f"memory proposal-accept {proposal_id} "
                '--reason "La fonte utente sostiene direttamente questa preferenza."'
            )
        ),
        context=context,
    )
    assert accepted.ok is True
    data = accepted.result["data"]
    assert data["status"] == "accepted_create"
    memory_id = data["outcome"]["memory_id"]

    with Session(db_engine) as db:
        memory = repositories.get_memory(db, memory_id)
        resolved = repositories.get_memory_proposal(db, proposal_id)
        traces = repositories.list_traces_for_turn(
            db,
            turn_id=context.turn_id or "",
        )
        source_after = repositories.get_chat_session(db, source_session_id)
    assert memory is not None
    assert memory.source_session_id == source_session_id
    assert memory.source_turn_id == source_turn_id
    assert memory.source_message_id == source_message_id
    assert memory.metadata_json["source_context"]["proposal_id"] == proposal_id
    assert resolved is not None
    assert resolved.status == "accepted_create"
    assert resolved.applied_at is not None
    assert resolved.result_json["resolution"]["semantic_authority"] is True
    assert any(trace.kind == "mind.memory.proposal.decide" for trace in traces)
    assert source_after is not None
    assert source_after.updated_at == source_updated_at


def test_scarlet_resolves_duplicate_reject_and_supersede_proposals(
    db_engine: Engine,
) -> None:
    context, source_session_id, source_turn_id, source_message_id = _setup_turns(
        db_engine
    )
    with Session(db_engine) as db:
        existing = repositories.add_memory(
            db,
            memory_type="user_preference",
            scope="user",
            content="L'utente preferisce bevande serali senza caffeina.",
            reason_for_storage="Preferenza già confermata.",
        )
        old = repositories.add_memory(
            db,
            memory_type="user_preference",
            scope="user",
            content="L'utente preferisce il caffè dopo cena.",
            reason_for_storage="Preferenza storica ormai superata.",
        )
        existing_id = existing.id
        old_id = old.id
        initial_count = len(repositories.list_all_memories(db))

    duplicate_id = _proposal(
        db_engine,
        source_session_id=source_session_id,
        source_turn_id=source_turn_id,
        source_message_id=source_message_id,
        key="proposal:duplicate",
        content="Per la sera l'utente sceglie bevande senza caffeina.",
    )
    duplicate = dispatch_mind_shell(
        MindShellRequest(
            command=(
                f"memory proposal-duplicate {duplicate_id} {existing_id} "
                '--reason "Le fonti mostrano la stessa preferenza già attiva."'
            )
        ),
        context=context,
    )
    assert duplicate.ok is True
    assert duplicate.result["data"]["status"] == "resolved_duplicate"

    rejected_id = _proposal(
        db_engine,
        source_session_id=source_session_id,
        source_turn_id=source_turn_id,
        source_message_id=source_message_id,
        key="proposal:reject",
        content="Una battuta transitoria dovrebbe diventare una preferenza.",
    )
    rejected = dispatch_mind_shell(
        MindShellRequest(
            command=(
                f"memory proposal-reject {rejected_id} "
                '--reason "La fonte è transitoria e non sostiene memoria durevole."'
            )
        ),
        context=context,
    )
    assert rejected.ok is True
    assert rejected.result["data"]["status"] == "rejected_by_scarlet"

    supersede_id = _proposal(
        db_engine,
        source_session_id=source_session_id,
        source_turn_id=source_turn_id,
        source_message_id=source_message_id,
        key="proposal:supersede",
        content="L'utente evita il caffè dopo cena e preferisce una tisana.",
    )
    superseded = dispatch_mind_shell(
        MindShellRequest(
            command=(
                f"memory proposal-supersede {supersede_id} {old_id} "
                '--reason "La nuova fonte corregge esplicitamente la preferenza storica."'
            )
        ),
        context=context,
    )
    assert superseded.ok is True
    supersede_data = superseded.result["data"]
    assert supersede_data["status"] == "accepted_supersede"

    with Session(db_engine) as db:
        duplicate_proposal = repositories.get_memory_proposal(db, duplicate_id)
        rejected_proposal = repositories.get_memory_proposal(db, rejected_id)
        supersede_proposal = repositories.get_memory_proposal(db, supersede_id)
        old_after = repositories.get_memory(db, old_id)
        final_memories = repositories.list_all_memories(db)
    assert duplicate_proposal is not None
    assert duplicate_proposal.status == "resolved_duplicate"
    assert rejected_proposal is not None
    assert rejected_proposal.status == "rejected_by_scarlet"
    assert supersede_proposal is not None
    assert supersede_proposal.status == "accepted_supersede"
    assert old_after is not None and old_after.status == "deprecated"
    assert len(final_memories) == initial_count + 1


def test_pending_review_is_open_and_has_no_applied_timestamp(
    db_engine: Engine,
) -> None:
    context, source_session_id, source_turn_id, source_message_id = _setup_turns(
        db_engine
    )
    proposal_id = _proposal(
        db_engine,
        source_session_id=source_session_id,
        source_turn_id=source_turn_id,
        source_message_id=source_message_id,
        key="proposal:pending",
        content="Una proposta resta aperta finché Scarlet non la decide.",
    )

    with Session(db_engine) as db:
        proposal = repositories.get_memory_proposal(db, proposal_id)
    assert proposal is not None
    assert proposal.status == "pending_review"
    assert proposal.applied_at is None
    assert proposal.status in repositories.OPEN_MEMORY_PROPOSAL_STATUSES
    assert proposal.status not in repositories.RESOLVED_MEMORY_PROPOSAL_STATUSES

    resolved = dispatch_mind_shell(
        MindShellRequest(command="memory proposals --status resolved"),
        context=context,
    )
    assert resolved.ok is True
    assert resolved.result["data"]["proposals"] == []
