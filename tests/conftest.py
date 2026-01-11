"""Pytest fixtures for specbook tests."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """create temp directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def project_with_specify(temp_dir: Path) -> Path:
    """create project with just a .specify/ directory"""
    (temp_dir / ".specify").mkdir()
    return temp_dir


@pytest.fixture
def project_with_specs(temp_dir: Path) -> Path:
    """create project with just a specs/ directory"""
    (temp_dir / "specs").mkdir()
    return temp_dir


@pytest.fixture
def project_with_both(temp_dir: Path) -> Path:
    """create typical spec-kit project with both .specify/ and specs/ directories"""
    (temp_dir / ".specify").mkdir()
    (temp_dir / "specs").mkdir()
    return temp_dir


@pytest.fixture
def nested_subdir(project_with_both: Path) -> Path:
    """create a nested subdirectory structure within a project"""
    nested = project_with_both / "src" / "components" / "deep"
    nested.mkdir(parents=True)
    return nested
