#!/usr/bin/env python3
# ==============================================================================
# Script Name: qdrant_embed_chunks.py
# Date: 2025-12-21
# Author: ChatGPT (for Blaine Winslow / cbwinslow)
# Summary:
#   Reads text chunks from Postgres (doc_analysis.chunks) and upserts embeddings
#   into Qdrant for semantic search.
#
#   Idempotent: uses chunk_id as Qdrant point ID (safe to rerun).
#   Provenance-safe payload: doc_id, offsets, source_url.
#
# Usage (Docker-first):
#   make embed
# ==============================================================================
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional

import psycopg
from psycopg.rows import dict_row
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

try:
    from fastembed import TextEmbedding  # type: ignore
except Exception as e:  # noqa: BLE001
    TextEmbedding = None  # type: ignore
    _FASTEMBED_IMPORT_ERR = str(e)

DEFAULT_DSN_DOCKER = "postgresql://analysis:analysis@postgres:5432/analysis"
DEFAULT_QDRANT = "http://localhost:6333"
DEFAULT_COLLECTION = "epstein_chunks"
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"

@dataclass(frozen=True)
class ChunkRow:
    chunk_id: int
    doc_id: str
    start_char: int
    end_char: int
    chunk_index: int
    chunk_text: str
    source_url: Optional[str]

def eprint(msg: str) -> None:
    print(msg, file=sys.stderr)

def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}

def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")

def table_exists(conn: psycopg.Connection, fq_name: str) -> bool:
    schema, table = fq_name.split(".", 1)
    q = """
    SELECT EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema=%s AND table_name=%s
    ) AS exists;
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(q, (schema, table))
        return bool(cur.fetchone()["exists"])

def ensure_collection(client: QdrantClient, collection: str, dim: int) -> None:
    cols = client.get_collections().collections
    if any(c.name == collection for c in cols):
        return
    client.create_collection(
        collection_name=collection,
        vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
    )

def fetch_chunks(conn: psycopg.Connection, resume_after: Optional[int], limit: Optional[int]) -> Iterable[ChunkRow]:
    base = """
    SELECT c.id AS chunk_id, c.doc_id, c.start_char, c.end_char, c.chunk_index, c.chunk_text,
           d.source_url
    FROM doc_analysis.chunks c
    JOIN doc_analysis.documents d ON d.doc_id = c.doc_id
    """
    params: List[Any] = []
    where = ""
    if resume_after is not None:
        where = "WHERE c.id > %s"
        params.append(resume_after)
    order = "ORDER BY c.id ASC"
    lim = ""
    if limit is not None:
        lim = "LIMIT %s"
        params.append(limit)
    q = " ".join([base, where, order, lim])
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(q, params)
        for row in cur:
            yield ChunkRow(
                chunk_id=int(row["chunk_id"]),
                doc_id=str(row["doc_id"]),
                start_char=int(row["start_char"]),
                end_char=int(row["end_char"]),
                chunk_index=int(row["chunk_index"]),
                chunk_text=str(row.get("chunk_text") or ""),
                source_url=(str(row.get("source_url")) if row.get("source_url") is not None else None),
            )

def batched(it: Iterable[ChunkRow], n: int) -> Iterable[List[ChunkRow]]:
    batch: List[ChunkRow] = []
    for x in it:
        batch.append(x)
        if len(batch) >= n:
            yield batch
            batch = []
    if batch:
        yield batch

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=os.getenv("EPSTEIN_DSN", DEFAULT_DSN_DOCKER))
    ap.add_argument("--qdrant-url", default=os.getenv("QDRANT_URL", DEFAULT_QDRANT))
    ap.add_argument("--collection", default=DEFAULT_COLLECTION)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--state-file", default=".epstein/embed_state.json")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--write-back", action="store_true")
    args = ap.parse_args()

    if TextEmbedding is None:
        eprint("fastembed import failed; add dependency fastembed and rebuild container.")
        eprint(f"Import error: {_FASTEMBED_IMPORT_ERR}")
        return 3

    state_path = Path(args.state_file)
    state = load_state(state_path) if args.resume else {}
    resume_after = int(state.get("last_chunk_id")) if args.resume and state.get("last_chunk_id") else None

    embedder = TextEmbedding(args.model)
    qclient = QdrantClient(url=args.qdrant_url)

    total = 0
    last = resume_after

    with psycopg.connect(args.dsn, autocommit=False) as conn:
        do_writeback = args.write_back and table_exists(conn, "doc_analysis.chunk_embeddings")

        for batch in batched(fetch_chunks(conn, resume_after, args.limit), args.batch_size):
            texts = [c.chunk_text for c in batch]
            t0 = time.time()
            vecs = list(embedder.embed(texts))
            if not vecs:
                continue
            dim = len(vecs[0])
            ensure_collection(qclient, args.collection, dim)

            points: List[qm.PointStruct] = []
            for c, v in zip(batch, vecs):
                payload = {
                    "doc_id": c.doc_id,
                    "chunk_id": c.chunk_id,
                    "chunk_index": c.chunk_index,
                    "start_char": c.start_char,
                    "end_char": c.end_char,
                    "source_url": c.source_url,
                }
                points.append(qm.PointStruct(id=c.chunk_id, vector=v, payload=payload))

            qclient.upsert(collection_name=args.collection, points=points, wait=True)

            if do_writeback:
                with conn.cursor() as cur:
                    cur.executemany(
                        """
                        INSERT INTO doc_analysis.chunk_embeddings (chunk_id, collection, model)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (chunk_id, collection, model) DO NOTHING;
                        """,
                        [(c.chunk_id, args.collection, args.model) for c in batch],
                    )
                conn.commit()

            total += len(points)
            last = batch[-1].chunk_id
            save_state(state_path, {"last_chunk_id": last, "collection": args.collection, "model": args.model})
            dt = time.time() - t0
            print(f"[embed] upserted {len(points)} (total {total}) in {dt:.2f}s; last={last}")

    print(f"[embed] DONE total_upserted={total}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
