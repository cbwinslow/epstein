# Ingestion Design

## Principles
- Idempotent
- Resume-safe
- Source-aware
- Rate-limit respectful

## Ingestion Runs
Each run has:
- run_id
- source
- start_time / end_time
- status
- cursor/checkpoint
- error_log

## Resume Strategy
- Persist last successful cursor
- Skip already-ingested hashes
- Never overwrite files

## Failure Handling
- Retry transient errors
- Persist fatal errors
- Resume without duplication
