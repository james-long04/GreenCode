---
title: Supervisor guidance — energy measurement
created: 2026-10-22
project: GreenCode
tags: [project, energy, supervisor]
---

# Supervisor guidance — energy measurement

The supervisor pointed to four things and asked whether they apply and whether the project can really measure energy:

| Pointer | What it is | Verdict for this laptop (Intel Core Ultra 5 135U, 12 cores, Windows) |
|---|---|---|
| **Intel PCM** | Intel's Performance Counter Monitor; reads RAPL at ~100 ms | Most precise, but on Windows it needs its MSR kernel driver compiled and **test-signed** (Visual Studio + WDK, test-signing mode). Not practical for a laptop that is also the daily machine. |
| **pcm-graph** | Plots PCM output | Depends on PCM; same blocker. |
| **CodeCarbon RAPL doc** | CodeCarbon reads `/sys/class/powercap` on Linux; on Windows it falls back to a TDP-based estimate | Not a real measurement on Windows. Kept as a fallback method. |
| **Bachras & Jacobsen 2025** (arXiv:2504.18980) | Measures analytical databases with RAPL package energy × regional grid intensity | Directly applicable precedent: same metric chain as GreenCode (package joules → kWh → gCO₂e via SEAI factor). Cited as [27]. |

## What was done
Added a **LibreHardwareMonitor** route: LHM ships a *signed* kernel driver and exposes "CPU Package" power as JSON from its built-in web server (`http://localhost:8085/data.json`). The backend's `LhmMeter` polls it; `select_method()` now prefers `lhm → codecarbon → estimate`. The sidebar shows **Energy: lhm** when it is running. Details in [[02 Architecture/Energy measurement]].

## Result of the first real measurement
Original workload: 21.9 J gross / 13.9 J net at 14.5 W mean vs 5.3 W idle floor.

## Caveats to report in the dissertation
1 s refresh is coarse relative to ms benchmarks → energy only over the whole repetition loop (30+ repetitions); reading is machine-wide → close other apps; approach is Intel/LHM-specific.

## The exchange (verbatim)

**User (turn 118, Sun 18 Oct 2026 15:17), verbatim:**

in a meeting with my supervisor, hes a bit old and im not quite sure if he fully understands my project idea yet, he told me to research intel pcm something to measure power from my laptop, rapl and all of that, and also sent me on this paper ive attached. and these links below. https://github.com/timogasda/pcm-graph https://www.intel.com/content/www/us/en/developer/articles/tool/performance-counter-monitor.html
https://docs.codecarbon.io/latest/explanation/rapl/ do these apply to my project, and am i able to measure evrything currently how the  project is, or do i need to modify things

(Attached PDF: `Environmental_impact_of_databases.pdf` — Bachras & Jacobsen, "Beyond Performance: Measuring the Environmental Impact of Analytical Databases", arXiv:2504.18980, 2025.)

**Assistant (turn 119), verbatim (after reading the PDF, energy.py, the CodeCarbon RAPL doc and the pcm-graph repo):**

Short version: yes, everything he sent is relevant, it's all the same topic approached from three angles, and no, your project as it stands cannot measure real energy on your laptop. It's falling back to the coefficient estimate, which is why your dashboard sidebar says "Energy: coefficient". Here's why, and what to change.

**What each thing is**

- **RAPL** is the energy counter built into Intel (and recent AMD) processors. It reports joules used by the CPU package and, on some machines, DRAM. It's the only way to *measure* rather than *estimate* energy on a laptop without a plug-in power meter. The paper your supervisor sent (Bachras & Jacobsen, "Beyond Performance", 2025) uses exactly this: RAPL for CPU and DRAM energy, multiplied by the grid's carbon intensity, which is the same formula GreenCode uses. So the paper is a good methodological precedent to cite, and it's also about database energy, which supports your SQL side.
- **Intel PCM** (Performance Counter Monitor) is Intel's open-source tool for reading those counters. On Windows it's the practical route, because Windows has no `/sys/class/powercap` interface. It needs a small driver installed once and must run as Administrator.
- **pcm-graph** is just a Python script that plots PCM's CSV output. It's handy for a figure in your dissertation, but it isn't a measurement tool.
- **The CodeCarbon RAPL page** explains how CodeCarbon reads the Linux counters. On Windows, CodeCarbon only has a limited "EMI" backend and otherwise falls back to estimating from CPU load, so installing it on your laptop wouldn't give you a real measurement either.

**Why your current code can't measure on Windows**

GreenCode's `RaplMeter` reads `/sys/class/powercap/intel-rapl:*/energy_uj`. That path only exists on Linux. On your Windows laptop `rapl_available()` is always false, CodeCarbon isn't installed, so `select_method()` picks `estimate`. The design was right to fall back honestly, but it means H3 and H4 are currently resting on an estimate derived from CPU time, which a sharp examiner will point out is almost tautological for H4.

**What to change**

1. Add a `PcmMeter` to `energy.py` that, on Windows, starts `pcm.exe` sampling to a CSV, runs the benchmark, stops it, and sums the "Proc Energy (Joules)" and "DRAM Energy (Joules)" columns over the window. It plugs into the existing `EnergyMeter` interface and gets labelled `measured`, source `pcm`, so no other code changes. I can write this.
2. Install Intel PCM on your laptop (download the Windows release from the GitHub page, run the driver installer, run uvicorn from an Administrator PowerShell).
3. Keep the idle-baseline subtraction the code already does, because PCM is machine-wide like RAPL.

**One thing I need to know first.** PCM only works on Intel processors. Run this in PowerShell and send me the output:

```powershell
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores
```

If it's Intel, the plan above works. If it's AMD, PCM won't help and we'd use AMD μProf or LibreHardwareMonitor instead, which is a different adapter.

For your supervisor, you can tell him plainly: "The system is designed for RAPL and falls back to an estimate; I'm adding Intel PCM as the Windows RAPL reader so the energy figures become real measurements, and I'll report both." That's exactly the distinction the Bachras paper and the SCI spec make.

**Follow-up (turn 120, user):** CPU reported as `Intel(R) Core(TM) Ultra 5 135U`, 12 cores.

**Outcome (turns 121–137, summarised, not verbatim):** PCM meter added (turn 121), then — because Intel PCM on Windows needs a self-compiled, test-signed MSR driver — a LibreHardwareMonitor route was added (turn 123) and became the one actually used on the laptop ("Energy: lhm"). Turn 131 summary sentence for the supervisor: "the laptop's Intel RAPL counters are read via LibreHardwareMonitor's signed driver, energy is integrated over each benchmark window with an idle baseline subtracted, and every figure is tagged measured or estimated." Turn 155 later removed the Linux RAPL and PCM code paths entirely; the energy chain is now lhm → codecarbon → estimate.
