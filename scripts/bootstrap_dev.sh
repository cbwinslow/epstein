#!/usr/bin/env bash
# =============================================================================
# Script Name: bootstrap_dev.sh
# Date: 2025-12-23
# Author: cbwinslow + ChatGPT
# Summary:
#   Safe developer bootstrap: create venv, install deps, validate.
# =============================================================================

set -euo pipefail

LOG_DIR="${OPENDISCOURSE_LOG_DIR:-./logs}"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/bootstrap_dev.log"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "[INFO] Bootstrapping OpenDiscourse dev environment..."

command -v python3 >/dev/null 2>&1 || { echo "[ERROR] python3 not found."; exit 1; }

if [ ! -d ".venv" ]; then
  echo "[INFO] Creating venv in .venv..."
  python3 -m venv .venv
else
  echo "[INFO] .venv already exists."
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[INFO] Upgrading pip..."
pip install -U pip

echo "[INFO] Installing project (editable + dev deps)..."
pip install -e ".[dev]"

echo "[INFO] Done. Next:"
echo "  make up"
echo "  psql ... -f db/schema.sql"
echo "  opendiscourse-ingest --dry-run"
