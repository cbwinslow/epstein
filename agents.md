# Agents Overview

This file summarizes the active agents and MCP servers in the Epstein Files project. It complements `knowledge_base/agents.md` and is intended as a quick reference for operators.

## MCP Servers

- **Epstein Files Downloader MCP** (`mcp_servers/epstein_files_downloader/server.py`)
  - Discover collections, paginate over large releases, download incrementally, and stream/zip completed files.
- **Epstein Files Processor MCP** (`mcp_servers/epstein_files_processor/server.py`)
  - Orchestrates end-to-end pipeline runs (download → OCR → NER → relationships → embeddings).

## Operational Notes

- Use pagination (`offset`, `limit`, `page_size`) for large releases.
- Respect rate limits using `max_requests_per_minute` and `polite_delay_seconds`.
- Archive completed batches to reduce transfer overhead.
