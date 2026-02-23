#!/usr/bin/env python3
# =============================================================================
# Script Name: config.py
# Date: 2025-12-23
# Author: cbwinslow + ChatGPT
# Summary:
#   Centralized configuration using Pydantic Settings. Supports .env files.
# =============================================================================

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    db_host: str = Field(default="127.0.0.1", alias="OPENDISCOURSE_DB_HOST")
    db_port: int = Field(default=5432, alias="OPENDISCOURSE_DB_PORT")
    db_name: str = Field(default="opendiscourse", alias="OPENDISCOURSE_DB_NAME")
    db_user: str = Field(default="opendiscourse", alias="OPENDISCOURSE_DB_USER")
    db_password: str = Field(default="change_me", alias="OPENDISCOURSE_DB_PASSWORD")

    storage_root: str = Field(default="./documents", alias="OPENDISCOURSE_STORAGE_ROOT")

    log_level: str = Field(default="INFO", alias="OPENDISCOURSE_LOG_LEVEL")
    log_dir: str = Field(default="./logs", alias="OPENDISCOURSE_LOG_DIR")

    govinfo_api_key: str = Field(default="change_me", alias="GOVINFO_API_KEY")

    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
