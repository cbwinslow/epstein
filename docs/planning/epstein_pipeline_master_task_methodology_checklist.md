# Epstein Files — Master Task, TODO, and Methodology Checklist

> **Purpose**: This document is a *ground-truth execution plan* for setting up, validating, operating, and analyzing the Epstein Files document pipeline.
> It is written so that **a human or an AI agent** can follow it step-by-step and *prove* completion via tests.

---

## LEGEND

- ☐ = Not started
- ☐→☑ = Has a measurable test
- ☑ = Completed
- 🧪 = Test / validation step
- ⚠️ = Common failure / troubleshooting note

---

# PHASE 0 — PRE-FLIGHT & MENTAL MODEL (DO NOT SKIP)

## 0.1 Understand the Architecture (Conceptual Lock-in)

☐ Understand that **PDFs are never stored in SQL**
☐ Understand that **Postgres = structured truth**
☐ Understand that **Qdrant = semantic similarity only**
☐ Understand that **filesystem = immutable artifacts**

🧪 Test of understanding:
- You can explain what happens if Postgres is deleted but artifacts remain
- You can explain what happens if Qdrant is deleted but Postgres remains

---

## 0.2 Threat Model & Methodology Rules

☐ No destructive operations by default
☐ Every claim must be evidence-backed
☐ Prefer *relationships* over *conclusions*
☐ Avoid narrative framing early

🧪 Test:
- You can show a finding with doc_id + chunk_id + offsets + source_url

---

# PHASE 1 — REPOSITORY & ENVIRONMENT SETUP

## 1.1 Fresh Clone Validation

☐ Clone repository
☐ Confirm repo has **no generated artifacts** committed
☐ Confirm `.env.example` exists and `.env` does not

🧪 Test:
```bash
git status --ignored
```
Expected: clean repo, ignored paths visible

---

## 1.2 Environment Doctor Checks

☐ Run `make doctor`
☐ Docker daemon detected
☐ docker compose plugin detected
☐ Disk space ≥ 2GB free
☐ No fatal port collisions

🧪 Test:
```bash
echo $?
```
Expected: exit code `0` or `2` (warnings allowed)

⚠️ If port collision:
- Change ports in `.env`
- Re-run `make doctor`

---

# PHASE 2 — INFRASTRUCTURE BOOTSTRAP (DATABASES)

## 2.1 Postgres + pgvector Setup

☐ `make bootstrap` executed
☐ Postgres container running
☐ pgvector extension installed
☐ Schema `doc_analysis` exists

🧪 Test:
```sql
SELECT schema_name FROM information_schema.schemata WHERE schema_name='doc_analysis';
```
Expected: 1 row

---

## 2.2 Qdrant Setup

☐ Qdrant container running
☐ REST endpoint reachable
☐ Storage volume mounted

🧪 Test:
```bash
curl http://localhost:6333/
```
Expected: JSON with version info

---

## 2.3 Existing Infrastructure (Optional Path)

☐ Ran `scripts/configure.py`
☐ External Postgres validated
☐ External Qdrant validated
☐ `.env` written

🧪 Test:
```bash
cat .env
```
Expected: EPSTEIN_DSN and QDRANT_URL present

---

# PHASE 3 — PIPELINE INITIALIZATION

## 3.1 Config Generation

☐ Ran `make pipeline-init`
☐ `config.json` created
☐ Default values understood

🧪 Test:
```bash
jq . config.json
```
Expected: valid JSON

---

## 3.2 Source Selection (CRITICAL THINKING)

☐ Seed URLs chosen deliberately
☐ Domains allow-listed
☐ Scope intentionally constrained

⚠️ Methodology warning:
> Wide ingestion early = noise. Start small.

🧪 Test:
- Can explain why each seed URL was chosen

---

# PHASE 4 — DOCUMENT INGESTION & ARTIFACT CREATION

## 4.1 Pipeline Run

☐ `make pipeline-run` executed
☐ PDFs downloaded
☐ OCR performed where needed
☐ Text extracted

