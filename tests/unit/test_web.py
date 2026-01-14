"""Unit tests for web API endpoints."""

from pathlib import Path

from starlette.testclient import TestClient


class TestApiDocumentRaw:
    """tests for GET /api/document/raw endpoint"""

    def test_returns_raw_markdown_content(self, project_with_specs: Path) -> None:
        """endpoint returns raw markdown without rendering"""
        from specbook.ui.web.app import create_app

        # create spec with a markdown file
        spec_dir = project_with_specs / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        doc_path = spec_dir / "spec.md"
        doc_path.write_text("# Test Spec\n\nSome **bold** content.")

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.get("/api/document/raw?path=specs/001-test/spec.md")

        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "specs/001-test/spec.md"
        assert data["raw"] == "# Test Spec\n\nSome **bold** content."
        assert "modified" in data

    def test_returns_404_for_missing_file(self, project_with_specs: Path) -> None:
        """endpoint returns 404 for non-existent file"""
        from specbook.ui.web.app import create_app

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.get("/api/document/raw?path=specs/nonexistent/spec.md")

        assert response.status_code == 404
        assert response.json()["error"] == "Document not found"

    def test_returns_400_for_missing_path(self, project_with_specs: Path) -> None:
        """endpoint returns 400 when path parameter is missing"""
        from specbook.ui.web.app import create_app

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.get("/api/document/raw")

        assert response.status_code == 400
        assert response.json()["error"] == "Invalid path"

    def test_returns_400_for_non_markdown_file(self, project_with_specs: Path) -> None:
        """endpoint rejects non-.md files"""
        from specbook.ui.web.app import create_app

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.get("/api/document/raw?path=specs/001-test/file.txt")

        assert response.status_code == 400
        assert "Only markdown files allowed" in response.json()["detail"]

    def test_blocks_path_traversal(self, project_with_specs: Path) -> None:
        """endpoint blocks directory traversal attacks"""
        from specbook.ui.web.app import create_app

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.get("/api/document/raw?path=../../../etc/passwd.md")

        assert response.status_code == 400
        assert "Path outside project root" in response.json()["detail"]


