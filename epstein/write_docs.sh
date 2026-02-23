import os, shutil, zipfile, pathlib, py_compile, subprocess, re

src_zip = pathlib.Path("/mnt/data/epstein_full_project_bundle_v4.zip")
work = pathlib.Path("/mnt/data/epstein_full_bundle_v5_work")
out_dir = pathlib.Path("/mnt/data/epstein_full_bundle_v5")

for p in [work, out_dir]:
    if p.exists():
        shutil.rmtree(p)
work.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(src_zip, "r") as z:
    z.extractall(work)
shutil.copytree(work, out_dir)

def write(rel, content, executable=False):
    p = out_dir / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8", newline="\n")
    if executable:
        os.chmod(p, 0o755)

# Issue templates + PR template
write(".github/ISSUE_TEMPLATE/00_bug_report.yml", """name: Bug report
description: Report a reproducible bug in the pipeline/stack/scripts
title: "bug: <short summary>"
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for filing a bug. Please include **repro steps** and **evidence**.
  - type: input
    id: environment
    attributes:
      label: Environment
      description: OS, Docker version, repo commit SHA
      placeholder: "Ubuntu 24.04, Docker 26.x, commit abc123"
    validations:
      required: true
  - type: textarea
    id: steps
    attributes:
      label: Steps to reproduce
      description: Commands run and order
      render: bash
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: Expected behavior
    validations:
      required: true
  - type: textarea
    id: actual
    attributes:
      label: Actual behavior / logs
      description: Paste relevant logs or point to files under epstein_artifacts/
      render: text
    validations:
      required: true
  - type: textarea
    id: artifacts
    attributes:
      label: Artifacts references
      description: Mention doc_id, run_id, failure entry (if applicable)
""")

write(".github/ISSUE_TEMPLATE/01_task.yml", """name: Task
description: Track a micro-goal or checklist item
title: "task: <micro-goal>"
labels: ["task"]
body:
  - type: textarea
    id: goal
    attributes:
      label: Goal
      description: What is being done and why?
    validations:
      required: true
  - type: textarea
    id: acceptance
    attributes:
      label: Acceptance tests
      description: Concrete tests proving completion (commands + expected outputs)
      render: bash
    validations:
      required: true
  - type: textarea
    id: notes
    attributes:
      label: Notes / risks
""")

write(".github/ISSUE_TEMPLATE/02_analysis_finding.yml", """name: Analysis finding
description: Evidence-bound note from semantic search / entity analysis
title: "finding: <topic>"
labels: ["finding"]
body:
  - type: markdown
    attributes:
      value: |
        **No claims without evidence.** Fill the evidence block for every finding.
  - type: textarea
    id: evidence
    attributes:
      label: Evidence block (required)
      description: Provide doc_id, chunk_id, offsets, source_url, excerpt, confidence
      render: yaml
      value: |
        finding:
          summary: ""
          doc_id: ""
          chunk_id: 0
          offsets: "0..0"
          source_url: ""
          excerpt: ""
          confidence: 0.0
    validations:
      required: true
  - type: textarea
    id: followups
    attributes:
      label: Follow-ups
      description: Next queries / cross-checks / corroboration steps
""")

write(".github/pull_request_template.md", """## Summary
What does this PR change?

## Tests / Validation
- [ ] `make doctor`
- [ ] `make demo` (or explain why not)
- [ ] lint/compile checks

## Risk / Rollback
How to revert safely?

## Notes
Anything an auditor should know?
""")

