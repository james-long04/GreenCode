#!/usr/bin/env python3
"""Load the controlled SQL benchmark dataset (database/seed/bench_dataset.sql)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg  # noqa: E402

from app.config import get_settings  # noqa: E402

SQL_FILE = Path(__file__).resolve().parents[2] / "database" / "seed" / "bench_dataset.sql"

if __name__ == "__main__":
    settings = get_settings()
    with psycopg.connect(settings.benchmark_database_url, autocommit=True) as conn:
        conn.execute(SQL_FILE.read_text())
        n = conn.execute(f"SELECT count(*) FROM {settings.benchmark_schema}.orders").fetchone()[0]
    print(f"bench dataset loaded ({n} orders)")
