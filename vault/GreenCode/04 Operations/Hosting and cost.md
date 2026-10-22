---
title: Hosting and cost
created: 2026-10-22
project: GreenCode
tags: [ops, hosting]
---

# Hosting and cost (asked once; decision: run locally)

Hosting the dashboard + backend + PostgreSQL on a small VPS for the "greencode" domain would cost roughly **€5–25/month** (VPS €5–15, domain ~€10/year, managed Postgres optional). But the experiment must run on a known, idle machine with RAPL access and a local GPU/CPU for Ollama, so **experiments stay on the laptop**; hosting would only make sense for a read-only results viewer. Not pursued.
