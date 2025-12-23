# Database Schema Overview

## Core Tables
- ingestion_runs
- sources
- documents
- document_versions
- extracted_text
- entities
- relationships

## Naming Conventions
- snake_case
- singular table names
- explicit foreign keys

## UUIDs
All primary keys use UUIDv7 (preferred) or UUIDv4.

## Schema Status: ✅ COMPLETED

### Implementation Details
- **Complete schema implemented** in `db/schema.sql`
- **Migration system** created with `db/migrate.py`
- **Initial migration** available as `db/migrations/001_initial_schema.sql`
- **Performance indexes** included for all major query patterns
- **Data validation** through constraints and check constraints
- **Automated triggers** for timestamp management
- **Views** for common query patterns

### Tables Implemented
1. **sources** - Document source tracking (govinfo.gov, uploads, etc.)
2. **ingestion_runs** - Processing run tracking with status and metrics
3. **documents** - Core document metadata with deduplication
4. **document_versions** - Document version history
5. **extracted_text** - OCR and native text extraction results
6. **entities** - Named entities from NER processing
7. **relationships** - Entity relationships and connections
8. **schema_migrations** - Migration tracking

### Key Features
- UUIDv7 primary keys for time-ordered uniqueness
- Comprehensive indexing strategy for performance
- Full-text search capabilities on extracted text
- JSONB metadata storage for flexibility
- Foreign key constraints with cascade deletes
- Automatic timestamp updates via triggers
- Check constraints for data validation
- Optimized views for common queries

### Usage
```bash
# Check migration status
python db/migrate.py status

# Apply migrations
python db/migrate.py up

# Create new migration
python db/migrate.py create "add_new_feature"
```

This file documents intent; actual schema lives in /db.
