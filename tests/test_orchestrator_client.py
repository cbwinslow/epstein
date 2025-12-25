import asyncio
import pytest

from tools.mission_control.orchestrator_client import OrchestratorClient


class DummyOrch:
    async def get_system_status(self):
        return {"agents": {"a": {"status": "ok"}}, "tasks": {"total": 1, "pending": 0, "running": 0, "completed": 1, "failed": 0}}

    async def run_comprehensive_analysis(self):
        return {"task_id": "comprehensive_analysis", "status": "completed"}


@pytest.mark.asyncio
async def test_orchestrator_client_monkeypatched(monkeypatch):
    # Patch the underlying Orchestrator to be our dummy
    import tools.mission_control.orchestrator_client as ocmod
    monkeypatch.setattr(ocmod, "MultiAgentOrchestrator", lambda config=None: DummyOrch())

    client = OrchestratorClient()
    status = await client.get_status()
    assert status["agents"]["a"]["status"] == "ok"

    res = await client.run_comprehensive()
    assert res["status"] == "completed"
