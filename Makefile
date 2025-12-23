# ==============================================================================
# File: Makefile
# Date: 2025-12-19
# Purpose:
#   Convenience targets for the document analysis project.
# ======================================================================

ARTIFACTS_DIR ?= ./epstein_artifacts
VECTOR_DIR ?= ./vector-stack
PY ?= uv run python

.PHONY: help
help:
	@echo "Targets:"
	@echo "  bootstrap      - run Ubuntu bootstrap (creates uv env + lock + docs)"
	@echo "  pipeline-init  - write starter config.json"
	@echo "  pipeline-run   - run OCR/chunk/NER pipeline"
	@echo "  vectordb-up    - start Qdrant + Postgres stack"
	@echo "  vectordb-down  - stop stack"
	@echo "  db-load        - load artifacts into Postgres (requires DSN)"
	@echo "  status         - show stack status"

.PHONY: bootstrap
bootstrap:
	chmod +x scripts/cbw_bootstrap_project_ubuntu.sh scripts/vector_db_bootstrap.sh
	./scripts/cbw_bootstrap_project_ubuntu.sh

.PHONY: pipeline-init
pipeline-init:
	$(PY) epstein/epstein_files_pipeline.py init-config --out ./config.json

.PHONY: pipeline-run
pipeline-run:
	$(PY) epstein_files_pipeline.py run --config ./config.json

.PHONY: vectordb-up
vectordb-up:
	chmod +x scripts/vector_db_bootstrap.sh
	./scripts/vector_db_bootstrap.sh --dir $(VECTOR_DIR) up

.PHONY: vectordb-down
vectordb-down:
	chmod +x scripts/vector_db_bootstrap.sh
	./scripts/vector_db_bootstrap.sh --dir $(VECTOR_DIR) down

.PHONY: status
status:
	./scripts/vector_db_bootstrap.sh --dir $(VECTOR_DIR) status

.PHONY: doctor
doctor:
	@python3 scripts/doctor.py --check-db || true

.PHONY: doctor-check
doctor-check:
	@python3 scripts/doctor.py --check-db

.PHONY: lint
lint:
	@uv run ruff check . || true
	@uv run mypy epstein || true

.PHONY: db-load
db-load:
	@if [ -z "$$DSN" ]; then echo "Set DSN=postgresql://user:pass@localhost:5432/analysis"; exit 2; fi
	$(PY) db_ingest_artifacts.py --artifacts-dir $(ARTIFACTS_DIR) --dsn "$$DSN"
