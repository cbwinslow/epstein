# OCR and Parsing

## When OCR Is Used
- PDF has no embedded text (or very low text size)
- OCR confidence below threshold
- Image-only documents (JPG/PNG/TIFF)

## Tools
- Tesseract
- OCRmyPDF

## Stored Outputs
- OCR PDFs (`epstein_project/ocr/*.ocr.pdf`)
- Fallback text (`epstein_project/ocr_fallback/*.txt`)
- Full extracted text (`epstein_project/text/*.txt`)
- Page-level chunks (`epstein_project/chunks/*.chunks.jsonl`)
- Status records (`epstein_project/processing_status.jsonl`)
