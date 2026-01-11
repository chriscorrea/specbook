"""Data models for specbook project root detection."""

from dataclasses import dataclass
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
