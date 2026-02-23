# Epstein Project - Knowledge Base

## Quick Reference

**Project**: OpenDiscourse - provenance-safe document analysis pipeline for governance data  
**Status**: Active development  
**Branch**: `main` (default)  
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
| `TASKS.md` | Current task list with priorities |
| `docs/KNOWLEDGE_BASE.md` | This file - always reference first |
| `docs/ARCHITECTURE.md` | Logical layers, data flow |
| `docs/AGENTS_AND_TOOLS.md` | Agent implementations, tool definitions |
| `docs/PROJECT_SUMMARY.md` | High-level overview, current phase |

---

## Current Priorities (from TASKS.md)

### 🔴 Critical
1. **TASK-001**: Fix Rich Dashboard Hanging Issue
2. **TASK-002**: Add PYTHONPATH Configuration  
3. **TASK-003**: Create Installation Script for OCR Dependencies

### 🟡 Important
4. **TASK-004**: Add Example Configuration Files
5. **TASK-005**: Create Real-World Usage Examples
6. **TASK-006**: Enhance Validation Script
7. **TASK-007**: Add CI/CD GitHub Actions Workflow

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
make bootstrap           # Start Postgres + Qdrant
make down              # Stop services

# Pipeline
make pipeline-init     # Initialize config
make pipeline-run     # Run full ingestion
make db-load          # Load to Postgres
make embed            # Generate embeddings

# Development
uv run pre-commit run --all-files  # Lint & format
uv run ruff check .                # Quick lint
uv run pytest                      # Run tests
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
