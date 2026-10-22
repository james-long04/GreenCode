---
title: Ethics and AI accountability
created: 2026-10-22
project: GreenCode
tags: [project, ethics]
---

# Ethics and AI accountability

- **No human participants, no personal data.** All benchmark data is synthetic (`database/seed/bench_dataset.sql` generates it; emails are `userN@…`).
- **AI-generated code is never trusted on its own.** Every candidate is verified against the original on every test before it is measured; failures are recorded and reported as results.
- **Measurements are labelled.** `measured | derived | estimated` on every row, badges on the dashboard, never mixed silently.
- **Transparency.** Prompt, raw model response, settings and environment snapshot are stored with every optimisation, so any figure can be traced back.
- **Sandboxing.** Candidate code runs in a separate hardened process with no network, no subprocesses and no file writes; the README states plainly that this is defence in depth, not a security boundary.
- **Declaration of AI assistance.** The codebase was generated with Claude (Anthropic) under the author's direction, declared in line with TU Dublin's policy on AI use; every AI-generated commit carries a co-author line. See [[07 Working with Claude/_Claude MOC]].
- **Environmental honesty.** The point of the project is to measure rather than assume; the H4 analysis exists precisely to check whether "faster" means "greener".
