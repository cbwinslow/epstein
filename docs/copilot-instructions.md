# GitHub Copilot / AI Agent Instructions — epstein

Purpose: Make an AI coding agent or new contributor productive quickly by listing the repo's key workflows, conventions, and safe-guards with concrete commands and file references.

## Quick start (most common flows) ✅
- Bootstrap environment (Ubuntu):
  - ./cbw_bootstrap_project_ubuntu.sh  (or `make bootstrap`)
  - Installs Python deps via `uv` and system packages (OCRmyPDF, tesseract, ghostscript, qpdf, poppler-utils)
- Start local data stack (Qdrant + optional Postgres/pgvector):
  - `make vectordb-up`
  - or: `./vector_db_bootstrap.sh --dir ./vector-stack up`
- Create pipeline config and run:
  - `uv run python epstein_files_pipeline.py init-config --out ./config.json`
  - `uv run python epstein_files_pipeline.py run --config ./config.json --verbose`
- Rebuild safe exports or re-run stages:
  - `uv run python epstein_files_pipeline.py export-safe --config ./config.json`
- Load artifacts into Postgres:
  - `DSN=postgresql://user:pass@localhost:5432/analysis make db-load`
  - or: `uv run python db_ingest_artifacts.py --dsn "<DSN>" --artifacts-dir ./epstein_artifacts`

## Practical Qdrant / semantic search commands 🔍
- Boot Qdrant: `./vector_db_bootstrap.sh up` (or `make vectordb-up`)
- Embed chunks (idempotent):
  - `uv run python qdrant_embed_chunks.py --dsn "$EPSTEIN_DSN" --qdrant-url "$QDRANT_URL" --resume --write-back`
- Run semantic search (optionally print chunk text from Postgres):
  - `uv run python qdrant_semantic_search.py "your query" --qdrant-url "$QDRANT_URL" --with-text`
- Services env: `.env.example` documents QDRANT_URL/QDRANT_PORT/EPSTEIN_DSN; use `scripts/doctor.py` to validate local services

## High-level architecture (short) 🔧
- Single pipeline entrypoint: `epstein_files_pipeline.py` (discover → download → ocr → extract → redact → chunk → NER → safe_exports).
- Filesystem: stores raw and OCR’d PDFs + extracted text under `epstein_artifacts/` (downloads, ocr, text, chunks, entities, safe_exports).
- SQL (Postgres `doc_analysis` schema): stores metadata, text, chunks, entities, runs, failures. Use `db_ingest_artifacts.py` to load artifacts.
- Vector DB (Qdrant): stores embeddings for semantic search; embedding scripts are idempotent (use chunk_id as point ID).

## Key conventions & concrete formats 📚
- doc_id = sha256(file bytes). Manifest lines: `{ "sha256": <doc_id>, "url": <source_url>, ... }` in `epstein_artifacts/manifest.jsonl`.
- Outputs per doc_id: `{doc_id}.txt`, `{doc_id}.chunks.jsonl`, `{doc_id}.entities.jsonl` in `text/`, `chunks/`, `entities/`.
- Chunking defaults: `chunk_chars = 10000`, `chunk_overlap_chars = 1500` (see `PipelineConfig` in `epstein_files_pipeline.py`).
- NER: default spaCy model `en_core_web_sm` (run `uv run python -m spacy download en_core_web_sm` when bootstrapping).
- Redaction flags: `redact_emails`, `redact_phones`, `redact_ssns` (enabled by default) — redaction happens BEFORE chunking/NER.
- Run tracking (append-only): `runs.jsonl`, `failures.jsonl` — do not rewrite; append semantics are relied on downstream.

## Developer workflows & checks 🧪
- Use `Makefile` shortcuts (see `makefile_checkpoint_commands.txt`) for common tasks.
- Use `uv` for reproducible virtualenv & dependency management (`uv add`, `uv lock`, `uv run`).
- Debugging OCR: run `ocrmypdf` manually and inspect `epstein_artifacts/run.log` and `failures.jsonl`.
- Check services: `scripts/doctor.py` tests Qdrant/Postgres reachability and useful for CI sanity checks.

## Integrations & important files 🔗
- Pipeline: `epstein_files_pipeline.py`
- DB loader: `db_ingest_artifacts.py`
- Vector embed/search: `qdrant_embed_chunks.py`, `qdrant_semantic_search.py` (or `qdrant_embed_chunks2.py` variants)
- Local stack bootstrap: `vector_db_bootstrap.sh` and `.env.example`
- Project layout & rationale: `PROJECT_LAYOUT.md`, `project_markdown_starter_pack_uv_python_3.md`

## Safety & guardrails ⚠️
- Never infer wrongdoing from content — treat names as "mentioned" unless explicitly stated in sources.
- Do not expose PII in outputs or PRs (emails, phones, SSNs, victim identifiers). Use `safe_exports/` for publishable artifacts.
- When changing `seed_urls` or `allow_domains`, prefer small, reviewed adjustments — `allow_domains` is a safety boundary.

## Editing or extending the project (tips) ✍️
- When adding a new extraction stage, update `epstein_files_pipeline.py`, add run metrics to `runs.jsonl`, and extend `db_ingest_artifacts.py` if outputs should land in Postgres.
- If you add a new script that depends on external services, document required env vars in `.env.example` and add a `scripts/doctor.py` check.
- Keep examples and real commands in docs (not just narrative prose) so agents can run them automatically.

---
If anything here is unclear or you want added examples (SQL snippets, `psql` commands, or diagnostic checklists), tell me which section to expand and I’ll iterate. ✅