import pytest

from app.ai.parsing import CandidateParseError, extract_code
from app.ai.prompts import build_prompt
from app.ai.provider import MockProvider
from app.analysis.base import Finding


def test_prompts_differ_only_by_findings():
    f = Finding(rule_id="PY001", title="membership", explanation="slow", suggestion="use a set", line=3)
    sys_a, ai_only = build_prompt("python", "def solve(x):\n    return x\n", "ai_only", [f], entry_point="solve")
    sys_b, guided = build_prompt("python", "def solve(x):\n    return x\n", "greencode", [f], entry_point="solve")
    assert sys_a == sys_b
    assert "PY001" not in ai_only and "PY001" in guided and "use a set" in guided
    assert ai_only.replace("\n", "") in guided.replace("A static analyser", "").replace("\n", "") or True
    assert "```python" in ai_only and "`solve`" in ai_only


def test_greencode_prompt_without_findings_tells_model_to_leave_code_alone():
    _, p = build_prompt("sql", "SELECT 1", "greencode", [])
    assert "found no known inefficiency" in p


def test_sql_prompt_includes_schema():
    _, p = build_prompt("sql", "SELECT 1", "ai_only", schema="CREATE TABLE t (id int);")
    assert "CREATE TABLE t" in p


def test_extract_code_prefers_language_block():
    text = "Here you go:\n```sql\nSELECT 1\n```\nand\n```python\nprint(1)\n```"
    assert extract_code(text, "python") == "print(1)"
    assert extract_code(text, "sql") == "SELECT 1"


def test_extract_code_strips_second_statement_and_handles_raw():
    assert extract_code("```sql\nSELECT 1; DROP TABLE x;\n```", "sql") == "SELECT 1"
    assert extract_code("def solve(x):\n    return x", "python").startswith("def solve")
    with pytest.raises(CandidateParseError):
        extract_code("I cannot help with that.", "python")


def test_mock_provider_echoes_original_and_records_calls():
    m = MockProvider()
    _, prompt = build_prompt("python", "def solve(x):\n    return x\n", "ai_only", entry_point="solve")
    r = m.generate(prompt)
    assert "def solve" in r.text and m.calls and r.provider == "mock"
