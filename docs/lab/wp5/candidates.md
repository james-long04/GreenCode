## tpch_c01 — ai_only — benchmarked

speed-up: 5.3269133998334235  energy ratio: 0.5433609187170455

### Original
```sql
SELECT c.c_custkey, c.c_name, c.c_mktsegment,
       (SELECT count(*) FROM orders o WHERE o.o_custkey = c.c_custkey AND extract(year FROM o.o_orderdate) = 1995) AS orders_1995,
       (SELECT sum(o.o_totalprice) FROM orders o WHERE o.o_custkey = c.c_custkey AND extract(year FROM o.o_orderdate) = 1995) AS spend_1995
FROM customer c
WHERE c.c_mktsegment = 'AUTOMOBILE'
ORDER BY spend_1995 DESC NULLS LAST
LIMIT 50;
```

### Candidate
```sql
SELECT c.c_custkey, c.c_name, c.c_mktsegment,
       COALESCE(o1995.count, 0) AS orders_1995,
       COALESCE(o1995.spend, 0) AS spend_1995
FROM customer c
LEFT JOIN (
    SELECT o_custkey,
           COUNT(*) AS count,
           SUM(o_totalprice) AS spend
    FROM orders
    WHERE EXTRACT(YEAR FROM o_orderdate) = 1995
    GROUP BY o_custkey
) o1995 ON c.c_custkey = o1995.o_custkey
WHERE c.c_mktsegment = 'AUTOMOBILE'
ORDER BY spend_1995 DESC NULLS LAST
LIMIT 50
```

### Test results

- columns: pass
- row_count: pass
- rows: pass

<details><summary>Prompt</summary>

```
Optimise the following PostgreSQL query for execution time and resource usage.

The query runs against this PostgreSQL schema:
```sql
CREATE TABLE customer (c_custkey integer, c_name character varying, c_address character varying, c_nationkey integer, c_phone character, c_acctbal numeric, c_mktsegment character, c_comment character varying);
CREATE TABLE lineitem (l_orderkey integer, l_partkey integer, l_suppkey integer, l_linenumber integer, l_quantity numeric, l_extendedprice numeric, l_discount numeric, l_tax numeric, l_returnflag character, l_linestatus character, l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct character, l_shipmode character, l_comment character varying);
CREATE TABLE nation (n_nationkey integer, n_name character, n_regionkey integer, n_comment character varying);
CREATE TABLE orders (o_orderkey integer, o_custkey integer, o_orderstatus character, o_totalprice numeric, o_orderdate date, o_orderpriority character, o_clerk character, o_shippriority integer, o_comment character varying);
CREATE TABLE part (p_partkey integer, p_name character varying, p_mfgr character, p_brand character, p_type character varying, p_size integer, p_container character, p_retailprice numeric, p_comment character varying);
CREATE TABLE partsupp (ps_partkey integer, ps_suppkey integer, ps_availqty integer, ps_supplycost numeric, ps_comment character varying);
CREATE TABLE region (r_regionkey integer, r_name character, r_comment character varying);
CREATE TABLE supplier (s_suppkey integer, s_name character, s_address character varying, s_nationkey integer, s_phone character, s_acctbal numeric, s_comment character varying);
-- CREATE INDEX customer_c_nationkey_idx ON tpch.customer USING btree (c_nationkey)
-- CREATE UNIQUE INDEX customer_pkey ON tpch.customer USING btree (c_custkey)
-- CREATE INDEX lineitem_l_partkey_idx ON tpch.lineitem USING btree (l_partkey)
-- CREATE INDEX lineitem_l_shipdate_idx ON tpch.lineitem USING btree (l_shipdate)
-- CREATE INDEX lineitem_l_suppkey_idx ON tpch.lineitem USING btree (l_suppkey)
-- CREATE UNIQUE INDEX lineitem_pkey ON tpch.lineitem USING btree (l_orderkey, l_linenumber)
-- CREATE UNIQUE INDEX nation_pkey ON tpch.nation USING btree (n_nationkey)
-- CREATE INDEX orders_o_custkey_idx ON tpch.orders USING btree (o_custkey)
-- CREATE INDEX orders_o_orderdate_idx ON tpch.orders USING btree (o_orderdate)
-- CREATE UNIQUE INDEX orders_pkey ON tpch.orders USING btree (o_orderkey)
-- CREATE UNIQUE INDEX part_pkey ON tpch.part USING btree (p_partkey)
-- CREATE UNIQUE INDEX partsupp_pkey ON tpch.partsupp USING btree (ps_partkey, ps_suppkey)
-- CREATE INDEX partsupp_ps_suppkey_idx ON tpch.partsupp USING btree (ps_suppkey)
-- CREATE UNIQUE INDEX region_pkey ON tpch.region USING btree (r_regionkey)
-- CREATE UNIQUE INDEX supplier_pkey ON tpch.supplier USING btree (s_suppkey)
-- CREATE INDEX supplier_s_nationkey_idx ON tpch.supplier USING btree (s_nationkey)
```

Original:
```sql
SELECT c.c_custkey, c.c_name, c.c_mktsegment,
       (SELECT count(*) FROM orders o WHERE o.o_custkey = c.c_custkey AND extract(year FROM o.o_orderdate) = 1995) AS orders_1995,
       (SELECT sum(o.o_totalprice) FROM orders o WHERE o.o_custkey = c.c_custkey AND extract(year FROM o.o_orderdate) = 1995) AS spend_1995
FROM customer c
WHERE c.c_mktsegment = 'AUTOMOBILE'
ORDER BY spend_1995 DESC NULLS LAST
LIMIT 50;
```

Constraints:
- Preserve exact behaviour and output for every possible input.
- Do not change names, signatures or the set of returned columns.
- Prefer simple, idiomatic changes with a clear algorithmic or I/O benefit.

Respond with the complete optimised SQL statement in a single ```sql fenced code block and nothing else. Do not include explanations, comments or more than one statement.
```

</details>

## tpch_c01 — greencode — rejected (wrong_output)

speed-up: None  energy ratio: None

### Original
```sql
SELECT c.c_custkey, c.c_name, c.c_mktsegment,
       (SELECT count(*) FROM orders o WHERE o.o_custkey = c.c_custkey AND extract(year FROM o.o_orderdate) = 1995) AS orders_1995,
       (SELECT sum(o.o_totalprice) FROM orders o WHERE o.o_custkey = c.c_custkey AND extract(year FROM o.o_orderdate) = 1995) AS spend_1995
FROM customer c
WHERE c.c_mktsegment = 'AUTOMOBILE'
ORDER BY spend_1995 DESC NULLS LAST
LIMIT 50;
```

### Candidate
```sql
WITH orders_1995 AS (
    SELECT o_custkey, COUNT(*) AS orders_count, SUM(o_totalprice) AS total_spend
    FROM orders
    WHERE EXTRACT(YEAR FROM o_orderdate) = 1995
    GROUP BY o_custkey
)
SELECT c.c_custkey, c.c_name, c.c_mktsegment, o.orders_count, o.total_spend
FROM customer c
JOIN orders_1995 o ON c.c_custkey = o.o_custkey
WHERE c.c_mktsegment = 'AUTOMOBILE'
ORDER BY o.total_spend DESC NULLS LAST
LIMIT 50
```

### Test results

- columns: FAIL — wrong_output: columns differ: original ['c_custkey', 'c_name', 'c_mktsegment', 'orders_1995', 'spend_1995'] vs candidate ['c_custkey', 'c_name', 'c_mktsegment', 'orders_count', 'total_spend']
- row_count: pass
- rows: pass

<details><summary>Prompt</summary>

```
Optimise the following PostgreSQL query for execution time and resource usage.

The query runs against this PostgreSQL schema:
```sql
CREATE TABLE customer (c_custkey integer, c_name character varying, c_address character varying, c_nationkey integer, c_phone character, c_acctbal numeric, c_mktsegment character, c_comment character varying);
CREATE TABLE lineitem (l_orderkey integer, l_partkey integer, l_suppkey integer, l_linenumber integer, l_quantity numeric, l_extendedprice numeric, l_discount numeric, l_tax numeric, l_returnflag character, l_linestatus character, l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct character, l_shipmode character, l_comment character varying);
CREATE TABLE nation (n_nationkey integer, n_name character, n_regionkey integer, n_comment character varying);
CREATE TABLE orders (o_orderkey integer, o_custkey integer, o_orderstatus character, o_totalprice numeric, o_orderdate date, o_orderpriority character, o_clerk character, o_shippriority integer, o_comment character varying);
CREATE TABLE part (p_partkey integer, p_name character varying, p_mfgr character, p_brand character, p_type character varying, p_size integer, p_container character, p_retailprice numeric, p_comment character varying);
CREATE TABLE partsupp (ps_partkey integer, ps_suppkey integer, ps_availqty integer, ps_supplycost numeric, ps_comment character varying);
CREATE TABLE region (r_regionkey integer, r_name character, r_comment character varying);
CREATE TABLE supplier (s_suppkey integer, s_name character, s_address character varying, s_nationkey integer, s_phone character, s_acctbal numeric, s_comment character varying);
-- CREATE INDEX customer_c_nationkey_idx ON tpch.customer USING btree (c_nationkey)
-- CREATE UNIQUE INDEX customer_pkey ON tpch.customer USING btree (c_custkey)
-- CREATE INDEX lineitem_l_partkey_idx ON tpch.lineitem USING btree (l_partkey)
-- CREATE INDEX lineitem_l_shipdate_idx ON tpch.lineitem USING btree (l_shipdate)
-- CREATE INDEX lineitem_l_suppkey_idx ON tpch.lineitem USING btree (l_suppkey)
-- CREATE UNIQUE INDEX lineitem_pkey ON tpch.lineitem USING btree (l_orderkey, l_linenumber)
-- CREATE UNIQUE INDEX nation_pkey ON tpch.nation USING btree (n_nationkey)
-- CREATE INDEX orders_o_custkey_idx ON tpch.orders USING btree (o_custkey)
-- CREATE INDEX orders_o_orderdate_idx ON tpch.orders USING btree (o_orderdate)
-- CREATE UNIQUE INDEX orders_pkey ON tpch.orders USING btree (o_orderkey)
-- CREATE UNIQUE INDEX part_pkey ON tpch.part USING btree (p_partkey)
-- CREATE UNIQUE INDEX partsupp_pkey ON tpch.partsupp USING btree (ps_partkey, ps_suppkey)
-- CREATE INDEX partsupp_ps_suppkey_idx ON tpch.partsupp USING btree (ps_suppkey)
-- CREATE UNIQUE INDEX region_pkey ON tpch.region USING btree (r_regionkey)
-- CREATE UNIQUE INDEX supplier_pkey ON tpch.supplier USING btree (s_suppkey)
-- CREATE INDEX supplier_s_nationkey_idx ON tpch.supplier USING btree (s_nationkey)
```

Original:
```sql
SELECT c.c_custkey, c.c_name, c.c_mktsegment,
       (SELECT count(*) FROM orders o WHERE o.o_custkey = c.c_custkey AND extract(year FROM o.o_orderdate) = 1995) AS orders_1995,
       (SELECT sum(o.o_totalprice) FROM orders o WHERE o.o_custkey = c.c_custkey AND extract(year FROM o.o_orderdate) = 1995) AS spend_1995
FROM customer c
WHERE c.c_mktsegment = 'AUTOMOBILE'
ORDER BY spend_1995 DESC NULLS LAST
LIMIT 50;
```

A static analyser has identified the following specific inefficiencies. Address each one directly. Do not make unrelated changes.

1. [SQL003] non sargable predicate
   Why it is inefficient: The column `o.o_orderdate` is wrapped in `EXTRACT(YEAR FROM o.o_orderdate)` before comparison. PostgreSQL cannot use a plain B-tree index on the column for this predicate and must evaluate the expression for every row.
   Suggested change: Rewrite the predicate so the bare column is compared to a constant/range (e.g. `date_col >= '2024-01-01' AND date_col < '2025-01-01'` instead of `EXTRACT(YEAR FROM date_col) = 2024`; `email = lower($1)` instead of `lower(email) = $1`), or create an expression index.
   Code: EXTRACT(YEAR FROM o.o_orderdate) = 1995
2. [SQL003] non sargable predicate
   Why it is inefficient: The column `o.o_orderdate` is wrapped in `EXTRACT(YEAR FROM o.o_orderdate)` before comparison. PostgreSQL cannot use a plain B-tree index on the column for this predicate and must evaluate the expression for every row.
   Suggested change: Rewrite the predicate so the bare column is compared to a constant/range (e.g. `date_col >= '2024-01-01' AND date_col < '2025-01-01'` instead of `EXTRACT(YEAR FROM date_col) = 2024`; `email = lower($1)` instead of `lower(email) = $1`), or create an expression index.
   Code: EXTRACT(YEAR FROM o.o_orderdate) = 1995
