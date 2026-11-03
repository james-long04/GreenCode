# WP2 — does measuring change the measurement?

Median client time of each query under each meter, divided by the same query with no meter.

| query | none ms | codecarbon ÷ none | lhm@0.1 ÷ none | lhm@0.5 ÷ none |
|---|---|---|---|---|
| q01 | 2,093 | 0.90 | 0.91 | 0.79 |
| q02 | 447 | 1.06 | 1.03 | 1.01 |
| q03 | 358 | 1.05 | 0.98 | 1.00 |
| q04 | 198 | 1.02 | 1.01 | 0.88 |
| q05 | 371 | 0.96 | 0.95 | 0.93 |
| q06 | 407 | 1.08 | 1.07 | 1.08 |
| q07 | 984 | 1.04 | 1.04 | 1.04 |
| q08 | 231 | 0.88 | 0.88 | 0.86 |
| q09 | 832 | 1.00 | 1.01 | 0.93 |
| q10 | 776 | 0.95 | 0.96 | 0.88 |
| q11 | 191 | 1.08 | 0.96 | 1.00 |
| q12 | 718 | 0.99 | 0.97 | 0.86 |
| q13 | 3,433 | 1.14 | 1.16 | 1.19 |
| q14 | 154 | 1.00 | 1.04 | 1.02 |
| q15 | 520 | 0.99 | 1.00 | 0.97 |
| q16 | 431 | 1.07 | 1.05 | 1.06 |
| q17 | 1,971 | 1.17 | 1.08 | 1.11 |
| q18 | 5,751 | 1.03 | 0.98 | 1.01 |
| q19 | 89.1 | 0.96 | 1.00 | 0.83 |
| q20 | 1,337 | 1.01 | 0.96 | 0.98 |
| q21 | 857 | 1.01 | 1.04 | 0.93 |
| q22 | 126 | 0.99 | 1.01 | 1.19 |

## Summary

| meter | queries | geomean ratio | median ratio | min | max | Wilcoxon p (vs 1.0) |
|---|---|---|---|---|---|---|
| codecarbon | 22 | 1.02 | 1.01 | 0.88 | 1.17 | 0.26 |
| lhm@0.1 | 22 | 1.00 | 1.00 | 0.88 | 1.16 | 0.85 |
| lhm@0.5 | 22 | 0.97 | 0.99 | 0.79 | 1.19 | 0.34 |

A ratio of 1.00 means no overhead. The Wilcoxon test asks whether the paired log-ratios differ from zero across the 22 queries.
