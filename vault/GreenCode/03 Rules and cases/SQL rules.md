---
title: SQL rules
created: 2026-10-22
project: GreenCode
tags: [rules, sql]
---

# SQL rules (SQL001–SQL012)

Implemented in `backend/app/analysis/sql_rules.py` with `sqlglot`; SQL011 needs an `EXPLAIN` plan and row estimates (attached automatically for bench-schema queries).

| Rule | Pattern | Typical suggestion |
|---|---|---|
| SQL001 | `SELECT *` | Name the needed columns |
| SQL002 | No `WHERE` on a base table | Add a predicate |
| SQL003 | Non-sargable predicate (function/cast/arithmetic on column) | Rewrite as a range on the bare column |
| SQL004 | Leading-wildcard `LIKE` | Trigram index or suffix search |
| SQL005 | `NOT IN (subquery)` | `NOT EXISTS` / anti-join |
| SQL006 | Correlated subquery in SELECT list | Join + GROUP BY |
| SQL007 | `DISTINCT` over a join | `EXISTS` / semi-join |
| SQL008 | Implicit cross join | Explicit join condition |
| SQL009 | `ORDER BY` without `LIMIT` | Add `LIMIT` for feeds |
| SQL010 | `IN (subquery)` | `EXISTS` / join |
| SQL011 | Sequential scan on large table (EXPLAIN evidence) | Sargable predicate / index |
| SQL012 | `COUNT(*) > 0` for existence | `EXISTS` |
