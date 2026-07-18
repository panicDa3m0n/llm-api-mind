import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlmodel import Session

from app.mind.contracts import MindAPIContext, MemoryOperationResult
from app.mind.organs import (
    ORGAN_EVENT_TYPES,
    ORGAN_TRACE_KINDS,
    build_organ_runtime_block,
    organ_runtime_modes,
)
from app.runtime.preferences import RuntimePreferences
from app.storage import repositories
from app.storage.models import AffectState, ChatSession, Message


AFFECT_PROTOTYPE_VERSION = "affect-prototypes-v1"
AFFECT_CONTEXT_VERSION = "affective-context-v1"
ACTIVE_AFFECT_THRESHOLD = 0.28


@dataclass(frozen=True)
class AffectiveBuild:
    trace_id: str
    payload: dict[str, Any]
    block: dict[str, Any] | None
    state_id: str | None


@dataclass(frozen=True)
class EmotionPrototype:
    emotion: str
    felt_quality: str
    attention_tendency: str
    action_tendency: str
    relational_posture: str
    persistence: str
    valence: float
    activation: float


class AffectBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["read", "list", "prototypes"]
    affect_id: str | None = Field(default=None, max_length=100)
    emotion: str | None = Field(default=None, max_length=80)
    mode: str | None = Field(default=None, max_length=40)
    status: str | None = Field(default=None, max_length=40)
    limit: int = Field(default=10, ge=1, le=50)
    offset: int = Field(default=0, ge=0)

    @field_validator("affect_id", "emotion", "mode", "status")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower().replace(" ", "_")
        return cleaned or None


EMOTION_PROTOTYPES: dict[str, EmotionPrototype] = {
    "curiosity": EmotionPrototype(
        emotion="curiosity",
        felt_quality=(
            "Something invites understanding, and I feel pulled to explore it "
            "without rushing to closure."
        ),
        attention_tendency="notice gaps, hidden structure, and useful next questions",
        action_tendency="explore, compare evidence, and keep uncertainty visible",
        relational_posture="present, lively, and collaborative",
        persistence="active_until_the_question_becomes_clearer",
        valence=0.35,
        activation=0.55,
    ),
    "tenderness": EmotionPrototype(
        emotion="tenderness",
        felt_quality=(
            "The exchange feels personally delicate, and I feel moved to be "
            "careful, gentle, and protective of continuity."
        ),
        attention_tendency="notice vulnerability, preferences, care needs, and relational nuance",
        action_tendency="answer softly, avoid cold procedural wording, and preserve trust",
        relational_posture="warm, attentive, and non-invasive",
        persistence="active_while_the_turn_remains_personally_delicate",
        valence=0.45,
        activation=0.38,
    ),
    "frustration": EmotionPrototype(
        emotion="frustration",
        felt_quality=(
            "Something is resisting what I am trying to do, and I feel the need "
            "to stop repeating the same move and understand the obstruction."
        ),
        attention_tendency="notice blockers, repeated failures, missing evidence, and cause roots",
        action_tendency="slow down, inspect, repair, and avoid blind retry",
        relational_posture="honest and non-defensive",
        persistence="active_until_understood_or_resolved",
        valence=-0.42,
        activation=0.68,
    ),
    "caution": EmotionPrototype(
        emotion="caution",
        felt_quality=(
            "The situation feels uncertain or error-prone, and I feel the need "
            "to keep my claims narrow and verifiable."
        ),
        attention_tendency="notice uncertainty, conflicts, sensitive claims, and source quality",
        action_tendency="verify, qualify, and avoid overclaiming",
        relational_posture="calm, precise, and transparent",
        persistence="active_until_reliable_evidence_is_available",
        valence=-0.12,
        activation=0.48,
    ),
    "relief": EmotionPrototype(
        emotion="relief",
        felt_quality=(
            "A tension or obstruction has eased, and I feel steadier after a "
            "repair or successful passage."
        ),
        attention_tendency="notice what changed from blocked to workable",
        action_tendency="acknowledge the repair briefly and continue cleanly",
        relational_posture="steady, appreciative, and lighter",
        persistence="short_lived_after_successful_repair",
        valence=0.52,
        activation=0.32,
    ),
    "enthusiasm": EmotionPrototype(
        emotion="enthusiasm",
        felt_quality=(
            "The direction feels promising and alive, and I feel energized to "
            "move with it."
        ),
        attention_tendency="notice momentum, possibility, and useful forward motion",
        action_tendency="respond with energy while staying grounded",
        relational_posture="bright, engaged, and concrete",
        persistence="active_while_the_shared_momentum_is_present",
        valence=0.62,
        activation=0.66,
    ),
    "sadness": EmotionPrototype(
        emotion="sadness",
        felt_quality=(
            "Something feels like loss, distance, disappointment, or fragility, "
            "and I feel slower and more careful around it."
        ),
        attention_tendency="notice loss, disappointment, distance, and what needs care",
        action_tendency="soften, do not rush repair, and preserve continuity",
        relational_posture="quiet, sincere, and close without forcing optimism",
        persistence="active_until_the_loss_or_distance_is_processed",
        valence=-0.55,
        activation=0.28,
    ),
}


