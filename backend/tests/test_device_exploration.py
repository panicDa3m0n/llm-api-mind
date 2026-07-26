from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.config import Settings
from app.main import create_app
from app.storage.models import ChatSession, DeviceObservation, MemoryRecord, Trace


def make_client(engine: Engine) -> TestClient:
    return TestClient(
        create_app(
            Settings(
                environment="test",
                database_role="test",
                maintenance_enabled=False,
            ),
            db_engine=engine,
        )
    )


def observation(
    *,
    client_event_id: str = "device-event-1",
    probe: str = "device",
    event_type: str = "snapshot",
) -> dict:
    return {
        "client_event_id": client_event_id,
        "schema_version": "device-observation-v1",
        "run_id": "run-physical-device-1",
        "device_id": "android-install-1",
        "probe": probe,
        "event_type": event_type,
        "source": "capacitor",
        "app_state": "active",
        "observed_at": "2026-07-26T18:00:00+02:00",
        "payload": {"model": "SM-S918B", "raw": True},
        "normalized": {"platform": "android"},
        "metadata": {"app_version": "1.58.0"},
    }


def test_device_observation_batch_is_append_only_and_idempotent(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)

    first = client.post(
        "/api/device-exploration/observations/batch",
        json={
            "observations": [
                observation(),
                observation(
                    client_event_id="device-event-2",
                    probe="network",
                    event_type="status",
                ),
            ]
        },
    )
    repeated = client.post(
        "/api/device-exploration/observations/batch",
        json={"observations": [observation()]},
    )

    assert first.status_code == 200
    assert first.json()["accepted"] == 2
    assert first.json()["deduplicated"] == 0
    assert first.json()["observations"][0]["payload"]["model"] == "SM-S918B"
    assert repeated.status_code == 200
    assert repeated.json()["accepted"] == 0
    assert repeated.json()["deduplicated"] == 1

    listed = client.get(
        "/api/device-exploration/observations",
        params={"device_id": "android-install-1", "probe": "network"},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["returned"] == 1
    assert listed.json()["observations"][0]["probe"] == "network"

    unfiltered = client.get(
        "/api/device-exploration/observations",
        params={"device_id": "android-install-1"},
    )
    assert unfiltered.status_code == 200
    assert unfiltered.json()["total"] == 2


def test_device_exploration_summary_states_cognitive_isolation(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)
    response = client.post(
        "/api/device-exploration/observations/batch",
        json={
            "observations": [
                observation(probe="device"),
                observation(
                    client_event_id="device-event-2",
                    probe="battery",
                    event_type="snapshot",
                ),
                observation(
                    client_event_id="device-event-3",
                    probe="battery",
                    event_type="snapshot",
                ),
            ]
        },
    )
    assert response.status_code == 200

    summary = client.get(
        "/api/device-exploration/summary",
        params={
            "device_id": "android-install-1",
            "run_id": "run-physical-device-1",
        },
    )
    assert summary.status_code == 200
    assert summary.json() == {
        "schema_version": "device-exploration-summary-v1",
        "total": 3,
        "device_id": "android-install-1",
        "run_id": "run-physical-device-1",
        "probe_counts": {"battery": 2, "device": 1},
        "latest_observation_at": "2026-07-26T16:00:00Z",
        "model_context_delivery": False,
        "cognitive_persistence": False,
    }

    with Session(db_engine) as db:
        assert len(list(db.exec(select(DeviceObservation)).all())) == 3
        assert list(db.exec(select(ChatSession)).all()) == []
        assert list(db.exec(select(MemoryRecord)).all()) == []
        assert list(db.exec(select(Trace)).all()) == []


def test_device_exploration_rejects_unknown_fields(db_engine: Engine) -> None:
    client = make_client(db_engine)
    invalid = observation()
    invalid["inject_into_model"] = True

    response = client.post(
        "/api/device-exploration/observations/batch",
        json={"observations": [invalid]},
    )

    assert response.status_code == 422
    with Session(db_engine) as db:
        assert list(db.exec(select(DeviceObservation)).all()) == []
