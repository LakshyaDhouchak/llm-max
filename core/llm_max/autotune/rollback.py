"""Rollback detection and execution for autopilot mode.

Rollback is a different concern from "did we find something better"
(evaluator.py) — this handles "the config we're currently running is now
actively broken and must be reverted immediately", e.g. another process
took VRAM and the previously-fine config now OOMs.
"""

from __future__ import annotations

from llm_max.autotune.state import TuningCandidateResult


def needs_rollback(active: TuningCandidateResult) -> bool:
    """True if the currently active config is failing right now and must
    be reverted before anything else happens this cycle."""
    return active.benchmark.oom_occurred or not active.benchmark.succeeded


def rollback_target(
    current: TuningCandidateResult, history: list[TuningCandidateResult]
) -> dict | None:
    """Pick the config to revert to: the most recent prior candidate in
    `history` (oldest-to-newest order assumed) that succeeded and did not
    OOM. Returns None if there's no known-good config to fall back to —
    callers should treat that as "stop autopilot for this model and alert
    the user", not retry blindly.
    """
    for candidate in reversed(history):
        if candidate.config == current.config:
            continue
        if candidate.benchmark.succeeded and not candidate.benchmark.oom_occurred:
            return candidate.config
    return None