3. [SQL006] correlated subquery in select
   Why it is inefficient: A subquery in the SELECT list references the outer query, so it is evaluated once per outer row.
   Suggested change: Rewrite as a JOIN to a pre-aggregated derived table (GROUP BY the key) or a LATERAL join.
   Code: (SELECT COUNT(*) FROM orders AS o WHERE o.o_custkey = c.c_custkey AND EXTRACT(YEAR FROM o.o_orderdate) = 1995)
4. [SQL006] correlated subquery in select
   Why it is inefficient: A subquery in the SELECT list references the outer query, so it is evaluated once per outer row.
   Suggested change: Rewrite as a JOIN to a pre-aggregated derived table (GROUP BY the key) or a LATERAL join.
   Code: (SELECT SUM(o.o_totalprice) FROM orders AS o WHERE o.o_custkey = c.c_custkey AND EXTRACT(YEAR FROM o.o_orderdate) = 1995)
5. [SQL011] sequential scan on large table
   Why it is inefficient: The planner chose a sequential scan of `customer` (~150000 rows, estimated cost 2175745.98).
   Suggested change: Make the predicate index-friendly or add an index on the filtered/joined columns, then re-check EXPLAIN.

Constraints:
- Preserve exact behaviour and output for every possible input.
- Do not change names, signatures or the set of returned columns.
- Prefer simple, idiomatic changes with a clear algorithmic or I/O benefit.

Respond with the complete optimised SQL statement in a single ```sql fenced code block and nothing else. Do not include explanations, comments or more than one statement.
```

</details>

## tpch_c02 — ai_only — benchmarked

speed-up: 1.037531279160242  energy ratio: 1.4871211681165286

### Original
```sql
SELECT *
FROM supplier
WHERE s_suppkey NOT IN (
    SELECT l_suppkey FROM lineitem WHERE l_receiptdate > l_commitdate AND l_shipdate >= DATE '1996-01-01')
  AND s_nationkey IN (SELECT n_nationkey FROM nation WHERE n_name IN ('UNITED KINGDOM', 'IRELAND', 'FRANCE', 'GERMANY'))
ORDER BY s_acctbal DESC;
```

### Candidate
```sql
SELECT *
FROM supplier
WHERE s_suppkey NOT IN (
    SELECT l_suppkey FROM lineitem WHERE l_receiptdate > l_commitdate AND l_shipdate >= DATE '1996-01-01'
)
  AND s_nationkey IN (SELECT n_nationkey FROM nation WHERE n_name IN ('UNITED KINGDOM', 'IRELAND', 'FRANCE', 'GERMANY'))
ORDER BY s_acctbal DESC
```

### Test results

- columns: pass
- row_count: pass
- rows: pass

<details><summary>Prompt</summary>

```
Optimise the following PostgreSQL query for execution time and resource usage.

The query runs against this PostgreSQL schema:
```sql
CREATE TABLE customer (c_custkey integer, c_name character varying, c_address character varying, c_nationkey integer, c_phone character, c_acctbal numeric, c_mktsegment character, c_comment character varying);
CREATE TABLE lineitem (l_orderkey integer, l_partkey integer, l_suppkey integer, l_linenumber integer, l_quantity numeric, l_extendedprice numeric, l_discount numeric, l_tax numeric, l_returnflag character, l_linestatus character, l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct character, l_shipmode character, l_comment character varying);
CREATE TABLE nation (n_nationkey integer, n_name character, n_regionkey integer, n_comment character varying);
CREATE TABLE orders (o_orderkey integer, o_custkey integer, o_orderstatus character, o_totalprice numeric, o_orderdate date, o_orderpriority character, o_clerk character, o_shippriority integer, o_comment character varying);
CREATE TABLE part (p_partkey integer, p_name character varying, p_mfgr character, p_brand character, p_type character varying, p_size integer, p_container character, p_retailprice numeric, p_comment character varying);
CREATE TABLE partsupp (ps_partkey integer, ps_suppkey integer, ps_availqty integer, ps_supplycost numeric, ps_comment character varying);
CREATE TABLE region (r_regionkey integer, r_name character, r_comment character varying);
CREATE TABLE supplier (s_suppkey integer, s_name character, s_address character varying, s_nationkey integer, s_phone character, s_acctbal numeric, s_comment character varying);
-- CREATE INDEX customer_c_nationkey_idx ON tpch.customer USING btree (c_nationkey)
-- CREATE UNIQUE INDEX customer_pkey ON tpch.customer USING btree (c_custkey)
-- CREATE INDEX lineitem_l_partkey_idx ON tpch.lineitem USING btree (l_partkey)
-- CREATE INDEX lineitem_l_shipdate_idx ON tpch.lineitem USING btree (l_shipdate)
-- CREATE INDEX lineitem_l_suppkey_idx ON tpch.lineitem USING btree (l_suppkey)
-- CREATE UNIQUE INDEX lineitem_pkey ON tpch.lineitem USING btree (l_orderkey, l_linenumber)
-- CREATE UNIQUE INDEX nation_pkey ON tpch.nation USING btree (n_nationkey)
-- CREATE INDEX orders_o_custkey_idx ON tpch.orders USING btree (o_custkey)
-- CREATE INDEX orders_o_orderdate_idx ON tpch.orders USING btree (o_orderdate)
-- CREATE UNIQUE INDEX orders_pkey ON tpch.orders USING btree (o_orderkey)
-- CREATE UNIQUE INDEX part_pkey ON tpch.part USING btree (p_partkey)
-- CREATE UNIQUE INDEX partsupp_pkey ON tpch.partsupp USING btree (ps_partkey, ps_suppkey)
-- CREATE INDEX partsupp_ps_suppkey_idx ON tpch.partsupp USING btree (ps_suppkey)
-- CREATE UNIQUE INDEX region_pkey ON tpch.region USING btree (r_regionkey)
-- CREATE UNIQUE INDEX supplier_pkey ON tpch.supplier USING btree (s_suppkey)
-- CREATE INDEX supplier_s_nationkey_idx ON tpch.supplier USING btree (s_nationkey)
```

Original:
```sql
SELECT *
FROM supplier
WHERE s_suppkey NOT IN (
    SELECT l_suppkey FROM lineitem WHERE l_receiptdate > l_commitdate AND l_shipdate >= DATE '1996-01-01')
  AND s_nationkey IN (SELECT n_nationkey FROM nation WHERE n_name IN ('UNITED KINGDOM', 'IRELAND', 'FRANCE', 'GERMANY'))
ORDER BY s_acctbal DESC;
```

Constraints:
- Preserve exact behaviour and output for every possible input.
- Do not change names, signatures or the set of returned columns.
- Prefer simple, idiomatic changes with a clear algorithmic or I/O benefit.

Respond with the complete optimised SQL statement in a single ```sql fenced code block and nothing else. Do not include explanations, comments or more than one statement.
```

</details>

## tpch_c02 — greencode — benchmarked

speed-up: 330.02050137618096  energy ratio: 69.70761163048897

### Original
```sql
SELECT *
FROM supplier
WHERE s_suppkey NOT IN (
    SELECT l_suppkey FROM lineitem WHERE l_receiptdate > l_commitdate AND l_shipdate >= DATE '1996-01-01')
  AND s_nationkey IN (SELECT n_nationkey FROM nation WHERE n_name IN ('UNITED KINGDOM', 'IRELAND', 'FRANCE', 'GERMANY'))
ORDER BY s_acctbal DESC;
```

### Candidate
```sql
SELECT s_suppkey, s_name, s_address, s_nationkey, s_phone, s_acctbal, s_comment
FROM supplier
WHERE NOT EXISTS (
    SELECT 1
    FROM lineitem
    WHERE l_suppkey = supplier.s_suppkey
      AND l_receiptdate > l_commitdate
      AND l_shipdate >= '1996-01-01'
)
  AND EXISTS (
    SELECT 1
    FROM nation
    WHERE nation.n_nationkey = supplier.s_nationkey
      AND nation.n_name IN ('UNITED KINGDOM', 'IRELAND', 'FRANCE', 'GERMANY')
)
ORDER BY s_acctbal DESC
```

### Test results

- columns: pass
- row_count: pass
- rows: pass

<details><summary>Prompt</summary>

```
Optimise the following PostgreSQL query for execution time and resource usage.

The query runs against this PostgreSQL schema:
```sql
CREATE TABLE customer (c_custkey integer, c_name character varying, c_address character varying, c_nationkey integer, c_phone character, c_acctbal numeric, c_mktsegment character, c_comment character varying);
CREATE TABLE lineitem (l_orderkey integer, l_partkey integer, l_suppkey integer, l_linenumber integer, l_quantity numeric, l_extendedprice numeric, l_discount numeric, l_tax numeric, l_returnflag character, l_linestatus character, l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct character, l_shipmode character, l_comment character varying);
CREATE TABLE nation (n_nationkey integer, n_name character, n_regionkey integer, n_comment character varying);
CREATE TABLE orders (o_orderkey integer, o_custkey integer, o_orderstatus character, o_totalprice numeric, o_orderdate date, o_orderpriority character, o_clerk character, o_shippriority integer, o_comment character varying);
CREATE TABLE part (p_partkey integer, p_name character varying, p_mfgr character, p_brand character, p_type character varying, p_size integer, p_container character, p_retailprice numeric, p_comment character varying);
CREATE TABLE partsupp (ps_partkey integer, ps_suppkey integer, ps_availqty integer, ps_supplycost numeric, ps_comment character varying);
CREATE TABLE region (r_regionkey integer, r_name character, r_comment character varying);
CREATE TABLE supplier (s_suppkey integer, s_name character, s_address character varying, s_nationkey integer, s_phone character, s_acctbal numeric, s_comment character varying);
-- CREATE INDEX customer_c_nationkey_idx ON tpch.customer USING btree (c_nationkey)
-- CREATE UNIQUE INDEX customer_pkey ON tpch.customer USING btree (c_custkey)
-- CREATE INDEX lineitem_l_partkey_idx ON tpch.lineitem USING btree (l_partkey)
-- CREATE INDEX lineitem_l_shipdate_idx ON tpch.lineitem USING btree (l_shipdate)
-- CREATE INDEX lineitem_l_suppkey_idx ON tpch.lineitem USING btree (l_suppkey)
-- CREATE UNIQUE INDEX lineitem_pkey ON tpch.lineitem USING btree (l_orderkey, l_linenumber)
-- CREATE UNIQUE INDEX nation_pkey ON tpch.nation USING btree (n_nationkey)
-- CREATE INDEX orders_o_custkey_idx ON tpch.orders USING btree (o_custkey)
-- CREATE INDEX orders_o_orderdate_idx ON tpch.orders USING btree (o_orderdate)
-- CREATE UNIQUE INDEX orders_pkey ON tpch.orders USING btree (o_orderkey)
-- CREATE UNIQUE INDEX part_pkey ON tpch.part USING btree (p_partkey)
-- CREATE UNIQUE INDEX partsupp_pkey ON tpch.partsupp USING btree (ps_partkey, ps_suppkey)
-- CREATE INDEX partsupp_ps_suppkey_idx ON tpch.partsupp USING btree (ps_suppkey)
-- CREATE UNIQUE INDEX region_pkey ON tpch.region USING btree (r_regionkey)
-- CREATE UNIQUE INDEX supplier_pkey ON tpch.supplier USING btree (s_suppkey)
-- CREATE INDEX supplier_s_nationkey_idx ON tpch.supplier USING btree (s_nationkey)
```

Original:
```sql
SELECT *
FROM supplier
WHERE s_suppkey NOT IN (
    SELECT l_suppkey FROM lineitem WHERE l_receiptdate > l_commitdate AND l_shipdate >= DATE '1996-01-01')
  AND s_nationkey IN (SELECT n_nationkey FROM nation WHERE n_name IN ('UNITED KINGDOM', 'IRELAND', 'FRANCE', 'GERMANY'))
ORDER BY s_acctbal DESC;
```

A static analyser has identified the following specific inefficiencies. Address each one directly. Do not make unrelated changes.

1. [SQL001] select star
   Why it is inefficient: SELECT * returns every column, including ones the consumer never uses. Wider rows mean more I/O, more memory for sorts/hashes and no chance of an index-only scan.
   Suggested change: List only the columns that are actually needed.
   Code: SELECT * FROM supplier WHERE NOT s_suppkey IN (SELECT l_suppkey FROM lineitem WHERE l_receiptdate > l_commitdate AND l_shipdate >= CAST('1996-01-01' AS DATE)) AND s_nationkey IN (SELECT n_nationkey FROM nation WHERE n_name IN ('UNITED KINGDOM', 'IRELAND', 'FRANCE', 'GERMANY')) ORDER BY s_acctbal DES...
2. [SQL005] not in subquery
   Why it is inefficient: NOT IN (subquery) must materialise the full subquery result and returns no rows at all if the subquery yields a NULL; PostgreSQL often cannot plan it as an efficient anti-join.
   Suggested change: Rewrite as `NOT EXISTS (SELECT 1 FROM ... WHERE ...)` or a `LEFT JOIN ... WHERE x IS NULL`.
   Code: NOT s_suppkey IN (SELECT l_suppkey FROM lineitem WHERE l_receiptdate > l_commitdate AND l_shipdate >= CAST('1996-01-01' AS DATE))
