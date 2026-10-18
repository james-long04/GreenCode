"""Energy and carbon measurement.

Three methods are implemented, in decreasing order of fidelity, mirroring the
Software Energy Intensity distinction between *measurement*, *calculation* and
*coefficient-based estimation*:

``rapl``        Intel/AMD RAPL counters via the Linux powercap interface. A direct
                hardware measurement of package (CPU + uncore) energy. Machine-wide,
                so an idle-power baseline is recorded and subtracted.
``pcm``         Intel Performance Counter Monitor (``pcm.exe``) sampling the same RAPL
                counters on Windows, where the powercap interface does not exist.
                Package and DRAM energy per sample are summed over the measured window.
``codecarbon``  The CodeCarbon library's tracker (uses RAPL/NVML where available and
                falls back to TDP-based estimation internally).
``estimate``    A documented coefficient model (Green Algorithms, Lannelongue et al.
                2021): E = t_cpu * P_core + t_wall * mem_GB * P_mem, scaled by PUE.

The pipeline records *which* method produced every figure (``measurements.method``
= measured | estimated, ``measurements.source``) so the dissertation can present
measured and estimated values separately and discuss their limitations.
"""

from __future__ import annotations

import csv
import functools
import glob
import os
import shutil
import subprocess
import sys
import tempfile
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


def measure_idle_power_watts(seconds: float = 1.0, method: str = "rapl") -> float | None:
    """Sample the machine-wide meter while sleeping to estimate the idle draw."""
    if method == "rapl" and rapl_available():
        m: Any = RaplMeter()
    elif method == "pcm" and pcm_available():
        m = PcmMeter()
    else:
        return None
    m.start()
    time.sleep(seconds)
    s = m.stop()
    return s.joules / s.wall_seconds if s.wall_seconds else None


# ----------------------------------------------------------------------------
# Intel PCM (Windows route to RAPL)
# ----------------------------------------------------------------------------

PCM_INTERVAL_SECONDS = 0.1


def pcm_executable(settings: Settings | None = None) -> str | None:
    settings = settings or get_settings()
    if settings.pcm_path:
        return settings.pcm_path if os.path.exists(settings.pcm_path) else None
    for name in ("pcm", "pcm.exe"):
        found = shutil.which(name)
        if found:
            return found
    return None


@functools.lru_cache(maxsize=1)
def pcm_available() -> bool:
    """True when pcm is installed *and* can read the energy counters (driver + privileges)."""
    exe = pcm_executable()
    if not exe:
        return False
    try:
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "probe.csv")
            subprocess.run([exe, "0.1", "-i=2", f"-csv={out}"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=20, check=False)
            if not os.path.exists(out):
                return False
            rows = _read_pcm_csv(out)
            return any(r.get("proc_j") is not None for r in rows)
    except Exception:  # noqa: BLE001
        return False


def _read_pcm_csv(path: str) -> list[dict[str, float | None]]:
    """Parse PCM's two-header CSV into rows of {proc_j, dram_j}. Tolerates ';' or ','."""
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        head = fh.readline()
        if not head:
            return []
        delim = ";" if head.count(";") > head.count(",") else ","
        fh.seek(0)
        reader = csv.reader(fh, delimiter=delim)
        groups = next(reader, None)
        names = next(reader, None)
        if not groups or not names:
            return []
        current = ""
        proc_idx = dram_idx = None
        for i, name in enumerate(names):
            if i < len(groups) and groups[i]:
                current = groups[i]
            lname = name.strip().lower()
            if current.lower().startswith("system"):
                if proc_idx is None and lname.startswith("proc energy"):
                    proc_idx = i
                if dram_idx is None and lname.startswith("dram energy"):
                    dram_idx = i
        rows: list[dict[str, float | None]] = []
        for rec in reader:
            def val(idx: int | None) -> float | None:
                try:
                    return float(rec[idx]) if idx is not None and rec[idx] not in ("", "N/A") else None
                except (ValueError, IndexError):
                    return None
            rows.append({"proc_j": val(proc_idx), "dram_j": val(dram_idx)})
        return rows


class PcmMeter:
    """Runs pcm as a background sampler for the duration of the measured window.

    PCM reports energy consumed per sampling interval, so the total is the sum of the
    samples that fall inside the window, scaled by the fraction of the window they cover.
    The coverage ratio is recorded so short windows can be judged for what they are.
    """

    source = "pcm"

    def __init__(self, settings: Settings | None = None) -> None:
        self.exe = pcm_executable(settings)
        self._tmp = tempfile.mkdtemp(prefix="greencode-pcm-")
        self._csv = os.path.join(self._tmp, "pcm.csv")
        self._proc: subprocess.Popen[bytes] | None = None
        self._t0 = 0.0

    def start(self) -> None:
        if not self.exe:
            raise RuntimeError("pcm executable not found")
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0  # type: ignore[attr-defined]
        self._proc = subprocess.Popen([self.exe, str(PCM_INTERVAL_SECONDS), f"-csv={self._csv}"],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
        # Let pcm initialise and write its headers before the window starts.
        deadline = time.time() + 10
        while time.time() < deadline and not (os.path.exists(self._csv) and os.path.getsize(self._csv) > 0):
            time.sleep(0.05)
        time.sleep(PCM_INTERVAL_SECONDS)
        self._t0 = time.perf_counter()

    def stop(self) -> EnergySample:
        wall = time.perf_counter() - self._t0
        # Allow one more interval so the final partial sample is flushed, then stop pcm.
        time.sleep(PCM_INTERVAL_SECONDS * 1.5)
        if self._proc is not None:
            try:
                if sys.platform == "win32":
                    import signal

                    self._proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
                else:
                    self._proc.terminate()
                self._proc.wait(timeout=5)
            except Exception:  # noqa: BLE001
                self._proc.kill()
        rows = _read_pcm_csv(self._csv) if os.path.exists(self._csv) else []
        # Drop the warm-up sample taken before t0; the rest cover the window plus the flush.
        rows = rows[1:] if len(rows) > 1 else rows
        proc = sum(r["proc_j"] or 0.0 for r in rows)
        dram = sum(r["dram_j"] or 0.0 for r in rows)
        covered = len(rows) * PCM_INTERVAL_SECONDS
        scale = (wall / covered) if covered > 0 else 0.0
        total = (proc + dram) * scale
        shutil.rmtree(self._tmp, ignore_errors=True)
        return EnergySample(joules=total, method="measured", source=self.source, wall_seconds=wall,
                            details={"samples": len(rows), "interval_s": PCM_INTERVAL_SECONDS,
                                     "covered_s": covered, "scale": scale, "proc_joules_raw": proc,
                                     "dram_joules_raw": dram, "tool": "Intel PCM"})


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
        if pcm_available():
            return "pcm"
        if codecarbon_available():
            return "codecarbon"
        return "estimate"
    if method == "rapl" and not rapl_available():
        return "estimate"
    if method == "pcm" and not pcm_available():
        return "estimate"
    if method == "codecarbon" and not codecarbon_available():
        return "estimate"
    return method


def make_meter(method: str, settings: Settings | None = None):  # type: ignore[no-untyped-def]
    settings = settings or get_settings()
    if method == "rapl":
        return RaplMeter()
    if method == "pcm":
        return PcmMeter(settings)
    if method == "codecarbon":
        iso = {"IE": "IRL", "EU": "IRL", "WORLD": "IRL"}.get(settings.carbon_factor_region, "IRL")
        return CodeCarbonMeter(country_iso=iso)
    return None


def co2e_grams(joules: float, grams_per_kwh: float) -> float:
    return joules / 3.6e6 * grams_per_kwh
