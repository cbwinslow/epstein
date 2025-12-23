#!/usr/bin/env bash
# ==============================================================================
# Script Name: vector_db_bootstrap.sh
# Date: 2025-12-19
# Author: ChatGPT (for Blaine Winslow / cbwinslow)
# Summary:
#   Bootstraps a local analysis data stack using Docker Compose:
#     - Qdrant (vector DB)        [default: enabled]
#     - Postgres + pgvector       [default: enabled]
#     - Opinionated schema for findings (documents/chunks/entities/runs)
#
#   Security-first defaults:
#     - Services bind to 127.0.0.1 by default
#     - Use --bind-all ONLY if you understand the exposure risk
#
# Usage:
#   chmod +x vector_db_bootstrap.sh
#   ./vector_db_bootstrap.sh up
#   ./vector_db_bootstrap.sh status
#   ./vector_db_bootstrap.sh down
#
# Common:
#   ./vector_db_bootstrap.sh --dir ./vector-stack up
#   ./vector_db_bootstrap.sh --enable-postgres false up
#   ./vector_db_bootstrap.sh --bind-all up
#
# Inputs:
#   --dir PATH                   Stack directory (default: ./vector-stack)
#   --enable-postgres true|false (default: true)
#   --enable-qdrant true|false   (default: true)
#   --bind-all                   Bind ports to 0.0.0.0 (DANGEROUS)
#   --qdrant-port 6333
#   --qdrant-grpc-port 6334
#   --pg-port 5432
#   --pg-db analysis
#   --pg-user analysis
#   --pg-pass PASS               If omitted, auto-generated and stored in .env
#   --verbose
#   --dry-run
#
# Outputs (in --dir):
#   - docker-compose.yml
#   - .env
#   - initdb/00_pgvector.sql
#   - initdb/01_schema.sql
#
# Modification Log:
#   - 2025-12-19: v2 adds schema + optional toggles + safer defaults
# ==============================================================================

set -Eeuo pipefail

SCRIPT_NAME="vector_db_bootstrap"
LOG_FILE="/tmp/CBW-${SCRIPT_NAME}.log"

STACK_DIR="./vector-stack"
ENABLE_POSTGRES="true"
ENABLE_QDRANT="true"
BIND_ADDR="127.0.0.1"

QDRANT_PORT="6333"
QDRANT_GRPC_PORT="6334"
PG_PORT="5432"
PG_DB="analysis"
PG_USER="analysis"
PG_PASS=""

VERBOSE="false"
DRY_RUN="false"

log(){ echo "$(date '+%Y-%m-%d %H:%M:%S') [$1] $*" | tee -a "${LOG_FILE}" >/dev/null; }
info(){ log INFO "$@"; }
warn(){ log WARN "$@"; }
err(){ log ERROR "$@"; }

run(){
  if [[ "${DRY_RUN}" == "true" ]]; then
    info "[dry-run] $*"
    return 0
  fi
  [[ "${VERBOSE}" == "true" ]] && info "$*"
  eval "$@"
}

have(){ command -v "$1" >/dev/null 2>&1; }

ausage(){
  cat <<'USAGE'
vector_db_bootstrap.sh [options] <command>

Commands:
  up | down | restart | status | logs | config

Options:
  --dir PATH
  --enable-postgres true|false
  --enable-qdrant true|false
  --bind-all
  --qdrant-port 6333
  --qdrant-grpc-port 6334
  --pg-port 5432
  --pg-db NAME
  --pg-user USER
  --pg-pass PASS
  --verbose
  --dry-run
  -h, --help
USAGE
}

CMD=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    up|down|restart|status|logs|config) CMD="$1"; shift;;
    --dir) STACK_DIR="$2"; shift 2;;
    --enable-postgres) ENABLE_POSTGRES="$2"; shift 2;;
    --enable-qdrant) ENABLE_QDRANT="$2"; shift 2;;
    --bind-all) BIND_ADDR="0.0.0.0"; shift;;
    --qdrant-port) QDRANT_PORT="$2"; shift 2;;
    --qdrant-grpc-port) QDRANT_GRPC_PORT="$2"; shift 2;;
    --pg-port) PG_PORT="$2"; shift 2;;
    --pg-db) PG_DB="$2"; shift 2;;
    --pg-user) PG_USER="$2"; shift 2;;
    --pg-pass) PG_PASS="$2"; shift 2;;
    --verbose) VERBOSE="true"; shift;;
    --dry-run) DRY_RUN="true"; shift;;
    -h|--help) ausage; exit 0;;
    *) err "Unknown arg: $1"; ausage; exit 2;;
  esac
