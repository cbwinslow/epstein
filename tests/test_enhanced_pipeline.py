#!/usr/bin/env python3
"""
Comprehensive Test Suite for Enhanced Pipeline Components

Tests for:
- Download Manager
- File Organizer
- OCR Processor
- Operation Monitor
- Pipeline Orchestrator

Author: Epstein Project Team
Date: 2026-02-13
"""

import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from epstein.download_manager import (
    DownloadManager,
    DownloadSource,
    DownloadStatus,
    DownloadTask,
    SessionConfig,
)
from epstein.file_organizer import (
    FileCategory,
    FileOrganizer,
    FileType,
)
from epstein.ocr_processor import (
    OCRProcessor,
    OCRQuality,
    OCRStatus,
)
from epstein.operation_monitor import (
    AlertLevel,
    OperationMonitor,
    OperationType,
)


class TestDownloadManager:
    """Test suite for DownloadManager"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def download_manager(self, temp_dir):
        """Create DownloadManager instance"""
        return DownloadManager(
            output_dir=temp_dir,
            max_concurrent=2,
            chunk_size=1024,
        )

    def test_initialization(self, download_manager, temp_dir):
        """Test download manager initialization"""
        assert download_manager.output_dir == temp_dir
        assert download_manager.max_concurrent == 2
        assert download_manager.chunk_size == 1024
        assert len(download_manager.tasks) == 0

    def test_add_task(self, download_manager):
        """Test adding download task"""
        task = DownloadTask(
            url="https://example.com/file.pdf",
            destination=download_manager.output_dir / "file.pdf",
            source=DownloadSource.DOJ_DISCLOSURES,
            name="Test File",
        )

        task_id = download_manager.add_task(task)

        assert task_id in download_manager.tasks
        assert download_manager.tasks[task_id] == task

    def test_add_batch_tasks(self, download_manager):
        """Test adding multiple tasks"""
        tasks = [
            DownloadTask(
                url=f"https://example.com/file{i}.pdf",
                destination=download_manager.output_dir / f"file{i}.pdf",
                source=DownloadSource.DOJ_DISCLOSURES,
                name=f"Test File {i}",
            )
            for i in range(5)
        ]

        task_ids = download_manager.add_batch_tasks(tasks)

        assert len(task_ids) == 5
        assert all(tid in download_manager.tasks for tid in task_ids)

    def test_get_task_status(self, download_manager):
        """Test getting task status"""
        task = DownloadTask(
            url="https://example.com/file.pdf",
            destination=download_manager.output_dir / "file.pdf",
            source=DownloadSource.DOJ_DISCLOSURES,
            name="Test File",
            status=DownloadStatus.COMPLETED,
        )

        task_id = download_manager.add_task(task)
        status = download_manager.get_task_status(task_id)

        assert status == DownloadStatus.COMPLETED

    def test_calculate_checksum(self, download_manager, temp_dir):
        """Test checksum calculation"""
        test_file = temp_dir / "test.txt"
        test_content = b"test content"
        test_file.write_bytes(test_content)

        checksum = download_manager._calculate_checksum(test_file)

        expected = hashlib.sha256(test_content).hexdigest()
        assert checksum == expected

    @patch('requests.Session')
    def test_session_creation(self, mock_session, download_manager):
        """Test HTTP session creation"""
        session = download_manager._get_session()

        assert session is not None
        assert "User-Agent" in session.headers

    def test_session_with_cookies(self, temp_dir):
        """Test session with cookies"""
        cookies = {"session": "test123", "auth": "token456"}
        session_config = SessionConfig(cookies=cookies)

        manager = DownloadManager(
            output_dir=temp_dir,
            session_config=session_config
        )

        session = manager._get_session()

        for key, value in cookies.items():
            assert session.cookies.get(key) == value

    def test_session_with_auth_key(self, temp_dir):
        """Test session with authentication key"""
        session_config = SessionConfig(session_key="test_key_123")

        manager = DownloadManager(
            output_dir=temp_dir,
            session_config=session_config
        )

        session = manager._get_session()

        assert "Authorization" in session.headers
        assert session.headers["Authorization"] == "Bearer test_key_123"

    def test_get_statistics(self, download_manager):
        """Test statistics calculation"""
        # Add tasks with different statuses
        for i in range(10):
            status = DownloadStatus.COMPLETED if i < 7 else DownloadStatus.FAILED
            task = DownloadTask(
                url=f"https://example.com/file{i}.pdf",
                destination=download_manager.output_dir / f"file{i}.pdf",
                source=DownloadSource.DOJ_DISCLOSURES,
                name=f"File {i}",
                status=status,
            )
            download_manager.add_task(task)

        stats = download_manager.get_statistics()

        assert stats["total_tasks"] == 10
        assert stats["completed"] == 7
        assert stats["failed"] == 3
        assert stats["success_rate"] == 70.0


class TestFileOrganizer:
    """Test suite for FileOrganizer"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def organizer(self, temp_dir):
        """Create FileOrganizer instance"""
        return FileOrganizer(
            base_dir=temp_dir,
            dedup_enabled=True,
            auto_extract_zips=False,
        )

    def test_initialization(self, organizer, temp_dir):
        """Test organizer initialization"""
        assert organizer.base_dir == temp_dir
        assert organizer.organized_dir.exists()
        assert organizer.dedup_enabled is True

    def test_detect_file_type(self, organizer):
        """Test file type detection"""
        test_cases = [
            ("file.pdf", FileType.PDF),
            ("file.zip", FileType.ZIP),
            ("file.jpg", FileType.IMAGE),
            ("file.mp4", FileType.VIDEO),
            ("file.txt", FileType.TEXT),
            ("file.unknown", FileType.UNKNOWN),
        ]

        for filename, expected_type in test_cases:
            file_path = Path(filename)
            detected_type = organizer.detect_file_type(file_path)
            assert detected_type == expected_type

    def test_categorize_file(self, organizer):
        """Test file categorization"""
        test_cases = [
            ("file.pdf", "doj_disclosures", FileCategory.DOJ_DISCLOSURES),
            ("file.pdf", "fbi_vault", FileCategory.FBI_RECORDS),
            ("court_doc.pdf", "", FileCategory.COURT_RECORDS),
            ("email.txt", "", FileCategory.EMAILS),
            ("photo.jpg", "", FileCategory.IMAGES),
            ("video.mp4", "", FileCategory.VIDEOS),
            ("transcript.pdf", "", FileCategory.TRANSCRIPTS),
        ]

        for filename, source, expected_category in test_cases:
            file_path = Path(filename)
            category = organizer.categorize_file(file_path, source)
            assert category == expected_category

    def test_normalize_filename(self, organizer):
        """Test filename normalization"""
        normalized = organizer.normalize_filename(
            "Test File (with special chars!).pdf",
            source="doj_disclosures",
            dataset_number=1,
            index=42,
        )

        assert "DOJ_DS01" in normalized
        assert "0042" in normalized
        assert ".pdf" in normalized
        assert "!" not in normalized
        assert "(" not in normalized

    def test_calculate_hash(self, organizer, temp_dir):
        """Test hash calculation"""
        test_file = temp_dir / "test.txt"
        test_content = b"test content for hashing"
        test_file.write_bytes(test_content)

        file_hash = organizer.calculate_hash(test_file)
        expected = hashlib.sha256(test_content).hexdigest()

        assert file_hash == expected

    def test_deduplication(self, organizer, temp_dir):
        """Test file deduplication"""
        # Create test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")

        # First organization should succeed
        success1, path1, error1 = organizer.organize_file(test_file, source="test")
        assert success1 is True
        assert path1 is not None

        # Second organization should detect duplicate
        success2, path2, error2 = organizer.organize_file(test_file, source="test")
        assert success2 is True
        assert "Duplicate" in (error2 or "")
        assert path2 == path1  # Should return existing path

    def test_organize_file(self, organizer, temp_dir):
        """Test organizing a single file"""
        # Create test file
        test_file = temp_dir / "document.pdf"
        test_file.write_text("test pdf content")

        success, organized_path, error = organizer.organize_file(
            test_file,
            source="doj_disclosures",
            dataset_number=1,
        )

        assert success is True
        assert organized_path is not None
        assert organized_path.exists()
        assert error is None

    def test_get_statistics(self, organizer, temp_dir):
        """Test statistics gathering"""
        # Create and organize some files
        for i in range(5):
            test_file = temp_dir / f"file{i}.pdf"
            test_file.write_text(f"content {i}")
            organizer.organize_file(test_file, source="test")

        stats = organizer.get_statistics()

        assert stats["total_files"] >= 5
        assert "by_category" in stats
        assert "total_size_bytes" in stats