3. [SQL009] order by without limit
   Why it is inefficient: The complete result set is sorted even though no LIMIT bounds how many rows are needed.
   Suggested change: Add a LIMIT if only the top rows are used, or drop ORDER BY if ordering is not required by the consumer (sorting in SQL costs O(n log n) and may spill to disk).
   Code: ORDER BY s_acctbal DESC
4. [SQL010] in list subquery could be join
   Why it is inefficient: IN (subquery) is planned as a semi-join; this is often fine, but when the subquery is large or filtered on the outer table a JOIN/EXISTS can be cheaper.
   Suggested change: Consider `EXISTS` or a `JOIN` and compare EXPLAIN costs.
   Code: s_nationkey IN (SELECT n_nationkey FROM nation WHERE n_name IN ('UNITED KINGDOM', 'IRELAND', 'FRANCE', 'GERMANY'))
5. [SQL011] sequential scan on large table
   Why it is inefficient: The planner chose a sequential scan of `lineitem` (~6001215 rows, estimated cost 202610.22).
   Suggested change: Make the predicate index-friendly or add an index on the filtered/joined columns, then re-check EXPLAIN.

Constraints:
- Preserve exact behaviour and output for every possible input.
- Do not change names, signatures or the set of returned columns.
- Prefer simple, idiomatic changes with a clear algorithmic or I/O benefit.

Respond with the complete optimised SQL statement in a single ```sql fenced code block and nothing else. Do not include explanations, comments or more than one statement.
```

</details>

## tpch_c03 — ai_only — rejected (wrong_output)

speed-up: None  energy ratio: None

### Original
```sql
SELECT DISTINCT n.n_name, to_char(o.o_orderdate, 'YYYY-MM') AS month,
       sum(l.l_extendedprice * (1 - l.l_discount)) OVER (PARTITION BY n.n_name, to_char(o.o_orderdate, 'YYYY-MM')) AS revenue
FROM lineitem l
JOIN orders o ON o.o_orderkey = l.l_orderkey
JOIN customer c ON c.c_custkey = o.o_custkey
JOIN nation n ON n.n_nationkey = c.c_nationkey
WHERE extract(year FROM o.o_orderdate) = 1996
ORDER BY n.n_name, month;
```

### Candidate
```sql
SELECT n.n_name, to_char(o.o_orderdate, 'YYYY-MM') AS month,
       sum(l.l_extendedprice * (1 - l.l_discount)) OVER (PARTITION BY n.n_name, to_char(o.o_orderdate, 'YYYY-MM')) AS revenue
FROM lineitem l
JOIN orders o ON o.o_orderkey = l.l_orderkey
JOIN customer c ON c.c_custkey = o.o_custkey
JOIN nation n ON n.n_nationkey = c.c_nationkey
WHERE o.o_orderdate >= '1996-01-01' AND o.o_orderdate < '1997-01-01'
ORDER BY n.n_name, month
```

### Test results

- columns: pass
- row_count: FAIL — wrong_output: row count differs: original 300 vs candidate 200001

<details><summary>Prompt</summary>

```
Optimise the following PostgreSQL query for execution time and resource usage.

The query runs against this PostgreSQL schema:
```sql
CREATE TABLE customer (c_custkey integer, c_name character varying, c_address character varying, c_nationkey integer, c_phone character, c_acctbal numeric, c_mktsegment character, c_comment character varying);
CREATE TABLE lineitem (l_orderkey integer, l_partkey integer, l_suppkey integer, l_linenumber integer, l_quantity numeric, l_extendedprice numeric, l_discount numeric, l_tax numeric, l_returnflag character, l_linestatus character, l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct character, l_shipmode character, l_comment character varying);
CREATE TABLE nation (n_nationkey integer, n_name character, n_regionkey integer, n_comment character varying);
CREATE TABLE orders (o_orderkey integer, o_custkey integer, o_orderstatus character, o_totalprice numeric, o_orderdate date, o_orderpriority character, o_clerk character, o_shippriority integer, o_comment character varying);
CREATE TABLE part (p_partkey integer, p_name character varying, p_mfgr character, p_brand character, p_type character varying, p_size integer, p_container character, p_retailprice numeric, p_comment character varying);
CREATE TABLE partsupp (ps_partkey integer, ps_suppkey integer, ps_availqty integer, ps_supplycost numeric, ps_comment character varying);
CREATE TABLE region (r_regionkey integer, r_name character, r_comment character varying);
CREATE TABLE supplier (s_suppkey integer, s_name character, s_address character varying, s_nationkey integer, s_phone character, s_acctbal numeric, s_comment character varying);
-- CREATE INDEX customer_c_nationkey_idx ON tpch.customer USING btree (c_nationkey)
-- CREATE UNIQUE INDEX customer_pkey ON tpch.customer USING btree (c_custkey)
-- CREATE INDEX lineitem_l_partkey_idx ON tpch.lineitem USING btree (l_partkey)
-- CREATE INDEX lineitem_l_shipdate_idx ON tpch.lineitem USING btree (l_shipdate)
-- CREATE INDEX lineitem_l_suppkey_idx ON tpch.lineitem USING btree (l_suppkey)
-- CREATE UNIQUE INDEX lineitem_pkey ON tpch.lineitem USING btree (l_orderkey, l_linenumber)
-- CREATE UNIQUE INDEX nation_pkey ON tpch.nation USING btree (n_nationkey)
-- CREATE INDEX orders_o_custkey_idx ON tpch.orders USING btree (o_custkey)
-- CREATE INDEX orders_o_orderdate_idx ON tpch.orders USING btree (o_orderdate)
-- CREATE UNIQUE INDEX orders_pkey ON tpch.orders USING btree (o_orderkey)
-- CREATE UNIQUE INDEX part_pkey ON tpch.part USING btree (p_partkey)
-- CREATE UNIQUE INDEX partsupp_pkey ON tpch.partsupp USING btree (ps_partkey, ps_suppkey)
-- CREATE INDEX partsupp_ps_suppkey_idx ON tpch.partsupp USING btree (ps_suppkey)
-- CREATE UNIQUE INDEX region_pkey ON tpch.region USING btree (r_regionkey)
-- CREATE UNIQUE INDEX supplier_pkey ON tpch.supplier USING btree (s_suppkey)
-- CREATE INDEX supplier_s_nationkey_idx ON tpch.supplier USING btree (s_nationkey)
```

Original:
```sql
SELECT DISTINCT n.n_name, to_char(o.o_orderdate, 'YYYY-MM') AS month,
       sum(l.l_extendedprice * (1 - l.l_discount)) OVER (PARTITION BY n.n_name, to_char(o.o_orderdate, 'YYYY-MM')) AS revenue
FROM lineitem l
JOIN orders o ON o.o_orderkey = l.l_orderkey
JOIN customer c ON c.c_custkey = o.o_custkey
JOIN nation n ON n.n_nationkey = c.c_nationkey
WHERE extract(year FROM o.o_orderdate) = 1996
ORDER BY n.n_name, month;
```

Constraints:
- Preserve exact behaviour and output for every possible input.
- Do not change names, signatures or the set of returned columns.
- Prefer simple, idiomatic changes with a clear algorithmic or I/O benefit.

Respond with the complete optimised SQL statement in a single ```sql fenced code block and nothing else. Do not include explanations, comments or more than one statement.
```

</details>

## tpch_c03 — greencode — rejected (wrong_output)

speed-up: None  energy ratio: None

### Original
```sql
SELECT DISTINCT n.n_name, to_char(o.o_orderdate, 'YYYY-MM') AS month,
       sum(l.l_extendedprice * (1 - l.l_discount)) OVER (PARTITION BY n.n_name, to_char(o.o_orderdate, 'YYYY-MM')) AS revenue
FROM lineitem l
JOIN orders o ON o.o_orderkey = l.l_orderkey
JOIN customer c ON c.c_custkey = o.o_custkey
JOIN nation n ON n.n_nationkey = c.c_nationkey
WHERE extract(year FROM o.o_orderdate) = 1996
ORDER BY n.n_name, month;
```

### Candidate
```sql
SELECT n.n_name, to_char(o.o_orderdate, 'YYYY-MM') AS month,
       sum(l.l_extendedprice * (1 - l.l_discount)) OVER (PARTITION BY n.n_name, to_char(o.o_orderdate, 'YYYY-MM')) AS revenue
FROM lineitem l
JOIN orders o ON o.o_orderkey = l.l_orderkey
JOIN customer c ON c.c_custkey = o.o_custkey
JOIN nation n ON n.n_nationkey = c.c_nationkey
WHERE o.o_orderdate >= '1996-01-01' AND o.o_orderdate < '1997-01-01'
ORDER BY n.n_name, month
```

### Test results

- columns: pass
- row_count: FAIL — wrong_output: row count differs: original 300 vs candidate 200001

<details><summary>Prompt</summary>

```
Optimise the following PostgreSQL query for execution time and resource usage.

The query runs against this PostgreSQL schema:
```sql
CREATE TABLE customer (c_custkey integer, c_name character varying, c_address character varying, c_nationkey integer, c_phone character, c_acctbal numeric, c_mktsegment character, c_comment character varying);
CREATE TABLE lineitem (l_orderkey integer, l_partkey integer, l_suppkey integer, l_linenumber integer, l_quantity numeric, l_extendedprice numeric, l_discount numeric, l_tax numeric, l_returnflag character, l_linestatus character, l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct character, l_shipmode character, l_comment character varying);
CREATE TABLE nation (n_nationkey integer, n_name character, n_regionkey integer, n_comment character varying);
CREATE TABLE orders (o_orderkey integer, o_custkey integer, o_orderstatus character, o_totalprice numeric, o_orderdate date, o_orderpriority character, o_clerk character, o_shippriority integer, o_comment character varying);
CREATE TABLE part (p_partkey integer, p_name character varying, p_mfgr character, p_brand character, p_type character varying, p_size integer, p_container character, p_retailprice numeric, p_comment character varying);
CREATE TABLE partsupp (ps_partkey integer, ps_suppkey integer, ps_availqty integer, ps_supplycost numeric, ps_comment character varying);
CREATE TABLE region (r_regionkey integer, r_name character, r_comment character varying);
CREATE TABLE supplier (s_suppkey integer, s_name character, s_address character varying, s_nationkey integer, s_phone character, s_acctbal numeric, s_comment character varying);
-- CREATE INDEX customer_c_nationkey_idx ON tpch.customer USING btree (c_nationkey)
-- CREATE UNIQUE INDEX customer_pkey ON tpch.customer USING btree (c_custkey)
-- CREATE INDEX lineitem_l_partkey_idx ON tpch.lineitem USING btree (l_partkey)
-- CREATE INDEX lineitem_l_shipdate_idx ON tpch.lineitem USING btree (l_shipdate)
-- CREATE INDEX lineitem_l_suppkey_idx ON tpch.lineitem USING btree (l_suppkey)
-- CREATE UNIQUE INDEX lineitem_pkey ON tpch.lineitem USING btree (l_orderkey, l_linenumber)
-- CREATE UNIQUE INDEX nation_pkey ON tpch.nation USING btree (n_nationkey)
-- CREATE INDEX orders_o_custkey_idx ON tpch.orders USING btree (o_custkey)
-- CREATE INDEX orders_o_orderdate_idx ON tpch.orders USING btree (o_orderdate)
-- CREATE UNIQUE INDEX orders_pkey ON tpch.orders USING btree (o_orderkey)
-- CREATE UNIQUE INDEX part_pkey ON tpch.part USING btree (p_partkey)
-- CREATE UNIQUE INDEX partsupp_pkey ON tpch.partsupp USING btree (ps_partkey, ps_suppkey)
-- CREATE INDEX partsupp_ps_suppkey_idx ON tpch.partsupp USING btree (ps_suppkey)
-- CREATE UNIQUE INDEX region_pkey ON tpch.region USING btree (r_regionkey)
-- CREATE UNIQUE INDEX supplier_pkey ON tpch.supplier USING btree (s_suppkey)
-- CREATE INDEX supplier_s_nationkey_idx ON tpch.supplier USING btree (s_nationkey)
```

Original:
```sql
SELECT DISTINCT n.n_name, to_char(o.o_orderdate, 'YYYY-MM') AS month,
       sum(l.l_extendedprice * (1 - l.l_discount)) OVER (PARTITION BY n.n_name, to_char(o.o_orderdate, 'YYYY-MM')) AS revenue
FROM lineitem l
JOIN orders o ON o.o_orderkey = l.l_orderkey
JOIN customer c ON c.c_custkey = o.o_custkey
JOIN nation n ON n.n_nationkey = c.c_nationkey
WHERE extract(year FROM o.o_orderdate) = 1996
ORDER BY n.n_name, month;
```

A static analyser has identified the following specific inefficiencies. Address each one directly. Do not make unrelated changes.

