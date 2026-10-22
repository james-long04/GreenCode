---
title: Backend — benchmark
created: 2026-10-22
project: GreenCode
tags: [architecture, backend, benchmark]
---

# `benchmark/` — timing and statistics

## `runner.py`
`benchmark_python(source, spec, settings, energy_ctx)` benchmarks **one** variant: builds a sandbox benchmark job, wraps the call in `energy_ctx.measure()`, returns `BenchmarkOutcome` (samples ms, `stats.Summary`, CPU time, peak RSS, `EnergySample`s, `environment_snapshot()` = CPU, cores, Python, OS, settings). Interleaving original/candidate is done by `pipeline.benchmark_pair()`.

`EnergyContext` — created once per run; when method is `lhm` it measures the idle floor first (`measure_idle_power_watts(6.0)`); `measure()` attaches `idle_joules`, `idle_watts`, `mean_watts`.

## `sql_runner.py`
Client-observed time over repetitions after warm-up (buffer cache steady), plus planner cost and actual time / buffers from `EXPLAIN (ANALYZE, BUFFERS)`; energy around the loop (machine-wide, meaningful relative to idle and the paired original).

## `stats.py`
`summarise()` mean/median/SD/min/max/CI95 (t via SciPy if present); `compare(original, candidate)` → median & mean speed-up, Mann–Whitney p, Cliff's δ, CI overlap (stored in `optimisations.summary`); `cliffs_delta()`, `wilcoxon_paired()` reused by `results.py`.

Defaults: warm-up 3, repetitions 15 (use **30+** for energy), benchmark timeout 120 s, SQL statement timeout 30 s.

See [[02 Architecture/Energy measurement]]
