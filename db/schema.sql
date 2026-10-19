-- ============================================================================
-- File: db/schema.sql
-- Date: 2025-12-23
-- Purpose: Canonical database schema for Epstein Document Analysis Pipeline
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Sources table - tracks document sources (govinfo.gov, uploads, etc.)
CREATE TABLE sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    name VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(100) NOT NULL,
    description TEXT,
    config JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ingestion runs table - tracks processing runs
CREATE TABLE ingestion_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    files_processed INTEGER DEFAULT 0,
    files_total INTEGER DEFAULT 0,
    bytes_processed BIGINT DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    config JSONB,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Documents table - core document metadata
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    ingestion_run_id UUID NOT NULL REFERENCES ingestion_runs(id) ON DELETE CASCADE,
    external_id VARCHAR(500),
    title TEXT,
    description TEXT,
    file_path VARCHAR(1000) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    file_hash VARCHAR(128) NOT NULL,
    mime_type VARCHAR(100),
    language VARCHAR(10),
    page_count INTEGER,
    is_image_only BOOLEAN DEFAULT FALSE,
    ocr_required BOOLEAN DEFAULT FALSE,
    ocr_confidence DECIMAL(5,2),
    processing_status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT documents_file_hash_unique UNIQUE (file_hash),
    CONSTRAINT documents_external_id_source_unique UNIQUE (external_id, source_id)
);

-- Document versions table - track version history
CREATE TABLE document_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_hash VARCHAR(128) NOT NULL,
    file_size BIGINT NOT NULL,
    change_description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT document_versions_unique UNIQUE (document_id, version_number)
);

-- Extracted text table - OCR and text extraction results
CREATE TABLE extracted_text (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER,
    text_content TEXT NOT NULL,
    extraction_method VARCHAR(50) NOT NULL,
    confidence_score DECIMAL(5,2),
    language VARCHAR(10),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT extracted_text_unique UNIQUE (document_id, page_number)
);

-- Entities table - named entities extracted from documents
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    extracted_text_id UUID REFERENCES extracted_text(id) ON DELETE CASCADE,
    entity_type VARCHAR(100) NOT NULL,
    entity_text TEXT NOT NULL,
    confidence_score DECIMAL(5,2),
    start_position INTEGER,
    end_position INTEGER,
    page_number INTEGER,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Relationships table - relationships between entities
CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    source_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,
    confidence_score DECIMAL(5,2),
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT relationships_unique UNIQUE (source_entity_id, target_entity_id, relationship_type),
    CONSTRAINT relationships_no_self_reference CHECK (source_entity_id != target_entity_id)
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Sources indexes
CREATE INDEX idx_sources_type ON sources(type);
CREATE INDEX idx_sources_name ON sources(name);

-- Ingestion runs indexes
CREATE INDEX idx_ingestion_runs_source_id ON ingestion_runs(source_id);
CREATE INDEX idx_ingestion_runs_status ON ingestion_runs(status);
CREATE INDEX idx_ingestion_runs_created_at ON ingestion_runs(created_at);

-- Documents indexes
CREATE INDEX idx_documents_source_id ON documents(source_id);
CREATE INDEX idx_documents_ingestion_run_id ON documents(ingestion_run_id);
CREATE INDEX idx_documents_file_hash ON documents(file_hash);
CREATE INDEX idx_documents_processing_status ON documents(processing_status);
CREATE INDEX idx_documents_created_at ON documents(created_at);
CREATE INDEX idx_documents_metadata_gin ON documents USING GIN(metadata);

-- Document versions indexes
CREATE INDEX idx_document_versions_document_id ON document_versions(document_id);

-- Extracted text indexes
CREATE INDEX idx_extracted_text_document_id ON extracted_text(document_id);
CREATE INDEX idx_extracted_text_document_id_page ON extracted_text(document_id, page_number);
CREATE INDEX idx_extracted_text_confidence ON extracted_text(confidence_score);
CREATE INDEX idx_extracted_text_text_gin ON extracted_text USING GIN(to_tsvector('english', text_content));

