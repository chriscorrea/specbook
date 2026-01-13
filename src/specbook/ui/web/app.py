"""Starlette web application for specbook spec viewer"""

import re
import sys
from pathlib import Path

from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from specbook.core.models import (
    CompletionStatus,
    ProjectDocument,
    ProjectListing,
    SpecDirectoryExpanded,
    SpecDocument,
)

# markdown renderer with tables, strikethrough, and task lists
_md = MarkdownIt("commonmark").enable("table").enable("strikethrough").use(tasklists_plugin)


def render_markdown(content: str) -> str:
    """render markdown content to HTML"""
    return _md.render(content)


# templates and static dir relative to this file
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# document type display name mapping
_DOCUMENT_TYPE_MAP: dict[str, tuple[str, str, int]] = {
    # filename: (display_name, doc_type, sort_order)
    # typically, project-level
    "constitution.md": ("Constitution", "constitution", 1),
    "product.md": ("Product Goals", "product", 5),
    "architecture.md": ("System Architecture", "architecture", 10),
    "tech.md": ("Tech Overview", "tech", 15),
    "glossary.md": ("Glossary", "glossary", 90),
    "api-standards.md": ("API Standards", "api-standards", 50),
    "testing-standards.md": ("Testing Approach", "testing-standards", 51),
    "code-conventions.md": ("Code Style", "code-conventions", 52),
    "security-policies.md": ("Security Policies", "security-policies", 53),
    "deployment-workflow.md": ("Deployment Process", "deployment-workflow", 54),
    # implementation-specific
    "AGENTS.md": ("Agent Rules", "agents", 91),
    "CLAUDE.md": ("Claude Rules", "claude", 92),
    # typically, spec-level
    "spec.md": ("Specification", "spec", 101),
    "plan.md": ("Plan", "plan", 105),
    "tasks.md": ("Tasks", "tasks", 110),
    "research.md": ("Research", "research", 115),
    "quickstart.md": ("Quickstart", "quickstart", 150),
    "data-model.md": ("Data Model", "data-model", 155),
}

# project document locations (directory, category)
_PROJECT_DOC_LOCATIONS: list[tuple[str, str]] = [
    # .specify/memory/ for spec-kit projects
    (".specify/memory/constitution.md", "guide"),
    (".specify/memory/", "memory"),
    # .kiro/steering/ for kiro projects
    (".kiro/steering/", "steering"),
    # root-level documents
    ("CLAUDE.md", "guide"),
    ("AGENT.md", "guide"),
]


def _get_document_info(filename: str) -> tuple[str, str, int]:
    """get display name, doc type, and sort order for a filename"""
    if filename in _DOCUMENT_TYPE_MAP:
        return _DOCUMENT_TYPE_MAP[filename]
    # other markdown files: use filename without extension
    display_name = filename[:-3] if filename.endswith(".md") else filename
    return (display_name.replace("-", " ").replace("_", " ").title(), "other", 999)


def _parse_completion_status(tasks_path: Path) -> CompletionStatus:
    """parse tasks.md to determine completion status based on checkboxes"""
    if not tasks_path.is_file():
        return CompletionStatus(total_tasks=0, completed_tasks=0)

    try:
        content = tasks_path.read_text(encoding="utf-8")
        # count checked and unchecked items
        checked = len(re.findall(r"- \[[xX]\]", content))
        unchecked = len(re.findall(r"- \[ \]", content))
        return CompletionStatus(
            total_tasks=checked + unchecked,
            completed_tasks=checked,
        )
    except OSError:
        return CompletionStatus(total_tasks=0, completed_tasks=0)


def _scan_spec_documents(spec_dir: Path) -> list[SpecDocument]:
    """scan a spec directory for all markdown documents"""
    if not spec_dir.is_dir():
        return []

    docs = []
    for f in spec_dir.iterdir():
        if f.is_file() and f.suffix == ".md":
            display_name, doc_type, _ = _get_document_info(f.name)
            docs.append(
                SpecDocument(
                    name=f.name,
                    path=f,
                    display_name=display_name,
                    doc_type=doc_type,
                )
            )

    # also scan subdirectories for contracts etc.
    for subdir in spec_dir.iterdir():
        if subdir.is_dir() and not subdir.name.startswith("."):
            for f in subdir.iterdir():
                if f.is_file() and f.suffix == ".md":
                    # use subdir/filename format for display
                    display_name = f"{subdir.name}/{f.stem}".title()
                    docs.append(
                        SpecDocument(
                            name=f"{subdir.name}/{f.name}",
                            path=f,
                            display_name=display_name,
                            doc_type="other",
                        )
                    )

    # sort by known type order, then alphabetically
    def sort_key(doc: SpecDocument) -> tuple[int, str]:
        _, _, order = _get_document_info(doc.name)
        return (order, doc.name)

    return sorted(docs, key=sort_key)


