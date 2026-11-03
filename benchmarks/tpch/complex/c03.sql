-- C3: Monthly revenue by nation with a function on the filtered column (SQL003) and DISTINCT over a join (SQL007)
SELECT DISTINCT n.n_name, to_char(o.o_orderdate, 'YYYY-MM') AS month,
       sum(l.l_extendedprice * (1 - l.l_discount)) OVER (PARTITION BY n.n_name, to_char(o.o_orderdate, 'YYYY-MM')) AS revenue
FROM lineitem l
JOIN orders o ON o.o_orderkey = l.l_orderkey
JOIN customer c ON c.c_custkey = o.o_custkey
JOIN nation n ON n.n_nationkey = c.c_nationkey
WHERE extract(year FROM o.o_orderdate) = 1996
ORDER BY n.n_name, month;
