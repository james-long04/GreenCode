---
title: What SQL can be run
created: 2026-10-22
project: GreenCode
tags: [rules, sql, faq]
---

# What SQL can be run through the full pipeline

A SQL input works end-to-end only if it is:
1. **One `SELECT` statement** — no scripts, `CREATE`, `INSERT`, `EXPLAIN`, `SET`, multiple statements (`sql_safety_check()` rejects them because model output executes against a live database).
2. **Against the bench tables** (`customers, products, orders, order_items`) — verification and benchmarking execute the query, so the tables must exist with data.
3. Finishes in < 30 s and returns < 200 000 rows.

Any other single `SELECT` (e.g. coursework queries on `campusevents.*`) can be pasted and **analysed** (rules work on text alone) but optimisation fails at verification ("relation does not exist").

Multi-statement files (e.g. a CA script with EXPLAIN/CREATE INDEX blocks) can't be used whole — paste one query out of them.

## Options if you want your own schema
- **Analysis-only mode** for foreign tables (small UI change; findings only, nothing measured).
- **Load your schema + data** into the same PostgreSQL and set `GREENCODE_BENCHMARK_SCHEMA=<schema>` → full pipeline, including EXPLAIN evidence.

Python is different: a `.py` carries its own inputs (tests + workload in the spec), so any function works.
