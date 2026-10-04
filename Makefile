.PHONY: install run-simulation clean test-simulation run-simulation-high-income run-simulation-4o run-simple-regression book format lint test

# Use Python 3.12 for compatibility
# On macOS with Homebrew, use the specific path; otherwise let uv find it
ifeq ($(shell uname -s),Darwin)
    ifneq ($(wildcard /opt/homebrew/opt/python@3.12/bin/python3.12),)
        export UV_PYTHON := /opt/homebrew/opt/python@3.12/bin/python3.12
    endif
endif

# Install dependencies using uv
install:
	@command -v uv >/dev/null 2>&1 || (echo "Installing uv..." && curl -LsSf https://astral.sh/uv/install.sh | sh)
	@echo "Creating virtual environment with Python 3.12..."
	@uv venv --python 3.12
	@echo "Installing dependencies..."
	@uv sync --group dev
	@echo ""
	@echo "✅ Installation complete!"
	@echo ""
	@echo "To get started:"
	@echo "1. Set your API key: export EXPECTED_PARROT_API_KEY=your-key-here"
	@echo "2. Build and serve the book: cd book && make serve"

# Legacy simulation commands - removed since we don't have cli.py anymore
# These can be reimplemented using direct Python scripts if needed

run-simple-regression:
	uv run python -m llm_eti.simple_regression

# JupyterBook commands
book:
	cd book && make book

book-serve:
	cd book && make serve

book-pdf:
	cd book && make pdf

book-test:
	cd book && make test-data && make figures && make tables && make book

clean:
	rm -rf results/*
	cd book && make clean-all

# Format code
format:
	uv run black .
	uv run ruff check --fix .

# Lint code
lint:
	uv run black --check .
	uv run ruff check .
	uv run mypy . --ignore-missing-imports

test:
	uv run python -m pytest tests/

# Help
help:
	@echo "Simulation commands:"
	@echo "  install               - Install dependencies with uv"
	@echo "  run-simulation        - Run standard simulation"
	@echo "  test-simulation       - Run quick test simulation"
	@echo "  run-simple-regression - Run enhanced regression analysis"
	@echo ""
	@echo "JupyterBook commands:"
	@echo "  book                  - Build the JupyterBook"
	@echo "  book-serve            - Serve book locally"
	@echo "  book-pdf              - Generate PDF"
	@echo "  book-test             - Run test pipeline with book"
	@echo ""
	@echo "Development commands:"
	@echo "  format                - Format code with black and ruff"
	@echo "  lint                  - Run linters"
	@echo ""
	@echo "  clean                 - Clean all generated files"

# ---- Paper (Overleaf mirror in manuscript/, frozen inputs in paper_inputs/) ----
PY ?= uv run python
OVERLEAF ?= https://git.overleaf.com/6818d868a5b36406065db49b
GS_TABLES = gs_eti_regression_taxable_spline.tex gs_eti_regression_broad_spline.tex \
	gs_table9_income_group_all_models_cpi2026.tex gs_summary_statistics.tex=summary_statistics.tex

paper-tables:  ## regenerate paper tables from paper_inputs/ into build/paper-tables
	rm -rf build/paper-tables && mkdir -p build/paper-tables
	LLM_ETI_GS_DATA_DIR=paper_inputs/gs LLM_ETI_GS_OUT_DIR=build/paper-tables \
		$(PY) book/scripts/make_gs_eti_results_tables.py

check-paper: paper-tables  ## inputs unchanged and manuscript numbers match regeneration
	cd paper_inputs/gs && shasum -a 256 -c SHA256SUMS
	$(PY) scripts/check_paper_tables.py build/paper-tables manuscript/images_tables $(GS_TABLES)

paper-pull:  ## bring Overleaf edits into manuscript/
	git subtree pull --prefix=manuscript $(OVERLEAF) main --squash

paper-push:  ## send repo-side manuscript changes (regenerated tables) to Overleaf
	git subtree push --prefix=manuscript $(OVERLEAF) main
