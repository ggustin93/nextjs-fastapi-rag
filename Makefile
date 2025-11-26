.PHONY: help install install-dev lint format test test-backend test-frontend test-unit test-integration run run-backend run-frontend ingest docker-build docker-up docker-down docker-clean clean

BACKEND_DIR := services/api
FRONTEND_DIR := services/web

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -e .
	cd $(FRONTEND_DIR) && npm ci

install-dev: install ## Install dev dependencies
	pip install -e ".[dev]"

lint: ## Lint code
	ruff check . --fix
	cd $(FRONTEND_DIR) && npm run lint

format: ## Format code
	ruff format .

test: ## Run tests
	@echo "Running backend tests..."
	.venv/bin/python -m pytest tests/ -v --cov=packages --cov=services/api/app
	@echo "Running frontend tests..."
	cd $(FRONTEND_DIR) && npm test

test-backend: ## Run backend tests only
	@echo "Running backend tests..."
	.venv/bin/python -m pytest tests/ -v --cov=packages --cov=services/api/app

test-frontend: ## Run frontend tests only
	@echo "Running frontend tests..."
	cd $(FRONTEND_DIR) && npm test

test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	.venv/bin/python -m pytest tests/unit/ -v

test-integration: ## Run integration tests only
	@echo "Running integration tests..."
	.venv/bin/python -m pytest tests/integration/ -v

run: ## Start dev servers
	./scripts/restart-servers.sh

run-backend: ## Start backend only
	cd $(BACKEND_DIR) && uvicorn app.main:app --reload --port 8000

run-frontend: ## Start frontend only
	cd $(FRONTEND_DIR) && npm run dev

ingest: ## Ingest documents into vector DB
	.venv/bin/python -m packages.ingestion.ingest -d data/raw

docker-build: ## Build Docker images
	docker-compose build

docker-up: ## Start Docker containers
	docker-compose up -d

docker-down: ## Stop Docker containers
	docker-compose down

docker-clean: ## Clean Docker images, containers, and volumes
	docker system prune -af --volumes

clean: ## Clean build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	cd $(FRONTEND_DIR) && rm -rf .next/ 2>/dev/null || true
