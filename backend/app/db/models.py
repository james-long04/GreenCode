"""SQLAlchemy ORM models for the GreenCode evidence store.

The eight tables mirror section 11 of the project proposal:

projects → analyses → findings
                   → optimisations → test_results
                                   → benchmark_runs → measurements
carbon_factors (reference data)

Every stage of the Detect → Explain → Optimise → Test → Benchmark → Measure
pipeline writes a row, so the full evidence trail for a result can be
reconstructed from the database alone.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    analyses: Mapped[list["Analysis"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Analysis(Base):
    """A submitted piece of Python code or a SQL query."""

    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False)  # python | sql
    source: Mapped[str] = mapped_column(Text, nullable=False)
    # Benchmark-case metadata (entry point, test inputs, workload). Stored as JSON so
    # ad-hoc submissions from the dashboard and suite cases share one table.
    case_spec: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    case_id: Mapped[str | None] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(32), default="analysed")
    analyser_version: Mapped[str] = mapped_column(String(32), default="")
    duration_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    project: Mapped[Project] = relationship(back_populates="analyses")
    findings: Mapped[list["Finding"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")
    optimisations: Mapped[list["Optimisation"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class Finding(Base):
    """A statically detected inefficiency together with its explanation."""

    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    category: Mapped[str] = mapped_column(String(64), default="")
    line: Mapped[int | None] = mapped_column(Integer)
    column: Mapped[int | None] = mapped_column(Integer)
    end_line: Mapped[int | None] = mapped_column(Integer)
    snippet: Mapped[str | None] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    analysis: Mapped[Analysis] = relationship(back_populates="findings")


class Optimisation(Base):
    """An AI-generated candidate for one analysis under one experimental condition."""

    __tablename__ = "optimisations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    condition: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # ai_only | greencode
    original_source: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_source: Mapped[str | None] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String(120), default="")
    provider: Mapped[str] = mapped_column(String(32), default="")
    prompt: Mapped[str | None] = mapped_column(Text)
    raw_response: Mapped[str | None] = mapped_column(Text)
    generation_ms: Mapped[float | None] = mapped_column(Float)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    # pending → generated → verified | rejected → benchmarked | failed
    failure_reason: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    analysis: Mapped[Analysis] = relationship(back_populates="optimisations")
    test_results: Mapped[list["TestResult"]] = relationship(
        back_populates="optimisation", cascade="all, delete-orphan"
    )
    benchmark_runs: Mapped[list["BenchmarkRun"]] = relationship(
        back_populates="optimisation", cascade="all, delete-orphan"
    )


class TestResult(Base):
    """Correctness result for a candidate (one row per test case)."""

    __tablename__ = "test_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    optimisation_id: Mapped[str] = mapped_column(
        ForeignKey("optimisations.id", ondelete="CASCADE"), index=True
    )
    test_name: Mapped[str] = mapped_column(String(200), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_type: Mapped[str | None] = mapped_column(String(64))
    # compile_error | runtime_error | wrong_output | timeout | resource_limit | unsafe | sql_error
    details: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    optimisation: Mapped[Optimisation] = relationship(back_populates="test_results")


class BenchmarkRun(Base):
    """A batch of repeated executions of one variant (original or candidate)."""

    __tablename__ = "benchmark_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    optimisation_id: Mapped[str] = mapped_column(
        ForeignKey("optimisations.id", ondelete="CASCADE"), index=True
    )
    variant: Mapped[str] = mapped_column(String(16), nullable=False)  # original | candidate
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False)
    warmup_runs: Mapped[int] = mapped_column(Integer, nullable=False)
    mean_ms: Mapped[float | None] = mapped_column(Float)
    median_ms: Mapped[float | None] = mapped_column(Float)
    stdev_ms: Mapped[float | None] = mapped_column(Float)
    min_ms: Mapped[float | None] = mapped_column(Float)
    max_ms: Mapped[float | None] = mapped_column(Float)
    ci95_low_ms: Mapped[float | None] = mapped_column(Float)
    ci95_high_ms: Mapped[float | None] = mapped_column(Float)
    samples_ms: Mapped[list[float]] = mapped_column(JSON, default=list)
    environment: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    optimisation: Mapped[Optimisation] = relationship(back_populates="benchmark_runs")
    measurements: Mapped[list["Measurement"]] = relationship(
        back_populates="benchmark_run", cascade="all, delete-orphan"
    )


class Measurement(Base):
    """Resource, energy and carbon measurements aggregated over a benchmark run."""

    __tablename__ = "measurements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    benchmark_run_id: Mapped[str] = mapped_column(
        ForeignKey("benchmark_runs.id", ondelete="CASCADE"), index=True
    )
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    # cpu_time_ms | peak_rss_mb | cpu_percent | energy_joules | co2e_grams | pg_total_cost | ...
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    method: Mapped[str] = mapped_column(String(32), default="measured")  # measured | estimated
    source: Mapped[str] = mapped_column(String(64), default="")  # psutil | rapl | codecarbon | ...
    carbon_factor_id: Mapped[str | None] = mapped_column(ForeignKey("carbon_factors.id"))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    benchmark_run: Mapped[BenchmarkRun] = relationship(back_populates="measurements")
    carbon_factor: Mapped["CarbonFactor | None"] = relationship()


class CarbonFactor(Base):
    """Environmental assumptions used to convert energy into CO2e.

    Values are deliberately stored with their source so every CO2e figure in the
    results can be traced back to an explicit, citable assumption.
    """

    __tablename__ = "carbon_factors"
    __table_args__ = (UniqueConstraint("region", "year", "source", name="uq_carbon_factor"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    region: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    grams_co2e_per_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(300), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
