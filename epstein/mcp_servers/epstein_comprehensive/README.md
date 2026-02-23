# Epstein Comprehensive MCP Server

## Overview

The Epstein Comprehensive MCP Server is a complete Model Context Protocol server that exposes all major functionality of the Epstein project through a unified REST API. This server provides programmatic access to:

- **Pipeline Management**: Run and monitor document processing pipelines
- **Database Operations**: Query PostgreSQL database for documents and entities
- **Vector Search**: Perform semantic search using Qdrant
- **Agent Orchestration**: Interact with and coordinate multiple AI agents
- **Document Processing**: Process documents with OCR, NER, and analysis
- **Entity Extraction**: Extract and manage entities and relationships

## Features

### Core Capabilities

- ✅ **Unified API**: Single endpoint for all Epstein functionality
- ✅ **Pipeline Orchestration**: Trigger and monitor document processing
- ✅ **Database Queries**: Execute SQL queries and get results
- ✅ **Vector Search**: Semantic search across document embeddings
- ✅ **Agent Management**: List, query, and execute agent tasks
- ✅ **Health Monitoring**: System health checks and status
- ✅ **Async Support**: Background task processing
- ✅ **OpenAPI Docs**: Interactive API documentation

### API Endpoints

#### Information & Health
- `GET /` - Server information and endpoint list
- `GET /health` - Health check with service status
- `GET /tools` - List all available MCP tools

#### Pipeline Management
- `POST /pipeline/run` - Run processing pipeline
- `GET /pipeline/status/{task_id}` - Get pipeline status
- `POST /pipeline/init-config` - Initialize pipeline configuration

#### Database Operations
- `POST /database/query` - Execute SQL query
- `GET /database/tables` - List all tables
- `GET /database/stats` - Get database statistics

#### Vector Search
- `POST /vector/search` - Semantic vector search
- `GET /vector/collections` - List Qdrant collections
- `GET /vector/collection/{name}/stats` - Collection statistics

#### Agent Operations
- `GET /agents` - List all available agents
- `GET /agents/{agent_id}` - Get specific agent info
- `POST /agents/task` - Execute agent task
- `GET /agents/task/{task_id}` - Get task status

## Quick Start

### Installation

```bash
cd mcp_servers/epstein_comprehensive

# Install dependencies
uv pip install fastapi uvicorn pydantic
```

### Running the Server

```bash
# Start with defaults (localhost:8000)
python server.py

# Custom configuration
python server.py --host 0.0.0.0 --port 8000 \
  --postgres-dsn postgresql://user:pass@localhost:5432/analysis \
  --qdrant-url http://localhost:6333 \
  --verbose
```

### Verify Server

```bash
# Check health
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs

# List available tools
curl http://localhost:8000/tools
```

## Usage Examples

### Run Document Processing Pipeline

```bash
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "documents": ["/path/to/doc1.pdf", "/path/to/doc2.pdf"],
    "operations": ["ocr", "text", "ner", "embed"]
  }'
```

Response:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Pipeline execution queued",
  "started_at": "2026-01-15T22:00:00Z"
}
```

### Execute Database Query

```bash
curl -X POST http://localhost:8000/database/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT * FROM documents WHERE created_at > $1",
    "params": {"1": "2026-01-01"},
    "limit": 100
  }'
```

### Perform Vector Search

```bash
curl -X POST http://localhost:8000/vector/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "financial transactions in 2019",
    "collection": "epstein_documents",
    "limit": 10,
    "score_threshold": 0.7
  }'
```

### Execute Agent Task

```bash
curl -X POST http://localhost:8000/agents/task \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "entity_extraction_agent",
    "task_name": "extract_entities",
    "parameters": {
      "text": "Jeffrey Epstein met with Bill Clinton in New York.",
      "entity_types": ["PERSON", "LOC"]
    }
  }'
```

## Python Client Example

```python
import requests
import time

# Initialize client
base_url = "http://localhost:8000"

# Run pipeline
response = requests.post(f"{base_url}/pipeline/run", json={
    "documents": ["/data/document.pdf"],
    "operations": ["ocr", "text", "ner"]
})
task_id = response.json()["task_id"]

# Monitor status
while True:
    status = requests.get(f"{base_url}/pipeline/status/{task_id}").json()
    if status["status"] in ["completed", "failed"]:
        break
    print(f"Status: {status['status']}")
    time.sleep(2)

# Perform vector search
search_response = requests.post(f"{base_url}/vector/search", json={
    "query": "legal proceedings",
    "limit": 5
})
results = search_response.json()["results"]
print(f"Found {len(results)} results")
```

## Integration with AI Agents

### PydanticAI Example

```python
from pydantic_ai import Agent
import requests

