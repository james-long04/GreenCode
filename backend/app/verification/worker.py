"""Sandbox worker: executes untrusted Python in a separate, restricted process.

This file is run as ``python -I worker.py`` by ``sandbox.py``. It must not import
anything from the application. It reads one JSON job from stdin and writes one
JSON result to stdout.

Job format::

    {"mode": "verify" | "benchmark",
     "source": "<python module source>",
     "entry_point": "solve",
     "tests": [{"name": "t1", "args": "([1,2,3], 2)", "kwargs": "{}"}],   # verify
     "setup": "<python code building workload variables>",             # benchmark
     "call": "solve(data, 5)",                                          # benchmark
     "warmup": 3, "repetitions": 15}

Defence in depth: the parent applies a timeout, an empty
environment and a throw-away working directory; this worker additionally
disables the obvious escape hatches (network, subprocesses, writing files).
The sandbox is defence in depth, not a security boundary: only run code you would run on your own machine.
"""

from __future__ import annotations

import builtins
import gc
import io
import json
import os
import sys
import time
import traceback
import types

# psutil must be imported *before* _harden() blocks the modules it depends on
# (subprocess, socket); it is the only way to read peak working set on Windows.
try:
    _extra = os.environ.get("GREENCODE_PSUTIL_DIR")
    if _extra and _extra not in sys.path:
        sys.path.append(_extra)
    import psutil as _psutil
except Exception:  # noqa: BLE001
    _psutil = None  # type: ignore[assignment]


def _rusage():  # type: ignore[no-untyped-def]
    """(user_s, system_s, peak_rss_kb) via psutil (peak working set on Windows)."""
    if _psutil is not None:
        try:
            p = _psutil.Process()
            ct = p.cpu_times()
            mi = p.memory_info()
            peak = getattr(mi, "peak_wset", mi.rss)
            return ct.user, ct.system, peak / 1024
        except Exception:  # noqa: BLE001
            pass
    t = time.process_time()
    return t, 0.0, 0


def _harden() -> None:
    blocked = [
        "socket", "ssl", "subprocess", "multiprocessing", "ctypes", "urllib", "urllib.request",
        "http", "http.client", "ftplib", "smtplib", "telnetlib", "xmlrpc", "asyncio", "signal",
        "shutil", "pty", "webbrowser", "importlib.metadata", "_posixsubprocess",
    ]
    for name in blocked:
        sys.modules[name] = None  # type: ignore[assignment]  # makes `import x` raise ImportError

    for attr in ("system", "popen", "fork", "forkpty", "execv", "execve", "execvp", "execvpe",
                 "execl", "execlp", "spawnl", "spawnv", "kill", "remove", "unlink", "rmdir",
                 "rename", "chmod", "chown", "setuid", "setgid", "putenv", "unsetenv"):
        if hasattr(os, attr):
            setattr(os, attr, _denied(f"os.{attr}"))

    real_open = builtins.open
    cwd = os.getcwd()

    def guarded_open(file, mode="r", *args, **kwargs):  # type: ignore[no-untyped-def]
        if any(m in mode for m in ("w", "a", "x", "+")):
            raise PermissionError("sandbox: file writes are not permitted")
        path = os.path.abspath(os.fspath(file)) if not isinstance(file, int) else None
        if path is not None and not path.startswith(cwd):
            raise PermissionError("sandbox: reading outside the working directory is not permitted")
        return real_open(file, mode, *args, **kwargs)

    builtins.open = guarded_open  # type: ignore[assignment]
    io.open = guarded_open  # type: ignore[assignment]


def _denied(name: str):  # type: ignore[no-untyped-def]
    def _fn(*_a, **_k):
        raise PermissionError(f"sandbox: {name} is not permitted")

    return _fn


def _canonical(value):  # type: ignore[no-untyped-def]
    """Convert a result to a stable, comparable, JSON-serialisable form."""
    try:
        json.dumps(value)
        return {"kind": "json", "value": value}
    except (TypeError, ValueError):
        pass
    if isinstance(value, (set, frozenset)):
        try:
            return {"kind": "set", "value": sorted(repr(v) for v in value)}
        except TypeError:
            return {"kind": "set", "value": sorted(map(repr, value))}
    if isinstance(value, tuple):
        return {"kind": "tuple", "value": [_canonical(v) for v in value]}
    if isinstance(value, dict):
        return {"kind": "dict", "value": {repr(k): _canonical(v) for k, v in value.items()}}
    if isinstance(value, (list,)):
        return {"kind": "list", "value": [_canonical(v) for v in value]}
    if isinstance(value, types.GeneratorType) or hasattr(value, "__next__"):
        return {"kind": "list", "value": [_canonical(v) for v in value]}
    if isinstance(value, float):
        return {"kind": "float", "value": repr(value)}
    return {"kind": "repr", "value": repr(value)}


