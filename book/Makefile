# Makefile for LLM-ETI JupyterBook project

# Variables
PYTHON := python3
UV := uv

# Use Python 3.12 for compatibility
# On macOS with Homebrew, use the specific path; otherwise let uv find it
ifeq ($(shell uname -s),Darwin)
    ifneq ($(wildcard /opt/homebrew/opt/python@3.12/bin/python3.12),)
        export UV_PYTHON := /opt/homebrew/opt/python@3.12/bin/python3.12
    endif
endif

BOOK_DIR := .
BUILD_DIR := _build
SCRIPTS_DIR := scripts
DATA_DIR := data
FIGURES_DIR := figures
TABLES_DIR := tables

# Default target
.PHONY: all
all: data figures tables book

# Install dependencies with uv
.PHONY: install
install:
	@command -v uv >/dev/null 2>&1 || (echo "Installing uv..." && curl -LsSf https://astral.sh/uv/install.sh | sh)
	@echo "Installing dependencies with uv..."
	cd .. && $(UV) sync

# Run LLM simulations (expensive - only run when needed)
.PHONY: data
data:
	@echo "Running LLM simulations with EDSL..."
	@mkdir $(DATA_DIR)
	cd .. && $(UV) run python book/$(SCRIPTS_DIR)/run_pknf_simulation.py
	cd .. && $(UV) run python book/$(SCRIPTS_DIR)/run_gruber_saez_simulation.py

# Run test simulations with gpt-4o-mini only (for CI)
.PHONY: test-data
test-data:
	@echo "Running test simulations with gpt-4o-mini using EDSL..."
	@mkdir $(DATA_DIR)
	cd .. && $(UV) run python book/$(SCRIPTS_DIR)/run_pknf_simulation.py --test --model gpt-4o-mini
	cd .. && $(UV) run python book/$(SCRIPTS_DIR)/run_gruber_saez_simulation.py --test --model gpt-4o-mini

# Generate figures from data
.PHONY: figures
figures:
	@echo "Generating figures..."
	@mkdir $(FIGURES_DIR)
	cd .. && $(UV) run python book/$(SCRIPTS_DIR)/generate_figures.py

# Generate tables from data
.PHONY: tables
tables:
	@echo "Generating tables..."
	@mkdir $(TABLES_DIR)
	cd .. && $(UV) run python book/$(SCRIPTS_DIR)/generate_tables.py

# Build the JupyterBook
.PHONY: book
book:
	@echo "Building JupyterBook..."
	cd .. && $(UV) run jupyter-book build book

# Build PDF via LaTeX
.PHONY: pdf
pdf: book
	@echo "Building PDF..."
	cd .. && $(UV) run jupyter-book build book --builder pdflatex

# Clean build artifacts
.PHONY: clean
clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(BUILD_DIR)
	rm -rf $(BOOK_DIR)/.jupyter_cache

# Clean all generated content
.PHONY: clean-all
clean-all: clean
	@echo "Cleaning all generated content..."
	rm -rf $(FIGURES_DIR)/*.png
	rm -rf $(TABLES_DIR)/*.tex
	rm -rf $(DATA_DIR)/*.csv

# Serve the book locally
.PHONY: serve
serve: book
	@echo "Starting local server..."
	cd $(BUILD_DIR)/html && $(PYTHON) -m http.server 8000

# Check for required environment variables
.PHONY: check-env
check-env:
	@if [ -z "$$EXPECTED_PARROT_API_KEY" ]; then \
		echo "Error: EXPECTED_PARROT_API_KEY environment variable is not set"; \
		exit 1; \
	fi

# Development tasks
.PHONY: format
format:
	@echo "Formatting code..."
	cd .. && $(UV) run black .
	cd .. && $(UV) run ruff check --fix .

.PHONY: lint
lint:
	@echo "Linting code..."
	cd .. && $(UV) run black --check .
	cd .. && $(UV) run ruff check .
	cd .. && $(UV) run mypy .

.PHONY: test
test:
	@echo "Running tests..."
	cd .. && $(UV) run pytest tests/

# Help
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  all        - Run full pipeline (data, figures, tables, book)"
	@echo "  install    - Install Python dependencies with uv"
	@echo "  data       - Run LLM simulations (expensive!)"
	@echo "  test-data  - Run test simulations with gpt-4o-mini only"
	@echo "  figures    - Generate figures from data"
	@echo "  tables     - Generate tables from data"
	@echo "  book       - Build JupyterBook"
	@echo "  pdf        - Build PDF via LaTeX"
	@echo "  serve      - Serve book locally on port 8000"
	@echo "  clean      - Clean build artifacts"
	@echo "  clean-all  - Clean all generated content"
	@echo "  check-env  - Check required environment variables"
	@echo "  format     - Format code with black and ruff"
	@echo "  lint       - Run linters"
	@echo "  test       - Run tests"