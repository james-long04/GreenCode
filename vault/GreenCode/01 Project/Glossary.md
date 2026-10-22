---
title: Glossary
created: 2026-10-22
project: GreenCode
tags: [project, glossary]
---

# Glossary

| Term | Meaning in this project |
|---|---|
| Condition | One of the two experimental arms, `ai_only` or `greencode` |
| Baseline | The original code's own benchmark run (`variant = original`) |
| Finding | A structured detection by one rule: where, why it is inefficient, what to change |
| Candidate | The model's proposed optimised code |
| Differential testing | Running original and candidate on the same inputs and comparing behaviour |
| RAPL | Running Average Power Limit — the CPU's own energy counters |
| LHM | LibreHardwareMonitor, which exposes RAPL package power over HTTP |
| Idle floor | Minimum machine power while nothing runs; subtracted to give net energy |
| measured / derived / estimated | Energy read from hardware; CO₂e computed from a measurement; energy from the coefficient model |
| Green Algorithms | Lannelongue et al. 2021 coefficient model used for the estimate |
| SEAI factor | Irish grid carbon intensity (gCO₂e/kWh) stored in `carbon_factors` |
| Cliff's δ | Non-parametric effect size (−1…+1) |
| Speed-up | median_original ÷ median_candidate; > 1 means faster |
| Case | A JSON benchmark file in `benchmarks/python` or `benchmarks/sql` |
| Spec / case_spec | Entry point, tests and benchmark workload for a Python case |
| Bench schema | The controlled PostgreSQL schema `bench` (customers, products, orders, order_items) |
