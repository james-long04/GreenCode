-- C4: Parts whose average lineitem price exceeds the part's retail price; correlated subquery in SELECT and WHERE (SQL006), IN (subquery) over a large table (SQL010)
SELECT p.p_partkey, p.p_name, p.p_retailprice,
       (SELECT avg(l.l_extendedprice / l.l_quantity) FROM lineitem l WHERE l.l_partkey = p.p_partkey) AS avg_unit_price
FROM part p
WHERE p.p_partkey IN (SELECT l_partkey FROM lineitem WHERE l_shipmode = 'AIR')
  AND p.p_brand = 'Brand#13'
  AND (SELECT avg(l.l_extendedprice / l.l_quantity) FROM lineitem l WHERE l.l_partkey = p.p_partkey) > p.p_retailprice * 1.05
ORDER BY avg_unit_price DESC
LIMIT 100;
