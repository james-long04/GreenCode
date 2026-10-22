---
title: Frontend
created: 2026-10-22
project: GreenCode
tags: [architecture, frontend]
---

# Frontend (`frontend/src`)

Vite + React 19 + TypeScript; **no runtime deps beyond React** — hand-written SVG charts, hash routing, one CSS file with OKLCH design tokens (light + dark).

| File | Role |
|---|---|
| `main.tsx` | mounts `<App/>` |
| `App.tsx` | shell: sidebar `NAV` (Overview, Projects, Analyse, Experiments, Rules & assumptions, Admin), status strip from `/api/health` (**Energy: lhm/codecarbon/estimate**), theme toggle, route switch |
| `hooks.ts` | `useHashRoute`, `useAsync(fn, deps, intervalMs)` (polling), `useLocalStorage`, `useTheme`, `useDocumentTitle` |
| `api.ts` | typed client `api.*`, `api.admin.*`; `X-Admin-Token` only on `/admin` |
| `types.ts` | mirrors of `schemas.py` |
| `components/ui.tsx` | `PageHeader, Section, Badge, Metric, Alert, ErrorBox, Empty, LoadingBlock, TableWrap, Term` (GLOSSARY tooltips), `fmt` |
| `components/charts.tsx` | `PairedBars, SamplesPlot, ConditionBars, Legend` |
| `components/code.tsx` | `diffLines`, `CodeBlock` |
| `components/icons.tsx` | inline SVG icon set |
| `styles.css` | tokens, layout (`.stack`, `.panel`, `.settings-grid`, `.subnav`), tables, badges, focus rings, `.btn-file`, `textarea.drop-target` |

## Pages
- **Overview** — counts + per-condition summary + H1–H4.
- **Projects** — create/open/delete; lists analyses (polls every 8 s).
- **Analyse** — paste or **Open file… / drag-drop** `.py .sql .ipynb` (notebooks flattened to code cells, `%`/`!` lines dropped); language from extension; Python needs the spec (entry point, tests, benchmark); run analysis → findings → launch AI-only / GreenCode.
- **Optimisation** — status timeline, prompt/raw response, diff, tests, paired bars, samples plot, energy with `wattsNote()` and method badges.
- **Experiments** — pick cases/conditions, run suite, progress, aggregated results.
- **Rules & assumptions** — rule catalogue, carbon factors, energy note.
- **Admin** — see [[02 Architecture/Admin panel and security]].

## Conventions
Exact evidence values (format only for display); every colour a token with light/dark value; keyboard + screen-reader checked; `docs/ui-audit.md` (Nielsen heuristics).

![[_assets/usecase.png]]
