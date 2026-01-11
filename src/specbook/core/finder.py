"""project root finder implementation"""

from pathlib import Path

from specbook.core.models import ProjectRoot, SearchResult


def find_project_root(start_path: Path) -> SearchResult:
    """Find the Specbook project root by searching upward from start_path:
    Looks for directories containing .specify/ or specs/ markers.

    Args:
        start_path: directory to start searching from.

    Returns:
        SearchResult with found=True if a project root was discovered
    """
    current = start_path.resolve()
    searched_from = current

    while True:
        has_specify = (current / ".specify").is_dir()
        has_specs = (current / "specs").is_dir()

        if has_specify or has_specs:
            return SearchResult(
                found=True,
                project_root=ProjectRoot(
                    path=current,
                    has_specify_dir=has_specify,
                    has_specs_dir=has_specs,
                ),
                searched_from=searched_from,
                searched_to=current,
            )

        # check if we've reached the filesystem root
        parent = current.parent
        if parent == current:
            # at root, one final check 
            return SearchResult(
                found=False,
                project_root=None,
                searched_from=searched_from,
                searched_to=current,
            )

        current = parent
