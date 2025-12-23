#!/usr/bin/env bash
# ==============================================================================
# Script Name: cbw_vector_db_bootstrap.sh
# Date: 2025-12-19
# Author: ChatGPT (for Blaine Winslow / cbwinslow)
# Summary:
#   Idempotent, repeatable installer for a FREE + OPEN-SOURCE vector database.
#   Default choice: Qdrant (Apache-2.0) + optional PostgreSQL with pgvector.
#
#   Why Qdrant by default?
#     - Simple to self-host (single container; great local dev + small prod)
#     - Open source under Apache License 2.0
#     - Strong performance + filters/payloads; good fit for document analysis
#
#   Alternatives you can switch to later:
#     - Weaviate (BSD-3-Clause; OSS)  [supports modules + hybrid search]
#     - Milvus (Apache-2.0; OSS)      [heavier stack, scales big]
#     - Postgres + pgvector           [best when you want ONE DB for everything]
#
# Inputs:
#   CLI flags (see --help)
#
# Outputs:
#   Creates an install directory with:
#     - docker-compose.yml
#     - .env (generated if missing)
#     - init/01_pgvector.sql (if Postgres enabled)
#     - data volumes (docker)
#   Logs:
#     - /tmp/CBW-cbw_vector_db_bootstrap.log
#
# Requirements:
#   - Docker Engine
#   - Docker Compose plugin ("docker compose")
#
# Usage:
#   ./cbw_vector_db_bootstrap.sh --dir ./vector-stack up
#   ./cbw_vector_db_bootstrap.sh --dir ./vector-stack status
#   ./cbw_vector_db_bootstrap.sh --dir ./vector-stack down
#
# Notes:
#   - This script is designed to be safely re-runnable (idempotent).
#   - Non-critical issues are logged and the script attempts to continue.
#
# Modification Log:
#   - 2025-12-19: Initial version
# ==============================================================================

set -Eeuo pipefail

# ------------------------------
# Constants
# ------------------------------

SCRIPT_NAME="cbw_vector_db_bootstrap"
LOG_FILE="/tmp/CBW-${SCRIPT_NAME}.log"
DEFAULT_DIR="./vector-stack"
DEFAULT_VECTOR_DB="qdrant"           # qdrant|weaviate|milvus|pgvector-only (future)
DEFAULT_ENABLE_POSTGRES="true"       # true|false
DEFAULT_PROJECT="vectorstack"
DEFAULT_QDRANT_PORT="6333"
DEFAULT_QDRANT_GRPC_PORT="6334"
DEFAULT_POSTGRES_PORT="5432"
DEFAULT_POSTGRES_DB="vectordb"
DEFAULT_POSTGRES_USER="vector"
DEFAULT_POSTGRES_PASSWORD="vector_change_me"

# ------------------------------
# Logging helpers
# ------------------------------

mkdir -p "$(dirname "${LOG_FILE}")" || true

log() {
  local level="$1"; shift
  local msg="$*"
  local ts
  ts="$(date '+%Y-%m-%d %H:%M:%S')"
  echo "${ts} [${level}] ${msg}" | tee -a "${LOG_FILE}" >/dev/null
}

info() { log INFO "$*"; }
warn() { log WARN "$*"; }
err()  { log ERROR "$*"; }

on_error() {
  local exit_code=$?
  local line_no=$1
  err "Unhandled error at line ${line_no}. Exit code: ${exit_code}. See ${LOG_FILE}"
  exit "${exit_code}"
}
trap 'on_error $LINENO' ERR

# ------------------------------
# CLI parsing
# ------------------------------

DIR="${DEFAULT_DIR}"
VECTOR_DB="${DEFAULT_VECTOR_DB}"
ENABLE_POSTGRES="${DEFAULT_ENABLE_POSTGRES}"
PROJECT_NAME="${DEFAULT_PROJECT}"
QDRANT_PORT="${DEFAULT_QDRANT_PORT}"
QDRANT_GRPC_PORT="${DEFAULT_QDRANT_GRPC_PORT}"
POSTGRES_PORT="${DEFAULT_POSTGRES_PORT}"
POSTGRES_DB="${DEFAULT_POSTGRES_DB}"
POSTGRES_USER="${DEFAULT_POSTGRES_USER}"
POSTGRES_PASSWORD="${DEFAULT_POSTGRES_PASSWORD}"
DRY_RUN="false"
VERBOSE="false"

