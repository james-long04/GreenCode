# WP2 — does measuring change the measurement?

Median client time of each query under each meter, divided by the same query with no meter.

| query | none ms | codecarbon ÷ none | lhm@0.1 ÷ none | lhm@0.5 ÷ none |
|---|---|---|---|---|
| q01 | 2.09e+03 | 0.904 | 0.913 | 0.786 |
| q02 | 447 | 1.06 | 1.03 | 1.01 |
| q03 | 358 | 1.05 | 0.985 | 0.997 |
| q04 | 198 | 1.02 | 1.01 | 0.884 |
| q05 | 371 | 0.963 | 0.952 | 0.933 |
| q06 | 407 | 1.08 | 1.07 | 1.08 |
| q07 | 984 | 1.04 | 1.04 | 1.04 |
| q08 | 231 | 0.884 | 0.876 | 0.856 |
| q09 | 832 | 1 | 1.01 | 0.932 |
| q10 | 776 | 0.951 | 0.961 | 0.882 |
| q11 | 191 | 1.08 | 0.964 | 0.995 |
| q12 | 718 | 0.993 | 0.967 | 0.864 |
| q13 | 3.43e+03 | 1.14 | 1.16 | 1.19 |
| q14 | 154 | 0.996 | 1.04 | 1.02 |
| q15 | 520 | 0.987 | 0.999 | 0.966 |
| q16 | 431 | 1.07 | 1.05 | 1.06 |
| q17 | 1.97e+03 | 1.17 | 1.08 | 1.11 |
| q18 | 5.75e+03 | 1.03 | 0.975 | 1.01 |
| q19 | 89.1 | 0.958 | 1 | 0.832 |
| q20 | 1.34e+03 | 1.01 | 0.958 | 0.983 |
| q21 | 857 | 1.01 | 1.04 | 0.932 |
| q22 | 126 | 0.988 | 1.01 | 1.19 |

## Summary

| meter | queries | geomean ratio | median ratio | min | max | Wilcoxon p (vs 1.0) |
|---|---|---|---|---|---|---|
| codecarbon | 22 | 1.02 | 1.01 | 0.884 | 1.17 | 0.262 |
| lhm@0.1 | 22 | 1 | 1 | 0.876 | 1.16 | 0.849 |
| lhm@0.5 | 22 | 0.974 | 0.989 | 0.786 | 1.19 | 0.337 |

A ratio of 1.00 means no overhead. The Wilcoxon test asks whether the paired log-ratios differ from zero across the 22 queries.
