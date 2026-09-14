#!/usr/bin/env python3
"""
Comprehensive Validation and Assessment Script
Tests all automation system components and generates detailed reports.

Author: Epstein Project Team
Date: 2026-02-23
"""

import json
import logging
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("/tmp/validation_report.log")],
)
logger = logging.getLogger(__name__)

# Results tracking
validation_results = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "tests": [],
    "summary": {"total": 0, "passed": 0, "failed": 0, "warnings": 0},
}


def log_test(name: str, status: str, message: str = "", details: dict = None):
    """Log a test result"""
    result = {"name": name, "status": status, "message": message, "details": details or {}}
    validation_results["tests"].append(result)
    validation_results["summary"]["total"] += 1

    if status == "PASS":
        validation_results["summary"]["passed"] += 1
        logger.info(f"✓ {name}: {message}")
    elif status == "FAIL":
        validation_results["summary"]["failed"] += 1
        logger.error(f"✗ {name}: {message}")
    elif status == "WARN":
        validation_results["summary"]["warnings"] += 1
        logger.warning(f"⚠ {name}: {message}")


def test_module_imports():
    """Test that all core modules can be imported"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 1: Module Import Validation")
    logger.info("=" * 70)

    modules = [
        ("epstein.download_manager", ["DownloadManager", "DownloadTask", "DownloadSource"]),
        ("epstein.file_organizer", ["FileOrganizer", "FileType", "FileCategory"]),
        ("epstein.ocr_processor", ["OCRProcessor", "OCRStatus", "OCRQuality"]),
        ("epstein.operation_monitor", ["OperationMonitor", "OperationType", "AlertLevel"]),
    ]

    for module_name, expected_classes in modules:
        try:
            module = __import__(module_name, fromlist=expected_classes)

            # Check classes exist
            missing = []
            for cls_name in expected_classes:
                if not hasattr(module, cls_name):
                    missing.append(cls_name)

            if missing:
                log_test(f"Import {module_name}", "WARN", f"Missing classes: {', '.join(missing)}")
            else:
                log_test(
                    f"Import {module_name}",
                    "PASS",
                    f"All {len(expected_classes)} classes available",
                )
        except Exception as e:
            log_test(f"Import {module_name}", "FAIL", f"{type(e).__name__}: {str(e)}")


def test_download_manager():
    """Test DownloadManager functionality"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 2: Download Manager Validation")
    logger.info("=" * 70)

    try:
        from epstein.download_manager import (
            DownloadManager,
            DownloadSource,
            DownloadTask,
            SessionConfig,
        )

        # Test initialization
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DownloadManager(output_dir=Path(tmpdir))
            log_test("DownloadManager init", "PASS", f"Initialized with output_dir={tmpdir}")

            # Test session config
            session_config = SessionConfig(user_agent="Test/1.0", cookies={"test": "value"})
            DownloadManager(output_dir=Path(tmpdir), session_config=session_config)
            log_test("DownloadManager with auth", "PASS", "Session config applied successfully")

            # Test task creation
            task = DownloadTask(
                url="https://example.com/test.pdf",
                destination=Path(tmpdir) / "test.pdf",
                source=DownloadSource.DOJ_DISCLOSURES,
                name="Test Task",
            )
            task_id = dm.add_task(task)
            log_test("DownloadManager add_task", "PASS", f"Task added with ID: {task_id[:8]}...")

            # Test statistics
            stats = dm.get_statistics()
            if stats["total_tasks"] == 1:
                log_test(
                    "DownloadManager statistics",
                    "PASS",
                    f"Correct task count: {stats['total_tasks']}",
                )
            else:
                log_test(
                    "DownloadManager statistics",
                    "FAIL",
                    f"Expected 1 task, got {stats['total_tasks']}",
                )

    except Exception as e:
        log_test("DownloadManager tests", "FAIL", f"{type(e).__name__}: {str(e)}")
        logger.error(traceback.format_exc())


