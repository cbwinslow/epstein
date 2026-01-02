# Embeddings & Indexing

Model recommendations
- Local and reproducible: `sentence-transformers/all-MiniLM-L6-v2` (fast) or `all-mpnet-base-v2` (higher quality).

Workflow
1. Chunk text with overlap (see `docs/chunking.md`).
2. Embed each chunk in batches (batch size tuned to hardware, e.g., 64–128).
3. Upsert vectors to Qdrant with metadata: `{doc_id, chunk_id, char_start, char_end, preview, ts}`.

Qdrant setup
- Collection name: `epstein_v1` or date-suffixed collections for migrations.
- Use deterministic vector ids: `<sha>-<chunk_id>`.

Backups
- Regularly export Qdrant collections (use Qdrant export API or scheduler that saves files to object storage).
- Keep retention policy and verify restore on a small sample during each snapshot.

Verification
- After upsert, run k-NN queries for known sample queries and verify expected documents are retrieved in top-K.