agent = Agent(
    model='openai:gpt-4',
    system_prompt='You are an assistant that processes documents.'
)

@agent.tool
async def process_documents(documents: list[str]) -> dict:
    """Process documents through Epstein pipeline"""
    response = requests.post(
        'http://localhost:8000/pipeline/run',
        json={"documents": documents}
    )
    return response.json()

@agent.tool
async def search_documents(query: str, limit: int = 10) -> list:
    """Search documents using semantic search"""
    response = requests.post(
        'http://localhost:8000/vector/search',
        json={"query": query, "limit": limit}
    )
    return response.json()["results"]

# Use the agent
result = await agent.run(
    "Process the new DOJ documents and find mentions of financial transactions"
)
```

## Configuration

### Environment Variables

```bash
# Server settings
MCP_HOST=0.0.0.0
MCP_PORT=8000

# Database
POSTGRES_DSN=postgresql://analysis:analysis@localhost:5432/analysis
QDRANT_URL=http://localhost:6333

# Paths
ARTIFACTS_DIR=./epstein_artifacts
CONFIG_FILE=./config.json
AGENT_CONFIG=./config/agent_config.json
```

### Configuration File

Create `config.json`:
```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8000,
    "enable_cors": true
  },
  "database": {
    "postgres_dsn": "postgresql://analysis:analysis@localhost:5432/analysis",
    "qdrant_url": "http://localhost:6333"
  },
  "pipeline": {
    "artifacts_dir": "./epstein_artifacts",
    "config_file": "./config.json"
  }
}
```

## Architecture

```
┌─────────────────────────────────────────────┐
│         FastAPI MCP Server                  │
│  ┌────────────────────────────────────────┐ │
│  │  REST API Endpoints                    │ │
│  │  - Pipeline  - Database  - Vector     │ │
│  │  - Agents    - Health    - Tools      │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
                     │
      ┌──────────────┼──────────────┐
      │              │              │
      ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Pipeline │  │ Database │  │  Agents  │
│  Engine  │  │  Layer   │  │  System  │
└──────────┘  └──────────┘  └──────────┘
      │              │              │
      └──────────────┼──────────────┘
                     ▼
            ┌─────────────────┐
            │   Data Storage  │
            │  - PostgreSQL   │
            │  - Qdrant       │
            │  - Artifacts    │
            └─────────────────┘
```

## Development

### Adding New Endpoints

1. Define Pydantic models for request/response
2. Add route handler in `_setup_routes()`
3. Implement business logic as helper method
4. Add to tool definitions in `_get_tool_definitions()`
5. Update documentation

### Running Tests

```bash
# Install test dependencies
uv pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/test_mcp_server.py -v

# With coverage
pytest tests/test_mcp_server.py --cov=server --cov-report=html
```

### Code Quality

```bash
# Format
black server.py

# Lint
ruff check server.py

# Type check
mypy server.py
```

## Security

### Best Practices

1. **Authentication**: Add API key authentication for production
2. **Rate Limiting**: Implement rate limiting for public endpoints
3. **Input Validation**: All inputs validated with Pydantic
4. **CORS**: Configure appropriate CORS origins
5. **HTTPS**: Use HTTPS in production
6. **Logging**: Comprehensive audit logging

### Production Deployment

```bash
# Run with Gunicorn
gunicorn server:app -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000

# Docker deployment
docker build -t epstein-mcp-server .
docker run -p 8000:8000 epstein-mcp-server
```

## Troubleshooting

### Server Won't Start

```bash
# Check port availability
netstat -an | grep 8000

# Use different port
python server.py --port 8001
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
psql postgresql://analysis:analysis@localhost:5432/analysis

# Test Qdrant connection
curl http://localhost:6333/
```

### Performance Issues

```bash
# Monitor server
curl http://localhost:8000/health

# Check logs
tail -f /var/log/epstein-mcp-server.log

# Monitor resources
top -p $(pgrep -f "python.*server.py")
```

## Related Documentation

- [Agent Capability Matrix](../../docs/AGENT_CAPABILITY_MATRIX.md)
- [Repository Structure](../../docs/REPOSITORY_STRUCTURE.md)
- [Agent Configuration Schema](../../schemas/agent_config_schema.json)
- [Epstein Files Downloader MCP](../epstein_files_downloader/README.md)

## Support

- **Issues**: https://github.com/cbwinslow/epstein/issues
- **Documentation**: `docs/` directory
- **Examples**: `examples/` directory

## License

Part of the Epstein Files Pipeline project. See main repository for license information.

---

**Version**: 1.0.0  
**Last Updated**: 2026-01-15  
**Maintainer**: Epstein Project Team
