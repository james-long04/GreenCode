# GreenCode

**Static-Analysis-Guided AI Optimisation for Sustainable Python and SQL**
Final Year Project · BSc Computer Science · TU Dublin

> *Don't just optimise. Prove the impact.*

GreenCode finds inefficient Python code and SQL queries with a fixed set of
static-analysis rules, asks a locally hosted coding model (via Ollama) for an
optimisation, **verifies** the candidate for correctness in a sandbox, and then
**benchmarks** original and optimised versions for runtime, CPU, memory, energy
and CO₂e. Every stage writes its evidence to PostgreSQL and the dashboard shows
it side by side.

The research question: *to what extent does static-analysis guidance improve the
correctness, performance and energy efficiency of locally generated AI
optimisations?* Every benchmark case runs under two conditions against the
original as baseline:

| Condition | Process |
|-----------|---------|
| **AI-only** | original → local LLM → verify → benchmark → measure |
| **GreenCode** | original → static analysis → *structured findings* → local LLM → verify → benchmark → measure |

The two prompts are identical except for the findings block, so the comparison
isolates the effect of static-analysis guidance (hypotheses H1–H4).

The project runs natively on a Windows laptop. There is no Docker, no cloud and
no Linux-only code path.

---

## Architecture

```
React/TS dashboard  ──►  FastAPI  ──►  Static analysis (Python ast · sqlglot + EXPLAIN)
                                              │ structured findings
                                              ▼
                                       Ollama (local LLM)        provider abstraction, mock for tests
                                              │ candidate
                                              ▼
                                   Verification                    Python: sandboxed differential tests
                                              │                     SQL: result-set equivalence on controlled data
                                              ▼
                                   Benchmark engine                warm-up + N repetitions, interleaved pairs
                                              │
                                              ▼
                     Measurement: psutil · LibreHardwareMonitor (RAPL) / CodeCarbon / estimate · CO₂e
                                              │
                                              ▼
                                        PostgreSQL evidence store (8 tables)
```

```
backend/app/
  analysis/      base.py, python_rules.py (PY001–PY011), sql_rules.py (SQL001–SQL012), engine.py
  ai/            provider.py (Ollama + Mock), prompts.py (ai_only / greencode), parsing.py
  verification/  worker.py + sandbox.py (restricted subprocess), python_verifier.py, sql_verifier.py
  benchmark/     runner.py, sql_runner.py, energy.py (lhm | codecarbon | estimate), stats.py
  experiments/   pipeline.py (generate → verify → benchmark → measure), suite.py, results.py (H1–H4)
  db/            models.py, session.py, benchdb.py
  api/           routes.py (dashboard API), admin.py (admin API) · main.py · logbuffer.py
backend/tests/   pytest suite (unit + integration; integration skips without PostgreSQL)
backend/scripts/ init_db.py · seed_bench_dataset.py · run_suite.py · export_results.py
benchmarks/      python/*.json (18 cases) · sql/*.json (12 cases)
database/        schema/initial_schema.sql · seed/bench_dataset.sql (controlled SQL dataset)
frontend/        Vite + React + TypeScript dashboard (Overview, Projects, Analyse, Experiments, Rules, Admin)
docs/            methodology, architecture, UI audit, diagrams, Gantt plan, reference library (BibTeX)
```

---

## Quick start (Windows)

### Prerequisites

