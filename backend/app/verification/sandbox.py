"""Run the sandbox worker in a restricted subprocess."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings

WORKER_PATH = Path(__file__).with_name("worker.py")

@dataclass
class SandboxResult:
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    failure_type: str | None = None
    error: str | None = None
    stderr: str = ""
    returncode: int | None = None


def run_job(job: dict[str, Any], settings: Settings | None = None,
            timeout: float | None = None) -> SandboxResult:
    """Execute one worker job and return its parsed result."""
    settings = settings or get_settings()
    timeout = timeout or settings.sandbox_timeout_seconds
    python = settings.python_executable or sys.executable
    env = {"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8", "PYTHONIOENCODING": "utf-8"}
    if os.name == "nt":
        # The Windows loader needs SYSTEMROOT (and friends) to start python.exe at all.
        for key in ("SYSTEMROOT", "SYSTEMDRIVE", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT", "WINDIR"):
            if key in os.environ:
                env[key] = os.environ[key]
    # ``-I`` ignores user-site packages, so pass the parent's psutil location explicitly.
    # The worker adds it to sys.path only to import psutil, before hardening.
    try:
        import psutil as _ps

        env["GREENCODE_PSUTIL_DIR"] = os.path.dirname(os.path.dirname(_ps.__file__))
    except Exception:  # noqa: BLE001
        pass
    with tempfile.TemporaryDirectory(prefix="greencode-sandbox-") as cwd:
        try:
            proc = subprocess.run(
                [python, "-I", "-B", str(WORKER_PATH)],
                input=json.dumps(job),
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(ok=False, failure_type="timeout",
                                 error=f"sandbox exceeded {timeout:.0f}s")
        except OSError as err:
            return SandboxResult(ok=False, failure_type="sandbox_error", error=str(err))

    stderr = proc.stderr[-4000:]
    if proc.returncode != 0 and not proc.stdout.strip():
        ftype = "resource_limit" if proc.returncode < 0 or "MemoryError" in stderr else "runtime_error"
        return SandboxResult(ok=False, failure_type=ftype, stderr=stderr, returncode=proc.returncode,
                             error=f"worker exited with {proc.returncode}: {stderr.strip()[-500:]}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return SandboxResult(ok=False, failure_type="sandbox_error", stderr=stderr,
                             returncode=proc.returncode,
                             error=f"worker produced unparsable output: {proc.stdout[:300]!r}")
    if not data.get("ok", False):
        return SandboxResult(ok=False, data=data, failure_type=data.get("failure_type", "runtime_error"),
                             error=data.get("error"), stderr=stderr, returncode=proc.returncode)
    return SandboxResult(ok=True, data=data, stderr=stderr, returncode=proc.returncode)
