"""REST API for the GreenCode dashboard and scripts."""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app import schemas
from app.ai.provider import build_provider
from app.analysis.engine import all_rules
from app.benchmark.energy import codecarbon_available, rapl_available, select_method
from app.config import get_settings
from app.db.models import Analysis, BenchmarkRun, CarbonFactor, Finding, Optimisation, Project
from app.db.session import get_db, session_scope
from app.experiments import results as results_mod
from app.experiments.pipeline import create_analysis, create_optimisation, process_optimisation
from app.experiments.suite import load_cases, run_suite

log = logging.getLogger("greencode.api")
router = APIRouter()

# In-memory registry of background suite runs (single-process deployment).
_JOBS: dict[str, schemas.SuiteRunStatus] = {}
_JOBS_LOCK = threading.Lock()


# --- health -----------------------------------------------------------------

@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, Any]:
    settings = get_settings()
    try:
        db.execute(select(func.count(Project.id)))
        db_ok = True
    except Exception as err:  # noqa: BLE001
        db_ok = False
        log.warning("db health failed: %s", err)
    provider = build_provider(settings)
    return {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
        "llm": provider.health(),
        "energy": {"selected": select_method(settings), "rapl": rapl_available(),
                   "codecarbon": codecarbon_available()},
        "settings": {"model": settings.ollama_model, "provider": settings.llm_provider,
                     "repetitions": settings.benchmark_repetitions, "warmup": settings.benchmark_warmup_runs,
                     "region": settings.carbon_factor_region},
    }


@router.get("/rules", response_model=list[schemas.RuleOut])
def rules() -> list[schemas.RuleOut]:
    return [schemas.RuleOut(**r.__dict__) for r in all_rules()]


# --- projects ---------------------------------------------------------------

@router.get("/projects", response_model=list[schemas.ProjectOut])
def list_projects(db: Session = Depends(get_db)) -> list[schemas.ProjectOut]:
    rows = db.execute(
        select(Project, func.count(Analysis.id)).outerjoin(Analysis).group_by(Project.id).order_by(Project.created_at.desc())
    ).all()
    return [schemas.ProjectOut(id=p.id, name=p.name, description=p.description, created_at=p.created_at,
                               analysis_count=n) for p, n in rows]


@router.post("/projects", response_model=schemas.ProjectOut, status_code=201)
def create_project(body: schemas.ProjectCreate, db: Session = Depends(get_db)) -> schemas.ProjectOut:
    p = Project(name=body.name, description=body.description)
    db.add(p)
    db.commit()
    db.refresh(p)
    return schemas.ProjectOut(id=p.id, name=p.name, description=p.description, created_at=p.created_at)


@router.get("/projects/{project_id}", response_model=schemas.ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)) -> schemas.ProjectOut:
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(404, "project not found")
    n = db.scalar(select(func.count(Analysis.id)).where(Analysis.project_id == project_id)) or 0
    return schemas.ProjectOut(id=p.id, name=p.name, description=p.description, created_at=p.created_at, analysis_count=n)


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db)) -> None:
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(404, "project not found")
    db.delete(p)
    db.commit()


# --- analyses ---------------------------------------------------------------

@router.get("/analyses", response_model=list[schemas.AnalysisSummary])
def list_analyses(project_id: str | None = None, language: str | None = None, limit: int = Query(200, le=1000),
                  db: Session = Depends(get_db)) -> list[schemas.AnalysisSummary]:
    stmt = select(Analysis).options(selectinload(Analysis.findings), selectinload(Analysis.optimisations))
    if project_id:
        stmt = stmt.where(Analysis.project_id == project_id)
    if language:
        stmt = stmt.where(Analysis.language == language)
    stmt = stmt.order_by(Analysis.created_at.desc()).limit(limit)
    out = []
    for a in db.execute(stmt).scalars().all():
        out.append(schemas.AnalysisSummary(id=a.id, project_id=a.project_id, name=a.name, language=a.language,
                                           case_id=a.case_id, status=a.status, created_at=a.created_at,
                                           finding_count=len(a.findings), optimisation_count=len(a.optimisations)))
    return out


@router.post("/analyses", response_model=schemas.AnalysisOut, status_code=201)
def post_analysis(body: schemas.AnalysisCreate, db: Session = Depends(get_db)) -> Analysis:
    try:
        return create_analysis(db, body.project_id, body.name, body.language, body.source, body.case_spec, body.case_id)
    except ValueError as err:
        raise HTTPException(400, str(err)) from err


@router.get("/analyses/{analysis_id}", response_model=schemas.AnalysisOut)
def get_analysis(analysis_id: str, db: Session = Depends(get_db)) -> Analysis:
    a = db.get(Analysis, analysis_id, options=[selectinload(Analysis.findings)])
    if a is None:
        raise HTTPException(404, "analysis not found")
    a.findings.sort(key=lambda f: ((f.line or 0), f.rule_id))
    return a


@router.get("/analyses/{analysis_id}/findings", response_model=list[schemas.FindingOut])
def get_findings(analysis_id: str, db: Session = Depends(get_db)) -> list[Finding]:
    rows = db.execute(select(Finding).where(Finding.analysis_id == analysis_id)).scalars().all()
    return sorted(rows, key=lambda f: ((f.line or 0), f.rule_id))


@router.get("/analyses/{analysis_id}/optimisations", response_model=list[schemas.OptimisationSummary])
def analysis_optimisations(analysis_id: str, db: Session = Depends(get_db)) -> list[Optimisation]:
    return db.execute(select(Optimisation).where(Optimisation.analysis_id == analysis_id)
                      .order_by(Optimisation.created_at)).scalars().all()


# --- optimisations ----------------------------------------------------------

