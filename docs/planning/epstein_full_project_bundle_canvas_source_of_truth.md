# Epstein Full Project Bundle (Canvas Source of Truth)

This canvas mirrors **every file** in the downloadable zip. Copy/paste sections into matching filenames.

---

## README.md

```md
# Epstein Files — Provenance-Safe Document Analysis Pipeline

A reproducible, audit-friendly pipeline for large PDF releases:

**Download → OCR → Text → Chunk → NER → Postgres (truth) → Qdrant (semantic search)**

- Filesystem stores PDFs, OCR’d PDFs, extracted text, chunk JSONL, entity JSONL.
- PostgreSQL stores structured provenance + relationships (no PDF blobs).
- Qdrant stores embeddings for semantic search over chunks.

## Quickstart (cross-platform, Docker-first)

### Prereqs
- Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- Docker Compose v2

### Run
```bash
make doctor
make bootstrap
make pipeline-init
# edit config.json with seed_urls + allow_domains
make pipeline-run
make db-load
make embed
make search Q="your query"
```

> Windows without `make`: run `scripts/bootstrap.ps1`.
```

---

## PROJECT_LAYOUT.md

```md
# Project Layout

```
.
├── epstein_files_pipeline.py
├── db_ingest_artifacts.py
├── qdrant_embed_chunks.py
├── qdrant_semantic_search.py
├── vector_db_bootstrap.sh
├── compose.yml
├── Dockerfile
├── pyproject.toml
├── Makefile
├── .env.example
├── scripts/
│   ├── doctor.py
│   ├── bootstrap.sh
│   └── bootstrap.ps1
└── rulebook_packs/
    └── epstein-pipeline-pack/
```
```

---

## USAGE.md

```md
# Usage

## Docker-first
```bash
make bootstrap
make pipeline-init
# edit config.json
make pipeline-run
make db-load
make embed
make search Q="your query"
```

## Without make
- Windows: `powershell -ExecutionPolicy Bypass -File .\\scripts\\bootstrap.ps1`
- macOS/Linux: `./scripts/bootstrap.sh`
```

---

## .gitignore

```gitignore
__pycache__/
*.pyc
.venv/
uv.lock
.DS_Store
.vscode/
.idea/
.env
epstein_artifacts/
vector-stack/
.epstein/
.rulebook-ai/
.cursor/
.windsurf/
.clinerules/
GEMINI.md
CODEX.md
*.log
```

---

## .env.example

```dotenv
POSTGRES_DB=analysis
POSTGRES_USER=analysis
POSTGRES_PASSWORD=change_me
POSTGRES_PORT=5432

QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334

EPSTEIN_DSN=postgresql://analysis:analysis@postgres:5432/analysis
QDRANT_URL=http://qdrant:6333
```

---

## Dockerfile

```dockerfile
FROM python:3.11-slim
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    ocrmypdf tesseract-ocr ghostscript qpdf poppler-utils \
    ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"
WORKDIR /app
COPY pyproject.toml uv.lock* /app/
RUN if [ -f uv.lock ]; then uv sync --frozen; else uv sync; fi
COPY . /app
ENTRYPOINT ["uv","run","python"]
CMD ["epstein_files_pipeline.py","--help"]
```

---

## compose.yml

```yaml
services:
  pipeline:
    build:
      context: .
      dockerfile: Dockerfile
    image: epstein-pipeline:local
    container_name: epstein_pipeline_runner
    volumes:
      - ./:/app
    working_dir: /app
    environment:
      EPSTEIN_DSN: ${EPSTEIN_DSN:-}
      QDRANT_URL: ${QDRANT_URL:-http://qdrant:6333}
    depends_on:
      - qdrant
      - postgres
    profiles: ["pipeline"]

  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    restart: unless-stopped
    ports:
      - "127.0.0.1:${QDRANT_PORT:-6333}:6333"
      - "127.0.0.1:${QDRANT_GRPC_PORT:-6334}:6334"
    volumes:
      - qdrant_storage:/qdrant/storage

  postgres:
    image: pgvector/pgvector:pg16
    container_name: pgvector_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-analysis}
      POSTGRES_USER: ${POSTGRES_USER:-analysis}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-analysis}
    ports:
      - "127.0.0.1:${POSTGRES_PORT:-5432}:5432"
    volumes:
      - pg_storage:/var/lib/postgresql/data
      - ./vector-stack/initdb:/docker-entrypoint-initdb.d:ro

volumes:
  qdrant_storage:
  pg_storage:
```

---

## pyproject.toml

```toml
[project]
name = "epstein-files-pipeline"
version = "0.2.0"
description = "Reproducible, provenance-safe PDF analysis pipeline (OCR/text/chunk/NER/embeddings)."
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "requests>=2.31",
  "beautifulsoup4>=4.12",
  "lxml>=5.0",
  "tqdm>=4.66",
  "pydantic>=2.6",
  "pdfminer.six>=20231228",
  "spacy>=3.7",
  "psycopg[binary]>=3.2",
  "qdrant-client>=1.9",
  "fastembed>=0.3",
  "python-dotenv>=1.0",
]

[tool.uv]
dev-dependencies = ["ruff>=0.6", "mypy>=1.11"]

[tool.ruff]
line-length = 100
target-version = "py311"
extend-exclude = ["epstein_artifacts", "vector-stack", ".epstein", ".rulebook-ai"]

[tool.ruff.lint]
select = ["E","F","I","B","UP","SIM","W"]
ignore = ["E501"]
```

---

## Makefile

