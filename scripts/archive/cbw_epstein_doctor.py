#!/usr/bin/env python3
"""
Script Name: cbw_epstein_doctor.py
Date: 2025-12-23
Author: ChatGPT (for Blaine Winslow / cbwinslow)

Summary
-------
A safe, idempotent "doctor" + setup validator for your Epstein/OpenDiscourse-style project.

This script is designed for the moment you said: "I haven't run anything yet".
It will:
  - Auto-discover the project root (walk upward looking for common markers).
  - Validate the repo layout + presence of critical docs/config.
  - Validate Python runtime, optional venv, and dependency installability.
  - Validate external tooling (git, curl, unzip, psql, docker, etc.).
  - Validate PostgreSQL connectivity (if DATABASE_URL / PG* env vars provided).
  - Validate docker compose (if docker-compose.yml exists).
  - Produce a single, readable report and a machine-parsable JSON report.
  - Optionally attempt fixes in a DRY-RUN manner unless --apply is provided.

Inputs
------
Environment variables (optional):
  - PROJECT_ROOT: Force project root path.
  - DATABASE_URL: PostgreSQL connection string.
  - PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD: standard Postgres vars.
  - PYTHONPATH, VIRTUAL_ENV: used for introspection.

Command-line arguments:
  - --mode {doctor,validate,init,fix}
  - --apply (required to actually install packages / run mutating commands)
  - --project-root PATH (override autodiscovery)
  - --venv PATH (default: <project>/.venv)
  - --requirements PATH (default: <project>/requirements.txt if present)
  - --compose PATH (default: <project>/docker-compose.yml if present)
  - --timeout-seconds N
  - --json-out PATH
  - --log PATH

Outputs
-------
- Human-readable report to stdout.
- Detailed log file (default: /tmp/CBW-cbw_epstein_doctor.log).
- JSON report (default: <project>/.cbw/doctor_report.json when possible, else /tmp).

Safety
------
- By default this script is non-destructive.
- Any install / config changes require BOTH --mode fix|init AND --apply.

Modification Log
----------------
- 2025-12-23: Initial version.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as _dt
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ------------------------------
# Constants (edit me)
# ------------------------------
SCRIPT_NAME = "cbw_epstein_doctor"
DEFAULT_LOG_PATH = Path("/tmp") / f"CBW-{SCRIPT_NAME}.log"
DEFAULT_TIMEOUT_SECONDS = 20

# Common markers used to auto-discover project root.
PROJECT_ROOT_MARKERS = [
    ".git",
    "pyproject.toml",
    "requirements.txt",
    "docker-compose.yml",
    "compose.yml",
    "README.md",
    "srs.md",
    "PROJECT_SUMMARY.md",
    "docs",
]

# Files you likely expect in a well-documented repo skeleton.
# This is intentionally *soft* validation — missing items become warnings, not fatal errors.
RECOMMENDED_DOC_FILES = [
    "README.md",
    "srs.md",
    "project_summary.md",
    "features.md",
    "tasks.md",
    "todo.md",
    "agents.md",
    "tools.md",
    "rules.md",
    "logs.md",
]

# Tools that help bootstrap/download large datasets and manage infra.
RECOMMENDED_TOOLS = [
    "git",
    "curl",
    "unzip",
    "tar",
]

OPTIONAL_TOOLS = [
    "psql",
    "docker",
    "docker-compose",  # legacy
]

# ------------------------------
# Data models
# ------------------------------


@dataclass
class CheckResult:
    name: str
    ok: bool
    severity: str  # INFO | WARN | ERROR
    summary: str
    details: dict[str, Any] = dataclasses.field(default_factory=dict)
    remediation: str = ""


@dataclass
class DoctorReport:
    started_at: str
    finished_at: str
    elapsed_seconds: float
    project_root: str
    mode: str
    checks: list[CheckResult]

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "elapsed_seconds": self.elapsed_seconds,
            "project_root": self.project_root,
            "mode": self.mode,
            "checks": [dataclasses.asdict(c) for c in self.checks],
        }


# ------------------------------
# Logging
# ------------------------------


class Logger:
    """Simple logger that writes to file + stdout with levels."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, level: str, msg: str) -> None:
        ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [{level}] {msg}"
        print(line)
        try:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            # Last-resort: never crash due to logging.
            pass

    def info(self, msg: str) -> None:
        self._write("INFO", msg)

    def warn(self, msg: str) -> None:
        self._write("WARN", msg)

    def error(self, msg: str) -> None:
        self._write("ERROR", msg)