# Structured master tasks
write("tasks/master_tasks.yml", """version: 1
project: epstein-files-pipeline
principles:
  - auditability_over_speed
  - provenance_required
  - no_destructive_defaults

milestones:
  - id: M0
    title: Pre-flight & Architecture
    tasks:
      - id: M0-T01
        title: Verify repo hygiene
        description: Ensure no artifacts/secrets committed; .env is not tracked.
        tests:
          - cmd: "git status --ignored"
            expect: "No untracked artifacts committed; ignored paths visible."
      - id: M0-T02
        title: Run doctor checks
        description: Validate Docker, compose, ports, disk, volumes.
        tests:
          - cmd: "make doctor"
            expect: "Exit code 0 or 2 (warnings ok)."

  - id: M1
    title: Infrastructure Bootstrap
    tasks:
      - id: M1-T01
        title: Bring up Postgres + Qdrant
        description: Start docker compose services; ensure localhost-bound ports.
        tests:
          - cmd: "make bootstrap && make status"
            expect: "postgres and qdrant running."
      - id: M1-T02
        title: Validate schema exists
        description: doc_analysis schema and tables present.
        tests:
          - cmd: "docker exec -i pgvector_postgres psql -U analysis -d analysis -c \\"SELECT schema_name FROM information_schema.schemata WHERE schema_name='doc_analysis';\\""
            expect: "1 row"

  - id: M2
    title: Config & Demo Proof
    tasks:
      - id: M2-T01
        title: Run offline demo end-to-end
        description: Use bundled demo pdf to validate pipeline, db-load, embed, search.
        tests:
          - cmd: "make demo"
            expect: "Completes without error; chunks/entities > 0; Qdrant populated."
      - id: M2-T02
        title: Search returns results
        description: Validate semantic search returns evidence payload.
        tests:
          - cmd: "make search Q=\\"demo\\""
            expect: "At least 1 result with doc_id + chunk_id."

  - id: M3
    title: Real Ingestion (Controlled)
    tasks:
      - id: M3-T01
        title: Curate seed URLs and allowlist
        description: Select small initial set; document rationale.
        tests:
          - cmd: "jq . config.json"
            expect: "seed_urls non-empty; allow_domains set."
      - id: M3-T02
        title: Pipeline run on real sources
        description: Download/OCR/extract/chunk/NER with logs.
        tests:
          - cmd: "make pipeline-run"
            expect: "Artifacts populated in epstein_artifacts/."
      - id: M3-T03
        title: Load to Postgres and verify counts
        description: Ingest artifacts into Postgres.
        tests:
          - cmd: "make db-load && docker exec -i pgvector_postgres psql -U analysis -d analysis -c \\"SELECT COUNT(*) FROM doc_analysis.documents;\\""
            expect: ">0"

  - id: M4
    title: Analysis & Relationship Mining
    tasks:
      - id: M4-T01
        title: Establish query playbook
        description: Define initial query sets and how to corroborate.
        tests:
          - cmd: "test -f docs/ANALYSIS_PLAYBOOK.md && echo OK"
            expect: "OK"
      - id: M4-T02
        title: Produce 10 evidence-bound findings
        description: Use the finding issue template to record evidence-bound notes.
        tests:
          - cmd: "echo 'Use GitHub issues labeled finding OR docs/findings/'"
            expect: "10 findings exist"
""")

