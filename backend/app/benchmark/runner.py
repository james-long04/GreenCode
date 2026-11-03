"""Benchmark engine: repeated, measured execution of a Python or SQL workload.

Each call benchmarks ONE variant (original or candidate). The caller is
responsible for benchmarking the pair back-to-back so both see the same
machine state. Interleaving is handled in ``experiments.pipeline``.
"""

from __future__ import annotations

import os
import platform
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import psutil

from app.benchmark.energy import (
    EnergySample,
    estimate_energy,
    make_meter,
    measure_idle_power_watts,
    select_method,
)
from app.benchmark.stats import Summary, summarise
from app.config import Settings, get_settings
from app.verification.sandbox import run_job


@dataclass
class BenchmarkOutcome:
    ok: bool
    samples_ms: list[float] = field(default_factory=list)
    summary: Summary | None = None
    cpu_time_ms: float | None = None
    peak_rss_mb: float | None = None
    wall_seconds: float | None = None
    energy: list[EnergySample] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)  # extra numeric metrics
    environment: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    failure_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["summary"] = self.summary.to_dict() if self.summary else None
        d["energy"] = [e.to_dict() for e in self.energy]
        return d

    @property
    def primary_energy(self) -> EnergySample | None:
        return self.energy[0] if self.energy else None


def host_state() -> dict[str, Any]:
    """Laboratory-protocol facts: power plan, battery, process count, noisy processes (Windows-aware)."""
    out: dict[str, Any] = {"process_count": len(psutil.pids())}
    try:
        b = psutil.sensors_battery()
        if b is not None:
            out["on_ac_power"] = bool(b.power_plugged)
            out["battery_percent"] = b.percent
    except Exception:  # noqa: BLE001
        pass
    noisy = {"ollama", "msmpeng", "searchindexer", "onedrive", "chrome", "msedge", "firefox", "code", "teams",
             "spotify", "discord", "steam", "tiworker", "mousocoreworker"}
    present = set()
    for p in psutil.process_iter(["name"]):
        n = (p.info.get("name") or "").lower().removesuffix(".exe")
        if n in noisy:
            present.add(n)
    out["noisy_processes"] = sorted(present)
    if os.name == "nt":
        try:
            import subprocess
            r = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True, timeout=5)
            out["power_plan"] = r.stdout.strip().split(":", 1)[-1].strip() if r.returncode == 0 else None
            r = subprocess.run(["powercfg", "/overlaygetactivescheme"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                out["power_mode_overlay"] = r.stdout.strip().split(":", 1)[-1].strip()
        except Exception:  # noqa: BLE001
            pass
    return out


def environment_snapshot(settings: Settings) -> dict[str, Any]:
    vm = psutil.virtual_memory()
    freq = None
    try:
        f = psutil.cpu_freq()
        freq = f.current if f else None
    except Exception:  # noqa: BLE001
        pass
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "logical_cores": os.cpu_count(),
        "physical_cores": psutil.cpu_count(logical=False),
        "cpu_freq_mhz": freq,
        "memory_total_gb": round(vm.total / 1e9, 2),
        "load_avg_1m": os.getloadavg()[0] if hasattr(os, "getloadavg") else None,
        "energy_method": select_method(settings),
        **host_state(),
        "warmup_runs": settings.benchmark_warmup_runs,
        "repetitions": settings.benchmark_repetitions,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


class EnergyContext:
    """Starts the selected meter and records an idle baseline once per session."""

    def __init__(self, settings: Settings | None = None, method: str | None = None,
                 poll_seconds: float | None = None, idle_seconds: float = 6.0) -> None:
        self.settings = settings or get_settings()
        self.method = method or select_method(self.settings)
        self.poll_seconds = poll_seconds
        self.idle_watts: float | None = None
        if self.method == "lhm":
            # LHM refreshes about once a second; a longer, quiet baseline is needed.
            self.idle_watts = measure_idle_power_watts(idle_seconds)

    def measure(self, fn, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Run ``fn`` and return (result, [energy samples])."""
        meter = make_meter(self.method, self.settings, poll_seconds=self.poll_seconds)
        t0 = time.perf_counter()
        if meter is not None:
            meter.start()
        result = fn(*args, **kwargs)
        samples: list[EnergySample] = []
        wall = time.perf_counter() - t0
        if meter is not None:
            sample = meter.stop()
            if self.idle_watts is not None:
                sample.idle_joules = self.idle_watts * sample.wall_seconds
                sample.details["idle_watts"] = self.idle_watts
                sample.details["mean_watts"] = sample.joules / sample.wall_seconds if sample.wall_seconds else None
            samples.append(sample)
        return result, samples, wall


def benchmark_python(source: str, spec: dict[str, Any], settings: Settings | None = None,
                     energy_ctx: EnergyContext | None = None,
                     repetitions: int | None = None, warmup: int | None = None) -> BenchmarkOutcome:
    settings = settings or get_settings()
    energy_ctx = energy_ctx or EnergyContext(settings)
    reps = repetitions or settings.benchmark_repetitions
    warm = settings.benchmark_warmup_runs if warmup is None else warmup
    bench = spec.get("benchmark") or {}
    call = bench.get("call")
    if not call:
        return BenchmarkOutcome(ok=False, error="case has no benchmark.call", failure_type="no_benchmark")
    job = {"mode": "benchmark", "source": source, "setup": bench.get("setup", ""), "call": call,
           "warmup": warm, "repetitions": reps, "gc": bench.get("gc", True)}

    result, energy, wall = energy_ctx.measure(run_job, job, settings, settings.benchmark_timeout_seconds)
    if not result.ok:
        return BenchmarkOutcome(ok=False, error=result.error, failure_type=result.failure_type,
                                environment=environment_snapshot(settings))
    data = result.data
    samples = data["samples_ms"]
    cpu_ms = float(data.get("cpu_time_ms") or 0.0)
    rss_mb = float(data.get("peak_rss_kb") or 0) / 1024
    # The coefficient-based estimate is always recorded alongside any measurement so the
    # two can be compared (H4 / methodology discussion).
    est = estimate_energy(cpu_seconds=cpu_ms / 1000, wall_seconds=sum(samples) / 1000,
                          peak_rss_bytes=rss_mb * 1024 * 1024, settings=settings)
    energy = list(energy) + [est]
    return BenchmarkOutcome(
        ok=True, samples_ms=samples, summary=summarise(samples), cpu_time_ms=cpu_ms, peak_rss_mb=rss_mb,
        wall_seconds=wall, energy=energy,
        metrics={"user_time_ms": data.get("user_time_ms", 0.0), "system_time_ms": data.get("system_time_ms", 0.0),
                 "process_wall_seconds": wall},
        environment=environment_snapshot(settings),
    )
