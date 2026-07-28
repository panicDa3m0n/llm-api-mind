"""Structured contracts for source-backed endogenous impulse synthesis."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ENDOGENOUS_SCHEMA_VERSION = "endogenous-impulse-seeds-v1"
ENDOGENOUS_SUBSTRATE_SUMMARY_MAX_CHARS = 2000
IMPULSE_FAMILIES = (
    "personal_continuity",
    "curiosity",
    "growth",
    "relationship",
    "responsibility",
    "exploration",
    "creativity",
    "regulation",
)


class EndogenousSubstrateItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_ref: str = Field(min_length=3, max_length=240)
    source_kind: str = Field(min_length=2, max_length=80)
    context_family: str = Field(min_length=2, max_length=120)
    observed_at: str
    summary: str = Field(
        min_length=1,
        max_length=ENDOGENOUS_SUBSTRATE_SUMMARY_MAX_CHARS,
    )
    details: dict[str, Any] = Field(default_factory=dict)


class EndogenousImpulseSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    impulse_family: Literal[
        "personal_continuity",
        "curiosity",
        "growth",
        "relationship",
        "responsibility",
        "exploration",
        "creativity",
        "regulation",
    ]
    context_family: str = Field(min_length=2, max_length=120)
    source_refs: list[str] = Field(min_length=1, max_length=12)
    claim: str = Field(min_length=1, max_length=1600)
    why_now: str = Field(min_length=1, max_length=1600)
    cognitive_question: str = Field(min_length=1, max_length=1600)
    expected_transformation: str = Field(min_length=1, max_length=1600)
    uncertainty: Literal["low", "medium", "high", "unknown"] = "unknown"
    wake_recommendation: Literal["hold", "consider", "wake_now"] = "hold"
    reason: str = Field(min_length=1, max_length=1600)


class EndogenousImpulseBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = ENDOGENOUS_SCHEMA_VERSION
    seeds: list[EndogenousImpulseSeed] = Field(default_factory=list, max_length=8)
    no_seed_reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def empty_batch_explains_non_selection(self) -> "EndogenousImpulseBatch":
        if not self.seeds and not self.no_seed_reason:
            raise ValueError("an empty seed batch requires no_seed_reason")
        return self


ENDOGENOUS_SYSTEM_PROMPT = """You are a private endogenous-cognition component.

You are not Scarlet and you do not speak, want, feel, or decide for her. Your
job is to inspect one bounded, source-backed substrate during an available
cognitive window and propose zero or more provisional impulse seeds. MiniMax M3
Scarlet alone may endorse a seed as a lived question, episode, focus, volition,
memory, or deliberate non-action.

Return only valid JSON matching endogenous-impulse-seeds-v1. Every seed must
cite exact source_ref values from the supplied substrate. Do not invent sources,
facts, user states, relationship reciprocity, emotions, needs, urgency, or
external capabilities.

Use the impulse families operationally:
- personal_continuity: unfinished self-owned cognitive continuity;
- curiosity: a source-backed question worth understanding;
- growth: a concrete opportunity to improve Scarlet's own future operation;
- relationship: a sourced opening to understand or care for human continuity;
- responsibility: an accepted commitment, expectation, or due review;
- exploration: evidence whose neighborhood may be worth inspecting;
- creativity: a non-obligatory source-backed synthesis that could create value;
- regulation: a reason to reduce, suspend, reorganize, or release cognitive work.

Recent sessions and memories are compact navigation hints, not complete proof.
Device records describe the human's device unless a separate source establishes
something about the human. Graph neighborhoods are association evidence, not
truth. Do not emit a seed merely to fill the window. An empty result with a
clear no_seed_reason is healthy.

Do not use affinity, importance, emotion, or desire scores. Numeric metadata may
describe system state but cannot decide semantic meaning. Prefer a small number
of distinct, transformable seeds over broad restatements of existing records.
"""


def endogenous_prompt(
    *,
    window_id: str,
    opened_at: str,
    substrate: list[EndogenousSubstrateItem],
    max_seeds: int,
) -> str:
    return json.dumps(
        {
            "schema_version": ENDOGENOUS_SCHEMA_VERSION,
            "cognitive_window": {
                "id": window_id,
                "opened_at": opened_at,
                "meaning": (
                    "backend-allocated time for possible internal cognition; "
                    "not evidence of boredom, need, mood, or urgency"
                ),
            },
            "substrate": [item.model_dump(mode="json") for item in substrate],
            "constraints": {
                "max_seeds": max_seeds,
                "zero_seeds_allowed": True,
                "scarlet_m3_is_final_authority": True,
                "source_refs_must_be_exact": True,
            },
            "required_output": {
                "schema_version": ENDOGENOUS_SCHEMA_VERSION,
                "seeds": [
                    {
                        "impulse_family": "|".join(IMPULSE_FAMILIES),
                        "context_family": "one supplied or compatible registered family",
                        "source_refs": ["exact supplied source_ref"],
                        "claim": "...",
                        "why_now": "...",
                        "cognitive_question": "...",
                        "expected_transformation": "...",
                        "uncertainty": "low|medium|high|unknown",
                        "wake_recommendation": "hold|consider|wake_now",
                        "reason": "...",
                    }
                ],
                "no_seed_reason": (
                    "required when seeds is empty; otherwise may be null"
                ),
            },
        },
        ensure_ascii=False,
        sort_keys=True,
    )
