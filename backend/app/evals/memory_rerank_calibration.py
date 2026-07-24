"""Calibrate final memory reranking on frozen real references.

The runner never opens the source database as a runtime target. Every case and
repetition starts from a fresh guarded copy, then records recall-pool, final
rerank, V2 delivery, and optional real-Scarlet evidence separately.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from shutil import copy2
from time import perf_counter
from typing import Any

from fastapi.testclient import TestClient

from app.config import Settings
from app.llm.provider import LLMMessage, LLMStreamEvent, LLMTextResult
from app.main import create_app
from app.storage.db import create_db_engine, init_db


CALIBRATION_VERSION = "memory-rerank-negative-calibration-v2"
DEFAULT_SOURCE_DB = "data/v131-live-rerank-provenance-20260713.db"
DEFAULT_RUN_DB = "data/sca31-memory-rerank-run.db"
EXPECTED_SOURCE_SHA256 = (
    "4fd51648530bb9cb0959fba0adc0a96ec9cf41eb35408373085ffbbe64535010"
)
UTC = timezone.utc


@dataclass(frozen=True)
class CalibrationCase:
    case_id: str
    category: str
    query: str
    required_groups: tuple[tuple[str, ...], ...] = ()
    optional_relevant_ids: tuple[str, ...] = ()
    forbidden_ids: tuple[str, ...] = ()
    required_route: str | None = None
    live_scarlet: bool = False
    rationale: str = ""


class CalibrationProbeProvider:
    """Deterministic final answer while the real retrieval pipeline runs."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        if system and "runtime answer-obligation judge" in system:
            payload = json.loads(prompt)
            findings = [
                {
                    "obligation_id": obligation["id"],
                    "status": "pass",
                    "reason": (
                        "The controlled calibration answer makes no claim beyond "
                        "the retrieval evidence under test."
                    ),
                }
                for obligation in payload.get("obligations", [])
            ]
            return LLMTextResult(
                model=self.settings.minimax_model,
                text=json.dumps({"findings": findings}),
                usage={"input_tokens": 1, "output_tokens": 1},
                stop_reason="end_turn",
            )
        return self._result()

    def generate_chat(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        return self._result()

    def generate_chat_with_tools(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]],
        tool_runner: Any,
        max_tool_calls: int | None = None,
    ) -> LLMTextResult:
        return self._result()

    def stream_chat_with_tools(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]],
        tool_runner: Any,
        max_tool_calls: int | None = None,
    ):
        result = self._result()
        yield LLMStreamEvent(type="text_delta", data={"text": result.text})
        yield LLMStreamEvent(
            type="final_result",
            data={"result": result.model_dump(mode="json")},
        )

    def _result(self) -> LLMTextResult:
        text = "Calibration retrieval completed."
        return LLMTextResult(
            model=self.settings.minimax_model,
            text=text,
            usage={"input_tokens": 1, "output_tokens": 4},
            raw_content=[{"type": "text", "text": text}],
            stop_reason="end_turn",
        )


