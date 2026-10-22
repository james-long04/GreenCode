---
title: Backend — verification and sandbox
created: 2026-10-22
project: GreenCode
tags: [architecture, backend, sandbox]
---

# `verification/` — proving the candidate is correct

A faster wrong answer is worthless; nothing is benchmarked until verified.

## `python_verifier.py` — differential testing
1. `static_safety_check()` rejects imports of `os, sys, subprocess, socket, ctypes…` and calls to `exec, eval, compile, __import__, open, globals, breakpoint, input` unless the original already used them.
2. `verify_python()` runs original and candidate on every test in the spec and compares: canonicalised return value, exception type, and the post-call state of mutable arguments. Explicit `expected` values also check the original (catches bad case files).
3. Result: `VerificationReport` of `TestOutcome`s → `test_results` rows.

## `sandbox.py`
`run_job(job)` launches `python -I -B worker.py` with a timeout, an essentially empty environment (Windows keeps `SYSTEMROOT` etc.), a throw-away cwd, and `GREENCODE_PSUTIL_DIR` so the worker can import psutil. JSON in on stdin, JSON out on stdout → `SandboxResult(ok, timed_out, output, stderr)`. **No POSIX rlimits** (Windows); `sandbox_memory_limit_mb` is recorded, not enforced.

## `worker.py`
Must not import the application (runs isolated). Imports psutil **before** `_harden()`, which strips `subprocess, socket, ctypes…` from `sys.modules`/builtins, makes `open` read-only, shadows `__import__`. Modes:
- `verify` — exec module, call entry point per test, return canonical outputs / exception types / argument state.
- `benchmark` — exec `setup`, warm-up, time each repetition with `perf_counter_ns`, return samples + CPU time + peak working set (`_rusage()` via psutil `peak_wset`).

> Defence in depth, not a security boundary. Only run code you'd run on your own machine.

## `sql_verifier.py`
`sql_safety_check()` → single `SELECT` only (no DDL/DML, no multiple statements). `verify_sql()` runs both on the `bench` schema (read-only, statement timeout) and accepts only if column names/order are identical and rows are the same multiset (`_normalise()` for Decimal/datetime/None); order must match if the original has `ORDER BY`. `MAX_COMPARE_ROWS = 200_000`.
