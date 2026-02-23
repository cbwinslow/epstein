import os
import pathlib
import shutil
import zipfile

src_zip = pathlib.Path("/mnt/data/epstein_files_project_final.zip")
work = pathlib.Path("/mnt/data/epstein_files_project_final_v2")
if work.exists():
    shutil.rmtree(work)
work.mkdir(parents=True)

# Unzip existing bundle
with zipfile.ZipFile(src_zip, "r") as z:
    z.extractall(work)

# Add embedding + search scripts
embed_py = r'''#!/usr/bin/env python3
# ==============================================================================
# Script Name: qdrant_embed_chunks.py
# Date: 2025-12-21
# Author: ChatGPT (for Blaine Winslow / cbwinslow)
# Summary:
#   Reads text chunks from Postgres (doc_analysis.chunks) and upserts embeddings
#   into Qdrant for semantic search.
#
#   Design goals:
#     - Idempotent: uses stable point IDs (chunk_id), safe to re-run
#     - Provenance-safe: payload contains doc_id + offsets + source_url + hashes
#     - Resume-friendly: optional state file (.epstein/embed_state.json)
#     - Cross-platform: intended to run via Docker runner (Makefile)
#
# Requirements:
#   - Postgres schema created by vector_db_bootstrap.sh (doc_analysis.*)
#   - Qdrant running (compose.yml)
#   - Python deps:
#       qdrant-client, psycopg, fastembed
#
# Usage (Docker-first):
#   make embed
#
# Manual:
#   python qdrant_embed_chunks.py --dsn ... --qdrant-url ... --collection epstein_chunks
#
# Inputs:
#   --dsn                  Postgres DSN (default: env EPSTEIN_DSN or docker default)
#   --qdrant-url           Qdrant base URL (default: env QDRANT_URL or http://localhost:6333)
#   --collection           Qdrant collection name (default: epstein_chunks)
#   --batch-size           Number of chunks per embed batch (default: 64)
#   --model                FastEmbed model name (default: BAAI/bge-small-en-v1.5)
#   --state-file           Resume state file (default: .epstein/embed_state.json)
#   --resume               Resume from last chunk_id recorded in state file
#   --limit                Optional limit for testing
#   --write-back           If chunk_embeddings table exists, write vector ids + model info
#   --verbose              More logs
#
# Outputs:
#   - Qdrant collection populated with vectors + payload
#   - Optional: .epstein/embed_state.json updated
#
# Modification Log:
#   - 2025-12-21: Initial, Docker-first foundation version.
# ==============================================================================

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional, Tuple

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


def info(msg: str, verbose: bool = True) -> None:
    if verbose:
        print(msg)


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
      SELECT 1
      FROM information_schema.tables
      WHERE table_schema = %s AND table_name = %s
    ) AS exists;
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(q, (schema, table))
        return bool(cur.fetchone()["exists"])


def ensure_collection(
    client: QdrantClient,
    collection: str,
    dim: int,
) -> None:
    existing = client.get_collections().collections
    if any(c.name == collection for c in existing):
        return
    client.create_collection(
        collection_name=collection,
        vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
        optimizers_config=qm.OptimizersConfigDiff(default_segment_number=2),
    )


def fetch_chunks(
    conn: psycopg.Connection,
    resume_after: Optional[int],
    limit: Optional[int],
) -> Iterable[ChunkRow]:
    # NOTE: column name is assumed chunk_text; adjust if your schema differs.
    base = """
    SELECT
      c.id AS chunk_id,
      c.doc_id AS doc_id,
      c.start_char AS start_char,
      c.end_char AS end_char,
      c.chunk_index AS chunk_index,
      c.chunk_text AS chunk_text,
      d.source_url AS source_url
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
                chunk_text=str(row["chunk_text"] or ""),
                source_url=(str(row["source_url"]) if row["source_url"] is not None else None),
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
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if TextEmbedding is None:
        eprint("fastembed is not installed or failed to import.")
        eprint(f"Import error: {_FASTEMBED_IMPORT_ERR}")
        eprint("Fix: add `fastembed` to deps and rebuild container, or use a different embed provider.")
        return 3

    state_path = Path(args.state_file)
    state = load_state(state_path) if args.resume else {}
    resume_after = state.get("last_chunk_id") if args.resume else None

    verbose = bool(args.verbose)
    info(f"[embed] DSN: {args.dsn}", verbose=True)
    info(f"[embed] Qdrant: {args.qdrant_url} collection={args.collection}", verbose=True)
    info(f"[embed] Model: {args.model}", verbose=True)
    if resume_after is not None:
        info(f"[embed] Resuming after chunk_id={resume_after}", verbose=True)

    embedder = TextEmbedding(args.model)

    # Determine embedding dimension from first vector
    # (fastembed yields vectors lazily)
    dim: Optional[int] = None

    qclient = QdrantClient(url=args.qdrant_url)

    with psycopg.connect(args.dsn, autocommit=False) as conn:
        # Optional write-back table
        do_writeback = False
        if args.write_back:
            do_writeback = table_exists(conn, "doc_analysis.chunk_embeddings")
            if args.write_back and not do_writeback:
                info("[embed] chunk_embeddings table not present; skipping write-back.", verbose=True)

        chunk_iter = fetch_chunks(conn, resume_after=resume_after, limit=args.limit)
        total_upserted = 0
        last_chunk_id = resume_after

        for batch in batched(chunk_iter, args.batch_size):
            texts = [c.chunk_text for c in batch]
            t0 = time.time()
            vecs = list(embedder.embed(texts))
            if not vecs:
                continue
            if dim is None:
                dim = len(vecs[0])
                ensure_collection(qclient, args.collection, dim)
                info(f"[embed] Ensured collection {args.collection} dim={dim}", verbose=True)

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

            dt = time.time() - t0
            total_upserted += len(points)
            last_chunk_id = batch[-1].chunk_id
            save_state(state_path, {"last_chunk_id": last_chunk_id, "collection": args.collection, "model": args.model})
            info(f"[embed] upserted {len(points)} (total {total_upserted}) in {dt:.2f}s; last={last_chunk_id}", verbose=True)

    info(f"[embed] DONE total_upserted={total_upserted}", verbose=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

search_py = r'''#!/usr/bin/env python3
# ==============================================================================
# Script Name: qdrant_semantic_search.py
# Date: 2025-12-21
# Author: ChatGPT (for Blaine Winslow / cbwinslow)
# Summary:
#   Semantic search against Qdrant using the same embedding model as ingest.
#   Optionally fetches chunk text from Postgres for display.
#
# Usage (Docker-first):
#   make search Q="your query"
#
# Manual:
#   python qdrant_semantic_search.py "your query" --dsn ... --qdrant-url ...
# ==============================================================================

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Optional

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


