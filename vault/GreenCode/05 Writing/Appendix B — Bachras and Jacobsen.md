---
title: Appendix B — Bachras and Jacobsen
created: 2026-10-22
project: GreenCode
type: report-section
tags: [writing, appendix]
---

# Appendix B: Second Similar Piece of Work Review — Bachras & Jacobsen [27]

M. Bachras and H.-A. Jacobsen, "Beyond performance: Measuring the environmental impact of analytical databases," arXiv:2504.18980, 2025.

Why it matters to GreenCode: precedent for RAPL package energy × regional grid intensity — the same metric chain GreenCode uses (package joules → kWh → gCO₂e via the SEAI factor). See [[01 Project/Supervisor guidance — energy measurement]].

## Final text
**Appendix B: Second Similar Piece of Work Review**

**Title:** Beyond Performance: Measuring the Environmental Impact of Analytical Databases [27]

**Author:** M. Bachras and H.-A. Jacobsen, University of Toronto, arXiv 2025

**Description (brief):** The authors argue that database research optimises for response time and ignores what a query costs the planet. They present ATLAS, a methodology for quantifying the carbon and water footprint of database operations, and EcoQuery, a benchmark harness that extends TPC-H with environmental instrumentation. They run four analytical engines (DuckDB, Hyper, MonetDB and StarRocks) on the same server, read CPU and DRAM energy from Intel RAPL during each query, convert it to CO₂e using regional grid intensity from Electricity Maps, and add embodied manufacturing emissions and water use. Architectural choices turned out to change energy use by orders of magnitude, and deployment region could amplify or cancel those differences. This is the paper my supervisor pointed me to for the measurement side of GreenCode.

**What is complex in this project:** Attribution. Separating a query's energy from everything else running on the machine, correlating RAPL samples with query start and end times, and then extending the figure with embodied carbon (chip die area, fab yield, DRAM per GB) and water footprints per energy source all require assumptions from secondary literature. Running the full 300 GB TPC-H workload against four engines with different storage models and configurations on one server is itself a substantial engineering effort.

**What technical architecture was used:** A 16-thread Xeon E5-2637 v4 server with 512 GB RAM. EcoQuery wraps TPC-H queries with RAPL sampling for CPU and DRAM, collects I/O and resource statistics, and stores them with timestamps. ATLAS then applies the Software Carbon Intensity formula (operational energy × grid intensity, plus embodied emissions amortised per unit of work), regional carbon and water coefficients, and a break-even analysis of when operational savings outweigh manufacturing costs.

**Key strengths and weaknesses:** The measurement approach is exactly what GreenCode needs and it validated my design: RAPL for energy, a published grid factor for CO₂e, and a clear separation of measured from modelled quantities. Treating region as a variable is a strong idea I can borrow for the carbon-factor table. The weaknesses are mostly scope. The study compares *engines*, not *changes to a query*, so it cannot say whether a rewrite helped. It runs on server hardware with full powercap access, which is not the situation of a student laptop. Embodied-carbon and water figures come from vendor and literature estimates and inherit their uncertainty, and I did not find statistical tests behind the comparisons. GreenCode narrows the question (one query or function, original versus candidate, on known hardware) and adds correctness verification and significance testing, while reusing this paper's energy-to-carbon chain.
