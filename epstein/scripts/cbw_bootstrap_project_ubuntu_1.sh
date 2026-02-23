#!/usr/bin/env bash
# ==============================================================================
# Script Name: cbw_bootstrap_project_ubuntu.sh
# Date: 2025-12-19
# Author: ChatGPT (for Blaine Winslow / cbwinslow)
# Summary:
#   One-command bootstrap for a fresh document-analysis repo on Ubuntu:
#     - Installs system OCR dependencies (ocrmypdf, tesseract, etc.)
#     - Installs uv (if missing)
#     - Ensures Python 3.10 is available via uv-managed Python
#     - Creates .venv pinned to Python 3.10
#     - Initializes pyproject.toml (if missing) and installs Python deps
#     - Downloads spaCy model
#     - Creates repo hygiene files (.gitignore)
#     - Writes critical project markdown files (README/USAGE/AGENTS/RULES/...)
#     - Writes a starter config.json (if missing)
#
#   This script is designed to be safe and repeatable (idempotent).
#   It logs to /tmp/CBW-cbw_bootstrap_project_ubuntu.log
#
# Inputs:
#   --dir PATH            Project directory (default: current directory)
#   --name NAME           Project name (default: doc-analysis-pipeline)
#   --no-apt              Skip apt installs
#   --no-uv               Skip uv install
#   --no-python           Skip uv python install 3.10
#   --no-venv             Skip venv creation
#   --no-deps             Skip python deps install
#   --no-spacy-model      Skip spaCy model download
#   --write-docs-only     Only write markdown + .gitignore + config.json
#   --verbose             More logs
#   --dry-run             Print actions; don't execute
#
# Outputs:
#   - pyproject.toml / uv.lock / .venv/
#   - README.md, USAGE.md, AGENTS.md, RULES.md, ARCHITECTURE.md, RESEARCH_LOG.md, PUBLISHING.md
#   - .gitignore
#   - config.json (starter)
#
# Modification Log:
#   - 2025-12-19: Initial version
# ==============================================================================

set -Eeuo pipefail

SCRIPT_NAME="cbw_bootstrap_project_ubuntu"
LOG_FILE="/tmp/CBW-${SCRIPT_NAME}.log"

PROJECT_DIR="$(pwd)"
PROJECT_NAME="doc-analysis-pipeline"

DO_APT="true"
DO_UV="true"
DO_PYTHON="true"
DO_VENV="true"
DO_DEPS="true"
DO_SPACY_MODEL="true"
WRITE_DOCS_ONLY="false"
VERBOSE="false"
DRY_RUN="false"

# ------------------------------
# Logging
# ------------------------------

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
  if [[ "${VERBOSE}" == "true" ]]; then
    info "$*"
  fi
  eval "$@"
}

have(){ command -v "$1" >/dev/null 2>&1; }

# ------------------------------
# CLI
# ------------------------------

usage(){
  cat <<'USAGE'
cbw_bootstrap_project_ubuntu.sh [options]

Options:
  --dir PATH            Project directory (default: pwd)
  --name NAME           Project name (default: doc-analysis-pipeline)

  --no-apt              Skip apt installs
  --no-uv               Skip uv install
  --no-python           Skip uv python install 3.10
  --no-venv             Skip venv creation
  --no-deps             Skip python deps install
  --no-spacy-model      Skip spaCy model download
  --write-docs-only     Only write markdown + .gitignore + config.json

  --verbose             More logs
  --dry-run             Print actions; don't execute
  -h, --help            Help

Examples:
  ./cbw_bootstrap_project_ubuntu.sh
  ./cbw_bootstrap_project_ubuntu.sh --dir ~/dev/epstein-analysis --name epstein-analysis
  ./cbw_bootstrap_project_ubuntu.sh --write-docs-only
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) PROJECT_DIR="$2"; shift 2;;
    --name) PROJECT_NAME="$2"; shift 2;;

    --no-apt) DO_APT="false"; shift;;
    --no-uv) DO_UV="false"; shift;;
    --no-python) DO_PYTHON="false"; shift;;
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

