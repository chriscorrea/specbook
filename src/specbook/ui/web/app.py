"""Starlette web application for specbook spec viewer"""

import sys
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from specbook.core.models import SpecListing

# templates and static dir relative to this file
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# global project root (set by create_app or main)
_project_root: Path | None = None


async def index(request: Request) -> HTMLResponse:
    """render the spec listing page"""
    if _project_root is None:
        return HTMLResponse("Server not configured", status_code=500)

    listing = SpecListing.from_project(_project_root)
    return templates.TemplateResponse(
        request,
        "index.html",
        {"specs": listing.specs},
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
