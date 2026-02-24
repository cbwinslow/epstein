#!/usr/bin/env python3
"""
Epstein Files Monitoring Dashboard

A comprehensive web-based dashboard for monitoring and managing the document
processing pipeline. Provides real-time visibility into:

- Task queue status and management
- Download progress tracking
- Worker/thread monitoring
- Error and message logging
- Batch operations

Usage:
    python dashboard.py
    # Then open http://localhost:8080 in your browser

Or run with uvicorn:
    uvicorn dashboard:app --reload --port 8080

Author: Epstein Project Team
Version: 1.0.0
"""

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dashboard")


# =============================================================================
# Data Models
# =============================================================================


class TaskStatus(str, Enum):
    """Task status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskPriority(int, Enum):
    """Task priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class BatchJob:
    """Represents a batch of tasks to be processed."""

    job_id: str
    name: str
    description: str
    tasks: list[dict[str, Any]]
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    progress: float = 0.0
    completed_tasks: int = 0
    failed_tasks: int = 0


@dataclass
class WorkerStatus:
    """Represents a worker thread status."""

    worker_id: str
    status: str  # idle, busy, paused
    current_task: str | None = None
    progress: float = 0.0
    started_at: str | None = None
    messages: list[str] = field(default_factory=list)


@dataclass
class LogEntry:
    """Represents a log entry."""

    timestamp: str
    level: str
    source: str
    message: str
    details: dict[str, Any] | None = None


# =============================================================================
# Dashboard State
# =============================================================================


class DashboardState:
    """
    Manages the in-memory state for the dashboard.

    This class maintains:
    - Batch jobs
    - Worker statuses
    - Log entries
    - Active downloads
    - System metrics
    """

    def __init__(self):
        self.batches: dict[str, BatchJob] = {}
        self.workers: dict[str, WorkerStatus] = {}
        self.logs: list[LogEntry] = []
        self.downloads: dict[str, dict[str, Any]] = {}
        self.metrics = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "active_workers": 0,
        }
        self._lock = threading.Lock()
        self._max_logs = 1000  # Keep last 1000 logs

        # Initialize default workers
        for i in range(5):
            self.workers[f"worker-{i}"] = WorkerStatus(worker_id=f"worker-{i}", status="idle")

    def add_log(self, level: str, source: str, message: str, details: dict | None = None):
        """Add a log entry."""
        with self._lock:
            entry = LogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                level=level,
                source=source,
                message=message,
                details=details,
            )
            self.logs.append(entry)

            # Trim logs if too many
            if len(self.logs) > self._max_logs:
                self.logs = self.logs[-self._max_logs :]

    def create_batch(self, name: str, description: str, tasks: list[dict[str, Any]]) -> str:
        """Create a new batch job."""
        job_id = str(uuid4())[:8]
        batch = BatchJob(
            job_id=job_id,
            name=name,
            description=description,
            tasks=tasks,
        )
        with self._lock:
            self.batches[job_id] = batch
            self.add_log("INFO", "batch", f"Created batch: {name} ({job_id})")
        return job_id

    def get_status(self) -> dict[str, Any]:
        """Get overall system status."""
        with self._lock:
            return {
                "batches": {
                    job_id: {
                        "name": b.name,
                        "status": b.status,
                        "progress": b.progress,
                        "completed": b.completed_tasks,
                        "failed": b.failed_tasks,
                        "total": len(b.tasks),
                    }
                    for job_id, b in self.batches.items()
                },
                "workers": {
                    w_id: {
                        "status": w.status,
                        "current_task": w.current_task,
                        "progress": w.progress,
                    }
                    for w_id, w in self.workers.items()
                },
                "metrics": self.metrics.copy(),
                "active_downloads": len(self.downloads),
            }

    def update_download(self, download_id: str, data: dict[str, Any]):
        """Update download progress."""
        with self._lock:
            if download_id not in self.downloads:
                self.downloads[download_id] = {}
            self.downloads[download_id].update(data)
            self.downloads[download_id]["updated_at"] = datetime.now(timezone.utc).isoformat()


# Create global state
state = DashboardState()


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="Epstein Files Dashboard",
    description="Monitoring and management dashboard for document processing pipeline",
    version="1.0.0",
)

