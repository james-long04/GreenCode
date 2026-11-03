"""TPC-H-derived laboratory experiments: query set, cases, conditions, pre-flight (no database needed)."""

from __future__ import annotations

import json

from app.analysis.engine import analyse
from app.benchmark.energy import _lhm_dram_watts, _lhm_temperature, _parse_value
from app.config import get_settings
from app.experiments import tpch
from app.experiments.preflight import Check, all_required_ok, format_checks
from app.experiments.suite import load_cases


def test_standard_query_set_is_complete():
    qs = tpch.load_queries("standard")
    assert [q.id for q in qs] == [f"q{i:02d}" for i in range(1, 23)]
    for q in qs:
        assert q.title.startswith("TPC-H Q"), q.id
        assert q.sql.strip().endswith(";")
        assert q.sql.count(";") == 1, f"{q.id} must be a single statement"


def test_standard_queries_parse_as_single_select():
    for q in tpch.load_queries("standard"):
        res = analyse("sql", q.sql.rstrip().rstrip(";"))
        assert res is not None, q.id  # sqlglot accepted it


def test_complex_queries_and_cases_agree():
    qs = {q.id: q for q in tpch.load_queries("complex")}
    cases = load_cases(tpch.TPCH_DIR / "cases")
    assert len(qs) == len(cases) == 8
    for case in cases:
        assert case.language == "sql"
        assert case.id.startswith("tpch_c")
        fired = {f.rule_id for f in analyse("sql", case.source).findings}
        missing = set(case.expected_rules) - fired
        assert not missing, f"{case.id}: expected {case.expected_rules}, fired {sorted(fired)}"


def test_case_files_are_valid_json_with_required_keys():
    for p in sorted((tpch.TPCH_DIR / "cases").glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        assert {"id", "title", "language", "source", "expected_rules"} <= set(data)


def test_tpch_settings_points_at_schema_and_raises_timeout():
    s = tpch.tpch_settings(get_settings())
    assert s.benchmark_schema == get_settings().tpch_schema
    assert s.sql_statement_timeout_ms >= 600_000


def test_wp2_conditions_include_no_meter_and_two_poll_rates():
    conds = tpch.conditions_for("wp2", get_settings(), plan_label="balanced")
    labels = [c.label for c in conds]
    assert "meter=none;plan=balanced" in labels
    assert any(c.meter == "lhm" and c.poll_seconds == 0.1 for c in conds)
    assert any(c.meter == "lhm" and c.poll_seconds == 0.5 for c in conds)


def test_lhm_value_parsing_and_sensor_lookup():
    assert _parse_value("7,5 W") == 7.5
    assert _parse_value("48 °C") == 48.0
    assert _parse_value("") is None
    tree = {"Text": "PC", "Children": [{"Text": "Intel CPU", "Children": [
        {"Text": "CPU Package", "SensorId": "/intelcpu/0/temperature/4", "Value": "61,0 °C"},
        {"Text": "CPU Package", "SensorId": "/intelcpu/0/power/0", "Value": "12,3 W"},
        {"Text": "CPU Memory", "SensorId": "/intelcpu/0/power/3", "Value": "1,1 W"},
    ]}]}
    assert _lhm_temperature(tree) == 61.0
    assert _lhm_dram_watts(tree) == 1.1
    assert _lhm_dram_watts({"Text": "PC", "Children": []}) is None


def test_preflight_formatting_and_required_logic():
    checks = [Check("mains power", True, "plugged in"), Check("noisy processes", False, "chrome", required=False)]
    assert all_required_ok(checks)
    text = format_checks(checks)
    assert "[OK ]" in text and "[?? ]" in text
    checks.append(Check("LibreHardwareMonitor", False, "not reachable"))
    assert not all_required_ok(checks)
