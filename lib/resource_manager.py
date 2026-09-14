#!/usr/bin/env python3
"""
Epstein Files Project - Resource Manager

Comprehensive resource management system with worker pools,
threading, and resource optimization for the document processing pipeline.

Features:
- Dynamic worker pool management
- Resource monitoring and optimization
- Thread-safe resource allocation
- Memory and CPU usage tracking
- Auto-scaling based on system load
- Graceful shutdown and cleanup
"""

import asyncio
import concurrent.futures
import logging
import threading
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from threading import Event, Lock
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import uuid4

import psutil

# Configure logging
logger = logging.getLogger("epstein_resource_manager")


class ResourceType(Enum):
    """Types of resources managed by the system"""

    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    FILE_HANDLES = "file_handles"
    DATABASE_CONNECTIONS = "db_connections"


class WorkerType(Enum):
    """Types of worker pools"""

    DOWNLOAD = "download"
    OCR = "ocr"
    NER = "ner"
    PROCESSING = "processing"
    DATABASE = "database"
    MONITORING = "monitoring"


@dataclass
class ResourceMetrics:
    """Resource usage metrics"""

    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    disk_usage_percent: float
    network_io_mb: float
    active_threads: int
    active_processes: int
    load_average: float


@dataclass
class WorkerPoolConfig:
    """Configuration for worker pools"""

    pool_type: WorkerType
    min_workers: int = 1
    max_workers: int = 10
    target_utilization: float = 0.7  # Target 70% utilization
    scale_up_threshold: float = 0.8  # Scale up when >80% utilized
    scale_down_threshold: float = 0.3  # Scale down when <30% utilized
    scale_up_factor: float = 1.5  # Increase workers by 50%
    scale_down_factor: float = 0.7  # Decrease workers by 30%
    check_interval: float = 30.0  # Check every 30 seconds
    task_timeout: float = 300.0  # 5 minute timeout
    retry_attempts: int = 3
    retry_delay: float = 1.0


@dataclass
class ResourceLimits:
    """System resource limits"""

    max_cpu_percent: float = 80.0
    max_memory_percent: float = 85.0
    max_memory_gb: float = 16.0
    max_disk_usage_percent: float = 90.0
    max_network_mb_per_sec: float = 100.0
    max_file_handles: int = 1000
    max_database_connections: int = 50


