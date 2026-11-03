-- C7: SELECT * over a wide multi-table join (SQL001); nation and region are comma-joined without a condition, a Cartesian product the rule set only detects when there is no WHERE at all
SELECT *
FROM lineitem l, orders o, nation n, region r
WHERE l.l_orderkey = o.o_orderkey
  AND o.o_orderdate = DATE '1995-06-15'
  AND r.r_name = 'EUROPE';
