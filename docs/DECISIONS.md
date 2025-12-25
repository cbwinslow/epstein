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

---

## 004 — Mission Control TUI (Textual) + OpenTelemetry

**Decision:** Implement a terminal-based Mission Control UI using Textual, and instrument agents and the UI using OpenTelemetry for traces and metrics.

**Reasoning:**
- Textual provides a high-productivity, modern TUI toolkit with pane layout and async support
- OpenTelemetry enables standardized traces/metrics for distributed workflows and easy integration with OTLP backends (console/collector)
- A central TUI reduces the risk of duplicating agent logic by orchestrating existing agents instead of reimplementing them

**Alternatives Considered:**
- Simple CLI only (insufficient for visualization)
- Web dashboard (more infra and complexity)

**Consequences:**
- Add optional dependencies (textual, opentelemetry SDK)
- Provide a config/doctor check to validate OTLP endpoint when enabled
