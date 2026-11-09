#!/usr/bin/env python3
"""
Unified Pipeline Orchestrator
Orchestrates the complete workflow: download → organize → OCR → process

Author: Epstein Project Team
Date: 2026-02-13
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from epstein.download_manager import (
    DownloadManager,
    DownloadTask,
    SessionConfig,
)
from epstein.file_organizer import FileOrganizer
from epstein.ocr_processor import OCRProcessor, OCRQuality
from epstein.operation_monitor import (
    AlertLevel,
    OperationMonitor,
    OperationType,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/tmp/pipeline_orchestrator.log"),
    ],
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the pipeline"""

    # Directories
    base_dir: Path
    download_dir: Path
    organized_dir: Path
    ocr_output_dir: Path
    log_dir: Path

    # Download settings
    max_concurrent_downloads: int = 3
    download_chunk_size: int = 8 * 1024 * 1024
    enable_checksums: bool = True

    # Organization settings
    enable_deduplication: bool = True
    auto_extract_zips: bool = True

    # OCR settings
    max_ocr_workers: int = 2
    ocr_quality_threshold: OCRQuality = OCRQuality.ACCEPTABLE
    skip_existing_ocr: bool = True
    tesseract_lang: str = "eng"

    # Monitoring settings
    enable_dashboard: bool = False
    enable_alerts: bool = True

    # Session/auth settings
    user_agent: str = "Epstein-Project-Pipeline/2.0"
    cookies: dict[str, str] | None = None
    headers: dict[str, str] | None = None
    session_key: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> PipelineConfig:
        """Create from dictionary"""
        return cls(
            base_dir=Path(data.get("base_dir", "./epstein_pipeline")),
            download_dir=Path(data.get("download_dir", "./epstein_pipeline/downloads")),
            organized_dir=Path(data.get("organized_dir", "./epstein_pipeline/organized")),
            ocr_output_dir=Path(data.get("ocr_output_dir", "./epstein_pipeline/ocr_output")),
            log_dir=Path(data.get("log_dir", "./epstein_pipeline/logs")),
            max_concurrent_downloads=data.get("max_concurrent_downloads", 3),
            download_chunk_size=data.get("download_chunk_size", 8 * 1024 * 1024),
            enable_checksums=data.get("enable_checksums", True),
            enable_deduplication=data.get("enable_deduplication", True),
            auto_extract_zips=data.get("auto_extract_zips", True),
            max_ocr_workers=data.get("max_ocr_workers", 2),
            ocr_quality_threshold=OCRQuality[
                data.get("ocr_quality_threshold", "ACCEPTABLE").upper()
            ],
            skip_existing_ocr=data.get("skip_existing_ocr", True),
            tesseract_lang=data.get("tesseract_lang", "eng"),
            enable_dashboard=data.get("enable_dashboard", False),
            enable_alerts=data.get("enable_alerts", True),
            user_agent=data.get("user_agent", "Epstein-Project-Pipeline/2.0"),
            cookies=data.get("cookies"),
            headers=data.get("headers"),
            session_key=data.get("session_key"),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "base_dir": str(self.base_dir),
            "download_dir": str(self.download_dir),
            "organized_dir": str(self.organized_dir),
            "ocr_output_dir": str(self.ocr_output_dir),
            "log_dir": str(self.log_dir),
            "max_concurrent_downloads": self.max_concurrent_downloads,
            "download_chunk_size": self.download_chunk_size,
            "enable_checksums": self.enable_checksums,
            "enable_deduplication": self.enable_deduplication,
            "auto_extract_zips": self.auto_extract_zips,
            "max_ocr_workers": self.max_ocr_workers,
            "ocr_quality_threshold": self.ocr_quality_threshold.value,
            "skip_existing_ocr": self.skip_existing_ocr,
            "tesseract_lang": self.tesseract_lang,
            "enable_dashboard": self.enable_dashboard,
            "enable_alerts": self.enable_alerts,
            "user_agent": self.user_agent,
        }


