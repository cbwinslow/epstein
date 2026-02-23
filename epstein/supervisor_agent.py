"""
Supervisor Agent - Long-running AI Agent with Task Queue
Coordinates sub-agents, manages tasks, and provides monitoring.
"""

import asyncio
import json
import logging
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests

from epstein.task_queue import (
    TaskQueue,
    DeduplicationManager,
    TaskWorker,
    TaskStatus,
    TaskPriority,
)

logger = logging.getLogger("supervisor_agent")


class AgentCommand(Enum):
    """Commands the supervisor can execute."""

    ANALYZE = "analyze"
    DOWNLOAD = "download"
    PROCESS = "process"
    EXTRACT_ENTITIES = "extract_entities"
    SEARCH = "search"
    QUERY = "query"
    STATUS = "status"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"


@dataclass
class AnalysisResult:
    """Result from an analysis operation."""

    query: str
    results: List[Dict[str, Any]]
    agents_used: List[str]
    execution_time: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class SupervisorAgent:
    """
    Long-running Supervisor Agent that:
    - Manages task queue with persistence
    - Coordinates sub-agents
    - Provides monitoring and status
    - Supports pause/resume/stop
    - Uses free AI models (Ollama/OpenRouter)
    """

    def __init__(
        self,
        name: str = "SupervisorAgent",
        model: str = "ollama:mistral",  # or openrouter model
        db_path: str = "./data/epstein.db",
        log_path: str = "./logs",
    ):
        self.name = name
        self.model = model
        self.db_path = db_path
        self.log_path = log_path

        # Ensure directories exist
        Path(log_path).mkdir(parents=True, exist_ok=True)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.task_queue = TaskQueue(db_path)
        self.dedup = DeduplicationManager(db_path)

        # Agent registry
        self.agents: Dict[str, Callable] = {}
        self.workers: List[TaskWorker] = []

        # State
        self._running = False
        self._paused = False
        self._stop_event = threading.Event()

        # Results storage
        self.analysis_history: List[AnalysisResult] = []

        # Configure logging
        self._setup_logging()

        # Register default handlers
        self._register_default_handlers()

    def _setup_logging(self):
        """Setup logging to file."""
        log_file = Path(self.log_path) / f"supervisor_{datetime.now().strftime('%Y%m%d')}.log"

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(),
            ],
        )

    def _register_default_handlers(self):
        """Register default command handlers."""
        self.agents = {
            "download": self._handle_download,
            "process": self._handle_process,
            "extract_entities": self._handle_extract_entities,
            "analyze": self._handle_analyze,
            "search": self._handle_search,
        }

    def register_agent(self, command: str, handler: Callable):
        """Register a sub-agent handler."""
        self.agents[command] = handler
        logger.info(f"Registered agent handler: {command}")

    def start_workers(self, num_workers: int = 2):
        """Start background workers."""
        for i in range(num_workers):
            worker = TaskWorker(
                worker_id=f"worker-{i}",
                task_queue=self.task_queue,
                deduplication=self.dedup,
                handlers=self.agents,
            )
            worker.start()
            self.workers.append(worker)

        logger.info(f"Started {num_workers} workers")

    def stop_workers(self):
        """Stop all workers."""
        for worker in self.workers:
            worker.stop()
        self.workers.clear()
        logger.info("All workers stopped")

    def submit_task(
        self,
        command: str,
        name: str,
        args: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> str:
        """Submit a task to the queue."""
        import uuid

        task_id = str(uuid.uuid4())[:8]

        self.task_queue.add_task(
            task_id=task_id,
            name=name,
            command=command,
            args=args,
            priority=priority,
        )

        logger.info(f"Submitted task {task_id}: {command} - {name}")
        return task_id

    def get_status(self) -> Dict[str, Any]:
        """Get supervisor status."""
        queue_status = self.task_queue.get_queue_status()

        return {
            "name": self.name,
            "model": self.model,
            "running": self._running,
            "paused": self._paused,
            "workers": len(self.workers),
            "queue": queue_status,
            "registered_agents": list(self.agents.keys()),
            "analysis_history_count": len(self.analysis_history),
        }

    def analyze(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """
        Main analysis method - uses AI to analyze documents.
        """
        start_time = time.time()

        # Build the prompt
        prompt = self._build_analysis_prompt(query, context or {})

        # Call AI model
        response = self._call_ai(prompt)

        # Parse results
        results = self._parse_ai_response(response)

        execution_time = time.time() - start_time

        result = AnalysisResult(
            query=query,
            results=results,
            agents_used=["supervisor", "analysis"],
            execution_time=execution_time,
        )

        self.analysis_history.append(result)

        return result

    def _build_analysis_prompt(self, query: str, context: Dict[str, Any]) -> str:
        """Build prompt for AI analysis."""
        prompt = f"""You are analyzing documents related to the Epstein case.
        
Query: {query}

Context:
- Document types: flight logs, emails, meetings, financial records, phone records
- Entity types: PERSON, ORG, GPE, DATE, MONEY, FLIGHT, CONTACT
- Relationship types: COMMUNICATED_WITH, FLIGHT_WITH, MET_AT, PAID, WORKED_FOR

Provide a detailed analysis with:
1. Key findings
2. Entities mentioned (people, organizations, locations)
3. Dates and times
4. Relationships identified
5. Confidence level

Format as JSON with keys: findings, entities, dates, relationships, confidence
"""

        if context.get("documents"):
            prompt += f"\n\nRelevant documents:\n{context['documents'][:2000]}"

        return prompt

    def _call_ai(self, prompt: str) -> str:
        """Call AI model (Ollama or OpenRouter)."""
        if self.model.startswith("ollama:"):
            return self._call_ollama(prompt)
        elif self.model.startswith("openrouter:"):
            return self._call_openrouter(prompt)
        else:
            return self._call_ollama(prompt)

    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama local model."""
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        model = self.model.replace("ollama:", "")

        try:
            response = requests.post(
                f"{host}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=120,
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return json.dumps({"error": str(e)})

    def _call_openrouter(self, prompt: str) -> str:
        """Call OpenRouter API."""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return json.dumps({"error": "OPENROUTER_API_KEY not set"})

        model = self.model.replace("openrouter:", "")

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenRouter call failed: {e}")
            return json.dumps({"error": str(e)})

    def _parse_ai_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse AI response into structured results."""
        try:
            # Try to parse as JSON
            data = json.loads(response)
            if isinstance(data, dict):
                return [data]
            return data
        except json.JSONDecodeError:
            # Return as text
            return [{"type": "text", "content": response}]

    # Handler methods
    def _handle_download(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle download task."""
        url = args.get("url")
        dest = args.get("destination", "./downloads")

        # Check dedup
        url_hash = self.dedup.compute_hash(url=url)
        if self.dedup.is_processed(url_hash, "download"):
            return {"status": "skipped", "reason": "already_downloaded", "url": url}

        # TODO: Implement actual download
        # For now, mark as processed
        self.dedup.mark_processed(url_hash, "download", dest)

        return {"status": "completed", "url": url, "destination": dest}

    def _handle_process(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document processing task."""
        file_path = args.get("file_path")

        # Check dedup
        file_hash = self.dedup.compute_hash(file_path=file_path)
        if self.dedup.is_processed(file_hash, "process"):
            return {"status": "skipped", "reason": "already_processed"}

        # TODO: Implement actual processing
        self.dedup.mark_processed(file_hash, "process", file_path)

        return {"status": "completed", "file": file_path}

    def _handle_extract_entities(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle entity extraction task."""
        text = args.get("text", "")

        # Use AI to extract entities
        prompt = f"""Extract entities from this text. Return JSON with:
- persons: list of person names
- organizations: list of org names
- locations: list of location names
- dates: list of dates mentioned
- flights: flight numbers/aircraft mentioned
- money: monetary amounts mentioned

Text: {text[:3000]}
"""
        response = self._call_ai(prompt)

        try:
            entities = json.loads(response)
        except:
            entities = {"raw": response}

        return {"status": "completed", "entities": entities}

    def _handle_analyze(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle analysis task."""
        query = args.get("query", "")
        context = args.get("context", {})

        result = self.analyze(query, context)

        return {
            "status": "completed",
            "query": query,
            "results": result.results,
            "execution_time": result.execution_time,
        }

    def _handle_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search task."""
        query = args.get("query", "")

        # Use RAG to search
        # TODO: Implement actual search
        return {"status": "completed", "query": query, "results": []}

    def run_analysis_loop(self):
        """Run the supervisor in analysis mode."""
        self._running = True

        logger.info(f"{self.name} started in analysis mode")

        while self._running and not self._stop_event.is_set():
            if self._paused:
                time.sleep(1)
                continue

            # Check for pending tasks
            status = self.get_status()
            pending = status["queue"]["status_counts"].get("pending", 0)

            if pending > 0:
                logger.info(f"Processing {pending} pending tasks")

            time.sleep(5)

        logger.info(f"{self.name} stopped")

    def stop(self):
        """Stop the supervisor."""
        self._running = False
        self._stop_event.set()
        self.stop_workers()
        logger.info(f"{self.name} stopped")

    def pause(self):
        """Pause the supervisor."""
        self._paused = True
        for worker in self.workers:
            worker.pause()
        logger.info(f"{self.name} paused")

    def resume(self):
        """Resume the supervisor."""
        self._paused = False
        for worker in self.workers:
            worker.resume()
        logger.info(f"{self.name} resumed")


def main():
    """Main entry point for supervisor agent."""
    import argparse

    parser = argparse.ArgumentParser(description="Epstein Supervisor Agent")
    parser.add_argument("--model", default="ollama:mistral", help="AI model to use")
    parser.add_argument("--workers", type=int, default=2, help="Number of workers")
    parser.add_argument("--db", default="./data/epstein.db", help="Database path")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    # Create supervisor
    supervisor = SupervisorAgent(
        model=args.model,
        db_path=args.db,
    )

    # Setup signal handlers
    def signal_handler(sig, frame):
        print("\nShutting down...")
        supervisor.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start workers
    supervisor.start_workers(args.workers)

    if args.interactive:
        # Interactive mode
        print("Epstein Supervisor Agent")
        print("Commands: analyze, status, stop, pause, resume, quit")

        while True:
            try:
                cmd = input("\n> ").strip()

                if cmd == "quit" or cmd == "exit":
                    break
                elif cmd == "status":
                    print(json.dumps(supervisor.get_status(), indent=2))
                elif cmd.startswith("analyze "):
                    query = cmd[8:]
                    result = supervisor.analyze(query)
                    print(json.dumps(result.results, indent=2))
                elif cmd == "pause":
                    supervisor.pause()
                elif cmd == "resume":
                    supervisor.resume()
                elif cmd == "stop":
                    break
                else:
                    print("Unknown command")

            except EOFError:
                break
            except Exception as e:
                print(f"Error: {e}")

        supervisor.stop()
    else:
        # Run loop
        supervisor.run_analysis_loop()


if __name__ == "__main__":
    main()