def _load_module(source: str) -> dict:
    ns: dict = {"__name__": "candidate", "__builtins__": builtins}
    code = compile(source, "<candidate>", "exec")
    exec(code, ns)
    return ns


def run_verify(job: dict) -> dict:
    out: dict = {"ok": True, "tests": []}
    try:
        ns = _load_module(job["source"])
    except SyntaxError as err:
        return {"ok": False, "failure_type": "compile_error", "error": f"{err.__class__.__name__}: {err}"}
    except Exception as err:  # noqa: BLE001
        return {"ok": False, "failure_type": "runtime_error",
                "error": f"module import failed: {err.__class__.__name__}: {err}",
                "traceback": traceback.format_exc()[-2000:]}
    entry = job.get("entry_point") or "solve"
    fn = ns.get(entry)
    if not callable(fn):
        return {"ok": False, "failure_type": "missing_entry_point",
                "error": f"entry point '{entry}' is not defined"}
    for t in job.get("tests", []):
        record: dict = {"name": t.get("name", "test")}
        start = time.perf_counter()
        try:
            args = eval(t.get("args", "()"), {"__builtins__": builtins}, dict(ns))
            kwargs = eval(t.get("kwargs", "{}"), {"__builtins__": builtins}, dict(ns))
            if not isinstance(args, tuple):
                args = (args,)
            before = repr(args)
            result = fn(*args, **kwargs)
            record["result"] = _canonical(result)
            record["args_after"] = repr(args)
            record["mutated_inputs"] = before != record["args_after"]
            record["error"] = None
        except Exception as err:  # noqa: BLE001
            record["result"] = None
            record["error"] = f"{err.__class__.__name__}: {err}"
            record["error_type"] = err.__class__.__name__
        record["duration_ms"] = (time.perf_counter() - start) * 1000
        out["tests"].append(record)
    return out


def run_benchmark(job: dict) -> dict:
    try:
        ns = _load_module(job["source"])
        if job.get("setup"):
            exec(compile(job["setup"], "<setup>", "exec"), ns)
        call = compile(job["call"], "<call>", "eval")
    except Exception as err:  # noqa: BLE001
        return {"ok": False, "failure_type": "runtime_error", "error": f"{err.__class__.__name__}: {err}",
                "traceback": traceback.format_exc()[-2000:]}

    warmup = int(job.get("warmup", 3))
    reps = int(job.get("repetitions", 15))
    gc_enabled = bool(job.get("gc", True))

    try:
        for _ in range(warmup):
            eval(call, ns)
    except Exception as err:  # noqa: BLE001
        return {"ok": False, "failure_type": "runtime_error", "error": f"warm-up failed: {err.__class__.__name__}: {err}"}

    samples_ns: list[int] = []
    u0, s0, _ = _rusage()
    cpu0 = time.process_time_ns()
    try:
        for _ in range(reps):
            gc.collect()
            if not gc_enabled:
                gc.disable()
            t0 = time.perf_counter_ns()
            eval(call, ns)
            t1 = time.perf_counter_ns()
            if not gc_enabled:
                gc.enable()
            samples_ns.append(t1 - t0)
    except Exception as err:  # noqa: BLE001
        return {"ok": False, "failure_type": "runtime_error", "error": f"{err.__class__.__name__}: {err}"}
    cpu1 = time.process_time_ns()
    u1, s1, peak_kb = _rusage()
    return {
        "ok": True,
        "samples_ms": [s / 1e6 for s in samples_ns],
        "cpu_time_ms": (cpu1 - cpu0) / 1e6,
        "user_time_ms": (u1 - u0) * 1000,
        "system_time_ms": (s1 - s0) * 1000,
        "peak_rss_kb": peak_kb,
        "repetitions": reps,
        "warmup": warmup,
    }


def main() -> None:
    raw = sys.stdin.read()
    job = json.loads(raw)
    _harden()
    try:
        result = run_verify(job) if job.get("mode") == "verify" else run_benchmark(job)
    except MemoryError:
        result = {"ok": False, "failure_type": "resource_limit", "error": "MemoryError"}
    except RecursionError as err:
        result = {"ok": False, "failure_type": "runtime_error", "error": f"RecursionError: {err}"}
    sys.stdout.write(json.dumps(result))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
