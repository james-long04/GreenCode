---
title: Project overview
created: 2026-10-22
project: GreenCode
tags: [project]
---

# Project overview

GreenCode finds inefficient Python code and SQL queries with a **fixed set of static-analysis rules**, asks a **locally hosted coding model** (Ollama, `qwen2.5-coder:7b`) for an optimisation, **verifies** the candidate for correctness in a sandbox, and **benchmarks** original and optimised versions for runtime, CPU, memory, energy and CO₂e. Every stage writes its evidence to PostgreSQL and the dashboard shows it side by side.

It is an **experiment** as much as a tool. Each benchmark case runs under two conditions against the original as baseline:

| Condition | Process |
|---|---|
| **AI-only** (control) | original → local LLM → verify → benchmark → measure |
| **GreenCode** (treatment) | original → static analysis → *structured findings* → local LLM → verify → benchmark → measure |

The two prompts are identical except for the findings block, so the comparison isolates the effect of static-analysis guidance. See [[01 Project/Research design]].

## Why local, why Windows
- A local model keeps the experiment reproducible (temperature 0, fixed seed) and free of API cost; the provider abstraction lets the model be swapped as a variable ([[02 Architecture/Backend — ai]]).
- Everything runs natively on James's Windows laptop: PostgreSQL 18, Python 3.15 (`pip --user`), Node, Ollama, LibreHardwareMonitor. No Docker, no cloud, no Linux-only code paths ([[01 Project/Ground rules]]).

## What exists
- `backend/` FastAPI + SQLAlchemy + psycopg; 23 rules; sandboxed verification; benchmark + energy meters; experiment pipeline; dashboard and admin APIs.
- `frontend/` React 19 + TypeScript + Vite dashboard (Overview, Projects, Analyse, Experiments, Rules, Admin), dependency-free SVG charts, light/dark.
- `benchmarks/` 18 Python and 12 SQL cases; `database/` the controlled bench dataset (~850k rows).
- `docs/` methodology, architecture, UI audit, diagrams, Gantt, BibTeX, and the Word walkthrough [[06 Resources/Documents]].

Related: [[02 Architecture/System overview]] · [[04 Operations/Setup on Windows]]
