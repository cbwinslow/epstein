#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request


def run(cmd: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False
        )
        return p.returncode, p.stdout.strip()
    except Exception as e:
        return 99, str(e)


def http_json(url: str, timeout: int = 3) -> tuple[bool, dict]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = r.read().decode("utf-8", errors="replace")
        return True, json.loads(data)
    except Exception:
        return False, {}


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []

    rc, _ = run(["docker", "version"])
    if rc != 0:
        failures.append("Docker not available (is the daemon running?)")
    else:
        print("✅ Docker OK")

    rc, _ = run(["docker", "compose", "version"])
    if rc != 0:
        warnings.append("docker compose plugin not found.")
    else:
        print("✅ docker compose OK")

    qdrant_port = os.getenv("QDRANT_PORT", "6333")
    ok, _ = http_json(f"http://127.0.0.1:{qdrant_port}/")
    if ok:
        print("✅ Qdrant reachable on localhost")
    else:
        warnings.append("Qdrant not reachable on localhost (run `make bootstrap`).")

    if failures:
        print("\n❌ Failures:")
        for f in failures:
            print(f"  - {f}")
        return 3
    if warnings:
        print("\n⚠️ Warnings:")
        for w in warnings:
            print(f"  - {w}")
        return 2
    print("\nAll good.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