def _discover_project_documents(project_root: Path) -> list[ProjectDocument]:
    """discover project-level documents from configured locations"""
    docs: list[ProjectDocument] = []
    seen_files = set()

    for location, category in _PROJECT_DOC_LOCATIONS:
        location_path = project_root / location

        # handle single file locations (e.g., "CLAUDE.md")
        if location_path.is_file():
            if location_path.name not in seen_files:
                display_name, _, _ = _get_document_info(location_path.name)
                docs.append(
                    ProjectDocument(
                        name=display_name,
                        path=location_path,
                        category=category,
                    )
                )
                seen_files.add(location_path.name)

        # handle directory locations (e.g., ".specify/memory/")
        elif location_path.is_dir():
            for f in sorted(location_path.iterdir()):
                if f.is_file() and f.suffix == ".md" and f.name not in seen_files:
                    display_name, _, _ = _get_document_info(f.name)
                    docs.append(
                        ProjectDocument(
                            name=display_name,
                            path=f,
                            category=category,
                        )
                    )
                    seen_files.add(f.name)

    # sort by sort_order from document type map, then alphabetically
    def sort_key(doc: ProjectDocument) -> tuple[int, str]:
        _, _, order = _get_document_info(doc.path.name)
        return (order, doc.name)

    return sorted(docs, key=sort_key)


def _build_project_listing(project_root: Path) -> ProjectListing:
    """build complete project listing for the web UI"""
    # discover project-level documents
    project_documents = _discover_project_documents(project_root)

    # scan specs directory
    specs_dir = project_root / "specs"
    specs: list[SpecDirectoryExpanded] = []

    if specs_dir.is_dir():
        for spec_path in sorted(specs_dir.iterdir()):
            if spec_path.is_dir() and not spec_path.name.startswith("."):
                documents = _scan_spec_documents(spec_path)
                # parse completion status from tasks.md
                tasks_path = spec_path / "tasks.md"
                completion = _parse_completion_status(tasks_path)
                specs.append(
                    SpecDirectoryExpanded(
                        name=spec_path.name,
                        path=spec_path,
                        documents=documents,
                        completion=completion,
                    )
                )

    return ProjectListing(
        project_root=project_root,
        project_documents=project_documents,
        specs=specs,
    )


# global project root (set by create_app or main)
_project_root: Path | None = None


async def index(request: Request) -> HTMLResponse:
    """render the spec listing page"""
    if _project_root is None:
        return HTMLResponse("Server not configured", status_code=500)

    listing = _build_project_listing(_project_root)

    # compute relative paths for project documents
    project_docs_with_paths = []
    for doc in listing.project_documents:
        try:
            rel_path = doc.path.relative_to(_project_root)
        except ValueError:
            rel_path = doc.path
        project_docs_with_paths.append(
            {
                "name": doc.name,
                "path": str(rel_path),
                "category": doc.category,
            }
        )

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "project_documents": project_docs_with_paths,
            "specs": listing.specs,
        },
    )


def _is_safe_path(project_root: Path, requested_path: Path) -> bool:
    """check if requested path is within project root (prevents directory traverse)"""
    try:
        resolved = requested_path.resolve()
        project_resolved = project_root.resolve()
        return resolved.is_relative_to(project_resolved)
    except (ValueError, OSError):
        return False


async def api_document(request: Request) -> JSONResponse:
    """fetch and render a markdown document"""
    if _project_root is None:
        return JSONResponse({"error": "Server not configured"}, status_code=500)

    # get path parameter
    path_param = request.query_params.get("path")
    if not path_param:
        return JSONResponse(
            {"error": "Invalid path", "detail": "Missing path parameter"},
            status_code=400,
        )

    # only allow .md files
    if not path_param.endswith(".md"):
        return JSONResponse(
            {"error": "Invalid path", "detail": "Only markdown files allowed"},
            status_code=400,
        )

    # resolve the full path
    full_path = _project_root / path_param

    # security: check path is within project root
    if not _is_safe_path(_project_root, full_path):
        return JSONResponse(
            {"error": "Invalid path", "detail": "Path outside project root"},
            status_code=400,
        )

    # check if file exists
    if not full_path.is_file():
        return JSONResponse(
            {"error": "Document not found", "path": path_param},
            status_code=404,
        )

    # read and render
    try:
        content = full_path.read_text(encoding="utf-8")
        html = render_markdown(content)
        # extract title from first h1 or use filename
        title = full_path.stem
        lines = content.split("\n")
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # get file timestamps
        stat = full_path.stat()
        modified_ts = stat.st_mtime
        created_ts = stat.st_ctime

        return JSONResponse(
            {
                "title": title,
                "content": html,
                "path": path_param,
                "modified": modified_ts,
                "created": created_ts,
            }
        )
    except OSError:
        return JSONResponse(
            {"error": "Document not found", "path": path_param},
            status_code=404,
        )


def create_app(project_root: Path) -> Starlette:
    """Create a Starlette application for the given project.

    Args:
        project_root: path to the project root directory

    Returns:
        configured Starlette application
    """
    global _project_root
    _project_root = project_root

    routes = [
        Route("/", index),
        Route("/api/document", api_document),
        Mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static"),
    ]
    return Starlette(routes=routes)


def run_server(port: int, project_root: Path) -> None:
    """run the uvicorn server (called when the module is run directly as a subprocess)"""
    import uvicorn

    global _project_root
    _project_root = project_root

    app = create_app(project_root)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        # show usage
        print("Usage: python -m specbook.ui.web.app <port> <project_root>")
        sys.exit(1)

    port = int(sys.argv[1])
    project_root = Path(sys.argv[2])
    run_server(port, project_root)
