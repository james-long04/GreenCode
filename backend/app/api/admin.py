"""Admin API: operate the evidence store and the pipeline configuration.

Everything here is for the person running the experiment. Nothing changes the
scientific method: prompts, rules and statistics live elsewhere and are not
editable from the panel.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import platform
import secrets
import sys
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import psutil
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import schemas
from app.ai.provider import build_provider
from app.benchmark.energy import codecarbon_available, rapl_available, select_method
from app.config import (RUNTIME_ADJUSTABLE, admin_token_is_generated, clear_runtime_overrides, effective_admin_token,
                        get_settings, runtime_overrides, set_runtime_overrides)
from app.db.models import Analysis, BenchmarkRun, CarbonFactor, Finding, Measurement, Optimisation, Project
from app.db.session import get_db
from app.experiments import results as results_mod
from app.logbuffer import recent as recent_logs

log = logging.getLogger("greencode.admin")

ACTIVE_STATUSES = ("pending", "generated", "verified")
_SECRET_KEYS = {"admin_token"}
_URL_KEYS = {"database_url", "benchmark_database_url"}


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Every admin route needs the token. There is no open mode."""
    if not x_admin_token or not secrets.compare_digest(x_admin_token, effective_admin_token()):
        raise HTTPException(401, "admin token required")


router = APIRouter(dependencies=[Depends(require_admin)])


def _mask_url(url: str) -> str:
    # postgresql://user:password@host/db -> postgresql://user:***@host/db
    if "@" in url and "://" in url:
        head, tail = url.split("://", 1)
        creds, rest = tail.rsplit("@", 1)
        if ":" in creds:
            creds = creds.split(":", 1)[0] + ":***"
        return f"{head}://{creds}@{rest}"
    return url


# --- overview ------------------------------------------------------------------

@router.get("/overview")
def overview(db: Session = Depends(get_db)) -> dict[str, Any]:
    settings = get_settings()
    counts = {
        "projects": db.scalar(select(func.count(Project.id))) or 0,
        "analyses": db.scalar(select(func.count(Analysis.id))) or 0,
        "findings": db.scalar(select(func.count(Finding.id))) or 0,
        "optimisations": db.scalar(select(func.count(Optimisation.id))) or 0,
        "benchmark_runs": db.scalar(select(func.count(BenchmarkRun.id))) or 0,
        "measurements": db.scalar(select(func.count(Measurement.id))) or 0,
    }
    by_status = dict(db.execute(select(Optimisation.status, func.count(Optimisation.id)).group_by(Optimisation.status)).all())
    stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
    stuck = db.scalar(select(func.count(Optimisation.id)).where(Optimisation.status.in_(ACTIVE_STATUSES),
                                                               Optimisation.updated_at < stale_cutoff)) or 0
    orphan_analyses = db.scalar(
        select(func.count(Analysis.id)).where(~Analysis.id.in_(select(Optimisation.analysis_id)))
    ) or 0
    first = db.scalar(select(func.min(Optimisation.created_at)))
    last = db.scalar(select(func.max(Optimisation.created_at)))
    try:
        db_size = db.scalar(text("SELECT pg_database_size(current_database())"))
        db_version = db.scalar(text("SHOW server_version"))
    except Exception:  # noqa: BLE001
        db_size, db_version = None, None
    vm = psutil.virtual_memory()
    return {
        "store": {"counts": counts, "optimisations_by_status": by_status, "stuck_optimisations": stuck,
                  "orphan_analyses": orphan_analyses, "first_run": first, "last_run": last,
                  "database_bytes": db_size, "postgres_version": db_version,
                  "database_url": _mask_url(settings.database_url)},
        "llm": build_provider(settings).health(),
        "energy": {"selected": select_method(settings), "rapl": rapl_available(), "codecarbon": codecarbon_available(),
                   "configured": settings.energy_method},
        "host": {"python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.machine(),
                 "logical_cores": os.cpu_count(), "physical_cores": psutil.cpu_count(logical=False),
                 "memory_total_gb": round(vm.total / 1e9, 2), "memory_used_percent": vm.percent,
                 "cpu_percent": psutil.cpu_percent(interval=None), "pid": os.getpid(),
                 "cwd": os.getcwd()},
        "admin_token_generated": admin_token_is_generated(),
    }


# --- settings --------------------------------------------------------------------

