# OCR Debugging Guide

When OCR fails or produces poor text, follow this checklist:

1. Reproduce locally
   - Run `python3 scripts/ocr_runner.py --batch 1 --min-bytes 1` for a failing doc.
   - Check per-file log: `epstein_project/logs/ocr/<sha>.ocr.log` and `epstein_project/processing_status.jsonl`.

2. Common failure modes
   - input_missing: path not found in manifest; ensure manifest paths are correct.
   - ocr_timeout: increase `--timeout` and consider running single-file retry.
   - ocr_empty: `ocrmypdf` completed but produced no text; try fallback tesseract.
   - fallback_empty: tesseract returned no text; check page images and contrast.
   - JBIG2 errors: ensure `jbig2` is installed and on PATH (`~/.local/bin/jbig2`).

3. Tools
   - `pdftotext -layout -enc UTF-8 file.pdf -` to check existing text.
   - `pdftoppm -r 300 file.pdf prefix` + `tesseract prefix-1.png stdout` for per-page diagnostics.

4. When to replace original text
   - Runner will replace `epstein_project/text/<sha>.txt` if fallback produces more characters (>= 200) than original.
   - Backups are saved in `epstein_project/text_pre_ocr_fix/`.

5. Logging & metrics
   - Keep `processing_status.jsonl` entries: before_chars, after_chars, fallback_chars, status.
   - Run canary and compare pass rates; if >10% failures, halt and investigate.

6. Escalation
   - If a large corpus shows systemic ocr_empty with high-resolution images, increase DPI and test `--image-dpi` flags.
   - Consider specialized tesseract configs for poor contrast documents (PSM, OEM, language models).
