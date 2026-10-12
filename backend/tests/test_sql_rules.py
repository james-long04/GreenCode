import pytest

from app.analysis.engine import analyse
from app.analysis.sql_rules import analyse_sql


def rules_for(sql: str, **kw) -> set[str]:
    return {f.rule_id for f in analyse_sql(sql, **kw)}


def test_select_star():
    assert "SQL001" in rules_for("SELECT * FROM orders WHERE id = 1")
    assert "SQL001" not in rules_for("SELECT id FROM orders WHERE id = 1")


def test_non_sargable_function_and_cast():
    assert "SQL003" in rules_for("SELECT id FROM orders WHERE EXTRACT(YEAR FROM created_at) = 2023")
    assert "SQL003" in rules_for("SELECT id FROM orders WHERE created_at::date = DATE '2023-01-01'")
    assert "SQL003" in rules_for("SELECT id FROM customers WHERE c.id * 1 BETWEEN 1 AND 5")
    assert "SQL003" not in rules_for("SELECT id FROM orders WHERE created_at >= '2023-01-01'")


def test_leading_wildcard_like():
    assert "SQL004" in rules_for("SELECT id FROM customers WHERE email LIKE '%@x.ie'")
    assert "SQL004" not in rules_for("SELECT id FROM customers WHERE email LIKE 'user1%'")


def test_not_in_vs_in_subquery():
    assert "SQL005" in rules_for("SELECT id FROM customers WHERE id NOT IN (SELECT customer_id FROM orders)")
    assert "SQL010" in rules_for("SELECT id FROM customers WHERE id IN (SELECT customer_id FROM orders)")


def test_correlated_subquery_in_select_list():
    sql = "SELECT c.id, (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.id) FROM customers c WHERE c.id < 10"
    assert "SQL006" in rules_for(sql)


def test_distinct_join_and_order_by_without_limit():
    assert "SQL007" in rules_for("SELECT DISTINCT c.id FROM customers c JOIN orders o ON o.customer_id = c.id")
    assert "SQL009" in rules_for("SELECT id FROM orders WHERE customer_id = 1 ORDER BY created_at")
    assert "SQL009" not in rules_for("SELECT id FROM orders WHERE customer_id = 1 ORDER BY created_at LIMIT 5")


def test_implicit_cross_join():
    assert "SQL008" in rules_for("SELECT c.id FROM customers c, orders o")
    assert "SQL008" not in rules_for("SELECT c.id FROM customers c, orders o WHERE o.customer_id = c.id")


def test_count_star_existence():
    sql = "SELECT p.id FROM products p WHERE (SELECT COUNT(*) FROM order_items oi WHERE oi.product_id = p.id) > 0"
    assert "SQL012" in rules_for(sql)


def test_explain_evidence_adds_seq_scan_finding():
    plan = {"Plan": {"Node Type": "Seq Scan", "Relation Name": "orders", "Plan Rows": 200000, "Total Cost": 4000.0}}
    assert "SQL011" in rules_for("SELECT id FROM orders WHERE total_cents > 5", explain=plan, table_stats={"orders": 200000})


def test_parse_error_is_reported():
    res = analyse("sql", "SELEC id FROM")
    assert res.error and res.findings == []


def test_unsupported_language():
    with pytest.raises(ValueError):
        analyse("java", "class A {}")