1. [SQL003] non sargable predicate
   Why it is inefficient: The column `o.o_orderdate` is wrapped in `EXTRACT(YEAR FROM o.o_orderdate)` before comparison. PostgreSQL cannot use a plain B-tree index on the column for this predicate and must evaluate the expression for every row.
   Suggested change: Rewrite the predicate so the bare column is compared to a constant/range (e.g. `date_col >= '2024-01-01' AND date_col < '2025-01-01'` instead of `EXTRACT(YEAR FROM date_col) = 2024`; `email = lower($1)` instead of `lower(email) = $1`), or create an expression index.
   Code: EXTRACT(YEAR FROM o.o_orderdate) = 1996
2. [SQL007] distinct with group or join
   Why it is inefficient: DISTINCT over a joined result de-duplicates after the join has multiplied rows; the join output must be fully hashed or sorted.
   Suggested change: Filter with EXISTS (semi-join) or aggregate before joining so duplicates are never produced.
   Code: SELECT DISTINCT n.n_name, TO_CHAR(o.o_orderdate, 'YYYY-MM') AS month, SUM(l.l_extendedprice * (1 - l.l_discount)) OVER (PARTITION BY n.n_name, TO_CHAR(o.o_orderdate, 'YYYY-MM')) AS revenue FROM lineitem AS l JOIN orders AS o ON o.o_orderkey = l.l_orderkey JOIN customer AS c ON c.c_custkey = o.o_cust...
3. [SQL009] order by without limit
   Why it is inefficient: The complete result set is sorted even though no LIMIT bounds how many rows are needed.
   Suggested change: Add a LIMIT if only the top rows are used, or drop ORDER BY if ordering is not required by the consumer (sorting in SQL costs O(n log n) and may spill to disk).
   Code: ORDER BY n.n_name, month
4. [SQL011] sequential scan on large table
   Why it is inefficient: The planner chose a sequential scan of `customer` (~150000 rows, estimated cost 4225.0).
   Suggested change: Make the predicate index-friendly or add an index on the filtered/joined columns, then re-check EXPLAIN.
5. [SQL011] sequential scan on large table
   Why it is inefficient: The planner chose a sequential scan of `orders` (~1500000 rows, estimated cost 35511.0).
   Suggested change: Make the predicate index-friendly or add an index on the filtered/joined columns, then re-check EXPLAIN.

Constraints:
- Preserve exact behaviour and output for every possible input.
- Do not change names, signatures or the set of returned columns.
- Prefer simple, idiomatic changes with a clear algorithmic or I/O benefit.

Respond with the complete optimised SQL statement in a single ```sql fenced code block and nothing else. Do not include explanations, comments or more than one statement.
```

</details>

## tpch_c04 — ai_only — benchmarked

speed-up: 1.2630211490470287  energy ratio: 1.3054717412024797

### Original
```sql
SELECT p.p_partkey, p.p_name, p.p_retailprice,
       (SELECT avg(l.l_extendedprice / l.l_quantity) FROM lineitem l WHERE l.l_partkey = p.p_partkey) AS avg_unit_price
FROM part p
WHERE p.p_partkey IN (SELECT l_partkey FROM lineitem WHERE l_shipmode = 'AIR')
  AND p.p_brand = 'Brand#13'
  AND (SELECT avg(l.l_extendedprice / l.l_quantity) FROM lineitem l WHERE l.l_partkey = p.p_partkey) > p.p_retailprice * 1.05
ORDER BY avg_unit_price DESC
LIMIT 100;
```

### Candidate
```sql
SELECT p.p_partkey, p.p_name, p.p_retailprice,
       l.avg_unit_price
FROM part p
JOIN (
    SELECT l_partkey, avg(l_extendedprice / l_quantity) AS avg_unit_price
    FROM lineitem
    WHERE l_shipmode = 'AIR'
    GROUP BY l_partkey
) l ON p.p_partkey = l.l_partkey
WHERE p.p_brand = 'Brand#13'
  AND l.avg_unit_price > p.p_retailprice * 1.05
ORDER BY l.avg_unit_price DESC
LIMIT 100
```

### Test results

- columns: pass
- row_count: pass
- rows: pass

<details><summary>Prompt</summary>

```
Optimise the following PostgreSQL query for execution time and resource usage.

The query runs against this PostgreSQL schema:
```sql
CREATE TABLE customer (c_custkey integer, c_name character varying, c_address character varying, c_nationkey integer, c_phone character, c_acctbal numeric, c_mktsegment character, c_comment character varying);
CREATE TABLE lineitem (l_orderkey integer, l_partkey integer, l_suppkey integer, l_linenumber integer, l_quantity numeric, l_extendedprice numeric, l_discount numeric, l_tax numeric, l_returnflag character, l_linestatus character, l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct character, l_shipmode character, l_comment character varying);
CREATE TABLE nation (n_nationkey integer, n_name character, n_regionkey integer, n_comment character varying);
CREATE TABLE orders (o_orderkey integer, o_custkey integer, o_orderstatus character, o_totalprice numeric, o_orderdate date, o_orderpriority character, o_clerk character, o_shippriority integer, o_comment character varying);
CREATE TABLE part (p_partkey integer, p_name character varying, p_mfgr character, p_brand character, p_type character varying, p_size integer, p_container character, p_retailprice numeric, p_comment character varying);
CREATE TABLE partsupp (ps_partkey integer, ps_suppkey integer, ps_availqty integer, ps_supplycost numeric, ps_comment character varying);
CREATE TABLE region (r_regionkey integer, r_name character, r_comment character varying);
CREATE TABLE supplier (s_suppkey integer, s_name character, s_address character varying, s_nationkey integer, s_phone character, s_acctbal numeric, s_comment character varying);
-- CREATE INDEX customer_c_nationkey_idx ON tpch.customer USING btree (c_nationkey)
-- CREATE UNIQUE INDEX customer_pkey ON tpch.customer USING btree (c_custkey)
-- CREATE INDEX lineitem_l_partkey_idx ON tpch.lineitem USING btree (l_partkey)
-- CREATE INDEX lineitem_l_shipdate_idx ON tpch.lineitem USING btree (l_shipdate)
-- CREATE INDEX lineitem_l_suppkey_idx ON tpch.lineitem USING btree (l_suppkey)
-- CREATE UNIQUE INDEX lineitem_pkey ON tpch.lineitem USING btree (l_orderkey, l_linenumber)
-- CREATE UNIQUE INDEX nation_pkey ON tpch.nation USING btree (n_nationkey)
-- CREATE INDEX orders_o_custkey_idx ON tpch.orders USING btree (o_custkey)
-- CREATE INDEX orders_o_orderdate_idx ON tpch.orders USING btree (o_orderdate)
-- CREATE UNIQUE INDEX orders_pkey ON tpch.orders USING btree (o_orderkey)
-- CREATE UNIQUE INDEX part_pkey ON tpch.part USING btree (p_partkey)
-- CREATE UNIQUE INDEX partsupp_pkey ON tpch.partsupp USING btree (ps_partkey, ps_suppkey)
-- CREATE INDEX partsupp_ps_suppkey_idx ON tpch.partsupp USING btree (ps_suppkey)
-- CREATE UNIQUE INDEX region_pkey ON tpch.region USING btree (r_regionkey)
-- CREATE UNIQUE INDEX supplier_pkey ON tpch.supplier USING btree (s_suppkey)
-- CREATE INDEX supplier_s_nationkey_idx ON tpch.supplier USING btree (s_nationkey)
```

Original:
```sql
SELECT p.p_partkey, p.p_name, p.p_retailprice,
       (SELECT avg(l.l_extendedprice / l.l_quantity) FROM lineitem l WHERE l.l_partkey = p.p_partkey) AS avg_unit_price
FROM part p
WHERE p.p_partkey IN (SELECT l_partkey FROM lineitem WHERE l_shipmode = 'AIR')
  AND p.p_brand = 'Brand#13'
  AND (SELECT avg(l.l_extendedprice / l.l_quantity) FROM lineitem l WHERE l.l_partkey = p.p_partkey) > p.p_retailprice * 1.05
ORDER BY avg_unit_price DESC
LIMIT 100;
```

Constraints:
- Preserve exact behaviour and output for every possible input.
- Do not change names, signatures or the set of returned columns.
- Prefer simple, idiomatic changes with a clear algorithmic or I/O benefit.

Respond with the complete optimised SQL statement in a single ```sql fenced code block and nothing else. Do not include explanations, comments or more than one statement.
```

</details>

## tpch_c04 — greencode — benchmarked

speed-up: 1.3833284800902157  energy ratio: 0.23171313803772994

### Original
```sql
SELECT p.p_partkey, p.p_name, p.p_retailprice,
       (SELECT avg(l.l_extendedprice / l.l_quantity) FROM lineitem l WHERE l.l_partkey = p.p_partkey) AS avg_unit_price
FROM part p
WHERE p.p_partkey IN (SELECT l_partkey FROM lineitem WHERE l_shipmode = 'AIR')
  AND p.p_brand = 'Brand#13'
  AND (SELECT avg(l.l_extendedprice / l.l_quantity) FROM lineitem l WHERE l.l_partkey = p.p_partkey) > p.p_retailprice * 1.05
ORDER BY avg_unit_price DESC
LIMIT 100;
```

### Candidate
```sql
WITH avg_unit_price AS (
    SELECT l_partkey, AVG(l_extendedprice / l_quantity) AS avg_unit_price
    FROM lineitem
    GROUP BY l_partkey
)
SELECT p.p_partkey, p.p_name, p.p_retailprice, a.avg_unit_price
FROM part p
JOIN avg_unit_price a ON p.p_partkey = a.l_partkey
JOIN lineitem l ON p.p_partkey = l.l_partkey AND l.l_shipmode = 'AIR'
WHERE p.p_brand = 'Brand#13'
  AND a.avg_unit_price > p.p_retailprice * 1.05
ORDER BY a.avg_unit_price DESC
LIMIT 100
```

### Test results

- columns: pass
- row_count: pass
- rows: pass

<details><summary>Prompt</summary>

```
Optimise the following PostgreSQL query for execution time and resource usage.

The query runs against this PostgreSQL schema:
```sql
CREATE TABLE customer (c_custkey integer, c_name character varying, c_address character varying, c_nationkey integer, c_phone character, c_acctbal numeric, c_mktsegment character, c_comment character varying);
CREATE TABLE lineitem (l_orderkey integer, l_partkey integer, l_suppkey integer, l_linenumber integer, l_quantity numeric, l_extendedprice numeric, l_discount numeric, l_tax numeric, l_returnflag character, l_linestatus character, l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct character, l_shipmode character, l_comment character varying);
CREATE TABLE nation (n_nationkey integer, n_name character, n_regionkey integer, n_comment character varying);
CREATE TABLE orders (o_orderkey integer, o_custkey integer, o_orderstatus character, o_totalprice numeric, o_orderdate date, o_orderpriority character, o_clerk character, o_shippriority integer, o_comment character varying);
CREATE TABLE part (p_partkey integer, p_name character varying, p_mfgr character, p_brand character, p_type character varying, p_size integer, p_container character, p_retailprice numeric, p_comment character varying);
CREATE TABLE partsupp (ps_partkey integer, ps_suppkey integer, ps_availqty integer, ps_supplycost numeric, ps_comment character varying);
CREATE TABLE region (r_regionkey integer, r_name character, r_comment character varying);
CREATE TABLE supplier (s_suppkey integer, s_name character, s_address character varying, s_nationkey integer, s_phone character, s_acctbal numeric, s_comment character varying);
-- CREATE INDEX customer_c_nationkey_idx ON tpch.customer USING btree (c_nationkey)
-- CREATE UNIQUE INDEX customer_pkey ON tpch.customer USING btree (c_custkey)
-- CREATE INDEX lineitem_l_partkey_idx ON tpch.lineitem USING btree (l_partkey)
-- CREATE INDEX lineitem_l_shipdate_idx ON tpch.lineitem USING btree (l_shipdate)
-- CREATE INDEX lineitem_l_suppkey_idx ON tpch.lineitem USING btree (l_suppkey)
-- CREATE UNIQUE INDEX lineitem_pkey ON tpch.lineitem USING btree (l_orderkey, l_linenumber)
-- CREATE UNIQUE INDEX nation_pkey ON tpch.nation USING btree (n_nationkey)
-- CREATE INDEX orders_o_custkey_idx ON tpch.orders USING btree (o_custkey)
-- CREATE INDEX orders_o_orderdate_idx ON tpch.orders USING btree (o_orderdate)
-- CREATE UNIQUE INDEX orders_pkey ON tpch.orders USING btree (o_orderkey)
-- CREATE UNIQUE INDEX part_pkey ON tpch.part USING btree (p_partkey)
-- CREATE UNIQUE INDEX partsupp_pkey ON tpch.partsupp USING btree (ps_partkey, ps_suppkey)
-- CREATE INDEX partsupp_ps_suppkey_idx ON tpch.partsupp USING btree (ps_suppkey)
-- CREATE UNIQUE INDEX region_pkey ON tpch.region USING btree (r_regionkey)
-- CREATE UNIQUE INDEX supplier_pkey ON tpch.supplier USING btree (s_suppkey)
-- CREATE INDEX supplier_s_nationkey_idx ON tpch.supplier USING btree (s_nationkey)
```

