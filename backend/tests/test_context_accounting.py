from sqlmodel import Session

from app.config import Settings
from app.llm.provider import LLMMessage, LLMTextResult
from app.runtime.context_accounting import (
    build_context_accounting_observation,
    build_context_accounting_preflight,
    build_external_context_accounting_preflight,
)
from app.storage import repositories
from app.storage.db import init_db


def _settings(**updates) -> Settings:
    return Settings(
        context_window_tokens=1_000,
        context_operational_input_limit_tokens=500,
        context_compaction_trigger_tokens=100,
        history_compaction_target_tokens=50,
        history_compaction_verbatim_tokens=200,
        history_compaction_safety_tokens=20,
        history_compaction_recent_turns=8,
        context_estimated_chars_per_token=2.0,
        **updates,
    )


def test_preflight_accounts_channels_and_plans_shadow_compaction(db_engine) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(db, title="Long session")
        canonical_history = []
        for index in range(10):
            turn = repositories.create_turn(
                db,
                session_id=chat_session.id,
                model="MiniMax-M3",
            )
            repositories.add_message(
                db,
                session_id=chat_session.id,
                turn_id=turn.id,
                role="user",
                content=f"user-{index}-" + ("x" * 80),
            )
            repositories.add_message(
                db,
                session_id=chat_session.id,
                turn_id=turn.id,
                role="assistant",
                content=f"assistant-{index}-" + ("y" * 80),
            )
            repositories.add_trace(
                db,
                session_id=chat_session.id,
                turn_id=turn.id,
                kind="llm.request",
                payload={
                    "provider_messages": canonical_history
                    + [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"user-{index}-" + ("x" * 80),
                                }
                            ],
                        }
                    ]
                },
            )
            repositories.add_trace(
                db,
                session_id=chat_session.id,
                turn_id=turn.id,
                kind="llm.response",
                payload={"raw_provider_messages": [], "tool_calls": []},
            )
            repositories.complete_turn(db, turn_id=turn.id)
            canonical_history.extend(
                [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"user-{index}-" + ("x" * 80),
                            }
                        ],
                    },
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "text",
                                "text": f"assistant-{index}-" + ("y" * 80),
                            }
                        ],
                    },
                ]
            )
        repositories.update_chat_session_provider_history(
            db,
            session_id=chat_session.id,
            provider_history=canonical_history,
        )
        current = repositories.create_turn(
            db,
            session_id=chat_session.id,
            model="MiniMax-M3",
        )
        payload = build_context_accounting_preflight(
            db,
            session_id=chat_session.id,
            turn_id=current.id,
            model="MiniMax-M3",
            transport="native",
            base_system="system policy",
            runtime_context="runtime evidence",
            messages=[
                LLMMessage(role=item["role"], content=item["content"])
                for item in canonical_history
            ]
            + [LLMMessage(role="user", content="current question")],
            tools=[{"name": "mind_shell"}],
            settings=_settings(),
        )
        stored = repositories.get_chat_session(db, chat_session.id)

    assert set(payload["channels"]) == {
        "static_system_policy",
        "model_context_packet",
        "provider_history",
        "current_user_message",
        "mind_shell_tool_schema",
        "request_structure",
    }
    assert payload["accounting_surface"] == "native_model_request"
    assert payload["chronology_source_map"]["mapping_verified"] is True
    assert payload["chronology_source_map"]["turn_count"] == 10
    assert payload["compaction_plan"]["would_trigger"] is True
    assert payload["compaction_plan"]["status"] == "would_recompact"
    assert payload["compaction_plan"]["areas"]["verbatim_chronology"][
        "selected_turn_count"
    ] < 10
    assert payload["compaction_plan"]["canonical_history_mutation"] == "none"
    assert stored is not None
    assert stored.provider_history_json == canonical_history


