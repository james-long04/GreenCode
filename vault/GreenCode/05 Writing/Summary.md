---
title: Summary
created: 2026-10-22
project: GreenCode
type: report-section
tags: [writing, summary]
---

# Summary

## Brief
```
Summary
Hints:
Approx 200 words

What is the project idea?
Why is it useful/unique?
What does it offer (eg. To the user)
How will it operate?
Why is this a good idea and what will the end deliverable be?

reference masters and phd level writing styles online to answer this question
```
Plus: mention the research question and hypotheses; add ethics / AI accountability to the last paragraph; include a sentence on what it offers the user.

## Final text (≈285 words; trim options noted below)
GreenCode investigates whether static analysis can make AI code optimisation trustworthy. Large language models readily rewrite Python and SQL for efficiency, but their output is unverified and unmeasured: a candidate may be incorrect, slower, or faster without consuming less energy. The project addresses the research question: *to what extent does static-analysis guidance improve the correctness, performance and energy efficiency of locally generated AI optimisations for Python code and SQL queries?*

The system detects inefficiency patterns from a fixed rule catalogue, supplies these structured findings to a locally hosted model (Ollama, qwen2.5-coder:7b), verifies each candidate in a sandbox against correctness tests, benchmarks it with repeated timings and non-parametric statistics, and records energy and CO₂e, labelling every value as measured or estimated. For a developer, this means every suggested optimisation arrives with a correctness verdict, a measured speed-up with confidence intervals, and an energy and CO₂e estimate, so the change can be accepted or rejected on evidence rather than trust. A controlled benchmark suite is run under two conditions, AI-only and analysis-guided, with the original code as baseline.

Four hypotheses are tested: that guidance yields a higher proportion of correct optimisations (H1), greater execution-time improvements (H2) and greater energy-efficiency improvements (H3), and that time reductions do not always translate into equivalent energy reductions (H4). The deliverables are an open-source pipeline and dashboard presenting this evidence transparently, and a dissertation reporting the findings, including failed optimisations and threats to validity. The work also engages with AI accountability: by requiring every model-generated change to be verified, measured and traceable to a documented assumption, GreenCode treats the model as a proposer rather than an authority, and the dissertation examines what level of evidence should be expected before AI-produced code is accepted.

> [!tip] If the 200-word limit is strict
> Drop the H1–H4 listing to "Four hypotheses compare the two conditions on correctness, execution time, energy efficiency, and the relationship between time and energy savings", and shorten the ethics sentence to its first clause.
