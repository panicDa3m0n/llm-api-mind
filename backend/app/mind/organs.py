from dataclasses import dataclass
from typing import Any


ORGAN_REGISTRY_VERSION = "2026-06-25.digital-organs-substrate-v1"

ORGAN_VISIBILITY_MODES = {
    "off",
    "shadow",
    "model",
    "manual",
    "autonomous_only",
}


@dataclass(frozen=True)
class OrganBlockSpec:
    organ: str
    block_type: str
    default_id: str
    scope: str
    lifetime: str
    source: str
    default_visibility: str
    settings_mode_field: str
    purpose: str


ORGAN_BLOCK_SPECS: tuple[OrganBlockSpec, ...] = (
    OrganBlockSpec(
        organ="focus",
        block_type="focus_context",
        default_id="scarlet.focus",
        scope="session",
        lifetime="dynamic",
        source="backend.focus_state",
        default_visibility="model",
        settings_mode_field="organ_focus_mode",
        purpose=(
            "Current lived-attention packet. It is separate from memory retrieval "
            "and must not narrow retrieval by default."
        ),
    ),
    OrganBlockSpec(
        organ="volition",
        block_type="volition_context",
        default_id="scarlet.volition",
        scope="profile",
        lifetime="dynamic",
        source="backend.volition_state",
        default_visibility="manual",
        settings_mode_field="organ_volition_mode",
        purpose=(
            "Self-generated intentions. Normal active chat should not receive "
            "automatic intention retrieval in the first organ design."
        ),
    ),
    OrganBlockSpec(
        organ="affect",
        block_type="affective_context",
        default_id="scarlet.affect",
        scope="turn",
        lifetime="dynamic",
        source="backend.affective_appraisal",
        default_visibility="shadow",
        settings_mode_field="organ_affect_mode",
        purpose=(
            "Subconscious human-emotion state computed by API Mind. It affects "
            "model behavior when surfaced and must not mutate backend retrieval, "
            "focus, intentions, or operations."
        ),
    ),
    OrganBlockSpec(
        organ="temporal_experience",
        block_type="temporal_experience",
        default_id="scarlet.temporal_experience",
        scope="turn",
        lifetime="turn",
        source="backend.temporal_experience",
        default_visibility="model",
        settings_mode_field="organ_temporal_experience_mode",
        purpose=(
            "Derived duration, waiting, freshness, staleness, return, and "
            "continuity signals. Runtime time remains the factual clock."
        ),
    ),
    OrganBlockSpec(
        organ="dream",
        block_type="continuity_delta",
        default_id="scarlet.continuity_delta",
        scope="profile",
        lifetime="dynamic",
        source="backend.dream_consolidation",
        default_visibility="model",
        settings_mode_field="organ_dream_mode",
        purpose=(
            "Trace-backed changes produced by intention-guided exploratory "
            "consolidation while no user is actively conversing."
        ),
    ),
)

ORGAN_BLOCK_SPECS_BY_TYPE = {
    spec.block_type: spec for spec in ORGAN_BLOCK_SPECS
}
ORGAN_BLOCK_SPECS_BY_ORGAN = {
    spec.organ: spec for spec in ORGAN_BLOCK_SPECS
}

ORGAN_EVENT_TYPES = {
    "focus": {
        "created": "organ.focus.created",
        "updated": "organ.focus.updated",
        "closed": "organ.focus.closed",
        "surfaced": "organ.focus.surfaced",
    },
    "volition": {
        "created": "organ.volition.created",
        "updated": "organ.volition.updated",
        "reviewed": "organ.volition.reviewed",
        "closed": "organ.volition.closed",
    },
    "affect": {
        "appraised": "organ.affect.appraised",
        "surfaced": "organ.affect.surfaced",
        "decayed": "organ.affect.decayed",
    },
    "temporal_experience": {
        "computed": "organ.temporal.computed",
        "surfaced": "organ.temporal.surfaced",
    },
    "dream": {
        "seeded": "organ.dream.seeded",
        "started": "organ.dream.started",
        "completed": "organ.dream.completed",
        "delta_created": "organ.dream.continuity_delta_created",
    },
}

ORGAN_TRACE_KINDS = {
    "focus": "organ.focus",
    "volition": "organ.volition",
    "affect": "organ.affect",
    "temporal_experience": "organ.temporal_experience",
    "dream": "organ.dream",
}


def organ_manifest() -> dict[str, Any]:
    return {
        "registry_version": ORGAN_REGISTRY_VERSION,
        "visibility_modes": sorted(ORGAN_VISIBILITY_MODES),
        "blocks": [
            {
                "organ": spec.organ,
                "block_type": spec.block_type,
                "default_id": spec.default_id,
                "scope": spec.scope,
                "lifetime": spec.lifetime,
                "source": spec.source,
                "default_visibility": spec.default_visibility,
                "settings_mode_field": spec.settings_mode_field,
                "purpose": spec.purpose,
            }
            for spec in ORGAN_BLOCK_SPECS
        ],
        "event_types": ORGAN_EVENT_TYPES,
        "trace_kinds": ORGAN_TRACE_KINDS,
    }


def organ_runtime_modes(settings: Any) -> dict[str, str]:
    modes: dict[str, str] = {}
    for spec in ORGAN_BLOCK_SPECS:
        raw_mode = str(getattr(settings, spec.settings_mode_field, "off")).lower()
        modes[spec.organ] = raw_mode if raw_mode in ORGAN_VISIBILITY_MODES else "off"
    return modes


def build_organ_runtime_block(
    *,
    block_type: str,
    content: dict[str, Any],
    block_id: str | None = None,
    source: str | None = None,
    visibility: str | None = None,
    policy: str | None = None,
) -> dict[str, Any]:
    spec = ORGAN_BLOCK_SPECS_BY_TYPE.get(block_type)
    if spec is None:
        known = ", ".join(sorted(ORGAN_BLOCK_SPECS_BY_TYPE))
        raise ValueError(f"Unknown organ block type: {block_type}. Known: {known}")

    visibility_value = visibility or spec.default_visibility
    if visibility_value not in ORGAN_VISIBILITY_MODES:
        known = ", ".join(sorted(ORGAN_VISIBILITY_MODES))
        raise ValueError(f"Unknown organ visibility: {visibility_value}. Known: {known}")

    return {
        "id": block_id or spec.default_id,
        "type": spec.block_type,
        "scope": spec.scope,
        "lifetime": spec.lifetime,
        "source": source or spec.source,
        "visibility": visibility_value,
        "content": {
            "organ": spec.organ,
            "registry_version": ORGAN_REGISTRY_VERSION,
            "policy": policy or spec.purpose,
            **content,
        },
    }
