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
| RAPL (`/sys/class/powercap`) | measured | CPU package (+ DRAM where exposed) | machine-wide; idle baseline measured for 1 s and subtracted; root/privileged read on most kernels; Intel/AMD Linux only |
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


## Energy measurement on Windows (Intel PCM)

The Linux powercap interface does not exist on Windows, so on the development laptop
(Intel Core Ultra 5 135U) GreenCode reads the same RAPL counters through Intel
Performance Counter Monitor. `pcm.exe` runs as a background sampler at 100 ms for
the duration of each benchmark window; package and DRAM energy per sample are summed
and scaled by the fraction of the window the samples cover, and the coverage ratio is
stored with the measurement. Because the sampler is machine-wide, a two-second idle
baseline is recorded once per session and subtracted, as for RAPL on Linux.

Limitations to report: sampling granularity is coarse relative to millisecond
benchmarks, so per-run energy should be read at the level of the whole repetition
loop, not individual samples; PCM requires its kernel driver and an administrator
shell; and it is Intel-only. The coefficient estimate is still recorded alongside
every PCM measurement so the two can be compared (H4).

Precedent: Bachras and Jacobsen, "Beyond Performance: Measuring the Environmental
Impact of Analytical Databases" (arXiv:2504.18980, 2025) use RAPL package and DRAM
energy multiplied by regional grid intensity in the same way.