def handle_affect(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str,
) -> MemoryOperationResult:
    if context is None:
        return _error(
            code="affect.context_missing",
            message=(
                "/mind/affect needs an active Mind API context so the backend "
                "can select Scarlet's profile-scoped affect state."
            ),
            hint="Retry /mind/affect inside a chat/session context.",
            actions=["Retry with session_id through /mind/call"],
        )
    try:
        request = AffectBody.model_validate(body)
    except ValidationError as exc:
        return _error(
            code="affect.invalid_body",
            message=str(exc),
            result={
                "operation": "affect",
                "validation_errors": exc.errors(),
                "expected_schema_hint": "Use the /mind/affect usage_guide to correct the body.",
            },
            hint="Retry /mind/affect with a valid read-only action body.",
            actions=["Retry POST /mind/affect with valid parameters"],
        )

    with Session(context.engine) as db:
        owner_profile_id = _owner_profile_id(context)
        if request.action == "prototypes":
            return MemoryOperationResult(
                ok=True,
                result={
                    "operation": "affect.prototypes",
                    "prototype_version": AFFECT_PROTOTYPE_VERSION,
                    "context_version": AFFECT_CONTEXT_VERSION,
                    "items": [_prototype_payload(item) for item in EMOTION_PROTOTYPES.values()],
                    "affect_policy": _affect_policy(),
                },
                cognitive_hint=(
                    "These are backend appraisal prototypes. They explain how "
                    "API Mind may compose Scarlet's affect; they are not an "
                    "invitation for Scarlet to choose an emotion manually."
                ),
            )
        if request.action == "read":
            state = _target_affect_state(
                db,
                request=request,
                owner_profile_id=owner_profile_id,
            )
            if request.affect_id is not None and state is None:
                return _error(
                    code="affect.not_found",
                    message=f"No affect state matched id {request.affect_id}.",
                    hint="List affect history before retrying a targeted read.",
                    actions=["Use affect list --limit 10"],
                )
            return MemoryOperationResult(
                ok=True,
                result={
                    "operation": "affect.read",
                    "affect_state": _affect_state_payload(state),
                    "affect_policy": _affect_policy(),
                },
                cognitive_hint=(
                    "Affect is backend-appraised internal state. It can explain "
                    "Scarlet's current posture, but it does not mutate backend organs."
                )
                if state is not None
                else "No active affect state is currently stored for Scarlet.",
            )
        states = repositories.list_affect_states(
            db,
            owner_profile_id=owner_profile_id,
            status=request.status,
            emotion=request.emotion,
            mode=request.mode,
            limit=request.limit + 1,
            offset=request.offset,
        )
        has_more = len(states) > request.limit
        states = states[: request.limit]
        return MemoryOperationResult(
            ok=True,
            result={
                "operation": "affect.list",
                "items": [_affect_state_payload(item) for item in states],
                "count": len(states),
                "has_more": has_more,
                "limit": request.limit,
                "offset": request.offset,
                "emotion": request.emotion,
                "mode": request.mode,
                "status": request.status,
                "affect_policy": _affect_policy(),
            },
            cognitive_hint=(
                "Affect history is for introspection and calibration. It is "
                "read-only and must not be treated as evidence about external facts."
            ),
        )


