.PHONY: help venv install install-dev lint typecheck test fmt up down psql

help:
	@echo "Targets:"
	@echo "  venv         Create venv in .venv"
	@echo "  install      Install runtime deps"
	@echo "  install-dev  Install runtime + dev deps"
	@echo "  fmt          Auto-fix formatting (ruff)"
	@echo "  lint         Lint (ruff)"
	@echo "  typecheck    mypy type checking"
	@echo "  test         Run pytest"
	@echo "  up           Start postgres via docker compose"
	@echo "  down         Stop postgres"
	@echo "  psql         Open psql shell (requires psql client)"

venv:
	python3 -m venv .venv

install:
	. .venv/bin/activate && pip install -U pip && pip install .

install-dev:
	. .venv/bin/activate && pip install -U pip && pip install ".[dev]"

fmt:
	. .venv/bin/activate && ruff check --fix .

lint:
	. .venv/bin/activate && ruff check .

typecheck:
	. .venv/bin/activate && mypy src

test:
	. .venv/bin/activate && pytest -q

up:
	docker compose -f ops/docker-compose.yml up -d

down:
	docker compose -f ops/docker-compose.yml down

psql:
	@echo "Example: PGPASSWORD=$$OPENDISCOURSE_DB_PASSWORD psql -h 127.0.0.1 -p 5432 -U $$OPENDISCOURSE_DB_USER -d $$OPENDISCOURSE_DB_NAME"
