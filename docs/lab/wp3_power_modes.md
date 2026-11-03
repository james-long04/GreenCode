# WP3 — power management

Reference plan: **best-efficiency**. Ratios < 1 are faster / lower energy than the reference.

| query | best-efficiency ms | best-efficiency J/exec | balanced time ÷ | balanced energy ÷ | best-performance time ÷ | best-performance energy ÷ |
|---|---|---|---|---|---|---|
| q01 | 1,656 | 37.1 | 1.17 | 0.69 |  |  | 1.05 | 0.75 |
| q02 | 447 | 1.95 | 0.87 | 1.10 |  |  | 0.55 | 1.29 |
| q03 | 363 | 7.98 | 0.98 | 0.88 |  |  | 0.85 | 0.94 |
| q04 | 176 | 3.41 | 1.12 | 0.79 |  |  | 0.91 | 0.85 |
| q05 | 355 | 6.83 | 0.97 | 1.00 |  |  | 0.87 | 0.98 |
| q06 | 431 | 4.94 | 0.88 | 1.10 |  |  | 0.66 | 1.05 |
| q07 | 1,005 | 19.3 | 0.96 | 1.03 |  |  | 0.88 | 1.01 |
| q08 | 199 | 4.07 | 1.03 | 0.81 |  |  | 0.90 | 0.87 |
| q09 | 755 | 18.0 | 1.10 | 0.77 |  |  | 0.92 | 0.92 |
| q10 | 697 | 12.4 | 1.03 | 0.68 |  |  | 0.85 | 0.79 |
| q11 | 191 | 0.21 | 0.84 | 2.22 |  |  | 0.55 | 2.88 |
| q12 | 597 | 12.7 | 1.12 | 0.70 |  |  | 0.96 | 0.76 |
| q13 | 3,998 | 3.10 | 0.79 | 2.08 |  |  | 0.55 | 2.72 |
| q14 | 158 | 2.90 | 0.96 | 1.01 |  |  | 0.87 | 0.92 |
| q15 | 525 | 0.67 | 0.85 | 1.63 |  |  | 0.52 | 2.22 |
| q16 | 460 | 5.36 | 0.91 | 1.08 |  |  | 0.65 | 1.02 |
| q17 | 2,127 | 1.74 | 0.79 | 2.84 |  |  | 0.52 | 3.95 |
| q18 | 5,762 | 55.5 | 0.86 | 1.25 |  |  | 0.54 | 1.16 |
| q19 | 76.3 | 1.56 | 1.11 | 0.77 |  |  | 0.92 | 0.77 |
| q20 | 1,330 | 0.82 | 0.92 | 2.61 |  |  | 0.54 | 3.89 |
| q21 | 786 | 16.5 | 1.10 | 0.74 |  |  | 0.98 | 0.87 |
| q22 | 148 | 2.13 | 0.83 | 1.20 |  |  | 0.76 | 1.16 |

## Summary (geometric means across queries)

| plan | queries | time ÷ ref | energy ÷ ref |
|---|---|---|---|
| balanced | 22 | 0.96 | 1.11 |
| best-performance | 22 | 0.74 | 1.23 |

## One pass over the query set

| plan | query time (s) | net energy (J) | avg net W |
|---|---|---|---|
| balanced | 20.3 | 213 | 10.5 |
| best-efficiency | 22.2 | 219 | 9.85 |
| best-performance | 14.9 | 223 | 15.0 |

## Serial (<10 W under best-efficiency) queries only: q02, q11, q13, q15, q17, q20

| plan | queries | time ÷ ref | energy ÷ ref |
|---|---|---|---|
| balanced | 6 | 0.84 | 1.99 |
| best-performance | 6 | 0.54 | 2.65 |
