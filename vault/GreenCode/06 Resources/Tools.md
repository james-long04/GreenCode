---
title: Tools
created: 2026-10-22
project: GreenCode
tags: [resources, tools]
---

# Tools

| Tool | Used for | Notes |
|---|---|---|
| PostgreSQL 18 (native Windows) | evidence store + bench dataset | role/db `greencode` |
| Ollama + `qwen2.5-coder:7b` | local model | http://localhost:11434 |
| LibreHardwareMonitor | RAPL package power over HTTP | run as Admin; Remote Web Server on 8085 |
| CodeCarbon | fallback energy | TDP-based on Windows |
| psutil | CPU time, peak working set | imported inside the sandbox worker |
| sqlglot 30.22 | SQL parsing | `from_` key rename |
| SciPy | Mann–Whitney, Wilcoxon, Fisher, t | optional, graceful fallback |
| Vite / React 19 / TypeScript | dashboard | no UI framework |
| pytest | 110 tests | mock provider |
| Zotero | reference manager | all 31 refs with full text; BibTeX in `docs/references/` |
| Excel / Word | Gantt, report | `docs/plan`, `docs/*.docx` |
| Mermaid CLI | diagrams | `.mmd` sources |
| Intel PCM / pcm-graph | considered, rejected | needs test-signed driver on Windows |
