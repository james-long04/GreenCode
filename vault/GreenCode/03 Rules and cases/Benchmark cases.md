---
title: Benchmark cases
created: 2026-10-22
project: GreenCode
tags: [rules, cases]
---

# Benchmark cases (18 Python, 12 SQL)

Files in `benchmarks/python/` and `benchmarks/sql/`. `tests/test_suite_cases.py` checks every original passes its own tests and that the expected rules fire. Two **control** cases (already-efficient code) check that the analyser says "no known pattern" and the model leaves them alone.

| Case | Title | Expected rules | Category |
|---|---|---|---|
| `py_001_membership_list_in_loop` | Membership test against a list inside a loop | PY001 | data_structures |
| `py_002_string_concat_loop` | String building with += in a loop | PY002 | allocations |
| `py_003_loop_append` | Loop that only appends to a list | PY003 | redundant_operations |
| `py_004_range_len_indexing` | Indexing with range(len(x)) | PY004 | redundant_operations |
| `py_005_loop_invariant_sorted` | sorted() recomputed inside a loop | PY005 | repeated_computation |
| `py_006_nested_loop_join` | Nested loops joining two lists on a key | PY006 | data_structures |
| `py_007_sorted_for_min` | Full sort used to find the minimum | PY007 | sorting |
| `py_008_sum_listcomp` | sum() over a materialised list comprehension | PY008 | allocations |
| `py_009_query_in_loop` | N+1 query pattern against a fake database cursor | PY009 | database |
| `py_010_manual_sum` | Manual accumulation loop | PY010 | redundant_operations |
| `py_011_keys_membership` | Membership test on list(dict.keys()) inside a loop | PY008, PY005 | allocations |
| `py_012_regex_compile_in_loop` | Regular expression compiled inside a loop | PY005 | repeated_computation |
| `py_013_dedupe_with_list` | De-duplication using `not in list` | PY001 | data_structures |
| `py_014_top_k_full_sort` | Full sort to obtain the top k items | PY007 | sorting |
| `py_015_len_list_generator` | len(list(generator)) to count matches | PY008 | allocations |
| `py_016_count_matching_loop` | Counting loop with a condition | PY010 | redundant_operations |
| `py_017_nested_membership_tuple` | Membership test against a tuple literal in a hot loop | PY001 | data_structures |
| `py_018_no_known_pattern` | Control case: already efficient code | — (control) | control |
| `sql_001_select_star_function_predicate` | SELECT * with a function wrapped around an indexed column | SQL001, SQL003 | indexing |
| `sql_002_correlated_count_subquery` | Correlated COUNT(*) subquery per customer | SQL006 | joins |
| `sql_003_not_in_subquery` | Customers without orders via NOT IN | SQL005 | joins |
| `sql_004_leading_wildcard_like` | Leading wildcard LIKE on email | SQL004 | indexing |
| `sql_005_distinct_join` | DISTINCT used to collapse a one-to-many join | SQL007 | unnecessary_work |
| `sql_006_lower_email_predicate` | lower() on the filtered column defeats the index | SQL003 | indexing |
| `sql_007_count_exists` | COUNT(*) > 0 used for an existence check | SQL012 | unnecessary_work |
| `sql_008_order_by_no_limit_select_star` | SELECT * sorted without LIMIT for a recent-orders feed | SQL001, SQL009 | unnecessary_work |
| `sql_009_date_cast_predicate` | Casting a timestamp column to date in WHERE | SQL003 | indexing |
| `sql_010_in_subquery_large` | IN (subquery) over a large table | SQL010 | joins |
| `sql_011_control_efficient` | Control case: already index-friendly query | — (control) | control |
| `sql_012_per_customer_total_subquery` | Correlated SUM subquery with an arithmetic predicate | SQL006, SQL003 | joins |
