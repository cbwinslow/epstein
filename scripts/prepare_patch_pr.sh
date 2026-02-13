#!/usr/bin/env bash
set -euo pipefail

if ! command -v git >/dev/null 2>&1; then
  echo "git is required" >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree is not clean. Commit or stash changes before preparing PR." >&2
  git status --short
  exit 1
fi

echo "Running repair/validation suite..."
python scripts/repair_project.py || {
  echo "Validation failed. Review logs before creating PR." >&2
  exit 1
}

echo "Validation complete."
echo "Next steps:"
echo "  1) Ensure PR title/body reflect changes."
echo "  2) Capture any additional tests in the PR description."
echo "  3) Create the PR via your automation tool."
