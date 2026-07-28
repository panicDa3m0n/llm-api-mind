"""Versioned admission rules from canonical events to cognitive attention.

The registry never decides semantic importance. It states whether an event is
technical evidence, progress inside an existing episode, a candidate source,
or a deterministic wake contract.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


WAKE_SOURCE_REGISTRY_VERSION = "2026-07-28.wake-sources-v2"

WakePolicy = Literal[
    "trace_only",
    "episode_evidence",
    "candidate",
    "conditional_wake",
    "required_wake",
    "invalid",
]
InterruptPolicy = Literal["never", "at_boundary", "immediate"]


@dataclass(frozen=True)
class WakeSourceSpec:
    pattern: str
    policy: WakePolicy
    context_family: str
    appraisal_required: bool
    coalescing_key: str
    interrupt_policy: InterruptPolicy = "never"
    purpose: str = ""


EXACT_WAKE_SOURCES: tuple[WakeSourceSpec, ...] = (
    WakeSourceSpec(
        pattern="turn.completed",
        policy="candidate",
        context_family="session_continuity",
        appraisal_required=True,
        coalescing_key="session:{session_id}:turn:{turn_id}",
        purpose=(
            "A completed human exchange may contain an unresolved question, "
            "commitment, relational change, or useful follow-up."
        ),
    ),
    WakeSourceSpec(
        pattern="memory.proposals.review_ready",
        policy="candidate",
        context_family="memory_continuity",
        appraisal_required=True,
        coalescing_key="memory-proposals:{turn_id}",
        purpose=(
            "Source-backed memory proposals may deserve Scarlet's semantic "
            "review; the event exposes availability without deciding outcome."
        ),
    ),
    WakeSourceSpec(
        pattern="agent.mode.changed",
        policy="candidate",
        context_family="agent_posture",
        appraisal_required=True,
        coalescing_key="mode:{profile_id}",
        purpose="A posture change may alter which unresolved work is eligible.",
    ),
    WakeSourceSpec(
        pattern="organ.focus.created",
        policy="candidate",
        context_family="foreground_attention",
        appraisal_required=True,
        coalescing_key="focus:{entity_id}",
        purpose="New foreground attention may open or redirect a cognitive episode.",
    ),
    WakeSourceSpec(
        pattern="organ.focus.updated",
        policy="episode_evidence",
        context_family="foreground_attention",
        appraisal_required=False,
        coalescing_key="focus:{entity_id}",
        purpose="A focus mutation normally records progress inside current cognition.",
    ),
    WakeSourceSpec(
        pattern="organ.focus.closed",
        policy="episode_evidence",
        context_family="foreground_attention",
        appraisal_required=False,
        coalescing_key="focus:{entity_id}",
        purpose="Focus closure is an outcome, not a fresh reason to wake by itself.",
    ),
    WakeSourceSpec(
        pattern="organ.volition.created",
        policy="candidate",
        context_family="agent_posture",
        appraisal_required=True,
        coalescing_key="volition:{entity_id}",
        purpose="A new durable intention may deserve a bounded future inquiry.",
    ),
    WakeSourceSpec(
        pattern="organ.volition.updated",
        policy="episode_evidence",
        context_family="agent_posture",
        appraisal_required=False,
        coalescing_key="volition:{entity_id}",
        purpose="An intention update normally records progress in the current episode.",
    ),
    WakeSourceSpec(
        pattern="organ.volition.reviewed",
        policy="episode_evidence",
        context_family="agent_posture",
        appraisal_required=False,
        coalescing_key="volition:{entity_id}",
        purpose="A review result is evidence for the episode that performed it.",
    ),
    WakeSourceSpec(
        pattern="organ.volition.closed",
        policy="episode_evidence",
        context_family="agent_posture",
        appraisal_required=False,
        coalescing_key="volition:{entity_id}",
        purpose="Closed volition is an outcome and must not create a wake loop.",
    ),
    WakeSourceSpec(
        pattern="organ.affect.appraised",
        policy="candidate",
        context_family="affective_posture",
        appraisal_required=True,
        coalescing_key="affect:{profile_id}",
        purpose=(
            "An affect delta is factual self-state evidence; only semantic appraisal "
            "may decide whether the change deserves attention."
        ),
    ),
    WakeSourceSpec(
        pattern="organ.dream.continuity_delta_created",
        policy="candidate",
        context_family="memory_continuity",
        appraisal_required=True,
        coalescing_key="dream:{entity_id}",
        purpose="A trace-backed continuity delta may alter an unresolved inquiry.",
    ),
    WakeSourceSpec(
        pattern="cognition.wake.condition_matched",
        policy="required_wake",
        context_family="agent_posture",
        appraisal_required=False,
        coalescing_key="wake:{entity_id}",
        purpose="A condition previously registered by Scarlet became true.",
    ),
    WakeSourceSpec(
        pattern="cognition.watchdog.due",
        policy="required_wake",
        context_family="agent_posture",
        appraisal_required=False,
        coalescing_key="watchdog:{profile_id}",
        purpose="Maximum silence elapsed without another valid ignition.",
    ),
    WakeSourceSpec(
        pattern="operation.needs_decision",
        policy="required_wake",
        context_family="active_operation",
        appraisal_required=False,
        coalescing_key="operation:{entity_id}",
        purpose="An authorized active operation cannot continue without cognition.",
    ),
    WakeSourceSpec(
        pattern="safety.certified",
        policy="required_wake",
        context_family="human_wellbeing",
        appraisal_required=False,
        coalescing_key="safety:{entity_id}",
        interrupt_policy="at_boundary",
        purpose=(
            "Reserved for separately validated safety adapters; semantic suspicion "
            "must never emit this event type."
        ),
    ),
)


PREFIX_WAKE_SOURCES: tuple[WakeSourceSpec, ...] = (
    WakeSourceSpec(
        pattern="mind.tool_call.",
        policy="episode_evidence",
        context_family="active_operation",
        appraisal_required=False,
        coalescing_key="tool:{turn_id}",
        purpose="Tool lifecycle is progress evidence, not a separate impulse.",
    ),
    WakeSourceSpec(
        pattern="turn.failed",
        policy="episode_evidence",
        context_family="active_operation",
        appraisal_required=False,
        coalescing_key="turn:{turn_id}",
        purpose="A failed turn updates the active episode and recovery path.",
    ),
    WakeSourceSpec(
        pattern="organ.affect.surfaced",
        policy="trace_only",
        context_family="affective_posture",
        appraisal_required=False,
        coalescing_key="affect:{turn_id}",
        purpose="Projection of state already known by the affect organ.",
    ),
    WakeSourceSpec(
        pattern="organ.temporal.",
        policy="trace_only",
        context_family="operational_orientation",
        appraisal_required=False,
        coalescing_key="temporal:{turn_id}",
        purpose="Derived temporal context is not itself an impulse.",
    ),
    WakeSourceSpec(
        pattern="cognition.",
        policy="trace_only",
        context_family="agent_posture",
        appraisal_required=False,
        coalescing_key="cognition:{turn_id}",
        purpose="Workspace receipts must not recursively feed the workspace.",
    ),
    WakeSourceSpec(
        pattern="autonomy.",
        policy="trace_only",
        context_family="agent_posture",
        appraisal_required=False,
        coalescing_key="autonomy:{turn_id}",
        purpose="Activation lifecycle is execution evidence, not a fresh impulse.",
    ),
    WakeSourceSpec(
        pattern="maintenance.",
        policy="trace_only",
        context_family="operational_orientation",
        appraisal_required=False,
        coalescing_key="maintenance:{turn_id}",
        purpose="Backend maintenance remains separate from Scarlet cognition.",
    ),
    WakeSourceSpec(
        pattern="history.",
        policy="trace_only",
        context_family="session_continuity",
        appraisal_required=False,
        coalescing_key="history:{session_id}",
        purpose="History derivation is technical context infrastructure.",
    ),
    WakeSourceSpec(
        pattern="runtime.context.",
        policy="trace_only",
        context_family="operational_orientation",
        appraisal_required=False,
        coalescing_key="context:{turn_id}",
        purpose="Context construction must not create recursive cognition.",
    ),
    WakeSourceSpec(
        pattern="memory.context.",
        policy="trace_only",
        context_family="memory_continuity",
        appraisal_required=False,
        coalescing_key="memory-context:{turn_id}",
        purpose="Automatic retrieval delivery is not a manual memory use or impulse.",
    ),
    WakeSourceSpec(
        pattern="memory.recent_context.",
        policy="trace_only",
        context_family="memory_continuity",
        appraisal_required=False,
        coalescing_key="memory-context:{turn_id}",
        purpose="Recent-memory packet construction is context infrastructure.",
    ),
    WakeSourceSpec(
        pattern="session.continuity.",
        policy="trace_only",
        context_family="session_continuity",
        appraisal_required=False,
        coalescing_key="session-context:{turn_id}",
        purpose="Session hint construction is not a new lived event.",
    ),
    WakeSourceSpec(
        pattern="llm.",
        policy="trace_only",
        context_family="operational_orientation",
        appraisal_required=False,
        coalescing_key="llm:{turn_id}",
        purpose="Provider lifecycle is technical evidence.",
    ),
    WakeSourceSpec(
        pattern="assistant.",
        policy="trace_only",
        context_family="session_continuity",
        appraisal_required=False,
        coalescing_key="assistant:{turn_id}",
        purpose="The completed turn event owns post-conversation appraisal.",
    ),
    WakeSourceSpec(
        pattern="message.",
        policy="trace_only",
        context_family="session_continuity",
        appraisal_required=False,
        coalescing_key="message:{turn_id}",
        purpose="Message persistence is represented by the completed turn.",
    ),
    WakeSourceSpec(
        pattern="answer.",
        policy="trace_only",
        context_family="operational_orientation",
        appraisal_required=False,
        coalescing_key="answer:{turn_id}",
        purpose="Answer validation is technical control evidence.",
    ),
    WakeSourceSpec(
        pattern="agentic_module.",
        policy="candidate",
        context_family="active_operation",
        appraisal_required=True,
        coalescing_key="module:{entity_id}",
        purpose="Module receipts require semantic appraisal before attention.",
    ),
)


INVALID_WAKE_SOURCE = WakeSourceSpec(
    pattern="*",
    policy="invalid",
    context_family="operational_orientation",
    appraisal_required=False,
    coalescing_key="unclassified:{event_type}",
    purpose="Unknown events fail closed and remain visible for registry review.",
)


def classify_wake_source(event_type: str) -> WakeSourceSpec:
    for spec in EXACT_WAKE_SOURCES:
        if spec.pattern == event_type:
            return spec
    for spec in PREFIX_WAKE_SOURCES:
        if event_type.startswith(spec.pattern):
            return spec
    return INVALID_WAKE_SOURCE


def wake_source_manifest() -> dict[str, object]:
    return {
        "registry_version": WAKE_SOURCE_REGISTRY_VERSION,
        "exact": [asdict(spec) for spec in EXACT_WAKE_SOURCES],
        "prefix": [asdict(spec) for spec in PREFIX_WAKE_SOURCES],
        "unknown": asdict(INVALID_WAKE_SOURCE),
    }