def calibration_cases() -> tuple[CalibrationCase, ...]:
    return (
        CalibrationCase(
            case_id="zero_luce_exact_kg",
            category="exact_and_kg",
            query=(
                "Quando uso il protocollo Zero-Luce, quali sezioni devo seguire "
                "e in quale ordine?"
            ),
            required_groups=(("mem_1bbd0dc1ef4f47e787ec2fa1c521e1d3",),),
            forbidden_ids=(
                "mem_abed5590f91b4eb8aa93d1103db024de",
                "mem_5e55df32b680410682340c8c32270ba8",
                "mem_57bc7bfe187645fea2eaa8567cd3296e",
            ),
            required_route="graph",
            rationale=(
                "The active four-block protocol must be found and delivered; "
                "the deprecated predecessor and Vetro-Luna are not substitutes."
            ),
        ),
        CalibrationCase(
            case_id="mint_evening_paraphrase",
            category="paraphrase",
            query=(
                "Sto per lavorare stasera e vorrei una bevanda che mi tenga "
                "calmo, senza caffeina e senza appesantirmi. Cosa scegli per me?"
            ),
            required_groups=(("mem_e1a9e89d843346c38a10989b626ea8f1",),),
            optional_relevant_ids=("mem_b5a37f5b1ba044bdbfd9610479cfeee7",),
            forbidden_ids=(
                "mem_fb0ca3c2a0d54cabaf62eac9456ef6c6",
                "mem_ac8a30ef37ec4f18ad0deca702eb8b16",
            ),
            live_scarlet=True,
            rationale=(
                "Natural Italian paraphrase of the known mint-tea preference; "
                "evening report formats are lexical distractors."
            ),
        ),
        CalibrationCase(
            case_id="chocolate_limit_paraphrase",
            category="paraphrase",
            query=(
                "Vorrei concedermi un dolce al cioccolato: c'e un mio limite "
                "personale che dovresti ricordare prima di consigliarmi?"
            ),
            required_groups=(("mem_f76b8682ebcf4e1b99c2845bbf66710d",),),
            forbidden_ids=(
                "mem_0c328a2f155e4ab6b3da3d2f3558c0d1",
                "mem_3ad23e75ce3242ebb0ccaff140e5be78",
            ),
            rationale=(
                "Food/body wording must not drift into the architectural body memories."
            ),
        ),
        CalibrationCase(
            case_id="tired_concise_style",
            category="personal_style",
            query=(
                "Sono stanco: come preferisco che mi rispondi quando ho poca energia?"
            ),
            required_groups=(("mem_56436816cb794b0db7b6b5330eaf6d50",),),
            optional_relevant_ids=("mem_d7db4ec7f62b4965bc475e7711ef8734",),
            rationale="Retrieve the fatigue-specific concise-response preference.",
        ),
        CalibrationCase(
            case_id="evening_report_disambiguation",
            category="similar_memories",
            query=(
                "Quando lavoro la sera e ti chiedo un report, quali sezioni preferisco?"
            ),
            required_groups=(("mem_fb0ca3c2a0d54cabaf62eac9456ef6c6",),),
            optional_relevant_ids=("mem_ac8a30ef37ec4f18ad0deca702eb8b16",),
            forbidden_ids=(
                "mem_1bbd0dc1ef4f47e787ec2fa1c521e1d3",
                "mem_5e55df32b680410682340c8c32270ba8",
            ),
            rationale=(
                "The evening three-section report preference is primary; the "
                "test/probe format is a plausible secondary memory."
            ),
        ),
        CalibrationCase(
            case_id="body_architecture_disambiguation",
            category="homonymous_concept",
            query=(
                "Quando parlo del corpo di Scarlet, intendo un robot fisico o "
                "il sistema di memorie e database?"
            ),
            required_groups=(
                (
                    "mem_0c328a2f155e4ab6b3da3d2f3558c0d1",
                    "mem_3ad23e75ce3242ebb0ccaff140e5be78",
                ),
            ),
            forbidden_ids=("mem_f76b8682ebcf4e1b99c2845bbf66710d",),
            live_scarlet=True,
            rationale=(
                "Disambiguate digital/robotic body from an unrelated food/body "
                "constraint. Either of the two complementary architecture "
                "memories is sufficient direct evidence."
            ),
        ),
        CalibrationCase(
            case_id="vetro_luna_temporal_pair",
            category="temporal_pair",
            query=(
                "Su Vetro-Luna avevamo preso una decisione recente? E qual era "
                "esattamente il formato storico che avevamo definito?"
            ),
            required_groups=(
                ("mem_57bc7bfe187645fea2eaa8567cd3296e",),
                ("mem_5e55df32b680410682340c8c32270ba8",),
            ),
            forbidden_ids=("mem_1bbd0dc1ef4f47e787ec2fa1c521e1d3",),
            rationale=(
                "Both the recent no-decision note and historical format are "
                "needed to answer the temporal contrast."
            ),
        ),
        CalibrationCase(
            case_id="davide_entity_overlap",
            category="entity_overlap",
            query="Che cosa ricordi su chi e Davide nel progetto Scarlet?",
            required_groups=(
                (
                    "mem_37b02f388d0d4affaa89c6b3efa1f32f",
                    "mem_6fbaf3a7787848049ba9c15916a27dab",
                ),
            ),
            rationale=(
                "Two overlapping source memories identify the same person; at "
                "least one must survive without assuming deterministic dedup."
            ),
        ),
        CalibrationCase(
            case_id="unrelated_jazz_negative",
            category="negative",
            query="Mi consigli una playlist jazz notturna mentre cucino?",
            live_scarlet=True,
            rationale="No stored memory is relevant to jazz playlists or cooking.",
        ),
        CalibrationCase(
            case_id="unrelated_weather_negative",
            category="negative",
            query="Che tempo fara domani sul lago di Garda?",
            rationale="No stored memory can establish a weather forecast.",
        ),
        CalibrationCase(
            case_id="wrong_protocol_entity_negative",
            category="negative_entity_collision",
            query="Cosa sai del protocollo Mare-Vetro?",
            forbidden_ids=("mem_1bbd0dc1ef4f47e787ec2fa1c521e1d3",),
            rationale=(
                "Existing regression control: sharing the generic word protocol "
                "must not turn Zero-Luce into evidence about Mare-Vetro."
            ),
        ),
        CalibrationCase(
            case_id="unknown_landscape_preference",
            category="negative_personal_preference",
            query="Ti ricordi se preferisco il mare o la montagna?",
            rationale=(
                "No stored memory establishes a sea-versus-mountain preference; "
                "generic preference memories are distractors."
            ),
        ),
        CalibrationCase(
            case_id="unknown_colleague_name",
            category="negative_personal_relationship",
            query="Come si chiama il mio collega Marco?",
            rationale=(
                "No stored memory establishes a colleague named Marco; known-person "
                "memories must not substitute for this relationship."
            ),
        ),
        CalibrationCase(
            case_id="unknown_strawberry_allergy",
            category="negative_personal_constraint",
            query="Sono allergico alle fragole?",
            rationale=(
                "No stored memory establishes a strawberry allergy; the chocolate "
                "limit is a nearby food/body distractor, not evidence."
            ),
        ),
        CalibrationCase(
            case_id="unknown_running_routine",
            category="negative_personal_routine",
            query="A che ora vado a correre di solito?",
            rationale=(
                "No stored memory establishes a running routine; temporal and "
                "personal memories are distractors."
            ),
        ),
        CalibrationCase(
            case_id="unknown_favourite_colour",
            category="negative_personal_preference",
            query="Qual e il mio colore preferito?",
            rationale=(
                "No stored memory establishes a favourite colour; generic user "
                "preferences must not be accepted."
            ),
        ),
    )


