---
title: Proposed Approach
created: 2026-10-22
project: GreenCode
type: report-section
tags: [writing, approach]
---

# Proposed Approach

## Brief
Approx 500 words. Five areas: Research · Requirements Gathering (User Group) · Analysis and Design · Implementation · Testing / Evaluation.

## Final text (≈520 words)
I am managing GreenCode as a phased, iterative project in which each phase produces something I can test and document before the next begins, so that I never arrive at the end with a large system that has not been evaluated. Five areas structure the work.

**Research.** The literature review will establish the gap I identified in the background: nobody has yet guided an LLM with deterministic static analysis and then measured the energy outcome. I will keep reading in two streams, green software measurement [1], [5], [6] and LLM code optimisation [12]–[18], and I will use Wohlin et al.'s guidance on experimentation in software engineering [25] to frame the hypotheses so that each can be supported or rejected by a named statistical test. Research continues throughout, because implementation decisions such as the energy method or the benchmark statistics need to be defensible against the literature.

**Requirements gathering.** My user group has two parts. The primary users are developers and computing students who want to know whether an AI-suggested optimisation is safe to accept; the secondary users are my supervisor and examiners, who need to audit the evidence trail. I will gather requirements from three sources: the research question itself, which fixes the functional core (detect, generate, verify, benchmark, measure); the usability literature, since Nielsen's heuristics [26] give me a checklist for how evidence should be presented; and short structured feedback sessions with a handful of classmates using the prototype, recorded as a requirements log. I will separate must-have requirements that serve the hypotheses from should-have ones that improve the dashboard.

**Analysis and design.** The architecture is a FastAPI backend, a PostgreSQL evidence store and a React dashboard. The central design decision is that the two experimental conditions share one prompt that differs only by the findings block, so the comparison isolates the effect of static analysis. I will design the rule catalogue (Python AST and SQL via sqlglot and EXPLAIN) as a fixed, versioned set, the database schema so that every measurement records its method and carbon factor, and the sandbox so that generated code is treated as untrusted. Design artefacts will include the schema, the pipeline sequence and the benchmark-case format.

**Implementation.** I will build the core pipeline before any optional feature, in the order analysis, AI integration, verification, benchmarking, energy and dashboard, committing to Git with a documented history. Where energy counters are unavailable I will fall back to a published coefficient model [6] and label the result as estimated, never as measured. The dashboard will be built against a written design brief and audited against Nielsen's heuristics before I call it finished.

**Testing and evaluation.** Unit and integration tests (pytest) will cover each rule, the verifier and the statistics. The evaluation is the research contribution: a controlled suite of 30–50 Python and SQL cases, run under the AI-only and GreenCode conditions with randomised order, warm-up runs and repeated timings, following Georges et al. [21]. H1 will be tested with Fisher's exact test, H2 and H3 with paired Wilcoxon tests on log ratios, and H4 by examining the divergence between time and energy changes. I will analyse failed optimisations as carefully as successful ones, report threats to validity, and release the code and data so the experiment can be reproduced.
