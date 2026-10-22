---
title: Adding a case
created: 2026-10-22
project: GreenCode
tags: [rules, cases, howto]
---

# Adding a benchmark case

Drop a JSON file in `benchmarks/python/` or `benchmarks/sql/`:

```json
{
  "id": "py_019_my_case", "title": "…", "language": "python", "category": "…",
  "expected_rules": ["PY001"],
  "source": "def solve(xs):\n    ...",
  "entry_point": "solve",
  "tests": [{"name": "basic", "args": "([1, 2, 3],)", "expected": [1]}],
  "benchmark": {"setup": "xs = list(range(100000))", "call": "solve(xs)"}
}
```

For SQL: `source` is the single `SELECT` against the [[03 Rules and cases/Bench dataset]]; no entry point or tests needed.

Then `python -m pytest tests\test_suite_cases.py` — it verifies the original passes its own tests and the expected rules fire.
