"""Integration tests for specbook CLI."""

import os
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from specbook.cli import DEFAULT_PORT, app

runner = CliRunner()


class TestCLIServerStart:
    """tests for the serve command that starts the web server"""

    def test_starts_server_from_project(self, project_with_both: Path) -> None:
        """CLI starts server and returns prompt"""
        # mock the server start and browser open to avoid actual side effects
        with (
            patch("specbook.cli.start_server") as mock_start,
            patch("specbook.cli.open_browser") as mock_browser,
            patch("specbook.cli.get_server_status") as mock_status,
        ):
            from specbook.core.models import ServerState, ServerStatus

            mock_status.return_value = ServerStatus(
                port=DEFAULT_PORT,
                state=ServerState.STOPPED,
                pid=None,
                project_root=None,
            )

            result = runner.invoke(app, ["serve", str(project_with_both)])

            assert result.exit_code == 0
            assert "Server started" in result.output
            assert f"http://127.0.0.1:{DEFAULT_PORT}" in result.output
            mock_start.assert_called_once()
            mock_browser.assert_called_once()

    def test_starts_server_with_custom_port(self, project_with_both: Path) -> None:
        """CLI starts server on custom port with -p flag."""
        with (
            patch("specbook.cli.start_server") as mock_start,
            patch("specbook.cli.open_browser"),
            patch("specbook.cli.get_server_status") as mock_status,
        ):
            from specbook.core.models import ServerState, ServerStatus

            mock_status.return_value = ServerStatus(
                port=3627,
                state=ServerState.STOPPED,
                pid=None,
                project_root=None,
            )

            result = runner.invoke(app, ["serve", "-p", "3627", str(project_with_both)])

            assert result.exit_code == 0
            assert "3627" in result.output  
            # verify start_server was called with custom port
            call_args = mock_start.call_args[0][0]
            assert call_args.port == 3627 # Dial D-O-C-S

    def test_auto_restarts_existing_specbook_server(
        self, project_with_both: Path
    ) -> None:
        """CLI auto-restarts existing specbook server on same port"""
        with (
            patch("specbook.cli.start_server"),
            patch("specbook.cli.open_browser"),
            patch("specbook.cli.stop_server") as mock_stop,
            patch("specbook.cli.get_server_status") as mock_status,
        ):
            from specbook.core.models import ServerState, ServerStatus

            mock_status.return_value = ServerStatus(
                port=DEFAULT_PORT,
                state=ServerState.RUNNING,
                pid=12345,
                project_root=project_with_both,
            )

            result = runner.invoke(app, ["serve", str(project_with_both)])

            assert result.exit_code == 0
            mock_stop.assert_called_once_with(DEFAULT_PORT)

    def test_shows_error_for_port_conflict(self, project_with_both: Path) -> None:
        """CLI shows error when port is used by non-specbook process"""
        with patch("specbook.cli.get_server_status") as mock_status:
            from specbook.core.models import ServerState, ServerStatus

            mock_status.return_value = ServerStatus(
                port=DEFAULT_PORT,
                state=ServerState.PORT_CONFLICT,
                pid=99999,
                project_root=None,
            )

            result = runner.invoke(app, ["serve", str(project_with_both)])

            assert result.exit_code == 1
            assert "already in use" in result.output


class TestCLIErrorCases:
    """Tests for CLI error handling"""

    def test_nonexistent_path_error(self) -> None:
        """should show error for non-existent path"""
        result = runner.invoke(app, ["serve", "/nonexistent/path/that/does/not/exist"])

        assert result.exit_code == 2
        assert "does not exist" in result.output

    def test_file_instead_of_directory_error(self, temp_dir: Path) -> None:
        """should show error when path is a file, not directory"""
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test content")

        result = runner.invoke(app, ["serve", str(test_file)])

        assert result.exit_code == 2
        assert "not a directory" in result.output

    def test_no_project_found_error(self, temp_dir: Path) -> None:
        """Should show error when no project markers are found."""
        result = runner.invoke(app, ["serve", str(temp_dir)])

        assert result.exit_code == 1
        assert "No spec-driven development project" in result.output


