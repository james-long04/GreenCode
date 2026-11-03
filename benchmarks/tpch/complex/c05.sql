-- C5: Existence check with COUNT(*) > 0 (SQL012), leading-wildcard LIKE on a comment column (SQL004), ORDER BY without LIMIT (SQL009)
SELECT o.o_orderkey, o.o_orderdate, o.o_totalprice
FROM orders o
WHERE o.o_orderdate BETWEEN DATE '1997-01-01' AND DATE '1997-03-31'
  AND (SELECT count(*) FROM lineitem l WHERE l.l_orderkey = o.o_orderkey AND l.l_returnflag = 'R') > 0
  AND o.o_comment LIKE '%unusual%'
ORDER BY o.o_totalprice DESC;
