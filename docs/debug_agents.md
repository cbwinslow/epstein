# Debug Agent Playbook

Purpose
- Agents specialized in debugging, triage, and automated fixes for the OCR pipeline.

Responsibilities
- Run canary tests before and after changes.
- Gather logs, stack traces, and `processing_status.jsonl` entries.
- Attempt automated fixes (rerun with increased timeout, run fallback), and create issues when manual intervention is needed.

Checklist for each failing doc
1. Verify file exists and manifest path is correct.
2. Check `pdftotext` before chars; if non-zero, assess why conversion lost text.
3. Run `ocrmypdf` with `--deskew --force` and capture log.
4. If `ocrmypdf` fails, run fallback (`pdftoppm` -> `tesseract`) and compare results.
5. If fallback is better, back up and replace original text file. Otherwise attach logs to an issue.

Automation ideas
- `pipeline_monitor` agent watches `processing_status.jsonl` and raises alerts when error rates exceed thresholds.
- Automated PR templates created with problem summary and suggested patch when 1) fix was automated or 2) requires manual code changes.
