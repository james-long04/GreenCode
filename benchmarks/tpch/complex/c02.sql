-- C2: Suppliers with no late lineitems via NOT IN (SQL005) and SELECT * (SQL001)
SELECT *
FROM supplier
WHERE s_suppkey NOT IN (
    SELECT l_suppkey FROM lineitem WHERE l_receiptdate > l_commitdate AND l_shipdate >= DATE '1996-01-01')
  AND s_nationkey IN (SELECT n_nationkey FROM nation WHERE n_name IN ('UNITED KINGDOM', 'IRELAND', 'FRANCE', 'GERMANY'))
ORDER BY s_acctbal DESC;