class TestOCRProcessor:
    """Test suite for OCRProcessor"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def ocr_processor(self, temp_dir):
        """Create OCRProcessor instance"""
        return OCRProcessor(
            output_dir=temp_dir,
            max_workers=1,
            max_retries=2,
        )

    def test_initialization(self, ocr_processor, temp_dir):
        """Test OCR processor initialization"""
        assert ocr_processor.output_dir == temp_dir
        assert ocr_processor.max_workers == 1
        assert ocr_processor.max_retries == 2

    def test_add_task(self, ocr_processor, temp_dir):
        """Test adding OCR task"""
        input_file = temp_dir / "input.pdf"
        input_file.touch()

        task_id = ocr_processor.add_task(input_file)

        assert task_id in ocr_processor.tasks
        assert ocr_processor.tasks[task_id].status == OCRStatus.PENDING

    def test_add_batch_tasks(self, ocr_processor, temp_dir):
        """Test adding multiple OCR tasks"""
        input_files = []
        for i in range(5):
            input_file = temp_dir / f"input{i}.pdf"
            input_file.touch()
            input_files.append(input_file)

        task_ids = ocr_processor.add_batch_tasks(input_files)

        assert len(task_ids) == 5
        assert all(tid in ocr_processor.tasks for tid in task_ids)

    def test_assess_text_quality(self, ocr_processor):
        """Test text quality assessment"""
        # Excellent quality text
        good_text = "This is a well-formatted document with proper words and sentences. " * 10
        quality, confidence = ocr_processor.assess_text_quality(good_text)
        assert confidence > 60.0

        # Poor quality text
        poor_text = "@@##$$%%^^&&"
        quality, confidence = ocr_processor.assess_text_quality(poor_text)
        assert quality == OCRQuality.FAILED
        assert confidence < 40.0

        # Empty text
        empty_text = ""
        quality, confidence = ocr_processor.assess_text_quality(empty_text)
        assert quality == OCRQuality.FAILED
        assert confidence == 0.0

    def test_get_statistics(self, ocr_processor, temp_dir):
        """Test statistics calculation"""
        # Add tasks with different statuses
        for i in range(10):
            input_file = temp_dir / f"input{i}.pdf"
            input_file.touch()
            task_id = ocr_processor.add_task(input_file)

            # Manually set status for testing
            if i < 7:
                ocr_processor.tasks[task_id].status = OCRStatus.COMPLETED
            elif i < 9:
                ocr_processor.tasks[task_id].status = OCRStatus.FAILED
            else:
                ocr_processor.tasks[task_id].status = OCRStatus.SKIPPED

        stats = ocr_processor.get_statistics()

        assert stats["total_tasks"] == 10
        assert stats["completed"] == 7
        assert stats["failed"] == 2
        assert stats["skipped"] == 1


class TestOperationMonitor:
    """Test suite for OperationMonitor"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def monitor(self, temp_dir):
        """Create OperationMonitor instance"""
        return OperationMonitor(
            log_dir=temp_dir,
            enable_dashboard=False,
            enable_alerts=True,
        )

    def test_initialization(self, monitor, temp_dir):
        """Test monitor initialization"""
        assert monitor.log_dir == temp_dir
        assert monitor.enable_alerts is True
        assert len(monitor.metrics) == len(OperationType)

    def test_start_operation(self, monitor):
        """Test starting operation tracking"""
        monitor.start_operation(
            OperationType.DOWNLOAD,
            total_count=100,
            description="Test downloads"
        )

        metrics = monitor.metrics[OperationType.DOWNLOAD]
        assert metrics.total_count == 100

    def test_update_progress(self, monitor):
        """Test progress updates"""
        monitor.start_operation(OperationType.DOWNLOAD, total_count=100)

        monitor.update_progress(
            OperationType.DOWNLOAD,
            completed=10,
            failed=2,
            skipped=1,
        )

        metrics = monitor.metrics[OperationType.DOWNLOAD]
        assert metrics.completed_count == 10
        assert metrics.failed_count == 2
        assert metrics.skipped_count == 1

    def test_complete_operation(self, monitor):
        """Test completing operation"""
        monitor.start_operation(OperationType.DOWNLOAD, total_count=100)
        monitor.update_progress(OperationType.DOWNLOAD, completed=100)
        monitor.complete_operation(OperationType.DOWNLOAD)

        metrics = monitor.metrics[OperationType.DOWNLOAD]
        assert metrics.end_time is not None
        assert metrics.in_progress_count == 0

    def test_report_error(self, monitor):
        """Test error reporting"""
        monitor.start_operation(OperationType.DOWNLOAD, total_count=100)

        monitor.report_error(
            OperationType.DOWNLOAD,
            "Test error message",
            metadata={"file": "test.pdf"}
        )

        metrics = monitor.metrics[OperationType.DOWNLOAD]
        assert len(metrics.errors) == 1
        assert "Test error message" in metrics.errors

    def test_report_warning(self, monitor):
        """Test warning reporting"""
        monitor.start_operation(OperationType.DOWNLOAD, total_count=100)

        monitor.report_warning(
            OperationType.DOWNLOAD,
            "Test warning message"
        )

        metrics = monitor.metrics[OperationType.DOWNLOAD]
        assert len(metrics.warnings) == 1

    def test_alert_generation(self, monitor):
        """Test alert generation"""
        monitor.start_operation(OperationType.DOWNLOAD, total_count=100)

        # Trigger high failure rate alert
        monitor.update_progress(OperationType.DOWNLOAD, failed=30)

        # Check alerts were generated
        assert len(monitor.alerts) > 0

    def test_alert_callback(self, monitor):
        """Test alert callback"""
        callback_called = []

        def test_callback(alert):
            callback_called.append(alert)

        monitor.register_alert_callback(test_callback)

        monitor.start_operation(OperationType.DOWNLOAD, total_count=100)
        monitor.report_error(OperationType.DOWNLOAD, "Test error")

        assert len(callback_called) > 0

    def test_get_metrics(self, monitor):
        """Test getting metrics"""
        monitor.start_operation(OperationType.DOWNLOAD, total_count=100)
        monitor.update_progress(OperationType.DOWNLOAD, completed=50)

        # Get specific metrics
        download_metrics = monitor.get_metrics(OperationType.DOWNLOAD)
        assert download_metrics["total_count"] == 100
        assert download_metrics["completed_count"] == 50

        # Get all metrics
        all_metrics = monitor.get_metrics()
        assert OperationType.DOWNLOAD.value in all_metrics

    def test_get_recent_alerts(self, monitor):
        """Test getting recent alerts"""
        monitor.start_operation(OperationType.DOWNLOAD, total_count=100)

        # Generate some alerts
        for i in range(5):
            monitor.report_error(OperationType.DOWNLOAD, f"Error {i}")

        recent_alerts = monitor.get_recent_alerts(count=3)
        assert len(recent_alerts) == 3

        # Test filtering by level
        error_alerts = monitor.get_recent_alerts(count=10, level=AlertLevel.ERROR)
        assert all(a.level == AlertLevel.ERROR for a in error_alerts)

    def test_audit_trail(self, monitor):
        """Test audit trail logging"""
        monitor.start_operation(OperationType.DOWNLOAD, total_count=100)
        monitor.update_progress(OperationType.DOWNLOAD, completed=10)
        monitor.complete_operation(OperationType.DOWNLOAD)

        # Check audit file exists and has content
        assert monitor.audit_file.exists()

        with open(monitor.audit_file) as f:
            lines = f.readlines()
            assert len(lines) > 0

            # Verify it's valid JSON
            for line in lines:
                data = json.loads(line.strip())
                assert "timestamp" in data
                assert "event" in data


