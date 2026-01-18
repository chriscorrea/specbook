"""Data models for specbook project root detection and server management."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

__all__ = [
    "ProjectRoot",
    "SearchContext",
    "ServerState",
    "SpecStatus",
    "SpecDocument",
    "CompletionStatus",
    "ProjectDocument",
    "ProjectListing",
    "SpecDirectoryExpanded",
]


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
            # f"Reached: {self.searched_to}\n\n"
            # f"Specbook works in a project with .specify/ or specs/"
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


class SpecStatus(Enum):
    """workflow status for a specification"""

    DRAFT = "draft"
    IN_REVIEW = "in-review"
    APPROVED = "approved"
    IMPLEMENTING = "implementing"
    COMPLETE = "complete"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str | None) -> "SpecStatus":
        """parse status string, returning DRAFT for missing,  UNKNOWN bad data"""
        if not value:
            return cls.DRAFT

        # normalize string
        normalized = value.lower().strip().replace("_", "-")

        for status in cls:
            if status.value == normalized:
                return status

        return cls.UNKNOWN


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


@dataclass
class ProjectDocument:
    """project-level document for sidebar display"""

    name: str
    """display name (e.g., 'Constitution', 'CLAUDE.md', and so on)"""

    path: Path
    """absolute path to the document"""

    category: str
    """grouping: 'guide' for constitution/agent, 'memory' for .specify/memory/"""


@dataclass
class SpecDocument:
    """document within a spec directory"""

    name: str
    """filename (e.g., 'spec.md', 'plan.md')"""

    path: Path
    """absolute path to the document"""

    display_name: str
    """human-readable name (e.g., 'Specification', 'Plan')"""

    doc_type: str
    """type identifier: 'spec', 'plan', 'tasks', 'research', 'data-model', 'quickstart', 'other'"""

    status: "SpecStatus" = None  # type: ignore[assignment]
    """workflow status from doc frontmatter
    TODO: consider all docs in spec dir to determine status
    """

    def __post_init__(self) -> None:
        if self.status is None:
            self.status = SpecStatus.UNKNOWN


@dataclass
class CompletionStatus:
    """completion status for a spec"""

    total_tasks: int
    """total number of checkbox items in tasks.md"""

    completed_tasks: int
    """number of checked items [x]"""

    @property
    def is_complete(self) -> bool:
        """true if all tasks are completed (or no tasks exist)

        NOTE: this is a temporary definition of completness; in the future,
        other approaches of inference or explicit annotation may be used
        """
        return self.total_tasks > 0 and self.completed_tasks == self.total_tasks

    @property
    def progress_percent(self) -> int:
        """completion percentage (0-100)"""
        if self.total_tasks == 0:
            return 0
        return int((self.completed_tasks / self.total_tasks) * 100)


@dataclass
class SpecDirectoryExpanded:
    """specification directory with documents and completion status"""

    name: str
    """directory name (e.g., '001-spec-core')"""

    path: Path
    """absolute path to the directory"""

    documents: list[SpecDocument]
    """documents in this spec, ordered by type priority"""

    completion: CompletionStatus
    """completion status from tasks.md analysis"""

    status: SpecStatus = SpecStatus.DRAFT
    """workflow status from spec.md frontmatter"""

    @property
    def is_complete(self) -> bool:
        """true if spec is complete"""
        return self.completion.is_complete


@dataclass
class ProjectListing:
    """complete project structure for web UI"""

    project_root: Path
    """path to project root"""

    project_documents: list[ProjectDocument]
    """project-level docs (constitution, agent files)"""

    specs: list[SpecDirectoryExpanded]
    """spec directories with documents and completion"""

    @property
    def has_project_documents(self) -> bool:
        """true if any project-level documents exist"""
        return len(self.project_documents) > 0

    @property
    def is_empty(self) -> bool:
        """True if no specs found"""
        return len(self.specs) == 0
