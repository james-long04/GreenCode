---
title: Configuration
created: 2026-10-22
project: GreenCode
tags: [architecture, config]
---

# Configuration (`config.py`, `backend/.env`)

All settings are env vars prefixed `GREENCODE_` (pydantic `Settings`, `.env` file). The environment snapshot stored with every run includes them.

| Group | Setting (default) |
|---|---|
| Persistence | `DATABASE_URL` (postgresql+psycopg://greencode:greencode@localhost:5432/greencode), `BENCHMARK_DATABASE_URL`, `BENCHMARK_SCHEMA` (bench) |
| AI | `LLM_PROVIDER` (ollama\|mock), `OLLAMA_BASE_URL`, `OLLAMA_MODEL` (qwen2.5-coder:7b), `OLLAMA_TIMEOUT_SECONDS` (300), `LLM_TEMPERATURE` (0.0), `LLM_SEED` (42) |
| Sandbox | `SANDBOX_TIMEOUT_SECONDS` (20), `SANDBOX_MEMORY_LIMIT_MB` (512, recorded only), `SANDBOX_CPU_SECONDS`, `PYTHON_EXECUTABLE` |
| Benchmark | `BENCHMARK_WARMUP_RUNS` (3), `BENCHMARK_REPETITIONS` (15), `BENCHMARK_TIMEOUT_SECONDS` (120), `SQL_STATEMENT_TIMEOUT_MS` (30000) |
| Energy | `ENERGY_METHOD` (auto\|lhm\|codecarbon\|estimate), `LHM_URL` (http://localhost:8085/data.json), `CARBON_FACTOR_REGION` (IE), `ESTIMATE_CPU_TDP_WATTS` (65), `ESTIMATE_MEMORY_WATTS_PER_GB` (0.3725), `ESTIMATE_PUE` (1.0) |
| API | `CORS_ORIGINS`, `BENCHMARK_SUITE_DIR` (../benchmarks), `ADMIN_TOKEN` |

`RUNTIME_ADJUSTABLE` (admin may override at runtime): provider, model, base URL, temperature, seed, warm-up, repetitions, benchmark timeout, energy method, LHM URL, carbon region, TDP, PUE, sandbox timeout and memory limit.

Runtime overrides live in-process only (`set_runtime_overrides`, `clear_runtime_overrides`; `get_settings.cache_clear` shim).

Minimal `backend\.env` for the laptop:
```
GREENCODE_ADMIN_TOKEN=<secret>
```
Everything else can stay at defaults.
