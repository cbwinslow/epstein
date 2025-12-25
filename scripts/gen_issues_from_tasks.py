#!/usr/bin/env python3
"""Generate GitHub issues from tasks/master_tasks.yml

Usage:
  python scripts/gen_issues_from_tasks.py --in tasks/master_tasks.yml --out-json ./issues.json [--dry-run] [--create-issues]

By default it writes a JSON file with issues and a human-readable MASTER_TASKS.md. With --create-issues it will attempt to use `gh` CLI to create issues (dry-run default).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except Exception:
    print("PyYAML not installed. Install it with `uv add PyYAML` or run in the dev env.")
    raise


def load_tasks(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def tasks_to_issues(tasks: dict) -> list[dict]:
    issues = []
    for m in tasks.get("milestones", []):
        for t in m.get("tasks", []):
            title = f"task: {t.get('title')}"
            body = f"{t.get('description', '')}\n\n---\nMilestone: {m.get('title')}\nTask ID: {t.get('id')}"
            labels = ["task", m.get('id').lower()]
            issues.append({"title": title, "body": body, "labels": labels})
    return issues


def write_outputs(issues: list[dict], md_path: Path, json_path: Path) -> None:
    # Write issues JSON
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(issues, f, indent=2)

    # Write simple MASTER_TASKS.md
    lines = ["# MASTER_TASKS\n\n"]
    for i in issues:
        lines.append(f"- **{i['title']}**  \n  {i['body']}  \n  labels: {', '.join(i['labels'])}\n\n")
    md_path.write_text("".join(lines), encoding="utf-8")


def create_github_issue(issue: dict) -> bool:
    # Use `gh issue create --title <title> --body <body> --label <labels>`
    labels = ",".join(issue.get("labels", []))
    cmd = ["gh", "issue", "create", "--title", issue["title"], "--body", issue["body"], "--label", labels]
    try:
        subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        print(f"Error creating issue: {e}")
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="infile", default="tasks/master_tasks.yml")
    parser.add_argument("--out-json", dest="outjson", default="./issues.json")
    parser.add_argument("--out-md", dest="outmd", default="./MASTER_TASKS.md")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=False)
    parser.add_argument("--create-issues", dest="create_issues", action="store_true", default=False)

    args = parser.parse_args(argv)

    p = Path(args.infile)
    if not p.exists():
        print(f"Tasks file not found: {p}")
        return 2

    tasks = load_tasks(p)
    issues = tasks_to_issues(tasks)

    write_outputs(issues, Path(args.outmd), Path(args.outjson))
    print(f"Wrote {args.outjson} and {args.outmd}")

    if args.create_issues:
        if args.dry_run:
            print("Dry run - no issues will be created. Use --no-dry-run --create-issues to create.")
        else:
            for i in issues:
                ok = create_github_issue(i)
                print(f"Created: {i['title']} - {ok}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
