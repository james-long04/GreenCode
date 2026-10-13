# Product

## What it is

GreenCode is a research instrument for a final-year project (BSc Computer Science, TU Dublin). It
detects inefficient Python and SQL with static analysis, asks a local LLM to optimise it, verifies
the result, and benchmarks original against candidate for runtime, CPU, memory, energy and CO2e.
The dashboard is how the author runs the experiment and reads the evidence.

Tagline: "Don't just optimise. Prove the impact."

## Users

- **Primary:** the author, running the three-condition experiment (Baseline, AI-only, GreenCode)
  and writing the dissertation from the results. Technical, patient, reads numbers closely.
- **Secondary:** a supervisor or examiner opening the dashboard to check that the evidence is real:
  what was measured versus estimated, the sample sizes, the statistics, the hypotheses.

## Mode

**Operate.** Scanability, honesty about uncertainty and consistency outrank expression. The brand
lives in precise details (exact figures, measured/estimated labels), not decoration.

## Principles

1. Evidence over decoration. Every number says where it came from and whether it was measured.
2. Never overstate. A hypothesis is "supported so far" or "not supported yet", never "proven".
3. The comparison is the point: AI-only and GreenCode always sit side by side, same scale.
4. Say what is happening. Long-running steps show their stage; failures say what to do next.
5. Calm and dense. Light by default (read at a desk, in daylight), dark available.

## Constraints

- Dependency-free SVG charts, hash routing, no UI framework.
- Self-hosted fonts (Geist, Geist Mono). Icons from Phosphor (inlined).
- Light and dark themes, WCAG AA contrast, full keyboard operation, reduced-motion respected.
- Assumptions made without an interview: audience, mode and principles above were inferred from
  the project proposal and the existing dashboard.
