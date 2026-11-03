---
title: TPC-H laboratory experiments
created: 2026-11-03
project: GreenCode
tags: [ops, experiment, tpch, energy]
---

# TPC-H-derived laboratory experiments (supervisor meeting, 3 Nov 2026)

Supervisor asked for: a standard workload (TPC-H) on the laptop with power measured; the cost of measuring itself and of power management; a staged experiment (standard → complex → optimised queries) run lab-style with documented environment and "work packages".

## Work packages
| WP | Question | Command |
|---|---|---|
| WP1 baseline | 22 standard queries, hot cache, 3 passes | `run_tpch.py --wp 1 --passes 3` |
| WP2 meter overhead | none / LHM@0.1 / LHM@0.5 / CodeCarbon | `run_tpch.py --wp 2` (run first) |
| WP3 power management | one run per power plan | `run_tpch.py --wp 3 --plan-label X --expect-plan X` |
| WP4 complex queries | 8 anti-pattern queries (`benchmarks/tpch/complex`) | `run_tpch.py --wp 4 --repetitions 30` |
| WP5 optimised | WP4 through the pipeline, AI-only vs GreenCode | `run_tpch.py --wp 5` |

## Setup
`pip install --user duckdb` → `Check-TpchFeasibility.ps1` (phase 0) → `load_tpch.py --sf 1` → `run_tpch.py --validate` → `--check` → WPs. Results in `lab_runs` table; `--export lab.csv`.

## Code
`experiments/tpch.py` (resumable runner, conditions, export), `experiments/preflight.py`, `energy.py` ('none' meter, poll interval, temp/DRAM sensors), `runner.host_state()` (power plan, battery, processes), `db.models.LabRun`, `benchmarks/tpch/{q01..q22, complex/c01..c08, cases/}`, `docs/protocol.md`.

## Decisions / caveats
- Always "TPC-H-derived", never "TPC-H result" (unaudited).
- DuckDB's `tpch` extension generates the data — no dbgen compile on Windows.
- Statement timeout raised to 600 s for TPC-H queries.
- SQL008 (implicit cross join) only fires with no WHERE at all — noted as a rule limitation in c07.
- DRAM sensor may not exist on Core Ultra mobile: package-only if so.

See [[01 Project/Supervisor guidance — energy measurement]] · [[05 Writing/Benchmarking Approach]]