# Issue generation script (full)
write("scripts/gen_issues_from_tasks.py", """#!/usr/bin/env python3
# ==============================================================================
# Script Name: scripts/gen_issues_from_tasks.py
# Date: 2025-12-23
# Author: ChatGPT (for Blaine Winslow / cbwinslow)
# Summary:
#   Converts tasks/master_tasks.yml into:
#     - JSON (for GitHub Actions issue creation)
#     - Markdown checklist (human-friendly)
#
# Usage:
#   python scripts/gen_issues_from_tasks.py --in tasks/master_tasks.yml --out-json issues.json --out-md MASTER_TASKS.md
#
# Outputs:
#   issues.json: [{title, body, labels}, ...]
# ==============================================================================
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def die(msg: str) -> None:
    print(f"[gen_issues] ERROR: {msg}", file=sys.stderr)
    raise SystemExit(2)


def load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as ex:  # noqa: BLE001
        die(f"PyYAML not installed: {ex}. Install `pyyaml` or run inside the pipeline container.")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        die("Unexpected YAML structure")
    return data


def task_to_issue(milestone_id: str, milestone_title: str, task: Dict[str, Any]) -> Dict[str, Any]:
    tid = str(task.get("id", "TASK"))
    title = f"{tid}: {task.get('title', 'Untitled task')}"
    desc = str(task.get("description", "")).strip()

    tests = task.get("tests", []) or []
    test_lines: List[str] = []
    for t in tests:
        if not isinstance(t, dict):
            continue
        cmd = str(t.get("cmd", "")).strip()
        exp = str(t.get("expect", "")).strip()
        if cmd:
            test_lines.append(f"- `{cmd}`\\n  - Expected: {exp}")

    body = (
        f"## Milestone\\n- **{milestone_id} — {milestone_title}**\\n\\n"
        f"## Goal\\n{desc or '—'}\\n\\n"
        f"## Acceptance tests\\n{chr(10).join(test_lines) if test_lines else '- (add tests)'}\\n\\n"
        "## Notes\\n"
        "- Keep work non-destructive.\\n"
        "- Record evidence for findings (doc_id + chunk offsets + source_url).\\n"
    )

    labels = ["task", milestone_id]
    return {"title": title, "body": body, "labels": labels}


def export_markdown(data: Dict[str, Any]) -> str:
    proj = data.get("project", "project")
    lines: List[str] = []
    lines.append(f"# Master Tasks — {proj}\\n")
    lines.append("This file is generated from `tasks/master_tasks.yml`.\\n")
    for m in data.get("milestones", []) or []:
        mid = m.get("id", "M?")
        mtitle = m.get("title", "")
        lines.append(f"## {mid} — {mtitle}\\n")
        for t in m.get("tasks", []) or []:
            tid = t.get("id", "T?")
            ttitle = t.get("title", "")
            lines.append(f"- [ ] **{tid}** {ttitle}")
            desc = t.get("description")
            if desc:
                lines.append(f"  - {desc}")
            for test in t.get("tests", []) or []:
                cmd = test.get("cmd", "")
                exp = test.get("expect", "")
                if cmd:
                    lines.append(f"  - 🧪 `{cmd}`")
                if exp:
                    lines.append(f"    - Expected: {exp}")
        lines.append("")
    return "\\n".join(lines).rstrip() + "\\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="Path to tasks YAML")
    ap.add_argument("--out-json", default="", help="Write issues JSON to path")
    ap.add_argument("--out-md", default="", help="Write markdown checklist to path")
    args = ap.parse_args()

    data = load_yaml(Path(args.inp))

    issues: List[Dict[str, Any]] = []
    for m in data.get("milestones", []) or []:
        mid = str(m.get("id", "M?"))
        mtitle = str(m.get("title", ""))
        for t in m.get("tasks", []) or []:
            if not isinstance(t, dict):
                continue
            issues.append(task_to_issue(mid, mtitle, t))

    if args.out_json:
        Path(args.out_json).write_text(json.dumps(issues, indent=2) + "\\n", encoding="utf-8")
        print(f"✅ wrote {args.out_json} ({len(issues)} issues)")
    else:
        print(json.dumps(issues, indent=2))

    if args.out_md:
        Path(args.out_md).write_text(export_markdown(data), encoding="utf-8")
        print(f"✅ wrote {args.out_md}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
""", executable=True)

# Add workflow to create issues
write(".github/workflows/bootstrap_issues.yml", """name: Bootstrap Issues

on:
  workflow_dispatch:
    inputs:
      dry_run:
        description: "If true, do not create issues; just print payload"
        required: false
        default: "true"

permissions:
  contents: read
  issues: write

jobs:
  create-issues:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Generate issues JSON
        run: |
          set -euo pipefail
          python -m pip install --upgrade pip pyyaml
          python scripts/gen_issues_from_tasks.py --in tasks/master_tasks.yml --out-json /tmp/issues.json --out-md /tmp/MASTER_TASKS.md
          echo "Generated $(jq length /tmp/issues.json) issues"

      - name: Create issues (or dry run)
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const dry = (core.getInput('dry_run') || 'true').toLowerCase() === 'true';
            const issues = JSON.parse(fs.readFileSync('/tmp/issues.json','utf8'));
            core.info(`dry_run=${dry} issues=${issues.length}`);
            for (const it of issues) {
              if (dry) { core.info(`[DRY] ${it.title}`); continue; }
              const res = await github.rest.issues.create({
                owner: context.repo.owner,
                repo: context.repo.repo,
                title: it.title,
                body: it.body,
                labels: it.labels,
              });
              core.info(`Created: ${res.data.number} ${it.title}`);
            }
""")

