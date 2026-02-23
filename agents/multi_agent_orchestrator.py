"""
Multi-Agent Orchestrator
Coordinates multiple specialized agents for comprehensive vector database analysis and troubleshooting.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

# Import all our specialized agents. These are optional at import time - wrap imports
# so tests that only need enums/dataclasses don't fail when heavy optional deps
# (like qdrant_client) are missing.
try:
    from agents.epstein_data_processor import EpsteinDataProcessor
except Exception:  # pragma: no cover - best-effort import
    EpsteinDataProcessor = None

try:
    from agents.vector_db_analyzer import VectorDBAnalyzer
except Exception:  # pragma: no cover
    VectorDBAnalyzer = None

try:
    from agents.db_troubleshooter import DatabaseTroubleshooter
except Exception:  # pragma: no cover
    DatabaseTroubleshooter = None

try:
    from agents.pipeline_monitor import PipelineMonitor, Task, TaskPriority, TaskStatus
except Exception:  # pragma: no cover
    PipelineMonitor = None
    Task = None
    TaskPriority = None
    TaskStatus = None


class _MissingAgent:
    """Placeholder for agents that failed to import due to missing optional deps."""
    def __init__(self, name: str, config: dict[str, Any] | None = None):
        self.name = name
        self.config = config

    def __getattr__(self, item):
        raise RuntimeError(
            f"Agent '{self.name}' is not available because optional dependencies are missing."
        )


class OrchestrationMode(Enum):
    """Orchestration execution modes"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ADAPTIVE = "adaptive"


class AgentStatus(Enum):
    """Agent execution status"""
    IDLE = "idle"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"


@dataclass
class AgentResult:
    """Result from agent execution"""
    agent_name: str
    status: AgentStatus
    result: dict[str, Any]
    execution_time: float
    error_message: str | None = None
    timestamp: datetime = None


@dataclass
class OrchestrationTask:
    """Orchestration task definition"""
    task_id: str
    task_name: str
    required_agents: list[str]
    parameters: dict[str, Any]
    mode: OrchestrationMode
    priority: int = 1
    timeout: int = 300  # 5 minutes
    retry_count: int = 3
    status: AgentStatus | None = None

    def __post_init__(self):
        # Ensure status is an AgentStatus enum; default to PENDING
        if self.status is None:
            self.status = AgentStatus.PENDING
        elif not isinstance(self.status, AgentStatus):
            with contextlib.suppress(Exception):
                self.status = AgentStatus(self.status)


