# Epstein Files Downloader MCP Server

A Model Context Protocol (MCP) compliant server for downloading and managing Epstein-related documents from government sources.

## Overview

The Epstein Files Downloader MCP Server provides a standardized REST API for AI agents and automation tools to discover, download, and track documents from multiple government sources including:

- **DOJ Disclosures**: Department of Justice Epstein document releases
- **FBI Vault**: FBI FOIA records for Jeffrey Epstein
- **House Oversight**: Congressional oversight committee releases

## Features

### Core Functionality

- ✅ **Collection Discovery**: Auto-discover available document collections
- ✅ **Bulk Downloads**: Download entire collections with progress tracking
- ✅ **Status Monitoring**: Real-time download progress and status
- ✅ **Retry Logic**: Automatic retry with exponential backoff
- ✅ **Checksum Verification**: SHA-256 integrity checking
- ✅ **Queue Management**: Concurrent download processing
- ✅ **Manifest Generation**: JSONL manifest files for provenance

### API Features

- 🔌 **REST API**: FastAPI-based HTTP interface
- 📚 **OpenAPI Docs**: Interactive API documentation at `/docs`
- 🔍 **Health Checks**: Built-in health monitoring
- 📊 **Status Tracking**: Download history and active task monitoring
- 🛡️ **Error Handling**: Comprehensive error reporting
- ⚡ **Async Support**: AsyncIO-based concurrent operations

## Quick Start

### Prerequisites

- Python 3.10 or higher
- pip or uv package manager
- Network access to government sources

### Installation

```bash
# Navigate to MCP server directory
cd mcp_servers/epstein_files_downloader

# Install dependencies
pip install -r requirements.txt

# Or using uv
uv pip install -r requirements.txt
```

### Running the Server

```bash
# Start with default settings
python server.py

# Custom configuration
python server.py \
  --host 0.0.0.0 \
  --port 8765 \
  --download-dir /data/downloads \
  --max-concurrent 5 \
  --verbose
```

### Verify Server is Running

```bash
# Check health
curl http://localhost:8765/health

# View API documentation
open http://localhost:8765/docs
```

## API Reference

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Server information and endpoint list |
| `/health` | GET | Health check and server statistics |
| `/collections` | GET | List all available document collections |
| `/collections/{id}` | GET | Get specific collection details |
| `/collections/{id}/documents` | GET | List documents in a collection |
| `/download` | POST | Download a single document |
| `/download/bulk` | POST | Bulk download from a collection |
| `/download/status` | GET | Get all active download statuses |
| `/download/status/{task_id}` | GET | Get specific download status |
| `/download/history` | GET | Get download history |

### Example Usage

#### List Collections

```bash
curl http://localhost:8765/collections
```

Response:
```json
[
  {
    "collection_id": "doj_releases",
    "name": "DOJ Epstein Disclosures",
    "description": "Department of Justice document releases",
    "document_count": 150,
    "url": "https://www.justice.gov/epstein/doj-disclosures",
    "source": "justice.gov"
  }
]
```

#### Download a Collection

```bash
curl -X POST http://localhost:8765/download/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "collection_id": "doj_releases",
    "destination": "/tmp/downloads"
  }'
```

Response:
```json
[
  {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "url": "https://www.justice.gov/epstein/dataset_01.zip",
    "status": "queued",
    "progress": 0.0
  }
]
```

#### Check Download Status

```bash
curl http://localhost:8765/download/status/550e8400-e29b-41d4-a716-446655440000
```

Response:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://www.justice.gov/epstein/dataset_01.zip",
  "destination": "/tmp/downloads/dataset_01.zip",
  "status": "downloading",
  "progress": 45.2,
  "error": null,
  "created_at": 1735632748.123,
  "updated_at": 1735632750.456
}
```

## Configuration

### Environment Variables

```bash
# Server configuration
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8765

# Download settings
DOWNLOAD_DIR=/data/downloads
MAX_CONCURRENT_DOWNLOADS=5
RETRY_ATTEMPTS=3
RETRY_DELAY=5
TIMEOUT_SECONDS=60

# User agent for HTTP requests
USER_AGENT="MCP-EpsteinFilesDownloader/1.0"
```

### Configuration File

Create `config.json`:

```json
{
  "host": "0.0.0.0",
  "port": 8765,
  "download_dir": "./downloads",
  "max_concurrent_downloads": 5,
  "retry_attempts": 3,
  "retry_delay": 5,
  "timeout_seconds": 60
}
```

## Integration with AI Agents

### PydanticAI Example

```python
from pydantic_ai import Agent
from pydantic import BaseModel
import requests

class DownloadRequest(BaseModel):
    collection_id: str
    destination: str

agent = Agent(
    model='openai:gpt-4',
    system_prompt='You are a document retrieval specialist.'
)

@agent.tool
async def download_collection(request: DownloadRequest) -> dict:
    """Download documents from a collection"""
    response = requests.post(
        'http://localhost:8765/download/bulk',
        json=request.model_dump()
    )
    return response.json()

# Use the agent
result = await agent.run(
    "Download all DOJ disclosure documents"
)
```

### Python Requests Example

```python
import requests
import time

