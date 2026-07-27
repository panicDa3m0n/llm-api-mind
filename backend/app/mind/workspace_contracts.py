"""Structured semantic contracts for the Cognitive Workspace auxiliary LLM."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


APPRAISAL_SCHEMA_VERSION = "cognitive-appraisal-v1"
IGNITION_SCHEMA_VERSION = "cognitive-ignition-v1"


class CognitiveSignalEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_id: str
    source_ref: str
    source_type: str
    policy: str
    context_family: str
    observed_at: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class CognitiveAppraisalItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_refs: list[str] = Field(min_length=1, max_length=20)
    disposition: Literal["candidate", "irrelevant", "insufficient_evidence"]
    candidate_kind: str | None = Field(default=None, max_length=120)
    context_family: str | None = Field(default=None, max_length=120)
    claim: str | None = Field(default=None, max_length=1600)
    why_now: str | None = Field(default=None, max_length=1600)
    cognitive_question: str | None = Field(default=None, max_length=1600)
    expected_transformation: str | None = Field(default=None, max_length=1600)
    uncertainty: Literal["low", "medium", "high", "unknown"] = "unknown"
    wake_recommendation: Literal["hold", "consider", "wake_now"] = "hold"
    reason: str = Field(min_length=1, max_length=1600)

    @model_validator(mode="after")
    def candidate_fields_are_complete(self) -> "CognitiveAppraisalItem":
        if self.disposition != "candidate":
            return self
        required = {
            "candidate_kind": self.candidate_kind,
            "context_family": self.context_family,
            "claim": self.claim,
            "why_now": self.why_now,
            "cognitive_question": self.cognitive_question,
            "expected_transformation": self.expected_transformation,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(
                "candidate appraisal is missing: " + ", ".join(sorted(missing))
            )
        return self


class CognitiveAppraisalBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = APPRAISAL_SCHEMA_VERSION
    appraisals: list[CognitiveAppraisalItem] = Field(default_factory=list)


class IgnitionCoalition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_ids: list[str] = Field(min_length=1, max_length=20)
    reason: str = Field(min_length=1, max_length=1600)
    proposed_episode_question: str = Field(min_length=1, max_length=1600)
    expected_transformation: str = Field(min_length=1, max_length=1600)


class IgnitionDeferral(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    reason: str = Field(min_length=1, max_length=1600)
    revisit_kind: Literal["next_audit", "at_time", "on_new_evidence", "none"]
    revisit_at: str | None = None
    revisit_source_ref: str | None = None


class CognitiveIgnitionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = IGNITION_SCHEMA_VERSION
    ignite: Literal["now", "hold", "none"]
    coalitions: list[IgnitionCoalition] = Field(default_factory=list, max_length=5)
    deferred: list[IgnitionDeferral] = Field(default_factory=list, max_length=50)
    rejected_ids: list[str] = Field(default_factory=list, max_length=50)
    rationale: str = Field(min_length=1, max_length=2400)

    @model_validator(mode="after")
    def now_requires_a_coalition(self) -> "CognitiveIgnitionDecision":
        if self.ignite == "now" and not self.coalitions:
            raise ValueError("ignite=now requires at least one coalition")
        return self


APPRAISER_SYSTEM_PROMPT = """You are a private cognitive appraisal component.

You are not Scarlet and you do not speak for her. You may only turn supplied,
source-backed changes into provisional candidates for Scarlet's attention.
You cannot mutate memory, focus, volition, affect, episodes, or operations.

Return only valid JSON matching cognitive-appraisal-v1. Every appraisal must
cite one or more exact source_ref values from the supplied signals. Do not
invent sources. A technical lifecycle event is not automatically meaningful.
Use disposition=irrelevant when the signal adds no possible cognitive
transformation. Use insufficient_evidence when significance cannot yet be
assessed. Use candidate only when there is a sourceable question Scarlet could
resolve, connect, learn from, or deliberately suspend.

Do not treat numeric metadata as semantic importance. Do not call a possible
conflict, emotion, intention, prediction failure, or safety concern established
unless the evidence directly supports that classification. wake_now is only a
recommendation to the separate ignition gate.
"""


IGNITION_SYSTEM_PROMPT = """You are a private ignition gate for Scarlet.

You are not Scarlet. You compare provisional, source-backed candidates and
recommend whether a full Scarlet M3 autonomous activation is justified now.
You cannot mutate cognitive state and cannot perform the episode yourself.

Return only valid JSON matching cognitive-ignition-v1. You may choose none.
Do not assign or expose a synthetic importance score. Compare candidates by
new evidence, active continuity, due conditions, expected cognitive
transformation, reversibility, and whether waiting would lose a real
opportunity. Build a coalition only when candidates describe one compatible
inquiry. Cite candidate ids exactly. A deferred candidate needs a real revisit
contract; do not defer indefinitely merely because nothing feels urgent.
"""


JSON_REPAIR_SYSTEM_PROMPT = """Repair the supplied malformed internal output.

Return only one valid JSON object matching the schema described in the prompt.
Preserve source ids and meaning. Do not add markdown or explanatory prose.
"""


def appraisal_prompt(signals: list[CognitiveSignalEnvelope]) -> str:
    payload = {
        "schema_version": APPRAISAL_SCHEMA_VERSION,
        "signals": [item.model_dump(mode="json") for item in signals],
        "required_output": {
            "schema_version": APPRAISAL_SCHEMA_VERSION,
            "appraisals": [
                {
                    "source_refs": ["exact supplied source_ref"],
                    "disposition": (
                        "candidate|irrelevant|insufficient_evidence"
                    ),
                    "candidate_kind": "required for candidate",
                    "context_family": "required for candidate",
                    "claim": "required for candidate",
                    "why_now": "required for candidate",
                    "cognitive_question": "required for candidate",
                    "expected_transformation": "required for candidate",
                    "uncertainty": "low|medium|high|unknown",
                    "wake_recommendation": "hold|consider|wake_now",
                    "reason": "always required",
                }
            ],
        },
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def ignition_prompt(
    *,
    candidates: list[dict[str, Any]],
    active_episodes: list[dict[str, Any]],
    max_deferrals: int,
) -> str:
    payload = {
        "schema_version": IGNITION_SCHEMA_VERSION,
        "candidates": candidates,
        "active_episodes": active_episodes,
        "fairness_contract": {
            "max_deferrals_before_mandatory_reconsideration": max_deferrals,
            "mandatory_reconsideration_is_not_mandatory_selection": True,
        },
        "required_output": {
            "schema_version": IGNITION_SCHEMA_VERSION,
            "ignite": "now|hold|none",
            "coalitions": [
                {
                    "candidate_ids": ["cand_..."],
                    "reason": "...",
                    "proposed_episode_question": "...",
                    "expected_transformation": "...",
                }
            ],
            "deferred": [
                {
                    "candidate_id": "cand_...",
                    "reason": "...",
                    "revisit_kind": (
                        "next_audit|at_time|on_new_evidence|none"
                    ),
                    "revisit_at": None,
                    "revisit_source_ref": None,
                }
            ],
            "rejected_ids": [],
            "rationale": "...",
        },
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def repair_prompt(*, malformed: str, schema_name: str) -> str:
    return json.dumps(
        {
            "schema": schema_name,
            "malformed_output": malformed,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
