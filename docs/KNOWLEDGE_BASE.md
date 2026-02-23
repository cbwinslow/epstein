# Epstein Project - Comprehensive Knowledge Base

> **AI Agent Context**: Read this file first. It contains everything you need to work on this project.

## Quick Start

```bash
# Setup
uv sync

# Run pipeline
make bootstrap          # Start DBs
make pipeline-run       # Run ingestion
make db-load           # Load to Postgres

# Development
uv run pre-commit run --all-files  # Lint & format
uv run pytest                          # Run tests
```

---

## Project Overview

**Project**: Epstein Files Document Analysis Pipeline  
**Purpose**: Provenance-safe document analysis for government releases (DOJ, FBI, House Oversight)  
**Data**: 14,676 documents, ~14.6 GB processed  
**Python**: 3.10+ (managed via `.python-version` and `pyproject.toml`)

---

## Core Principles (Non-Negotiable)

1. **Accuracy, traceability, auditability > speed**
2. **Documents are immutable, metadata evolves**
3. Every claim needs evidence: `doc_id (sha256) → source URL → artifact paths → offsets → text`
4. Prefer idempotent operations
5. Never "invent" findings

---

## File Structure

```
/                    # Root - main code and scripts
├── agents/          # AI agent implementations
├── bin/             # Executable scripts
├── config/          # Configuration files
├── db/              # Database migrations & schema
├── docs/            # Documentation (66 files)
├── epstein/         # Core pipeline code
├── examples/        # Usage examples
├── lib/             # Shared libraries
├── mcp_servers/     # MCP server implementations
├── projects/        # Sub-projects
├── rulebook_packs/  # rulebook-ai packs
├── schemas/         # JSON schemas
├── scripts/         # Utility scripts
├── tasks/           # Task definitions (YAML)
├── tests/           # Test suite
├── tools/           # CLI tools
└── vector-stack/    # Qdrant Docker setup
```

**Important Paths**:
- `docs/RULES.md` - Project rules (append-only)
- `docs/KNOWLEDGE_BASE.md` - This file
- `TASKS.md` - Current task list
- `.claude/conversations/` - Conversation logs

---

## Key Components

### Agents (in `agents/`)

| Agent | Purpose |
|-------|---------|
| `document_analysis_agent.py` | OCR, text extraction, classification |
| `epstein_data_processor.py` | Bulk document processing |
| `entity_extraction_agent.py` | NER, relationship extraction |
| `vector_db_analyzer.py` | Vector similarity search |
| `multi_agent_orchestrator.py` | Task coordination |
| `pipeline_monitor.py` | Health & performance monitoring |
| `govinfo_downloader.py` | Government API downloads |

### Core Modules (in `epstein/`)

| Module | Purpose |
|--------|---------|
| `download_manager.py` | File downloads |
| `file_organizer.py` | File organization |
| `ocr_processor.py` | OCR processing |
| `operation_monitor.py` | Pipeline monitoring |
| `telemetry.py` | OpenTelemetry instrumentation |
| `epstein_files_pipeline.py` | Main pipeline |

### MCP Servers (in `mcp_servers/`)

- `epstein_files_downloader/` - Document download API
- `epstein_comprehensive/` - Full pipeline MCP

---

## Configuration

### Environment Variables

```bash
# Database
EPSTEIN_DSN=postgresql://user:pass@localhost:5432/db

# Vector DB  
QDRANT_URL=http://localhost:6333

# OpenTelemetry (optional)
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317
```

### Config Files

- `config/agent_config.json` - Agent settings
- `pyproject.toml` - Python dependencies & tool config

---

## Commands

### Make Targets

```bash
make bootstrap       # Start Postgres + Qdrant
make down           # Stop services
make pipeline-init  # Initialize config
make pipeline-run   # Run full ingestion
make db-load       # Load to Postgres
make embed         # Generate embeddings
make doctor        # Run diagnostics
```

### Development

```bash
uv sync             # Install dependencies
uv run pytest      # Run tests
uv run ruff check .    # Lint
uv run mypy epstein/   # Type check
uv run pre-commit run --all-files  # Full check
```

---

## Coding Standards

- **Format**: black (100 char), isort
- **Lint**: ruff
- **Type**: mypy
- **Test**: pytest
- **Commit only after**: lint + typecheck pass

---

## Rules (from docs/RULES.md)

### Must Follow

- Run everything through `make` when possible
- Use `uv` for package management
- Add docstrings to all functions
- Log all operations
- Never commit secrets

### Append-Only Files

- `docs/RULES.md`
- `knowledge_base/agents.md`

---

## Current Tasks

See `TASKS.md` for full list. Key priorities:

### Critical
1. Fix Rich Dashboard hanging (TASK-001)
2. Add PYTHONPATH configuration (TASK-002)
3. Create OCR dependency install script (TASK-003)

### Important
4. Add example configuration files (TASK-004)
5. Create usage examples (TASK-005)
6. Enhance validation script (TASK-006)
7. Add CI/CD workflow (TASK-007)

---

## Error Handling

All scripts must:
- Log at appropriate levels (DEBUG, INFO, WARNING, ERROR)
- Provide actionable error messages
- Include context in errors (file, line, operation)
- Use try/except with specific exceptions
- Exit with appropriate codes

---

## Monitoring & Logging

- **Logging**: loguru (configured in each module)
- **Metrics**: OpenTelemetry (see `epstein/telemetry.py`)
- **Tracing**: OTLP export supported
- **Dashboard**: Rich-based TUI in `tools/mission_control/`

---

## Security

- Never commit secrets
- Use `.env` files (gitignored)
- Pin dependency versions
- Run security scans regularly

---

## Knowledge Base Maintenance

When making changes:
1. Update relevant docs
2. Add to CHANGELOG.md
3. Update TASKS.md if adding tasks
4. Run lint/tests before commit

---

*Last updated: 2026-02-23*
*Read this file first when starting work on the project.*