# Discover collections
collections = requests.get('http://localhost:8765/collections').json()

# Download a collection
for collection in collections:
    if 'doj' in collection['collection_id']:
        response = requests.post(
            'http://localhost:8765/download/bulk',
            json={'collection_id': collection['collection_id']}
        )
        tasks = response.json()
        
        # Monitor progress
        for task in tasks:
            task_id = task['task_id']
            while True:
                status = requests.get(
                    f'http://localhost:8765/download/status/{task_id}'
                ).json()
                
                if status['status'] == 'completed':
                    print(f"✓ Downloaded: {status['destination']}")
                    break
                elif status['status'] == 'failed':
                    print(f"✗ Failed: {status['error']}")
                    break
                
                print(f"Progress: {status['progress']:.1f}%")
                time.sleep(2)
```

## Architecture

### Components

```
┌─────────────────────────────────────────┐
│         FastAPI Application             │
│  ┌────────────────────────────────────┐ │
│  │      API Endpoints                 │ │
│  │  - Collections                     │ │
│  │  - Documents                       │ │
│  │  - Downloads                       │ │
│  │  - Status                          │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│      EpsteinFilesDownloader             │
│  ┌────────────────────────────────────┐ │
│  │  Collection Discovery              │ │
│  │  - govinfo.gov scraping            │ │
│  │  - FBI Vault API                   │ │
│  │  - House Oversight parsing         │ │
│  └────────────────────────────────────┘ │
│  ┌────────────────────────────────────┐ │
│  │  Download Manager                  │ │
│  │  - Queue-based processing          │ │
│  │  - Concurrent downloads            │ │
│  │  - Retry logic                     │ │
│  │  - Progress tracking               │ │
│  └────────────────────────────────────┘ │
│  ┌────────────────────────────────────┐ │
│  │  Status Tracker                    │ │
│  │  - Active tasks                    │ │
│  │  - Completed tasks                 │ │
│  │  - History management              │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│         File System                     │
│  - downloads/                           │
│  - manifests/                           │
│  - logs/                                │
└─────────────────────────────────────────┘
```

### Data Flow

1. **Discovery**: Client requests available collections
2. **Selection**: Client selects collection(s) to download
3. **Queueing**: Download tasks added to queue
4. **Processing**: Concurrent workers process queue
5. **Tracking**: Status updates reported to client
6. **Completion**: Files stored, manifests generated

## Security

### Security Features

- ✅ **No Code Execution**: Downloaded files never executed
- ✅ **ZIP Slip Protection**: Secure archive extraction
- ✅ **Path Validation**: Prevents directory traversal
- ✅ **Checksum Verification**: SHA-256 integrity checks
- ✅ **Rate Limiting**: Respects source rate limits
- ✅ **Audit Logging**: Complete operation trail

### Security Best Practices

1. **Restrict Download Directory**: Use dedicated directory with appropriate permissions
2. **Network Security**: Run behind firewall, use reverse proxy
3. **Authentication**: Add authentication layer for production
4. **HTTPS**: Use HTTPS in production environments
5. **Resource Limits**: Configure appropriate timeouts and limits

## Troubleshooting

### Common Issues

#### Server Won't Start

```bash
# Check if port is already in use
netstat -an | grep 8765

# Use different port
python server.py --port 8766
```

#### Downloads Failing

```bash
# Check network connectivity
curl -I https://www.justice.gov/epstein/doj-disclosures

# Increase timeout
python server.py --timeout 120

# Check server logs
tail -f /tmp/epstein_downloads.log
```

#### Slow Performance

```bash
# Reduce concurrent downloads
python server.py --max-concurrent 3

# Check disk I/O
iostat -x 1

# Monitor server health
curl http://localhost:8765/health
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest tests/test_mcp_server.py -v

# Run with coverage
pytest tests/test_mcp_server.py --cov=mcp_servers --cov-report=html

# Run integration tests
pytest tests/test_mcp_server.py -m integration
```

### Code Quality

```bash
# Format code
black server.py

# Lint code
ruff check server.py

# Type checking
mypy server.py
```

## Documentation

### Additional Resources

- [AI Agent Workflow Guide](../../knowledge_base/ai_agent_workflow_guide.md)
- [DOJ Releases 2024](../../knowledge_base/doj_releases_2024.md)
- [MCP Server Setup Guide](../../docs/MCP_SERVER_SETUP.md)
- [Agent Documentation](../../knowledge_base/agents.md)

## Support

- **Issues**: https://github.com/cbwinslow/epstein/issues
- **Discussions**: GitHub Discussions
- **Documentation**: `knowledge_base/` directory

## License

This project is part of the Epstein Files Pipeline project. See main repository for license information.

## Contributing

1. Follow the project's code style (Black, Ruff)
2. Add tests for new features
3. Update documentation
4. Follow append-only rules for `RULES.md` and `agents.md`
5. Submit PRs with clear descriptions

---

**Version**: 1.0.0  
**Last Updated**: 2024-12-31  
**Maintainer**: Epstein Project Team
