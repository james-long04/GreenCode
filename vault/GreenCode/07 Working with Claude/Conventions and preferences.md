---
title: Conventions and preferences
created: 2026-10-22
project: GreenCode
tags: [claude, conventions]
---

# Conventions and preferences (James)

- Commands are given as **PowerShell**, with `cd $HOME\GreenCode-app\…` first.
- Repo files arrive by **git push + git pull**, never by direct copy to disk.
- Writing style: first person, humanised, academic (Masters/PhD level), IEEE references `[n]`, Irish theses included in the background.
- Keep it short when asked ("make this much shorter"); no timelines in the Conclusion.
- Admin token: `GREENCODE_ADMIN_TOKEN` in `backend\.env` (value kept out of the repo).
- Windows only; no Docker/Linux-only paths.
- Every answer about measurements must keep measured vs estimated distinct.
- Zotero: no connector — deliver BibTeX files + a PDF-download script instead.
