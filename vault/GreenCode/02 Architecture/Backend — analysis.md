---
title: Backend — analysis
created: 2026-10-22
project: GreenCode
tags: [architecture, backend]
---

# `analysis/` — the static analysers

Deliberately a **fixed** deterministic rule set, not a general linter: the experiment needs a stable definition of "inefficiency".

## `base.py`
- `Finding` dataclass: `rule_id, title, severity, category, line, column, end_line, snippet, explanation, suggestion, confidence, evidence`. `to_prompt_text(i)` renders the numbered text that goes into the GreenCode prompt — the exact wording the model sees is defined here.
- `RuleInfo` (for the Rules page), `AnalysisResult`, `ANALYSER_VERSION` (stored on every analysis).

## `python_rules.py` — PY001–PY011
Walks the module `ast`; each rule is a small class yielding findings with `evidence` (loop depth, container type …). Full table: [[03 Rules and cases/Python rules]].

## `sql_rules.py` — SQL001–SQL012
Parses with `sqlglot`. SQL001–010, 012 are syntactic; **SQL011** uses the planner (`EXPLAIN (FORMAT JSON)` + `pg_class.reltuples`) to flag a sequential scan on a large table. Notes:
- `s.args.get("from") or s.args.get("from_")` — key renamed in sqlglot 30.
- `_unconditioned()` handles comma joins, `CROSS JOIN` and `JOIN` without `ON` (all represented differently). Full table: [[03 Rules and cases/SQL rules]].

## `engine.py`
`analyse(language, source, explain=..., row_estimates=...)` dispatches, times, returns `AnalysisResult`; `all_rules()` feeds `GET /api/rules`. The only entry point the rest of the app uses.