Original:
```sql
SELECT p.p_partkey, p.p_name, p.p_retailprice,
       (SELECT avg(l.l_extendedprice / l.l_quantity) FROM lineitem l WHERE l.l_partkey = p.p_partkey) AS avg_unit_price
FROM part p
WHERE p.p_partkey IN (SELECT l_partkey FROM lineitem WHERE l_shipmode = 'AIR')
  AND p.p_brand = 'Brand#13'
  AND (SELECT avg(l.l_extendedprice / l.l_quantity) FROM lineitem l WHERE l.l_partkey = p.p_partkey) > p.p_retailprice * 1.05
ORDER BY avg_unit_price DESC
LIMIT 100;
```

A static analyser has identified the following specific inefficiencies. Address each one directly. Do not make unrelated changes.

1. [SQL006] correlated subquery in select
   Why it is inefficient: A subquery in the SELECT list references the outer query, so it is evaluated once per outer row.
   Suggested change: Rewrite as a JOIN to a pre-aggregated derived table (GROUP BY the key) or a LATERAL join.
   Code: (SELECT AVG(l.l_extendedprice / l.l_quantity) FROM lineitem AS l WHERE l.l_partkey = p.p_partkey)
2. [SQL010] in list subquery could be join
   Why it is inefficient: IN (subquery) is planned as a semi-join; this is often fine, but when the subquery is large or filtered on the outer table a JOIN/EXISTS can be cheaper.
   Suggested change: Consider `EXISTS` or a `JOIN` and compare EXPLAIN costs.
   Code: p.p_partkey IN (SELECT l_partkey FROM lineitem WHERE l_shipmode = 'AIR')
3. [SQL011] sequential scan on large table
   Why it is inefficient: The planner chose a sequential scan of `lineitem` (~6001215 rows, estimated cost 187607.19).
   Suggested change: Make the predicate index-friendly or add an index on the filtered/joined columns, then re-check EXPLAIN.

Constraints:
- Preserve exact behaviour and output for every possible input.
- Do not change names, signatures or the set of returned columns.
- Prefer simple, idiomatic changes with a clear algorithmic or I/O benefit.

Respond with the complete optimised SQL statement in a single ```sql fenced code block and nothing else. Do not include explanations, comments or more than one statement.
```

</details>

## tpch_c05 — ai_only — benchmarked

speed-up: 0.7902886244633279  energy ratio: 0.6172025929909678

### Original
```sql
SELECT o.o_orderkey, o.o_orderdate, o.o_totalprice
FROM orders o
WHERE o.o_orderdate BETWEEN DATE '1997-01-01' AND DATE '1997-03-31'
  AND (SELECT count(*) FROM lineitem l WHERE l.l_orderkey = o.o_orderkey AND l.l_returnflag = 'R') > 0
  AND o.o_comment LIKE '%unusual%'
ORDER BY o.o_totalprice DESC;
```

### Candidate
```sql
SELECT o.o_orderkey, o.o_orderdate, o.o_totalprice
FROM orders o
JOIN lineitem l ON o.o_orderkey = l.l_orderkey AND l.l_returnflag = 'R'
WHERE o.o_orderdate BETWEEN DATE '1997-01-01' AND DATE '1997-03-31'
  AND o.o_comment LIKE '%unusual%'
ORDER BY o.o_totalprice DESC
```

### Test results

- columns: pass
- row_count: pass
- rows: pass

<details><summary>Prompt</summary>

```
Optimise the following PostgreSQL query for execution time and resource usage.

The query runs against this PostgreSQL schema:
```sql
CREATE TABLE customer (c_custkey integer, c_name character varying, c_address character varying, c_nationkey integer, c_phone character, c_acctbal numeric, c_mktsegment character, c_comment character varying);
CREATE TABLE lineitem (l_orderkey integer, l_partkey integer, l_suppkey integer, l_linenumber integer, l_quantity numeric, l_extendedprice numeric, l_discount numeric, l_tax numeric, l_returnflag character, l_linestatus character, l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct character, l_shipmode character, l_comment character varying);
CREATE TABLE nation (n_nationkey integer, n_name character, n_regionkey integer, n_comment character varying);
CREATE TABLE orders (o_orderkey integer, o_custkey integer, o_orderstatus character, o_totalprice numeric, o_orderdate date, o_orderpriority character, o_clerk character, o_shippriority integer, o_comment character varying);
CREATE TABLE part (p_partkey integer, p_name character varying, p_mfgr character, p_brand character, p_type character varying, p_size integer, p_container character, p_retailprice numeric, p_comment character varying);
CREATE TABLE partsupp (ps_partkey integer, ps_suppkey integer, ps_availqty integer, ps_supplycost numeric, ps_comment character varying);
CREATE TABLE region (r_regionkey integer, r_name character, r_comment character varying);
CREATE TABLE supplier (s_suppkey integer, s_name character, s_address character varying, s_nationkey integer, s_phone character, s_acctbal numeric, s_comment character varying);
-- CREATE INDEX customer_c_nationkey_idx ON tpch.customer USING btree (c_nationkey)
-- CREATE UNIQUE INDEX customer_pkey ON tpch.customer USING btree (c_custkey)
-- CREATE INDEX lineitem_l_partkey_idx ON tpch.lineitem USING btree (l_partkey)
-- CREATE INDEX lineitem_l_shipdate_idx ON tpch.lineitem USING btree (l_shipdate)
-- CREATE INDEX lineitem_l_suppkey_idx ON tpch.lineitem USING btree (l_suppkey)
-- CREATE UNIQUE INDEX lineitem_pkey ON tpch.lineitem USING btree (l_orderkey, l_linenumber)
-- CREATE UNIQUE INDEX nation_pkey ON tpch.nation USING btree (n_nationkey)
-- CREATE INDEX orders_o_custkey_idx ON tpch.orders USING btree (o_custkey)
-- CREATE INDEX orders_o_orderdate_idx ON tpch.orders USING btree (o_orderdate)
-- CREATE UNIQUE INDEX orders_pkey ON tpch.orders USING btree (o_orderkey)
-- CREATE UNIQUE INDEX part_pkey ON tpch.part USING btree (p_partkey)
-- CREATE UNIQUE INDEX partsupp_pkey ON tpch.partsupp USING btree (ps_partkey, ps_suppkey)
-- CREATE INDEX partsupp_ps_suppkey_idx ON tpch.partsupp USING btree (ps_suppkey)
-- CREATE UNIQUE INDEX region_pkey ON tpch.region USING btree (r_regionkey)
-- CREATE UNIQUE INDEX supplier_pkey ON tpch.supplier USING btree (s_suppkey)
-- CREATE INDEX supplier_s_nationkey_idx ON tpch.supplier USING btree (s_nationkey)
```

Original:
```sql
SELECT o.o_orderkey, o.o_orderdate, o.o_totalprice
FROM orders o
WHERE o.o_orderdate BETWEEN DATE '1997-01-01' AND DATE '1997-03-31'
  AND (SELECT count(*) FROM lineitem l WHERE l.l_orderkey = o.o_orderkey AND l.l_returnflag = 'R') > 0
  AND o.o_comment LIKE '%unusual%'
ORDER BY o.o_totalprice DESC;
```

Constraints:
- Preserve exact behaviour and output for every possible input.
- Do not change names, signatures or the set of returned columns.
- Prefer simple, idiomatic changes with a clear algorithmic or I/O benefit.

Respond with the complete optimised SQL statement in a single ```sql fenced code block and nothing else. Do not include explanations, comments or more than one statement.
```

</details>

## tpch_c05 — greencode — benchmarked

speed-up: 0.7064360568895031  energy ratio: 0.5273983722178046

### Original
```sql
SELECT o.o_orderkey, o.o_orderdate, o.o_totalprice
FROM orders o
WHERE o.o_orderdate BETWEEN DATE '1997-01-01' AND DATE '1997-03-31'
  AND (SELECT count(*) FROM lineitem l WHERE l.l_orderkey = o.o_orderkey AND l.l_returnflag = 'R') > 0
  AND o.o_comment LIKE '%unusual%'
ORDER BY o.o_totalprice DESC;
```

### Candidate
```sql
SELECT o.o_orderkey, o.o_orderdate, o.o_totalprice
FROM orders o
WHERE o.o_orderdate BETWEEN DATE '1997-01-01' AND DATE '1997-03-31'
  AND EXISTS (SELECT 1 FROM lineitem l WHERE l.l_orderkey = o.o_orderkey AND l.l_returnflag = 'R')
  AND o.o_comment LIKE '%unusual%'
ORDER BY o.o_totalprice DESC
LIMIT 100
```

### Test results

- columns: pass
- row_count: pass
- rows: pass

<details><summary>Prompt</summary>

```
Optimise the following PostgreSQL query for execution time and resource usage.

The query runs against this PostgreSQL schema:
```sql
CREATE TABLE customer (c_custkey integer, c_name character varying, c_address character varying, c_nationkey integer, c_phone character, c_acctbal numeric, c_mktsegment character, c_comment character varying);
CREATE TABLE lineitem (l_orderkey integer, l_partkey integer, l_suppkey integer, l_linenumber integer, l_quantity numeric, l_extendedprice numeric, l_discount numeric, l_tax numeric, l_returnflag character, l_linestatus character, l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct character, l_shipmode character, l_comment character varying);
CREATE TABLE nation (n_nationkey integer, n_name character, n_regionkey integer, n_comment character varying);
CREATE TABLE orders (o_orderkey integer, o_custkey integer, o_orderstatus character, o_totalprice numeric, o_orderdate date, o_orderpriority character, o_clerk character, o_shippriority integer, o_comment character varying);
CREATE TABLE part (p_partkey integer, p_name character varying, p_mfgr character, p_brand character, p_type character varying, p_size integer, p_container character, p_retailprice numeric, p_comment character varying);
CREATE TABLE partsupp (ps_partkey integer, ps_suppkey integer, ps_availqty integer, ps_supplycost numeric, ps_comment character varying);
CREATE TABLE region (r_regionkey integer, r_name character, r_comment character varying);
CREATE TABLE supplier (s_suppkey integer, s_name character, s_address character varying, s_nationkey integer, s_phone character, s_acctbal numeric, s_comment character varying);
-- CREATE INDEX customer_c_nationkey_idx ON tpch.customer USING btree (c_nationkey)
-- CREATE UNIQUE INDEX customer_pkey ON tpch.customer USING btree (c_custkey)
-- CREATE INDEX lineitem_l_partkey_idx ON tpch.lineitem USING btree (l_partkey)
-- CREATE INDEX lineitem_l_shipdate_idx ON tpch.lineitem USING btree (l_shipdate)
-- CREATE INDEX lineitem_l_suppkey_idx ON tpch.lineitem USING btree (l_suppkey)
-- CREATE UNIQUE INDEX lineitem_pkey ON tpch.lineitem USING btree (l_orderkey, l_linenumber)
-- CREATE UNIQUE INDEX nation_pkey ON tpch.nation USING btree (n_nationkey)
-- CREATE INDEX orders_o_custkey_idx ON tpch.orders USING btree (o_custkey)
-- CREATE INDEX orders_o_orderdate_idx ON tpch.orders USING btree (o_orderdate)
-- CREATE UNIQUE INDEX orders_pkey ON tpch.orders USING btree (o_orderkey)
-- CREATE UNIQUE INDEX part_pkey ON tpch.part USING btree (p_partkey)
-- CREATE UNIQUE INDEX partsupp_pkey ON tpch.partsupp USING btree (ps_partkey, ps_suppkey)
-- CREATE INDEX partsupp_ps_suppkey_idx ON tpch.partsupp USING btree (ps_suppkey)
-- CREATE UNIQUE INDEX region_pkey ON tpch.region USING btree (r_regionkey)
-- CREATE UNIQUE INDEX supplier_pkey ON tpch.supplier USING btree (s_suppkey)
-- CREATE INDEX supplier_s_nationkey_idx ON tpch.supplier USING btree (s_nationkey)
```

Original:
```sql
SELECT o.o_orderkey, o.o_orderdate, o.o_totalprice
FROM orders o
WHERE o.o_orderdate BETWEEN DATE '1997-01-01' AND DATE '1997-03-31'
  AND (SELECT count(*) FROM lineitem l WHERE l.l_orderkey = o.o_orderkey AND l.l_returnflag = 'R') > 0
  AND o.o_comment LIKE '%unusual%'
ORDER BY o.o_totalprice DESC;
```

A static analyser has identified the following specific inefficiencies. Address each one directly. Do not make unrelated changes.

1. [SQL004] leading wildcard like
   Why it is inefficient: The pattern `%unusual%` starts with a wildcard, so no B-tree index on the column can be used and every row is compared.
   Suggested change: Anchor the pattern (`'abc%'`) if the semantics allow, or use a trigram index (`pg_trgm`) / full-text search for substring matching.
   Code: o.o_comment LIKE '%unusual%'
