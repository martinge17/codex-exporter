.PHONY: install-dev format lint test coverage check

PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin

install-dev:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip
	$(BIN)/python -m pip install --no-cache-dir -r requirements-dev.txt

format:
	$(BIN)/ruff format .
	$(BIN)/ruff check . --fix

lint:
	$(BIN)/ruff format --check .
	$(BIN)/ruff check .

test:
	$(BIN)/python -m pytest

coverage:
	$(BIN)/coverage run -m pytest
	$(BIN)/coverage report --fail-under=85
	$(BIN)/coverage xml -o coverage.xml

check: lint coverage
	git diff --check