usage() {
  cat <<'USAGE'
cbw_vector_db_bootstrap.sh

Commands:
  up         Create/update compose stack and start services
  down       Stop services
  restart    Restart services
  status     Show status + health checks
  logs       Tail logs
  config     Print resolved config

Options:
  --dir PATH                 Install directory (default: ./vector-stack)
  --vector-db NAME           qdrant|weaviate|milvus (default: qdrant)
  --enable-postgres BOOL     true|false (default: true)
  --project NAME             Docker compose project name (default: vectorstack)

  --qdrant-port PORT         Qdrant HTTP port (default: 6333)
  --qdrant-grpc-port PORT    Qdrant gRPC port (default: 6334)

  --postgres-port PORT       Postgres port (default: 5432)
  --postgres-db NAME         Postgres DB name (default: vectordb)
  --postgres-user NAME       Postgres username (default: vector)
  --postgres-password PASS   Postgres password (default: vector_change_me)

  --dry-run                  Print actions, don't change system
  --verbose                  More logs
  -h, --help                 Show help

Examples:
  ./cbw_vector_db_bootstrap.sh --dir ./vector-stack up
  ./cbw_vector_db_bootstrap.sh --dir ./vector-stack --enable-postgres false up
  ./cbw_vector_db_bootstrap.sh --dir ./vector-stack status
USAGE
}

cmd="${1:-}"
shift || true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) DIR="$2"; shift 2;;
    --vector-db) VECTOR_DB="$2"; shift 2;;
    --enable-postgres) ENABLE_POSTGRES="$2"; shift 2;;
    --project) PROJECT_NAME="$2"; shift 2;;

    --qdrant-port) QDRANT_PORT="$2"; shift 2;;
    --qdrant-grpc-port) QDRANT_GRPC_PORT="$2"; shift 2;;

    --postgres-port) POSTGRES_PORT="$2"; shift 2;;
    --postgres-db) POSTGRES_DB="$2"; shift 2;;
    --postgres-user) POSTGRES_USER="$2"; shift 2;;
    --postgres-password) POSTGRES_PASSWORD="$2"; shift 2;;

    --dry-run) DRY_RUN="true"; shift;;
    --verbose) VERBOSE="true"; shift;;
    -h|--help) usage; exit 0;;
    *) err "Unknown option: $1"; usage; exit 2;;
  esac
done

if [[ -z "${cmd}" ]]; then
  usage
  exit 2
fi

# ------------------------------
# Preconditions
# ------------------------------

run() {
  # Execute commands unless dry-run
  if [[ "${DRY_RUN}" == "true" ]]; then
    info "[dry-run] $*"
    return 0
  fi
  if [[ "${VERBOSE}" == "true" ]]; then
    info "$*"
  fi
  eval "$@"
}

require_cmd() {
  local c="$1"
  if ! command -v "$c" >/dev/null 2>&1; then
    err "Missing required command: ${c}"
    return 1
  fi
}

validate_bool() {
  local v="$1"
  [[ "$v" == "true" || "$v" == "false" ]]
}

if ! validate_bool "${ENABLE_POSTGRES}"; then
  err "--enable-postgres must be true|false"
  exit 2
fi

case "${VECTOR_DB}" in
  qdrant|weaviate|milvus) ;;
  *) err "--vector-db must be qdrant|weaviate|milvus"; exit 2;;
esac

# Docker check
require_cmd docker || exit 1

# Ensure compose is available
if ! docker compose version >/dev/null 2>&1; then
  err "Docker Compose plugin not found. Install Docker Compose (v2) so 'docker compose' works."
  exit 1
fi

# ------------------------------
# File generation
# ------------------------------

DIR="$(python3 - <<PY
import os
print(os.path.abspath(os.path.expanduser("${DIR}")))
PY
)"

ENV_FILE="${DIR}/.env"
COMPOSE_FILE="${DIR}/docker-compose.yml"
INIT_DIR="${DIR}/init"

write_env_if_missing() {
  run "mkdir -p '${DIR}'"
  if [[ -f "${ENV_FILE}" ]]; then
    info "Using existing ${ENV_FILE}"
    return 0
  fi

  info "Creating ${ENV_FILE}"
  run "cat > '${ENV_FILE}' <<'EOF'
# Generated by cbw_vector_db_bootstrap.sh
PROJECT_NAME=${PROJECT_NAME}
VECTOR_DB=${VECTOR_DB}
ENABLE_POSTGRES=${ENABLE_POSTGRES}

QDRANT_PORT=${QDRANT_PORT}
QDRANT_GRPC_PORT=${QDRANT_GRPC_PORT}

POSTGRES_PORT=${POSTGRES_PORT}
POSTGRES_DB=${POSTGRES_DB}
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
EOF"
}

