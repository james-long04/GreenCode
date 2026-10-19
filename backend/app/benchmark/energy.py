"""Energy and carbon measurement.

Three methods are implemented, in decreasing order of fidelity (the project runs on a
Windows laptop; LibreHardwareMonitor reads the processor's RAPL energy counter there), mirroring the
Software Energy Intensity distinction between *measurement*, *calculation* and
*coefficient-based estimation*:

``lhm``         LibreHardwareMonitor's built-in web server (Windows). LHM ships a signed
                driver and exposes the CPU package power (from RAPL) as JSON; the meter
                polls it and integrates power over the window.
``codecarbon``  The CodeCarbon library's tracker (uses RAPL/NVML where available and
                falls back to TDP-based estimation internally).
``estimate``    A documented coefficient model (Green Algorithms, Lannelongue et al.
                2021): E = t_cpu * P_core + t_wall * mem_GB * P_mem, scaled by PUE.

The pipeline records *which* method produced every figure (``measurements.method``
= measured | estimated, ``measurements.source``) so the dissertation can present
measured and estimated values separately and discuss their limitations.
"""

from __future__ import annotations

import functools
import os
import threading
import time
import json
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any

from app.config import Settings, get_settings



@dataclass
class EnergySample:
    joules: float
    method: str  # measured | estimated
    source: str  # lhm | codecarbon | estimate
    wall_seconds: float
    details: dict[str, Any] = field(default_factory=dict)
    idle_joules: float | None = None  # subtracted baseline for machine-wide meters

    @property
    def net_joules(self) -> float:
        if self.idle_joules is None:
            return self.joules
        return max(self.joules - self.idle_joules, 0.0)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["net_joules"] = self.net_joules
        return d


# ----------------------------------------------------------------------------
# LibreHardwareMonitor (Windows, signed driver, JSON over HTTP)
# ----------------------------------------------------------------------------

LHM_POLL_SECONDS = 0.1


def _lhm_fetch(url: str, timeout: float = 1.0) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:  # noqa: BLE001
        return None


def _lhm_power_sensors(tree: dict[str, Any]) -> list[tuple[str, float]]:
    """Walk LHM's nested JSON and return (name, watts) for CPU power sensors."""
    out: list[tuple[str, float]] = []

    def walk(node: dict[str, Any], path: list[str]) -> None:
        sid = str(node.get("SensorId", ""))
        text = str(node.get("Text", ""))
        if "/power/" in sid and ("cpu" in sid.lower() or any("cpu" in p.lower() for p in path)):
            raw = str(node.get("Value", "")).replace("W", "").replace(",", ".").strip()
            try:
                out.append((text, float(raw)))
            except ValueError:
                pass
        for child in node.get("Children", []) or []:
            walk(child, path + [text])

    walk(tree, [])
    return out


def _lhm_package_watts(tree: dict[str, Any]) -> tuple[str, float] | None:
    sensors = _lhm_power_sensors(tree)
    for name, w in sensors:
        if "package" in name.lower():
            return name, w
    return sensors[0] if sensors else None


@functools.lru_cache(maxsize=1)
def lhm_available() -> bool:
    url = get_settings().lhm_url
    tree = _lhm_fetch(url)
    return bool(tree) and _lhm_package_watts(tree) is not None


class LhmMeter:
    """Polls LibreHardwareMonitor's web server and integrates CPU package power.

    LHM refreshes its sensors about once a second, so a reading observed at time ``u_k``
    is the average power over the *preceding* refresh interval ``(u_{k-1}, u_k]``. The
    meter therefore keeps polling after the window closes until it has seen the first
    refresh that lands after ``t1``, then integrates each reading over the part of its
    interval that overlaps the window. Without this, the first second of every window
    reports pre-window (idle) power and the last second of activity is never seen.
    """

    source = "lhm"
    MAX_TAIL_SECONDS = 3.0

    def __init__(self, settings: Settings | None = None) -> None:
        self.url = (settings or get_settings()).lhm_url
        self._updates: list[tuple[float, float]] = []  # (time observed, watts) at value changes only
        self._polls = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._t0 = 0.0
        self._sensor = ""

    def _poll(self) -> None:
        last: float | None = None
        while not self._stop.is_set():
            tree = _lhm_fetch(self.url, timeout=0.5)
            if tree:
                pw = _lhm_package_watts(tree)
                if pw:
                    self._sensor, watts = pw
                    self._polls += 1
                    if last is None or watts != last:
                        self._updates.append((time.perf_counter(), watts))
                        last = watts
            self._stop.wait(LHM_POLL_SECONDS)

    def start(self) -> None:
        self._updates.clear()
        self._polls = 0
        self._stop.clear()
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()
        # Capture the reading in force when the window opens.
        deadline = time.time() + 2.0
        while not self._updates and time.time() < deadline:
            time.sleep(0.02)
        self._t0 = time.perf_counter()

    def stop(self) -> EnergySample:
        t1 = time.perf_counter()
        wall = t1 - self._t0
        # Wait for the first refresh after the window closed so the tail is covered.
        deadline = time.time() + self.MAX_TAIL_SECONDS
        while time.time() < deadline and not any(u > t1 for u, _ in self._updates):
            time.sleep(0.05)
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        ups = sorted(self._updates)
        joules = 0.0
        covered = 0.0
        for i, (u, w) in enumerate(ups):
            prev = ups[i - 1][0] if i else self._t0 - 1.0  # first reading covers the window start
            lo, hi = max(prev, self._t0), min(u, t1)
            if hi > lo:
                joules += w * (hi - lo)
                covered += hi - lo
        if ups and covered < wall:  # window ran past the last refresh we saw
            joules += ups[-1][1] * (wall - covered)
        mean_w = joules / wall if wall else 0.0
        return EnergySample(joules=joules, method="measured", source=self.source, wall_seconds=wall,
                            details={"sensor": self._sensor, "polls": self._polls, "distinct_readings": len(ups),
                                     "mean_watts": mean_w, "coverage": (covered / wall) if wall else 0.0,
                                     "tool": "LibreHardwareMonitor"})


