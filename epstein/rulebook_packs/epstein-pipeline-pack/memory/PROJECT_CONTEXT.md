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