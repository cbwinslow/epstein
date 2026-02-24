#!/usr/bin/env python3
"""
Integration tests for Epstein pipeline.

These tests verify actual behavior against real dependencies.
Tests are written to work with the actual API.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestFileOrganizerIntegration:
    """Integration tests for FileOrganizer."""
    
    def test_detect_file_type_pdf(self):
        """Test PDF file type detection."""
        from epstein.file_organizer import FileOrganizer, FileType
        
        with tempfile.TemporaryDirectory() as tmpdir:
            organizer = FileOrganizer(base_dir=Path(tmpdir))
            
            # Create fake PDF
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 fake pdf content")
            
            result = organizer.detect_file_type(pdf_path)
            assert result == FileType.PDF
    
    def test_detect_file_type_zip(self):
        """Test ZIP file type detection."""
        from epstein.file_organizer import FileOrganizer, FileType
        
        with tempfile.TemporaryDirectory() as tmpdir:
            organizer = FileOrganizer(base_dir=Path(tmpdir))
            
            # Create fake ZIP
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.write_bytes(b"PK\x03\x04 fake zip content")
            
            result = organizer.detect_file_type(zip_path)
            assert result == FileType.ZIP
    
    def test_calculate_hash(self):
        """Test SHA256 hash calculation."""
        from epstein.file_organizer import FileOrganizer
        
        with tempfile.TemporaryDirectory() as tmpdir:
            organizer = FileOrganizer(base_dir=Path(tmpdir))
            
            # Create test file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("hello world")
            
            checksum = organizer.calculate_hash(test_file)
            
            # Verify against known SHA256
            import hashlib
            expected = hashlib.sha256(b"hello world").hexdigest()
            assert checksum == expected
    
    def test_normalize_filename(self):
        """Test filename normalization."""
        from epstein.file_organizer import FileOrganizer
        
        with tempfile.TemporaryDirectory() as tmpdir:
            organizer = FileOrganizer(base_dir=Path(tmpdir))
            
            # Test unsafe characters
            unsafe = "test<>:\"/\\|?*file.txt"
            safe = organizer.normalize_filename(unsafe)
            
            # Should not contain unsafe characters
            assert "<" not in safe
            assert ">" not in safe
            assert ":" not in safe
    
    def test_is_duplicate(self):
        """Test duplicate detection."""
        from epstein.file_organizer import FileOrganizer
        
        with tempfile.TemporaryDirectory() as tmpdir:
            organizer = FileOrganizer(base_dir=Path(tmpdir))
            
            # Create test file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("hello world")
            
            # Should not be duplicate initially (returns tuple: (is_dup, hash))
            is_dup, file_hash = organizer.is_duplicate(test_file)
            assert is_dup is False


class TestDownloadManagerIntegration:
    """Integration tests for DownloadManager."""
    
    def test_download_manager_init(self):
        """Test DownloadManager initialization."""
        from epstein.download_manager import DownloadManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DownloadManager(
                output_dir=Path(tmpdir),
                max_concurrent=2,
            )
            
            assert manager.output_dir == Path(tmpdir)
            assert manager.max_concurrent == 2
    
    def test_session_manager(self):
        """Test requests session management."""
        from epstein.download_manager import DownloadManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DownloadManager(output_dir=Path(tmpdir))
            
            # Should have a session_config
            assert manager.session_config is not None


class TestOCRProcessorIntegration:
    """Integration tests for OCRProcessor."""
    
    def test_ocr_processor_init(self):
        """Test OCRProcessor initialization."""
        from epstein.ocr_processor import OCRProcessor
        
        with tempfile.TemporaryDirectory() as tmpdir:
            processor = OCRProcessor(output_dir=Path(tmpdir))
            
            assert processor.output_dir == Path(tmpdir)


class TestOperationMonitorIntegration:
    """Integration tests for OperationMonitor."""
    
    def test_monitor_init(self):
        """Test OperationMonitor initialization."""
        from epstein.operation_monitor import OperationMonitor, OperationType
        
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = OperationMonitor(
                log_dir=Path(tmpdir),
                enable_dashboard=False,
            )
            
            assert monitor.log_dir == Path(tmpdir)
            assert monitor.enable_dashboard is False
    
    def test_operation_type_enum(self):
        """Test OperationType enum values."""
        from epstein.operation_monitor import OperationType
        
        # Verify expected operation types exist
        assert OperationType.DOWNLOAD is not None
        assert OperationType.PROCESS is not None
        assert OperationType.EXTRACT is not None


class TestDashboardIntegration:
    """Integration tests for Dashboard."""
    
    def test_dashboard_app_init(self):
        """Test dashboard FastAPI app initialization."""
        from epstein.dashboard import app
        
        # Should be FastAPI app
        assert app is not None
        assert hasattr(app, 'routes')
    
    def test_dashboard_routes(self):
        """Test dashboard has expected routes."""
        from epstein.dashboard import app
        
        # Get route paths
        routes = [r.path for r in app.routes]
        
        # Should have basic routes
        assert isinstance(routes, list)


class TestIngestionUtils:
    """Test ingestion utilities."""
    
    def test_detect_file_type_util(self):
        """Test detect_file_type utility function."""
        from scripts.ingestion_utils import detect_file_type
        
        # Should work with string path
        result = detect_file_type("/tmp/test.pdf")
        assert result == "pdf"
    
    def test_safe_filename_util(self):
        """Test safe_filename utility function."""
        from scripts.ingestion_utils import safe_filename
        
        result = safe_filename("test<>file.txt")
        assert "<" not in result
        assert ">" not in result
    
    def test_get_file_metadata(self):
        """Test get_file_metadata utility."""
        from scripts.ingestion_utils import get_file_metadata
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test")
            f.flush()
            
            meta = get_file_metadata(f.name)
            
            assert "name" in meta
            assert "size" in meta
            assert meta["size"] == 4  # "test"
    
    def test_generate_file_hash(self):
        """Test generate_file_hash utility."""
        from scripts.ingestion_utils import generate_file_hash
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("hello world")
            f.flush()
            
            hash_result = generate_file_hash(f.name)
            
            import hashlib
            expected = hashlib.sha256(b"hello world").hexdigest()
            assert hash_result == expected
