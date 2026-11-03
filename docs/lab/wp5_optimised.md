# WP5 — complex queries through the GreenCode pipeline (3 Nov 2026, SF 1, Balanced mode, qwen2.5-coder:7b)

Speed-up = original median ÷ candidate median; energy ratio = original net J ÷ candidate net J (both > 1 = candidate better).

| Case | Anti-patterns planted | AI-only | GreenCode | What the model did (see `wp5/candidates.md`) |
|---|---|---|---|---|
| c01 | correlated COUNT/SUM per customer; `extract()` on date | **5.33×**, energy 0.54 | rejected (columns renamed) | Both pre-aggregated orders into a derived table. GreenCode's version renamed `orders_1995`/`spend_1995` to `orders_count`/`total_spend` and used an inner join — rows matched, column names did not, so verification rejected it. Neither fixed the `extract()` predicate despite the SQL003 finding. |
| c02 | `NOT IN (subquery)` over lineitem; `SELECT *` | 1.04×, energy 1.49 | **330×**, energy **69.7** | AI-only returned the query unchanged. GreenCode rewrote to `NOT EXISTS` / `EXISTS` and expanded `SELECT *` — PostgreSQL's hashed-subplan NOT IN over 6 M rows collapses to an anti-join. |
| c03 | function on column; DISTINCT over window | rejected | rejected | Identical candidates under both conditions: both dropped DISTINCT, returning 200 001 rows instead of 300. A model limitation, not a guidance effect. |
| c04 | correlated subqueries in SELECT/WHERE; `IN (subquery)` | 1.26×, energy 1.31 | 1.38×, energy 0.23 | Faster under guidance but 4× the energy: the rewrite moved a serial plan onto a parallel one. |
| c05 | `COUNT(*) > 0`; leading-wildcard LIKE; no LIMIT | 0.79×, energy 0.62 | 0.71×, energy 0.53 | Correct but slower under both — the planner already handled the original well. |
| c06 | arithmetic on column; DISTINCT over join | 0.53×, energy 1.61 | 0.84×, energy 1.31 | Correct but slower under both; guidance halved the damage. |
| c07 | `SELECT *` over a wide join | rejected | **1.67×**, energy 0.89 | AI-only changed the result set; GreenCode's explicit column list was verified. |
| c08 | three correlated aggregates per supplier | 0.66×, energy **0.14** | 0.66×, energy 0.16 | Both produced the textbook pre-aggregation — over *all* 6 M lineitems, not just Japan's suppliers — so 1.5× slower and 7× the energy. The "right" rewrite was the wrong one for this data. |

## Per-condition (from `summary.json`)

| | AI-only | GreenCode |
|---|---|---|
| Verified / generated | 6 / 8 (75 %) | 6 / 8 (75 %) |
| Geomean speed-up, per-protocol (5 pairs) | 0.82× | 2.83× |
| Geomean speed-up, intention-to-treat (8) | 1.09× | 2.04× |
| Geomean energy ratio, per-protocol | 0.77 | 1.12 |

With eight cases nothing reaches significance (H2 per-protocol p = 0.16); the value of WP5 is qualitative. Four observations for the report:

1. **Guidance found the one big win.** c02's `NOT IN` → `NOT EXISTS` is a 330× / 70× result that the unguided model did not attempt.
2. **Correct-but-slower is common** (c05, c06, c08 under both conditions). Verification passes, the benchmark catches it. This reproduces Peng et al. and is the strongest argument for measuring rather than trusting.
3. **Time and energy diverge in both directions.** c01 AI-only: 5.3× faster, 1.8× more energy. c08: 1.5× slower, 7× more energy. c04 GreenCode: 1.4× faster, 4× more energy. The mechanism is the serial→parallel plan change interacting with the laptop's P-/E-core scheduling that WP3 exposed. H4 is not a corner case here; it is the norm.
4. **Rejections are informative.** c01 GreenCode failed only on column names (the output contract is strict by design); c03 failed identically under both conditions (model limitation); c07 AI-only changed the result set where the guided version kept it.
