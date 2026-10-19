-- ============================================================================
-- File: db/migrations/001_initial_schema.sql
-- Date: 2025-12-23
-- Purpose: Initial database schema migration
-- Description: Creates all core tables, indexes, triggers, and views
-- ============================================================================

-- This migration creates the complete initial schema
-- Run with: psql -d epstein_db -f db/migrations/001_initial_schema.sql

\i ../schema.sql

-- Record migration completion
INSERT INTO schema_migrations (version, description, executed_at)
VALUES ('001_initial', 'Initial schema creation', NOW())
ON CONFLICT (version) DO NOTHING;