-- Entities indexes
CREATE INDEX idx_entities_document_id ON entities(document_id);
CREATE INDEX idx_entities_extracted_text_id ON entities(extracted_text_id);
CREATE INDEX idx_entities_entity_type ON entities(entity_type);
CREATE INDEX idx_entities_confidence_score ON entities(confidence_score);
CREATE INDEX idx_entities_metadata_gin ON entities USING GIN(metadata);

-- Relationships indexes
CREATE INDEX idx_relationships_source_entity ON relationships(source_entity_id);
CREATE INDEX idx_relationships_target_entity ON relationships(target_entity_id);
CREATE INDEX idx_relationships_type ON relationships(relationship_type);

-- ============================================================================
-- TRIGGERS FOR AUTOMATIC TIMESTAMP UPDATES
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to tables with updated_at columns
CREATE TRIGGER update_sources_updated_at BEFORE UPDATE ON sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ingestion_runs_updated_at BEFORE UPDATE ON ingestion_runs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_extracted_text_updated_at BEFORE UPDATE ON extracted_text
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_entities_updated_at BEFORE UPDATE ON entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_relationships_updated_at BEFORE UPDATE ON relationships
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Document summary view
CREATE VIEW document_summary AS
SELECT
    d.id,
    d.title,
    d.file_name,
    d.file_size,
    d.processing_status,
    d.ocr_confidence,
    d.created_at,
    s.name as source_name,
    ir.status as ingestion_status,
    COUNT(DISTINCT et.id) as text_extracted_pages,
    COUNT(DISTINCT e.id) as entity_count
FROM documents d
JOIN sources s ON d.source_id = s.id
JOIN ingestion_runs ir ON d.ingestion_run_id = ir.id
LEFT JOIN extracted_text et ON d.id = et.document_id
LEFT JOIN entities e ON d.id = e.document_id
GROUP BY d.id, s.name, ir.status;

-- Entity summary view
CREATE VIEW entity_summary AS
SELECT
    e.id,
    e.entity_type,
    e.entity_text,
    e.confidence_score,
    d.title as document_title,
    d.file_name,
    e.created_at
FROM entities e
JOIN documents d ON e.document_id = d.id
WHERE e.confidence_score >= 0.5;

-- ============================================================================
-- CONSTRAINTS AND VALIDATIONS
-- ============================================================================

-- Check constraints for valid status values
ALTER TABLE ingestion_runs ADD CONSTRAINT ingestion_runs_status_check
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'));

ALTER TABLE documents ADD CONSTRAINT documents_processing_status_check
    CHECK (processing_status IN ('pending', 'processing', 'ocr_required', 'text_extracted', 'entity_extracted', 'completed', 'failed'));

ALTER TABLE extracted_text ADD CONSTRAINT extracted_text_method_check
    CHECK (extraction_method IN ('native', 'ocr', 'manual'));

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE sources IS 'Tracks document sources and their configurations';
COMMENT ON TABLE ingestion_runs IS 'Tracks individual document processing runs';
COMMENT ON TABLE documents IS 'Core metadata for all processed documents';
COMMENT ON TABLE document_versions IS 'Version history for document changes';
COMMENT ON TABLE extracted_text IS 'Text content extracted from documents via OCR or native extraction';
COMMENT ON TABLE entities IS 'Named entities extracted from document text';
COMMENT ON TABLE relationships IS 'Relationships between extracted entities';

COMMENT ON COLUMN documents.file_hash IS 'SHA-256 hash of file contents for deduplication';
COMMENT ON COLUMN documents.ocr_confidence IS 'Confidence score from OCR processing (0-100)';
COMMENT ON COLUMN entities.confidence_score IS 'Confidence score from NER processing (0-100)';
COMMENT ON COLUMN relationships.confidence_score IS 'Confidence score for relationship validity (0-100)';
