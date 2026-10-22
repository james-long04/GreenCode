---
title: Appendix A — Abtahi and Azim
created: 2026-10-22
project: GreenCode
type: report-section
tags: [writing, appendix]
---

# Appendix A: First Similar Piece of Work Review — Abtahi & Azim [19]

S. M. Abtahi and A. Azim, "Augmenting large language models with static code analysis for automated code quality improvements," *Proc. IEEE/ACM FORGE*, 2025, pp. 82–92, doi: 10.1109/FORGE66646.2025.00017.

How the Background positions it: "Abtahi and Azim [19] pair static analysis with LLMs for code quality … but neither closes the loop with energy evidence."

## Final text (shortened version)
**Appendix A: First Similar Piece of Work Review**

**Title:** Augmenting Large Language Models with Static Code Analysis for Automated Code Quality Improvements [19]

**Author:** S. M. Abtahi and A. Azim, Ontario Tech University, FORGE 2025

**Description (brief):** The authors ran SonarQube over an industrial codebase, which flagged 7,599 bugs, vulnerabilities and code smells, then fed each finding to an LLM to rewrite the offending code. GPT-3.5 Turbo made a first pass, the code was re-scanned, and GPT-4o handled what remained. The pipeline cleared every bug and vulnerability and about 81% of code smells for under $35 in API costs. It is the closest precedent to GreenCode: a static analyser tells the model exactly what is wrong instead of asking it to "improve" code in general.

**What is complex in this project:** Keeping the model honest. Prompts needed over twenty iterations and few-shot examples per issue type before rewrites stayed on task, and the authors built a diff tool to catch hallucinated edits and route them to manual review. Chaining two models with a re-scan between passes, and choosing between one prompt per issue type or one for everything, added further engineering.

**What technical architecture was used:** A linear pipeline: SonarQube scan → issue extraction → per-file prompt with few-shot examples → optional retrieval of fixes from GitHub, SonarQube Community and Stack Overflow → GPT-3.5 Turbo revision → re-scan → GPT-4o revision → diff-based hallucination check with human sign-off. Evaluation was by counting issues remaining after a re-scan, plus a manual sample of 30 issues per category.

**Key strengths and weaknesses:** The core idea is right, and the results show how much a located, specific finding helps a model (GPT-4o fixed 30/30 sampled issues). The work is on a real codebase and the costs are reported honestly. But the project had no test suite, so fixes were never executed; "success" means SonarQube stopped complaining, not that the code still works. Nothing is measured about speed or energy, so a fix that made the code slower would still count. There is one codebase, one LLM vendor, a dependency on a paid API whose model can change mid-experiment, and one internal arithmetic inconsistency in the reported totals. GreenCode keeps the static-analysis-first design but adds what is missing: executed correctness tests, benchmarking and energy measurement, a locally hosted fixed-version model, and an AI-only control condition so the benefit of the findings is measured rather than assumed.
