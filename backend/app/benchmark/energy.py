"""Energy and carbon measurement.

Three methods are implemented, in decreasing order of fidelity, mirroring the
Software Energy Intensity distinction between *measurement*, *calculation* and
*coefficient-based estimation*:

``rapl``        Intel/AMD RAPL counters via the Linux powercap interface. A direct
                hardware measurement of package (CPU + uncore) energy. Machine-wide,
                so an idle-power baseline is recorded and subtracted.
``codecarbon``  The CodeCarbon library's tracker (uses RAPL/NVML where available and
                falls back to TDP-based estimation internally).
``estimate``    A documented coefficient model (Green Algorithms, Lannelongue et al.
                2021): E = t_cpu * P_core + t_wall * mem_GB * P_mem, scaled by PUE.

The pipeline records *which* method produced every figure (``measurements.method``
= measured | estimated, ``measurements.source``) so the dissertation can present
measured and estimated values separately and discuss their limitations.
"""

from __future__ import annotations

import glob
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from app.config import Settings, get_settings

RAPL_GLOB = "/sys/class/powercap/intel-rapl:*/energy_uj"


@dataclass
class EnergySample:
    joules: float
    method: str  # measured | estimated
    source: str  # rapl | codecarbon | estimate
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
# RAPL
# ----------------------------------------------------------------------------

def rapl_package_files() -> list[str]:
    """Top-level package domains only (``intel-rapl:N``), not sub-domains."""
    files = []
    for path in sorted(glob.glob(RAPL_GLOB)):
        name_file = os.path.join(os.path.dirname(path), "name")
        try:
            with open(name_file) as fh:
                name = fh.read().strip()
            with open(path) as fh:
                fh.read()
        except OSError:
            continue
        if name.startswith("package") or name == "psys":
            files.append(path)
    return files


def rapl_available() -> bool:
    return bool(rapl_package_files())


def _read_uj(path: str) -> int:
    with open(path) as fh:
        return int(fh.read().strip())


def _max_uj(path: str) -> int:
    try:
        with open(os.path.join(os.path.dirname(path), "max_energy_range_uj")) as fh:
            return int(fh.read().strip())
    except OSError:
        return 2**63


class RaplMeter:
    source = "rapl"

    def __init__(self) -> None:
        self.files = rapl_package_files()
        self._start: dict[str, int] = {}
        self._t0 = 0.0

    def start(self) -> None:
        self._t0 = time.perf_counter()
        self._start = {f: _read_uj(f) for f in self.files}

    def stop(self) -> EnergySample:
        wall = time.perf_counter() - self._t0
        total_uj = 0
        per_domain = {}
        for f, s in self._start.items():
            e = _read_uj(f)
            delta = e - s
            if delta < 0:  # counter wrapped
                delta += _max_uj(f)
            per_domain[f] = delta
            total_uj += delta
        return EnergySample(joules=total_uj / 1e6, method="measured", source=self.source,
                            wall_seconds=wall, details={"domains_uj": per_domain})


def measure_idle_power_watts(seconds: float = 1.0) -> float | None:
    """Sample RAPL while sleeping to estimate the machine's idle draw."""
    if not rapl_available():
        return None
    m = RaplMeter()
    m.start()
    time.sleep(seconds)
    s = m.stop()
    return s.joules / s.wall_seconds if s.wall_seconds else None


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
        if rapl_available():
            return "rapl"
        if codecarbon_available():
            return "codecarbon"
        return "estimate"
    if method == "rapl" and not rapl_available():
        return "estimate"
    if method == "codecarbon" and not codecarbon_available():
        return "estimate"
    return method


def make_meter(method: str, settings: Settings | None = None):  # type: ignore[no-untyped-def]
    settings = settings or get_settings()
    if method == "rapl":
        return RaplMeter()
    if method == "codecarbon":
        iso = {"IE": "IRL", "EU": "IRL", "WORLD": "IRL"}.get(settings.carbon_factor_region, "IRL")
        return CodeCarbonMeter(country_iso=iso)
    return None


def co2e_grams(joules: float, grams_per_kwh: float) -> float:
    return joules / 3.6e6 * grams_per_kwh
