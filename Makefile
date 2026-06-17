.PHONY: install install-dev lint typecheck test test-cov run clean help

# Default target
help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install core dependencies
	pip install -e .

install-dev: ## Install all dependencies (core + analysis + mcp + dev)
	pip install -e ".[all]"

lint: ## Run ruff linter
	ruff check src/ tests/

lint-fix: ## Run ruff linter with auto-fix
	ruff check --fix src/ tests/

format: ## Format code with ruff
	ruff format src/ tests/

typecheck: ## Run mypy type checker
	mypy src/

test: ## Run tests
	pytest tests/

test-cov: ## Run tests with coverage
	pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

run: ## Run pulse CLI (pass ARGS, e.g. make run ARGS="run --product groww")
	python -m src.main $(ARGS)

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/ htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
