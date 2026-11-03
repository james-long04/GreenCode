# Draft: interim-report section 5 — Laboratory experiments on a TPC-H-derived workload

(Text as sent to James on 3 Nov 2026; 5.3 updated with the Balanced baseline. Figures: 5.1 = wp1_mean_watts.png, 5.2 = wp3_energy_ratio.png.)

## 5.3 WP1 — baseline, and an unexpected split

Three randomised passes over the 22 queries under the standard *Balanced* power mode gave a stable baseline: one pass is 21.8 s of query time and 205 J of net energy, 9.4 W above the idle floor on average. The queries fell into two groups (Figure 5.1). Seventeen ran at 13–23 W with client time close to their own `EXPLAIN ANALYZE` time (1.28× on average). Five — Q11, Q13, Q15, Q17 and Q20 — ran at 6–10 W and took 2.07× longer than their `EXPLAIN ANALYZE`. Those five are exactly the queries whose plans PostgreSQL cannot parallelise (correlated subqueries, the Q15 view, the Q13 `NOT LIKE` outer join): a single-threaded backend was evidently being run on the processor's efficiency cores at low frequency, while parallel plans got the performance cores. An earlier set of three passes made before I had noticed the power-mode setting, under *Best Power Efficiency*, gave 23.0 s and 202 J per pass; the serial group was 14 % slower and used 37 % less energy there, and Q2 joined it. WP3 tests whether the mode is the cause.
