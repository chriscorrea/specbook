"""Starlette web application for specbook spec viewer"""

import re
import sys
from pathlib import Path

import yaml
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
    SpecStatus,
)

# markdown renderer with tables, strikethrough, and task lists
_md = MarkdownIt("commonmark").enable("table").enable("strikethrough").use(tasklists_plugin)

# regex to match YAML frontmatter (but doesn't validate YAML; see parse_frontmatter)
_FRONTMATTER_PATTERN = re.compile(r"^\s*---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def render_markdown(content: str) -> str:
    """render markdown content to HTML, excluding frontmatter"""

    # remove frontmatter when rendering view
    match = _FRONTMATTER_PATTERN.match(content)
    if match:
        # define content as post-frontmatter
        content = content[match.end() :]
    return _md.render(content)


def parse_frontmatter(content: str) -> dict:
    """extract YAML frontmatter from markdown content
    (What is 'frontmatter'? See https://jekyllrb.com/docs/front-matter/

    returns empty dict if frontmatter cannot be parsed
    """
    match = _FRONTMATTER_PATTERN.match(content)
    if not match:
        return {}
    try:
        result = yaml.safe_load(match.group(1))
        if not isinstance(result, dict):
            return {}
        # normalize keys to lowercase for case-insensitivity
        return {k.lower(): v for k, v in result.items()}
    except yaml.YAMLError:
        return {}


def get_doc_status(doc_path: Path) -> SpecStatus:
    """read status value from frontmatter of doc at doc_path

    returns SpecStatus.DRAFT if status or frontmatter can't be parsed
    returns SpecStatus.UNKNOWN if status value is not recognized
    TODO: return other statuses based on doc analysis (e.g. tasks completed)
    """
    if not doc_path.is_file():
        return SpecStatus.DRAFT

    try:
        content = doc_path.read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(content)
        status_value = frontmatter.get("status")
        return SpecStatus.from_string(status_value)
    except OSError:
        return SpecStatus.DRAFT


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
            status = get_doc_status(f)
            docs.append(
                SpecDocument(
                    name=f.name,
                    path=f,
                    display_name=display_name,
                    doc_type=doc_type,
                    status=status,
                )
            )

    # also scan subdirectories for contracts etc.
    for subdir in spec_dir.iterdir():
        if subdir.is_dir() and not subdir.name.startswith("."):
            for f in subdir.iterdir():
                if f.is_file() and f.suffix == ".md":
                    # use subdir/filename format for display
                    display_name = f"{subdir.name}/{f.stem}".title()
                    status = get_doc_status(f)
                    docs.append(
                        SpecDocument(
                            name=f"{subdir.name}/{f.name}",
                            path=f,
                            display_name=display_name,
                            doc_type="other",
                            status=status,
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


def _validate_document_path(path_param: str | None) -> tuple[Path | None, JSONResponse | None]:
    """validate document path and return (full_path, error_response)

    Returns (full_path, None) on success, or (None, error_response) on failure.
    """
    if _project_root is None:
        return None, JSONResponse({"error": "Server not configured"}, status_code=500)

    if not path_param:
        return None, JSONResponse(
            {"error": "Invalid path", "detail": "Missing path parameter"},
            status_code=400,
        )

    # only allow .md files
    if not path_param.endswith(".md"):
        return None, JSONResponse(
            {"error": "Invalid path", "detail": "Only markdown files allowed"},
            status_code=400,
        )

    # resolve the full path
    full_path = _project_root / path_param

    # security: check path is within project root
    if not _is_safe_path(_project_root, full_path):
        return None, JSONResponse(
            {"error": "Invalid path", "detail": "Path outside project root"},
            status_code=400,
        )

    return full_path, None


async def api_document(request: Request) -> JSONResponse:
    """fetch and render a markdown doc"""
    path_param = request.query_params.get("path")
    full_path, error = _validate_document_path(path_param)
    if error:
        return error

    assert full_path is not None  # for type checks

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


async def api_document_raw(request: Request) -> JSONResponse:
    """fetch raw markdown content for editing"""
    path_param = request.query_params.get("path")
    full_path, error = _validate_document_path(path_param)
    if error:
        return error

    assert full_path is not None

    if not full_path.is_file():
        return JSONResponse(
            {"error": "Document not found", "path": path_param},
            status_code=404,
        )

    try:
        content = full_path.read_text(encoding="utf-8")
        stat = full_path.stat()
        return JSONResponse(
            {
                "path": path_param,
                "raw": content,
                "modified": stat.st_mtime,
            }
        )
    except OSError:
        return JSONResponse(
            {"error": "Document not found", "path": path_param},
            status_code=404,
        )


async def api_document_save(request: Request) -> JSONResponse:
    """save edited markdown content to file"""
    if _project_root is None:
        return JSONResponse({"error": "Server not configured"}, status_code=500)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"error": "Invalid request", "detail": "Invalid JSON body"},
            status_code=400,
        )

    path_param = body.get("path")
    content = body.get("content")

    if content is None:
        return JSONResponse(
            {"error": "Invalid request", "detail": "Missing content field"},
            status_code=400,
        )

    full_path, error = _validate_document_path(path_param)
    if error:
        return error

    assert full_path is not None

    # check if file exists
    if not full_path.is_file():
        return JSONResponse(
            {"error": "Document not found", "path": path_param},
            status_code=404,
        )

    try:
        full_path.write_text(content, encoding="utf-8")
        stat = full_path.stat()
        return JSONResponse(
            {
                "success": True,
                "path": path_param,
                "modified": stat.st_mtime,
            }
        )
    except PermissionError:
        return JSONResponse(
            {"error": "Save failed", "detail": "Permission denied"},
            status_code=403,
        )
    except OSError as e:
        return JSONResponse(
            {"error": "Save failed", "detail": str(e)},
            status_code=500,
        )


async def api_checkbox_toggle(request: Request) -> JSONResponse:
    """toggle a checkbox on a particular line"""
    if _project_root is None:
        return JSONResponse({"error": "Server not configured"}, status_code=500)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"error": "Invalid request", "detail": "Invalid JSON body"},
            status_code=400,
        )

    path_param = body.get("path")
    line_number = body.get("lineNumber")
    checked = body.get("checked")

    if line_number is None or not isinstance(line_number, int) or line_number < 1:
        return JSONResponse(
            {"error": "Invalid line number", "detail": "lineNumber must be a positive integer"},
            status_code=400,
        )

    if checked is None or not isinstance(checked, bool):
        return JSONResponse(
            {"error": "Invalid request", "detail": "checked must be a boolean"},
            status_code=400,
        )

    full_path, error = _validate_document_path(path_param)
    if error:
        return error

    assert full_path is not None

    if not full_path.is_file():
        return JSONResponse(
            {"error": "Document not found", "path": path_param},
            status_code=404,
        )

    try:
        content = full_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        # validate line number is in range
        if line_number > len(lines):
            return JSONResponse(
                {
                    "error": "Invalid line number",
                    "detail": f"Line {line_number} exceeds file length",
                },
                status_code=400,
            )

        # get the line (1-indexed)
        line_idx = line_number - 1
        line = lines[line_idx]

        # check if line contains checkbox
        checkbox_unchecked = re.match(r"^(\s*-\s*)\[ \](.*)$", line)
        checkbox_checked = re.match(r"^(\s*-\s*)\[[xX]\](.*)$", line)

        if not checkbox_unchecked and not checkbox_checked:
            return JSONResponse(
                {
                    "error": "Invalid checkbox",
                    "detail": f"Line {line_number} is not a checkbox item",
                },
                status_code=400,
            )

        # toggle the box
        if checked:
            # set to *checked*
            if checkbox_unchecked:
                lines[line_idx] = f"{checkbox_unchecked.group(1)}[x]{checkbox_unchecked.group(2)}"
        else:
            # set to *unchecked*
            if checkbox_checked:
                lines[line_idx] = f"{checkbox_checked.group(1)}[ ]{checkbox_checked.group(2)}"

        # write back
        new_content = "\n".join(lines)
        full_path.write_text(new_content, encoding="utf-8")

        return JSONResponse(
            {
                "success": True,
                "path": path_param,
                "lineNumber": line_number,
                "checked": checked,
            }
        )
    except PermissionError:
        return JSONResponse(
            {"error": "Save failed", "detail": "Permission denied"},
            status_code=403,
        )
    except OSError as e:
        return JSONResponse(
            {"error": "Save failed", "detail": str(e)},
            status_code=500,
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
        Route("/api/document/raw", api_document_raw),
        Route("/api/document", api_document_save, methods=["POST"]),
        Route("/api/checkbox", api_checkbox_toggle, methods=["POST"]),
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
