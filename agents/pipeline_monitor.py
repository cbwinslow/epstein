"""
Pipeline Monitoring Agent
Specialized agent for monitoring pipeline execution, error detection, and performance tracking.
"""

from typing import List, Dict, Any, Optional
import asyncio
import json
import time
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum


class PipelineStatus(Enum):
    """Pipeline execution status"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PipelineMetrics:
    """Pipeline performance metrics"""
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    running_tasks: int
    average_execution_time: float
    success_rate: float
    throughput: float  # tasks per minute
    last_updated: str


@dataclass
class ErrorPattern:
    """Detected error patterns"""
    error_type: str
    frequency: int
    recent_occurrences: List[str]
    severity: str
    recommended_action: str


class PipelineMonitor:
    """
    Specialized agent for monitoring pipeline execution, detecting errors,
    and providing performance insights and recommendations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.pipeline_status = PipelineStatus.IDLE
        self.active_tasks = {}
        self.completed_tasks = {}
        self.failed_tasks = {}
        self.metrics = PipelineMetrics(
            total_tasks=0,
            completed_tasks=0,
            failed_tasks=0,
            running_tasks=0,
            average_execution_time=0.0,
            success_rate=0.0,
            throughput=0.0,
            last_updated=datetime.now().isoformat()
        )
        self.error_patterns = []
        self.alerts = []
        
    async def start_pipeline_monitoring(self, pipeline_id: str) -> Dict[str, Any]:
        """
        Start monitoring a pipeline execution.
        
        Args:
            pipeline_id: ID of the pipeline to monitor
            
        Returns:
            Dictionary with monitoring start confirmation
        """
        self.pipeline_status = PipelineStatus.RUNNING
        
        # Initialize monitoring data
        self.active_tasks[pipeline_id] = {
            "status": TaskStatus.RUNNING,
            "start_time": datetime.now().isoformat(),
            "tasks": {},
            "progress": 0.0
        }
        
        return {
            "monitoring_started": True,
            "pipeline_id": pipeline_id,
            "status": self.pipeline_status.value,
            "start_time": datetime.now().isoformat(),
            "message": "Pipeline monitoring started successfully"
        }
    
    async def update_task_status(self, pipeline_id: str, task_id: str, 
                               status: str, progress: Optional[float] = None) -> Dict[str, Any]:
        """
        Update task status during pipeline execution.
        
        Args:
            pipeline_id: ID of the pipeline
            task_id: ID of the task to update
            status: New task status
            progress: Task progress percentage (0-100)
            
        Returns:
            Dictionary with update confirmation
        """
        if pipeline_id not in self.active_tasks:
            return {"error": f"Pipeline {pipeline_id} not found in monitoring"}
        
        task_status = TaskStatus(status.lower()) if status.lower() in [e.value for e in TaskStatus] else TaskStatus.PENDING
        
        self.active_tasks[pipeline_id]["tasks"][task_id] = {
            "status": task_status,
            "last_updated": datetime.now().isoformat(),
            "progress": progress or 0.0
        }
        
        # Update overall pipeline progress
        if progress is not None:
            self._update_pipeline_progress(pipeline_id)
        
        # Detect errors
        if task_status == TaskStatus.FAILED:
            await self._detect_error_pattern(pipeline_id, task_id)
        
        return {
            "task_updated": True,
            "pipeline_id": pipeline_id,
            "task_id": task_id,
            "status": task_status.value,
            "progress": progress or 0.0,
            "timestamp": datetime.now().isoformat()
        }
    
    async def complete_pipeline(self, pipeline_id: str) -> Dict[str, Any]:
        """
        Mark pipeline as completed and generate final metrics.
        
        Args:
            pipeline_id: ID of the pipeline to complete
            
        Returns:
            Dictionary with completion metrics and analysis
        """
        if pipeline_id not in self.active_tasks:
            return {"error": f"Pipeline {pipeline_id} not found in monitoring"}
        
        # Move tasks to completed
        self.completed_tasks[pipeline_id] = self.active_tasks[pipeline_id]
        del self.active_tasks[pipeline_id]
        
        # Update metrics
        await self._update_pipeline_metrics(pipeline_id)
        
        # Generate final analysis
        analysis = await self._generate_pipeline_analysis(pipeline_id)
        
        return {
            "pipeline_completed": True,
            "pipeline_id": pipeline_id,
            "completion_time": datetime.now().isoformat(),
            "metrics": self.metrics,
            "analysis": analysis,
            "recommendations": self._generate_pipeline_recommendations(analysis)
        }
    
    async def monitor_pipeline_health(self) -> Dict[str, Any]:
        """
        Monitor overall pipeline health and detect issues.
        
        Returns:
            Dictionary with health status and alerts
        """
        health_status = "healthy"
        alerts = []
        
        # Check for running pipelines
        if self.active_tasks:
            for pipeline_id, pipeline_data in self.active_tasks.items():
                # Check for stuck tasks
                await self._check_for_stuck_tasks(pipeline_id, alerts)
                
                # Check for resource usage
                await self._check_resource_usage(pipeline_id, alerts)
        
        # Check error patterns
        if self.error_patterns:
            for pattern in self.error_patterns:
                if pattern.frequency > 10:  # High frequency errors
                    alerts.append({
                        "type": "error_pattern",
                        "severity": pattern.severity,
                        "message": f"High frequency of {pattern.error_type} errors",
                        "recommendation": pattern.recommended_action,
                        "pipeline_id": pattern.recent_occurrences[0] if pattern.recent_occurrences else "unknown"
                    })
        
        # Update health status based on alerts
        if alerts:
            health_status = "needs_attention" if len(alerts) < 5 else "critical"
        
        return {
            "health_status": health_status,
            "active_pipelines": len(self.active_tasks),
            "completed_pipelines": len(self.completed_tasks),
            "failed_pipelines": len(self.failed_tasks),
            "alerts": alerts,
            "metrics": self.metrics,
            "last_checked": datetime.now().isoformat()
        }
    
    async def analyze_performance_trends(self, hours: int = 24) -> Dict[str, Any]:
        """
        Analyze performance trends over specified time period.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Dictionary with performance trend analysis
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Calculate trends
        trend_analysis = {
            "time_period": f"{hours} hours",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "throughput_trend": self._calculate_throughput_trend(start_time, end_time),
            "success_rate_trend": self._calculate_success_rate_trend(start_time, end_time),
            "execution_time_trend": self._calculate_execution_time_trend(start_time, end_time),
            "error_rate_trend": self._calculate_error_rate_trend(start_time, end_time)
        }
        
        # Generate insights
        insights = self._generate_performance_insights(trend_analysis)
        
        return {
            "performance_trends": trend_analysis,
            "insights": insights,
            "recommendations": self._generate_performance_recommendations(insights),
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    async def detect_anomalies(self) -> Dict[str, Any]:
        """
        Detect anomalies in pipeline execution.
        
        Returns:
            Dictionary with anomaly detection results
        """
        anomalies = []
        
        # Check for abnormal execution times
        if self.metrics.average_execution_time > 300:  # > 5 minutes
            anomalies.append({
                "type": "performance",
                "severity": "medium",
                "issue": "High average execution time",
                "current_value": self.metrics.average_execution_time,
                "threshold": 300,
                "recommendation": "Consider optimizing pipeline configuration"
            })
        
        # Check for low success rate
        if self.metrics.success_rate < 0.8:  # < 80%
            anomalies.append({
                "type": "reliability",
                "severity": "high",
                "issue": "Low success rate",
                "current_value": self.metrics.success_rate,
                "threshold": 0.8,
                "recommendation": "Investigate error patterns and improve error handling"
            })
        
        # Check for low throughput
        if self.metrics.throughput < 1.0:  # < 1 task per minute
            anomalies.append({
