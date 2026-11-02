#!/usr/bin/env python3
# =============================================================================
# Script Name: cli.py
# Date: 2025-12-23
# Author: cbwinslow + ChatGPT
# Summary:
#   CLI entrypoint for ingestion runs.
# =============================================================================

from __future__ import annotations

import argparse

from opendiscourse.config import Settings
from opendiscourse.db.database import healthcheck, make_engine
from opendiscourse.ingestion.govinfo import GovInfoIngestor
from opendiscourse.logging import setup_logger


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="OpenDiscourse ingestion runner")
    p.add_argument("--source", default="govinfo", choices=["govinfo"], help="Data source to ingest")
    p.add_argument(
        "--dry-run", action="store_true", help="Do not download/write; only validate config"
    )
    p.add_argument("--limit", type=int, default=0, help="Limit number of items (0 = unlimited)")
    return p


def main() -> int:
    args = build_parser().parse_args()
    settings = Settings()
    logger = setup_logger("opendiscourse", settings.log_dir, settings.log_level)

    logger.info("Starting ingestion CLI")
    logger.info(f"Selected source={args.source} dry_run={args.dry_run} limit={args.limit}")

    engine = make_engine(settings.database_url())
    try:
        healthcheck(engine)
        logger.info("Database healthcheck OK")
    except Exception as e:
        logger.error("Database healthcheck FAILED")
        logger.exception(e)
        return 2

    if args.dry_run:
        logger.info("Dry-run complete (no writes).")
        return 0

    if args.source == "govinfo":
        GovInfoIngestor(settings=settings, logger=logger, engine=engine, limit=args.limit).run()
        logger.info("Ingestion finished (skeleton).")
        return 0

    logger.error(f"Unsupported source: {args.source}")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