# ------------------------------
# Helpers
# ------------------------------


def run_cmd(
    logger: Logger,
    cmd: list[str],
    timeout: int,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    allow_fail: bool = True,
) -> tuple[int, str, str]:
    """Run a command with robust capture. Never raises unless allow_fail=False."""
    logger.info(f"Running: {' '.join(cmd)} (cwd={cwd or Path.cwd()})")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=env,
            timeout=timeout,
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired as e:
        logger.error(f"Timeout after {timeout}s: {' '.join(cmd)}")
        return 124, "", f"TimeoutExpired: {e}"
    except FileNotFoundError as e:
        logger.error(f"Command not found: {cmd[0]}")
        return 127, "", f"FileNotFoundError: {e}"
    except Exception as e:
        logger.error(f"Unexpected error running command: {e}")
        if not allow_fail:
            raise
        return 1, "", f"Exception: {e}"


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def detect_package_manager() -> str | None:
    """Return one of: apt, dnf, yum, pacman, zypper, brew, apk."""
    for pm in ["apt-get", "dnf", "yum", "pacman", "zypper", "brew", "apk"]:
        if shutil.which(pm):
            return "apt" if pm == "apt-get" else pm
    return None


def is_wsl() -> bool:
    try:
        return "microsoft" in platform.uname().release.lower()
    except Exception:
        return False


def find_project_root(start: Path) -> Path:
    """Walk upward until we find any marker; fallback to start."""
    cur = start.resolve()
    for _ in range(50):
        for marker in PROJECT_ROOT_MARKERS:
            if (cur / marker).exists():
                return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()


def safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat()


def format_table(rows: list[tuple[str, str, str]]) -> str:
    """Very small table formatter (no external deps)."""
    if not rows:
        return "(no rows)"
    c1 = max(len(r[0]) for r in rows)
    c2 = max(len(r[1]) for r in rows)
    c3 = max(len(r[2]) for r in rows)
    out = []
    out.append(f"{'Check'.ljust(c1)}  {'Status'.ljust(c2)}  {'Summary'.ljust(c3)}")
    out.append(f"{'-'*c1}  {'-'*c2}  {'-'*c3}")
    for a, b, c in rows:
        out.append(f"{a.ljust(c1)}  {b.ljust(c2)}  {c.ljust(c3)}")
    return "\n".join(out)


# ------------------------------
# Checks
# ------------------------------


def check_runtime(logger: Logger) -> CheckResult:
    py_ver = sys.version.split()[0]
    ok = sys.version_info >= (3, 10)
    sev = "INFO" if ok else "ERROR"
    return CheckResult(
        name="python_runtime",
        ok=ok,
        severity=sev,
        summary=f"Python {py_ver} ({'OK' if ok else 'Need >= 3.10'})",
        details={
            "executable": sys.executable,
            "version": py_ver,
            "platform": platform.platform(),
            "wsl": is_wsl(),
        },
        remediation=(
            "Install Python 3.10+ (Ubuntu: apt install python3.11 python3.11-venv)"
            if not ok
            else ""
        ),
    )


def check_tools(logger: Logger, timeout: int) -> CheckResult:
    missing_required = [t for t in RECOMMENDED_TOOLS if which(t) is None]
    missing_optional = [t for t in OPTIONAL_TOOLS if which(t) is None]

    ok = len(missing_required) == 0
    sev = "INFO" if ok else "WARN"

    return CheckResult(
        name="tooling",
        ok=ok,
        severity=sev,
        summary=(
            "All required tools present" if ok else f"Missing required: {', '.join(missing_required)}"
        ),
        details={
            "missing_required": missing_required,
            "missing_optional": missing_optional,
            "package_manager": detect_package_manager(),
        },
        remediation=(
            "Install missing tools (Ubuntu/Debian: sudo apt-get update && sudo apt-get install -y "
            + " ".join(missing_required)
            if missing_required
            else ""
        ),
    )


