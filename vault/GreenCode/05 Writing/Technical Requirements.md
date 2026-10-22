---
title: Technical Requirements
created: 2026-10-22
project: GreenCode
type: report-section
tags: [writing, requirements]
---

# Technical Requirements

## Brief
Same style; first a short version; then James's own draft edited to add citations [27] (Bachras & Jacobsen), [31] (LibreHardwareMonitor) and [6] (Green Algorithms).

## Final text — James's draft with citations placed (turn 145)
Here's your text with the citations slotted in and the typos tidied, keeping your voice:

**Hardware:** I'm building GreenCode on just my laptop. About 10 GB of free disk space is needed, and the local AI model I'll be using via Ollama needs about 5 GB of RAM. Energy is read through the processor's RAPL counters, following the approach Bachras and Jacobsen take for database workloads [27], using LibreHardwareMonitor's signed driver as the reader on Windows [31]. Where no reader is available the system falls back to a documented coefficient estimate [6] and labels it as such. My benchmarks will run on mains power so that power management won't skew timings.

**Software:** I'll be building GreenCode using Python (3.12+ required) with FastAPI, SQLAlchemy and psycopg; the standard `ast` module and sqlglot for analysis. I'll have a subprocess sandbox with timeouts and memory limits for verifying results, and psutil, LibreHardwareMonitor [31] and optionally CodeCarbon for measuring resources and energy. My web dashboard will be built using React with TypeScript. I'll be using a PostgreSQL (16+) database to store everything, including the controlled dataset for the SQL experiments.

**Infrastructure:** I don't plan on hosting anything for this project, to minimise costs; everything will run locally. Another reason for this is that timing and energy can only be measured accurately when the hardware is known and stable. I considered using a hosted LLM API but decided against it, as it would remove control over model version and determinism and add a cost per run.

Changes beyond citations: "sqlgot" → "sqlglot", "PostgresSQL" → "PostgreSQL", and I swapped the CodeCarbon mention for LibreHardwareMonitor since that's what your laptop actually uses now (CodeCarbon stays as optional). Everything else is your wording.

(For reference, the user's original draft at turn 144 read:)

> Hardware: I'm building GreenCode off just my laptop. About 10 GB of free disk space is needed, and the local AI model ill be using via Ollama needs about 5 GB of RAM. Energy is read through the processors RAPL counters where a driver allows it, and my benchmarks will run on mains power so that power management wont affect and skew timings.
>
> Software: I'll be building Greencode using Python (3.12+ required) with FastAPI, SQLAlchemy and psycopg; the standard ast module and sqlgot for analysing. I'll have a subprocess sandbox with timeouts and limits on memory for verifying results, psutil and CodeCarbon for measuring energy. My web dashboard will be built using react with typescript. Ill be using a PostgresSQL (16+) database to store everything.
>
> Infrastructure: I don't plan on hosting anything for this project currently to minimise costs, I will have everything run locally. Another reason for this is timing and energy reads only can be measured accurately when the hardware is known and stable (local). I considered using a hosted LLM API but decided against this as it would remove control over model version and determinism.

## Alternative — Claude's short version with the same citations (turn 143)
Here is the short Technical Requirements section with those citations placed, plus one sentence you can drop into the methodology for the alternatives.

**Technical Requirements**

GreenCode is built to run on one ordinary laptop, because the research depends on controlling the measurement environment rather than on scale.

**Hardware.** A Windows machine with a multi-core x86-64 CPU, 16 GB RAM and about 10 GB of free disk. The local model, qwen2.5-coder:7b, needs around 5 GB of RAM through Ollama; a GPU helps but is not required. Energy is read from the processor's RAPL counters, following the approach Bachras and Jacobsen use for database workloads [27], through LibreHardwareMonitor's signed driver and web interface [31]; benchmarks run on mains power so that power management does not distort timings. Where counters are unavailable the system falls back to a documented coefficient estimate [6], labelled as such.

**Software.** Python 3.12+ with FastAPI, SQLAlchemy and psycopg; the standard `ast` module and sqlglot for analysis; a subprocess sandbox with timeouts and memory limits for verification; psutil, SciPy and optionally CodeCarbon for measurement. The dashboard is React with TypeScript, built by Vite. Ollama serves the model locally, and PostgreSQL 16+ holds both the evidence store and the controlled SQL benchmark dataset. Git, GitHub, VS Code, pytest and optional Docker Compose complete the toolchain.

**Infrastructure.** Nothing is hosted. Backend, database, model and dashboard all run locally, which is a methodological choice: timing and energy figures only mean something when the hardware is known and stable. GitHub provides version control and a CI pipeline, and the admin API is protected by a shared token. I rejected a hosted LLM API because it would remove control over model version and determinism and add a cost per run; I rejected SQLite because PostgreSQL is needed for the SQL experiments anyway.

**For the methodology section**, after you describe the LibreHardwareMonitor reader:

> I considered two alternatives for reading the counters on Windows. Intel's own Performance Counter Monitor [28] reports per-sample package and DRAM energy and has plotting support [29], but it requires compiling and test-signing a kernel driver; CodeCarbon [30] reads RAPL directly on Linux but falls back to a load-based estimate on Windows. LibreHardwareMonitor [31] exposes the same package counter through a signed driver, so I adopted it and kept the PCM path in the code for a Linux or driver-equipped machine.

> [!note] Both versions still mention Docker Compose / a CI pipeline, which have since been removed; drop those words before submission.
