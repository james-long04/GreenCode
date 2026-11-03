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
    ap.add_argument("--sources", action="store_true",
                    help="also write candidates.md: original, prompt, raw response and candidate per optimisation")
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
        if args.sources:
            parts = []
            for r in sorted(rows, key=lambda r: (r["case_id"] or "", r["condition"])):
                opt = db.get(Optimisation, r["optimisation_id"])
                parts += [f"## {r['case_id']} — {r['condition']} — {opt.status}" + (f" ({opt.failure_reason})" if opt.failure_reason else ""), "",
                          f"speed-up: {r.get('speedup')}  energy ratio: {r.get('energy_ratio')}", "",
                          "### Original", "```sql" if r["language"] == "sql" else "```python", (opt.original_source or "").strip(), "```", "",
                          "### Candidate", "```sql" if r["language"] == "sql" else "```python", (opt.candidate_source or "(none)").strip(), "```", "",
                          "### Test results", ""]
                for t in opt.test_results:
                    parts.append(f"- {t.test_name}: {'pass' if t.passed else 'FAIL'}" + (f" — {t.failure_type}: {(t.details or '')[:300]}" if not t.passed else ""))
                parts += ["", "<details><summary>Prompt</summary>", "", "```", (opt.prompt or "").strip(), "```", "", "</details>", ""]
            (out / "candidates.md").write_text("\n".join(parts), encoding="utf-8")
    print(f"exported {len(rows)} optimisations to {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
