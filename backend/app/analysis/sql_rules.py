"""SQL static-analysis rules.

Queries are parsed with ``sqlglot`` (PostgreSQL dialect) and inspected for a
fixed set of patterns from the proposal: SELECT *, missing filters, non-sargable
predicates, leading-wildcard LIKE, NOT IN (subquery), DISTINCT misuse, correlated
subqueries, implicit cross joins and ORDER BY without LIMIT.

Optionally, when a database connection is supplied, the analyser also runs
``EXPLAIN (FORMAT JSON)`` and attaches planner evidence (sequential scans on
large tables, estimated cost) to the findings. This keeps the rules static and
deterministic while still giving the language model concrete evidence.
"""

from __future__ import annotations

from typing import Any, Iterable

import sqlglot
from sqlglot import exp

from app.analysis.base import Finding, RuleInfo

SQL_RULES: list[RuleInfo] = [
    RuleInfo("SQL001", "select_star", "sql", "unnecessary_work", "medium",
             "SELECT * transfers every column, prevents index-only scans and widens sorts/hashes."),
    RuleInfo("SQL002", "missing_where_clause", "sql", "unnecessary_work", "medium",
             "A query that reads an entire table with no filter forces a sequential scan."),
    RuleInfo("SQL003", "non_sargable_predicate", "sql", "indexing", "high",
             "Wrapping an indexed column in a function or expression in WHERE prevents index use."),
    RuleInfo("SQL004", "leading_wildcard_like", "sql", "indexing", "high",
             "LIKE '%...' cannot use a B-tree index and scans every row."),
    RuleInfo("SQL005", "not_in_subquery", "sql", "joins", "medium",
             "NOT IN (subquery) has NULL pitfalls and is often planned poorly; NOT EXISTS/anti-join is preferred."),
    RuleInfo("SQL006", "correlated_subquery_in_select", "sql", "joins", "high",
             "A correlated subquery in the SELECT list is re-executed for every outer row (N+1 inside SQL)."),
    RuleInfo("SQL007", "distinct_with_group_or_join", "sql", "unnecessary_work", "medium",
             "DISTINCT used to hide duplicates introduced by a join adds a sort/hash over the whole result."),
    RuleInfo("SQL008", "implicit_cross_join", "sql", "joins", "high",
             "Comma-separated tables without a join condition produce a Cartesian product."),
    RuleInfo("SQL009", "order_by_without_limit", "sql", "unnecessary_work", "low",
             "Sorting a full result set that the caller does not need ordered (or only partially)."),
    RuleInfo("SQL010", "in_list_subquery_could_be_join", "sql", "joins", "low",
             "IN (SELECT ...) is usually fine in PostgreSQL but a JOIN/EXISTS gives the planner more options."),
    RuleInfo("SQL011", "sequential_scan_on_large_table", "sql", "indexing", "high",
             "EXPLAIN shows a sequential scan on a large table where an index could be used (dynamic evidence)."),
    RuleInfo("SQL012", "count_star_subquery_for_existence", "sql", "unnecessary_work", "medium",
             "COUNT(*) > 0 counts every matching row when only existence is needed."),
]

RULE_INDEX = {r.rule_id: r for r in SQL_RULES}

LARGE_TABLE_ROWS = 10_000


def _emit(findings: list[Finding], rule_id: str, explanation: str, suggestion: str,
          node: exp.Expression | None = None, confidence: float = 0.8, **evidence: Any) -> None:
    info = RULE_INDEX[rule_id]
    snippet = node.sql(dialect="postgres") if node is not None else None
    if snippet and len(snippet) > 300:
        snippet = snippet[:300] + "..."
    findings.append(
        Finding(
            rule_id=rule_id,
            title=info.name.replace("_", " "),
            explanation=explanation,
            suggestion=suggestion,
            severity=info.severity,
            category=info.category,
            snippet=snippet,
            confidence=confidence,
            evidence=evidence,
        )
    )


def _is_column_wrapped(e: exp.Expression) -> bool:
    """True if a column appears inside a function/arithmetic on the left of a comparison."""
    if isinstance(e, exp.Column):
        return False
    if isinstance(e, (exp.Cast, exp.Func, exp.Binary)) and not isinstance(e, exp.Predicate):
        return any(isinstance(c, exp.Column) for c in e.find_all(exp.Column))
    return False


