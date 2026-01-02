# GitHub OCR Action

This workflow runs OCR and analysis on a supplied manifest and uploads artifacts.

Usage
- Trigger via Actions > OCR Action > Supply `manifest_path` (default: `manifests/ocr_manifest_example.json`).
- Workflow steps:
  - Checkout code
  - Install system deps (poppler, tesseract)
  - Run `scripts/ocr_runner.py --input-manifest <manifest>`
  - Run `scripts/ocr_summary.py`
  - Chunk text and run `scripts/embed_chunks.py` (optional; controlled by workflow input)
  - Upload artifacts: `processing_status.jsonl`, `ocr_summary.json`, logs, chunks, embeddings
  - Run `scripts/ocr_watch.py` to ingest and emit alerts

Configuration
- Inputs:
  - `manifest_path` - path to JSON manifest listing files to process
  - `run_embeddings` - 'true'|'false' to control embeddings step
  - `model` - sentence-transformers model to use for local embedding

Secrets
- If using remote embedding (OpenRouter), set `OPENROUTER_API_KEY` in repository secrets and modify `scripts/embed_chunks.py` to enable remote embedding.

Outputs & Monitoring
- Artifacts are uploaded to the workflow run and can be downloaded.
- The `ocr_summary.json` file contains metrics and top failures for quick inspection.