def test_integration_workflow(tmp_path):
    """Integration test for complete workflow"""
    # Create components
    DownloadManager(output_dir=tmp_path / "downloads")
    organizer = FileOrganizer(base_dir=tmp_path / "downloads", organized_dir=tmp_path / "organized")
    monitor = OperationMonitor(log_dir=tmp_path / "logs", enable_dashboard=False)

    # Simulate download
    monitor.start_operation(OperationType.DOWNLOAD, total_count=5)

    for i in range(5):
        # Create mock downloaded file
        test_file = tmp_path / "downloads" / f"file{i}.pdf"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text(f"content {i}")

        monitor.update_progress(OperationType.DOWNLOAD, completed=1)

    monitor.complete_operation(OperationType.DOWNLOAD)

    # Organize files
    monitor.start_operation(OperationType.ORGANIZE, total_count=5)

    for file in (tmp_path / "downloads").glob("*.pdf"):
        organizer.organize_file(file, source="test")
        monitor.update_progress(OperationType.ORGANIZE, completed=1)

    monitor.complete_operation(OperationType.ORGANIZE)

    # Verify
    download_metrics = monitor.get_metrics(OperationType.DOWNLOAD)
    assert download_metrics["completed_count"] == 5

    organize_metrics = monitor.get_metrics(OperationType.ORGANIZE)
    assert organize_metrics["completed_count"] == 5

    org_stats = organizer.get_statistics()
    assert org_stats["total_files"] >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
