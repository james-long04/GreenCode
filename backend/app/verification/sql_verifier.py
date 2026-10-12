"""Result-equivalence verification for SQL candidates.

A candidate query is accepted only if, against the controlled benchmark
dataset, it returns the same column names (in the same order) and the same
multiset of rows as the original. If the original has an ORDER BY the row
order must match as well.
"""

from __future__ import annotations

import datetime as dt
import decimal
import time
from typing import Any

import psycopg
import sqlglot
from sqlglot import exp

from app.config import Settings, get_settings
from app.db.benchdb import bench_connection
from app.verification.python_verifier import TestOutcome, VerificationReport

MAX_COMPARE_ROWS = 200_000


def sql_safety_check(candidate: str) -> str | None:
    try:
        statements = sqlglot.parse(candidate, read="postgres")
    except sqlglot.errors.ParseError as err:
        return f"compile_error: {err}"
    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        return f"expected exactly one statement, got {len(statements)}"
    stmt = statements[0]
    if not isinstance(stmt, (exp.Select, exp.Union)) and not (isinstance(stmt, exp.With) and isinstance(stmt.this, (exp.Select, exp.Union))):
        return f"only SELECT statements are permitted (got {type(stmt).__name__})"
    for node in stmt.walk():
        if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter, exp.Command)):
            return f"unsafe statement '{type(node).__name__}' inside query"
    return None


def _normalise(v: Any) -> Any:
    if isinstance(v, decimal.Decimal):
        return str(v.normalize()) if v == v.to_integral() else str(v)
    if isinstance(v, (dt.datetime, dt.date, dt.time)):
        return v.isoformat()
    if isinstance(v, float):
        return round(v, 9)
    if isinstance(v, memoryview):
        return bytes(v).hex()
    if isinstance(v, (list, tuple)):
        return tuple(_normalise(x) for x in v)
    if isinstance(v, dict):
        return tuple(sorted((k, _normalise(x)) for k, x in v.items()))
    return v


def _run(conn: psycopg.Connection, sql: str) -> tuple[list[str], list[tuple[Any, ...]], float]:
    start = time.perf_counter()
    with conn.cursor() as cur:
        cur.execute(sql)
        cols = [d.name for d in cur.description or []]
        rows = cur.fetchmany(MAX_COMPARE_ROWS + 1)
    conn.rollback()
    return cols, [tuple(_normalise(v) for v in r) for r in rows], (time.perf_counter() - start) * 1000


def _has_order_by(sql: str) -> bool:
    try:
        tree = sqlglot.parse_one(sql, read="postgres")
    except sqlglot.errors.ParseError:
        return False
    root = tree.this if isinstance(tree, exp.With) else tree
    return isinstance(root, exp.Select) and root.args.get("order") is not None


def verify_sql(original: str, candidate: str, spec: dict[str, Any] | None = None,
               settings: Settings | None = None) -> VerificationReport:
    settings = settings or get_settings()
    unsafe = sql_safety_check(candidate)
    if unsafe:
        ftype = "compile_error" if unsafe.startswith("compile_error") else "unsafe"
        return VerificationReport(passed=False, failure_type=ftype, error=unsafe,
                                  tests=[TestOutcome("static_safety", False, ftype, unsafe)])
    try:
        with bench_connection(settings, read_only=True) as conn:
            try:
                ref_cols, ref_rows, ref_ms = _run(conn, original)
            except psycopg.Error as err:
                conn.rollback()
                return VerificationReport(passed=False, failure_type="reference_failed",
                                          error=f"original query failed: {err}")
            try:
                cand_cols, cand_rows, cand_ms = _run(conn, candidate)
            except psycopg.Error as err:
                conn.rollback()
                msg = str(err).strip().splitlines()[0]
                ftype = "timeout" if "statement timeout" in msg else "sql_error"
                return VerificationReport(passed=False, failure_type=ftype, error=msg,
                                          tests=[TestOutcome("execute_candidate", False, ftype, msg)])
    except psycopg.OperationalError as err:
        return VerificationReport(passed=False, failure_type="sandbox_error",
                                  error=f"benchmark database unavailable: {err}")

    outcomes: list[TestOutcome] = []
    if len(ref_rows) > MAX_COMPARE_ROWS:
        outcomes.append(TestOutcome("row_limit", False, "reference_failed",
                                    f"original returns more than {MAX_COMPARE_ROWS} rows; case is too large"))
    if [c.lower() for c in cand_cols] != [c.lower() for c in ref_cols]:
        outcomes.append(TestOutcome("columns", False, "wrong_output",
                                    f"columns differ: original {ref_cols} vs candidate {cand_cols}", cand_ms))
    else:
        outcomes.append(TestOutcome("columns", True, None, f"{len(ref_cols)} columns match", cand_ms))

    if len(cand_rows) != len(ref_rows):
        outcomes.append(TestOutcome("row_count", False, "wrong_output",
                                    f"row count differs: original {len(ref_rows)} vs candidate {len(cand_rows)}"))
    else:
        outcomes.append(TestOutcome("row_count", True, None, f"{len(ref_rows)} rows"))
        ordered = _has_order_by(original)
        if ordered:
            same = cand_rows == ref_rows
            detail = "ordered rows match" if same else "row order or content differs"
        else:
            same = sorted(map(repr, cand_rows)) == sorted(map(repr, ref_rows))
            detail = "row multiset matches" if same else "row content differs"
        outcomes.append(TestOutcome("rows", same, None if same else "wrong_output", detail))

    passed = all(o.passed for o in outcomes)
    failure = None if passed else next(o.failure_type for o in outcomes if not o.passed)
    return VerificationReport(passed=passed, tests=outcomes, failure_type=failure)
