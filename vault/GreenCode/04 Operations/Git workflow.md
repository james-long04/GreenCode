---
title: Git workflow
created: 2026-10-22
project: GreenCode
tags: [ops, git]
---

# Git workflow

- Remote: https://github.com/james-long04/GreenCode (public) · branch `main` · local clone `C:\Users\james\GreenCode-app`.
- Claude commits and pushes from its own clone; James runs `git pull`. **Nothing is copied straight onto the laptop's disk if it is also committed** (it causes pull conflicts).
- `.env`, `docs/references/pdfs/`, `node_modules`, `__pycache__` are git-ignored.
- Every AI-generated commit ends with a `Co-Authored-By: Claude …` line (AI-use declaration).
- Commit style: `area: what changed` (e.g. `frontend: open .py/.sql/.ipynb files…`).
