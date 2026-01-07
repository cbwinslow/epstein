# Epstein Files Processor MCP Server

This MCP server runs the end-to-end pipeline (download → OCR → NER → relationships → embeddings) by invoking `epstein.pipeline_orchestrator`.

## Features

- Start pipeline runs from AI agents
- Optional Postgres ingestion + Qdrant embeddings
- Optional image OCR for standalone image releases
- Relationship co-occurrence outputs

## Run locally

```bash
cd mcp_servers/epstein_files_processor
uv run python server.py --host 0.0.0.0 --port 8780
```

## API

- `POST /process/run`: start a pipeline run
- `GET /process/status/{task_id}`: get a run status
- `GET /process/status`: list all runs

### Example request

```bash
curl -X POST http://localhost:8780/process/run \
  -H "Content-Type: application/json" \
  -d '{
    "config_path": "./config.json",
    "artifacts_dir": "./epstein_artifacts",
    "dsn": "postgresql://analysis:analysis@localhost:5432/analysis",
    "qdrant_url": "http://localhost:6333",
    "run_ingest": true,
    "run_relationships": true,
    "run_embeddings": false,
    "run_image_ocr": false
  }'
```