2. [SQL009] order by without limit
   Why it is inefficient: The complete result set is sorted even though no LIMIT bounds how many rows are needed.
   Suggested change: Add a LIMIT if only the top rows are used, or drop ORDER BY if ordering is not required by the consumer (sorting in SQL costs O(n log n) and may spill to disk).
   Code: ORDER BY o.o_totalprice DESC
3. [SQL012] count star subquery for existence
   Why it is inefficient: COUNT(*) in the subquery must visit every matching row to produce a number that is only compared with zero.
   Suggested change: Use `EXISTS (SELECT 1 ... )`, which stops at the first matching row.
   Code: (SELECT COUNT(*) FROM lineitem AS l WHERE l.l_orderkey = o.o_orderkey AND l.l_returnflag = 'R') > 0

Constraints:
- Preserve exact behaviour and output for every possible input.
- Do not change names, signatures or the set of returned columns.
- Prefer simple, idiomatic changes with a clear algorithmic or I/O benefit.

Respond with the complete optimised SQL statement in a single ```sql fenced code block and nothing else. Do not include explanations, comments or more than one statement.
```

</details>

## tpch_c06 — ai_only — benchmarked

speed-up: 0.5338018007631274  energy ratio: 1.6122857106382185

### Original
```sql
SELECT DISTINCT r.r_name, c.c_custkey, c.c_name, sum(o.o_totalprice) AS total
FROM region r
JOIN nation n ON n.n_regionkey = r.r_regionkey
JOIN customer c ON c.c_nationkey = n.n_nationkey
JOIN orders o ON o.o_custkey = c.c_custkey
WHERE o.o_orderkey * 1 > 0
  AND o.o_orderdate + INTERVAL '0 day' >= DATE '1998-01-01'
GROUP BY r.r_name, c.c_custkey, c.c_name
HAVING sum(o.o_totalprice) > 500000
ORDER BY r.r_name, total DESC;
```

### Candidate
```sql
SELECT r.r_name, c.c_custkey, c.c_name, sum(o.o_totalprice) AS total
FROM region r
JOIN nation n ON n.n_regionkey = r.r_regionkey
JOIN customer c ON c.c_nationkey = n.n_nationkey
JOIN orders o ON o.o_custkey = c.c_custkey
WHERE o.o_orderdate >= '1998-01-01'
GROUP BY r.r_name, c.c_custkey, c.c_name
HAVING sum(o.o_totalprice) > 500000
ORDER BY r.r_name, total DESC
```

### Test results

- columns: pass
- row_count: pass
- rows: pass

<details><summary>Prompt</summary>

```
Optimise the following PostgreSQL query for execution time and resource usage.

The query runs against this PostgreSQL schema:
```sql
CREATE TABLE customer (c_custkey integer, c_name character varying, c_address character varying, c_nationkey integer, c_phone character, c_acctbal numeric, c_mktsegment character, c_comment character varying);
CREATE TABLE lineitem (l_orderkey integer, l_partkey integer, l_suppkey integer, l_linenumber integer, l_quantity numeric, l_extendedprice numeric, l_discount numeric, l_tax numeric, l_returnflag character, l_linestatus character, l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct character, l_shipmode character, l_comment character varying);
CREATE TABLE nation (n_nationkey integer, n_name character, n_regionkey integer, n_comment character varying);
CREATE TABLE orders (o_orderkey integer, o_custkey integer, o_orderstatus character, o_totalprice numeric, o_orderdate date, o_orderpriority character, o_clerk character, o_shippriority integer, o_comment character varying);
CREATE TABLE part (p_partkey integer, p_name character varying, p_mfgr character, p_brand character, p_type character varying, p_size integer, p_container character, p_retailprice numeric, p_comment character varying);
CREATE TABLE partsupp (ps_partkey integer, ps_suppkey integer, ps_availqty integer, ps_supplycost numeric, ps_comment character varying);
CREATE TABLE region (r_regionkey integer, r_name character, r_comment character varying);
CREATE TABLE supplier (s_suppkey integer, s_name character, s_address character varying, s_nationkey integer, s_phone character, s_acctbal numeric, s_comment character varying);
-- CREATE INDEX customer_c_nationkey_idx ON tpch.customer USING btree (c_nationkey)
-- CREATE UNIQUE INDEX customer_pkey ON tpch.customer USING btree (c_custkey)
-- CREATE INDEX lineitem_l_partkey_idx ON tpch.lineitem USING btree (l_partkey)
-- CREATE INDEX lineitem_l_shipdate_idx ON tpch.lineitem USING btree (l_shipdate)
-- CREATE INDEX lineitem_l_suppkey_idx ON tpch.lineitem USING btree (l_suppkey)
-- CREATE UNIQUE INDEX lineitem_pkey ON tpch.lineitem USING btree (l_orderkey, l_linenumber)
-- CREATE UNIQUE INDEX nation_pkey ON tpch.nation USING btree (n_nationkey)
-- CREATE INDEX orders_o_custkey_idx ON tpch.orders USING btree (o_custkey)
-- CREATE INDEX orders_o_orderdate_idx ON tpch.orders USING btree (o_orderdate)
-- CREATE UNIQUE INDEX orders_pkey ON tpch.orders USING btree (o_orderkey)
-- CREATE UNIQUE INDEX part_pkey ON tpch.part USING btree (p_partkey)
-- CREATE UNIQUE INDEX partsupp_pkey ON tpch.partsupp USING btree (ps_partkey, ps_suppkey)
-- CREATE INDEX partsupp_ps_suppkey_idx ON tpch.partsupp USING btree (ps_suppkey)
-- CREATE UNIQUE INDEX region_pkey ON tpch.region USING btree (r_regionkey)
-- CREATE UNIQUE INDEX supplier_pkey ON tpch.supplier USING btree (s_suppkey)
-- CREATE INDEX supplier_s_nationkey_idx ON tpch.supplier USING btree (s_nationkey)
```

Original:
```sql
SELECT DISTINCT r.r_name, c.c_custkey, c.c_name, sum(o.o_totalprice) AS total
FROM region r
JOIN nation n ON n.n_regionkey = r.r_regionkey
JOIN customer c ON c.c_nationkey = n.n_nationkey
JOIN orders o ON o.o_custkey = c.c_custkey
WHERE o.o_orderkey * 1 > 0
  AND o.o_orderdate + INTERVAL '0 day' >= DATE '1998-01-01'
GROUP BY r.r_name, c.c_custkey, c.c_name
HAVING sum(o.o_totalprice) > 500000
ORDER BY r.r_name, total DESC;
```

Constraints:
- Preserve exact behaviour and output for every possible input.
- Do not change names, signatures or the set of returned columns.
- Prefer simple, idiomatic changes with a clear algorithmic or I/O benefit.

Respond with the complete optimised SQL statement in a single ```sql fenced code block and nothing else. Do not include explanations, comments or more than one statement.
```

</details>

## tpch_c06 — greencode — benchmarked

speed-up: 0.8437654837708918  energy ratio: 1.3079758647722712

### Original
```sql
SELECT DISTINCT r.r_name, c.c_custkey, c.c_name, sum(o.o_totalprice) AS total
FROM region r
JOIN nation n ON n.n_regionkey = r.r_regionkey
JOIN customer c ON c.c_nationkey = n.n_nationkey
JOIN orders o ON o.o_custkey = c.c_custkey
WHERE o.o_orderkey * 1 > 0
  AND o.o_orderdate + INTERVAL '0 day' >= DATE '1998-01-01'
GROUP BY r.r_name, c.c_custkey, c.c_name
HAVING sum(o.o_totalprice) > 500000
ORDER BY r.r_name, total DESC;
```

### Candidate
```sql
SELECT r.r_name, c.c_custkey, c.c_name, SUM(o.o_totalprice) AS total
FROM region r
JOIN nation n ON n.n_regionkey = r.r_regionkey
JOIN customer c ON c.c_nationkey = n.n_nationkey
JOIN orders o ON o.o_custkey = c.c_custkey
WHERE o.o_orderkey > 0
  AND o.o_orderdate >= '1998-01-01'
GROUP BY r.r_name, c.c_custkey, c.c_name
HAVING SUM(o.o_totalprice) > 500000
ORDER BY r.r_name, total DESC
```

### Test results

- columns: pass
- row_count: pass
- rows: pass

<details><summary>Prompt</summary>

```
Optimise the following PostgreSQL query for execution time and resource usage.

The query runs against this PostgreSQL schema:
```sql
CREATE TABLE customer (c_custkey integer, c_name character varying, c_address character varying, c_nationkey integer, c_phone character, c_acctbal numeric, c_mktsegment character, c_comment character varying);
CREATE TABLE lineitem (l_orderkey integer, l_partkey integer, l_suppkey integer, l_linenumber integer, l_quantity numeric, l_extendedprice numeric, l_discount numeric, l_tax numeric, l_returnflag character, l_linestatus character, l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct character, l_shipmode character, l_comment character varying);
CREATE TABLE nation (n_nationkey integer, n_name character, n_regionkey integer, n_comment character varying);
CREATE TABLE orders (o_orderkey integer, o_custkey integer, o_orderstatus character, o_totalprice numeric, o_orderdate date, o_orderpriority character, o_clerk character, o_shippriority integer, o_comment character varying);
CREATE TABLE part (p_partkey integer, p_name character varying, p_mfgr character, p_brand character, p_type character varying, p_size integer, p_container character, p_retailprice numeric, p_comment character varying);
CREATE TABLE partsupp (ps_partkey integer, ps_suppkey integer, ps_availqty integer, ps_supplycost numeric, ps_comment character varying);
CREATE TABLE region (r_regionkey integer, r_name character, r_comment character varying);
CREATE TABLE supplier (s_suppkey integer, s_name character, s_address character varying, s_nationkey integer, s_phone character, s_acctbal numeric, s_comment character varying);
-- CREATE INDEX customer_c_nationkey_idx ON tpch.customer USING btree (c_nationkey)
-- CREATE UNIQUE INDEX customer_pkey ON tpch.customer USING btree (c_custkey)
-- CREATE INDEX lineitem_l_partkey_idx ON tpch.lineitem USING btree (l_partkey)
-- CREATE INDEX lineitem_l_shipdate_idx ON tpch.lineitem USING btree (l_shipdate)
-- CREATE INDEX lineitem_l_suppkey_idx ON tpch.lineitem USING btree (l_suppkey)
-- CREATE UNIQUE INDEX lineitem_pkey ON tpch.lineitem USING btree (l_orderkey, l_linenumber)
-- CREATE UNIQUE INDEX nation_pkey ON tpch.nation USING btree (n_nationkey)
-- CREATE INDEX orders_o_custkey_idx ON tpch.orders USING btree (o_custkey)
-- CREATE INDEX orders_o_orderdate_idx ON tpch.orders USING btree (o_orderdate)
-- CREATE UNIQUE INDEX orders_pkey ON tpch.orders USING btree (o_orderkey)
-- CREATE UNIQUE INDEX part_pkey ON tpch.part USING btree (p_partkey)
-- CREATE UNIQUE INDEX partsupp_pkey ON tpch.partsupp USING btree (ps_partkey, ps_suppkey)
-- CREATE INDEX partsupp_ps_suppkey_idx ON tpch.partsupp USING btree (ps_suppkey)
-- CREATE UNIQUE INDEX region_pkey ON tpch.region USING btree (r_regionkey)
-- CREATE UNIQUE INDEX supplier_pkey ON tpch.supplier USING btree (s_suppkey)
-- CREATE INDEX supplier_s_nationkey_idx ON tpch.supplier USING btree (s_nationkey)
```

Original:
```sql
SELECT DISTINCT r.r_name, c.c_custkey, c.c_name, sum(o.o_totalprice) AS total
FROM region r
JOIN nation n ON n.n_regionkey = r.r_regionkey
JOIN customer c ON c.c_nationkey = n.n_nationkey
JOIN orders o ON o.o_custkey = c.c_custkey
WHERE o.o_orderkey * 1 > 0
  AND o.o_orderdate + INTERVAL '0 day' >= DATE '1998-01-01'
GROUP BY r.r_name, c.c_custkey, c.c_name
HAVING sum(o.o_totalprice) > 500000
ORDER BY r.r_name, total DESC;
```

A static analyser has identified the following specific inefficiencies. Address each one directly. Do not make unrelated changes.

1. [SQL003] non sargable predicate
   Why it is inefficient: The column `o.o_orderkey` is wrapped in `o.o_orderkey * 1` before comparison. PostgreSQL cannot use a plain B-tree index on the column for this predicate and must evaluate the expression for every row.
   Suggested change: Rewrite the predicate so the bare column is compared to a constant/range (e.g. `date_col >= '2024-01-01' AND date_col < '2025-01-01'` instead of `EXTRACT(YEAR FROM date_col) = 2024`; `email = lower($1)` instead of `lower(email) = $1`), or create an expression index.
   Code: o.o_orderkey * 1 > 0