class WorkerPool:
    """Managed worker pool with auto-scaling and monitoring"""

    def __init__(self, config: WorkerPoolConfig):
        self.config = config
        self.pool_id = str(uuid4())
        self.executor: Optional[Union[ThreadPoolExecutor, ProcessPoolExecutor]] = None
        self.lock = Lock()
        self.shutdown_event = Event()
        self.active_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.total_task_time = 0.0
        self.metrics_history: List[ResourceMetrics] = []

        # Initialize executor
        self._init_executor()

        # Start monitoring
        self.monitor_thread = threading.Thread(target=self._monitor_pool, daemon=True)
        self.monitor_thread.start()

        logger.info(f"🚀 Worker pool {self.pool_id} ({self.config.pool_type.value}) initialized")

    def _init_executor(self):
        """Initialize the appropriate executor based on worker type"""
        if self.config.pool_type in [WorkerType.OCR, WorkerType.PROCESSING]:
            # Use ProcessPoolExecutor for CPU-intensive tasks
            self.executor = ProcessPoolExecutor(
                max_workers=self.config.max_workers,
                thread_name_prefix=f"{self.config.pool_type.value}_pool",
            )
        else:
            # Use ThreadPoolExecutor for I/O-bound tasks
            self.executor = ThreadPoolExecutor(
                max_workers=self.config.max_workers,
                thread_name_prefix=f"{self.config.pool_type.value}_pool",
            )

    def submit_task(self, func: Callable, *args, **kwargs) -> concurrent.futures.Future:
        """Submit a task to the worker pool"""
        with self.lock:
            if self.shutdown_event.is_set():
                raise RuntimeError("Worker pool is shutting down")

            self.active_tasks += 1

            # Submit task with timeout
            future = self.executor.submit(self._task_wrapper, func, *args, **kwargs)
            future.add_done_callback(self._task_completed)

            return future

    def _task_wrapper(self, func: Callable, *args, **kwargs):
        """Wrapper for task execution with error handling and timing"""
        start_time = time.time()

        try:
            # Execute the task
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            with self.lock:
                self.completed_tasks += 1
                self.total_task_time += execution_time

            logger.debug(f"✅ Task completed in {execution_time:.2f}s")
            return result

        except Exception as e:
            execution_time = time.time() - start_time

            with self.lock:
                self.failed_tasks += 1
                self.total_task_time += execution_time

            logger.error(f"❌ Task failed after {execution_time:.2f}s: {e}")
            raise

    def _task_completed(self, future: concurrent.futures.Future):
        """Callback when task is completed"""
        with self.lock:
            self.active_tasks -= 1

        # Check if we need to scale the pool
        if not self.shutdown_event.is_set():
            self._check_scaling()

    def _check_scaling(self):
        """Check if pool needs scaling based on utilization"""
        utilization = self.get_utilization()

        if utilization > self.config.scale_up_threshold:
            self._scale_up()
        elif utilization < self.config.scale_down_threshold:
            self._scale_down()

    def _scale_up(self):
        """Scale up the worker pool"""
        current_workers = (
            self.executor._max_workers
            if hasattr(self.executor, "_max_workers")
            else self.config.max_workers
        )

        if current_workers < self.config.max_workers:
            new_workers = min(
                self.config.max_workers, int(current_workers * self.config.scale_up_factor)
            )

            logger.info(
                f"📈 Scaling up {self.config.pool_type.value} pool: {current_workers} → {new_workers} workers"
            )

            # For ThreadPoolExecutor, we need to recreate it
            if isinstance(self.executor, ThreadPoolExecutor):
                self._update_thread_pool_max_workers(new_workers)

    def _scale_down(self):
        """Scale down the worker pool"""
        current_workers = (
            self.executor._max_workers
            if hasattr(self.executor, "_max_workers")
            else self.config.max_workers
        )

        if current_workers > self.config.min_workers:
            new_workers = max(
                self.config.min_workers, int(current_workers * self.config.scale_down_factor)
            )

            logger.info(
                f"📉 Scaling down {self.config.pool_type.value} pool: {current_workers} → {new_workers} workers"
            )

            # For ThreadPoolExecutor, we need to recreate it
            if isinstance(self.executor, ThreadPoolExecutor):
                self._update_thread_pool_max_workers(new_workers)

    def _update_thread_pool_max_workers(self, new_max_workers: int):
        """Update ThreadPoolExecutor max workers (limited capability)"""
        # Note: ThreadPoolExecutor doesn't support dynamic resizing
        # We'll log the intended change for monitoring purposes
        logger.debug(
            f"🔄 Would update {self.config.pool_type.value} pool to {new_max_workers} workers"
        )

    def _monitor_pool(self):
        """Monitor pool performance and resource usage"""
        while not self.shutdown_event.is_set():
            try:
                # Collect metrics
                metrics = self._collect_pool_metrics()
                self.metrics_history.append(metrics)

                # Keep only last hour of metrics
                cutoff_time = time.time() - 3600
                self.metrics_history = [
                    m for m in self.metrics_history if m.timestamp > cutoff_time
                ]

                # Log performance summary
                if len(self.metrics_history) % 10 == 0:  # Every 10th check
                    self._log_performance_summary()

                # Sleep until next check
                self.shutdown_event.wait(self.config.check_interval)

            except Exception as e:
                logger.error(f"❌ Pool monitoring error: {e}")
                traceback.print_exc()
                self.shutdown_event.wait(5)  # Wait before retrying

    def _collect_pool_metrics(self) -> ResourceMetrics:
        """Collect current pool and system metrics"""
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        network = psutil.net_io_counters()

        # Pool metrics
        with self.lock:
            active_tasks = self.active_tasks
            utilization = self.get_utilization()

        return ResourceMetrics(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_gb=memory.used / (1024**3),
            disk_usage_percent=disk.percent,
            network_io_mb=(network.bytes_sent + network.bytes_recv) / (1024**2),
            active_threads=threading.active_count(),
            active_processes=len(psutil.pids()),
            load_average=psutil.getloadavg()[0] if hasattr(psutil, "getloadavg") else 0.0,
        )

    def _log_performance_summary(self):
        """Log performance summary"""
        if not self.metrics_history:
            return

        latest = self.metrics_history[-1]
        avg_cpu = sum(m.cpu_percent for m in self.metrics_history) / len(self.metrics_history)
        avg_memory = sum(m.memory_percent for m in self.metrics_history) / len(self.metrics_history)

        logger.info(
            f"📊 Pool {self.config.pool_type.value} - "
            f"Active: {self.active_tasks}, "
            f"Completed: {self.completed_tasks}, "
            f"Failed: {self.failed_tasks}, "
            f"Utilization: {self.get_utilization():.2%}, "
            f"System CPU: {latest.cpu_percent:.1f}%, "
            f"Memory: {latest.memory_percent:.1f}%"
        )

    def get_utilization(self) -> float:
        """Get current pool utilization (0.0 to 1.0)"""
        if self.config.max_workers == 0:
            return 0.0

        with self.lock:
            return min(1.0, self.active_tasks / self.config.max_workers)

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self.lock:
            total_tasks = self.completed_tasks + self.failed_tasks
            avg_task_time = self.total_task_time / total_tasks if total_tasks > 0 else 0.0
            success_rate = self.completed_tasks / total_tasks if total_tasks > 0 else 1.0

        return {
            "pool_id": self.pool_id,
            "pool_type": self.config.pool_type.value,
            "active_tasks": self.active_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "total_task_time": self.total_task_time,
            "avg_task_time": avg_task_time,
            "success_rate": success_rate,
            "utilization": self.get_utilization(),
            "max_workers": self.config.max_workers,
            "metrics_history_size": len(self.metrics_history),
        }

    def shutdown(self):
        """Gracefully shutdown the worker pool"""
        logger.info(f"🛑 Shutting down worker pool {self.pool_id}")

        self.shutdown_event.set()

        if self.executor:
            self.executor.shutdown(wait=True)

        self.monitor_thread.join(timeout=10)

        logger.info(f"✅ Worker pool {self.pool_id} shutdown complete")