def run_calibration(
    *,
    source_db: Path,
    run_db: Path,
    output_path: Path,
    repetitions: int,
    run_live_scarlet: bool,
    settings: Settings,
    cases: tuple[CalibrationCase, ...] | None = None,
) -> dict[str, Any]:
    selected_cases = cases or calibration_cases()
    source_hash = _file_sha256(source_db)
    if source_hash != EXPECTED_SOURCE_SHA256:
        raise RuntimeError(
            "Calibration source hash mismatch: "
            f"expected {EXPECTED_SOURCE_SHA256}, got {source_hash}."
        )
    _validate_run_path(source_db=source_db, run_db=run_db)
    _validate_source_references(source_db, selected_cases)
    artifact: dict[str, Any] = {
        "schema_version": CALIBRATION_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "source_database": {
            "path": str(source_db),
            "sha256": source_hash,
            "mutation_policy": "immutable_seed_fresh_copy_per_case",
        },
        "configuration": _configuration(settings),
        "cases": [asdict(case) for case in selected_cases],
        "probe_runs": [],
        "live_scarlet_runs": [],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)

    for repetition in range(1, repetitions + 1):
        for case in selected_cases:
            artifact["probe_runs"].append(
                _run_case(
                    source_db=source_db,
                    run_db=run_db,
                    settings=settings,
                    case=case,
                    repetition=repetition,
                    live_scarlet=False,
                )
            )
            _write_artifact(output_path, artifact)

    if run_live_scarlet:
        for case in selected_cases:
            if not case.live_scarlet:
                continue
            artifact["live_scarlet_runs"].append(
                _run_case(
                    source_db=source_db,
                    run_db=run_db,
                    settings=settings,
                    case=case,
                    repetition=1,
                    live_scarlet=True,
                )
            )
            _write_artifact(output_path, artifact)

    artifact["analysis"] = threshold_analysis(
        artifact["probe_runs"],
        current_threshold=settings.retrieval_hybrid_min_rerank_score,
        relative_floor=settings.retrieval_hybrid_relative_rerank_floor,
    )
    artifact["source_database"]["sha256_after"] = _file_sha256(source_db)
    artifact["source_database"]["unchanged"] = (
        artifact["source_database"]["sha256_after"] == source_hash
    )
    artifact["summary"] = _summary(artifact)
    _write_artifact(output_path, artifact)
    return artifact


