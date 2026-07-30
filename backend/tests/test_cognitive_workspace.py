from __future__ import annotations

from datetime import timedelta
import json

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.llm.provider import LLMStreamEvent, LLMTextResult
from app.mind.contracts import MindAPIContext
from app.mind.workspace_contracts import (
    APPRAISAL_SCHEMA_VERSION,
    CognitiveAppraisalBatch,
    CognitiveSignalEnvelope,
    appraisal_prompt,
)
from app.mind.shell import MindShellRequest, dispatch_mind_shell
from app.runtime.cognitive_workspace import run_cognitive_workspace_tick
from app.runtime.autonomy import (
    run_autonomous_activation,
    run_due_autonomous_activations,
)
from app.runtime.events import record_event
from app.mind.wake_registry import classify_wake_source
from app.storage import repositories
from app.storage.db import init_db
from app.storage.models import utc_now


class WorkspaceProvider:
    models: list[str] = []

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.__class__.models.append(settings.minimax_model)

    def generate_text(self, *, prompt: str, system=None, max_tokens=None):
        payload = json.loads(prompt)
        if "signals" in payload:
            appraisals = [
                {
                    "source_refs": [signal["source_ref"]],
                    "disposition": "candidate",
                    "candidate_kind": "continuity_question",
                    "context_family": signal["context_family"],
                    "claim": signal["summary"],
                    "why_now": "The completed human turn may contain an open loop.",
                    "cognitive_question": "Did the exchange leave useful unfinished work?",
                    "expected_transformation": "A sourced decision to act, suspend, or reject.",
                    "uncertainty": "medium",
                    "wake_recommendation": "consider",
                    "reason": "The source is a completed human exchange.",
                }
                for signal in payload["signals"]
            ]
            text = json.dumps(
                {
                    "schema_version": APPRAISAL_SCHEMA_VERSION,
                    "appraisals": appraisals,
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
                            "reason": "One bounded source-backed inquiry is available.",
                            "proposed_episode_question": "What remains unresolved?",
                            "expected_transformation": "A traceable Scarlet decision.",
                        }
                    ],
                    "deferred": [],
                    "rejected_ids": [],
                    "rationale": "The inquiry can produce a concrete transformation.",
                }
            )
        return LLMTextResult(
            model=self.settings.minimax_model,
            text=text,
            stop_reason="end_turn",
        )


class ActiveCycleProvider(WorkspaceProvider):
    def stream_chat_with_tools(
        self,
        *,
        messages,
        system=None,
        max_tokens=None,
        tools,
        tool_runner,
        max_tool_calls=None,
    ):
        result = LLMTextResult(
            model=self.settings.minimax_model,
            text=(
                "Checkpoint interno: ho esaminato il filo emerso e non serve "
                "un'altra azione adesso."
            ),
            stop_reason="end_turn",
        )
        yield LLMStreamEvent(
            type="assistant_note",
            data={"text": "Esamino il filo che ha richiesto la mia attenzione."},
        )
        yield LLMStreamEvent(
            type="assistant_answer",
            data={"text": result.text},
        )
        yield LLMStreamEvent(
            type="final_result",
            data={"result": result.model_dump(mode="json")},
        )


def _settings(mode: str = "shadow") -> Settings:
    return Settings(
        agent_system_prompt="You are Scarlet.",
        maintenance_enabled=False,
        cognitive_workspace_mode=mode,
        endogenous_cognition_enabled=False,
        autonomous_activation_interval_seconds=600,
    )


def test_cognitive_workspace_defaults_to_active() -> None:
    settings = Settings(_env_file=None)

    assert settings.cognitive_workspace_mode == "active"
    assert settings.endogenous_cognition_enabled is True


def _completed_human_turn(engine: Engine, *, content: str = "Ne riparliamo domani.") -> str:
    with Session(engine) as db:
        session = repositories.create_chat_session(
            db,
            title="Human continuity",
            profile_id="local-user",
        )
        turn = repositories.create_turn(
            db,
            session_id=session.id,
            model="MiniMax-M3",
        )
        repositories.add_message(
            db,
            session_id=session.id,
            turn_id=turn.id,
            role="user",
            content=content,
        )
        repositories.add_message(
            db,
            session_id=session.id,
            turn_id=turn.id,
            role="assistant",
            content="Va bene, resta un punto aperto.",
        )
        repositories.complete_turn(db, turn_id=turn.id)
        record_event(
            db,
            session_id=session.id,
            turn_id=turn.id,
            event_type="turn.completed",
            payload={"status": "completed"},
            source="chat",
            actor="backend",
            visibility="private",
        )
        return turn.id