def check_project_docs(logger: Logger, project_root: Path) -> CheckResult:
    present = []
    missing = []
    for f in RECOMMENDED_DOC_FILES:
        # Support both lower + common upper-case variants.
        cand = [project_root / f, project_root / f.upper()]
        if any(c.exists() for c in cand):
            present.append(f)
        else:
            missing.append(f)

    ok = len(missing) == 0
    sev = "INFO" if ok else "WARN"
    return CheckResult(
        name="project_docs",
        ok=ok,
        severity=sev,
        summary=("Docs look complete" if ok else f"Missing docs (non-fatal): {', '.join(missing[:6])}{'...' if len(missing)>6 else ''}"),
        details={"present": present, "missing": missing},
        remediation=(
            "If you used my zip bundles, make sure you extracted into the project root (not a nested folder)."
            if missing
            else ""
        ),
    )


def check_venv(logger: Logger, project_root: Path, venv_path: Path, timeout: int) -> CheckResult:
    py = venv_path / "bin" / "python"
    pip = venv_path / "bin" / "pip"

    exists = py.exists() and pip.exists()

    details: dict[str, Any] = {
        "venv_path": str(venv_path),
        "venv_exists": exists,
        "active_virtual_env": os.environ.get("VIRTUAL_ENV"),
    }

    if exists:
        rc, out, err = run_cmd(logger, [str(py), "-c", "import sys; print(sys.executable)"], timeout=timeout)
        details["venv_python_executable"] = out if rc == 0 else None
        details["venv_python_check_err"] = err if rc != 0 else ""

    ok = True  # Non-fatal — you might want to use system python.
    sev = "INFO" if exists else "WARN"
    return CheckResult(
        name="python_venv",
        ok=ok,
        severity=sev,
        summary=(".venv present" if exists else "No .venv found (recommended but not required)"),
        details=details,
        remediation=(
            "Create a venv: python3 -m venv .venv && . .venv/bin/activate && python -m pip install -U pip"
            if not exists
            else ""
        ),
    )


def check_requirements_installability(
    logger: Logger,
    project_root: Path,
    venv_path: Path,
    requirements_path: Path | None,
    timeout: int,
) -> CheckResult:
    if not requirements_path or not requirements_path.exists():
        return CheckResult(
            name="python_requirements",
            ok=True,
            severity="INFO",
            summary="No requirements.txt found (skipping dependency check)",
            details={"requirements_path": str(requirements_path) if requirements_path else None},
            remediation="",
        )

    pip = venv_path / "bin" / "pip"
    if not pip.exists():
        return CheckResult(
            name="python_requirements",
            ok=False,
            severity="WARN",
            summary="requirements.txt present but no venv pip found",
            details={"requirements_path": str(requirements_path), "venv_path": str(venv_path)},
            remediation="Create a venv at .venv (or pass --venv) before installing requirements.",
        )

    # Use --dry-run with pip when available; if not, we do a conservative "pip download" into temp.
    # We do NOT want to mutate your env in validate/doctor mode.
    details: dict[str, Any] = {
        "requirements_path": str(requirements_path),
        "method": None,
        "result": None,
        "stderr": "",
    }

    # Try pip 23+ dry-run resolver (not always supported).
    rc, out, err = run_cmd(
        logger,
        [str(pip), "install", "--dry-run", "-r", str(requirements_path)],
        timeout=timeout,
        cwd=project_root,
    )
    if rc == 0:
        details["method"] = "pip_install_dry_run"
        details["result"] = "ok"
        return CheckResult(
            name="python_requirements",
            ok=True,
            severity="INFO",
            summary="requirements appear installable (dry-run)",
            details=details,
            remediation="",
        )

    # Fallback: attempt to download wheels/sdists to temp (still non-destructive).
    with tempfile.TemporaryDirectory(prefix="cbw_pip_dl_") as td:
        rc2, out2, err2 = run_cmd(
            logger,
            [str(pip), "download", "-r", str(requirements_path), "-d", td],
            timeout=max(timeout, 45),
            cwd=project_root,
        )
        details["method"] = "pip_download_fallback"
        details["stderr"] = (err + "\n" + err2).strip()
        if rc2 == 0:
            details["result"] = "ok"
            return CheckResult(
                name="python_requirements",
                ok=True,
                severity="INFO",
                summary="requirements appear downloadable (good sign)",
                details=details,
                remediation="",
            )

    details["result"] = "failed"
    return CheckResult(
        name="python_requirements",
        ok=False,
        severity="WARN",
        summary="Dependency check failed (does not mean it's hopeless)",
        details=details,
        remediation=(
            "Typical fixes: upgrade pip/setuptools/wheel, ensure build deps, or pin versions. "
            "Run: . .venv/bin/activate && python -m pip install -U pip setuptools wheel"
        ),
    )


