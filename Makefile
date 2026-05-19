.PHONY: help setup setup-uv setup-env setup-db wait-db reset doctor \
        install sync lock dev run shell lint format typecheck check test test-cov clean \
        migrate makemigration downgrade db-revision \
        docker-build docker-up docker-down docker-logs docker-restart

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
UV ?= uv
PYTHON_VERSION ?= 3.13
PORT ?= 8000
MSG ?= "auto migration"
DB_SERVICE ?= db
DB_WAIT_TIMEOUT ?= 60

# ---------------------------------------------------------------------------
# Help (default target)
# ---------------------------------------------------------------------------
help: ## Show this help message
	@echo "FastAPI Boilerplate — make targets"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "}; /^[a-zA-Z_-]+:.*?## / { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ---------------------------------------------------------------------------
# One-shot project bootstrap
# ---------------------------------------------------------------------------
setup: setup-uv setup-env install setup-db wait-db migrate ## Bootstrap everything: uv, .env, deps, Postgres, migrations
	@echo ""
	@echo "✅ Setup complete. Next step: \033[36mmake dev\033[0m"

setup-uv: ## Install uv and pin Python $(PYTHON_VERSION)
	@if ! command -v $(UV) >/dev/null 2>&1; then \
		echo "→ uv not found; installing…"; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		echo "→ uv installed. Restart your shell or run: source ~/.local/bin/env"; \
	else \
		echo "✓ uv already installed ($$($(UV) --version))"; \
	fi
	@$(UV) python install $(PYTHON_VERSION)

setup-env: ## Create .env from .env.example if missing
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ Created .env from .env.example — review and adjust credentials."; \
	else \
		echo "✓ .env already exists."; \
	fi

setup-db: ## Start the Postgres container via docker compose
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "✗ docker not found. Install Docker, or point .env at an existing Postgres."; \
		exit 1; \
	fi
	@docker compose up -d $(DB_SERVICE)

wait-db: ## Block until Postgres is accepting connections (timeout: $(DB_WAIT_TIMEOUT)s)
	@echo "→ Waiting for Postgres to be ready…"
	@elapsed=0; \
	until docker compose exec -T $(DB_SERVICE) pg_isready -q >/dev/null 2>&1; do \
		if [ $$elapsed -ge $(DB_WAIT_TIMEOUT) ]; then \
			echo "✗ Postgres did not become ready within $(DB_WAIT_TIMEOUT)s."; exit 1; \
		fi; \
		sleep 1; elapsed=$$((elapsed + 1)); \
	done; \
	echo "✓ Postgres is ready."

reset: ## Wipe Postgres data volume and rerun setup (destructive!)
	@printf "This will DROP the database volume. Continue? [y/N] "; \
	read ans; [ "$$ans" = "y" ] || { echo "aborted"; exit 1; }
	docker compose down -v
	$(MAKE) setup

doctor: ## Print versions of key tools — handy for bug reports
	@echo "uv:     $$($(UV) --version 2>/dev/null || echo 'not installed')"
	@echo "python: $$($(UV) run python --version 2>/dev/null || python3 --version 2>/dev/null || echo 'not installed')"
	@echo "docker: $$(docker --version 2>/dev/null || echo 'not installed')"
	@echo "make:   $$(make --version | head -1)"

# ---------------------------------------------------------------------------
# Environment management (uv)
# ---------------------------------------------------------------------------
install: ## Create the venv and install runtime + dev + test deps
	$(UV) sync --all-extras

sync: ## Re-sync the venv with the lockfile
	$(UV) sync --all-extras --frozen

lock: ## Refresh uv.lock
	$(UV) lock

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
dev: ## Run the API with auto-reload (development)
	$(UV) run uvicorn app.main:app --reload --host 0.0.0.0 --port $(PORT)

run: ## Run the API (production-style, no reload)
	$(UV) run uvicorn app.main:app --host 0.0.0.0 --port $(PORT)

shell: ## Drop into a Python shell with the project on the path
	$(UV) run python

# ---------------------------------------------------------------------------
# Code quality
# ---------------------------------------------------------------------------
format: ## Format code with ruff
	$(UV) run ruff format src tests

lint: ## Lint code with ruff (auto-fix where possible)
	$(UV) run ruff check --fix src tests

typecheck: ## Static type check with mypy
	$(UV) run mypy

check: format lint typecheck ## Run formatter, linter, and type checker

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
test: ## Run the test suite
	$(UV) run pytest

test-cov: ## Run tests with coverage report
	$(UV) run pytest --cov --cov-report=term-missing --cov-report=xml

# ---------------------------------------------------------------------------
# Database migrations
# ---------------------------------------------------------------------------
migrate: ## Apply all pending migrations
	$(UV) run alembic upgrade head

makemigration: ## Create a new auto-generated migration. Usage: make makemigration MSG="add foo"
	$(UV) run alembic revision --autogenerate -m $(MSG)

downgrade: ## Roll back one migration
	$(UV) run alembic downgrade -1

db-revision: ## Show current DB revision
	$(UV) run alembic current

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------
docker-build: ## Build the API image
	docker compose build

docker-up: ## Start the stack (detached)
	docker compose up -d

docker-down: ## Stop and remove containers
	docker compose down

docker-logs: ## Tail logs from all services
	docker compose logs -f

docker-restart: ## Restart the API container
	docker compose restart api

# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------
clean: ## Remove caches and build artifacts
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -prune -exec rm -rf {} +
	find . -type f -name "*.py[co]" -delete
	rm -rf .coverage coverage.xml htmlcov dist build *.egg-info
