---
title: Troubleshooting
created: 2026-10-22
project: GreenCode
tags: [ops, troubleshooting]
---

# Troubleshooting (things that actually happened)

| Symptom | Cause | Fix |
|---|---|---|
| `git pull`: "untracked working tree files would be overwritten" | files had been copied straight to disk that were also committed | `git clean -f <dir>` then `git pull` (rule since then: repo files only arrive via git) |
| git errors in the wrong folder | ran commands from `$HOME` | `cd $HOME\GreenCode-app` first |
| `test_implicit_cross_join` failing | sqlglot 30 renamed `from` → `from_` | `s.args.get("from") or s.args.get("from_")` |
| `test_sandbox_timeout_and_memory_limit` failing | no rlimits on Windows, 32 GB RAM | memory assertion skipped when `os.name == "nt"` |
| `energy_joules_net` = 0.000 | LHM refresh lag; mean idle too high | refresh-aware integration + 3 s tail; idle = min reading |
| `peak_rss_mb` = 0 | psutil blocked by `_harden()` and `-I` ignores user-site | import psutil before harden; pass `GREENCODE_PSUTIL_DIR` |
| Sidebar says **Energy: estimate** | LHM not running / web server off / not Administrator | start LHM as Admin, Options → Remote Web Server → Run |
| Admin page 401 | token missing/wrong | token from `backend\.env` (`GREENCODE_ADMIN_TOKEN`) or server log |
| Intel PCM on Windows | needs self-compiled, test-signed driver | use LibreHardwareMonitor instead |
| Reference PDFs 403 (Arrow, Wiley) | publisher blocks scripts | save manually; arXiv mirror for Wiley paper (2007.07610); Georges at dri.es |
| Model returns prose / no fence | output contract violated | recorded as `parse_error` (a result, not a bug) |
| SQL optimisation `failed` with "relation does not exist" | query not against bench schema | see [[03 Rules and cases/What SQL can be run]] |
