.PHONY: help build run test clean docker-build docker-run docker-test

help: ## Show this help message
	@echo "MDF MCP Server - Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build the Docker image
	docker build -t mdfmcp .

run: ## Run the server locally
	python -m mdfmcp.server

test: ## Run tests
	pytest tests/

clean: ## Clean up build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

docker-build: ## Build Docker image
	docker build -t mdfmcp .

docker-run: ## Run Docker container
	docker run -it --rm mdfmcp

docker-test: ## Test Docker container
	docker run --rm mdfmcp python -m pytest tests/

docker-compose-up: ## Start with docker-compose
	docker-compose up -d

docker-compose-down: ## Stop docker-compose
	docker-compose down

docker-compose-logs: ## View docker-compose logs
	docker-compose logs -f

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install -e .

format: ## Format code with black
	black src/ tests/

lint: ## Lint code with ruff
	ruff src/ tests/

type-check: ## Type check with mypy
	mypy src/

check-all: format lint type-check test ## Run all checks