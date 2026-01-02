# Chunking Guide

Objective
- Break document text into manageable chunks for embeddings and retrieval.

Strategy
- Prefer sentence-aware chunking to avoid cutting sentences in half.
- Recommend: ~3,000 chars per chunk with 600 chars overlap (approx 20% overlap).
- Use `scripts/chunking.py` to generate `.chunks.jsonl` for a given text file.

Output format
- JSONL per chunk:
  - `chunk_id`: integer
  - `char_start`, `char_end` (optional)
  - `preview` (first ~200 chars)
  - `text` (chunk contents)

Validation
- Confirm no chunk is empty.
- Check that preview contains readable content (not only whitespace or identifiers).

Integration
- After chunking, generate embeddings for each chunk and include metadata: `doc_id`, `chunk_id`, `char_start`, `char_end`, `preview`.
