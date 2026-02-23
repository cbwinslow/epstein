# Architecture Overview

## Core Principle

**Documents are immutable. Metadata evolves.**

The system treats original source documents as immutable artifacts and allows metadata, annotations, and derived data to evolve independently.

## Logical Layers

### 1. Data Sources
- govinfo.gov (bulk + API)
- congress.gov
- openstates.org
- Future: state & local sources

### 2. Ingestion Layer
- Source-specific adapters
- Pagination + rate-limit handling
- Idempotent fetch logic
- Resume support via checkpoints

### 3. Storage Layer
- PostgreSQL: structured data + metadata
- Filesystem / object storage: raw documents
- Hash-based deduplication

### 4. Processing Layer
- OCR for image-based documents
- Text extraction
- Normalization & parsing

### 5. Analysis Layer (Future)
- Embeddings
- RAG pipelines
- Agent-based analysis
- Dashboards & APIs

## Data Flow (Simplified)

Source → Ingestion → Raw Storage → Parsing/OCR → PostgreSQL → Analysis

## Failure Model

- Any step may fail independently
- Failures are logged
- Ingestion can resume without duplication
