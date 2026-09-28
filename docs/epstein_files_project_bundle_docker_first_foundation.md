# Epstein Files — Foundation Bundle (Docker-first)

This canvas mirrors the **final** files in the zip bundle. The intent: unzip → `make bootstrap` → run.

---

## What I changed vs your current directory

- **Fixed** `cbw_bootstrap_project_ubuntu.sh` (it had a Bash syntax error: missing closing brace / EOF).
- **Canonicalized** `vector_db_bootstrap.sh` to the *v2* script (the older v1 didn’t create schema).
- Added **Docker-first** scaffolding so the project is runnable on **Windows/macOS/Linux** without fiddling with system Python.
- Added `pyproject.toml` with uv + ruff/mypy config.
- Added `compose.yml` and `Dockerfile` for a reproducible runner.
- Added `.env.example` and `scripts/doctor.py`.
- Intentionally **excluded** the `*.crdownload` (not a real project artifact).

---

## File: Makefile
```make
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
```

---

## File: compose.yml
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
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-change_me}
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

## File: Dockerfile
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

## File: pyproject.toml
```toml
[project]
name = "epstein-files-pipeline"
version = "0.1.0"
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
  "python-dotenv>=1.0",
  "tomli>=2.0; python_version<'3.11'",
]

[tool.uv]
dev-dependencies = ["ruff>=0.6", "mypy>=1.11"]

[tool.ruff]
line-length = 100
target-version = "py311"
extend-exclude = ["epstein_artifacts", "vector-stack", ".epstein"]

[tool.ruff.lint]
select = ["E","F","I","B","UP","SIM","W"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true
warn_unused_ignores = true
warn_redundant_casts = true
no_implicit_optional = true
```

---

## File: .env.example
```bash
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

## File: scripts/doctor.py
```python
#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request


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
    failures: list[str] = []
    warnings: list[str] = []

    rc, _ = run(["docker", "version"])
    if rc != 0:
        failures.append("Docker not available (is the daemon running?)")
    else:
        print("✅ Docker OK")

    rc, _ = run(["docker", "compose", "version"])
    if rc != 0:
        warnings.append("docker compose plugin not found.")
    else:
        print("✅ docker compose OK")

    qdrant_port = os.getenv("QDRANT_PORT", "6333")
    ok, _ = http_json(f"http://127.0.0.1:{qdrant_port}/")
    if ok:
        print("✅ Qdrant reachable on localhost")
    else:
        warnings.append("Qdrant not reachable on localhost (run `make bootstrap`).")

    if failures:
        print("\n❌ Failures:")
        for f in failures:
            print(f"  - {f}")
        return 3
    if warnings:
        print("\n⚠️ Warnings:")
        for w in warnings:
            print(f"  - {w}")
        return 2
    print("\nAll good.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

## File: vector_db_bootstrap.sh
(In the zip — kept verbatim as your v2 script, since it defines the schema and initdb correctly.)

---

## File: cbw_bootstrap_project_ubuntu.sh
(In the zip — fixed + simplified; Ubuntu helper only.)
