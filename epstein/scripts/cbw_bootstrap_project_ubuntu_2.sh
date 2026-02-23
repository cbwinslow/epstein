#!/usr/bin/env bash
# ==============================================================================
# Script Name: cbw_bootstrap_project_ubuntu.sh
# Date: 2025-12-21
# Author: ChatGPT (for Blaine Winslow / cbwinslow)
# Summary:
#   Ubuntu-only convenience bootstrap for this repo.
#
#   For cross-platform (Windows/macOS/Linux) setup, prefer:
#     make bootstrap
#   which uses Docker/Compose and does not require system Python setup.
#
# Inputs:
#   --dir PATH            Project directory (default: current directory)
#   --name NAME           Project name (default: epstein-files-pipeline)
#   --no-apt              Skip apt installs
#   --no-uv               Skip uv install
#   --no-venv             Skip venv creation
#   --no-deps             Skip python deps install
#   --no-spacy-model      Skip spaCy model download
#   --write-docs-only     Only write markdown + .gitignore + starter config
#   --verbose             More logs
#   --dry-run             Print actions; don't execute
#
# Modification Log:
#   - 2025-12-21: Fix syntax error from previous version; clarify Docker-first path.
# ==============================================================================

set -Eeuo pipefail

SCRIPT_NAME="cbw_bootstrap_project_ubuntu"
LOG_FILE="/tmp/CBW-${SCRIPT_NAME}.log"

PROJECT_DIR="$(pwd)"
PROJECT_NAME="epstein-files-pipeline"

DO_APT="true"
DO_UV="true"
DO_VENV="true"
DO_DEPS="true"
DO_SPACY_MODEL="true"
WRITE_DOCS_ONLY="false"
VERBOSE="false"
DRY_RUN="false"

mkdir -p "$(dirname "${LOG_FILE}")" || true

log() {
  local level="$1"; shift
  local ts
  ts="$(date '+%Y-%m-%d %H:%M:%S')"
  echo "${ts} [${level}] $*" | tee -a "${LOG_FILE}" >/dev/null
}
info(){ log INFO "$@"; }
warn(){ log WARN "$@"; }
err(){ log ERROR "$@"; }

on_error(){
  local code=$?
  local line=$1
  err "Unhandled error at line ${line} (exit ${code}). See ${LOG_FILE}"
  exit "${code}"
}
trap 'on_error $LINENO' ERR

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
cbw_bootstrap_project_ubuntu.sh [options]

Options:
  --dir PATH            Project directory (default: pwd)
  --name NAME           Project name (default: epstein-files-pipeline)

  --no-apt              Skip apt installs
  --no-uv               Skip uv install
  --no-venv             Skip venv creation
  --no-deps             Skip python deps install
  --no-spacy-model      Skip spaCy model download
  --write-docs-only     Only write markdown + .gitignore + starter config

  --verbose             More logs
  --dry-run             Print actions; don't execute
  -h, --help            Help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) PROJECT_DIR="$2"; shift 2;;
    --name) PROJECT_NAME="$2"; shift 2;;

    --no-apt) DO_APT="false"; shift;;
    --no-uv) DO_UV="false"; shift;;
    --no-venv) DO_VENV="false"; shift;;
    --no-deps) DO_DEPS="false"; shift;;
    --no-spacy-model) DO_SPACY_MODEL="false"; shift;;
    --write-docs-only) WRITE_DOCS_ONLY="true"; shift;;

    --verbose) VERBOSE="true"; shift;;
    --dry-run) DRY_RUN="true"; shift;;
    -h|--help) usage; exit 0;;
    *) err "Unknown arg: $1"; usage; exit 2;;
  esac
done

# Normalize path without relying on python
if command -v realpath >/dev/null 2>&1; then
  PROJECT_DIR="$(realpath -m "${PROJECT_DIR}")"
else
  PROJECT_DIR="$(cd "${PROJECT_DIR}" && pwd)"
fi

info "Log: ${LOG_FILE}"
info "Project dir: ${PROJECT_DIR}"

run "mkdir -p '${PROJECT_DIR}'"
run "cd '${PROJECT_DIR}'"

install_apt_deps(){
  [[ "${DO_APT}" != "true" ]] && { warn "Skipping apt installs (--no-apt)"; return 0; }
  if ! have apt-get; then
    warn "apt-get not found. Are you on Ubuntu/Debian? Skipping system deps."
    return 0
  fi
  info "Installing system OCR + utilities via apt..."
  run "sudo apt-get update"
  run "sudo apt-get install -y --no-install-recommends     ocrmypdf tesseract-ocr ghostscript qpdf poppler-utils     curl wget ca-certificates git"
}