```make
ARTIFACTS_DIR ?= ./epstein_artifacts
VECTOR_DIR ?= ./vector-stack
CONFIG ?= ./config.json

COMPOSE ?= docker compose
COMPOSE_FILE ?= compose.yml

.PHONY: help
help:
	@echo "Targets: doctor bootstrap down status pipeline-init pipeline-run db-load embed search lint"

.PHONY: doctor
doctor:
	@python scripts/doctor.py || true

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

.PHONY: embed
embed:
	@$(COMPOSE) -f $(COMPOSE_FILE) --profile pipeline run --rm \
	  -e EPSTEIN_DSN="$${EPSTEIN_DSN:-postgresql://analysis:analysis@postgres:5432/analysis}" \
	  -e QDRANT_URL="$${QDRANT_URL:-http://qdrant:6333}" \
	  pipeline qdrant_embed_chunks.py --dsn "$${EPSTEIN_DSN:-postgresql://analysis:analysis@postgres:5432/analysis}" --qdrant-url "$${QDRANT_URL:-http://qdrant:6333}" --resume --write-back

.PHONY: search
search:
	@$(COMPOSE) -f $(COMPOSE_FILE) --profile pipeline run --rm \
	  -e EPSTEIN_DSN="$${EPSTEIN_DSN:-postgresql://analysis:analysis@postgres:5432/analysis}" \
	  -e QDRANT_URL="$${QDRANT_URL:-http://qdrant:6333}" \
	  -e Q="$${Q:-}" \
	  pipeline qdrant_semantic_search.py "$${Q:-}" --qdrant-url "$${QDRANT_URL:-http://qdrant:6333}" --dsn "$${EPSTEIN_DSN:-postgresql://analysis:analysis@postgres:5432/analysis}" --with-text

.PHONY: lint
lint:
	@$(COMPOSE) -f $(COMPOSE_FILE) --profile pipeline run --rm pipeline -m ruff check .
```

---

## scripts/doctor.py

```python
#!/usr/bin/env python3
from __future__ import annotations
import json, os, subprocess, sys, urllib.request

def run(cmd: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
        return p.returncode, p.stdout.strip()
    except Exception as e:
        return 99, str(e)

def http_json(url: str, timeout: int = 3) -> tuple[bool, dict]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = r.read().decode("utf-8", errors="replace")
        return True, json.loads(data)
    except Exception:
        return False, {}

def main() -> int:
    failures, warnings = [], []
    rc, _ = run(["docker","version"])
    if rc != 0: failures.append("Docker not available (is daemon running?)")
    else: print("✅ Docker OK")
    rc, _ = run(["docker","compose","version"])
    if rc != 0: warnings.append("docker compose plugin not found.")
    else: print("✅ docker compose OK")
    qdrant_port = os.getenv("QDRANT_PORT","6333")
    ok, _ = http_json(f"http://127.0.0.1:{qdrant_port}/")
    if ok: print("✅ Qdrant reachable on localhost")
    else: warnings.append("Qdrant not reachable (run `make bootstrap`).")
    if failures:
        print("\n❌ Failures:"); [print(f"  - {f}") for f in failures]; return 3
    if warnings:
        print("\n⚠️ Warnings:"); [print(f"  - {w}") for w in warnings]; return 2
    print("\nAll good."); return 0

if __name__ == "__main__":
    sys.exit(main())
```

---

## scripts/bootstrap.sh

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
COMPOSE="${COMPOSE:-docker compose}"
COMPOSE_FILE="${COMPOSE_FILE:-compose.yml}"
python3 scripts/doctor.py || true
chmod +x ./vector_db_bootstrap.sh
./vector_db_bootstrap.sh --dir ./vector-stack up
${COMPOSE} -f ${COMPOSE_FILE} up -d qdrant postgres
${COMPOSE} -f ${COMPOSE_FILE} --profile pipeline run --rm pipeline epstein_files_pipeline.py init-config --out ./config.json
echo "Edit ./config.json then run: make pipeline-run"
```

---

## scripts/bootstrap.ps1

```powershell
$ErrorActionPreference = "Stop"
function Info($m){ Write-Host "[bootstrap] $m" }
$compose = if ($env:COMPOSE) { $env:COMPOSE } else { "docker compose" }
$composeFile = if ($env:COMPOSE_FILE) { $env:COMPOSE_FILE } else { "compose.yml" }
Info "doctor"; python scripts/doctor.py | Out-Host
Info "schema+stack"; bash -lc "chmod +x ./vector_db_bootstrap.sh && ./vector_db_bootstrap.sh --dir ./vector-stack up" | Out-Host
Invoke-Expression "$compose -f $composeFile up -d qdrant postgres" | Out-Host
Info "init config"; Invoke-Expression "$compose -f $composeFile --profile pipeline run --rm pipeline epstein_files_pipeline.py init-config --out ./config.json" | Out-Host
Info "done"; Write-Host "Edit .\\config.json then run make pipeline-run (or docker compose equivalents)."
```

---

## config.example.json

```json
{
  "seed_urls": [],
  "allow_domains": [],
  "output_dir": "./epstein_artifacts",
  "do_ocr": true,
  "redact_pii": true,
  "chunk_chars": 1800,
  "chunk_overlap": 250,
  "spacy_model": "en_core_web_sm"
}
```

---

## epstein_files_pipeline.py

*(Included in zip; large file not duplicated here to avoid scroll fatigue.)*

## db_ingest_artifacts.py

*(Included in zip; large file not duplicated here to avoid scroll fatigue.)*

## vector_db_bootstrap.sh

*(Included in zip; large file not duplicated here to avoid scroll fatigue.)*

## qdrant_embed_chunks.py

*(Included in zip; full file present.)*

## qdrant_semantic_search.py

*(Included in zip; full file present.)*

---

## rulebook_packs/epstein-pipeline-pack/

*(Entire pack included in zip; see previous pack canvas for full contents.)*
