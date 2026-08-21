from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from llm_max.adapters.ollama import OllamaAdapter
from llm_max.autotune import RuntimeUnavailableError as TuneRuntimeUnavailableError
from llm_max.autotune import TuningEngine, TuningOutcome
from llm_max.catalog import load_catalog
from llm_max.compatibility import classify_all
from llm_max.config import redis_enabled
from llm_max.domain import CompatibilityTier
from llm_max.launcher import LauncherService, RuntimeUnavailableError
from llm_max.profiler import scan_hardware
from llm_max.storage import get_storage

console = Console()

_TIER_STYLE = {
    CompatibilityTier.GREAT_FIT: ("Great fit", "bold green"),
    CompatibilityTier.WILL_RUN: ("Will run", "yellow"),
    CompatibilityTier.MAY_BE_SLOW: ("May be slow", "dark_orange"),
    CompatibilityTier.NOT_RECOMMENDED: ("Not recommended", "red"),
}

_OUTCOME_STYLE = {
    TuningOutcome.ACCEPTED_NEW: ("Applied new config", "bold green"),
    TuningOutcome.KEPT_BASELINE: ("Kept existing config", "yellow"),
    TuningOutcome.ROLLED_BACK: ("Rolled back", "bold red"),
    TuningOutcome.LOCKED: ("Locked — skipped", "dim"),
}


@click.group()
@click.version_option()
def main():
    """llm-max: profile your hardware, find LLMs that fit, tune them to max performance."""


@main.command()
def scan():
    """Profile this machine's GPU/CPU/RAM."""
    with console.status("Scanning hardware..."):
        hw = scan_hardware()

    if hw.has_gpu:
        table = Table(title="GPU(s) detected")
        table.add_column("Idx")
        table.add_column("Name")
        table.add_column("VRAM (free/total)")
        table.add_column("Util %")
        table.add_column("Temp °C")
        for gpu in hw.gpus:
            table.add_row(
                str(gpu.index),
                gpu.name,
                f"{gpu.free_vram_mb} / {gpu.total_vram_mb} MB",
                str(gpu.utilization_pct) if gpu.utilization_pct is not None else "-",
                str(gpu.temperature_c) if gpu.temperature_c is not None else "-",
            )
        console.print(table)
    else:
        console.print(
            "[yellow]No NVIDIA GPU detected[/yellow] — will use CPU-only "
            "compatibility estimates."
        )

    console.print(
        f"\nCPU: {hw.cpu_model or 'unknown'} "
        f"({hw.cpu_cores_physical} physical / {hw.cpu_cores_logical} logical cores)"
    )
    console.print(
        f"RAM: {hw.available_ram_mb:,} MB available / {hw.total_ram_mb:,} MB total"
    )
    console.print("\nRun [bold]llm-max models[/bold] to see which LLMs fit.")


@main.command()
def models():
    """Show which models from the catalog fit this machine."""
    with console.status("Scanning hardware..."):
        hw = scan_hardware()
    results = classify_all(hw)

    table = Table(title="Model compatibility for this machine")
    table.add_column("Model")
    table.add_column("Params")
    table.add_column("Tier")
    table.add_column("Why")

    for r in results:
        label, style = _TIER_STYLE[r.tier]
        table.add_row(
            r.model.id,
            f"{r.model.param_size_b}B",
            f"[{style}]{label}[/{style}]",
            r.reason,
        )
    console.print(table)


@main.command()
@click.argument("model_id")
def pull(model_id: str):
    """Download a model via Ollama."""
    service = LauncherService(adapter=OllamaAdapter(), storage=get_storage())

    console.print(f"Pulling [bold]{model_id}[/bold] via Ollama...")

    from rich.progress import (
        BarColumn,
        DownloadColumn,
        Progress,
        TextColumn,
        TransferSpeedColumn,
    )

    tasks = {}
    try:
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            console=console,
        ) as progress:
            for event in service.pull(model_id):
                status = event.get("status", "")
                digest = event.get("digest")
                total = event.get("total")
                completed = event.get("completed")

                if digest and total:
                    key = digest[:12]
                    if key not in tasks:
                        tasks[key] = progress.add_task(key, total=total)
                    progress.update(tasks[key], completed=completed or 0)
                elif status:
                    progress.console.print(f"  {status}")
    except RuntimeUnavailableError:
        console.print(
            "[red]Ollama doesn't seem to be running[/red] "
            "(expected at http://localhost:11434). Install/start it and retry."
        )
        raise SystemExit(1)

    console.print(f"[green]Done.[/green] Run it with: llm-max run {model_id}")


