#!/usr/bin/env python3
"""
Epstein Files Downloader MCP Server

Model Context Protocol (MCP) server for downloading Epstein-related documents
from government sources including govinfo.gov and other official repositories.

This server provides tools for:
- Discovering available document collections
- Downloading documents with metadata
- Tracking download progress
- Managing download configurations
- Integrating with the main pipeline
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time
import zipfile
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple
from uuid import uuid4

try:
    import aiohttp
except Exception:  # pragma: no cover - optional dependency
    aiohttp = None
try:
    from fastapi import BackgroundTasks, FastAPI, HTTPException
    from fastapi.responses import FileResponse
except Exception:  # pragma: no cover - optional dependency
    FastAPI = None
    HTTPException = Exception
    BackgroundTasks = None
    FileResponse = None

import requests
from bs4 import BeautifulSoup

# Import CORSMiddleware only if FastAPI is available
if FastAPI is not None:
    from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("epstein_files_downloader")


def _require_aiohttp():
    if aiohttp is None:
        raise RuntimeError(
            "aiohttp is required for async downloads. Install it (e.g., `uv add aiohttp` and `uv install`)"
        )


# ============================================================================
# Configuration and Data Models
# ============================================================================

@dataclass
class ServerConfig:
    """Configuration for the MCP server"""
    host: str = "0.0.0.0"
    port: int = 8765
    base_url: str = "http://localhost:8765"
    download_dir: str = "./downloads"
    max_concurrent_downloads: int = 5
    retry_attempts: int = 3
    retry_delay: int = 5
    user_agent: str = "MCP-EpsteinFilesDownloader/1.0"
    timeout_seconds: int = 60
    polite_delay_seconds: float = 0.25
    max_bulk_documents: int = 100000
    max_requests_per_minute: int = 120
    
    # GovInfo.gov specific settings
    govinfo_base_url: str = "https://www.govinfo.gov"
    govinfo_bulk_api: str = "https://www.govinfo.gov/bulkdata/bulkdata"
    govinfo_collections: str = "https://www.govinfo.gov/bulkdata"


@dataclass
class DownloadTask:
    """Represents a download task"""
    task_id: str
    url: str
    destination: str
    status: str = "pending"
    progress: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    file_path: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class CollectionInfo:
    """Information about a document collection"""
    collection_id: str
    name: str
    description: str
    url: str
    document_count: int = 0
    source: str = "govinfo.gov"
    last_updated: Optional[str] = None


@dataclass
class DocumentInfo:
    """Metadata about a document"""
    document_id: str
    collection_id: str
    title: str
    url: str
    file_size: Optional[int] = None
    publish_date: Optional[str] = None
    mime_type: Optional[str] = None
    file_name: Optional[str] = None
    metadata: Dict[str, Any] = None


# Pydantic models for API
class CollectionResponse(BaseModel):
    """API response for collection information"""
    collection_id: str
    name: str
    description: str
    document_count: int
    url: HttpUrl
    source: str
    last_updated: Optional[str] = None


class DocumentResponse(BaseModel):
    """API response for document information"""
    document_id: str
    collection_id: str
    title: str
    url: HttpUrl
    file_size: Optional[int] = None
    publish_date: Optional[str] = None
    mime_type: Optional[str] = None
    file_name: Optional[str] = None
    metadata: Dict[str, Any] = None


class DownloadStatus(BaseModel):
    """API response for download status"""
    task_id: str
    url: HttpUrl
    destination: str
    status: str
    progress: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    file_path: Optional[str] = None
    created_at: float
    updated_at: float


class DownloadRequest(BaseModel):
    """API request for download"""
    url: HttpUrl
    destination: Optional[str] = None
    metadata: Dict[str, Any] = None


class BulkDownloadRequest(BaseModel):
    """API request for bulk download"""
    collection_id: str
    destination: Optional[str] = None
    filter_criteria: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    limit: Optional[int] = None
    offset: int = 0
    page_size: int = 100
    max_pages: Optional[int] = None
    archive_after: bool = False
    archive_name: Optional[str] = None
    output_mode: str = "download"  # download|manifest


class BulkDownloadResponse(BaseModel):
    """API response for bulk download with pagination"""
    tasks: List[DownloadStatus]
    next_offset: Optional[int] = None
    total_requested: int


class DocumentPageResponse(BaseModel):
    """Paginated documents response"""
    documents: List[DocumentResponse]
    next_offset: Optional[int] = None


class ArchiveRequest(BaseModel):
    """Request to create an archive from completed tasks or a directory."""
    task_ids: Optional[List[str]] = None
    directory: Optional[str] = None
    archive_path: Optional[str] = None


# ============================================================================
# MCP Server Implementation
# ============================================================================

class EpsteinFilesDownloader:
    """Main MCP server for downloading Epstein files"""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.session = None
        self.download_queue = asyncio.Queue()
        self.active_tasks: Dict[str, DownloadTask] = {}
        self.completed_tasks: Dict[str, DownloadTask] = {}
        self._request_times: Deque[float] = deque()
        self._rate_lock = asyncio.Lock()
        self.status = "initialized"
        
        # Initialize download directory
        Path(config.download_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="Epstein Files Downloader MCP Server",
            description="MCP Server for downloading Epstein-related documents from government sources",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Register API endpoints
        self._register_endpoints()
        
        # Initialize HTTP session
        self._init_http_session()
    
    def _init_http_session(self):
        """Initialize HTTP session with retry configuration"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config.user_agent,
            'Accept': 'application/json',
        })
    
    def _register_endpoints(self):
        """Register all API endpoints"""
        
        @self.app.get("/")
        async def root():
            """Root endpoint"""
            return {
                "server": "Epstein Files Downloader MCP Server",
                "version": "1.0.0",
                "status": "running",
                "endpoints": {
                    "/collections": "List available collections",
                    "/collections/{collection_id}": "Get collection details",
                    "/collections/{collection_id}/documents": "List documents in collection",
                    "/download": "Download single document",
                    "/download/bulk": "Bulk download from collection",
                    "/download/status": "Check download status",
                    "/download/status/{task_id}": "Check specific download status",
                    "/download/history": "Get download history",
                    "/health": "Health check endpoint"
                }
            }
        
        @self.app.get("/health")
        async def health():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": time.time(),
                "active_downloads": len(self.active_tasks),
                "completed_downloads": len(self.completed_tasks),
                "queue_size": self.download_queue.qsize()
            }
        
        @self.app.get("/collections", response_model=List[CollectionResponse])
        async def list_collections():
            """List all available document collections"""
            try:
                collections = await self.discover_collections()
                return [
                    CollectionResponse(
                        collection_id=coll.collection_id,
                        name=coll.name,
                        description=coll.description,
                        document_count=coll.document_count,
                        url=coll.url,
                        source=coll.source,
                        last_updated=coll.last_updated
                    )
                    for coll in collections
                ]
            except Exception as e:
                logger.error(f"Failed to list collections: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/collections/{collection_id}", response_model=CollectionResponse)
        async def get_collection(collection_id: str):
            """Get details about a specific collection"""
            try:
                collections = await self.discover_collections()
                for coll in collections:
                    if coll.collection_id == collection_id:
                        return CollectionResponse(
                            collection_id=coll.collection_id,
                            name=coll.name,
                            description=coll.description,
                            document_count=coll.document_count,
                            url=coll.url,
                            source=coll.source,
                            last_updated=coll.last_updated
                        )
                raise HTTPException(status_code=404, detail="Collection not found")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get collection {collection_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/collections/{collection_id}/documents", response_model=List[DocumentResponse])
        async def list_collection_documents(
            collection_id: str,
            limit: int = 100,
            offset: int = 0,
            page_size: int = 100,
        ):
            """List documents in a collection"""
            try:
                documents = await self.get_collection_documents(collection_id, limit, offset, page_size=page_size)
                return [
                    DocumentResponse(
                        document_id=doc.document_id,
                        collection_id=doc.collection_id,
                        title=doc.title,
                        url=doc.url,
                        file_size=doc.file_size,
                        publish_date=doc.publish_date,
                        mime_type=doc.mime_type,
                        file_name=doc.file_name,
                        metadata=doc.metadata or {}
                    )
                    for doc in documents
                ]
            except Exception as e:
                logger.error(f"Failed to list documents for collection {collection_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/collections/{collection_id}/documents/paginated", response_model=DocumentPageResponse)
        async def list_collection_documents_paginated(
            collection_id: str,
            limit: int = 100,
            offset: int = 0,
            page_size: int = 100,
        ):
            """List documents in a collection with pagination metadata"""
            try:
                documents = await self.get_collection_documents(collection_id, limit, offset, page_size=page_size)
                next_offset = None if len(documents) < limit else offset + limit
                return DocumentPageResponse(
                    documents=[
                        DocumentResponse(
                            document_id=doc.document_id,
                            collection_id=doc.collection_id,
                            title=doc.title,
                            url=doc.url,
                            file_size=doc.file_size,
                            publish_date=doc.publish_date,
                            mime_type=doc.mime_type,
                            file_name=doc.file_name,
                            metadata=doc.metadata or {},
                        )
                        for doc in documents
                    ],
                    next_offset=next_offset,
                )
            except Exception as e:
                logger.error(f"Failed to list documents for collection {collection_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/download", response_model=DownloadStatus)
        async def download_document(request: DownloadRequest, background_tasks: BackgroundTasks):
            """Download a single document"""
            try:
                task_id = str(uuid4())
                destination = request.destination or self.config.download_dir
                
                task = DownloadTask(
                    task_id=task_id,
                    url=str(request.url),
                    destination=destination,
                    status="queued",
                    metadata=request.metadata or {}
                )
                
                self.active_tasks[task_id] = task
                await self.download_queue.put(task)
                
                # Start download in background
                background_tasks.add_task(self._process_download_queue)
                
                return DownloadStatus(**asdict(task))
            except Exception as e:
                logger.error(f"Failed to start download: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/download/bulk", response_model=List[DownloadStatus])
        async def bulk_download(request: BulkDownloadRequest, background_tasks: BackgroundTasks):
            """Bulk download documents from a collection"""
            try:
                # Get documents from collection
                limit = request.limit or self.config.max_bulk_documents
                offset = request.offset
                documents = await self.get_collection_documents(
                    request.collection_id,
                    limit,
                    offset,
                    page_size=request.page_size,
                    max_pages=request.max_pages,
                )
                
                # Filter documents if criteria provided
                if request.filter_criteria:
                    filtered_docs = []
                    for doc in documents:
                        # Simple filter implementation
                        match = True
                        for key, value in request.filter_criteria.items():
                            if hasattr(doc, key):
                                attr_value = getattr(doc, key)
                                if str(attr_value) != str(value):
                                    match = False
                                    break
                        if match:
                            filtered_docs.append(doc)
                    documents = filtered_docs
                
                if request.output_mode == "manifest":
                    return []

                # Create download tasks
                tasks = []
                for doc in documents:
                    task_id = str(uuid4())
                    destination = request.destination or self.config.download_dir
                    
                    task = DownloadTask(
                        task_id=task_id,
                        url=doc.url,
                        destination=destination,
                        status="queued",
                        metadata={
                            "document_id": doc.document_id,
                            "collection_id": doc.collection_id,
                            "title": doc.title,
                            **(request.metadata or {})
                        }
                    )
                    
                    self.active_tasks[task_id] = task
                    await self.download_queue.put(task)
                    tasks.append(task)
                
                # Start processing queue in background
                background_tasks.add_task(self._process_download_queue)

                if request.archive_after and tasks:
                    archive_name = request.archive_name or f"{request.collection_id}_{int(time.time())}.zip"
                    archive_path = Path(request.destination or self.config.download_dir) / archive_name
                    background_tasks.add_task(self._archive_after_tasks, [t.task_id for t in tasks], archive_path)
                
                return [DownloadStatus(**asdict(task)) for task in tasks]
            except Exception as e:
                logger.error(f"Failed to start bulk download: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/download/bulk/paginated", response_model=BulkDownloadResponse)
        async def bulk_download_paginated(request: BulkDownloadRequest, background_tasks: BackgroundTasks):
            """Bulk download documents with pagination metadata."""
            try:
                limit = request.limit or self.config.max_bulk_documents
                offset = request.offset
                documents = await self.get_collection_documents(
                    request.collection_id,
                    limit,
                    offset,
                    page_size=request.page_size,
                    max_pages=request.max_pages,
                )
                next_offset = None if len(documents) < limit else offset + limit

                if request.output_mode == "manifest":
                    return BulkDownloadResponse(tasks=[], next_offset=next_offset, total_requested=len(documents))

                tasks = []
                for doc in documents:
                    task_id = str(uuid4())
                    destination = request.destination or self.config.download_dir
                    task = DownloadTask(
                        task_id=task_id,
                        url=doc.url,
                        destination=destination,
                        status="queued",
                        metadata={
                            "document_id": doc.document_id,
                            "collection_id": doc.collection_id,
                            "title": doc.title,
                            **(request.metadata or {}),
                        },
                    )
                    self.active_tasks[task_id] = task
                    await self.download_queue.put(task)
                    tasks.append(task)

                background_tasks.add_task(self._process_download_queue)

                if request.archive_after and tasks:
                    archive_name = request.archive_name or f"{request.collection_id}_{int(time.time())}.zip"
                    archive_path = Path(request.destination or self.config.download_dir) / archive_name
                    background_tasks.add_task(self._archive_after_tasks, [t.task_id for t in tasks], archive_path)

                return BulkDownloadResponse(
                    tasks=[DownloadStatus(**asdict(task)) for task in tasks],
                    next_offset=next_offset,
                    total_requested=len(tasks),
                )
            except Exception as e:
                logger.error(f"Failed to start bulk paginated download: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/download/status", response_model=List[DownloadStatus])
        async def get_all_download_status():
            """Get status of all active downloads"""
            return [DownloadStatus(**asdict(task)) for task in self.active_tasks.values()]
        
        @self.app.get("/download/status/{task_id}", response_model=DownloadStatus)
        async def get_download_status(task_id: str):
            """Get status of a specific download"""
            if task_id in self.active_tasks:
                return DownloadStatus(**asdict(self.active_tasks[task_id]))
            elif task_id in self.completed_tasks:
                return DownloadStatus(**asdict(self.completed_tasks[task_id]))
            else:
                raise HTTPException(status_code=404, detail="Task not found")

        @self.app.get("/download/stream/{task_id}")
        async def stream_download(task_id: str):
            """Stream a completed download to the client."""
            if FileResponse is None:
                raise HTTPException(status_code=500, detail="FastAPI FileResponse unavailable")
            task = self.completed_tasks.get(task_id)
            if not task or not task.file_path:
                raise HTTPException(status_code=404, detail="File not available for streaming")
            path = Path(task.file_path)
            if not path.exists():
                raise HTTPException(status_code=404, detail="File not found on disk")
            return FileResponse(path)
        
        @self.app.get("/download/history", response_model=List[DownloadStatus])
        async def get_download_history(limit: int = 100):
            """Get download history"""
            # Return most recent completed tasks
            completed = sorted(self.completed_tasks.values(), key=lambda x: x.updated_at, reverse=True)
            return [DownloadStatus(**asdict(task)) for task in completed[:limit]]

        @self.app.post("/download/archive")
        async def archive_downloads(request: ArchiveRequest):
            """Create a ZIP archive from completed downloads or a directory."""
            archive_path = request.archive_path or str(Path(self.config.download_dir) / f"downloads_{int(time.time())}.zip")
            files: List[Path] = []
            if request.task_ids:
                for tid in request.task_ids:
                    task = self.completed_tasks.get(tid)
                    if task and task.file_path:
                        path = Path(task.file_path)
                        if path.exists():
                            files.append(path)
            if request.directory:
                directory = Path(request.directory)
                if directory.exists():
                    files.extend([p for p in directory.rglob("*") if p.is_file()])

            if not files:
                raise HTTPException(status_code=404, detail="No files found to archive")
            self._create_archive(files, Path(archive_path))
            return {"archive_path": archive_path, "file_count": len(files)}
    
    async def _process_download_queue(self):
        """Process download queue with concurrency control"""
        while not self.download_queue.empty():
            tasks = []
            # Get up to max_concurrent_downloads tasks
            for _ in range(min(self.config.max_concurrent_downloads, self.download_queue.qsize())):
                task = await self.download_queue.get()
                tasks.append(task)
            
            # Process tasks concurrently
            await asyncio.gather(*[self._download_single(task) for task in tasks])

    async def _apply_rate_limit(self) -> None:
        """Best-effort rate limiting to respect source limits."""
        async with self._rate_lock:
            now = time.time()
            window_start = now - 60
            while self._request_times and self._request_times[0] < window_start:
                self._request_times.popleft()
            if len(self._request_times) >= self.config.max_requests_per_minute:
                sleep_for = self._request_times[0] + 60 - now
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
            self._request_times.append(time.time())
    
    async def _download_single(self, task: DownloadTask):
        """Download a single file with retry logic"""
        task.status = "downloading"
        task.progress = 0.0
        task.updated_at = time.time()
        
        destination_path = Path(task.destination)
        if destination_path.suffix:
            destination_dir = destination_path.parent
        else:
            destination_dir = destination_path
        destination_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate safe filename
        safe_filename = self._generate_safe_filename(task.url, task.metadata)
        final_path = destination_dir / safe_filename
        
        # Skip if already exists
        if final_path.exists() and final_path.stat().st_size > 1000:
            task.status = "completed"
            task.progress = 100.0
            task.destination = str(final_path)
            task.file_path = str(final_path)
            self._complete_task(task)
            return
        
        # Download with retry
        for attempt in range(self.config.retry_attempts):
            try:
                # Use aiohttp for async download
                _require_aiohttp()
                await self._apply_rate_limit()
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        task.url,
                        timeout=self.config.timeout_seconds,
                        headers={"User-Agent": self.config.user_agent},
                    ) as response:
                        if response.status != 200:
                            raise HTTPException(status_code=response.status, detail=f"HTTP {response.status}")
                        
                        total_size = int(response.headers.get('content-length', 0))
                        downloaded = 0
                        
                        with open(final_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                                downloaded += len(chunk)
                                task.progress = (downloaded / total_size * 100) if total_size > 0 else 0
                                task.updated_at = time.time()
                                
                                # Update progress periodically
                                if downloaded % (1024 * 1024) < 8192:  # Every ~1MB
                                    logger.debug(f"Download {task.task_id}: {task.progress:.1f}% ({downloaded}/{total_size} bytes)")
                        
                        # Complete task
                        task.status = "completed"
                        task.progress = 100.0
                        task.destination = str(final_path)
                        task.file_path = str(final_path)
                        task.updated_at = time.time()
                        self._complete_task(task)
                        logger.info(f"✅ Completed download {task.task_id}: {task.url}")
                        if self.config.polite_delay_seconds:
                            await asyncio.sleep(self.config.polite_delay_seconds)
                        return
                        
            except Exception as e:
                task.status = "retrying"
                task.error = str(e)
                task.updated_at = time.time()
                logger.warning(f"⚠️  Download attempt {attempt + 1} failed for {task.task_id}: {e}")
                
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    task.status = "failed"
                    task.error = f"Failed after {self.config.retry_attempts} attempts: {e}"
                    task.updated_at = time.time()
                    self._complete_task(task)
                    logger.error(f"❌ Failed download {task.task_id}: {e}")
                    return
    
    def _complete_task(self, task: DownloadTask):
        """Move task from active to completed"""
        if task.task_id in self.active_tasks:
            del self.active_tasks[task.task_id]
        self.completed_tasks[task.task_id] = task
        
        # Keep completed tasks manageable
        if len(self.completed_tasks) > 1000:
            # Remove oldest tasks
            sorted_tasks = sorted(self.completed_tasks.items(), key=lambda x: x[1].updated_at)
            for task_id, _ in sorted_tasks[:-500]:
                del self.completed_tasks[task_id]

    async def _archive_after_tasks(self, task_ids: List[str], archive_path: Path) -> None:
        """Wait for tasks to finish and archive completed files."""
        pending = set(task_ids)
        while pending:
            done = {tid for tid in list(pending) if tid in self.completed_tasks}
            pending -= done
            if pending:
                await asyncio.sleep(2)

        files: List[Path] = []
        for tid in task_ids:
            task = self.completed_tasks.get(tid)
            if task and task.file_path:
                path = Path(task.file_path)
                if path.exists():
                    files.append(path)
        if not files:
            logger.warning("Archive requested but no files found to include.")
            return
        self._create_archive(files, archive_path)

    def _create_archive(self, files: List[Path], archive_path: Path) -> None:
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in files:
                zf.write(path, arcname=path.name)
    
    def _generate_safe_filename(self, url: str, metadata: Optional[Dict] = None) -> str:
        """Generate safe filename from URL and metadata"""
        import re
        from urllib.parse import urlparse
        
        # Extract filename from URL
        parsed = urlparse(url)
        filename = Path(parsed.path).name
        filename = re.sub(r'[^\w\-_.]', '_', filename)
        
        # Use metadata title if available
        if metadata and metadata.get('title'):
            title = metadata['title']
            # Clean title for filename
            safe_title = re.sub(r'[^\w\s\-_.]', '_', title)
            safe_title = re.sub(r'\s+', '_', safe_title).strip('_')[:50]
            filename = f"{safe_title}_{filename}"
        elif metadata and metadata.get('document_id'):
            filename = f"{metadata['document_id']}_{filename}"
        
        # Ensure unique filename
        counter = 1
        base_name = Path(filename).stem
        extension = Path(filename).suffix
        final_filename = filename
        
        while (Path(self.config.download_dir) / final_filename).exists():
            final_filename = f"{base_name}_{counter}{extension}"
            counter += 1
        
        return final_filename
    
    async def discover_collections(self) -> List[CollectionInfo]:
        """Discover available collections from multiple government sources"""
        collections = []
        
        # Add predefined Epstein-related collections based on known sources
        known_collections = [
            CollectionInfo(
                collection_id="court_documents",
                name="Epstein Court Documents",
                description="Court filings, motions, and rulings related to Jeffrey Epstein case",
                url="https://www.govinfo.gov/search/results?search=Jeffrey%20Epstein",
                source="govinfo.gov",
                document_count=0
            ),
            CollectionInfo(
                collection_id="docket_materials",
                name="Epstein Docket Materials",
                description="Docket entries and case materials from federal courts",
                url="https://www.govinfo.gov/bulkdata",
                source="govinfo.gov",
                document_count=0
            ),
            CollectionInfo(
                collection_id="fbi_vault",
                name="FBI Vault - Epstein Files",
                description="FBI records and documents related to Jeffrey Epstein investigation",
                url="https://vault.fbi.gov/jeffrey-epstein",
                source="fbi.gov",
                document_count=0
            ),
            CollectionInfo(
                collection_id="doj_releases",
                name="DOJ Press Releases and Documents",
                description="Department of Justice releases regarding Epstein case",
                url="https://www.justice.gov/search/results?search=Epstein",
                source="justice.gov",
                document_count=0
            ),
            CollectionInfo(
                collection_id="southern_district_ny",
                name="SDNY Epstein Case Files",
                description="Southern District of New York court documents related to Epstein",
                url="https://www.nysd.uscourts.gov/cases-opinions",
                source="nysd.uscourts.gov",
                document_count=0
            )
        ]
        
        collections.extend(known_collections)
        
        # Try to discover additional collections from govinfo.gov
        try:
            search_url = f"{self.config.govinfo_base_url}/search/results?search=Jeffrey%20Epstein"
            response = self.session.get(search_url, timeout=self.config.timeout_seconds)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for document links
            doc_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if '/content/pkg/' in href:
                    title = link.get_text('').strip()
                    if title and len(title) > 10:  # Filter out short/empty titles
                        doc_links.append({
                            'url': f"{self.config.govinfo_base_url}{href}",
                            'title': title
                        })
            
            if doc_links:
                # Add discovered documents as a collection
                collections.append(CollectionInfo(
                    collection_id="discovered_documents",
                    name="Discovered Epstein Documents",
                    description=f"Documents discovered from govinfo.gov search ({len(doc_links)} items)",
                    url=search_url,
                    source="govinfo.gov",
                    document_count=len(doc_links),
                    last_updated=time.strftime("%Y-%m-%d")
                ))
            
            logger.info(f"Discovered {len(collections)} total collections (including {len(doc_links)} documents)")
            
        except Exception as e:
            logger.warning(f"Failed to discover additional collections from govinfo.gov: {e}")
        
        # Try to get document counts for each collection
        for collection in collections:
            try:
                count = await self._get_collection_document_count(collection)
                collection.document_count = count
            except Exception as e:
                logger.debug(f"Could not get document count for {collection.collection_id}: {e}")
        
        return collections
    
    async def _get_collection_document_count(self, collection: CollectionInfo) -> int:
        """Get document count for a collection"""
        try:
            if collection.source == "fbi.gov":
                # FBI Vault - scrape for document count
                response = self.session.get(collection.url, timeout=self.config.timeout_seconds)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for document count indicators
                count_text = soup.find('span', class_='results-count')
                if count_text:
                    import re
                    numbers = re.findall(r'\d+', count_text.get_text())
                    if numbers:
                        return int(numbers[0])
                
                # Alternative: count document links
                doc_links = soup.find_all('a', href=lambda x: x and '/jeffrey-epstein/' in x)
                return len(doc_links)
                
            elif collection.source == "govinfo.gov":
                # GovInfo.gov - use search API
                search_url = f"{self.config.govinfo_base_url}/search/results?search=Jeffrey%20Epstein&pageSize=1"
                response = self.session.get(search_url, timeout=self.config.timeout_seconds)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for result count
                results_text = soup.find('div', class_='results-summary')
                if results_text:
                    import re
                    numbers = re.findall(r'(\d+,?\d*)', results_text.get_text())
                    if numbers:
                        return int(numbers[0].replace(',', ''))
                
                # Alternative: count links
                doc_links = soup.find_all('a', href=lambda x: x and '/content/pkg/' in x)
                return len(doc_links)
                
            elif collection.source == "justice.gov":
                # DOJ - similar approach
                response = self.session.get(collection.url, timeout=self.config.timeout_seconds)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Count document links
                doc_links = soup.find_all('a', href=lambda x: x and 'epstein' in x.lower())
                return len(doc_links)
                
            else:
                # Generic approach - try to count links
                response = self.session.get(collection.url, timeout=self.config.timeout_seconds)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                links = soup.find_all('a', href=True)
                return len([link for link in links if 'pdf' in link.get('href', '').lower()])
                
        except Exception as e:
            logger.debug(f"Could not get document count for {collection.collection_id}: {e}")
            return 0
    
    async def get_collection_documents(
        self,
        collection_id: str,
        limit: int = 100,
        offset: int = 0,
        page_size: int = 100,
        max_pages: Optional[int] = None,
    ) -> List[DocumentInfo]:
        """Get documents from a specific collection with pagination support."""
        documents: List[DocumentInfo] = []
        
        try:
            # Find collection URL
            collections = await self.discover_collections()
            collection_url = None
            for coll in collections:
                if coll.collection_id == collection_id:
                    collection_url = coll.url
                    break
            
            if not collection_url:
                raise ValueError(f"Collection {collection_id} not found")
            
            remaining = limit
            current_offset = offset
            page = 0
            while remaining > 0:
                if max_pages is not None and page >= max_pages:
                    break
                page_limit = min(page_size, remaining)
                api_url = (
                    f"{self.config.govinfo_bulk_api}?collection={collection_id}"
                    f"&offset={current_offset}&limit={page_limit}"
                )
                response = self.session.get(api_url, timeout=self.config.timeout_seconds)
                response.raise_for_status()

                data = response.json()

                if "packages" in data:
                    for pkg_data in data["packages"]:
                        doc = DocumentInfo(
                            document_id=pkg_data.get("packageId", str(uuid4())),
                            collection_id=collection_id,
                            title=pkg_data.get("title", "Untitled Document"),
                            url=pkg_data.get("downloadUrl", ""),
                            file_size=pkg_data.get("size"),
                            publish_date=pkg_data.get("publishDate"),
                            mime_type=pkg_data.get("mimeType"),
                            file_name=pkg_data.get("fileName"),
                            metadata={
                                "granuleId": pkg_data.get("granuleId"),
                                "granuleTitle": pkg_data.get("granuleTitle"),
                                "collectionName": pkg_data.get("collectionName"),
                            },
                        )
                        documents.append(doc)

                    if len(data["packages"]) < page_limit:
                        break
                    remaining -= len(data["packages"])
                    current_offset += len(data["packages"])
                    page += 1
            
            logger.info(f"Found {len(documents)} documents in collection {collection_id}")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to get documents for collection {collection_id}: {e}")
            return []
    
    def run(self):
        """Run the MCP server"""
        import uvicorn
        
        logger.info(f"🚀 Starting Epstein Files Downloader MCP Server")
        logger.info(f"📍 Server URL: {self.config.base_url}")
        logger.info(f"📁 Download directory: {self.config.download_dir}")
        logger.info(f"🔗 Max concurrent downloads: {self.config.max_concurrent_downloads}")
        
        # Start background task for download queue
        asyncio.create_task(self._process_download_queue())
        
        # Run FastAPI server
        uvicorn.run(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info",
            access_log=True
        )
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down Epstein Files Downloader MCP Server...")
        
        # Cancel active downloads
        for task_id, task in self.active_tasks.items():
            task.status = "cancelled"
            task.error = "Server shutdown"
            task.updated_at = time.time()
            self._complete_task(task)
            logger.info(f"Cancelled download task {task_id}")
        
        # Close HTTP session
        if self.session:
            self.session.close()
        
        logger.info("✅ Server shutdown complete")


# ============================================================================
# MCP Server Tools Definition
# ============================================================================

MCP_SERVER_TOOLS = {
    "epstein_files_downloader": {
        "description": "MCP Server for downloading Epstein-related documents from government sources",
        "tools": {
            "discover_collections": {
                "description": "Discover available Epstein document collections from government sources",
                "parameters": {},
                "returns": {
                    "type": "array",
                    "description": "List of available collections with metadata"
                }
            },
            "list_collection_documents": {
                "description": "List documents available in a specific collection",
                "parameters": {
                    "collection_id": {
                        "type": "string",
                        "description": "ID of the collection to list documents from"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of documents to return",
                        "default": 100
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset for pagination",
                        "default": 0
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Page size for API requests",
                        "default": 100
                    }
                },
                "returns": {
                    "type": "array",
                    "description": "List of documents with metadata"
                }
            },
            "list_collection_documents_paginated": {
                "description": "List documents with pagination metadata",
                "parameters": {
                    "collection_id": {
                        "type": "string",
                        "description": "ID of the collection to list documents from"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of documents to return",
                        "default": 100
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset for pagination",
                        "default": 0
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Page size for API requests",
                        "default": 100
                    }
                },
                "returns": {
                    "type": "object",
                    "description": "Documents plus next_offset for incremental fetching"
                }
            },
            "download_document": {
                "description": "Download a single document from a URL",
                "parameters": {
                    "url": {
                        "type": "string",
                        "description": "URL of the document to download"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination path for the downloaded file",
                        "optional": True
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata to associate with the download",
                        "optional": True
                    }
                },
                "returns": {
                    "type": "object",
                    "description": "Download task status and information"
                }
            },
            "bulk_download": {
                "description": "Download all documents from a collection",
                "parameters": {
                    "collection_id": {
                        "type": "string",
                        "description": "ID of the collection to download"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Base destination directory for downloaded files",
                        "optional": True
                    },
                    "filter_criteria": {
                        "type": "object",
                        "description": "Criteria to filter documents before downloading",
                        "optional": True
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata to associate with all downloads",
                        "optional": True
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of documents to download",
                        "optional": True
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset for incremental downloads",
                        "default": 0
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Page size per API request",
                        "default": 100
                    },
                    "max_pages": {
                        "type": "integer",
                        "description": "Maximum pages to fetch per request",
                        "optional": True
                    },
                    "archive_after": {
                        "type": "boolean",
                        "description": "Create a ZIP archive after downloads finish",
                        "default": False
                    },
                    "archive_name": {
                        "type": "string",
                        "description": "Optional archive filename",
                        "optional": True
                    },
                    "output_mode": {
                        "type": "string",
                        "description": "download or manifest",
                        "default": "download"
                    }
                },
                "returns": {
                    "type": "array",
                    "description": "List of download task statuses"
                }
            },
            "bulk_download_paginated": {
                "description": "Download documents with pagination metadata",
                "parameters": {
                    "collection_id": {
                        "type": "string",
                        "description": "ID of the collection to download"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Base destination directory for downloaded files",
                        "optional": True
                    },
                    "filter_criteria": {
                        "type": "object",
                        "description": "Criteria to filter documents before downloading",
                        "optional": True
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata to associate with all downloads",
                        "optional": True
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of documents to download",
                        "optional": True
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset for incremental downloads",
                        "default": 0
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Page size per API request",
                        "default": 100
                    },
                    "max_pages": {
                        "type": "integer",
                        "description": "Maximum pages to fetch per request",
                        "optional": True
                    },
                    "archive_after": {
                        "type": "boolean",
                        "description": "Create a ZIP archive after downloads finish",
                        "default": False
                    },
                    "archive_name": {
                        "type": "string",
                        "description": "Optional archive filename",
                        "optional": True
                    },
                    "output_mode": {
                        "type": "string",
                        "description": "download or manifest",
                        "default": "download"
                    }
                },
                "returns": {
                    "type": "object",
                    "description": "Download tasks plus next_offset"
                }
            },
            "stream_download": {
                "description": "Stream a completed download by task ID",
                "parameters": {
                    "task_id": {
                        "type": "string",
                        "description": "Download task ID"
                    }
                },
                "returns": {
                    "type": "file",
                    "description": "Streamed file response"
                }
            },
            "archive_downloads": {
                "description": "Create an archive from completed downloads or a directory",
                "parameters": {
                    "task_ids": {
                        "type": "array",
                        "description": "List of task IDs to archive",
                        "optional": True
                    },
                    "directory": {
                        "type": "string",
                        "description": "Directory to archive",
                        "optional": True
                    },
                    "archive_path": {
                        "type": "string",
                        "description": "Output archive path",
                        "optional": True
                    }
                },
                "returns": {
                    "type": "object",
                    "description": "Archive path and file count"
                }
            },
            "get_download_status": {
                "description": "Get status of a download task",
                "parameters": {
                    "task_id": {
                        "type": "string",
                        "description": "ID of the download task to check"
                    }
                },
                "returns": {
                    "type": "object",
                    "description": "Current status of the download task"
                }
            },
            "get_all_download_status": {
                "description": "Get status of all active download tasks",
                "parameters": {},
                "returns": {
                    "type": "array",
                    "description": "List of all active download task statuses"
                }
            },
            "get_download_history": {
                "description": "Get history of completed download tasks",
                "parameters": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of historical tasks to return",
                        "default": 100
                    }
                },
                "returns": {
                    "type": "array",
                    "description": "List of completed download task statuses"
                }
            },
            "get_server_health": {
                "description": "Check server health and status",
                "parameters": {},
                "returns": {
                    "type": "object",
                    "description": "Server health information and statistics"
                }
            }
        }
    }
}


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Epstein Files Downloader MCP Server"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host address to bind to"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to listen on"
    )
    parser.add_argument(
        "--download-dir",
        default="./downloads",
        help="Directory to store downloaded files"
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=5,
        help="Maximum concurrent downloads"
    )
    parser.add_argument(
        "--polite-delay",
        type=float,
        default=0.25,
        help="Delay (seconds) between downloads to respect source limits"
    )
    parser.add_argument(
        "--max-requests-per-minute",
        type=int,
        default=120,
        help="Max HTTP requests per minute"
    )
    parser.add_argument(
        "--max-bulk-docs",
        type=int,
        default=100000,
        help="Maximum documents per bulk download request"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("uvicorn").setLevel(logging.DEBUG)
    
    # Configure server
    config = ServerConfig(
        host=args.host,
        port=args.port,
        download_dir=args.download_dir,
        max_concurrent_downloads=args.max_concurrent,
        polite_delay_seconds=args.polite_delay,
        max_requests_per_minute=args.max_requests_per_minute,
        max_bulk_documents=args.max_bulk_docs,
    )
    
    # Create and run server
    server = EpsteinFilesDownloader(config)
    
    # Handle graceful shutdown
    def handle_shutdown(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(server.shutdown())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Run server
    server.run()


if __name__ == "__main__":
    main()