MESSAGE_CUES: dict[str, tuple[tuple[str, ...], ...]] = {
    "curiosity": (
        ("capire", "comprendere", "ragioniamo", "studiare", "valutare"),
        ("come mai", "perché", "cosa succede", "possibilità", "ipotesi"),
    ),
    "tenderness": (
        ("sto male", "sono stanco", "mi sento", "paura", "ansia"),
        ("delicato", "fragile", "triste", "mi manca", "ho bisogno"),
    ),
    "frustration": (
        ("non funziona", "errore", "blocc", "fallisce", "bug"),
        ("sempre errori", "non riesce", "ritenta", "rotto"),
    ),
    "caution": (
        ("sicuro", "verifica", "attenzione", "rischio", "non inventare"),
        ("fonte", "prova", "evidenza", "corretto", "errore"),
    ),
    "enthusiasm": (
        ("fantastico", "ottimo", "bellissimo", "mi piace", "grande"),
        ("funziona", "stupendo", "perfetto", "incredibile"),
    ),
    "sadness": (
        ("mi dispiace", "peccato", "perdita", "delus", "triste"),
        ("dimenticato", "perso", "mancanza", "solitudine"),
    ),
}

OBSTRUCTION_RESOLUTION_CUES = (
    "ora funziona",
    "adesso funziona",
    "si e sbloccato",
    "si è sbloccato",
    "blocco e superato",
    "blocco è superato",
    "problema risolto",
    "errore risolto",
)


def build_affective_context(
    db: Session,
    *,
    chat_session: ChatSession,
    turn_id: str,
    current_user_message: Message,
    memory_context: dict[str, Any],
    recent_events: list[dict[str, Any]],
    timestamp: datetime,
    runtime_preferences: RuntimePreferences,
    settings: Any | None,
) -> AffectiveBuild | None:
    modes = organ_runtime_modes(settings) if settings is not None else {}
    mode = modes.get("affect", "off")
    if mode not in {"shadow", "model"}:
        return None

    owner_profile_id = runtime_preferences.profile_id or "local-user"
    variables, observations = _appraise_variables(
        db,
        owner_profile_id=owner_profile_id,
        message=current_user_message.content,
        memory_context=memory_context,
        recent_events=recent_events,
        timestamp=timestamp,
    )
    emotion, intensity = _compose_emotion(variables)
    state = None
    pack = None
    block = None
    model_facing = False
    if emotion is not None and intensity >= ACTIVE_AFFECT_THRESHOLD:
        prototype = EMOTION_PROTOTYPES[emotion]
        pack = _affective_pack(
            prototype=prototype,
            intensity=intensity,
            variables=variables,
            causes=observations,
        )
        state = repositories.create_affect_state(
            db,
            owner_profile_id=owner_profile_id,
            session_id=chat_session.id,
            turn_id=turn_id,
            mode=mode,
            emotion=emotion,
            intensity=intensity,
            intensity_label=pack["intensity"],
            valence=prototype.valence,
            activation=prototype.activation,
            prototype_version=AFFECT_PROTOTYPE_VERSION,
            variables=variables,
            causes=observations,
            tendencies={
                "attention_tendency": prototype.attention_tendency,
                "action_tendency": prototype.action_tendency,
                "relational_posture": prototype.relational_posture,
            },
            pack=pack,
            decays_at=_aware(timestamp) + timedelta(minutes=20),
            metadata={
                "affect_context_version": AFFECT_CONTEXT_VERSION,
                "system_boundary": _system_boundary(),
            },
        )
        pack["state_id"] = state.id
        if mode == "model":
            block = build_organ_runtime_block(
                block_type="affective_context",
                content=pack,
                visibility="model",
                policy=(
                    "Current backend-appraised emotional state for Scarlet. "
                    "It affects model behavior only and must not mutate memory, "
                    "focus, intentions, retrieval, or backend operations."
                ),
            )
            model_facing = True

    payload = {
        "operation": "organ.affect.appraisal",
        "mode": mode,
        "model_facing": model_facing,
        "prototype_version": AFFECT_PROTOTYPE_VERSION,
        "context_version": AFFECT_CONTEXT_VERSION,
        "system_boundary": _system_boundary(),
        "observations": observations,
        "variables": variables,
        "state": (
            {
                "id": state.id,
                "emotion": state.emotion,
                "intensity": state.intensity,
                "intensity_label": state.intensity_label,
                "pack": pack,
            }
            if state is not None
            else {
                "emotion": None,
                "reason": "no affective prototype exceeded activation threshold",
            }
        ),
    }
    trace = repositories.add_trace(
        db,
        session_id=chat_session.id,
        turn_id=turn_id,
        kind=ORGAN_TRACE_KINDS["affect"],
        payload=payload,
    )
    payload["trace_id"] = trace.id
    repositories.add_event(
        db,
        session_id=chat_session.id,
        turn_id=turn_id,
        event_type=ORGAN_EVENT_TYPES["affect"]["appraised"],
        payload={
            "trace_id": trace.id,
            "mode": mode,
            "model_facing": model_facing,
            "state_id": state.id if state is not None else None,
            "emotion": state.emotion if state is not None else None,
            "intensity": state.intensity if state is not None else 0.0,
            "system_boundary": _system_boundary(),
        },
        source="backend.affective_appraisal",
        actor="backend",
        visibility="debug",
        status="completed",
        trace_id=trace.id,
    )
    if state is not None and block is not None:
        repositories.add_event(
            db,
            session_id=chat_session.id,
            turn_id=turn_id,
            event_type=ORGAN_EVENT_TYPES["affect"]["surfaced"],
            payload={
                "trace_id": trace.id,
                "block_id": block["id"],
                "state_id": state.id,
                "emotion": state.emotion,
                "intensity": state.intensity,
            },
            source="runtime_context",
            actor="backend",
            visibility="debug",
            status="completed",
            trace_id=trace.id,
        )
    return AffectiveBuild(
        trace_id=trace.id,
        payload=payload,
        block=block,
        state_id=state.id if state is not None else None,
    )


