"""
Global configuration system for Epstein Files Pipeline.

This module provides a centralized configuration system that:
- Loads settings from environment variables and config files
- Provides defaults for all configurable parameters
- Supports multiple environments (dev, test, prod)
- Is easily reproducible by other users
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from functools import lru_cache
import json


# Base directory - the epstein/ folder
BASE_DIR = Path(__file__).parent.parent.resolve()


@dataclass
class DatabaseConfig:
    """Database configuration."""

    postgres_dsn: Optional[str] = None
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "analysis"
    postgres_password: str = "analysis"
    postgres_db: str = "analysis"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    qdrant_collection: str = "epstein_documents"
    qdrant_vector_size: int = 384

    def __post_init__(self):
        if not self.postgres_dsn:
            self.postgres_dsn = (
                f"postgresql://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )


@dataclass
class MCPConfig:
    """MCP Server configuration."""

    host: str = "0.0.0.0"
    port: int = 8765
    base_url: str = "http://localhost:8765"
    download_dir: str = "./downloads"
    max_concurrent_downloads: int = 5
    retry_attempts: int = 3
    retry_delay: int = 5
    timeout_seconds: int = 60
    user_agent: str = "EpsteinFilesPipeline/1.0"


@dataclass
class PipelineConfig:
    """Pipeline processing configuration."""

    batch_size: int = 10
    chunk_size: int = 512
    chunk_overlap: int = 50
    max_file_size_mb: int = 100
    supported_formats: List[str] = field(
        default_factory=lambda: ["pdf", "txt", "docx", "png", "jpg", "jpeg", "tiff"]
    )

    ocr_engine: str = "tesseract"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ner_model: str = "en_core_web_sm"

    use_gpu: bool = False
    verbose: bool = False


@dataclass
class AgentConfig:
    """Agent system configuration."""

    max_concurrent_tasks: int = 50
    task_timeout: int = 3600
    retry_policy: str = "exponential_backoff"
    load_balancing: str = "round_robin"

    openai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    model_name: str = "gpt-4o-mini"


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "json"
    output: str = "file"
    log_dir: str = "./logs"
    log_file: str = "epstein.log"


@dataclass
class TestConfig:
    """Test configuration."""

    mock_external_apis: bool = True
    use_test_database: bool = True
    test_data_dir: str = "./tests/fixtures"
    postgres_test_dsn: str = "postgresql://test:test@localhost:5432/test"
    qdrant_test_url: str = "http://localhost:6334"
    coverage_threshold: float = 80.0


@dataclass
class Config:
    """Main configuration container."""

    env: str = "development"
    debug: bool = False

    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    test: TestConfig = field(default_factory=TestConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables."""
        config = cls()

        # Environment
        config.env = os.getenv("EPSTEIN_ENV", "development")
        config.debug = os.getenv("EPSTEIN_DEBUG", "false").lower() == "true"

        # Database - override with env vars
        db = config.database
        db.postgres_host = os.getenv("POSTGRES_HOST", db.postgres_host)
        db.postgres_port = int(os.getenv("POSTGRES_PORT", str(db.postgres_port)))
        db.postgres_user = os.getenv("POSTGRES_USER", db.postgres_user)
        db.postgres_password = os.getenv("POSTGRES_PASSWORD", db.postgres_password)
        db.postgres_db = os.getenv("POSTGRES_DB", db.postgres_db)
        db.qdrant_url = os.getenv("QDRANT_URL", db.qdrant_url)
        db.qdrant_api_key = os.getenv("QDRANT_API_KEY")

        # MCP Server
        mcp = config.mcp
        mcp.host = os.getenv("MCP_HOST", mcp.host)
        mcp.port = int(os.getenv("MCP_PORT", str(mcp.port)))
        mcp.base_url = os.getenv("MCP_BASE_URL", mcp.base_url)
        mcp.download_dir = os.getenv("MCP_DOWNLOAD_DIR", mcp.download_dir)
        mcp.max_concurrent_downloads = int(
            os.getenv("MCP_MAX_CONCURRENT", str(mcp.max_concurrent_downloads))
        )

        # Pipeline
        pipeline = config.pipeline
        pipeline.batch_size = int(os.getenv("PIPELINE_BATCH_SIZE", str(pipeline.batch_size)))
        pipeline.chunk_size = int(os.getenv("PIPELINE_CHUNK_SIZE", str(pipeline.chunk_size)))
        pipeline.embedding_model = os.getenv("EMBEDDING_MODEL", pipeline.embedding_model)

        # Agents
        agent = config.agent
        agent.openai_api_key = os.getenv("OPENAI_API_KEY")
        agent.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        agent.model_name = os.getenv("MODEL_NAME", agent.model_name)

        # Logging
        logging_conf = config.logging
        logging_conf.level = os.getenv("LOG_LEVEL", logging_conf.level)
        logging_conf.log_dir = os.getenv("LOG_DIR", logging_conf.log_dir)

        return config

    @classmethod
    def from_file(cls, config_path: Path) -> "Config":
        """Load config from JSON file."""
        with open(config_path) as f:
            data = json.load(f)

        config = cls()

        # Apply file config
        if "database" in data:
            for key, value in data["database"].items():
                if hasattr(config.database, key):
                    setattr(config.database, key, value)

        if "mcp" in data:
            for key, value in data["mcp"].items():
                if hasattr(config.mcp, key):
                    setattr(config.mcp, key, value)

        if "pipeline" in data:
            for key, value in data["pipeline"].items():
                if hasattr(config.pipeline, key):
                    setattr(config.pipeline, key, value)

        # Environment vars override file config
        return cls.from_env()

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary (without secrets)."""
        return {
            "env": self.env,
            "debug": self.debug,
            "database": {
                "postgres_host": self.database.postgres_host,
                "postgres_port": self.database.postgres_port,
                "postgres_db": self.database.postgres_db,
                "qdrant_url": self.database.qdrant_url,
                "qdrant_collection": self.database.qdrant_collection,
            },
            "mcp": {
                "host": self.mcp.host,
                "port": self.mcp.port,
                "base_url": self.mcp.base_url,
                "download_dir": self.mcp.download_dir,
                "max_concurrent_downloads": self.mcp.max_concurrent_downloads,
            },
            "pipeline": {
                "batch_size": self.pipeline.batch_size,
                "chunk_size": self.pipeline.chunk_size,
                "embedding_model": self.pipeline.embedding_model,
                "ocr_engine": self.pipeline.ocr_engine,
            },
            "agent": {
                "model_name": self.agent.model_name,
            },
        }


@lru_cache()
def get_config() -> Config:
    """Get cached config instance."""
    config_file = BASE_DIR / "config.json"
    if config_file.exists():
        return Config.from_file(config_file)
    return Config.from_env()


def reset_config_cache():
    """Reset the config cache (useful for testing)."""
    get_config.cache_clear()


# Default instance for convenience
default_config = get_config()
