import os
import importlib.util
import types
import pytest
import os


spec = importlib.util.spec_from_file_location("doctor", os.path.join(os.path.dirname(__file__), "..", "scripts", "doctor.py"))
doctor = importlib.util.module_from_spec(spec)
assert spec is not None
spec.loader.exec_module(doctor)  # type: ignore


class DummySocketCM:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_check_postgres_tcp_success(monkeypatch):
    # No DSN, use POSTGRES_HOST/PORT
    monkeypatch.delenv("EPSTEIN_DSN", raising=False)
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")

    monkeypatch.setattr(doctor.socket, "create_connection", lambda *a, **k: DummySocketCM())

    ok, msg = doctor.check_postgres()
    assert ok is True
    assert "TCP reachable" in msg


def test_check_postgres_tcp_failure(monkeypatch):
    monkeypatch.delenv("EPSTEIN_DSN", raising=False)
    monkeypatch.setenv("POSTGRES_HOST", "nohost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")

    def raise_conn(*a, **k):
        raise ConnectionError("failed")

    monkeypatch.setattr(doctor.socket, "create_connection", raise_conn)

    ok, msg = doctor.check_postgres()
    assert ok is False
    assert "failed" in msg


def test_check_postgres_with_dsn_and_psycopg(monkeypatch):
    # Provide DSN and mock psycopg connection and cursor
    monkeypatch.setenv("EPSTEIN_DSN", "postgresql://user:pass@localhost:5432/db")

    # mock TCP
    monkeypatch.setattr(doctor.socket, "create_connection", lambda *a, **k: DummySocketCM())

    class DummyCursor:
        def execute(self, q):
            assert q == "SELECT 1"

        def fetchone(self):
            return (1,)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyConn:
        def cursor(self):
            return DummyCursor()

        def close(self):
            pass

    # Ensure psycopg is present in doctor module and mock connect
    monkeypatch.setattr(doctor, "psycopg", types.SimpleNamespace(connect=lambda dsn, timeout=3: DummyConn()))

    ok, msg = doctor.check_postgres()
    assert ok is True
    assert "SELECT 1" in msg or "responded" in msg
