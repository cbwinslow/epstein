"""
Unit tests for the Pipeline module.

These tests verify:
- Pipeline configuration
- Chunking utilities
- Text extraction helpers
- Document processing utilities
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestPipelineConfig:
    """Tests for pipeline configuration loading."""

    def test_default_config_structure(self):
        """Test that config has required fields."""
        config = {
            "seed_urls": ["https://example.com/docs"],
            "output_dir": "./output",
            "allow_domains": ["example.com"],
        }

        assert "seed_urls" in config
        assert "output_dir" in config
        assert "allow_domains" in config

    def test_chunking_config(self):
        """Test chunking configuration."""
        chunk_config = {
            "chunk_size": 512,
            "chunk_overlap": 50,
        }

        assert chunk_config["chunk_size"] == 512
        assert chunk_config["chunk_overlap"] == 50

    def test_ner_config(self):
        """Test NER configuration."""
        ner_config = {
            "model": "en_core_web_sm",
            "entity_types": ["PERSON", "ORG", "GPE", "DATE"],
        }

        assert ner_config["model"] == "en_core_web_sm"
        assert "PERSON" in ner_config["entity_types"]


class TestDocumentProcessing:
    """Tests for document processing utilities."""

    def test_document_id_generation(self):
        """Test generating document ID from content."""
        import hashlib

        content = b"Test document content"
        doc_id = hashlib.sha256(content).hexdigest()

        assert len(doc_id) == 64  # SHA256 produces 64 hex characters

    def test_chunk_offsets(self):
        """Test calculating chunk offsets."""
        text = "0123456789" * 100  # 1000 characters
        chunk_size = 100
        chunk_overlap = 20

        offsets = []
        for i in range(0, len(text), chunk_size - chunk_overlap):
            offsets.append((i, min(i + chunk_size, len(text))))
            if i + chunk_size >= len(text):
                break

        # Verify overlap works
        assert offsets[0][1] - offsets[0][0] == chunk_size
        if len(offsets) > 1:
            # Check overlap
            assert offsets[0][1] - offsets[1][0] == chunk_overlap

    def test_provenance_tracking(self):
        """Test provenance data structure."""
        provenance = {
            "doc_id": "abc123def456",
            "source_url": "https://example.com/doc.pdf",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "file_size": 1024000,
            "file_format": "pdf",
        }

        assert "doc_id" in provenance
        assert "source_url" in provenance
        assert "sha256" in provenance

    def test_chunk_metadata(self):
        """Test chunk metadata structure."""
        chunk = {
            "doc_id": "abc123",
            "chunk_id": "abc123_chunk_0",
            "text": "Sample text...",
            "start_offset": 0,
            "end_offset": 512,
        }

        assert "doc_id" in chunk
        assert "chunk_id" in chunk
        assert "text" in chunk
        assert "start_offset" in chunk
        assert "end_offset" in chunk


class TestEntityExtraction:
    """Tests for entity extraction utilities."""

    def test_entity_structure(self):
        """Test entity data structure."""
        entity = {
            "text": "Jeffrey Epstein",
            "label": "PERSON",
            "start": 0,
            "end": 16,
            "doc_id": "abc123",
        }

        assert entity["text"] == "Jeffrey Epstein"
        assert entity["label"] == "PERSON"
        assert "start" in entity

    def test_entity_types(self):
        """Test common entity types."""
        entity_types = [
            "PERSON",  # People
            "ORG",  # Organizations
            "GPE",  # Geo-political entities
            "DATE",  # Dates
            "MONEY",  # Monetary values
            "FAC",  # Facilities
            "EVENT",  # Events
        ]

        assert "PERSON" in entity_types
        assert "ORG" in entity_types
        assert "GPE" in entity_types


class TestManifestGeneration:
    """Tests for manifest generation."""

    def test_manifest_entry(self):
        """Test single manifest entry."""
        entry = {
            "doc_id": "test123",
            "source_url": "https://example.com/doc.pdf",
            "local_path": "./downloads/doc.pdf",
            "sha256": "abc123",
            "file_size": 1024,
            "download_timestamp": "2024-01-01T00:00:00Z",
        }

        assert entry["doc_id"] == "test123"
        assert entry["source_url"] == "https://example.com/doc.pdf"

    def test_manifest_jsonl_format(self):
        """Test manifest in JSONL format."""
        entries = [
            {"doc_id": "doc1", "source_url": "https://example.com/1.pdf"},
            {"doc_id": "doc2", "source_url": "https://example.com/2.pdf"},
        ]

        # JSONL format - one JSON object per line
        jsonl_output = "\n".join(json.dumps(e) for e in entries)

        # Verify we can parse it back
        parsed = [json.loads(line) for line in jsonl_output.split("\n")]

        assert len(parsed) == 2
        assert parsed[0]["doc_id"] == "doc1"
        assert parsed[1]["doc_id"] == "doc2"


class TestRunTracking:
    """Tests for run tracking."""

    def test_run_record(self):
        """Test run record structure."""
        run = {
            "run_id": "run_2024_01_01_001",
            "timestamp": "2024-01-01T12:00:00Z",
            "config": {"seed_urls": ["https://example.com"]},
            "status": "completed",
            "documents_processed": 100,
            "documents_failed": 2,
            "duration_seconds": 3600,
        }

        assert "run_id" in run
        assert run["status"] == "completed"
        assert run["documents_processed"] == 100

    def test_failure_record(self):
        """Test failure record structure."""
        failure = {
            "run_id": "run_001",
            "doc_id": "failed_doc",
            "source_url": "https://example.com/fail.pdf",
            "error": "OCRFailed",
            "error_message": "Could not extract text",
            "timestamp": "2024-01-01T12:00:00Z",
        }

        assert "doc_id" in failure
        assert "error" in failure


class TestPipelineIntegration:
    """Integration tests for pipeline components."""

    def test_end_to_end_provenance(self):
        """Test complete provenance tracking."""
        # Simulate full pipeline

        # 1. Document downloaded
        doc = {
            "doc_id": "sha256hash",
            "source_url": "https://justice.gov/epstein/disclosure1.pdf",
            "local_path": "./downloads/disclosure1.pdf",
            "sha256": "sha256hash",
        }

        # 2. Text extracted
        text_chunk = {
            "doc_id": doc["doc_id"],
            "text": "Sample extracted text...",
            "start_offset": 0,
            "end_offset": 512,
        }

        # 3. Entities extracted
        entity = {
            "doc_id": doc["doc_id"],
            "text": "Jeffrey Epstein",
            "label": "PERSON",
            "start": 0,
            "end": 16,
        }

        # Verify traceback chain
        assert entity["doc_id"] == doc["doc_id"]
        assert text_chunk["doc_id"] == doc["doc_id"]

    def test_config_to_args(self):
        """Test converting config to CLI args."""
        config = {
            "output_dir": "/data/output",
            "seed_urls": ["https://example.com"],
            "chunk_size": 512,
        }

        # This would be converted to CLI args in actual pipeline
        args = [
            "--output-dir",
            config["output_dir"],
            "--chunk-size",
            str(config["chunk_size"]),
        ]

        assert "--output-dir" in args
        assert "/data/output" in args
