---
title: Decisions log
created: 2026-10-22
project: GreenCode
tags: [project, decisions]
---

# Decisions log

A running record of choices made while building, so the dissertation can justify them.

| Date | Decision | Why |
|---|---|---|
| 2026-09 | Two conditions (AI-only vs GreenCode) with identical prompts bar the findings block | Isolates the effect of guidance; keeps the experiment a fair test |
| 2026-09 | Local model via Ollama (`qwen2.5-coder:7b`), temperature 0, seed 42 | Reproducible, no API cost; provider abstraction keeps the model a variable |
| 2026-09 | Fixed rule set (11 Python, 12 SQL) rather than a general linter | A stable, documented definition of "inefficiency" is needed for the experiment |
| 2026-09 | Differential testing as the correctness oracle | The original is the ground truth; exception type and argument mutation also compared |
| 2026-09 | SQL candidates must be a single `SELECT`; verified by result-set equivalence on a controlled dataset | Safety (no DDL executes) and comparability |
| 2026-09 | Controlled bench dataset (~850k rows, generated deterministically) | Every SQL case measured against the same data and statistics |
| 2026-10 | Dashboard with no UI framework; dependency-free SVG charts; OKLCH tokens | Auditable, accessible, light/dark; fewer dependencies |
| 2026-10 | Admin panel behind a mandatory `X-Admin-Token`; random token if unset | Repo is public; no open mode |
| 2026-10 | Repo trimmed to Windows-native code (removed Docker, RAPL powercap, PCM, POSIX rlimits, CI) | "Just the code necessary for everything to work on my laptop" |
| 2026-10 | Energy via LibreHardwareMonitor (RAPL) instead of Intel PCM | PCM needs a self-compiled, test-signed driver on Windows |
| 2026-10 | LHM readings treated as mean power over the preceding refresh interval; poll continues ≤3 s after window close | Net energy was 0.000 because of refresh lag |
| 2026-10 | Idle floor = **minimum** reading over 6 s, not the mean | Mean idle was pulled up by background activity |
| 2026-10 | CO₂e from measured energy tagged `derived` (not `measured`, not `estimated`) | Only the grid factor is modelled |
| 2026-10 | Coefficient estimate (Green Algorithms) always stored alongside | Lets measured vs modelled be compared (H4 discussion) |
| 2026-10 | psutil imported in the worker before hardening, via `GREENCODE_PSUTIL_DIR` | Only way to read peak working set on Windows with `python -I` |
| 2026-10 | Analyse page accepts `.py`, `.sql`, `.ipynb` (notebooks flattened to code cells, magics dropped) | Convenience; backend unchanged |
| 2026-10 | Files going into the repo are pushed via git, never copied straight to disk | Copying caused `git pull` "untracked files would be overwritten" errors |

Related: [[04 Operations/Troubleshooting]]
