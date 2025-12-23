#!/usr/bin/env python3
# ==============================================================================
# Script Name: db_ingest_artifacts.py
# Date: 2025-12-19
# Author: ChatGPT (for Blaine Winslow / cbwinslow)
# Summary:
#   Loads outputs from epstein_files_pipeline.py into Postgres (doc_analysis schema).
#
#   This script is intentionally separate from the pipeline so you can:
#     - run the pipeline offline without DB access
#     - re-load / rebuild DB indices safely
#     - keep the pipeline simple and auditable
#
# What it ingests:
#   - manifest.jsonl              -> doc_analysis.documents
#   - runs.jsonl                  -> doc_analysis.runs
#   - failures.jsonl              -> doc_analysis.failures
#   - text/*.txt                  -> doc_analysis.document_text
#   - chunks/*.chunks.jsonl       -> doc_analysis.chunks
#   - entities/*.entities.jsonl   -> doc_analysis.entities
#
# Storage strategy (recommended):
#   - PDFs live on filesystem/object storage (NOT in SQL)
#   - SQL stores metadata, text, chunks, entities, relationships
#   - Optionally store embeddings (pgvector or Qdrant)
#
# Inputs:
#   --artifacts-dir PATH   Path to pipeline output_dir (default: ./epstein_artifacts)
#   --dsn DSN              Postgres DSN (e.g., postgresql://user:pass@localhost:5432/analysis)
#   --truncate             Truncate tables before loading (DANGEROUS)
#   --verbose
#
# Outputs:
#   - Populated Postgres tables in doc_analysis schema
#
# Dependencies:
#   uv add psycopg[binary]
#
# Modification Log:
#   - 2025-12-19: Initial version
# ==============================================================================

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Optional

import psycopg
from psycopg.rows import dict_row


# ------------------------------
# Logging
# ------------------------------

def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


# ------------------------------
# IO helpers
# ------------------------------

def iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


# ------------------------------
# DB helpers
# ------------------------------

TRUNCATE_SQL = """
TRUNCATE TABLE
  doc_analysis.chunk_embeddings,
  doc_analysis.entities,
  doc_analysis.chunks,
  doc_analysis.document_text,
  doc_analysis.failures,
  doc_analysis.runs,
  doc_analysis.documents
CASCADE;
"""


def ensure_schema_exists(conn: psycopg.Connection) -> None:
    # Safety: ensure schema exists even if initdb didn't run (e.g., existing DB)
    conn.execute("CREATE SCHEMA IF NOT EXISTS doc_analysis")


def upsert_document(conn: psycopg.Connection, obj: Dict[str, Any]) -> None:
    doc_id = str(obj.get("sha256") or "").strip()
    if not doc_id:
        return

    conn.execute(
        """
        INSERT INTO doc_analysis.documents
          (doc_id, source_url, original_path, bytes, sha256, downloaded_at, meta)
        VALUES
          (%(doc_id)s, %(source_url)s, %(original_path)s, %(bytes)s, %(sha256)s,
           to_timestamp(%(ts)s), %(meta)s::jsonb)
        ON CONFLICT (doc_id) DO UPDATE SET
          source_url = EXCLUDED.source_url,
          original_path = COALESCE(EXCLUDED.original_path, doc_analysis.documents.original_path),
          bytes = COALESCE(EXCLUDED.bytes, doc_analysis.documents.bytes),
          downloaded_at = COALESCE(EXCLUDED.downloaded_at, doc_analysis.documents.downloaded_at),
          meta = doc_analysis.documents.meta || EXCLUDED.meta;
        """,
        {
            "doc_id": doc_id,
            "source_url": str(obj.get("url") or ""),
            "original_path": str(obj.get("path") or ""),
            "bytes": obj.get("bytes"),
            "sha256": doc_id,
            "ts": int(obj.get("ts") or 0),
            "meta": json.dumps({"manifest": obj}, ensure_ascii=False),
        },
    )