🧪 Tests:
```bash
ls epstein_artifacts/raw_pdfs
ls epstein_artifacts/text
```
Expected: non-empty directories

---

## 4.2 Chunking Validation

☐ Chunks created with overlap
☐ Offsets deterministic

🧪 Test:
```bash
jq 'length' epstein_artifacts/chunks/*.jsonl
```
Expected: >0 chunks per doc

---

## 4.3 Entity Extraction Validation

☐ spaCy model loaded
☐ Entities written to JSONL

🧪 Test:
```bash
jq '.label' epstein_artifacts/entities/*.jsonl | sort | uniq -c
```
Expected: PERSON / ORG / GPE etc

---

# PHASE 5 — DATABASE INGESTION

## 5.1 Artifact → Postgres Load

☐ `make db-load` executed
☐ Documents inserted
☐ Chunks inserted
☐ Entities inserted

🧪 Tests:
```sql
SELECT COUNT(*) FROM doc_analysis.documents;
SELECT COUNT(*) FROM doc_analysis.chunks;
SELECT COUNT(*) FROM doc_analysis.entities;
```
Expected: all > 0

---

## 5.2 Provenance Integrity Checks

☐ doc_id uniqueness verified
☐ chunk offsets consistent
☐ source_url preserved

🧪 Test:
```sql
SELECT doc_id, COUNT(*) FROM doc_analysis.documents GROUP BY doc_id HAVING COUNT(*) > 1;
```
Expected: zero rows

---

# PHASE 6 — EMBEDDINGS & SEMANTIC SEARCH

## 6.1 Embedding Generation

☐ `make embed` executed
☐ Qdrant collection created
☐ Points inserted

🧪 Tests:
```bash
curl http://localhost:6333/collections
```
Expected: collection present

---

## 6.2 Semantic Search Validation

☐ `make search Q="..."` returns results
☐ Payload includes doc_id + chunk_id

🧪 Test:
- Query: "flight", "island", "meeting"
- Confirm results are coherent

---

# PHASE 7 — ANALYSIS METHODOLOGY (THE IMPORTANT PART)

## 7.1 How to Perform Analysis (DO THIS SLOWLY)

☐ Start with **broad semantic queries**
☐ Identify recurring entities
☐ Track co-occurrence across documents
☐ Look for temporal clustering

⚠️ Rule:
> Never jump to conclusions from a single chunk.

---

## 7.2 Relationship Discovery Workflow

☐ Pick entity A (person/org)
☐ Query semantic space for entity A
☐ Extract co-mentioned entities
☐ Validate across *multiple documents*

🧪 Test:
- Same relationship appears in ≥ 2 documents

---

## 7.3 Pattern Types Worth Investigating

☐ Repeated travel references
☐ Repeated financial institutions
☐ Repeated intermediaries (law firms, shell orgs)
☐ Sudden disappearance of names

---

# PHASE 8 — SAFE EXPORTS & PUBLICATION (FUTURE)

## 8.1 Safe Export Rules

☐ Redacted excerpts only
☐ Evidence metadata preserved
☐ No narrative framing

---

## 8.2 Publication Readiness Checklist

☐ Findings reproducible
☐ Queries documented
☐ Data lineage clear

---

# PHASE 9 — FAILURE MODES & TROUBLESHOOTING

## 9.1 Pipeline Failures

☐ Inspect `failures.jsonl`
☐ Re-run idempotently
☐ Never delete artifacts

---

## 9.2 Data Quality Issues

☐ OCR noise detected
☐ Flag for manual review
☐ Consider re-OCR with different params

---

# PHASE 10 — CONFIDENCE CHECK (FINAL)

☐ You can recreate the entire system from scratch
☐ You can explain every table
☐ You can justify every claim with evidence

🧪 Final Test:
> Delete containers + volumes → re-run → get same doc_ids

---

## END STATE

If all boxes are checked, the project is:

✔ Reproducible
✔ Auditable
✔ Methodologically sound
✔ Ready for careful analysis

**This checklist is intentionally long. That’s the point.**
