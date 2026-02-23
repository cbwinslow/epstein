# Storage Strategy

## Core Rule
Binary documents do NOT live in PostgreSQL.

PostgreSQL stores metadata, relationships, hashes, extracted text, and analysis artifacts.
Raw files live on disk or object storage.

## Why
- Prevent DB bloat
- Faster backups
- Easier lifecycle management
- OCR and reprocessing flexibility

## Filesystem Layout (Proposed)

documents/
  └── govinfo/
      └── BILL/
          └── 118/
              └── hr/
                  └── hr1234/
                      ├── original.pdf
                      ├── sha256.txt
                      └── ocr.txt

## PostgreSQL Stores
- document_id (UUID)
- source
- canonical_type
- file_path
- sha256
- extracted_text
- ocr_confidence
- ingestion_run_id
