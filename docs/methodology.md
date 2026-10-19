# Experimental methodology

## Design

A within-subjects design: every benchmark case is evaluated under all three
conditions (Baseline, AI-only, GreenCode) on the same machine in the same
session. The *only* difference between the AI-only and GreenCode prompts is the
block of structured findings produced by static analysis
(`backend/app/ai/prompts.py`), so any difference in outcome is attributable to
that guidance.

| Variable | Role | Where it is controlled |
|---|---|---|
| Condition (ai_only / greencode) | independent | `experiments/suite.py` |
| Model, temperature (0), seed | held constant | `GREENCODE_OLLAMA_MODEL`, `provider.py` |
| Case order | randomised (seeded) | `run_suite(shuffle=True, seed=42)` |
| Condition order within a case | alternated | `run_suite` |
| Warm-up / repetitions | held constant | `GREENCODE_BENCHMARK_*` |
| Correctness | dependent (H1) | `verification/` |
| Execution time | dependent (H2) | `benchmark/runner.py` |
| Energy, CO₂e | dependent (H3, H4) | `benchmark/energy.py` |

## Procedure per case

1. Static analysis → findings stored (`findings` table) regardless of condition.
2. For each condition: prompt → candidate (`optimisations`), verification
   (`test_results`), then **original and candidate are benchmarked back-to-back**
   (`benchmark_runs` + `measurements`). The baseline is therefore re-measured for
   every pair, which cancels slow drift (thermal state, background load).
3. Candidates that fail verification are *not* benchmarked; their failure type is
   recorded (`compile_error`, `runtime_error`, `wrong_output`, `timeout`,
   `resource_limit`, `unsafe`, `sql_error`) and analysed as a result in its own right.

## Statistics

* Per pair: median, mean, SD, 95 % CI (t-distribution), Mann–Whitney U (two-sided,
  α = 0.05), Cliff's δ, speed-up = median_original / median_candidate.
* H1: proportion verified, one-sided Fisher exact test (GreenCode > AI-only).
* H2 / H3: paired on cases benchmarked under both conditions; one-sided Wilcoxon
  signed-rank on log(speed-up) / log(energy ratio). Geometric means are reported
  because ratios are multiplicative.
* H4: |Δtime% − Δenergy%| per case; count of cases diverging by > 10 pp; Spearman ρ
  between the two.
* Results are exported with `scripts/export_results.py` (long-format CSV of every
  sample and measurement) for further analysis in R / pandas.

## Energy measurement

| Method | Type | What it covers | Caveats |
|---|---|---|---|
| LibreHardwareMonitor (RAPL via signed driver) | measured | CPU package | machine-wide; 6 s idle floor subtracted; ~1 s refresh; Intel, Windows |
| CodeCarbon | measured/estimated | CPU (RAPL or TDP), RAM, GPU | 1 s sampling interval, coarse for sub-second workloads |
| Coefficient estimate | estimated | CPU time × (TDP / cores) + wall × RAM × 0.3725 W/GB, × PUE | Green Algorithms model; TDP must be set for the test machine |

Each `measurements` row stores `method` and `source`; the estimate is recorded
alongside every measurement so measured and estimated figures can be compared.

## Threats to validity

* **Construct** – energy counters are machine-wide; PostgreSQL work happens in a
  separate process. Mitigation: paired interleaved runs, idle subtraction, idle machine.
* **Internal** – the mock/echo path and "unchanged" candidates are flagged so a model
  returning the input unchanged is not counted as an improvement.
* **External** – one local model and ~30 synthetic cases; the rule set defines the
  scope. The provider abstraction allows the model to be varied as a factor.
* **Reliability** – every run stores the environment snapshot, settings, prompt,
  raw model response and all raw samples, so a result can be re-examined or reproduced.


## Energy measurement (LibreHardwareMonitor)

GreenCode runs on a Windows laptop (Intel Core Ultra 5 135U). It reads the processor's RAPL
energy counter through LibreHardwareMonitor, which ships a signed kernel driver and exposes
"CPU Package" power as JSON from its built-in web server. LHM refreshes about once a second and
a reading observed at time *u* is the mean power over the preceding refresh interval, so the
meter keeps polling until the first refresh after the window closes and integrates each reading
over the part of its interval that overlaps the window. The number of distinct readings and the
coverage fraction are stored with each measurement. A six-second idle baseline is taken once per
session and its lowest steady reading is subtracted as the idle floor. CO₂e derived from a
measured energy value is tagged "derived" rather than "estimated", since only the grid factor
is modelled. The coefficient estimate is always recorded alongside so the two can be compared (H4).

Limitations to report: one-second granularity is coarse relative to millisecond benchmarks, so
energy is only meaningful over the whole repetition loop (use 30+ repetitions); the reading is
machine-wide, so other applications must be closed during runs; and the approach is specific to
Intel processors with LHM support.

Alternatives considered: Intel PCM gives 100 ms samples but requires compiling and test-signing
its MSR driver on Windows; CodeCarbon reads RAPL natively only on Linux and otherwise estimates
from CPU load. Precedent for RAPL package energy × regional grid intensity: Bachras and Jacobsen,
"Beyond Performance: Measuring the Environmental Impact of Analytical Databases" (arXiv:2504.18980, 2025).
