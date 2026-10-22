---
title: System overview
created: 2026-10-22
project: GreenCode
tags: [architecture]
---

# System overview

![[_assets/flowchart.png]]

```
React/TS dashboard ──► FastAPI ──► Static analysis (Python ast · sqlglot + EXPLAIN)
                                        │ structured findings
                                        ▼
                                 Ollama (local LLM)        provider abstraction, mock for tests
                                        │ candidate
                                        ▼
                             Verification                  Python: sandboxed differential tests
                                        │                   SQL: result-set equivalence on controlled data
                                        ▼
                             Benchmark engine              warm-up + N repetitions, interleaved pairs
                                        │
                                        ▼
               Measurement: psutil · LibreHardwareMonitor (RAPL) / CodeCarbon / estimate · CO₂e
                                        │
                                        ▼
                                  PostgreSQL evidence store (8 tables)
```

## Package layout
```
backend/app/
  analysis/      base.py, python_rules.py (PY001–PY011), sql_rules.py (SQL001–SQL012), engine.py
  ai/            provider.py (Ollama + Mock), prompts.py (ai_only / greencode), parsing.py
  verification/  worker.py + sandbox.py, python_verifier.py, sql_verifier.py
  benchmark/     runner.py, sql_runner.py, energy.py (lhm | codecarbon | estimate), stats.py
  experiments/   pipeline.py, suite.py, results.py (H1–H4)
  db/            models.py, session.py, benchdb.py
  api/           routes.py, admin.py · main.py · config.py · schemas.py · logbuffer.py
backend/scripts/ init_db.py · seed_bench_dataset.py · run_suite.py · export_results.py
backend/tests/   110 tests
benchmarks/      python/*.json (18) · sql/*.json (12)
database/        schema/initial_schema.sql · seed/bench_dataset.sql
frontend/        Vite + React + TypeScript dashboard
docs/            methodology, architecture, ui-audit, diagrams, plan, references
```

## Request flow (click "Run both conditions" on Analyse)
1. `POST /api/analyses` → `pipeline.create_analysis()` → `analysis.engine.analyse()` → rows in `analyses` + `findings`.
2. `POST /api/optimisations` ×2 → `optimisations` row (`pending`), `process_optimisation()` scheduled as a background task, `202`.
3. `generate_candidate()` → prompt → provider → `extract_code()` → `generated`.
4. `verify_candidate()` → safety check → sandbox differential tests / SQL equivalence → `verified` | `rejected`.
5. `benchmark_pair()` → original and candidate back-to-back → `benchmark_runs` + `measurements` → `summary` → `benchmarked`.
6. Dashboard polls `GET /api/optimisations/{id}` every ~3 s and re-renders.

Next: [[02 Architecture/Pipeline]]
