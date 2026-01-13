"""Specbook CLI application."""

from pathlib import Path

import typer

from specbook.core.finder import find_project_root
from specbook.core.models import SearchContext, ServerConfig, ServerState
from specbook.core.server import (
    get_server_status,
    open_browser,
    start_server,
    stop_server,
)
from specbook.ui.console import (
    error_panel,
    search_progress,
    server_error,
    server_info,
    server_message,
    success_output,
)

# 📞 SPEC
DEFAULT_PORT = 7732

app = typer.Typer(
    help="CLI tool to view spec-driven development docs",
    no_args_is_help=False,
    invoke_without_command=True,
)


def _start_server_impl(port: int, path: str | None) -> None:
    """implementation of server start logic"""
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
    if not result.found or not result.project_root:
        error_panel(result.error_message or "Unknown error")
        raise typer.Exit(code=1)

    project_root = result.project_root.path

    # check current port status
    current_status = get_server_status(port)

    if current_status.state == ServerState.PORT_CONFLICT:
        # another (non-specbook) process is using the port
        server_error(
            f"Port {port} is already in use by another application",
            f"Try a different port with: specbook -p {port + 1}",
        )
        raise typer.Exit(code=1)

    if current_status.state == ServerState.RUNNING:
        # existing specbook server - auto-restart
        stop_server(port)

    # start the server
    config = ServerConfig(port=port, project_root=project_root)
    start_server(config)

    # open browser and show message
    open_browser(config.url)
    server_message(
        f"Server started at {config.url}",
        path=str(project_root),
    )
    typer.echo("  Press Ctrl+C or run 'specbook stop' to stop")
    raise typer.Exit(code=0)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    port: int = typer.Option(
        DEFAULT_PORT,
        "--port",
        "-p",
        help="Port to run the server on",
    ),
) -> None:
    """Start the spec viewer web server (or use a subcommand).

    Without arguments, finds the project root from current directory,
    starts a web server, *and* launches the browser.
    """
    # if a subcommand was invoked, don't run the default
    if ctx.invoked_subcommand is not None:
        return

    # default behavior: start the server
    _start_server_impl(port, None)


@app.command()
def serve(
    port: int = typer.Option(
        DEFAULT_PORT,
        "--port",
        "-p",
        help="Port to run the server on",
    ),
    path: str | None = typer.Argument(
        None,
        help="Directory to search from (defaults to current directory)",
    ),
) -> None:
    """start the spec viewer web server *with* explicit path"""
    _start_server_impl(port, path)


@app.command()
def stop(
    port: int = typer.Option(
        DEFAULT_PORT,
        "--port",
        "-p",
        help="Port of the server to stop",
    ),
) -> None:
    """stop a running specbook server."""
    status = get_server_status(port)

    if status.state == ServerState.STOPPED:
        server_info(f"No server running on port {port}")
        raise typer.Exit(code=0)

    if status.state == ServerState.PORT_CONFLICT:
        server_error(
            f"Port {port} is in use by another application"
        )
        raise typer.Exit(code=1)

    # stop the specbook server
    if stop_server(port):
        server_message("Server stopped")
        raise typer.Exit(code=0)
    else:
        server_error("Failed to stop server")
        raise typer.Exit(code=1)


@app.command()
def status(
    port: int = typer.Option(
        DEFAULT_PORT,
        "--port",
        "-p",
        help="Port to check server status on",
    ),
) -> None:
    """show the status of a specbook server"""
    server_status = get_server_status(port)

    if server_status.state == ServerState.STOPPED:
        server_info(f"No server running on port {port}")
        raise typer.Exit(code=0)

    if server_status.state == ServerState.PORT_CONFLICT:
        server_info(f"Port {port} is in use by another application (not specbook)")
        raise typer.Exit(code=0)

    # server is running
    server_message(
        "Server running",
        url=server_status.url,
        path=str(server_status.project_root) if server_status.project_root else None,
    )
    if server_status.pid:
        typer.echo(f"  PID: {server_status.pid}")
    raise typer.Exit(code=0)


@app.command()
def restart(
    port: int = typer.Option(
        DEFAULT_PORT,
        "--port",
        "-p",
        help="Port to restart the server on",
    ),
    path: str | None = typer.Argument(
        None,
        help="Directory to search from (defaults to current directory)",
    ),
) -> None:
    """restart the specbook server."""
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

    if not result.found or not result.project_root:
        error_panel(result.error_message or "Unknown error")
        raise typer.Exit(code=1)

    project_root = result.project_root.path

    # stop existing server if running
    current_status = get_server_status(port)
    if current_status.state == ServerState.RUNNING:
        stop_server(port)
    elif current_status.state == ServerState.PORT_CONFLICT:
        server_error(
            f"Port {port} is already in use by another application",
            f"Try a different port with: specbook restart -p {port + 1}",
        )
        raise typer.Exit(code=1)

    # start the server
    config = ServerConfig(port=port, project_root=project_root)
    start_server(config)

    # open browser and show message
    open_browser(config.url)
    server_message(
        f"Server restarted at {config.url}",
        path=str(project_root),
    )
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
