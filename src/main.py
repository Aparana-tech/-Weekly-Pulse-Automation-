"""
Pulse CLI Application.

Command-line interface for running the pipeline, checking status, and viewing history.
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from src.config.product_registry import ProductRegistry
from src.config.settings import Settings
from src.config.week_utils import current_iso_week, format_iso_week, parse_iso_week
from src.delivery import MCPClientManager
from src.orchestrator import run_pulse
from src.state.models import RunRecord
from src.state.run_ledger import RunLedger

console = Console()


@click.group()
def cli() -> None:
    """Pulse — Automated Weekly App Review Pipeline."""
    pass


def _get_week_str(week_arg: Optional[str]) -> str:
    if week_arg:
        # Validate format
        year, week = parse_iso_week(week_arg)
        return format_iso_week(year, week)
    else:
        year, week = current_iso_week()
        return format_iso_week(year, week)


def _load_core_components() -> tuple[Settings, ProductRegistry, RunLedger, MCPClientManager]:
    settings = Settings()
    try:
        registry = ProductRegistry.from_file("config/products.json")
    except FileNotFoundError:
        console.print("[red]Error: config/products.json not found.[/red]")
        raise click.Abort()
        
    ledger = RunLedger()
    client_manager = MCPClientManager()
    
    return settings, registry, ledger, client_manager


@cli.command()
@click.option("--product", help="Product slug to run.")
@click.option("--week", help="ISO week string (e.g. 2026-W23). Defaults to current week.")
@click.option("--all", "run_all", is_flag=True, help="Run for all registered products.")
@click.option("--dry-run", is_flag=True, help="Run without delivering payloads.")
@click.option("--force", is_flag=True, help="Bypass production confirmation prompts.")
def run(product: Optional[str], week: Optional[str], run_all: bool, dry_run: bool, force: bool) -> None:
    """Execute the Pulse pipeline."""
    if not product and not run_all:
        console.print("[red]Error: Must specify --product or --all[/red]")
        raise click.Abort()
        
    week_str = _get_week_str(week)
    iso_year, iso_week = parse_iso_week(week_str)
    
    settings, registry, ledger, client_manager = _load_core_components()
    
    if settings.env == "production" and settings.email_mode == "send" and not force:
        console.print("[bold yellow]WARNING: You are about to run in PRODUCTION with EMAIL_MODE=send.[/bold yellow]")
        if not click.confirm("Are you sure you want to proceed and send live emails?"):
            console.print("Aborted.")
            raise click.Abort()
    
    products_to_run = registry.list_slugs() if run_all else [product]
    
    async def _run_all() -> None:
        for slug in products_to_run:
            if not slug:
                continue
            console.print(f"[bold blue]Starting Pulse for {slug} ({week_str})[/bold blue]")
            try:
                record = await run_pulse(
                    product_slug=slug,
                    iso_year=iso_year,
                    iso_week=iso_week,
                    settings=settings,
                    registry=registry,
                    ledger=ledger,
                    client_manager=client_manager,
                    dry_run=dry_run,
                )
                console.print(f"[green]Completed {slug} — Status: {record.status.value}[/green]")
            except Exception as e:
                console.print(f"[bold red]Failed {slug}: {e}[/bold red]")
                
    asyncio.run(_run_all())


@cli.command()
@click.option("--product", required=True, help="Product slug.")
@click.option("--week", required=True, help="ISO week string (e.g. 2026-W23).")
def status(product: str, week: str) -> None:
    """Check the status of a specific pipeline run."""
    week_str = _get_week_str(week)
    iso_year, iso_week = parse_iso_week(week_str)
    key = f"{product}:{iso_year}:W{iso_week:02d}"
    
    _, _, ledger, _ = _load_core_components()
    record = ledger.get_record(key)
    
    if not record:
        console.print(f"[yellow]No record found for {key}[/yellow]")
        return
        
    console.print(f"[bold]Status for {key}:[/bold] [blue]{record.status.value}[/blue]")
    console.print(f"Started: {record.started_at}")
    if record.completed_at:
        console.print(f"Completed: {record.completed_at}")
        
    console.print("\n[bold]Metrics:[/bold]")
    console.print(f"Reviews Fetched: {record.reviews_fetched.total}")
    console.print(f"Clusters: {record.clusters_found}")
    console.print(f"Themes: {record.themes_generated}")
    console.print(f"Quotes Validated: {record.quotes_validated}")
    
    console.print("\n[bold]Delivery:[/bold]")
    if record.doc_delivered:
        console.print("[green]Doc: Delivered[/green]")
    else:
        console.print("[yellow]Doc: Pending/Skipped[/yellow]")
        
    if record.email_delivered:
        console.print("[green]Email: Delivered[/green]")
    else:
        console.print("[yellow]Email: Pending/Skipped[/yellow]")


@cli.command()
@click.option("--product", help="Filter by product slug.")
@click.option("--limit", default=10, type=int, help="Maximum number of records to show.")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
def history(product: Optional[str], limit: int, output_format: str) -> None:
    """View recent pipeline runs."""
    _, _, ledger, _ = _load_core_components()
    
    # Sort records newest first
    records = list(ledger._cache.values())
    records.sort(key=lambda r: r.started_at, reverse=True)
    
    if product:
        records = [r for r in records if r.product == product]
        
    records = records[:limit]
    
    if not records:
        console.print("No history found.")
        return
        
    if output_format == "json":
        data = [json.loads(r.model_dump_json()) for r in records]
        console.print(json.dumps(data, indent=2))
        return
        
    table = Table(title="Recent Pulse Runs")
    table.add_column("Product", style="cyan")
    table.add_column("Week", style="magenta")
    table.add_column("Status")
    table.add_column("Started At")
    
    for r in records:
        status_color = "green" if r.status == "completed" else "red" if r.status == "failed" else "yellow"
        week_str = f"W{r.iso_week:02d} {r.iso_year}"
        table.add_row(
            r.product,
            week_str,
            f"[{status_color}]{r.status.value}[/{status_color}]",
            r.started_at.strftime("%Y-%m-%d %H:%M") if r.started_at else "N/A"
        )
        
    console.print(table)


if __name__ == "__main__":
    cli()
