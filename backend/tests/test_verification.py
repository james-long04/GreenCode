from app.verification.python_verifier import static_safety_check, verify_python
from app.verification.sandbox import run_job

ORIGINAL = "def solve(items, targets):\n    allowed = [x for x in items]\n    return [t in allowed for t in targets]\n"
SPEC = {"entry_point": "solve", "tests": [
    {"name": "small", "args": "([1, 2, 3], [2, 5])", "expected": [True, False]},
    {"name": "empty", "args": "([], [1])"},
]}


def test_equivalent_candidate_passes():
    cand = "def solve(items, targets):\n    allowed = set(items)\n    return [t in allowed for t in targets]\n"
    report = verify_python(ORIGINAL, cand, SPEC)
    assert report.passed and all(t.passed for t in report.tests)


def test_wrong_candidate_is_rejected_with_wrong_output():
    cand = "def solve(items, targets):\n    return [True for _ in targets]\n"
    report = verify_python(ORIGINAL, cand, SPEC)
    assert not report.passed and report.failure_type == "wrong_output"


def test_syntax_error_candidate():
    report = verify_python(ORIGINAL, "def solve(:\n", SPEC)
    assert report.failure_type == "compile_error"


def test_unsafe_candidate_is_blocked_statically():
    assert static_safety_check("import os\ndef solve(a, b): return os.listdir('.')", ORIGINAL)
    assert static_safety_check("def solve(a, b): return eval('1')", ORIGINAL)
    assert static_safety_check("import re\ndef solve(a, b): return 1", ORIGINAL) is None
    report = verify_python(ORIGINAL, "import socket\ndef solve(a, b):\n    return []\n", SPEC)
    assert report.failure_type == "unsafe"


def test_candidate_that_raises_is_runtime_error():
    cand = "def solve(items, targets):\n    raise RuntimeError('boom')\n"
    report = verify_python(ORIGINAL, cand, SPEC)
    assert report.failure_type == "runtime_error"


def test_candidate_must_mutate_inputs_like_original():
    orig = "def solve(xs):\n    xs.append(1)\n    return len(xs)\n"
    cand = "def solve(xs):\n    return len(xs) + 1\n"
    report = verify_python(orig, cand, {"entry_point": "solve", "tests": [{"name": "t", "args": "([0],)"}]})
    assert not report.passed and "mutates" in (report.tests[0].details or "")


def test_sandbox_blocks_network_subprocess_and_file_writes():
    r = run_job({"mode": "verify", "source": "import subprocess\ndef solve(): return 1", "entry_point": "solve", "tests": [{"name": "a", "args": "()"}]})
    assert not r.ok
    r = run_job({"mode": "verify", "source": "def solve():\n    open('x.txt', 'w').write('hi')\n    return 1",
                 "entry_point": "solve", "tests": [{"name": "a", "args": "()"}]})
    assert r.ok and r.data["tests"][0]["error_type"] == "PermissionError"


def test_sandbox_timeout_and_memory_limit():
    r = run_job({"mode": "verify", "source": "def solve():\n    while True: pass", "entry_point": "solve", "tests": [{"name": "a", "args": "()"}]}, timeout=2)
    assert r.failure_type == "timeout"
    r = run_job({"mode": "verify", "source": "def solve():\n    return len(bytearray(10**10))", "entry_point": "solve", "tests": [{"name": "a", "args": "()"}]})
    assert (not r.ok) or r.data["tests"][0]["error_type"] == "MemoryError"


def test_benchmark_mode_returns_samples():
    r = run_job({"mode": "benchmark", "source": "def solve(n):\n    return sum(range(n))", "setup": "n = 10000",
                 "call": "solve(n)", "warmup": 1, "repetitions": 4})
    assert r.ok and len(r.data["samples_ms"]) == 4 and r.data["cpu_time_ms"] >= 0
