from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from llm_max.adapters.ollama import OllamaAdapter
from llm_max.compatibility import classify_all
from llm_max.domain import CompatibilityTier, RunRecord
from llm_max.profiler import scan_hardware
from llm_max.storage import SqliteStore

console = Console()

_TIER_STYLE = {
    CompatibilityTier.GREAT_FIT: ("Great fit", "bold green"),
    CompatibilityTier.WILL_RUN: ("Will run", "yellow"),
    CompatibilityTier.MAY_BE_SLOW: ("May be slow", "dark_orange"),
    CompatibilityTier.NOT_RECOMMENDED: ("Not recommended", "red"),
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
    adapter = OllamaAdapter()
    if not adapter.is_available():
        console.print(
            "[red]Ollama doesn't seem to be running[/red] "
            "(expected at http://localhost:11434). Install/start it and retry."
        )
        raise SystemExit(1)

    console.print(f"Pulling [bold]{model_id}[/bold] via Ollama...")

    from rich.progress import (
        BarColumn,
        DownloadColumn,
        Progress,
        TextColumn,
        TransferSpeedColumn,
    )

    tasks = {}
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        console=console,
    ) as progress:
        for event in adapter.pull(model_id):
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
                # non-download events: "pulling manifest", "verifying sha256
                # digest", "writing manifest", "success"
                progress.console.print(f"  {status}")

    console.print(f"[green]Done.[/green] Run it with: llm-max run {model_id}")


@main.command()
@click.argument("model_id")
@click.option("--prompt", "-p", default="Hello! Briefly introduce yourself.")
def run(model_id: str, prompt: str):
    """Run a prompt against a model via Ollama and report timing."""
    adapter = OllamaAdapter()
    if not adapter.is_available():
        console.print(
            "[red]Ollama doesn't seem to be running[/red] "
            "(expected at http://localhost:11434)."
        )
        raise SystemExit(1)

    with console.status(f"Running {model_id}..."):
        result = adapter.run(model_id, prompt)

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

    store = SqliteStore()
    store.save_run(
        RunRecord(
            model_id=model_id,
            runtime="ollama",
            prompt=prompt,
            tokens_generated=result["tokens_generated"],
            total_duration_s=result["total_duration_s"],
            tokens_per_sec=result["tokens_per_sec"],
        )
    )


@main.command()
@click.option("--model", "model_id", default=None, help="Filter history to one model.")
@click.option("--limit", default=20, help="Max number of records to show.")
def history(model_id: str | None, limit: int):
    """Show recent `llm-max run` history from local storage."""
    store = SqliteStore()
    runs = store.list_runs(model_id=model_id, limit=limit)

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


if __name__ == "__main__":
    main()