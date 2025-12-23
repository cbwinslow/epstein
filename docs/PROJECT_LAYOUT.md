# Checkpoint: Project layout + storage plan

## What we are keeping

- `epstein_files_pipeline.py`  
  The core pipeline (download → OCR → text → chunk → NER → safe_exports). Keep it as the single source of truth for reproducible extraction.

- `cbw_bootstrap_project_ubuntu.sh`  
  Your one-shot project bootstrap script (system deps + uv + Python 3.10 + lock file + basic docs).

- `vector_db_bootstrap.sh`  
  The local data stack bootstrap (Qdrant + Postgres/pgvector + schema).

- `db_ingest_artifacts.py`  
  Loads pipeline outputs into Postgres, so you can query and build reports.

- `Makefile`  
  One-liners for repeatable commands.

## What we should delete (redundant)

- `setup.sh`  
  Redundant with `cbw_bootstrap_project_ubuntu.sh`.

- `project_markdown_starter_pack_uv_python_3.md`  
  Redundant once the bootstrap script is generating README/USAGE/AGENTS/RULES.

- `vector_db_bootstrap_qdrant_optional_postgres_pgvector.sh`  
  Replaced by `vector_db_bootstrap.sh` (v2) which also creates the schema.

> If you want, we can keep a `docs/` folder with the old markdown as historical reference, but it’s cleaner to remove it now.

---

## Where documents should live: filesystem vs SQL

### Best practice (recommended)
**Store PDFs on the filesystem**, and store *metadata + derived artifacts* in SQL.

**Why:**
- PDFs can be large; storing them in Postgres bloats backups and slows restores.
- File hashing + path references give you perfect provenance without database bloat.
- You can re-run OCR/text extraction without moving BLOBs around.

### What goes into Postgres
- `documents`: doc_id (sha256), source_url, file paths, bytes, timestamps
- `document_text`: extracted (redacted) text
- `chunks`: chunk_id + offsets + chunk text
- `entities`: entity mentions (label/text + provenance)
- `runs` / `failures`: auditability and reproducibility

### What *does not* go into Postgres
- Raw PDF bytes, unless you have a very specific reason.

### Vector DB usage
- Use **Qdrant** for fast semantic search across chunks
- Use **Postgres** for structured queries (filters, aggregations, joins)
- Optional: store embeddings either in Qdrant or in `doc_analysis.chunk_embeddings` (pgvector)

---

## OCR: should we insert OCR output into SQL?

**No.** OCR output should be written to the filesystem as:
- an OCR’d PDF (searchable)
- extracted text (`.txt`)

Then SQL stores the extracted text and the chunks/entities.

This gives you:
- repeatable extraction (you can always re-derive)
- smaller DB
- easier provenance

---

## Minimal checkpoint definition

You’re at a solid checkpoint when you can:
1) Run `make vectordb-up` and Postgres/Qdrant start locally.
2) Run the pipeline and get `manifest.jsonl`, `text/`, `chunks/`, `entities/`.
3) Run `make db-load DSN=...` and query in Postgres:

```sql
SELECT COUNT(*) FROM doc_analysis.documents;
SELECT label, COUNT(*) FROM doc_analysis.entities GROUP BY label ORDER BY 2 DESC;
```

Once this works, we can add:
- co-occurrence graphs
- date normalization + timelines
- custom NER patterns
- vector indexing + hybrid retrieval

