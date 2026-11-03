-- C8: Supplier scorecard: three correlated aggregates per supplier (SQL006) over lineitem
SELECT s.s_suppkey, s.s_name,
       (SELECT count(*) FROM lineitem l WHERE l.l_suppkey = s.s_suppkey) AS n_items,
       (SELECT sum(l.l_extendedprice) FROM lineitem l WHERE l.l_suppkey = s.s_suppkey) AS revenue,
       (SELECT count(*) FROM lineitem l WHERE l.l_suppkey = s.s_suppkey AND l.l_receiptdate > l.l_commitdate) AS late_items
FROM supplier s
WHERE s.s_nationkey = (SELECT n_nationkey FROM nation WHERE n_name = 'JAPAN')
ORDER BY revenue DESC
LIMIT 25;
