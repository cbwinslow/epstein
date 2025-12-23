#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import urllib.request
from typing import Tuple

try:
    import psycopg
except Exception:
    psycopg = None


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


def check_postgres(dsn: str | None = None, timeout: int = 3) -> Tuple[bool, str]:
    """Check Postgres reachability.

    Steps:
    - If DSN provided, parse host/port and attempt TCP connection.
    - If psycopg is installed, try a short connection and run `SELECT 1`.

    Returns (ok, message)
    """
    # Allow env override
    if not dsn:
        dsn = os.getenv("EPSTEIN_DSN")
    if not dsn:
        # try individual POSTGRES_* vars
        user = os.getenv("POSTGRES_USER")
        host = os.getenv("POSTGRES_HOST", os.getenv("POSTGRES_HOSTNAME", "localhost"))
        port = os.getenv("POSTGRES_PORT", os.getenv("PG_PORT", "5432"))
        db = os.getenv("POSTGRES_DB")
        if host:
            try:
                port_i = int(port)
            except Exception:
                port_i = 5432
            try:
                with socket.create_connection((host, port_i), timeout=timeout):
                    pass
            except Exception as e:
                return False, f"Postgres TCP connect to {host}:{port} failed: {e}"
            return True, "Postgres TCP reachable (no DSN provided, skipped SQL check)"
        return False, "No Postgres DSN or host information found in environment"

    # Parse DSN using urllib
    try:
        from urllib.parse import urlparse

        parsed = urlparse(dsn)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
    except Exception:
        return False, "Failed to parse EPSTEIN_DSN"

    # TCP check
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except Exception as e:
        return False, f"Postgres TCP connect to {host}:{port} failed: {e}"

    # If psycopg available, do a simple SELECT 1
    if psycopg is None:
        return True, "Postgres reachable (psycopg not installed; only TCP check performed)"

    try:
        conn = psycopg.connect(dsn, timeout=timeout)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                _ = cur.fetchone()
        finally:
            conn.close()
        return True, "Postgres reachable and responded to SELECT 1"
    except Exception as e:
        return False, f"Postgres connection or query failed: {e}"


def _parse_args() -> any:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--check-db", action="store_true", help="check Postgres reachability using EPSTEIN_DSN or POSTGRES_* env vars")
    return ap.parse_args()

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
    args = _parse_args()
    if args.check_db:
        ok, msg = check_postgres()
        if ok:
            print("✅", msg)
            sys.exit(0)
        else:
            print("❌", msg)
            sys.exit(2)
    sys.exit(main())
