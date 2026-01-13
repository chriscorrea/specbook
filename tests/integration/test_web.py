"""Integration tests for the web server."""

from pathlib import Path

import pytest
from starlette.testclient import TestClient


class TestWebApp:
    """integration tests for the Starlette web app"""

    def test_index_returns_html_with_header(self, project_with_specs: Path) -> None:
        """web app returns HTML with Specbook header"""
        # avoid import errors if app not yet created
        from specbook.ui.web.app import create_app

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Specbook" in response.text

    def test_index_lists_spec_directories(self, project_with_specs: Path) -> None:
        """web app lists spec directories from project"""
        from specbook.ui.web.app import create_app

        # create some spec directories
        (project_with_specs / "specs" / "001-feature-a").mkdir()
        (project_with_specs / "specs" / "002-feature-b").mkdir()

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        assert "001-feature-a" in response.text
        assert "002-feature-b" in response.text

    def test_index_shows_empty_state(self, project_with_specs: Path) -> None:
        """Web app shows empty state when no specs exist."""
        from specbook.ui.web.app import create_app

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        assert "No specifications found" in response.text