* Python 3.12+ · Node 20+ · PostgreSQL 16+ (installed natively)
* [Ollama](https://ollama.com) with a coding model: `ollama pull qwen2.5-coder:7b`
* [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases)
  for energy measurement (optional, see below)

### 1. Database

In `psql` (as the `postgres` superuser):

```sql
CREATE ROLE greencode WITH LOGIN PASSWORD 'greencode';
CREATE DATABASE greencode OWNER greencode;
```

### 2. Backend

```powershell
cd backend
copy .env.example .env          # then set GREENCODE_ADMIN_TOKEN in .env
pip install -r requirements.txt
python scripts\init_db.py       # creates tables and seeds carbon factors
python scripts\seed_bench_dataset.py   # loads the controlled SQL dataset (~850k rows)
python -m uvicorn app.main:app --reload --port 8000
```

### 3. Dashboard

```powershell
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

### 4. Energy measurement

Start LibreHardwareMonitor **as Administrator**, then **Options → Remote Web
Server → Run**. The backend polls `http://localhost:8085/data.json` and the
dashboard sidebar shows **Energy: lhm**. Without it the sidebar shows
**Energy: estimate** and energy figures are labelled as estimates.

### 5. Run the experiment

Use the **Experiments** page, or from the command line:

```powershell
cd backend
python scripts\run_suite.py --project "Experiment 1"
python scripts\export_results.py --out results.csv
```

### Tests

```powershell
cd backend
python -m pytest
```

---

## How a case flows through the system

1. **Detect** – `analysis.engine.analyse()` parses the input (Python `ast` /
   `sqlglot`) and runs the fixed rule set. For SQL it also runs `EXPLAIN` against
   the bench schema to attach planner evidence.
2. **Explain** – each `Finding` carries rule id, location, snippet, an
   explanation of *why* it is inefficient, a concrete suggestion and a confidence.
3. **Optimise** – `ai.prompts.build_prompt()` produces the AI-only or GreenCode
   prompt; `OllamaProvider` calls the local model with `temperature=0`, fixed seed.
4. **Test** – Python candidates run in `verification/worker.py`: a separate
   `python -I` process with a timeout, an empty environment, no network, no
   subprocesses and a throw-away working directory. Outputs are compared with the
   original's on every test input (differential testing), including exception
   types and in-place mutation of arguments. SQL candidates must be a single
   SELECT and return identical columns and rows on the controlled dataset.
5. **Benchmark** – `benchmark/runner.py` performs warm-up runs then *N* timed
   repetitions (default 15; use 30+ for energy) and records every sample.
6. **Measure** – CPU time and peak working set (psutil); energy from the
   processor's RAPL counter via LibreHardwareMonitor (idle floor subtracted),
   else CodeCarbon, else a documented coefficient model. Every row in
   `measurements` records `method = measured | derived | estimated` and `source`.
7. **Verify** – `stats.compare()` reports median speed-up, Mann–Whitney *p*,
   Cliff's δ and CI overlap; `results.summarise()` aggregates per condition and
   evaluates H1 (Fisher exact), H2/H3 (paired Wilcoxon on log ratios) and H4
   (time-vs-energy divergence).

## Rule catalogue

| Python | | SQL | |
|---|---|---|---|
| PY001 | membership test on list/tuple in a loop | SQL001 | `SELECT *` |
| PY002 | string `+=` in a loop | SQL002 | no WHERE on a base table |
| PY003 | append-only loop → comprehension | SQL003 | non-sargable predicate (function/cast/arithmetic on column) |
| PY004 | `range(len(x))` indexing | SQL004 | leading-wildcard `LIKE` |
| PY005 | loop-invariant expensive call (`sorted`, `re.compile`, …) | SQL005 | `NOT IN (subquery)` |
| PY006 | nested-loop key join (O(n·m)) | SQL006 | correlated subquery in SELECT list |
| PY007 | full sort for min/max/top-k | SQL007 | `DISTINCT` over a join |
| PY008 | unnecessary allocations (`sum([...])`, `in d.keys()`, `len(list(...))`) | SQL008 | implicit cross join |
| PY009 | query inside a loop (N+1) | SQL009 | `ORDER BY` without `LIMIT` |
| PY010 | manual sum/count loop | SQL010 | `IN (subquery)` |
| PY011 | `DataFrame.iterrows()` | SQL011 | sequential scan on large table (EXPLAIN evidence) |
| | | SQL012 | `COUNT(*) > 0` for existence |

## Adding a benchmark case

Drop a JSON file in `benchmarks/python/` or `benchmarks/sql/`:

```json
{
  "id": "py_019_my_case", "title": "…", "language": "python", "category": "…",
  "expected_rules": ["PY001"],
  "source": "def solve(xs):\n    ...",
  "entry_point": "solve",
  "tests": [{"name": "basic", "args": "([1, 2, 3],)", "expected": [1]}],
  "benchmark": {"setup": "xs = list(range(100000))", "call": "solve(xs)"}
}
```

`tests/test_suite_cases.py` automatically checks that the original passes its
own tests and that the expected rules fire.

## Configuration

All settings are environment variables prefixed `GREENCODE_` (see
`backend/.env.example`): database URLs, provider/model, sandbox limits,
repetitions/warm-up, energy method, the LibreHardwareMonitor URL and the CPU
TDP used by the estimate model. The environment snapshot (CPU, cores, Python
version, settings) is stored with every benchmark run.

### Admin page

The dashboard's **Admin** page (`#/admin`, API under `/api/admin/*`) shows
evidence-store counts and host status, lets you override benchmark/model/energy
settings at runtime (process-only; every run records the values it used), lists
and pulls Ollama models, manages carbon factors (values that evidence already
references are locked), offers maintenance actions (mark stuck runs failed,
delete orphan analyses or failed/rejected runs; benchmarked evidence is never
deleted), shows the server log and exports all results as CSV. The admin API
always requires an `X-Admin-Token` header: set `GREENCODE_ADMIN_TOKEN` in
`backend/.env`, or copy the random token the backend prints at startup.

## Measurement caveats (for the dissertation)

* LibreHardwareMonitor and CodeCarbon measure the **whole machine** and refresh
  about once a second; results are only comparable within an interleaved
  original/candidate pair on an otherwise idle laptop, over windows of several
  seconds. Close other applications during experiment runs.
* The coefficient estimate (Green Algorithms) is an *estimate*; it is always
  stored alongside any measurement so the two can be compared (H4 discussion).
* CO₂e uses the SEAI grid factor stored in `carbon_factors`; cite the release used.
* The Python sandbox is defence-in-depth, not a security boundary. Only run
  code you are prepared to execute on your own machine.

## Documentation

* `docs/methodology.md` – experimental protocol, energy measurement, statistics, threats to validity
* `docs/architecture.md` – component responsibilities and data model
* `docs/ui-audit.md` – usability review of the dashboard (Nielsen heuristics)
* `docs/diagrams/` – flowchart, use case and class diagrams; `docs/plan/` – Gantt chart
* `docs/references/` – BibTeX reference library for Zotero
* API reference: `http://localhost:8000/docs`

## Acknowledgement of AI assistance

The codebase was generated with Claude (Anthropic) under the author's direction
from the project proposal, and is declared as such in line with TU Dublin's
policy on AI use. Commit messages carry a co-author line for every AI-generated change.
