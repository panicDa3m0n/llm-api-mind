import pytest

from app.config import Settings
from app.mind.organs import (
    ORGAN_REGISTRY_VERSION,
    build_organ_runtime_block,
    organ_manifest,
    organ_runtime_modes,
)


def test_organ_runtime_modes_default_to_off() -> None:
    modes = organ_runtime_modes(Settings())

    assert modes == {
        "focus": "off",
        "volition": "off",
        "affect": "off",
        "temporal_experience": "off",
        "dream": "off",
    }


def test_organ_runtime_modes_normalize_unknown_values_to_off() -> None:
    modes = organ_runtime_modes(
        Settings(
            organ_focus_mode="model",
            organ_volition_mode="manual",
            organ_affect_mode="shadow",
            organ_temporal_experience_mode="unexpected",
            organ_dream_mode="autonomous_only",
        )
    )

    assert modes == {
        "focus": "model",
        "volition": "manual",
        "affect": "shadow",
        "temporal_experience": "off",
        "dream": "autonomous_only",
    }


def test_organ_manifest_declares_canonical_blocks() -> None:
    manifest = organ_manifest()

    assert manifest["registry_version"] == ORGAN_REGISTRY_VERSION
    assert {block["block_type"] for block in manifest["blocks"]} == {
        "focus_context",
        "volition_context",
        "affective_context",
        "temporal_experience",
        "continuity_delta",
    }
    assert manifest["event_types"]["focus"]["updated"] == "organ.focus.updated"
    assert manifest["trace_kinds"]["dream"] == "organ.dream"


def test_build_organ_runtime_block_uses_canonical_shape() -> None:
    block = build_organ_runtime_block(
        block_type="focus_context",
        content={"current_focus": {"object": "tesi organi digitali"}},
    )

    assert block == {
        "id": "scarlet.focus",
        "type": "focus_context",
        "scope": "session",
        "lifetime": "dynamic",
        "source": "backend.focus_state",
        "visibility": "model",
        "content": {
            "organ": "focus",
            "registry_version": ORGAN_REGISTRY_VERSION,
            "policy": (
                "Current lived-attention packet. It is separate from memory retrieval "
                "and must not narrow retrieval by default."
            ),
            "current_focus": {"object": "tesi organi digitali"},
        },
    }


def test_affective_block_policy_declares_model_only_boundary() -> None:
    block = build_organ_runtime_block(
        block_type="affective_context",
        content={"current_emotion": "curiosity"},
        visibility="model",
    )

    assert block["type"] == "affective_context"
    assert block["visibility"] == "model"
    assert "affects model behavior" in block["content"]["policy"]
    assert "must not mutate backend retrieval" in block["content"]["policy"]


def test_build_organ_runtime_block_rejects_unknown_block_type() -> None:
    with pytest.raises(ValueError, match="Unknown organ block type"):
        build_organ_runtime_block(block_type="memory_context", content={})