def analyse_sql(sql: str, explain: dict[str, Any] | None = None,
                table_stats: dict[str, int] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    try:
        tree = sqlglot.parse_one(sql, read="postgres")
    except sqlglot.errors.ParseError as err:  # pragma: no cover - surfaced to caller
        raise ValueError(f"SQL could not be parsed: {err}") from err

    selects = list(tree.find_all(exp.Select))
    root = tree if isinstance(tree, exp.Select) else (selects[0] if selects else None)
    for s in selects:
        _check_select(s, findings, is_root=(s is root))

    _check_where_predicates(tree, findings)
    _check_subqueries(tree, findings)

    if explain is not None:
        _check_explain(explain, findings, table_stats or {})

    findings.sort(key=lambda f: f.rule_id)
    return findings


def _check_select(s: exp.Select, findings: list[Finding], is_root: bool) -> None:
    # SQL001 SELECT *
    if any(isinstance(e, exp.Star) for e in s.expressions) or any(
        isinstance(e, exp.Column) and isinstance(e.this, exp.Star) for e in s.expressions
    ):
        _emit(findings, "SQL001",
              "SELECT * returns every column, including ones the consumer never uses. Wider rows mean more "
              "I/O, more memory for sorts/hashes and no chance of an index-only scan.",
              "List only the columns that are actually needed.", node=s, confidence=0.9)

    from_ = s.args.get("from")
    tables = list(s.find_all(exp.Table))
    joins = s.args.get("joins") or []

    # SQL002 missing WHERE (root query, reading a base table, no aggregation/limit)
    if is_root and from_ is not None and not s.args.get("where") and not s.args.get("group") \
            and not s.args.get("limit") and not any(isinstance(e, exp.AggFunc) for e in s.expressions) \
            and not joins:
        _emit(findings, "SQL002",
              "The statement has no WHERE clause, so every row of the table is read and returned.",
              "Add a selective filter, or add a LIMIT if only a sample is needed.", node=s, confidence=0.6)

    # SQL008 implicit cross join: FROM a, b with no join and no WHERE linking them
    if from_ is not None and isinstance(from_.this, exp.Table):
        extra = [j for j in joins if j.args.get("on") is None and j.args.get("using") is None and not j.args.get("kind")]
        if extra:
            where = s.args.get("where")
            if where is None:
                _emit(findings, "SQL008",
                      "Tables are combined with a comma (or JOIN without ON) and there is no WHERE condition "
                      "relating them, so the result is a Cartesian product.",
                      "Use an explicit `JOIN ... ON` with the key columns.", node=s, confidence=0.95)

    # SQL007 DISTINCT with JOIN
    if s.args.get("distinct") and joins:
        _emit(findings, "SQL007",
              "DISTINCT over a joined result de-duplicates after the join has multiplied rows; the join "
              "output must be fully hashed or sorted.",
              "Filter with EXISTS (semi-join) or aggregate before joining so duplicates are never produced.",
              node=s, confidence=0.7)

    # SQL009 ORDER BY without LIMIT at the root
    if is_root and s.args.get("order") is not None and s.args.get("limit") is None:
        _emit(findings, "SQL009",
              "The complete result set is sorted even though no LIMIT bounds how many rows are needed.",
              "Add a LIMIT if only the top rows are used, or drop ORDER BY if ordering is not required by "
              "the consumer (sorting in SQL costs O(n log n) and may spill to disk).",
              node=s.args["order"], confidence=0.5)

    # SQL006 correlated subquery in the select list
    for e in s.expressions:
        for sub in e.find_all(exp.Subquery):
            if _is_correlated(sub, s):
                _emit(findings, "SQL006",
                      "A subquery in the SELECT list references the outer query, so it is evaluated once "
                      "per outer row.",
                      "Rewrite as a JOIN to a pre-aggregated derived table (GROUP BY the key) or a LATERAL join.",
                      node=sub, confidence=0.85)
                break
        # SQL012 COUNT(*) > 0 pattern handled in predicates


def _outer_aliases(s: exp.Select) -> set[str]:
    names: set[str] = set()
    for t in s.find_all(exp.Table):
        if t.alias:
            names.add(t.alias)
        if t.name:
            names.add(t.name)
    return names


def _is_correlated(sub: exp.Subquery, outer: exp.Select) -> bool:
    inner = sub.this
    if not isinstance(inner, exp.Select):
        return False
    inner_names: set[str] = set()
    for t in inner.find_all(exp.Table):
        inner_names.add(t.alias or t.name)
    outer_names = {n for n in _outer_aliases(outer) if n not in inner_names}
    for col in inner.find_all(exp.Column):
        if col.table and col.table in outer_names:
            return True
    return False


def _check_where_predicates(tree: exp.Expression, findings: list[Finding]) -> None:
    for where in tree.find_all(exp.Where):
        for pred in where.find_all((exp.EQ, exp.NEQ, exp.GT, exp.GTE, exp.LT, exp.LTE)):
            left, right = pred.left, pred.right
            # SQL003: function(column) = literal
            if _is_column_wrapped(left) and not any(isinstance(c, exp.Column) for c in right.find_all(exp.Column)) \
                    and not isinstance(left, exp.Subquery):
                col = next(iter(left.find_all(exp.Column)), None)
                _emit(findings, "SQL003",
                      f"The column `{col.sql() if col else '?'}` is wrapped in `{left.sql()}` before comparison. "
                      "PostgreSQL cannot use a plain B-tree index on the column for this predicate and must "
                      "evaluate the expression for every row.",
                      "Rewrite the predicate so the bare column is compared to a constant/range (e.g. "
                      "`date_col >= '2024-01-01' AND date_col < '2025-01-01'` instead of `EXTRACT(YEAR FROM "
                      "date_col) = 2024`; `email = lower($1)` instead of `lower(email) = $1`), or create an "
                      "expression index.",
                      node=pred, confidence=0.85, expression=left.sql())
            # SQL012: (SELECT COUNT(*) ...) > 0
            if isinstance(pred, (exp.GT, exp.GTE, exp.NEQ)) and isinstance(left, exp.Subquery):
                inner = left.this
                if isinstance(inner, exp.Select) and any(isinstance(e, exp.Count) for e in inner.expressions):
                    _emit(findings, "SQL012",
                          "COUNT(*) in the subquery must visit every matching row to produce a number that is "
                          "only compared with zero.",
                          "Use `EXISTS (SELECT 1 ... )`, which stops at the first matching row.",
                          node=pred, confidence=0.9)
        for between in where.find_all(exp.Between):
            left = between.this
            if _is_column_wrapped(left):
                col = next(iter(left.find_all(exp.Column)), None)
                _emit(findings, "SQL003",
                      f"The column `{col.sql() if col else '?'}` is wrapped in `{left.sql()}` inside BETWEEN, so "
                      "an index on the column cannot be used for the range scan.",
                      "Compare the bare column with the range bounds (move the arithmetic to the constants).",
                      node=between, confidence=0.85, expression=left.sql())
        for like in where.find_all(exp.Like):
            pat = like.expression
            if isinstance(pat, exp.Literal) and pat.is_string and pat.this.startswith("%"):
                _emit(findings, "SQL004",
                      f"The pattern `{pat.this}` starts with a wildcard, so no B-tree index on the column can "
                      "be used and every row is compared.",
                      "Anchor the pattern (`'abc%'`) if the semantics allow, or use a trigram index "
                      "(`pg_trgm`) / full-text search for substring matching.",
                      node=like, confidence=0.9, pattern=pat.this)
        for like in where.find_all(exp.ILike):
            pat = like.expression
            if isinstance(pat, exp.Literal) and pat.is_string and pat.this.startswith("%"):
                _emit(findings, "SQL004",
                      f"ILIKE `{pat.this}` starts with a wildcard; no ordinary index can be used.",
                      "Use a trigram index (`pg_trgm`) or anchor the pattern.", node=like, confidence=0.9)


def _check_subqueries(tree: exp.Expression, findings: list[Finding]) -> None:
    for node in tree.find_all(exp.In):
        q = node.args.get("query")
        if q is None:
            continue
        parent = node.parent
        negated = isinstance(parent, exp.Not)
        if negated:
            _emit(findings, "SQL005",
                  "NOT IN (subquery) must materialise the full subquery result and returns no rows at all if "
                  "the subquery yields a NULL; PostgreSQL often cannot plan it as an efficient anti-join.",
                  "Rewrite as `NOT EXISTS (SELECT 1 FROM ... WHERE ...)` or a `LEFT JOIN ... WHERE x IS NULL`.",
                  node=parent, confidence=0.9)
        else:
            _emit(findings, "SQL010",
                  "IN (subquery) is planned as a semi-join; this is often fine, but when the subquery is "
                  "large or filtered on the outer table a JOIN/EXISTS can be cheaper.",
                  "Consider `EXISTS` or a `JOIN` and compare EXPLAIN costs.", node=node, confidence=0.4)


def _check_explain(explain: dict[str, Any], findings: list[Finding], table_stats: dict[str, int]) -> None:
    plan = explain.get("Plan") if isinstance(explain, dict) else None
    if plan is None:
        return

    def walk(p: dict[str, Any]) -> Iterable[dict[str, Any]]:
        yield p
        for child in p.get("Plans", []) or []:
            yield from walk(child)

    for node in walk(plan):
        if node.get("Node Type") == "Seq Scan":
            rel = node.get("Relation Name")
            rows = table_stats.get(rel, 0)
            if rel and (rows >= LARGE_TABLE_ROWS or node.get("Plan Rows", 0) >= LARGE_TABLE_ROWS):
                _emit(findings, "SQL011",
                      f"The planner chose a sequential scan of `{rel}` (~{rows or node.get('Plan Rows')} rows, "
                      f"estimated cost {node.get('Total Cost')}).",
                      "Make the predicate index-friendly or add an index on the filtered/joined columns, then "
                      "re-check EXPLAIN.",
                      confidence=0.7, relation=rel, plan_rows=node.get("Plan Rows"),
                      total_cost=node.get("Total Cost"), filter=node.get("Filter"))


def iter_rules() -> Iterable[RuleInfo]:
    return SQL_RULES
