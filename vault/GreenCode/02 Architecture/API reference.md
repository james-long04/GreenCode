---
title: API reference
created: 2026-10-22
project: GreenCode
tags: [architecture, api]
---

# API reference (`/api`, docs at http://localhost:8000/docs)

| Endpoint | Purpose |
|---|---|
| `GET /health` | DB reachability, Ollama status, energy `{selected, lhm, codecarbon}`, key settings |
| `GET /rules` · `GET /carbon-factors` | Rule catalogue, grid factors |
| `GET/POST /projects`, `GET/DELETE /projects/{id}` | Projects (delete cascades) |
| `GET/POST /analyses`, `GET /analyses/{id}`, `/findings`, `/optimisations` | Analyse pasted source; read back |
| `POST /optimisations` (202), `GET /optimisations`, `GET /optimisations/{id}`, `POST …/rerun` | Start, list, poll, resume the pipeline |
| `GET /suite/cases`, `POST /suite/run` (202), `GET /suite/jobs`, `GET /suite/jobs/{id}` | Benchmark suite runs |
| `GET /results`, `GET /results/summary` | Evidence rows; per-condition summary + H1–H4 |

## Admin (`/api/admin`, header `X-Admin-Token`)
`GET /overview` · `GET/PUT/DELETE /settings` · `GET /models`, `POST /models/pull` · `POST/PUT/DELETE /carbon-factors` · `POST /maintenance/mark-stuck-failed` · `DELETE /maintenance/orphan-analyses` · `DELETE /maintenance/project-runs/{id}?status=failed|rejected` · `GET /export/results.csv` · `GET /logs`

See [[02 Architecture/Admin panel and security]]
