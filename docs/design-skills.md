# Design skills used on the dashboard

The `frontend/` dashboard was built with AI assistance, and the design work is guided by a set of
third-party Claude skills stored in `.claude/skills/`. Claude Code picks them up automatically when
you open this repo (in the terminal or the VS Code extension).

## What is included

| Skill (folder) | Source | Licence | Use it for |
| --- | --- | --- | --- |
| `impeccable` | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | Apache-2.0 | Designing, critiquing, auditing and polishing UI: hierarchy, type, colour, layout, UX copy, accessibility, responsiveness |
| `nielsen-heuristics-audit` | [mastepanoski/claude-skills](https://github.com/mastepanoski/claude-skills) | MIT | Usability review against Nielsen's 10 heuristics |
| `emil-design-eng` | [emilkowalski/skills](https://github.com/emilkowalski/skills) | MIT | UI polish and interaction philosophy (easing, timing, springs, details that compound) |
| `animate` | emilkowalski/skills | MIT | Building an animation from scratch, starting with whether it should animate at all |
| `review-animations` | emilkowalski/skills | MIT | Strict motion review with a Block/Approve verdict |
| `taste-skill` (`design-taste-frontend`) | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | MIT | Avoiding generic AI-looking UI |
| `redesign-skill` | Leonxlnx/taste-skill | MIT | Upgrading an existing UI without rewriting it |
| `output-skill` | Leonxlnx/taste-skill | MIT | Forcing complete, non-truncated output |
| `minimalist-skill`, `soft-skill`, `brutalist-skill` | Leonxlnx/taste-skill | MIT | Alternative aesthetic directions. Pick one per task; they contradict each other |

Licence texts are in `.claude/skills/_licenses/` and `.claude/skills/impeccable/LICENSE`. The skills
are unmodified copies of the upstream files. They are development tooling and are not part of the
runtime application or the experiment.

## Recommended workflow for a UI change

1. `impeccable` (shape, then critique) to decide what the page should do and how it reads.
2. Implement the change, keeping the constraints in `CLAUDE.md` (SVG charts, hash routing,
   exact evidence values, light and dark themes).
3. `nielsen-heuristics-audit` on the changed page, then `impeccable` audit/polish.
4. Motion only if it earns its place: `emil-design-eng`, then `review-animations`. This is a
   repeatedly used research dashboard, so the default is little or no animation.

## Dissertation note

If you use these skills while developing or evaluating the interface, say so in the AI-assistance
declaration and cite the sources above. The usability review should be recorded as evidence
(heuristic, finding, severity, change made) rather than described from memory.

## Updating

The skills are copied, not linked. To update one, replace its folder from the upstream repository
and re-check the licence. Impeccable can also be installed as a plugin with
`/plugin marketplace add pbakaus/impeccable` inside Claude Code if you prefer upstream updates.
