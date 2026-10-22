---
title: Research design
created: 2026-10-22
project: GreenCode
tags: [project, research]
---

# Research design

## Research question
> To what extent does static-analysis guidance improve the correctness, performance and energy efficiency of locally generated AI optimisations of Python and SQL?

## Hypotheses
| | Statement | Test | Code |
|---|---|---|---|
| **H1** | Guided (GreenCode) candidates are verified correct more often than AI-only candidates | one-sided Fisher's exact test on verified / not-verified counts | `results._hypotheses()` |
| **H2** | Guided candidates give larger execution-time improvements | paired Wilcoxon signed-rank on log(speed-up), cases benchmarked under both conditions | same |
| **H3** | Guided candidates give larger energy improvements | paired Wilcoxon on log(energy ratio) | same |
| **H4** | A reduction in execution time is not the same as a reduction in energy | per-case divergence \|Δtime% − Δenergy%\|, count > 10 pp, Spearman ρ | same |

## Design
Within-subjects: every case is evaluated under both conditions on the same machine in the same session, original re-measured for every pair (cancels drift).

| Variable | Role | Controlled in |
|---|---|---|
| Condition (ai_only / greencode) | independent | `experiments/suite.py` |
| Model, temperature (0), seed (42) | held constant | `GREENCODE_OLLAMA_MODEL`, `ai/provider.py` |
| Case order | randomised (seeded) | `run_suite(shuffle=True, seed=42)` |
| Condition order within a case | alternated | `run_suite` |
| Warm-up / repetitions | held constant | `GREENCODE_BENCHMARK_*` |
| Correctness | dependent (H1) | `verification/` |
| Execution time | dependent (H2) | `benchmark/runner.py` |
| Energy, CO₂e | dependent (H3, H4) | `benchmark/energy.py` |

## Per-pair statistics (`benchmark/stats.py`)
median, mean, SD, 95 % CI (t), Mann–Whitney U (two-sided, α = 0.05), Cliff's δ, speed-up = median_original / median_candidate. Geometric means for ratios.

## Per-protocol vs intention-to-treat (H2/H3)
Repeated runs of a case are aggregated by median. **Per-protocol** = only cases verified under both conditions (sets the verdict). **Intention-to-treat** = every attempted case, a rejected/failed candidate scores 1.0×. When guidance mainly prevents wrong rewrites, those cases leave the per-protocol comparison (they count towards H1) — on the 22 Oct data H2 was p = 0.17 per-protocol and p = 0.026 intention-to-treat; H3 p = 0.37 / 0.07.

## Failure taxonomy
Candidates that fail verification are not benchmarked; the failure type is a result in its own right: `parse_error`, `unsafe`, `compile_error`, `runtime_error`, `wrong_output`, `timeout`, `resource_limit`, `sql_error`.

## Threats to validity
- **Construct** – energy counters are machine-wide; PostgreSQL runs in another process. Mitigation: interleaved pairs, idle subtraction, idle machine.
- **Internal** – "unchanged" candidates are flagged so an echo is not counted as an improvement.
- **External** – one local model, ~30 synthetic cases; the rule set defines scope.
- **Reliability** – every run stores environment snapshot, settings, prompt, raw response and raw samples.

See also [[02 Architecture/Energy measurement]] · [[05 Writing/Summary]]
