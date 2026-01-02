# Tasks — OpenDiscourse

## Ingestion
- [ ] Design ingestion run tracking table
- [ ] Implement govinfo.gov bulk downloader
- [ ] Add pagination + retry logic
- [ ] Resume interrupted runs

## Database
- [ ] Finalize canonical schema
- [ ] Implement migrations
- [ ] Add indexes for search
- [ ] Add deduplication constraints

## Storage
- [ ] Define directory layout for documents
- [ ] Implement hash-based file naming
- [ ] Track file paths in DB

## OCR & Parsing
- [ ] Detect image-only PDFs
- [ ] OCR pipeline
- [ ] Store extracted text
- [ ] Confidence scoring
- [ ] Add unit tests for OCR runner and chunking (`tests/test_ocr_runner_unit.py`, `tests/test_chunking.py`)
- [ ] Add integration tests for OCR end-to-end (`tests/test_integration_ocr.py`)
- [ ] Add debugging docs (`docs/ocr_debugging.md`, `docs/debug_agents.md`)
- [ ] Add CI workflow to run OCR canary tests on PRs (`.github/workflows/ocr-tests.yml`)

## Ops
- [ ] Logging standard
- [ ] Config management
- [ ] Backups

## MCP Server (cbwinslow)
- [x] Create MCP server architecture and basic endpoints
- [x] Implement collection discovery from govinfo.gov
- [x] Add download queue and progress tracking
- [x] Create comprehensive test suite
- [x] Test all data source connectivity
- [x] Fix Pydantic serialization bug (created_at/updated_at fields)
- [x] Fix download directory creation and filename generation
- [ ] Update DOJ and FBI data source URLs
- [ ] Implement PACER authentication system
- [ ] Add rate limiting and exponential backoff
- [ ] Improve error handling for network failures
- [ ] Add connection pooling for concurrent downloads
- [ ] Test with real PACER credentials
- [ ] Performance optimization for large downloads
- [ ] Add download resume capability
- [ ] Implement proper logging and monitoring

This file is intentionally simple and acts as the project’s task source of truth.

## OCR Hardening (New)
- [ ] Fix JBIG2 install/permissions or standardize `--optimize 0` in OCR runs
- [ ] Add OCR quality-gate report (summarize `processing_status.jsonl`, fail-rate thresholds)
- [ ] Extend OCR coverage to standalone images (batch script + status logging)
- [ ] Normalize OCR pipeline usage (choose canonical flow and deprecate the other)
- [ ] Add OCR runner unit tests and CI canary workflow
- [ ] Add per-run OCR tracking summary (run_id, config, counts, failure totals)