def parse_db_env() -> dict[str, str | None]:
    return {
        "DATABASE_URL": os.environ.get("DATABASE_URL"),
        "PGHOST": os.environ.get("PGHOST"),
        "PGPORT": os.environ.get("PGPORT"),
        "PGDATABASE": os.environ.get("PGDATABASE"),
        "PGUSER": os.environ.get("PGUSER"),
        "PGPASSWORD": "***" if os.environ.get("PGPASSWORD") else None,
    }


def check_postgres(logger: Logger, timeout: int) -> CheckResult:
    env = parse_db_env()
    has_any = any(v for k, v in env.items() if k != "PGPASSWORD")

    if not has_any:
        return CheckResult(
            name="postgres_connectivity",
            ok=True,
            severity="INFO",
            summary="No Postgres env vars set (skipping connectivity test)",
            details=env,
            remediation=(
                "Set DATABASE_URL (recommended) or PGHOST/PGDATABASE/PGUSER/PGPASSWORD to enable checks."
            ),
        )

    if which("psql") is None:
        return CheckResult(
            name="postgres_connectivity",
            ok=False,
            severity="WARN",
            summary="psql not installed (can't test Postgres connectivity)",
            details=env,
            remediation="Install PostgreSQL client tools (Ubuntu/Debian: sudo apt-get install -y postgresql-client).",
        )

    # Prefer DATABASE_URL if set.
    if os.environ.get("DATABASE_URL"):
        cmd = ["psql", os.environ["DATABASE_URL"], "-c", "SELECT 1;"]
    else:
        # psql will read PG* env vars.
        cmd = ["psql", "-c", "SELECT 1;"]

    rc, out, err = run_cmd(logger, cmd, timeout=timeout)
    ok = rc == 0
    sev = "INFO" if ok else "ERROR"
    return CheckResult(
        name="postgres_connectivity",
        ok=ok,
        severity=sev,
        summary=("Postgres connection OK" if ok else "Postgres connection FAILED"),
        details={"env": env, "stdout": out[-500:], "stderr": err[-500:], "rc": rc},
        remediation=(
            "Verify DB is reachable, credentials correct, and firewall allows access. "
            "If local, ensure service is running: sudo systemctl status postgresql"
            if not ok
            else ""
        ),
    )


