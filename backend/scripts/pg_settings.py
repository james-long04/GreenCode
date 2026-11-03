"""Print the PostgreSQL settings that matter for benchmarking (used by Check-TpchFeasibility.ps1)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg  # noqa: E402

from app.config import get_settings  # noqa: E402

NAMES = ("server_version", "shared_buffers", "work_mem", "maintenance_work_mem", "effective_cache_size",
         "max_parallel_workers_per_gather", "max_worker_processes", "jit", "random_page_cost",
         "wal_level", "synchronous_commit", "huge_pages", "track_io_timing")

with psycopg.connect(get_settings().benchmark_database_url) as c:
    rows = c.execute("SELECT name, setting, unit FROM pg_settings WHERE name = ANY(%s) ORDER BY name", (list(NAMES),))
    for name, setting, unit in rows:
        print(f"   {name:32s} {setting} {unit or ''}")
    print("   database size:", c.execute("SELECT pg_size_pretty(pg_database_size(current_database()))").fetchone()[0])
    print("   config file:  ", c.execute("SHOW config_file").fetchone()[0])
