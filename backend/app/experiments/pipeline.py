"""The end-to-end GreenCode pipeline.

Detect → Explain → Optimise → Test → Benchmark → Measure → Verify

Each stage persists its evidence before the next one starts, so a failure at
any point leaves a complete, inspectable trail in PostgreSQL.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.parsing import CandidateParseError, extract_code
from app.ai.prompts import CONDITIONS, build_prompt
from app.ai.provider import LLMProvider, build_provider
from app.analysis.base import Finding
from app.analysis.engine import analyse
from app.benchmark.energy import co2e_grams
from app.benchmark.runner import BenchmarkOutcome, EnergyContext, benchmark_python
from app.benchmark.sql_runner import benchmark_sql
from app.benchmark.stats import compare
from app.config import Settings, get_settings
from app.db.models import (
    Analysis,
    BenchmarkRun,
    CarbonFactor,
    Finding as FindingRow,
    Measurement,
    Optimisation,
    Project,
    TestResult,
)
from app.verification import verify_python, verify_sql

log = logging.getLogger("greencode.pipeline")


# ---------------------------------------------------------------------------
# Detect + Explain
# ---------------------------------------------------------------------------

def _sql_context(source: str, settings: Settings) -> tuple[dict[str, Any] | None, dict[str, int], str | None]:
    """Best-effort EXPLAIN + schema summary for SQL analyses (skipped if the DB is down)."""
    try:
        import psycopg

        from app.db.benchdb import bench_connection, explain_json, schema_ddl_summary, table_row_estimates

        with bench_connection(settings) as conn:
            stats = table_row_estimates(conn, settings.benchmark_schema)
            ddl = schema_ddl_summary(conn, settings.benchmark_schema)
            try:
                plan = explain_json(conn, source, analyze=False)
            except psycopg.Error:
                conn.rollback()
                plan = None
            return plan, stats, ddl
    except Exception as err:  # noqa: BLE001
        log.warning("SQL context unavailable: %s", err)
        return None, {}, None


def create_analysis(db: Session, project_id: str, name: str, language: str, source: str,
                    case_spec: dict[str, Any] | None = None, case_id: str | None = None,
                    settings: Settings | None = None) -> Analysis:
    settings = settings or get_settings()
    project = db.get(Project, project_id)
    if project is None:
        raise ValueError("project not found")
    language = language.lower()
    explain = None
    stats: dict[str, int] = {}
    spec = dict(case_spec or {})
    if language == "sql":
        explain, stats, ddl = _sql_context(source, settings)
        if ddl and not spec.get("schema"):
            spec["schema"] = ddl
    result = analyse(language, source, explain=explain, table_stats=stats)
    analysis = Analysis(project_id=project_id, name=name, language=language, source=source,
                        case_spec=spec, case_id=case_id, analyser_version=result.analyser_version,
                        duration_ms=result.duration_ms,
                        status="analysed" if result.error is None else "analysis_error")
    db.add(analysis)
    db.flush()
    for f in result.findings:
        db.add(FindingRow(analysis_id=analysis.id, rule_id=f.rule_id, title=f.title, severity=f.severity,
                          category=f.category, line=f.line, column=f.column, end_line=f.end_line,
                          snippet=f.snippet, explanation=f.explanation, suggestion=f.suggestion,
                          confidence=f.confidence, evidence=f.evidence))
    if result.error:
        analysis.case_spec = {**spec, "analysis_error": result.error}
    db.commit()
    db.refresh(analysis)
    return analysis


def _findings_of(analysis: Analysis) -> list[Finding]:
    rows = sorted(analysis.findings, key=lambda r: ((r.line or 0), r.rule_id))
    return [Finding(rule_id=r.rule_id, title=r.title, explanation=r.explanation, suggestion=r.suggestion,
                    severity=r.severity, category=r.category, line=r.line, column=r.column,
                    end_line=r.end_line, snippet=r.snippet, confidence=r.confidence, evidence=r.evidence or {})
            for r in rows]


# ---------------------------------------------------------------------------
# Optimise
# ---------------------------------------------------------------------------

def create_optimisation(db: Session, analysis_id: str, condition: str) -> Optimisation:
    if condition not in CONDITIONS:
        raise ValueError(f"condition must be one of {CONDITIONS}")
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise ValueError("analysis not found")
    opt = Optimisation(analysis_id=analysis.id, condition=condition, original_source=analysis.source,
                       status="pending")
    db.add(opt)
    db.commit()
    db.refresh(opt)
    return opt


def generate_candidate(db: Session, opt: Optimisation, provider: LLMProvider) -> bool:
    analysis = opt.analysis
    spec = analysis.case_spec or {}
    findings = _findings_of(analysis) if opt.condition == "greencode" else None
    system, prompt = build_prompt(analysis.language, analysis.source, opt.condition, findings,
                                  entry_point=spec.get("entry_point"), schema=spec.get("schema"))
    opt.prompt = prompt
    opt.provider = provider.name
    opt.model_name = provider.model_name()
    try:
        gen = provider.generate(prompt, system)
    except Exception as err:  # noqa: BLE001
        opt.status = "failed"
        opt.failure_reason = f"generation_error: {err}"
        db.commit()
        return False
    opt.raw_response = gen.text
    opt.generation_ms = gen.duration_ms
    opt.prompt_tokens = gen.prompt_tokens
    opt.completion_tokens = gen.completion_tokens
    try:
        opt.candidate_source = extract_code(gen.text, analysis.language)
    except CandidateParseError as err:
        opt.status = "failed"
        opt.failure_reason = f"parse_error: {err}"
        db.commit()
        return False
    opt.status = "generated"
    db.commit()
    return True


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def verify_candidate(db: Session, opt: Optimisation, settings: Settings) -> bool:
    analysis = opt.analysis
    if not opt.candidate_source:
        opt.status = "failed"
        opt.failure_reason = "no candidate"
        db.commit()
        return False
    if analysis.language == "python":
        report = verify_python(opt.original_source, opt.candidate_source, analysis.case_spec or {}, settings)
    else:
        report = verify_sql(opt.original_source, opt.candidate_source, analysis.case_spec or {}, settings)
    for t in report.tests:
        db.add(TestResult(optimisation_id=opt.id, test_name=t.name, passed=t.passed,
                          failure_type=t.failure_type, details=t.details, duration_ms=t.duration_ms))
    if not report.tests and report.error:
        db.add(TestResult(optimisation_id=opt.id, test_name="verification", passed=False,
                          failure_type=report.failure_type, details=report.error))
    opt.summary = {**(opt.summary or {}), "verification": report.to_dict(),
                   "unchanged": _normalise_ws(opt.candidate_source) == _normalise_ws(opt.original_source)}
    if report.passed:
        opt.status = "verified"
    else:
        opt.status = "rejected"
        opt.failure_reason = f"{report.failure_type}: {report.error or ''}".strip(": ")
    db.commit()
    return report.passed


def _normalise_ws(s: str | None) -> str:
    return " ".join((s or "").split())


# ---------------------------------------------------------------------------
# Benchmark + Measure
# ---------------------------------------------------------------------------

def _default_factor(db: Session, settings: Settings) -> CarbonFactor | None:
    row = db.execute(select(CarbonFactor).where(CarbonFactor.region == settings.carbon_factor_region,
                                                CarbonFactor.is_default.is_(True))).scalars().first()
    if row is None:
        row = db.execute(select(CarbonFactor).where(CarbonFactor.is_default.is_(True))).scalars().first()
    return row


def _store_run(db: Session, opt: Optimisation, variant: str, outcome: BenchmarkOutcome,
               factor: CarbonFactor | None, settings: Settings) -> BenchmarkRun:
    s = outcome.summary
    run = BenchmarkRun(
        optimisation_id=opt.id, variant=variant, repetitions=settings.benchmark_repetitions,
        warmup_runs=settings.benchmark_warmup_runs, samples_ms=outcome.samples_ms,
        environment=outcome.environment, status="completed" if outcome.ok else "failed",
        error=outcome.error,
    )
    if s:
        run.mean_ms, run.median_ms, run.stdev_ms = s.mean, s.median, s.stdev
        run.min_ms, run.max_ms, run.ci95_low_ms, run.ci95_high_ms = s.min, s.max, s.ci95_low, s.ci95_high
        run.repetitions = s.n
    db.add(run)
    db.flush()
    if not outcome.ok:
        return run

    def m(metric: str, value: float, unit: str, method: str = "measured", source: str = "psutil",
          details: dict[str, Any] | None = None, factor_id: str | None = None) -> None:
        db.add(Measurement(benchmark_run_id=run.id, metric=metric, value=float(value), unit=unit,
                           method=method, source=source, details=details or {}, carbon_factor_id=factor_id))

    if outcome.cpu_time_ms is not None:
        m("cpu_time_ms", outcome.cpu_time_ms, "ms")
    if outcome.peak_rss_mb is not None:
        m("peak_rss_mb", outcome.peak_rss_mb, "MB")
    for k, v in outcome.metrics.items():
        m(k, v, "ms" if k.endswith("_ms") else "count" if "blocks" in k or "scans" in k else "unit",
          source="postgresql" if k.startswith("pg_") else "psutil")
    for e in outcome.energy:
        m("energy_joules", e.joules, "J", method=e.method, source=e.source, details=e.details)
        if e.idle_joules is not None:
            m("energy_joules_net", e.net_joules, "J", method=e.method, source=e.source,
              details={"idle_joules": e.idle_joules})
        if factor is not None:
            # CO2e is energy x grid factor: "derived" when the energy was measured, "estimated" otherwise.
            m("co2e_grams", co2e_grams(e.net_joules, factor.grams_co2e_per_kwh), "gCO2e",
              method="derived" if e.method == "measured" else "estimated",
              source=e.source, factor_id=factor.id,
              details={"grams_per_kwh": factor.grams_co2e_per_kwh, "factor_source": factor.source})
    return run


def benchmark_pair(db: Session, opt: Optimisation, settings: Settings,
                   energy_ctx: EnergyContext | None = None) -> bool:
    analysis = opt.analysis
    spec = analysis.case_spec or {}
    energy_ctx = energy_ctx or EnergyContext(settings)
    factor = _default_factor(db, settings)
    if analysis.language == "python":
        orig = benchmark_python(opt.original_source, spec, settings, energy_ctx)
        cand = benchmark_python(opt.candidate_source or "", spec, settings, energy_ctx)
    else:
        orig = benchmark_sql(opt.original_source, settings, energy_ctx)
        cand = benchmark_sql(opt.candidate_source or "", settings, energy_ctx)
    run_o = _store_run(db, opt, "original", orig, factor, settings)
    run_c = _store_run(db, opt, "candidate", cand, factor, settings)
    summary = dict(opt.summary or {})
    if orig.ok and cand.ok:
        summary["timing"] = compare(orig.samples_ms, cand.samples_ms)
        summary["energy"] = _energy_comparison(orig, cand, factor)
        summary["resources"] = {
            "original_cpu_ms": orig.cpu_time_ms, "candidate_cpu_ms": cand.cpu_time_ms,
            "original_peak_rss_mb": orig.peak_rss_mb, "candidate_peak_rss_mb": cand.peak_rss_mb,
        }
        if analysis.language == "sql":
            summary["sql_plan"] = {"original": orig.metrics, "candidate": cand.metrics}
        opt.status = "benchmarked"
    else:
        opt.status = "failed"
        opt.failure_reason = f"benchmark_error: {orig.error or cand.error}"
    summary["benchmark_runs"] = {"original": run_o.id, "candidate": run_c.id}
    opt.summary = summary
    db.commit()
    return orig.ok and cand.ok


def _energy_comparison(orig: BenchmarkOutcome, cand: BenchmarkOutcome,
                       factor: CarbonFactor | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for eo, ec in zip(orig.energy, cand.energy):
        if eo.source != ec.source:
            continue
        o, c = eo.net_joules, ec.net_joules
        entry = {
            "method": eo.method, "original_joules": o, "candidate_joules": c,
            "percent_change": ((c - o) / o * 100) if o else None,
            "energy_ratio": (o / c) if c else None,
        }
        if factor is not None:
            entry["original_co2e_g"] = co2e_grams(o, factor.grams_co2e_per_kwh)
            entry["candidate_co2e_g"] = co2e_grams(c, factor.grams_co2e_per_kwh)
        out[eo.source] = entry
    # H4 evidence: compare time change with energy change for the primary method.
    if orig.summary and cand.summary and out:
        primary = next(iter(out.values()))
        t_pct = ((cand.summary.median - orig.summary.median) / orig.summary.median * 100) if orig.summary.median else None
        out["time_vs_energy"] = {"time_percent_change": t_pct, "energy_percent_change": primary.get("percent_change"),
                                 "divergence_pp": (abs((t_pct or 0) - (primary.get("percent_change") or 0)))}
    return out


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def process_optimisation(db: Session, optimisation_id: str, provider: LLMProvider | None = None,
                         settings: Settings | None = None, energy_ctx: EnergyContext | None = None) -> Optimisation:
    """Run generate → verify → benchmark for one optimisation row."""
    settings = settings or get_settings()
    provider = provider or build_provider(settings)
    opt = db.get(Optimisation, optimisation_id)
    if opt is None:
        raise ValueError("optimisation not found")
    started = time.perf_counter()
    try:
        if opt.status == "pending" and not generate_candidate(db, opt, provider):
            return opt
        if opt.status == "generated" and not verify_candidate(db, opt, settings):
            return opt
        if opt.status == "verified":
            benchmark_pair(db, opt, settings, energy_ctx)
    except Exception as err:  # noqa: BLE001
        log.exception("pipeline failure for optimisation %s", optimisation_id)
        db.rollback()
        opt = db.get(Optimisation, optimisation_id)
        if opt is not None:
            opt.status = "failed"
            opt.failure_reason = f"pipeline_error: {err}"
            db.commit()
    finally:
        if opt is not None:
            opt.summary = {**(opt.summary or {}), "pipeline_seconds": time.perf_counter() - started}
            db.commit()
    return opt
