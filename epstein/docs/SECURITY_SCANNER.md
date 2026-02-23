Pre-commit Scanner & Fallback

The repository uses a secret scanning helper invoked by a pre-commit hook to prevent accidental commits of secrets.

If you see a pre-commit error referring to `$HOME/.bash_functions.d/scan_secrets.sh` being missing, a minimal fallback scanner was added that performs heuristic checks and writes a short report to `$HOME/.bash_functions.d/deploy_scan_report.txt`.

Local test
- Run `./scripts/test_precommit_scan.sh [files...]` to test the scanner (defaults to `README.md`).

Notes
- Preferred: install the official scanner provided by your org and ensure it places a `scan_secrets.sh` script under `$HOME/.bash_functions.d`.
- The fallback is intentionally minimal and non-blocking; it flags obvious items and exits non-zero when it finds matches.
- If the fallback reports issues, review the referenced report file and remove or rotate any secrets before committing.
