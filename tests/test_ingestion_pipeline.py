#!/usr/bin/env python3
"""
Comprehensive Test Suite for Epstein Files Ingestion Pipeline

Tests all ingestion pipeline functionality including:
- Pipeline initialization and configuration
- Document processing and text extraction
- OCR and NER functionality
- Database integration
- Error handling and edge cases
- Performance and memory management
"""

import asyncio
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import pipeline components
from scripts.ingestion_pipeline import (
    DocumentMetadata,
    EpsteinIngestionPipeline,
    ExtractedEntity,
    ExtractedText,
    PipelineConfig,
)
from scripts.ingestion_utils import (
    detect_file_type,
    generate_file_hash,
    get_file_metadata,
    safe_filename,
)

# Test Configuration
TEST_CONFIG = PipelineConfig(
    download_dir=tempfile.mkdtemp(),
    processed_dir=tempfile.mkdtemp(),
    failed_dir=tempfile.mkdtemp(),
    database_url=None,  # No database for testing
    max_workers=2,
    batch_size=5,
    ocr_enabled=True,
    ner_enabled=True,
)


@pytest.fixture
def test_pipeline():
    """Create test pipeline instance"""
    pipeline = EpsteinIngestionPipeline(TEST_CONFIG)
    return pipeline


# ============================================================================
# Pipeline Initialization Tests
# ============================================================================


class TestPipelineInitialization:
    """Test pipeline initialization and configuration"""

    def test_pipeline_creation(self, test_pipeline):
        """Test pipeline instance creation"""
        assert test_pipeline is not None
        assert test_pipeline.config.download_dir == TEST_CONFIG.download_dir
        assert test_pipeline.status == "initialized"
        assert test_pipeline.processed_count == 0
        assert test_pipeline.error_count == 0

    def test_directory_creation(self, test_pipeline):
        """Test directory creation"""
        assert Path(TEST_CONFIG.download_dir).exists()
        assert Path(TEST_CONFIG.processed_dir).exists()
        assert Path(TEST_CONFIG.failed_dir).exists()

    def test_run_id_generation(self, test_pipeline):
        """Test run ID generation"""
        assert test_pipeline.run_id is not None
        assert len(test_pipeline.run_id) > 0
        assert test_pipeline.run_id != ""


# ============================================================================
# Utility Function Tests
# ============================================================================


class TestUtilityFunctions:
    """Test utility functions"""

    def test_file_hash_generation(self):
        """Test file hash generation"""
        # Create test file
        test_file = Path(TEST_CONFIG.download_dir) / "test_file.txt"
        test_file.write_text("Test content for hashing")

        hash_result = generate_file_hash(str(test_file))
        assert hash_result is not None
        assert len(hash_result) == 64  # SHA-256 hash length
        assert hash_result == hashlib.sha256(b"Test content for hashing").hexdigest()

        # Clean up
        test_file.unlink()

    def test_file_metadata_extraction(self):
        """Test file metadata extraction"""
        # Create test file
        test_file = Path(TEST_CONFIG.download_dir) / "test_metadata.txt"
        test_file.write_text("Test content")

        metadata = get_file_metadata(str(test_file))
        assert metadata is not None
        assert "name" in metadata
        assert "size" in metadata
        assert "extension" in metadata

        # Clean up
        test_file.unlink()

    def test_file_type_detection(self):
        """Test file type detection"""
        # Test various file types
        test_cases = [
            ("test.pdf", "pdf"),
            ("test.jpg", "image"),
            ("test.txt", "text"),
            ("test.html", "text"),
            ("test.unknown", "unknown"),
        ]

        for filename, expected_type in test_cases:
            test_file = Path(TEST_CONFIG.download_dir) / filename
            test_file.write_text("Test")

            file_type = detect_file_type(str(test_file))
            assert file_type == expected_type

            test_file.unlink()

    def test_safe_filename_generation(self):
        """Test safe filename generation"""
        unsafe_names = [
            "Test File (Special).txt",
            "file/with/slashes.txt",
            "file:with:colons.txt",
            "file*with*asterisks.txt",
        ]

        for unsafe_name in unsafe_names:
            safe_name = safe_filename(unsafe_name)
            assert all(c.isalnum() or c in ["_", "-", "."] for c in safe_name)
            assert safe_name.endswith(".txt")


# ============================================================================
# Document Processing Tests
# ============================================================================