done

[[ -z "${CMD}" ]] && { err "Missing command"; ausage; exit 2; }

STACK_DIR="$(python3 - <<PY
import os
print(os.path.abspath(os.path.expanduser("${STACK_DIR}")))
PY
)"

info "Log: ${LOG_FILE}"
info "Stack dir: ${STACK_DIR}"
info "Bind address: ${BIND_ADDR}"
info "Enable Qdrant: ${ENABLE_QDRANT}"
info "Enable Postgres: ${ENABLE_POSTGRES}"

if ! have docker; then
  err "docker not found. Install Docker Engine + Compose plugin first."
  exit 1
fi

COMPOSE=""
if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif have docker-compose; then
  COMPOSE="docker-compose"
else
  err "docker compose not available. Install Docker Compose plugin."
  exit 1
fi

run "mkdir -p '${STACK_DIR}/initdb'"

ENV_FILE="${STACK_DIR}/.env"
COMPOSE_FILE="${STACK_DIR}/docker-compose.yml"

if [[ -z "${PG_PASS}" ]]; then
  if [[ -f "${ENV_FILE}" ]] && grep -q '^POSTGRES_PASSWORD=' "${ENV_FILE}"; then
    PG_PASS="$(grep '^POSTGRES_PASSWORD=' "${ENV_FILE}" | head -n1 | cut -d'=' -f2-)"
  else
    PG_PASS="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
)"
  fi
fi

# Write .env (idempotent)
run "cat > '${ENV_FILE}' <<EOF
BIND_ADDR=${BIND_ADDR}
ENABLE_QDRANT=${ENABLE_QDRANT}
QDRANT_PORT=${QDRANT_PORT}
QDRANT_GRPC_PORT=${QDRANT_GRPC_PORT}
ENABLE_POSTGRES=${ENABLE_POSTGRES}
POSTGRES_PORT=${PG_PORT}
POSTGRES_DB=${PG_DB}
POSTGRES_USER=${PG_USER}
POSTGRES_PASSWORD=${PG_PASS}
EOF"

# Init SQL: pgvector + schema
if [[ "${ENABLE_POSTGRES}" == "true" ]]; then
  run "cat > '${STACK_DIR}/initdb/00_pgvector.sql' <<'EOF'
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
EOF"

  # Opinionated schema for findings (idempotent)
  run "cat > '${STACK_DIR}/initdb/01_schema.sql' <<'EOF'
-- =========================================================
-- Schema: doc_analysis
-- Purpose:
--   Store provenance-rich outputs from epstein_files_pipeline.py
--   and any follow-on analysis.
-- =========================================================

CREATE SCHEMA IF NOT EXISTS doc_analysis;

