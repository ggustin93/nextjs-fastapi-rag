.PHONY: help install install-dev clean test test-backend test-frontend test-unit test-integration test-coverage lint format run-backend run-frontend run docker-build docker-up docker-down docker-logs docker-clean pre-commit venv setup db-migrate db-seed docs-serve docs-build git-prune deploy-staging deploy-production clean-all

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
UV := uv run
VENV := venv
BACKEND_DIR := services/api
FRONTEND_DIR := services/web

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Default target
help: ## Show this help message
	@echo "$(BLUE)Osiris MultiRAG Agent - Development Commands$(NC)"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# ====================================
# Installation
# ====================================

install: ## Install production dependencies
	@echo "$(YELLOW)Installing production dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	cd $(FRONTEND_DIR) && npm ci

install-dev: install ## Install all dependencies including dev tools
	@echo "$(YELLOW)Installing development dependencies...$(NC)"
	$(PIP) install -r requirements-dev.txt 2>/dev/null || $(PIP) install pytest pytest-cov pytest-asyncio pytest-mock black ruff mypy pre-commit
	cd $(FRONTEND_DIR) && npm ci
	pre-commit install

venv: ## Create Python virtual environment
	@echo "$(YELLOW)Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV)
	@echo "$(GREEN)Virtual environment created. Activate with: source $(VENV)/bin/activate$(NC)"

# ====================================
# Code Quality
# ====================================

lint: ## Run all linters
	@echo "$(YELLOW)Running Python linters...$(NC)"
	$(UV) ruff check . --fix || true
	@echo "$(YELLOW)Running TypeScript linters...$(NC)"
	cd $(FRONTEND_DIR) && npm run lint

format: ## Format all code
	@echo "$(YELLOW)Formatting Python code...$(NC)"
	$(UV) ruff format . || true
	@echo "$(YELLOW)Formatting TypeScript code...$(NC)"
	cd $(FRONTEND_DIR) && npm run format 2>/dev/null || echo "No format script configured"

pre-commit: ## Run pre-commit hooks
	@echo "$(YELLOW)Running pre-commit hooks...$(NC)"
	pre-commit run --all-files

# ====================================
# Testing
# ====================================

test: ## Run all tests
	@echo "$(YELLOW)Running backend tests...$(NC)"
	$(UV) pytest tests/ -v --cov=packages --cov=services/api/app --cov-report=term-missing
	@echo "$(YELLOW)Running frontend tests...$(NC)"
	cd $(FRONTEND_DIR) && npm test

test-backend: ## Run backend tests only
	@echo "$(YELLOW)Running backend tests...$(NC)"
	$(UV) pytest tests/ -v --cov=packages --cov=services/api/app --cov-report=term-missing --cov-report=html

test-frontend: ## Run frontend tests only
	@echo "$(YELLOW)Running frontend tests...$(NC)"
	cd $(FRONTEND_DIR) && npm test

test-unit: ## Run unit tests only (fast)
	@echo "$(YELLOW)Running unit tests...$(NC)"
	$(UV) pytest tests/unit/ -v

test-integration: ## Run integration tests only
	@echo "$(YELLOW)Running integration tests...$(NC)"
	$(UV) pytest tests/integration/ -v

test-coverage: ## Generate test coverage report
	@echo "$(YELLOW)Generating coverage report...$(NC)"
	$(UV) pytest tests/ --cov=packages --cov=services/api/app --cov-report=html
	@echo "$(GREEN)Coverage report generated in htmlcov/index.html$(NC)"

# ====================================
# Development Servers
# ====================================

run: ## Start both backend and frontend servers
	@echo "$(YELLOW)Starting development servers...$(NC)"
	./scripts/restart-servers.sh

run-backend: ## Start backend server only
	@echo "$(YELLOW)Starting backend server...$(NC)"
	cd $(BACKEND_DIR) && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-frontend: ## Start frontend server only
	@echo "$(YELLOW)Starting frontend server...$(NC)"
	cd $(FRONTEND_DIR) && npm run dev

# ====================================
# Docker
# ====================================

docker-build: ## Build Docker images
	@echo "$(YELLOW)Building Docker images...$(NC)"
	docker-compose build

docker-up: ## Start Docker containers
	@echo "$(YELLOW)Starting Docker containers...$(NC)"
	docker-compose up -d

docker-down: ## Stop Docker containers
	@echo "$(YELLOW)Stopping Docker containers...$(NC)"
	docker-compose down

docker-logs: ## Show Docker container logs
	docker-compose logs -f

docker-clean: ## Remove Docker containers and volumes
	@echo "$(RED)Removing Docker containers and volumes...$(NC)"
	docker-compose down -v

# ====================================
# Database
# ====================================

db-migrate: ## Run database migrations
	@echo "$(YELLOW)Running database migrations...$(NC)"
	cd packages/ingestion && python migrate.py

db-seed: ## Seed database with sample data
	@echo "$(YELLOW)Seeding database...$(NC)"
	python -m packages.ingestion.ingest --path documents/samples

# ====================================
# Documentation
# ====================================

docs-serve: ## Serve documentation locally
	@echo "$(YELLOW)Serving documentation...$(NC)"
	mkdocs serve

docs-build: ## Build documentation
	@echo "$(YELLOW)Building documentation...$(NC)"
	mkdocs build

# ====================================
# Cleaning
# ====================================

clean: ## Clean build artifacts and caches
	@echo "$(RED)Cleaning build artifacts...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ 2>/dev/null || true
	cd $(FRONTEND_DIR) && rm -rf .next/ out/ 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete!$(NC)"

clean-all: clean ## Clean everything including node_modules and venv
	@echo "$(RED)Removing ALL dependencies...$(NC)"
	rm -rf $(VENV) 2>/dev/null || true
	rm -rf $(BACKEND_DIR)/venv 2>/dev/null || true
	rm -rf $(FRONTEND_DIR)/node_modules 2>/dev/null || true
	@echo "$(GREEN)Full cleanup complete!$(NC)"

# ====================================
# Git Helpers
# ====================================

git-prune: ## Clean up git repository
	@echo "$(YELLOW)Pruning git repository...$(NC)"
	git gc --prune=now --aggressive
	git repack -Ad
	@echo "$(GREEN)Git repository pruned!$(NC)"

# ====================================
# Project Setup
# ====================================

setup: venv install-dev ## Complete project setup for new developers
	@echo "$(GREEN)=====================================$(NC)"
	@echo "$(GREEN)Project setup complete!$(NC)"
	@echo ""
	@echo "Next steps:"
	@echo "1. Copy .env.example to .env and configure"
	@echo "2. Copy services/web/.env.example to services/web/.env.local"
	@echo "3. Activate virtual environment: source $(VENV)/bin/activate"
	@echo "4. Run 'make run' to start development servers"
	@echo "$(GREEN)=====================================$(NC)"

# ====================================
# Deployment
# ====================================

deploy-staging: ## Deploy to staging environment
	@echo "$(YELLOW)Deploying to staging...$(NC)"
	@echo "This would trigger staging deployment pipeline"

deploy-production: ## Deploy to production environment
	@echo "$(RED)Deploying to PRODUCTION...$(NC)"
	@echo "This would trigger production deployment pipeline"