# Simple HTML dashboard (embedded for simplicity)
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Epstein Files - Pipeline Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        [x-cloak] { display: none !important; }
        .log-entry { font-family: 'Monaco', 'Menlo', monospace; font-size: 12px; }
        .progress-bar { transition: width 0.3s ease; }
        .pulse { animation: pulse 2s infinite; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
    </style>
</head>
<body class="bg-gray-900 text-gray-100" x-data="dashboard()" x-init="init()">

    <!-- Header -->
    <header class="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div class="flex items-center justify-between">
            <div class="flex items-center space-x-4">
                <h1 class="text-2xl font-bold text-white">
                    <i class="fas fa-layer-group text-blue-500"></i>
                    Epstein Files Pipeline
                </h1>
                <span class="px-3 py-1 text-sm rounded-full"
                      :class="status.workers['worker-0']?.status === 'busy' ? 'bg-green-900 text-green-300' : 'bg-gray-700 text-gray-400'">
                    <span class="w-2 h-2 inline-block rounded-full mr-2"
                          :class="status.workers['worker-0']?.status === 'busy' ? 'bg-green-500' : 'bg-gray-500'"></span>
                    <span x-text="status.workers['worker-0']?.status || 'unknown'">--</span>
                </span>
            </div>
            <div class="flex items-center space-x-4">
                <button @click="refresh()" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg">
                    <i class="fas fa-sync-alt mr-2"></i>Refresh
                </button>
                <button @click="showNewBatch = true" class="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg">
                    <i class="fas fa-plus mr-2"></i>New Batch
                </button>
            </div>
        </div>
    </header>

    <!-- Main Content -->
    <main class="p-6">

        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-400 text-sm">Total Tasks</p>
                        <p class="text-3xl font-bold" x-text="status.metrics?.total_tasks || 0">0</p>
                    </div>
                    <div class="text-blue-500 text-3xl">
                        <i class="fas fa-tasks"></i>
                    </div>
                </div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-400 text-sm">Completed</p>
                        <p class="text-3xl font-bold text-green-500" x-text="status.metrics?.completed_tasks || 0">0</p>
                    </div>
                    <div class="text-green-500 text-3xl">
                        <i class="fas fa-check-circle"></i>
                    </div>
                </div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-400 text-sm">Failed</p>
                        <p class="text-3xl font-bold text-red-500" x-text="status.metrics?.failed_tasks || 0">0</p>
                    </div>
                    <div class="text-red-500 text-3xl">
                        <i class="fas fa-exclamation-triangle"></i>
                    </div>
                </div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4 border border-gray-700">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-400 text-sm">Active Workers</p>
                        <p class="text-3xl font-bold text-yellow-500" x-text="Object.keys(status.workers || {}).length">0</p>
                    </div>
                    <div class="text-yellow-500 text-3xl">
                        <i class="fas fa-users"></i>
                    </div>
                </div>
            </div>
        </div>

        <!-- Workers & Batches Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">

            <!-- Workers Panel -->
            <div class="bg-gray-800 rounded-lg border border-gray-700">
                <div class="px-4 py-3 border-b border-gray-700 flex justify-between items-center">
                    <h2 class="text-lg font-semibold">
                        <i class="fas fa-users mr-2"></i>Workers
                    </h2>
                    <span class="text-sm text-gray-400" x-text="Object.values(status.workers || {}).filter(w => w.status === 'busy').length + ' active'"></span>
                </div>
                <div class="p-4 space-y-3">
                    <template x-for="(worker, id) in status.workers" :key="id">
                        <div class="bg-gray-700 rounded-lg p-3">
                            <div class="flex items-center justify-between mb-2">
                                <span class="font-mono text-sm" x-text="id"></span>
                                <span class="px-2 py-1 text-xs rounded"
                                      :class="worker.status === 'busy' ? 'bg-green-900 text-green-300' :
                                             worker.status === 'paused' ? 'bg-yellow-900 text-yellow-300' :
                                             'bg-gray-600 text-gray-300'"
                                      x-text="worker.status">
                                </span>
                            </div>
                            <div class="w-full bg-gray-600 rounded-full h-2">
                                <div class="bg-blue-500 h-2 rounded-full progress-bar"
                                     :style="'width: ' + (worker.progress || 0) + '%'"></div>
                            </div>
                            <p class="text-xs text-gray-400 mt-2" x-text="worker.current_task || 'Idle'"></p>
                        </div>
                    </template>
                </div>
            </div>

            <!-- Batches Panel -->
            <div class="bg-gray-800 rounded-lg border border-gray-700">
                <div class="px-4 py-3 border-b border-gray-700 flex justify-between items-center">
                    <h2 class="text-lg font-semibold">
                        <i class="fas fa-layer-group mr-2"></i>Batch Jobs
                    </h2>
                    <span class="text-sm text-gray-400" x-text="Object.keys(status.batches || {}).length + ' jobs'"></span>
                </div>
                <div class="p-4 space-y-3 max-h-80 overflow-y-auto">
                    <template x-for="(batch, id) in status.batches" :key="id">
                        <div class="bg-gray-700 rounded-lg p-3">
                            <div class="flex items-center justify-between mb-2">
                                <span class="font-semibold" x-text="batch.name"></span>
                                <span class="px-2 py-1 text-xs rounded"
                                      :class="batch.status === 'completed' ? 'bg-green-900 text-green-300' :
                                             batch.status === 'failed' ? 'bg-red-900 text-red-300' :
                                             batch.status === 'running' ? 'bg-blue-900 text-blue-300' :
                                             'bg-gray-600 text-gray-300'"
                                      x-text="batch.status">
                                </span>
                            </div>
                            <div class="w-full bg-gray-600 rounded-full h-2 mb-2">
                                <div class="bg-blue-500 h-2 rounded-full progress-bar"
                                     :style="'width: ' + (batch.progress || 0) + '%'"></div>
                            </div>
                            <div class="flex justify-between text-xs text-gray-400">
                                <span x-text="batch.completed + '/' + batch.total + ' tasks'"></span>
                                <span x-text="batch.failed + ' failed'"></span>
                            </div>
                        </div>
                    </template>
                    <div x-show="Object.keys(status.batches || {}).length === 0" class="text-center text-gray-500 py-8">
                        <i class="fas fa-inbox text-4xl mb-2"></i>
                        <p>No batch jobs yet</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Downloads & Logs Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

            <!-- Active Downloads -->
            <div class="bg-gray-800 rounded-lg border border-gray-700">
                <div class="px-4 py-3 border-b border-gray-700">
                    <h2 class="text-lg font-semibold">
                        <i class="fas fa-download mr-2"></i>Active Downloads
                    </h2>
                </div>
                <div class="p-4 space-y-3 max-h-64 overflow-y-auto">
                    <template x-for="(dl, id) in status.downloads" :key="id">
                        <div class="bg-gray-700 rounded-lg p-3">
                            <div class="flex items-center justify-between mb-1">
                                <span class="text-sm font-mono truncate" x-text="id" style="max-width: 150px;"></span>
                                <span class="text-xs text-gray-400" x-text="dl.progress + '%'"></span>
                            </div>
                            <div class="w-full bg-gray-600 rounded-full h-1.5">
                                <div class="bg-green-500 h-1.5 rounded-full"
                                     :style="'width: ' + (dl.progress || 0) + '%'"></div>
                            </div>
                        </div>
                    </template>
                    <div x-show="Object.keys(status.downloads || {}).length === 0" class="text-center text-gray-500 py-4">
                        <p class="text-sm">No active downloads</p>
                    </div>
                </div>
            </div>

            <!-- Logs -->
            <div class="col-span-2 bg-gray-800 rounded-lg border border-gray-700">
                <div class="px-4 py-3 border-b border-gray-700 flex justify-between items-center">
                    <h2 class="text-lg font-semibold">
                        <i class="fas fa-list-alt mr-2"></i>System Logs
                    </h2>
                    <button @click="logs = []" class="text-xs text-red-400 hover:text-red-300">
                        Clear
                    </button>
                </div>
                <div class="p-4 max-h-64 overflow-y-auto font-mono text-xs">
                    <template x-for="(log, i) in logs" :key="i">
                        <div class="py-1 border-b border-gray-700 last:border-0">
                            <span class="text-gray-500" x-text="log.timestamp.split('T')[1].split('.')[0]"></span>
                            <span class="mx-2" :class="log.level === 'ERROR' ? 'text-red-400' :
                                                          log.level === 'WARNING' ? 'text-yellow-400' :
                                                          log.level === 'INFO' ? 'text-blue-400' : 'text-gray-400'"
                                  x-text="log.level"></span>
                            <span class="text-purple-400" x-text="log.source"></span>
                            <span class="text-gray-300" x-text="log.message"></span>
                        </div>
                    </template>
                    <div x-show="logs.length === 0" class="text-center text-gray-500 py-4">
                        <p>No logs yet</p>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- New Batch Modal -->
    <div x-show="showNewBatch" x-cloak class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md" @click.outside="showNewBatch = false">
            <h2 class="text-xl font-bold mb-4">Create New Batch</h2>

            <div class="space-y-4">
                <div>
                    <label class="block text-sm text-gray-400 mb-1">Batch Name</label>
                    <input type="text" x-model="newBatch.name" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2">
                </div>
                <div>
                    <label class="block text-sm text-gray-400 mb-1">Description</label>
                    <textarea x-model="newBatch.description" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2" rows="2"></textarea>
                </div>
                <div>
                    <label class="block text-sm text-gray-400 mb-1">URLs (one per line)</label>
                    <textarea x-model="newBatch.urls" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 font-mono text-sm" rows="5" placeholder="https://example.com/doc1.pdf&#10;https://example.com/doc2.pdf"></textarea>
                </div>
            </div>

            <div class="flex justify-end space-x-3 mt-6">
                <button @click="showNewBatch = false" class="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded">Cancel</button>
                <button @click="createBatch()" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded">Create Batch</button>
            </div>
        </div>
    </div>

    <script>
        function dashboard() {
            return {
                status: {},
                logs: [],
                showNewBatch: false,
                newBatch: {
                    name: '',
                    description: '',
                    urls: ''
                },

                init() {
                    this.refresh();
                    // Auto-refresh every 2 seconds
                    setInterval(() => this.refresh(), 2000);
                    // WebSocket for real-time logs
                    this.connectWebSocket();
                },

                async refresh() {
                    try {
                        const res = await fetch('/api/status');
                        this.status = await res.json();
                    } catch (e) {
                        console.error('Failed to refresh:', e);
                    }
                },

                connectWebSocket() {
                    const ws = new WebSocket(`ws://${window.location.host}/ws`);
                    ws.onmessage = (event) => {
                        const data = JSON.parse(event.data);
                        if (data.type === 'log') {
                            this.logs.unshift(data.log);
                            if (this.logs.length > 100) this.logs.pop();
                        } else if (data.type === 'status') {
                            this.status = data.status;
                        }
                    };
                    ws.onclose = () => {
                        setTimeout(() => this.connectWebSocket(), 3000);
                    };
                },

                async createBatch() {
                    const urls = this.newBatch.urls.split('\\n').filter(u => u.trim());
                    const tasks = urls.map(url => ({
                        url: url.trim(),
                        command: 'download'
                    }));

                    await fetch('/api/batches', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            name: this.newBatch.name,
                            description: this.newBatch.description,
                            tasks: tasks
                        })
                    });

                    this.showNewBatch = false;
                    this.newBatch = {name: '', description: '', urls: ''};
                    this.refresh();
                }
            }
        }
    </script>
