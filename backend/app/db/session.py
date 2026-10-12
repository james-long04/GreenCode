"""Database engine/session management."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.models import Base, CarbonFactor

_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency."""
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    db = get_sessionmaker()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


DEFAULT_CARBON_FACTORS = [
    # Ireland. SEAI publishes annual grid emission factors; the 2025 provisional
    # "electricity consumption" value is used as the project default. Source:
    # https://www.seai.ie/data-and-insights/seai-statistics/conversion-factors
    dict(
        region="IE",
        year=2025,
        grams_co2e_per_kwh=197.8,
        source="SEAI Conversion Factors – electricity consumption, 2025 (provisional)",
        notes="Operational (location-based) grid intensity for Ireland. Re-check the SEAI spreadsheet before final reporting.",
        is_default=True,
    ),
    dict(
        region="EU",
        year=2023,
        grams_co2e_per_kwh=242.0,
        source="European Environment Agency, GHG intensity of electricity generation (EU-27, 2023)",
        notes="Used for sensitivity analysis.",
        is_default=False,
    ),
    dict(
        region="WORLD",
        year=2023,
        grams_co2e_per_kwh=475.0,
        source="IEA / Green Algorithms default world average",
        notes="Used for sensitivity analysis.",
        is_default=False,
    ),
]


def init_db(create: bool = True) -> None:
    """Create tables (idempotent) and seed reference data."""
    engine = get_engine()
    if create:
        Base.metadata.create_all(engine)
    with session_scope() as db:
        existing = db.execute(select(CarbonFactor)).scalars().all()
        if not existing:
            for row in DEFAULT_CARBON_FACTORS:
                db.add(CarbonFactor(**row))