class ResourceManager:
    """Central resource manager for the entire system"""

    def __init__(self, resource_limits: Optional[ResourceLimits] = None):
        self.resource_limits = resource_limits or ResourceLimits()
        self.worker_pools: Dict[WorkerType, WorkerPool] = {}
        self.system_monitor_thread: Optional[threading.Thread] = None
        self.shutdown_event = Event()
        self.lock = Lock()

        # Resource monitoring
        self.resource_history: List[ResourceMetrics] = []
        self.last_resource_check = 0.0

        logger.info("🏗️  Resource Manager initialized")

    def create_worker_pool(
        self, pool_type: WorkerType, config: Optional[WorkerPoolConfig] = None
    ) -> WorkerPool:
        """Create a new worker pool"""
        if config is None:
            config = WorkerPoolConfig(pool_type=pool_type)

        pool = WorkerPool(config)
        self.worker_pools[pool_type] = pool

        logger.info(f"✅ Created worker pool: {pool_type.value}")
        return pool

    def get_worker_pool(self, pool_type: WorkerType) -> Optional[WorkerPool]:
        """Get a worker pool by type"""
        return self.worker_pools.get(pool_type)

    def submit_task(
        self, pool_type: WorkerType, func: Callable, *args, **kwargs
    ) -> concurrent.futures.Future:
        """Submit a task to the specified worker pool"""
        pool = self.get_worker_pool(pool_type)

        if not pool:
            raise ValueError(f"Worker pool {pool_type.value} not found")

        # Check resource limits before submitting
        if not self._check_resource_limits():
            raise RuntimeError("System resource limits exceeded")

        return pool.submit_task(func, *args, **kwargs)

    def _check_resource_limits(self) -> bool:
        """Check if system resources are within limits"""
        try:
            # Get current system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Check limits
            if cpu_percent > self.resource_limits.max_cpu_percent:
                logger.warning(
                    f"⚠️  CPU usage {cpu_percent:.1f}% exceeds limit {self.resource_limits.max_cpu_percent}%"
                )
                return False

            if memory.percent > self.resource_limits.max_memory_percent:
                logger.warning(
                    f"⚠️  Memory usage {memory.percent:.1f}% exceeds limit {self.resource_limits.max_memory_percent}%"
                )
                return False

            if disk.percent > self.resource_limits.max_disk_usage_percent:
                logger.warning(
                    f"⚠️  Disk usage {disk.percent:.1f}% exceeds limit {self.resource_limits.max_disk_usage_percent}%"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"❌ Resource limit check failed: {e}")
            return False

    def start_system_monitoring(self):
        """Start system-wide resource monitoring"""
        if self.system_monitor_thread is None:
            self.system_monitor_thread = threading.Thread(target=self._monitor_system, daemon=True)
            self.system_monitor_thread.start()
            logger.info("📊 System monitoring started")

    def _monitor_system(self):
        """Monitor overall system resource usage"""
        while not self.shutdown_event.is_set():
            try:
                # Collect system metrics
                metrics = self._collect_system_metrics()
                self.resource_history.append(metrics)

                # Keep only last 24 hours of metrics
                cutoff_time = time.time() - (24 * 3600)
                self.resource_history = [
                    m for m in self.resource_history if m.timestamp > cutoff_time
                ]

                # Check for resource alerts
                self._check_resource_alerts(metrics)

                # Sleep until next check
                self.shutdown_event.wait(60)  # Check every minute

            except Exception as e:
                logger.error(f"❌ System monitoring error: {e}")
                self.shutdown_event.wait(5)

    def _collect_system_metrics(self) -> ResourceMetrics:
        """Collect system-wide resource metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        network = psutil.net_io_counters()

        return ResourceMetrics(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_gb=memory.used / (1024**3),
            disk_usage_percent=disk.percent,
            network_io_mb=(network.bytes_sent + network.bytes_recv) / (1024**2),
            active_threads=threading.active_count(),
            active_processes=len(psutil.pids()),
            load_average=psutil.getloadavg()[0] if hasattr(psutil, "getloadavg") else 0.0,
        )

    def _check_resource_alerts(self, metrics: ResourceMetrics):
        """Check for resource alerts and take action"""
        alerts = []

        if metrics.cpu_percent > self.resource_limits.max_cpu_percent:
            alerts.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")

        if metrics.memory_percent > self.resource_limits.max_memory_percent:
            alerts.append(f"High memory usage: {metrics.memory_percent:.1f}%")

        if metrics.disk_usage_percent > self.resource_limits.max_disk_usage_percent:
            alerts.append(f"High disk usage: {metrics.disk_usage_percent:.1f}%")

        if alerts:
            logger.warning(f"⚠️  Resource alerts: {', '.join(alerts)}")

            # Take corrective action
            self._take_corrective_action(alerts, metrics)

    def _take_corrective_action(self, alerts: List[str], metrics: ResourceMetrics):
        """Take corrective action for resource alerts"""
        for alert in alerts:
            if "CPU" in alert:
                # Scale down CPU-intensive pools
                self._scale_down_cpu_pools()
            elif "memory" in alert:
                # Scale down memory-intensive pools
                self._scale_down_memory_pools()
            elif "disk" in alert:
                # Clean up temporary files
                self._cleanup_temp_files()

    def _scale_down_cpu_pools(self):
        """Scale down CPU-intensive worker pools"""
        cpu_pools = [WorkerType.OCR, WorkerType.PROCESSING]

        for pool_type in cpu_pools:
            pool = self.get_worker_pool(pool_type)
            if pool:
                current_util = pool.get_utilization()
                if current_util > 0.8:  # Only scale down if highly utilized
                    logger.info(f"🔄 Scaling down CPU pool: {pool_type.value}")
                    # Implementation would depend on pool type

    def _scale_down_memory_pools(self):
        """Scale down memory-intensive worker pools"""
        # Similar to CPU pools but for memory-intensive tasks
        pass

    def _cleanup_temp_files(self):
        """Clean up temporary files to free disk space"""
        import shutil
        import tempfile

        temp_dir = tempfile.gettempdir()

        try:
            # Get disk usage before cleanup
            disk_before = psutil.disk_usage(temp_dir)

            # Clean up old temp files (older than 1 hour)
            cutoff_time = time.time() - 3600

            for item in Path(temp_dir).iterdir():
                if item.stat().st_mtime < cutoff_time:
                    try:
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
                    except Exception as e:
                        logger.debug(f"Failed to clean up {item}: {e}")

            # Log cleanup results
            disk_after = psutil.disk_usage(temp_dir)
            freed_space = (disk_after.free - disk_before.free) / (1024**3)

            if freed_space > 0:
                logger.info(f"🧹 Cleaned up temp files, freed {freed_space:.2f} GB")

        except Exception as e:
            logger.error(f"❌ Temp file cleanup failed: {e}")

    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        with self.lock:
            # Current system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Pool statistics
            pool_stats = {}
            for pool_type, pool in self.worker_pools.items():
                pool_stats[pool_type.value] = pool.get_stats()

            # Resource history summary
            if self.resource_history:
                latest = self.resource_history[-1]
                avg_cpu = sum(m.cpu_percent for m in self.resource_history[-10:]) / min(
                    10, len(self.resource_history)
                )
                avg_memory = sum(m.memory_percent for m in self.resource_history[-10:]) / min(
                    10, len(self.resource_history)
                )
            else:
                latest = None
                avg_cpu = avg_memory = 0.0

            return {
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_used_gb": memory.used / (1024**3),
                    "disk_usage_percent": disk.percent,
                    "active_threads": threading.active_count(),
                    "active_processes": len(psutil.pids()),
                },
                "pools": pool_stats,
                "resource_history_size": len(self.resource_history),
                "latest_metrics": (
                    {
                        "cpu_percent": latest.cpu_percent if latest else 0,
                        "memory_percent": latest.memory_percent if latest else 0,
                        "avg_cpu_10min": avg_cpu,
                        "avg_memory_10min": avg_memory,
                    }
                    if latest
                    else {}
                ),
            }

    def shutdown(self):
        """Gracefully shutdown all worker pools and monitoring"""
        logger.info("🛑 Shutting down Resource Manager")

        self.shutdown_event.set()

        # Shutdown all worker pools
        for pool_type, pool in self.worker_pools.items():
            logger.info(f"🛑 Shutting down {pool_type.value} pool")
            pool.shutdown()

        # Wait for system monitor to finish
        if self.system_monitor_thread:
            self.system_monitor_thread.join(timeout=10)

        logger.info("✅ Resource Manager shutdown complete")


# Global resource manager instance
_resource_manager: Optional[ResourceManager] = None
_resource_manager_lock = Lock()


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager instance"""
    global _resource_manager

    if _resource_manager is None:
        with _resource_manager_lock:
            if _resource_manager is None:
                _resource_manager = ResourceManager()
                _resource_manager.start_system_monitoring()

    return _resource_manager