def threshold_analysis(
    runs: list[dict[str, Any]],
    *,
    current_threshold: float,
    relative_floor: float = 0.0,
) -> dict[str, Any]:
    positive_scores: list[float] = []
    negative_scores: list[float] = []
    relative_acceptance_failures: list[dict[str, Any]] = []
    for run in runs:
        entries = run.get("rerank", {}).get("entries", [])
        if not isinstance(entries, list):
            continue
        entry_scores = {
            str(entry.get("memory_id")): float(entry.get("score") or 0.0)
            for entry in entries
            if isinstance(entry, dict) and entry.get("evaluated") is True
        }
        groups = run.get("required_groups", [])
        if groups:
            best_score = max(entry_scores.values(), default=0.0)
            effective_threshold = max(
                current_threshold,
                best_score * relative_floor,
            )
            for group in groups:
                scores = [entry_scores[item] for item in group if item in entry_scores]
                if scores:
                    group_score = max(scores)
                    positive_scores.append(group_score)
                    if group_score < effective_threshold:
                        relative_acceptance_failures.append(
                            {
                                "case_id": run.get("case_id"),
                                "group": group,
                                "score": group_score,
                                "effective_threshold": effective_threshold,
                            }
                        )
        else:
            negative_scores.extend(entry_scores.values())
    positive_floor = min(positive_scores) if positive_scores else None
    negative_ceiling = max(negative_scores) if negative_scores else None
    separated = (
        positive_floor is not None
        and negative_ceiling is not None
        and negative_ceiling < positive_floor
    )
    threshold_within_observed_separation = (
        separated
        and negative_ceiling < current_threshold
        and current_threshold <= positive_floor
        and not relative_acceptance_failures
    )
    return {
        "current_threshold": current_threshold,
        "relative_floor": relative_floor,
        "positive_observation_count": len(positive_scores),
        "negative_observation_count": len(negative_scores),
        "positive_floor": positive_floor,
        "negative_ceiling": negative_ceiling,
        "observed_separation": separated,
        "threshold_within_observed_separation": (threshold_within_observed_separation),
        "relative_acceptance_failures": relative_acceptance_failures,
        "recommendation": (
            "maintain_current_threshold"
            if threshold_within_observed_separation
            else "human_review_required_no_safe_numeric_change"
        ),
        "policy": (
            "Scores summarize the configured reranker's observed separation. "
            "They do not replace semantic review and cannot authorize a "
            "deterministic fallback."
        ),
    }


