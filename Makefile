.PHONY: help install setup run test clean migrate migrate-create docker-build docker-run docker-stop

help: ## Show this help message
	@echo "FastAPI Boilerplate - Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

setup: ## Setup the project (install + migrate)
	$(MAKE) install
	python scripts/setup.py

run: ## Run the development server
	python main.py

test: ## Run tests (placeholder)
	@echo "Tests not implemented yet"

clean: ## Clean up cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

migrate: ## Apply database migrations
	alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MESSAGE="description")
	alembic revision --autogenerate -m "$(MESSAGE)"

docker-build: ## Build Docker image
	docker build -t fastapi-boilerplate .

docker-run: ## Run with Docker Compose
	docker-compose up -d

docker-stop: ## Stop Docker Compose
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f 