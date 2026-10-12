"""Benchmark a SQL query against the controlled PostgreSQL dataset.

Measures client-observed execution time over repeated runs (after warm-up so
the buffer cache is in a steady state), the planner's estimated cost and the
actual time / buffer usage from ``EXPLAIN (ANALYZE, BUFFERS)``. Energy is
measured around the repetition loop using the same meter as the Python runner;
because PostgreSQL runs in a separate process the figure is machine-wide and
only meaningful relative to the idle baseline and the paired original run.
"""

from __future__ import annotations

import time
from typing import Any

import psutil
import psycopg

from app.benchmark.energy import estimate_energy
from app.benchmark.runner import BenchmarkOutcome, EnergyContext, environment_snapshot
from app.benchmark.stats import summarise
from app.config import Settings, get_settings
from app.db.benchdb import bench_connection, explain_json


def _pg_backend_process(conn: psycopg.Connection) -> psutil.Process | None:
    try:
        pid = conn.info.backend_pid
        return psutil.Process(pid)
    except Exception:  # noqa: BLE001
        return None


def _plan_metrics(plan: dict[str, Any]) -> dict[str, float]:
    root = plan.get("Plan", {})
    metrics: dict[str, float] = {
        "pg_total_cost": float(root.get("Total Cost", 0.0)),
        "pg_actual_total_ms": float(root.get("Actual Total Time", 0.0)),
        "pg_plan_rows": float(root.get("Plan Rows", 0.0)),
        "pg_actual_rows": float(root.get("Actual Rows", 0.0)),
        "pg_planning_ms": float(plan.get("Planning Time", 0.0)),
        "pg_execution_ms": float(plan.get("Execution Time", 0.0)),
    }
    hit = read = 0.0
    seq_scans = 0

    def walk(p: dict[str, Any]) -> None:
        nonlocal hit, read, seq_scans
        hit += float(p.get("Shared Hit Blocks", 0) or 0)
        read += float(p.get("Shared Read Blocks", 0) or 0)
        if p.get("Node Type") == "Seq Scan":
            seq_scans += 1
        for c in p.get("Plans", []) or []:
            walk(c)

    walk(root)
    metrics["pg_shared_hit_blocks"] = hit
    metrics["pg_shared_read_blocks"] = read
    metrics["pg_seq_scans"] = float(seq_scans)
    return metrics


def benchmark_sql(sql: str, settings: Settings | None = None, energy_ctx: EnergyContext | None = None,
                  repetitions: int | None = None, warmup: int | None = None) -> BenchmarkOutcome:
    settings = settings or get_settings()
    energy_ctx = energy_ctx or EnergyContext(settings)
    reps = repetitions or settings.benchmark_repetitions
    warm = settings.benchmark_warmup_runs if warmup is None else warmup
    env = environment_snapshot(settings)

    try:
        with bench_connection(settings, read_only=True) as conn:
            backend = _pg_backend_process(conn)
            try:
                plan = explain_json(conn, sql, analyze=True)
            except psycopg.Error as err:
                conn.rollback()
                return BenchmarkOutcome(ok=False, error=f"EXPLAIN failed: {err}", failure_type="sql_error",
                                        environment=env)
            metrics = _plan_metrics(plan)

            def _loop() -> tuple[list[float], float, float]:
                samples: list[float] = []
                cpu0 = backend.cpu_times() if backend else None
                rss_peak = 0.0
                with conn.cursor() as cur:
                    for _ in range(warm):
                        cur.execute(sql)
                        cur.fetchall()
                    for _ in range(reps):
                        t0 = time.perf_counter_ns()
                        cur.execute(sql)
                        cur.fetchall()
                        samples.append((time.perf_counter_ns() - t0) / 1e6)
                        if backend:
                            try:
                                rss_peak = max(rss_peak, backend.memory_info().rss)
                            except psutil.Error:
                                pass
                conn.rollback()
                cpu_ms = 0.0
                if backend and cpu0:
                    try:
                        c1 = backend.cpu_times()
                        cpu_ms = ((c1.user - cpu0.user) + (c1.system - cpu0.system)) * 1000
                    except psutil.Error:
                        pass
                return samples, cpu_ms, rss_peak

            try:
                (samples, cpu_ms, rss_peak), energy, wall = energy_ctx.measure(_loop)
            except psycopg.Error as err:
                conn.rollback()
                msg = str(err).strip().splitlines()[0]
                return BenchmarkOutcome(ok=False, error=msg, environment=env,
                                        failure_type="timeout" if "statement timeout" in msg else "sql_error")
    except psycopg.OperationalError as err:
        return BenchmarkOutcome(ok=False, error=f"benchmark database unavailable: {err}",
                                failure_type="sandbox_error", environment=env)

    est = estimate_energy(cpu_seconds=cpu_ms / 1000, wall_seconds=sum(samples) / 1000,
                          peak_rss_bytes=rss_peak, settings=settings)
    return BenchmarkOutcome(
        ok=True, samples_ms=samples, summary=summarise(samples), cpu_time_ms=cpu_ms,
        peak_rss_mb=rss_peak / 1024 / 1024, wall_seconds=wall, energy=list(energy) + [est],
        metrics=metrics, environment=env,
    )