@main.command()
@click.argument("model_id")
@click.option("--prompt", "-p", default="Hello! Briefly introduce yourself.")
def run(model_id: str, prompt: str):
    """Run a prompt against a model via Ollama and report timing."""
    storage = get_storage()
    service = LauncherService(adapter=OllamaAdapter(), storage=storage)

    model_spec = next((m for m in load_catalog() if m.id == model_id), None)

    try:
        with console.status(f"Running {model_id}..."):
            result = service.run(model_id, prompt, model_spec=model_spec)
    except RuntimeUnavailableError:
        console.print(
            "[red]Ollama doesn't seem to be running[/red] "
            "(expected at http://localhost:11434)."
        )
        raise SystemExit(1)

    console.print(result["response"])
    console.print(
        f"\n[dim]{result['tokens_generated']} tokens in "
        f"{result['total_duration_s']}s"
        + (
            f" ({result['tokens_per_sec']} tok/s)"
            if result["tokens_per_sec"]
            else ""
        )
        + "[/dim]"
    )

    if getattr(storage, "last_used_fallback", False):
        console.print(
            "[yellow]Note:[/yellow] MySQL was unreachable — this run was "
            "saved to local SQLite instead."
        )


@main.command()
@click.option("--model", "model_id", default=None, help="Filter history to one model.")
@click.option("--limit", default=20, help="Max number of records to show.")
def history(model_id: str | None, limit: int):
    """Show recent `llm-max run` history from local storage."""
    store = get_storage()
    runs = store.list_runs(model_id=model_id, limit=limit)

    if getattr(store, "last_used_fallback", False):
        console.print(
            "[yellow]Note:[/yellow] MySQL was unreachable — showing local "
            "SQLite history instead.\n"
        )

    if not runs:
        console.print("No run history yet — try [bold]llm-max run <model>[/bold] first.")
        return

    table = Table(title="Run history")
    table.add_column("When")
    table.add_column("Model")
    table.add_column("Tokens")
    table.add_column("Duration")
    table.add_column("Tok/s")

    for r in runs:
        table.add_row(
            r.created_at or "-",
            r.model_id,
            str(r.tokens_generated),
            f"{r.total_duration_s}s",
            f"{r.tokens_per_sec}" if r.tokens_per_sec else "-",
        )
    console.print(table)


@main.command()
def status():
    """Show current hardware status, using a Redis cache if enabled."""
    profile = None
    cache_hit = False

    if redis_enabled():
        from llm_max.storage.redis_client import StatusCache

        cache = StatusCache()
        profile = cache.get_last_scan()
        cache_hit = profile is not None

    if profile is None:
        with console.status("Scanning hardware..."):
            profile = scan_hardware()
        if redis_enabled():
            cache.set_last_scan(profile)

    source = "[dim](from Redis cache)[/dim]" if cache_hit else "[dim](fresh scan)[/dim]"
    console.print(f"Hardware status {source}\n")

    if profile.has_gpu:
        table = Table(title="GPU(s)")
        table.add_column("Name")
        table.add_column("VRAM (free/total)")
        for gpu in profile.gpus:
            table.add_row(gpu.name, f"{gpu.free_vram_mb} / {gpu.total_vram_mb} MB")
        console.print(table)
    else:
        console.print("[yellow]No GPU detected[/yellow]")

    console.print(
        f"CPU: {profile.cpu_cores_physical} physical / "
        f"{profile.cpu_cores_logical} logical cores"
    )
    console.print(
        f"RAM: {profile.available_ram_mb:,} MB available / "
        f"{profile.total_ram_mb:,} MB total"
    )


def _print_tuning_session(session, model_id: str) -> None:
    label, style = _OUTCOME_STYLE[session.outcome]
    console.print(f"[{style}]{label}[/{style}] — {session.reason}\n")

    table = Table(title=f"Benchmark results for {model_id}")
    table.add_column("Config")
    table.add_column("Tok/s")
    table.add_column("p50 latency")
    table.add_column("p95 latency")
    table.add_column("Status")

    rows = [("baseline", session.baseline)] + [
        ("candidate", c) for c in session.candidates if c.config != session.baseline.config
    ]
    for label_prefix, candidate in rows:
        b = candidate.benchmark
        is_winner = candidate.config == session.winner.config
        marker = " *" if is_winner else ""
        status_text = (
            "OOM" if b.oom_occurred else ("failed" if not b.succeeded else "ok")
        )
        table.add_row(
            f"{candidate.config}{marker}",
            f"{b.tokens_per_sec:.1f}" if b.tokens_per_sec else "-",
            f"{b.p50_latency_s:.2f}s" if b.p50_latency_s else "-",
            f"{b.p95_latency_s:.2f}s" if b.p95_latency_s else "-",
            status_text,
        )
    console.print(table)
    console.print("[dim]* = winning config[/dim]")


