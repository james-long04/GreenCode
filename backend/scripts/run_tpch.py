#!/usr/bin/env python3
"""Run the laboratory (TPC-H-derived) work packages. See docs/protocol.md.

    python scripts\\run_tpch.py --check                      # pre-flight only
    python scripts\\run_tpch.py --validate                   # EXPLAIN all 22 queries, report errors
    python scripts\\run_tpch.py --wp 1 --passes 3            # baseline, 3 randomised passes
    python scripts\\run_tpch.py --wp 2                       # meter overhead: none / lhm@0.1 / lhm@0.5 / codecarbon
    python scripts\\run_tpch.py --wp 3 --plan-label balanced --expect-plan Balanced
    python scripts\\run_tpch.py --wp 4 --repetitions 30      # complex queries
    python scripts\\run_tpch.py --wp 5 --project "TPC-H WP5"  # complex queries through the GreenCode pipeline
    python scripts\\run_tpch.py --export lab.csv             # everything in lab_runs -> CSV

A work package is resumable: rerun the same command after an interruption and completed
(query, condition, pass) rows are skipped. Pre-flight checks must pass unless --force.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.db.models import Base, Project  # noqa: E402
from app.db.session import get_engine, session_scope  # noqa: E402
from app.experiments import tpch  # noqa: E402
from app.experiments.preflight import all_required_ok, format_checks, run_checks  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wp", type=int, choices=[1, 2, 3, 4, 5], help="work package to run")
    ap.add_argument("--check", action="store_true", help="run the pre-flight checks and exit")
    ap.add_argument("--validate", action="store_true", help="EXPLAIN every query and exit")
    ap.add_argument("--export", metavar="CSV", help="export all lab runs to CSV and exit")
    ap.add_argument("--passes", type=int, default=1, help="how many randomised passes over the query set")
    ap.add_argument("--repetitions", type=int, help="timed repetitions per query (default from settings)")
    ap.add_argument("--warmup", type=int, help="warm-up runs per query (default from settings)")
    ap.add_argument("--queries", nargs="*", help="subset of query ids, e.g. q01 q06 q14")
    ap.add_argument("--plan-label", help="label for the power plan/mode in force, recorded in the condition (wp3)")
    ap.add_argument("--expect-plan", help="pre-flight: require the active power plan name to contain this text")
    ap.add_argument("--meter", choices=["none", "lhm", "codecarbon", "estimate"], help="override the meter (wp1/3/4)")
    ap.add_argument("--poll", type=float, help="LHM poll interval in seconds (with --meter lhm)")
    ap.add_argument("--cooldown", type=float, default=5.0, help="seconds to pause between queries")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--project", default="TPC-H WP5", help="project name for wp5 pipeline runs")
    ap.add_argument("--force", action="store_true", help="run even if required pre-flight checks fail")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    settings = get_settings()
    Base.metadata.create_all(get_engine())  # lab_runs table

    if args.export:
        with session_scope() as db:
            rows = tpch.export_rows(db)
        if not rows:
            print("no lab runs yet")
            return 0
        with open(args.export, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {len(rows)} rows to {args.export}")
        return 0

    ok, msg = tpch.tpch_available(settings)
    print(f"TPC-H schema: {'OK' if ok else 'MISSING'} - {msg}")
    if not ok:
        print("run: python scripts\\load_tpch.py --sf 1")
        return 1
    sf = tpch.scale_factor_guess(settings)
    print(f"scale factor (from lineitem rows): ~{sf}")

    if args.validate:
        bad = 0
        for kind in ("standard", "complex"):
            for qid, err in tpch.validate_queries(settings, kind):
                print(f"  {qid}: {'OK' if err is None else 'ERROR ' + err}")
                bad += err is not None
        return 1 if bad else 0

    meter = args.meter or ("lhm" if args.wp != 2 else "lhm")
    checks = run_checks(settings, meter=meter, expect_plan=args.expect_plan)
    print("Pre-flight:\n" + format_checks(checks))
    if args.check:
        return 0 if all_required_ok(checks) else 1
    if not all_required_ok(checks) and not args.force:
        print("\nRequired checks failed. Fix them or pass --force to run anyway (the run will be recorded as such).")
        return 1
    if args.wp is None:
        ap.error("--wp is required")
    wp = f"wp{args.wp}"

    if wp == "wp5":
        return run_wp5(args, settings)

    queries = tpch.load_queries("complex" if wp == "wp4" else "standard")
    if args.queries:
        wanted = set(args.queries)
        queries = [q for q in queries if q.id in wanted]
    conds = None
    if args.meter and wp != "wp2":
        tag = f"meter={args.meter}" + (f"@{args.poll}" if args.poll is not None and args.meter == "lhm" else "")
        conds = [tpch.Condition(tag + (f";plan={args.plan_label}" if args.plan_label else ""), args.meter, args.poll)]
    print(f"\nRunning {wp}: {len(queries)} queries x {args.passes} pass(es); reps={args.repetitions or settings.benchmark_repetitions}")
    t0 = time.perf_counter()

    def progress(ev: dict) -> None:
        e = ev.get("energy_joules_net")
        print(f"  [{ev['done']}/{ev['total']}] {ev['query']} {ev['condition']} pass {ev['pass']}: {ev['status']} "
              f"median {ev['median_ms'] or 0:.1f} ms, net {e:.1f} J" if e is not None else
              f"  [{ev['done']}/{ev['total']}] {ev['query']} {ev['condition']} pass {ev['pass']}: {ev['status']} "
              f"median {ev['median_ms'] or 0:.1f} ms")

    with session_scope() as db:
        runs = tpch.run_work_package(db, wp, settings=settings, queries=queries, conditions=conds, passes=args.passes,
                                     repetitions=args.repetitions, warmup=args.warmup, seed=args.seed,
                                     cooldown_seconds=args.cooldown, plan_label=args.plan_label, progress=progress)
        failed = [r for r in runs if r.status != "completed"]
    print(f"\n{wp} done: {len(runs)} runs ({len(failed)} failed) in {(time.perf_counter() - t0) / 60:.1f} min")
    for r in failed:
        print(f"  FAILED {r.query_id} {r.condition}: {r.error}")
    return 0


def run_wp5(args: argparse.Namespace, settings) -> int:  # type: ignore[no-untyped-def]
    """Complex queries through the full pipeline (AI-only vs GreenCode) against the TPC-H schema."""
    from sqlalchemy import select

    from app.ai.provider import build_provider
    from app.experiments.suite import load_cases, run_suite

    s = tpch.tpch_settings(settings)
    cases = load_cases(tpch.TPCH_DIR / "cases")
    if not cases:
        print("no cases in benchmarks/tpch/cases")
        return 1
    provider = build_provider(s)
    print(f"provider: {provider.model_name}; {len(cases)} cases; schema {s.benchmark_schema}")
    with session_scope() as db:
        project = db.execute(select(Project).where(Project.name == args.project)).scalars().first()
        if project is None:
            project = Project(name=args.project, description=f"WP5: complex TPC-H-derived queries through the pipeline (sf~{tpch.scale_factor_guess(s)})")
            db.add(project)
            db.commit()
        results = run_suite(db, project.id, provider=provider, settings=s, seed=args.seed, cases=cases,
                            progress=lambda ev: print(f"  [{ev['done']}/{ev['total']}] {ev['case_id']} {ev['condition']}: {ev['status']} speedup={ev.get('speedup')}"))
    ok = sum(1 for r in results if r["status"] == "benchmarked")
    print(f"wp5 done: {ok}/{len(results)} benchmarked. Results are in the dashboard under project '{args.project}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
