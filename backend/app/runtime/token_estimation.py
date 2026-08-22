"""Shared deterministic token-estimation helpers for runtime planning.

Provider-reported usage remains authoritative after a call. These estimates are
only used before a call to budget context and history partitions.
"""

from __future__ import annotations

from math import ceil


def estimate_tokens(
    chars: int,
    chars_per_token: float,
    *,
    minimum_chars_per_token: float | None = None,
) -> int:
    """Return a conservative character-based token estimate.

    ``minimum_chars_per_token`` preserves the history runtime's defensive
    behavior for malformed ratios without imposing it on accounting callers
    that already validate their calibration inputs.
    """

    if chars <= 0:
        return 0
    ratio = float(chars_per_token)
    if minimum_chars_per_token is not None:
        ratio = max(ratio, minimum_chars_per_token)
    return ceil(chars / ratio)
