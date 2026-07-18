from app.runtime import maintenance
from app.runtime import maintenance_history
from app.runtime import maintenance_scheduler


def test_maintenance_facade_reexports_domain_owners() -> None:
    expected = {
        "schedule_session_idle_maintenance": (
            maintenance_scheduler.schedule_session_idle_maintenance
        ),
        "schedule_history_compaction": (
            maintenance_scheduler.schedule_history_compaction
        ),
        "schedule_summary_repairs": maintenance_scheduler.schedule_summary_repairs,
        "run_due_maintenance_jobs": maintenance_scheduler.run_due_maintenance_jobs,
        "run_maintenance_job": maintenance_scheduler.run_maintenance_job,
        "start_maintenance_worker": maintenance_scheduler.start_maintenance_worker,
        "session_summary_audit": maintenance_history.session_summary_audit,
    }

    for name, owner in expected.items():
        assert getattr(maintenance, name) is owner
