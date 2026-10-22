---
title: Setup on Windows
created: 2026-10-22
project: GreenCode
tags: [ops, setup]
---

# Setup on Windows (one-off)

Prerequisites: Python 3.12+ (laptop has 3.15, packages via `pip --user`), Node 20+, PostgreSQL 16+ (laptop has 18), Ollama with `ollama pull qwen2.5-coder:7b`, LibreHardwareMonitor.

## 1. Database (psql as postgres)
```sql
CREATE ROLE greencode WITH LOGIN PASSWORD 'greencode';
CREATE DATABASE greencode OWNER greencode;
```

## 2. Backend
```powershell
cd $HOME\GreenCode-app\backend
copy .env.example .env     # set GREENCODE_ADMIN_TOKEN
pip install --user -r requirements.txt
python scripts\init_db.py
python scripts\seed_bench_dataset.py
```

## 3. Dashboard
```powershell
cd $HOME\GreenCode-app\frontend
npm install
```

## 4. Energy
LibreHardwareMonitor as Administrator → Options → Remote Web Server → Run (port 8085). Optionally set it to start with Windows.

Then see [[04 Operations/Commands cheatsheet]].
