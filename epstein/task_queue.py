"""
Task Queue System with Deduplication and Persistence

This module provides a robust task queue system with:
- SQLite-backed persistent storage
- Deduplication using content hashing
- Task state management (pending, running, completed, failed, paused, cancelled)
- Multi-worker support with threading
- Pause/Resume/Cancel controls

Usage:
    from epstein.task_queue import TaskQueue, DeduplicationManager

    # Create queue and deduplication manager
    queue = TaskQueue("./data/tasks.db")
    dedup = DeduplicationManager("./data/tasks.db")

    # Add a task (automatically deduplicates)
    queue.add_task("task-1", "Process PDF", "process", {"file": "doc.pdf"})

    # Check if already processed
    file_hash = dedup.compute_hash(file_path="doc.pdf")
    if not dedup.is_processed(file_hash, "ocr"):
        # Process file...
        dedup.mark_processed(file_hash, "ocr", "output.pdf")

Author: Epstein Project Team
Version: 1.0.0
"""

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from contextlib import contextmanager
from uuid import uuid4


# Get logger for this module
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """
    Enumeration of possible task statuses.

    Attributes:
        PENDING: Task is queued but not yet started
        RUNNING: Task is currently being processed
        COMPLETED: Task finished successfully
        FAILED: Task encountered an error
        CANCELLED: Task was manually cancelled
        PAUSED: Task was paused (can be resumed)
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskPriority(Enum):
    """
    Enumeration of task priority levels.

    Attributes:
        LOW: Lowest priority, processed last
        NORMAL: Default priority
        HIGH: Higher priority
        CRITICAL: Highest priority, processed first
    """

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """
    Represents a single task in the task queue.

    Attributes:
        task_id: Unique identifier for the task
        name: Human-readable task name
        command: Command/type of task to execute
        args: Arguments for the task
        status: Current task status
        priority: Task priority (affects processing order)
        progress: Progress percentage (0-100)
        result: Result data from task execution
        error: Error message if task failed
        created_at: ISO timestamp when task was created
        started_at: ISO timestamp when task started processing
        completed_at: ISO timestamp when task finished
        worker_id: ID of worker processing this task
        retry_count: Number of retry attempts
        max_retries: Maximum number of retry attempts allowed
    """

    task_id: str
    name: str
    command: str
    args: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    worker_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class ProcessedItem:
    """
    Tracks processed items to prevent duplicate processing.

    Attributes:
        item_hash: SHA256 hash of the processed item
        item_type: Type of processing (e.g., "download", "ocr", "embedding")
        status: Processing status
        output_path: Path to the output file (if applicable)
        processed_at: ISO timestamp when processing completed
        metadata: Additional metadata about the processing
    """

    item_hash: str
    item_type: str
    status: str
    output_path: Optional[str] = None
    processed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskQueueError(Exception):
    """Base exception for task queue errors."""

    pass


class DatabaseError(TaskQueueError):
    """Exception raised for database-related errors."""

    pass


class TaskNotFoundError(TaskQueueError):
    """Exception raised when a task is not found."""

    pass


class TaskQueue:
    """
    Persistent task queue with SQLite backend.

    This class provides thread-safe task queue operations with:
    - SQLite persistence for durability
    - Automatic deduplication support
    - Task state tracking and progress monitoring
    - Multi-worker support

    Attributes:
        db_path: Path to SQLite database file

    Example:
        >>> queue = TaskQueue("./data/tasks.db")
        >>> task_id = queue.add_task(
        ...     task_id="task-1",
        ...     name="Download PDF",
        ...     command="download",
        ...     args={"url": "https://example.com/file.pdf"}
        ... )
        >>> print(f"Added task: {task_id}")
    """

    # SQL statements for database operations
    SQL_CREATE_TASKS_TABLE = """
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            command TEXT NOT NULL,
            args TEXT,
            status TEXT NOT NULL,
            priority INTEGER NOT NULL,
            progress REAL DEFAULT 0,
            result TEXT,
            error TEXT,
            created_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            worker_id TEXT,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3
        )
    """

    SQL_CREATE_PROCESSED_TABLE = """
        CREATE TABLE IF NOT EXISTS processed_items (
            item_hash TEXT PRIMARY KEY,
            item_type TEXT NOT NULL,
            status TEXT NOT NULL,
            output_path TEXT,
            processed_at TEXT NOT NULL,
            metadata TEXT
        )
    """

    def __init__(self, db_path: str = "./data/task_queue.db") -> None:
        """
        Initialize the task queue.

        Args:
            db_path: Path to SQLite database file. Directory will be created if needed.

        Raises:
            DatabaseError: If database initialization fails
        """
        self.db_path = db_path
        self._ensure_db_directory()
        try:
            self._init_database()
            self._lock = threading.Lock()
            logger.info(f"TaskQueue initialized at {db_path}")
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to initialize database: {e}")

    def _ensure_db_directory(self) -> None:
        """
        Ensure the database directory exists.
        Creates the directory and parent directories if they don't exist.
        """
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _get_connection(self):
        """
        Get a SQLite connection with automatic commit/rollback.

        Yields:
            sqlite3.Connection: Database connection with row factory set

        Raises:
            DatabaseError: If database operation fails
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            conn.close()

    def _init_database(self) -> None:
        """
        Initialize database schema.

        Creates tasks and processed_items tables if they don't exist.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(self.SQL_CREATE_TASKS_TABLE)
            cursor.execute(self.SQL_CREATE_PROCESSED_TABLE)
            # Execute each index separately
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority DESC)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_processed_type ON processed_items(item_type)"
            )

    def add_task(
        self,
        task_id: str,
        name: str,
        command: str,
        args: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
    ) -> Task:
        """
        Add a new task to the queue.

        Args:
            task_id: Unique identifier for the task
            name: Human-readable task name
            command: Command/type of task to execute
            args: Dictionary of arguments for the task
            priority: Task priority level
            max_retries: Maximum number of retry attempts on failure

        Returns:
            Task: The created task object

        Example:
            >>> task = queue.add_task(
            ...     task_id="download-001",
            ...     name="Download FBI file",
            ...     command="download",
            ...     args={"url": "https://..."},
            ...     priority=TaskPriority.HIGH
            ... )
        """
        with self._lock:
            task = Task(
                task_id=task_id,
                name=name,
                command=command,
                args=args or {},
                priority=priority,
                max_retries=max_retries,
            )

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO tasks 
                    (task_id, name, command, args, status, priority, progress, 
                     created_at, max_retries)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.task_id,
                        task.name,
                        task.command,
                        json.dumps(task.args),
                        task.status.value,
                        task.priority.value,
                        task.progress,
                        task.created_at,
                        task.max_retries,
                    ),
                )

            logger.info(f"Added task {task_id}: {name} (command: {command})")
            return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Retrieve a task by its ID.

        Args:
            task_id: The unique identifier of the task

        Returns:
            Task if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_task(row)
            return None

    def get_next_task(self, worker_id: str) -> Optional[Task]:
        """
        Get the next pending task for processing.

        Tasks are ordered by priority (highest first) then by creation time.

        Args:
            worker_id: ID of the worker requesting a task

        Returns:
            Task if one is available, None otherwise
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM tasks 
                    WHERE status = ? 
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                    """,
                    (TaskStatus.PENDING.value,),
                )
                row = cursor.fetchone()

                if row:
                    task = self._row_to_task(row)
                    # Mark as running
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now(timezone.utc).isoformat()
                    task.worker_id = worker_id
                    self._update_task(task)
                    return task
            return None

    def update_progress(self, task_id: str, progress: float) -> None:
        """
        Update the progress of a task.

        Args:
            task_id: The task ID
            progress: Progress percentage (0-100)
        """
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE tasks SET progress = ? WHERE task_id = ?",
                (min(100.0, max(0.0, progress)), task_id),
            )

    def complete_task(
        self,
        task_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Mark a task as completed.

        Args:
            task_id: The task ID
            result: Optional result data to store
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE tasks 
                SET status = ?, progress = 100, result = ?, completed_at = ?
                WHERE task_id = ?
                """,
                (
                    TaskStatus.COMPLETED.value,
                    json.dumps(result) if result else None,
                    datetime.now(timezone.utc).isoformat(),
                    task_id,
                ),
            )
        logger.info(f"Task {task_id} completed successfully")

    def fail_task(self, task_id: str, error: str, retry: bool = True) -> None:
        """
        Mark a task as failed, optionally retrying.

        Args:
            task_id: The task ID
            error: Error message describing the failure
            retry: If True and retries remain, task will be requeued
        """
        task = self.get_task(task_id)
        if not task:
            return

        if retry and task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.PENDING
            task.error = None
            self._update_task(task)
            logger.info(
                f"Task {task_id} will retry (attempt {task.retry_count}/{task.max_retries})"
            )
        else:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    UPDATE tasks 
                    SET status = ?, error = ?, completed_at = ?
                    WHERE task_id = ?
                    """,
                    (
                        TaskStatus.FAILED.value,
                        error,
                        datetime.now(timezone.utc).isoformat(),
                        task_id,
                    ),
                )
            logger.error(f"Task {task_id} failed: {error}")

    def cancel_task(self, task_id: str) -> None:
        """
        Cancel a pending or running task.

        Args:
            task_id: The task ID to cancel
        """
        task = self.get_task(task_id)
        if task and task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now(timezone.utc).isoformat()
            self._update_task(task)
            logger.info(f"Task {task_id} cancelled")

    def pause_task(self, task_id: str) -> None:
        """
        Pause a running task.

        Args:
            task_id: The task ID to pause
        """
        task = self.get_task(task_id)
        if task and task.status == TaskStatus.RUNNING:
            task.status = TaskStatus.PAUSED
            self._update_task(task)
            logger.info(f"Task {task_id} paused")

    def resume_task(self, task_id: str) -> None:
        """
        Resume a paused task.

        Args:
            task_id: The task ID to resume
        """
        task = self.get_task(task_id)
        if task and task.status == TaskStatus.PAUSED:
            task.status = TaskStatus.PENDING
            self._update_task(task)
            logger.info(f"Task {task_id} resumed")

    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get the current status of the task queue.

        Returns:
            Dictionary containing:
            - status_counts: Count of tasks by status
            - total: Total number of tasks
            - recent_tasks: List of recently created tasks
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Count by status
            cursor.execute("SELECT status, COUNT(*) as count FROM tasks GROUP BY status")
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # Get recent tasks
            cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 10")
            recent = [self._row_to_task(row) for row in cursor.fetchall()]

            return {
                "status_counts": status_counts,
                "total": sum(status_counts.values()),
                "recent_tasks": [self._task_to_dict(t) for t in recent],
            }

    def _update_task(self, task: Task) -> None:
        """Update task in database."""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE tasks SET
                    status = ?,
                    progress = ?,
                    result = ?,
                    error = ?,
                    started_at = ?,
                    completed_at = ?,
                    worker_id = ?,
                    retry_count = ?
                WHERE task_id = ?
                """,
                (
                    task.status.value,
                    task.progress,
                    json.dumps(task.result) if task.result else None,
                    task.error,
                    task.started_at,
                    task.completed_at,
                    task.worker_id,
                    task.retry_count,
                    task.task_id,
                ),
            )

    def _row_to_task(self, row) -> Task:
        """Convert database row to Task object."""
        return Task(
            task_id=row["task_id"],
            name=row["name"],
            command=row["command"],
            args=json.loads(row["args"]) if row["args"] else {},
            status=TaskStatus(row["status"]),
            priority=TaskPriority(row["priority"]),
            progress=row["progress"],
            result=json.loads(row["result"]) if row["result"] else None,
            error=row["error"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            worker_id=row["worker_id"],
            retry_count=row["retry_count"],
            max_retries=row["max_retries"],
        )

    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Convert Task object to dictionary."""
        return {
            "task_id": task.task_id,
            "name": task.name,
            "command": task.command,
            "status": task.status.value,
            "priority": task.priority.value,
            "progress": task.progress,
            "created_at": task.created_at,
        }


class DeduplicationManager:
    """
    Manages deduplication of downloads and processing tasks.

    Uses content hashing (SHA256) to avoid re-downloading or re-processing
    files that have already been handled.

    Attributes:
        db_path: Path to SQLite database file

    Example:
        >>> dedup = DeduplicationManager("./data/tasks.db")
        >>> file_hash = dedup.compute_hash(file_path="document.pdf")
        >>> if not dedup.is_processed(file_hash, "ocr"):
        ...     # Process the file...
        ...     dedup.mark_processed(file_hash, "ocr", "output.pdf")
    """

    def __init__(self, db_path: str = "./data/task_queue.db") -> None:
        """
        Initialize the deduplication manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
        logger.info(f"DeduplicationManager initialized at {db_path}")

    def _ensure_db_directory(self) -> None:
        """Ensure database directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _init_database(self) -> None:
        """Initialize processed items table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_items (
                item_hash TEXT PRIMARY KEY,
                item_type TEXT NOT NULL,
                status TEXT NOT NULL,
                output_path TEXT,
                processed_at TEXT NOT NULL,
                metadata TEXT
            )
        """
        )
        conn.commit()
        conn.close()

    @staticmethod
    def compute_hash(
        content: Optional[str] = None,
        url: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> str:
        """
        Compute SHA256 hash for deduplication.

        Args:
            content: Text content to hash
            url: URL string to hash
            file_path: Path to file to hash

        Returns:
            str: SHA256 hex digest of the input

        Raises:
            ValueError: If no valid input is provided

        Example:
            >>> hash1 = DeduplicationManager.compute_hash(content="Hello World")
            >>> hash2 = DeduplicationManager.compute_hash(url="https://example.com")
            >>> hash3 = DeduplicationManager.compute_hash(file_path="document.pdf")
        """
        if content is not None:
            return hashlib.sha256(content.encode()).hexdigest()
        elif url is not None:
            return hashlib.sha256(url.encode()).hexdigest()
        elif file_path is not None:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        raise ValueError("Must provide content, url, or file_path")

    def is_processed(
        self,
        item_hash: str,
        item_type: str,
    ) -> bool:
        """
        Check if an item has already been processed.

        Args:
            item_hash: SHA256 hash of the item
            item_type: Type of processing (e.g., "download", "ocr")

        Returns:
            bool: True if item was processed successfully

        Example:
            >>> if not dedup.is_processed(file_hash, "ocr"):
            ...     # Process the file
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT status FROM processed_items 
            WHERE item_hash = ? AND item_type = ?
            """,
            (item_hash, item_type),
        )

        row = cursor.fetchone()
        conn.close()

        return row is not None and row[0] == "completed"

    def mark_processed(
        self,
        item_hash: str,
        item_type: str,
        output_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Mark an item as processed.

        Args:
            item_hash: SHA256 hash of the processed item
            item_type: Type of processing performed
            output_path: Path to output file (if applicable)
            metadata: Additional metadata about the processing

        Example:
            >>> dedup.mark_processed(
            ...     file_hash,
            ...     "ocr",
            ...     output_path="output.pdf",
            ...     metadata={"pages": 10, "language": "en"}
            ... )
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO processed_items
            (item_hash, item_type, status, output_path, processed_at, metadata)
            VALUES (?, ?, 'completed', ?, ?, ?)
            """,
            (
                item_hash,
                item_type,
                output_path,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(metadata) if metadata else None,
            ),
        )

        conn.commit()
        conn.close()
        logger.info(f"Marked {item_type} {item_hash[:16]}... as processed")

    def get_processed_items(
        self,
        item_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[ProcessedItem]:
        """
        Get list of processed items.

        Args:
            item_type: Filter by item type (optional)
            limit: Maximum number of items to return

        Returns:
            List of ProcessedItem objects
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if item_type:
            cursor.execute(
                """
                SELECT * FROM processed_items 
                WHERE item_type = ?
                ORDER BY processed_at DESC
                LIMIT ?
                """,
                (item_type, limit),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM processed_items 
                ORDER BY processed_at DESC
                LIMIT ?
                """,
                (limit,),
            )

        rows = cursor.fetchall()
        conn.close()

        items = []
        for row in rows:
            items.append(
                ProcessedItem(
                    item_hash=row["item_hash"],
                    item_type=row["item_type"],
                    status=row["status"],
                    output_path=row["output_path"],
                    processed_at=row["processed_at"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
            )

        return items

    def clear_processed(
        self,
        item_type: Optional[str] = None,
        before_date: Optional[str] = None,
    ) -> int:
        """
        Clear processed items (for testing or reset).

        Args:
            item_type: Only clear items of this type (optional)
            before_date: Only clear items processed before this date (optional)

        Returns:
            Number of items cleared
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if item_type and before_date:
            cursor.execute(
                """
                DELETE FROM processed_items 
                WHERE item_type = ? AND processed_at < ?
                """,
                (item_type, before_date),
            )
        elif item_type:
            cursor.execute("DELETE FROM processed_items WHERE item_type = ?", (item_type,))
        elif before_date:
            cursor.execute("DELETE FROM processed_items WHERE processed_at < ?", (before_date,))
        else:
            cursor.execute("DELETE FROM processed_items")

        count = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"Cleared {count} processed items")
        return count


class TaskWorker:
    """
    Worker that processes tasks from the queue.

    Provides background task processing with support for
    pausing, resuming, and graceful shutdown.

    Attributes:
        worker_id: Unique identifier for this worker
        task_queue: The TaskQueue to process tasks from
        deduplication: DeduplicationManager instance
        handlers: Dictionary mapping commands to handler functions

    Example:
        >>> def handle_download(args):
        ...     # Download logic here
        ...     return {"status": "success", "file": args["url"]}
        ...
        >>> worker = TaskWorker(
        ...     worker_id="worker-1",
        ...     task_queue=queue,
        ...     deduplication=dedup,
        ...     handlers={"download": handle_download}
        ... )
        >>> worker.start()
        >>> # Worker processes tasks in background
        >>> worker.stop()
    """

    def __init__(
        self,
        worker_id: str,
        task_queue: TaskQueue,
        deduplication: DeduplicationManager,
        handlers: Dict[str, Callable],
    ) -> None:
        """
        Initialize the task worker.

        Args:
            worker_id: Unique identifier for this worker
            task_queue: TaskQueue to process tasks from
            deduplication: DeduplicationManager for skip duplicate processing
            handlers: Dictionary mapping command names to handler functions
        """
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.dedup = deduplication
        self.handlers = handlers
        self._running = False
        self._paused = False
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the worker in a background thread."""
        self._running = True
        self._stop_event.clear()
        thread = threading.Thread(target=self._process_loop, daemon=True)
        thread.start()
        logger.info(f"Worker {self.worker_id} started")

    def stop(self) -> None:
        """
        Stop the worker gracefully.

        Waits for current task to complete before stopping.
        """
        self._running = False
        self._stop_event.set()
        logger.info(f"Worker {self.worker_id} stopping...")

    def pause(self) -> None:
        """Pause the worker (stops picking up new tasks)."""
        self._paused = True
        logger.info(f"Worker {self.worker_id} paused")

    def resume(self) -> None:
        """Resume the worker (continues picking up new tasks)."""
        self._paused = False
        logger.info(f"Worker {self.worker_id} resumed")

    def _process_loop(self) -> None:
        """Main processing loop - runs in background thread."""
        while self._running and not self._stop_event.is_set():
            if self._paused:
                time.sleep(1)
                continue

            task = self.task_queue.get_next_task(self.worker_id)

            if task:
                self._process_task(task)
            else:
                # No tasks, wait a bit
                time.sleep(2)

    def _process_task(self, task: Task) -> None:
        """
        Process a single task.

        Args:
            task: Task to process
        """
        logger.info(f"Processing task {task.task_id}: {task.name}")

        try:
            handler = self.handlers.get(task.command)

            if handler:
                result = handler(task.args)
                self.task_queue.complete_task(task.task_id, result)
            else:
                self.task_queue.fail_task(task.task_id, f"Unknown command: {task.command}")

        except Exception as e:
            logger.exception(f"Error processing task {task.task_id}")
            self.task_queue.fail_task(task.task_id, str(e))


# Convenience factory functions
def create_task_queue(db_path: str = "./data/task_queue.db") -> TaskQueue:
    """
    Create a TaskQueue instance.

    Args:
        db_path: Path to SQLite database

    Returns:
        TaskQueue: Configured task queue instance
    """
    return TaskQueue(db_path)


def create_dedup_manager(db_path: str = "./data/task_queue.db") -> DeduplicationManager:
    """
    Create a DeduplicationManager instance.

    Args:
        db_path: Path to SQLite database

    Returns:
        DeduplicationManager: Configured deduplication manager
    """
    return DeduplicationManager(db_path)
