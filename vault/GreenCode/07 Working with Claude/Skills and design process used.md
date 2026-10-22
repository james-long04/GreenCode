---
title: Skills and design process used
created: 2026-10-22
project: GreenCode
tags: [claude, skills]
---

# Skills and design process used

Skills are packaged instruction sets Claude follows for a kind of task. Those used on GreenCode:

| Skill | Used for |
|---|---|
| `frontend-design` | the dashboard redesign and the admin panel — intentional typography, OKLCH tokens, no template look |
| `dataviz` | the SVG charts (paired bars, samples plot, condition bars), palette validated for light/dark |
| `design:accessibility-review`, `anthropic-skills:nielsen-heuristics-audit` | the UI audit recorded in `docs/ui-audit.md` |
| `anthropic-skills:docx` | the Word code walkthrough |
| `anthropic-skills:xlsx` | the Excel Gantt |
| Mermaid / mermaid-cli | flowchart, use case, class diagrams |
| `pbakaus/impeccable` plugin (marketplace) | added at James's request for frontend polish |

Design process followed for the UI: tokens first (colour, spacing, type scale, both themes) → layout primitives → components → pages → audit (keyboard, screen reader, contrast, heuristics) → fixes (mobile overflow, sr-only overflow, table nowrap).

Writing process for the report: James supplies the brief/hints → first-person, humanised, Masters/PhD register → IEEE numeric citations → iterate ("shorten", "humanise", "rephrase this bit").
