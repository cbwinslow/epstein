#!/usr/bin/env bash
# Simple test harness to exercise the configured secrets scanner.
set -euo pipefail
SCANNER="$HOME/.bash_functions.d/scan_secrets.sh"
REPORT="$HOME/.bash_functions.d/deploy_scan_report.txt"

if [[ ! -x "$SCANNER" ]]; then
  echo "Scanner not found: $SCANNER" >&2
  exit 1
fi

# Accept one or more files to test, or default to README.md
FILES=("${@:-README.md}")
printf "%s\n" "${FILES[@]}" | "$SCANNER" - "$REPORT"
rc=$?
if [[ $rc -eq 0 ]]; then
  echo "Scanner exit 0 — no obvious secrets found. Report: $REPORT"
else
  echo "Scanner exit $rc — see report: $REPORT" >&2
fi
exit $rc
