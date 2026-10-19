# UI design pass: audit

Applied using Nielsen's ten usability heuristics, Impeccable's craft checklist (restrained colour, scanability, one container level) and Emil Kowalski's motion rules.
Severity uses Nielsen's 0–4 scale.

| # | Heuristic | Problem in the old UI | Sev | Fix |
|---|-----------|-----------------------|-----|-----|
| 1 | Visibility of system status | Pipeline progress was a text line; loading was the word "Loading…" | 3 | Pipeline stepper with state, plain-language verdict sentence, skeleton loaders, polling retained |
| 2 | Match with real world | Raw status strings, `ai_only`, jargon (geomean, Cliff's δ) unexplained | 3 | Plain labels via `fmt.label`, glossary `Term` tooltips for statistics and energy terms |
| 3 | User control and freedom | `window.confirm` for project delete | 2 | Inline confirm with Keep/Delete, no blocking dialog |
| 4 | Consistency | Mixed card styles, nested cards, three badge palettes | 2 | One `panel` level, shared tokens, severity colours fixed (high = bad) |
| 5 | Error prevention | Run buttons enabled without a project | 3 | Disabled with an explanatory alert; JSON spec validated before submit |
| 6 | Recognition over recall | Original and candidate code shown as two unmarked blocks | 3 | LCS line diff with +/− marks (also announced to screen readers) |
| 7 | Flexibility | No keyboard shortcut for analyse | 1 | Ctrl+Enter on the analyse form |
| 8 | Aesthetic and minimal | Four stat cards, coloured side borders, decoration | 2 | Flat metric strip, restrained colour, no gradients or eyebrows |
| 9 | Error recovery | Errors without a remedy | 3 | `ErrorBox` explains how to start the API and offers Try again |
| 10 | Help | Hypotheses and units unexplained | 2 | Hypothesis list with thresholds, Getting started panel on Overview |

## Accessibility and craft
- Light default, dark via `prefers-color-scheme` or the toggle; no flash on load.
- Skip link, `aria-current` navigation, visible focus rings, table rows use a real link (no clickable `tr`).
- Charts are `role="img"` with a text summary and direct value labels (no colour-only encoding).
- Motion: short ease-out transitions only, no animation on keyboard actions, `prefers-reduced-motion` respected.
- Mobile: single column, wrapped nav, wide tables scroll inside a focusable region (verified at 390 px).

## Impeccable detector
One finding, accepted: `overused-font` (Geist). Kept deliberately: it is self-hosted (OFL), has a matching mono face with tabular figures, and suits a dense data tool. Revisit if you want a more distinctive identity.

## Not done
- Automated visual regression tests; screenshots were checked by hand against a mock API.
- Real `npm run build` was not run in the authoring environment (no registry access); bundling was verified with esbuild. No dependencies were added.

## Admin page (added after the first pass)

Built with the same skills. Decisions worth recording:

| Heuristic | Decision |
|-----------|----------|
| Visibility of status | Metric strip plus Pipeline/Host panels; stuck-run alert links straight to the fix; model pulls show a progress bar and keep running off-page. |
| Match with real world | Setting keys are shown verbatim (they are the env-var names) with a plain-language line under each. |
| User control | Every destructive action is an inline confirm; settings form has Discard; overrides can be cleared in one click. |
| Error prevention | Apply is disabled until something changed; numbers use number inputs; backend refuses to edit or delete a carbon factor that evidence references (409) and the UI explains why. |
| Consistency | Same panel, table, badge and alert components as the rest of the dashboard; sub-navigation reuses the quiet link style. |
| Minimalism | Fixed settings are behind a disclosure; only runtime-adjustable keys are in the form. |
| Help | The token form says exactly which variable it matches and where a generated token is printed; a notice flags when the token is temporary. |
| Security | The admin API is never open: a token is always required (configured or generated per process). It lives in localStorage of that browser only, is sent solely to `/api/admin/*`, and a Lock button clears it. |