class MultiAgentOrchestrator:
    """
    Orchestrates multiple specialized agents for comprehensive vector database analysis
    and troubleshooting with A2A (Agent-to-Agent) communication capabilities.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Initialize all specialized agents
        self.agents = {
            "epstein_data_processor": (EpsteinDataProcessor(config)
                                       if EpsteinDataProcessor is not None
                                       else _MissingAgent('epstein_data_processor', config)),
            "vector_db_analyzer": (VectorDBAnalyzer(config)
                                   if VectorDBAnalyzer is not None
                                   else _MissingAgent('vector_db_analyzer', config)),
            "db_troubleshooter": (DatabaseTroubleshooter(config)
                                  if DatabaseTroubleshooter is not None
                                  else _MissingAgent('db_troubleshooter', config)),
            "pipeline_monitor": (PipelineMonitor(config)
                                 if PipelineMonitor is not None
                                 else _MissingAgent('pipeline_monitor', config))
        }

        # Orchestration state
        self.tasks = {}
        self.results = {}
        self.agent_status = {name: AgentStatus.IDLE for name in self.agents}
        self.communication_history = []

        # Configuration
        self.default_mode = self.config.get('default_mode', OrchestrationMode.ADAPTIVE)
        self.max_concurrent_tasks = self.config.get('max_concurrent_tasks', 4)
        self.enable_a2a_communication = self.config.get('enable_a2a_communication', True)
        self.enable_error_recovery = self.config.get('enable_error_recovery', True)
        self.communication_timeout = self.config.get('communication_timeout', 30)

        # Performance tracking
        self.execution_metrics = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "average_execution_time": 0.0,
            "agent_utilization": {}
        }

    async def run_comprehensive_analysis(self) -> dict[str, Any]:
        """
        Run comprehensive analysis using all specialized agents.

        Returns:
            Dictionary with comprehensive analysis results
        """
        from epstein.telemetry import get_tracer
        tracer = get_tracer("multiagent.orchestrator")

        try:
            with tracer.start_as_current_span("run_comprehensive_analysis"):
                # Define comprehensive analysis task
                task = OrchestrationTask(
                    task_id="comprehensive_analysis",
                    task_name="Comprehensive Vector Database Analysis",
                    required_agents=list(self.agents.keys()),
                    parameters={},
                    mode=self.default_mode,
                    priority=1
                )

                # Execute the task
                results = await self._execute_task(task)

                # Consolidate and analyze results
                consolidated_result = self._consolidate_results(results)

                # Generate comprehensive report
                report = self._generate_comprehensive_report(consolidated_result)

                return {
                    "task_id": task.task_id,
                    "status": "completed",
                    "results": consolidated_result,
                    "report": report,
                    "execution_metrics": self.execution_metrics,
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            with tracer.start_as_current_span("run_comprehensive_analysis.error"):
                return {
                    "task_id": "comprehensive_analysis",
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }

    def get_agent_status(self) -> dict[str, dict[str, Any]]:
        """Return the current status for all agents as structured dictionaries.

        Each agent entry includes keys like `status`, and optionally `capabilities` or `tools`
        if the agent exposes them. This structure is easier to extend and more informative
        for UIs and telemetry consumers.
        """
        statuses = {}
        for name, status in self.agent_status.items():
            agent = self.agents.get(name)
            capabilities = getattr(agent, "capabilities", None)
            tools = getattr(agent, "tools", None)
            statuses[name] = {
                "status": status.value,
                "capabilities": capabilities if capabilities is not None else [],
                "tools": tools if tools is not None else [],
            }
        return statuses

    async def run_troubleshooting_workflow(self, issue_type: str) -> dict[str, Any]:
        """
        Run troubleshooting workflow for specific issue types.

        Args:
            issue_type: Type of issue to troubleshoot ('vector_db', 'database', 'pipeline', 'performance')

        Returns:
            Dictionary with troubleshooting results
        """
        try:
            # Define troubleshooting workflow based on issue type
            workflow = self._define_troubleshooting_workflow(issue_type)

            # Execute workflow
            results = await self._execute_workflow(workflow)

            # Generate troubleshooting report
            self._generate_troubleshooting_report(results, issue_type)

            return {
                "workflow_id": workflow.get('workflow_id', f"troubleshooting_{issue_type}"),
                "issue_type": issue_type,
                "status": "completed",
                "results": results,
            }
        except Exception as e:
            return {
                "workflow_id": workflow.get('workflow_id', f"troubleshooting_{issue_type}"),
                "issue_type": issue_type,
                "status": "failed",
                "error": str(e),
                "results": {}
            }


    async def coordinate_pipeline_optimization(self) -> dict[str, Any]:
        """
        Coordinate pipeline optimization across monitoring and analysis agents.

        Returns:
            Dictionary with optimization results
        """
        task_id = f"pipeline_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Create coordinated task
        task = Task(
            task_id=task_id,
            task_type="pipeline_optimization",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.PENDING,
            assigned_agents=[
                'pipeline_monitor',
                'vector_db_analyzer',
                'db_troubleshooter'
            ],
            parameters={
                "optimization_scope": "comprehensive",
                "enable_performance_analysis": True,
                "enable_recommendations": True
            }
        )

        # Add task to queue
        await self.task_queue.put(task)
        self.tasks[task_id] = task

        # Wait for completion
        while task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            await asyncio.sleep(1)

        return {
            "task_id": task_id,
            "status": task.status.value,
            "result": task.result,
            "error": task.error,
            "completed_at": task.completed_at
        }

    async def coordinate_document_analysis(self, document_path: str) -> dict[str, Any]:
        """
        Coordinate document analysis across relevant agents.

        Args:
            document_path: Path to the document to analyze

        Returns:
            Dictionary with document analysis results
        """
        task_id = f"document_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Create coordinated task
        task = Task(
            task_id=task_id,
            task_type="document_analysis",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.PENDING,
            assigned_agents=[
                'epstein_data_processor',
                'document_analysis_agent',
                'entity_extraction_agent'
            ],
            parameters={
                "document_path": document_path,
                "analysis_depth": "comprehensive",
                "enable_entity_extraction": True,
                "enable_semantic_analysis": True
            }
        )

        # Add task to queue
        await self.task_queue.put(task)
        self.tasks[task_id] = task

        # Wait for completion
        while task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            await asyncio.sleep(1)

        return {
            "task_id": task_id,
            "status": task.status.value,
            "result": task.result,
            "error": task.error,
            "completed_at": task.completed_at
        }

    async def get_system_status(self) -> dict[str, Any]:
        """
        Get overall system status across all agents.

        Returns:
            Dictionary with system status information
        """
        from epstein.telemetry import get_tracer
        tracer = get_tracer("multiagent.orchestrator")
        with tracer.start_as_current_span("get_system_status"):
            status = {
                "timestamp": datetime.now().isoformat(),
                "agents": {},
                "tasks": {
                    "total": len(self.tasks),
                    "pending": len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
                    "running": len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING]),
                    "completed": len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]),
                    "failed": len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED])
                },
                "queue_size": self.task_queue.qsize()
            }

        # Get individual agent status
        for agent_name, agent in self.agents.items():
            try:
                if hasattr(agent, 'get_status'):
                    agent_status = await agent.get_status()
                else:
                    agent_status = {"status": "active", "last_check": datetime.now().isoformat()}

                status["agents"][agent_name] = agent_status

            except Exception as e:
                status["agents"][agent_name] = {
                    "status": "error",
                    "error": str(e),
                    "last_check": datetime.now().isoformat()
                }

        return status

    async def _process_task_queue(self):
        """Process tasks from the queue"""
        while True:
            try:
                task = await self.task_queue.get()

                # Update task status
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now().isoformat()

                # Process task
                await self._process_task(task)

            except Exception as e:
                self.logger.error(f"Error processing task: {e}")

    async def _process_task(self, task: Any):
        """Process a single task"""
        try:
            # Execute task based on type
            if task.task_type == "comprehensive_analysis":
                result = await self._execute_comprehensive_analysis(task)
            elif task.task_type == "database_troubleshooting":
                result = await self._execute_database_troubleshooting(task)
            elif task.task_type == "pipeline_optimization":
                result = await self._execute_pipeline_optimization(task)
            elif task.task_type == "document_analysis":
                result = await self._execute_document_analysis(task)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")

            # Update task with result
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now().isoformat()
            self.logger.error(f"Task {task.task_id} failed: {e}")

    async def _execute_comprehensive_analysis(self, task: Any) -> dict[str, Any]:
        """Execute comprehensive analysis task"""
        collection_name = task.parameters["collection_name"]
        query_text = task.parameters.get("query_text")

        results = {}

        # Vector database analysis
        if 'vector_db_analyzer' in task.assigned_agents:
            vector_result = await self.agents['vector_db_analyzer'].analyze_all_collections()
            results['vector_analysis'] = vector_result

        # Database troubleshooting
        if 'db_troubleshooter' in task.assigned_agents:
            db_result = await self.agents['db_troubleshooter'].optimize_database()
            results['database_analysis'] = db_result

        # Pipeline monitoring
        if 'pipeline_monitor' in task.assigned_agents:
            monitor_result = await self.agents['pipeline_monitor'].monitor_pipeline_health()
            results['pipeline_monitoring'] = monitor_result

        # Document analysis
        if 'document_analysis_agent' in task.assigned_agents:
            doc_result = await self.agents['document_analysis_agent'].analyze_document_structure(
                f"Collection: {collection_name}"
            )
            results['document_analysis'] = doc_result

        # Entity extraction
        if 'entity_extraction_agent' in task.assigned_agents:
            entity_result = await self.agents['entity_extraction_agent'].extract_entities(
                f"Collection: {collection_name}"
            )
            results['entity_extraction'] = entity_result

        # Query performance testing
        if query_text and 'vector_db_analyzer' in task.assigned_agents:
            perf_result = await self.agents['vector_db_analyzer'].benchmark_query_performance(
                collection_name, query_text
            )
            results['performance_benchmark'] = perf_result

        return {
            "collection_name": collection_name,
            "analysis_timestamp": datetime.now().isoformat(),
            "components": results,
            "summary": self._generate_analysis_summary(results)
        }

    async def _execute_database_troubleshooting(self, task: Any) -> dict[str, Any]:
        """Execute database troubleshooting task"""
        results = {}

        # Database health check
        if 'db_troubleshooter' in task.assigned_agents:
            health_result = await self.agents['db_troubleshooter'].check_database_health()
            results['health_check'] = health_result

        # Index analysis
        if 'db_troubleshooter' in task.assigned_agents:
            index_result = await self.agents['db_troubleshooter'].check_indexes()
            results['index_analysis'] = index_result

        # Table statistics
        if 'db_troubleshooter' in task.assigned_agents:
            table_result = await self.agents['db_troubleshooter'].check_table_statistics()
            results['table_statistics'] = table_result

        # Pipeline monitoring
        if 'pipeline_monitor' in task.assigned_agents:
            monitor_result = await self.agents['pipeline_monitor'].monitor_pipeline_health()
            results['pipeline_monitoring'] = monitor_result

        return {
            "troubleshooting_timestamp": datetime.now().isoformat(),
            "components": results,
            "recommendations": self._generate_troubleshooting_recommendations(results)
        }

    async def _execute_pipeline_optimization(self, task: Any) -> dict[str, Any]:
        """Execute pipeline optimization task"""
        results = {}

        # Pipeline monitoring
        if 'pipeline_monitor' in task.assigned_agents:
            monitor_result = await self.agents['pipeline_monitor'].monitor_pipeline_health()
            results['health_monitoring'] = monitor_result

        # Performance trends
        if 'pipeline_monitor' in task.assigned_agents:
            trends_result = await self.agents['pipeline_monitor'].analyze_performance_trends()
            results['performance_trends'] = trends_result

        # Anomaly detection
        if 'pipeline_monitor' in task.assigned_agents:
            anomaly_result = await self.agents['pipeline_monitor'].detect_anomalies()
            results['anomaly_detection'] = anomaly_result

        # Vector database optimization
        if 'vector_db_analyzer' in task.assigned_agents:
            # Get all collections and optimize them
            collections_result = await self.agents['vector_db_analyzer'].analyze_all_collections()
            if 'collections' in collections_result:
                optimizations = {}
                for collection_name in collections_result['collections']:
                    opt_result = await self.agents['vector_db_analyzer'].optimize_collection(collection_name)
                    optimizations[collection_name] = opt_result
                results['vector_optimizations'] = optimizations

        return {
            "optimization_timestamp": datetime.now().isoformat(),
            "components": results,
            "optimization_plan": self._generate_optimization_plan(results)
        }

    async def _execute_document_analysis(self, task: Any) -> dict[str, Any]:
        """Execute document analysis task"""
        document_path = task.parameters["document_path"]

        results = {}

        # Document processing
        if 'epstein_data_processor' in task.assigned_agents:
            processor_result = await self.agents['epstein_data_processor'].process_document(
                document_path, ["ocr", "extract_text", "ner", "embeddings"]
            )
            results['document_processing'] = processor_result

        # Document analysis
        if 'document_analysis_agent' in task.assigned_agents:
            analysis_result = await self.agents['document_analysis_agent'].analyze_document_structure(document_path)
            results['document_analysis'] = analysis_result

        # Entity extraction
        if 'entity_extraction_agent' in task.assigned_agents:
            entity_result = await self.agents['entity_extraction_agent'].extract_entities(document_path)
            results['entity_extraction'] = entity_result

        return {
            "document_path": document_path,
            "analysis_timestamp": datetime.now().isoformat(),
            "components": results,
            "summary": self._generate_document_summary(results)
        }

    def _generate_analysis_summary(self, results: dict[str, Any]) -> dict[str, Any]:
        """Generate summary of comprehensive analysis"""
        summary = {
            "overall_status": "healthy",
            "key_findings": [],
            "recommendations": [],
            "priority_actions": []
        }

        # Analyze results and generate insights
        for component_name, component_result in results.items():
            if "error" not in component_result:
                summary["key_findings"].append(f"{component_name}: Analysis completed successfully")
            else:
                summary["key_findings"].append(f"{component_name}: {component_result['error']}")
                summary["overall_status"] = "needs_attention"

        return summary

    def _generate_troubleshooting_recommendations(self, results: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate troubleshooting recommendations"""
        recommendations = []

        # Analyze health check results
        if 'health_check' in results:
            health_data = results['health_check']
            if 'database_health' in health_data:
                db_health = health_data['database_health']

                if db_health.get('connection_status') == 'slow':
                    recommendations.append({
                        "type": "performance",
                        "priority": "high",
                        "action": "Optimize database configuration",
                        "description": "Database response time is slow"
                    })

                if db_health.get('blocked_queries', 0) > 0:
                    recommendations.append({
                        "type": "blocking",
                        "priority": "critical",
                        "action": "Investigate blocked queries",
                        "description": f"Found {db_health['blocked_queries']} blocked queries"
                    })

        return recommendations

    def _generate_optimization_plan(self, results: dict[str, Any]) -> dict[str, Any]:
        """Generate optimization plan based on analysis results"""
        plan = {
            "immediate_actions": [],
            "short_term_actions": [],
            "long_term_actions": [],
            "estimated_impact": {}
        }

        # Analyze performance trends
        if 'performance_trends' in results:
            trends = results['performance_trends']
            if 'throughput_trend' in trends and trends['throughput_trend'] < 0:
                plan["immediate_actions"].append("Optimize pipeline throughput")

        # Analyze anomaly detection
        if 'anomaly_detection' in results:
            anomalies = results['anomaly_detection']
            for anomaly in anomalies:
                if anomaly['severity'] == 'high':
                    plan["immediate_actions"].append(anomaly['recommendation'])

        return plan

    def _generate_document_summary(self, results: dict[str, Any]) -> dict[str, Any]:
        """Generate summary of document analysis"""
        summary = {
            "document_type": "unknown",
            "complexity": "unknown",
            "key_entities": [],
            "sentiment": "unknown",
            "quality_score": 0.0
        }

        # Extract information from results
        if 'document_processing' in results:
            processing = results['document_processing']
            if 'results' in processing:
                if 'entities' in processing['results']:
                    summary['key_entities'] = [entity['text'] for entity in processing['results']['entities']]

        if 'document_analysis' in results:
            analysis = results['document_analysis']
            if 'complexity_score' in analysis:
                summary['complexity'] = "high" if analysis['complexity_score'] > 0.7 else "medium" if analysis['complexity_score'] > 0.4 else "low"

        return summary


