"""Conservative audit and maintenance for historical memory provenance."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from typing import Any

from sqlmodel import Session

from app.mind.search import sync_memory_retrieval_artifacts
from app.storage import repositories
from app.storage.models import ChatSession, MemoryRecord, utc_now


AUDIT_CONTRACT_VERSION = "memory-provenance-audit-v2"
EXPLICIT_FIXTURE_METADATA_KEYS = frozenset(
    {
        "codex_test_dataset_version",
        "codex_test_key",
        "codex_test_lane",
    }
)
EXPLICIT_FIXTURE_TAGS = frozenset({"codex-test", "codex-dirty-memory-v1"})
EXPLICIT_FIXTURE_SESSION_PREFIX = "Codex Test Seed - "


class MemoryProvenanceMutationError(ValueError):
    """Reject a maintenance mutation whose reviewed candidate set has drifted."""


def memory_provenance_audit(
    db: Session,
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    """Classify provenance and record disposition without mutating state.

    Provenance validity and record disposition are deliberately orthogonal. A
    fixture can have valid provenance, while a useful record can remain
    non-sourceable. Exact duplicates and explicit fixtures are evidence classes,
    not semantic judgments inferred from similarity.
    """

    all_memories = repositories.list_all_memories(db, include_low_confidence=True)
    checked_memories = all_memories[:limit] if limit is not None else all_memories
    exact_duplicate_ids = _exact_duplicate_ids(all_memories)
    items: list[dict[str, Any]] = []

    for memory in checked_memories:
        source_session = (
            repositories.get_chat_session(db, memory.source_session_id)
            if memory.source_session_id is not None
            else None
        )
        provenance = _classify_provenance(
            db,
            memory=memory,
            source_session=source_session,
        )
        fixture_evidence = _explicit_fixture_evidence(
            memory,
            source_session=source_session,
        )
        record_class, recommended_action = _classify_record(
            memory,
            provenance_class=provenance["classification"],
            fixture_evidence=fixture_evidence,
            exact_duplicate=memory.id in exact_duplicate_ids,
        )
        items.append(
            {
                "memory_id": memory.id,
                "memory_type": memory.memory_type,
                "scope": memory.scope,
                "status": memory.status,
                # Compatibility name retained for existing audit consumers.
                "classification": provenance["classification"],
                "provenance_class": provenance["classification"],
                "record_class": record_class,
                "recommended_action": recommended_action,
                "source_session_id": memory.source_session_id,
                "source_turn_id": memory.source_turn_id,
                "source_message_id": memory.source_message_id,
                "proposed_source_message_id": provenance.get(
                    "proposed_source_message_id"
                ),
                "evidence": provenance["evidence"],
                "evidence_flags": provenance["evidence_flags"],
                "fixture_evidence": fixture_evidence,
                "exact_content_duplicate": memory.id in exact_duplicate_ids,
                "content_sha256": hashlib.sha256(
                    _normalize_content(memory.content).encode("utf-8")
                ).hexdigest(),
            }
        )

    provenance_counts = Counter(item["provenance_class"] for item in items)
    record_counts = Counter(item["record_class"] for item in items)
    action_counts = Counter(item["recommended_action"] for item in items)
    counts_by_scope: dict[str, dict[str, int]] = defaultdict(dict)
    for item in items:
        scope = str(item["scope"])
        key = str(item["provenance_class"])
        counts_by_scope[scope][key] = counts_by_scope[scope].get(key, 0) + 1

    repair_items = [
        item
        for item in items
        if item["recommended_action"] == "repair_exact_source_message"
    ]
    fixture_items = [
        item
        for item in items
        if item["recommended_action"] == "deprecate_explicit_test_fixture"
    ]
    candidate_sets = {
        "exact_source_message_repair": _candidate_set(repair_items),
        "explicit_test_fixture_deprecation": _candidate_set(fixture_items),
    }

    return {
        "contract_version": AUDIT_CONTRACT_VERSION,
        "generated_at": utc_now().isoformat(),
        "read_only": True,
        "checked": len(items),
        "total_memories": len(all_memories),
        "limited": limit is not None and len(all_memories) > len(items),
        # Compatibility fields preserve the old provenance-count surface.
        "counts": dict(provenance_counts),
        "counts_by_scope": dict(counts_by_scope),
        "provenance_counts": dict(provenance_counts),
        "record_counts": dict(record_counts),
        "recommended_action_counts": dict(action_counts),
        "candidate_sets": candidate_sets,
        "criteria": _criteria_payload(),
        "items": items,
    }


def repair_exact_source_messages(
    db: Session,
    *,
    dry_run: bool = True,
    expected_candidate_digest: str | None = None,
    backup_reference: str | None = None,
) -> dict[str, Any]:
    """Repair only a single exact user-message hook inside a known source turn."""

    audit = memory_provenance_audit(db)
    candidate_set = audit["candidate_sets"]["exact_source_message_repair"]
    _validate_mutation_guard(
        dry_run=dry_run,
        candidate_set=candidate_set,
        expected_candidate_digest=expected_candidate_digest,
        backup_reference=backup_reference,
    )
    if dry_run:
        return _mutation_report(
            operation="maintenance.memory.provenance.repair",
            dry_run=True,
            candidate_set=candidate_set,
            backup_reference=backup_reference,
        )

    items_by_id = {item["memory_id"]: item for item in audit["items"]}
    activity_ids: list[str] = []
    for memory_id in candidate_set["memory_ids"]:
        item = items_by_id[memory_id]
        source_message_id = item["proposed_source_message_id"]
        assert isinstance(source_message_id, str)
        repositories.update_memory_source_message(
            db,
            memory_id=memory_id,
            source_message_id=source_message_id,
        )
        activity = repositories.add_memory_activity(
            db,
            memory_id=memory_id,
            activity_kind="provenance_repair",
            source="maintenance.memory.provenance",
            actor="backend",
            session_id=item["source_session_id"],
            turn_id=item["source_turn_id"],
            message_id=source_message_id,
            eligible_for_recent=False,
            metadata={
                "candidate_digest": candidate_set["digest_sha256"],
                "backup_reference": backup_reference,
                "evidence": item["evidence"],
            },
        )
        activity_ids.append(activity.id)

    return _mutation_report(
        operation="maintenance.memory.provenance.repair",
        dry_run=False,
        candidate_set=candidate_set,
        backup_reference=backup_reference,
        applied_count=len(candidate_set["memory_ids"]),
        activity_ids=activity_ids,
        residual_audit=memory_provenance_audit(db),
    )


def deprecate_explicit_test_fixtures(
    db: Session,
    *,
    reason: str,
    dry_run: bool = True,
    expected_candidate_digest: str | None = None,
    backup_reference: str | None = None,
) -> dict[str, Any]:
    """Deprecate only records carrying the complete explicit Codex fixture contract."""

    audit = memory_provenance_audit(db)
    candidate_set = audit["candidate_sets"]["explicit_test_fixture_deprecation"]
    _validate_mutation_guard(
        dry_run=dry_run,
        candidate_set=candidate_set,
        expected_candidate_digest=expected_candidate_digest,
        backup_reference=backup_reference,
    )
    if dry_run:
        return _mutation_report(
            operation="maintenance.memory.provenance.deprecate_explicit_test_fixtures",
            dry_run=True,
            candidate_set=candidate_set,
            backup_reference=backup_reference,
        )

    changed: list[MemoryRecord] = []
    facts_by_memory: dict[str, list[Any]] = {}
    activity_ids: list[str] = []
    recorded_at = utc_now().isoformat()
    for memory_id in candidate_set["memory_ids"]:
        memory = repositories.get_memory(db, memory_id)
        if memory is None or memory.status != "active":
            raise MemoryProvenanceMutationError(
                f"Candidate {memory_id} is missing or no longer active. Rerun dry-run."
            )
        metadata = _append_lifecycle_event(
            memory.metadata_json,
            event={
                "operation": "deprecate",
                "reason": reason,
                "previous_status": memory.status,
                "superseded_by": None,
                "source": "maintenance.memory.provenance",
                "classification": "explicit_test_fixture",
                "candidate_digest": candidate_set["digest_sha256"],
                "backup_reference": backup_reference,
                "recorded_at": recorded_at,
            },
        )
        updated = repositories.update_memory_lifecycle(
            db,
            memory_id=memory_id,
            status="deprecated",
            metadata=metadata,
            touch_source_session=False,
        )
        assert updated is not None
        facts = repositories.update_memory_facts_status(
            db,
            memory_id=memory_id,
            status="deprecated",
        )
        activity = repositories.add_memory_activity(
            db,
            memory_id=memory_id,
            activity_kind="lifecycle_deprecate",
            source="maintenance.memory.provenance",
            actor="backend",
            session_id=memory.source_session_id,
            eligible_for_recent=False,
            metadata={
                "classification": "explicit_test_fixture",
                "candidate_digest": candidate_set["digest_sha256"],
                "backup_reference": backup_reference,
                "reason": reason,
            },
        )
        changed.append(updated)
        facts_by_memory[memory_id] = facts
        activity_ids.append(activity.id)

    sync_memory_retrieval_artifacts(
        db,
        changed,
        facts_by_memory=facts_by_memory,
    )
    return _mutation_report(
        operation="maintenance.memory.provenance.deprecate_explicit_test_fixtures",
        dry_run=False,
        candidate_set=candidate_set,
        backup_reference=backup_reference,
        applied_count=len(changed),
        activity_ids=activity_ids,
        residual_audit=memory_provenance_audit(db),
    )


def _classify_provenance(
    db: Session,
    *,
    memory: MemoryRecord,
    source_session: ChatSession | None,
) -> dict[str, Any]:
    flags = {
        "source_session_present": memory.source_session_id is not None,
        "source_session_resolves": source_session is not None,
        "source_turn_present": memory.source_turn_id is not None,
        "source_message_present": memory.source_message_id is not None,
        "source_turn_resolves": False,
        "source_turn_matches_session": False,
        "source_message_resolves": False,
        "source_message_matches_session": False,
        "source_message_matches_turn": False,
        "source_message_is_user": False,
    }
    if memory.source_session_id is None:
        return _provenance_result(
            "missing_source_session",
            "memory has no persisted source session hook",
            flags,
        )
    if source_session is None:
        return _provenance_result(
            "invalid_source_session",
            "stored source session does not resolve",
            flags,
        )
    if memory.source_turn_id is None:
        return _provenance_result(
            "source_session_only",
            "source session resolves, but no source turn or message is persisted",
            flags,
        )

    source_turn = repositories.get_turn(db, memory.source_turn_id)
    flags["source_turn_resolves"] = source_turn is not None
    flags["source_turn_matches_session"] = bool(
        source_turn is not None and source_turn.session_id == memory.source_session_id
    )
    if source_turn is None or not flags["source_turn_matches_session"]:
        return _provenance_result(
            "invalid_source_turn",
            "stored source turn does not resolve inside the source session",
            flags,
        )

    if memory.source_message_id is None:
        user_messages = [
            message
            for message in repositories.list_messages_for_turn(
                db,
                turn_id=memory.source_turn_id,
            )
            if message.role == "user"
            and message.session_id == memory.source_session_id
        ]
        if len(user_messages) == 1:
            return _provenance_result(
                "repairable_single_user_message",
                "exactly one persisted user message exists in the source turn",
                flags,
                proposed_source_message_id=user_messages[0].id,
            )
        return _provenance_result(
            "ambiguous_source_turn",
            f"source turn contains {len(user_messages)} matching user messages",
            flags,
        )

    source_message = repositories.get_message(db, memory.source_message_id)
    flags["source_message_resolves"] = source_message is not None
    flags["source_message_matches_session"] = bool(
        source_message is not None
        and source_message.session_id == memory.source_session_id
    )
    flags["source_message_matches_turn"] = bool(
        source_message is not None and source_message.turn_id == memory.source_turn_id
    )
    flags["source_message_is_user"] = bool(
        source_message is not None and source_message.role == "user"
    )
    if not all(
        (
            flags["source_message_resolves"],
            flags["source_message_matches_session"],
            flags["source_message_matches_turn"],
            flags["source_message_is_user"],
        )
    ):
        return _provenance_result(
            "invalid_source_message",
            "stored source message is not a user message inside the declared source turn",
            flags,
        )
    return _provenance_result(
        "source_complete_valid",
        "source session, turn, and user message resolve consistently",
        flags,
    )


def _classify_record(
    memory: MemoryRecord,
    *,
    provenance_class: str,
    fixture_evidence: dict[str, Any],
    exact_duplicate: bool,
) -> tuple[str, str]:
    if fixture_evidence["confirmed"]:
        if memory.status == "active":
            return "explicit_test_fixture", "deprecate_explicit_test_fixture"
        return "explicit_test_fixture", "none_already_inactive"
    if exact_duplicate:
        return "exact_duplicate_review_candidate", "review_only"
    if provenance_class == "repairable_single_user_message":
        return "repairable_source_hook", "repair_exact_source_message"
    if provenance_class == "source_complete_valid":
        return "sourceable_record", "none"
    return "retained_non_sourceable_review", "review_only"


def _explicit_fixture_evidence(
    memory: MemoryRecord,
    *,
    source_session: ChatSession | None,
) -> dict[str, Any]:
    metadata_keys = set(memory.metadata_json)
    tags = set(memory.tags_json)
    session_title = source_session.title if source_session is not None else None
    checks = {
        "metadata_contract": EXPLICIT_FIXTURE_METADATA_KEYS.issubset(metadata_keys),
        "tag_contract": EXPLICIT_FIXTURE_TAGS.issubset(tags),
        "source_session_contract": bool(
            session_title and session_title.startswith(EXPLICIT_FIXTURE_SESSION_PREFIX)
        ),
    }
    return {
        "confirmed": all(checks.values()),
        "checks": checks,
        "matched_metadata_keys": sorted(
            EXPLICIT_FIXTURE_METADATA_KEYS.intersection(metadata_keys)
        ),
        "matched_tags": sorted(EXPLICIT_FIXTURE_TAGS.intersection(tags)),
        "source_session_title": session_title,
    }


def _exact_duplicate_ids(memories: list[MemoryRecord]) -> set[str]:
    groups: dict[str, list[str]] = defaultdict(list)
    for memory in memories:
        normalized = _normalize_content(memory.content)
        if normalized:
            groups[normalized].append(memory.id)
    return {
        memory_id
        for memory_ids in groups.values()
        if len(memory_ids) > 1
        for memory_id in memory_ids
    }


def _normalize_content(content: str) -> str:
    return " ".join(content.casefold().split())


def _candidate_set(items: list[dict[str, Any]]) -> dict[str, Any]:
    memory_ids = sorted(str(item["memory_id"]) for item in items)
    digest = hashlib.sha256("\n".join(memory_ids).encode("utf-8")).hexdigest()
    return {
        "count": len(memory_ids),
        "digest_sha256": digest,
        "memory_ids": memory_ids,
    }


def _validate_mutation_guard(
    *,
    dry_run: bool,
    candidate_set: dict[str, Any],
    expected_candidate_digest: str | None,
    backup_reference: str | None,
) -> None:
    if dry_run:
        return
    if not backup_reference or not backup_reference.strip():
        raise MemoryProvenanceMutationError(
            "Apply requires a verified backup reference."
        )
    actual_digest = str(candidate_set["digest_sha256"])
    if expected_candidate_digest != actual_digest:
        raise MemoryProvenanceMutationError(
            "Candidate set changed or was not acknowledged. Rerun dry-run and use "
            f"digest {actual_digest}."
        )


def _provenance_result(
    classification: str,
    evidence: str,
    evidence_flags: dict[str, bool],
    *,
    proposed_source_message_id: str | None = None,
) -> dict[str, Any]:
    return {
        "classification": classification,
        "evidence": evidence,
        "evidence_flags": evidence_flags,
        "proposed_source_message_id": proposed_source_message_id,
    }


def _append_lifecycle_event(
    metadata: dict[str, Any],
    *,
    event: dict[str, Any],
) -> dict[str, Any]:
    updated = dict(metadata)
    lifecycle = dict(updated.get("lifecycle") or {})
    history = list(lifecycle.get("history") or [])
    history.append(event)
    lifecycle["last_event"] = event
    lifecycle["history"] = history
    lifecycle["deprecated_reason"] = event.get("reason")
    lifecycle["superseded_by"] = None
    updated["lifecycle"] = lifecycle
    return updated


def _mutation_report(
    *,
    operation: str,
    dry_run: bool,
    candidate_set: dict[str, Any],
    backup_reference: str | None,
    applied_count: int = 0,
    activity_ids: list[str] | None = None,
    residual_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "operation": operation,
        "dry_run": dry_run,
        "candidate_set": candidate_set,
        "backup_reference": backup_reference,
        "applied_count": applied_count,
        "activity_ids": activity_ids or [],
        "residual_audit": residual_audit,
    }


def _criteria_payload() -> dict[str, Any]:
    return {
        "provenance": {
            "source_complete_valid": (
                "Session, turn, and user message all resolve and agree."
            ),
            "repairable_single_user_message": (
                "The declared source turn resolves and contains exactly one user message."
            ),
            "source_session_only": (
                "The session resolves, but no turn/message hook exists; no source is guessed."
            ),
            "invalid_source_message": (
                "The stored message is missing, mismatched, or not a user message."
            ),
        },
        "record": {
            "explicit_test_fixture": (
                "All fixed Codex-test metadata keys, tags, and source-session title "
                "must match. Content similarity is never used."
            ),
            "exact_duplicate_review_candidate": (
                "Normalized content is exactly equal; this is review evidence, not "
                "automatic semantic redundancy."
            ),
            "retained_non_sourceable_review": (
                "No deterministic source or disposition is available; retain for review."
            ),
        },
    }
