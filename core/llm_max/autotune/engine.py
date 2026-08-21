"""TuningEngine: the measure -> adjust -> evaluate -> accept loop.

This is the single implementation shared by one-shot `llm-max tune` and
autopilot mode (see docs/PHASE3_DESIGN.md section 2) — `tune_once()` is
one pass of the loop; `autopilot_loop()` calls it repeatedly with the
previously-accepted config as the new baseline, plus rollback handling
between passes.
"""

from __future__ import annotations

import time
from collections.abc import Iterator

from llm_max.adapters.base import RuntimeAdapter
from llm_max.autotune.evaluator import is_meaningful_improvement, pick_best
from llm_max.autotune.rollback import needs_rollback, rollback_target
from llm_max.autotune.search import generate_candidates
from llm_max.autotune.state import TuningCandidateResult, TuningOutcome, TuningSession
from llm_max.bench.runner import run_benchmark
from llm_max.domain import AutopilotEvent, HardwareProfile, ModelSpec, TunedConfig
from llm_max.launcher.config_builder import build_run_config
from llm_max.storage.base import Storage


class RuntimeUnavailableError(RuntimeError):
    """Raised when the configured runtime (e.g. Ollama) isn't reachable."""


class TuningEngine:
    def __init__(
        self,
        adapter: RuntimeAdapter,
        storage: Storage,
        hardware_provider=None,
    ):
        self.adapter = adapter
        self.storage = storage
        self._hardware_provider = hardware_provider

    def _scan(self) -> HardwareProfile:
        if self._hardware_provider is not None:
            return self._hardware_provider()
        from llm_max.profiler import scan_hardware

        return scan_hardware()

    def _default_baseline_config(self, model_spec: ModelSpec | None) -> dict:
        if model_spec is None:
            return {}
        hw = self._scan()
        return build_run_config(model_spec, hw) or {}

    def _log_event(self, model_id: str, event_type: str, details: dict) -> None:
        # Audit trail is best-effort: a logging failure should never break
        # the tuning loop itself.
        try:
            self.storage.save_autopilot_event(
                AutopilotEvent(model_id=model_id, event_type=event_type, details=details)
            )
        except Exception:
            pass

    def tune_once(
        self,
        model_id: str,
        model_spec: ModelSpec | None = None,
        baseline_config: dict | None = None,
    ) -> TuningSession:
        """One pass of measure -> adjust -> evaluate -> accept.

        `baseline_config` lets autopilot pass in the previously-accepted
        config as this pass's starting point. If omitted, the baseline is
        computed fresh from current hardware (same as one-shot `tune`).

        Raises RuntimeUnavailableError if the runtime isn't reachable.
        """
        if not self.adapter.is_available():
            raise RuntimeUnavailableError(
                f"{self.adapter.name} runtime is not available"
            )

        if baseline_config is None:
            baseline_config = self._default_baseline_config(model_spec)

        baseline = TuningCandidateResult(
            config=baseline_config,
            benchmark=run_benchmark(self.adapter, model_id, options=baseline_config or None),
        )

        candidate_configs = generate_candidates(baseline_config)
        candidates: list[TuningCandidateResult] = []
        for config in candidate_configs:
            if config == baseline_config:
                candidates.append(baseline)
                continue
            benchmark = run_benchmark(self.adapter, model_id, options=config or None)
            candidates.append(TuningCandidateResult(config=config, benchmark=benchmark))

        best = pick_best(candidates)

        if best is None:
            # Every candidate (including baseline) failed or OOM'd.
            return TuningSession(
                model_id=model_id,
                baseline=baseline,
                candidates=candidates,
                winner=baseline,
                outcome=TuningOutcome.KEPT_BASELINE,
                reason="every candidate failed or ran out of memory; keeping current config",
            )

        if best.config != baseline.config and is_meaningful_improvement(best, baseline):
            pct = _improvement_pct(baseline, best)
            return TuningSession(
                model_id=model_id,
                baseline=baseline,
                candidates=candidates,
                winner=best,
                outcome=TuningOutcome.ACCEPTED_NEW,
                reason=f"{best.config} improves throughput by {pct:.1f}% over baseline",
            )

        return TuningSession(
            model_id=model_id,
            baseline=baseline,
            candidates=candidates,
            winner=baseline,
            outcome=TuningOutcome.KEPT_BASELINE,
            reason="no candidate improved throughput enough to justify switching",
        )

    def apply(self, session: TuningSession) -> TunedConfig:
        """Persist the session's winning config as the model's tuned config,
        and log an 'adjust' audit event."""
        saved = self.storage.save_tuned_config(
            TunedConfig(model_id=session.model_id, config=session.winner.config)
        )
        self._log_event(
            session.model_id,
            "adjust",
            {"config": session.winner.config, "reason": session.reason},
        )
        return saved

    def autopilot_loop(
        self,
        model_id: str,
        model_spec: ModelSpec | None = None,
        interval_seconds: float = 3600,
        max_iterations: int | None = None,
        sleep_fn=time.sleep,
        initial_history: list[TuningCandidateResult] | None = None,
    ) -> Iterator[TuningSession]:
        """Repeatedly tune, sleeping `interval_seconds` between passes.

        Yields one TuningSession per iteration so the caller (the CLI)
        controls presentation. Stops (returns) if the model's tuned config
        is locked, or after `max_iterations` if given (mainly for tests —
        production use leaves this None and relies on the caller to
        Ctrl+C / stop the process).

        Between passes, checks whether the *currently active* config is
        newly broken (needs_rollback) — e.g. another process took VRAM
        since the last pass — and reverts immediately rather than trying
        to tune forward from a broken baseline. `initial_history` lets a
        caller seed known-good prior configs (e.g. when resuming autopilot
        after a restart) so rollback has somewhere to revert to even on
        the very first iteration of this call.
        """
        iteration = 0
        history: list[TuningCandidateResult] = list(initial_history or [])

        while max_iterations is None or iteration < max_iterations:
            existing = self.storage.get_tuned_config(model_id)
            if existing is not None and existing.is_locked:
                self._log_event(model_id, "lock", {"config": existing.config})
                yield TuningSession(
                    model_id=model_id,
                    baseline=TuningCandidateResult(
                        config=existing.config,
                        benchmark=_locked_placeholder_benchmark(existing.config),
                    ),
                    candidates=[],
                    winner=TuningCandidateResult(
                        config=existing.config,
                        benchmark=_locked_placeholder_benchmark(existing.config),
                    ),
                    outcome=TuningOutcome.LOCKED,
                    reason="config is locked; autopilot skipping this model",
                )
                return

            baseline_config = existing.config if existing is not None else None

            # Check whether the currently-active config is broken *before*
            # spending a full tuning pass on it.
            if baseline_config is not None and history:
                current_probe = TuningCandidateResult(
                    config=baseline_config,
                    benchmark=run_benchmark(self.adapter, model_id, options=baseline_config or None),
                )
                if needs_rollback(current_probe):
                    target = rollback_target(current_probe, history)
                    if target is not None:
                        self.storage.save_tuned_config(
                            TunedConfig(model_id=model_id, config=target)
                        )
                        self._log_event(
                            model_id,
                            "rollback",
                            {"from": current_probe.config, "to": target},
                        )
                        yield TuningSession(
                            model_id=model_id,
                            baseline=current_probe,
                            candidates=history,
                            winner=TuningCandidateResult(
                                config=target,
                                benchmark=current_probe.benchmark,
                            ),
                            outcome=TuningOutcome.ROLLED_BACK,
                            reason=f"active config failed; rolled back to {target}",
                        )
                        iteration += 1
                        if max_iterations is None or iteration < max_iterations:
                            sleep_fn(interval_seconds)
                        continue

            session = self.tune_once(model_id, model_spec=model_spec, baseline_config=baseline_config)
            history.append(session.winner)

            if session.outcome == TuningOutcome.ACCEPTED_NEW:
                self.apply(session)

            yield session

            iteration += 1
            if max_iterations is None or iteration < max_iterations:
                sleep_fn(interval_seconds)


def _improvement_pct(baseline: TuningCandidateResult, candidate: TuningCandidateResult) -> float:
    baseline_tps = baseline.benchmark.tokens_per_sec or 0.0
    candidate_tps = candidate.benchmark.tokens_per_sec or 0.0
    if baseline_tps <= 0:
        return 0.0
    return (candidate_tps - baseline_tps) / baseline_tps * 100


def _locked_placeholder_benchmark(config: dict):
    from llm_max.bench.metrics import BenchmarkResult

    return BenchmarkResult(config=config, samples_completed=0, samples_attempted=0)