# Pipeline Operations Guide

This guide documents the operational steps for the Epstein pipeline, including OCR, NER, relationship analysis, and vector embeddings. It complements `docs/PROJECT_LAYOUT.md` and `docs/TOOLS_AND_MCP_SERVERS.md`.

## 1) Configure sources

Create or edit a pipeline config:

```bash
uv run python epstein/epstein_files_pipeline.py init-config --out ./config.json
```

Key fields in `config.json`:

- `seed_urls`: DOJ and congressional sources to crawl for PDFs.
- `allow_domains`: strict allowlist for safe URL discovery.
- `output_dir`: output base for artifacts.
- `ocr_mode`: `auto` (default), `always`, or `skip`.
- `ocr_min_text_chars`: threshold used by `ocr_mode=auto`.

## 2) Run the pipeline

```bash
uv run python epstein/epstein_files_pipeline.py run --config ./config.json
```

Outputs (under `output_dir`):

- `downloads/`: original PDFs
- `ocr/`: OCR-processed PDFs
- `text/`: extracted text
- `chunks/`: chunked JSONL
- `entities/`: NER mentions
- `relationships/`: relationship analysis outputs (when generated)

## 3) Image OCR (non-PDF releases)

If sources include image files, run OCR with:

```bash
uv run python -m epstein.image_ocr --input-dir ./epstein_artifacts/images --output-dir ./epstein_artifacts/image_text
```

## 4) Relationship analysis

Generate co-occurrence relationships from entity mentions:

```bash
uv run python -m epstein.relationship_analysis \
  --entities-dir ./epstein_artifacts/entities \
  --out ./epstein_artifacts/relationships/relationships.jsonl
```

## 5) Ingest into Postgres

```bash
uv run python -m epstein.db_ingest_artifacts \
  --artifacts-dir ./epstein_artifacts \
  --dsn postgresql://analysis:analysis@localhost:5432/analysis
```

## 6) Generate embeddings (Qdrant)

```bash
uv run python -m epstein.qdrant_embed_chunks_1 \
  --dsn postgresql://analysis:analysis@localhost:5432/analysis \
  --qdrant-url http://localhost:6333 \
  --collection epstein_chunks
```

## 7) Orchestrator (all-in-one)

Run everything with a single orchestrator command:

```bash
uv run python -m epstein.pipeline_orchestrator \
  --config ./config.json \
  --dsn postgresql://analysis:analysis@localhost:5432/analysis \
  --qdrant-url http://localhost:6333 \
  --run-ingest \
  --run-relationships
```

## 8) MCP server usage

The `epstein_files_processor` MCP server wraps the orchestrator for agent-based execution:

```bash
cd mcp_servers/epstein_files_processor
uv run python server.py --host 0.0.0.0 --port 8780
```

Use the API to start pipeline runs.
