"""unit tests for server management utilities"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specbook.core.models import ServerState, SpecDirectory, SpecListing
from specbook.core.server import get_server_status


class TestSpecListing:
    """tests for SpecListing.from_project()"""

    def test_from_project_happy_path(self, temp_dir: Path) -> None:
        """SpecListing.from_project() returns specs sorted by name"""
        # create specs directory with subdirectories
        specs_dir = temp_dir / "specs"
        specs_dir.mkdir()
        (specs_dir / "002-feature-b").mkdir()
        (specs_dir / "001-feature-a").mkdir()
        (specs_dir / "003-feature-c").mkdir()

        listing = SpecListing.from_project(temp_dir)

        assert listing.project_root == temp_dir
        assert len(listing.specs) == 3
        assert listing.specs[0].name == "001-feature-a"
        assert listing.specs[1].name == "002-feature-b"
        assert listing.specs[2].name == "003-feature-c"
        assert not listing.is_empty

    def test_from_project_empty_specs(self, temp_dir: Path) -> None:
        """SpecListing.from_project() returns empty list when no subdirs"""
        specs_dir = temp_dir / "specs"
        specs_dir.mkdir()

        listing = SpecListing.from_project(temp_dir)

        assert listing.project_root == temp_dir
        assert len(listing.specs) == 0
        assert listing.is_empty

    def test_from_project_no_specs_dir(self, temp_dir: Path) -> None:
        """SpecListing.from_project() returns empty list when no specs/ dir"""
        listing = SpecListing.from_project(temp_dir)

        assert listing.project_root == temp_dir
        assert len(listing.specs) == 0
        assert listing.is_empty

    def test_from_project_excludes_hidden(self, temp_dir: Path) -> None:
        """SpecListing excludes hidden directories (starting with .)"""
        specs_dir = temp_dir / "specs"
        specs_dir.mkdir()
        (specs_dir / "001-visible").mkdir()
        (specs_dir / ".hidden").mkdir()
        (specs_dir / "002-also-visible").mkdir()

        listing = SpecListing.from_project(temp_dir)

        assert len(listing.specs) == 2
        spec_names = [s.name for s in listing.specs]
        assert "001-visible" in spec_names
        assert "002-also-visible" in spec_names
        assert ".hidden" not in spec_names

    def test_from_project_excludes_files(self, temp_dir: Path) -> None:
        """SpecListing excludes files, only lists directories"""
        specs_dir = temp_dir / "specs"
        specs_dir.mkdir()
        (specs_dir / "001-spec-dir").mkdir()
        (specs_dir / "README.md").write_text("readme")

        listing = SpecListing.from_project(temp_dir)

        assert len(listing.specs) == 1
        assert listing.specs[0].name == "001-spec-dir"


class TestSpecDirectory:
    """tests for SpecDirectory model"""

    def test_from_path(self, temp_dir: Path) -> None:
        """SpecDirectory.from_path() creates instance from path"""
        spec_path = temp_dir / "001-my-feature"
        spec_path.mkdir()

        spec_dir = SpecDirectory.from_path(spec_path)

        assert spec_dir.name == "001-my-feature"
        assert spec_dir.path == spec_path


class TestGetServerStatus:
    """tests for get_server_status() (RUNNING, STOPPED, etc) function"""

    def test_returns_stopped_when_no_process(self) -> None:
        """get_server_status() returns STOPPED when no process on port"""
        with patch("specbook.core.server.find_process_on_port") as mock_find:
            mock_find.return_value = None

            status = get_server_status(7732)

            assert status.state == ServerState.STOPPED
            assert status.port == 7732
            assert status.pid is None
            assert status.project_root is None

    def test_returns_running_for_specbook_process(self) -> None:
        """get_server_status() returns RUNNING for specbook process"""
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.cmdline.return_value = [
            "/usr/bin/python",
            "-m",
            "specbook.ui.web.app",
            "7732",
            "/path/to/project",
        ]

        with (
            patch("specbook.core.server.find_process_on_port") as mock_find,
            patch("specbook.core.server.is_specbook_process") as mock_is_specbook,
            patch(
                "specbook.core.server.get_project_root_from_process"
            ) as mock_get_root,
        ):
            mock_find.return_value = mock_proc
            mock_is_specbook.return_value = True
            mock_get_root.return_value = Path("/path/to/project")

            status = get_server_status(7732)

            assert status.state == ServerState.RUNNING
            assert status.port == 7732
            assert status.pid == 12345
            assert status.project_root == Path("/path/to/project")

    def test_returns_port_conflict_for_other_process(self) -> None:
        """get_server_status() returns PORT_CONFLICT for non-specbook"""
        mock_proc = MagicMock()
        mock_proc.pid = 99999

        with (
            patch("specbook.core.server.find_process_on_port") as mock_find,
            patch("specbook.core.server.is_specbook_process") as mock_is_specbook,
        ):
            mock_find.return_value = mock_proc
            mock_is_specbook.return_value = False

            status = get_server_status(7732)

            assert status.state == ServerState.PORT_CONFLICT
            assert status.port == 7732
            assert status.pid == 99999
            assert status.project_root is None
