"""Benchmark suite loading and the three-condition experiment runner.

A *case* is a JSON file under ``benchmarks/python`` or ``benchmarks/sql``::

    {
      "id": "py_001_membership_list",
      "title": "Membership test against a list inside a loop",
      "language": "python",
      "category": "data_structures",
      "expected_rules": ["PY001"],
      "source": "def solve(items, targets): ...",
      "entry_point": "solve",
      "tests": [{"name": "small", "args": "([1, 2, 3], [2, 5])", "expected": [true, false]}],
      "benchmark": {"setup": "data = list(range(20000)); q = ...", "call": "solve(data, q)"}
    }

For every case the runner creates one analysis (Detect + Explain, shared by both
conditions) and one optimisation per condition. The Baseline condition is the
``original`` benchmark run stored with each optimisation.
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from sqlalchemy.orm import Session

from app.ai.prompts import CONDITIONS
from app.ai.provider import LLMProvider, build_provider
from app.benchmark.runner import EnergyContext
from app.config import Settings, get_settings
from app.db.models import Project
from app.experiments.pipeline import create_analysis, create_optimisation, process_optimisation

log = logging.getLogger("greencode.suite")


@dataclass
class Case:
    id: str
    title: str
    language: str
    source: str
    category: str = ""
    description: str = ""
    expected_rules: list[str] = field(default_factory=list)
    entry_point: str | None = None
    tests: list[dict[str, Any]] = field(default_factory=list)
    benchmark: dict[str, Any] = field(default_factory=dict)
    path: str | None = None

    def spec(self) -> dict[str, Any]:
        spec: dict[str, Any] = {"expected_rules": self.expected_rules, "category": self.category}
        if self.language == "python":
            spec.update({"entry_point": self.entry_point or "solve", "tests": self.tests, "benchmark": self.benchmark})
        return spec

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "language": self.language, "category": self.category,
                "description": self.description, "expected_rules": self.expected_rules,
                "entry_point": self.entry_point, "tests": len(self.tests), "source": self.source,
                "benchmark": self.benchmark}


def suite_dir(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    p = Path(settings.benchmark_suite_dir)
    if not p.is_absolute():
        p = (Path(__file__).resolve().parents[2] / p).resolve()
    return p


def load_cases(root: Path | None = None, language: str | None = None) -> list[Case]:
    root = root or suite_dir()
    cases: list[Case] = []
    for sub in ("python", "sql"):
        if language and sub != language:
            continue
        for path in sorted((root / sub).glob("*.json")):
            data = json.loads(path.read_text())
            cases.append(Case(
                id=data["id"], title=data.get("title", data["id"]), language=data.get("language", sub),
                source=data["source"], category=data.get("category", ""), description=data.get("description", ""),
                expected_rules=data.get("expected_rules", []), entry_point=data.get("entry_point"),
                tests=data.get("tests", []), benchmark=data.get("benchmark", {}), path=str(path),
            ))
    return cases


def get_case(case_id: str, root: Path | None = None) -> Case | None:
    return next((c for c in load_cases(root) if c.id == case_id), None)


ProgressFn = Callable[[dict[str, Any]], None]


def run_suite(db: Session, project_id: str, case_ids: Iterable[str] | None = None,
              conditions: Iterable[str] = CONDITIONS, provider: LLMProvider | None = None,
              settings: Settings | None = None, shuffle: bool = True, seed: int = 42,
              progress: ProgressFn | None = None) -> list[dict[str, Any]]:
    """Run every selected case under every selected condition. Returns per-run summaries."""
    settings = settings or get_settings()
    provider = provider or build_provider(settings)
    if db.get(Project, project_id) is None:
        raise ValueError("project not found")
    cases = load_cases()
    if case_ids:
        wanted = set(case_ids)
        cases = [c for c in cases if c.id in wanted]
    conditions = [c for c in conditions if c in CONDITIONS]
    energy_ctx = EnergyContext(settings)
    # Randomise case order so systematic drift (thermal, background load) is not
    # confounded with case identity. Condition order is alternated per case.
    order = list(cases)
    if shuffle:
        random.Random(seed).shuffle(order)
    results: list[dict[str, Any]] = []
    for i, case in enumerate(order):
        analysis = create_analysis(db, project_id, case.title, case.language, case.source, case.spec(), case.id, settings)
        conds = list(conditions) if i % 2 == 0 else list(reversed(conditions))
        for cond in conds:
            opt = create_optimisation(db, analysis.id, cond)
            opt = process_optimisation(db, opt.id, provider, settings, energy_ctx)
            row = {"case_id": case.id, "language": case.language, "condition": cond, "analysis_id": analysis.id,
                   "optimisation_id": opt.id, "status": opt.status, "failure_reason": opt.failure_reason,
                   "findings": len(analysis.findings),
                   "speedup": (opt.summary or {}).get("timing", {}).get("speedup"),
                   "energy": {k: v.get("percent_change") for k, v in (opt.summary or {}).get("energy", {}).items()
                              if isinstance(v, dict) and "percent_change" in v}}
            results.append(row)
            log.info("case=%s condition=%s status=%s speedup=%s", case.id, cond, opt.status, row["speedup"])
            if progress:
                progress({"done": len(results), "total": len(order) * len(conditions), **row})
    return results