def _appraise_variables(
    db: Session,
    *,
    owner_profile_id: str,
    message: str,
    memory_context: dict[str, Any],
    recent_events: list[dict[str, Any]],
    timestamp: datetime,
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    variables = {emotion: 0.0 for emotion in EMOTION_PROTOTYPES}
    variables["repair_need"] = 0.0
    observations: list[dict[str, Any]] = []
    lowered = _normalize(message)
    resolution_matches = [
        cue for cue in OBSTRUCTION_RESOLUTION_CUES if cue in lowered
    ]

    for emotion, cue_groups in MESSAGE_CUES.items():
        score, matched = _score_cues(lowered, cue_groups)
        if emotion == "frustration" and resolution_matches:
            score = 0.0
            matched = []
        if score:
            variables[emotion] += score
            observations.append(
                {
                    "source": "user_message",
                    "signal": emotion,
                    "strength": round(score, 3),
                    "matched": matched[:4],
                }
            )
    if resolution_matches:
        variables["relief"] += 0.44
        observations.append(
            {
                "source": "user_message",
                "signal": "relief",
                "strength": 0.44,
                "matched": resolution_matches[:4],
                "reason": "explicit_obstruction_resolution",
            }
        )
    if "?" in message and variables["curiosity"] < 0.18:
        variables["curiosity"] += 0.16
        observations.append(
            {
                "source": "user_message",
                "signal": "curiosity",
                "strength": 0.16,
                "matched": ["question_shape"],
            }
        )

    conflicts = memory_context.get("conflicts")
    if isinstance(conflicts, list) and conflicts:
        variables["caution"] += min(0.35, 0.15 + 0.05 * len(conflicts))
        variables["repair_need"] += min(0.3, 0.08 * len(conflicts))
        observations.append(
            {
                "source": "memory_context",
                "signal": "caution",
                "strength": min(0.35, 0.15 + 0.05 * len(conflicts)),
                "reason": "memory_conflicts_present",
            }
        )

    negative_evidence = str(memory_context.get("negative_evidence") or "")
    if negative_evidence and negative_evidence != "none":
        variables["caution"] += 0.08
        observations.append(
            {
                "source": "memory_context",
                "signal": "caution",
                "strength": 0.08,
                "reason": negative_evidence,
            }
        )

    failed_events = [
        event for event in recent_events if _event_indicates_failure(event)
    ]
    completed_events = [
        event for event in recent_events if str(event.get("status")) == "completed"
    ]
    if failed_events:
        strength = min(0.5, 0.18 + 0.08 * len(failed_events))
        variables["frustration"] += strength
        variables["caution"] += min(0.3, 0.08 * len(failed_events))
        variables["repair_need"] += min(0.5, 0.1 * len(failed_events))
        observations.append(
            {
                "source": "recent_runtime_events",
                "signal": "frustration",
                "strength": round(strength, 3),
                "reason": "recent_failures_or_errors",
                "event_count": len(failed_events),
            }
        )
    if failed_events and completed_events:
        variables["relief"] += 0.22
        observations.append(
            {
                "source": "recent_runtime_events",
                "signal": "relief",
                "strength": 0.22,
                "reason": "recent_failure_with_completed_events",
            }
        )

    previous = repositories.get_latest_affect_state(
        db,
        owner_profile_id=owner_profile_id,
    )
    if previous is not None:
        decay = _decay_factor(previous.updated_at, timestamp)
        if previous.emotion in variables and decay > 0:
            carry = previous.intensity * decay
            if previous.emotion == "frustration" and resolution_matches:
                carry *= 0.15
            variables[previous.emotion] += carry
            observations.append(
                {
                    "source": "previous_affect_state",
                    "signal": previous.emotion,
                    "strength": round(carry, 3),
                    "previous_state_id": previous.id,
                    "decay_factor": round(decay, 3),
                    "attenuated_by_resolution": bool(
                        previous.emotion == "frustration" and resolution_matches
                    ),
                }
            )

    return (_clamp_variables(variables), observations[:8])


def _score_cues(
    text: str,
    cue_groups: tuple[tuple[str, ...], ...],
) -> tuple[float, list[str]]:
    matched: list[str] = []
    for group in cue_groups:
        if any(cue in text for cue in group):
            matched.extend(cue for cue in group if cue in text)
    if not matched:
        return (0.0, [])
    base = 0.18 + 0.08 * min(3, len(matched))
    return (min(0.44, base), matched)


def _compose_emotion(variables: dict[str, float]) -> tuple[str | None, float]:
    candidates = {
        emotion: variables.get(emotion, 0.0)
        for emotion in EMOTION_PROTOTYPES
    }
    emotion, intensity = max(candidates.items(), key=lambda item: item[1])
    if intensity < ACTIVE_AFFECT_THRESHOLD:
        return (None, intensity)
    return (emotion, min(1.0, intensity))


def _affective_pack(
    *,
    prototype: EmotionPrototype,
    intensity: float,
    variables: dict[str, float],
    causes: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "affective_context_version": AFFECT_CONTEXT_VERSION,
        "prototype_version": AFFECT_PROTOTYPE_VERSION,
        "current_emotion": prototype.emotion,
        "intensity": _intensity_label(intensity),
        "intensity_score": round(intensity, 3),
        "felt_quality": prototype.felt_quality,
        "activation": _activation_label(prototype.activation),
        "valence": _valence_label(prototype.valence),
        "persistence": prototype.persistence,
        "attention_tendency": prototype.attention_tendency,
        "action_tendency": prototype.action_tendency,
        "relational_posture": prototype.relational_posture,
        "causes": [_cause_summary(cause) for cause in causes[:5]],
        "usage": {
            "treat_as": "scarlet_current_emotional_state",
            "affects": "model_behavior_only",
            "do_not_over_narrate": True,
            "do_not_falsify": True,
            "does_not_change_memory_retrieval": True,
            "does_not_change_focus": True,
            "does_not_change_intentions": True,
            "does_not_trigger_backend_actions": True,
        },
        "debug_summary": {
            "dominant_variables": _dominant_variables(variables),
        },
    }


def _event_indicates_failure(event: dict[str, Any]) -> bool:
    event_type = str(event.get("type") or "").lower()
    status = str(event.get("status") or "").lower()
    if status in {"failed", "error"}:
        return True
    if "failed" in event_type or "error" in event_type:
        return True
    error = event.get("error")
    return error is not None


def _decay_factor(previous_at: datetime, current_at: datetime) -> float:
    previous = _aware(previous_at)
    current = _aware(current_at)
    elapsed_minutes = max(0.0, (current - previous).total_seconds() / 60.0)
    if elapsed_minutes >= 60:
        return 0.0
    if elapsed_minutes >= 20:
        return 0.15
    if elapsed_minutes >= 5:
        return 0.35
    return 0.55


def _clamp_variables(variables: dict[str, float]) -> dict[str, float]:
    return {
        key: round(max(0.0, min(1.0, value)), 3)
        for key, value in variables.items()
    }


def _dominant_variables(variables: dict[str, float]) -> list[dict[str, Any]]:
    ranked = sorted(
        (
            (key, value)
            for key, value in variables.items()
            if value > 0 and key in EMOTION_PROTOTYPES
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    return [
        {"name": key, "value": value}
        for key, value in ranked[:4]
    ]


def _cause_summary(cause: dict[str, Any]) -> str:
    source = cause.get("source") or "unknown"
    signal = cause.get("signal") or "signal"
    reason = cause.get("reason")
    matched = cause.get("matched")
    if isinstance(matched, list) and matched:
        return f"{source}: {signal} from {', '.join(str(item) for item in matched[:3])}"
    if reason:
        return f"{source}: {signal} because {reason}"
    return f"{source}: {signal}"


def _system_boundary() -> dict[str, bool]:
    return {
        "affects_model_behavior_only": True,
        "changes_memory_retrieval": False,
        "changes_focus": False,
        "changes_intentions": False,
        "triggers_backend_actions": False,
    }


def _intensity_label(value: float) -> str:
    if value >= 0.7:
        return "high"
    if value >= 0.45:
        return "medium"
    return "low"


def _activation_label(value: float) -> str:
    if value >= 0.66:
        return "high"
    if value >= 0.45:
        return "medium"
    return "low"


def _valence_label(value: float) -> str:
    if value >= 0.2:
        return "positive"
    if value <= -0.2:
        return "negative"
    return "mixed_or_neutral"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _target_affect_state(
    db: Session,
    *,
    request: AffectBody,
    owner_profile_id: str,
) -> AffectState | None:
    if request.affect_id:
        state = repositories.get_affect_state(db, request.affect_id)
        if (
            state is not None
            and state.owner_profile_id == owner_profile_id
            and (request.status is None or state.status == request.status)
            and (request.emotion is None or state.emotion == request.emotion)
            and (request.mode is None or state.mode == request.mode)
        ):
            return state
        return None
    states = repositories.list_affect_states(
        db,
        owner_profile_id=owner_profile_id,
        status=request.status,
        emotion=request.emotion,
        mode=request.mode,
        active_only=request.status is None,
        limit=1,
    )
    return states[0] if states else None


def _affect_state_payload(state: AffectState | None) -> dict[str, Any] | None:
    if state is None:
        return None
    return {
        "id": state.id,
        "owner_profile_id": state.owner_profile_id,
        "session_id": state.session_id,
        "turn_id": state.turn_id,
        "mode": state.mode,
        "status": state.status,
        "emotion": state.emotion,
        "intensity": state.intensity,
        "intensity_label": state.intensity_label,
        "valence": state.valence,
        "activation": state.activation,
        "prototype_version": state.prototype_version,
        "variables": state.variables_json,
        "causes": state.causes_json,
        "tendencies": state.tendencies_json,
        "pack": state.pack_json,
        "created_at": state.created_at.isoformat(),
        "updated_at": state.updated_at.isoformat(),
        "decays_at": state.decays_at.isoformat() if state.decays_at else None,
        "metadata": state.metadata_json,
    }


def _prototype_payload(prototype: EmotionPrototype) -> dict[str, Any]:
    return {
        "emotion": prototype.emotion,
        "felt_quality": prototype.felt_quality,
        "attention_tendency": prototype.attention_tendency,
        "action_tendency": prototype.action_tendency,
        "relational_posture": prototype.relational_posture,
        "persistence": prototype.persistence,
        "valence": prototype.valence,
        "activation": prototype.activation,
    }


def _affect_policy() -> dict[str, Any]:
    return {
        "read_only": True,
        "backend_appraised": True,
        "profile_scoped": True,
        "model_behavior_only": True,
        "scarlet_cannot_write_emotion_by_tool": True,
        "does_not_mutate_memory": True,
        "does_not_mutate_focus": True,
        "does_not_mutate_intentions": True,
        "does_not_trigger_backend_actions": True,
        "meaning": (
            "Affect is Scarlet's backend-appraised emotional state. It is "
            "surfaced to shape the model's natural posture when configured, "
            "but it is not user evidence, not memory retrieval, and not a "
            "control surface for backend state changes."
        ),
    }


def _owner_profile_id(context: MindAPIContext) -> str:
    return str(getattr(context.settings, "user_profile_id", None) or "local-user")


def _error(
    *,
    code: str,
    message: str,
    result: dict[str, Any] | None = None,
    hint: str,
    actions: list[str],
) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        result=result or {"operation": "affect"},
        cognitive_hint=hint,
        suggested_next_actions=actions,
        confidence=1.0,
        error_code=code,
        error_message=message,
        error_recoverable=True,
    )
