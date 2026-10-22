"""Aggregate stored evidence into the figures needed to evaluate H1–H4.

H1  correctness rate (verified / generated) per condition      → Fisher's exact test
H2  execution-time improvement per condition (verified only)   → paired Wilcoxon on log speed-up
H3  energy improvement per condition (verified only)           → paired Wilcoxon on energy ratio
    H2/H3 are reported twice: per-protocol (the pre-registered test, which
    sets ``supported``) and intention-to-treat (a rejected/failed candidate
    scores 1.0, i.e. no improvement delivered), aggregated by the median of
    repeated runs per case.
H4  time reduction ≠ energy reduction                          → per-case divergence + Spearman ρ
"""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.prompts import CONDITIONS
from app.db.models import Analysis, Optimisation

try:
    from scipy import stats as _st  # type: ignore
except Exception:  # pragma: no cover
    _st = None


def _geomean(xs: list[float]) -> float | None:
    xs = [x for x in xs if x and x > 0]
    if not xs:
        return None
    return math.exp(sum(math.log(x) for x in xs) / len(xs))


def _primary_energy(summary: dict[str, Any]) -> dict[str, Any] | None:
    energy = summary.get("energy") or {}
    for key in ("lhm", "codecarbon", "estimate"):
        if key in energy:
            return {"source": key, **energy[key]}
    return None


def collect(db: Session, project_id: str | None = None, language: str | None = None) -> list[dict[str, Any]]:
    stmt = select(Optimisation).options(selectinload(Optimisation.analysis).selectinload(Analysis.findings),
                                        selectinload(Optimisation.test_results))
    if project_id or language:
        stmt = stmt.join(Analysis)
        if project_id:
            stmt = stmt.where(Analysis.project_id == project_id)
        if language:
            stmt = stmt.where(Analysis.language == language)
    rows = []
    for opt in db.execute(stmt).scalars().all():
        s = opt.summary or {}
        timing = s.get("timing") or {}
        energy = _primary_energy(s)
        rows.append({
            "optimisation_id": opt.id, "analysis_id": opt.analysis_id, "case_id": opt.analysis.case_id,
            "name": opt.analysis.name, "language": opt.analysis.language, "condition": opt.condition,
            "status": opt.status, "failure_reason": opt.failure_reason, "model": opt.model_name,
            "findings": len(opt.analysis.findings),
            "rules": sorted({f.rule_id for f in opt.analysis.findings}),
            "unchanged": bool(s.get("unchanged")),
            "generation_ms": opt.generation_ms,
            "speedup": timing.get("speedup"), "time_percent_change": timing.get("percent_change"),
            "significant": timing.get("significant"), "verdict": timing.get("verdict"),
            "p_value": timing.get("mann_whitney_p"),
            "energy_source": energy.get("source") if energy else None,
            "energy_method": energy.get("method") if energy else None,
            "energy_ratio": energy.get("energy_ratio") if energy else None,
            "energy_percent_change": energy.get("percent_change") if energy else None,
            "original_co2e_g": energy.get("original_co2e_g") if energy else None,
            "candidate_co2e_g": energy.get("candidate_co2e_g") if energy else None,
            "created_at": opt.created_at.isoformat() if opt.created_at else None,
        })
    return rows


