#!/usr/bin/env bash
# ==============================================================================
# Script Name: vector_db_bootstrap.sh
# Date: 2025-12-19
# Author: ChatGPT (for Blaine Winslow / cbwinslow)
# Summary:
#   Bootstraps a local vector database stack using Docker Compose.
#   Default: Qdrant
#   Optional: Postgres + pgvector
#
#   Hardened defaults:
#     - Services bind to 127.0.0.1 by default (safer)
#     - Optional --bind-all to expose on 0.0.0.0
#
# Usage:
#   chmod +x vector_db_bootstrap.sh
#   ./vector_db_bootstrap.sh --dir ./vector-stack up
#   ./vector_db_bootstrap.sh --dir ./vector-stack --enable-postgres false up
#   ./vector_db_bootstrap.sh --dir ./vector-stack status
#   ./vector_db_bootstrap.sh --dir ./vector-stack down
#
# Flags:
#   --dir PATH                 Stack directory (default: ./vector-stack)
#   --enable-postgres true|false (default: true)
#   --bind-all                 Bind ports to 0.0.0.0 (DANGEROUS on untrusted networks)
#   --qdrant-port 6333         Qdrant HTTP port
#   --qdrant-grpc-port 6334    Qdrant gRPC port
#   --pg-port 5432             Postgres port
#   --pg-db vectordb
#   --pg-user vector
#   --pg-pass <pass>           If omitted, an auto password is generated in .env
#   --verbose
#   --dry-run
#
# Outputs:
#   - docker-compose.yml
#   - .env
#   - initdb/00_pgvector.sql (if Postgres enabled)
#
# ==============================================================================

set -Eeuo pipefail

SCRIPT_NAME="vector_db_bootstrap"
LOG_FILE="/tmp/CBW-${SCRIPT_NAME}.log"

STACK_DIR="./vector-stack"
ENABLE_POSTGRES="true"
BIND_ADDR="127.0.0.1"

QDRANT_PORT="6333"
QDRANT_GRPC_PORT="6334"
PG_PORT="5432"
PG_DB="vectordb"
PG_USER="vector"
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

usage(){
  cat <<'USAGE'
vector_db_bootstrap.sh [options] <command>

Commands:
  up | down | restart | status | logs | config

Options:
  --dir PATH
  --enable-postgres true|false
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

Examples:
  ./vector_db_bootstrap.sh --dir ./vector-stack up
  ./vector_db_bootstrap.sh --dir ./vector-stack --enable-postgres false up
  ./vector_db_bootstrap.sh --dir ./vector-stack status
USAGE
}

CMD=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    up|down|restart|status|logs|config) CMD="$1"; shift;;
    --dir) STACK_DIR="$2"; shift 2;;
    --enable-postgres) ENABLE_POSTGRES="$2"; shift 2;;
    --bind-all) BIND_ADDR="0.0.0.0"; shift;;
    --qdrant-port) QDRANT_PORT="$2"; shift 2;;
    --qdrant-grpc-port) QDRANT_GRPC_PORT="$2"; shift 2;;
    --pg-port) PG_PORT="$2"; shift 2;;
    --pg-db) PG_DB="$2"; shift 2;;
    --pg-user) PG_USER="$2"; shift 2;;
    --pg-pass) PG_PASS="$2"; shift 2;;
    --verbose) VERBOSE="true"; shift;;
    --dry-run) DRY_RUN="true"; shift;;
    -h|--help) usage; exit 0;;
    *) err "Unknown arg: $1"; usage; exit 2;;
  esac
done

[[ -z "${CMD}" ]] && { err "Missing command"; usage; exit 2; }

STACK_DIR="$(python3 - <<PY
import os
print(os.path.abspath(os.path.expanduser("${STACK_DIR}")))
PY
)"

info "Log: ${LOG_FILE}"
info "Stack dir: ${STACK_DIR}"
info "Bind address: ${BIND_ADDR}"

if ! have docker; then
  err "docker not found. Install Docker Engine + Compose plugin first."
  exit 1
fi

# Prefer docker compose plugin, fallback to docker-compose
COMPOSE=""
if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif have docker-compose; then
  COMPOSE="docker-compose"
else
  err "docker compose not available. Install Docker Compose plugin."
  exit 1
fi

run "mkdir -p '${STACK_DIR}'"
run "mkdir -p '${STACK_DIR}/initdb'"

ENV_FILE="${STACK_DIR}/.env"
COMPOSE_FILE="${STACK_DIR}/docker-compose.yml"

if [[ -z "${PG_PASS}" ]]; then
  if [[ -f "${ENV_FILE}" ]] && grep -q '^POSTGRES_PASSWORD=' "${ENV_FILE}"; then
    PG_PASS="$(grep '^POSTGRES_PASSWORD=' "${ENV_FILE}" | head -n1 | cut -d'=' -f2-)"
  else
    # Generate a strong-ish local password
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
QDRANT_PORT=${QDRANT_PORT}
QDRANT_GRPC_PORT=${QDRANT_GRPC_PORT}
ENABLE_POSTGRES=${ENABLE_POSTGRES}
POSTGRES_PORT=${PG_PORT}
POSTGRES_DB=${PG_DB}
POSTGRES_USER=${PG_USER}
POSTGRES_PASSWORD=${PG_PASS}
EOF"

# pgvector init SQL
if [[ "${ENABLE_POSTGRES}" == "true" ]]; then
  run "cat > '${STACK_DIR}/initdb/00_pgvector.sql' <<'EOF'
CREATE EXTENSION IF NOT EXISTS vector;
EOF"
fi

# Compose file
# IMPORTANT: bind ports to ${BIND_ADDR} by default
run "cat > '${COMPOSE_FILE}' <<'EOF'
services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    restart: unless-stopped
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

case "${CMD}" in
  config)
    run "${COMPOSE} ${compose_args[*]} config";
    ;;
  up)
    if [[ "${ENABLE_POSTGRES}" == "true" ]]; then
      run "${COMPOSE} ${compose_args[*]} --profile postgres up -d";
    else
      run "${COMPOSE} ${compose_args[*]} up -d";
    fi
    info "Up. Qdrant: http://localhost:${QDRANT_PORT}"
    [[ "${ENABLE_POSTGRES}" == "true" ]] && info "Postgres: postgresql://${PG_USER}:<hidden>@localhost:${PG_PORT}/${PG_DB}"
    ;;
  down)
    run "${COMPOSE} ${compose_args[*]} down";
    ;;
  restart)
    run "${COMPOSE} ${compose_args[*]} restart";
    ;;
  status)
    run "${COMPOSE} ${compose_args[*]} ps";
    ;;
  logs)
    run "${COMPOSE} ${compose_args[*]} logs -f --tail=200";
    ;;
  *)
    err "Unknown command: ${CMD}"; exit 2;;
esac

info "Done."
