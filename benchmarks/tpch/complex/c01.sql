-- C1: Customer order counts with a correlated COUNT subquery per customer (SQL006), function on o_orderdate (SQL003)
SELECT c.c_custkey, c.c_name, c.c_mktsegment,
       (SELECT count(*) FROM orders o WHERE o.o_custkey = c.c_custkey AND extract(year FROM o.o_orderdate) = 1995) AS orders_1995,
       (SELECT sum(o.o_totalprice) FROM orders o WHERE o.o_custkey = c.c_custkey AND extract(year FROM o.o_orderdate) = 1995) AS spend_1995
FROM customer c
WHERE c.c_mktsegment = 'AUTOMOBILE'
ORDER BY spend_1995 DESC NULLS LAST
LIMIT 50;
