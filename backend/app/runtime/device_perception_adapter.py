"""Admit a narrow set of device-lab transitions into perception evidence."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session

from app.config import Settings
from app.storage import repositories
from app.storage.models import DeviceObservation


DEVICE_ADAPTER_VERSION = "device-perception-adapter-v1"


def admit_device_observation(
    db: Session,
    *,
    settings: Settings,
    profile_id: str,
    observation: DeviceObservation,
) -> dict[str, Any]:
    """Classify one immutable lab record without changing its raw evidence."""

    mode = settings.device_perception_admission_mode
    mapping = _mapping(observation)
    if mapping is None:
        return {
            "mode": mode,
            "status": "not_admitted",
            "reason": "probe_or_event_not_in_v1_transition_contract",
            "device_observation_id": observation.id,
        }
    channel, event_type, context_family = mapping
    decision = {
        "mode": mode,
        "status": "eligible",
        "device_observation_id": observation.id,
        "channel": channel,
        "event_type": event_type,
        "context_family": context_family,
        "perspective": "human_device_not_scarlet_sensor",
    }
    if mode == "off":
        return {**decision, "status": "disabled"}
    if mode == "shadow":
        return {**decision, "status": "shadow_only"}

    event, created = repositories.add_perception_event(
        db,
        profile_id=profile_id,
        channel=channel,
        event_type=event_type,
        source=f"device_exploration_adapter:{DEVICE_ADAPTER_VERSION}",
        source_event_key=f"device_observation:{observation.id}",
        observed_at=observation.observed_at,
        payload={
            "state": _model_usable_state(observation),
            "app_state": observation.app_state,
        },
        navigation={
            "source_kind": "device_observation",
            "source_id": observation.id,
            "run_id": observation.run_id,
            "device_id": observation.device_id,
        },
        metadata={
            "adapter_version": DEVICE_ADAPTER_VERSION,
            "subject_domain": "human_device",
            "observer_domain": "human_device",
            "evidence_kind": "direct_observation",
            "context_family": context_family,
            "raw_payload_delivery": False,
            "human_state_inference": False,
        },
    )
    return {
        **decision,
        "status": "admitted" if created else "deduplicated",
        "perception_event_id": event.id,
    }


def _mapping(
    observation: DeviceObservation,
) -> tuple[str, str, str] | None:
    key = (observation.probe, observation.event_type)
    mappings = {
        ("lifecycle", "app_state_change"): (
            "device_lifecycle",
            "device.lifecycle.changed",
            "human_device_state",
        ),
        ("lifecycle", "pause"): (
            "device_lifecycle",
            "device.lifecycle.paused",
            "human_device_state",
        ),
        ("lifecycle", "resume"): (
            "device_lifecycle",
            "device.lifecycle.resumed",
            "human_device_state",
        ),
        ("network", "status_change"): (
            "device_network",
            "device.network.changed",
            "human_device_state",
        ),
        ("notifications", "action_performed"): (
            "notifications",
            "device.notification.interacted",
            "human_personal_events",
        ),
        ("location", "explicit_position"): (
            "device_location",
            "device.location.observed",
            "human_device_state",
        ),
    }
    return mappings.get(key)


def _model_usable_state(observation: DeviceObservation) -> dict[str, Any]:
    """Keep the derived event compact; raw payload stays in the lab ledger."""

    allowed_by_probe = {
        "lifecycle": {"active"},
        "network": {"connected", "transport"},
        "notifications": {"notification_id", "action_id"},
        "location": {
            "latitude",
            "longitude",
            "accuracy_meters",
            "altitude_meters",
            "speed_meters_second",
            "heading_degrees",
            "precise_permission",
            "approximate_permission",
        },
    }
    allowed = allowed_by_probe.get(observation.probe, set())
    return {
        key: value
        for key, value in observation.normalized_json.items()
        if key in allowed
    }