-- Documents (one row per unique file: doc_id = sha256 of bytes)
CREATE TABLE IF NOT EXISTS doc_analysis.documents (
  doc_id            TEXT PRIMARY KEY,
  source_url        TEXT NOT NULL,
  original_path     TEXT,
  ocr_path          TEXT,
  bytes             BIGINT,
  sha256            TEXT NOT NULL,
  downloaded_at     TIMESTAMPTZ,
  meta              JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS documents_source_url_idx ON doc_analysis.documents (source_url);

-- Runs (one row per pipeline run)
CREATE TABLE IF NOT EXISTS doc_analysis.runs (
  run_id            TEXT PRIMARY KEY,
  config_hash       TEXT,
  ts_start          TIMESTAMPTZ,
  ts_end            TIMESTAMPTZ,
  status            TEXT,
  counts            JSONB DEFAULT '{}'::jsonb,
  seed_urls         JSONB DEFAULT '[]'::jsonb
);

-- Failures (append-only diagnostics)
CREATE TABLE IF NOT EXISTS doc_analysis.failures (
  id                BIGSERIAL PRIMARY KEY,
  run_id            TEXT,
  stage             TEXT,
  doc_id            TEXT,
  url               TEXT,
  error             TEXT,
  ts                TIMESTAMPTZ,
  details           JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS failures_run_stage_idx ON doc_analysis.failures (run_id, stage);

-- Extracted document text (one row per doc)
CREATE TABLE IF NOT EXISTS doc_analysis.document_text (
  doc_id            TEXT PRIMARY KEY REFERENCES doc_analysis.documents(doc_id) ON DELETE CASCADE,
  text              TEXT NOT NULL,
  redacted          BOOLEAN DEFAULT TRUE,
  extracted_at      TIMESTAMPTZ,
  meta              JSONB DEFAULT '{}'::jsonb
);

-- Chunks (one row per chunk)
CREATE TABLE IF NOT EXISTS doc_analysis.chunks (
  doc_id            TEXT NOT NULL REFERENCES doc_analysis.documents(doc_id) ON DELETE CASCADE,
  chunk_id          INT  NOT NULL,
  char_start        INT  NOT NULL,
  char_end          INT  NOT NULL,
  preview           TEXT,
  text              TEXT NOT NULL,
  source_url        TEXT,
  PRIMARY KEY (doc_id, chunk_id)
);
CREATE INDEX IF NOT EXISTS chunks_doc_idx ON doc_analysis.chunks (doc_id);

-- Entity mentions (one row per mention)
CREATE TABLE IF NOT EXISTS doc_analysis.entities (
  id                BIGSERIAL PRIMARY KEY,
  doc_id            TEXT NOT NULL REFERENCES doc_analysis.documents(doc_id) ON DELETE CASCADE,
  chunk_id          INT  NOT NULL,
  label             TEXT NOT NULL,
  text              TEXT NOT NULL,
  char_start        INT,
  char_end          INT,
  source_url        TEXT,
  pdf_path          TEXT
);
CREATE INDEX IF NOT EXISTS entities_doc_label_idx ON doc_analysis.entities (doc_id, label);
CREATE INDEX IF NOT EXISTS entities_text_idx ON doc_analysis.entities (text);

-- Optional: embeddings (if you later embed chunks into pgvector)
CREATE TABLE IF NOT EXISTS doc_analysis.chunk_embeddings (
  doc_id            TEXT NOT NULL,
  chunk_id          INT  NOT NULL,
  model             TEXT NOT NULL,
  dim               INT  NOT NULL,
  embedding         vector,
  created_at        TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (doc_id, chunk_id, model)
);

EOF"
fi

# Compose file (bind ports to ${BIND_ADDR} by default)
run "cat > '${COMPOSE_FILE}' <<'EOF'
services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    restart: unless-stopped
    profiles: ["qdrant"]
    ports:
      - "${BIND_ADDR}:${QDRANT_PORT}:6333"
      - "${BIND_ADDR}:${QDRANT_GRPC_PORT}:6334"
    volumes:
      - qdrant_storage:/qdrant/storage

  postgres:
    image: pgvector/pgvector:pg16
    container_name: pgvector_postgres
    restart: unless-stopped
    profiles: ["postgres"]
    environment:
      POSTGRES_DB: "${POSTGRES_DB}"
      POSTGRES_USER: "${POSTGRES_USER}"
      POSTGRES_PASSWORD: "${POSTGRES_PASSWORD}"
    ports:
      - "${BIND_ADDR}:${POSTGRES_PORT}:5432"
    volumes:
      - pg_storage:/var/lib/postgresql/data
      - ./initdb:/docker-entrypoint-initdb.d:ro

volumes:
  qdrant_storage:
  pg_storage:
EOF"

compose_args=("-f" "${COMPOSE_FILE}" "--env-file" "${ENV_FILE}")

compose_up(){
  local profiles=()
  [[ "${ENABLE_QDRANT}" == "true" ]] && profiles+=("--profile" "qdrant")
  [[ "${ENABLE_POSTGRES}" == "true" ]] && profiles+=("--profile" "postgres")
  run "${COMPOSE} ${compose_args[*]} ${profiles[*]} up -d"
}

case "${CMD}" in
  config)  run "${COMPOSE} ${compose_args[*]} config";;
  up)
    compose_up
    [[ "${ENABLE_QDRANT}" == "true" ]] && info "Qdrant: http://localhost:${QDRANT_PORT}"
    if [[ "${ENABLE_POSTGRES}" == "true" ]]; then
      info "Postgres DSN: postgresql://${PG_USER}:<hidden>@localhost:${PG_PORT}/${PG_DB}"
      info "Schema: doc_analysis.*"
    fi
    ;;
  down)    run "${COMPOSE} ${compose_args[*]} down";;
  restart) run "${COMPOSE} ${compose_args[*]} restart";;
  status)  run "${COMPOSE} ${compose_args[*]} ps";;
  logs)    run "${COMPOSE} ${compose_args[*]} logs -f --tail=200";;
  *) err "Unknown command: ${CMD}"; exit 2;;
esac

info "Done."
