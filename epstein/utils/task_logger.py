from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TaskLogger:
    def __init__(self, log_dir: Path | str = "artifacts/task_logs") -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log(self, task_id: str, status: str, details: dict[str, Any] | None = None) -> Path:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "task_id": task_id,
            "status": status,
            "details": details or {},
        }
        path = self.log_dir / f"{task_id}.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return path


def collect_task_logs(log_dir: Path | str = "artifacts/task_logs") -> list[dict]:
    p = Path(log_dir)
    entries: list[dict] = []
    if not p.exists():
        return entries
    for f in sorted(p.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
    return entries
