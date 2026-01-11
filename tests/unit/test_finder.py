"""Unit tests for project root finder."""

from pathlib import Path

import pytest

from specbook.core.finder import find_project_root


class TestFindProjectRootHappyPath:
    """tests for successful project root discovery."""

    def test_finds_project_from_root(self, project_with_both: Path) -> None:
        """should find project when searching from project root"""
        result = find_project_root(project_with_both)

        assert result.found is True
        assert result.project_root is not None
        # resolve both paths to handle macOS /var -> /private/var symlink
        assert result.project_root.path.resolve() == project_with_both.resolve()
        assert result.project_root.has_specify_dir is True
        assert result.project_root.has_specs_dir is True

    def test_finds_project_from_subdirectory(self, nested_subdir: Path) -> None:
        """should find project when searching from nested subdirectory"""
        result = find_project_root(nested_subdir)

        assert result.found is True
        assert result.project_root is not None
        # project root is the parent, not the nested subdir
        # resolve both paths to handle macOS /var -> /private/var symlink
        expected_root = nested_subdir.parent.parent.parent.resolve()
        assert result.project_root.path.resolve() == expected_root
        assert result.searched_from.resolve() == nested_subdir.resolve()


class TestFindProjectRootNotFound:
    """Tests for when no project root exists."""

    def test_not_found_returns_false(self, temp_dir: Path) -> None:
        """Should return found=False when no markers exist."""
        result = find_project_root(temp_dir)

        assert result.found is False
        assert result.project_root is None
        # resolve to handle macOS /var -> /private/var symlink
        assert result.searched_from.resolve() == temp_dir.resolve()
        # searched_to should be filesystem root
        assert result.searched_to == Path("/")

    def test_error_message_when_not_found(self, temp_dir: Path) -> None:
        """should provide helpful error message when not found"""
        result = find_project_root(temp_dir)

        assert result.error_message is not None
        assert "No spec-driven development project" in result.error_message
        assert str(temp_dir) in result.error_message
        assert ".specify/ or specs/" in result.error_message


class TestFindProjectRootOnlySpecify:
    """tests for projects with only .specify/ dir"""

    def test_finds_with_only_specify_dir(self, project_with_specify: Path) -> None:
        """should find project with only .specify/ marker."""
        result = find_project_root(project_with_specify)

        assert result.found is True
        assert result.project_root is not None
        assert result.project_root.has_specify_dir is True
        assert result.project_root.has_specs_dir is False
        assert result.project_root.markers == [".specify/"]


class TestFindProjectRootOnlySpecs:
    """tests for projects with only specs/ directory"""

    def test_finds_with_only_specs_dir(self, project_with_specs: Path) -> None:
        """should find project with only specs/ marker"""
        result = find_project_root(project_with_specs)

        assert result.found is True
        assert result.project_root is not None
        assert result.project_root.has_specify_dir is False
        assert result.project_root.has_specs_dir is True
        assert result.project_root.markers == ["specs/"]


class TestProjectRootMarkers:
    """tests for ProjectRoot marker properties"""

    def test_markers_display_both(self, project_with_both: Path) -> None:
        """should display both markers when both exist"""
        result = find_project_root(project_with_both)

        assert result.project_root is not None
        assert result.project_root.markers_display == ".specify/, specs/"

    def test_markers_display_single(self, project_with_specs: Path) -> None:
        """should display single marker when only one exists"""
        result = find_project_root(project_with_specs)

        assert result.project_root is not None
        assert result.project_root.markers_display == "specs/"