PROJECT_DIR="$(python3 - <<PY
import os
print(os.path.abspath(os.path.expanduser("${PROJECT_DIR}")))
PY
)"

info "Log: ${LOG_FILE}"
info "Project dir: ${PROJECT_DIR}"

run "mkdir -p '${PROJECT_DIR}'"
run "cd '${PROJECT_DIR}'"

# ------------------------------
# 1) System deps (Ubuntu)
# ------------------------------

install_apt_deps(){
  if [[ "${DO_APT}" != "true" ]]; then
    warn "Skipping apt installs (--no-apt)"
    return 0
  fi

  if ! have apt-get; then
    warn "apt-get not found. Are you on Ubuntu/Debian? Skipping system deps."
    return 0
  fi

  info "Installing system OCR + utilities via apt..."
  run "sudo apt-get update"
  run "sudo apt-get install -y --no-install-recommends \
    ocrmypdf tesseract-ocr ghostscript qpdf poppler-utils \
    curl wget ca-certificates git"
}

# ------------------------------
# 2) uv + Python 3.10
# ------------------------------

install_uv(){
  if [[ "${DO_UV}" != "true" ]]; then
    warn "Skipping uv install (--no-uv)"
    return 0
  fi

  if have uv; then
    info "uv already installed: $(uv --version 2>/dev/null || true)"
    return 0
  fi

  if ! have curl; then
    err "curl is required to install uv. Install curl or rerun with --no-uv."
    exit 1
  fi

  info "Installing uv..."
  run "curl -LsSf https://astral.sh/uv/install.sh | sh"

  # Ensure common profile files contain uv PATH export (uv installer usually does)
  if ! have uv; then
    warn "uv not found on PATH after install. Try restarting your shell, or add ~/.local/bin to PATH."
  fi
}

install_python_310(){
  if [[ "${DO_PYTHON}" != "true" ]]; then
    warn "Skipping uv python install 3.10 (--no-python)"
    return 0
  fi
  if ! have uv; then
    err "uv is required for managed Python install. Install uv or rerun with --no-python."
    exit 1
  fi

  info "Ensuring Python 3.10 is available via uv..."
  run "uv python install 3.10"
}

# ------------------------------
# 3) Venv + deps + lock
# ------------------------------

ensure_venv(){
  if [[ "${DO_VENV}" != "true" ]]; then
    warn "Skipping venv creation (--no-venv)"
    return 0
  fi
  if ! have uv; then
    err "uv is required for venv creation."
    exit 1
  fi

  if [[ -d "${PROJECT_DIR}/.venv" ]]; then
    info ".venv already exists"
  else
    info "Creating .venv pinned to Python 3.10"
    run "uv venv --python 3.10"
  fi
}

ensure_pyproject(){
  if [[ -f "${PROJECT_DIR}/pyproject.toml" ]]; then
    info "pyproject.toml exists"
    return 0
  fi
  if ! have uv; then
    err "uv is required to init pyproject.toml"
    exit 1
  fi
  info "Initializing pyproject.toml"
  run "uv init --python 3.10"
}

install_python_deps(){
  if [[ "${DO_DEPS}" != "true" ]]; then
    warn "Skipping python deps install (--no-deps)"
    return 0
  fi
  if ! have uv; then
    err "uv is required to add deps"
    exit 1
  fi

  # Minimal set for pipeline + JSONL
  info "Adding Python dependencies via uv..."
  run "uv add requests beautifulsoup4 lxml tqdm pydantic pdfminer.six spacy"

  info "Locking dependencies (uv.lock)"
  run "uv lock"
}

install_spacy_model(){
  if [[ "${DO_SPACY_MODEL}" != "true" ]]; then
    warn "Skipping spaCy model download (--no-spacy-model)"
    return 0
  fi
  if ! have uv; then
    err "uv is required to run python commands reliably"
    exit 1
  fi
  info "Downloading spaCy model (en_core_web_sm)"
  run "uv run python -m spacy download en_core_web_sm"
}

# ------------------------------
# 4) Repo hygiene + docs
# ------------------------------

