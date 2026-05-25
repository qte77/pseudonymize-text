TERMS_FILE ?= tests/fixtures/terms.csv

.PHONY: help setup test lint lint_terms format check_links check clean

help:
	@echo 'Targets:'
	@echo '  setup        Install runtime + dev + ner deps via uv'
	@echo '  test         Run pytest'
	@echo '  lint         Run ruff check + markdownlint'
	@echo '  lint_terms   Validate $$(TERMS_FILE) for ReDoS / broad-pattern violations'
	@echo '  format       Run ruff format'
	@echo '  check_links  Run lychee against README and docs/'
	@echo '  check        lint + test'
	@echo '  clean        Remove build and cache artifacts'

setup:
	uv sync --all-extras

test:
	uv run pytest

lint:
	uv run ruff check .
	markdownlint README.md docs/

lint_terms:
	uv run python -m pseudonymize_text.lint_terms $(TERMS_FILE)

format:
	uv run ruff format .

check_links:
	lychee README.md docs/

check: lint test

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
