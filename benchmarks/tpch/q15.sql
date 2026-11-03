-- TPC-H Q15: Top Supplier (DATE = 1996-01-01). The spec's view is expressed as a CTE so the query is one statement.
WITH revenue0 AS (
    SELECT l_suppkey AS supplier_no, sum(l_extendedprice * (1 - l_discount)) AS total_revenue
    FROM lineitem
    WHERE l_shipdate >= DATE '1996-01-01' AND l_shipdate < DATE '1996-01-01' + INTERVAL '3 month'
    GROUP BY l_suppkey)
SELECT s_suppkey, s_name, s_address, s_phone, total_revenue
FROM supplier, revenue0
WHERE s_suppkey = supplier_no AND total_revenue = (SELECT max(total_revenue) FROM revenue0)
ORDER BY s_suppkey;