# Release workflow + docs already exist in v4; keep as-is.

# Add methodology/troubleshooting/analysis playbook docs (if not already)
def ensure_doc(rel, content):
    p = out_dir / rel
    if not p.exists():
        write(rel, content)

ensure_doc("docs/METHODOLOGY.md", """# Methodology

This repo is designed for **provenance-safe document analysis**.

## Golden rules
1. No claims without evidence (doc_id, chunk_id, offsets, source_url).
2. Corroborate across multiple documents/chunks.
3. Separate extraction from interpretation.
4. Start small; expand scope deliberately.

## Workflow
1. Semantic search → candidate passages.
2. Extract entities + context.
3. Verify co-occurrence across sources.
4. Record evidence-bound notes (Finding issues or docs/findings/*).
""")

ensure_doc("docs/TROUBLESHOOTING.md", """# Troubleshooting

Run:
- `make doctor`
- `make status`
- `docker compose logs -n 200 qdrant postgres`

Common issues:
- Port collisions: adjust env ports.
- OCR failures: inspect failures.jsonl and re-run.
- Empty search: ensure chunks > 0 and embed ran; verify Qdrant collection.
""")

ensure_doc("docs/ANALYSIS_PLAYBOOK.md", """# Analysis Playbook

1. Start with high-signal queries (logistics, locations, intermediaries).
2. Convert results into evidence-bound notes.
3. Corroborate relationship claims with 2+ docs or 3+ distant chunks.
4. Maintain a counter-evidence list to avoid confirmation bias.
""")

# Update docs index
idx_path = out_dir/"docs/INDEX.md"
idx = idx_path.read_text(encoding="utf-8")
for entry in ["docs/METHODOLOGY.md", "docs/TROUBLESHOOTING.md", "docs/ANALYSIS_PLAYBOOK.md", "tasks/master_tasks.yml"]:
    if entry not in idx:
        idx = idx.strip() + f"\n- {entry}\n"
idx_path.write_text(idx.strip()+"\n", encoding="utf-8", newline="\n")

# Add Makefile target issues-export
mk_path = out_dir/"Makefile"
mk = mk_path.read_text(encoding="utf-8")
if "issues-export" not in mk:
    mk += """
.PHONY: issues-export
issues-export:
\t@$(COMPOSE) -f $(COMPOSE_FILE) --profile pipeline run --rm pipeline scripts/gen_issues_from_tasks.py --in tasks/master_tasks.yml --out-json ./issues.json --out-md ./MASTER_TASKS.md
\t@echo "✅ wrote ./issues.json and ./MASTER_TASKS.md"
"""
    mk_path.write_text(mk, encoding="utf-8", newline="\n")

# Ensure PyYAML is present in pyproject dependencies
pyproject_path = out_dir/"pyproject.toml"
pyproject = pyproject_path.read_text(encoding="utf-8")
if re.search(r'PyYAML', pyproject, re.IGNORECASE) is None:
    # Insert before closing bracket of dependencies list in [project]
    pyproject = re.sub(r'(\[project\][\s\S]*?dependencies\s*=\s*\[\s*)([\s\S]*?)(\n\])',
                       lambda m: m.group(1) + m.group(2).rstrip() + '\n  "PyYAML>=6.0",' + m.group(3),
                       pyproject, count=1)
    pyproject_path.write_text(pyproject, encoding="utf-8", newline="\n")

# Validate python compile
py_compile.compile(str(out_dir/"scripts/gen_issues_from_tasks.py"), doraise=True)
py_compile.compile(str(out_dir/"scripts/doctor.py"), doraise=True)

# Basic bash syntax checks
subprocess.run(["bash","-n",str(out_dir/"scripts/bootstrap.sh")], check=True)
subprocess.run(["bash","-n",str(out_dir/"vector_db_bootstrap.sh")], check=True)

# Zip v5
zip_path = pathlib.Path("/mnt/data/epstein_full_project_bundle_v5.zip")
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for p in out_dir.rglob("*"):
        if p.is_file():
            z.write(p, p.relative_to(out_dir).as_posix())

print(zip_path.as_posix())
print("files:", len([p for p in out_dir.rglob("*") if p.is_file()]))

