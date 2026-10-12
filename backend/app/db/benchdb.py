"""Connection helpers for the controlled SQL benchmark dataset (schema ``bench``)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

import psycopg
from psycopg.rows import tuple_row

from app.config import Settings, get_settings


@contextmanager
def bench_connection(settings: Settings | None = None, *, read_only: bool = True,
                     statement_timeout_ms: int | None = None) -> Generator[psycopg.Connection, None, None]:
    settings = settings or get_settings()
    conn = psycopg.connect(settings.benchmark_database_url, row_factory=tuple_row, autocommit=False)
    try:
        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {settings.benchmark_schema}, public")
            timeout = statement_timeout_ms or settings.sql_statement_timeout_ms
            cur.execute(f"SET statement_timeout = {int(timeout)}")
            if read_only:
                cur.execute("SET default_transaction_read_only = on")
        conn.commit()
        yield conn
    finally:
        conn.close()


def explain_json(conn: psycopg.Connection, sql: str, analyze: bool = False) -> dict[str, Any]:
    opts = "ANALYZE, BUFFERS, FORMAT JSON" if analyze else "FORMAT JSON"
    with conn.cursor() as cur:
        cur.execute(f"EXPLAIN ({opts}) {sql}")
        row = cur.fetchone()
    conn.rollback()
    plan = row[0]
    if isinstance(plan, list):
        plan = plan[0]
    return plan


def table_row_estimates(conn: psycopg.Connection, schema: str) -> dict[str, int]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT relname, reltuples::bigint FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = %s AND relkind = 'r'",
            (schema,),
        )
        rows = cur.fetchall()
    conn.rollback()
    return {name: max(int(n), 0) for name, n in rows}


def schema_ddl_summary(conn: psycopg.Connection, schema: str) -> str:
    """A compact, human-readable description of the bench schema for prompts."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.table_name, c.column_name, c.data_type
            FROM information_schema.columns c
            WHERE c.table_schema = %s
            ORDER BY c.table_name, c.ordinal_position
            """,
            (schema,),
        )
        cols = cur.fetchall()
        cur.execute(
            "SELECT tablename, indexdef FROM pg_indexes WHERE schemaname = %s ORDER BY tablename, indexname",
            (schema,),
        )
        idx = cur.fetchall()
    conn.rollback()
    tables: dict[str, list[str]] = {}
    for t, c, d in cols:
        tables.setdefault(t, []).append(f"{c} {d}")
    lines = [f"CREATE TABLE {t} ({', '.join(cs)});" for t, cs in tables.items()]
    lines += [f"-- {d}" for _, d in idx]
    return "\n".join(lines)
