from app.analysis.engine import analyse
from app.analysis.python_rules import PYTHON_RULES, analyse_python


def rules_for(src: str) -> set[str]:
    return {f.rule_id for f in analyse_python(src)}


def test_rule_catalogue_has_unique_ids():
    ids = [r.rule_id for r in PYTHON_RULES]
    assert len(ids) == len(set(ids))


def test_membership_in_list_inside_loop_is_flagged():
    src = "def f(xs, ys):\n    allowed = list(xs)\n    return [y for y in ys if y in allowed]\n"
    assert "PY001" in rules_for(src)


def test_membership_in_set_is_not_flagged():
    src = "def f(xs, ys):\n    allowed = set(xs)\n    out = []\n    for y in ys:\n        if y in allowed:\n            out.append(y)\n    return out\n"
    assert "PY001" not in rules_for(src)


def test_string_concat_in_loop():
    src = "def f(parts):\n    s = ''\n    for p in parts:\n        s += p\n    return s\n"
    assert "PY002" in rules_for(src)


def test_string_concat_outside_loop_is_fine():
    src = "def f(a, b):\n    s = ''\n    s += a\n    s += b\n    return s\n"
    assert "PY002" not in rules_for(src)


def test_loop_invariant_sorted_is_flagged_but_dependent_call_is_not():
    flagged = "def f(qs, vs):\n    out = []\n    for q in qs:\n        out.append(sorted(vs)[q])\n    return out\n"
    fine = "def f(qs):\n    out = []\n    for q in qs:\n        out.append(sorted(q))\n    return out\n"
    assert "PY005" in rules_for(flagged)
    assert "PY005" not in rules_for(fine)


def test_sorted_index_zero_and_top_k():
    assert "PY007" in rules_for("def f(xs):\n    return sorted(xs)[0]\n")
    assert "PY007" in rules_for("def f(xs, k):\n    return sorted(xs, reverse=True)[:k]\n")
    assert "PY007" not in rules_for("def f(xs):\n    return sorted(xs)\n")


def test_nested_loop_join():
    src = ("def f(a, b):\n    out = []\n    for x in a:\n        for y in b:\n            if x['k'] == y['k']:\n"
           "                out.append((x, y))\n    return out\n")
    assert "PY006" in rules_for(src)


def test_query_in_loop():
    src = "def f(cur, ids):\n    for i in ids:\n        cur.execute('select 1', (i,))\n"
    assert "PY009" in rules_for(src)


def test_unnecessary_allocations():
    assert "PY008" in rules_for("def f(xs):\n    return sum([x for x in xs])\n")
    assert "PY008" in rules_for("def f(d, k):\n    return k in d.keys()\n")
    assert "PY008" in rules_for("def f(xs):\n    return len(list(x for x in xs))\n")


def test_manual_sum_and_append_loops():
    assert "PY010" in rules_for("def f(xs):\n    t = 0\n    for x in xs:\n        t += x\n    return t\n")
    assert "PY003" in rules_for("def f(xs):\n    out = []\n    for x in xs:\n        out.append(x * 2)\n    return out\n")


def test_range_len_indexing_not_flagged_when_writing():
    read = "def f(xs):\n    t = 0\n    for i in range(len(xs)):\n        t += xs[i]\n    return t\n"
    write = "def f(xs):\n    for i in range(len(xs)):\n        xs[i] = xs[i] * 2\n    return xs\n"
    assert "PY004" in rules_for(read)
    assert "PY004" not in rules_for(write)


def test_findings_have_locations_and_explanations():
    src = "def f(xs, ys):\n    allowed = list(xs)\n    return [y for y in ys if y in allowed]\n"
    f = analyse_python(src)[0]
    assert f.line == 3 and f.explanation and f.suggestion and 0 < f.confidence <= 1


def test_syntax_error_is_reported_not_raised():
    res = analyse("python", "def f(:\n    pass\n")
    assert res.error and res.error.startswith("SyntaxError") and res.findings == []


def test_control_case_has_no_findings():
    src = "def solve(values):\n    lookup = set(values)\n    return [v in lookup for v in range(0, 100, 7)]\n"
    assert rules_for(src) == set()