class PipelineOrchestrator:
    """
    Unified pipeline orchestrator that coordinates:
    - Download management
    - File organization
    - OCR processing
    - Monitoring and logging
    """

    def __init__(self, config: PipelineConfig):
        """
        Initialize pipeline orchestrator

        Args:
            config: Pipeline configuration
        """
        self.config = config

        # Create directories
        for directory in [
            config.base_dir,
            config.download_dir,
            config.organized_dir,
            config.ocr_output_dir,
            config.log_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self._init_components()

        # Pipeline state
        self.pipeline_state = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "downloads_completed": 0,
            "files_organized": 0,
            "ocr_completed": 0,
            "total_errors": 0,
        }

        logger.info("Pipeline orchestrator initialized")

    def _init_components(self) -> None:
        """Initialize pipeline components"""
        # Session configuration
        session_config = SessionConfig(
            user_agent=self.config.user_agent,
            cookies=self.config.cookies,
            headers=self.config.headers,
            session_key=self.config.session_key,
            use_session_auth=self.config.session_key is not None,
        )

        # Download manager
        self.download_manager = DownloadManager(
            output_dir=self.config.download_dir,
            max_concurrent=self.config.max_concurrent_downloads,
            chunk_size=self.config.download_chunk_size,
            session_config=session_config,
            progress_callback=self._download_progress_callback,
        )

        # File organizer
        self.file_organizer = FileOrganizer(
            base_dir=self.config.download_dir,
            organized_dir=self.config.organized_dir,
            dedup_enabled=self.config.enable_deduplication,
            auto_extract_zips=self.config.auto_extract_zips,
        )

        # OCR processor
        self.ocr_processor = OCRProcessor(
            output_dir=self.config.ocr_output_dir,
            tesseract_lang=self.config.tesseract_lang,
            max_workers=self.config.max_ocr_workers,
            quality_threshold=self.config.ocr_quality_threshold,
            skip_existing=self.config.skip_existing_ocr,
        )

        # Operation monitor
        self.monitor = OperationMonitor(
            log_dir=self.config.log_dir,
            enable_dashboard=self.config.enable_dashboard,
            enable_alerts=self.config.enable_alerts,
        )

        # Register alert callbacks
        self.monitor.register_alert_callback(self._handle_alert)

    def _download_progress_callback(self, task: DownloadTask) -> None:
        """Callback for download progress updates"""
        # Update monitor with download progress
        # This is called frequently, so we don't update every time
        pass

    def _handle_alert(self, alert) -> None:
        """Handle monitoring alerts"""
        # Log alert
        if alert.level == AlertLevel.CRITICAL:
            logger.critical(f"ALERT: {alert.message}")
        elif alert.level == AlertLevel.ERROR:
            logger.error(f"ALERT: {alert.message}")
        elif alert.level == AlertLevel.WARNING:
            logger.warning(f"ALERT: {alert.message}")

        # Could send notifications here (email, Slack, etc.)

    def add_download_tasks_from_doj(self, dataset_numbers: list[int] | None = None) -> list[str]:
        """
        Add download tasks for DOJ datasets

        Args:
            dataset_numbers: Specific dataset numbers (None = all available)

        Returns:
            List of task IDs
        """
        # This would integrate with the existing epstein_bulk_downloader
        # For now, this is a placeholder for the integration
        logger.info("Adding DOJ download tasks...")

        # TODO: Integrate with scripts/epstein_bulk_downloader.py
        # to auto-discover and create download tasks

        task_ids = []
        # Example task creation would go here

        return task_ids

    def run_download_phase(self, task_ids: list[str] | None = None) -> bool:
        """
        Run download phase

        Args:
            task_ids: Specific task IDs to download (None = all)

        Returns:
            Success status
        """
        logger.info("=== Starting Download Phase ===")

        task_ids = task_ids or list(self.download_manager.tasks.keys())

        if not task_ids:
            logger.warning("No download tasks to process")
            return True

        # Start monitoring
        self.monitor.start_operation(
            OperationType.DOWNLOAD, total_count=len(task_ids), description="Downloading files"
        )

        # Start dashboard if enabled
        if self.config.enable_dashboard:
            self.monitor.start_dashboard()

        try:
            # Download files
            results = self.download_manager.download_batch(
                task_ids=task_ids, verify_checksums=self.config.enable_checksums
            )

            # Update monitoring
            for task_id, (success, error) in results.items():
                task = self.download_manager.tasks[task_id]

                if success:
                    self.monitor.update_progress(
                        OperationType.DOWNLOAD,
                        completed=1,
                        bytes_processed=task.metrics.bytes_downloaded,
                        duration_seconds=task.metrics.duration_seconds,
                    )
                    self.pipeline_state["downloads_completed"] += 1
                else:
                    self.monitor.update_progress(OperationType.DOWNLOAD, failed=1)
                    self.monitor.report_error(
                        OperationType.DOWNLOAD,
                        error or "Unknown error",
                        metadata={"task_id": task_id, "url": task.url},
                    )
                    self.pipeline_state["total_errors"] += 1

            # Complete monitoring
            self.monitor.complete_operation(OperationType.DOWNLOAD)

            # Get statistics
            stats = self.download_manager.get_statistics()
            logger.info(
                f"Download phase completed: {stats['completed']}/{stats['total_tasks']} successful "
                f"({stats['success_rate']:.1f}%)"
            )

            return stats["success_rate"] > 0

        except Exception as e:
            logger.error(f"Download phase failed: {e}")
            self.monitor.report_error(OperationType.DOWNLOAD, f"Phase failure: {str(e)}")
            return False
        finally:
            if self.config.enable_dashboard:
                self.monitor.stop_dashboard()

    def run_organize_phase(self, source: str = "doj_disclosures") -> bool:
        """
        Run file organization phase

        Args:
            source: Source identifier for file naming

        Returns:
            Success status
        """
        logger.info("=== Starting Organization Phase ===")

        # Start monitoring
        # Count files to organize
        files = list(self.config.download_dir.glob("**/*"))
        files = [f for f in files if f.is_file()]

        if not files:
            logger.warning("No files to organize")
            return True

        self.monitor.start_operation(
            OperationType.ORGANIZE, total_count=len(files), description="Organizing files"
        )

        try:
            # Organize directory
            stats = self.file_organizer.organize_directory(
                directory=self.config.download_dir, source=source, recursive=True
            )

            # Update monitoring
            self.monitor.update_progress(
                OperationType.ORGANIZE,
                completed=stats["success"],
                failed=stats["failed"],
                skipped=stats["duplicates"],
            )

            self.pipeline_state["files_organized"] = stats["success"]
            self.pipeline_state["total_errors"] += stats["failed"]

            # Complete monitoring
            self.monitor.complete_operation(OperationType.ORGANIZE)

            logger.info(
                f"Organization phase completed: {stats['success']}/{stats['total']} files organized"
            )

            return stats["success"] > 0

        except Exception as e:
            logger.error(f"Organization phase failed: {e}")
            self.monitor.report_error(OperationType.ORGANIZE, f"Phase failure: {str(e)}")
            return False

    def run_ocr_phase(self) -> bool:
        """
        Run OCR processing phase

        Returns:
            Success status
        """
        logger.info("=== Starting OCR Phase ===")

        # Find PDF files to process
        pdf_files = []
        for category_dir in self.config.organized_dir.glob("*"):
            if category_dir.is_dir():
                pdf_files.extend(category_dir.glob("*.pdf"))

        if not pdf_files:
            logger.warning("No PDF files to process")
            return True

        # Add OCR tasks
        task_ids = self.ocr_processor.add_batch_tasks(pdf_files)

        # Start monitoring
        self.monitor.start_operation(
            OperationType.OCR, total_count=len(task_ids), description="Processing OCR"
        )

        try:
            # Process OCR
            results = self.ocr_processor.process_batch(
                task_ids=task_ids, parallel=self.config.max_ocr_workers > 1
            )

            # Update monitoring
            for task_id, (success, error) in results.items():
                task = self.ocr_processor.tasks[task_id]

                if success:
                    self.monitor.update_progress(
                        OperationType.OCR,
                        completed=1,
                        duration_seconds=task.metrics.duration_seconds,
                    )
                    self.pipeline_state["ocr_completed"] += 1
                else:
                    self.monitor.update_progress(OperationType.OCR, failed=1)
                    self.monitor.report_error(
                        OperationType.OCR,
                        error or "Unknown error",
                        metadata={"task_id": task_id, "file": str(task.input_path)},
                    )
                    self.pipeline_state["total_errors"] += 1

            # Complete monitoring
            self.monitor.complete_operation(OperationType.OCR)

            # Get statistics
            stats = self.ocr_processor.get_statistics()
            logger.info(
                f"OCR phase completed: {stats['completed']}/{stats['total_tasks']} successful "
                f"({stats['success_rate']:.1f}%)"
            )

            return stats["success_rate"] > 0

        except Exception as e:
            logger.error(f"OCR phase failed: {e}")
            self.monitor.report_error(OperationType.OCR, f"Phase failure: {str(e)}")
            return False

    def run_full_pipeline(
        self, skip_download: bool = False, skip_organize: bool = False, skip_ocr: bool = False
    ) -> bool:
        """
        Run the complete pipeline

        Args:
            skip_download: Skip download phase
            skip_organize: Skip organization phase
            skip_ocr: Skip OCR phase

        Returns:
            Success status
        """
        logger.info("=" * 60)
        logger.info("Starting Full Pipeline Execution")
        logger.info("=" * 60)

        pipeline_start = datetime.now(timezone.utc)

        try:
            # Phase 1: Download
            if not skip_download:
                success = self.run_download_phase()
                if not success:
                    logger.error("Download phase failed")
                    return False
            else:
                logger.info("Skipping download phase")

            # Phase 2: Organize
            if not skip_organize:
                success = self.run_organize_phase()
                if not success:
                    logger.error("Organization phase failed")
                    return False
            else:
                logger.info("Skipping organization phase")

            # Phase 3: OCR
            if not skip_ocr:
                success = self.run_ocr_phase()
                if not success:
                    logger.warning("OCR phase had failures, but continuing")
            else:
                logger.info("Skipping OCR phase")

            # Pipeline completed
            pipeline_end = datetime.now(timezone.utc)
            duration = (pipeline_end - pipeline_start).total_seconds()

            self.pipeline_state["completed_at"] = pipeline_end.isoformat()
            self.pipeline_state["duration_seconds"] = duration

            logger.info("=" * 60)
            logger.info("Pipeline Execution Complete")
            logger.info(f"Duration: {duration:.1f} seconds")
            logger.info(f"Downloads: {self.pipeline_state['downloads_completed']}")
            logger.info(f"Organized: {self.pipeline_state['files_organized']}")
            logger.info(f"OCR Completed: {self.pipeline_state['ocr_completed']}")
            logger.info(f"Total Errors: {self.pipeline_state['total_errors']}")
            logger.info("=" * 60)

            # Export reports
            self._export_reports()

            return True

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            return False
        finally:
            # Cleanup
            self.cleanup()

    def _export_reports(self) -> None:
        """Export comprehensive reports"""
        report_dir = self.config.log_dir / "reports"
        report_dir.mkdir(exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        # Pipeline state report
        with open(report_dir / f"pipeline_state_{timestamp}.json", "w") as f:
            json.dump(self.pipeline_state, f, indent=2)

        # Monitoring report
        self.monitor.export_report(report_dir / f"monitoring_{timestamp}.json")

        # OCR report
        self.ocr_processor.export_report(report_dir / f"ocr_{timestamp}.json")

        logger.info(f"Reports exported to: {report_dir}")

    def cleanup(self) -> None:
        """Cleanup resources"""
        self.download_manager.cleanup()
        self.monitor.cleanup()
        logger.info("Pipeline orchestrator cleanup completed")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Epstein Files Pipeline Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline with default settings
  python pipeline_orchestrator.py

  # Run with custom config
  python pipeline_orchestrator.py --config config.json

  # Skip download phase (use existing files)
  python pipeline_orchestrator.py --skip-download

  # Enable dashboard
  python pipeline_orchestrator.py --dashboard
        """,
    )

    parser.add_argument("--config", type=Path, help="Path to configuration JSON file")
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("./epstein_pipeline"),
        help="Base directory for pipeline (default: ./epstein_pipeline)",
    )
    parser.add_argument("--skip-download", action="store_true", help="Skip download phase")
    parser.add_argument("--skip-organize", action="store_true", help="Skip organization phase")
    parser.add_argument("--skip-ocr", action="store_true", help="Skip OCR phase")
    parser.add_argument("--dashboard", action="store_true", help="Enable real-time dashboard")
    parser.add_argument("--session-key", type=str, help="Session authentication key")

    args = parser.parse_args()

    # Load or create configuration
    if args.config and args.config.exists():
        with open(args.config) as f:
            config_data = json.load(f)
        config = PipelineConfig.from_dict(config_data)
    else:
        config = PipelineConfig(
            base_dir=args.base_dir,
            download_dir=args.base_dir / "downloads",
            organized_dir=args.base_dir / "organized",
            ocr_output_dir=args.base_dir / "ocr_output",
            log_dir=args.base_dir / "logs",
            enable_dashboard=args.dashboard,
            session_key=args.session_key,
        )

    # Create orchestrator
    orchestrator = PipelineOrchestrator(config)

    # Run pipeline
    success = orchestrator.run_full_pipeline(
        skip_download=args.skip_download,
        skip_organize=args.skip_organize,
        skip_ocr=args.skip_ocr,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
