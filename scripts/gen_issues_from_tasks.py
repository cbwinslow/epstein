#!/usr/bin/env python3
"""Generate GitHub issues from tasks/master_tasks.yml

Usage:
  python scripts/gen_issues_from_tasks.py --in tasks/master_tasks.yml --out-json ./issues.json [--dry-run] [--create-issues]

By default it writes a JSON file with issues and a human-readable MASTER_TASKS.md. With --create-issues it will attempt to use `gh` CLI to create issues (dry-run default).
"""
from __future__ import annotations

import argparse
import json
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
        milestone_id = m.get('id', '').lower()
        milestone_title = m.get('title', '')

        for t in m.get("tasks", []):
            task_id = t.get('id', '')
            title = f"task: {t.get('title')}"

            # Build body with all available metadata
            body_parts = [t.get('description', '')]

            # Add priority if present
            priority = t.get('priority', '')
            if priority:
                body_parts.append(f"\n**Priority**: {priority}")

            # Add tests if present
            tests = t.get('tests', [])
            if tests:
                body_parts.append("\n\n**Tests**:")
                for test in tests:
                    cmd = test.get('cmd', '')
                    expect = test.get('expect', '')
                    body_parts.append(f"- Command: `{cmd}`")
                    body_parts.append(f"  - Expected: {expect}")

            # Add milestone and task ID footer
            body_parts.append(f"\n\n---\n**Milestone**: {milestone_title}\n**Task ID**: {task_id}")

            body = "\n".join(body_parts)

            # Build labels list
            labels = ["task", milestone_id]

            # Add custom labels from task if present
            custom_labels = t.get('labels', [])
            if custom_labels:
                labels.extend(custom_labels)

            # Add priority as label if present
            if priority:
                labels.append(priority.lower())

            issues.append({
                "title": title,
                "body": body,
                "labels": labels,
                "milestone_id": milestone_id,
                "task_id": task_id
            })

    return issues


def write_outputs(issues: list[dict], md_path: Path, json_path: Path) -> None:
    # Write issues JSON
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(issues, f, indent=2)

    # Write enhanced MASTER_TASKS.md with better formatting
    lines = ["# MASTER_TASKS\n\n"]
    lines.append(f"**Generated**: {Path(json_path).name}\n")
    lines.append(f"**Total Tasks**: {len(issues)}\n\n")

    # Group by milestone
    current_milestone = None
    for i in issues:
        milestone = i.get('milestone_id', '')
        if milestone != current_milestone:
            lines.append(f"\n## Milestone: {milestone.upper()}\n\n")
            current_milestone = milestone

        lines.append(f"### {i['title']}\n\n")
        lines.append(f"{i['body']}\n\n")
        lines.append(f"**Labels**: {', '.join(i['labels'])}\n\n")
        lines.append("---\n\n")

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