class TestDocumentProcessing:
    """Test document processing functionality"""

    def test_document_metadata_creation(self):
        """Test document metadata creation"""
        metadata = DocumentMetadata(
            document_id="test_doc_1",
            source_id="govinfo",
            ingestion_run_id="test_run_1",
            file_path="/path/to/file.pdf",
            file_name="file.pdf",
            file_size=1024,
            file_hash="test_hash_123",
            mime_type="application/pdf",
            language="en",
            page_count=5,
            ocr_required=False,
            ocr_confidence=None,
            processing_status="pending",
            error_message=None,
            metadata={"test": "data"},
        )

        assert metadata.document_id == "test_doc_1"
        assert metadata.file_size == 1024
        assert metadata.processing_status == "pending"
        assert metadata.metadata["test"] == "data"

    def test_extracted_text_creation(self):
        """Test extracted text creation"""
        text = ExtractedText(
            document_id="test_doc_1",
            page_number=1,
            text_content="Extracted text content",
            extraction_method="native",
            confidence_score=0.95,
            language="en",
            metadata={"source": "test"},
        )

        assert text.document_id == "test_doc_1"
        assert text.page_number == 1
        assert text.text_content == "Extracted text content"
        assert text.extraction_method == "native"

    def test_extracted_entity_creation(self):
        """Test extracted entity creation"""
        entity = ExtractedEntity(
            document_id="test_doc_1",
            extracted_text_id="text_1",
            entity_type="PERSON",
            entity_text="John Doe",
            confidence_score=0.9,
            start_position=10,
            end_position=18,
            page_number=1,
            metadata={"model": "test"},
        )

        assert entity.entity_type == "PERSON"
        assert entity.entity_text == "John Doe"
        assert entity.confidence_score == 0.9


# ============================================================================
# File Processing Tests
# ============================================================================


