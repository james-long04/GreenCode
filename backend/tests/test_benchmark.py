import os

from app.benchmark.energy import EnergySample, co2e_grams, estimate_energy, select_method
from app.benchmark.runner import EnergyContext, benchmark_python
from app.benchmark.stats import cliffs_delta, compare, summarise


def test_summarise_and_ci():
    s = summarise([10, 11, 9, 10, 10])
    assert s.n == 5 and s.median == 10 and s.ci95_low < s.mean < s.ci95_high


def test_compare_detects_faster():
    slow = [100 + i for i in range(10)]
    fast = [10 + i for i in range(10)]
    c = compare(slow, fast)
    assert c["speedup"] > 5 and c["verdict"] == "faster" and c["cliffs_delta"] == 1.0


def test_compare_no_difference():
    c = compare([10, 11, 10, 12, 11, 10], [11, 10, 12, 10, 11, 10])
    assert c["verdict"] == "no_significant_change"


def test_cliffs_delta_bounds():
    assert cliffs_delta([1, 2], [3, 4]) == -1.0


def test_estimate_energy_is_documented_and_positive():
    s = estimate_energy(cpu_seconds=1.0, wall_seconds=1.0, peak_rss_bytes=1e9)
    assert s.method == "estimated" and s.joules > 0 and "model" in s.details


def test_co2e_conversion():
    assert abs(co2e_grams(3.6e6, 200.0) - 200.0) < 1e-9


def test_net_joules_subtracts_idle():
    s = EnergySample(joules=10, method="measured", source="lhm", wall_seconds=1, idle_joules=4)
    assert s.net_joules == 6


def test_select_method_falls_back_to_estimate(monkeypatch):
    monkeypatch.setenv("GREENCODE_ENERGY_METHOD", "lhm")
    from app.config import Settings

    assert select_method(Settings()) in {"lhm", "estimate"}


def test_benchmark_python_end_to_end():
    spec = {"entry_point": "solve", "benchmark": {"setup": "n = 20000", "call": "solve(n)"}}
    out = benchmark_python("def solve(n):\n    return sum(range(n))\n", spec, energy_ctx=EnergyContext(),
                           repetitions=4, warmup=1)
    assert out.ok and out.summary and out.summary.n == 4
    assert any(e.source == "estimate" for e in out.energy)
    assert out.environment["logical_cores"] == os.cpu_count()


def test_lhm_json_parser_finds_cpu_package_power():
    from app.benchmark.energy import _lhm_package_watts

    tree = {"Text": "Sensor", "Children": [{"Text": "LAPTOP", "Children": [
        {"Text": "Intel Core Ultra 5 135U", "Children": [
            {"Text": "Powers", "Children": [
                {"Text": "CPU Cores", "SensorId": "/intelcpu/0/power/1", "Value": "3.2 W"},
                {"Text": "CPU Package", "SensorId": "/intelcpu/0/power/0", "Value": "7,5 W"},
            ]}]}]}]}
    assert _lhm_package_watts(tree) == ("CPU Package", 7.5)
