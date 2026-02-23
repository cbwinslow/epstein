-- =============================================================================
-- File: schema.sql
-- Date: 2025-12-23
-- Author: cbwinslow + ChatGPT
-- Summary:
--   Core OpenDiscourse schema for ingestion runs, documents, deduplication,
--   and extracted text. Designed for idempotent ingestion with strong provenance.
--
-- Notes:
--   - Store binaries outside Postgres; store hashes + paths here.
--   - Use UUIDs for primary keys.
-- =============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS ingestion_runs (
  run_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_name      TEXT NOT NULL,
  started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at      TIMESTAMPTZ NULL,
  status           TEXT NOT NULL DEFAULT 'running',
  cursor_json      JSONB NOT NULL DEFAULT '{}'::jsonb,
  stats_json       JSONB NOT NULL DEFAULT '{}'::jsonb,
  error_summary    TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_source ON ingestion_runs(source_name);
CREATE INDEX IF NOT EXISTS idx_ingestion_runs_status ON ingestion_runs(status);

CREATE TABLE IF NOT EXISTS documents (
  document_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_name      TEXT NOT NULL,
  source_doc_id    TEXT NULL,
  doc_type         TEXT NOT NULL,
  jurisdiction     TEXT NULL,
  title            TEXT NULL,
  published_at     TIMESTAMPTZ NULL,
  file_path        TEXT NULL,
  content_type     TEXT NULL,
  sha256           TEXT NOT NULL,
  meta_json        JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_name, source_doc_id),
  UNIQUE (sha256)
);

CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source_name);
CREATE INDEX IF NOT EXISTS idx_documents_doctype ON documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_documents_published ON documents(published_at);

CREATE TABLE IF NOT EXISTS document_text (
  text_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id      UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
  extracted_text   TEXT NOT NULL,
  extraction_type  TEXT NOT NULL DEFAULT 'text',
  ocr_confidence   NUMERIC NULL,
  page_count       INT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_document_text_document_id ON document_text(document_id);

CREATE TABLE IF NOT EXISTS ingestion_events (
  event_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id           UUID NOT NULL REFERENCES ingestion_runs(run_id) ON DELETE CASCADE,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  level            TEXT NOT NULL DEFAULT 'INFO',
  message          TEXT NOT NULL,
  detail_json      JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_ingestion_events_run ON ingestion_events(run_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_events_level ON ingestion_events(level);

COMMIT;
