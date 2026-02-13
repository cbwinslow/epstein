#!/usr/bin/env python3
"""Run a best-effort repair and validation suite for the repo.

This script is intentionally conservative: it runs checks, captures output,
optionally applies safe auto-fixes (ruff), and writes a JSON report.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class CommandResult:
    name: str
    command: List[str]
    returncode: int
    duration_s: float
    stdout: str
    stderr: str
    skipped: bool


def run_command(name: str, command: List[str]) -> CommandResult:
    start = time.time()
    try:
        proc = subprocess.run(command, capture_output=True, text=True, check=False)
        return CommandResult(
            name=name,
            command=command,
            returncode=proc.returncode,
            duration_s=time.time() - start,
            stdout=proc.stdout,
            stderr=proc.stderr,
            skipped=False,
        )
    except FileNotFoundError:
        return CommandResult(
            name=name,
            command=command,
            returncode=127,
            duration_s=time.time() - start,
            stdout="",
            stderr="command not found",
            skipped=True,
        )


def tool_available(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run validation checks and emit a repair report.")
    parser.add_argument("--fix", action="store_true", help="Apply safe auto-fixes (ruff --fix)")
    parser.add_argument("--report-dir", default="./logs", help="Directory for report output")
    parser.add_argument("--pytest-args", default="-q", help="Arguments to pass to pytest")
    args = parser.parse_args()

    commands: List[tuple[str, List[str], Optional[str]]] = []

    if tool_available("uv"):
        commands.append(("ruff_check", ["uv", "run", "ruff", "check", "."], "ruff"))
        if args.fix:
            commands.append(("ruff_fix", ["uv", "run", "ruff", "check", ".", "--fix"], "ruff"))
        commands.append(("pytest", ["uv", "run", "pytest", *args.pytest_args.split()], "pytest"))
    else:
        commands.append(("ruff_check", ["ruff", "check", "."], "ruff"))
        if args.fix:
            commands.append(("ruff_fix", ["ruff", "check", ".", "--fix"], "ruff"))
        commands.append(("pytest", ["pytest", *args.pytest_args.split()], "pytest"))

    commands.append(("pip_check", [sys.executable, "-m", "pip", "check"], "pip"))

    results: List[CommandResult] = []
    for name, command, tool_name in commands:
        if tool_name and not tool_available(command[0]):
            results.append(
                CommandResult(
                    name=name,
                    command=command,
                    returncode=127,
                    duration_s=0.0,
                    stdout="",
                    stderr=f"{command[0]} not available",
                    skipped=True,
                )
            )
            continue
        results.append(run_command(name, command))

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"repair_report_{int(time.time())}.json"
    report_path.write_text(
        json.dumps([result.__dict__ for result in results], indent=2),
        encoding="utf-8",
    )

    failures = [r for r in results if not r.skipped and r.returncode != 0]
    print(f"[repair] report written to {report_path}")
    if failures:
        print("[repair] failures detected:")
        for failure in failures:
            print(f" - {failure.name}: exit {failure.returncode}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
