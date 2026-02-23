# Epstein Files Project - Complete Walkthrough

## Table of Contents
1. [Project Overview](#project-overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Components](#components)
5. [Usage Guide](#usage-guide)
6. [Configuration](#configuration)
7. [API Reference](#api-reference)
8. [Troubleshooting](#troubleshooting)

---

## Project Overview

The Epstein Files Project is an AI-powered platform for downloading, processing, and analyzing public documents related to the Epstein case. It uses:

- **Multi-threaded downloading** from government sources (DOJ, FBI, etc.)
- **OCR** for scanned documents
- **Named Entity Recognition** for extracting people, places, dates
- **Vector database (Qdrant)** for semantic search
- **AI Agents** for analysis and orchestration
- **RAG (Retrieval Augmented Generation)** for intelligent querying

---

## Quick Start

### Prerequisites

```bash
# Install dependencies
cd epstein
uv sync

# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Start services (Postgres + Qdrant)
docker compose up -d
```

### Start the Pipeline

```bash
# 1. Start the MCP server (for downloading)
uv run python -m mcp_servers.epstein_files_downloader.server

# 2. In another terminal, run the pipeline
uv run python epstein_files_pipeline.py run --config config.json

# 3. Start the AI Supervisor (optional)
uv run python -m supervisor_agent --interactive
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EPSTEIN PROJECT                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐        │
│  │   Download   │    │   Process    │    │   Analyze   │        │
│  │   Sources   │───▶│   Pipeline   │───▶│   Agents    │        │
│  │              │    │              │    │              │        │
│  │  • DOJ      │    │  • OCR       │    │  • RAG      │        │
│  │  • FBI      │    │  • NER       │    │  • Search   │        │
│  │  • GovInfo  │    │  • Chunking  │    │  • AI Query │        │
│  └──────────────┘    └──────────────┘    └──────────────┘        │
│         │                   │                   │                  │
│         └───────────────────┼───────────────────┘                  │
│                             ▼                                       │
│                    ┌──────────────┐                                │
│                    │   Qdrant    │                                │
│                    │  + Postgres  │                                │
│                    └──────────────┘                                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. MCP Server (Download)
- **File**: `mcp_servers/epstein_files_downloader/server.py`
- **Port**: 8765
- **Features**:
  - Async concurrent downloads (default 5 parallel)
  - Download queue management
  - Collection discovery from DOJ/FBI sources

**Usage**:
```bash
# Start server
uv run python -m mcp_servers.epstein_files_downloader.server

# API endpoints:
# GET  /health              - Health check
# GET  /collections         - List available collections
# POST /download             - Download single document
# POST /download/bulk       - Bulk download
# GET  /download/status     - Check download status
```

### 2. Pipeline (Processing)
- **File**: `epstein_files_pipeline.py`
- **Stages**:
  1. Discover URLs from seed pages
  2. Download PDFs (with SHA256 manifest)
  3. OCR with Tesseract
  4. Text extraction
  5. Chunking with overlap
  6. NER (Named Entity Recognition)
  7. Store in database

**Usage**:
```bash
# Initialize config
uv run python epstein_files_pipeline.py init-config --out config.json

# Run pipeline
uv run python epstein_files_pipeline.py run --config config.json

# Run specific stage
uv run python epstein_files_pipeline.py run --config config.json --stage ocr
```

### 3. RAG Ingestor
- **File**: `rag_ingestor.py`
- **Purpose**: Feed documents to vector database for semantic search
- **Features**:
  - Automatic chunking (512 tokens, 50 overlap)
  - Embeddings with sentence-transformers
  - Qdrant vector storage

**Usage**:
```python
from epstein.rag_ingestor import RAGIngestor

ingestor = RAGIngestor()
doc = ingestor.ingest_document(
    source_url="https://...",
    title="Flight Log 2001",
    doc_type="flight_log",
    content="Document text...",
)

# Search
results = ingestor.search("Who was on the flight?")
```

### 4. Supervisor Agent
- **File**: `supervisor_agent.py`
- **Purpose**: Long-running AI agent coordinator
- **Features**:
  - Task queue with SQLite persistence
  - Multi-worker processing
  - Pause/Resume/Stop
  - AI model interface (Ollama/OpenRouter)

**Usage**:
```bash
# Start supervisor
python -m epstein.supervisor_agent --workers 2 --model ollama:mistral

# Interactive mode
python -m supervisor_agent --interactive
```

### 5. Task Queue
- **File**: `task_queue.py`
- **Purpose**: Persistent task management with deduplication
- **Features**:
  - SQLite-backed queue
  - Content hashing to avoid re-processing
  - Pause/Resume/Cancel

**Usage**:
```python
from epstein.task_queue import TaskQueue, DeduplicationManager

queue = TaskQueue()
dedup = DeduplicationManager()

# Check if already processed
if not dedup.is_processed(file_hash, "ocr"):
    # Process file
    dedup.mark_processed(file_hash, "ocr", output_path)
```

---

## Usage Guide

### Downloading Documents

```bash
# Using MCP server API
curl http://localhost:8765/collections

# Download single document
curl -X POST http://localhost:8765/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://justice.gov/epstein/file.pdf"}'

# Bulk download
curl -X POST http://localhost:8765/download/bulk \
  -H "Content-Type: application/json" \
  -d '{"collection_id": "doj-001", "limit": 10}'
```

### Processing Documents

```bash
# Run full pipeline
uv run python epstein_files_pipeline.py run --config config.json

# Run specific stages
uv run python epstein_files_pipeline.py run --config config.json --stage download
uv run python epstein_files_pipeline.py run --config config.json --stage ocr
uv run python epstein_files_pipeline.py run --config config.json --stage ner
```

### Analyzing Documents

```bash
# Start supervisor agent
python -m supervisor_agent --interactive

# In interactive mode:
> analyze Who did Epstein meet in 2001?
> search flight logs
> status
```

### Searching

```bash
# Semantic search using RAG
uv run python -c "
from epstein.rag_ingestor import RAGIngestor
ingestor = RAGIngestor()
results = ingestor.search('flight to New York')
for r in results:
    print(r['text'][:200])
"
```

---

## Configuration

### Environment Variables

Create a `.env` file:

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=analysis
POSTGRES_PASSWORD=change_me

# Vector DB
QDRANT_URL=http://localhost:6333

# AI Models (free)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral
OPENROUTER_API_KEY=  # Get free key from openrouter.ai

# MCP Server
MCP_PORT=8765
MCP_MAX_CONCURRENT=5
```

### Pipeline Config (config.json)

```json
{
  "seed_urls": ["https://www.justice.gov/epstein/"],
  "output_dir": "./output",
  "allow_domains": ["justice.gov", "fbi.gov"],
  "chunk_size": 512,
  "chunk_overlap": 50,
  "batch_size": 10
}
```

---

## API Reference

### MCP Server Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Server info |
| GET | `/health` | Health check |
| GET | `/collections` | List document collections |
| GET | `/collections/{id}` | Get collection details |
| POST | `/download` | Download single document |
| POST | `/download/bulk` | Bulk download |
| GET | `/download/status` | List active downloads |
| GET | `/download/status/{id}` | Get download status |

### Supervisor Agent Commands

| Command | Description |
|---------|-------------|
| `analyze <query>` | Analyze documents with AI |
| `search <query>` | Semantic search |
| `status` | Show system status |
| `pause` | Pause all workers |
| `resume` | Resume workers |
| `stop` | Stop supervisor |

---

## Troubleshooting

### Common Issues

**Q: Downloads are slow**
```bash
# Increase concurrent downloads
# Edit .env: MCP_MAX_CONCURRENT=10
# Or use: curl -X POST http://localhost:8765/config -d '{"max_concurrent": 10}'
```

**Q: OCR not working**
```bash
# Install Tesseract
sudo apt-get install tesseract-ocr

# Check installation
tesseract --version
```

**Q: AI model not responding**
```bash
# Start Ollama
ollama serve
ollama pull mistral

# Or check OpenRouter key
echo $OPENROUTER_API_KEY
```

**Q: Database connection errors**
```bash
# Check services
docker compose ps

# Restart services
docker compose restart
```

### Getting Help

```bash
# Run doctor check
uv run python scripts/doctor.py

# View logs
tail -f logs/epstein.log

# Check status
curl http://localhost:8765/health
```

---

## For AI Agents

AI agents can use the following workflow:

1. **Query the Supervisor**: Send analysis requests to `supervisor_agent.py`
2. **Search RAG**: Use `rag_ingestor.py` for semantic search
3. **Process Documents**: Use `epstein_files_pipeline.py` for batch processing
4. **Track Tasks**: Use `task_queue.py` for long-running operations

### Agent Example

```python
from epstein.supervisor_agent import SupervisorAgent

agent = SupervisorAgent(model="ollama:mistral")

# Submit analysis task
task_id = agent.submit_task(
    command="analyze",
    name="Find meetings",
    args={"query": "meeting with [person] in 2001"}
)

# Check status
status = agent.get_status()
print(status)
```

---

## License

This project is for research purposes on publicly released materials.

*Last Updated: 2026-02-23*