</body>
</html>
"""


# =============================================================================
# API Endpoints
# =============================================================================


@app.get("/")
async def root():
    """Serve the dashboard HTML."""
    return HTMLResponse(DASHBOARD_HTML)


@app.get("/api/status")
async def get_status():
    """Get current system status."""
    return JSONResponse(state.get_status())


@app.post("/api/batches")
async def create_batch(request: Request):
    """Create a new batch job."""
    data = await request.json()

    name = data.get("name", "Untitled Batch")
    description = data.get("description", "")
    tasks = data.get("tasks", [])

    job_id = state.create_batch(name, description, tasks)

    return JSONResponse({"job_id": job_id, "status": "created"})


@app.get("/api/batches")
async def list_batches():
    """List all batch jobs."""
    return JSONResponse(
        {
            job_id: {
                "name": b.name,
                "description": b.description,
                "status": b.status,
                "progress": b.progress,
                "tasks": len(b.tasks),
                "created_at": b.created_at,
            }
            for job_id, b in state.batches.items()
        }
    )


@app.post("/api/batches/{job_id}/start")
async def start_batch(job_id: str):
    """Start a batch job."""
    if job_id not in state.batches:
        raise HTTPException(status_code=404, detail="Batch not found")

    batch = state.batches[job_id]
    batch.status = "running"
    batch.started_at = datetime.now(timezone.utc).isoformat()

    state.add_log("INFO", "batch", f"Started batch: {batch.name}")

    return JSONResponse({"status": "started"})


@app.post("/api/batches/{job_id}/cancel")
async def cancel_batch(job_id: str):
    """Cancel a batch job."""
    if job_id not in state.batches:
        raise HTTPException(status_code=404, detail="Batch not found")

    batch = state.batches[job_id]
    batch.status = "cancelled"

    state.add_log("INFO", "batch", f"Cancelled batch: {batch.name}")

    return JSONResponse({"status": "cancelled"})


@app.get("/api/logs")
async def get_logs(level: str | None = None, limit: int = 100):
    """Get system logs."""
    logs = state.logs

    if level:
        logs = [l for l in logs if l.level == level]

    return JSONResponse(logs[-limit:])


@app.delete("/api/logs")
async def clear_logs():
    """Clear all logs."""
    state.logs = []
    return JSONResponse({"status": "cleared"})


@app.get("/api/workers")
async def get_workers():
    """Get worker statuses."""
    return JSONResponse(
        {
            w_id: {
                "status": w.status,
                "current_task": w.current_task,
                "progress": w.progress,
                "messages": w.messages,
            }
            for w_id, w in state.workers.items()
        }
    )


# WebSocket for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates."""
    await websocket.accept()

    try:
        while True:
            # Send status updates every second
            await asyncio.sleep(1)
            await websocket.send_json({"type": "status", "status": state.get_status()})
    except WebSocketDisconnect:
        pass


