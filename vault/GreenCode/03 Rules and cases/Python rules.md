---
title: Python rules
created: 2026-10-22
project: GreenCode
tags: [rules, python]
---

# Python rules (PY001–PY011)

Implemented in `backend/app/analysis/python_rules.py` over the `ast`.

| Rule | Pattern | Typical suggestion |
|---|---|---|
| PY001 | Membership test (`x in lst`) against a list/tuple inside a loop | Build a `set` once outside the loop |
| PY002 | String `+=` inside a loop | Collect parts, `''.join()` |
| PY003 | Append-only loop building a list | List comprehension |
| PY004 | `for i in range(len(x))` used only to index | Iterate directly / `enumerate` |
| PY005 | Loop-invariant expensive call (`sorted`, `re.compile`, …) inside a loop | Hoist out of the loop |
| PY006 | Nested loops joining two sequences on a key (O(n·m)) | Index one side in a dict |
| PY007 | Full sort just to take min/max/top-k | `min`/`max`/`heapq.nlargest` |
| PY008 | Unnecessary allocations: `sum([...])`, `in d.keys()`, `len(list(...))` | Generator / direct call |
| PY009 | Query/IO call inside a loop (N+1) | Batch the call |
| PY010 | Manual sum/count loop | `sum()` / `len()` |
| PY011 | `DataFrame.iterrows()` | Vectorised pandas |

Each finding also records `evidence` (loop depth, container type …); line numbers are 1-based.