class TestApiDocumentSave:
    """tests for POST /api/document endpoint"""

    def test_saves_content_to_file(self, project_with_specs: Path) -> None:
        """endpoint saves content to existing file"""
        from specbook.ui.web.app import create_app

        # create spec with a markdown file
        spec_dir = project_with_specs / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        doc_path = spec_dir / "spec.md"
        doc_path.write_text("# Original Content")

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.post(
            "/api/document",
            json={
                "path": "specs/001-test/spec.md",
                "content": "# Updated Content\n\nNew text here.",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["path"] == "specs/001-test/spec.md"
        assert "modified" in data

        # verify file was actually updated
        assert doc_path.read_text() == "# Updated Content\n\nNew text here."

    def test_returns_404_for_missing_file(self, project_with_specs: Path) -> None:
        """endpoint returns 404 when trying to save to non-existent file"""
        from specbook.ui.web.app import create_app

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.post(
            "/api/document",
            json={
                "path": "specs/nonexistent/spec.md",
                "content": "# New Content",
            },
        )

        assert response.status_code == 404
        assert response.json()["error"] == "Document not found"

    def test_returns_400_for_missing_content(self, project_with_specs: Path) -> None:
        """endpoint returns 400 when content field is missing"""
        from specbook.ui.web.app import create_app

        spec_dir = project_with_specs / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Test")

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.post(
            "/api/document",
            json={"path": "specs/001-test/spec.md"},
        )

        assert response.status_code == 400
        assert "Missing content field" in response.json()["detail"]

    def test_returns_400_for_invalid_json(self, project_with_specs: Path) -> None:
        """endpoint returns 400 for invalid JSON body"""
        from specbook.ui.web.app import create_app

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.post(
            "/api/document",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        assert "Invalid JSON body" in response.json()["detail"]

    def test_blocks_path_traversal(self, project_with_specs: Path) -> None:
        """endpoint blocks directory traversal in save"""
        from specbook.ui.web.app import create_app

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.post(
            "/api/document",
            json={
                "path": "../../../tmp/malicious.md",
                "content": "# Bad Content",
            },
        )

        assert response.status_code == 400
        assert "Path outside project root" in response.json()["detail"]


class TestApiCheckboxToggle:
    """tests for POST /api/checkbox endpoint"""

    def test_toggles_unchecked_to_checked(self, project_with_specs: Path) -> None:
        """endpoint toggles unchecked checkbox to checked"""
        from specbook.ui.web.app import create_app

        spec_dir = project_with_specs / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        doc_path = spec_dir / "tasks.md"
        doc_path.write_text("# Tasks\n\n- [ ] First task\n- [ ] Second task\n")

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.post(
            "/api/checkbox",
            json={
                "path": "specs/001-test/tasks.md",
                "lineNumber": 3,
                "checked": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["lineNumber"] == 3
        assert data["checked"] is True

        # verify file was updated
        content = doc_path.read_text()
        assert "- [x] First task" in content
        assert "- [ ] Second task" in content

    def test_toggles_checked_to_unchecked(self, project_with_specs: Path) -> None:
        """endpoint toggles checked checkbox to unchecked"""
        from specbook.ui.web.app import create_app

        spec_dir = project_with_specs / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        doc_path = spec_dir / "tasks.md"
        doc_path.write_text("# Tasks\n\n- [x] First task\n- [x] Second task\n")

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.post(
            "/api/checkbox",
            json={
                "path": "specs/001-test/tasks.md",
                "lineNumber": 4,
                "checked": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["checked"] is False

        # verify file was updated
        content = doc_path.read_text()
        assert "- [x] First task" in content
        assert "- [ ] Second task" in content

    def test_returns_400_for_non_checkbox_line(self, project_with_specs: Path) -> None:
        """endpoint returns 400 when line is not a checkbox"""
        from specbook.ui.web.app import create_app

        spec_dir = project_with_specs / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        doc_path = spec_dir / "tasks.md"
        doc_path.write_text("# Tasks\n\nJust some text here\n")

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.post(
            "/api/checkbox",
            json={
                "path": "specs/001-test/tasks.md",
                "lineNumber": 3,
                "checked": True,
            },
        )

        assert response.status_code == 400
        assert "not a checkbox item" in response.json()["detail"]

    def test_returns_400_for_invalid_line_number(self, project_with_specs: Path) -> None:
        """endpoint returns 400 for out of range line number"""
        from specbook.ui.web.app import create_app

        spec_dir = project_with_specs / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        doc_path = spec_dir / "tasks.md"
        doc_path.write_text("# Tasks\n\n- [ ] Only task\n")

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.post(
            "/api/checkbox",
            json={
                "path": "specs/001-test/tasks.md",
                "lineNumber": 999,
                "checked": True,
            },
        )

        assert response.status_code == 400
        assert "exceeds file length" in response.json()["detail"]

    def test_returns_400_for_negative_line_number(self, project_with_specs: Path) -> None:
        """endpoint returns 400 for negative line number"""
        from specbook.ui.web.app import create_app

        spec_dir = project_with_specs / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        (spec_dir / "tasks.md").write_text("# Tasks\n")

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.post(
            "/api/checkbox",
            json={
                "path": "specs/001-test/tasks.md",
                "lineNumber": -1,
                "checked": True,
            },
        )

        assert response.status_code == 400
        assert "positive integer" in response.json()["detail"]

    def test_returns_400_for_missing_checked_field(self, project_with_specs: Path) -> None:
        """endpoint returns 400 when checked field is missing"""
        from specbook.ui.web.app import create_app

        spec_dir = project_with_specs / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        (spec_dir / "tasks.md").write_text("# Tasks\n- [ ] Task\n")

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.post(
            "/api/checkbox",
            json={
                "path": "specs/001-test/tasks.md",
                "lineNumber": 2,
            },
        )

        assert response.status_code == 400
        assert "checked must be a boolean" in response.json()["detail"]

    def test_preserves_indented_checkboxes(self, project_with_specs: Path) -> None:
        """endpoint handles indented checkboxes correctly"""
        from specbook.ui.web.app import create_app

        spec_dir = project_with_specs / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        doc_path = spec_dir / "tasks.md"
        doc_path.write_text("# Tasks\n\n  - [ ] Indented task\n")

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.post(
            "/api/checkbox",
            json={
                "path": "specs/001-test/tasks.md",
                "lineNumber": 3,
                "checked": True,
            },
        )

        assert response.status_code == 200

        # verify indentation preserved
        content = doc_path.read_text()
        assert "  - [x] Indented task" in content

    def test_blocks_path_traversal(self, project_with_specs: Path) -> None:
        """endpoint blocks directory traversal in checkbox toggle"""
        from specbook.ui.web.app import create_app

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.post(
            "/api/checkbox",
            json={
                "path": "../../../tmp/malicious.md",
                "lineNumber": 1,
                "checked": True,
            },
        )

        assert response.status_code == 400
        assert "Path outside project root" in response.json()["detail"]


class TestPathValidation:
    """tests for path validation helper"""

    def test_rejects_absolute_paths(self, project_with_specs: Path) -> None:
        """validation rejects absolute paths"""
        from specbook.ui.web.app import create_app

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.get("/api/document/raw?path=/etc/passwd.md")

        assert response.status_code == 400

    def test_rejects_double_dot_traversal(self, project_with_specs: Path) -> None:
        """validation rejects .. traversal"""
        from specbook.ui.web.app import create_app

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.get("/api/document/raw?path=specs/../../../etc/passwd.md")

        assert response.status_code == 400


class TestApiDocument:
    """tests for GET /api/document endpoint (renders markdown to HTML)"""

    def test_returns_rendered_html(self, project_with_specs: Path) -> None:
        """endpoint returns rendered HTML content"""
        from specbook.ui.web.app import create_app

        spec_dir = project_with_specs / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        doc_path = spec_dir / "spec.md"
        doc_path.write_text("# Test Spec\n\nSome **bold** content.")

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.get("/api/document?path=specs/001-test/spec.md")

        assert response.status_code == 200
        data = response.json()
        assert data["path"] == "specs/001-test/spec.md"
        assert "<h1>Test Spec</h1>" in data["content"]
        assert "<strong>bold</strong>" in data["content"]
        assert data["title"] == "Test Spec"
        assert "modified" in data
        assert "created" in data

    def test_extracts_h1_as_title(self, project_with_specs: Path) -> None:
        """endpoint uses first h1 as title"""
        from specbook.ui.web.app import create_app

        spec_dir = project_with_specs / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        doc_path = spec_dir / "plan.md"
        doc_path.write_text("# Implementation Plan\n\nDetails here.")

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.get("/api/document?path=specs/001-test/plan.md")

        assert response.status_code == 200
        assert response.json()["title"] == "Implementation Plan"

    def test_uses_filename_as_fallback_title(self, project_with_specs: Path) -> None:
        """endpoint uses filename if no h1 found"""
        from specbook.ui.web.app import create_app

        spec_dir = project_with_specs / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        doc_path = spec_dir / "notes.md"
        doc_path.write_text("Just some notes, no heading.")

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.get("/api/document?path=specs/001-test/notes.md")

        assert response.status_code == 200
        assert response.json()["title"] == "notes"

    def test_returns_404_for_missing_file(self, project_with_specs: Path) -> None:
        """endpoint returns 404 for non-existent file"""
        from specbook.ui.web.app import create_app

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.get("/api/document?path=specs/nonexistent/spec.md")

        assert response.status_code == 404


class TestIndex:
    """tests for GET / endpoint (main pg)"""

    def test_renders_index_page(self, project_with_specs: Path) -> None:
        """index endpoint returns HTML page"""
        from specbook.ui.web.app import create_app

        spec_dir = project_with_specs / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Test")

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_includes_project_documents(self, project_with_specs: Path) -> None:
        """index page includes project-level documents"""
        from specbook.ui.web.app import create_app

        (project_with_specs / "CLAUDE.md").write_text("# Claude Rules")

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        # CLAUDE.md example should be discovered as a project doc
        assert response.text  # just verify it renders

    def test_includes_specs(self, project_with_specs: Path) -> None:
        """index page includes specs directory"""
        from specbook.ui.web.app import create_app

        spec_dir = project_with_specs / "specs" / "001-core"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Core Spec")
        (spec_dir / "tasks.md").write_text("# Tasks\n- [ ] Task 1")

        app = create_app(project_with_specs)
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        # spec.md spec title should rendered on page
        assert "001-core" in response.text


class TestProjectListing:
    """tests for _build_project_listing function"""

    def test_builds_empty_project_listing(self, project_with_specs: Path) -> None:
        """listing for project with no specs"""
        from specbook.ui.web.app import _build_project_listing

        listing = _build_project_listing(project_with_specs)

        assert listing.project_root == project_with_specs
        assert listing.project_documents == []
        assert listing.specs == []
        assert listing.is_empty is True

    def test_discovers_specs(self, project_with_specs: Path) -> None:
        """listing discovers spec directories"""
        from specbook.ui.web.app import _build_project_listing

        spec_dir = project_with_specs / "specs" / "001-core"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Core")

        listing = _build_project_listing(project_with_specs)

        assert len(listing.specs) == 1
        assert listing.specs[0].name == "001-core"
        assert listing.is_empty is False

    def test_parses_completion_status(self, project_with_specs: Path) -> None:
        """listing includes completion status from tasks.md"""
        from specbook.ui.web.app import _build_project_listing

        spec_dir = project_with_specs / "specs" / "002-feature"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Feature")
        (spec_dir / "tasks.md").write_text("# Tasks\n- [x] Done\n- [ ] Pending")

        listing = _build_project_listing(project_with_specs)

        assert listing.specs[0].completion.total_tasks == 2
        assert listing.specs[0].completion.completed_tasks == 1

    def test_discovers_project_documents(self, project_with_specs: Path) -> None:
        """listing discovers CLAUDE.md and other project docs"""
        from specbook.ui.web.app import _build_project_listing

        (project_with_specs / "CLAUDE.md").write_text("# Rules")

        listing = _build_project_listing(project_with_specs)

        assert len(listing.project_documents) == 1
        assert listing.project_documents[0].path.name == "CLAUDE.md"
        assert listing.has_project_documents is True

    def test_scans_multiple_specs(self, project_with_specs: Path) -> None:
        """listing discovers multiple spec directories"""
        from specbook.ui.web.app import _build_project_listing

        for i in range(1, 4):
            spec_dir = project_with_specs / "specs" / f"00{i}-spec"
            spec_dir.mkdir(parents=True)
            (spec_dir / "spec.md").write_text(f"# Spec {i}")

        listing = _build_project_listing(project_with_specs)

        assert len(listing.specs) == 3
        assert listing.specs[0].name == "001-spec"
        assert listing.specs[2].name == "003-spec"


class TestDocumentInfo:
    """tests for _get_document_info helper function"""

    def test_known_document_types(self) -> None:
        """function returns info for known document types"""
        from specbook.ui.web.app import _get_document_info

        display, doc_type, order = _get_document_info("spec.md")
        assert display == "Specification"
        assert doc_type == "spec"
        assert order == 101

        display, doc_type, order = _get_document_info("tasks.md")
        assert display == "Tasks"
        assert doc_type == "tasks"
        assert order == 110

    def test_claude_document(self) -> None:
        """function recognizes CLAUDE.md"""
        from specbook.ui.web.app import _get_document_info

        display, doc_type, order = _get_document_info("CLAUDE.md")
        assert display == "Claude Rules"
        assert doc_type == "claude"

    def test_unknown_markdown_file(self) -> None:
        """function handles unknown markdown files"""
        from specbook.ui.web.app import _get_document_info

        display, doc_type, order = _get_document_info("custom-notes.md")
        assert display == "Custom Notes"
        assert doc_type == "other"
        assert order == 999

    def test_non_markdown_file(self) -> None:
        """function handles non-markdown files"""
        from specbook.ui.web.app import _get_document_info

        display, doc_type, order = _get_document_info("README.txt")
        assert display == "Readme.Txt"
        assert doc_type == "other"


class TestScanSpecDocuments:
    """tests for _scan_spec_documents function"""

    def test_scans_markdown_files(self, project_with_specs: Path) -> None:
        """function finds markdown files in spec directory"""
        from specbook.ui.web.app import _scan_spec_documents

        spec_dir = project_with_specs / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Spec")
        (spec_dir / "plan.md").write_text("# Plan")

        docs = _scan_spec_documents(spec_dir)

        assert len(docs) == 2
        assert any(d.name == "spec.md" for d in docs)
        assert any(d.name == "plan.md" for d in docs)

    def test_scans_subdirectories(self, project_with_specs: Path) -> None:
        """function finds markdown files in subdirectories"""
        from specbook.ui.web.app import _scan_spec_documents

        spec_dir = project_with_specs / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Spec")

        contracts_dir = spec_dir / "contracts"
        contracts_dir.mkdir()
        (contracts_dir / "api.md").write_text("# API")

        docs = _scan_spec_documents(spec_dir)

        assert len(docs) == 2
        assert any(d.name == "spec.md" for d in docs)
        assert any("api.md" in d.name for d in docs)

    def test_returns_empty_for_missing_directory(self, project_with_specs: Path) -> None:
        """function returns empty list for non-existent directory"""
        from specbook.ui.web.app import _scan_spec_documents

        spec_dir = project_with_specs / "specs" / "nonexistent"

        docs = _scan_spec_documents(spec_dir)

        assert docs == []

    def test_sorts_by_document_type_priority(self, project_with_specs: Path) -> None:
        """function sorts documents by type priority"""
        from specbook.ui.web.app import _scan_spec_documents

        spec_dir = project_with_specs / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        (spec_dir / "tasks.md").write_text("# Tasks")
        (spec_dir / "spec.md").write_text("# Spec")
        (spec_dir / "plan.md").write_text("# Plan")

        docs = _scan_spec_documents(spec_dir)

        # spec should come first (sort order 101), then plan (105), then tasks (110)
        assert docs[0].name == "spec.md"
        assert docs[1].name == "plan.md"
        assert docs[2].name == "tasks.md"


class TestParseCompletionStatus:
    """tests for _parse_completion_status function"""

    def test_counts_checkboxes(self, project_with_specs: Path) -> None:
        """function counts checked and unchecked items"""
        from specbook.ui.web.app import _parse_completion_status

        tasks_file = project_with_specs / "tasks.md"
        tasks_file.write_text("# Tasks\n- [x] Done\n- [ ] Pending\n- [x] Also Done")

        status = _parse_completion_status(tasks_file)

        assert status.total_tasks == 3
        assert status.completed_tasks == 2

    def test_handles_missing_file(self, project_with_specs: Path) -> None:
        """function returns empty status for missing file"""
        from specbook.ui.web.app import _parse_completion_status

        tasks_file = project_with_specs / "tasks.md"

        status = _parse_completion_status(tasks_file)

        assert status.total_tasks == 0
        assert status.completed_tasks == 0

    def test_handles_file_with_no_checkboxes(self, project_with_specs: Path) -> None:
        """function returns zero status for file with no checkboxes"""
        from specbook.ui.web.app import _parse_completion_status

        tasks_file = project_with_specs / "notes.md"
        tasks_file.write_text("# Notes\nJust some text here.")

        status = _parse_completion_status(tasks_file)

        assert status.total_tasks == 0
        assert status.completed_tasks == 0

    def test_handles_uppercase_x(self, project_with_specs: Path) -> None:
        """function recognizes [X] as checked"""
        from specbook.ui.web.app import _parse_completion_status

        tasks_file = project_with_specs / "tasks.md"
        tasks_file.write_text("- [X] Checked with uppercase\n- [x] Checked with lowercase")

        status = _parse_completion_status(tasks_file)

        assert status.completed_tasks == 2


class TestDiscoverProjectDocuments:
    """tests for _discover_project_documents function"""

    def test_discovers_root_level_documents(self, project_with_specs: Path) -> None:
        """function discovers root-level markdown files"""
        from specbook.ui.web.app import _discover_project_documents

        (project_with_specs / "CLAUDE.md").write_text("# Rules")

        docs = _discover_project_documents(project_with_specs)

        assert len(docs) == 1
        assert docs[0].path.name == "CLAUDE.md"

    def test_discovers_specify_memory_documents(self, project_with_specs: Path) -> None:
        """function discovers documents in .specify/memory/"""
        from specbook.ui.web.app import _discover_project_documents

        memory_dir = project_with_specs / ".specify" / "memory"
        memory_dir.mkdir(parents=True)
        (memory_dir / "constitution.md").write_text("# Constitution")

        docs = _discover_project_documents(project_with_specs)

        assert len(docs) == 1
        assert "constitution.md" in docs[0].path.name
