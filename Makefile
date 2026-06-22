TERMS_FILE ?= tests/fixtures/terms.csv

.PHONY: help setup test lint lint_terms format check_links check changelog_new changelog_preview changelog_release clean

help:
	@echo 'Targets:'
	@echo '  setup              Install runtime + dev + ner deps via uv'
	@echo '  test               Run pytest'
	@echo '  lint               Run ruff check + markdownlint'
	@echo '  lint_terms         Validate $$(TERMS_FILE) for ReDoS / broad-pattern violations'
	@echo '  format             Run ruff format'
	@echo '  check_links        Run lychee against README and docs/'
	@echo '  check              lint + test'
	@echo '  changelog_new      Add a changelog fragment under changelog.d/'
	@echo '  changelog_preview  Preview the assembled release entry (no consume)'
	@echo '  changelog_release  Collect fragments into CHANGELOG.md (VERSION=X.Y.Z)'
	@echo '  clean              Remove build, cache, and runs/ sandbox artefacts'

setup:
	uv sync --all-extras

test:
	uv run pytest --cov=src/pseudonymize_text --cov-fail-under=80

lint:
	uv run ruff check --no-cache .
	markdownlint README.md CONTRIBUTING.md AGENTS.md CHANGELOG.md docs/

lint_terms:
	uv run python -m pseudonymize_text.lint_terms $(TERMS_FILE)

format:
	uv run ruff format .

check_links:
	lychee README.md docs/

check: lint test

changelog_new:
	uv run scriv create --add

changelog_preview:
	uv run scriv print

changelog_release:
	test -n "$(VERSION)" || (echo "VERSION required, e.g. make changelog_release VERSION=0.3.0"; exit 2)
	uv run scriv collect --version $(VERSION)

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache htmlcov .coverage runs
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
