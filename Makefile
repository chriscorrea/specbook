.PHONY: help test lint install clean format check

help:
	@echo "Available commands:"
	@echo "  make install    Install dependencies for dev environment"
	@echo "  make test       Run tests with coverage"
	@echo "  make lint       Run linting and type checking"
	@echo "  make format     run linting with --fix"
	@echo "  make clean      Remove build artifacts and cache"

install:
	uv sync --all-extras --dev

test:
	uv run pytest --cov=specbook --cov-report=term-missing --cov-fail-under=75

lint:
	uv run pyright
	uv run ruff check src tests

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pyright -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov dist build *.egg-info