def check_docker_compose(logger: Logger, project_root: Path, compose_path: Path | None, timeout: int) -> CheckResult:
    # Find compose file if not provided.
    if compose_path is None:
        for cand in [project_root / "docker-compose.yml", project_root / "compose.yml"]:
            if cand.exists():
                compose_path = cand
                break

    if compose_path is None or not compose_path.exists():
        return CheckResult(
            name="docker_compose",
            ok=True,
            severity="INFO",
            summary="No docker compose file found (skipping)",
            details={"compose_path": None},
            remediation="",
        )

    if which("docker") is None:
        return CheckResult(
            name="docker_compose",
            ok=False,
            severity="WARN",
            summary="docker-compose.yml present but docker not installed",
            details={"compose_path": str(compose_path)},
            remediation="Install Docker Engine + Compose plugin, then re-run doctor.",
        )

    # Prefer docker compose (plugin). Fallback to docker-compose.
    compose_cmd: list[str] | None = None
    if shutil.which("docker"):
        # Test whether `docker compose` works.
        rc, _, _ = run_cmd(logger, ["docker", "compose", "version"], timeout=timeout)
        if rc == 0:
            compose_cmd = ["docker", "compose"]

    if compose_cmd is None and shutil.which("docker-compose"):
        compose_cmd = ["docker-compose"]

    if compose_cmd is None:
        return CheckResult(
            name="docker_compose",
            ok=False,
            severity="WARN",
            summary="Docker found but Compose not available",
            details={"compose_path": str(compose_path)},
            remediation="Install Docker Compose plugin (recommended) or docker-compose.",
        )

    # Validate the compose file.
    rc, out, err = run_cmd(
        logger,
        compose_cmd + ["-f", str(compose_path), "config"],
        timeout=max(timeout, 45),
        cwd=project_root,
    )
    ok = rc == 0
    sev = "INFO" if ok else "ERROR"
    return CheckResult(
        name="docker_compose",
        ok=ok,
        severity=sev,
        summary=("Compose config valid" if ok else "Compose config invalid"),
        details={"compose_path": str(compose_path), "stdout": out[-1000:], "stderr": err[-1000:], "rc": rc},
        remediation=(
            "Run: docker compose -f docker-compose.yml config (to see validation errors)"
            if not ok
            else ""
        ),
    )


def check_network(logger: Logger, timeout: int) -> CheckResult:
    # Simple DNS + outbound TCP probe (safe).
    targets = [
        ("dns_google", "8.8.8.8", 53),
        ("https_github", "github.com", 443),
    ]

    details: dict[str, Any] = {"probes": []}
    all_ok = True

    for name, host, port in targets:
        probe = {"name": name, "host": host, "port": port, "ok": False, "latency_ms": None, "error": ""}
        t0 = time.time()
        try:
            # Resolve if host is not IP.
            if not re.match(r"^\d+\.\d+\.\d+\.\d+$", host):
                _ = socket.getaddrinfo(host, port)
            with socket.create_connection((host, port), timeout=timeout) as s:
                s.settimeout(timeout)
            probe["ok"] = True
            probe["latency_ms"] = int((time.time() - t0) * 1000)
        except Exception as e:
            all_ok = False
            probe["error"] = str(e)
        details["probes"].append(probe)

    sev = "INFO" if all_ok else "WARN"
    return CheckResult(
        name="network_basic",
        ok=True,  # non-fatal; you might be offline intentionally
        severity=sev,
        summary=("Network looks OK" if all_ok else "Network probes failed (may be offline/VPN)"),
        details=details,
        remediation=(
            "If downloads fail, check DNS/VPN/proxy. On Linux: resolvectl status; ping 1.1.1.1"
            if not all_ok
            else ""
        ),
    )


# ------------------------------
# Fixers (only run with --apply)
# ------------------------------


