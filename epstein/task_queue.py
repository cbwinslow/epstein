"""
Task Queue System with Deduplication and Persistence
Provides queue management, task state tracking, and idempotent operations.
"""

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from contextlib import contextmanager

logger = logging.getLogger("task_queue")


class TaskStatus(Enum):
    """Task status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskPriority(Enum):
    """Task priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """Represents a task in the queue."""

    task_id: str
    name: str
    command: str
    args: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    worker_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class ProcessedItem:
    """Tracks processed items for deduplication."""

    item_hash: str
    item_type: str  # "download", "ocr", "embedding", "entity_extraction"
    status: str
    output_path: Optional[str] = None
    processed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskQueue:
    """
    Persistent task queue with SQLite backend.
    Supports deduplication, pausing, resuming, and monitoring.
    """

    def __init__(self, db_path: str = "./data/task_queue.db"):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
        self._lock = threading.Lock()

    def _ensure_db_directory(self):
        """Ensure database directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _get_connection(self):
        """Get SQLite connection with context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Tasks table
            cursor.execute("""
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
            """)

            # Processed items table (for deduplication)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_items (
                    item_hash TEXT PRIMARY KEY,
                    item_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    output_path TEXT,
                    processed_at TEXT NOT NULL,
                    metadata TEXT
                )
            """)

            # Indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed_type ON processed_items(item_type)
            """)

            logger.info(f"Initialized task queue database at {self.db_path}")

    def add_task(
        self,
        task_id: str,
        name: str,
        command: str,
        args: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
    ) -> Task:
        """Add a task to the queue."""
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

            logger.info(f"Added task {task_id}: {name}")
            return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_task(row)
            return None

    def get_next_task(self, worker_id: str) -> Optional[Task]:
        """Get the next pending task (highest priority first)."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM tasks 
                    WHERE status = 'pending' 
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                """)
                row = cursor.fetchone()

                if row:
                    task = self._row_to_task(row)
                    # Mark as running
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.utcnow().isoformat()
                    task.worker_id = worker_id
                    self._update_task(task)
                    return task
            return None

    def update_progress(self, task_id: str, progress: float):
        """Update task progress."""
        with self._get_connection() as conn:
            conn.execute("UPDATE tasks SET progress = ? WHERE task_id = ?", (progress, task_id))

    def complete_task(
        self,
        task_id: str,
        result: Optional[Dict[str, Any]] = None,
    ):
        """Mark task as completed."""
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
                    datetime.utcnow().isoformat(),
                    task_id,
                ),
            )
        logger.info(f"Task {task_id} completed")

    def fail_task(self, task_id: str, error: str, retry: bool = True):
        """Mark task as failed, optionally retry."""
        task = self.get_task(task_id)
        if not task:
            return

        if retry and task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.PENDING
            task.error = None
            self._update_task(task)
            logger.info(f"Task {task_id} will retry (attempt {task.retry_count})")
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
                        datetime.utcnow().isoformat(),
                        task_id,
                    ),
                )
            logger.error(f"Task {task_id} failed: {error}")

    def cancel_task(self, task_id: str):
        """Cancel a task."""
        task = self.get_task(task_id)
        if task and task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.utcnow().isoformat()
            self._update_task(task)
            logger.info(f"Task {task_id} cancelled")

    def pause_task(self, task_id: str):
        """Pause a running task."""
        task = self.get_task(task_id)
        if task and task.status == TaskStatus.RUNNING:
            task.status = TaskStatus.PAUSED
            self._update_task(task)
            logger.info(f"Task {task_id} paused")

    def resume_task(self, task_id: str):
        """Resume a paused task."""
        task = self.get_task(task_id)
        if task and task.status == TaskStatus.PAUSED:
            task.status = TaskStatus.PENDING
            self._update_task(task)
            logger.info(f"Task {task_id} resumed")

    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Count by status
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM tasks 
                GROUP BY status
            """)
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # Get recent tasks
            cursor.execute("""
                SELECT * FROM tasks 
                ORDER BY created_at DESC 
                LIMIT 10
            """)
            recent = [self._row_to_task(row) for row in cursor.fetchall()]

            return {
                "status_counts": status_counts,
                "total": sum(status_counts.values()),
                "recent_tasks": [asdict(t) for t in recent],
            }

    def _update_task(self, task: Task):
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
        """Convert database row to Task."""
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


class DeduplicationManager:
    """
    Manages deduplication of downloads and processing tasks.
    Uses content hashing to avoid re-downloading or re-processing.
    """

    def __init__(self, db_path: str = "./data/task_queue.db"):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()

    def _ensure_db_directory(self):
        """Ensure database directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _init_database(self):
        """Initialize processed items table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_items (
                item_hash TEXT PRIMARY KEY,
                item_type TEXT NOT NULL,
                status TEXT NOT NULL,
                output_path TEXT,
                processed_at TEXT NOT NULL,
                metadata TEXT
            )
        """)

        conn.close()

    def compute_hash(
        self,
        content: Optional[str] = None,
        url: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> str:
        """Compute hash for deduplication."""
        if content:
            return hashlib.sha256(content.encode()).hexdigest()
        elif url:
            return hashlib.sha256(url.encode()).hexdigest()
        elif file_path:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        raise ValueError("Must provide content, url, or file_path")

    def is_processed(
        self,
        item_hash: str,
        item_type: str,
    ) -> bool:
        """Check if item has been processed."""
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
    ):
        """Mark item as processed."""
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
                datetime.utcnow().isoformat(),
                json.dumps(metadata) if metadata else None,
            ),
        )

        conn.close()
        logger.info(f"Marked {item_type} {item_hash[:16]}... as processed")

    def get_processed_items(
        self,
        item_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[ProcessedItem]:
        """Get list of processed items."""
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
    ):
        """Clear processed items (for testing/reset)."""
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

        conn.commit()
        conn.close()
        logger.info(f"Cleared processed items")


class TaskWorker:
    """
    Worker that processes tasks from the queue.
    Supports pausing, resuming, and graceful shutdown.
    """

    def __init__(
        self,
        worker_id: str,
        task_queue: TaskQueue,
        deduplication: DeduplicationManager,
        handlers: Dict[str, Callable],
    ):
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.dedup = deduplication
        self.handlers = handlers
        self._running = False
        self._paused = False
        self._stop_event = threading.Event()

    def start(self):
        """Start the worker."""
        self._running = True
        self._stop_event.clear()
        thread = threading.Thread(target=self._process_loop, daemon=True)
        thread.start()
        logger.info(f"Worker {self.worker_id} started")

    def stop(self):
        """Stop the worker."""
        self._running = False
        self._stop_event.set()
        logger.info(f"Worker {self.worker_id} stopping...")

    def pause(self):
        """Pause the worker."""
        self._paused = True
        logger.info(f"Worker {self.worker_id} paused")

    def resume(self):
        """Resume the worker."""
        self._paused = False
        logger.info(f"Worker {self.worker_id} resumed")

    def _process_loop(self):
        """Main processing loop."""
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

    def _process_task(self, task: Task):
        """Process a single task."""
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


# Convenience functions
def create_task_queue(db_path: str = "./data/task_queue.db") -> TaskQueue:
    """Create a task queue instance."""
    return TaskQueue(db_path)


def create_dedup_manager(db_path: str = "./data/task_queue.db") -> DeduplicationManager:
    """Create a deduplication manager instance."""
    return DeduplicationManager(db_path)