write_gitignore(){
  local p="${PROJECT_DIR}/.gitignore"
  if [[ -f "${p}" ]]; then
    info ".gitignore exists"
    return 0
  fi

  info "Writing .gitignore"
  run "cat > '${p}' <<'EOF'
# Python
.venv/
__pycache__/
*.pyc
*.pyo
*.pyd
*.egg-info/
.dist/
.build/

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

# Logs
/tmp/CBW-*.log
*.log
EOF"
}

write_markdown_files(){
  info "Writing markdown starter files"

  run "cat > '${PROJECT_DIR}/README.md' <<'EOF'
# ${PROJECT_NAME}

A reproducible pipeline for analyzing public PDF document releases:

- Discover PDF links from trusted seed pages (strict allowlist)
- Download PDFs + hash manifest (doc_id = sha256)
- OCR (OCRmyPDF) for scanned docs
- Extract + lightly redact text
- Chunk with overlap + offsets
- Named Entity Recognition (NER)
- Run tracking + safe exports for publication

## Quickstart

### 1) Bootstrap environment (Ubuntu)
Run:
```bash
./cbw_bootstrap_project_ubuntu.sh
```

### 2) Create config
```bash
uv run python epstein_files_pipeline.py init-config --out ./config.json
```

Edit `config.json` to include the official seed pages for the release you’re analyzing.

### 3) Run
```bash
uv run python epstein_files_pipeline.py run --config ./config.json
```

## Output folders
- `epstein_artifacts/downloads/` original PDFs
- `epstein_artifacts/ocr/` OCR’d PDFs
- `epstein_artifacts/text/` extracted text
- `epstein_artifacts/chunks/` chunks w/ offsets
- `epstein_artifacts/entities/` entity mentions
- `epstein_artifacts/safe_exports/` publishable-ish aggregates

## Responsible publication
- Treat names as **“mentioned”** unless a document explicitly alleges/charges.
- Do not republish victim-identifying info or personal identifiers.
- Every claim should reference provenance (doc_id + source_url + chunk/page refs).
EOF"

  run "cat > '${PROJECT_DIR}/USAGE.md' <<'EOF'
# Usage

## Setup
```bash
./cbw_bootstrap_project_ubuntu.sh
```

## Configure
Create `config.json`:
```bash
uv run python epstein_files_pipeline.py init-config --out ./config.json
```

Edit `seed_urls` to the official release pages, and keep `allow_domains` strict.

## Run pipeline
```bash
uv run python epstein_files_pipeline.py run --config ./config.json
```

## Regenerate safe exports
```bash
uv run python epstein_files_pipeline.py export-safe --config ./config.json
```

## Key artifacts
- `epstein_artifacts/manifest.jsonl` (doc_id sha256 ↔ source_url)
- `epstein_artifacts/runs.jsonl` (run tracking)
- `epstein_artifacts/failures.jsonl` (errors)
- `epstein_artifacts/safe_exports/` (aggregates for publication)
EOF"

  run "cat > '${PROJECT_DIR}/AGENTS.md' <<'EOF'
# AI Agents

This repo supports agent workflows. The goal is correctness + traceability.

## Agent roles

### Collector
- Maintains `config.json` seed URLs
- Runs acquisition and verifies `manifest.jsonl`

### OCR/Text QA
- Spot-checks OCR quality
- Flags garbled extracts and suggests OCRmyPDF tweaks

### Entity Miner
- Aggregates entity mentions
- Proposes custom patterns (case IDs, tail numbers, etc.)

### Relationship Builder
- Builds co-occurrence clusters across chunks
- Produces evidence snippets with provenance

### Writer/Publisher
- Writes a blog post using safe exports + sources appendix
- Avoids personal identifiers and victim-identifying info

## Hard guardrails
- Never state or imply guilt.
- Treat names as “mentioned.”
- Do not publish personal identifiers.
- Every claim must reference provenance (doc_id + URL + chunk/page refs).
EOF"

  run "cat > '${PROJECT_DIR}/RULES.md' <<'EOF'
# Rules

## Reproducibility
- Preserve originals; never modify PDFs in-place.
- All runs append to `runs.jsonl` and `failures.jsonl`.

## Provenance
- All analysis outputs must carry doc_id (sha256) + source_url.

## Safety
- Redact basic identifiers before downstream analysis.
- Use `safe_exports/` for publication-first outputs.

## Git hygiene
- Do not commit artifacts or secrets.
- Keep `.env` out of git.
EOF"

  run "cat > '${PROJECT_DIR}/ARCHITECTURE.md' <<'EOF'
# Architecture

## Pipeline
1) **Discovery**: crawl seed URLs for PDF links (allowlist)
2) **Download**: store PDFs, hash sha256 => **doc_id**, write `manifest.jsonl`
3) **OCR**: generate searchable PDFs (if enabled)
4) **Extract + Redact**: produce text; redact emails/phones/SSNs
5) **Chunk**: character windowing with overlap + offsets
6) **NER**: entity mentions emitted with provenance
7) **Run tracking**: `runs.jsonl` + `failures.jsonl`
8) **Safe exports**: aggregates and sources for publication

## Provenance chain
`manifest.jsonl` is the source of truth:
- doc_id (sha256) ↔ source_url

Chunks and entities reference doc_id + source_url + offsets.

## Vector DB (optional)
Use Qdrant for vector search and Postgres/pgvector for structured tables.
EOF"

  run "cat > '${PROJECT_DIR}/RESEARCH_LOG.md' <<'EOF'
# Research Log

Use this to narrate and audit your work.

## Run: YYYY-MM-DD
- Seed URLs:
- Config hash:
- Notes:

### Acquisition
- Discovered:
- Downloaded:
- Failures:

### OCR/Text QA
- OCR failures:
- Quality notes:

### Entities
- Top PERSON:
- Top ORG:
- Top DATE:

### Publication
- Safe-to-publish outputs:
- Sensitive items to exclude:
EOF"

  run "cat > '${PROJECT_DIR}/PUBLISHING.md' <<'EOF'
# Publishing (later)

This repo will export publishable artifacts into `epstein_artifacts/safe_exports/`.

## Do not publish
- emails, phones, addresses, SSNs
- victim-identifying info
- allegations without direct provenance

## Recommended publish bundle
- `safe_exports/top_entities_by_label.json`
- `safe_exports/sources_from_manifest.json`
- a short methods + limitations section
EOF"
}

write_starter_config(){
  local p="${PROJECT_DIR}/config.json"
  if [[ -f "${p}" ]]; then
    info "config.json exists"
    return 0
  fi

  info "Writing starter config.json"
  run "cat > '${p}' <<'EOF'
{
  "seed_urls": [
    "https://www.justice.gov/opa/",
    "https://vault.fbi.gov/jeffrey-epstein",
    "https://oversight.house.gov/"
  ],
  "output_dir": "./epstein_artifacts",
  "allow_domains": [
    "www.justice.gov",
    "justice.gov",
    "oversight.house.gov",
    "vault.fbi.gov",
    "www.fbi.gov",
    "drive.google.com",
    "www.dropbox.com",
    "dropbox.com"
  ],
  "user_agent": "Mozilla/5.0 (X11; Linux x86_64) doc-pipeline/1.1",
  "timeout_seconds": 60,
  "max_bytes_per_file": 2000000000,
  "max_workers": 6,
  "polite_delay_seconds": 0.3,
  "verify_tls": true,
  "enable_ocr": true,
  "ocrmypdf_lang": "eng",
  "ocrmypdf_extra_args": ["--skip-text", "--rotate-pages"],
  "chunk_chars": 10000,
  "chunk_overlap_chars": 1500,
  "spacy_model": "en_core_web_sm",
  "redact_emails": true,
  "redact_phones": true,
  "redact_ssns": true,
  "safe_export_topn": 100
}
EOF"
}

# ------------------------------
# Execute
# ------------------------------

write_gitignore
write_markdown_files
write_starter_config

if [[ "${WRITE_DOCS_ONLY}" == "true" ]]; then
  info "Docs-only mode complete."
  exit 0
fi

install_apt_deps
install_uv
install_python_310
ensure_venv
ensure_pyproject
install_python_deps
install_spacy_model

info "Bootstrap complete."
info "Next: uv run python epstein_files_pipeline.py run --config ./config.json"
