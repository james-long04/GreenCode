---
title: CLAUDE.md instructions
created: 2026-10-22
project: GreenCode
tags: [claude, instructions]
---

# `CLAUDE.md` (verbatim, repo root)

```markdown
# GreenCode: guidance for Claude Code

GreenCode is a final-year project (BSc Computer Science, TU Dublin): static-analysis-guided AI
optimisation of Python and SQL, with measured runtime/energy/CO2e evidence. Read `README.md`,
`docs/methodology.md` and `docs/architecture.md` before changing behaviour.

## Ground rules

- The experiment is a controlled comparison (Baseline vs AI-only vs GreenCode). The AI-only and
  GreenCode prompts must stay identical except for the findings block (`backend/app/ai/prompts.py`).
  Do not change one without the other.
- Every measurement is tagged `measured` or `estimated`. Never present an estimate as a measurement.
- Run `cd backend && pytest` after backend changes (integration tests skip without PostgreSQL).
- Secrets (API keys) come from environment variables only. Never commit `.env`.
- The project runs natively on Windows (no Docker, no Linux-only code paths). The sandbox relies on
  a timeout, an empty environment and worker-side hardening.

## Frontend

The dashboard (`frontend/`, React + TypeScript + Vite) uses its own design tokens in
`src/styles.css` and dependency-free SVG charts. Keep light and dark themes working, keep
evidence values exact, and check keyboard and screen-reader behaviour on every change.
`docs/ui-audit.md` records the usability review.
```
