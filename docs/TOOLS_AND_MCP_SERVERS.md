# Tools & MCP Servers (services) — Epstein Files

This document lists *concrete* tools, system packages, Python dependencies, and the local services (what we refer to as "MCP servers" for this repo) that the project expects. Use this as the canonical place to add new service or tool requirements and the minimal validation checks to add to `scripts/doctor.py`.

## System tools (Ubuntu / macOS / Windows WSL)
- Docker & Docker Compose (used for Qdrant/Postgres + optional pipeline runner)
- uv (https://astral.sh/uv) — used for reproducible Python env and runner (`uv run`)
- ocrmypdf, tesseract-ocr, ghostscript, qpdf, poppler-utils — OCR & PDF toolchain
- curl, git, ca-certificates

Bootstrap example (Ubuntu):
- `./cbw_bootstrap_project_ubuntu.sh` (installs system deps + uv + Python + spacy model)

## Python packages (installed via `uv` / pyproject)
- requests, beautifulsoup4, lxml, tqdm, pydantic
- pdfminer.six, spacy (download model `en_core_web_sm`), psycopg[binary]
- qdrant-client, python-dotenv, tomli
- dev: ruff, mypy

Bootstrap Python example:
- `uv add requests beautifulsoup4 lxml tqdm pydantic pdfminer.six spacy psycopg[binary] qdrant-client python-dotenv tomli`
- `uv run python -m spacy download en_core_web_sm`

## MCP servers / Services (endpoints & defaults)
These are the services the repo expects to be *reachable* for local runs and CI sanity checks:

- Qdrant (vector DB)
  - Default: http://localhost:6333
  - Env vars: `QDRANT_URL`, `QDRANT_PORT`, `QDRANT_GRPC_PORT`
  - Bootstrap: `./vector_db_bootstrap.sh up` or `make vectordb-up`

- Postgres (+ pgvector extension)
  - Default DB: `postgresql://analysis:analysis@postgres:5432/analysis` (see `.env.example`)
  - Env vars: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`, `EPSTEIN_DSN`
  - Bootstrap: `./vector_db_bootstrap.sh --enable-postgres true up` (docker compose)

- Optional telemetry/analytics (if enabled): PostHog or similar (refer to `posthog_install.txt` for packages). If you add such a server, add env vars to `.env.example` and a reachable check to `scripts/doctor.py`.

## Validation checklist (what `scripts/doctor.py` should assert)
- Docker daemon reachable
- Docker Compose plugin available
- Qdrant HTTP endpoint reachable on `QDRANT_PORT`
- (Optional) Postgres reachable using `EPSTEIN_DSN` / configured port

Run the checks locally:

- `python scripts/doctor.py` — runs quick checks (Docker + Qdrant)
- `python scripts/doctor.py --check-db` — runs Postgres reachability check (uses `EPSTEIN_DSN` or `POSTGRES_*` env vars)
- `make doctor-check` — fails the Makefile target when checks fail (useful for CI)

Note: The `Doctor check` GitHub Actions workflow runs on manual dispatch and on PRs to validate these services before merging.

## How to add a new service
1. Add env vars to `.env.example`
2. Add a check to `scripts/doctor.py` and the GitHub workflow `doctor-check.yml` (or the `doctor` Makefile target)
3. Document the service in this file with default ports and usage notes

## Where to document MCP servers & tools
- This file: `docs/TOOLS_AND_MCP_SERVERS.md` (additions welcome)
- `.env.example` for env var defaults
- `scripts/doctor.py` for validation checks
- `.github/copilot-instructions.md` for high-level guidance to agents

---
If you want, I can add a `scripts/doctor.py` check for Postgres (attempt a TCP connect or a minimal SQL query) and a PostHog reachability check; tell me which services you'd like validated and I'll add them. (Suggested next step: add Postgres check to `scripts/doctor.py`.)