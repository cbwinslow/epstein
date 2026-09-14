#!/usr/bin/env python3
# =============================================================================
# Script Name: govinfo.py
# Date: 2025-12-23
# Author: cbwinslow + ChatGPT
# Summary:
#   GovInfo ingestion *skeleton*:
#   - validates API key presence
#   - creates a run record
#   - writes audit events
#   - scaffolds storage directories
#
# Next (Part 4):
#   - real GovInfo API + bulk download implementation
#   - resumable checkpoints and dedupe
#   - document upserts and text extraction hooks
# =============================================================================

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from opendiscourse.config import Settings
from sqlalchemy import text
from sqlalchemy.engine import Engine


@dataclass
class GovInfoIngestor:
    settings: Settings
    logger: Any
    engine: Engine
    limit: int = 0

    def _ensure_storage(self) -> None:
        os.makedirs(self.settings.storage_root, exist_ok=True)
        os.makedirs(os.path.join(self.settings.storage_root, "govinfo"), exist_ok=True)

    def _create_run(self) -> str:
        sql = text(
            "INSERT INTO ingestion_runs (source_name, status, cursor_json, stats_json) "
            "VALUES (:source, 'running', '{}'::jsonb, '{}'::jsonb) "
            "RETURNING run_id::text"
        )
        with self.engine.connect() as conn:
            run_id = conn.execute(sql, {"source": "govinfo"}).scalar_one()
            conn.commit()
        return run_id

    def _event(self, run_id: str, level: str, message: str, detail_json: str = "{}") -> None:
        sql = text(
            "INSERT INTO ingestion_events (run_id, level, message, detail_json) "
            "VALUES (:run_id::uuid, :level, :message, :detail_json::jsonb)"
        )
        with self.engine.connect() as conn:
            conn.execute(
                sql,
                {"run_id": run_id, "level": level, "message": message, "detail_json": detail_json},
            )
            conn.commit()

    def run(self) -> None:
        if not self.settings.govinfo_api_key or self.settings.govinfo_api_key == "change_me":
            raise RuntimeError("GOVINFO_API_KEY not set. Put it in .env (copy from .env.example).")

        self._ensure_storage()
        run_id = self._create_run()
        self.logger.info(f"Created ingestion run: {run_id}")
        self._event(run_id, "INFO", "GovInfo ingestion run started")

        self.logger.info("GovInfo skeleton ready. Bulk ingestion to be implemented in Part 4.")
        self._event(run_id, "INFO", "Skeleton ready; bulk download not yet implemented")

        # Mark run paused so we don't pretend completion
        with self.engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE ingestion_runs SET status='paused', finished_at=now() WHERE run_id=:rid::uuid"
                ),
                {"rid": run_id},
            )
            conn.commit()
        self._event(run_id, "INFO", "Run paused (skeleton)")
        self.logger.info("Run paused (skeleton).")
