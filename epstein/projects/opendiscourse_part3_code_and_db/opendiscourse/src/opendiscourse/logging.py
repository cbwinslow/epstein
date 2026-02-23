#!/usr/bin/env python3
# =============================================================================
# Script Name: logging.py
# Date: 2025-12-23
# Author: cbwinslow + ChatGPT
# Summary:
#   Rich console logging + JSONL file logging.
# =============================================================================

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

from rich.logging import RichHandler


def setup_logger(name: str, log_dir: str, level: str = "INFO") -> logging.Logger:
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    console = RichHandler(rich_tracebacks=True, markup=True)
    console.setLevel(getattr(logging, level.upper(), logging.INFO))

    ts = datetime.utcnow().strftime("%Y%m%d")
    file_path = os.path.join(log_dir, f"{name}-{ts}.jsonl")
    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            payload: Dict[str, Any] = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
            }
            if record.exc_info:
                payload["exc_info"] = self.formatException(record.exc_info)
            return json.dumps(payload, ensure_ascii=False)

    file_handler.setFormatter(JsonFormatter())

    logger.addHandler(console)
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger
