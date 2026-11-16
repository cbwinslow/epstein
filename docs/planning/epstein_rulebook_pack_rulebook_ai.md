# Epstein Rulebook Pack (rulebook-ai)

This canvas contains the **full contents** of a Rulebook-AI “pack” you can drop into your Epstein pipeline repo at:

`rulebook_packs/epstein-pipeline-pack/`

---

## Tree

```
rulebook_packs/
  epstein-pipeline-pack/
    pack.yaml
    USAGE.md
    rules/
      RULES.md
    memory/
      PROJECT_CONTEXT.md
    tools/
      README.md
      .gitignore.rulebook-generated
```

---

## rulebook_packs/epstein-pipeline-pack/pack.yaml

```yaml
# Epstein Pipeline Pack for rulebook-ai
# Author: cbwinslow
# Created: 2025-12-23
name: epstein-pipeline
version: "0.1.0"
description: >
  Rules + memory + tool-starters for the Epstein Files document analysis pipeline:
  provenance-safe PDF ingestion, OCR, chunking, NER, Postgres storage, and Qdrant semantic search.
authors:
  - "cbwinslow"
license: "MIT"

# rulebook-ai copies these starters into the target project workspace.
starters:
  memory_dir: "memory"
  tools_dir: "tools"
  rules_file: "rules/RULES.md"

tags:
  - "data-pipeline"
  - "forensics"
  - "provenance"
  - "postgres"
  - "qdrant"
  - "ocr"
```

---

## rulebook_packs/epstein-pipeline-pack/USAGE.md

```md
# Using this pack with rulebook-ai

rulebook-ai supports adding packs from GitHub (`github:`) or local directories (`local:`).

## Add this pack to a project (local development)
From your Epstein pipeline repository root:

```bash
uvx rulebook-ai packs add local:./rulebook_packs/epstein-pipeline-pack
uvx rulebook-ai project sync --all
```

Tip: Commit your `memory/` and `tools/` folders, but ignore generated artifacts like `.rulebook-ai/` and assistant-specific rule outputs.
```

---

## rulebook_packs/epstein-pipeline-pack/rules/RULES.md

```md
# Epstein Pipeline — Rules of Engagement (rulebook-ai pack)

You are working inside a repository that implements a **provenance-safe document analysis pipeline** for large PDF releases.

## Non-negotiables
- **Accuracy, traceability, and auditability > speed.**
- Never "invent" findings. Every claim must have an evidence trail:
  - `doc_id` (sha256) → source URL → artifact paths → offsets (chunk start/end) → extracted text.
- Prefer **idempotent** operations. If a step is re-run, it must not corrupt existing state.
- Avoid destructive actions by default. If deletion is needed, require an explicit flag and log it.

## Repository conventions
- Run everything through `make` when possible.
- Favor cross-platform execution:
  - If a step depends on system packages, prefer `docker compose` or provide OS-specific install notes.
- Any new scripts must:
  - include robust logging,
  - validate inputs,
  - fail loudly on critical errors, but continue when safe.

## How you should work
- When changing pipeline logic, update:
  - the matching doc in `memory/` (architecture + invariants),
  - and any schema migration notes.
- If you introduce a new dependency, add it to:
  - `requirements.txt` or `pyproject.toml` (whichever the repo uses),
  - and the bootstrap instructions.

## Audit trail requirements
- All pipeline steps must produce:
  - a run record (timestamp, version, inputs),
  - and a failures record (error, stack trace, doc_id).
- When writing to Postgres, store:
  - doc-level provenance (hashes, URLs, timestamps),
  - chunk offsets, and deterministic chunk IDs.

## Guardrails for publishable output
- Anything in `safe_exports/` must be review-friendly:
  - no raw PII,
  - references back to the underlying evidence.

## Commands you will use frequently
- `make vectordb-up` / `make vectordb-down`
- `make pipeline-run`
- `make db-load`
- `make embed`
- `make search Q="..."` (semantic search)
```

---

## rulebook_packs/epstein-pipeline-pack/memory/PROJECT_CONTEXT.md

```md
# Epstein Pipeline — Project Context

## Goal
Build a reproducible, provenance-safe pipeline:

Download → OCR → text extraction → chunking (overlap) → NER → Postgres (truth) → Qdrant (semantic search)

**Principle:** PDFs are stored on the filesystem; SQL stores relationships and provenance, not blobs.

## Data model (logical)
- documents: doc_id (sha256), source_url, timestamps, artifact paths
- document_text: extracted text metadata (path, encoding, hash)
- chunks: chunk_id, doc_id, offsets, chunk_text, deterministic hash
- entities: entity mentions, label, offsets, surrounding recall context
- runs: pipeline runs, versions, parameters
- failures: structured errors

## Filesystem layout (logical)
- data/raw_pdfs/
- data/ocr_pdfs/
- data/text/
- data/chunks/
- data/entities/
- data/safe_exports/
- data/manifests/manifest.jsonl
- data/runs/runs.jsonl + failures.jsonl

## Make targets (expected)
- bootstrap / dependencies
- vectordb-up / vectordb-down
- pipeline-run
- db-load
- embed
- search

## Invariants
- doc_id == sha256(raw_pdf_bytes)
- chunk IDs are deterministic (doc_id + offsets + hash)
- every entity mention ties back to a chunk (and thus offsets)
```

---

## rulebook_packs/epstein-pipeline-pack/tools/README.md

```md
# Epstein Pipeline — Tool Starters

This folder exists so rulebook-ai can copy "starter tools" into projects.
In this repo, tool starters are small helper notes and example commands.

## Quickstart
```bash
make vectordb-up
make pipeline-run
make db-load
make embed
make search Q="test query"
```

## When debugging
- Confirm Docker is running
- Confirm Postgres + Qdrant containers are healthy
- Confirm DSN is set (or `make` defaults are correct)
- Confirm the pipeline produced artifacts under `data/`
```

---

## rulebook_packs/epstein-pipeline-pack/tools/.gitignore.rulebook-generated

```gitignore
# rulebook-ai generated artifacts (do not commit)
.rulebook-ai/
.cursor/
.windsurf/
.clinerules/
GEMINI.md
CODEX.md
```
