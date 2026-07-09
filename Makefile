.PHONY: install artifacts test format lint site publication check clean serve

UV := uv
PYTHON := $(UV) run python

install:
	$(UV) sync --python 3.13 --group dev --frozen

artifacts:
	$(PYTHON) scripts/generate_artifacts.py

test:
	$(UV) run pytest --cov=llm_eti --cov-report=term-missing

format:
	$(UV) run black llm_eti scripts tests
	$(UV) run ruff check --fix llm_eti scripts tests

lint:
	$(UV) run black --check llm_eti scripts tests
	$(UV) run ruff check llm_eti scripts tests
	$(UV) run mypy llm_eti scripts tests --ignore-missing-imports

site: artifacts
	$(PYTHON) scripts/render_publication.py

check:
	$(PYTHON) scripts/check_publication.py

publication: artifacts test lint site check

serve: site
	$(PYTHON) -m http.server 8000 --directory _site

clean:
	rm -rf _site .coverage htmlcov
