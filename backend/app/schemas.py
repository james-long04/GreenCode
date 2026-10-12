"""Pydantic request/response models for the REST API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- projects ---------------------------------------------------------------

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class ProjectOut(ORMModel):
    id: str
    name: str
    description: str | None
    created_at: datetime
    analysis_count: int = 0


# --- analyses ---------------------------------------------------------------

class AnalysisCreate(BaseModel):
    project_id: str
    name: str = Field(min_length=1, max_length=200)
    language: str = Field(pattern="^(python|sql)$")
    source: str = Field(min_length=1)
    case_spec: dict[str, Any] = Field(default_factory=dict)
    case_id: str | None = None


class FindingOut(ORMModel):
    id: str
    rule_id: str
    title: str
    severity: str
    category: str
    line: int | None
    column: int | None
    end_line: int | None
    snippet: str | None
    explanation: str
    suggestion: str
    confidence: float
    evidence: dict[str, Any]


class AnalysisOut(ORMModel):
    id: str
    project_id: str
    name: str
    language: str
    source: str
    case_spec: dict[str, Any]
    case_id: str | None
    status: str
    analyser_version: str
    duration_ms: float | None
    created_at: datetime
    findings: list[FindingOut] = []


class AnalysisSummary(ORMModel):
    id: str
    project_id: str
    name: str
    language: str
    case_id: str | None
    status: str
    created_at: datetime
    finding_count: int = 0
    optimisation_count: int = 0


# --- optimisations ----------------------------------------------------------

class OptimisationCreate(BaseModel):
    analysis_id: str
    condition: str = Field(pattern="^(ai_only|greencode)$")
    run_pipeline: bool = True


class TestResultOut(ORMModel):
    id: str
    test_name: str
    passed: bool
    failure_type: str | None
    details: str | None
    duration_ms: float | None


class MeasurementOut(ORMModel):
    id: str
    metric: str
    value: float
    unit: str
    method: str
    source: str
    details: dict[str, Any]


class BenchmarkRunOut(ORMModel):
    id: str
    variant: str
    repetitions: int
    warmup_runs: int
    mean_ms: float | None
    median_ms: float | None
    stdev_ms: float | None
    min_ms: float | None
    max_ms: float | None
    ci95_low_ms: float | None
    ci95_high_ms: float | None
    samples_ms: list[float]
    environment: dict[str, Any]
    status: str
    error: str | None
    measurements: list[MeasurementOut] = []


class OptimisationOut(ORMModel):
    id: str
    analysis_id: str
    condition: str
    original_source: str
    candidate_source: str | None
    model_name: str
    provider: str
    prompt: str | None
    raw_response: str | None
    generation_ms: float | None
    prompt_tokens: int | None
    completion_tokens: int | None
    status: str
    failure_reason: str | None
    summary: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    test_results: list[TestResultOut] = []
    benchmark_runs: list[BenchmarkRunOut] = []


class OptimisationSummary(ORMModel):
    id: str
    analysis_id: str
    condition: str
    status: str
    model_name: str
    failure_reason: str | None
    summary: dict[str, Any]
    created_at: datetime


# --- experiments ------------------------------------------------------------

class SuiteRunRequest(BaseModel):
    project_id: str
    case_ids: list[str] | None = None
    conditions: list[str] = ["ai_only", "greencode"]
    shuffle: bool = True
    seed: int = 42


class SuiteRunStatus(BaseModel):
    job_id: str
    status: str
    done: int = 0
    total: int = 0
    results: list[dict[str, Any]] = []
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class CarbonFactorOut(ORMModel):
    id: str
    region: str
    year: int
    grams_co2e_per_kwh: float
    source: str
    notes: str | None
    is_default: bool


class RuleOut(BaseModel):
    rule_id: str
    name: str
    language: str
    category: str
    severity: str
    description: str