def _run_pipeline_bg(optimisation_id: str) -> None:
    with session_scope() as db:
        process_optimisation(db, optimisation_id)


@router.post("/optimisations", response_model=schemas.OptimisationSummary, status_code=202)
def post_optimisation(body: schemas.OptimisationCreate, background: BackgroundTasks,
                      db: Session = Depends(get_db)) -> Optimisation:
    try:
        opt = create_optimisation(db, body.analysis_id, body.condition)
    except ValueError as err:
        raise HTTPException(400, str(err)) from err
    if body.run_pipeline:
        background.add_task(_run_pipeline_bg, opt.id)
    return opt


@router.get("/optimisations", response_model=list[schemas.OptimisationSummary])
def list_optimisations(project_id: str | None = None, condition: str | None = None, status: str | None = None,
                       limit: int = Query(500, le=5000), db: Session = Depends(get_db)) -> list[Optimisation]:
    stmt = select(Optimisation).join(Analysis)
    if project_id:
        stmt = stmt.where(Analysis.project_id == project_id)
    if condition:
        stmt = stmt.where(Optimisation.condition == condition)
    if status:
        stmt = stmt.where(Optimisation.status == status)
    return db.execute(stmt.order_by(Optimisation.created_at.desc()).limit(limit)).scalars().all()


@router.get("/optimisations/{optimisation_id}", response_model=schemas.OptimisationOut)
def get_optimisation(optimisation_id: str, db: Session = Depends(get_db)) -> Optimisation:
    opt = db.get(Optimisation, optimisation_id, options=[
        selectinload(Optimisation.test_results),
        selectinload(Optimisation.benchmark_runs).selectinload(BenchmarkRun.measurements),
    ])
    if opt is None:
        raise HTTPException(404, "optimisation not found")
    return opt


@router.post("/optimisations/{optimisation_id}/rerun", response_model=schemas.OptimisationSummary, status_code=202)
def rerun_optimisation(optimisation_id: str, background: BackgroundTasks, db: Session = Depends(get_db)) -> Optimisation:
    opt = db.get(Optimisation, optimisation_id)
    if opt is None:
        raise HTTPException(404, "optimisation not found")
    for tr in list(opt.test_results):
        db.delete(tr)
    for br in list(opt.benchmark_runs):
        db.delete(br)
    opt.status, opt.failure_reason, opt.summary, opt.candidate_source = "pending", None, {}, None
    db.commit()
    background.add_task(_run_pipeline_bg, opt.id)
    return opt


# --- benchmark suite / experiments ----------------------------------------

@router.get("/suite/cases")
def suite_cases(language: str | None = None) -> list[dict[str, Any]]:
    return [c.to_dict() for c in load_cases(language=language)]


def _run_suite_bg(job_id: str, req: schemas.SuiteRunRequest) -> None:
    def progress(ev: dict[str, Any]) -> None:
        with _JOBS_LOCK:
            job = _JOBS[job_id]
            job.done, job.total = ev["done"], ev["total"]
            job.results.append({k: v for k, v in ev.items() if k not in {"done", "total"}})

    try:
        with session_scope() as db:
            run_suite(db, req.project_id, req.case_ids, req.conditions, shuffle=req.shuffle, seed=req.seed,
                      progress=progress)
        with _JOBS_LOCK:
            _JOBS[job_id].status = "completed"
    except Exception as err:  # noqa: BLE001
        log.exception("suite run failed")
        with _JOBS_LOCK:
            _JOBS[job_id].status = "failed"
            _JOBS[job_id].error = str(err)
    finally:
        with _JOBS_LOCK:
            _JOBS[job_id].finished_at = datetime.now(timezone.utc)


@router.post("/suite/run", response_model=schemas.SuiteRunStatus, status_code=202)
def run_suite_endpoint(req: schemas.SuiteRunRequest, background: BackgroundTasks,
                       db: Session = Depends(get_db)) -> schemas.SuiteRunStatus:
    if db.get(Project, req.project_id) is None:
        raise HTTPException(404, "project not found")
    with _JOBS_LOCK:
        running = [j for j in _JOBS.values() if j.status == "running"]
    if running:
        raise HTTPException(409, f"a suite run is already in progress ({running[0].job_id})")
    job_id = str(uuid.uuid4())
    n_cases = len(req.case_ids) if req.case_ids else len(load_cases())
    job = schemas.SuiteRunStatus(job_id=job_id, status="running", total=n_cases * len(req.conditions),
                                 started_at=datetime.now(timezone.utc))
    with _JOBS_LOCK:
        _JOBS[job_id] = job
    background.add_task(_run_suite_bg, job_id, req)
    return job


@router.get("/suite/jobs", response_model=list[schemas.SuiteRunStatus])
def suite_jobs() -> list[schemas.SuiteRunStatus]:
    with _JOBS_LOCK:
        return sorted(_JOBS.values(), key=lambda j: j.started_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)


@router.get("/suite/jobs/{job_id}", response_model=schemas.SuiteRunStatus)
def suite_job(job_id: str) -> schemas.SuiteRunStatus:
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return job


# --- results ----------------------------------------------------------------

@router.get("/results")
def results(project_id: str | None = None, language: str | None = None,
            db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return results_mod.collect(db, project_id, language)


@router.get("/results/summary")
def results_summary(project_id: str | None = None, language: str | None = None,
                    db: Session = Depends(get_db)) -> dict[str, Any]:
    return results_mod.summarise(results_mod.collect(db, project_id, language))


@router.get("/carbon-factors", response_model=list[schemas.CarbonFactorOut])
def carbon_factors(db: Session = Depends(get_db)) -> list[CarbonFactor]:
    return db.execute(select(CarbonFactor).order_by(CarbonFactor.region, CarbonFactor.year.desc())).scalars().all()