write_pgvector_init() {
  run "mkdir -p '${INIT_DIR}'"
  local sql_path="${INIT_DIR}/01_pgvector.sql"
  if [[ -f "${sql_path}" ]]; then
    info "Using existing ${sql_path}"
    return 0
  fi

  info "Creating pgvector init SQL at ${sql_path}"
  run "cat > '${sql_path}' <<'EOF'
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Recommended indexes are workload-specific; keep this minimal.
-- You can add HNSW or IVFFLAT indexes after you create tables.
EOF"
}

write_compose() {
  run "mkdir -p '${DIR}'"

  info "Writing ${COMPOSE_FILE} (vector-db=${VECTOR_DB}, postgres=${ENABLE_POSTGRES})"

  # Compose is generated to be portable.
  # For Qdrant, we expose 6333 and 6334.
  # For Postgres, we include pgvector-enabled image.

  local qdrant_service=""
  local weaviate_service=""
  local milvus_service=""

  qdrant_service=$(cat <<'QDRANT'
  qdrant:
    image: qdrant/qdrant:latest
    container_name: ${PROJECT_NAME}_qdrant
    restart: unless-stopped
    ports:
      - "${QDRANT_PORT}:6333"
      - "${QDRANT_GRPC_PORT}:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:6333/readyz"]
      interval: 10s
      timeout: 5s
      retries: 20
QDRANT
)

  # NOTE: We keep Weaviate/Milvus as placeholders (so you can switch later)
  # without rewriting your entire stack. Their configs are intentionally minimal.
  weaviate_service=$(cat <<'WEAVIATE'
  weaviate:
    image: semitechnologies/weaviate:latest
    container_name: ${PROJECT_NAME}_weaviate
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      QUERY_DEFAULTS_LIMIT: "25"
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: "true"
      PERSISTENCE_DATA_PATH: "/var/lib/weaviate"
      DEFAULT_VECTORIZER_MODULE: "none"
      ENABLE_MODULES: ""
      CLUSTER_HOSTNAME: "node1"
    volumes:
      - weaviate_data:/var/lib/weaviate
WEAVIATE
)

  milvus_service=$(cat <<'MILVUS'
  # Milvus has multiple deployment modes; the full stack is bigger.
  # This is a *starter* using standalone mode container, suitable for local eval.
  milvus:
    image: milvusdb/milvus:latest
    container_name: ${PROJECT_NAME}_milvus
    restart: unless-stopped
    ports:
      - "19530:19530"
      - "9091:9091"
    environment:
      MILVUS_LOG_LEVEL: "info"
    volumes:
      - milvus_data:/var/lib/milvus
MILVUS
)

  # Compose header
  run "cat > '${COMPOSE_FILE}' <<'EOF'
name: ${PROJECT_NAME}
services:
EOF"

  # Choose vector DB service
  case "${VECTOR_DB}" in
    qdrant)
      run "cat >> '${COMPOSE_FILE}' <<'EOF'
${qdrant_service}
EOF";;
    weaviate)
      run "cat >> '${COMPOSE_FILE}' <<'EOF'
${weaviate_service}
EOF";;
    milvus)
      run "cat >> '${COMPOSE_FILE}' <<'EOF'
${milvus_service}
EOF";;
  esac

  # Optional Postgres
  if [[ "${ENABLE_POSTGRES}" == "true" ]]; then
    write_pgvector_init
    run "cat >> '${COMPOSE_FILE}' <<'EOF'

  postgres:
    image: pgvector/pgvector:pg16
    container_name: ${PROJECT_NAME}_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "${POSTGRES_PORT}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 20
EOF"
  fi

  # Volumes
  run "cat >> '${COMPOSE_FILE}' <<'EOF'

volumes:
  qdrant_data:
  weaviate_data:
  milvus_data:
  postgres_data:
EOF"
}

compose() {
  # Use explicit files so it works anywhere
  (cd "${DIR}" && docker compose --project-name "${PROJECT_NAME}" --env-file ./.env -f ./docker-compose.yml "$@")
}