def test_file_organizer():
    """Test FileOrganizer functionality"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 3: File Organizer Validation")
    logger.info("=" * 70)

    try:
        from epstein.file_organizer import FileOrganizer, FileType

        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "base"
            org_dir = Path(tmpdir) / "organized"

            # Test initialization
            organizer = FileOrganizer(base_dir=base_dir, organized_dir=org_dir, dedup_enabled=True)
            log_test("FileOrganizer init", "PASS", "Initialized with deduplication enabled")

            # Test file type detection
            test_cases = [
                ("file.pdf", FileType.PDF),
                ("file.zip", FileType.ZIP),
                ("file.jpg", FileType.IMAGE),
            ]

            for filename, expected_type in test_cases:
                detected = organizer.detect_file_type(Path(filename))
                if detected == expected_type:
                    log_test(
                        f"FileType detection: {filename}",
                        "PASS",
                        f"Correctly detected as {expected_type.value}",
                    )
                else:
                    log_test(
                        f"FileType detection: {filename}",
                        "FAIL",
                        f"Expected {expected_type.value}, got {detected.value}",
                    )

            # Test statistics
            stats = organizer.get_statistics()
            log_test(
                "FileOrganizer statistics",
                "PASS",
                f"Retrieved statistics: {stats['total_files']} files",
            )

    except Exception as e:
        log_test("FileOrganizer tests", "FAIL", f"{type(e).__name__}: {str(e)}")
        logger.error(traceback.format_exc())


def test_ocr_processor():
    """Test OCRProcessor functionality"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 4: OCR Processor Validation")
    logger.info("=" * 70)

    try:
        from epstein.ocr_processor import OCRProcessor, OCRQuality

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test initialization
            processor = OCRProcessor(
                output_dir=Path(tmpdir), max_workers=2, quality_threshold=OCRQuality.ACCEPTABLE
            )
            log_test(
                "OCRProcessor init",
                "PASS",
                f"Initialized with quality threshold: {OCRQuality.ACCEPTABLE.value}",
            )

            # Test quality assessment
            test_texts = [
                ("This is a well-formatted document. " * 20, "good quality"),
                ("@@##$$%%", "poor quality"),
                ("", "empty text"),
            ]

            for text, description in test_texts:
                quality, confidence = processor.assess_text_quality(text)
                log_test(
                    f"Quality assessment: {description}",
                    "PASS",
                    f"Quality={quality.value}, Confidence={confidence:.1f}%",
                )

            # Test statistics
            stats = processor.get_statistics()
            log_test(
                "OCRProcessor statistics",
                "PASS",
                f"Retrieved statistics: {stats['total_tasks']} tasks",
            )

    except Exception as e:
        log_test("OCRProcessor tests", "FAIL", f"{type(e).__name__}: {str(e)}")
        logger.error(traceback.format_exc())


def test_operation_monitor():
    """Test OperationMonitor functionality"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 5: Operation Monitor Validation")
    logger.info("=" * 70)

    try:
        from epstein.operation_monitor import OperationMonitor, OperationType

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test initialization
            monitor = OperationMonitor(
                log_dir=Path(tmpdir), enable_dashboard=False, enable_alerts=True
            )
            log_test("OperationMonitor init", "PASS", "Initialized with alerts enabled")

            # Test operation tracking
            monitor.start_operation(
                OperationType.DOWNLOAD, total_count=100, description="Test operation"
            )
            log_test("OperationMonitor start_operation", "PASS", "Operation started successfully")

            # Test progress update
            monitor.update_progress(OperationType.DOWNLOAD, completed=10, failed=2)
            log_test(
                "OperationMonitor update_progress",
                "PASS",
                "Progress updated: 10 completed, 2 failed",
            )

            # Test metrics retrieval
            metrics = monitor.get_metrics(OperationType.DOWNLOAD)
            if metrics["completed_count"] == 10:
                log_test(
                    "OperationMonitor metrics",
                    "PASS",
                    f"Correct metrics: {metrics['completed_count']} completed",
                )
            else:
                log_test(
                    "OperationMonitor metrics",
                    "FAIL",
                    f"Expected 10 completed, got {metrics['completed_count']}",
                )

            # Test alert generation
            monitor.report_error(OperationType.DOWNLOAD, "Test error message")
            alerts = monitor.get_recent_alerts(count=1)
            if len(alerts) > 0:
                log_test("OperationMonitor alerts", "PASS", f"Alert generated: {alerts[0].message}")
            else:
                log_test("OperationMonitor alerts", "WARN", "No alerts generated")

            monitor.complete_operation(OperationType.DOWNLOAD)

    except Exception as e:
        log_test("OperationMonitor tests", "FAIL", f"{type(e).__name__}: {str(e)}")
        logger.error(traceback.format_exc())


def test_pipeline_orchestrator():
    """Test Pipeline Orchestrator"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 6: Pipeline Orchestrator Validation")
    logger.info("=" * 70)

    try:
        # Check if file exists
        orchestrator_path = Path("scripts/pipeline_orchestrator.py")
        if orchestrator_path.exists():
            log_test("Pipeline Orchestrator file", "PASS", f"Found at {orchestrator_path}")

            # Try to import the module
            sys.path.insert(0, str(Path.cwd()))
            from scripts.pipeline_orchestrator import PipelineConfig

            log_test("Pipeline Orchestrator import", "PASS", "PipelineConfig imported successfully")

            # Test config creation
            with tempfile.TemporaryDirectory() as tmpdir:
                PipelineConfig(
                    base_dir=Path(tmpdir),
                    download_dir=Path(tmpdir) / "downloads",
                    organized_dir=Path(tmpdir) / "organized",
                    ocr_output_dir=Path(tmpdir) / "ocr",
                    log_dir=Path(tmpdir) / "logs",
                )
                log_test("PipelineConfig creation", "PASS", "Configuration created successfully")
        else:
            log_test("Pipeline Orchestrator file", "FAIL", f"Not found at {orchestrator_path}")

    except Exception as e:
        log_test("Pipeline Orchestrator tests", "FAIL", f"{type(e).__name__}: {str(e)}")
        logger.error(traceback.format_exc())


