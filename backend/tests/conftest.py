"""Shared fixtures. Integration tests need PostgreSQL; they are skipped when it is unreachable."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("GREENCODE_LLM_PROVIDER", "mock")
os.environ.setdefault("GREENCODE_BENCHMARK_REPETITIONS", "5")
os.environ.setdefault("GREENCODE_BENCHMARK_WARMUP_RUNS", "1")
os.environ.setdefault("GREENCODE_SANDBOX_TIMEOUT_SECONDS", "20")

from app.config import get_settings  # noqa: E402


def _db_available() -> bool:
    try:
        import psycopg

        with psycopg.connect(get_settings().benchmark_database_url, connect_timeout=2) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001
        return False


DB_AVAILABLE = _db_available()
requires_db = pytest.mark.skipif(not DB_AVAILABLE, reason="PostgreSQL not reachable")


def _bench_loaded() -> bool:
    if not DB_AVAILABLE:
        return False
    try:
        import psycopg

        s = get_settings()
        with psycopg.connect(s.benchmark_database_url, connect_timeout=2) as conn:
            row = conn.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema = %s", (s.benchmark_schema,)
            ).fetchone()
        return bool(row and row[0] >= 4)
    except Exception:  # noqa: BLE001
        return False


requires_bench_data = pytest.mark.skipif(not _bench_loaded(), reason="bench dataset not loaded")


@pytest.fixture
def mock_provider():
    from app.ai.provider import MockProvider

    return MockProvider()


@pytest.fixture
def db_session():
    from app.db.session import get_sessionmaker, init_db

    init_db()
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.rollback()
        db.close()
