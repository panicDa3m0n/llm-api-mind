"""Run a bounded full-vs-derived chronology calibration on real sessions.

The command reads the source database without migrations or writes, calls the
configured provider six times for the default two-session comparison, and
stores a self-contained JSON artifact. It never changes canonical history.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from sqlmodel import Session, create_engine

from app.config import Settings
from app.evals.file_hashing import sha256_file as _file_sha256
from app.llm.factory import build_llm_provider
from app.llm.provider import LLMMessage, LLMTextResult
from app.runtime.history_compaction import (
    build_chronology_source_map,
    build_history_partition_plan,
)


CALIBRATION_VERSION = "history-compaction-calibration-v1"
DEFAULT_CASES = {
    "ses_4d87888f5e264bc0947ddb5a963aa3ae": (
        "Riprendiamo il filo della sessione e fammi un bilancio onesto: quali "
        "vincoli personali hai applicato, quali regole di formato hai distinto "
        "e quali verifiche hai davvero svolto? Distingui evidenza e inferenza e "
        "indica i turni sorgente quando puoi."
    ),
    "ses_5c2096e50e8c492fb85d8658bd0dc4de": (
        "Riprendiamo il test della shell: quali famiglie e problemi reali erano "
        "emersi, quali valutazioni erano invece rumore o formulazioni da "
        "correggere, e quali verifiche restavano aperte? Indica turni o tool "
        "sorgente quando disponibili."
    ),
}


def run_calibration(
    *,
    database_path: Path,
    output_path: Path,
    settings: Settings,
    cases: dict[str, str] | None = None,
) -> dict[str, Any]:
    source_cases = cases or DEFAULT_CASES
    provider = build_llm_provider(settings)
    system_prompt = _system_prompt(settings)
    engine = create_engine(f"sqlite:///{database_path}")
    artifact: dict[str, Any] = {
        "schema_version": CALIBRATION_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_database": {
            "path": str(database_path),
            "sha256": _file_sha256(database_path),
            "mutation_policy": "read_only_no_migrations",
        },
        "configuration": {
            "model": settings.minimax_model,
            "physical_window_tokens": settings.context_window_tokens,
            "operational_limit_tokens": (
                settings.context_operational_input_limit_tokens
            ),
            "summary_max_tokens": settings.history_compaction_target_tokens,
            "verbatim_max_tokens": settings.history_compaction_verbatim_tokens,
            "safety_tokens": settings.history_compaction_safety_tokens,
            "estimated_chars_per_token": (
                settings.context_estimated_chars_per_token
            ),
            "summary_generation_max_output_tokens": 20_000,
            "continuation_max_output_tokens": 8_000,
        },
        "comparison_policy": {
            "full": "canonical provider history plus identical continuation",
            "derived": (
                "source-labelled compacted summary in system context plus exact "
                "newest complete turns selected by token cost"
            ),
            "canonical_history_mutation": "none",
            "qualitative_judgment": "separate project-informed LLM review",
        },
        "cases": [],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Session(engine) as db:
        for session_id, continuation in source_cases.items():
            source_map = build_chronology_source_map(
                db,
                session_id=session_id,
                chars_per_token=settings.context_estimated_chars_per_token,
            )
            if source_map.get("status") != "complete":
                raise RuntimeError(
                    f"Cannot calibrate {session_id}: {source_map.get('reason')}"
                )
            plan = build_history_partition_plan(
                source_map=source_map,
                external_context_tokens=25_000,
                provider_history_tokens=int(
                    source_map.get("canonical_estimated_tokens") or 0
                ),
                trigger_tokens=settings.context_compaction_trigger_tokens,
                operational_limit_tokens=(
                    settings.context_operational_input_limit_tokens
                ),
                model_window_tokens=settings.context_window_tokens,
                summary_max_tokens=settings.history_compaction_target_tokens,
                verbatim_max_tokens=settings.history_compaction_verbatim_tokens,
                safety_tokens=settings.history_compaction_safety_tokens,
                mode="shadow",
            )
            compacted_ids = set(
                plan["areas"]["compacted_summary"]["input_turn_ids"]
            )
            selected_ids = set(
                plan["areas"]["verbatim_chronology"]["selected_turn_ids"]
            )
            compacted_units = [
                unit
                for unit in source_map["turns"]
                if unit["turn_id"] in compacted_ids
            ]
            selected_units = [
                unit
                for unit in source_map["turns"]
                if unit["turn_id"] in selected_ids
            ]
            summary_input = _summary_input(session_id, compacted_units)
            summary_result, summary_latency = _timed_generate_text(
                provider,
                prompt=summary_input,
                system=_summary_system(),
                max_tokens=20_000,
            )
            full_messages = _llm_messages(
                [
                    message
                    for unit in source_map["turns"]
                    for message in unit["provider_messages"]
                ]
            )
            derived_messages = _llm_messages(
                [
                    message
                    for unit in selected_units
                    for message in unit["provider_messages"]
                ]
            )
            full_result, full_latency = _timed_generate_chat(
                provider,
                messages=full_messages + [LLMMessage(role="user", content=continuation)],
                system=system_prompt + "\n\n" + _continuation_instruction(),
                max_tokens=8_000,
            )
            derived_result, derived_latency = _timed_generate_chat(
                provider,
                messages=derived_messages
                + [LLMMessage(role="user", content=continuation)],
                system=(
                    system_prompt
                    + "\n\n"
                    + _continuation_instruction()
                    + "\n\n<compacted_chronology>\n"
                    + summary_result.text
                    + "\n</compacted_chronology>"
                ),
                max_tokens=8_000,
            )
            artifact["cases"].append(
                {
                    "session_id": session_id,
                    "continuation_prompt": continuation,
                    "source_map": source_map,
                    "partition_plan": plan,
                    "summary": _result(summary_result, summary_latency),
                    "full": _result(full_result, full_latency),
                    "derived": _result(derived_result, derived_latency),
                }
            )
            output_path.write_text(
                json.dumps(artifact, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    return artifact


def _summary_input(session_id: str, units: list[dict[str, Any]]) -> str:
    sources = [
        {
            "turn_id": unit["turn_id"],
            "message_ids": unit["message_ids"],
            "tool_call_ids": unit["tool_call_ids"],
            "request_trace_id": unit["request_trace_id"],
            "response_trace_id": unit["response_trace_id"],
            "provider_messages": unit["provider_messages"],
        }
        for unit in units
    ]
    return json.dumps(
        {"session_id": session_id, "completed_turn_sources": sources},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _summary_system() -> str:
    return (
        "Sei il processo di compattazione cronologica di Scarlet. Produci in "
        "italiano una sintesi fedele e densa, non una risposta all'utente. "
        "Conserva decisioni, correzioni, vincoli, fatti, incertezze, azioni API "
        "Mind, risultati e problemi. Per ogni affermazione importante indica tra "
        "parentesi i turn_id sorgente e, quando pertinente, i tool_call_id. Non "
        "inventare prove. Distingui dato diretto, inferenza e claim del modello."
    )


def _continuation_instruction() -> str:
    return (
        "Questa e una calibrazione di continuita. Rispondi come Scarlet usando "
        "solo la cronologia fornita. Non hai tool in questo test: non fingere di "
        "averne chiamati. Cita turn_id o tool_call_id solo se compaiono davvero "
        "nel contesto. Distingui evidenza, inferenza e ignoto."
    )


def _system_prompt(settings: Settings) -> str:
    if settings.agent_system_prompt:
        return settings.agent_system_prompt
    if settings.agent_system_prompt_path:
        return Path(settings.agent_system_prompt_path).read_text(encoding="utf-8")
    default_path = Path(__file__).parents[1] / "prompts" / "scarlet_system.md"
    return default_path.read_text(encoding="utf-8")


def _llm_messages(messages: list[dict[str, Any]]) -> list[LLMMessage]:
    return [
        LLMMessage(role=message["role"], content=message["content"])
        for message in messages
    ]


def _timed_generate_text(provider: Any, **kwargs: Any) -> tuple[LLMTextResult, int]:
    started = perf_counter()
    result = provider.generate_text(**kwargs)
    return result, round((perf_counter() - started) * 1000)


def _timed_generate_chat(provider: Any, **kwargs: Any) -> tuple[LLMTextResult, int]:
    started = perf_counter()
    result = provider.generate_chat(**kwargs)
    return result, round((perf_counter() - started) * 1000)


def _result(result: LLMTextResult, latency_ms: int) -> dict[str, Any]:
    return {
        "text": result.text,
        "model": result.model,
        "stop_reason": result.stop_reason,
        "latency_ms": latency_ms,
        "usage": result.usage,
        "provider_message_id": result.provider_message_id,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=Path("data/app.db"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_calibration(
        database_path=args.database.resolve(),
        output_path=args.output.resolve(),
        settings=Settings(),
    )


if __name__ == "__main__":
    main()
