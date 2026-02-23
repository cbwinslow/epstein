"""
Pipeline Monitor Agent
Specialized agent for monitoring pipeline execution, health checks, and performance optimization.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import psutil


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineHealth(Enum):
    """Pipeline health status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class TaskInfo:
    """Information about a pipeline task"""
    task_id: str
    task_name: str
    status: TaskStatus
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration: float | None = None
    error_message: str | None = None
    progress: float = 0.0
    resource_usage: dict[str, Any] | None = None


@dataclass
class PipelineMetrics:
    """Pipeline performance metrics"""
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    running_tasks: int
    average_duration: float
    success_rate: float
    throughput: float  # tasks per minute
    last_updated: datetime


class PipelineMonitor:
    """
    Specialized agent for monitoring pipeline execution, health checks, and performance optimization.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.tasks = {}
        self.metrics = PipelineMetrics(
            total_tasks=0,
            completed_tasks=0,
            failed_tasks=0,
            running_tasks=0,
            average_duration=0.0,
            success_rate=0.0,
            throughput=0.0,
            last_updated=datetime.now()
        )

        # Configuration
        self.health_check_interval = self.config.get('health_check_interval', 60)
        self.task_timeout = self.config.get('task_timeout', 3600)  # 1 hour
        self.max_concurrent_tasks = self.config.get('max_concurrent_tasks', 10)
        self.enable_resource_monitoring = self.config.get('enable_resource_monitoring', True)
        self.alert_thresholds = self.config.get('alert_thresholds', {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'task_failure_rate': 0.1,
            'task_duration': 300.0  # 5 minutes
        })

        # Alerting
        self.alerts = []
        self.health_history = []

    async def monitor_pipeline_health(self) -> dict[str, Any]:
        """
        Perform comprehensive pipeline health check.

        Returns:
            Dictionary with health check results
        """
        try:
            # Get system resource usage
            resource_usage = self._get_resource_usage()

            # Analyze task status
            task_analysis = self._analyze_task_status()

            # Calculate pipeline health score
            health_score = self._calculate_health_score(resource_usage, task_analysis)

            # Determine overall health status
            health_status = self._determine_health_status(health_score, resource_usage, task_analysis)

            # Generate recommendations
            recommendations = self._generate_health_recommendations(resource_usage, task_analysis)

            # Check for alerts
            alerts = self._check_alerts(resource_usage, task_analysis)

            # Update metrics
            self._update_metrics(task_analysis)

            health_check_result = {
                "health_status": health_status.value,
                "health_score": health_score,
                "resource_usage": resource_usage,
                "task_analysis": task_analysis,
                "recommendations": recommendations,
                "alerts": alerts,
                "metrics": {
                    "total_tasks": self.metrics.total_tasks,
                    "completed_tasks": self.metrics.completed_tasks,
                    "failed_tasks": self.metrics.failed_tasks,
                    "running_tasks": self.metrics.running_tasks,
                    "success_rate": self.metrics.success_rate,
                    "average_duration": self.metrics.average_duration,
                    "throughput": self.metrics.throughput
                },
                "check_timestamp": datetime.now().isoformat()
            }

            # Store health history
            self.health_history.append(health_check_result)
            if len(self.health_history) > 100:  # Keep last 100 health checks
                self.health_history.pop(0)

            return health_check_result

        except Exception as e:
            return {"error": f"Health check failed: {e}"}

    async def monitor_task_execution(self, task_id: str, task_name: str) -> dict[str, Any]:
        """
        Monitor a specific task execution.

        Args:
            task_id: Unique identifier for the task
            task_name: Name of the task being monitored

        Returns:
            Dictionary with task monitoring results
        """
        try:
            # Create task info
            task_info = TaskInfo(
                task_id=task_id,
                task_name=task_name,
                status=TaskStatus.RUNNING,
                start_time=datetime.now()
            )

            self.tasks[task_id] = task_info

            # Simulate task monitoring (in real implementation, this would monitor actual task)
            await self._simulate_task_execution(task_id)

            # Update metrics
            self._update_task_metrics(task_info)

            return {
                "task_id": task_id,
                "task_name": task_name,
                "status": task_info.status.value,
                "start_time": task_info.start_time.isoformat() if task_info.start_time else None,
                "end_time": task_info.end_time.isoformat() if task_info.end_time else None,
                "duration": task_info.duration,
                "progress": task_info.progress,
                "resource_usage": task_info.resource_usage,
                "monitoring_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"error": f"Task monitoring failed: {e}"}

    async def analyze_performance_trends(self) -> dict[str, Any]:
        """
        Analyze performance trends and identify optimization opportunities.

        Returns:
            Dictionary with performance analysis results
        """
        try:
            if len(self.health_history) < 5:
                return {"error": "Insufficient data for trend analysis"}

            # Extract trends from health history
            trends = {
                "cpu_usage_trend": self._calculate_trend([h['resource_usage']['cpu_usage'] for h in self.health_history]),
                "memory_usage_trend": self._calculate_trend([h['resource_usage']['memory_usage'] for h in self.health_history]),
                "task_success_rate_trend": self._calculate_trend([h['metrics']['success_rate'] for h in self.health_history]),
                "average_duration_trend": self._calculate_trend([h['metrics']['average_duration'] for h in self.health_history]),
                "throughput_trend": self._calculate_trend([h['metrics']['throughput'] for h in self.health_history])
            }

            # Identify anomalies
            anomalies = self._identify_anomalies()

            # Generate optimization recommendations
            recommendations = self._generate_performance_recommendations(trends, anomalies)

            return {
                "trends": trends,
                "anomalies": anomalies,
                "recommendations": recommendations,
                "analysis_period": f"{len(self.health_history)} health checks",
                "analysis_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"error": f"Performance analysis failed: {e}"}

    async def optimize_pipeline_performance(self) -> dict[str, Any]:
        """
        Provide comprehensive pipeline optimization recommendations.

        Returns:
            Dictionary with optimization recommendations
        """
        try:
            # Get current health status
            health_result = await self.monitor_pipeline_health()

            # Analyze performance trends
            performance_result = await self.analyze_performance_trends()

            # Check resource utilization
            resource_analysis = self._analyze_resource_utilization()

            # Generate optimization plan
            optimization_plan = self._generate_optimization_plan(
                health_result, performance_result, resource_analysis
            )

            # Estimate impact
            estimated_impact = self._estimate_optimization_impact(optimization_plan)

            return {
                "current_status": health_result,
                "performance_analysis": performance_result,
                "resource_analysis": resource_analysis,
                "optimization_plan": optimization_plan,
                "estimated_impact": estimated_impact,
                "optimization_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"error": f"Pipeline optimization failed: {e}"}

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        """
        Get status of a specific task.

        Args:
            task_id: Unique identifier for the task

        Returns:
            Dictionary with task status information
        """
        if task_id not in self.tasks:
            return {"error": f"Task {task_id} not found"}

        task_info = self.tasks[task_id]

        return {
            "task_id": task_id,
            "task_name": task_info.task_name,
            "status": task_info.status.value,
            "start_time": task_info.start_time.isoformat() if task_info.start_time else None,
            "end_time": task_info.end_time.isoformat() if task_info.end_time else None,
            "duration": task_info.duration,
            "progress": task_info.progress,
            "error_message": task_info.error_message,
            "resource_usage": task_info.resource_usage,
            "status_timestamp": datetime.now().isoformat()
        }

    def list_tasks(self, status: TaskStatus | None = None) -> list[dict[str, Any]]:
        """
        List all tasks, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of task information dictionaries
        """
        tasks = []
        for task_id, task_info in self.tasks.items():
            if status is None or task_info.status == status:
                tasks.append({
                    "task_id": task_id,
                    "task_name": task_info.task_name,
                    "status": task_info.status.value,
                    "start_time": task_info.start_time.isoformat() if task_info.start_time else None,
                    "end_time": task_info.end_time.isoformat() if task_info.end_time else None,
                    "duration": task_info.duration,
                    "progress": task_info.progress
                })

        return tasks

    def _get_resource_usage(self) -> dict[str, Any]:
        """Get current system resource usage"""
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                "cpu_usage": cpu_usage,
                "memory_usage": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_usage": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Failed to get resource usage: {e}")
            return {
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "memory_available_gb": 0.0,
                "disk_usage": 0.0,
                "disk_free_gb": 0.0,
                "timestamp": datetime.now().isoformat()
            }

    def _analyze_task_status(self) -> dict[str, Any]:
        """Analyze current task status"""
        total_tasks = len(self.tasks)
        completed_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.COMPLETED)
        failed_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.FAILED)
        running_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.RUNNING)

        # Calculate average duration for completed tasks
        completed_durations = [task.duration for task in self.tasks.values()
                             if task.status == TaskStatus.COMPLETED and task.duration]
        average_duration = sum(completed_durations) / len(completed_durations) if completed_durations else 0.0

        # Calculate success rate
        success_rate = completed_tasks / total_tasks if total_tasks > 0 else 0.0

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "running_tasks": running_tasks,
            "average_duration": average_duration,
            "success_rate": success_rate,
            "pending_tasks": total_tasks - completed_tasks - failed_tasks - running_tasks
        }

    def _calculate_health_score(self, resource_usage: dict[str, Any],
                              task_analysis: dict[str, Any]) -> float:
        """Calculate overall pipeline health score (0-100)"""
        score = 100.0

        # Deduct points for resource issues
        if resource_usage['cpu_usage'] > self.alert_thresholds['cpu_usage']:
            score -= min((resource_usage['cpu_usage'] - self.alert_thresholds['cpu_usage']) * 2, 30)

        if resource_usage['memory_usage'] > self.alert_thresholds['memory_usage']:
            score -= min((resource_usage['memory_usage'] - self.alert_thresholds['memory_usage']) * 2, 25)

        if resource_usage['disk_usage'] > self.alert_thresholds['disk_usage']:
            score -= min((resource_usage['disk_usage'] - self.alert_thresholds['disk_usage']) * 2, 20)

        # Deduct points for task issues
        if task_analysis['success_rate'] < (1 - self.alert_thresholds['task_failure_rate']):
            score -= min((1 - task_analysis['success_rate']) * 50, 40)

        if task_analysis['average_duration'] > self.alert_thresholds['task_duration']:
            score -= min((task_analysis['average_duration'] - self.alert_thresholds['task_duration']) * 0.1, 15)

        return max(0.0, score)

    def _determine_health_status(self, health_score: float, resource_usage: dict[str, Any],
                               task_analysis: dict[str, Any]) -> PipelineHealth:
        """Determine overall pipeline health status"""
        if health_score >= 80:
            return PipelineHealth.HEALTHY
        elif health_score >= 50:
            return PipelineHealth.WARNING
        else:
            return PipelineHealth.CRITICAL

    def _generate_health_recommendations(self, resource_usage: dict[str, Any],
                                       task_analysis: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate health-based recommendations"""
        recommendations = []

        # CPU recommendations
        if resource_usage['cpu_usage'] > self.alert_thresholds['cpu_usage']:
            recommendations.append({
                "type": "resource",
                "priority": "high",
                "issue": f"High CPU usage ({resource_usage['cpu_usage']:.1f}%)",
                "recommendation": "Consider scaling up resources or optimizing CPU-intensive tasks"
            })

        # Memory recommendations
        if resource_usage['memory_usage'] > self.alert_thresholds['memory_usage']:
            recommendations.append({
                "type": "resource",
                "priority": "high",
                "issue": f"High memory usage ({resource_usage['memory_usage']:.1f}%)",
                "recommendation": "Consider increasing memory or optimizing memory usage"
            })

        # Task performance recommendations
        if task_analysis['success_rate'] < 0.9:
            recommendations.append({
                "type": "task_performance",
                "priority": "medium",
                "issue": f"Low success rate ({task_analysis['success_rate']:.1%})",
                "recommendation": "Investigate failed tasks and improve error handling"
            })

        if task_analysis['average_duration'] > self.alert_thresholds['task_duration']:
            recommendations.append({
                "type": "task_performance",
                "priority": "medium",
                "issue": f"High average task duration ({task_analysis['average_duration']:.1f}s)",
                "recommendation": "Optimize task execution or increase parallelism"
            })

        return recommendations

    def _check_alerts(self, resource_usage: dict[str, Any],
                      task_analysis: dict[str, Any]) -> list[dict[str, Any]]:
        """Check for alerts based on thresholds"""
        alerts = []

        # CPU alert
        if resource_usage['cpu_usage'] > self.alert_thresholds['cpu_usage']:
            alerts.append({
                "type": "cpu_usage",
                "severity": "warning" if resource_usage['cpu_usage'] < 90 else "critical",
                "message": f"CPU usage is {resource_usage['cpu_usage']:.1f}%",
                "threshold": self.alert_thresholds['cpu_usage']
            })

        # Memory alert
        if resource_usage['memory_usage'] > self.alert_thresholds['memory_usage']:
            alerts.append({
                "type": "memory_usage",
                "severity": "warning" if resource_usage['memory_usage'] < 95 else "critical",
                "message": f"Memory usage is {resource_usage['memory_usage']:.1f}%",
                "threshold": self.alert_thresholds['memory_usage']
            })

        # Task failure rate alert
        if task_analysis['success_rate'] < (1 - self.alert_thresholds['task_failure_rate']):
            alerts.append({
                "type": "task_failure_rate",
                "severity": "warning" if task_analysis['success_rate'] > 0.8 else "critical",
                "message": f"Task failure rate is {(1 - task_analysis['success_rate']):.1%}",
                "threshold": self.alert_thresholds['task_failure_rate']
            })

        return alerts

    def _update_metrics(self, task_analysis: dict[str, Any]):
        """Update pipeline metrics"""
        self.metrics.total_tasks = task_analysis['total_tasks']
        self.metrics.completed_tasks = task_analysis['completed_tasks']
        self.metrics.failed_tasks = task_analysis['failed_tasks']
        self.metrics.running_tasks = task_analysis['running_tasks']
        self.metrics.average_duration = task_analysis['average_duration']
        self.metrics.success_rate = task_analysis['success_rate']

        # Calculate throughput (tasks per minute)
        if self.metrics.completed_tasks > 0:
            time_span = (datetime.now() - self.health_history[0]['check_timestamp']).total_seconds() / 60
            self.metrics.throughput = self.metrics.completed_tasks / max(time_span, 1)

        self.metrics.last_updated = datetime.now()

    def _update_task_metrics(self, task_info: TaskInfo):
        """Update metrics for a specific task"""
        if task_info.status == TaskStatus.COMPLETED:
            self.metrics.completed_tasks += 1
        elif task_info.status == TaskStatus.FAILED:
            self.metrics.failed_tasks += 1

        self.metrics.total_tasks = len(self.tasks)
        self.metrics.running_tasks = sum(1 for task in self.tasks.values() if task.status == TaskStatus.RUNNING)

        # Update average duration
        completed_tasks = [task for task in self.tasks.values()
                          if task.status == TaskStatus.COMPLETED and task.duration]
        if completed_tasks:
            self.metrics.average_duration = sum(task.duration for task in completed_tasks) / len(completed_tasks)

        # Update success rate
        self.metrics.success_rate = self.metrics.completed_tasks / self.metrics.total_tasks if self.metrics.total_tasks > 0 else 0.0

    async def _simulate_task_execution(self, task_id: str):
        """Simulate task execution (for demonstration purposes)"""
        task_info = self.tasks[task_id]

        try:
            # Simulate task progress
            for progress in [25, 50, 75, 90, 100]:
                await asyncio.sleep(0.5)  # Simulate work
                task_info.progress = progress

                # Simulate resource usage
                if self.enable_resource_monitoring:
                    task_info.resource_usage = self._get_resource_usage()

            # Complete task
            task_info.status = TaskStatus.COMPLETED
            task_info.end_time = datetime.now()
            task_info.duration = (task_info.end_time - task_info.start_time).total_seconds()

        except Exception as e:
            task_info.status = TaskStatus.FAILED
            task_info.end_time = datetime.now()
            task_info.duration = (task_info.end_time - task_info.start_time).total_seconds()
            task_info.error_message = str(e)

    def _calculate_trend(self, values: list[float]) -> dict[str, Any]:
        """Calculate trend from a list of values"""
        if len(values) < 2:
            return {"trend": "insufficient_data", "direction": "unknown"}

        # Simple linear regression for trend calculation
        n = len(values)
        x = list(range(n))

        # Calculate slope
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(xi * yi for xi, yi in zip(x, values, strict=False))
        sum_x2 = sum(xi * xi for xi in x)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

        # Determine trend direction
        if abs(slope) < 0.01:
            trend = "stable"
        elif slope > 0:
            trend = "increasing"
        else:
            trend = "decreasing"

        return {
            "trend": trend,
            "direction": "up" if slope > 0 else "down" if slope < 0 else "stable",
            "slope": slope,
            "current_value": values[-1],
            "previous_value": values[-2] if len(values) > 1 else values[-1]
        }

    def _identify_anomalies(self) -> list[dict[str, Any]]:
        """Identify anomalies in health history"""
        anomalies = []

        # Check for sudden changes in resource usage
        if len(self.health_history) >= 3:
            recent_cpu = [h['resource_usage']['cpu_usage'] for h in self.health_history[-3:]]
            if max(recent_cpu) - min(recent_cpu) > 20:  # 20% change
                anomalies.append({
                    "type": "cpu_spike",
                    "severity": "medium",
                    "description": "Sudden CPU usage spike detected",
                    "values": recent_cpu
                })

        # Check for task failure rate anomalies
        if len(self.health_history) >= 3:
            recent_success_rates = [h['metrics']['success_rate'] for h in self.health_history[-3:]]
            if min(recent_success_rates) < 0.8:  # Less than 80% success rate
                anomalies.append({
                    "type": "low_success_rate",
                    "severity": "high",
                    "description": "Consistently low task success rate",
                    "values": [f"{rate:.1%}" for rate in recent_success_rates]
                })

        return anomalies

    def _generate_performance_recommendations(self, trends: dict[str, Any],
                                           anomalies: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Generate performance optimization recommendations"""
        recommendations = []

        # CPU trend recommendations
        if trends['cpu_usage_trend']['trend'] == 'increasing':
            recommendations.append({
                "type": "cpu_optimization",
                "priority": "high",
                "issue": "CPU usage is trending upward",
                "recommendation": "Consider optimizing CPU-intensive tasks or scaling resources"
            })

        # Memory trend recommendations
        if trends['memory_usage_trend']['trend'] == 'increasing':
            recommendations.append({
                "type": "memory_optimization",
                "priority": "medium",
                "issue": "Memory usage is trending upward",
                "recommendation": "Consider memory optimization or increasing available memory"
            })

        # Task performance recommendations
        if trends['task_success_rate_trend']['trend'] == 'decreasing':
            recommendations.append({
                "type": "task_reliability",
                "priority": "high",
                "issue": "Task success rate is decreasing",
                "recommendation": "Improve error handling and task reliability"
            })

        # Anomaly-based recommendations
        for anomaly in anomalies:
            if anomaly['type'] == 'cpu_spike':
                recommendations.append({
                    "type": "resource_monitoring",
                    "priority": "medium",
                    "issue": "CPU usage spikes detected",
                    "recommendation": "Implement CPU usage monitoring and alerting"
                })
            elif anomaly['type'] == 'low_success_rate':
                recommendations.append({
                    "type": "task_improvement",
                    "priority": "high",
                    "issue": "Low task success rate",
                    "recommendation": "Investigate and fix failing tasks"
                })

        return recommendations

    def _analyze_resource_utilization(self) -> dict[str, Any]:
        """Analyze resource utilization patterns"""
        if len(self.health_history) < 5:
            return {"error": "Insufficient data for resource analysis"}

        # Calculate average resource usage
        avg_cpu = sum(h['resource_usage']['cpu_usage'] for h in self.health_history) / len(self.health_history)
        avg_memory = sum(h['resource_usage']['memory_usage'] for h in self.health_history) / len(self.health_history)
        avg_disk = sum(h['resource_usage']['disk_usage'] for h in self.health_history) / len(self.health_history)

        # Calculate resource efficiency
        resource_efficiency = {
            "cpu_efficiency": max(0, 100 - avg_cpu),
            "memory_efficiency": max(0, 100 - avg_memory),
            "disk_efficiency": max(0, 100 - avg_disk),
            "overall_efficiency": (max(0, 100 - avg_cpu) + max(0, 100 - avg_memory) + max(0, 100 - avg_disk)) / 3
        }

        return {
            "average_usage": {
                "cpu": avg_cpu,
                "memory": avg_memory,
                "disk": avg_disk
            },
            "efficiency": resource_efficiency,
            "utilization_pattern": self._determine_utilization_pattern(avg_cpu, avg_memory, avg_disk),
            "analysis_timestamp": datetime.now().isoformat()
        }

    def _determine_utilization_pattern(self, avg_cpu: float, avg_memory: float, avg_disk: float) -> str:
        """Determine resource utilization pattern"""
        if avg_cpu > 80 and avg_memory > 80:
            return "high_utilization_bottleneck"
        elif avg_cpu > 80:
            return "cpu_bottleneck"
        elif avg_memory > 80:
            return "memory_bottleneck"
        elif avg_disk > 90:
            return "disk_bottleneck"
        elif avg_cpu > 60 or avg_memory > 60:
            return "moderate_utilization"
        else:
            return "low_utilization"

    def _generate_optimization_plan(self, health_result: dict[str, Any],
                                  performance_result: dict[str, Any],
                                  resource_analysis: dict[str, Any]) -> dict[str, Any]:
        """Generate comprehensive optimization plan"""
        plan = {
            "immediate_actions": [],
            "short_term_actions": [],
            "long_term_actions": [],
            "resource_optimization": {},
            "performance_optimization": {}
        }

        # Immediate actions based on health status
        if health_result['health_status'] == 'critical':
            plan['immediate_actions'].append("Investigate critical health issues")

        # Resource optimization
        if resource_analysis['utilization_pattern'] == 'high_utilization_bottleneck':
            plan['resource_optimization']['cpu'] = "Scale up resources or optimize CPU usage"
            plan['resource_optimization']['memory'] = "Increase memory or optimize memory usage"
            plan['short_term_actions'].append("Implement resource scaling")

        # Performance optimization
        if 'trends' in performance_result:
            trends = performance_result['trends']
            if trends['task_success_rate_trend']['trend'] == 'decreasing':
                plan['performance_optimization']['reliability'] = "Improve task error handling"
                plan['short_term_actions'].append("Enhance error handling mechanisms")

        return plan

    def _estimate_optimization_impact(self, optimization_plan: dict[str, Any]) -> dict[str, Any]:
        """Estimate potential impact of optimizations"""
        impact = {
            "performance_improvement": "unknown",
            "resource_efficiency": "unknown",
            "reliability_improvement": "unknown",
            "maintenance_reduction": "unknown"
        }

        # Estimate based on optimization plan
        immediate_actions = len(optimization_plan.get('immediate_actions', []))
        len(optimization_plan.get('short_term_actions', []))

        if immediate_actions > 2:
            impact['performance_improvement'] = "20-40%"
            impact['resource_efficiency'] = "15-30%"
        elif immediate_actions > 0:
            impact['performance_improvement'] = "10-20%"
            impact['resource_efficiency'] = "5-15%"

        return impact


# OpenAI-compatible function definitions
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "monitor_pipeline_health",
            "description": "Perform comprehensive pipeline health check",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "monitor_task_execution",
            "description": "Monitor a specific task execution",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Unique identifier for the task"
                    },
                    "task_name": {
                        "type": "string",
                        "description": "Name of the task being monitored"
                    }
                },
                "required": ["task_id", "task_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_performance_trends",
            "description": "Analyze performance trends and identify optimization opportunities",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_pipeline_performance",
            "description": "Provide comprehensive pipeline optimization recommendations",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_task_status",
            "description": "Get status of a specific task",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Unique identifier for the task"
                    }
                },
                "required": ["task_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "List all tasks, optionally filtered by status",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Optional status filter (pending, running, completed, failed, cancelled)",
                        "enum": ["pending", "running", "completed", "failed", "cancelled"]
                    }
                }
            }
        }
    }
]


# Agent metadata
AGENT_INFO = {
    "name": "Pipeline Monitor",
    "description": "Specialized agent for monitoring pipeline execution, health checks, and performance optimization",
    "version": "1.0.0",
    "capabilities": [
        "Pipeline health monitoring",
        "Task execution tracking",
        "Performance trend analysis",
        "Resource utilization analysis",
        "Alert generation",
        "Optimization recommendations"
    ],
    "tools": TOOLS
}


if __name__ == "__main__":
    # Example usage
    monitor = PipelineMonitor()

    async def main():
        # Monitor pipeline health
        health_result = await monitor.monitor_pipeline_health()
        print("Pipeline Health:", json.dumps(health_result, indent=2))

        # Monitor a task
        task_result = await monitor.monitor_task_execution("task_001", "Document Processing")
        print("Task Monitoring:", json.dumps(task_result, indent=2))

        # Analyze performance trends
        trend_result = await monitor.analyze_performance_trends()
        print("Performance Trends:", json.dumps(trend_result, indent=2))

        # Optimize pipeline performance
        optimization_result = await monitor.optimize_pipeline_performance()
        print("Pipeline Optimization:", json.dumps(optimization_result, indent=2))

        # List tasks
        tasks = monitor.list_tasks()
        print("All Tasks:", json.dumps(tasks, indent=2))

    asyncio.run(main())
