# Laboratory protocol — TPC-H-derived energy experiments

This is the "white coat" procedure for the measured experiments on the TPC-H-derived dataset.
It exists so that every run is made under the same, recorded conditions, and so that the
dissertation can state exactly what was controlled and what was not. `scripts/run_tpch.py`
enforces the required items in a pre-flight check and refuses to start if they fail.

Wording: the data generator and queries are those of the TPC-H specification, but the runs are
not audited, so all results are described as **TPC-H-derived**, never as TPC-H results.

## 1. Apparatus

| Item | Value (recorded automatically in every run's `environment`) |
|---|---|
| Machine | Laptop, Intel Core Ultra 5 135U (12 cores), 32 GB RAM, Windows 11 |
| Database | PostgreSQL 16+ native, schema `tpch` loaded by `scripts/load_tpch.py --sf 1` |
| Energy reader | LibreHardwareMonitor (RAPL CPU package power) over `http://localhost:8085/data.json` |
| Fallbacks | CodeCarbon (TDP-based on Windows), Green Algorithms coefficient estimate; always labelled |
| Timing | `perf_counter_ns` around `execute()`+`fetchall()` per repetition; `EXPLAIN (ANALYZE, BUFFERS)` once per query |
| Resources | psutil on the PostgreSQL backend process (CPU time, peak RSS) |
| Temperature | LHM CPU package temperature at window start/end/max |

## 2. Fixed conditions (every run)

1. **Mains power**, battery above 50 %, lid open, screen on at fixed brightness.
2. **Power plan / power mode** set before the run and not changed during it; recorded by name.
3. **Ollama stopped** (it holds ~5 GB and wakes periodically). Required.
4. **Quiet machine**: browser, VS Code, Teams, Spotify, OneDrive sync, Windows Search indexing and Windows Update
   servicing closed or paused. The pre-flight lists offenders; it warns rather than refuses, and the list is recorded.
5. **Warm machine**: at least 10 minutes on after boot, PostgreSQL started, one throw-away pass over the query set
   so the buffer cache is hot. All measurements are hot-cache unless the condition says otherwise.
6. **Idle floor** measured once per (condition, pass) as the minimum LHM reading over 6 s; subtracted from every window.
7. **Nothing touched** during the run. The laptop is left alone; no remote sessions.
8. **Order randomised** per pass with a fixed seed, so thermal drift is not confounded with query identity; a 5 s
   cool-down between queries.
9. **Repetitions**: 15 per query for timing work packages, 30 for energy-critical ones; warm-up 3. Short queries are
   repeated enough that the energy window exceeds ~10 s (several LHM refreshes); `coverage` and `distinct_readings`
   are stored and runs with fewer than 3 distinct readings are flagged in analysis.

## 3. Work packages

| WP | Question | Conditions | Command |
|---|---|---|---|
| **WP1 Baseline** | What do the 22 standard queries cost on this machine? | Balanced plan, LHM @ 0.1 s, hot cache, 3 passes | `run_tpch.py --wp 1 --passes 3` |
| **WP2 Measurement overhead** | Does measuring change the measurement? | meter = none / LHM @ 0.1 s / LHM @ 0.5 s / CodeCarbon | `run_tpch.py --wp 2` |
| **WP3 Power management** | How much does the OS power plan move time and energy? | one invocation per plan: Best power efficiency, Balanced, Best performance | `run_tpch.py --wp 3 --plan-label <name> --expect-plan <name>` |
| **WP4 Complex queries** | Do heavier, anti-pattern queries behave differently? | 8 hand-written queries (`benchmarks/tpch/complex`), 30 reps | `run_tpch.py --wp 4 --repetitions 30` |
| **WP5 Optimised** | Does GreenCode's rewrite reduce time and energy on them? | WP4 queries through the pipeline, AI-only vs GreenCode | `run_tpch.py --wp 5` |

WP2 runs **first** so that WP1 can use the lowest-overhead meter setting it finds. WP3 is run three times,
changing the plan between invocations (`powercfg /setactive <GUID>` or the Windows power-mode slider), each with
its own label. Battery-mode runs are optional and are recorded as `on_ac_power=false`.

## 4. Analysis (per WP)

* Per query: median, 95 % CI, net energy (J), energy per 1 000 rows, mean watts, time–energy ratio.
* WP2: overhead of each meter as % of the no-meter median, paired Wilcoxon across the 22 queries.
* WP3: ratio of each plan to Balanced for time and for energy, per query and as geometric means; divergence between the two (H4).
* WP4/5: the existing per-pair statistics (speed-up, Mann–Whitney, Cliff's δ) and the condition-level tests.
* A TPC-Energy-style figure: total net joules for one pass over the query set, reported alongside total time, in the
  spirit of the TPC-Energy specification's energy-per-unit-of-work metric.
* Export: `run_tpch.py --export lab.csv` (one row per query × condition × pass with every field above).

## 5. Threats and controls

| Threat | Control |
|---|---|
| Thermal throttling over long runs | randomised order, cool-downs, temperature recorded; passes with `temp_c_max` above a threshold excluded |
| RAPL ~1 s refresh vs sub-second queries | windows over the whole repetition loop; `coverage`/`distinct_readings` stored; short queries get more reps |
| Background activity | pre-flight list, process count and idle floor per run; exclude runs whose idle floor drifts > 10 % from the session median |
| No DRAM sensor on this CPU | package-only energy; DRAM reported only if the sensor exists (`dram_joules_approx`) |
| Measurement overhead | quantified in WP2 and subtracted/discussed rather than ignored |
| Power plan changed mid-run | plan name recorded at every run; `--expect-plan` refuses to start on the wrong plan |
| Default PostgreSQL config | `shared_buffers`, `work_mem`, `max_parallel_workers_per_gather`, `jit` recorded; set once and left |
| Scale factor too large for the laptop | Phase 0 feasibility script; fall back to SF 0.3 |

## 6. Checklist before a night run

```
[ ] plugged in, battery > 50 %, lid open
[ ] power plan set:  powercfg /getactivescheme  -> matches --plan-label
[ ] Ollama quit, browser/VS Code/Teams closed, OneDrive paused, Defender quick scan not scheduled
[ ] LibreHardwareMonitor running as Administrator, Remote Web Server on (sidebar says Energy: lhm)
[ ] python scripts\run_tpch.py --check   -> all required OK
[ ] python scripts\run_tpch.py --wp N ...  (resumable; rerun the same command after an interruption)
[ ] morning: python scripts\run_tpch.py --export lab.csv
```
