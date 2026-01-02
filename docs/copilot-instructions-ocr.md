# Copilot (Agent) Instructions: OCR Debugging Specialist

Purpose
- This instruction set directs Copilot-style agents to triage, debug, and fix OCR issues in the Epstein pipeline.

High-level behavior
- Run canary tests before major runs and only after pulling updated docs.
- Gather detailed logs and artifacts for failing documents, including saved page images (`epstein_project/logs/ocr_debug_pages`), `processing_status.jsonl`, and `epstein_project/logs/ocr/*.ocr.log`.
- Attempt automated remediation in increasing order of intrusion:
  1. Retry `ocrmypdf` with increased timeout.
  2. Run fallback (`pdftoppm -png` -> `tesseract` with multiple PSMs) and compare character counts.
  3. Run image preprocessing (grayscale, histogram equalization, Otsu threshold) and re-run tesseract.
  4. If none work, open an issue with attached page image and log excerpts for manual review.

Actions for each failing doc
1. Identify doc in `processing_status.jsonl` and fetch `input_pdf` and log files.
2. Run `pdftotext` to determine `before_chars`.
3. Rerun `ocrmypdf` with `--force --output-type pdf` and capture log; if `ocrmypdf` fails due to flags, adjust flags.
4. If `after_chars < 200`, run fallback with `pdftoppm -r 300 -png` then `tesseract` with modes [3,6,11] and pick best.
5. If fallback <200: apply image preprocessing and re-run tesseract.
6. If fallback > original and >= 200: backup original text and replace; record replaced_text = true.

Reporting
- Generate a canary report (CSV + JSON) with pass rates, before/after char deltas, and list of replaced docs.
- Post summary to the `#epstein-ocr` channel and attach 3 sample diffs (before vs after) for manual inspection.

Safety checks
- Never overwrite original files without backup (`epstein_project/text_pre_ocr_fix`).
- Keep the number of concurrent jobs low (2–4) to avoid overwhelming resources.
- Respect environment variables `EPSTEIN_ROOT_OVERRIDE` and `EPSTEIN_OCR_DEBUG`.

When to escalate
- If >10% of canary docs fail to reach baseline after automated remediation, open an issue and tag `@maintainers` with findings.
