# Operational Runbook

## Start Ingestion
- Verify DB connectivity
- Verify disk space
- Start ingestion worker
- Run OCR canary: `python3 scripts/ocr_runner.py --batch 10 --min-bytes 300000 --max-text-bytes 500`

## Stop Safely
- Flush checkpoints
- Mark run paused

## Recovery
- Resume by run_id
- Validate last cursor
- Re-run OCR batches until `processing_status.jsonl` shows stable pass rates
