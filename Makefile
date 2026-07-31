.PHONY: help setup install lock dev run shell \
        format lint typecheck check test test-cov test-all \
        migrate makemigration downgrade db-revision db-reset \
        clean doctor

UV ?= uv
PORT ?= 8000
MSG ?= "auto migration"

# ---------------------------------------------------------------------------
# Help (default target)
# ---------------------------------------------------------------------------
help: ## Show this help
	@echo "FastAPI Boilerplate"
	@echo ""
	@echo "  First time here?  make setup  →  make dev"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "}; /^[a-zA-Z_-]+:.*?## / { printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ---------------------------------------------------------------------------
# Getting started
# ---------------------------------------------------------------------------
setup: ## Set the project up on this machine (safe to re-run)
	@./scripts/setup.sh

install: ## Install dependencies only
	$(UV) sync

lock: ## Refresh uv.lock after editing pyproject.toml
	$(UV) lock

# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------
dev: ## Run with auto-reload at http://localhost:$(PORT)
	$(UV) run fastapi dev src/app/main.py --port $(PORT)

run: ## Run using the API_* values from .env (production style)
	$(UV) run python -m app

shell: ## Python shell with the project importable
	$(UV) run python

# ---------------------------------------------------------------------------
# Code quality — `check` is what CI runs
# ---------------------------------------------------------------------------
format: ## Reformat the code
	$(UV) run ruff format src tests

lint: ## Lint, fixing what can be fixed
	$(UV) run ruff check --fix src tests

typecheck: ## Type-check with mypy (strict)
	$(UV) run mypy

check: format lint typecheck test ## Format, lint, type-check, and test

test: ## Run the tests
	$(UV) run pytest

test-cov: ## Run the tests with a coverage report
	$(UV) run pytest --cov --cov-report=term-missing --cov-report=xml

test-all: ## Run the tests against every installed backend driver
	$(UV) run --all-extras pytest

# ---------------------------------------------------------------------------
# Database (not used by MongoDB, which has no schema)
# ---------------------------------------------------------------------------
migrate: ## Apply pending migrations
	$(UV) run alembic upgrade head

makemigration: ## Create a migration from model changes. Usage: make makemigration MSG="add posts"
	$(UV) run alembic revision --autogenerate -m $(MSG)

downgrade: ## Undo the last migration
	$(UV) run alembic downgrade -1

db-revision: ## Show the revision the database is on
	$(UV) run alembic current

db-reset: ## Drop everything and re-apply all migrations (destructive)
	@printf "This deletes all data in the configured database. Continue? [y/N] "; \
	read ans; [ "$$ans" = "y" ] || { echo "aborted"; exit 1; }
	$(UV) run alembic downgrade base
	$(UV) run alembic upgrade head

# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------
doctor: ## Print tool versions and the configured backend — useful in bug reports
	@echo "uv:      $$($(UV) --version 2>/dev/null || echo 'not installed')"
	@echo "python:  $$($(UV) run python --version 2>/dev/null || echo 'not installed')"
	@echo "backend: $$($(UV) run python -c 'from app.core.config import settings; print(settings.backend.value)' 2>/dev/null || echo 'unknown — is .env present?')"

clean: ## Remove caches and build artifacts
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -prune -exec rm -rf {} +
	find . -type f -name "*.py[co]" -delete
	rm -rf .coverage coverage.xml htmlcov dist build *.egg-info
