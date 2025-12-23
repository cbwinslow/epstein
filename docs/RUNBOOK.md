# Operational Runbook

## Start Ingestion
- Verify DB connectivity
- Verify disk space
- Start ingestion worker

## Stop Safely
- Flush checkpoints
- Mark run paused

## Recovery
- Resume by run_id
- Validate last cursor
