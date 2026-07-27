from __future__ import annotations

from datetime import timedelta
import json

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.llm.provider import LLMStreamEvent, LLMTextResult, LLMToolRunner, LLMToolUse
from app.main import create_app
from app.runtime.autonomy import run_autonomous_activation
from app.runtime.cognitive_workspace import run_cognitive_workspace_tick
from app.storage import repositories
from app.storage.db import init_db
from app.storage.models import utc_now


class EndogenousProvider:
    models: list[str] = []
    empty = False

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.__class__.models.append(settings.minimax_model)

    def generate_text(self, *, prompt: str, system=None, max_tokens=None):
        payload = json.loads(prompt)
        if "cognitive_window" in payload:
            if self.__class__.empty:
                text = json.dumps(
                    {
                        "schema_version": "endogenous-impulse-seeds-v1",
                        "seeds": [],
                        "no_seed_reason": "No useful transformation is available.",
                    }
                )
            else:
                memory = next(
                    item
                    for item in payload["substrate"]
                    if item["source_kind"] == "memory"
                )
                session = next(
                    item
                    for item in payload["substrate"]
                    if item["source_kind"] == "session"
                )
                text = json.dumps(
                    {
                        "schema_version": "endogenous-impulse-seeds-v1",
                        "seeds": [
                            {
                                "impulse_family": "relationship",
                                "context_family": "relationship_continuity",
                                "source_refs": [
                                    memory["source_ref"],
                                    session["source_ref"],
                                ],
                                "claim": (
                                    "A recent relational memory may connect to "
                                    "the latest human conversation."
                                ),
                                "why_now": (
                                    "A free cognitive window is available and "
                                    "both sources are recent."
                                ),
                                "cognitive_question": (
                                    "Does this connection deserve a durable "
                                    "self-chosen direction?"
                                ),
                                "expected_transformation": (
                                    "Scarlet accepts, suspends, or rejects the "
                                    "connection after inspecting its sources."
                                ),
                                "uncertainty": "medium",
                                "wake_recommendation": "consider",
                                "reason": "The sources support a bounded inquiry.",
                            }
                        ],
                        "no_seed_reason": None,
                    }
                )
        else:
            candidate_id = payload["candidates"][0]["id"]
            text = json.dumps(
                {
                    "schema_version": "cognitive-ignition-v1",
                    "ignite": "now",
                    "coalitions": [
                        {
                            "candidate_ids": [candidate_id],
                            "reason": "The sourced seed can be decided now.",
                            "proposed_episode_question": (
                                "Does this become Scarlet's own direction?"
                            ),
                            "expected_transformation": (
                                "A traceable M3 decision over the seed."
                            ),
                        }
                    ],
                    "deferred": [],
                    "rejected_ids": [],
                    "rationale": "A bounded transformation is available.",
                }
            )
        return LLMTextResult(
            model=self.settings.minimax_model,
            text=text,
            stop_reason="end_turn",
        )


class EndorsingScarletProvider:
    candidate_id = ""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def stream_chat_with_tools(
        self,
        *,
        messages,
        system=None,
        max_tokens=None,
        tools,
        tool_runner: LLMToolRunner,
        max_tool_calls=None,
    ):
        note = "Scelgo se questo filo merita di diventare una mia direzione."
        yield LLMStreamEvent(type="assistant_note", data={"text": note})
        command = (
            'volition create "Comprendere questo filo relazionale nel tempo" '
            '--reason "Lo riconosco come una mia direzione interna" '
            f"--candidate-id {self.candidate_id}"
        )
        executed = tool_runner(
            LLMToolUse(
                id="toolu_endogenous_volition",
                name="mind_shell",
                input={
                    "command": command,
                    "intent": "Endorse the provisional seed as my own volition.",
                },
            )
        )
        answer = "Checkpoint interno: ho scelto di mantenere questo filo."
        result = LLMTextResult(
            model=self.settings.minimax_model,
            text=answer,
            usage={"input_tokens": 120, "output_tokens": 24},
            provider_message_id="provider_endogenous_endorsement",
            raw_content=[{"type": "text", "text": answer}],
            raw_provider_messages=[
                {
                    "id": "provider_endogenous_tool",
                    "stop_reason": "tool_use",
                    "content": [
                        {"type": "text", "text": note},
                        {
                            "type": "tool_use",
                            "id": "toolu_endogenous_volition",
                            "name": "mind_shell",
                            "input": {
                                "command": command,
                                "intent": (
                                    "Endorse the provisional seed as my own volition."
                                ),
                            },
                        },
                    ],
                },
                {
                    "id": "provider_endogenous_endorsement",
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": answer}],
                },
            ],
            stop_reason="end_turn",
            tool_calls=[executed],
        )
        yield LLMStreamEvent(type="assistant_answer", data={"text": answer})
        yield LLMStreamEvent(
            type="final_result",
            data={"result": result.model_dump(mode="json")},
        )