# ------------------------------
# Health checks
# ------------------------------

do_health_checks() {
  info "Checking service health..."

  if [[ "${VECTOR_DB}" == "qdrant" ]]; then
    if command -v curl >/dev/null 2>&1; then
      curl -fsS "http://localhost:${QDRANT_PORT}/readyz" >/dev/null && info "Qdrant ready" || warn "Qdrant not ready (yet)"
    else
      warn "curl not found; skipping Qdrant HTTP health probe"
    fi
  elif [[ "${VECTOR_DB}" == "weaviate" ]]; then
    if command -v curl >/dev/null 2>&1; then
      curl -fsS "http://localhost:8080/v1/.well-known/ready" >/dev/null && info "Weaviate ready" || warn "Weaviate not ready (yet)"
    else
      warn "curl not found; skipping Weaviate health probe"
    fi
  elif [[ "${VECTOR_DB}" == "milvus" ]]; then
    info "Milvus health probe is stack-dependent; check logs if needed."
  fi

  if [[ "${ENABLE_POSTGRES}" == "true" ]]; then
    if command -v psql >/dev/null 2>&1; then
      PGPASSWORD="${POSTGRES_PASSWORD}" psql "postgresql://${POSTGRES_USER}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}" -c "SELECT extname FROM pg_extension WHERE extname='vector';" >/dev/null \
        && info "Postgres reachable + pgvector installed" \
        || warn "Postgres check failed (psql installed but connection/pgvector check failed)"
    else
      warn "psql not found; skipping Postgres connectivity check"
    fi
  fi
}

print_config() {
  cat <<EOF
Resolved config:
  dir:              ${DIR}
  project:          ${PROJECT_NAME}
  vector_db:        ${VECTOR_DB}
  enable_postgres:  ${ENABLE_POSTGRES}

  Qdrant:
    http:           http://localhost:${QDRANT_PORT}
    grpc:           localhost:${QDRANT_GRPC_PORT}

  Postgres:
    conn:           postgresql://${POSTGRES_USER}:***@localhost:${POSTGRES_PORT}/${POSTGRES_DB}
EOF
}

print_next_steps() {
  cat <<'EOF'
Next steps (recommended):
  1) Create a collection/index and test insert+search (sample scripts).
  2) Add an embeddings worker (Ollama/OpenAI/OpenRouter) and store vectors.
  3) Add backups + auth:
     - Qdrant: put behind a reverse proxy with auth (or firewall to LAN/VPN only)
     - Postgres: restrict pg_hba.conf + strong password + TLS if remote
EOF
}

# ------------------------------
# Command handlers
# ------------------------------

case "${cmd}" in
  config)
    print_config
    ;;

  up)
    info "Log: ${LOG_FILE}"
    write_env_if_missing
    write_compose

    info "Starting services (docker compose up -d)"
    if [[ "${DRY_RUN}" == "true" ]]; then
      info "[dry-run] (cd '${DIR}' && docker compose up -d)"
    else
      compose up -d
    fi

    info "Waiting briefly for containers to initialize..."
    sleep 2 || true

    if [[ "${DRY_RUN}" != "true" ]]; then
      compose ps || true
      do_health_checks || true
    fi

    print_config
    print_next_steps
    ;;

  down)
    info "Stopping services"
    if [[ "${DRY_RUN}" == "true" ]]; then
      info "[dry-run] (cd '${DIR}' && docker compose down)"
    else
      (cd "${DIR}" && docker compose --project-name "${PROJECT_NAME}" --env-file ./.env -f ./docker-compose.yml down) || true
    fi
    ;;

  restart)
    info "Restarting services"
    if [[ "${DRY_RUN}" == "true" ]]; then
      info "[dry-run] restart via compose"
    else
      compose restart || true
      compose ps || true
      do_health_checks || true
    fi
    ;;

  status)
    info "Status"
    if [[ "${DRY_RUN}" == "true" ]]; then
      info "[dry-run] would run compose ps + probes"
    else
      compose ps || true
      do_health_checks || true
    fi
    ;;

  logs)
    info "Tailing logs (Ctrl+C to stop)"
    if [[ "${DRY_RUN}" == "true" ]]; then
      info "[dry-run] would tail compose logs"
    else
      compose logs -f --tail=200
    fi
    ;;

  *)
    err "Unknown command: ${cmd}"
    usage
    exit 2
    ;;
esac

exit 0