def fix_install_tools(logger: Logger, apply: bool, tools: list[str], timeout: int) -> CheckResult:
    pm = detect_package_manager()
    if pm is None:
        return CheckResult(
            name="fix_install_tools",
            ok=False,
            severity="WARN",
            summary="No supported package manager detected",
            details={"tools": tools},
            remediation="Install tools manually, or install a supported package manager.",
        )

    if not tools:
        return CheckResult(
            name="fix_install_tools",
            ok=True,
            severity="INFO",
            summary="No missing required tools to install",
            details={},
            remediation="",
        )

    # Build install command (DRY-RUN by default).
    cmds: list[list[str]] = []
    if pm == "apt":
        cmds.append(["sudo", "apt-get", "update"])
        cmds.append(["sudo", "apt-get", "install", "-y"] + tools)
    elif pm == "dnf":
        cmds.append(["sudo", "dnf", "install", "-y"] + tools)
    elif pm == "yum":
        cmds.append(["sudo", "yum", "install", "-y"] + tools)
    elif pm == "pacman":
        cmds.append(["sudo", "pacman", "-Sy", "--noconfirm"] + tools)
    elif pm == "zypper":
        cmds.append(["sudo", "zypper", "install", "-y"] + tools)
    elif pm == "brew":
        cmds.append(["brew", "install"] + tools)
    elif pm == "apk":
        cmds.append(["sudo", "apk", "add"] + tools)
    else:
        return CheckResult(
            name="fix_install_tools",
            ok=False,
            severity="WARN",
            summary=f"Unsupported package manager: {pm}",
            details={"tools": tools},
            remediation="Install tools manually.",
        )

    details: dict[str, Any] = {"pm": pm, "commands": cmds, "applied": False}

    if not apply:
        return CheckResult(
            name="fix_install_tools",
            ok=True,
            severity="INFO",
            summary=f"DRY-RUN: would install tools: {', '.join(tools)}",
            details=details,
            remediation="Re-run with --apply to actually install.",
        )

    # Apply installs.
    for c in cmds:
        rc, out, err = run_cmd(logger, c, timeout=max(timeout, 120))
        if rc != 0:
            return CheckResult(
                name="fix_install_tools",
                ok=False,
                severity="ERROR",
                summary=f"Failed installing tools via {pm}",
                details={**details, "failed_cmd": c, "rc": rc, "stdout": out[-1000:], "stderr": err[-1000:]},
                remediation="Inspect logs and re-run after resolving repo/package issues.",
            )

    details["applied"] = True
    return CheckResult(
        name="fix_install_tools",
        ok=True,
        severity="INFO",
        summary=f"Installed tools: {', '.join(tools)}",
        details=details,
        remediation="",
    )


def init_create_venv(logger: Logger, project_root: Path, venv_path: Path, apply: bool, timeout: int) -> CheckResult:
    if (venv_path / "bin" / "python").exists():
        return CheckResult(
            name="init_create_venv",
            ok=True,
            severity="INFO",
            summary="Venv already exists",
            details={"venv_path": str(venv_path)},
            remediation="",
        )

    cmd = [sys.executable, "-m", "venv", str(venv_path)]

    if not apply:
        return CheckResult(
            name="init_create_venv",
            ok=True,
            severity="INFO",
            summary="DRY-RUN: would create venv",
            details={"cmd": cmd, "venv_path": str(venv_path)},
            remediation="Re-run with --apply to actually create the venv.",
        )

    safe_mkdir(venv_path.parent)
    rc, out, err = run_cmd(logger, cmd, timeout=max(timeout, 60), cwd=project_root)
    ok = rc == 0
    sev = "INFO" if ok else "ERROR"

    if not ok:
        return CheckResult(
            name="init_create_venv",
            ok=False,
            severity=sev,
            summary="Failed to create venv",
            details={"cmd": cmd, "stdout": out, "stderr": err, "rc": rc},
            remediation="On Debian/Ubuntu you may need: sudo apt-get install -y python3-venv",
        )

    # Upgrade pip tooling (recommended).
    pip = venv_path / "bin" / "pip"
    rc2, out2, err2 = run_cmd(logger, [str(pip), "install", "-U", "pip", "setuptools", "wheel"], timeout=max(timeout, 120))

    return CheckResult(
        name="init_create_venv",
        ok=True,
        severity="INFO",
        summary="Created venv and upgraded pip tooling",
        details={"venv_path": str(venv_path), "pip_upgrade_rc": rc2, "stderr": err2[-500:]},
        remediation="",
    )


