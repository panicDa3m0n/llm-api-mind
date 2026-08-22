"""Persist and route recursive chronological summaries without source mutation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.llm.factory import (
    auxiliary_provider_max_tokens,
    auxiliary_provider_settings,
)
from app.llm.provider import LLMMessage, LLMProvider
from app.runtime.history_compaction import (
    build_chronology_source_map,
    build_history_partition_plan,
)
from app.runtime.token_estimation import estimate_tokens
from app.storage import repositories
from app.storage.models import HistoryCompaction


HISTORY_COMPACTION_ARTIFACT_VERSION = "history-compaction-artifact-v1"
HISTORY_ROUTING_VERSION = "history-routing-v1"
OPAQUE_SOURCE_ID_PATTERN = re.compile(
    r"\b(?:turn|msg|trace|toolu|mem|ses)_[A-Za-z0-9]+\b"
)

HISTORY_COMPACTION_SYSTEM_PROMPT = """You compact Scarlet's chronological provider history.

You are not answering the user. Produce only the new compacted chronology in
plain text. Preserve decisions, corrections, relationship changes, open loops,
source ids, tool outcomes, and uncertainty boundaries. Keep turn_id,
message_id, tool_call_id, and trace_id anchors when present. Never invent an
event or claim. The source transcript remains canonical and navigable; this
artifact is only a derived continuity view.
"""


ProviderFactory = Callable[[Any], LLMProvider]


@dataclass(frozen=True)
class HistoryRoutingResult:
    model_messages: list[LLMMessage]
    system_appendix: str
    payload: dict[str, Any]


def route_history_for_model(
    db: Session,
    *,
    session_id: str,
    canonical_messages: list[LLMMessage],
    chars_per_token: float,
    mode: str,
) -> HistoryRoutingResult:
    """Return a validated derived history or the untouched canonical request."""

    base = {
        "schema_version": HISTORY_ROUTING_VERSION,
        "mode": mode,
        "status": "canonical_history",
        "canonical_history_mutation": "none",
        "canonical_request_message_count": len(canonical_messages),
        "model_request_message_count": len(canonical_messages),
        "artifact_id": None,
    }
    if mode != "active" or not canonical_messages:
        return HistoryRoutingResult(canonical_messages, "", base)

    source_map = build_chronology_source_map(
        db,
        session_id=session_id,
        chars_per_token=chars_per_token,
    )
    if source_map.get("status") != "complete":
        return HistoryRoutingResult(
            canonical_messages,
            "",
            base
            | {
                "status": "canonical_fallback_source_map_unavailable",
                "source_map_status": source_map.get("status"),
                "source_map_reason": source_map.get("reason"),
            },
        )

    artifact = repositories.get_latest_history_compaction(
        db,
        session_id=session_id,
    )
    if artifact is None:
        return HistoryRoutingResult(
            canonical_messages,
            "",
            base
            | {
                "status": "canonical_fallback_artifact_missing",
                "source_history_sha256": source_map.get(
                    "canonical_history_sha256"
                ),
            },
        )

    valid, reason, covered_count = _validate_artifact(artifact, source_map)
    if not valid:
        return HistoryRoutingResult(
            canonical_messages,
            "",
            base
            | {
                "status": "canonical_fallback_artifact_invalid",
                "artifact_id": artifact.id,
                "artifact_generation": artifact.generation,
                "reason": reason,
            },
        )

    turns = _turns(source_map)
    tail_units = turns[covered_count:]
    tail_payloads = [
        message
        for unit in tail_units
        for message in _provider_messages(unit.get("provider_messages"))
    ]
    current = canonical_messages[-1]
    if current.role != "user":
        return HistoryRoutingResult(
            canonical_messages,
            "",
            base
            | {
                "status": "canonical_fallback_current_message_invalid",
                "artifact_id": artifact.id,
            },
        )
    model_messages = [
        LLMMessage(role=item["role"], content=item["content"])
        for item in tail_payloads
    ] + [current]
    appendix = _system_appendix(artifact)
    return HistoryRoutingResult(
        model_messages,
        appendix,
        base
        | {
            "status": "derived_history_active",
            "artifact_id": artifact.id,
            "artifact_generation": artifact.generation,
            "artifact_summary_sha256": artifact.summary_sha256,
            "artifact_summary_estimated_tokens": artifact.summary_estimated_tokens,
            "covered_through_turn_id": artifact.covered_through_turn_id,
            "covered_turn_count": covered_count,
            "verbatim_turn_ids": [unit.get("turn_id") for unit in tail_units],
            "verbatim_estimated_tokens": sum(
                int(unit.get("estimated_tokens") or 0) for unit in tail_units
            ),
            "source_history_sha256": source_map.get(
                "canonical_history_sha256"
            ),
            "model_request_message_count": len(model_messages),
        },
    )


def generate_history_compaction(
    engine: Engine,
    *,
    settings: Any,
    provider_factory: ProviderFactory,
    session_id: str,
    trigger_turn_id: str | None,
    expected_history_sha256: str,
    external_context_tokens: int,
    chars_per_token: float,
) -> dict[str, Any]:
    """Generate one recursive artifact after verifying the scheduled snapshot."""

    with Session(engine) as db:
        source_map = build_chronology_source_map(
            db,
            session_id=session_id,
            chars_per_token=chars_per_token,
        )
        if source_map.get("status") != "complete":
            return {
                "ok": False,
                "status": "source_map_unavailable",
                "reason": source_map.get("reason"),
            }
        if source_map.get("canonical_history_sha256") != expected_history_sha256:
            return {
                "ok": True,
                "status": "skipped_stale_snapshot",
                "expected_history_sha256": expected_history_sha256,
                "current_history_sha256": source_map.get(
                    "canonical_history_sha256"
                ),
            }
        plan = build_history_partition_plan(
            source_map=source_map,
            external_context_tokens=external_context_tokens,
            provider_history_tokens=int(
                source_map.get("canonical_estimated_tokens") or 0
            ),
            trigger_tokens=int(settings.context_compaction_trigger_tokens),
            operational_limit_tokens=int(
                settings.context_operational_input_limit_tokens
            ),
            model_window_tokens=int(settings.context_window_tokens),
            summary_max_tokens=int(settings.history_compaction_target_tokens),
            verbatim_max_tokens=int(settings.history_compaction_verbatim_tokens),
            safety_tokens=int(settings.history_compaction_safety_tokens),
            mode="active",
        )
        if plan.get("physical_window_failure") is not None:
            return {
                "ok": False,
                "status": "physical_window_failure",
                "plan": plan,
            }
        target_ids = [
            str(item)
            for item in plan["areas"]["compacted_summary"]["input_turn_ids"]
        ]
        if not target_ids:
            return {"ok": True, "status": "nothing_to_compact", "plan": plan}
        turns = _turns(source_map)
        target_units = [unit for unit in turns if str(unit.get("turn_id")) in target_ids]
        previous = repositories.get_latest_history_compaction(
            db,
            session_id=session_id,
        )
        previous_count = 0
        if previous is not None:
            valid, _, previous_count = _validate_artifact(previous, source_map)
            if not valid or previous.covered_turn_ids_json != target_ids[:previous_count]:
                previous = None
                previous_count = 0
        delta_units = target_units[previous_count:]
        if previous is not None and not delta_units:
            return {
                "ok": True,
                "status": "up_to_date",
                "artifact_id": previous.id,
                "generation": previous.generation,
                "plan": plan,
            }
        prompt = _compaction_prompt(
            session_id=session_id,
            previous=previous,
            legacy_prefix=(source_map.get("legacy_prefix") or {}),
            delta_units=delta_units,
            target_ids=target_ids,
            max_tokens=int(settings.history_compaction_target_tokens),
        )

    auxiliary_settings = auxiliary_provider_settings(settings)
    provider = provider_factory(auxiliary_settings)
    result = provider.generate_text(
        prompt=prompt,
        system=HISTORY_COMPACTION_SYSTEM_PROMPT,
        max_tokens=min(
            int(settings.history_compaction_target_tokens),
            auxiliary_provider_max_tokens(settings),
        ),
    )
    raw_summary = result.text.strip()
    summary, invalid_source_ids = _sanitize_unverified_source_ids(
        raw_summary,
        source_text=prompt,
    )
    if not summary:
        return {"ok": False, "status": "empty_provider_summary"}

    with Session(engine) as db:
        current_map = build_chronology_source_map(
            db,
            session_id=session_id,
            chars_per_token=chars_per_token,
        )
        if current_map.get("canonical_history_sha256") != expected_history_sha256:
            return {
                "ok": True,
                "status": "skipped_snapshot_changed_during_generation",
            }
        current_turns = _turns(current_map)
        covered_units = current_turns[: len(target_ids)]
        if [str(unit.get("turn_id")) for unit in covered_units] != target_ids:
            return {"ok": False, "status": "covered_prefix_changed"}
        covered_sources = [_source_ref(unit) for unit in covered_units]
        artifact = repositories.create_history_compaction(
            db,
            session_id=session_id,
            summary=summary,
            summary_sha256=_text_digest(summary),
            source_history_sha256=expected_history_sha256,
            covered_through_turn_id=target_ids[-1],
            covered_turn_ids=target_ids,
            covered_sources=covered_sources,
            source_estimated_tokens=(
                int(
                    (current_map.get("legacy_prefix") or {}).get(
                        "estimated_tokens"
                    )
                    or 0
                )
                + sum(
                    int(unit.get("estimated_tokens") or 0)
                    for unit in covered_units
                )
            ),
            summary_estimated_tokens=estimate_tokens(
                len(summary),
                chars_per_token,
                minimum_chars_per_token=1.0,
            ),
            trigger_turn_id=trigger_turn_id,
            model=result.model or auxiliary_settings.minimax_model,
            provider_message_id=result.provider_message_id,
            metadata={
                "schema_version": HISTORY_COMPACTION_ARTIFACT_VERSION,
                "recursive": previous is not None,
                "previous_generation": previous.generation if previous else None,
                "delta_turn_ids": [
                    str(unit.get("turn_id")) for unit in delta_units
                ],
                "legacy_prefix_sha256": (
                    current_map.get("legacy_prefix") or {}
                ).get("sha256"),
                "provider_usage": result.usage,
                "provider_stop_reason": result.stop_reason,
                "plan_schema_version": plan.get("schema_version"),
                "invalid_source_ids_removed": invalid_source_ids,
            },
        )
        trace = repositories.add_trace(
            db,
            session_id=session_id,
            turn_id=trigger_turn_id,
            kind="history.compaction.generated",
            payload={
                "schema_version": HISTORY_COMPACTION_ARTIFACT_VERSION,
                "artifact_id": artifact.id,
                "generation": artifact.generation,
                "previous_compaction_id": artifact.previous_compaction_id,
                "source_history_sha256": artifact.source_history_sha256,
                "summary_sha256": artifact.summary_sha256,
                "covered_turn_ids": artifact.covered_turn_ids_json,
                "covered_sources": artifact.covered_sources_json,
                "source_estimated_tokens": artifact.source_estimated_tokens,
                "summary_estimated_tokens": artifact.summary_estimated_tokens,
                "model": artifact.model,
                "provider_message_id": artifact.provider_message_id,
                "invalid_source_ids_removed": invalid_source_ids,
                "canonical_history_mutation": "none",
            },
        )
        db.refresh(artifact)
    return {
        "ok": True,
        "status": "generated",
        "artifact_id": artifact.id,
        "generation": artifact.generation,
        "trace_id": trace.id,
        "covered_turn_count": len(target_ids),
        "summary_estimated_tokens": artifact.summary_estimated_tokens,
        "plan": plan,
    }


def _validate_artifact(
    artifact: HistoryCompaction,
    source_map: dict[str, Any],
) -> tuple[bool, str | None, int]:
    if artifact.summary_sha256 != _text_digest(artifact.summary):
        return False, "summary_digest_mismatch", 0
    turns = _turns(source_map)
    covered_ids = list(artifact.covered_turn_ids_json)
    if not covered_ids:
        return False, "covered_turns_empty", 0
    if len(covered_ids) > len(turns):
        return False, "covered_turns_exceed_current_history", 0
    prefix = turns[: len(covered_ids)]
    if [str(unit.get("turn_id")) for unit in prefix] != covered_ids:
        return False, "covered_turns_not_canonical_prefix", 0
    if artifact.covered_through_turn_id != covered_ids[-1]:
        return False, "covered_through_turn_mismatch", 0
    expected_sources = [_source_identity(unit) for unit in prefix]
    artifact_sources = [
        _source_identity(item)
        for item in artifact.covered_sources_json
        if isinstance(item, dict)
    ]
    if artifact_sources != expected_sources:
        return False, "covered_source_digest_mismatch", 0
    legacy_sha = (source_map.get("legacy_prefix") or {}).get("sha256")
    if artifact.metadata_json.get("legacy_prefix_sha256") != legacy_sha:
        return False, "legacy_prefix_digest_mismatch", 0
    return True, None, len(covered_ids)


def _compaction_prompt(
    *,
    session_id: str,
    previous: HistoryCompaction | None,
    legacy_prefix: dict[str, Any],
    delta_units: list[dict[str, Any]],
    target_ids: list[str],
    max_tokens: int,
) -> str:
    sources: list[dict[str, Any]] = []
    if previous is None and legacy_prefix.get("provider_messages"):
        sources.append(
            {
                "kind": "legacy_provider_history_prefix",
                "sha256": legacy_prefix.get("sha256"),
                "provider_messages": legacy_prefix.get("provider_messages"),
            }
        )
    sources.extend(
        {
            "kind": "completed_turn",
            **_source_ref(unit),
            "message_ids": unit.get("message_ids"),
            "tool_call_ids": unit.get("tool_call_ids"),
            "request_trace_id": unit.get("request_trace_id"),
            "response_trace_id": unit.get("response_trace_id"),
            "provider_messages": unit.get("provider_messages"),
        }
        for unit in delta_units
    )
    payload = {
        "session_id": session_id,
        "target_covered_turn_ids": target_ids,
        "maximum_output_tokens": max_tokens,
        "previous_compaction": (
            {
                "artifact_id": previous.id,
                "generation": previous.generation,
                "covered_turn_ids": previous.covered_turn_ids_json,
                "summary": previous.summary,
            }
            if previous is not None
            else None
        ),
        "new_sources": sources,
    }
    return (
        "Recursively compact the chronology below. The new summary must cover "
        "the previous summary plus every new source and remain source-labelled.\n\n"
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )


def _system_appendix(artifact: HistoryCompaction) -> str:
    source_manifest = json.dumps(
        {
            "covered_turn_ids": artifact.covered_turn_ids_json,
            "covered_sources": artifact.covered_sources_json,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (
        "\n\n<compacted_chronology "
        f'artifact_id="{artifact.id}" generation="{artifact.generation}" '
        f'covered_through_turn_id="{artifact.covered_through_turn_id}" '
        f'summary_sha256="{artifact.summary_sha256}">\n'
        "This is a source-labelled derived continuity summary. Exact historical "
        "messages remain canonical and navigable through session commands.\n"
        f"<source_manifest>{source_manifest}</source_manifest>\n"
        f"{artifact.summary}\n"
        "</compacted_chronology>"
    )


def _turns(source_map: dict[str, Any]) -> list[dict[str, Any]]:
    value = source_map.get("turns")
    return value if isinstance(value, list) else []


def _provider_messages(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _source_ref(unit: dict[str, Any]) -> dict[str, Any]:
    return {
        "turn_id": str(unit.get("turn_id")),
        "sha256": str(unit.get("sha256")),
        "estimated_tokens": int(unit.get("estimated_tokens") or 0),
        "message_ids": list(unit.get("message_ids") or []),
        "tool_call_ids": list(unit.get("tool_call_ids") or []),
        "request_trace_id": unit.get("request_trace_id"),
        "response_trace_id": unit.get("response_trace_id"),
    }


def _source_identity(unit: dict[str, Any]) -> dict[str, str]:
    return {
        "turn_id": str(unit.get("turn_id")),
        "sha256": str(unit.get("sha256")),
    }


def _text_digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _sanitize_unverified_source_ids(
    summary: str,
    *,
    source_text: str,
) -> tuple[str, list[str]]:
    allowed = set(OPAQUE_SOURCE_ID_PATTERN.findall(source_text))
    found = set(OPAQUE_SOURCE_ID_PATTERN.findall(summary))
    invalid = sorted(found - allowed)
    sanitized = summary
    for source_id in invalid:
        sanitized = sanitized.replace(source_id, "[invalid_source_id_removed]")
    return sanitized, invalid