def upsert_run(conn: psycopg.Connection, obj: Dict[str, Any]) -> None:
    run_id = str(obj.get("run_id") or "").strip()
    if not run_id:
        return

    conn.execute(
        """
        INSERT INTO doc_analysis.runs
          (run_id, config_hash, ts_start, ts_end, status, counts, seed_urls)
        VALUES
          (%(run_id)s, %(config_hash)s,
           to_timestamp(%(ts_start)s), to_timestamp(%(ts_end)s),
           %(status)s, %(counts)s::jsonb, %(seed_urls)s::jsonb)
        ON CONFLICT (run_id) DO UPDATE SET
          config_hash = EXCLUDED.config_hash,
          ts_start = COALESCE(EXCLUDED.ts_start, doc_analysis.runs.ts_start),
          ts_end = COALESCE(EXCLUDED.ts_end, doc_analysis.runs.ts_end),
          status = EXCLUDED.status,
          counts = EXCLUDED.counts,
          seed_urls = EXCLUDED.seed_urls;
        """,
        {
            "run_id": run_id,
            "config_hash": obj.get("config_hash"),
            "ts_start": int(obj.get("ts_start") or 0),
            "ts_end": int(obj.get("ts_end") or 0),
            "status": obj.get("status"),
            "counts": json.dumps(obj.get("counts") or {}, ensure_ascii=False),
            "seed_urls": json.dumps(obj.get("seed_urls") or [], ensure_ascii=False),
        },
    )


def insert_failure(conn: psycopg.Connection, obj: Dict[str, Any]) -> None:
    # Append-only; de-dupe is not critical here.
    conn.execute(
        """
        INSERT INTO doc_analysis.failures
          (run_id, stage, doc_id, url, error, ts, details)
        VALUES
          (%(run_id)s, %(stage)s, %(doc_id)s, %(url)s, %(error)s,
           CASE WHEN %(ts)s IS NULL THEN NULL ELSE to_timestamp(%(ts)s) END,
           %(details)s::jsonb);
        """,
        {
            "run_id": obj.get("run_id"),
            "stage": obj.get("stage"),
            "doc_id": obj.get("doc_id"),
            "url": obj.get("url"),
            "error": obj.get("error"),
            "ts": obj.get("ts"),
            "details": json.dumps(obj, ensure_ascii=False),
        },
    )


def upsert_document_text(conn: psycopg.Connection, doc_id: str, text: str) -> None:
    if not doc_id:
        return
    conn.execute(
        """
        INSERT INTO doc_analysis.document_text
          (doc_id, text, redacted, extracted_at, meta)
        VALUES
          (%(doc_id)s, %(text)s, TRUE, now(), '{}'::jsonb)
        ON CONFLICT (doc_id) DO UPDATE SET
          text = EXCLUDED.text,
          extracted_at = EXCLUDED.extracted_at;
        """,
        {"doc_id": doc_id, "text": text},
    )


def upsert_chunk(conn: psycopg.Connection, obj: Dict[str, Any]) -> None:
    doc_id = str(obj.get("doc_id") or "").strip()
    if not doc_id:
        return
    conn.execute(
        """
        INSERT INTO doc_analysis.chunks
          (doc_id, chunk_id, char_start, char_end, preview, text, source_url)
        VALUES
          (%(doc_id)s, %(chunk_id)s, %(char_start)s, %(char_end)s, %(preview)s, %(text)s, %(source_url)s)
        ON CONFLICT (doc_id, chunk_id) DO UPDATE SET
          char_start = EXCLUDED.char_start,
          char_end = EXCLUDED.char_end,
          preview = EXCLUDED.preview,
          text = EXCLUDED.text,
          source_url = EXCLUDED.source_url;
        """,
        {
            "doc_id": doc_id,
            "chunk_id": int(obj.get("chunk_id") or 0),
            "char_start": int(obj.get("char_start") or 0),
            "char_end": int(obj.get("char_end") or 0),
            "preview": obj.get("preview"),
            "text": obj.get("text") or "",
            "source_url": obj.get("source_url"),
        },
    )


