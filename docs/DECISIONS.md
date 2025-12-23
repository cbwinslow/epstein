# Architectural Decisions

This document records **why** decisions were made, not just what was built.

---

## 001 — PostgreSQL as Primary Metadata Store

**Decision:** Use PostgreSQL for all structured data and metadata.

**Reasoning:**
- Strong relational modeling
- Mature tooling
- JSONB flexibility
- Extensions (pgvector, PostGIS)

**Alternatives Considered:**
- MongoDB
- Elastic-only approach

---

## 002 — Documents Stored Outside the Database

**Decision:** Store raw documents on filesystem or object storage.

**Reasoning:**
- Avoid database bloat
- Easier backups
- Cleaner lifecycle management
- Better performance

**DB stores:** references, hashes, metadata, extracted text.

---

## 003 — Idempotent Ingestion

**Decision:** All ingestion must be safe to re-run.

**Reasoning:**
- Network failures are normal
- Large datasets require resumability
- Prevents duplication and corruption
