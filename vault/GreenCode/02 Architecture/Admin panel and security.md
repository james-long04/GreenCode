---
title: Admin panel and security
created: 2026-10-22
project: GreenCode
tags: [architecture, admin, security]
---

# Admin panel and security

- Every `/api/admin/*` route depends on `require_admin`: `secrets.compare_digest(header, effective_admin_token())` (constant-time).
- **Always required.** If `GREENCODE_ADMIN_TOKEN` is unset a random token is generated per process and printed in the server log (`admin_token_is_generated()` tells the UI). James's token is set in `backend\.env`.
- Frontend stores it in localStorage `greencode.adminToken`, sends it only for `/admin` paths; `TokenForm` appears on 401; **Lock** clears it.

## Sections (`AdminPage.tsx`)
| Section | Does |
|---|---|
| System | counts per table, host/Python/Ollama status, energy availability, token source |
| Settings | runtime overrides of `RUNTIME_ADJUSTABLE` (process-only; every run records what it used) |
| Models | list Ollama models, pull new (background thread with progress) |
| Carbon factors | CRUD; factors referenced by evidence are locked (409) |
| Maintenance | mark stuck runs failed; delete orphan analyses; delete failed/rejected runs per project. Benchmarked evidence never deleted |
| Server log | ring buffer (`logbuffer.py`), level filter |
| Export | `results.csv` |

Why: the GitHub repo is public; the design means reading the code gives nobody access to the running instance.
