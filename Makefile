.PHONY: help install test lint run healthcheck backup docker-up docker-down docker-logs clean

PYTHON := python3
VENV := .venv
BIN := $(VENV)/bin

help: ## Show available commands
	@echo "ChronoDump Developer & Production Command Suite"
	@echo "================================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Setup virtual environment and install dependencies
	bash scripts/setup.sh

test: ## Run full test suite with pytest
	$(BIN)/pytest -v

test-cov: ## Run tests with coverage report
	$(BIN)/pytest --cov=app tests/

run: ## Run ChronoDump bot locally
	$(BIN)/python -m app.main

healthcheck: ## Run system diagnostic health probe
	$(BIN)/python scripts/healthcheck.py

backup: ## Perform automated database snapshot
	bash scripts/backup.sh

deploy: ## Execute zero-downtime 5-phase production deployment
	bash scripts/deploy.sh

rollback: ## Rollback to previous deployment backup
	bash scripts/rollback.sh

docker-up: ## Start Docker Compose stack
	docker compose up -d --build

docker-down: ## Stop Docker Compose stack
	docker compose down

docker-logs: ## Tail Docker Compose logs
	docker compose logs -f chronodump

clean: ## Remove bytecode, caches, and test artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.py[cod]" -delete
	rm -rf .pytest_cache .coverage htmlcov
