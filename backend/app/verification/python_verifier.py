"""Differential correctness testing for Python candidates.

The original and the candidate are executed on the same inputs inside the
sandbox and their canonicalised outputs are compared. Exceptions must match by
type, and in-place mutation of the inputs must match too (a candidate that stops
mutating a list the original mutated has changed observable behaviour).

Explicit expected values from the case specification are also honoured, so the
original is itself checked against the case author's expectations.
"""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass, field
from typing import Any

from app.config import Settings, get_settings
from app.verification.sandbox import run_job

FORBIDDEN_IMPORTS = {
    "os", "sys", "subprocess", "socket", "shutil", "ctypes", "multiprocessing", "threading",
    "urllib", "http", "requests", "httpx", "pathlib", "importlib", "signal", "pty",
}
FORBIDDEN_CALLS = {"exec", "eval", "compile", "__import__", "open", "globals", "breakpoint", "input"}


@dataclass
class TestOutcome:
    name: str
    passed: bool
    failure_type: str | None = None
    details: str | None = None
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationReport:
    passed: bool
    tests: list[TestOutcome] = field(default_factory=list)
    failure_type: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "failure_type": self.failure_type, "error": self.error,
                "tests": [t.to_dict() for t in self.tests]}


def static_safety_check(candidate: str, original: str) -> str | None:
    """Return a description of the first unsafe construct found, or None."""
    try:
        orig_tree = ast.parse(original)
    except SyntaxError:
        orig_tree = ast.Module(body=[], type_ignores=[])
    allowed = {
        (n.names[0].name.split(".")[0]) for n in ast.walk(orig_tree) if isinstance(n, ast.Import)
    } | {(n.module or "").split(".")[0] for n in ast.walk(orig_tree) if isinstance(n, ast.ImportFrom)}
    try:
        tree = ast.parse(candidate)
    except SyntaxError as err:
        return f"compile_error: {err}"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in FORBIDDEN_IMPORTS and root not in allowed:
                    return f"unsafe import '{alias.name}'"
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in FORBIDDEN_IMPORTS and root not in allowed:
                return f"unsafe import 'from {node.module}'"
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
            return f"unsafe call '{node.func.id}()'"
        elif isinstance(node, ast.Attribute) and node.attr in {"__subclasses__", "__globals__", "__builtins__"}:
            return f"unsafe attribute access '{node.attr}'"
    return None


def _tests_from_spec(spec: dict[str, Any]) -> list[dict[str, Any]]:
    tests = []
    for i, t in enumerate(spec.get("tests", [])):
        tests.append({"name": t.get("name", f"test_{i + 1}"), "args": t.get("args", "()"),
                      "kwargs": t.get("kwargs", "{}"), "expected": t.get("expected")})
    return tests


def verify_python(original: str, candidate: str, spec: dict[str, Any],
                  settings: Settings | None = None) -> VerificationReport:
    settings = settings or get_settings()
    unsafe = static_safety_check(candidate, original)
    if unsafe:
        ftype = "compile_error" if unsafe.startswith("compile_error") else "unsafe"
        return VerificationReport(passed=False, failure_type=ftype, error=unsafe,
                                  tests=[TestOutcome("static_safety", False, ftype, unsafe)])

    tests = _tests_from_spec(spec)
    if not tests:
        return VerificationReport(passed=False, failure_type="no_tests", error="case has no tests")
    entry = spec.get("entry_point", "solve")
    job_tests = [{"name": t["name"], "args": t["args"], "kwargs": t["kwargs"]} for t in tests]

    ref = run_job({"mode": "verify", "source": original, "entry_point": entry, "tests": job_tests}, settings)
    if not ref.ok:
        return VerificationReport(passed=False, failure_type="reference_failed",
                                  error=f"original failed in sandbox: {ref.error}")
    cand = run_job({"mode": "verify", "source": candidate, "entry_point": entry, "tests": job_tests}, settings)
    if not cand.ok:
        return VerificationReport(passed=False, failure_type=cand.failure_type, error=cand.error,
                                  tests=[TestOutcome("load_candidate", False, cand.failure_type, cand.error)])

    outcomes: list[TestOutcome] = []
    ref_by_name = {t["name"]: t for t in ref.data["tests"]}
    for spec_t, c in zip(tests, cand.data["tests"]):
        r = ref_by_name.get(c["name"], {})
        name = c["name"]
        if r.get("error") is not None:
            # The original raises for this input; the candidate must raise the same type.
            if c.get("error") is None:
                outcomes.append(TestOutcome(name, False, "wrong_output",
                                            f"original raised {r['error']} but candidate returned a value",
                                            c.get("duration_ms")))
            elif c.get("error_type") != r.get("error_type"):
                outcomes.append(TestOutcome(name, False, "wrong_output",
                                            f"original raised {r['error']}; candidate raised {c['error']}",
                                            c.get("duration_ms")))
            else:
                outcomes.append(TestOutcome(name, True, None, "both raised the same exception type",
                                            c.get("duration_ms")))
            continue
        if c.get("error") is not None:
            outcomes.append(TestOutcome(name, False, "runtime_error", c["error"], c.get("duration_ms")))
            continue
        if c["result"] != r["result"]:
            outcomes.append(TestOutcome(name, False, "wrong_output",
                                        f"expected {_short(r['result'])} got {_short(c['result'])}",
                                        c.get("duration_ms")))
            continue
        if c.get("args_after") != r.get("args_after"):
            outcomes.append(TestOutcome(name, False, "wrong_output",
                                        "candidate mutates its inputs differently from the original",
                                        c.get("duration_ms")))
            continue
        expected = spec_t.get("expected")
        if expected is not None and _canonical_matches(r["result"], expected) is False:
            outcomes.append(TestOutcome(name, False, "reference_mismatch",
                                        f"original does not match the case's expected value {expected!r}",
                                        c.get("duration_ms")))
            continue
        outcomes.append(TestOutcome(name, True, None, None, c.get("duration_ms")))

    passed = all(o.passed for o in outcomes)
    failure = None if passed else next(o.failure_type for o in outcomes if not o.passed)
    return VerificationReport(passed=passed, tests=outcomes, failure_type=failure)


def _canonical_matches(canon: dict[str, Any], expected: Any) -> bool | None:
    if canon.get("kind") == "json":
        return canon.get("value") == expected
    return None  # cannot compare non-JSON forms against a JSON expectation


def _short(value: Any, limit: int = 160) -> str:
    s = repr(value)
    return s if len(s) <= limit else s[:limit] + "..."
