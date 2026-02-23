#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import urllib.parse
import urllib.request


def run(cmd: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
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

    # Optional: OpenTelemetry endpoint check
    otel_enabled = os.getenv("OTEL_ENABLED", "false").lower() in ("1", "true", "yes")
    if otel_enabled:
        otlp = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4317")
        parsed = urllib.parse.urlparse(otlp)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (4317 if parsed.scheme == "http" else 4317)
        try:
            socket.create_connection((host, port), timeout=3)
            print(f"✅ OpenTelemetry OTLP endpoint reachable at {host}:{port}")
        except Exception:
            warnings.append(f"OpenTelemetry OTLP endpoint not reachable at {host}:{port}")

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
