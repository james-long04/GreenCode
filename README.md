# GreenCode

**Static-Analysis-Guided AI Optimisation for Sustainable Python and SQL**
Final Year Project · BSc Computer Science · TU Dublin

> *Don't just optimise. Prove the impact.*

GreenCode identifies inefficient Python code and SQL queries with deterministic
static-analysis rules, asks a locally hosted coding model (via Ollama) for an
optimisation, **verifies** the candidate for correctness in a sandbox, and then
**benchmarks** original and optimised versions for runtime, CPU, memory, energy
and estimated CO₂e. Every stage writes its evidence to PostgreSQL.

The research question: *to what extent does static-analysis guidance improve the
correctness, performance and energy efficiency of locally generated AI
optimisations?* The system therefore runs every benchmark case under three
conditions and compares them:

| Condition | Process |
|-----------|---------|
| **Baseline** | the original code/query is benchmarked |
| **AI-only** | original → local LLM → verify → benchmark |
| **GreenCode** | original → static analysis → *structured findings* → local LLM → verify → benchmark |

The two AI prompts are identical except for the findings block, so the
comparison isolates the effect of static-analysis guidance (hypotheses H1–H4 in
the proposal).

---

## Architecture

```
React/TS dashboard  ──►  FastAPI  ──►  Static analysis (Python AST · sqlglot + EXPLAIN)
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
                            Measurement: psutil · RAPL / CodeCarbon / coefficient estimate · CO₂e
                                              │
                                              ▼
                                        PostgreSQL evidence store (8 tables)
```

```
backend/app/
  analysis/      base.py, python_rules.py (PY001–PY011), sql_rules.py (SQL001–SQL012), engine.py
  ai/            provider.py (Ollama + Mock), prompts.py (ai_only / greencode), parsing.py
  verification/  worker.py + sandbox.py (restricted subprocess), python_verifier.py, sql_verifier.py
  benchmark/     runner.py, sql_runner.py, energy.py (rapl | codecarbon | estimate), stats.py
  experiments/   pipeline.py (Detect→…→Verify), suite.py (3-condition runner), results.py (H1–H4)
  db/            models.py (projects, analyses, findings, optimisations, test_results,
                 benchmark_runs, measurements, carbon_factors), session.py, benchdb.py
  api/routes.py  REST API · main.py
backend/tests/   100+ pytest tests (unit + integration)
backend/scripts/ run_suite.py · export_results.py · init_db.py · seed_bench_dataset.py
benchmarks/      python/*.json (18 cases) · sql/*.json (12 cases)
database/        schema/initial_schema.sql · seed/bench_dataset.sql (controlled SQL dataset)
frontend/        Vite + React + TypeScript dashboard
docs/            methodology notes
```

---

## Quick start

### Prerequisites

