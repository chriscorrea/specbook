<img src="src/specbook/ui/web/static/specbook_leaf.png" alt="Specbook" width="64">

# Specbook

A browser-based viewer and editor for spec-driven development (SDD) projects. Specbook facilitates review, collaboration on specs, plans, and task lists.

## How Does It Work?

Specbook launches a local web server that renders your `specs/` directory in a clean, readable format.

## Install

```bash
uv tool install specbook --from git+https://github.com/chriscorrea/specbook.git
```

## Usage

From any directory in your project:

```bash
specbook
```

The server runs in the background—use `specbook stop` when you're done.

## Development

```bash
git clone https://github.com/chriscorrea/specbook.git
cd specbook
uv sync
uv run specbook
```

## License

This project is licensed under the [BSD-3 License](LICENSE).
