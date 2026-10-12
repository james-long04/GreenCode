#!/usr/bin/env python3
"""Export the evidence store to CSV/JSON for statistical analysis in the dissertation.

    python scripts/export_results.py --project "Experiment 1" --out results/
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.db.models import BenchmarkRun, Measurement, Optimisation, Project  # noqa: E402
from app.db.session import session_scope  # noqa: E402
from app.experiments import results  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", help="project name (default: everything)")
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    with session_scope() as db:
        project_id = None
        if args.project:
            p = db.execute(select(Project).where(Project.name == args.project)).scalars().first()
            if p is None:
                print("project not found", file=sys.stderr)
                return 1
            project_id = p.id
        rows = results.collect(db, project_id)
        summary = results.summarise(rows)
        (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
        with (out / "optimisations.csv").open("w", newline="") as fh:
            if rows:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                w.writeheader()
                for r in rows:
                    w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()})
        # Long-format benchmark samples + measurements for R / pandas.
        with (out / "samples.csv").open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["optimisation_id", "case_id", "condition", "variant", "sample_index", "ms"])
            with (out / "measurements.csv").open("w", newline="") as mh:
                mw = csv.writer(mh)
                mw.writerow(["optimisation_id", "case_id", "condition", "variant", "metric", "value", "unit", "method", "source"])
                for r in rows:
                    opt = db.get(Optimisation, r["optimisation_id"])
                    for run in db.execute(select(BenchmarkRun).where(BenchmarkRun.optimisation_id == opt.id)).scalars():
                        for i, ms in enumerate(run.samples_ms or []):
                            w.writerow([opt.id, r["case_id"], r["condition"], run.variant, i, ms])
                        for m in db.execute(select(Measurement).where(Measurement.benchmark_run_id == run.id)).scalars():
                            mw.writerow([opt.id, r["case_id"], r["condition"], run.variant, m.metric, m.value, m.unit, m.method, m.source])
    print(f"exported {len(rows)} optimisations to {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