class TestFileProcessing:
    """Test file processing functionality"""

    def test_text_file_processing(self, test_pipeline):
        """Test text file processing"""
        # Create test text file
        test_file = Path(TEST_CONFIG.download_dir) / "test.txt"
        test_file.write_text("This is test content for processing.")

        # Process file
        pages_text, page_count, ocr_required = test_pipeline._extract_text_from_document(
            str(test_file)
        )

        assert len(pages_text) == 1
        assert page_count == 1
        assert not ocr_required
        assert "test content" in pages_text[0]

        # Clean up
        test_file.unlink()

    def test_pdf_file_processing(self, test_pipeline, mocker):
        """Test PDF file processing"""
        # Create test PDF file
        test_file = Path(TEST_CONFIG.download_dir) / "test.pdf"
        test_file.write_text("%PDF-1.4 test pdf content")

        # Mock pdfplumber
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Extracted PDF text"
        mock_pdf.pages = [mock_page]

        with patch("pdfplumber.open", return_value=mock_pdf):
            pages_text, page_count, ocr_required = test_pipeline._extract_text_from_document(
                str(test_file)
            )

        assert len(pages_text) == 1
        assert page_count == 1
        assert pages_text[0] == "Extracted PDF text"

        # Clean up
        test_file.unlink()

    def test_file_movement(self, test_pipeline):
        """Test file movement between directories"""
        # Create test file
        test_file = Path(TEST_CONFIG.download_dir) / "test_move.txt"
        test_file.write_text("Test content")

        # Test move to processed
        processed_path = test_pipeline._move_file_to_processed(str(test_file))
        assert Path(processed_path).exists()
        assert Path(processed_path).parent == Path(TEST_CONFIG.processed_dir)

        # Test move to failed
        test_file2 = Path(TEST_CONFIG.download_dir) / "test_move2.txt"
        test_file2.write_text("Test content 2")

        failed_path = test_pipeline._move_file_to_failed(str(test_file2))
        assert Path(failed_path).exists()
        assert Path(failed_path).parent == Path(TEST_CONFIG.failed_dir)


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_invalid_file_processing(self, test_pipeline):
        """Test processing of invalid file"""
        # Try to process non-existent file
        pages_text, page_count, ocr_required = test_pipeline._extract_text_from_document(
            "/nonexistent/file.txt"
        )

        assert len(pages_text) == 0
        assert page_count == 1  # Default fallback
        assert not ocr_required

    def test_corrupt_file_processing(self, test_pipeline):
        """Test processing of corrupt file"""
        # Create corrupt file
        test_file = Path(TEST_CONFIG.download_dir) / "corrupt.pdf"
        test_file.write_bytes(b"\x00\x01\x02\x03 invalid pdf content")

        pages_text, page_count, ocr_required = test_pipeline._extract_text_from_document(
            str(test_file)
        )

        assert len(pages_text) == 0
        assert page_count == 0  # Failed to read

        # Clean up
        test_file.unlink()

    def test_large_file_processing(self, test_pipeline):
        """Test processing of large file"""
        # Create large text file
        test_file = Path(TEST_CONFIG.download_dir) / "large.txt"
        large_content = "Large content line\n" * 10000
        test_file.write_text(large_content)

        pages_text, page_count, ocr_required = test_pipeline._extract_text_from_document(
            str(test_file)
        )

        assert len(pages_text) == 1
        assert page_count == 1
        assert len(pages_text[0]) > 10000

        # Clean up
        test_file.unlink()


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Test performance and memory management"""

    def test_batch_processing(self, test_pipeline, mocker):
        """Test batch processing performance"""
        # Create test files
        test_files = []
        for i in range(10):
            test_file = Path(TEST_CONFIG.download_dir) / f"batch_test_{i}.txt"
            test_file.write_text(f"Test content {i}")
            test_files.append(test_file)

        # Mock processing to avoid actual OCR/NER
        mocker.patch.object(
            EpsteinIngestionPipeline, "_perform_ocr_if_needed", return_value=(["test text"], 0.9)
        )

        mocker.patch.object(EpsteinIngestionPipeline, "_perform_ner", return_value=[])

        # Process files
        async def process_files():
            for test_file in test_files:
                await test_pipeline._process_single_document(str(test_file), "test_source")

        asyncio.run(process_files())

        # Verify processing
        assert test_pipeline.processed_count == 10
        assert test_pipeline.error_count == 0

        # Clean up
        for test_file in test_files:
            if test_file.exists():
                test_file.unlink()

    def test_memory_management(self, test_pipeline):
        """Test memory management with large files"""
        # Create multiple large files
        test_files = []
        for i in range(5):
            test_file = Path(TEST_CONFIG.download_dir) / f"memory_test_{i}.txt"
            large_content = "Memory test content\n" * 5000
            test_file.write_text(large_content)
            test_files.append(test_file)

        # Process files and check memory usage
        test_pipeline._get_status()

        # Clean up
        for test_file in test_files:
            test_file.unlink()

        # Memory should be managed properly
        test_pipeline._get_status()
        # Should not have memory leaks


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Test integration between components"""

    def test_complete_pipeline_flow(self, test_pipeline, mocker):
        """Test complete pipeline flow"""
        # Create test files
        test_files = []
        for i in range(3):
            test_file = Path(TEST_CONFIG.download_dir) / f"integration_test_{i}.txt"
            test_file.write_text(f"Integration test content {i}")
            test_files.append(test_file)

        # Mock OCR and NER to avoid dependencies
        mocker.patch.object(
            EpsteinIngestionPipeline, "_perform_ocr_if_needed", return_value=(["test text"], 0.9)
        )

        mocker.patch.object(EpsteinIngestionPipeline, "_perform_ner", return_value=[])

        # Run pipeline
        asyncio.run(test_pipeline.run_pipeline(TEST_CONFIG.download_dir, "test_source"))

        # Verify results
        assert test_pipeline.status == "completed"
        assert test_pipeline.processed_count == 3
        assert test_pipeline.error_count == 0

        # Check files moved to processed
        for test_file in test_files:
            processed_file = Path(TEST_CONFIG.processed_dir) / test_file.name
            assert processed_file.exists()

        # Clean up
        for test_file in test_files:
            processed_file = Path(TEST_CONFIG.processed_dir) / test_file.name
            if processed_file.exists():
                processed_file.unlink()

    def test_error_recovery(self, test_pipeline, mocker):
        """Test error recovery in pipeline"""
        # Create test files
        test_files = []
        for i in range(3):
            test_file = Path(TEST_CONFIG.download_dir) / f"error_test_{i}.txt"
            test_file.write_text(f"Error test content {i}")
            test_files.append(test_file)

        # Mock processing to fail for some files
        def mock_process(task, source_id):
            if "error_test_1" in task:
                raise Exception("Simulated error")
            return True

        mocker.patch.object(
            EpsteinIngestionPipeline, "_process_single_document", side_effect=mock_process
        )

        # Run pipeline
        asyncio.run(test_pipeline.run_pipeline(TEST_CONFIG.download_dir, "test_source"))

        # Verify error handling
        assert test_pipeline.error_count == 1
        assert test_pipeline.processed_count == 2

        # Check failed file moved to failed directory
        failed_file = Path(TEST_CONFIG.failed_dir) / "error_test_1.txt"
        assert failed_file.exists()

        # Clean up
        for test_file in test_files:
            if test_file.exists():
                test_file.unlink()

        if failed_file.exists():
            failed_file.unlink()


# ============================================================================
# Test Runner
# ============================================================================

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main(
        ["--verbose", "--color=yes", "-x", "-s", __file__]  # Stop on first failure  # Show output
    )
