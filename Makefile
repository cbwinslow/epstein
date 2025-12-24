ARTIFACTS_DIR ?= ./epstein_artifacts
VECTOR_DIR ?= ./vector-stack
CONFIG ?= ./config.json

COMPOSE ?= docker compose
COMPOSE_FILE ?= compose.yml

.PHONY: help
help:
	@echo "Targets: bootstrap down status doctor lint pipeline-init pipeline-run db-load"

.PHONY: doctor
doctor:
	@$(COMPOSE) version >/dev/null
	@docker version >/dev/null
	@echo "Docker OK."

.PHONY: bootstrap
bootstrap:
	@chmod +x ./vector_db_bootstrap.sh
	@./vector_db_bootstrap.sh --dir $(VECTOR_DIR) up
	@$(COMPOSE) -f $(COMPOSE_FILE) up -d qdrant postgres

.PHONY: down
down:
	@$(COMPOSE) -f $(COMPOSE_FILE) down

.PHONY: status
status:
	@$(COMPOSE) -f $(COMPOSE_FILE) ps

.PHONY: pipeline-init
pipeline-init:
	@$(COMPOSE) -f $(COMPOSE_FILE) --profile pipeline run --rm pipeline epstein_files_pipeline.py init-config --out $(CONFIG)

.PHONY: pipeline-run
pipeline-run:
	@$(COMPOSE) -f $(COMPOSE_FILE) --profile pipeline run --rm pipeline epstein_files_pipeline.py run --config $(CONFIG)

.PHONY: db-load
db-load:
	@$(COMPOSE) -f $(COMPOSE_FILE) --profile pipeline run --rm \
	  -e EPSTEIN_DSN="$${EPSTEIN_DSN:-postgresql://analysis:analysis@postgres:5432/analysis}" \
	  pipeline db_ingest_artifacts.py --artifacts-dir $(ARTIFACTS_DIR) --dsn "$${EPSTEIN_DSN:-postgresql://analysis:analysis@postgres:5432/analysis}"

.PHONY: lint
lint:
	@$(COMPOSE) -f $(COMPOSE_FILE) --profile pipeline run --rm pipeline -m ruff check .
	@$(COMPOSE) -f $(COMPOSE_FILE) --profile pipeline run --rm pipeline -m mypy epstein_files_pipeline.py db_ingest_artifacts.py || true

.PHONY: verify-bundles
verify-bundles:
	@bash scripts/verify_bundle.sh
