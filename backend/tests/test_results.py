"""Hypothesis aggregation in experiments.results (no database needed)."""

from __future__ import annotations

from app.experiments import results as R


def _row(case, cond, status, speedup=None, energy=None):
    return {"case_id": case, "analysis_id": case, "condition": cond, "status": status,
            "speedup": speedup, "energy_ratio": energy}


def _by(rows):
    return {c: [r for r in rows if r["condition"] == c] for c in ("ai_only", "greencode")}


def test_paired_uses_median_of_repeated_runs():
    rows = [_row("a", "ai_only", "benchmarked", 1.0), _row("a", "ai_only", "benchmarked", 3.0),
            _row("a", "greencode", "benchmarked", 2.0)]
    a, b, keys = R._paired(_by(rows), "speedup")
    assert keys == ["a"] and a == [2.0] and b == [2.0]


def test_per_protocol_drops_rejected_but_itt_scores_one():
    rows = [_row("a", "ai_only", "rejected"), _row("a", "greencode", "benchmarked", 20.0),
            _row("b", "ai_only", "benchmarked", 1.5), _row("b", "greencode", "benchmarked", 1.5)]
    a, b, keys = R._paired(_by(rows), "speedup")
    assert keys == ["b"]
    a, b, keys = R._paired(_by(rows), "speedup", intention_to_treat=True)
    assert keys == ["a", "b"] and a == [1.0, 1.5] and b == [20.0, 1.5]


def test_hypotheses_report_both_analyses():
    rows = [_row("a", "ai_only", "rejected"), _row("a", "greencode", "benchmarked", 20.0, 10.0)]
    for c in "bcdef":
        rows += [_row(c, "ai_only", "benchmarked", 1.0, 1.0), _row(c, "greencode", "benchmarked", 1.2, 1.2)]
    h = R._hypotheses(_by(rows), {})
    h2 = h["H2"]
    assert h2["paired_cases"] == 5 and h2["intention_to_treat"]["paired_cases"] == 6
    assert h2["greencode_better"] == 5 and h2["ai_only_better"] == 0 and h2["ties"] == 0
    assert h2["intention_to_treat"]["greencode_geomean"] > h2["intention_to_treat"]["ai_only_geomean"]
    assert "intention_to_treat" in h["H3"]