# =============================================================================
# Demo Data (for testing)
# =============================================================================


def add_demo_data():
    """Add demo data for testing the dashboard."""

    # Add some logs
    state.add_log("INFO", "system", "Dashboard started")
    state.add_log("INFO", "mcp_server", "MCP server initialized on port 8765")
    state.add_log("INFO", "database", "Connected to Qdrant at localhost:6333")
    state.add_log("INFO", "database", "Connected to PostgreSQL at localhost:5432")
    state.add_log("INFO", "worker-0", "Worker 0 started")
    state.add_log("INFO", "worker-1", "Worker 1 started")
    state.add_log("WARNING", "worker-2", "Worker 2 encountered slow response")
    state.add_log("INFO", "worker-2", "Worker 2 recovered")

    # Add demo batch
    demo_tasks = [
        {"url": "https://justice.gov/epstein/disclosure-001.pdf", "type": "download"},
        {"url": "https://justice.gov/epstein/disclosure-002.pdf", "type": "download"},
        {"url": "https://justice.gov/epstein/disclosure-003.pdf", "type": "download"},
    ]
    state.create_batch("DOJ Initial Disclosure", "First batch of DOJ documents", demo_tasks)

    # Add demo downloads
    state.update_download(
        "disclosure-001.pdf",
        {
            "url": "https://justice.gov/epstein/disclosure-001.pdf",
            "progress": 75,
            "size": "2.3 MB",
            "speed": "1.2 MB/s",
        },
    )
    state.update_download(
        "disclosure-002.pdf",
        {
            "url": "https://justice.gov/epstein/disclosure-002.pdf",
            "progress": 30,
            "size": "1.8 MB",
            "speed": "0.8 MB/s",
        },
    )


# Add demo data on startup
add_demo_data()


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("Epstein Files Pipeline Dashboard")
    print("=" * 60)
    print("\nStarting dashboard server...")
    print("Open http://localhost:8080 in your browser\n")

    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
