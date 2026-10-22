---
title: Testing
created: 2026-10-22
project: GreenCode
tags: [ops, testing]
---

# Testing (`backend/tests`, 110 tests)

`conftest.py` forces `GREENCODE_LLM_PROVIDER=mock`, repetitions 5, warm-up 1; `requires_db` skips integration tests when PostgreSQL is unreachable.

| File | Covers |
|---|---|
| `test_python_rules.py`, `test_sql_rules.py` | every rule fires / does not fire |
| `test_ai.py` | prompt construction (conditions identical bar findings), parsing |
| `test_verification.py` | sandbox, differential tests, safety checks (memory-limit assertion skipped on Windows) |
| `test_benchmark.py` | runner, stats, energy meters incl. LHM JSON parser |
| `test_admin.py` | admin auth (`effective_admin_token()`), settings overrides, carbon-factor locks |
| `test_api.py` | dashboard routes |
| `test_pipeline_integration.py` | end-to-end with mock provider (needs DB) |
| `test_suite_cases.py` | every case's original passes its tests; expected rules fire |

Run: `cd backend; python -m pytest`.
