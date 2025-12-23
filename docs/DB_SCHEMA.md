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

This file documents intent; actual schema lives in /db.
