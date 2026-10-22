---
title: Deliverables
created: 2026-10-22
project: GreenCode
type: report-section
tags: [writing, deliverables]
---

# Deliverables

## Brief
"What are your project deliverables?" — same style; deliverable 1 then humanised and shortened.

## Final text
I will produce three kinds of deliverable: a working system, an experimental dataset with its analysis, and the written record that lets someone else judge or repeat the work. I have grouped them below in the order an examiner would meet them.

**1. The GreenCode system (software).** The first deliverable is the system itself, as an open-source repository anyone can clone and run: a FastAPI backend, a React dashboard, the PostgreSQL schema and seed data, Docker configuration and a CI pipeline. Underneath, a versioned rule catalogue looks for known inefficiencies in Python (via the AST) and SQL (via sqlglot and EXPLAIN). A prompt pipeline then asks a local model, through Ollama, for an optimised version under one of two conditions: the code alone, or the code with the structured findings. Since I do not take a model's output on trust, a sandboxed verifier rejects any incorrect candidate before it is benchmarked with warm-up runs, repeated timings and confidence intervals. An energy layer reads RAPL or CodeCarbon where the hardware allows and otherwise falls back to a documented coefficient estimate [6], labelling every figure as measured or estimated. A dashboard, audited against Nielsen's heuristics [26], presents the verdict, diff, speed-up, energy, CO₂e and the four hypotheses. An administration page, a results export and a pytest suite complete it.

**2. The benchmark suite and evidence dataset.** A curated set of 30–50 Python and SQL cases, each with an original implementation, correctness tests and a benchmark harness, stored in a documented JSON format so that others can add cases. Running the suite produces the evidence dataset: every optimisation with its prompt, raw model response, candidate, test outcomes, timing samples, measurements, carbon factor and environment snapshot, held in PostgreSQL and exportable as CSV. I will release this dataset with the dissertation so that the statistics can be recomputed independently.

**3. The dissertation.** A written report containing the literature review, research question and hypotheses, methodology, system design (including the flowchart, use case and class diagrams), the experimental results with their statistical tests, an analysis of failed as well as successful optimisations, a discussion of AI accountability, threats to validity and limitations, and conclusions. Alongside it I will submit a user and reproducibility guide (README, methodology and architecture documents), the project management record (Git history, task board, experiment log) and a final presentation and demonstration.

The research contribution lies in deliverables 2 and 3: the system is the instrument, but the evidence and its interpretation are what answer the research question.

> [!note] Since this was written the Docker configuration and CI pipeline were removed (the project is Windows-native, see [[01 Project/Decisions log]]). Update the first sentence of deliverable 1 accordingly before submission: "…a FastAPI backend, a React dashboard, the PostgreSQL schema and seed data, and a documented Windows setup."
