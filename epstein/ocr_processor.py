#!/usr/bin/env python3
"""
Enhanced OCR Processing Pipeline
Provides OCR with quality validation, metrics, retry logic, and parallel processing.

Author: Epstein Project Team
Date: 2026-02-13
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

import pdfminer.high_level
from pdfminer.layout import LAParams

logger = logging.getLogger(__name__)


class OCRStatus(Enum):
    """Status of OCR processing"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRY = "retry"


class OCRQuality(Enum):
    """Quality assessment of OCR output"""
    EXCELLENT = "excellent"  # >95% confidence
    GOOD = "good"  # 80-95% confidence
    ACCEPTABLE = "acceptable"  # 60-80% confidence
    POOR = "poor"  # 40-60% confidence
    FAILED = "failed"  # <40% confidence


@dataclass
class OCRMetrics:
    """Metrics for OCR processing"""
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    duration_seconds: float = 0.0
    pages_processed: int = 0
    text_extracted_chars: int = 0
    text_extracted_words: int = 0
    confidence_score: float = 0.0
    quality_assessment: OCRQuality = OCRQuality.ACCEPTABLE
    retry_count: int = 0
    error_count: int = 0
    warnings: list[str] = field(default_factory=list)

    def update_duration(self) -> None:
        """Update duration calculation"""
        if self.end_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "pages_processed": self.pages_processed,
            "text_extracted_chars": self.text_extracted_chars,
            "text_extracted_words": self.text_extracted_words,
            "confidence_score": self.confidence_score,
            "quality_assessment": self.quality_assessment.value,
            "retry_count": self.retry_count,
            "error_count": self.error_count,
            "warnings": self.warnings,
        }


@dataclass
class OCRTask:
    """Represents an OCR processing task"""
    input_path: Path
    output_path: Path
    text_output_path: Path | None = None
    status: OCRStatus = OCRStatus.PENDING
    metrics: OCRMetrics = field(default_factory=OCRMetrics)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "input_path": str(self.input_path),
            "output_path": str(self.output_path),
            "text_output_path": str(self.text_output_path) if self.text_output_path else None,
            "status": self.status.value,
            "metrics": self.metrics.to_dict(),
            "metadata": self.metadata,
        }