def _run_case(
    *,
    source_db: Path,
    run_db: Path,
    settings: Settings,
    case: CalibrationCase,
    repetition: int,
    live_scarlet: bool,
) -> dict[str, Any]:
    _fresh_copy(source_db=source_db, run_db=run_db)
    active_settings = settings.model_copy(
        update={
            "environment": "evaluation",
            "database_role": "test",
            "database_url": f"sqlite:///{run_db}",
            "codex_test": False,
            "maintenance_enabled": False,
            "model_context_profile": "v2",
        }
    )
    engine = create_db_engine(active_settings.database_url)
    init_db(engine)
    provider_factory = None
    if not live_scarlet:
        provider_factory = _calibration_probe_provider
    app = create_app(
        active_settings,
        llm_provider_factory=provider_factory,
        db_engine=engine,
    )
    started = perf_counter()
    with TestClient(app) as client:
        session_response = client.post(
            "/api/chat/sessions",
            json={
                "title": f"SCA-3 {case.case_id}",
                "metadata": {"evaluation": CALIBRATION_VERSION},
            },
        )
        session_response.raise_for_status()
        session_id = session_response.json()["id"]
        response = client.post(
            f"/api/chat/sessions/{session_id}/turn",
            json={"message": case.query},
        )
        latency_ms = round((perf_counter() - started) * 1000)
        if response.status_code != 200:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "repetition": repetition,
                "live_scarlet": live_scarlet,
                "required_groups": [list(group) for group in case.required_groups],
                "latency_ms": latency_ms,
                "http_status": response.status_code,
                "passed": False,
                "error": response.json(),
            }
        body = response.json()
        traces_response = client.get(f"/api/debug/traces/{body['turn_id']}")
        traces_response.raise_for_status()
        traces = traces_response.json()

    memory_trace = _trace_payload(traces, "memory.context")
    model_trace = _trace_payload(traces, "model.context")
    rerank = memory_trace.get("query_plan", {}).get("retrieval_rerank", {})
    selected_ids = [
        str(item.get("id"))
        for item in memory_trace.get("selected", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    v2_lanes = _v2_memory_lanes(model_trace)
    v2_ids = {memory_id for lane in v2_lanes.values() for memory_id in lane}
    entries = rerank.get("entries", []) if isinstance(rerank, dict) else []
    matched_groups = [
        sorted(set(group) & set(selected_ids)) for group in case.required_groups
    ]
    pool_groups = [
        sorted(set(group) & _entry_ids(entries)) for group in case.required_groups
    ]
    v2_groups = [sorted(set(group) & v2_ids) for group in case.required_groups]
    route_ok = _required_route_present(
        entries,
        groups=case.required_groups,
        route=case.required_route,
    )
    negative_ok = bool(case.required_groups) or not selected_ids
    forbidden_present = sorted(set(case.forbidden_ids) & set(selected_ids))
    passed = all(
        [
            rerank.get("status") == "completed",
            rerank.get("fail_closed") is True,
            rerank.get("legacy_weighted_fusion") is False,
            all(matched_groups),
            all(pool_groups),
            all(v2_groups),
            not forbidden_present,
            route_ok,
            negative_ok,
        ]
    )
    return {
        "case_id": case.case_id,
        "category": case.category,
        "query": case.query,
        "rationale": case.rationale,
        "repetition": repetition,
        "live_scarlet": live_scarlet,
        "required_groups": [list(group) for group in case.required_groups],
        "optional_relevant_ids": list(case.optional_relevant_ids),
        "forbidden_ids": list(case.forbidden_ids),
        "required_route": case.required_route,
        "http_status": response.status_code,
        "session_id": body["session"]["id"],
        "turn_id": body["turn_id"],
        "latency_ms": latency_ms,
        "answer": body["assistant_message"]["content"],
        "selected_ids": selected_ids,
        "matched_required_groups": matched_groups,
        "pool_required_groups": pool_groups,
        "v2_required_groups": v2_groups,
        "forbidden_present": forbidden_present,
        "unexpected_selected_ids": sorted(
            set(selected_ids)
            - {memory_id for group in case.required_groups for memory_id in group}
            - set(case.optional_relevant_ids)
        ),
        "v2_memory_lanes": v2_lanes,
        "rerank": rerank,
        "retrieval_shadow": memory_trace.get("query_plan", {}).get(
            "retrieval_shadow", {}
        ),
        "negative_evidence": memory_trace.get("negative_evidence"),
        "passed": passed,
    }


def _configuration(settings: Settings) -> dict[str, Any]:
    return {
        "minimax_model": settings.minimax_model,
        "minimax_max_tokens": settings.minimax_max_tokens,
        "retrieval_shadow_enabled": settings.retrieval_shadow_enabled,
        "retrieval_shadow_backend": settings.retrieval_shadow_backend,
        "retrieval_shadow_cloud_surface_limit": (
            settings.retrieval_shadow_cloud_surface_limit
        ),
        "retrieval_shadow_embedding_model": (settings.retrieval_shadow_embedding_model),
        "retrieval_shadow_rerank_enabled": (settings.retrieval_shadow_rerank_enabled),
        "retrieval_shadow_rerank_model": settings.retrieval_shadow_rerank_model,
        "retrieval_shadow_rerank_candidate_limit": (
            settings.retrieval_shadow_rerank_candidate_limit
        ),
        "retrieval_shadow_rerank_top_n": settings.retrieval_shadow_rerank_top_n,
        "retrieval_hybrid_mode": settings.retrieval_hybrid_mode,
        "retrieval_hybrid_min_rerank_score": (
            settings.retrieval_hybrid_min_rerank_score
        ),
        "retrieval_hybrid_relative_rerank_floor": (
            settings.retrieval_hybrid_relative_rerank_floor
        ),
        "model_context_profile": "v2",
    }


def _validate_source_references(
    source_db: Path,
    cases: tuple[CalibrationCase, ...],
) -> None:
    import sqlite3

    connection = sqlite3.connect(f"file:{source_db}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT id, status, source_session_id, source_message_id FROM memories"
        ).fetchall()
    finally:
        connection.close()
    records = {
        str(memory_id): {
            "status": status,
            "source_session_id": source_session_id,
            "source_message_id": source_message_id,
        }
        for memory_id, status, source_session_id, source_message_id in rows
    }
    referenced = {
        memory_id
        for case in cases
        for memory_id in (
            *[item for group in case.required_groups for item in group],
            *case.optional_relevant_ids,
            *case.forbidden_ids,
        )
    }
    missing = sorted(referenced - set(records))
    if missing:
        raise RuntimeError(f"Calibration source is missing memories: {missing}")
    unsourceable = sorted(
        memory_id
        for memory_id in referenced
        if records[memory_id]["status"] == "active"
        and not (
            records[memory_id]["source_session_id"]
            and records[memory_id]["source_message_id"]
        )
    )
    if unsourceable:
        raise RuntimeError(
            f"Calibration source has unsourceable active memories: {unsourceable}"
        )


def _fresh_copy(*, source_db: Path, run_db: Path) -> None:
    _validate_run_path(source_db=source_db, run_db=run_db)
    run_db.parent.mkdir(parents=True, exist_ok=True)
    if run_db.exists():
        run_db.unlink()
    copy2(source_db, run_db)


def _validate_run_path(*, source_db: Path, run_db: Path) -> None:
    if not source_db.exists():
        raise RuntimeError(f"Calibration source does not exist: {source_db}")
    if "memory-rerank" not in run_db.name:
        raise RuntimeError(
            "Disposable run database filename must contain 'memory-rerank'."
        )
    if source_db.resolve() == run_db.resolve():
        raise RuntimeError("Calibration source and run database must differ.")


def _trace_payload(traces: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    trace = next((item for item in traces if item.get("kind") == kind), None)
    if trace is None or not isinstance(trace.get("payload"), dict):
        raise RuntimeError(f"Missing {kind} trace in calibration turn.")
    return trace["payload"]


def _v2_memory_lanes(model_trace: dict[str, Any]) -> dict[str, list[str]]:
    document = model_trace.get("document")
    memories = document.get("memories") if isinstance(document, dict) else None
    lanes: dict[str, list[str]] = {}
    for lane in ("relevant", "recent_user", "recent_general"):
        values = memories.get(lane, []) if isinstance(memories, dict) else []
        lanes[lane] = [
            str(item["id"])
            for item in values
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        ]
    return lanes


def _entry_ids(entries: Any) -> set[str]:
    if not isinstance(entries, list):
        return set()
    return {
        str(entry["memory_id"])
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("memory_id"), str)
    }


def _required_route_present(
    entries: Any,
    *,
    groups: tuple[tuple[str, ...], ...],
    route: str | None,
) -> bool:
    if route is None:
        return True
    required_ids = {memory_id for group in groups for memory_id in group}
    if not isinstance(entries, list):
        return False
    return any(
        isinstance(entry, dict)
        and entry.get("memory_id") in required_ids
        and route in entry.get("recall_routes", [])
        for entry in entries
    )


def _summary(artifact: dict[str, Any]) -> dict[str, Any]:
    probe_runs = artifact["probe_runs"]
    live_runs = artifact["live_scarlet_runs"]
    return {
        "probe_passed": sum(run.get("passed") is True for run in probe_runs),
        "probe_total": len(probe_runs),
        "live_technical_passed": sum(run.get("passed") is True for run in live_runs),
        "live_total": len(live_runs),
        "source_unchanged": artifact["source_database"].get("unchanged"),
        "human_semantic_review_required": bool(live_runs),
    }


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_artifact(path: Path, artifact: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calibrate final memory reranking on frozen real references."
    )
    parser.add_argument("--source-db", default=DEFAULT_SOURCE_DB)
    parser.add_argument("--run-db", default=DEFAULT_RUN_DB)
    parser.add_argument("--output")
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--live-scarlet", action="store_true")
    parser.add_argument(
        "--live-only",
        action="store_true",
        help="Run only the cases marked for real-Scarlet semantic review.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.repetitions < 1 and not args.live_only:
        raise RuntimeError("repetitions must be at least 1")
    if args.live_only and not args.live_scarlet:
        raise RuntimeError("--live-only requires --live-scarlet")
    root = Path(__file__).resolve().parents[2]
    source_db = _resolve(root, args.source_db)
    run_db = _resolve(root, args.run_db)
    output = (
        _resolve(root, args.output)
        if args.output
        else root
        / "app"
        / "evals"
        / "runs"
        / (datetime.now(UTC).strftime("%Y%m%d_%H%M%S_") + CALIBRATION_VERSION + ".json")
    )
    artifact = run_calibration(
        source_db=source_db,
        run_db=run_db,
        output_path=output,
        repetitions=0 if args.live_only else args.repetitions,
        run_live_scarlet=args.live_scarlet,
        settings=Settings(),
    )
    print(
        json.dumps(
            {"output": str(output), **artifact["summary"]},
            ensure_ascii=False,
            indent=2,
        )
    )


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _calibration_probe_provider(settings: Settings) -> CalibrationProbeProvider:
    return CalibrationProbeProvider(settings)


if __name__ == "__main__":
    main()