* Python 3.11+ · Node 20+ · PostgreSQL 16 (or Docker)
* [Ollama](https://ollama.com) with a coding model, e.g. `ollama pull qwen2.5-coder:7b`

### 1. Infrastructure

```bash
docker compose up -d postgres ollama
docker compose exec ollama ollama pull qwen2.5-coder:7b
```

(or point `GREENCODE_DATABASE_URL` at any PostgreSQL instance and run Ollama natively)

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # edit if needed
python scripts/init_db.py                               # creates the 8 tables + carbon factors
python scripts/seed_bench_dataset.py                    # loads the controlled SQL dataset (schema `bench`)
uvicorn app.main:app --reload --port 8000               # API + Swagger UI at http://localhost:8000/docs
```

### 3. Dashboard

```bash
cd frontend
npm install
npm run dev                                             # http://localhost:5173 (proxies /api to :8000)
```

### 4. Run the experiment

```bash
cd backend
python scripts/run_suite.py --project "Experiment 1"            # all 30 cases × 2 conditions
python scripts/run_suite.py --project smoke --cases py_001_membership_list_in_loop --conditions greencode
python scripts/export_results.py --project "Experiment 1" --out ../results   # CSV/JSON for the dissertation
```

Or use the **Experiments** page in the dashboard, which runs the same code and
shows per-case results, condition summaries and the H1–H4 tests live.

### Windows

Everything runs natively on Windows 10/11 (PowerShell):

```powershell
docker compose up -d postgres ollama
docker compose exec ollama ollama pull qwen2.5-coder:7b
cd backend
py -3.12 -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts\init_db.py
python scripts\seed_bench_dataset.py
uvicorn app.main:app --reload --port 8000
```

and in a second terminal `cd frontend; npm install; npm run dev`.

Differences on Windows: the sandbox cannot apply POSIX memory/CPU rlimits, so it
relies on the timeout plus the worker-side hardening (no network, no subprocesses,
no file writes). RAPL is unavailable; energy comes from CodeCarbon (which uses
Intel Power Gadget / TDP on Windows) or the coefficient estimate. If
`pip install codecarbon` fails, remove it from `requirements.txt` — the estimate
is used automatically.

### Offline / no GPU

`GREENCODE_LLM_PROVIDER=mock` runs the entire pipeline with a deterministic stand-in
model (it returns the original code), which is how the test-suite and CI work.

```bash
cd backend && pytest            # integration tests skip automatically if PostgreSQL is unreachable
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
   `python -I` process with RLIMIT memory/CPU/file limits, a timeout, no network,
   no subprocesses and read-only filesystem access to a temp directory. Outputs
   are compared with the original's on every test input (differential testing),
   including exception types and in-place mutation of arguments. SQL candidates
   must be a single SELECT and return identical columns and rows on the
   controlled dataset.
5. **Benchmark** – `benchmark/runner.py` performs warm-up runs then *N* timed
   repetitions (default 15) and records every sample, not just the mean.
6. **Measure** – CPU time and peak RSS (psutil/rusage); energy via RAPL when the
   counters are readable (with an idle-power baseline subtracted), else
   CodeCarbon, else a documented coefficient model. Every row in `measurements`
   records `method = measured | estimated` and `source`.
7. **Verify** – `stats.compare()` reports median speed-up, Mann–Whitney *p*,
   Cliff's δ and CI overlap; `results.summarise()` aggregates per condition and
   evaluates H1 (Fisher exact), H2/H3 (paired Wilcoxon on log ratios) and H4
   (time-vs-energy divergence, Spearman ρ).

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
repetitions/warm-up, energy method and the CPU TDP used by the estimate model.
The environment snapshot (CPU, cores, Python version, settings) is stored with
every benchmark run for reproducibility.

## Measurement caveats (for the dissertation)

* RAPL and CodeCarbon measure the **whole machine**; results are only comparable
  within an interleaved original/candidate pair on an otherwise idle system.
  Run experiments on the host, not inside Docker, so hardware counters are visible.
* The coefficient estimate (Green Algorithms) is an *estimate*; it is always
  stored alongside any measurement so the two can be compared (H4 discussion).
* CO₂e uses the SEAI grid factor stored in `carbon_factors`; update it and cite
  the release used.
* The Python sandbox is defence-in-depth, not a security boundary (and has no
  rlimits on Windows); run the backend in the provided container for untrusted inputs.

## Documentation

* `docs/methodology.md` – experimental protocol, statistics and threats to validity
* `docs/architecture.md` – component responsibilities and data model
* `docs/design-skills.md` – the design skills in `.claude/skills/` used for the dashboard UI
* API reference: `http://localhost:8000/docs`

## Acknowledgement of AI assistance

The codebase was generated with Claude (Anthropic) under the author's direction
from the project proposal, and is declared as such in line with TU Dublin's
policy on AI use. Commit messages carry a co-author line for every AI-generated change.

Dashboard design work is additionally guided by third-party Claude skills (Impeccable,
Taste skill, Emil Kowalski's design skills and a Nielsen heuristics audit) stored in
`.claude/skills/` with their licences; see `docs/design-skills.md`. `CLAUDE.md` tells Claude Code
how to use them in this repo.
