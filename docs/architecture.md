# Architecture notes

## Data model (`backend/app/db/models.py`)

```
projects 1─n analyses 1─n findings
                     1─n optimisations 1─n test_results
                                       1─n benchmark_runs 1─n measurements n─1 carbon_factors
```

* `analyses.case_spec` (JSON) holds the entry point, test inputs and benchmark workload
  so ad-hoc submissions and suite cases share one table.
* `optimisations.condition` ∈ {`ai_only`, `greencode`}; `status` moves
  `pending → generated → verified | rejected → benchmarked | failed`.
* `optimisations.summary` (JSON) caches the comparison (`timing`, `energy`,
  `resources`, `sql_plan`, `verification`) for fast dashboard queries; the raw
  evidence remains in the child tables.
* `benchmark_runs.variant` ∈ {`original`, `candidate`} — the Baseline condition is
  the `original` run.
* `measurements.method` ∈ {`measured`, `estimated`} and `source` ∈ {`psutil`,
  `postgresql`, `rapl`, `codecarbon`, `estimate`}.

## Sandbox (`backend/app/verification/`)

`sandbox.run_job()` starts `python -I -B worker.py` with:

* RLIMIT_AS (memory), RLIMIT_CPU, RLIMIT_FSIZE, RLIMIT_NPROC, RLIMIT_CORE
* a wall-clock timeout, a throw-away cwd, a minimal environment
* `worker._harden()` blocks `socket`, `subprocess`, `ctypes`, … via `sys.modules`,
  neuters `os.system/fork/exec/remove…`, and replaces `open` with a read-only,
  cwd-restricted version.
* `python_verifier.static_safety_check()` additionally rejects candidates that
  import os/sys/subprocess/… or call `eval`/`exec`/`open` (unless the original did).

The worker speaks JSON over stdin/stdout and has two modes: `verify` (run tests,
canonicalise outputs) and `benchmark` (warm-up, timed repetitions, rusage).

## API (`backend/app/api/routes.py`)

| Method & path | Purpose |
|---|---|
| `GET /api/health` | DB, LLM and energy-method status |
| `GET /api/rules` | rule catalogue |
| `GET/POST/DELETE /api/projects` | projects |
| `POST /api/analyses` | run static analysis, store findings |
| `GET /api/analyses/{id}` | analysis + findings |
| `POST /api/optimisations` | create and (in background) run generate → verify → benchmark |
| `GET /api/optimisations/{id}` | full evidence for one optimisation |
| `POST /api/optimisations/{id}/rerun` | repeat the pipeline |
| `GET /api/suite/cases` · `POST /api/suite/run` · `GET /api/suite/jobs/{id}` | benchmark suite |
| `GET /api/results` · `GET /api/results/summary` | per-case rows and H1–H4 summary |
| `GET /api/carbon-factors` | environmental assumptions |

## Frontend (`frontend/`)

Vite + React + TypeScript, no UI framework: `src/api.ts` (typed client),
`src/pages/*` (Overview, Projects, Analyse, Optimisation, Experiments, Rules),
`src/components/charts.tsx` (dependency-free SVG charts). Hash routing keeps the
build static so it can be served by nginx in Docker.
