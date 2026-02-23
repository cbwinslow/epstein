<todos title="Add Codex Agent" rule="Review steps frequently throughout the conversation and DO NOT stop between steps unless they explicitly require it.">
- [x] 1: Add `codex_agent` entry to `config/agent_config.json` and create initial agent file `agents/codex_agent.py` with scaffold and metadata 🔴
- [x] 2: Implement `CodexAgent` methods (generate_code, explain_code, suggest_tests) and register tools and AGENT_INFO 🔴
- [x] 3: Add unit tests `tests/test_codex_agent.py` covering key methods and metadata 🟡
- [x] 4: Update `agents/README.md` to document the new Codex agent and usage examples 🟢
- [x] 5: Run test suite and fix any issues; ensure linter/type checks pass 🟡
  _Full test run completed; all Codex agent tests passed. One unrelated test (`tests/test_ingestion_pipeline.py`) still fails due to missing `scripts.ingestion_utils` module - needs follow-up._
- [x] 6: Install missing test dependencies (qdrant_client, pdfplumber, fastapi, pytest-asyncio, openai) and run full test suite; address any failures 🟡
- [x] 7: Integrate Codex agent with OpenAI-compatible toolset and add tests + docs 🔴
  _Added `OPENAI_FUNCTIONS`, `build_openai_request` and `call_openai` (dry-run by default), config flags in `config/agent_config.json`, and tests in `tests/test_codex_agent_openai.py`._
</todos>

# Epstein Project - GitHub Copilot Instructions

## Project Overview
The Epstein project is a comprehensive data processing pipeline for analyzing PDF documents. It includes OCR (Optical Character Recognition), text extraction, chunking, Named Entity Recognition (NER), embeddings generation, and vector search capabilities using Qdrant and PostgreSQL.

## Key Technologies & Stack
- **Python 3.10** (always use this version)
- **uv** for Python package management
- **Docker** & **Docker Compose** for containerization
- **PostgreSQL** with pgvector extension for structured data
- **Qdrant** for vector search
- **OCR tools**: OCRmyPDF, Tesseract
- **NLP**: spaCy for NER
- **Web scraping**: requests, BeautifulSoup, lxml

## Development Guidelines
- Use `uv` for all Python dependency management
- Always pin Python version to 3.10
- Follow PEP 8 style guidelines
- Use type hints extensively
- Write comprehensive docstrings
- Implement proper error handling and logging
- Use async/await for I/O operations where beneficial

## Code Structure
- `epstein/` - Main pipeline code
- `scripts/` - Utility scripts
- `docs/` - Documentation
- `projects/` - Subprojects and bundles
- `docker/` - Docker configurations

## Common Patterns
- Data classes for configuration
- Factory patterns for pipeline components
- Context managers for resource handling
- Command-line interfaces with Click or argparse

## Database Schema
- `documents` table for metadata
- `document_text` for extracted text
- `chunks` for text chunks with offsets
- `entities` for NER results
- Vector embeddings stored in Qdrant

## Docker Development
- Use `make` commands for common operations
- Bootstrap with `make bootstrap`
- Run pipeline with `make pipeline-run`
- Load data with `make db-load`
- Run health checks with `python scripts/doctor.py` (quick checks) or `python scripts/doctor.py --check-db` (includes Postgres reachability). Use `make doctor-check` in CI to fail on unhealthy services.

## Security & Privacy
- Handle sensitive document data carefully
- Implement redaction where necessary
- Use environment variables for secrets
- Follow data minimization principles

## Testing
- Write unit tests for core functions
- Integration tests for pipeline components
- Use pytest framework
- Mock external dependencies
- Verify snapshot bundles in `docs/files/` with `scripts/verify_bundle.sh` and CI workflow `.github/workflows/verify-bundles.yml`
- Collect task logs with `epstein.utils.task_logger.TaskLogger` and summary with `scripts/collect_task_logs.py` (used in CI artifacts)

## Performance Considerations
- Process documents in batches
- Use streaming for large files
- Implement caching where appropriate
- Monitor memory usage with large documents

## AI/LLM Integration
- Use embeddings for semantic search
- Implement hybrid search (keyword + vector)
- Consider fine-tuning for domain-specific NER
- Evaluate model performance metrics

## Deployment
- Container-first approach
- Use Docker Compose for local development
- Implement health checks
- Configure proper logging and monitoring

Remember: This is a research/data processing project. Always prioritize data integrity, reproducibility, and ethical handling of information.
