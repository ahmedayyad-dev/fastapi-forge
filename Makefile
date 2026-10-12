.DEFAULT_GOAL := help
SHELL := /bin/bash
PY := uv run

.PHONY: help install dev run test test-cov lint format typecheck check docker-build docker-up docker-down clean

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install runtime + dev dependencies
	uv sync --extra dev

dev: ## Run the app in watch mode with auto-reload
	$(PY) uvicorn fastapi_forge.main:app --reload --host 0.0.0.0 --port 8000

run: ## Run the app (no reload)
	$(PY) uvicorn fastapi_forge.main:app --host 0.0.0.0 --port 8000

test: ## Run the test suite
	$(PY) pytest

test-cov: ## Run tests with coverage report
	$(PY) pytest --cov=fastapi_forge --cov-report=term-missing

lint: ## Lint with ruff
	$(PY) ruff check .

format: ## Auto-format with ruff
	$(PY) ruff format .
	$(PY) ruff check --fix .

typecheck: ## Static type checking with mypy
	$(PY) mypy src

check: lint typecheck test ## Run lint, typecheck and tests

docker-build: ## Build the Docker image
	docker build -t fastapi-forge:latest .

docker-up: ## Start app + redis via docker compose
	docker compose up --build -d

docker-down: ## Stop the compose stack
	docker compose down

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage dist build
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
