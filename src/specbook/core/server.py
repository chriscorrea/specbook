"""Server management utilities for specbook web server."""

import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import psutil

from specbook.core.models import ServerConfig, ServerState, ServerStatus


def find_process_on_port(port: int) -> psutil.Process | None:
    """find process listening on the given port; returns the Process object if found (else None)"""
    for proc in psutil.process_iter():
        try:
            for conn in proc.net_connections(kind="inet"):
                if conn.laddr and hasattr(conn.laddr, "port"):
                    if conn.laddr.port == port and conn.status == "LISTEN":
                        return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # skip processes we can't read (e.g. other users' processes)
            continue
    return None


def is_specbook_process(proc: psutil.Process) -> bool:
    """check if process is a specbook server"""
    try:
        cmdline = " ".join(proc.cmdline())
        return "specbook" in cmdline  # look for 'specbook' in the argument
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def get_project_root_from_process(proc: psutil.Process) -> Path | None:
    """extract project root from specbook server process command line"""
    try:
        cmdline = proc.cmdline()
        # look for the project root path argument (last argument after port)
        for i, arg in enumerate(cmdline):
            if arg == "--project-root" and i + 1 < len(cmdline):
                return Path(cmdline[i + 1])
        # fallback: check if last arg is a valid path
        if cmdline and Path(cmdline[-1]).is_dir():
            return Path(cmdline[-1])
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return None


def get_server_status(port: int) -> ServerStatus:
    """Get the status of a server on a specific port.

    Returns ServerStatus with appropriate state:
        - RUNNING: specbook server is active on the port
        - STOPPED: no process is listening on the port
        - PORT_CONFLICT: non-specbook process is using the port
    """
    proc = find_process_on_port(port)

    if proc is None:
        return ServerStatus(
            port=port,
            state=ServerState.STOPPED,
            pid=None,
            project_root=None,
        )

    if is_specbook_process(proc):
        project_root = get_project_root_from_process(proc)
        return ServerStatus(
            port=port,
            state=ServerState.RUNNING,
            pid=proc.pid,
            project_root=project_root,
        )

    # some other process is using the port
    return ServerStatus(
        port=port,
        state=ServerState.PORT_CONFLICT,
        pid=proc.pid,
        project_root=None,
    )


def start_server(config: ServerConfig) -> int:
    """Start the specbook web server detached/in the background.

    Args:
        config: server configuration with port and project root

    Returns:
        PID of the spawned server process
    """
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "specbook.ui.web.app",
            str(config.port),
            str(config.project_root),
        ],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # give the server a moment to start
    time.sleep(0.5)
    return proc.pid


def stop_server(port: int) -> bool:
    """Stop a specbook server running on the given port.

    Args:
        port: Port the server is listening on.

    Returns:
        True if server was stopped, False if no server was running
    """
    proc = find_process_on_port(port)
    if proc is None:
        return False

    if not is_specbook_process(proc):
        return False

    try:
        proc.terminate()
        proc.wait(timeout=5)
        return True
    except (psutil.NoSuchProcess, psutil.TimeoutExpired):
        # try again, this time harder
        try:
            proc.kill()
            return True
        except psutil.NoSuchProcess:
            return True


def open_browser(url: str) -> bool:
    """Open URL in the default browser.

    Args:
        url: URL to open

    Returns:
        True if browser was launched successfully
    """
    try:
        return webbrowser.open(url)
    except Exception:
        return False