class TestCLIHelp:
    """Tests for CLI help output."""

    def test_help_flag(self) -> None:
        """Should display help with --help flag."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        # verify help shows tool description
        assert "spec" in result.output.lower()


class TestCLIStop:
    """Tests for the stop command."""

    def test_stop_running_server(self) -> None:
        """T036: specbook stop stops running server."""
        with (
            patch("specbook.cli.get_server_status") as mock_status,
            patch("specbook.cli.stop_server") as mock_stop,
        ):
            from specbook.core.models import ServerState, ServerStatus

            mock_status.return_value = ServerStatus(
                port=DEFAULT_PORT,
                state=ServerState.RUNNING,
                pid=12345,
                project_root=Path("/path/to/project"),
            )
            mock_stop.return_value = True

            result = runner.invoke(app, ["stop"])

            assert result.exit_code == 0
            assert "stopped" in result.output.lower()
            mock_stop.assert_called_once_with(DEFAULT_PORT)

    def test_stop_no_server_running(self) -> None:
        """Stop shows info when no server running."""
        with patch("specbook.cli.get_server_status") as mock_status:
            from specbook.core.models import ServerState, ServerStatus

            mock_status.return_value = ServerStatus(
                port=DEFAULT_PORT,
                state=ServerState.STOPPED,
                pid=None,
                project_root=None,
            )

            result = runner.invoke(app, ["stop"])

            assert result.exit_code == 0
            assert "No server running" in result.output

    def test_stop_with_custom_port(self) -> None:
        """Stop uses custom port with -p flag."""
        with (
            patch("specbook.cli.get_server_status") as mock_status,
            patch("specbook.cli.stop_server") as mock_stop,
        ):
            from specbook.core.models import ServerState, ServerStatus

            mock_status.return_value = ServerStatus(
                port=8080,
                state=ServerState.RUNNING,
                pid=12345,
                project_root=Path("/path/to/project"),
            )
            mock_stop.return_value = True

            result = runner.invoke(app, ["stop", "-p", "8080"])

            assert result.exit_code == 0
            mock_stop.assert_called_once_with(8080)


class TestCLIStatus:
    """tests the status command"""

    def test_status_shows_running_server(self) -> None:
        """specbook status shows correct state for running server"""
        with patch("specbook.cli.get_server_status") as mock_status:
            from specbook.core.models import ServerState, ServerStatus

            mock_status.return_value = ServerStatus(
                port=DEFAULT_PORT,
                state=ServerState.RUNNING,
                pid=12345,
                project_root=Path("/path/to/project"),
            )

            result = runner.invoke(app, ["status"])

            assert result.exit_code == 0
            assert "running" in result.output.lower()
            assert "12345" in result.output
            assert "7732" in result.output

    def test_status_shows_stopped(self) -> None:
        """status shows info even when no server running"""
        with patch("specbook.cli.get_server_status") as mock_status:
            from specbook.core.models import ServerState, ServerStatus

            mock_status.return_value = ServerStatus(
                port=DEFAULT_PORT,
                state=ServerState.STOPPED,
                pid=None,
                project_root=None,
            )

            result = runner.invoke(app, ["status"])

            assert result.exit_code == 0
            assert "No server running" in result.output

    def test_status_with_custom_port(self) -> None:
        """status uses custom port with -p flag"""
        with patch("specbook.cli.get_server_status") as mock_status:
            from specbook.core.models import ServerState, ServerStatus

            mock_status.return_value = ServerStatus(
                port=8080,
                state=ServerState.STOPPED,
                pid=None,
                project_root=None,
            )

            result = runner.invoke(app, ["status", "-p", "8080"])

            assert result.exit_code == 0
            assert "8080" in result.output


class TestCLIRestart:
    """tests the restart command"""

    def test_restart_server(self, project_with_both: Path) -> None:
        """Restart stops and starts the server."""
        with (
            patch("specbook.cli.get_server_status") as mock_status,
            patch("specbook.cli.stop_server") as mock_stop,
            patch("specbook.cli.start_server"),
            patch("specbook.cli.open_browser"),
        ):
            from specbook.core.models import ServerState, ServerStatus

            mock_status.return_value = ServerStatus(
                port=DEFAULT_PORT,
                state=ServerState.RUNNING,
                pid=12345,
                project_root=project_with_both,
            )

            result = runner.invoke(app, ["restart", str(project_with_both)])

            assert result.exit_code == 0
            assert "restarted" in result.output.lower()
            mock_stop.assert_called_once_with(DEFAULT_PORT)
