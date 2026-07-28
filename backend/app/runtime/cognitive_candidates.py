"""Shared deterministic identity and persistence boundary for candidates."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from sqlmodel import Session

from app.storage import repositories
from app.storage.models import CognitiveCandidate


def candidate_fingerprint(
    *,
    profile_id: str,
    candidate_kind: str,
    claim: str,
    source_refs: list[str],
) -> str:
    """Create the canonical idempotency key for a source-backed candidate."""

    payload = {
        "profile_id": profile_id,
        "candidate_kind": candidate_kind,
        "claim": " ".join(claim.lower().split()),
        "source_refs": sorted(set(source_refs)),
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def candidate_source(
    source_ref: str,
    *,
    observed_at: datetime | None,
    metadata: dict[str, Any] | None = None,
    relation: str = "supports",
) -> dict[str, Any]:
    """Translate one canonical ``kind:id`` reference for repository storage."""

    source_kind, separator, source_id = source_ref.partition(":")
    if not separator or not source_kind or not source_id:
        raise ValueError(f"Candidate source reference must be kind:id, got {source_ref!r}")
    return {
        "source_kind": source_kind,
        "source_id": source_id,
        "observed_at": observed_at,
        "metadata": metadata or {},
        "relation": relation,
    }


def persist_cognitive_candidate(
    db: Session,
    *,
    profile_id: str,
    candidate_kind: str,
    context_family: str,
    claim: str,
    why_now: str,
    cognitive_question: str,
    expected_transformation: str,
    uncertainty: str,
    source_refs: list[str],
    sources: list[dict[str, Any]],
    appraisal_model: str | None = None,
    appraisal_trace_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    not_before: datetime | None = None,
    expires_at: datetime | None = None,
) -> tuple[CognitiveCandidate, bool]:
    """Persist a candidate while keeping its idempotency contract identical."""

    return repositories.create_candidate(
        db,
        profile_id=profile_id,
        candidate_kind=candidate_kind,
        context_family=context_family,
        claim=claim,
        why_now=why_now,
        cognitive_question=cognitive_question,
        expected_transformation=expected_transformation,
        uncertainty=uncertainty,
        exact_fingerprint=candidate_fingerprint(
            profile_id=profile_id,
            candidate_kind=candidate_kind,
            claim=claim,
            source_refs=source_refs,
        ),
        sources=sources,
        appraisal_model=appraisal_model,
        appraisal_trace_id=appraisal_trace_id,
        metadata=metadata,
        not_before=not_before,
        expires_at=expires_at,
    )
