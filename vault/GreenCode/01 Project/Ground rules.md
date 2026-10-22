---
title: Ground rules
created: 2026-10-22
project: GreenCode
tags: [project, rules]
---

# Ground rules (from `CLAUDE.md`)

These are the non-negotiables written into the repo for anyone (human or AI) changing it.

1. **The experiment is a controlled comparison.** The AI-only and GreenCode prompts in `backend/app/ai/prompts.py` must stay identical except for the findings block. Never change one without the other. `tests/test_ai.py` checks this.
2. **Every measurement is tagged** `measured`, `derived` or `estimated`. Never present an estimate as a measurement. The dashboard badges exist for this.
3. **Run `cd backend && python -m pytest` after backend changes.** Integration tests skip without PostgreSQL.
4. **Secrets come from environment variables only.** Never commit `.env`. The admin token lives in `backend/.env` (`GREENCODE_ADMIN_TOKEN`).
5. **Windows-native.** No Docker, no Linux-only code paths. The sandbox relies on a timeout, an empty environment and worker-side hardening — not OS resource limits.

## Frontend rules
- Design tokens live in `src/styles.css`; keep light **and** dark themes working.
- Evidence values are shown exactly as stored; format for display only.
- Check keyboard and screen-reader behaviour on every change; `docs/ui-audit.md` records the review.

Related: [[07 Working with Claude/CLAUDE.md instructions]]