def _settings(**overrides) -> Settings:
    values = {
        "agent_system_prompt": "You are Scarlet.",
        "maintenance_enabled": False,
        "autonomous_activation_enabled": False,
        "cognitive_workspace_mode": "active",
        "endogenous_cognition_enabled": True,
        "endogenous_cognition_min_interval_seconds": 300,
        "endogenous_cognition_productive_followup_seconds": 600,
        "endogenous_cognition_base_interval_seconds": 900,
        "endogenous_cognition_max_interval_seconds": 3600,
    }
    values.update(overrides)
    return Settings(
        **values,
    )


def _seed_human_continuity(engine: Engine) -> tuple[str, str]:
    with Session(engine) as db:
        session = repositories.create_chat_session(
            db,
            title="Una conversazione reale",
            profile_id="local-user",
        )
        turn = repositories.create_turn(
            db,
            session_id=session.id,
            model="MiniMax-M3",
        )
        user_message = repositories.add_message(
            db,
            session_id=session.id,
            turn_id=turn.id,
            role="user",
            content="Mi farebbe piacere riprendere questa cosa con calma.",
        )
        repositories.add_message(
            db,
            session_id=session.id,
            turn_id=turn.id,
            role="assistant",
            content="La terrò come un filo da non forzare.",
        )
        repositories.complete_turn(db, turn_id=turn.id)
        repositories.upsert_session_summary(
            db,
            session_id=session.id,
            summary=(
                "L'utente ha lasciato aperto un filo personale da riprendere "
                "con calma."
            ),
            source_turn_count=1,
            message_count=2,
            last_message_id=repositories.latest_message_for_turn(
                db,
                turn_id=turn.id,
                role="assistant",
            ).id,
        )
        memory = repositories.add_memory(
            db,
            memory_type="user_preference",
            scope="user",
            content="L'utente preferisce che i fili personali non vengano forzati.",
            reason_for_storage="Aiuta la continuità relazionale.",
            source_session_id=session.id,
            source_turn_id=turn.id,
            source_message_id=user_message.id,
        )
        node, _ = repositories.upsert_memory_graph_node(
            db,
            node_key=f"memory:{memory.id}:relationship",
            node_type="relationship_thread",
            label="ritmo relazionale non forzato",
            scope="user",
            source_memory_id=memory.id,
            source_session_id=session.id,
        )
        second, _ = repositories.upsert_memory_graph_node(
            db,
            node_key=f"memory:{memory.id}:continuity",
            node_type="concept",
            label="continuità nel tempo",
            scope="user",
            source_memory_id=memory.id,
            source_session_id=session.id,
        )
        repositories.upsert_memory_graph_edge(
            db,
            edge_key=f"memory:{memory.id}:relationship-continuity",
            source_node_id=node.id,
            target_node_id=second.id,
            relation="supports",
            source_memory_id=memory.id,
            source_session_id=session.id,
        )
        return session.id, memory.id


