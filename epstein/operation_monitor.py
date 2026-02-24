#!/usr/bin/env python3
"""
Comprehensive Monitoring and Logging System
Provides real-time progress tracking, metrics collection, and operation audit trail.

Author: Epstein Project Team
Date: 2026-02-13
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskID,
        TextColumn,
        TimeRemainingColumn,
    )
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Create dummy classes
    class Console:
        pass
    class Progress:
        def __init__(self, *args, **kwargs):
            pass
        def add_task(self, *args, **kwargs):
            return None
        def update(self, *args, **kwargs):
            pass
    class Table:
        pass

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of operations to monitor"""
    DOWNLOAD = "download"
    OCR = "ocr"
    EXTRACT = "extract"
    ORGANIZE = "organize"
    VALIDATE = "validate"
    PROCESS = "process"


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Represents a monitoring alert"""
    level: AlertLevel
    message: str
    operation_type: OperationType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "level": self.level.value,
            "message": self.message,
            "operation_type": self.operation_type.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class OperationMetrics:
    """Metrics for an operation"""
    operation_type: OperationType
    total_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    in_progress_count: int = 0
    skipped_count: int = 0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = None
    average_duration_seconds: float = 0.0
    total_bytes_processed: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_count == 0:
            return 0.0
        return (self.completed_count / self.total_count) * 100

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage"""
        if self.total_count == 0:
            return 0.0
        return (self.failed_count / self.total_count) * 100

    @property
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time in seconds"""
        end = self.end_time or datetime.now(timezone.utc)
        return (end - self.start_time).total_seconds()

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "operation_type": self.operation_type.value,
            "total_count": self.total_count,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "in_progress_count": self.in_progress_count,
            "skipped_count": self.skipped_count,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "elapsed_seconds": self.elapsed_seconds,
            "average_duration_seconds": self.average_duration_seconds,
            "total_bytes_processed": self.total_bytes_processed,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class OperationMonitor:
    """
    Comprehensive monitoring system with:
    - Real-time progress tracking
    - Metrics collection for all operations
    - Alert generation and management
    - Audit trail logging
    - Dashboard visualization
    - Performance analytics
    """

    # Alert thresholds
    HIGH_FAILURE_RATE_THRESHOLD = 20.0  # percent
    SLOW_OPERATION_THRESHOLD = 300.0  # seconds
    ERROR_COUNT_THRESHOLD = 10

    def __init__(
        self,
        log_dir: Path,
        enable_dashboard: bool = False,
        enable_alerts: bool = True,
        max_alerts_history: int = 1000
    ):
        """
        Initialize operation monitor

        Args:
            log_dir: Directory for logs and audit trail
            enable_dashboard: Enable real-time dashboard
            enable_alerts: Enable alert generation
            max_alerts_history: Maximum alerts to keep in memory
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.enable_dashboard = enable_dashboard
        self.enable_alerts = enable_alerts
        self.max_alerts_history = max_alerts_history

        # Metrics tracking
        self.metrics: dict[OperationType, OperationMetrics] = {
            op_type: OperationMetrics(operation_type=op_type)
            for op_type in OperationType
        }

        # Alert tracking
        self.alerts: deque[Alert] = deque(maxlen=max_alerts_history)
        self.alert_callbacks: list[Callable[[Alert], None]] = []

        # Audit trail
        self.audit_file = self.log_dir / "operation_audit.jsonl"
        self.metrics_file = self.log_dir / "operation_metrics.json"
        self.alerts_file = self.log_dir / "alerts.jsonl"

        # Progress tracking (for Rich progress bars)
        if RICH_AVAILABLE:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
            )
        else:
            self.progress = Progress()

        self.progress_tasks: dict[str, TaskID] = {}

        # Dashboard
        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None

        self.dashboard_thread: threading.Thread | None = None
        self.dashboard_running = False

        # Thread safety
        self.lock = threading.Lock()

        logger.info(f"Operation monitor initialized: log_dir={log_dir}")

    def start_operation(
        self,
        operation_type: OperationType,
        total_count: int,
        description: str = ""
    ) -> None:
        """
        Start tracking an operation

        Args:
            operation_type: Type of operation
            total_count: Total number of items to process
            description: Human-readable description
        """
        with self.lock:
            metrics = self.metrics[operation_type]
            metrics.total_count = total_count
            metrics.start_time = datetime.now(timezone.utc)
            metrics.end_time = None

            # Create progress bar if dashboard enabled
            if self.enable_dashboard:
                task_id = self.progress.add_task(
                    description or f"{operation_type.value.title()}",
                    total=total_count
                )
                self.progress_tasks[operation_type.value] = task_id

            # Log to audit trail
            self._log_audit({
                "event": "operation_started",
                "operation_type": operation_type.value,
                "total_count": total_count,
                "description": description,
            })

            logger.info(f"Started {operation_type.value} operation: {total_count} items")

    def update_progress(
        self,
        operation_type: OperationType,
        completed: int = 0,
        failed: int = 0,
        skipped: int = 0,
        bytes_processed: int = 0,
        duration_seconds: float = 0.0
    ) -> None:
        """
        Update operation progress

        Args:
            operation_type: Type of operation
            completed: Number of completed items
            failed: Number of failed items
            skipped: Number of skipped items
            bytes_processed: Bytes processed
            duration_seconds: Duration for this update
        """
        with self.lock:
            metrics = self.metrics[operation_type]

            metrics.completed_count += completed
            metrics.failed_count += failed
            metrics.skipped_count += skipped
            metrics.total_bytes_processed += bytes_processed

            # Update average duration
            if completed > 0 and duration_seconds > 0:
                total_ops = metrics.completed_count
                if total_ops > 0:
                    metrics.average_duration_seconds = (
                        (metrics.average_duration_seconds * (total_ops - completed) +
                         duration_seconds * completed) / total_ops
                    )

            # Update in-progress count
            metrics.in_progress_count = (
                metrics.total_count -
                metrics.completed_count -
                metrics.failed_count -
                metrics.skipped_count
            )

            # Update progress bar
            if self.enable_dashboard and operation_type.value in self.progress_tasks:
                task_id = self.progress_tasks[operation_type.value]
                self.progress.update(
                    task_id,
                    completed=metrics.completed_count + metrics.failed_count + metrics.skipped_count
                )

            # Check for alerts
            if self.enable_alerts:
                self._check_alert_conditions(operation_type)

    def complete_operation(self, operation_type: OperationType) -> None:
        """Mark operation as complete"""
        with self.lock:
            metrics = self.metrics[operation_type]
            metrics.end_time = datetime.now(timezone.utc)
            metrics.in_progress_count = 0

            # Log completion
            self._log_audit({
                "event": "operation_completed",
                "operation_type": operation_type.value,
                "metrics": metrics.to_dict(),
            })

            # Save metrics
            self._save_metrics()

            logger.info(
                f"Completed {operation_type.value} operation: "
                f"{metrics.completed_count}/{metrics.total_count} successful "
                f"({metrics.success_rate:.1f}%)"
            )

    def report_error(
        self,
        operation_type: OperationType,
        error_message: str,
        metadata: dict | None = None
    ) -> None:
        """
        Report an error

        Args:
            operation_type: Type of operation
            error_message: Error message
            metadata: Additional metadata
        """
        with self.lock:
            metrics = self.metrics[operation_type]
            metrics.errors.append(error_message)

            # Generate alert if enabled
            if self.enable_alerts:
                alert = Alert(
                    level=AlertLevel.ERROR,
                    message=error_message,
                    operation_type=operation_type,
                    metadata=metadata or {}
                )
                self._add_alert(alert)

            # Log to audit trail
            self._log_audit({
                "event": "error",
                "operation_type": operation_type.value,
                "error_message": error_message,
                "metadata": metadata or {},
            })

    def report_warning(
        self,
        operation_type: OperationType,
        warning_message: str,
        metadata: dict | None = None
    ) -> None:
        """Report a warning"""
        with self.lock:
            metrics = self.metrics[operation_type]
            metrics.warnings.append(warning_message)

            # Generate alert if enabled
            if self.enable_alerts:
                alert = Alert(
                    level=AlertLevel.WARNING,
                    message=warning_message,
                    operation_type=operation_type,
                    metadata=metadata or {}
                )
                self._add_alert(alert)

            # Log to audit trail
            self._log_audit({
                "event": "warning",
                "operation_type": operation_type.value,
                "warning_message": warning_message,
                "metadata": metadata or {},
            })

    def _check_alert_conditions(self, operation_type: OperationType) -> None:
        """Check if alert conditions are met"""
        metrics = self.metrics[operation_type]

        # High failure rate alert
        if metrics.failure_rate > self.HIGH_FAILURE_RATE_THRESHOLD:
            alert = Alert(
                level=AlertLevel.CRITICAL,
                message=f"High failure rate: {metrics.failure_rate:.1f}%",
                operation_type=operation_type,
                metadata={"failure_count": metrics.failed_count, "total": metrics.total_count}
            )
            self._add_alert(alert)

        # Slow operation alert
        if metrics.average_duration_seconds > self.SLOW_OPERATION_THRESHOLD:
            alert = Alert(
                level=AlertLevel.WARNING,
                message=f"Slow operation detected: {metrics.average_duration_seconds:.1f}s average",
                operation_type=operation_type,
                metadata={"average_duration": metrics.average_duration_seconds}
            )
            self._add_alert(alert)

        # High error count alert
        if len(metrics.errors) > self.ERROR_COUNT_THRESHOLD:
            alert = Alert(
                level=AlertLevel.ERROR,
                message=f"High error count: {len(metrics.errors)} errors",
                operation_type=operation_type,
                metadata={"error_count": len(metrics.errors)}
            )
            self._add_alert(alert)

    def _add_alert(self, alert: Alert) -> None:
        """Add an alert"""
        self.alerts.append(alert)

        # Save to file
        with open(self.alerts_file, "a") as f:
            f.write(json.dumps(alert.to_dict()) + "\n")

        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

        # Log based on severity
        if alert.level == AlertLevel.CRITICAL:
            logger.critical(f"[{alert.operation_type.value}] {alert.message}")
        elif alert.level == AlertLevel.ERROR:
            logger.error(f"[{alert.operation_type.value}] {alert.message}")
        elif alert.level == AlertLevel.WARNING:
            logger.warning(f"[{alert.operation_type.value}] {alert.message}")
        else:
            logger.info(f"[{alert.operation_type.value}] {alert.message}")

    def register_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """Register a callback for alerts"""
        self.alert_callbacks.append(callback)

    def get_metrics(self, operation_type: OperationType | None = None) -> dict:
        """
        Get metrics

        Args:
            operation_type: Specific operation type (None = all)

        Returns:
            Dictionary of metrics
        """
        with self.lock:
            if operation_type:
                return self.metrics[operation_type].to_dict()

            return {
                op_type.value: metrics.to_dict()
                for op_type, metrics in self.metrics.items()
            }

    def get_recent_alerts(self, count: int = 10, level: AlertLevel | None = None) -> list[Alert]:
        """Get recent alerts"""
        with self.lock:
            alerts = list(self.alerts)

            if level:
                alerts = [a for a in alerts if a.level == level]

            return alerts[-count:]

    def _log_audit(self, event: dict) -> None:
        """Log event to audit trail"""
        try:
            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **event
            }

            with open(self.audit_file, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def _save_metrics(self) -> None:
        """Save current metrics to file"""
        try:
            metrics_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metrics": self.get_metrics(),
            }

            with open(self.metrics_file, "w") as f:
                json.dump(metrics_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

    def generate_dashboard_table(self) -> Table:
        """Generate dashboard table for display"""
        table = Table(title="Operation Monitoring Dashboard", show_header=True)

        table.add_column("Operation", style="cyan")
        table.add_column("Total", justify="right")
        table.add_column("Completed", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Success %", justify="right")
        table.add_column("Elapsed", justify="right")
        table.add_column("Avg Duration", justify="right")

        with self.lock:
            for op_type, metrics in self.metrics.items():
                if metrics.total_count == 0:
                    continue

                table.add_row(
                    op_type.value.title(),
                    str(metrics.total_count),
                    str(metrics.completed_count),
                    str(metrics.failed_count),
                    f"{metrics.success_rate:.1f}%",
                    f"{metrics.elapsed_seconds:.1f}s",
                    f"{metrics.average_duration_seconds:.1f}s",
                )

        return table

    def generate_alerts_table(self, max_alerts: int = 5) -> Table:
        """Generate recent alerts table"""
        table = Table(title="Recent Alerts", show_header=True)

        table.add_column("Level", style="bold")
        table.add_column("Operation")
        table.add_column("Message")
        table.add_column("Time")

        recent_alerts = self.get_recent_alerts(max_alerts)

        for alert in reversed(recent_alerts):
            level_style = {
                AlertLevel.CRITICAL: "bold red",
                AlertLevel.ERROR: "red",
                AlertLevel.WARNING: "yellow",
                AlertLevel.INFO: "blue",
            }.get(alert.level, "")

            table.add_row(
                alert.level.value.upper(),
                alert.operation_type.value,
                alert.message,
                alert.timestamp.strftime("%H:%M:%S"),
                style=level_style
            )

        return table

    def start_dashboard(self, refresh_rate: float = 1.0) -> None:
        """Start real-time dashboard in background thread"""
        if not self.enable_dashboard or not RICH_AVAILABLE:
            logger.warning("Dashboard not available (Rich library not installed)")
            return

        self.dashboard_running = True

        def dashboard_loop():
            with Live(
                self.generate_dashboard_table(),
                console=self.console,
                refresh_per_second=refresh_rate
            ) as live:
                while self.dashboard_running:
                    layout = Layout()
                    layout.split_column(
                        Layout(self.generate_dashboard_table(), name="metrics"),
                        Layout(self.generate_alerts_table(), name="alerts"),
                    )
                    live.update(layout)
                    time.sleep(1.0 / refresh_rate)

        self.dashboard_thread = threading.Thread(target=dashboard_loop, daemon=True)
        self.dashboard_thread.start()

        logger.info("Dashboard started")

    def stop_dashboard(self) -> None:
        """Stop dashboard"""
        self.dashboard_running = False

        if self.dashboard_thread:
            self.dashboard_thread.join(timeout=2.0)

        logger.info("Dashboard stopped")

    def export_report(self, output_path: Path) -> None:
        """Export comprehensive monitoring report"""
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metrics": self.get_metrics(),
            "recent_alerts": [a.to_dict() for a in self.get_recent_alerts(50)],
            "alert_summary": {
                "total": len(self.alerts),
                "by_level": defaultdict(int),
                "by_operation": defaultdict(int),
            }
        }

        # Count alerts by level and operation
        for alert in self.alerts:
            report["alert_summary"]["by_level"][alert.level.value] += 1
            report["alert_summary"]["by_operation"][alert.operation_type.value] += 1

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Monitoring report exported to: {output_path}")

    def cleanup(self) -> None:
        """Cleanup resources"""
        self.stop_dashboard()
        self._save_metrics()
        logger.info("Operation monitor cleanup completed")
