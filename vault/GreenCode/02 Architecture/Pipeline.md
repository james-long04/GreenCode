---
title: Pipeline
created: 2026-10-22
project: GreenCode
tags: [architecture, pipeline]
---

# Pipeline — Detect → Explain → Optimise → Test → Benchmark → Measure → Verify

| Stage | What happens | Where |
|---|---|---|
| Detect | Parse (Python `ast` / `sqlglot`), run the fixed rule set; SQL also gets `EXPLAIN` against the bench schema | [[02 Architecture/Backend — analysis]] |
| Explain | Each `Finding`: rule id, location, snippet, why, suggestion, confidence | `analysis/base.py` |
| Optimise | `build_prompt()` → Ollama, temperature 0, fixed seed | [[02 Architecture/Backend — ai]] |
| Test | Sandboxed differential tests / SQL result equivalence | [[02 Architecture/Backend — verification and sandbox]] |
| Benchmark | Warm-up + N timed repetitions, original and candidate back-to-back | [[02 Architecture/Backend — benchmark]] |
| Measure | psutil CPU/peak RSS; energy LHM → CodeCarbon → estimate; CO₂e via grid factor | [[02 Architecture/Energy measurement]] |
| Verify | `stats.compare()`; `results.summarise()` and H1–H4 | [[02 Architecture/Backend — experiments]] |

## `pipeline.py` functions
| Function | Writes | Status afterwards |
|---|---|---|
| `create_analysis()` | `analyses`, `findings` (SQL: EXPLAIN plan, row estimates, schema summary into `case_spec`) | `analysed` |
| `create_optimisation()` | `optimisations` | `pending` |
| `generate_candidate()` | prompt, raw response, candidate, timings, tokens | `generated` / `failed` |
| `verify_candidate()` | `test_results` | `verified` / `rejected` / `failed` |
| `benchmark_pair()` | two `benchmark_runs`, `measurements`, `summary` | `benchmarked` / `failed` |
| `process_optimisation()` | runs whichever stages remain, catches everything → `failed` + `pipeline_error`, records `pipeline_seconds` | — |

`process_optimisation()` is resumable (looks at the current status), which is what `POST /optimisations/{id}/rerun` relies on. Each stage commits before the next starts → a crash leaves a complete trail.

State machine: `pending → generated → verified → benchmarked`, terminal `rejected`, `failed`.