def _settings_payload() -> dict[str, Any]:
    s = get_settings()
    values: dict[str, Any] = {}
    for key, value in s.model_dump().items():
        if key in _SECRET_KEYS:
            continue
        values[key] = _mask_url(value) if key in _URL_KEYS and isinstance(value, str) else value
    return {"values": values, "overrides": runtime_overrides(), "adjustable": sorted(RUNTIME_ADJUSTABLE)}


@router.get("/settings")
def settings_get() -> dict[str, Any]:
    return _settings_payload()


@router.put("/settings")
def settings_put(body: schemas.SettingsUpdate) -> dict[str, Any]:
    try:
        set_runtime_overrides(body.values)
    except ValueError as err:
        raise HTTPException(422, str(err)) from err
    except Exception as err:  # noqa: BLE001  (pydantic validation)
        raise HTTPException(422, f"invalid value: {err}") from err
    log.info("settings overridden at runtime: %s", ", ".join(sorted(body.values)))
    return _settings_payload()


@router.delete("/settings")
def settings_reset() -> dict[str, Any]:
    clear_runtime_overrides()
    log.info("runtime setting overrides cleared")
    return _settings_payload()


# --- models (Ollama) -------------------------------------------------------------

_PULLS: dict[str, schemas.ModelPullStatus] = {}
_PULLS_LOCK = threading.Lock()


@router.get("/models")
def models() -> dict[str, Any]:
    settings = get_settings()
    health = build_provider(settings).health()
    installed: list[dict[str, Any]] = []
    if settings.llm_provider == "ollama" and health.get("ok"):
        try:
            with httpx.Client(timeout=5.0) as client:
                data = client.get(f"{settings.ollama_base_url}/api/tags").json()
            for m in data.get("models", []):
                installed.append({"name": m.get("name"), "size_bytes": m.get("size"),
                                  "modified_at": m.get("modified_at"),
                                  "parameter_size": (m.get("details") or {}).get("parameter_size"),
                                  "quantization": (m.get("details") or {}).get("quantization_level")})
        except Exception as err:  # noqa: BLE001
            health = {**health, "ok": False, "error": str(err)}
    with _PULLS_LOCK:
        pulls = sorted(_PULLS.values(), key=lambda p: p.started_at or datetime.min.replace(tzinfo=timezone.utc),
                       reverse=True)
    return {"health": health, "configured": settings.ollama_model, "installed": installed, "pulls": pulls}