def _failure_counter(rows: list[dict[str, Any]]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for r in rows:
        if r["status"] in {"rejected", "failed"}:
            reason = (r.get("failure_reason") or "unknown").split(":")[0]
            c[reason] += 1
    return dict(c)


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_cond: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_cond[r["condition"]].append(r)

    conditions: dict[str, Any] = {}
    for cond in CONDITIONS:
        rs = by_cond.get(cond, [])
        generated = [r for r in rs if r["status"] in {"verified", "benchmarked", "rejected"} or
                     (r["status"] == "failed" and not (r.get("failure_reason") or "").startswith(("generation_error", "parse_error")))]
        correct = [r for r in rs if r["status"] in {"verified", "benchmarked"}]
        bench = [r for r in rs if r["status"] == "benchmarked" and r["speedup"]]
        faster = [r for r in bench if r["verdict"] == "faster"]
        slower = [r for r in bench if r["verdict"] == "slower"]
        energy_ratios = [r["energy_ratio"] for r in bench if r.get("energy_ratio")]
        conditions[cond] = {
            "runs": len(rs),
            "generated": len(generated),
            "correct": len(correct),
            "correctness_rate": (len(correct) / len(generated)) if generated else None,
            "unchanged": sum(1 for r in rs if r["unchanged"]),
            "benchmarked": len(bench),
            "faster_significant": len(faster),
            "slower_significant": len(slower),
            "median_speedup": statistics.median([r["speedup"] for r in bench]) if bench else None,
            "geomean_speedup": _geomean([r["speedup"] for r in bench]),
            "median_time_change_pct": statistics.median([r["time_percent_change"] for r in bench]) if bench else None,
            "geomean_energy_ratio": _geomean(energy_ratios),
            "median_energy_change_pct": statistics.median([r["energy_percent_change"] for r in bench if r.get("energy_percent_change") is not None]) if energy_ratios else None,
            "failures": _failure_counter(rs),
        }

    hyp = _hypotheses(by_cond, conditions)
    return {"total_runs": len(rows), "conditions": conditions, "hypotheses": hyp,
            "by_language": {lang: summarise([r for r in rows if r["language"] == lang])["conditions"]
                            for lang in sorted({r["language"] for r in rows})} if rows and len({r["language"] for r in rows}) > 1 else {}}


def _paired(by_cond: dict[str, list[dict[str, Any]]], key: str, *,
            intention_to_treat: bool = False) -> tuple[list[float], list[float], list[str]]:
    """Per-case paired values for the two conditions.

    A case may have been run several times; the *median* over its benchmarked
    runs is used so that repeated runs are aggregated rather than one of them
    silently winning. In the per-protocol analysis (default) a case only
    counts when it was benchmarked under both conditions. In the
    intention-to-treat analysis a condition whose candidates were all
    rejected or failed scores 1.0 (no improvement delivered), so the cases
    where one condition produced nothing usable are kept in the comparison.
    """
    def per_case(rows: list[dict[str, Any]]) -> dict[str, float]:
        values: dict[str, list[float]] = defaultdict(list)
        attempted: set[str] = set()
        for r in rows:
            cid = r["case_id"] or r["analysis_id"]
            attempted.add(cid)
            if r.get("status") == "benchmarked" and r.get(key):
                values[cid].append(float(r[key]))
        out = {cid: statistics.median(v) for cid, v in values.items()}
        if intention_to_treat:
            for cid in attempted - set(out):
                out[cid] = 1.0
        return out

    a = per_case(by_cond.get("ai_only", []))
    b = per_case(by_cond.get("greencode", []))
    keys = sorted(set(a) & set(b))
    return [a[k] for k in keys], [b[k] for k in keys], keys


def _paired_test(by_cond: dict[str, list[dict[str, Any]]], key: str, *, intention_to_treat: bool) -> dict[str, Any]:
    a, b, keys = _paired(by_cond, key, intention_to_treat=intention_to_treat)
    out: dict[str, Any] = {"paired_cases": len(a), "ai_only_geomean": _geomean(a), "greencode_geomean": _geomean(b),
                           "greencode_better": sum(1 for x, y in zip(a, b) if y > x * 1.1),
                           "ai_only_better": sum(1 for x, y in zip(a, b) if x > y * 1.1)}
    out["ties"] = out["paired_cases"] - out["greencode_better"] - out["ai_only_better"]
    if _st is not None and len(a) >= 5:
        try:
            out["wilcoxon_p"] = float(_st.wilcoxon([math.log(y) for y in b], [math.log(x) for x in a],
                                                   alternative="greater").pvalue)
        except ValueError:
            out["wilcoxon_p"] = None
    out["supported"] = (out["greencode_geomean"] or 0) > (out["ai_only_geomean"] or 0) and (out.get("wilcoxon_p") or 1) < 0.05
    return out


def _hypotheses(by_cond: dict[str, list[dict[str, Any]]], conditions: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    ai, gc = conditions.get("ai_only", {}), conditions.get("greencode", {})

    # H1 correctness
    h1: dict[str, Any] = {"ai_only_rate": ai.get("correctness_rate"), "greencode_rate": gc.get("correctness_rate")}
    if _st is not None and ai.get("generated") and gc.get("generated"):
        table = [[gc["correct"], gc["generated"] - gc["correct"]], [ai["correct"], ai["generated"] - ai["correct"]]]
        try:
            h1["fisher_p"] = float(_st.fisher_exact(table, alternative="greater")[1])
        except Exception:  # noqa: BLE001
            h1["fisher_p"] = None
    h1["supported"] = (h1["greencode_rate"] or 0) > (h1["ai_only_rate"] or 0) and (h1.get("fisher_p") or 1) < 0.05
    out["H1"] = h1

    # H2 speed-up, H3 energy ratio. Primary (per-protocol): cases verified and
    # benchmarked under both conditions. Secondary (intention-to-treat): a
    # condition that produced no usable candidate scores 1.0.
    for name, key in (("H2", "speedup"), ("H3", "energy_ratio")):
        primary = _paired_test(by_cond, key, intention_to_treat=False)
        primary["intention_to_treat"] = _paired_test(by_cond, key, intention_to_treat=True)
        out[name] = primary

    # H4 time vs energy
    pairs = [(r["time_percent_change"], r["energy_percent_change"]) for rs in by_cond.values() for r in rs
             if r.get("time_percent_change") is not None and r.get("energy_percent_change") is not None]
    h4: dict[str, Any] = {"cases": len(pairs)}
    if pairs:
        diverg = [abs(t - e) for t, e in pairs]
        h4["median_divergence_pp"] = statistics.median(diverg)
        h4["cases_diverging_over_10pp"] = sum(1 for d in diverg if d > 10)
        if _st is not None and len(pairs) >= 3:
            rho = _st.spearmanr([p[0] for p in pairs], [p[1] for p in pairs])
            h4["spearman_rho"], h4["spearman_p"] = float(rho.statistic), float(rho.pvalue)
        h4["supported"] = h4["cases_diverging_over_10pp"] > 0
    out["H4"] = h4
    return out
