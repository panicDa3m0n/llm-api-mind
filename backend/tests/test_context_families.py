from datetime import datetime, timezone

import pytest

from app.mind.context_families import (
    CONTEXT_FAMILIES,
    ContextFamilyPacket,
    compose_context_policy_bundle,
    context_family_registry,
    context_family_routing_plan,
    validate_context_family_packet,
    validate_context_family_registry,
)


def test_context_family_registry_is_complete_and_policy_bound() -> None:
    validate_context_family_registry()
    registry = context_family_registry()

    assert registry["routing_status"] == "shadow"
    assert registry["live_model_context_changed"] is False
    assert len(registry["families"]) == len(CONTEXT_FAMILIES)
    assert all(item["policy_block_ids"] for item in registry["families"])
    assert {
        "human",
        "human_device",
        "scarlet",
        "relationship",
        "shared_environment",
        "operation",
    } == set(registry["subject_domains"])


def test_human_device_location_cannot_be_mislabeled_as_human_or_scarlet_perception() -> (
    None
):
    device_location = ContextFamilyPacket(
        packet_id="ctx_sim_device_location",
        family_id="human_device_state",
        subject_domain="human_device",
        observer_domain="human_device",
        evidence_kind="direct_observation",
        observed_at=datetime.now(timezone.utc).isoformat(),
        summary="The user's phone reported a location outside the expected route.",
        data={"device_location": "simulated checkpoint B", "route_state": "unexpected"},
        source_refs=["device_observation:sim_location_1"],
    )
    assert validate_context_family_packet(device_location) == device_location

    invalid = device_location.model_copy(
        update={
            "family_id": "scarlet_perceptual_scene",
            "subject_domain": "shared_environment",
            "observer_domain": "human_device",
        }
    )
    with pytest.raises(
        ValueError,
        match="does not allow observer_domain 'human_device'",
    ):
        validate_context_family_packet(invalid)

    invalid_human_presence = device_location.model_copy(
        update={
            "family_id": "human_situated_presence",
            "subject_domain": "human",
        }
    )
    with pytest.raises(
        ValueError,
        match="does not allow observer_domain 'human_device'",
    ):
        validate_context_family_packet(invalid_human_presence)


def test_human_presence_requires_an_explicit_derived_packet() -> None:
    packet = ContextFamilyPacket(
        packet_id="ctx_sim_human_presence",
        family_id="human_situated_presence",
        subject_domain="human",
        observer_domain="derived_cognition",
        evidence_kind="derived_assessment",
        observed_at="2026-07-26T16:29:00+02:00",
        summary=(
            "The phone deviated from the expected route; whether it is still with "
            "the human is not established."
        ),
        data={
            "assessment": "route_deviation_candidate",
            "human_device_coupling": "unverified",
        },
        source_refs=[
            "context_packet:ctx_sim_device_location",
            "operation:sim_stay_with_me",
        ],
    )

    assert validate_context_family_packet(packet).evidence_kind == "derived_assessment"


def test_scarlet_sensor_packet_keeps_direct_first_person_provenance() -> None:
    packet = ContextFamilyPacket(
        packet_id="ctx_sim_scarlet_camera",
        family_id="scarlet_perceptual_scene",
        subject_domain="shared_environment",
        observer_domain="scarlet_sensor",
        evidence_kind="direct_observation",
        observed_at="2026-07-26T16:30:00+02:00",
        summary="Scarlet's forward camera currently shows an open interior door.",
        data={
            "modality": "vision",
            "observation": "open interior door",
            "uncertainty": "the cause and person involved are not visible",
        },
        source_refs=["sensor_frame:sim_frame_42"],
    )

    validated = validate_context_family_packet(packet)
    policies = compose_context_policy_bundle([validated.family_id])

    assert validated.observer_domain == "scarlet_sensor"
    assert "context.scarlet_perception.v1" in {
        item["id"] for item in policies["blocks"]
    }


def test_operation_simulation_distinguishes_dispatch_from_completion() -> None:
    dispatched = ContextFamilyPacket(
        packet_id="ctx_sim_haptic_dispatch",
        family_id="active_operation",
        subject_domain="operation",
        observer_domain="core_runtime",
        evidence_kind="operation_state",
        observed_at="2026-07-26T16:31:00+02:00",
        summary="A confirmation vibration was requested on the user's phone.",
        data={"status": "dispatched", "authorized_scope": "single_haptic"},
        source_refs=["operation:sim_haptic_7"],
    )
    completed = ContextFamilyPacket(
        packet_id="ctx_sim_haptic_receipt",
        family_id="active_operation",
        subject_domain="operation",
        observer_domain="human_device",
        evidence_kind="operation_result",
        observed_at="2026-07-26T16:31:01+02:00",
        summary="The phone returned a completion receipt for the vibration.",
        data={"status": "completed", "receipt": "sim_receipt_7"},
        source_refs=["operation:sim_haptic_7", "device_receipt:sim_receipt_7"],
    )

    assert validate_context_family_packet(dispatched).evidence_kind == "operation_state"
    assert validate_context_family_packet(completed).evidence_kind == "operation_result"


def test_shadow_router_combines_family_tags_without_live_admission() -> None:
    interactive = context_family_routing_plan(
        active_tag="interactive",
        candidate_family_ids=[
            "session_continuity",
            "human_personal_events",
            "scarlet_perceptual_scene",
            "active_operation",
        ],
    )
    idle = context_family_routing_plan(
        active_tag="idle",
        candidate_family_ids=[
            "human_personal_events",
            "scarlet_perceptual_scene",
            "active_operation",
        ],
    )

    assert interactive["current_model_context_unchanged"] is True
    assert interactive["routing_applied_to_live_context"] is False
    assert interactive["shadow_only_family_ids"] == [
        "human_personal_events",
        "scarlet_perceptual_scene",
        "active_operation",
    ]
    assert idle["mode_ineligible_family_ids"] == ["scarlet_perceptual_scene"]
    assert "human_personal_events" in idle["mode_eligible_family_ids"]
    assert "active_operation" in idle["mode_eligible_family_ids"]


def test_unknown_family_and_wrong_evidence_fail_closed() -> None:
    with pytest.raises(ValueError, match="Unknown context family"):
        context_family_routing_plan(
            active_tag="interactive",
            candidate_family_ids=["unknown_sensor_dump"],
        )

    packet = {
        "packet_id": "ctx_invalid_device_inference",
        "family_id": "human_device_state",
        "subject_domain": "human_device",
        "observer_domain": "human_device",
        "evidence_kind": "derived_assessment",
        "observed_at": "2026-07-26T16:32:00+02:00",
        "summary": "Invalid derived assessment.",
        "source_refs": ["device_observation:sim_invalid"],
    }
    with pytest.raises(ValueError, match="does not allow evidence_kind"):
        validate_context_family_packet(packet)

    with pytest.raises(ValueError, match="shadow-only"):
        context_family_routing_plan(
            active_tag="interactive",
            candidate_family_ids=["session_continuity"],
            routing_mode="active",
        )
