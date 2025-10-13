# RMCP Development Makefile
# Optional local testing scripts (use instead of pre-commit hooks)

.PHONY: help lint-python lint-r lint test-fast test-r test-all coverage clean

help:  ## Show this help message
	@echo "RMCP Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Examples:"
	@echo "  make lint          # Lint all code (Python + R)"
	@echo "  make test-fast     # Run unit tests only"
	@echo "  make test-all      # Run full test suite"

# Python linting and formatting
lint-python:  ## Format and lint Python code
	@echo "🐍 Formatting Python code..."
	poetry run black rmcp tests streamlit docs
	poetry run isort rmcp tests streamlit docs
	@echo "🔍 Linting Python code..."
	poetry run flake8 rmcp tests streamlit docs

# R linting and formatting  
lint-r:  ## Format and lint R code
	@echo "📊 Formatting R code..."
	cd rmcp/r_assets && R -e "library(styler); files <- list.files(c('R', 'scripts'), pattern='[.]R$$', recursive=TRUE, full.names=TRUE); if(length(files) > 0) styler::style_file(files)"
	@echo "🔍 Linting R code..."
	cd rmcp/r_assets && R -e "library(lintr); files <- list.files(c('R', 'scripts'), pattern='[.]R$$', recursive=TRUE, full.names=TRUE); if(length(files) > 0) { results <- lapply(files, lint); all_lints <- unlist(results, recursive=FALSE); if(length(all_lints) > 0) { print(all_lints); stop('Linting issues found') } else { cat('✅ R linting passed\\n') } }"

lint: lint-python lint-r  ## Lint all code (Python + R)

# Testing
test-fast:  ## Run Python unit tests only (fast)
	@echo "⚡ Running unit tests..."
	poetry run pytest tests/unit/ -v

test-r:  ## Run R tests only
	@echo "📊 Running R tests..."
	cd rmcp/r_assets && testthat_testing=TRUE R -e "library(testthat); test_dir('tests/testthat')"

test-python:  ## Run all Python tests (unit + integration)
	@echo "🐍 Running Python tests..."
	poetry run pytest tests/unit/ tests/integration/ -v

test-all:  ## Run full test suite (Python + R)
	@echo "🧪 Running full test suite..."
	make test-python
	make test-r

# Coverage
coverage:  ## Generate coverage reports
	@echo "📊 Generating Python coverage..."
	poetry run pytest tests/unit/ --cov=rmcp --cov-report=html --cov-report=term-missing
	@echo "📈 Python coverage report: htmlcov/index.html"
	@echo ""
	@echo "📊 Generating R coverage..."
	cd rmcp/r_assets && R -e "library(covr); cov <- package_coverage('.'); print(cov); report(cov, file='coverage.html')"
	@echo "📈 R coverage report: rmcp/r_assets/coverage.html"

# Development helpers
install:  ## Install development dependencies
	@echo "📦 Installing dependencies..."
	poetry install --with dev
	cd rmcp/r_assets && R -e "install.packages(c('testthat', 'lintr', 'styler', 'covr'), repos='https://cran.r-project.org')"

clean:  ## Clean up generated files
	@echo "🧹 Cleaning up..."
	rm -rf htmlcov/ .coverage coverage.xml
	rm -rf rmcp/r_assets/coverage.html rmcp/r_assets/coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +

# Server commands
start:  ## Start RMCP server (stdio mode)
	poetry run rmcp start

start-http:  ## Start RMCP server (HTTP mode)
	poetry run rmcp http

# Development workflow examples
dev-check: lint test-fast  ## Quick development check (lint + unit tests)
	@echo "✅ Development check passed!"

ci-check: lint test-all coverage  ## Full CI-like check locally
	@echo "✅ CI check passed!"

# Help is default target
.DEFAULT_GOAL := help