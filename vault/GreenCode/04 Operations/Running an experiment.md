---
title: Running an experiment
created: 2026-10-22
project: GreenCode
tags: [ops, experiment]
---

# Running an experiment (protocol)

1. Reboot or at least close everything except PostgreSQL, Ollama, LHM, the backend and the dashboard. Plug in; same power plan each time.
2. Confirm sidebar **Energy: lhm** and `GET /api/health` shows `lhm: true`.
3. Admin → Settings: repetitions **30+**, warm-up 3 (or set `GREENCODE_BENCHMARK_REPETITIONS=30` in `.env`).
4. Create a project named for the run (model, machine, date), e.g. "Experiment 1, qwen2.5-coder:7b, 2026-11-05".
5. Experiments page → select all cases → both conditions → Run. Or `python scripts\run_suite.py --project "…"`.
6. Leave the laptop alone until it finishes (the idle floor is only valid if the machine stays idle).
7. Overview / Experiments show the summary and H1–H4; Admin → Export → `results.csv` for R/pandas.
8. Record in the dissertation: model, settings, environment snapshot, carbon-factor release, which energy method, number of repetitions, and the caveats in [[02 Architecture/Energy measurement]].

Check per-measurement `coverage` and `distinct_readings` — short windows with 1–2 readings are not trustworthy.
