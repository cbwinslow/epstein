#!/usr/bin/env python3
"""Orchestrate the Epstein pipeline: download, OCR, NER, relationships, embeddings."""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import psycopg
from psycopg.rows import dict_row

from epstein.db_ingest_artifacts import (
    TRUNCATE_SQL,
    ensure_schema_exists,
    insert_entity,
    insert_failure,
    iter_jsonl,
    resolve_paths,
    upsert_chunk,
    upsert_document,
    upsert_document_text,
    upsert_run,
)
from epstein.epstein_files_pipeline import PipelineConfig, run_pipeline
from epstein.image_ocr import run_image_ocr
from epstein.relationship_analysis import run_relationship_analysis


@dataclass
class OrchestratorOptions:
    config_path: Path
    artifacts_dir: Path
    dsn: Optional[str]
    qdrant_url: Optional[str]
    collection: str
    run_ingest: bool
    run_embeddings: bool
    run_relationships: bool
    run_image_ocr: bool
    image_input_dir: Path
    image_output_dir: Path
    image_extensions: Iterable[str]
    relationship_min_count: int
    relationship_max_evidence: int
    truncate: bool
    verbose: bool


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def load_config(config_path: Path) -> PipelineConfig:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    return PipelineConfig.model_validate(data)


def ingest_artifacts(artifacts_dir: Path, dsn: str, truncate: bool = False) -> None:
    paths = resolve_paths(artifacts_dir)
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        conn.execute("SET statement_timeout = '10min'")
        ensure_schema_exists(conn)

        if truncate:
            logging.warning("TRUNCATE enabled. This will delete existing analysis tables.")
            conn.execute(TRUNCATE_SQL)

        if paths.manifest.exists():
            for obj in iter_jsonl(paths.manifest):
                upsert_document(conn, obj)
        if paths.runs.exists():
            for obj in iter_jsonl(paths.runs):
                upsert_run(conn, obj)
        if paths.failures.exists():
            for obj in iter_jsonl(paths.failures):
                insert_failure(conn, obj)
        if paths.text_dir.exists():
            for txt in paths.text_dir.glob("*.txt"):
                doc_id = txt.stem
                upsert_document_text(conn, doc_id, txt.read_text(encoding="utf-8", errors="replace"))
        if paths.chunks_dir.exists():
            for cfile in paths.chunks_dir.glob("*.chunks.jsonl"):
                for obj in iter_jsonl(cfile):
                    upsert_chunk(conn, obj)
        if paths.entities_dir.exists():
            for efile in paths.entities_dir.glob("*.entities.jsonl"):
                for obj in iter_jsonl(efile):
                    insert_entity(conn, obj)

        conn.commit()


def run_embeddings(dsn: str, qdrant_url: str, collection: str) -> None:
    cmd = [
        sys.executable,
        "-m",
        "epstein.qdrant_embed_chunks_1",
        "--dsn",
        dsn,
        "--qdrant-url",
        qdrant_url,
        "--collection",
        collection,
    ]
    logging.info("Running embeddings: %s", " ".join(cmd))
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Embedding step failed with code {proc.returncode}")


def run_orchestrator(opts: OrchestratorOptions) -> None:
    setup_logging(opts.verbose)

    logging.info("Loading pipeline config: %s", opts.config_path)
    cfg = load_config(opts.config_path)

    if opts.artifacts_dir:
        cfg.output_dir = str(opts.artifacts_dir)

    run_pipeline(cfg, verbose=opts.verbose)

    if opts.run_image_ocr:
        logging.info("Running image OCR on %s", opts.image_input_dir)
        successes, failures = run_image_ocr(
            opts.image_input_dir,
            opts.image_output_dir,
            opts.image_extensions,
            lang=cfg.ocrmypdf_lang,
        )
        logging.info("Image OCR complete: %d success, %d failed", len(successes), len(failures))

    if opts.run_ingest:
        if not opts.dsn:
            raise RuntimeError("Postgres DSN is required when run_ingest is enabled")
        logging.info("Ingesting artifacts into Postgres")
        ingest_artifacts(opts.artifacts_dir, opts.dsn, truncate=opts.truncate)

    if opts.run_relationships:
        relationships_out = opts.artifacts_dir / "relationships" / "relationships.jsonl"
        logging.info("Building relationships -> %s", relationships_out)
        count = run_relationship_analysis(
            entities_dir=opts.artifacts_dir / "entities",
            output_path=relationships_out,
            min_count=opts.relationship_min_count,
            max_evidence=opts.relationship_max_evidence,
        )
        logging.info("Relationships written: %d", count)

    if opts.run_embeddings:
        if not opts.dsn or not opts.qdrant_url:
            raise RuntimeError("Both DSN and Qdrant URL are required for embeddings")
        run_embeddings(opts.dsn, opts.qdrant_url, opts.collection)


def main() -> int:
    ap = argparse.ArgumentParser(description="Orchestrate the Epstein pipeline end-to-end.")
    ap.add_argument("--config", required=True, help="Path to pipeline config JSON")
    ap.add_argument("--artifacts-dir", default=None, help="Override output_dir for pipeline artifacts")
    ap.add_argument("--dsn", default=None, help="Postgres DSN for ingestion/embeddings")
    ap.add_argument("--qdrant-url", default=None, help="Qdrant URL for embeddings")
    ap.add_argument("--collection", default="epstein_chunks")
    ap.add_argument("--run-ingest", action="store_true")
    ap.add_argument("--run-embeddings", action="store_true")
    ap.add_argument("--run-relationships", action="store_true")
    ap.add_argument("--run-image-ocr", action="store_true")
    ap.add_argument("--image-input-dir", default=None)
    ap.add_argument("--image-output-dir", default=None)
    ap.add_argument("--image-extensions", default=".png,.jpg,.jpeg,.tif,.tiff")
    ap.add_argument("--relationship-min-count", type=int, default=2)
    ap.add_argument("--relationship-max-evidence", type=int, default=5)
    ap.add_argument("--truncate", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    cfg = load_config(config_path)

    artifacts_dir = Path(args.artifacts_dir or cfg.output_dir).expanduser().resolve()
    image_input_dir = Path(args.image_input_dir or artifacts_dir / "images").expanduser().resolve()
    image_output_dir = Path(args.image_output_dir or artifacts_dir / "image_text").expanduser().resolve()
    image_extensions = [ext.strip() for ext in args.image_extensions.split(",") if ext.strip()]

    opts = OrchestratorOptions(
        config_path=config_path,
        artifacts_dir=artifacts_dir,
        dsn=args.dsn,
        qdrant_url=args.qdrant_url,
        collection=args.collection,
        run_ingest=args.run_ingest,
        run_embeddings=args.run_embeddings,
        run_relationships=args.run_relationships,
        run_image_ocr=args.run_image_ocr,
        image_input_dir=image_input_dir,
        image_output_dir=image_output_dir,
        image_extensions=image_extensions,
        relationship_min_count=args.relationship_min_count,
        relationship_max_evidence=args.relationship_max_evidence,
        truncate=args.truncate,
        verbose=args.verbose,
    )

    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")

    run_orchestrator(opts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