def measure_idle_power_watts(seconds: float = 6.0) -> float | None:
    """Sample LibreHardwareMonitor while sleeping and return the idle floor.

    LHM readings are one-second averages that include background spikes, so the *lowest*
    steady reading in the period is taken as the idle floor rather than the mean.
    """
    if not lhm_available():
        return None
    m = LhmMeter()
    m.start()
    time.sleep(seconds)
    m.stop()
    readings = [w for _, w in m._updates if w > 0]
    return min(readings) if readings else None




# ----------------------------------------------------------------------------
# CodeCarbon
# ----------------------------------------------------------------------------

def codecarbon_available() -> bool:
    try:
        import codecarbon  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


class CodeCarbonMeter:
    source = "codecarbon"

    def __init__(self, country_iso: str = "IRL") -> None:
        from codecarbon import OfflineEmissionsTracker  # type: ignore

        self.tracker = OfflineEmissionsTracker(
            country_iso_code=country_iso, save_to_file=False, log_level="error",
            tracking_mode="machine", measure_power_secs=1,
        )
        self._t0 = 0.0

    def start(self) -> None:
        self._t0 = time.perf_counter()
        self.tracker.start()

    def stop(self) -> EnergySample:
        self.tracker.stop()
        wall = time.perf_counter() - self._t0
        data = self.tracker.final_emissions_data
        kwh = float(getattr(data, "energy_consumed", 0.0) or 0.0)
        details = {
            "emissions_kg": float(getattr(data, "emissions", 0.0) or 0.0),
            "cpu_energy_kwh": float(getattr(data, "cpu_energy", 0.0) or 0.0),
            "ram_energy_kwh": float(getattr(data, "ram_energy", 0.0) or 0.0),
            "gpu_energy_kwh": float(getattr(data, "gpu_energy", 0.0) or 0.0),
            "cpu_model": getattr(data, "cpu_model", None),
            "codecarbon_version": getattr(data, "codecarbon_version", None),
        }
        return EnergySample(joules=kwh * 3.6e6, method="measured", source=self.source,
                            wall_seconds=wall, details=details)


# ----------------------------------------------------------------------------
# Coefficient-based estimate
# ----------------------------------------------------------------------------

def estimate_energy(cpu_seconds: float, wall_seconds: float, peak_rss_bytes: float,
                    settings: Settings | None = None) -> EnergySample:
    settings = settings or get_settings()
    cores = os.cpu_count() or 1
    p_core = settings.estimate_cpu_tdp_watts / cores
    mem_gb = peak_rss_bytes / 1e9
    cpu_j = cpu_seconds * p_core
    mem_j = wall_seconds * mem_gb * settings.estimate_memory_watts_per_gb
    total = (cpu_j + mem_j) * settings.estimate_pue
    return EnergySample(
        joules=total, method="estimated", source="estimate", wall_seconds=wall_seconds,
        details={
            "model": "Green Algorithms (Lannelongue, Grealey & Inouye, 2021)",
            "cpu_tdp_watts": settings.estimate_cpu_tdp_watts, "logical_cores": cores,
            "watts_per_core": p_core, "memory_watts_per_gb": settings.estimate_memory_watts_per_gb,
            "pue": settings.estimate_pue, "cpu_seconds": cpu_seconds, "peak_rss_gb": mem_gb,
            "cpu_joules": cpu_j, "memory_joules": mem_j,
        },
    )


# ----------------------------------------------------------------------------
# Selection
# ----------------------------------------------------------------------------

def select_method(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    method = settings.energy_method
    if method == "auto":
        if lhm_available():
            return "lhm"
        if codecarbon_available():
            return "codecarbon"
        return "estimate"
    if method == "lhm" and not lhm_available():
        return "estimate"
    if method == "codecarbon" and not codecarbon_available():
        return "estimate"
    return method


def make_meter(method: str, settings: Settings | None = None):  # type: ignore[no-untyped-def]
    settings = settings or get_settings()
    if method == "lhm":
        return LhmMeter(settings)
    if method == "codecarbon":
        iso = {"IE": "IRL", "EU": "IRL", "WORLD": "IRL"}.get(settings.carbon_factor_region, "IRL")
        return CodeCarbonMeter(country_iso=iso)
    return None


def co2e_grams(joules: float, grams_per_kwh: float) -> float:
    return joules / 3.6e6 * grams_per_kwh
