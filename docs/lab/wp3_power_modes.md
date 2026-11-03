# WP3 — power management

Reference plan: **best-efficiency**. Ratios < 1 are faster / lower energy than the reference.

| query | best-efficiency ms | best-efficiency J/exec | balanced time ÷ | balanced energy ÷ | best-performance time ÷ | best-performance energy ÷ |
|---|---|---|---|---|---|---|
| q01 | 1.66e+03 | 37.1 | 1.17 | 0.689 |  |  | 1.05 | 0.745 |
| q02 | 447 | 1.95 | 0.875 | 1.1 |  |  | 0.551 | 1.29 |
| q03 | 363 | 7.98 | 0.984 | 0.879 |  |  | 0.853 | 0.943 |
| q04 | 176 | 3.41 | 1.12 | 0.786 |  |  | 0.91 | 0.849 |
| q05 | 355 | 6.83 | 0.974 | 1 |  |  | 0.874 | 0.978 |
| q06 | 431 | 4.94 | 0.882 | 1.1 |  |  | 0.664 | 1.05 |
| q07 | 1.01e+03 | 19.3 | 0.965 | 1.03 |  |  | 0.882 | 1.01 |
| q08 | 199 | 4.07 | 1.03 | 0.812 |  |  | 0.904 | 0.865 |
| q09 | 755 | 18 | 1.1 | 0.768 |  |  | 0.924 | 0.921 |
| q10 | 697 | 12.4 | 1.03 | 0.684 |  |  | 0.851 | 0.795 |
| q11 | 191 | 0.21 | 0.838 | 2.22 |  |  | 0.553 | 2.88 |
| q12 | 597 | 12.7 | 1.12 | 0.704 |  |  | 0.964 | 0.764 |
| q13 | 4e+03 | 3.1 | 0.79 | 2.08 |  |  | 0.547 | 2.72 |
| q14 | 158 | 2.9 | 0.961 | 1.01 |  |  | 0.867 | 0.919 |
| q15 | 525 | 0.671 | 0.849 | 1.63 |  |  | 0.521 | 2.22 |
| q16 | 460 | 5.36 | 0.911 | 1.08 |  |  | 0.648 | 1.02 |
| q17 | 2.13e+03 | 1.74 | 0.793 | 2.84 |  |  | 0.521 | 3.95 |
| q18 | 5.76e+03 | 55.5 | 0.862 | 1.25 |  |  | 0.542 | 1.16 |
| q19 | 76.3 | 1.56 | 1.11 | 0.773 |  |  | 0.922 | 0.774 |
| q20 | 1.33e+03 | 0.824 | 0.922 | 2.61 |  |  | 0.544 | 3.89 |
| q21 | 786 | 16.5 | 1.1 | 0.743 |  |  | 0.98 | 0.874 |
| q22 | 148 | 2.13 | 0.833 | 1.2 |  |  | 0.756 | 1.16 |

## Summary (geometric means across queries)

| plan | queries | time ÷ ref | energy ÷ ref |
|---|---|---|---|
| balanced | 22 | 0.958 | 1.11 |
| best-performance | 22 | 0.743 | 1.23 |

## One pass over the query set

| plan | query time (s) | net energy (J) | avg net W |
|---|---|---|---|
| balanced | 20.3 | 213 | 10.5 |
| best-efficiency | 22.2 | 219 | 9.85 |
| best-performance | 14.9 | 223 | 15 |

## Serial (<10 W under best-efficiency) queries only: q02, q11, q13, q15, q17, q20

| plan | queries | time ÷ ref | energy ÷ ref |
|---|---|---|---|
| balanced | 6 | 0.843 | 1.99 |
| best-performance | 6 | 0.539 | 2.65 |
