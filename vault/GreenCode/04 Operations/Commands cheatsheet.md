---
title: Commands cheatsheet
created: 2026-10-22
project: GreenCode
tags: [ops, commands]
---

# Commands cheatsheet (PowerShell)

## Start everything
```powershell
# window 1
cd $HOME\GreenCode-app\backend
python -m uvicorn app.main:app --reload --port 8000

# window 2
cd $HOME\GreenCode-app\frontend
npm run dev            # http://localhost:5173
```
Plus LibreHardwareMonitor (Administrator, Remote Web Server running). Check the sidebar says **Energy: lhm**.

## Update from GitHub
```powershell
cd $HOME\GreenCode-app
git pull
```
If pull complains about untracked files: `git clean -f <path>` then `git pull` again ([[04 Operations/Troubleshooting]]).

## Tests
```powershell
cd $HOME\GreenCode-app\backend
python -m pytest
```

## Run the suite / export
```powershell
cd $HOME\GreenCode-app\backend
python scripts\run_suite.py --project "Experiment 1"
python scripts\export_results.py --out results.csv
```

## Freeze dependencies (recommended, once)
```powershell
cd $HOME\GreenCode-app\backend
pip freeze > requirements-lock.txt
git add requirements-lock.txt; git commit -m "lock deps"; git push
```

## Useful URLs
- Dashboard http://localhost:5173 · API docs http://localhost:8000/docs · Health http://localhost:8000/api/health · LHM JSON http://localhost:8085/data.json · Ollama http://localhost:11434
