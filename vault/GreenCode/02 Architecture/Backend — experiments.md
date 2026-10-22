---
title: Backend — experiments
created: 2026-10-22
project: GreenCode
tags: [architecture, backend, experiments]
---

# `experiments/` — orchestration and hypotheses

## `pipeline.py`
See [[02 Architecture/Pipeline]]. `_store_run()` creates every measurement via `m(metric, value, unit, method, source)`; `_energy_comparison()` computes the energy ratio and time/energy divergence for H4; `_normalise_ws()` flags candidates identical to the original.

## `suite.py`
A **case** = JSON file under `benchmarks/<lang>/`: `id, title, language, category, expected_rules, source, entry_point, tests[], benchmark{setup, call}` (SQL: the query). `load_cases()`, `get_case()`, `run_suite(db, project_id, case_ids, conditions, shuffle, seed)` — one analysis per case, one optimisation per condition, shared `EnergyContext` (idle floor measured once). API wraps it as a background job with progress.

## `results.py`
`collect()` → one row per optimisation; `summarise()` → per-condition counts, verification rate, geometric-mean speed-up and energy ratio, failure breakdown; `_hypotheses()` → H1 Fisher, H2/H3 paired Wilcoxon on log ratios, H4 divergence + Spearman ρ, with plain-language notes. Served by `GET /api/results/summary`, shown on Overview and Experiments.

Export: `scripts/export_results.py --out results.csv` or admin **Export** button.
