"""Rich console helpers for specbook CLI output."""

from contextlib import contextmanager
from typing import Generator

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# shared console instance
console = Console()


def error_panel(message: str, title: str = "Error") -> None:
    """display an error message in a red Rich panel"""
    console.print(Panel(message, title=title, border_style="red"))


def success_output(path: str, markers: str) -> None:
    """display successful project root discovery in green"""
    console.print(f"[green]✓[/green] Project root: {path}")
    console.print(f"  Found: {markers}")


def server_message(message: str, url: str | None = None, path: str | None = None) -> None:
    """display a server status message with optional details"""
    console.print(f"[green]✓[/green] {message}")
    if url:
        console.print(f"  URL: {url}")
    if path:
        console.print(f"  Serving: {path}")


def server_info(message: str) -> None:
    """display an informational server message"""
    console.print(f"[blue]ℹ[/blue] {message}")


def server_error(message: str, suggestion: str | None = None) -> None:
    """display a server error message in a red panel with optional suggestion"""
    full_message = message
    if suggestion:
        full_message = f"{message}\n\n{suggestion}"
    console.print(Panel(full_message, title="Error", border_style="red"))


@contextmanager
def search_progress() -> Generator[None, None, None]:
    """context manager for displaying progress spinner"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,  # remove after complete
        console=console,
    ) as progress:
        progress.add_task("Searching for project root...", total=None)
        yield