# OpenAI-compatible function definitions
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "coordinate_comprehensive_analysis",
            "description": "Coordinate comprehensive analysis across all agents for vector database analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "collection_name": {
                        "type": "string",
                        "description": "Name of the vector collection to analyze"
                    },
                    "query_text": {
                        "type": "string",
                        "description": "Optional query text for performance testing"
                    }
                },
                "required": ["collection_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "coordinate_database_troubleshooting",
            "description": "Coordinate database troubleshooting across relevant agents",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "coordinate_pipeline_optimization",
            "description": "Coordinate pipeline optimization across monitoring and analysis agents",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "coordinate_document_analysis",
            "description": "Coordinate document analysis across relevant agents",
            "parameters": {
                "type": "object",
                "properties": {
                    "document_path": {
                        "type": "string",
                        "description": "Path to the document to analyze"
                    }
                },
                "required": ["document_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_status",
            "description": "Get overall system status across all agents",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]


# Agent metadata
AGENT_INFO = {
    "name": "Multi-Agent Orchestrator",
    "description": "Central orchestrator for coordinating multiple specialized agents for comprehensive vector database analysis and troubleshooting",
    "version": "1.0.0",
    "capabilities": [
        "Multi-agent coordination",
        "Comprehensive analysis orchestration",
        "Database troubleshooting coordination",
        "Pipeline optimization coordination",
        "Document analysis coordination",
        "System status monitoring",
        "Task queue management",
        "Result aggregation"
    ],
    "tools": TOOLS
}


if __name__ == "__main__":
    # Example usage
    orchestrator = MultiAgentOrchestrator()

    async def main():
        # Get system status
        status = await orchestrator.get_system_status()
        print("System status:", json.dumps(status, indent=2))

        # Coordinate comprehensive analysis
        analysis_result = await orchestrator.coordinate_comprehensive_analysis("test_collection")
        print("Comprehensive analysis:", json.dumps(analysis_result, indent=2))

        # Coordinate database troubleshooting
        troubleshooting_result = await orchestrator.coordinate_database_troubleshooting()
        print("Database troubleshooting:", json.dumps(troubleshooting_result, indent=2))

        # Coordinate pipeline optimization
        optimization_result = await orchestrator.coordinate_pipeline_optimization()
        print("Pipeline optimization:", json.dumps(optimization_result, indent=2))

    asyncio.run(main())
