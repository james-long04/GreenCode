---
title: Energy measurement
created: 2026-10-22
project: GreenCode
tags: [architecture, energy]
---

# Energy measurement (`benchmark/energy.py`)

`select_method(settings)` resolves `auto` → `lhm → codecarbon → estimate`. Every `EnergySample` has `joules, method (measured|estimated), source, wall_seconds, details, idle_joules, net_joules`.

## LibreHardwareMonitor (`LhmMeter`) — measured
- Reads CPU **package** power from LHM's web server JSON (`_lhm_power_sensors()` walks for `/power/` SensorIds under the CPU node; parses "7,5 W"; `_lhm_package_watts()` prefers "package").
- LHM refreshes ~1 s. The meter polls every 100 ms, records a value-change event, treats each new reading as **mean power over the preceding refresh interval**, keeps polling ≤ 3 s after the window closes (`MAX_TAIL_SECONDS`), integrates overlap with the window.
- `details`: `coverage`, `distinct_readings`, `mean_watts`, `idle_watts`.
- **Idle floor**: `measure_idle_power_watts(6.0)` returns the **minimum** reading; `net_joules = joules − idle_watts × wall`.
- First real result: 21.9 J gross / 13.9 J net at 14.5 W vs 5.3 W idle.

## CodeCarbon (`CodeCarbonMeter`) — measured/estimated
Fallback; on Windows it is TDP-based, not RAPL.

## Coefficient estimate (`estimate_energy`) — estimated
Green Algorithms: CPU time × (TDP / cores) + wall × RAM GB × 0.3725 W/GB, × PUE. **Always stored alongside** any measurement (H4 comparison).

## CO₂e
`co2e_grams(joules, factor)` with the default `carbon_factors` row (SEAI, region IE). Tagged `derived` when energy was measured, `estimated` otherwise.

## Setup on the laptop
LibreHardwareMonitor **as Administrator** → Options → Remote Web Server → Run. Sidebar shows **Energy: lhm**. Set LHM to start with Windows. Close other apps during runs; plug in; same power plan.

## Why not Intel PCM / CodeCarbon RAPL
See [[01 Project/Supervisor guidance — energy measurement]].

Dashboard: `wattsNote()` shows mean/idle W; badges measured = green, derived = blue, estimated = amber.