def init_install_requirements(
    logger: Logger,
    project_root: Path,
    venv_path: Path,
    requirements_path: Path | None,
    apply: bool,
    timeout: int,
) -> CheckResult:
    if not requirements_path or not requirements_path.exists():
        return CheckResult(
            name="init_install_requirements",
            ok=True,
            severity="INFO",
            summary="No requirements.txt found (nothing to install)",
            details={},
            remediation="",
        )

    pip = venv_path / "bin" / "pip"
    if not pip.exists():
        return CheckResult(
            name="init_install_requirements",
            ok=False,
            severity="ERROR",
            summary="Can't install requirements: venv pip not found",
            details={"venv_path": str(venv_path)},
            remediation="Create the venv first (run --mode init --apply).",
        )

    cmd = [str(pip), "install", "-r", str(requirements_path)]
    if not apply:
        return CheckResult(
            name="init_install_requirements",
            ok=True,
            severity="INFO",
            summary="DRY-RUN: would install requirements",
            details={"cmd": cmd},
            remediation="Re-run with --apply to actually install dependencies.",
        )

    rc, out, err = run_cmd(logger, cmd, timeout=max(timeout, 600), cwd=project_root)
    ok = rc == 0
    sev = "INFO" if ok else "ERROR"

    return CheckResult(
        name="init_install_requirements",
        ok=ok,
        severity=sev,
        summary=("Installed requirements" if ok else "Failed installing requirements"),
        details={"cmd": cmd, "stdout": out[-1000:], "stderr": err[-1000:], "rc": rc},
        remediation=(
            "If compilation errors occur, install build deps (e.g., python3-dev, build-essential, libpq-dev)."
            if not ok
            else ""
        ),
    )


# ------------------------------
# Orchestration
# ------------------------------


def build_report(
    logger: Logger,
    mode: str,
    project_root: Path,
    venv_path: Path,
    requirements_path: Path | None,
    compose_path: Path | None,
    timeout: int,
    apply: bool,
) -> DoctorReport:
    started = time.time()
    started_at = now_iso()

    checks: list[CheckResult] = []

    # Always run baseline checks.
    checks.append(check_runtime(logger))
    checks.append(check_network(logger, timeout=timeout))
    checks.append(check_tools(logger, timeout=timeout))
    checks.append(check_project_docs(logger, project_root))
    checks.append(check_venv(logger, project_root, venv_path, timeout=timeout))
    checks.append(check_requirements_installability(logger, project_root, venv_path, requirements_path, timeout=timeout))
    checks.append(check_postgres(logger, timeout=timeout))
    checks.append(check_docker_compose(logger, project_root, compose_path, timeout=timeout))

    # Mode-specific actions.
    if mode in {"fix", "init"}:
        # Install missing required tools.
        missing_required = [t for t in RECOMMENDED_TOOLS if which(t) is None]
        checks.append(fix_install_tools(logger, apply=apply, tools=missing_required, timeout=timeout))

    if mode == "init":
        checks.append(init_create_venv(logger, project_root, venv_path, apply=apply, timeout=timeout))
        checks.append(init_install_requirements(logger, project_root, venv_path, requirements_path, apply=apply, timeout=timeout))

    finished_at = now_iso()
    elapsed = round(time.time() - started, 3)

    return DoctorReport(
        started_at=started_at,
        finished_at=finished_at,
        elapsed_seconds=elapsed,
        project_root=str(project_root),
        mode=mode,
        checks=checks,
    )


def print_report(report: DoctorReport) -> None:
    # Summarize in a clean table.
    rows: list[tuple[str, str, str]] = []
    for c in report.checks:
        status = "OK" if c.ok else c.severity
        rows.append((c.name, status, c.summary))

    # Count by severity.
    errs = sum(1 for c in report.checks if c.severity == "ERROR")
    warns = sum(1 for c in report.checks if c.severity == "WARN")

    print("\n" + "=" * 80)
    print(f"CBW Doctor Report  |  mode={report.mode}  |  root={report.project_root}")
    print(f"Started: {report.started_at}")
    print(f"Finished: {report.finished_at}  |  Elapsed: {report.elapsed_seconds}s")
    print("=" * 80)
    print(format_table(rows))
    print("=" * 80)
    print(f"Summary: {errs} ERROR, {warns} WARN\n")

    # Print remediations for non-OK items.
    actionable = [c for c in report.checks if (not c.ok) or c.severity in {"WARN", "ERROR"}]
    if actionable:
        print("Fix suggestions:")
        for c in actionable:
            if c.remediation:
                print(f"- {c.name}: {c.remediation}")
        print()


