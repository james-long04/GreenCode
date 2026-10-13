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
- Windows is a supported dev platform (the sandbox falls back to timeout plus worker hardening).

## Frontend design skills (`.claude/skills/`)

Any work in `frontend/` (the React + TypeScript dashboard) should use the design skills in this
repo. See `docs/design-skills.md` for what each one does. Default workflow:

1. **`impeccable`**: shape, critique, audit, polish and harden UI. Start here for layout,
   typography, colour, hierarchy and empty/error states.
2. **`nielsen-heuristics-audit`**: usability review against Nielsen's 10 heuristics. Run it on
   each page (Overview, Analyse, Optimisation, Experiments, Rules) before calling a UI change done.
3. **`emil-design-eng`**, **`animate`**, **`review-animations`**: motion and interaction polish.
   Dashboards are used repeatedly, so default to little or no animation.
4. **`taste-skill`** and **`redesign-skill`**: avoid generic "AI-looking" UI; use for redesigns.
   `minimalist-skill`, `soft-skill` and `brutalist-skill` are alternative aesthetic directions.
   Pick at most one per task, since they contradict each other.
5. **`output-skill`**: use when a task needs complete files rather than abbreviated output.

Dashboard constraints that override skill defaults: charts stay dependency-free SVG, routing stays
hash-based, evidence values (speed-up, energy, CO2e, p-values) must remain readable and exact,
and light and dark themes must both work. Check accessibility (contrast, focus, keyboard) on
every change, since this is a research tool people read closely.
