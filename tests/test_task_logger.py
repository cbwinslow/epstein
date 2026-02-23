import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from epstein.utils.task_logger import TaskLogger, collect_task_logs


def test_task_logger(tmp_path: Path):
    logdir = tmp_path / "logs"
    t = TaskLogger(logdir)
    p1 = t.log("task-1", "in_progress", {"note": "started"})
    assert p1.exists()
    p2 = t.log("task-1", "completed", {"result": "ok"})
    assert p2.exists()

    entries = collect_task_logs(logdir)
    assert len(entries) == 2
    assert any(e.get("status") == "completed" for e in entries)
