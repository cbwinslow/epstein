#!/usr/bin/env python3
"""
Enhanced Download Manager for Epstein Files
Supports multiple sources, authentication, resumable downloads, and progress tracking.

Author: Epstein Project Team
Date: 2026-02-13
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from enum import Enum

import requests

try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm not available
    class tqdm:
        def __init__(self, *args, **kwargs):
            self.total = kwargs.get('total', 0)
            self.n = kwargs.get('initial', 0)
        def update(self, n):
            self.n += n
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

logger = logging.getLogger(__name__)


class DownloadStatus(Enum):
    """Status of a download operation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class DownloadSource(Enum):
    """Supported download sources"""
    DOJ_DISCLOSURES = "doj_disclosures"
    FBI_VAULT = "fbi_vault"
    HOUSE_OVERSIGHT = "house_oversight"
    GOVINFO = "govinfo"
    CUSTOM = "custom"


@dataclass
class DownloadMetrics:
    """Metrics for a download operation"""
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    bytes_downloaded: int = 0
    total_bytes: Optional[int] = None
    download_speed: float = 0.0  # bytes per second
    retry_count: int = 0
    error_count: int = 0
    
    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds"""
        end = self.end_time or datetime.now(timezone.utc)
        return (end - self.start_time).total_seconds()
    
    @property
    def progress_percentage(self) -> float:
        """Calculate download progress percentage"""
        if not self.total_bytes:
            return 0.0
        return (self.bytes_downloaded / self.total_bytes) * 100
    
    def update_speed(self) -> None:
        """Update download speed based on current metrics"""
        duration = self.duration_seconds
        if duration > 0:
            self.download_speed = self.bytes_downloaded / duration


@dataclass
class DownloadTask:
    """Represents a single download task"""
    url: str
    destination: Path
    source: DownloadSource
    name: str
    status: DownloadStatus = DownloadStatus.PENDING
    metrics: DownloadMetrics = field(default_factory=DownloadMetrics)
    checksum: Optional[str] = None
    checksum_algorithm: str = "sha256"
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "url": self.url,
            "destination": str(self.destination),
            "source": self.source.value,
            "name": self.name,
            "status": self.status.value,
            "checksum": self.checksum,
            "checksum_algorithm": self.checksum_algorithm,
            "metadata": self.metadata,
            "metrics": {
                "bytes_downloaded": self.metrics.bytes_downloaded,
                "total_bytes": self.metrics.total_bytes,
                "progress_percentage": self.metrics.progress_percentage,
                "download_speed": self.metrics.download_speed,
                "retry_count": self.metrics.retry_count,
                "error_count": self.metrics.error_count,
            }
        }


@dataclass
class SessionConfig:
    """Configuration for HTTP sessions"""
    user_agent: str = "Epstein-Project-Downloader/2.0"
    timeout: int = 60
    max_retries: int = 8
    backoff_base: float = 1.75
    cookies: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None
    session_key: Optional[str] = None
    use_session_auth: bool = False


class DownloadManager:
    """
    Enhanced download manager with support for:
    - Multiple sources (DOJ, FBI, House, GovInfo)
    - Session/cookie authentication
    - Resumable downloads
    - Progress tracking and monitoring
    - Concurrent downloads
    - Automatic retries with exponential backoff
    - Checksum verification
    - Detailed metrics and logging
    """
    
    def __init__(
        self,
        output_dir: Path,
        max_concurrent: int = 3,
        chunk_size: int = 8 * 1024 * 1024,
        session_config: Optional[SessionConfig] = None,
        progress_callback: Optional[Callable[[DownloadTask], None]] = None
    ):
        """
        Initialize download manager
        
        Args:
            output_dir: Base directory for downloads
            max_concurrent: Maximum concurrent downloads
            chunk_size: Chunk size for streaming downloads
            session_config: Session configuration for authentication
            progress_callback: Callback function for progress updates
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_concurrent = max_concurrent
        self.chunk_size = chunk_size
        self.session_config = session_config or SessionConfig()
        self.progress_callback = progress_callback
        
        # Task tracking
        self.tasks: Dict[str, DownloadTask] = {}
        self.active_tasks: List[str] = []
        
        # Session management
        self._session: Optional[requests.Session] = None
        
        # Manifest file for tracking
        self.manifest_file = self.output_dir / "download_manifest.jsonl"
        
        logger.info(f"Download manager initialized: output_dir={output_dir}, max_concurrent={max_concurrent}")
    
    def _get_session(self) -> requests.Session:
        """Get or create HTTP session with authentication"""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({"User-Agent": self.session_config.user_agent})
            
            # Add custom headers if provided
            if self.session_config.headers:
                self._session.headers.update(self.session_config.headers)
            
            # Add cookies if provided
            if self.session_config.cookies:
                for key, value in self.session_config.cookies.items():
                    self._session.cookies.set(key, value)
            
            # Add session key authentication if provided
            if self.session_config.session_key:
                self._session.headers.update({
                    "Authorization": f"Bearer {self.session_config.session_key}"
                })
            
            logger.info("HTTP session created with authentication")
        
        return self._session
    
    def add_task(self, task: DownloadTask) -> str:
        """
        Add a download task
        
        Args:
            task: Download task to add
            
        Returns:
            Task ID
        """
        task_id = hashlib.md5(f"{task.url}{task.destination}".encode()).hexdigest()
        self.tasks[task_id] = task
        logger.info(f"Added task {task_id}: {task.name}")
        return task_id
    
    def add_batch_tasks(self, tasks: List[DownloadTask]) -> List[str]:
        """Add multiple tasks"""
        return [self.add_task(task) for task in tasks]
    
    def get_task_status(self, task_id: str) -> Optional[DownloadStatus]:
        """Get status of a task"""
        task = self.tasks.get(task_id)
        return task.status if task else None
    
    def get_all_tasks(self) -> Dict[str, DownloadTask]:
        """Get all tasks"""
        return self.tasks.copy()
    
    def download_file(
        self,
        task_id: str,
        verify_checksum: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Download a single file
        
        Args:
            task_id: ID of the task to download
            verify_checksum: Whether to verify checksum after download
            
        Returns:
            Tuple of (success, error_message)
        """
        task = self.tasks.get(task_id)
        if not task:
            return False, f"Task {task_id} not found"
        
        task.status = DownloadStatus.IN_PROGRESS
        task.metrics.start_time = datetime.now(timezone.utc)
        
        session = self._get_session()
        
        try:
            # Check if file already exists and is complete
            existing_size = task.destination.stat().st_size if task.destination.exists() else 0
            
            # Get remote file size
            head_response = session.head(
                task.url, 
                timeout=self.session_config.timeout,
                allow_redirects=True
            )
            
            remote_size = None
            if "Content-Length" in head_response.headers:
                remote_size = int(head_response.headers["Content-Length"])
                task.metrics.total_bytes = remote_size
            
            # Check if already downloaded
            if existing_size > 0 and remote_size and existing_size == remote_size:
                logger.info(f"File already downloaded: {task.name}")
                task.status = DownloadStatus.COMPLETED
                task.metrics.bytes_downloaded = existing_size
                task.metrics.end_time = datetime.now(timezone.utc)
                self._save_to_manifest(task)
                return True, None
            
            # Prepare for resumable download
            headers = {}
            mode = "wb"
            
            if existing_size > 0:
                headers["Range"] = f"bytes={existing_size}-"
                mode = "ab"
                logger.info(f"Resuming download at byte {existing_size}: {task.name}")
            
            # Create destination directory
            task.destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Download with streaming and progress
            response = session.get(
                task.url,
                headers=headers,
                stream=True,
                timeout=self.session_config.timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # Handle server not supporting resume
            if existing_size > 0 and response.status_code == 200:
                logger.warning(f"Server does not support resume, restarting download: {task.name}")
                mode = "wb"
                existing_size = 0
            
            # Download with progress tracking
            task.metrics.bytes_downloaded = existing_size
            
            with open(task.destination, mode) as f:
                with tqdm(
                    total=task.metrics.total_bytes,
                    initial=existing_size,
                    unit="B",
                    unit_scale=True,
                    desc=task.name
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            f.write(chunk)
                            task.metrics.bytes_downloaded += len(chunk)
                            pbar.update(len(chunk))
                            
                            # Update metrics and callback
                            task.metrics.update_speed()
                            if self.progress_callback:
                                self.progress_callback(task)
            
            # Verify checksum if provided
            if verify_checksum and task.checksum:
                calculated_checksum = self._calculate_checksum(
                    task.destination,
                    task.checksum_algorithm
                )
                
                if calculated_checksum != task.checksum:
                    error = f"Checksum mismatch: expected {task.checksum}, got {calculated_checksum}"
                    logger.error(error)
                    task.status = DownloadStatus.FAILED
                    task.metrics.end_time = datetime.now(timezone.utc)
                    return False, error
            
            # Calculate checksum if not provided
            if not task.checksum:
                task.checksum = self._calculate_checksum(
                    task.destination,
                    task.checksum_algorithm
                )
            
            # Mark as completed
            task.status = DownloadStatus.COMPLETED
            task.metrics.end_time = datetime.now(timezone.utc)
            task.metrics.update_speed()
            
            logger.info(
                f"Download completed: {task.name} "
                f"({task.metrics.bytes_downloaded} bytes in {task.metrics.duration_seconds:.1f}s, "
                f"{task.metrics.download_speed / 1024 / 1024:.2f} MB/s)"
            )
            
            # Save to manifest
            self._save_to_manifest(task)
            
            return True, None
            
        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            logger.error(f"{error_msg} for task {task.name}")
            task.status = DownloadStatus.FAILED
            task.metrics.error_count += 1
            task.metrics.end_time = datetime.now(timezone.utc)
            return False, error_msg
    
    def download_with_retry(
        self,
        task_id: str,
        max_retries: Optional[int] = None,
        verify_checksum: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Download file with automatic retries
        
        Args:
            task_id: ID of task to download
            max_retries: Maximum number of retries (uses session config if None)
            verify_checksum: Whether to verify checksum
            
        Returns:
            Tuple of (success, error_message)
        """
        max_retries = max_retries or self.session_config.max_retries
        task = self.tasks.get(task_id)
        
        if not task:
            return False, f"Task {task_id} not found"
        
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            task.metrics.retry_count = attempt - 1
            
            success, error = self.download_file(task_id, verify_checksum)
            
            if success:
                return True, None
            
            last_error = error
            
            if attempt < max_retries:
                backoff = self.session_config.backoff_base ** min(attempt, 6)
                logger.warning(
                    f"Download attempt {attempt}/{max_retries} failed for {task.name}. "
                    f"Retrying in {backoff:.1f}s..."
                )
                time.sleep(backoff)
        
        return False, last_error
    
    def download_batch(
        self,
        task_ids: List[str],
        verify_checksums: bool = True
    ) -> Dict[str, Tuple[bool, Optional[str]]]:
        """
        Download multiple files concurrently
        
        Args:
            task_ids: List of task IDs to download
            verify_checksums: Whether to verify checksums
            
        Returns:
            Dictionary mapping task IDs to (success, error_message) tuples
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            futures = {
                executor.submit(self.download_with_retry, tid, None, verify_checksums): tid
                for tid in task_ids
            }
            
            for future in as_completed(futures):
                task_id = futures[future]
                try:
                    success, error = future.result()
                    results[task_id] = (success, error)
                except Exception as e:
                    logger.error(f"Exception downloading task {task_id}: {e}")
                    results[task_id] = (False, str(e))
        
        return results
    
    def _calculate_checksum(self, file_path: Path, algorithm: str = "sha256") -> str:
        """Calculate file checksum"""
        hasher = hashlib.new(algorithm)
        
        with open(file_path, "rb") as f:
            while chunk := f.read(self.chunk_size):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def _save_to_manifest(self, task: DownloadTask) -> None:
        """Save task to manifest file"""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task": task.to_dict()
        }
        
        with open(self.manifest_file, "a") as f:
            f.write(json.dumps(record) + "\n")
    
    def load_manifest(self) -> List[Dict]:
        """Load download manifest"""
        if not self.manifest_file.exists():
            return []
        
        records = []
        with open(self.manifest_file, "r") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        
        return records
    
    def get_statistics(self) -> Dict:
        """Get download statistics"""
        total_tasks = len(self.tasks)
        completed = sum(1 for t in self.tasks.values() if t.status == DownloadStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.status == DownloadStatus.FAILED)
        in_progress = sum(1 for t in self.tasks.values() if t.status == DownloadStatus.IN_PROGRESS)
        
        total_bytes = sum(t.metrics.bytes_downloaded for t in self.tasks.values())
        total_duration = sum(t.metrics.duration_seconds for t in self.tasks.values())
        
        avg_speed = total_bytes / total_duration if total_duration > 0 else 0
        
        return {
            "total_tasks": total_tasks,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": total_tasks - completed - failed - in_progress,
            "success_rate": (completed / total_tasks * 100) if total_tasks > 0 else 0,
            "total_bytes_downloaded": total_bytes,
            "average_speed_mbps": avg_speed / 1024 / 1024,
            "total_duration_seconds": total_duration,
        }
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        if self._session:
            self._session.close()
            self._session = None
        logger.info("Download manager cleanup completed")