def insert_entity(conn: psycopg.Connection, obj: Dict[str, Any]) -> None:
    doc_id = str(obj.get("doc_id") or "").strip()
    if not doc_id:
        return
    conn.execute(
        """
        INSERT INTO doc_analysis.entities
          (doc_id, chunk_id, label, text, char_start, char_end, source_url, pdf_path)
        VALUES
          (%(doc_id)s, %(chunk_id)s, %(label)s, %(text)s, %(char_start)s, %(char_end)s, %(source_url)s, %(pdf_path)s);
        """,
        {
            "doc_id": doc_id,
            "chunk_id": int(obj.get("chunk_id") or 0),
            "label": obj.get("label"),
            "text": obj.get("text"),
            "char_start": obj.get("char_start"),
            "char_end": obj.get("char_end"),
            "source_url": obj.get("source_url"),
            "pdf_path": obj.get("pdf_path"),
        },
    )


# ------------------------------
# Main loader
# ------------------------------

@dataclass
class Paths:
    base: Path
    manifest: Path
    runs: Path
    failures: Path
    text_dir: Path
    chunks_dir: Path
    entities_dir: Path


def resolve_paths(artifacts_dir: Path) -> Paths:
    base = artifacts_dir
    return Paths(
        base=base,
        manifest=base / "manifest.jsonl",
        runs=base / "runs.jsonl",
        failures=base / "failures.jsonl",
        text_dir=base / "text",
        chunks_dir=base / "chunks",
        entities_dir=base / "entities",
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Load pipeline artifacts into Postgres.")
    ap.add_argument("--artifacts-dir", default="./epstein_artifacts", help="Pipeline output_dir")
    ap.add_argument("--dsn", required=True, help="Postgres DSN")
    ap.add_argument("--truncate", action="store_true", help="Truncate tables before loading (dangerous)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    setup_logging(args.verbose)

    artifacts_dir = Path(args.artifacts_dir).expanduser().resolve()
    p = resolve_paths(artifacts_dir)

    if not artifacts_dir.exists():
        raise SystemExit(f"Artifacts dir not found: {artifacts_dir}")

    logging.info("Connecting to Postgres...")
    with psycopg.connect(args.dsn, row_factory=dict_row) as conn:
        conn.execute("SET statement_timeout = '10min'")
        ensure_schema_exists(conn)

        if args.truncate:
            logging.warning("TRUNCATE enabled. This will delete existing analysis tables.")
            conn.execute(TRUNCATE_SQL)

        # 1) manifest -> documents
        if p.manifest.exists():
            n = 0
            for obj in iter_jsonl(p.manifest):
                upsert_document(conn, obj)
                n += 1
            logging.info("Loaded documents from manifest: %d", n)
        else:
            logging.warning("manifest.jsonl not found at %s", p.manifest)

        # 2) runs
        if p.runs.exists():
            n = 0
            for obj in iter_jsonl(p.runs):
                upsert_run(conn, obj)
                n += 1
            logging.info("Loaded runs: %d", n)

        # 3) failures
        if p.failures.exists():
            n = 0
            for obj in iter_jsonl(p.failures):
                insert_failure(conn, obj)
                n += 1
            logging.info("Loaded failures: %d", n)

        # 4) document text
        if p.text_dir.exists():
            n = 0
            for txt in p.text_dir.glob("*.txt"):
                doc_id = txt.stem
                upsert_document_text(conn, doc_id, read_text(txt))
                n += 1
            logging.info("Loaded document_text rows: %d", n)

        # 5) chunks
        if p.chunks_dir.exists():
            n = 0
            for cfile in p.chunks_dir.glob("*.chunks.jsonl"):
                for obj in iter_jsonl(cfile):
                    upsert_chunk(conn, obj)
                    n += 1
            logging.info("Loaded chunk rows: %d", n)

        # 6) entities
        if p.entities_dir.exists():
            n = 0
            for efile in p.entities_dir.glob("*.entities.jsonl"):
                for obj in iter_jsonl(efile):
                    insert_entity(conn, obj)
                    n += 1
            logging.info("Loaded entity mentions: %d", n)

        conn.commit()
        logging.info("Done. Commit successful.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
