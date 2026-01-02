# OCR Procedures

Overview
- Primary OCR: `ocrmypdf` (with `jbig2` optimization where available).
- Fallback: rasterize with `pdftoppm` then OCR with `tesseract`.

Runner
- Use `scripts/ocr_runner.py` to run a checkpointed, resumable batch.
- Default thresholds: pick files with `text` size < 500 bytes and `pdf` size >= 300k.

Usage
- Run a debug batch: `python3 scripts/ocr_runner.py --batch 10 --min-bytes 300000 --max-text-bytes 500`
- Logs are written to `epstein_project/logs/ocr` and per-file records to `epstein_project/processing_status.jsonl`.

Recommendations
- Run canary (10 files) before large runs.
- Limit concurrency to 2–4 workers on a shared server.
- Back up original `text` before replacement (runner writes backups to `epstein_project/text_pre_ocr_fix/`).

Troubleshooting
- If `ocrmypdf` fails during JBIG2 optimization, ensure `jbig2`/`jbig2enc` is in `~/.local/bin` or system path.
- For large PDFs with many images, consider using `--output-type pdf` to avoid PDF/A conversion overhead.
