.PHONY: help install install-dev test coverage lint format clean build docs

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install package in production mode
	pip install -r requirements.txt
	pip install .

install-dev:  ## Install package in development mode with all extras
	pip install -e ".[dev,full]"
	pre-commit install 2>/dev/null || true

test:  ## Run unit tests
	pytest tests/ -v

coverage:  ## Run tests with coverage report
	pytest tests/ --cov=src --cov-report=html --cov-report=term

lint:  ## Run linting checks
	flake8 src tests
	mypy src

format:  ## Format code with black and isort
	black src tests
	isort src tests

check:  ## Run all checks (lint, format check, tests)
	black --check src tests
	isort --check src tests
	flake8 src tests
	mypy src
	pytest tests/

clean:  ## Clean build artifacts and caches
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .coverage htmlcov coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

build:  ## Build distribution packages
	python -m build

docs:  ## Generate documentation
	@echo "Documentation generation not yet configured"
	@echo "See docs/ directory for markdown documentation"

run:  ## Run validation on example model (requires model.stl)
	@if [ -f model.stl ]; then \
		python -m src.cli model.stl; \
	else \
		echo "No model.stl found. Please provide a test STL file."; \
	fi

benchmark:  ## Run performance benchmarks
	@echo "Running performance benchmark..."
	@python -c "import time; from src.core.analysis import mesh_validator; import trimesh; \
		mesh = trimesh.creation.icosphere(subdivisions=4); \
		start = time.time(); \
		result = mesh_validator.validate_mesh(mesh); \
		elapsed = time.time() - start; \
		print(f'Validation completed in {elapsed:.3f} seconds'); \
		print(f'Issues found: {len(result.issues)}'); \
		print(f'Success: {result.success}')"