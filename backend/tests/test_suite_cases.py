"""Every benchmark case must be well-formed, pass its own tests and trigger its expected rules."""

import pytest

from app.analysis.engine import analyse
from app.experiments.suite import load_cases
from app.verification.sandbox import run_job

CASES = load_cases()


def test_suite_is_non_trivial():
    assert len(CASES) >= 20 and len({c.id for c in CASES}) == len(CASES)


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_expected_rules_fire(case):
    found = {f.rule_id for f in analyse(case.language, case.source).findings}
    assert set(case.expected_rules) <= found


@pytest.mark.parametrize("case", [c for c in CASES if c.language == "python"], ids=[c.id for c in CASES if c.language == "python"])
def test_python_case_original_passes_its_tests(case):
    job = {"mode": "verify", "source": case.source, "entry_point": case.entry_point or "solve",
           "tests": [{"name": t["name"], "args": t["args"]} for t in case.tests]}
    r = run_job(job)
    assert r.ok, r.error
    for t, spec in zip(r.data["tests"], case.tests):
        assert t["error"] is None, t["error"]
        if spec.get("expected") is not None:
            assert t["result"]["value"] == spec["expected"]