install_uv(){
  [[ "${DO_UV}" != "true" ]] && { warn "Skipping uv install (--no-uv)"; return 0; }
  if have uv; then
    info "uv already installed: $(uv --version 2>/dev/null || true)"
    return 0
  fi
  have curl || { err "curl is required to install uv. Install curl or rerun with --no-uv."; exit 1; }
  info "Installing uv..."
  run "curl -LsSf https://astral.sh/uv/install.sh | sh"
  have uv || warn "uv not found on PATH after install. Restart your shell or add ~/.local/bin to PATH."
}

ensure_venv(){
  [[ "${DO_VENV}" != "true" ]] && { warn "Skipping venv creation (--no-venv)"; return 0; }
  have uv || { err "uv is required for venv creation."; exit 1; }
  if [[ -d "${PROJECT_DIR}/.venv" ]]; then
    info ".venv already exists"
  else
    info "Creating .venv (uv)"
    run "uv venv"
  fi
}

ensure_pyproject(){
  if [[ -f "${PROJECT_DIR}/pyproject.toml" ]]; then
    info "pyproject.toml exists"
    return 0
  fi
  have uv || { err "uv is required to init pyproject.toml"; exit 1; }
  info "Initializing pyproject.toml"
  run "uv init"
}

install_python_deps(){
  [[ "${DO_DEPS}" != "true" ]] && { warn "Skipping python deps install (--no-deps)"; return 0; }
  have uv || { err "uv is required to add deps"; exit 1; }
  info "Adding Python dependencies via uv..."
  run "uv add requests beautifulsoup4 lxml tqdm pydantic pdfminer.six spacy psycopg[binary] qdrant-client python-dotenv tomli"
  info "Locking dependencies (uv.lock)"
  run "uv lock"
}

install_spacy_model(){
  [[ "${DO_SPACY_MODEL}" != "true" ]] && { warn "Skipping spaCy model download (--no-spacy-model)"; return 0; }
  have uv || { err "uv is required to run python commands reliably"; exit 1; }
  info "Downloading spaCy model (en_core_web_sm)"
  run "uv run python -m spacy download en_core_web_sm"
}

write_gitignore(){
  local p="${PROJECT_DIR}/.gitignore"
  if [[ -f "${p}" ]]; then
    info ".gitignore exists"
    return 0
  fi
  info "Writing .gitignore"
  [[ "${DRY_RUN}" == "true" ]] && { info "[dry-run] write ${p}"; return 0; }
  cat > "${p}" <<'EOF'
# Python
.venv/
__pycache__/
*.pyc
*.pyo
*.pyd
*.egg-info/

# uv
uv.lock

# OS / editor
.DS_Store
.vscode/
.idea/

# Secrets
.env
*.key
*.pem

# Artifacts (keep private by default)
epstein_artifacts/
vector-stack/
.epstein/

# Logs
*.log
EOF
}

write_docs_and_config(){
  info "Writing markdown starter files + config.json"
  [[ "${DRY_RUN}" == "true" ]] && { info "[dry-run] write docs"; return 0; }

  cat > "${PROJECT_DIR}/README.md" <<EOF
# ${PROJECT_NAME}

Reproducible pipeline for analyzing large PDF releases.

**Cross-platform**: run \`make bootstrap\` (Docker-first).
EOF

  cat > "${PROJECT_DIR}/USAGE.md" <<'EOF'
# Usage

## Docker-first (recommended)
```bash
make bootstrap
make pipeline-init
make pipeline-run
make db-load
```

## Ubuntu helper (optional)
```bash
./cbw_bootstrap_project_ubuntu.sh
```
EOF

  python3 - <<'PY'
import json, pathlib
cfg = {
  "seed_urls": [],
  "allow_domains": [],
  "output_dir": "./epstein_artifacts",
  "do_ocr": True,
  "redact_pii": True,
  "chunk_chars": 1800,
  "chunk_overlap": 250,
  "spacy_model": "en_core_web_sm",
}
pathlib.Path("config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
print("Wrote config.json")
PY
}

main(){
  if [[ "${WRITE_DOCS_ONLY}" == "true" ]]; then
    write_gitignore
    write_docs_and_config
    info "Docs-only mode complete."
    exit 0
  fi

  install_apt_deps
  install_uv
  ensure_pyproject
  ensure_venv
  install_python_deps
  install_spacy_model
  write_gitignore
  write_docs_and_config

  info "Bootstrap complete. Log: ${LOG_FILE}"
}

main "$@"
