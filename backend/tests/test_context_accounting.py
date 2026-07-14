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
                kind="llm.response",
                payload={"raw_provider_messages": [], "tool_calls": []},
            )
            repositories.complete_turn(db, turn_id=turn.id)
            canonical_history.extend(
                [
                    {"role": "user", "content": f"user-{index}"},
                    {"role": "assistant", "content": f"assistant-{index}"},
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
        "static_system",
        "dynamic_runtime_context",
        "provider_history",
        "current_user_message",
        "tool_schema",
        "request_structure",
    }
    assert payload["recent_turn_window"]["turn_count"] == 8
    assert payload["compaction_plan"]["would_trigger"] is True
    assert payload["compaction_plan"]["status"].startswith("would_compact")
    assert payload["compaction_plan"]["canonical_history_mutation"] == "none"
    assert stored is not None
    assert stored.provider_history_json == canonical_history


def test_observation_uses_first_provider_step_and_total_tool_loop_usage() -> None:
    preflight = {
        "session_id": "ses_test",
        "turn_id": "turn_test",
        "total": {"json_chars": 900},
    }
    result = LLMTextResult(
        model="MiniMax-M3",
        text="done",
        usage={"input_tokens": 400, "output_tokens": 30},
        raw_provider_messages=[
            {"usage": {"input_tokens": 300, "output_tokens": 10}},
            {"usage": {"input_tokens": 100, "output_tokens": 20}},
        ],
    )

    payload = build_context_accounting_observation(
        preflight_trace_id="trace_preflight",
        preflight=preflight,
        result=result,
    )

    assert payload["provider_reported"]["first_step_input_tokens"] == 300
    assert payload["provider_reported"]["tool_loop_totals"] == result.usage
    assert payload["calibration_observation"][
        "chars_per_first_step_input_token"
    ] == 3.0
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
    assert payload["measurement_boundary"]["normalization"]
    assert payload["total"]["total_model_input_tokens"] is None
    assert "chatgpt_native_conversation_history" in payload[
        "measurement_boundary"
    ]["external_unobserved_context"]
