"""
Base Agent Class for Epstein Multi-Agent System

This module provides the base class that all agents should inherit from,
ensuring consistent interfaces and common functionality across the system.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AgentStatus(Enum):
    """Agent operational status"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class AgentCapability(Enum):
    """Standard agent capabilities"""
    DOCUMENT_PROCESSING = "document_processing"
    ENTITY_EXTRACTION = "entity_extraction"
    VECTOR_SEARCH = "vector_search"
    DATABASE_QUERY = "database_query"
    ANALYSIS = "analysis"
    MONITORING = "monitoring"
    ORCHESTRATION = "orchestration"
    CODE_GENERATION = "code_generation"
    DOWNLOADING = "downloading"


@dataclass
class AgentMetadata:
    """Metadata describing an agent"""
    name: str
    version: str
    description: str
    capabilities: list[AgentCapability]
    author: str = "Epstein Project Team"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "capabilities": [c.value for c in self.capabilities],
            "author": self.author,
            "created_at": self.created_at,
            "tags": self.tags,
            "dependencies": self.dependencies
        }


@dataclass
class AgentHealth:
    """Agent health status"""
    status: AgentStatus
    uptime_seconds: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_error: str | None = None
    last_error_timestamp: str | None = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    def to_dict(self) -> dict[str, Any]:
        """Convert health status to dictionary"""
        return {
            "status": self.status.value,
            "uptime_seconds": self.uptime_seconds,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.success_rate,
            "last_error": self.last_error,
            "last_error_timestamp": self.last_error_timestamp
        }


class BaseAgent(ABC):
    """
    Base class for all Epstein agents.

    All agents should inherit from this class and implement the required methods.
    This ensures consistent interfaces and common functionality across the system.
    """

    def __init__(
        self,
        agent_id: str,
        config: dict[str, Any] | None = None
    ):
        """
        Initialize the base agent.

        Args:
            agent_id: Unique identifier for this agent instance
            config: Optional configuration dictionary
        """
        self.agent_id = agent_id
        self.config = config or {}
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{agent_id}")

        # Initialize tracking
        self._start_time = datetime.utcnow()
        self._health = AgentHealth(status=AgentStatus.INITIALIZING)
        self._metadata: AgentMetadata | None = None

        # Initialize state
        self._is_initialized = False
        self._lock = asyncio.Lock()

    @abstractmethod
    def get_metadata(self) -> AgentMetadata:
        """
        Get agent metadata.

        Returns:
            AgentMetadata describing this agent
        """
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the agent.

        Returns:
            True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    async def shutdown(self) -> bool:
        """
        Shutdown the agent gracefully.

        Returns:
            True if shutdown successful, False otherwise
        """
        pass

    async def health_check(self) -> AgentHealth:
        """
        Perform a health check.

        Returns:
            AgentHealth object with current health status
        """
        self._health.uptime_seconds = (
            datetime.utcnow() - self._start_time
        ).total_seconds()
        return self._health

    async def get_capabilities(self) -> list[AgentCapability]:
        """
        Get list of agent capabilities.

        Returns:
            List of AgentCapability enums
        """
        metadata = self.get_metadata()
        return metadata.capabilities

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key (supports dot notation for nested dicts)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    async def _track_request(self, success: bool, error: str | None = None):
        """
        Track a request for health monitoring.

        Args:
            success: Whether the request was successful
            error: Error message if request failed
        """
        async with self._lock:
            self._health.total_requests += 1
            if success:
                self._health.successful_requests += 1
                self._health.status = AgentStatus.READY
            else:
                self._health.failed_requests += 1
                self._health.last_error = error
                self._health.last_error_timestamp = datetime.utcnow().isoformat()
                self._health.status = AgentStatus.ERROR

    def to_dict(self) -> dict[str, Any]:
        """
        Convert agent to dictionary representation.

        Returns:
            Dictionary with agent information
        """
        metadata = self.get_metadata()
        return {
            "agent_id": self.agent_id,
            "metadata": metadata.to_dict(),
            "health": self._health.to_dict(),
            "config": self.config
        }

    def __repr__(self) -> str:
        """String representation of agent"""
        metadata = self.get_metadata()
        return f"{self.__class__.__name__}(id={self.agent_id}, name={metadata.name}, status={self._health.status.value})"


class AgentRegistry:
    """
    Registry for discovering and managing agents.

    Provides a centralized way to register, discover, and retrieve agent instances.
    """

    def __init__(self):
        """Initialize the agent registry"""
        self._agents: dict[str, BaseAgent] = {}
        self._agent_classes: dict[str, type] = {}
        self.logger = logging.getLogger("AgentRegistry")

    def register_agent_class(self, agent_class: type, name: str | None = None):
        """
        Register an agent class for discovery.

        Args:
            agent_class: Agent class to register
            name: Optional name (defaults to class name)
        """
        class_name = name or agent_class.__name__
        self._agent_classes[class_name] = agent_class
        self.logger.info(f"Registered agent class: {class_name}")

    def register_agent_instance(self, agent: BaseAgent):
        """
        Register an agent instance.

        Args:
            agent: Agent instance to register
        """
        self._agents[agent.agent_id] = agent
        self.logger.info(f"Registered agent instance: {agent.agent_id}")

    def get_agent(self, agent_id: str) -> BaseAgent | None:
        """
        Get an agent instance by ID.

        Args:
            agent_id: Agent ID to retrieve

        Returns:
            Agent instance or None if not found
        """
        return self._agents.get(agent_id)

    def get_all_agents(self) -> list[BaseAgent]:
        """
        Get all registered agent instances.

        Returns:
            List of all agent instances
        """
        return list(self._agents.values())

    def get_agents_by_capability(self, capability: AgentCapability) -> list[BaseAgent]:
        """
        Get all agents with a specific capability.

        Args:
            capability: Capability to search for

        Returns:
            List of agents with the specified capability
        """
        agents = []
        for agent in self._agents.values():
            metadata = agent.get_metadata()
            if capability in metadata.capabilities:
                agents.append(agent)
        return agents

    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent instance.

        Args:
            agent_id: Agent ID to unregister

        Returns:
            True if agent was unregistered, False if not found
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            self.logger.info(f"Unregistered agent: {agent_id}")
            return True
        return False

    def list_agent_classes(self) -> list[str]:
        """
        List all registered agent classes.

        Returns:
            List of agent class names
        """
        return list(self._agent_classes.keys())

    def get_registry_info(self) -> dict[str, Any]:
        """
        Get information about the registry.

        Returns:
            Dictionary with registry information
        """
        return {
            "total_instances": len(self._agents),
            "total_classes": len(self._agent_classes),
            "agent_ids": list(self._agents.keys()),
            "agent_classes": list(self._agent_classes.keys())
        }


# Global registry instance
_global_registry = AgentRegistry()


def get_global_registry() -> AgentRegistry:
    """
    Get the global agent registry.

    Returns:
        Global AgentRegistry instance
    """
    return _global_registry


def register_agent(agent: BaseAgent):
    """
    Register an agent with the global registry.

    Args:
        agent: Agent instance to register
    """
    _global_registry.register_agent_instance(agent)


def get_agent(agent_id: str) -> BaseAgent | None:
    """
    Get an agent from the global registry.

    Args:
        agent_id: Agent ID to retrieve

    Returns:
        Agent instance or None if not found
    """
    return _global_registry.get_agent(agent_id)
