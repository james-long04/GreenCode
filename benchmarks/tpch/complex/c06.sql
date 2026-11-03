-- C6: Top customers per region with an arithmetic predicate on an indexed column (SQL003) and a redundant DISTINCT
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
