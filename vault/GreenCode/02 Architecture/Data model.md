---
title: Data model
created: 2026-10-22
project: GreenCode
tags: [architecture, database]
---

# Data model — 8 tables (`db/models.py`, `database/schema/initial_schema.sql`)

```
projects 1─n analyses 1─n findings
                     1─n optimisations 1─n test_results
                                       1─n benchmark_runs 1─n measurements n─1 carbon_factors
```

| Table | One row per | Key columns |
|---|---|---|
| `projects` | experiment / working set | `name, description` |
| `analyses` | piece of source analysed | `project_id, language, source, case_spec (JSON), case_id, status, analyser_version, duration_ms` |
| `findings` | rule detection | `analysis_id, rule_id, title, severity, category, line, column, end_line, snippet, explanation, suggestion, confidence, evidence (JSON)` |
| `optimisations` | analysis × condition | `condition, original_source, candidate_source, model_name, provider, prompt, raw_response, generation_ms, prompt_tokens, completion_tokens, status, failure_reason, summary (JSON)` |
| `test_results` | differential test | `optimisation_id, test_name, passed, failure_type, details, duration_ms` |
| `benchmark_runs` | variant benchmarked | `optimisation_id, variant (original|candidate), repetitions, warmup_runs, mean/median/stdev/min/max/ci95 ms, samples_ms (JSON), environment (JSON), status, error` |
| `measurements` | metric of a run | `benchmark_run_id, metric, value, unit, method (measured|derived|estimated), source (psutil|lhm|codecarbon|estimate|postgresql), carbon_factor_id, details (JSON)` |
| `carbon_factors` | grid intensity | `region, year, grams_co2e_per_kwh, source, notes, is_default` |

- UUID string PKs, `created_at` everywhere; FKs cascade downward except `measurements.carbon_factor_id` (a factor in use cannot be deleted → admin returns 409).
- Metrics stored: `cpu_seconds, peak_rss_mb, energy_joules, energy_joules_net, energy_estimate_joules, co2e_grams`, plus SQL plan metrics.
- `session.py`: engine, `get_db()` dependency, `session_scope()`, `init_db()` + `DEFAULT_CARBON_FACTORS`. `benchdb.py`: psycopg connection to `bench` (read-only, timeout), `explain_json()`, `table_row_estimates()`, `schema_ddl_summary()`.

![[_assets/classdiagram.png]]
