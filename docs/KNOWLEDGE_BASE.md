# Epstein Project - Knowledge Base

## Quick Reference

**Project**: OpenDiscourse - provenance-safe document analysis pipeline for governance data  
**Status**: 79% Complete (15/19 milestone tasks)  
**Data Processed**: 14,676 documents, ~14.6 GB

---

## Essential Context

### Core Principles
- **Accuracy, traceability, auditability > speed**
- Documents are immutable, metadata evolves
- Every claim needs evidence trail: `doc_id (sha256) → source URL → artifact paths → offsets → extracted text`
- Prefer idempotent operations

### Key Files (Reference These)
| Document | Purpose |
|----------|---------|
| `docs/RULES.md` | Rules of engagement, coding standards |
| `docs/TASKS.md` | Master task list with milestone progress |
| `docs/ARCHITECTURE.md` | Logical layers, data flow |
| `docs/AGENTS_AND_TOOLS.md` | Agent implementations, tool definitions |
| `docs/PROJECT_SUMMARY.md` | High-level overview, current phase |
| `issues.json` | GitHub issue templates |

---

## Current Priorities (from TASKS.md)

### P0 - Must Fix
1. **Issue #52**: Database schema validation (M1-T02)
2. **Issue #53**: Test suite implementation (M5-T04)

### P1 - Important
3. **Issue #54**: Search functionality validation (M2-T02)
4. **Issue #55**: Database loading verification (M3-T03)
5. **Issue #56**: Establish query playbook (M4-T01)
6. **Issue #57**: Produce 10 evidence-bound findings (M4-T02)

---

## Completed Milestones

| Milestone | Status | Notes |
|-----------|--------|-------|
| M0 - Pre-flight & Architecture | 2/2 ✅ | Repo hygiene, doctor checks |
| M1 - Infrastructure Bootstrap | 1/2 ✅ | Postgres + Qdrant up |
| M2 - Config & Demo Proof | 1/2 ✅ | Offline demo runs |
| M3 - Real Ingestion | 2/3 ✅ | Seed URLs, pipeline run |
| M4 - Analysis & Relationship Mining | 0/2 ❌ | Not started |
| M5 - Mission Control & Observability | 4/5 ✅ | TUI, telemetry, issue generator |

---

## Tech Stack

- **Database**: PostgreSQL (primary metadata store)
- **Vector DB**: Qdrant (embeddings, semantic search)
- **OCR**: Tesseract
- **NER**: spaCy (en_core_web_sm)
- **Embeddings**: text-embedding-ada-002
- **Language**: Python 3
- **Package Manager**: uv
- **CLI**: rich, textual

---

## Commands

```bash
# Infrastructure
make vectordb-up      # Start Postgres + Qdrant
make vectordb-down   # Stop services

# Pipeline
make pipeline-run    # Run full ingestion
make db-load         # Load to Postgres
make embed           # Generate embeddings
make search Q="..."  # Semantic search

# Development
uv run pre-commit run --all-files  # Lint & format
uv run pytest                           # Run tests
```

---

## Coding Standards

- **Format**: black (100 char line length), isort --profile black
- **Lint**: ruff --fix
- **Type**: mypy
- **Test**: pytest
- **Commit only after**: lint + typecheck pass

---

## Conversation Log

- **Location**: `.claude/conversations/YYYY-MM-DD.json`
- **Format**: JSON Lines (one entry per line)
- **Commands**: `/save`, `/conversations`, `/resume`

---

## Notes

- This is a long-lived research platform for governance data
- Designed for AI-assisted exploration without hallucination
- Safe exports go to `epstein_artifacts/safe_exports/`
- All pipeline steps must produce run records and failures records

---

*Last updated: 2026-02-23*
*This document should be updated whenever significant context changes.*
