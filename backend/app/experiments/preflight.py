"""Laboratory-protocol pre-flight checks (docs/protocol.md).

Each check returns (name, ok, detail). ``run_checks`` is used by scripts/run_tpch.py, which
refuses to start a work package while any *required* check fails unless ``--force`` is given.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

import psutil

from app.benchmark.energy import lhm_available
from app.config import Settings, get_settings


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True


NOISY = {"ollama": "Ollama holds ~5 GB and wakes up periodically; stop it (ollama stop / quit the tray icon)",
         "chrome": "browser open", "msedge": "browser open", "firefox": "browser open",
         "code": "VS Code open", "teams": "Teams open", "spotify": "Spotify open", "discord": "Discord open",
         "steam": "Steam open", "onedrive": "OneDrive syncing", "searchindexer": "Windows Search indexing",
         "tiworker": "Windows Update servicing", "mousocoreworker": "Windows Update orchestrator"}


def _procs() -> set[str]:
    out = set()
    for p in psutil.process_iter(["name"]):
        out.add((p.info.get("name") or "").lower().removesuffix(".exe"))
    return out


def _power_plan() -> str | None:
    if os.name != "nt":
        return None
    try:
        r = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:  # noqa: BLE001
        return None


def run_checks(settings: Settings | None = None, *, meter: str = "lhm", expect_plan: str | None = None) -> list[Check]:
    settings = settings or get_settings()
    checks: list[Check] = []

    # power
    b = None
    try:
        b = psutil.sensors_battery()
    except Exception:  # noqa: BLE001
        pass
    if b is None:
        checks.append(Check("mains power", True, "no battery detected (desktop)", required=False))
    else:
        checks.append(Check("mains power", bool(b.power_plugged),
                            f"{'plugged in' if b.power_plugged else 'ON BATTERY'} ({b.percent:.0f} %)"))
    plan = _power_plan()
    if expect_plan:
        ok = plan is not None and expect_plan.lower() in plan.lower()
        checks.append(Check("power plan", ok, f"active: {plan or 'unknown'}; expected to contain '{expect_plan}'"))
    else:
        checks.append(Check("power plan", True, f"active: {plan or 'unknown'} (recorded, not enforced)", required=False))

    # meter
    if meter == "lhm":
        ok = lhm_available()
        checks.append(Check("LibreHardwareMonitor", ok,
                            f"{settings.lhm_url} {'reachable, package power sensor found' if ok else 'NOT reachable (run LHM as Administrator, Options > Remote Web Server > Run)'}"))

    # quiet machine
    procs = _procs()
    present = {p: NOISY[p] for p in NOISY if p in procs}
    checks.append(Check("Ollama stopped", "ollama" not in procs,
                        "ollama is not running" if "ollama" not in procs else NOISY["ollama"]))
    others = {k: v for k, v in present.items() if k != "ollama"}
    checks.append(Check("noisy processes", not others,
                        "none of the usual suspects" if not others else "; ".join(f"{k} ({v})" for k, v in others.items()),
                        required=False))
    cpu = psutil.cpu_percent(interval=2.0)
    checks.append(Check("idle CPU", cpu < 10.0, f"{cpu:.0f} % over 2 s (want < 10 %)", required=False))

    # memory headroom
    vm = psutil.virtual_memory()
    checks.append(Check("free memory", vm.available > 4e9, f"{vm.available / 1e9:.1f} GB available"))
    return checks


def format_checks(checks: list[Check]) -> str:
    lines = []
    for c in checks:
        mark = "OK " if c.ok else ("!! " if c.required else "?? ")
        lines.append(f"  [{mark}] {c.name:<22} {c.detail}")
    return "\n".join(lines)


def all_required_ok(checks: list[Check]) -> bool:
    return all(c.ok for c in checks if c.required)
