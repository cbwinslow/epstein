#!/usr/bin/env python3
# ==============================================================================
# Script Name: qdrant_semantic_search.py
# Date: 2025-12-21
# Summary:
#   Semantic search against Qdrant; optionally prints chunk excerpts from Postgres.
#
# Usage:
#   make search Q="your query"
# ==============================================================================
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import psycopg
from psycopg.rows import dict_row
from qdrant_client import QdrantClient

try:
    from fastembed import TextEmbedding  # type: ignore
except Exception as e:  # noqa: BLE001
    TextEmbedding = None  # type: ignore
    _FASTEMBED_IMPORT_ERR = str(e)

DEFAULT_DSN_DOCKER = "postgresql://analysis:analysis@postgres:5432/analysis"
DEFAULT_QDRANT = "http://localhost:6333"
DEFAULT_COLLECTION = "epstein_chunks"
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"

def eprint(msg: str) -> None:
    print(msg, file=sys.stderr)

def fetch_chunk(conn: psycopg.Connection, chunk_id: int) -> dict[str, Any] | None:
    q = """
    SELECT c.id AS chunk_id, c.doc_id, c.start_char, c.end_char, c.chunk_index, c.chunk_text, d.source_url
    FROM doc_analysis.chunks c
    JOIN doc_analysis.documents d ON d.doc_id = c.doc_id
    WHERE c.id = %s
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(q, (chunk_id,))
        row = cur.fetchone()
        return dict(row) if row else None

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?", default=os.getenv("Q", ""))
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--collection", default=DEFAULT_COLLECTION)
    ap.add_argument("--qdrant-url", default=os.getenv("QDRANT_URL", DEFAULT_QDRANT))
    ap.add_argument("--dsn", default=os.getenv("EPSTEIN_DSN", DEFAULT_DSN_DOCKER))
    ap.add_argument("--with-text", action="store_true")
    args = ap.parse_args()

    if not args.query.strip():
        eprint("Provide a query string, or set env Q=...")
        return 2

    if TextEmbedding is None:
        eprint("fastembed import failed.")
        eprint(f"Import error: {_FASTEMBED_IMPORT_ERR}")
        return 3

    embedder = TextEmbedding(args.model)
    qvec = next(iter(embedder.embed([args.query])))

    client = QdrantClient(url=args.qdrant_url)
    hits = client.search(collection_name=args.collection, query_vector=qvec, limit=args.top_k)

    print(f'Query: "{args.query}"')
    print(f"Collection: {args.collection}  top_k={args.top_k}")
    print("-" * 80)

    if args.with_text:
        with psycopg.connect(args.dsn) as conn:
            for h in hits:
                cid = int(h.id)
                payload = h.payload or {}
                row = fetch_chunk(conn, cid)
                print(f"score={h.score:.4f} chunk_id={cid} doc_id={payload.get('doc_id')}")
                if row:
                    print(f"source_url: {row.get('source_url')}")
                    print(f"offsets: {row.get('start_char')}..{row.get('end_char')} idx={row.get('chunk_index')}")
                    text = str(row.get('chunk_text') or "").replace("\n", " ")
                    excerpt = text[:600]
                    print(f"excerpt: {excerpt}{'...' if len(text) > 600 else ''}")
                print("-" * 80)
    else:
        for h in hits:
            payload = h.payload or {}
            print(f"score={h.score:.4f} chunk_id={h.id} doc_id={payload.get('doc_id')} offsets={payload.get('start_char')}..{payload.get('end_char')}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
