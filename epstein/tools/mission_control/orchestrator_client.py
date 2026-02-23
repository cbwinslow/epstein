"""Simple async client that wraps the MultiAgentOrchestrator to provide a stable API for the TUI."""
from __future__ import annotations

from typing import Any, Dict
import asyncio

try:
    from agents.multi_agent_orchestrator import MultiAgentOrchestrator
except Exception:
    MultiAgentOrchestrator = None


class OrchestratorClient:
    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        self._orchestrator = MultiAgentOrchestrator(config) if MultiAgentOrchestrator else None
        self._lock = asyncio.Lock()

    async def get_status(self) -> Dict[str, Any]:
        if self._orchestrator is None:
            return {"error": "orchestrator_not_available"}
        async with self._lock:
            return await self._orchestrator.get_system_status()

    async def run_comprehensive(self) -> Dict[str, Any]:
        if self._orchestrator is None:
            return {"error": "orchestrator_not_available"}
        async with self._lock:
            return await self._orchestrator.run_comprehensive_analysis()