@main.command()
@click.argument("model_id")
@click.option(
    "--dry-run", is_flag=True, help="Benchmark and show the recommendation without saving it."
)
def tune(model_id: str, dry_run: bool):
    """One-shot: benchmark a model against a small set of configs and
    apply whichever performs best."""
    storage = get_storage()
    engine = TuningEngine(adapter=OllamaAdapter(), storage=storage)
    model_spec = next((m for m in load_catalog() if m.id == model_id), None)

    try:
        with console.status(f"Benchmarking {model_id} (this runs several prompts per config)..."):
            session = engine.tune_once(model_id, model_spec=model_spec)
    except TuneRuntimeUnavailableError:
        console.print(
            "[red]Ollama doesn't seem to be running[/red] "
            "(expected at http://localhost:11434)."
        )
        raise SystemExit(1)

    _print_tuning_session(session, model_id)

    if session.outcome == TuningOutcome.ACCEPTED_NEW:
        if dry_run:
            console.print("\n[dim]Dry run — config not saved.[/dim]")
        else:
            engine.apply(session)
            console.print(f"\n[green]Saved.[/green] {model_id} will now run with {session.winner.config}.")
    else:
        console.print("\nNo change made.")


@main.group()
def autopilot():
    """Continuous background tuning for a model.

    Runs in the foreground until stopped (Ctrl+C) — never starts itself
    silently. See docs/PHASE3_DESIGN.md section 5 for why this boundary
    is deliberate.
    """


@autopilot.command("enable")
@click.argument("model_id")
@click.option("--interval", default=3600, help="Seconds between tuning passes.")
@click.option(
    "--max-iterations",
    default=None,
    type=int,
    help="Stop after N iterations (mainly useful for testing/demoing).",
)
def autopilot_enable(model_id: str, interval: int, max_iterations: int | None):
    """Start continuous tuning for MODEL_ID. Runs until Ctrl+C."""
    storage = get_storage()
    engine = TuningEngine(adapter=OllamaAdapter(), storage=storage)
    model_spec = next((m for m in load_catalog() if m.id == model_id), None)

    console.print(
        f"Starting autopilot for [bold]{model_id}[/bold] "
        f"(checking every {interval}s). Press Ctrl+C to stop.\n"
    )

    try:
        for session in engine.autopilot_loop(
            model_id,
            model_spec=model_spec,
            interval_seconds=interval,
            max_iterations=max_iterations,
        ):
            label, style = _OUTCOME_STYLE[session.outcome]
            console.print(f"[{style}]{label}[/{style}] — {session.reason}")
            if session.outcome == TuningOutcome.LOCKED:
                break
    except TuneRuntimeUnavailableError:
        console.print(
            "[red]Ollama doesn't seem to be running[/red] "
            "(expected at http://localhost:11434)."
        )
        raise SystemExit(1)
    except KeyboardInterrupt:
        console.print("\nAutopilot stopped.")


@autopilot.command("disable")
@click.argument("model_id")
def autopilot_disable(model_id: str):
    """Lock MODEL_ID's current config so autopilot skips it."""
    store = get_storage()
    existing = store.get_tuned_config(model_id)
    if existing is None:
        console.print(
            f"No tuned config exists yet for [bold]{model_id}[/bold] — "
            "run [bold]llm-max tune[/bold] first."
        )
        return
    store.lock_config(model_id)
    console.print(f"[green]Locked.[/green] Autopilot will skip {model_id} until unlocked.")


@autopilot.command("status")
@click.argument("model_id")
def autopilot_status(model_id: str):
    """Show the current saved config and recent autopilot events for MODEL_ID."""
    store = get_storage()
    config = store.get_tuned_config(model_id)

    if config is None:
        console.print(f"No tuned config saved yet for [bold]{model_id}[/bold].")
        return

    console.print(f"Current config: [bold]{config.config}[/bold]")
    console.print(f"Locked: {'yes' if config.is_locked else 'no'}")
    console.print(f"Saved at: {config.created_at}\n")

    events = store.list_autopilot_events(model_id=model_id, limit=10)
    if not events:
        console.print("[dim]No autopilot events logged yet.[/dim]")
        return

    table = Table(title="Recent autopilot events")
    table.add_column("When")
    table.add_column("Event")
    table.add_column("Details")
    for e in events:
        table.add_row(e.created_at or "-", e.event_type, str(e.details))
    console.print(table)


if __name__ == "__main__":
    main()