import asyncio
import pytest
from tools.mission_control.orchestrator_client import OrchestratorClient


@pytest.mark.asyncio
async def test_orchestrator_client_poll(monkeypatch):
    # Create a dummy orchestrator with an async get_system_status
    class DummyOrch:
        def __init__(self):
            self.called = 0

        async def get_system_status(self):
            self.called += 1
            return {"agents": {"a": {"status": "ok"}}}

    # Patch the MultiAgentOrchestrator inside the client module to use our dummy
    import tools.mission_control.orchestrator_client as oc

    monkeypatch.setattr(oc, "MultiAgentOrchestrator", lambda config=None: DummyOrch())

    client = oc.OrchestratorClient()

    # Poll once using poll_status with a callback that stores the status
    results = []

    def cb(s):
        results.append(s)

    # Run poll_status for one iteration and stop
    stop = asyncio.Event()

    async def runner():
        # schedule stop after first poll
        async def stop_later():
            await asyncio.sleep(0.1)
            stop.set()

        task = asyncio.create_task(client.poll_status(cb, interval=0.05, stop_event=stop))
        await stop_later()
        await task

    await runner()

    assert len(results) >= 1
    assert results[0]["agents"]["a"]["status"] == "ok"


class DummyOrch:
    async def get_system_status(self):
        return {
            "agents": {"a": {"status": "ok"}},
            "tasks": {"total": 1, "pending": 0, "running": 0, "completed": 1, "failed": 0},
        }

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
