"""
SuperAI Main CLI (Typer-based)
"""

import typer
from rich import print as rprint
from src.core.cli_discovery import discover_and_update_config, CLIDiscovery
from src.core.model_updater import merge_discovered_models_into_config

app = typer.Typer(help="SuperAI - Multi-model AI Super App")

@app.command()
def discover():
    """Discover installed AI CLIs and available models."""
    rprint("[bold cyan]Running CLI & Model Discovery...[/bold cyan]")
    result = discover_and_update_config()
    rprint("[green]Discovery complete. Results saved to config/discovered_clis.json[/green]")

@app.command()
def update_models():
    """Merge discovered external CLI models into config/models.json"""
    rprint("[bold cyan]Merging discovered models into config...[/bold cyan]")
    merge_discovered_models_into_config()
    rprint("[green]models.json updated with discovered external CLIs.[/green]")

@app.command()
def init():
    """Initialize SuperAI (runs discovery + model update on first setup)."""
    rprint("[bold green]Initializing SuperAI...[/bold green]")
    discover_and_update_config()
    merge_discovered_models_into_config()
    rprint("[bold green]SuperAI initialized successfully![/bold green]")

if __name__ == "__main__":
    app()