def create_default_pools() -> ResourceManager:
    """Create default worker pools for the Epstein Files project"""
    rm = get_resource_manager()

    # Download pool (I/O bound)
    download_config = WorkerPoolConfig(
        pool_type=WorkerType.DOWNLOAD,
        min_workers=2,
        max_workers=10,
        target_utilization=0.6,
        check_interval=30.0,
    )
    rm.create_worker_pool(WorkerType.DOWNLOAD, download_config)

    # OCR pool (CPU bound)
    ocr_config = WorkerPoolConfig(
        pool_type=WorkerType.OCR,
        min_workers=1,
        max_workers=4,
        target_utilization=0.7,
        check_interval=60.0,
    )
    rm.create_worker_pool(WorkerType.OCR, ocr_config)

    # NER pool (CPU bound)
    ner_config = WorkerPoolConfig(
        pool_type=WorkerType.NER,
        min_workers=1,
        max_workers=4,
        target_utilization=0.7,
        check_interval=60.0,
    )
    rm.create_worker_pool(WorkerType.NER, ner_config)

    # Processing pool (CPU bound)
    processing_config = WorkerPoolConfig(
        pool_type=WorkerType.PROCESSING,
        min_workers=2,
        max_workers=8,
        target_utilization=0.7,
        check_interval=45.0,
    )
    rm.create_worker_pool(WorkerType.PROCESSING, processing_config)

    # Database pool (I/O bound)
    db_config = WorkerPoolConfig(
        pool_type=WorkerType.DATABASE,
        min_workers=2,
        max_workers=10,
        target_utilization=0.5,
        check_interval=30.0,
    )
    rm.create_worker_pool(WorkerType.DATABASE, db_config)

    # Monitoring pool (I/O bound)
    monitoring_config = WorkerPoolConfig(
        pool_type=WorkerType.MONITORING,
        min_workers=1,
        max_workers=3,
        target_utilization=0.3,
        check_interval=15.0,
    )
    rm.create_worker_pool(WorkerType.MONITORING, monitoring_config)

    logger.info("✅ Created default worker pools")
    return rm


if __name__ == "__main__":
    # Example usage
    import asyncio

    async def example_task(task_id: int, duration: float = 1.0):
        """Example task that simulates work"""
        await asyncio.sleep(duration)
        return f"Task {task_id} completed"

    # Create resource manager with default pools
    rm = create_default_pools()

    # Submit some example tasks
    futures = []
    for i in range(20):
        future = rm.submit_task(WorkerType.PROCESSING, example_task, i, duration=0.5)
        futures.append(future)

    # Wait for all tasks to complete
    for future in concurrent.futures.as_completed(futures):
        try:
            result = future.result()
            print(f"✅ {result}")
        except Exception as e:
            print(f"❌ Task failed: {e}")

    # Print final statistics
    stats = rm.get_system_stats()
    print(f"\n📊 Final Statistics:")
    print(f"System CPU: {stats['system']['cpu_percent']:.1f}%")
    print(f"System Memory: {stats['system']['memory_percent']:.1f}%")

    # Shutdown
    rm.shutdown()