def test_endogenous_window_proposes_source_backed_seed_and_schedules_m3(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    EndogenousProvider.models = []
    EndogenousProvider.empty = False
    _, memory_id = _seed_human_continuity(db_engine)
    now = utc_now()

    result = run_cognitive_workspace_tick(
        db_engine,
        settings=_settings(),
        provider_factory=EndogenousProvider,
        now=now,
    )

    assert result["endogenous"]["status"] == "seeds_proposed"
    assert result["endogenous"]["candidate_ids"]
    assert result["ignition"]["activation_id"] is not None
    assert EndogenousProvider.models == ["MiniMax-M2.7", "MiniMax-M2.7"]
    with Session(db_engine) as db:
        window = repositories.latest_endogenous_window(
            db,
            profile_id="local-user",
        )
        assert window is not None
        assert window.activation_id == result["ignition"]["activation_id"]
        assert f"memory:{memory_id}" in window.source_refs_json
        candidate = repositories.get_candidate(
            db,
            window.candidate_ids_json[0],
        )
        assert candidate is not None
        assert candidate.candidate_kind == "endogenous_relationship"
        assert candidate.metadata_json["m3_endorsement_required"] is True
        activation = next(
            item
            for item in repositories.list_autonomous_activations(
                db,
                profile_id="local-user",
                limit=10,
            )
            if item.id == result["ignition"]["activation_id"]
        )
        assert activation.workspace_json["endogenous"]["window_id"] == window.id
        assert activation.workspace_json["selected_candidate_ids"] == [candidate.id]


def test_empty_endogenous_windows_back_off_without_waking_m3(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    EndogenousProvider.models = []
    EndogenousProvider.empty = True
    _seed_human_continuity(db_engine)
    settings = _settings()
    now = utc_now()

    first = run_cognitive_workspace_tick(
        db_engine,
        settings=settings,
        provider_factory=EndogenousProvider,
        now=now,
    )
    second = run_cognitive_workspace_tick(
        db_engine,
        settings=settings,
        provider_factory=EndogenousProvider,
        now=now + timedelta(seconds=1800),
    )

    assert first["endogenous"]["status"] == "empty"
    assert first["endogenous"]["cadence_seconds"] == 1800
    assert first["ignition"].get("activation_id") is None
    assert second["endogenous"]["status"] == "empty"
    assert second["endogenous"]["cadence_seconds"] == 3600
    assert second["ignition"].get("activation_id") is None
    assert EndogenousProvider.models == ["MiniMax-M2.7", "MiniMax-M2.7"]


def test_scarlet_can_endorse_seed_as_linked_volition(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    EndogenousProvider.models = []
    EndogenousProvider.empty = False
    _seed_human_continuity(db_engine)
    settings = _settings(autonomous_activation_enabled=True)
    workspace = run_cognitive_workspace_tick(
        db_engine,
        settings=settings,
        provider_factory=EndogenousProvider,
        now=utc_now(),
    )
    candidate_id = workspace["endogenous"]["candidate_ids"][0]
    activation_id = workspace["ignition"]["activation_id"]
    EndorsingScarletProvider.candidate_id = candidate_id

    result = run_autonomous_activation(
        db_engine,
        settings=settings,
        provider_factory=EndorsingScarletProvider,
        activation_id=activation_id,
        now=utc_now(),
    )

    assert result["status"] == "completed"
    with Session(db_engine) as db:
        candidate = repositories.get_candidate(db, candidate_id)
        assert candidate is not None
        assert candidate.status == "resolved"
        assert candidate.resolution is not None
        assert candidate.resolution.startswith("endorsed_as_volition:intent_")
        window = repositories.latest_endogenous_window(
            db,
            profile_id="local-user",
        )
        assert window is not None
        outcome = window.outcome_json["activation_outcome"]
        assert outcome["transformation_observed"] is True
        intentions = repositories.list_open_intention_records(
            db,
            owner_profile_id="local-user",
        )
        assert len(intentions) == 1
        links = repositories.list_intention_links(
            db,
            intention_id=intentions[0].id,
        )
        assert links[0].target_type == "candidate"
        assert links[0].target_id == candidate_id


def test_device_adapter_admits_only_bounded_transitions(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    app = create_app(
        settings=_settings(device_perception_admission_mode="active"),
        llm_provider_factory=EndogenousProvider,
        db_engine=db_engine,
    )
    now = utc_now()
    with TestClient(app) as client:
        response = client.post(
            "/api/device-exploration/observations/batch",
            json={
                "observations": [
                    {
                        "client_event_id": "device-transition-1",
                        "run_id": "run-1",
                        "device_id": "device-1",
                        "probe": "network",
                        "event_type": "status_change",
                        "source": "capacitor",
                        "app_state": "active",
                        "observed_at": now.isoformat(),
                        "payload": {"connected": True, "connectionType": "wifi"},
                        "normalized": {
                            "connected": True,
                            "transport": "wifi",
                        },
                        "metadata": {},
                    },
                    {
                        "client_event_id": "raw-motion-1",
                        "run_id": "run-1",
                        "device_id": "device-1",
                        "probe": "motion",
                        "event_type": "sample",
                        "source": "capacitor",
                        "app_state": "active",
                        "observed_at": now.isoformat(),
                        "payload": {"acceleration": 1.0},
                        "normalized": {"acceleration_magnitude": 1.0},
                        "metadata": {},
                    },
                ]
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] == 2
    assert [item["status"] for item in payload["cognitive_admission"]] == [
        "admitted",
        "not_admitted",
    ]
    with Session(db_engine) as db:
        events = repositories.list_perception_events(
            db,
            profile_id="local-user",
            limit=10,
        )
        assert len(events) == 1
        assert events[0].event_type == "device.network.changed"
        assert events[0].payload_json["state"] == {
            "connected": True,
            "transport": "wifi",
        }
        assert events[0].metadata_json["human_state_inference"] is False
