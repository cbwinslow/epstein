import pytest
import asyncio

from tools.mission_control.app import MissionControlApp


class DummyPane:
    def __init__(self):
        self.content = ""

    async def refresh(self):
        return True


class DummyOrch:
    async def get_status(self):
        return {"agents": {"a": {"status": "ok"}}, "tasks": {"total": 2, "pending": 1, "running": 0, "completed": 1, "failed": 0}}


@pytest.mark.asyncio
async def test_poll_updates_panes(monkeypatch):
    app = MissionControlApp()
    # stub panes and orch
    app.agents_pane = DummyPane()
    app.tasks_pane = DummyPane()
    app.logs_pane = DummyPane()
    app.orch = DummyOrch()

    await app._poll_status()
    assert "a: ok" in app.agents_pane.content
    assert "total:2" in app.tasks_pane.content or "total:2" in app.tasks_pane.content.replace(' ', '')
