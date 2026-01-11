"""Specbook CLI application."""

import sys
from pathlib import Path

import typer

from specbook.core.finder import find_project_root
from specbook.core.models import SearchContext
from specbook.ui.console import error_panel, search_progress, success_output

app = typer.Typer(
    help="CLI tool to view specification-driven development docs.",
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    path: str | None = typer.Argument(
        None,
        help="Directory to search from (defaults to current directory)",
    ),
) -> None:
    """Find the Specbook project root directory.

    Searches from the current directory (or specified path) upward through
    ancestor directories looking for .specify/ or specs/ directories.
    """
    # if a subcommand was invoked, don't run the default
    if ctx.invoked_subcommand is not None:
        return

    # validate provided path argument
    if path is not None:
        target = Path(path)
        if not target.exists():
            error_panel(f"Directory does not exist: {path}")
            raise typer.Exit(code=2)
        if not target.is_dir():
            error_panel(f"Path is not a directory: {path}")
            raise typer.Exit(code=2)
        search_ctx = SearchContext.from_path(path)
    else:
        search_ctx = SearchContext.from_cwd()

    # search for project root
    with search_progress():
        result = find_project_root(search_ctx.start_path)

    # display results
    if result.found and result.project_root:
        success_output(
            str(result.project_root.path),
            result.project_root.markers_display,
        )
        raise typer.Exit(code=0)
    else:
        error_panel(result.error_message or "Unknown error")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