2. [SQL003] non sargable predicate
   Why it is inefficient: The column `o.o_orderdate` is wrapped in `o.o_orderdate + INTERVAL '0' DAY` before comparison. PostgreSQL cannot use a plain B-tree index on the column for this predicate and must evaluate the expression for every row.
   Suggested change: Rewrite the predicate so the bare column is compared to a constant/range (e.g. `date_col >= '2024-01-01' AND date_col < '2025-01-01'` instead of `EXTRACT(YEAR FROM date_col) = 2024`; `email = lower($1)` instead of `lower(email) = $1`), or create an expression index.
   Code: o.o_orderdate + INTERVAL '0 DAY' >= CAST('1998-01-01' AS DATE)
3. [SQL007] distinct with group or join
   Why it is inefficient: DISTINCT over a joined result de-duplicates after the join has multiplied rows; the join output must be fully hashed or sorted.
   Suggested change: Filter with EXISTS (semi-join) or aggregate before joining so duplicates are never produced.
   Code: SELECT DISTINCT r.r_name, c.c_custkey, c.c_name, SUM(o.o_totalprice) AS total FROM region AS r JOIN nation AS n ON n.n_regionkey = r.r_regionkey JOIN customer AS c ON c.c_nationkey = n.n_nationkey JOIN orders AS o ON o.o_custkey = c.c_custkey WHERE o.o_orderkey * 1 > 0 AND o.o_orderdate + INTERVAL '...
4. [SQL009] order by without limit
   Why it is inefficient: The complete result set is sorted even though no LIMIT bounds how many rows are needed.
   Suggested change: Add a LIMIT if only the top rows are used, or drop ORDER BY if ordering is not required by the consumer (sorting in SQL costs O(n log n) and may spill to disk).
   Code: ORDER BY r.r_name, total DESC
5. [SQL011] sequential scan on large table
   Why it is inefficient: The planner chose a sequential scan of `orders` (~1500000 rows, estimated cost 38636.0).
   Suggested change: Make the predicate index-friendly or add an index on the filtered/joined columns, then re-check EXPLAIN.
6. [SQL011] sequential scan on large table
   Why it is inefficient: The planner chose a sequential scan of `customer` (~150000 rows, estimated cost 4225.0).
   Suggested change: Make the predicate index-friendly or add an index on the filtered/joined columns, then re-check EXPLAIN.

Constraints:
- Preserve exact behaviour and output for every possible input.
- Do not change names, signatures or the set of returned columns.
- Prefer simple, idiomatic changes with a clear algorithmic or I/O benefit.

Respond with the complete optimised SQL statement in a single ```sql fenced code block and nothing else. Do not include explanations, comments or more than one statement.
```

</details>

## tpch_c07 — ai_only — rejected (wrong_output)

speed-up: None  energy ratio: None

### Original
```sql
SELECT *
FROM lineitem l, orders o, nation n, region r
WHERE l.l_orderkey = o.o_orderkey
  AND o.o_orderdate = DATE '1995-06-15'
  AND r.r_name = 'EUROPE';
```

### Candidate
```sql
SELECT *
FROM lineitem l
JOIN orders o ON l.l_orderkey = o.o_orderkey
JOIN nation n ON o.o_custkey = n.n_nationkey
JOIN region r ON n.n_regionkey = r.r_regionkey
WHERE o.o_orderdate = DATE '1995-06-15'
  AND r.r_name = 'EUROPE'
```

### Test results

- columns: pass
- row_count: FAIL — wrong_output: row count differs: original 62450 vs candidate 0

<details><summary>Prompt</summary>

```
Optimise the following PostgreSQL query for execution time and resource usage.

The query runs against this PostgreSQL schema:
```sql
CREATE TABLE customer (c_custkey integer, c_name character varying, c_address character varying, c_nationkey integer, c_phone character, c_acctbal numeric, c_mktsegment character, c_comment character varying);
CREATE TABLE lineitem (l_orderkey integer, l_partkey integer, l_suppkey integer, l_linenumber integer, l_quantity numeric, l_extendedprice numeric, l_discount numeric, l_tax numeric, l_returnflag character, l_linestatus character, l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct character, l_shipmode character, l_comment character varying);
CREATE TABLE nation (n_nationkey integer, n_name character, n_regionkey integer, n_comment character varying);
CREATE TABLE orders (o_orderkey integer, o_custkey integer, o_orderstatus character, o_totalprice numeric, o_orderdate date, o_orderpriority character, o_clerk character, o_shippriority integer, o_comment character varying);
CREATE TABLE part (p_partkey integer, p_name character varying, p_mfgr character, p_brand character, p_type character varying, p_size integer, p_container character, p_retailprice numeric, p_comment character varying);
CREATE TABLE partsupp (ps_partkey integer, ps_suppkey integer, ps_availqty integer, ps_supplycost numeric, ps_comment character varying);
CREATE TABLE region (r_regionkey integer, r_name character, r_comment character varying);
CREATE TABLE supplier (s_suppkey integer, s_name character, s_address character varying, s_nationkey integer, s_phone character, s_acctbal numeric, s_comment character varying);
-- CREATE INDEX customer_c_nationkey_idx ON tpch.customer USING btree (c_nationkey)
-- CREATE UNIQUE INDEX customer_pkey ON tpch.customer USING btree (c_custkey)
-- CREATE INDEX lineitem_l_partkey_idx ON tpch.lineitem USING btree (l_partkey)
-- CREATE INDEX lineitem_l_shipdate_idx ON tpch.lineitem USING btree (l_shipdate)
-- CREATE INDEX lineitem_l_suppkey_idx ON tpch.lineitem USING btree (l_suppkey)
-- CREATE UNIQUE INDEX lineitem_pkey ON tpch.lineitem USING btree (l_orderkey, l_linenumber)
-- CREATE UNIQUE INDEX nation_pkey ON tpch.nation USING btree (n_nationkey)
-- CREATE INDEX orders_o_custkey_idx ON tpch.orders USING btree (o_custkey)
-- CREATE INDEX orders_o_orderdate_idx ON tpch.orders USING btree (o_orderdate)
-- CREATE UNIQUE INDEX orders_pkey ON tpch.orders USING btree (o_orderkey)
-- CREATE UNIQUE INDEX part_pkey ON tpch.part USING btree (p_partkey)
-- CREATE UNIQUE INDEX partsupp_pkey ON tpch.partsupp USING btree (ps_partkey, ps_suppkey)
-- CREATE INDEX partsupp_ps_suppkey_idx ON tpch.partsupp USING btree (ps_suppkey)
-- CREATE UNIQUE INDEX region_pkey ON tpch.region USING btree (r_regionkey)
-- CREATE UNIQUE INDEX supplier_pkey ON tpch.supplier USING btree (s_suppkey)
-- CREATE INDEX supplier_s_nationkey_idx ON tpch.supplier USING btree (s_nationkey)
```

Original:
```sql
SELECT *
FROM lineitem l, orders o, nation n, region r
WHERE l.l_orderkey = o.o_orderkey
  AND o.o_orderdate = DATE '1995-06-15'
  AND r.r_name = 'EUROPE';
```

Constraints:
- Preserve exact behaviour and output for every possible input.
- Do not change names, signatures or the set of returned columns.
- Prefer simple, idiomatic changes with a clear algorithmic or I/O benefit.

Respond with the complete optimised SQL statement in a single ```sql fenced code block and nothing else. Do not include explanations, comments or more than one statement.
```

</details>

## tpch_c07 — greencode — benchmarked

speed-up: 1.672861051568867  energy ratio: 0.8946237664818433

### Original
```sql
SELECT *
FROM lineitem l, orders o, nation n, region r
WHERE l.l_orderkey = o.o_orderkey
  AND o.o_orderdate = DATE '1995-06-15'
  AND r.r_name = 'EUROPE';
```

### Candidate
```sql
SELECT l.l_orderkey, l.l_partkey, l.l_suppkey, l.l_linenumber, l.l_quantity, l.l_extendedprice, l.l_discount, l.l_tax, l.l_returnflag, l.l_linestatus, l.l_shipdate, l.l_commitdate, l.l_receiptdate, l.l_shipinstruct, l.l_shipmode, l.l_comment, o.o_orderkey, o.o_custkey, o.o_orderstatus, o.o_totalprice, o.o_orderdate, o.o_orderpriority, o.o_clerk, o.o_shippriority, o.o_comment, n.n_nationkey, n.n_name, n.n_regionkey, n.n_comment, r.r_regionkey, r.r_name, r.r_comment
FROM lineitem l, orders o, nation n, region r
WHERE l.l_orderkey = o.o_orderkey
  AND o.o_orderdate = DATE '1995-06-15'
  AND r.r_name = 'EUROPE'
```

### Test results

- columns: pass
- row_count: pass
- rows: pass

<details><summary>Prompt</summary>

```
Optimise the following PostgreSQL query for execution time and resource usage.

The query runs against this PostgreSQL schema:
```sql
CREATE TABLE customer (c_custkey integer, c_name character varying, c_address character varying, c_nationkey integer, c_phone character, c_acctbal numeric, c_mktsegment character, c_comment character varying);
CREATE TABLE lineitem (l_orderkey integer, l_partkey integer, l_suppkey integer, l_linenumber integer, l_quantity numeric, l_extendedprice numeric, l_discount numeric, l_tax numeric, l_returnflag character, l_linestatus character, l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct character, l_shipmode character, l_comment character varying);
CREATE TABLE nation (n_nationkey integer, n_name character, n_regionkey integer, n_comment character varying);
CREATE TABLE orders (o_orderkey integer, o_custkey integer, o_orderstatus character, o_totalprice numeric, o_orderdate date, o_orderpriority character, o_clerk character, o_shippriority integer, o_comment character varying);
CREATE TABLE part (p_partkey integer, p_name character varying, p_mfgr character, p_brand character, p_type character varying, p_size integer, p_container character, p_retailprice numeric, p_comment character varying);
CREATE TABLE partsupp (ps_partkey integer, ps_suppkey integer, ps_availqty integer, ps_supplycost numeric, ps_comment character varying);
CREATE TABLE region (r_regionkey integer, r_name character, r_comment character varying);
CREATE TABLE supplier (s_suppkey integer, s_name character, s_address character varying, s_nationkey integer, s_phone character, s_acctbal numeric, s_comment character varying);
-- CREATE INDEX customer_c_nationkey_idx ON tpch.customer USING btree (c_nationkey)
-- CREATE UNIQUE INDEX customer_pkey ON tpch.customer USING btree (c_custkey)
-- CREATE INDEX lineitem_l_partkey_idx ON tpch.lineitem USING btree (l_partkey)
-- CREATE INDEX lineitem_l_shipdate_idx ON tpch.lineitem USING btree (l_shipdate)
-- CREATE INDEX lineitem_l_suppkey_idx ON tpch.lineitem USING btree (l_suppkey)
-- CREATE UNIQUE INDEX lineitem_pkey ON tpch.lineitem USING btree (l_orderkey, l_linenumber)
-- CREATE UNIQUE INDEX nation_pkey ON tpch.nation USING btree (n_nationkey)
-- CREATE INDEX orders_o_custkey_idx ON tpch.orders USING btree (o_custkey)
-- CREATE INDEX orders_o_orderdate_idx ON tpch.orders USING btree (o_orderdate)
-- CREATE UNIQUE INDEX orders_pkey ON tpch.orders USING btree (o_orderkey)
-- CREATE UNIQUE INDEX part_pkey ON tpch.part USING btree (p_partkey)
-- CREATE UNIQUE INDEX partsupp_pkey ON tpch.partsupp USING btree (ps_partkey, ps_suppkey)
-- CREATE INDEX partsupp_ps_suppkey_idx ON tpch.partsupp USING btree (ps_suppkey)
-- CREATE UNIQUE INDEX region_pkey ON tpch.region USING btree (r_regionkey)
-- CREATE UNIQUE INDEX supplier_pkey ON tpch.supplier USING btree (s_suppkey)
-- CREATE INDEX supplier_s_nationkey_idx ON tpch.supplier USING btree (s_nationkey)
```

Original:
```sql
SELECT *
FROM lineitem l, orders o, nation n, region r
WHERE l.l_orderkey = o.o_orderkey
  AND o.o_orderdate = DATE '1995-06-15'
  AND r.r_name = 'EUROPE';
```

A static analyser has identified the following specific inefficiencies. Address each one directly. Do not make unrelated changes.

1. [SQL001] select star
   Why it is inefficient: SELECT * returns every column, including ones the consumer never uses. Wider rows mean more I/O, more memory for sorts/hashes and no chance of an index-only scan.
   Suggested change: List only the columns that are actually needed.
   Code: SELECT * FROM lineitem AS l, orders AS o, nation AS n, region AS r WHERE l.l_orderkey = o.o_orderkey AND o.o_orderdate = CAST('1995-06-15' AS DATE) AND r.r_name = 'EUROPE'

Constraints:
- Preserve exact behaviour and output for every possible input.
- Do not change names, signatures or the set of returned columns.
- Prefer simple, idiomatic changes with a clear algorithmic or I/O benefit.

Respond with the complete optimised SQL statement in a single ```sql fenced code block and nothing else. Do not include explanations, comments or more than one statement.
```

</details>

## tpch_c08 — ai_only — benchmarked

speed-up: 0.6597366247766752  energy ratio: 0.14353673071954534