def write_json_report(logger: Logger, report: DoctorReport, json_out: Path) -> None:
    safe_mkdir(json_out.parent)
    data = report.to_jsonable()
    with json_out.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Wrote JSON report: {json_out}")


def choose_default_json_out(project_root: Path) -> Path:
    # Prefer writing to project-local hidden folder; fallback to /tmp.
    try:
        p = project_root / ".cbw" / "doctor_report.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    except Exception:
        return Path("/tmp") / "CBW-doctor_report.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        prog=SCRIPT_NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """
            CBW Epstein/OpenDiscourse Doctor

            Examples
            --------
            # Safe validation (no changes)
            python3 cbw_epstein_doctor.py --mode doctor

            # Initialize venv + install requirements (WILL CHANGE SYSTEM) - requires --apply
            python3 cbw_epstein_doctor.py --mode init --apply

            # Attempt to install missing basic tools (WILL CHANGE SYSTEM) - requires --apply
            python3 cbw_epstein_doctor.py --mode fix --apply

            # Point at a specific project root
            python3 cbw_epstein_doctor.py --mode doctor --project-root ~/dev/opendiscourse
            """
        ).strip(),
    )

    parser.add_argument(
        "--mode",
        choices=["doctor", "validate", "init", "fix"],
        default="doctor",
        help="doctor/validate are non-destructive; init/fix can change your system when --apply is set",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually perform system changes (installs, venv creation). Without this, init/fix are DRY-RUN.",
    )
    parser.add_argument("--project-root", default=os.environ.get("PROJECT_ROOT"), help="Override project root")
    parser.add_argument("--venv", default=None, help="Venv path (default: <project>/.venv)")
    parser.add_argument("--requirements", default=None, help="Path to requirements.txt")
    parser.add_argument("--compose", default=None, help="Path to docker-compose.yml")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--json-out", default=None, help="Write JSON report to this path")
    parser.add_argument("--log", default=str(DEFAULT_LOG_PATH), help="Log path")

    args = parser.parse_args()

    log_path = Path(args.log).expanduser().resolve()
    logger = Logger(log_path)

    # Determine project root.
    if args.project_root:
        project_root = Path(args.project_root).expanduser().resolve()
    else:
        project_root = find_project_root(Path.cwd())

    # Determine venv path.
    venv_path = Path(args.venv).expanduser().resolve() if args.venv else (project_root / ".venv")

    # Determine requirements.
    requirements_path: Path | None
    if args.requirements:
        requirements_path = Path(args.requirements).expanduser().resolve()
    else:
        rp = project_root / "requirements.txt"
        requirements_path = rp if rp.exists() else None

    # Determine compose.
    compose_path: Path | None
    compose_path = Path(args.compose).expanduser().resolve() if args.compose else None

    logger.info(f"Starting {SCRIPT_NAME} mode={args.mode} apply={args.apply}")
    logger.info(f"Project root: {project_root}")
    logger.info(f"Log path: {log_path}")

    report = build_report(
        logger=logger,
        mode=args.mode,
        project_root=project_root,
        venv_path=venv_path,
        requirements_path=requirements_path,
        compose_path=compose_path,
        timeout=args.timeout_seconds,
        apply=args.apply,
    )

    print_report(report)

    json_out = Path(args.json_out).expanduser().resolve() if args.json_out else choose_default_json_out(project_root)
    try:
        write_json_report(logger, report, json_out)
    except Exception as e:
        logger.warn(f"Failed writing JSON report: {e}")

    # Non-zero if any ERROR checks.
    has_error = any(c.severity == "ERROR" for c in report.checks)
    return 2 if has_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
