"""MCP server for running the Epstein processing pipeline."""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("epstein_files_processor")

Runner = Callable[[List[str], Path], Awaitable[int]]


class ProcessingRequest(BaseModel):
    config_path: str = Field(..., description="Path to pipeline config JSON")
    artifacts_dir: Optional[str] = Field(None, description="Override pipeline output_dir")
    dsn: Optional[str] = Field(None, description="Postgres DSN for ingestion/embeddings")
    qdrant_url: Optional[str] = Field(None, description="Qdrant URL for embeddings")
    collection: str = Field("epstein_chunks", description="Qdrant collection name")
    run_ingest: bool = Field(True, description="Load artifacts into Postgres")
    run_relationships: bool = Field(True, description="Generate relationship analysis outputs")
    run_embeddings: bool = Field(False, description="Generate vector embeddings in Qdrant")
    run_image_ocr: bool = Field(False, description="OCR images stored in artifacts/images")
    relationship_min_count: int = Field(2, description="Minimum co-occurrence count")
    relationship_max_evidence: int = Field(5, description="Max evidence records per relationship")
    image_input_dir: Optional[str] = Field(None, description="Directory of images to OCR")
    image_output_dir: Optional[str] = Field(None, description="Output directory for OCR text")
    image_extensions: List[str] = Field(default_factory=lambda: [".png", ".jpg", ".jpeg", ".tif", ".tiff"])


class ProcessingStatus(BaseModel):
    task_id: str
    status: str
    command: List[str]
    log_path: Optional[str]
    error: Optional[str]
    exit_code: Optional[int]


@dataclass
class ProcessTask:
    task_id: str
    request: ProcessingRequest
    command: List[str]
    status: str = "queued"
    log_path: Optional[Path] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None


def default_runner_factory() -> Runner:
    async def _runner(command: List[str], log_path: Path) -> int:
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("wb") as handle:
            assert proc.stdout is not None
            while True:
                chunk = await proc.stdout.readline()
                if not chunk:
                    break
                handle.write(chunk)
        return await proc.wait()

    return _runner


class EpsteinFilesProcessor:
    def __init__(self, runner: Optional[Runner] = None) -> None:
        self.app = FastAPI(
            title="Epstein Files Processor",
            description="MCP Server for running the Epstein download/OCR/NER/analysis pipeline.",
            version="0.1.0",
        )
        self.tasks: Dict[str, ProcessTask] = {}
        self.runner = runner or default_runner_factory()
        self._configure_routes()

    def _build_command(self, request: ProcessingRequest) -> List[str]:
        cmd = [sys.executable, "-m", "epstein.pipeline_orchestrator", "--config", request.config_path]
        if request.artifacts_dir:
            cmd += ["--artifacts-dir", request.artifacts_dir]
        if request.dsn:
            cmd += ["--dsn", request.dsn]
        if request.qdrant_url:
            cmd += ["--qdrant-url", request.qdrant_url]
        if request.collection:
            cmd += ["--collection", request.collection]
        if request.run_ingest:
            cmd.append("--run-ingest")
        if request.run_relationships:
            cmd.append("--run-relationships")
        if request.run_embeddings:
            cmd.append("--run-embeddings")
        if request.run_image_ocr:
            cmd.append("--run-image-ocr")
        cmd += ["--relationship-min-count", str(request.relationship_min_count)]
        cmd += ["--relationship-max-evidence", str(request.relationship_max_evidence)]
        if request.image_input_dir:
            cmd += ["--image-input-dir", request.image_input_dir]
        if request.image_output_dir:
            cmd += ["--image-output-dir", request.image_output_dir]
        if request.image_extensions:
            cmd += ["--image-extensions", ",".join(request.image_extensions)]
        return cmd

    def _task_to_status(self, task: ProcessTask) -> ProcessingStatus:
        return ProcessingStatus(
            task_id=task.task_id,
            status=task.status,
            command=task.command,
            log_path=str(task.log_path) if task.log_path else None,
            error=task.error,
            exit_code=task.exit_code,
        )

    async def _execute_task(self, task: ProcessTask) -> None:
        task.status = "running"
        try:
            log_path = task.log_path or Path("./logs") / f"pipeline_{task.task_id}.log"
            task.log_path = log_path
            task.exit_code = await self.runner(task.command, log_path)
            task.status = "completed" if task.exit_code == 0 else "failed"
        except Exception as exc:  # noqa: BLE001
            task.status = "failed"
            task.error = str(exc)

    def _configure_routes(self) -> None:
        @self.app.get("/")
        async def root() -> dict:
            return {
                "service": "epstein_files_processor",
                "status": "ok",
                "active_tasks": len([t for t in self.tasks.values() if t.status == "running"]),
            }

        @self.app.post("/process/run", response_model=ProcessingStatus)
        async def run_process(request: ProcessingRequest, background_tasks: BackgroundTasks) -> ProcessingStatus:
            task_id = str(uuid.uuid4())
            command = self._build_command(request)
            task = ProcessTask(task_id=task_id, request=request, command=command)
            self.tasks[task_id] = task
            background_tasks.add_task(self._execute_task, task)
            return self._task_to_status(task)

        @self.app.get("/process/status/{task_id}", response_model=ProcessingStatus)
        async def get_status(task_id: str) -> ProcessingStatus:
            task = self.tasks.get(task_id)
            if not task:
                raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
            return self._task_to_status(task)

        @self.app.get("/process/status", response_model=List[ProcessingStatus])
        async def list_status() -> List[ProcessingStatus]:
            return [self._task_to_status(task) for task in self.tasks.values()]


def main() -> None:
    import argparse

    import uvicorn

    logging.basicConfig(level=logging.INFO)

    ap = argparse.ArgumentParser(description="Run the Epstein Files Processor MCP server.")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8780)
    args = ap.parse_args()

    server = EpsteinFilesProcessor()
    uvicorn.run(server.app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
