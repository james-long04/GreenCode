---
title: Background
created: 2026-10-22
project: GreenCode
type: report-section
tags: [writing, background]
---

# Background (and References)

## Brief
Approx 300 words; what is the background, similar solutions/research, research guiding feasibility; IEEE referencing; top-quality academic refs incl. Irish university theses; first-person, humanised, high-level style; ~20 references explored.

## Final text
GreenCode sits at the meeting point of two research conversations that have, until recently, run in parallel. The first is green software engineering. Pinto and Castor [1] argued in 2017 that energy was a concern application developers could no longer leave to hardware, and Lee et al. [2] have since mapped how that concern cuts across the whole lifecycle. Empirical work has shown that implementation choices matter: Pereira et al. [3] ranked languages by energy use, and Connolly Bree's UCD doctoral thesis [4] found that refactoring object-oriented design reduced energy consumption by between 5% and 66% in open-source systems. Measuring that energy honestly is its own problem. Khan et al. [5] characterised the behaviour of Intel's RAPL counters, Lannelongue et al. [6] provided the coefficient model I fall back on when counters are unavailable, and the Green Software Foundation's SCI specification [7] gives me a standard vocabulary for carbon intensity.

The second conversation concerns large language models as code optimisers. Since Codex [8], benchmarks such as EffiBench [9] and Mercury [10] have shown that correctness and efficiency are different targets, while Shypula et al. [11] demonstrated that models can learn performance-improving edits. The energy question is newer and the findings are sobering: Cursaru et al. [12], Vartziotis et al. [13], Solovyeva et al. [14], Islam et al. [15] and Apsan et al. [16] all report that LLM-generated Python is usually correct yet typically less energy-efficient than human code, and Peng et al. [17] found LLM optimisation helped only half their test programs. Romero Rosas et al. [18] add that models sometimes produce incorrect transformations, which is why I treat verification as non-negotiable.

What I have not found is work that guides the model with deterministic static analysis and then measures the result. Abtahi and Azim [19] pair static analysis with LLMs for code quality, and LLM-R2 [20] uses an LLM to select SQL rewrite rules, but neither closes the loop with energy evidence. Methodologically, I lean on Georges et al. [21] and Mytkowicz et al. [22] for statistically rigorous benchmarking, and on Ferreira's TU Dublin dissertation [23], which showed how much the test environment alone can shift benchmark results. Yadav et al. [24], writing from an Irish practitioner perspective, capture the accountability concerns that GreenCode's evidence-first design is meant to answer.

## Added paragraph on the energy-measurement references [27]–[31]
Add this after the sentence ending "...a standard vocabulary for carbon intensity." at the end of the first paragraph:

> Bachras and Jacobsen [27] show the full chain in practice for database workloads, reading CPU and DRAM energy from RAPL during each query and converting it to CO₂e with regional grid factors, which is the approach GreenCode follows for its SQL cases. Reading those counters is a practical question in its own right: Intel's Performance Counter Monitor [28] and its plotting companion [29] expose them on Linux but need a self-built driver on Windows, CodeCarbon [30] reads them natively only on Linux, and LibreHardwareMonitor [31] supplies a signed Windows driver, which is why it is the reader I use on my laptop.

Two small fixes to your existing text while you're in there: "Firstly is green software engineering" reads better as "The first is green software engineering", and the thesis author's name is **Connolly Bree** (surname), so "Connolly Bree's UCD doctoral thesis".

## Notes to check before submission
Three things to check before you submit. The UCD thesis [4] was under embargo until May 2026, so confirm the PDF opens for you. References [8], [9], [11]–[18] and [20] are arXiv preprints; several have since appeared at venues (for example [16] has an ACM DOI), so a quick search for each will let you cite the published version where one exists. I verified [4], [14]–[17], [20], [23] and [24] against their repository pages today; the rest are well-known papers whose details I am confident of but have not re-fetched.

References: [[05 Writing/References (IEEE)]]