def test_observation_uses_first_provider_step_and_total_tool_loop_usage() -> None:
    preflight = {
        "session_id": "ses_test",
        "turn_id": "turn_test",
        "total": {"json_chars": 900},
        "compaction_plan": {"mode": "shadow", "shadow_only": True},
    }
    result = LLMTextResult(
        model="MiniMax-M3",
        text="done",
        usage={"input_tokens": 400, "output_tokens": 30},
        raw_provider_messages=[
            {
                "usage": {
                    "input_tokens": 30,
                    "cache_read_input_tokens": 250,
                    "cache_creation_input_tokens": 20,
                    "output_tokens": 10,
                }
            },
            {
                "usage": {
                    "input_tokens": 10,
                    "cache_read_input_tokens": 390,
                    "output_tokens": 20,
                }
            },
        ],
    )

    payload = build_context_accounting_observation(
        preflight_trace_id="trace_preflight",
        preflight=preflight,
        result=result,
    )

    assert payload["provider_reported"]["first_step_input_tokens"] == 300
    assert payload["provider_reported"][
        "maximum_step_effective_input_tokens"
    ] == 400
    assert [step["effective_input_tokens"] for step in payload[
        "provider_reported"
    ]["steps"]] == [300, 400]
    assert payload["provider_reported"]["tool_loop_totals"] == result.usage
    assert payload["calibration_observation"][
        "chars_per_first_step_input_token"
    ] == 3.0
    assert payload["canonical_history_mutated"] is False
    assert payload["compaction_plan_mode"] == "shadow"
    assert payload["compaction_plan_was_shadow_only"] is True


def test_observed_accounting_reports_active_compaction_mode() -> None:
    payload = build_context_accounting_observation(
        preflight_trace_id="trace_preflight",
        preflight={
            "session_id": "ses_active",
            "turn_id": "turn_active",
            "model": "MiniMax-M3",
            "total": {"json_chars": 100},
            "compaction_plan": {
                "mode": "active",
                "shadow_only": False,
            },
        },
        result=LLMTextResult(
            text="done",
            model="MiniMax-M3",
            usage={},
        ),
    )

    assert payload["compaction_plan_mode"] == "active"
    assert payload["compaction_plan_was_shadow_only"] is False
    assert payload["canonical_history_mutated"] is False


def test_external_accounting_never_claims_total_chatgpt_input() -> None:
    payload = build_external_context_accounting_preflight(
        session_id="ses_test",
        turn_id="turn_test",
        transport="gpt_bridge_bootstrap",
        payload={"runtime_context": "evidence", "provider_messages_recent": []},
        settings=_settings(),
    )

    assert payload["measurement_boundary"]["is_total_model_input"] is False
    assert payload["accounting_surface"] == "gpt_bridge_backend_packet_only"
    assert payload["measurement_boundary"]["normalization"]
    assert payload["total"]["total_model_input_tokens"] is None
    assert "chatgpt_native_conversation_history" in payload[
        "measurement_boundary"
    ]["external_unobserved_context"]


def test_preflight_calibration_ignores_incompatible_v1_observations(
    db_engine,
) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        chat_session = repositories.create_chat_session(db, title="Calibration")
        turn = repositories.create_turn(
            db,
            session_id=chat_session.id,
            model="MiniMax-M3",
        )
        for version, ratio in [
            ("context-accounting-v1", 10.0),
            ("context-accounting-v2", 4.0),
        ]:
            repositories.add_trace(
                db,
                session_id=chat_session.id,
                turn_id=turn.id,
                kind="context.accounting.observed",
                payload={
                    "schema_version": version,
                    "model": "MiniMax-M3",
                    "calibration_observation": {
                        "chars_per_first_step_input_token": ratio
                    },
                },
            )

        payload = build_context_accounting_preflight(
            db,
            session_id=chat_session.id,
            turn_id=turn.id,
            model="MiniMax-M3",
            transport="native",
            base_system="policy",
            runtime_context="runtime",
            messages=[LLMMessage(role="user", content="question")],
            tools=[{"name": "mind_shell"}],
            settings=_settings(),
        )

    assert payload["calibration"]["sample_count"] == 1
    assert payload["calibration"]["chars_per_token_used"] == 4.0
