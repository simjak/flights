.PHONY: setup build run test lint format clean

setup: ## Setup development environment
	@echo "Setting up development environment..."
	@curl -LsSf https://astral.sh/uv/install.sh | sh
	@uv venv
	@. .venv/bin/activate && uv pip install -e .

build: ## Build Docker images
	@echo "Building Docker images..."
	@docker-compose build

run: ## Run services
	@echo "Starting services..."
	@docker-compose up -d

test: ## Run tests
	@echo "Running tests..."
	@. .venv/bin/activate && uv pip install pytest pytest-asyncio pytest-cov
	@. .venv/bin/activate && pytest tests/ -v --cov=src

lint: ## Run linters
	@echo "Running linters..."
	@. .venv/bin/activate && uv pip install ruff mypy
	@. .venv/bin/activate && ruff check src/
	@. .venv/bin/activate && mypy src/

format: ## Format code
	@echo "Formatting code..."
	@. .venv/bin/activate && uv pip install ruff
	@. .venv/bin/activate && ruff format src/

clean: ## Clean up
	@echo "Cleaning up..."
	@docker-compose down -v
	@rm -rf .pytest_cache .coverage .mypy_cache .ruff_cache .venv
	@find . -type d -name "__pycache__" -exec rm -r {} +

help: ## Show this help
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help