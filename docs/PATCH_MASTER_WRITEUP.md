# Master Patch Write-up

## Summary
This patch set focuses on scaling downloads for multi-million document releases, adding streaming/archive capabilities to the downloader MCP server, and providing tooling to validate and repair project health.

## Highlights
- **Downloader MCP enhancements**: incremental pagination, rate limiting, archive bundling, and streaming endpoints.
- **Operational docs**: updated pipeline operations and rules for large release handling.
- **Repair tooling**: new `repair_project.py` for lint/test/dependency validation with JSON reporting and optional auto-fix.
- **PR preparation helper**: `prepare_patch_pr.sh` to run validation and print next steps.

## How to Run
1. Start the downloader MCP server with rate limits:
   ```bash
   python mcp_servers/epstein_files_downloader/server.py --port 8765 --polite-delay 0.25
   ```
2. Run incremental download batches:
   ```bash
   curl -X POST http://localhost:8765/download/bulk/paginated \
     -H "Content-Type: application/json" \
     -d '{"collection_id":"court_documents","limit":1000,"offset":0,"page_size":100}'
   ```
3. Run validation suite:
   ```bash
   python scripts/repair_project.py
   ```
4. Prepare the PR:
   ```bash
   bash scripts/prepare_patch_pr.sh
   ```
