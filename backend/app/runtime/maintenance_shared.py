from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.config import Settings
from app.llm.provider import LLMProvider


SESSION_IDLE_MAINTENANCE_KIND = "session.idle_maintenance"
SESSION_SUMMARY_REPAIR_KIND = "session.summary_repair"
SESSION_HISTORY_COMPACTION_KIND = "session.history_compaction"

ProviderFactory = Callable[[Settings], LLMProvider]


@dataclass(frozen=True)
class MaintenanceJobRef:
    id: str
    kind: str
    session_id: str
    trigger_turn_id: str | None
    trigger_event_id: str | None
    input_payload: dict[str, Any]