def test_shadow_workspace_uses_m27_and_never_schedules_scarlet(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    WorkspaceProvider.models = []
    settings = _settings("shadow")
    run_cognitive_workspace_tick(
        db_engine,
        settings=settings,
        provider_factory=WorkspaceProvider,
    )
    _completed_human_turn(db_engine)

    result = run_cognitive_workspace_tick(
        db_engine,
        settings=settings,
        provider_factory=WorkspaceProvider,
    )

    assert result["appraisal"]["candidate_ids"]
    assert result["ignition"]["selected_ids"]
    assert result["ignition"]["activation_id"] is None
    assert WorkspaceProvider.models == ["MiniMax-M2.7", "MiniMax-M2.7"]
    with Session(db_engine) as db:
        assert repositories.list_autonomous_activations(
            db,
            profile_id="local-user",
            limit=10,
        ) == []
        receipts = repositories.list_signal_receipts(
            db,
            profile_id="local-user",
            limit=100,
        )
        assert any(item.source_type == "turn.completed" for item in receipts)


def test_signal_disposition_receipt_does_not_recursively_feed_workspace(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    settings = _settings("shadow")
    run_cognitive_workspace_tick(
        db_engine,
        settings=settings,
        provider_factory=WorkspaceProvider,
    )
    _completed_human_turn(db_engine)

    run_cognitive_workspace_tick(
        db_engine,
        settings=settings,
        provider_factory=WorkspaceProvider,
    )
    # Drain the finite cognition events created while appraising the source
    # turn. Their receipt events must remain terminal telemetry.
    run_cognitive_workspace_tick(
        db_engine,
        settings=settings,
        provider_factory=WorkspaceProvider,
    )

    with Session(db_engine) as db:
        autonomous_session = repositories.get_or_create_autonomous_session(
            db,
            profile_id="local-user",
        )
        receipt_events_before = [
            event
            for event in repositories.list_events_for_session(
                db,
                session_id=autonomous_session.id,
                limit=100,
            )
            if event.type == "cognition.signal.dispositioned"
        ]
        receipts_before = repositories.list_signal_receipts(
            db,
            profile_id="local-user",
            limit=100,
        )

    run_cognitive_workspace_tick(
        db_engine,
        settings=settings,
        provider_factory=WorkspaceProvider,
    )

    with Session(db_engine) as db:
        receipt_events_after = [
            event
            for event in repositories.list_events_for_session(
                db,
                session_id=autonomous_session.id,
                limit=100,
            )
            if event.type == "cognition.signal.dispositioned"
        ]
        receipts_after = repositories.list_signal_receipts(
            db,
            profile_id="local-user",
            limit=100,
        )

    assert receipt_events_before
    assert len(receipt_events_after) == len(receipt_events_before)
    assert len(receipts_after) == len(receipts_before)
    assert all(
        receipt.source_type != "cognition.signal.dispositioned"
        for receipt in receipts_after
    )


def test_active_workspace_schedules_m3_activation_without_running_it(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    WorkspaceProvider.models = []
    settings = _settings("active")
    run_cognitive_workspace_tick(
        db_engine,
        settings=settings,
        provider_factory=WorkspaceProvider,
    )
    _completed_human_turn(db_engine)

    result = run_cognitive_workspace_tick(
        db_engine,
        settings=settings,
        provider_factory=WorkspaceProvider,
    )

    activation_id = result["ignition"]["activation_id"]
    assert activation_id is not None
    with Session(db_engine) as db:
        rows = repositories.list_autonomous_activations(
            db,
            profile_id="local-user",
            limit=10,
        )
        activation = next(item for item in rows if item.id == activation_id)
        assert activation.trigger_kind == "cognitive_workspace"
        assert activation.workspace_json["authority"] == "provisional_m2.7_ignition"
        assert activation.status == "pending"
    assert all(model == "MiniMax-M2.7" for model in WorkspaceProvider.models)


def test_active_workspace_executes_the_selected_m3_cycle(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    ActiveCycleProvider.models = []
    settings = _settings("active")
    run_cognitive_workspace_tick(
        db_engine,
        settings=settings,
        provider_factory=ActiveCycleProvider,
    )
    _completed_human_turn(db_engine)

    admitted = run_cognitive_workspace_tick(
        db_engine,
        settings=settings,
        provider_factory=ActiveCycleProvider,
    )
    activation_id = admitted["ignition"]["activation_id"]
    assert activation_id is not None

    completed = run_autonomous_activation(
        db_engine,
        settings=settings,
        provider_factory=ActiveCycleProvider,
        activation_id=activation_id,
    )

    assert completed["status"] == "completed"
    assert ActiveCycleProvider.models == [
        "MiniMax-M2.7",
        "MiniMax-M2.7",
        "MiniMax-M3",
    ]
    with Session(db_engine) as db:
        activation = next(
            item
            for item in repositories.list_autonomous_activations(
                db,
                profile_id="local-user",
                limit=10,
            )
            if item.id == activation_id
        )
        assert activation.status == "completed"
        assert activation.trigger_kind == "cognitive_workspace"
        assert activation.turn_id is not None
        candidate_id = activation.workspace_json["selected_candidate_ids"][0]
        candidate = repositories.get_candidate(db, candidate_id)
        assert candidate is not None
        assert candidate.status == "parked"
        messages = repositories.list_messages_for_turn(
            db,
            turn_id=activation.turn_id,
        )
        assert [item.role for item in messages] == ["activation", "assistant"]
        assert "Checkpoint interno" in messages[-1].content


def test_parked_candidate_requires_new_source_backed_reconsideration(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    now = utc_now()
    with Session(db_engine) as db:
        candidate, _ = repositories.create_candidate(
            db,
            profile_id="local-user",
            candidate_kind="continuity_question",
            context_family="session_continuity",
            claim="Un filo precedente potrebbe meritare un controllo futuro.",
            why_now="Il primo segnale e stato gia esaminato da Scarlet.",
            cognitive_question="C'e nuova evidenza che riapre il filo?",
            expected_transformation="Riattivare solo un'indagine supportata.",
            uncertainty="medium",
            exact_fingerprint="parked-candidate-reconsideration",
            sources=[
                {
                    "source_kind": "event",
                    "source_id": "evt_original",
                    "observed_at": now,
                }
            ],
        )
        repositories.update_candidate(
            db,
            candidate_id=candidate.id,
            status="parked",
        )

        assert repositories.list_eligible_candidates(
            db,
            profile_id="local-user",
            now=now + timedelta(days=1),
        ) == []
        with pytest.raises(ValueError, match="newly attached source evidence"):
            repositories.reconsider_candidate(
                db,
                candidate_id=candidate.id,
                sources=[
                    {
                        "source_kind": "event",
                        "source_id": "evt_original",
                        "observed_at": now,
                    }
                ],
                appraisal_model="MiniMax-M2.7",
                appraisal_trace_id=None,
            )

        reopened = repositories.reconsider_candidate(
            db,
            candidate_id=candidate.id,
            sources=[
                {
                    "source_kind": "event",
                    "source_id": "evt_new_evidence",
                    "observed_at": now + timedelta(minutes=1),
                }
            ],
            appraisal_model="MiniMax-M2.7",
            appraisal_trace_id=None,
        )

    assert reopened.status == "proposed"


def test_appraisal_contract_exposes_parked_candidates_for_exact_reconsideration() -> None:
    signal = CognitiveSignalEnvelope(
        receipt_id="receipt_1",
        source_ref="event:evt_new_evidence",
        source_type="turn.completed",
        policy="candidate",
        context_family="session_continuity",
        observed_at=utc_now().isoformat(),
        summary="A new source could reopen a known continuity question.",
    )
    prompt = appraisal_prompt(
        [signal],
        parked_candidates=[
            {
                "id": "cand_parked",
                "cognitive_question": "What changed after the earlier review?",
            }
        ],
    )
    parsed = CognitiveAppraisalBatch.model_validate(
        {
            "schema_version": APPRAISAL_SCHEMA_VERSION,
            "appraisals": [
                {
                    "source_refs": ["event:evt_new_evidence"],
                    "disposition": "reconsider",
                    "candidate_id": "cand_parked",
                    "reason": "The new event directly reopens the same question.",
                }
            ],
        }
    )

    assert '"id": "cand_parked"' in prompt
    assert parsed.appraisals[0].candidate_id == "cand_parked"


def test_advisory_workspace_attaches_to_periodic_cycle_without_rescheduling(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    settings = _settings("advisory")
    now = utc_now()
    run_due_autonomous_activations(
        db_engine,
        settings=settings,
        provider_factory=WorkspaceProvider,
        now=now,
    )
    _completed_human_turn(db_engine)

    result = run_cognitive_workspace_tick(
        db_engine,
        settings=settings,
        provider_factory=WorkspaceProvider,
        now=now,
    )

    assert result["ignition"]["activation_id"] is not None
    with Session(db_engine) as db:
        rows = repositories.list_autonomous_activations(
            db,
            profile_id="local-user",
            limit=10,
        )
        assert len(rows) == 1
        assert rows[0].trigger_kind == "periodic"
        assert rows[0].scheduled_at.replace(tzinfo=now.tzinfo) == now + timedelta(
            seconds=600
        )
        assert rows[0].workspace_json["selected_candidates"]


def test_active_mode_does_not_create_periodic_activation(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    now = utc_now()

    result = run_due_autonomous_activations(
        db_engine,
        settings=_settings("active"),
        provider_factory=WorkspaceProvider,
        now=now,
    )

    assert result == []
    with Session(db_engine) as db:
        assert repositories.list_autonomous_activations(
            db,
            profile_id="local-user",
            limit=10,
        ) == []


def test_archived_autonomous_replay_is_trace_only_and_cannot_wake_scarlet(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    WorkspaceProvider.models = []
    with Session(db_engine) as db:
        session = repositories.get_or_create_autonomous_session(
            db,
            profile_id="local-user",
        )
        turn = repositories.create_turn(
            db,
            session_id=session.id,
            model="MiniMax-M3",
            trigger_kind="autonomous_activation",
            actor="scarlet",
        )
        record_event(
            db,
            session_id=session.id,
            turn_id=turn.id,
            event_type="turn.completed",
            payload={"status": "completed"},
            source="autonomy",
            actor="scarlet",
            visibility="private",
        )
        archived = repositories.archive_autonomous_session(
            db,
            profile_id="local-user",
            expected_session_id=session.id,
            reason="workspace_replay_test",
        )
        assert archived is not None
        assert archived.kind == "scarlet_autonomous_archive"

    result = run_cognitive_workspace_tick(
        db_engine,
        settings=_settings("shadow"),
        provider_factory=WorkspaceProvider,
        replay_existing=True,
    )

    assert result["bootstrapped"]["replay_existing"] is True
    assert result["appraisal"]["status"] == "not_required"
    assert result["ignition"].get("activation_id") is None
    assert WorkspaceProvider.models == []
    with Session(db_engine) as db:
        receipts = repositories.list_signal_receipts(
            db,
            profile_id="local-user",
            limit=100,
        )
        replayed = next(
            item
            for item in receipts
            if item.source_type == "turn.completed"
        )
        assert replayed.policy == "trace_only"
        assert replayed.disposition == "trace_only"
        assert repositories.list_autonomous_activations(
            db,
            profile_id="local-user",
            limit=10,
        ) == []


def test_existing_event_replay_is_rejected_outside_shadow(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    _completed_human_turn(db_engine)

    result = run_cognitive_workspace_tick(
        db_engine,
        settings=_settings("active"),
        provider_factory=WorkspaceProvider,
        replay_existing=True,
    )

    assert result == {
        "mode": "active",
        "status": "replay_requires_shadow",
        "replay_existing": True,
    }
    with Session(db_engine) as db:
        assert repositories.list_signal_receipts(
            db,
            profile_id="local-user",
            limit=100,
        ) == []
        assert repositories.list_autonomous_activations(
            db,
            profile_id="local-user",
            limit=10,
        ) == []


def test_active_mode_cancels_existing_pending_periodic_activation(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    now = utc_now()
    with Session(db_engine) as db:
        session = repositories.get_or_create_autonomous_session(
            db,
            profile_id="local-user",
        )
        periodic = repositories.schedule_autonomous_activation(
            db,
            profile_id="local-user",
            session_id=session.id,
            scheduled_at=now,
            trigger_kind="periodic",
        )

    result = run_due_autonomous_activations(
        db_engine,
        settings=_settings("active"),
        provider_factory=WorkspaceProvider,
        now=now,
    )

    assert result == []
    with Session(db_engine) as db:
        stored = next(
            item
            for item in repositories.list_autonomous_activations(
                db,
                profile_id="local-user",
                limit=10,
            )
            if item.id == periodic.id
        )
        assert stored.status == "cancelled"
        assert stored.outcome_json["reason"] == (
            "periodic_wake_retired_by_active_workspace"
        )


def test_due_wake_condition_bypasses_semantic_appraisal(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    WorkspaceProvider.models = []
    settings = _settings("active")
    now = utc_now()
    run_cognitive_workspace_tick(
        db_engine,
        settings=settings,
        provider_factory=WorkspaceProvider,
        now=now,
    )
    with Session(db_engine) as db:
        repositories.create_wake_condition(
            db,
            profile_id="local-user",
            kind="at_time",
            condition_key="wake:test:due",
            predicate={"at": (now - timedelta(seconds=1)).isoformat()},
            not_before=now - timedelta(seconds=1),
        )

    result = run_cognitive_workspace_tick(
        db_engine,
        settings=settings,
        provider_factory=WorkspaceProvider,
        now=now,
    )

    assert result["wake_conditions"]["matched_ids"]
    assert result["appraisal"]["status"] == "not_required"
    assert result["ignition"]["activation_id"] is not None
    assert WorkspaceProvider.models == []


def test_episode_shell_keeps_scarlet_as_final_candidate_authority(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    now = utc_now()
    with Session(db_engine) as db:
        session = repositories.create_chat_session(
            db,
            title="Autonomous episode",
            kind="scarlet_autonomous",
            profile_id="local-user",
        )
        turn = repositories.create_turn(
            db,
            session_id=session.id,
            model="MiniMax-M3",
            trigger_kind="autonomous_activation",
            actor="scarlet",
        )
        candidate, _ = repositories.create_candidate(
            db,
            profile_id="local-user",
            candidate_kind="open_loop",
            context_family="session_continuity",
            claim="A source-backed open loop exists.",
            why_now="New evidence arrived.",
            cognitive_question="Should this become a bounded inquiry?",
            expected_transformation="A decision or suspension.",
            uncertainty="medium",
            exact_fingerprint="episode-shell-candidate",
            sources=[
                {
                    "source_kind": "event",
                    "source_id": "evt_source",
                    "observed_at": now,
                }
            ],
            appraisal_model="MiniMax-M2.7",
        )
        session_id = session.id
        turn_id = turn.id
        candidate_id = candidate.id
    context = MindAPIContext(
        engine=db_engine,
        session_id=session_id,
        turn_id=turn_id,
        runtime_trigger="autonomous_activation",
        settings=_settings(),
        provider_factory=WorkspaceProvider,
    )

    opened = dispatch_mind_shell(
        MindShellRequest(
            command=(
                f'episode open {candidate_id} --question "Che cosa resta aperto?" '
                '--expected-transformation "Una decisione sorgentata."'
            )
        ),
        context=context,
    )
    assert opened.ok is True
    episode_id = opened.result["data"]["episode"]["id"]

    checkpoint = dispatch_mind_shell(
        MindShellRequest(
            command=(
                f'episode checkpoint {episode_id} --progress "Ho verificato la fonte." '
                '--next "Attendere nuovo dato." --source event:evt_source'
            )
        ),
        context=context,
    )
    assert checkpoint.ok is True
    suspended = dispatch_mind_shell(
        MindShellRequest(
            command=(
                f'episode suspend {episode_id} --reason "Serve nuova evidenza." '
                f'--resume-at "{(now + timedelta(hours=1)).isoformat()}"'
            )
        ),
        context=context,
    )
    assert suspended.ok is True
    with Session(db_engine) as db:
        stored_candidate = repositories.get_candidate(db, candidate_id)
        episode = repositories.get_episode(db, episode_id)
        assert stored_candidate is not None
        assert stored_candidate.status == "selected"
        assert stored_candidate.selected_episode_id == episode_id
        assert episode is not None
        assert episode.status == "suspended"
        assert repositories.list_pending_wake_conditions(
            db,
            profile_id="local-user",
            now=now + timedelta(hours=2),
        )


def test_wake_registry_fails_closed_for_unknown_events() -> None:
    unknown = classify_wake_source("future.unregistered.signal")
    recursive = classify_wake_source("cognition.signal.dispositioned")

    assert unknown.policy == "invalid"
    assert recursive.policy == "trace_only"


def test_episode_creation_is_atomic_across_profile_boundary(
    db_engine: Engine,
) -> None:
    init_db(db_engine)
    with Session(db_engine) as db:
        candidate, _ = repositories.create_candidate(
            db,
            profile_id="other-user",
            candidate_kind="private_question",
            context_family="session_continuity",
            claim="Private evidence belongs to another profile.",
            why_now="It must not cross the profile boundary.",
            cognitive_question="Can another profile open this?",
            expected_transformation="Reject the cross-profile transaction.",
            uncertainty="low",
            exact_fingerprint="cross-profile-candidate",
            sources=[
                {
                    "source_kind": "event",
                    "source_id": "evt_private",
                    "observed_at": utc_now(),
                }
            ],
        )
        with pytest.raises(ValueError, match="another profile"):
            repositories.create_episode(
                db,
                profile_id="local-user",
                question="This episode must roll back.",
                expected_transformation="No partial episode remains.",
                candidate_ids=[candidate.id],
                source_session_id=None,
                source_turn_id=None,
            )

        assert repositories.list_episodes(
            db,
            profile_id="local-user",
            limit=10,
        ) == []
        stored = repositories.get_candidate(db, candidate.id)
        assert stored is not None
        assert stored.status == "proposed"
