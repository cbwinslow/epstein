#!/usr/bin/env python3
# =============================================================================
# Script Name: database.py
# Date: 2025-12-23
# Author: cbwinslow + ChatGPT
# Summary:
#   SQLAlchemy engine/session utilities with safe connection checks.
# =============================================================================

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def make_engine(db_url: str) -> Engine:
    return create_engine(db_url, pool_pre_ping=True, future=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def healthcheck(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        conn.commit()


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
