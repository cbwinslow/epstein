# Patch Scripts Write-up

This document describes helper scripts added for repair/validation and PR preparation.

## scripts/repair_project.py

**Purpose:** Run a best-effort validation suite (lint + tests + dependency checks) and write a JSON report.

**Key behaviors:**
- Runs `ruff check`, `pytest`, and `pip check` (prefers `uv run` if available).
- Supports optional auto-fix for ruff via `--fix`.
- Emits a report JSON to `./logs/repair_report_<timestamp>.json`.
- Exits non-zero if any check fails.

**Usage:**

```bash
python scripts/repair_project.py
python scripts/repair_project.py --fix
python scripts/repair_project.py --pytest-args "-q tests/test_mcp_server.py"
```

## scripts/prepare_patch_pr.sh

**Purpose:** Provide a structured sequence to validate changes and prepare a PR.

**Key behaviors:**
- Ensures the working tree is clean before packaging.
- Runs `scripts/repair_project.py` for validation.
- Emits reminders for PR metadata.

**Usage:**

```bash
bash scripts/prepare_patch_pr.sh
```
