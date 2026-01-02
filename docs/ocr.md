# OCR Procedures

## Scope
Repeatable bulk OCR for PDFs and images in `epstein_project/`, producing searchable PDFs plus extracted text. Primary OCR uses `ocrmypdf`; fallback uses `pdftoppm` + `tesseract`.

## Prereqs
- System tools: `ocrmypdf`, `tesseract-ocr`, `poppler-utils`, `ghostscript`, `qpdf`.
- Optional: `jbig2`/`jbig2enc` for PDF optimization. If it is missing or not executable, run with `--optimize 0`.
- Verify tools:
  - `ocrmypdf --version`
  - `tesseract --version`
  - `pdftoppm -h`

## Inputs and outputs
- Input index: `epstein_project/manifest.jsonl` (must include `sha256`, `path`, `bytes`).
- Candidate text: `epstein_project/text/*.txt` (used to select low-text PDFs).
- Outputs:
  - OCR PDFs: `epstein_project/ocr/*.ocr.pdf`
  - Fallback text: `epstein_project/ocr_fallback/*.txt`
  - Replaced text (backups): `epstein_project/text_pre_ocr_fix/*.txt`
  - Logs: `epstein_project/logs/ocr/<sha>.ocr.log`
  - Status: `epstein_project/processing_status.jsonl` (append-only)

## Procedure (PDFs)
1) Canary run (10 files):
```
python3 scripts/ocr_runner.py --batch 10 --min-bytes 300000 --max-text-bytes 500
```
2) Bulk run (repeat in batches):
```
python3 scripts/ocr_runner.py --batch 200 --min-bytes 300000 --max-text-bytes 500
```
3) If `jbig2` is missing or permissioned incorrectly:
```
python3 scripts/ocr_runner.py --batch 200 --min-bytes 300000 --max-text-bytes 500 --optimize 0
```

Notes:
- The runner defaults to `--skip-text` and `--rotate-pages`; use `--no-skip-text` or `--no-rotate-pages` to disable.
- The runner automatically falls back to `pdftoppm` + `tesseract` when OCR output is too small.

## Procedure (images)
For standalone images (JPG/PNG/TIFF), OCR with Tesseract directly or convert to PDF first.

Direct OCR:
```
tesseract input.tif stdout -l eng --oem 1 --psm 6 > output.txt
```

Convert to PDF then OCR:
```
img2pdf input.jpg -o input.pdf
python3 scripts/ocr_runner.py --batch 1 --min-bytes 1 --max-text-bytes 500 --no-skip-text
```

## QA and acceptance
- Check `processing_status.jsonl` for `ocr_status`, `fallback_status`, and `after_chars`.
- Spot-check a few outputs:
  - `pdftotext -layout -enc UTF-8 epstein_project/ocr/<sha>.ocr.pdf - | head`
- If >10% of canary docs are `ocr_empty`, `fallback_empty`, or `ocr_failed`, pause and investigate.
 - Run the quality gate report:
   - `python3 scripts/ocr_quality_gate.py --status-file epstein_project/processing_status.jsonl --max-fail-rate 0.1 --min-total 10`

## Repeatability and resume
- The runner is idempotent and append-only; it only targets low-text PDFs and never deletes originals.
- You can re-run with the same thresholds to resume after interruption.

## Troubleshooting
- If `ocrmypdf` fails during JBIG2 optimization, ensure `jbig2`/`jbig2enc` is on PATH and executable, or use `--optimize 0`.
- For heavy scans, keep concurrency low (2-4 parallel processes) and watch disk usage.
