"""Data models for specbook project root detection and server management."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


@dataclass
class ProjectRoot:
    """discovered Specbook project root"""

    path: Path
    """absolute path to the project root directory"""

    has_specify_dir: bool
    """true if .specify/ directory exists at root"""

    has_specs_dir: bool
    """true if specs/ directory exists at root"""

    @property
    def markers(self) -> list[str]:
        """list of marker directories found"""
        result = []
        if self.has_specify_dir:
            result.append(".specify/")
        if self.has_specs_dir:
            result.append("specs/")
        return result

    @property
    def markers_display(self) -> str:
        """formatted string of markers for display"""
        return ", ".join(self.markers)


@dataclass
class SearchContext:
    """configuration for project root search"""

    start_path: Path
    """directory to start searching from"""

    @classmethod
    def from_cwd(cls) -> "SearchContext":
        """create context starting from current working directory"""
        return cls(start_path=Path.cwd())

    @classmethod
    def from_path(cls, path: str | Path) -> "SearchContext":
        """create context starting from specified path"""
        return cls(start_path=Path(path).resolve())


@dataclass
class SearchResult:
    """result of searching for project root"""

    found: bool
    """true if a project root was found"""

    project_root: ProjectRoot | None
    """discovered project root (or None if not found)"""

    searched_from: Path
    """starting directory of the search"""

    searched_to: Path
    """last directory checked (filesystem root if not found)"""

    @property
    def error_message(self) -> str | None:
        """user-friendly error message if not found"""
        if self.found:
            return None
        return (
            f"No spec-driven development project found.\n\n"
            f"Did not find .specify/ or specs/ at \033[1m{self.searched_from}\033[0m\n"
            #f"Reached: {self.searched_to}\n\n"
            #f"Specbook works in a project with .specify/ or specs/"
        )


# server management models

@dataclass
class ServerConfig:
    """config for a specbook web server"""

    port: int
    """port to bind server to"""

    project_root: Path
    """absolute path to the project root being served"""

    host: str = "127.0.0.1"
    """host to bind to—always localhost"""

    @property
    def url(self) -> str:
        """full URL for the server."""
        return f"http://{self.host}:{self.port}"


class ServerState(Enum):
    """possible states for a server port"""

    RUNNING = "running"
    STOPPED = "stopped"
    PORT_CONFLICT = "conflict"


@dataclass
class ServerStatus:
    """status of a server on a specific port"""

    port: int
    """port number being checked"""

    state: ServerState
    """current state of the port"""

    pid: int | None
    """process ID if running (else None)"""

    project_root: Path | None
    """project being served if running (else None)"""

    @property
    def url(self) -> str | None:
        """URL if server is running"""
        if self.state == ServerState.RUNNING:
            return f"http://127.0.0.1:{self.port}"
        return None

    @property
    def is_running(self) -> bool:
        """True if a specbook server is running on this port"""
        return self.state == ServerState.RUNNING

    @property
    def has_conflict(self) -> bool:
        """True if port is occupied by a non-specbook process"""
        return self.state == ServerState.PORT_CONFLICT


@dataclass
class SpecDirectory:
    """specification directory for display"""

    name: str
    """directory name (e.g., '001-spec-a')"""

    path: Path
    """absolute path to the directory"""

    @classmethod
    def from_path(cls, path: Path) -> "SpecDirectory":
        """create from a directory path"""
        return cls(name=path.name, path=path)


@dataclass
class SpecListing:
    """all spec directories in a project"""

    project_root: Path
    """path to the project root"""

    specs: list[SpecDirectory]
    """list of spec directories, sorted by name"""

    @property
    def is_empty(self) -> bool:
        """True if no specs found"""
        return len(self.specs) == 0

    @classmethod
    def from_project(cls, project_root: Path) -> "SpecListing":
        """scan project and build spec listing"""
        specs_dir = project_root / "specs"
        if not specs_dir.is_dir():
            return cls(project_root=project_root, specs=[])

        specs = [
            SpecDirectory.from_path(p)
            for p in sorted(specs_dir.iterdir())
            if p.is_dir() and not p.name.startswith(".")
        ]
        return cls(project_root=project_root, specs=specs)