### Original
```sql
SELECT s.s_suppkey, s.s_name,
       (SELECT count(*) FROM lineitem l WHERE l.l_suppkey = s.s_suppkey) AS n_items,
       (SELECT sum(l.l_extendedprice) FROM lineitem l WHERE l.l_suppkey = s.s_suppkey) AS revenue,
       (SELECT count(*) FROM lineitem l WHERE l.l_suppkey = s.s_suppkey AND l.l_receiptdate > l.l_commitdate) AS late_items
FROM supplier s
WHERE s.s_nationkey = (SELECT n_nationkey FROM nation WHERE n_name = 'JAPAN')
ORDER BY revenue DESC
LIMIT 25;
```

### Candidate
```sql
SELECT s.s_suppkey, s.s_name,
       l.n_items,
       l.revenue,
       l.late_items
FROM supplier s
JOIN (
    SELECT l_suppkey,
           COUNT(*) AS n_items,
           SUM(l_extendedprice) AS revenue,
           COUNT(*) FILTER (WHERE l_receiptdate > l_commitdate) AS late_items
    FROM lineitem
    GROUP BY l_suppkey
) l ON s.s_suppkey = l.l_suppkey
WHERE s.s_nationkey = (SELECT n_nationkey FROM nation WHERE n_name = 'JAPAN')
ORDER BY l.revenue DESC
LIMIT 25
```

### Test results

- columns: pass
- row_count: pass
- rows: pass

<details><summary>Prompt</summary>

```
Optimise the following PostgreSQL query for execution time and resource usage.

The query runs against this PostgreSQL schema:
```sql
CREATE TABLE customer (c_custkey integer, c_name character varying, c_address character varying, c_nationkey integer, c_phone character, c_acctbal numeric, c_mktsegment character, c_comment character varying);
CREATE TABLE lineitem (l_orderkey integer, l_partkey integer, l_suppkey integer, l_linenumber integer, l_quantity numeric, l_extendedprice numeric, l_discount numeric, l_tax numeric, l_returnflag character, l_linestatus character, l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct character, l_shipmode character, l_comment character varying);
CREATE TABLE nation (n_nationkey integer, n_name character, n_regionkey integer, n_comment character varying);
CREATE TABLE orders (o_orderkey integer, o_custkey integer, o_orderstatus character, o_totalprice numeric, o_orderdate date, o_orderpriority character, o_clerk character, o_shippriority integer, o_comment character varying);
CREATE TABLE part (p_partkey integer, p_name character varying, p_mfgr character, p_brand character, p_type character varying, p_size integer, p_container character, p_retailprice numeric, p_comment character varying);
CREATE TABLE partsupp (ps_partkey integer, ps_suppkey integer, ps_availqty integer, ps_supplycost numeric, ps_comment character varying);
CREATE TABLE region (r_regionkey integer, r_name character, r_comment character varying);
CREATE TABLE supplier (s_suppkey integer, s_name character, s_address character varying, s_nationkey integer, s_phone character, s_acctbal numeric, s_comment character varying);
-- CREATE INDEX customer_c_nationkey_idx ON tpch.customer USING btree (c_nationkey)
-- CREATE UNIQUE INDEX customer_pkey ON tpch.customer USING btree (c_custkey)
-- CREATE INDEX lineitem_l_partkey_idx ON tpch.lineitem USING btree (l_partkey)
-- CREATE INDEX lineitem_l_shipdate_idx ON tpch.lineitem USING btree (l_shipdate)
-- CREATE INDEX lineitem_l_suppkey_idx ON tpch.lineitem USING btree (l_suppkey)
-- CREATE UNIQUE INDEX lineitem_pkey ON tpch.lineitem USING btree (l_orderkey, l_linenumber)
-- CREATE UNIQUE INDEX nation_pkey ON tpch.nation USING btree (n_nationkey)
-- CREATE INDEX orders_o_custkey_idx ON tpch.orders USING btree (o_custkey)
-- CREATE INDEX orders_o_orderdate_idx ON tpch.orders USING btree (o_orderdate)
-- CREATE UNIQUE INDEX orders_pkey ON tpch.orders USING btree (o_orderkey)
-- CREATE UNIQUE INDEX part_pkey ON tpch.part USING btree (p_partkey)
-- CREATE UNIQUE INDEX partsupp_pkey ON tpch.partsupp USING btree (ps_partkey, ps_suppkey)
-- CREATE INDEX partsupp_ps_suppkey_idx ON tpch.partsupp USING btree (ps_suppkey)
-- CREATE UNIQUE INDEX region_pkey ON tpch.region USING btree (r_regionkey)
-- CREATE UNIQUE INDEX supplier_pkey ON tpch.supplier USING btree (s_suppkey)
-- CREATE INDEX supplier_s_nationkey_idx ON tpch.supplier USING btree (s_nationkey)
```

Original:
```sql
SELECT s.s_suppkey, s.s_name,
       (SELECT count(*) FROM lineitem l WHERE l.l_suppkey = s.s_suppkey) AS n_items,
       (SELECT sum(l.l_extendedprice) FROM lineitem l WHERE l.l_suppkey = s.s_suppkey) AS revenue,
       (SELECT count(*) FROM lineitem l WHERE l.l_suppkey = s.s_suppkey AND l.l_receiptdate > l.l_commitdate) AS late_items
FROM supplier s
WHERE s.s_nationkey = (SELECT n_nationkey FROM nation WHERE n_name = 'JAPAN')
ORDER BY revenue DESC
LIMIT 25;
```

Constraints:
- Preserve exact behaviour and output for every possible input.
- Do not change names, signatures or the set of returned columns.
- Prefer simple, idiomatic changes with a clear algorithmic or I/O benefit.

Respond with the complete optimised SQL statement in a single ```sql fenced code block and nothing else. Do not include explanations, comments or more than one statement.
```

</details>

## tpch_c08 — greencode — benchmarked

speed-up: 0.66428910603599  energy ratio: 0.15951593839982012

### Original
```sql
SELECT s.s_suppkey, s.s_name,
       (SELECT count(*) FROM lineitem l WHERE l.l_suppkey = s.s_suppkey) AS n_items,
       (SELECT sum(l.l_extendedprice) FROM lineitem l WHERE l.l_suppkey = s.s_suppkey) AS revenue,
       (SELECT count(*) FROM lineitem l WHERE l.l_suppkey = s.s_suppkey AND l.l_receiptdate > l.l_commitdate) AS late_items
FROM supplier s
WHERE s.s_nationkey = (SELECT n_nationkey FROM nation WHERE n_name = 'JAPAN')
ORDER BY revenue DESC
LIMIT 25;
```

### Candidate
```sql
WITH supplier_lineitem AS (
    SELECT l_suppkey, 
           COUNT(*) AS n_items, 
           SUM(l_extendedprice) AS revenue, 
           COUNT(*) FILTER (WHERE l_receiptdate > l_commitdate) AS late_items
    FROM lineitem
    GROUP BY l_suppkey
)
SELECT s.s_suppkey, s.s_name, 
       sl.n_items, 
       sl.revenue, 
       sl.late_items
FROM supplier s
JOIN supplier_lineitem sl ON s.s_suppkey = sl.l_suppkey
WHERE s.s_nationkey = (SELECT n_nationkey FROM nation WHERE n_name = 'JAPAN')
ORDER BY sl.revenue DESC
LIMIT 25
```

### Test results

- columns: pass
- row_count: pass
- rows: pass

<details><summary>Prompt</summary>

```
Optimise the following PostgreSQL query for execution time and resource usage.

The query runs against this PostgreSQL schema:
```sql
CREATE TABLE customer (c_custkey integer, c_name character varying, c_address character varying, c_nationkey integer, c_phone character, c_acctbal numeric, c_mktsegment character, c_comment character varying);
CREATE TABLE lineitem (l_orderkey integer, l_partkey integer, l_suppkey integer, l_linenumber integer, l_quantity numeric, l_extendedprice numeric, l_discount numeric, l_tax numeric, l_returnflag character, l_linestatus character, l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct character, l_shipmode character, l_comment character varying);
CREATE TABLE nation (n_nationkey integer, n_name character, n_regionkey integer, n_comment character varying);
CREATE TABLE orders (o_orderkey integer, o_custkey integer, o_orderstatus character, o_totalprice numeric, o_orderdate date, o_orderpriority character, o_clerk character, o_shippriority integer, o_comment character varying);
CREATE TABLE part (p_partkey integer, p_name character varying, p_mfgr character, p_brand character, p_type character varying, p_size integer, p_container character, p_retailprice numeric, p_comment character varying);
CREATE TABLE partsupp (ps_partkey integer, ps_suppkey integer, ps_availqty integer, ps_supplycost numeric, ps_comment character varying);
CREATE TABLE region (r_regionkey integer, r_name character, r_comment character varying);
CREATE TABLE supplier (s_suppkey integer, s_name character, s_address character varying, s_nationkey integer, s_phone character, s_acctbal numeric, s_comment character varying);
-- CREATE INDEX customer_c_nationkey_idx ON tpch.customer USING btree (c_nationkey)
-- CREATE UNIQUE INDEX customer_pkey ON tpch.customer USING btree (c_custkey)
-- CREATE INDEX lineitem_l_partkey_idx ON tpch.lineitem USING btree (l_partkey)
-- CREATE INDEX lineitem_l_shipdate_idx ON tpch.lineitem USING btree (l_shipdate)
-- CREATE INDEX lineitem_l_suppkey_idx ON tpch.lineitem USING btree (l_suppkey)
-- CREATE UNIQUE INDEX lineitem_pkey ON tpch.lineitem USING btree (l_orderkey, l_linenumber)
-- CREATE UNIQUE INDEX nation_pkey ON tpch.nation USING btree (n_nationkey)
-- CREATE INDEX orders_o_custkey_idx ON tpch.orders USING btree (o_custkey)
-- CREATE INDEX orders_o_orderdate_idx ON tpch.orders USING btree (o_orderdate)
-- CREATE UNIQUE INDEX orders_pkey ON tpch.orders USING btree (o_orderkey)
-- CREATE UNIQUE INDEX part_pkey ON tpch.part USING btree (p_partkey)
-- CREATE UNIQUE INDEX partsupp_pkey ON tpch.partsupp USING btree (ps_partkey, ps_suppkey)
-- CREATE INDEX partsupp_ps_suppkey_idx ON tpch.partsupp USING btree (ps_suppkey)
-- CREATE UNIQUE INDEX region_pkey ON tpch.region USING btree (r_regionkey)
-- CREATE UNIQUE INDEX supplier_pkey ON tpch.supplier USING btree (s_suppkey)
-- CREATE INDEX supplier_s_nationkey_idx ON tpch.supplier USING btree (s_nationkey)
```

Original:
```sql
SELECT s.s_suppkey, s.s_name,
       (SELECT count(*) FROM lineitem l WHERE l.l_suppkey = s.s_suppkey) AS n_items,
       (SELECT sum(l.l_extendedprice) FROM lineitem l WHERE l.l_suppkey = s.s_suppkey) AS revenue,
       (SELECT count(*) FROM lineitem l WHERE l.l_suppkey = s.s_suppkey AND l.l_receiptdate > l.l_commitdate) AS late_items
FROM supplier s
WHERE s.s_nationkey = (SELECT n_nationkey FROM nation WHERE n_name = 'JAPAN')
ORDER BY revenue DESC
LIMIT 25;
```

A static analyser has identified the following specific inefficiencies. Address each one directly. Do not make unrelated changes.

1. [SQL006] correlated subquery in select
   Why it is inefficient: A subquery in the SELECT list references the outer query, so it is evaluated once per outer row.
   Suggested change: Rewrite as a JOIN to a pre-aggregated derived table (GROUP BY the key) or a LATERAL join.
   Code: (SELECT COUNT(*) FROM lineitem AS l WHERE l.l_suppkey = s.s_suppkey)
2. [SQL006] correlated subquery in select
   Why it is inefficient: A subquery in the SELECT list references the outer query, so it is evaluated once per outer row.
   Suggested change: Rewrite as a JOIN to a pre-aggregated derived table (GROUP BY the key) or a LATERAL join.
   Code: (SELECT SUM(l.l_extendedprice) FROM lineitem AS l WHERE l.l_suppkey = s.s_suppkey)
3. [SQL006] correlated subquery in select
   Why it is inefficient: A subquery in the SELECT list references the outer query, so it is evaluated once per outer row.
   Suggested change: Rewrite as a JOIN to a pre-aggregated derived table (GROUP BY the key) or a LATERAL join.
   Code: (SELECT COUNT(*) FROM lineitem AS l WHERE l.l_suppkey = s.s_suppkey AND l.l_receiptdate > l.l_commitdate)

Constraints:
- Preserve exact behaviour and output for every possible input.
- Do not change names, signatures or the set of returned columns.
- Prefer simple, idiomatic changes with a clear algorithmic or I/O benefit.

Respond with the complete optimised SQL statement in a single ```sql fenced code block and nothing else. Do not include explanations, comments or more than one statement.
```

</details>
