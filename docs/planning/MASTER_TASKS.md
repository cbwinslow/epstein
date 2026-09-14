# MASTER_TASKS

- **task: Verify repo hygiene**
  Ensure no artifacts/secrets committed; .env is not tracked.

---
Milestone: Pre-flight & Architecture
Task ID: M0-T01
  labels: task, m0

- **task: Run doctor checks**
  Validate Docker, compose, ports, disk, volumes.

---
Milestone: Pre-flight & Architecture
Task ID: M0-T02
  labels: task, m0

- **task: Bring up Postgres + Qdrant**
  Start docker compose services; ensure localhost-bound ports.

---
Milestone: Infrastructure Bootstrap
Task ID: M1-T01
  labels: task, m1

- **task: Validate schema exists**
  doc_analysis schema and tables present.

---
Milestone: Infrastructure Bootstrap
Task ID: M1-T02
  labels: task, m1

- **task: Run offline demo end-to-end**
  Use bundled demo pdf to validate pipeline, db-load, embed, search.

---
Milestone: Config & Demo Proof
Task ID: M2-T01
  labels: task, m2

- **task: Search returns results**
  Validate semantic search returns evidence payload.

---
Milestone: Config & Demo Proof
Task ID: M2-T02
  labels: task, m2

- **task: Curate seed URLs and allowlist**
  Select small initial set; document rationale.

---
Milestone: Real Ingestion (Controlled)
Task ID: M3-T01
  labels: task, m3

- **task: Pipeline run on real sources**
  Download/OCR/extract/chunk/NER with logs.

---
Milestone: Real Ingestion (Controlled)
Task ID: M3-T02
  labels: task, m3

- **task: Load to Postgres and verify counts**
  Ingest artifacts into Postgres.

---
Milestone: Real Ingestion (Controlled)
Task ID: M3-T03
  labels: task, m3

- **task: Establish query playbook**
  Define initial query sets and how to corroborate.

---
Milestone: Analysis & Relationship Mining
Task ID: M4-T01
  labels: task, m4

- **task: Produce 10 evidence-bound findings**
  Use the finding issue template to record evidence-bound notes.

---
Milestone: Analysis & Relationship Mining
Task ID: M4-T02
  labels: task, m4

- **task: Design Mission Control**
  Document features, UI layout, integration points, and ADR in `docs/MISSION_CONTROL.md` and `docs/DECISIONS.md`.

---
Milestone: Mission Control & Observability
Task ID: M5-T01
  labels: task, m5

- **task: Implement TUI PoC**
  Minimal Textual PoC `tools/mission_control/app.py` + CLI `bin/mission-control`.

---
Milestone: Mission Control & Observability
Task ID: M5-T02
  labels: task, m5

- **task: Add OpenTelemetry instrumentation**
  Add `epstein.telemetry` helper and `OTEL_*` env vars, include doctor checks.

---
Milestone: Mission Control & Observability
Task ID: M5-T03
  labels: task, m5

- **task: Tests & CI for Mission Control**
  Add pytest tests for TUI, telemetry, doctor; update CI to run these tests.

---
Milestone: Mission Control & Observability
Task ID: M5-T04
  labels: task, m5

- **task: Add issue generator + create GitHub issues for these tasks**
  Add `scripts/gen_issues_from_tasks.py` to generate `issues.json` and optionally create issues via `gh` CLI.

---
Milestone: Mission Control & Observability
Task ID: M5-T05
  labels: task, m5
