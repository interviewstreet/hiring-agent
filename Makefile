# Makefile for Hiring Agent

.PHONY: help install test test-unit test-integration test-performance test-coverage lint format clean setup-dev

help: ## Show this help message
	@echo "Hiring Agent - Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

setup-dev: ## Set up development environment
	python -m venv .venv
	.venv/bin/pip install -r requirements.txt
	@echo "Development environment set up. Activate with: source .venv/bin/activate"

test: ## Run all tests
	pytest

test-unit: ## Run unit tests only
	pytest tests/test_models.py tests/test_llm_utils.py -m "not integration and not slow"

test-integration: ## Run integration tests only
	pytest tests/test_integration.py -m integration

test-performance: ## Run performance tests only
	pytest tests/test_performance.py -m slow

test-coverage: ## Run tests with coverage report
	pytest --cov=. --cov-report=html --cov-report=term-missing

test-fast: ## Run fast tests only (exclude slow and integration)
	pytest -m "not slow and not integration"

lint: ## Run linting
	black --check .
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

format: ## Format code with black
	black .

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete

run-example: ## Run the hiring agent on an example PDF
	python score.py examples/sample_resume.pdf

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install pytest-xdist  # For parallel test execution

test-parallel: ## Run tests in parallel
	pytest -n auto

test-verbose: ## Run tests with verbose output
	pytest -v -s

test-specific: ## Run specific test (usage: make test-specific TEST=test_name)
	pytest -k $(TEST)

check-all: lint test ## Run linting and tests
	@echo "All checks passed!"

ci: ## Run CI pipeline (linting + tests + coverage)
	black --check .
	pytest --cov=. --cov-report=xml --cov-fail-under=80
	@echo "CI pipeline completed successfully!"
