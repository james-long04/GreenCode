---
title: GreenCode — Home
created: 2026-10-22
project: GreenCode
tags: [moc]
---

# GreenCode

> *Don't just optimise. Prove the impact.*

Final-year project (BSc Computer Science, TU Dublin) by James Long. Static-analysis-guided AI optimisation of Python and SQL, with measured runtime, energy and CO₂e evidence. Repo: https://github.com/james-long04/GreenCode · local clone `C:\Users\james\GreenCode-app`.

This vault holds **everything about the project in one place**: what it is, how the code works, how to run it, the report writing, the references, and the decisions and instructions that shaped it.

## Start here
- [[01 Project/Project overview]] — one page on what GreenCode is and why
- [[01 Project/Research design]] — the research question, H1–H4, variables, statistics
- [[04 Operations/Commands cheatsheet]] — the PowerShell commands you actually type
- [[02 Architecture/Pipeline]] — the seven stages a piece of code goes through

## Maps of content
- [[01 Project/_Project MOC]] — purpose, plan, supervisor guidance, decisions, ethics
- [[02 Architecture/_Architecture MOC]] — backend packages, data model, energy chain, frontend, API
- [[03 Rules and cases/_Rules MOC]] — the 23 rules, 30 benchmark cases, the bench dataset
- [[04 Operations/_Operations MOC]] — setup, running, testing, troubleshooting
- [[05 Writing/_Writing MOC]] — proposal / interim report sections, references, style guide
- [[06 Resources/_Resources MOC]] — diagrams, documents, tools, reference library
- [[07 Working with Claude/_Claude MOC]] — the instructions, skills and conventions used when building with AI

## Status (as of 2026-10-22)
- Backend, dashboard and admin panel complete; 110 tests passing on Windows.
- Energy is **measured** on the laptop (Intel Core Ultra 5 135U) through LibreHardwareMonitor → RAPL; idle floor subtracted.
- Proposal / interim-report sections drafted (see [[05 Writing/_Writing MOC]]); 31 IEEE references in Zotero with full text.
- Next: run the full suite with 30+ repetitions, export CSV, write up results.