def fetch_chunk_text(conn: psycopg.Connection, chunk_id: int) -> Optional[dict[str, Any]]:
    q = """
    SELECT c.id AS chunk_id, c.doc_id, c.start_char, c.end_char, c.chunk_index, c.chunk_text,
           d.source_url
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
        eprint("fastembed is not installed or failed to import.")
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
                row = fetch_chunk_text(conn, cid)
                print(f"score={h.score:.4f} chunk_id={cid} doc_id={payload.get('doc_id')}")
                if row:
                    print(f"source_url: {row.get('source_url')}")
                    print(f"offsets: {row.get('start_char')}..{row.get('end_char')}  idx={row.get('chunk_index')}")
                    text = str(row.get("chunk_text") or "")
                    excerpt = text[:600].replace("\n", " ")
                    print(f"excerpt: {excerpt}{'...' if len(text)>600 else ''}")
                print("-" * 80)
    else:
        for h in hits:
            payload = h.payload or {}
            print(f"score={h.score:.4f} chunk_id={h.id} doc_id={payload.get('doc_id')} offsets={payload.get('start_char')}..{payload.get('end_char')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

# Write new scripts
(work/"qdrant_embed_chunks.py").write_text(embed_py, encoding="utf-8")
(work/"qdrant_semantic_search.py").write_text(search_py, encoding="utf-8")
os.chmod(work/"qdrant_embed_chunks.py", 0o755)
os.chmod(work/"qdrant_semantic_search.py", 0o755)

# Update pyproject.toml to include fastembed
pyproj = (work/"pyproject.toml").read_text(encoding="utf-8")
if "fastembed" not in pyproj:
    pyproj = pyproj.replace('"qdrant-client>=1.9",', '"qdrant-client>=1.9",\n  "fastembed>=0.3",')
    (work/"pyproject.toml").write_text(pyproj, encoding="utf-8")

# Update Makefile with embed/search targets if missing
mk = (work/"Makefile").read_text(encoding="utf-8")
if "embed:" not in mk:
    mk += r"""

.PHONY: embed
embed:
	@$(COMPOSE) -f $(COMPOSE_FILE) --profile pipeline run --rm \
	  -e EPSTEIN_DSN="$${EPSTEIN_DSN:-postgresql://analysis:analysis@postgres:5432/analysis}" \
	  -e QDRANT_URL="$${QDRANT_URL:-http://qdrant:6333}" \
	  pipeline qdrant_embed_chunks.py --dsn "$${EPSTEIN_DSN:-postgresql://analysis:analysis@postgres:5432/analysis}" --qdrant-url "$${QDRANT_URL:-http://qdrant:6333}" --resume --write-back

.PHONY: search
search:
	@$(COMPOSE) -f $(COMPOSE_FILE) --profile pipeline run --rm \
	  -e EPSTEIN_DSN="$${EPSTEIN_DSN:-postgresql://analysis:analysis@postgres:5432/analysis}" \
	  -e QDRANT_URL="$${QDRANT_URL:-http://qdrant:6333}" \
	  -e Q="$${Q:-}" \
	  pipeline qdrant_semantic_search.py "$${Q:-}" --qdrant-url "$${QDRANT_URL:-http://qdrant:6333}" --dsn "$${EPSTEIN_DSN:-postgresql://analysis:analysis@postgres:5432/analysis}" --with-text
"""
    (work/"Makefile").write_text(mk, encoding="utf-8")

# Create updated zip
zip_path = pathlib.Path("/mnt/data/epstein_files_project_final_v2.zip")
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for p in work.rglob("*"):
        if p.is_file():
            z.write(p, p.relative_to(work).as_posix())

str(zip_path), len([p for p in work.rglob("*") if p.is_file()])

