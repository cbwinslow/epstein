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
	@echo "Running lint and type checks..."
	@uv run ruff check .
	@uv run mypy . || true

.PHONY: verify-bundles
verify-bundles:
	@bash scripts/verify_bundle.sh

.PHONY: collect-task-logs
collect-task-logs:
	@python scripts/collect_task_logs.py

.PHONY: test
test:
	@echo "Running multi-agent system tests with OpenTelemetry..."
	@python tests/run_tests.py

.PHONY: test-unit
test-unit:
	@echo "Running unit tests..."
	@pytest tests/test_agents.py -v

.PHONY: test-integration
test-integration:
	@echo "Running integration tests..."
	@pytest tests/test_integration.py -v

.PHONY: format
format:
	@echo "Formatting code (black / isort / ruff --fix)"
	@uv run ruff --fix . || true
	@uv run isort --profile black . || true
	@uv run black --line-length 100 . || true

.PHONY: check-lock
check-lock:
	@echo "Verifying uv.lock exists"
	@test -f uv.lock || (echo "uv.lock is missing. Run 'uv lock' and commit it." && exit 1)

.PHONY: test-coverage
test-coverage:
	@echo "Running tests with coverage..."
	@pytest tests/ --cov=agents --cov=tools --cov-report=html --cov-report=term-missing

.PHONY: test-watch
test-watch:
	@echo "Running tests in watch mode..."
	@pytest-watch tests/ -v

.PHONY: install-test-deps
install-test-deps:
	@echo "Installing test dependencies..."
	@pip install -r tests/requirements.txt
