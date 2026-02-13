# Project Memories

This file captures high-level operational memories for future runs.

## 2026-01-07
- Large releases (3M+ docs) require incremental pagination and rate limiting via the downloader MCP server.
- Use batch ZIP archives to simplify transfer/storage and maintain manifest provenance.
- Streaming endpoints can be used to retrieve completed downloads remotely without SSH.
