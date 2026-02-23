# AI Agent Workflow Guide for Epstein Document Downloads

## Overview

This guide provides step-by-step workflows for AI agents to download, process, and analyze Epstein-related documents using the MCP server and PydanticAI framework.

**Last Updated**: 2024-12-31  
**Target Audience**: AI agents, developers, automated systems  
**Prerequisites**: MCP server running, Python 3.10+, PydanticAI installed

## Table of Contents

1. [Quick Start](#quick-start)
2. [Environment Setup](#environment-setup)
3. [Basic Workflows](#basic-workflows)
4. [Advanced Workflows](#advanced-workflows)
5. [Error Handling](#error-handling)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

## Quick Start

### 1. Start the MCP Server

```bash
cd /home/runner/work/epstein/epstein/mcp_servers/epstein_files_downloader
python server.py --port 8765 --download-dir /tmp/downloads
```

### 2. Verify Server Health

```bash
curl http://localhost:8765/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": 1735632748.123,
  "active_downloads": 0,
  "completed_downloads": 0,
  "queue_size": 0
}
```

### 3. List Available Collections

```bash
curl http://localhost:8765/collections
```

## Environment Setup

### Required Dependencies

```bash
# Install core dependencies
pip install pydantic-ai requests aiohttp beautifulsoup4 lxml

# Install MCP server dependencies
cd mcp_servers/epstein_files_downloader
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file:

```bash
# MCP Server Configuration
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8765
DOWNLOAD_DIR=/data/downloads
MAX_CONCURRENT_DOWNLOADS=5

# Optional: LLM API Keys
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

### Verify Installation

```python
import requests
import pydantic_ai

# Test MCP server connectivity
response = requests.get('http://localhost:8765/health')
assert response.status_code == 200
print("✓ MCP server is accessible")

# Test PydanticAI
from pydantic_ai import Agent
print("✓ PydanticAI is installed")
```

## Basic Workflows

### Workflow 1: Discover Available Collections

**Purpose**: Find all available document collections

```python
import requests
from typing import List, Dict

def discover_collections() -> List[Dict]:
    """Discover all available Epstein document collections"""
    response = requests.get('http://localhost:8765/collections')
    response.raise_for_status()
    collections = response.json()
    
    print(f"Found {len(collections)} collections:")
    for coll in collections:
        print(f"  - {coll['name']} ({coll['document_count']} documents)")
        print(f"    Source: {coll['source']}")
        print(f"    URL: {coll['url']}")
    
    return collections

# Usage
collections = discover_collections()
```

### Workflow 2: List Documents in a Collection

**Purpose**: Get metadata for documents in a specific collection

```python
def list_documents(collection_id: str, limit: int = 100) -> List[Dict]:
    """List documents in a collection with pagination"""
    url = f'http://localhost:8765/collections/{collection_id}/documents'
    params = {'limit': limit, 'offset': 0}
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    documents = response.json()
    
    print(f"Found {len(documents)} documents in '{collection_id}':")
    for doc in documents[:5]:  # Show first 5
        print(f"  - {doc['title']}")
        print(f"    Size: {doc.get('file_size', 'Unknown')} bytes")
        print(f"    URL: {doc['url']}")
    
    return documents

# Usage
docs = list_documents('doj_releases')
```

### Workflow 3: Download a Single Document

**Purpose**: Download one document with progress tracking

```python
import time

def download_document(url: str, destination: str = None) -> Dict:
    """Download a single document and track progress"""
    request_data = {
        'url': url,
        'destination': destination,
        'metadata': {
            'requested_at': time.time(),
            'source': 'manual_request'
        }
    }
    
    # Initiate download
    response = requests.post(
        'http://localhost:8765/download',
        json=request_data
    )
    response.raise_for_status()
    task = response.json()
    task_id = task['task_id']
    
    print(f"Download started: {task_id}")
    
    # Poll for completion
    while True:
        status_response = requests.get(
            f'http://localhost:8765/download/status/{task_id}'
        )
        status = status_response.json()
        
        print(f"Status: {status['status']} - Progress: {status['progress']:.1f}%")
        
        if status['status'] in ['completed', 'failed']:
            break
        
        time.sleep(2)
    
    return status

# Usage
result = download_document(
    'https://www.justice.gov/epstein/dataset_01.zip',
    destination='/tmp/downloads'
)
```

### Workflow 4: Bulk Download Collection

**Purpose**: Download all documents from a collection

```python
def bulk_download_collection(collection_id: str, destination: str = None) -> List[Dict]:
    """Download all documents from a collection"""
    request_data = {
        'collection_id': collection_id,
        'destination': destination,
        'filter_criteria': {},
        'metadata': {
            'bulk_download': True,
            'requested_at': time.time()
        }
    }
    
    # Initiate bulk download
    response = requests.post(
        'http://localhost:8765/download/bulk',
        json=request_data
    )
    response.raise_for_status()
    tasks = response.json()
    
    print(f"Started {len(tasks)} downloads")
    
    # Track progress of all downloads
    task_ids = [task['task_id'] for task in tasks]
    completed = 0
    
    while completed < len(task_ids):
        status_response = requests.get('http://localhost:8765/download/status')
        all_statuses = status_response.json()
        
        completed = sum(
            1 for s in all_statuses 
            if s['task_id'] in task_ids and s['status'] == 'completed'
        )
        
        print(f"Progress: {completed}/{len(task_ids)} completed")
        time.sleep(5)
    
    print("All downloads completed!")
    return tasks

# Usage
results = bulk_download_collection('doj_releases', '/tmp/downloads')
```

## Advanced Workflows

### Workflow 5: PydanticAI Agent for Automated Downloads

**Purpose**: Create an AI agent that autonomously downloads documents

```python
from pydantic_ai import Agent
from pydantic import BaseModel
import requests

class DownloadRequest(BaseModel):
    collection_id: str
    destination: str
    filter_by_date: str | None = None

class DownloadAgent:
    """AI agent for automated document downloads"""
    
    def __init__(self, mcp_server_url: str = 'http://localhost:8765'):
        self.mcp_url = mcp_server_url
        self.agent = Agent(
            model='openai:gpt-4',
            system_prompt='''You are a document retrieval specialist.
            Your job is to help users download Epstein-related documents
            from government sources. Use the available tools to discover
            collections, list documents, and initiate downloads.'''
        )
        self._register_tools()
    
    def _register_tools(self):
        """Register MCP server tools with the agent"""
        
        @self.agent.tool
        def list_collections() -> list[dict]:
            """List all available document collections"""
            response = requests.get(f'{self.mcp_url}/collections')
            return response.json()
        
        @self.agent.tool
        def download_collection(request: DownloadRequest) -> dict:
            """Download all documents from a collection"""
            response = requests.post(
                f'{self.mcp_url}/download/bulk',
                json=request.model_dump()
            )
            return response.json()
        
        @self.agent.tool
        def check_download_status(task_id: str) -> dict:
            """Check the status of a download task"""
            response = requests.get(
                f'{self.mcp_url}/download/status/{task_id}'
            )
            return response.json()
    
    async def run(self, user_request: str) -> str:
        """Run the agent with a user request"""
        result = await self.agent.run(user_request)
        return result.data

# Usage
async def main():
    agent = DownloadAgent()
    result = await agent.run(
        "Download all DOJ disclosure documents from December 2024"
    )
    print(result)

# Run with asyncio
import asyncio
asyncio.run(main())
```

### Workflow 6: Multi-Source Download with Verification

**Purpose**: Download from multiple sources with checksum verification

```python
import hashlib
from pathlib import Path

def verify_download(file_path: Path, expected_sha256: str = None) -> bool:
    """Verify downloaded file integrity"""
    if not file_path.exists():
        return False
    
    # Calculate SHA-256
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256_hash.update(chunk)
    
    calculated = sha256_hash.hexdigest()
    
    if expected_sha256:
        return calculated == expected_sha256
    else:
        print(f"SHA-256: {calculated}")
        return True

def download_and_verify_collection(collection_id: str) -> Dict:
    """Download collection and verify all files"""
    # Initiate bulk download
    response = requests.post(
        'http://localhost:8765/download/bulk',
        json={'collection_id': collection_id}
    )
    tasks = response.json()
    
    # Wait for completion
    task_ids = [t['task_id'] for t in tasks]
    results = {}
    
    for task_id in task_ids:
        # Wait for completion
        while True:
            status = requests.get(
                f'http://localhost:8765/download/status/{task_id}'
            ).json()
            
            if status['status'] == 'completed':
                # Verify file
                file_path = Path(status['destination'])
                is_valid = verify_download(file_path)
                results[task_id] = {
                    'file': str(file_path),
                    'verified': is_valid
                }
                break
            elif status['status'] == 'failed':
                results[task_id] = {
                    'error': status.get('error'),
                    'verified': False
                }
                break
            
            time.sleep(2)
    
    # Summary
    total = len(results)
    verified = sum(1 for r in results.values() if r.get('verified'))
    print(f"Download complete: {verified}/{total} files verified")
    
    return results

# Usage
results = download_and_verify_collection('doj_releases')
```

### Workflow 7: Incremental Download with Resume

**Purpose**: Resume interrupted downloads

```python
def get_download_history() -> List[Dict]:
    """Get history of previous downloads"""
    response = requests.get('http://localhost:8765/download/history')
    return response.json()

def resume_failed_downloads(destination: str = None) -> List[Dict]:
    """Resume any failed downloads"""
    history = get_download_history()
    
    # Find failed downloads
    failed = [h for h in history if h['status'] == 'failed']
    print(f"Found {len(failed)} failed downloads")
    
    # Retry each failed download
    retried = []
    for task in failed:
        print(f"Retrying: {task['url']}")
        response = requests.post(
            'http://localhost:8765/download',
            json={
                'url': task['url'],
                'destination': destination or task['destination'],
                'metadata': {
                    'retry': True,
                    'original_task_id': task['task_id']
                }
            }
        )
        retried.append(response.json())
    
    return retried

# Usage
retried_tasks = resume_failed_downloads()
```

## Error Handling

### Common Error Scenarios

#### 1. Network Errors

```python
import requests
from requests.exceptions import RequestException

def safe_request(url: str, max_retries: int = 3) -> requests.Response:
    """Make HTTP request with retry logic"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response
        except RequestException as e:
            if attempt == max_retries - 1:
                raise
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt)  # Exponential backoff
```

#### 2. Server Unavailable

```python
def wait_for_server(url: str, timeout: int = 60) -> bool:
    """Wait for MCP server to become available"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(f'{url}/health', timeout=5)
            if response.status_code == 200:
                return True
        except RequestException:
            pass
        time.sleep(5)
    return False

# Usage
if wait_for_server('http://localhost:8765'):
    print("Server is ready")
else:
    print("Server did not start in time")
```

#### 3. Disk Space Issues

```python
import shutil

def check_disk_space(path: str, required_bytes: int) -> bool:
    """Check if enough disk space is available"""
    stat = shutil.disk_usage(path)
    available = stat.free
    
    if available < required_bytes:
        print(f"Insufficient disk space: {available / 1e9:.2f} GB available")
        print(f"Required: {required_bytes / 1e9:.2f} GB")
        return False
    
    return True

# Usage before bulk download
if check_disk_space('/tmp/downloads', 10 * 1024**3):  # 10 GB
    bulk_download_collection('doj_releases')
```

## Best Practices

### 1. Rate Limiting

```python
import time
from datetime import datetime, timedelta

class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.calls = []
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = datetime.now()
        # Remove calls older than 1 minute
        self.calls = [c for c in self.calls if now - c < timedelta(minutes=1)]
        
        if len(self.calls) >= self.calls_per_minute:
            # Wait until oldest call is 1 minute old
            wait_until = self.calls[0] + timedelta(minutes=1)
            wait_seconds = (wait_until - now).total_seconds()
            if wait_seconds > 0:
                time.sleep(wait_seconds)
        
        self.calls.append(now)

# Usage
limiter = RateLimiter(calls_per_minute=30)

for url in document_urls:
    limiter.wait_if_needed()
    download_document(url)
```

### 2. Progress Tracking

```python
from tqdm import tqdm

def download_with_progress(urls: List[str]) -> List[Dict]:
    """Download multiple URLs with progress bar"""
    results = []
    
    with tqdm(total=len(urls), desc="Downloading") as pbar:
        for url in urls:
            result = download_document(url)
            results.append(result)
            pbar.update(1)
    
    return results
```

### 3. Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('downloads.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def logged_download(url: str) -> Dict:
    """Download with comprehensive logging"""
    logger.info(f"Starting download: {url}")
    
    try:
        result = download_document(url)
        logger.info(f"Completed: {result['destination']}")
        return result
    except Exception as e:
        logger.error(f"Failed: {url} - {e}")
        raise
```

## Troubleshooting

### Issue: Server Not Responding

**Symptoms**: Connection refused or timeout errors

**Solutions**:
1. Check if server is running: `ps aux | grep server.py`
2. Verify port is correct: `netstat -an | grep 8765`
3. Check server logs for errors
4. Restart server with verbose logging: `python server.py --verbose`

### Issue: Downloads Failing

**Symptoms**: Downloads show 'failed' status

**Solutions**:
1. Check network connectivity
2. Verify source URLs are accessible
3. Review error messages in task status
4. Check disk space availability
5. Increase timeout settings

### Issue: Slow Downloads

**Symptoms**: Downloads taking longer than expected

**Solutions**:
1. Reduce concurrent downloads: `--max-concurrent 3`
2. Check network bandwidth
3. Verify no rate limiting by source
4. Use closer mirror if available

### Issue: Incomplete Downloads

**Symptoms**: Files smaller than expected

**Solutions**:
1. Check for interrupted connections
2. Verify checksums against manifest
3. Re-download with `--resume` flag
4. Review server error logs

## Related Documentation

- [MCP Server Setup](../docs/MCP_SERVER_SETUP.md)
- [DOJ Releases 2024](doj_releases_2024.md)
- [AI Agent Cheat Sheet](../docs/AI_AGENT_CHEAT_SHEET.md)
- [Agents Documentation](agents.md)
- [RULES.md](../docs/RULES.md)

## Support and Feedback

- **Issues**: https://github.com/cbwinslow/epstein/issues
- **Discussions**: GitHub Discussions
- **Documentation**: `knowledge_base/` directory

---

**Last Updated**: 2024-12-31  
**Version**: 1.0.0  
**Maintainer**: Epstein Project Team