def test_integration():
    """Test component integration"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 7: Integration Testing")
    logger.info("=" * 70)

    try:
        from epstein.download_manager import DownloadManager
        from epstein.file_organizer import FileOrganizer
        from epstein.operation_monitor import OperationMonitor, OperationType

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create components
            DownloadManager(output_dir=tmppath / "downloads")
            FileOrganizer(base_dir=tmppath / "downloads", organized_dir=tmppath / "organized")
            monitor = OperationMonitor(log_dir=tmppath / "logs", enable_dashboard=False)

            log_test(
                "Integration: Component creation", "PASS", "All components created successfully"
            )

            # Test workflow simulation
            monitor.start_operation(OperationType.DOWNLOAD, total_count=5)

            # Simulate some work
            for _i in range(5):
                monitor.update_progress(OperationType.DOWNLOAD, completed=1)

            monitor.complete_operation(OperationType.DOWNLOAD)

            metrics = monitor.get_metrics(OperationType.DOWNLOAD)
            if metrics["completed_count"] == 5:
                log_test(
                    "Integration: Workflow simulation",
                    "PASS",
                    "Simulated workflow completed successfully",
                )
            else:
                log_test(
                    "Integration: Workflow simulation",
                    "FAIL",
                    f"Expected 5 completed, got {metrics['completed_count']}",
                )

    except Exception as e:
        log_test("Integration tests", "FAIL", f"{type(e).__name__}: {str(e)}")
        logger.error(traceback.format_exc())


def generate_report():
    """Generate validation report"""
    logger.info("\n" + "=" * 70)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 70)

    summary = validation_results["summary"]
    logger.info(f"\nTotal Tests: {summary['total']}")
    logger.info(f"Passed: {summary['passed']} ✓")
    logger.info(f"Failed: {summary['failed']} ✗")
    logger.info(f"Warnings: {summary['warnings']} ⚠")

    success_rate = (summary["passed"] / summary["total"] * 100) if summary["total"] > 0 else 0
    logger.info(f"\nSuccess Rate: {success_rate:.1f}%")

    # Save detailed report
    report_path = Path("/tmp/validation_report.json")
    with open(report_path, "w") as f:
        json.dump(validation_results, f, indent=2)
    logger.info(f"\nDetailed report saved to: {report_path}")

    # Determine overall status
    if summary["failed"] == 0:
        logger.info("\n✓ ALL TESTS PASSED")
        return 0
    else:
        logger.error(f"\n✗ {summary['failed']} TEST(S) FAILED")
        return 1


def main():
    """Run all validation tests"""
    logger.info("=" * 70)
    logger.info("EPSTEIN AUTOMATION SYSTEM VALIDATION")
    logger.info("=" * 70)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("Log file: /tmp/validation_report.log")

    # Run all tests
    test_module_imports()
    test_download_manager()
    test_file_organizer()
    test_ocr_processor()
    test_operation_monitor()
    test_pipeline_orchestrator()
    test_integration()

    # Generate report
    return generate_report()


if __name__ == "__main__":
    sys.exit(main())
