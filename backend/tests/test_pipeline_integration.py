"""Full Detect → Optimise → Test → Benchmark run against PostgreSQL with the mock provider."""

import pytest
from sqlalchemy import select

from app.ai.provider import MockProvider
from app.db.models import BenchmarkRun, Measurement, Optimisation, Project, TestResult
from app.experiments import results
from app.experiments.pipeline import create_analysis, create_optimisation, process_optimisation
from app.experiments.suite import run_suite
from tests.conftest import requires_bench_data, requires_db

GOOD = "```python\ndef solve(items, targets):\n    allowed = set(items)\n    return [t for t in targets if t in allowed]\n```"
BAD = "```python\ndef solve(items, targets):\n    return list(targets)\n```"


@requires_db
def test_python_pipeline_stores_full_evidence_trail(db_session):
    db = db_session
    project = Project(name="test")
    db.add(project)
    db.commit()
    src = "def solve(items, targets):\n    allowed = [x for x in items]\n    return [t for t in targets if t in allowed]\n"
    spec = {"entry_point": "solve", "tests": [{"name": "t", "args": "([1,2,3],[2,9])", "expected": [2]}],
            "benchmark": {"setup": "a=list(range(3000)); b=list(range(0,6000,2))", "call": "solve(a,b)"}}
    analysis = create_analysis(db, project.id, "case", "python", src, spec)
    assert {f.rule_id for f in analysis.findings} >= {"PY001"}

    good = create_optimisation(db, analysis.id, "greencode")
    good = process_optimisation(db, good.id, MockProvider({"Optimise": GOOD}))
    assert good.status == "benchmarked", good.failure_reason
    assert good.summary["timing"]["speedup"] > 1
    assert "PY001" in good.prompt
    runs = db.execute(select(BenchmarkRun).where(BenchmarkRun.optimisation_id == good.id)).scalars().all()
    assert {r.variant for r in runs} == {"original", "candidate"}
    metrics = {m.metric for r in runs for m in db.execute(select(Measurement).where(Measurement.benchmark_run_id == r.id)).scalars()}
    assert {"cpu_time_ms", "energy_joules", "co2e_grams"} <= metrics

    bad = create_optimisation(db, analysis.id, "ai_only")
    bad = process_optimisation(db, bad.id, MockProvider({"Optimise": BAD}))
    assert bad.status == "rejected" and bad.failure_reason.startswith("wrong_output")
    assert "PY001" not in bad.prompt
    assert db.execute(select(TestResult).where(TestResult.optimisation_id == bad.id)).scalars().first() is not None

    rows = results.collect(db, project.id)
    summary = results.summarise(rows)
    assert summary["conditions"]["greencode"]["correct"] == 1
    assert summary["conditions"]["ai_only"]["failures"].get("wrong_output") == 1
    db.delete(project)
    db.commit()


@requires_bench_data
def test_sql_pipeline_against_bench_dataset(db_session):
    db = db_session
    project = Project(name="sql-test")
    db.add(project)
    db.commit()
    src = "SELECT c.id, c.email FROM customers c WHERE c.id NOT IN (SELECT o.customer_id FROM orders o)"
    cand = "```sql\nSELECT c.id, c.email FROM customers c WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id)\n```"
    analysis = create_analysis(db, project.id, "sql", "sql", src)
    assert "SQL005" in {f.rule_id for f in analysis.findings}
    assert "CREATE TABLE" in analysis.case_spec.get("schema", "")
    opt = create_optimisation(db, analysis.id, "greencode")
    opt = process_optimisation(db, opt.id, MockProvider({"Optimise": cand}))
    assert opt.status == "benchmarked", opt.failure_reason
    assert "pg_total_cost" in opt.summary["sql_plan"]["original"]
    db.delete(project)
    db.commit()


@requires_db
def test_run_suite_subset(db_session):
    db = db_session
    project = Project(name="suite-test")
    db.add(project)
    db.commit()
    rows = run_suite(db, project.id, ["py_007_sorted_for_min", "py_018_no_known_pattern"], provider=MockProvider())
    assert len(rows) == 4 and all(r["status"] in {"benchmarked", "rejected", "failed"} for r in rows)
    opts = db.execute(select(Optimisation).join(Optimisation.analysis).where(Optimisation.analysis.has(project_id=project.id))).scalars().all()
    assert len(opts) == 4
    db.delete(project)
    db.commit()
