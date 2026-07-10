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
	$(UV) run black .
	$(UV) run ruff check --fix .

lint:
	$(UV) run black --check .
	$(UV) run ruff check .
	$(UV) run mypy . --ignore-missing-imports

site: artifacts
	$(PYTHON) scripts/render_publication.py

check:
	$(PYTHON) scripts/check_publication.py

publication: artifacts test lint site check

serve: site
	$(PYTHON) -m http.server 8000 --directory _site

clean:
	rm -rf _site .coverage htmlcov
