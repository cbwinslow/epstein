#!/usr/bin/env python3
from __future__ import annotations

import json

from epstein.utils.task_logger import collect_task_logs


def main() -> int:
    logs = collect_task_logs()
    counts: dict[str, int] = {}
    for e in logs:
        s = e.get("status", "unknown")
        counts[s] = counts.get(s, 0) + 1
    print(json.dumps({"count": len(logs), "by_status": counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
