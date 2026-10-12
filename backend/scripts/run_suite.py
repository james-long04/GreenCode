#!/usr/bin/env python3
"""Run the benchmark suite from the command line.

Examples
--------
    # Full suite, both conditions, default model from .env
    python scripts/run_suite.py --project "Experiment 1"

    # A subset, one condition, custom repetitions
    python scripts/run_suite.py --project smoke --cases py_001_membership_list_in_loop sql_003_not_in_subquery \
        --conditions greencode --repetitions 10

    # Offline dry run with the mock provider (no Ollama needed)
    GREENCODE_LLM_PROVIDER=mock python scripts/run_suite.py --project dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db.models import Project  # noqa: E402
from app.db.session import init_db, session_scope  # noqa: E402
from app.experiments import results  # noqa: E402
from app.experiments.suite import load_cases, run_suite  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True, help="project name (created if missing)")
    ap.add_argument("--cases", nargs="*", help="case ids to run (default: all)")
    ap.add_argument("--language", choices=["python", "sql"], help="restrict to one language")
    ap.add_argument("--conditions", nargs="*", default=["ai_only", "greencode"])
    ap.add_argument("--repetitions", type=int, help="override GREENCODE_BENCHMARK_REPETITIONS")
    ap.add_argument("--no-shuffle", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--list", action="store_true", help="list cases and exit")
    ap.add_argument("--out", help="write per-run results JSON here")
    args = ap.parse_args()

    if args.repetitions:
        os.environ["GREENCODE_BENCHMARK_REPETITIONS"] = str(args.repetitions)
        get_settings.cache_clear()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    cases = load_cases(language=args.language)
    if args.list:
        for c in cases:
            print(f"{c.id:45s} {c.language:6s} {','.join(c.expected_rules):20s} {c.title}")
        return 0
    case_ids = args.cases or [c.id for c in cases]

    init_db()
    with session_scope() as db:
        project = db.execute(select(Project).where(Project.name == args.project)).scalars().first()
        if project is None:
            project = Project(name=args.project, description="created by scripts/run_suite.py")
            db.add(project)
            db.flush()
        project_id = project.id
    settings = get_settings()
    print(f"project={args.project} ({project_id}) provider={settings.llm_provider} model={settings.ollama_model} "
          f"cases={len(case_ids)} conditions={args.conditions} repetitions={settings.benchmark_repetitions}")

    with session_scope() as db:
        rows = run_suite(db, project_id, case_ids, args.conditions, shuffle=not args.no_shuffle, seed=args.seed)
        summary = results.summarise(results.collect(db, project_id))

    print("\n=== per-run ===")
    for r in rows:
        sp = f"{r['speedup']:.2f}x" if r["speedup"] else "-"
        print(f"{r['case_id']:45s} {r['condition']:10s} {r['status']:12s} {sp:>8s}  {r['failure_reason'] or ''}")
    print("\n=== summary ===")
    print(json.dumps(summary, indent=2, default=str))
    if args.out:
        Path(args.out).write_text(json.dumps({"runs": rows, "summary": summary}, indent=2, default=str))
        print(f"written {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