class OCRProcessor:
    """
    Enhanced OCR processing system with:
    - Quality validation and metrics
    - Automatic retry logic
    - Parallel processing
    - Text extraction and validation
    - Comprehensive error handling
    - Progress tracking
    """

    # Quality thresholds
    QUALITY_THRESHOLDS = {
        OCRQuality.EXCELLENT: 95.0,
        OCRQuality.GOOD: 80.0,
        OCRQuality.ACCEPTABLE: 60.0,
        OCRQuality.POOR: 40.0,
    }

    # Minimum text length for quality assessment
    MIN_TEXT_LENGTH = 100

    def __init__(
        self,
        output_dir: Path,
        tesseract_lang: str = "eng",
        max_workers: int = 2,
        max_retries: int = 3,
        quality_threshold: OCRQuality = OCRQuality.ACCEPTABLE,
        skip_existing: bool = True
    ):
        """
        Initialize OCR processor

        Args:
            output_dir: Directory for OCR outputs
            tesseract_lang: Tesseract language (default: eng)
            max_workers: Maximum parallel workers
            max_retries: Maximum retry attempts for failed OCR
            quality_threshold: Minimum acceptable quality
            skip_existing: Skip files that already exist
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.tesseract_lang = tesseract_lang
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.quality_threshold = quality_threshold
        self.skip_existing = skip_existing

        # Task tracking
        self.tasks: dict[str, OCRTask] = {}

        # Metrics file
        self.metrics_file = self.output_dir / "ocr_metrics.jsonl"

        # Check OCR dependencies
        self._check_dependencies()

        logger.info(
            f"OCR processor initialized: output_dir={output_dir}, "
            f"workers={max_workers}, quality_threshold={quality_threshold.value}"
        )

    def _check_dependencies(self) -> None:
        """Check if required OCR tools are installed"""
        required_tools = ["ocrmypdf", "tesseract", "gs", "qpdf"]
        missing_tools = []

        for tool in required_tools:
            try:
                subprocess.run(
                    [tool, "--version"],
                    capture_output=True,
                    check=True,
                    timeout=5
                )
            except (subprocess.SubprocessError, FileNotFoundError):
                missing_tools.append(tool)

        if missing_tools:
            logger.warning(
                f"Missing OCR dependencies: {', '.join(missing_tools)}. "
                f"Install with: apt-get install {' '.join(missing_tools)}"
            )

    def add_task(self, input_path: Path, output_path: Path | None = None) -> str:
        """
        Add OCR task

        Args:
            input_path: Input PDF path
            output_path: Output PDF path (defaults to output_dir/filename)

        Returns:
            Task ID
        """
        if output_path is None:
            output_path = self.output_dir / input_path.name

        text_output_path = output_path.with_suffix(".txt")

        task = OCRTask(
            input_path=input_path,
            output_path=output_path,
            text_output_path=text_output_path,
        )

        task_id = str(input_path)
        self.tasks[task_id] = task

        logger.info(f"Added OCR task: {input_path.name}")
        return task_id

    def add_batch_tasks(self, input_paths: list[Path]) -> list[str]:
        """Add multiple OCR tasks"""
        return [self.add_task(path) for path in input_paths]

    def check_if_text_searchable(self, pdf_path: Path) -> tuple[bool, int]:
        """
        Check if PDF already has searchable text

        Args:
            pdf_path: Path to PDF

        Returns:
            Tuple of (has_text, character_count)
        """
        try:
            text = pdfminer.high_level.extract_text(
                str(pdf_path),
                laparams=LAParams()
            )

            # Count non-whitespace characters
            text_chars = len([c for c in text if not c.isspace()])

            # Consider searchable if has significant text
            has_text = text_chars > self.MIN_TEXT_LENGTH

            return has_text, text_chars

        except Exception as e:
            logger.error(f"Failed to check text in {pdf_path.name}: {e}")
            return False, 0

    def extract_text(self, pdf_path: Path) -> tuple[bool, str, str | None]:
        """
        Extract text from PDF

        Args:
            pdf_path: Path to PDF

        Returns:
            Tuple of (success, extracted_text, error_message)
        """
        try:
            text = pdfminer.high_level.extract_text(
                str(pdf_path),
                laparams=LAParams()
            )

            return True, text, None

        except Exception as e:
            error_msg = f"Text extraction failed: {str(e)}"
            logger.error(f"{error_msg} for {pdf_path.name}")
            return False, "", error_msg

    def assess_text_quality(self, text: str) -> tuple[OCRQuality, float]:
        """
        Assess quality of extracted text

        Args:
            text: Extracted text

        Returns:
            Tuple of (quality_assessment, confidence_score)
        """
        if not text or len(text) < self.MIN_TEXT_LENGTH:
            return OCRQuality.FAILED, 0.0

        # Calculate various quality metrics
        total_chars = len(text)
        alpha_chars = sum(1 for c in text if c.isalpha())
        digit_chars = sum(1 for c in text if c.isdigit())
        space_chars = sum(1 for c in text if c.isspace())
        special_chars = total_chars - alpha_chars - digit_chars - space_chars

        # Calculate ratios
        alpha_ratio = alpha_chars / total_chars if total_chars > 0 else 0
        special_ratio = special_chars / total_chars if total_chars > 0 else 0

        # Words detection
        words = text.split()
        avg_word_length = sum(len(w) for w in words) / len(words) if words else 0

        # Quality scoring (0-100)
        confidence = 0.0

        # Alpha characters should dominate (40% weight)
        if 0.4 <= alpha_ratio <= 0.9:
            confidence += 40.0 * (alpha_ratio / 0.9)

        # Special characters should be minimal (30% weight)
        if special_ratio < 0.2:
            confidence += 30.0 * (1 - (special_ratio / 0.2))

        # Average word length should be reasonable (30% weight)
        if 3 <= avg_word_length <= 8:
            confidence += 30.0
        elif avg_word_length > 0:
            confidence += 15.0

        # Determine quality level
        quality = OCRQuality.FAILED
        for qual, threshold in sorted(
            self.QUALITY_THRESHOLDS.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            if confidence >= threshold:
                quality = qual
                break

        return quality, confidence

    def run_ocr(self, task_id: str) -> tuple[bool, str | None]:
        """
        Run OCR on a single task

        Args:
            task_id: Task ID

        Returns:
            Tuple of (success, error_message)
        """
        task = self.tasks.get(task_id)
        if not task:
            return False, f"Task {task_id} not found"

        task.status = OCRStatus.IN_PROGRESS
        task.metrics.start_time = datetime.now(UTC)

        try:
            # Check if output already exists
            if self.skip_existing and task.output_path.exists():
                logger.info(f"Skipping existing file: {task.output_path.name}")
                task.status = OCRStatus.SKIPPED
                return True, "Already exists"

            # Check if input has searchable text
            has_text, text_chars = self.check_if_text_searchable(task.input_path)

            if has_text:
                logger.info(
                    f"PDF already has searchable text ({text_chars} chars): {task.input_path.name}"
                )
                # Just copy the file
                task.output_path.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy2(task.input_path, task.output_path)
                task.status = OCRStatus.SKIPPED
                task.metadata["already_searchable"] = True
            else:
                # Run OCR with ocrmypdf
                logger.info(f"Running OCR on: {task.input_path.name}")

                task.output_path.parent.mkdir(parents=True, exist_ok=True)

                cmd = [
                    "ocrmypdf",
                    "--language", self.tesseract_lang,
                    "--output-type", "pdf",
                    "--optimize", "1",
                    "--skip-text",  # Skip pages that already have text
                    "--force-ocr",  # Force OCR on pages without text
                    str(task.input_path),
                    str(task.output_path),
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minute timeout
                )

                if result.returncode != 0:
                    error_msg = f"OCRmyPDF failed: {result.stderr}"
                    logger.error(error_msg)
                    task.status = OCRStatus.FAILED
                    task.metrics.error_count += 1
                    return False, error_msg

                task.metadata["ocr_performed"] = True

            # Extract and validate text
            success, text, error = self.extract_text(task.output_path)

            if not success:
                task.status = OCRStatus.FAILED
                return False, error

            # Save extracted text
            if task.text_output_path:
                task.text_output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(task.text_output_path, "w", encoding="utf-8") as f:
                    f.write(text)

            # Assess quality
            quality, confidence = self.assess_text_quality(text)

            # Update metrics
            task.metrics.text_extracted_chars = len(text)
            task.metrics.text_extracted_words = len(text.split())
            task.metrics.confidence_score = confidence
            task.metrics.quality_assessment = quality
            task.metrics.end_time = datetime.now(UTC)
            task.metrics.update_duration()

            # Check quality threshold
            if self.QUALITY_THRESHOLDS[quality] < self.QUALITY_THRESHOLDS[self.quality_threshold]:
                warning = f"Quality below threshold: {quality.value} (score: {confidence:.1f}%)"
                task.metrics.warnings.append(warning)
                logger.warning(f"{warning} for {task.input_path.name}")

            task.status = OCRStatus.COMPLETED

            logger.info(
                f"OCR completed: {task.input_path.name} - "
                f"Quality: {quality.value} ({confidence:.1f}%), "
                f"Text: {task.metrics.text_extracted_words} words, "
                f"Duration: {task.metrics.duration_seconds:.1f}s"
            )

            # Save metrics
            self._save_metrics(task)

            return True, None

        except subprocess.TimeoutExpired:
            error_msg = "OCR timeout (>10 minutes)"
            logger.error(f"{error_msg} for {task.input_path.name}")
            task.status = OCRStatus.FAILED
            task.metrics.error_count += 1
            return False, error_msg

        except Exception as e:
            error_msg = f"OCR processing error: {str(e)}"
            logger.error(f"{error_msg} for {task.input_path.name}")
            task.status = OCRStatus.FAILED
            task.metrics.error_count += 1
            return False, error_msg

    def run_ocr_with_retry(self, task_id: str) -> tuple[bool, str | None]:
        """
        Run OCR with automatic retries

        Args:
            task_id: Task ID

        Returns:
            Tuple of (success, error_message)
        """
        task = self.tasks.get(task_id)
        if not task:
            return False, f"Task {task_id} not found"

        last_error = None

        for attempt in range(1, self.max_retries + 1):
            task.metrics.retry_count = attempt - 1

            success, error = self.run_ocr(task_id)

            if success or task.status == OCRStatus.SKIPPED:
                return True, None

            last_error = error

            if attempt < self.max_retries:
                backoff = 2 ** min(attempt, 5)  # Exponential backoff
                logger.warning(
                    f"OCR attempt {attempt}/{self.max_retries} failed for {task.input_path.name}. "
                    f"Retrying in {backoff}s..."
                )
                time.sleep(backoff)

        return False, last_error

    def process_batch(
        self,
        task_ids: list[str] | None = None,
        parallel: bool = True
    ) -> dict[str, tuple[bool, str | None]]:
        """
        Process multiple OCR tasks

        Args:
            task_ids: List of task IDs (None = all tasks)
            parallel: Whether to process in parallel

        Returns:
            Dictionary mapping task IDs to (success, error_message) tuples
        """
        task_ids = task_ids or list(self.tasks.keys())
        results = {}

        if parallel and self.max_workers > 1:
            logger.info(f"Processing {len(task_ids)} tasks in parallel (workers={self.max_workers})")

            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self.run_ocr_with_retry, tid): tid
                    for tid in task_ids
                }

                for future in as_completed(futures):
                    task_id = futures[future]
                    try:
                        success, error = future.result()
                        results[task_id] = (success, error)
                    except Exception as e:
                        logger.error(f"Exception processing task {task_id}: {e}")
                        results[task_id] = (False, str(e))
        else:
            logger.info(f"Processing {len(task_ids)} tasks sequentially")

            for task_id in task_ids:
                success, error = self.run_ocr_with_retry(task_id)
                results[task_id] = (success, error)

        return results

    def get_statistics(self) -> dict:
        """Get OCR processing statistics"""
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks.values() if t.status == OCRStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.status == OCRStatus.FAILED)
        skipped = sum(1 for t in self.tasks.values() if t.status == OCRStatus.SKIPPED)
        in_progress = sum(1 for t in self.tasks.values() if t.status == OCRStatus.IN_PROGRESS)

        # Quality distribution
        quality_dist = {}
        for task in self.tasks.values():
            if task.status == OCRStatus.COMPLETED:
                qual = task.metrics.quality_assessment.value
                quality_dist[qual] = quality_dist.get(qual, 0) + 1

        # Calculate averages
        completed_tasks = [t for t in self.tasks.values() if t.status == OCRStatus.COMPLETED]

        avg_duration = 0.0
        avg_confidence = 0.0
        total_text_chars = 0
        total_text_words = 0

        if completed_tasks:
            avg_duration = sum(t.metrics.duration_seconds for t in completed_tasks) / len(completed_tasks)
            avg_confidence = sum(t.metrics.confidence_score for t in completed_tasks) / len(completed_tasks)
            total_text_chars = sum(t.metrics.text_extracted_chars for t in completed_tasks)
            total_text_words = sum(t.metrics.text_extracted_words for t in completed_tasks)

        return {
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "in_progress": in_progress,
            "pending": total - completed - failed - skipped - in_progress,
            "success_rate": (completed / total * 100) if total > 0 else 0,
            "quality_distribution": quality_dist,
            "average_duration_seconds": avg_duration,
            "average_confidence_score": avg_confidence,
            "total_text_extracted_chars": total_text_chars,
            "total_text_extracted_words": total_text_words,
        }

    def _save_metrics(self, task: OCRTask) -> None:
        """Save task metrics to file"""
        try:
            record = {
                "timestamp": datetime.now(UTC).isoformat(),
                "task": task.to_dict()
            }

            with open(self.metrics_file, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

    def export_report(self, output_path: Path) -> None:
        """Export comprehensive OCR report"""
        stats = self.get_statistics()

        report = {
            "generated_at": datetime.now(UTC).isoformat(),
            "statistics": stats,
            "tasks": {tid: task.to_dict() for tid, task in self.tasks.items()},
        }

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"OCR report exported to: {output_path}")