def _pull_bg(name: str) -> None:
    settings = get_settings()
    try:
        with httpx.Client(timeout=None) as client, client.stream(
            "POST", f"{settings.ollama_base_url}/api/pull", json={"name": name, "stream": True}
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                ev = json.loads(line)
                with _PULLS_LOCK:
                    st = _PULLS[name]
                    st.detail = ev.get("status", "")
                    st.completed_bytes = ev.get("completed", st.completed_bytes)
                    st.total_bytes = ev.get("total", st.total_bytes)
                    if ev.get("error"):
                        st.status, st.error = "failed", ev["error"]
        with _PULLS_LOCK:
            if _PULLS[name].status == "running":
                _PULLS[name].status = "completed"
    except Exception as err:  # noqa: BLE001
        with _PULLS_LOCK:
            _PULLS[name].status, _PULLS[name].error = "failed", str(err)
    finally:
        with _PULLS_LOCK:
            _PULLS[name].finished_at = datetime.now(timezone.utc)
        log.info("model pull %s: %s", name, _PULLS[name].status)


@router.post("/models/pull", response_model=schemas.ModelPullStatus, status_code=202)
def pull_model(body: schemas.ModelPullRequest, background: BackgroundTasks) -> schemas.ModelPullStatus:
    settings = get_settings()
    if settings.llm_provider != "ollama":
        raise HTTPException(409, "model pulls only apply to the ollama provider")
    with _PULLS_LOCK:
        running = _PULLS.get(body.name)
        if running and running.status == "running":
            return running
        st = schemas.ModelPullStatus(name=body.name, status="running", started_at=datetime.now(timezone.utc))
        _PULLS[body.name] = st
    background.add_task(_pull_bg, body.name)
    return st


# --- carbon factors ---------------------------------------------------------------

@router.post("/carbon-factors", response_model=schemas.CarbonFactorOut, status_code=201)
def carbon_factor_create(body: schemas.CarbonFactorIn, db: Session = Depends(get_db)) -> CarbonFactor:
    if body.is_default:
        db.execute(CarbonFactor.__table__.update().values(is_default=False))
    row = CarbonFactor(**body.model_dump())
    db.add(row)
    try:
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(409, "a factor for that region, year and source already exists") from err
    db.refresh(row)
    return row


@router.put("/carbon-factors/{factor_id}", response_model=schemas.CarbonFactorOut)
def carbon_factor_update(factor_id: str, body: schemas.CarbonFactorIn, db: Session = Depends(get_db)) -> CarbonFactor:
    row = db.get(CarbonFactor, factor_id)
    if row is None:
        raise HTTPException(404, "carbon factor not found")
    used = db.scalar(select(func.count(Measurement.id)).where(Measurement.carbon_factor_id == factor_id)) or 0
    if used and (row.grams_co2e_per_kwh != body.grams_co2e_per_kwh or row.region != body.region or row.year != body.year):
        raise HTTPException(409, f"this factor is referenced by {used} measurements; add a new factor instead of "
                                 "changing a value that evidence already depends on")
    if body.is_default:
        db.execute(CarbonFactor.__table__.update().values(is_default=False))
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    try:
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(409, "a factor for that region, year and source already exists") from err
    db.refresh(row)
    return row


@router.delete("/carbon-factors/{factor_id}", status_code=204)
def carbon_factor_delete(factor_id: str, db: Session = Depends(get_db)) -> None:
    row = db.get(CarbonFactor, factor_id)
    if row is None:
        raise HTTPException(404, "carbon factor not found")
    used = db.scalar(select(func.count(Measurement.id)).where(Measurement.carbon_factor_id == factor_id)) or 0
    if used:
        raise HTTPException(409, f"this factor is referenced by {used} measurements and cannot be deleted")
    if row.is_default:
        raise HTTPException(409, "make another factor the default first")
    db.delete(row)
    db.commit()


# --- maintenance ----------------------------------------------------------------

@router.post("/maintenance/mark-stuck-failed")
def mark_stuck_failed(older_than_minutes: int = Query(30, ge=1), db: Session = Depends(get_db)) -> dict[str, int]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)
    rows = db.execute(select(Optimisation).where(Optimisation.status.in_(ACTIVE_STATUSES),
                                                 Optimisation.updated_at < cutoff)).scalars().all()
    for opt in rows:
        opt.status = "failed"
        opt.failure_reason = f"marked failed by admin: no progress for {older_than_minutes} minutes"
    db.commit()
    log.info("marked %d stuck optimisations failed", len(rows))
    return {"updated": len(rows)}


@router.delete("/maintenance/orphan-analyses")
def delete_orphan_analyses(db: Session = Depends(get_db)) -> dict[str, int]:
    ids = db.execute(select(Analysis.id).where(~Analysis.id.in_(select(Optimisation.analysis_id)))).scalars().all()
    if ids:
        db.execute(delete(Analysis).where(Analysis.id.in_(ids)))
        db.commit()
    log.info("deleted %d analyses without optimisations", len(ids))
    return {"deleted": len(ids)}


@router.delete("/maintenance/project-runs/{project_id}")
def delete_project_runs(project_id: str, status: str = Query(..., pattern="^(failed|rejected)$"),
                        db: Session = Depends(get_db)) -> dict[str, int]:
    """Delete failed or rejected optimisations in one project. Benchmarked evidence is never deleted here."""
    if db.get(Project, project_id) is None:
        raise HTTPException(404, "project not found")
    ids = db.execute(select(Optimisation.id).join(Analysis).where(Analysis.project_id == project_id,
                                                                  Optimisation.status == status)).scalars().all()
    if ids:
        db.execute(delete(Optimisation).where(Optimisation.id.in_(ids)))
        db.commit()
    log.info("deleted %d %s optimisations in project %s", len(ids), status, project_id)
    return {"deleted": len(ids)}


# --- export ----------------------------------------------------------------------

@router.get("/export/results.csv")
def export_results_csv(project_id: str | None = None, db: Session = Depends(get_db)) -> StreamingResponse:
    rows = results_mod.collect(db, project_id=project_id)
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow({k: ("" if v is None else (";".join(v) if isinstance(v, list) else v)) for k, v in r.items()})
    buf.seek(0)
    name = f"greencode-results{'-' + project_id[:8] if project_id else ''}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


# --- logs ---------------------------------------------------------------------------

@router.get("/logs")
def logs(limit: int = Query(200, ge=1, le=500), level: str | None = None) -> list[dict[str, Any]]:
    return recent_logs(limit=limit, level=level)
