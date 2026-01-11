"""Integration tests for specbook CLI."""

import os
from pathlib import Path

from typer.testing import CliRunner

from specbook.cli import app

runner = CliRunner()


class TestCLIFromCurrentDirectory:
    """tests for running specbook from current directory (no args)"""

    def test_finds_project_from_cwd(self, project_with_both: Path) -> None:
        """should find project when run from project root"""
        # change to project directory for this test
        original_cwd = os.getcwd()
        try:
            os.chdir(project_with_both)
            result = runner.invoke(app)

            assert result.exit_code == 0
            assert "Project root:" in result.output
            assert str(project_with_both) in result.output
        finally:
            os.chdir(original_cwd)

    def test_finds_project_from_subdirectory(self, nested_subdir: Path) -> None:
        """should find project when run from nested subdirectory"""
        project_root = nested_subdir.parent.parent.parent
        original_cwd = os.getcwd()
        try:
            os.chdir(nested_subdir)
            result = runner.invoke(app)

            assert result.exit_code == 0
            assert str(project_root) in result.output
        finally:
            os.chdir(original_cwd)


class TestCLIWithPathArgument:
    """tests for specbook with explicit path argument"""

    def test_finds_project_with_path_arg(self, project_with_both: Path) -> None:
        """should find project when path argument provided"""
        result = runner.invoke(app, [str(project_with_both)])

        assert result.exit_code == 0
        assert "Project root:" in result.output
        assert str(project_with_both) in result.output

    def test_finds_project_from_subdirectory_path(self, nested_subdir: Path) -> None:
        """should find project when searching from subdirectory path"""
        project_root = nested_subdir.parent.parent.parent
        result = runner.invoke(app, [str(nested_subdir)])

        assert result.exit_code == 0
        assert str(project_root) in result.output


class TestCLIErrorCases:
    """tests for CLI error handling"""

    def test_nonexistent_path_error(self) -> None:
        """should show error for non-existent path"""
        result = runner.invoke(app, ["/nonexistent/path/that/does/not/exist"])

        assert result.exit_code == 2
        assert "does not exist" in result.output

    def test_file_instead_of_directory_error(self, temp_dir: Path) -> None:
        """should show error when path is a file, not directory"""
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test content")

        result = runner.invoke(app, [str(test_file)])

        assert result.exit_code == 2
        assert "not a directory" in result.output

    def test_no_project_found_error(self, temp_dir: Path) -> None:
        """should show error when no project markers are found"""
        result = runner.invoke(app, [str(temp_dir)])

        assert result.exit_code == 1
        assert "No spec-driven development project" in result.output


class TestCLIHelp:
    """tests for CLI help output"""

    def test_help_flag(self) -> None:
        """should display help with a --help flag"""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        # verify help shows tool description
        assert "driven development" in result.output.lower()


class TestCLIMarkerDisplay:
    """tests for displaying which markers were found"""

    def test_displays_both_markers(self, project_with_both: Path) -> None:
        """Should display both markers when both exist"""
        result = runner.invoke(app, [str(project_with_both)])

        assert result.exit_code == 0
        assert ".specify/" in result.output
        assert "specs/" in result.output

    def test_displays_only_specify(self, project_with_specify: Path) -> None:
        """should display only .specify/ when only that exists"""
        result = runner.invoke(app, [str(project_with_specify)])

        assert result.exit_code == 0
        assert ".specify/" in result.output
        assert "specs/" not in result.output

    def test_displays_only_specs(self, project_with_specs: Path) -> None:
        """should display only specs/ when only that exists"""
        result = runner.invoke(app, [str(project_with_specs)])

        assert result.exit_code == 0
        assert "specs/" in result.output
        # make sure we're not seeing ".specify/" as part of a path
        lines = [l for l in result.output.split("\n") if "Found:" in l]
        if lines:
            assert ".specify/" not in lines[0]
