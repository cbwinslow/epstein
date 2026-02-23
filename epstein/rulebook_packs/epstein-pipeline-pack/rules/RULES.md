# Epstein Pipeline — Rules of Engagement (rulebook-ai pack)

You are working inside a repository that implements a **provenance-safe document analysis pipeline** for large PDF releases.

## Non-negotiables
- **Accuracy, traceability, and auditability > speed.**
- Never "invent" findings. Every claim must have an evidence trail:
  - `doc_id` (sha256) → source URL → artifact paths → offsets (chunk start/end) → extracted text.
- Prefer **idempotent** operations. If a step is re-run, it must not corrupt existing state.
- Avoid destructive actions by default. If deletion is needed, require an explicit flag and log it.

## Repository conventions
- Run everything through `make` when possible.
- Favor cross-platform execution:
  - If a step depends on system packages, prefer `docker compose` or provide OS-specific install notes.
- Any new scripts must:
  - include robust logging,
  - validate inputs,
  - fail loudly on critical errors, but continue when safe.

## How you should work
- When changing pipeline logic, update:
  - the matching doc in `memory/` (architecture + invariants),
  - and any schema migration notes.
- If you introduce a new dependency, add it to:
  - `requirements.txt` or `pyproject.toml` (whichever the repo uses),
  - and the bootstrap instructions.

## Audit trail requirements
- All pipeline steps must produce:
  - a run record (timestamp, version, inputs),
  - and a failures record (error, stack trace, doc_id).
- When writing to Postgres, store:
  - doc-level provenance (hashes, URLs, timestamps),
  - chunk offsets, and deterministic chunk IDs.

## Guardrails for publishable output
- Anything in `safe_exports/` must be review-friendly:
  - no raw PII,
  - references back to the underlying evidence.

## Commands you will use frequently
- `make vectordb-up` / `make vectordb-down`
- `make pipeline-run`
- `make db-load`
- `make embed`
- `make search Q="..."` (semantic search)