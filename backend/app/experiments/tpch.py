"""Laboratory experiments on the TPC-H-derived dataset.

Work packages (see docs/protocol.md):

  wp1  baseline          22 standard queries, default meter, chosen power plan
  wp2  meter overhead    same queries under meter = none | lhm@0.1 | lhm@0.5 | codecarbon
  wp3  power management  same queries, one condition per power plan / mode overlay
  wp4  complex queries   hand-written heavier queries with known anti-patterns
  wp5  optimised         wp4 queries through the GreenCode pipeline (AI-only vs GreenCode)

Every measurement is one ``LabRun`` row: (work package, query, condition, pass). The
runner is resumable: a (wp, query, condition, pass) that already has a completed row is
skipped, so an interrupted night can be continued with the same command.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

import psycopg
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.benchmark.energy import codecarbon_available, lhm_available
from app.benchmark.runner import EnergyContext, environment_snapshot
from app.benchmark.sql_runner import benchmark_sql
from app.config import Settings, get_settings
from app.db.benchdb import bench_connection
from app.db.models import LabRun

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
TPCH_DIR = ROOT / "benchmarks" / "tpch"
WORK_PACKAGES = ("wp1", "wp2", "wp3", "wp4", "wp5")


@dataclass(frozen=True)
class Query:
    id: str           # q01 .. q22 or c01 ..
    title: str
    sql: str
    path: Path


@dataclass(frozen=True)
class Condition:
    """One experimental condition: which meter, and a free label for the power plan etc."""
    label: str                 # stored in LabRun.condition, e.g. "meter=lhm@0.1;plan=balanced"
    meter: str = "lhm"         # none | lhm | codecarbon | estimate
    poll_seconds: float | None = None


def _read_query(path: Path) -> Query:
    text = path.read_text(encoding="utf-8")
    title = ""
    for line in text.splitlines():
        if line.startswith("--"):
            title = line.lstrip("- ").strip()
            break
    return Query(id=path.stem, title=title, sql=text, path=path)


def load_queries(kind: str = "standard") -> list[Query]:
    """``standard`` = q01..q22 in benchmarks/tpch; ``complex`` = benchmarks/tpch/complex/*.sql."""
    d = TPCH_DIR if kind == "standard" else TPCH_DIR / "complex"
    return [_read_query(p) for p in sorted(d.glob("*.sql"))]


def tpch_settings(settings: Settings | None = None, schema: str | None = None) -> Settings:
    """A settings copy pointed at the TPC-H schema, so the SQL runner and pipeline use it."""
    settings = settings or get_settings()
    # TPC-H queries at SF1 can take tens of seconds on a laptop; never let the 30 s default cut them off.
    return settings.model_copy(update={"benchmark_schema": schema or settings.tpch_schema,
                                       "sql_statement_timeout_ms": max(settings.sql_statement_timeout_ms, 600_000)})


def tpch_available(settings: Settings | None = None) -> tuple[bool, str]:
    s = tpch_settings(settings)
    try:
        with bench_connection(s) as conn:
            n = conn.execute("SELECT count(*) FROM lineitem").fetchone()[0]
        return True, f"{s.benchmark_schema}.lineitem has {n:,} rows"
    except psycopg.Error as err:
        return False, str(err).strip().splitlines()[0]


def scale_factor_guess(settings: Settings | None = None) -> float | None:
    """lineitem has ~6,001,215 rows per unit of scale factor."""
    s = tpch_settings(settings)
    try:
        with bench_connection(s) as conn:
            n = conn.execute("SELECT count(*) FROM lineitem").fetchone()[0]
        return round(n / 6_001_215, 2)
    except psycopg.Error:
        return None


def validate_queries(settings: Settings | None = None, kind: str = "standard") -> list[tuple[str, str | None]]:
    """EXPLAIN every query once; returns (query_id, error_or_None)."""
    s = tpch_settings(settings)
    out = []
    with bench_connection(s) as conn:
        for q in load_queries(kind):
            try:
                conn.execute("EXPLAIN " + q.sql)
                conn.rollback()
                out.append((q.id, None))
            except psycopg.Error as err:
                conn.rollback()
                out.append((q.id, str(err).strip().splitlines()[0]))
    return out


def conditions_for(wp: str, settings: Settings, plan_label: str | None = None) -> list[Condition]:
    """Default condition set per work package. wp3 is one condition per invocation (the plan is set outside)."""
    plan = f";plan={plan_label}" if plan_label else ""
    if wp == "wp2":
        conds = [Condition(f"meter=none{plan}", "none"),
                 Condition(f"meter=lhm@0.1{plan}", "lhm", 0.1),
                 Condition(f"meter=lhm@0.5{plan}", "lhm", 0.5)]
        if codecarbon_available():
            conds.append(Condition(f"meter=codecarbon{plan}", "codecarbon"))
        return conds
    meter = "lhm" if lhm_available() else ("codecarbon" if codecarbon_available() else "estimate")
    poll = settings.lhm_poll_seconds if meter == "lhm" else None
    tag = f"meter={meter}@{poll}" if poll is not None else f"meter={meter}"
    return [Condition(f"{tag}{plan}", meter, poll)]


def _existing(db: Session, wp: str, qid: str, cond: str, pass_no: int, schema: str, sf: float | None) -> bool:
    stmt = select(LabRun.id).where(LabRun.work_package == wp, LabRun.query_id == qid,
                                   LabRun.condition == cond, LabRun.pass_no == pass_no,
                                   LabRun.schema_name == schema, LabRun.status == "completed")
    if sf is not None:
        stmt = stmt.where(LabRun.scale_factor == sf)
    return db.execute(stmt).first() is not None


def clear_work_package(db: Session, wp: str, schema: str | None = None, sf: float | None = None) -> int:
    """Delete lab runs for a work package (optionally only for one schema / scale factor). Returns rows deleted."""
    from sqlalchemy import delete
    stmt = delete(LabRun).where(LabRun.work_package == wp)
    if schema:
        stmt = stmt.where(LabRun.schema_name == schema)
    if sf is not None:
        stmt = stmt.where(LabRun.scale_factor == sf)
    n = db.execute(stmt).rowcount
    db.commit()
    return n


ProgressFn = Callable[[dict[str, Any]], None]

MAX_REPETITIONS = 2000


def _probe_ms(settings: Settings, sql: str) -> float | None:
    """One timed execution (after one untimed warm-up) to size the energy window."""
    try:
        with bench_connection(settings) as conn, conn.cursor() as cur:
            cur.execute(sql); cur.fetchall()
            t0 = time.perf_counter()
            cur.execute(sql); cur.fetchall()
            ms = (time.perf_counter() - t0) * 1000
            conn.rollback()
            return ms
    except psycopg.Error:
        return None


def repetitions_for_window(base_reps: int, probe_ms: float | None, min_window_seconds: float) -> int:
    """At least ``base_reps``, and enough that the timed loop spans ``min_window_seconds``.

    LibreHardwareMonitor refreshes about once a second, so a window shorter than a few
    refreshes cannot be measured; short queries are simply repeated more often.
    """
    if not probe_ms or probe_ms <= 0 or min_window_seconds <= 0:
        return base_reps
    needed = int(min_window_seconds * 1000 / probe_ms) + 1
    return max(base_reps, min(needed, MAX_REPETITIONS))


def run_work_package(db: Session, wp: str, *, settings: Settings | None = None, queries: Iterable[Query] | None = None,
                     conditions: Iterable[Condition] | None = None, passes: int = 1, repetitions: int | None = None,
                     warmup: int | None = None, shuffle: bool = True, seed: int = 42, cooldown_seconds: float = 5.0,
                     plan_label: str | None = None, min_window_seconds: float = 10.0,
                     progress: ProgressFn | None = None) -> list[LabRun]:
    """Benchmark every (query, condition, pass) for a work package and persist LabRun rows."""
    if wp not in WORK_PACKAGES:
        raise ValueError(f"unknown work package {wp}")
    base = tpch_settings(settings)
    reps = repetitions or base.benchmark_repetitions
    warm = base.benchmark_warmup_runs if warmup is None else warmup
    qs = list(queries) if queries is not None else load_queries("complex" if wp in ("wp4", "wp5") else "standard")
    conds = list(conditions) if conditions is not None else conditions_for(wp, base, plan_label)
    sf = scale_factor_guess(base)
    done: list[LabRun] = []
    total = len(qs) * len(conds) * passes
    n = 0
    for pass_no in range(1, passes + 1):
        order = list(qs)
        if shuffle:
            random.Random(seed + pass_no).shuffle(order)
        for cond in conds:
            # One energy context per (condition, pass): idle floor measured once, same meter throughout.
            ctx = EnergyContext(base, method=cond.meter, poll_seconds=cond.poll_seconds)
            for q in order:
                n += 1
                if _existing(db, wp, q.id, cond.label, pass_no, base.benchmark_schema, sf):
                    log.info("skip %s %s %s pass %d (already done)", wp, q.id, cond.label, pass_no)
                    continue
                t0 = time.perf_counter()
                probe = _probe_ms(base, q.sql)
                reps_q = repetitions_for_window(reps, probe, min_window_seconds)
                outcome = benchmark_sql(q.sql, base, ctx, repetitions=reps_q, warmup=warm)
                run = LabRun(work_package=wp, query_id=q.id, condition=cond.label, pass_no=pass_no,
                             schema_name=base.benchmark_schema, scale_factor=sf, repetitions=reps_q, warmup_runs=warm,
                             environment={**outcome.environment, "query_title": q.title, "meter": cond.meter,
                                          "poll_seconds": cond.poll_seconds, "idle_watts": ctx.idle_watts,
                                          "probe_ms": probe, "min_window_seconds": min_window_seconds})
                if outcome.ok and outcome.summary:
                    s = outcome.summary
                    run.status = "completed"
                    run.samples_ms = outcome.samples_ms
                    run.median_ms, run.mean_ms, run.stdev_ms = s.median, s.mean, s.stdev
                    run.ci95_low_ms, run.ci95_high_ms = s.ci95_low, s.ci95_high
                    run.cpu_time_ms, run.peak_rss_mb = outcome.cpu_time_ms, outcome.peak_rss_mb
                    run.plan_metrics = outcome.metrics
                    run.rows_returned = int(outcome.metrics.get("pg_actual_rows", 0)) if outcome.metrics else None
                    measured = [e for e in outcome.energy if e.method == "measured"]
                    est = [e for e in outcome.energy if e.source == "estimate"]
                    if measured:
                        e = measured[0]
                        run.energy_joules, run.energy_joules_net = e.joules, e.net_joules
                        run.energy_method, run.energy_source, run.energy_details = e.method, e.source, e.details
                    else:
                        run.energy_method, run.energy_source = "none" if cond.meter == "none" else "estimated", cond.meter
                    if est:
                        run.energy_estimate_joules = est[0].joules
                else:
                    run.status = "failed"
                    run.error = outcome.error
                db.add(run)
                db.commit()
                done.append(run)
                cov = (run.energy_details or {}).get("coverage")
                log.info("%s %s %s pass %d: %s reps=%d median=%.1f ms window=%.1fs energy=%s J coverage=%s (%.0fs)",
                         wp, q.id, cond.label, pass_no, run.status, reps_q, run.median_ms or 0.0,
                         (outcome.wall_seconds or 0.0), f"{run.energy_joules_net:.1f}" if run.energy_joules_net else "-",
                         f"{cov:.2f}" if cov is not None else "-", time.perf_counter() - t0)
                if progress:
                    progress({"done": n, "total": total, "wp": wp, "query": q.id, "condition": cond.label,
                              "pass": pass_no, "status": run.status, "median_ms": run.median_ms,
                              "repetitions": reps_q, "window_s": outcome.wall_seconds,
                              "energy_joules_net": run.energy_joules_net})
                if cooldown_seconds:
                    time.sleep(cooldown_seconds)
    return done


def export_rows(db: Session, wp: str | None = None) -> list[dict[str, Any]]:
    stmt = select(LabRun).order_by(LabRun.work_package, LabRun.query_id, LabRun.condition, LabRun.pass_no)
    if wp:
        stmt = stmt.where(LabRun.work_package == wp)
    rows = []
    for r in db.execute(stmt).scalars():
        env = r.environment or {}
        rows.append({
            "id": r.id, "work_package": r.work_package, "query_id": r.query_id, "condition": r.condition,
            "pass_no": r.pass_no, "scale_factor": r.scale_factor, "repetitions": r.repetitions, "status": r.status,
            "median_ms": r.median_ms, "mean_ms": r.mean_ms, "stdev_ms": r.stdev_ms,
            "ci95_low_ms": r.ci95_low_ms, "ci95_high_ms": r.ci95_high_ms, "rows_returned": r.rows_returned,
            "cpu_time_ms": r.cpu_time_ms, "peak_rss_mb": r.peak_rss_mb,
            "energy_joules": r.energy_joules, "energy_joules_net": r.energy_joules_net,
            "energy_method": r.energy_method, "energy_source": r.energy_source,
            "energy_estimate_joules": r.energy_estimate_joules,
            "mean_watts": (r.energy_details or {}).get("mean_watts"), "idle_watts": env.get("idle_watts"),
            "coverage": (r.energy_details or {}).get("coverage"),
            "distinct_readings": (r.energy_details or {}).get("distinct_readings"),
            "temp_c_start": (r.energy_details or {}).get("temp_c_start"),
            "temp_c_max": (r.energy_details or {}).get("temp_c_max"),
            "dram_joules_approx": (r.energy_details or {}).get("dram_joules_approx"),
            "platform_mean_watts": (r.energy_details or {}).get("platform_mean_watts"),
            "platform_joules_approx": (r.energy_details or {}).get("platform_joules_approx"),
            "pg_execution_ms": (r.plan_metrics or {}).get("pg_execution_ms"),
            "pg_shared_hit_blocks": (r.plan_metrics or {}).get("pg_shared_hit_blocks"),
            "pg_shared_read_blocks": (r.plan_metrics or {}).get("pg_shared_read_blocks"),
            "pg_parallel_workers": (r.plan_metrics or {}).get("pg_parallel_workers"),
            "pg_gather_nodes": (r.plan_metrics or {}).get("pg_gather_nodes"),
            "pg_io_read_ms": (r.plan_metrics or {}).get("pg_io_read_ms"),
            "window_s": (r.median_ms or 0) * r.repetitions / 1000 if r.median_ms else None,
            "power_plan": env.get("power_plan"), "power_mode_overlay": env.get("power_mode_overlay"),
            "on_ac_power": env.get("on_ac_power"), "process_count": env.get("process_count"),
            "noisy_processes": ";".join(env.get("noisy_processes") or []),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return rows


def joules_per_1000_rows(run: LabRun) -> float | None:
    if run.energy_joules_net is None or not run.rows_returned:
        return None
    return run.energy_joules_net / run.rows_returned * 1000
