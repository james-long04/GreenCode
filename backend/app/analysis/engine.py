"""Entry point for static analysis: dispatches by language and times the run."""

from __future__ import annotations

import time
from typing import Any

from app.analysis.base import ANALYSER_VERSION, AnalysisResult, RuleInfo
from app.analysis.python_rules import PYTHON_RULES, analyse_python
from app.analysis.sql_rules import SQL_RULES, analyse_sql

SUPPORTED_LANGUAGES = ("python", "sql")


def all_rules() -> list[RuleInfo]:
    return [*PYTHON_RULES, *SQL_RULES]


def analyse(language: str, source: str, *, explain: dict[str, Any] | None = None,
            table_stats: dict[str, int] | None = None) -> AnalysisResult:
    language = language.lower()
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language '{language}'. Expected one of {SUPPORTED_LANGUAGES}.")
    start = time.perf_counter()
    try:
        if language == "python":
            findings = analyse_python(source)
        else:
            findings = analyse_sql(source, explain=explain, table_stats=table_stats)
        error = None
    except (SyntaxError, ValueError) as err:
        findings, error = [], f"{type(err).__name__}: {err}"
    duration_ms = (time.perf_counter() - start) * 1000
    return AnalysisResult(language=language, findings=findings, duration_ms=duration_ms,
                          analyser_version=ANALYSER_VERSION, error=error)
