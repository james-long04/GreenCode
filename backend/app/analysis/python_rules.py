"""Python static-analysis rules (AST based).

Each rule is a small, deterministic detector for a named inefficiency pattern
drawn from the project proposal (section 7): data structures, repeated
computation, unnecessary allocations, membership checks, sorting, redundant
operations, repeated expensive calls and N+1 database access.

The detectors are intentionally conservative: a false positive would send the
language model misleading guidance, which would contaminate the experiment. Where
a rule cannot be certain (for example the runtime type of a variable) it records
a lower ``confidence`` and the evidence it used.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Iterable

from app.analysis.base import Finding, RuleInfo

# --------------------------------------------------------------------------
# Rule catalogue
# --------------------------------------------------------------------------

PYTHON_RULES: list[RuleInfo] = [
    RuleInfo("PY001", "membership_test_on_sequence", "python", "data_structures", "high",
             "`x in <list/tuple>` inside a loop is O(n) per test; a set/dict gives O(1)."),
    RuleInfo("PY002", "string_concatenation_in_loop", "python", "allocations", "medium",
             "Building a string with += in a loop creates a new string on every iteration."),
    RuleInfo("PY003", "loop_append_to_comprehension", "python", "redundant_operations", "low",
             "A loop that only appends to a list can be a list comprehension."),
    RuleInfo("PY004", "range_len_indexing", "python", "redundant_operations", "low",
             "`for i in range(len(x))` with `x[i]` can iterate directly or use enumerate()."),
    RuleInfo("PY005", "loop_invariant_expensive_call", "python", "repeated_computation", "high",
             "An expensive call whose arguments do not change is repeated on every iteration."),
    RuleInfo("PY006", "nested_loop_quadratic_join", "python", "data_structures", "high",
             "Nested loops comparing elements of two sequences perform O(n*m) work; a dict/set index makes it O(n+m)."),
    RuleInfo("PY007", "full_sort_for_extreme_value", "python", "sorting", "medium",
             "sorted(x)[0] / sorted(x)[-1] sorts the whole sequence (O(n log n)) to obtain one value (O(n))."),
    RuleInfo("PY008", "unnecessary_allocation", "python", "allocations", "medium",
             "Materialising an intermediate list/tuple/set that is immediately consumed."),
    RuleInfo("PY009", "database_query_in_loop", "python", "database", "high",
             "A query executed inside a loop (N+1 pattern); batch the work into one query."),
    RuleInfo("PY010", "manual_aggregation_loop", "python", "redundant_operations", "low",
             "A loop that only accumulates a total/count can use sum()/any()/len()."),
    RuleInfo("PY011", "dataframe_iterrows", "python", "repeated_computation", "medium",
             "Iterating a pandas DataFrame with iterrows() is orders of magnitude slower than vectorised operations."),
]

RULE_INDEX = {r.rule_id: r for r in PYTHON_RULES}

# Calls treated as "expensive" for loop-invariant detection.
EXPENSIVE_FUNCS = {
    "sorted", "sum", "max", "min", "set", "list", "tuple", "frozenset", "dict",
    "reversed", "enumerate", "zip", "open", "compile",
}
EXPENSIVE_DOTTED = {
    "re.compile", "re.match", "re.search", "re.findall", "re.sub", "re.fullmatch", "re.split",
    "json.loads", "json.dumps", "json.load", "copy.deepcopy", "copy.copy",
    "os.listdir", "os.path.exists", "glob.glob", "Path.glob",
}
EXPENSIVE_METHODS = {
    "lower", "upper", "strip", "split", "join", "keys", "values", "items", "read", "readlines",
    "sort", "copy", "deepcopy", "encode", "decode", "replace",
}
QUERY_METHODS = {"execute", "query", "filter", "filter_by", "find", "find_one", "fetchall", "get_object_or_404"}
QUERY_FUNCS = {"requests.get", "requests.post", "urlopen", "httpx.get", "httpx.post"}


@dataclass
class _Scope:
    """Tracks simple name → inferred container type within one function."""

    types: dict[str, str] = field(default_factory=dict)
    sizes: dict[str, int] = field(default_factory=dict)
    assigned_in_loops: set[str] = field(default_factory=set)


@dataclass
class _LoopCtx:
    node: ast.AST
    targets: set[str]
    iter_names: set[str] = field(default_factory=set)
    assigned: set[str] = field(default_factory=set)


def _names_in(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _dotted(node: ast.AST) -> str | None:
    """Return 'a.b.c' for an attribute chain of names, else None."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f"{base}.{node.attr}" if base else None
    return None


def _assigned_names(node: ast.AST) -> set[str]:
    out: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            for t in targets:
                out |= {x.id for x in ast.walk(t) if isinstance(x, ast.Name)}
        elif isinstance(n, (ast.For, ast.comprehension)):
            out |= _names_in(n.target)
        elif isinstance(n, ast.withitem) and n.optional_vars is not None:
            out |= _names_in(n.optional_vars)
        elif isinstance(n, ast.NamedExpr):
            out |= _names_in(n.target)
    return out


def _infer_type(value: ast.AST) -> str | None:
    if isinstance(value, ast.List) or isinstance(value, ast.ListComp):
        return "list"
    if isinstance(value, ast.Tuple):
        return "tuple"
    if isinstance(value, (ast.Set, ast.SetComp)):
        return "set"
    if isinstance(value, (ast.Dict, ast.DictComp)):
        return "dict"
    if isinstance(value, ast.Constant):
        if isinstance(value.value, str):
            return "str"
        if isinstance(value.value, bool):
            return "bool"
        if isinstance(value.value, (int, float)):
            return "number"
    if isinstance(value, ast.Call):
        name = _dotted(value.func)
        if name in {"list", "sorted"}:
            return "list"
        if name in {"set", "frozenset"}:
            return "set"
        if name == "dict":
            return "dict"
        if name == "tuple":
            return "tuple"
        if name == "str":
            return "str"
        if isinstance(value.func, ast.Attribute) and value.func.attr in {"split", "readlines", "splitlines"}:
            return "list"
        if isinstance(value.func, ast.Attribute) and value.func.attr in {"keys", "values", "items"}:
            return "view"
    if isinstance(value, ast.JoinedStr):
        return "str"
    if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Mult) and isinstance(value.left, ast.List):
        return "list"
    return None


def _literal_len(value: ast.AST) -> int | None:
    if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
        return len(value.elts)
    if isinstance(value, ast.Dict):
        return len(value.keys)
    return None


class _PythonAnalyser(ast.NodeVisitor):
    def __init__(self, source: str) -> None:
        self.source = source
        self.lines = source.splitlines()
        self.findings: list[Finding] = []
        self.scope = _Scope()
        self.loops: list[_LoopCtx] = []
        self._seen: set[tuple[str, int]] = set()

    # ------------------------------------------------------------------ utils
    def _snippet(self, node: ast.AST) -> str | None:
        line = getattr(node, "lineno", None)
        if not line:
            return None
        end = getattr(node, "end_lineno", line) or line
        chunk = self.lines[line - 1 : min(end, line + 2)]
        text = "\n".join(chunk)
        return text if len(text) < 300 else text[:300] + "..."

    def _emit(self, rule_id: str, node: ast.AST, explanation: str, suggestion: str,
              confidence: float = 0.8, **evidence) -> None:
        line = getattr(node, "lineno", None)
        key = (rule_id, line or -1)
        if key in self._seen:
            return
        self._seen.add(key)
        info = RULE_INDEX[rule_id]
        self.findings.append(
            Finding(
                rule_id=rule_id,
                title=info.name.replace("_", " "),
                explanation=explanation,
                suggestion=suggestion,
                severity=info.severity,
                category=info.category,
                line=line,
                column=getattr(node, "col_offset", None),
                end_line=getattr(node, "end_lineno", None),
                snippet=self._snippet(node),
                confidence=confidence,
                evidence=evidence,
            )
        )

    def _in_loop(self) -> bool:
        return bool(self.loops)

    def _loop_varying_names(self) -> set[str]:
        out: set[str] = set()
        for lp in self.loops:
            out |= lp.targets | lp.assigned
        return out

    def _type_of(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return self.scope.types.get(node.id)
        return _infer_type(node)

    # -------------------------------------------------------------- scoping
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.AST) -> None:
        saved_scope, saved_loops = self.scope, self.loops
        self.scope, self.loops = _Scope(), []
        self._prescan(node)
        self.generic_visit(node)
        self.scope, self.loops = saved_scope, saved_loops

    def visit_Module(self, node: ast.Module) -> None:
        self._prescan(node)
        self.generic_visit(node)

    def _prescan(self, node: ast.AST) -> None:
        """Record the first inferred type of each simple assignment in this scope."""
        for n in ast.walk(node):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and n is not node:
                continue
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                name = n.targets[0].id
                t = _infer_type(n.value)
                if t and name not in self.scope.types:
                    self.scope.types[name] = t
                size = _literal_len(n.value)
                if size is not None:
                    self.scope.sizes[name] = size
            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value is not None:
                t = _infer_type(n.value)
                if t and n.target.id not in self.scope.types:
                    self.scope.types[n.target.id] = t
            elif isinstance(n, ast.arg) and n.annotation is not None:
                ann = _dotted(n.annotation)
                if ann in {"list", "List", "str", "set", "dict", "tuple"}:
                    self.scope.types.setdefault(n.arg, ann.lower())
                elif isinstance(n.annotation, ast.Subscript):
                    base = _dotted(n.annotation.value)
                    if base in {"list", "List", "set", "Set", "dict", "Dict", "tuple", "Tuple"}:
                        self.scope.types.setdefault(n.arg, base.lower())

    # ---------------------------------------------------------------- loops
    def visit_For(self, node: ast.For) -> None:
        self._enter_loop(node, _names_in(node.target), _names_in(node.iter))
        self._check_loop_body(node)
        self.generic_visit(node)
        self.loops.pop()

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.visit_For(node)  # type: ignore[arg-type]

    def visit_While(self, node: ast.While) -> None:
        self._enter_loop(node, set(), _names_in(node.test))
        self._check_loop_body(node)
        self.generic_visit(node)
        self.loops.pop()

    # Comprehensions are loops too: `[t for t in ys if t in allowed]` repeats the test.
    def _visit_comprehension(self, node: ast.AST) -> None:
        targets: set[str] = set()
        iter_names: set[str] = set()
        for gen in getattr(node, "generators", []):
            targets |= _names_in(gen.target)
            iter_names |= _names_in(gen.iter)
        ctx = _LoopCtx(node=node, targets=targets, iter_names=iter_names, assigned=targets)
        self.loops.append(ctx)
        self.generic_visit(node)
        self.loops.pop()

    visit_ListComp = _visit_comprehension
    visit_SetComp = _visit_comprehension
    visit_DictComp = _visit_comprehension
    visit_GeneratorExp = _visit_comprehension

    def _enter_loop(self, node: ast.AST, targets: set[str], iter_names: set[str]) -> None:
        ctx = _LoopCtx(node=node, targets=targets, iter_names=iter_names)
        ctx.assigned = _assigned_names(node)
        self.loops.append(ctx)

    def _check_loop_body(self, node: ast.For | ast.While) -> None:
        body = node.body
        self._rule_py003_py010(node, body)
        if isinstance(node, ast.For):
            self._rule_py004(node)
            self._rule_py006(node)
            self._rule_py011(node)

    # PY003 / PY010 ---------------------------------------------------------
    def _rule_py003_py010(self, loop: ast.For | ast.While, body: list[ast.stmt]) -> None:
        if not isinstance(loop, ast.For) or len(body) != 1:
            return
        stmt = body[0]
        # Unwrap a single `if cond:` guard.
        guard = None
        if isinstance(stmt, ast.If) and not stmt.orelse and len(stmt.body) == 1:
            guard = stmt.test
            stmt = stmt.body[0]
        if (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Attribute)
            and stmt.value.func.attr == "append"
            and isinstance(stmt.value.func.value, ast.Name)
            and len(stmt.value.args) == 1
        ):
            target = stmt.value.func.value.id
            if self.scope.types.get(target) == "list":
                self._emit(
                    "PY003", loop,
                    f"The loop only appends to `{target}`; the interpreter executes the append method "
                    "call and attribute lookup on every iteration.",
                    f"Build `{target}` with a list comprehension"
                    + (" (keeping the `if` condition as a filter)." if guard is not None else "."),
                    confidence=0.7, target=target,
                )
        elif (
            isinstance(stmt, ast.AugAssign)
            and isinstance(stmt.op, ast.Add)
            and isinstance(stmt.target, ast.Name)
            and self.scope.types.get(stmt.target.id) == "number"
        ):
            target = stmt.target.id
            is_count = isinstance(stmt.value, ast.Constant) and stmt.value.value == 1
            self._emit(
                "PY010", loop,
                f"The loop only accumulates into `{target}`; a Python-level loop is slower than the "
                "C-implemented builtin aggregation functions.",
                ("Use `sum(1 for ... if ...)` or `len(...)` to count." if is_count
                 else "Use `sum(<expression> for ... in ...)` (a generator expression) instead of the loop."),
                confidence=0.75, target=target,
            )

    # PY004 -----------------------------------------------------------------
    def _rule_py004(self, node: ast.For) -> None:
        it = node.iter
        if not (
            isinstance(it, ast.Call) and _dotted(it.func) == "range" and len(it.args) == 1
            and isinstance(it.args[0], ast.Call) and _dotted(it.args[0].func) == "len"
            and len(it.args[0].args) == 1 and isinstance(it.args[0].args[0], ast.Name)
            and isinstance(node.target, ast.Name)
        ):
            return
        seq, idx = it.args[0].args[0].id, node.target.id
        uses_index_only = False
        for n in ast.walk(node):
            if (
                isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == seq
                and isinstance(n.slice, ast.Name) and n.slice.id == idx
            ):
                uses_index_only = True
                break
        # If the index is written to the sequence (x[i] = ...), direct iteration is not equivalent.
        writes = any(
            isinstance(n, ast.Assign) and any(
                isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id == seq
                for t in n.targets)
            for n in ast.walk(node)
        )
        if uses_index_only and not writes:
            self._emit(
                "PY004", node,
                f"`range(len({seq}))` with `{seq}[{idx}]` performs an index lookup on every iteration "
                "and is slower than direct iteration.",
                f"Iterate with `for item in {seq}:` or `for {idx}, item in enumerate({seq}):`.",
                confidence=0.7, sequence=seq, index=idx,
            )

    # PY006 -----------------------------------------------------------------
    def _rule_py006(self, outer: ast.For) -> None:
        if not isinstance(outer.target, ast.Name):
            return
        a = outer.target.id
        for stmt in outer.body:
            inner = stmt
            if isinstance(inner, ast.For) and isinstance(inner.target, ast.Name):
                b = inner.target.id
                inner_iter_type = self._type_of(inner.iter)
                for n in ast.walk(inner):
                    if isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], ast.Eq):
                        names_l, names_r = _names_in(n.left), _names_in(n.comparators[0])
                        if (a in names_l and b in names_r) or (b in names_l and a in names_r):
                            self._emit(
                                "PY006", outer,
                                f"For every `{a}` the inner loop scans every `{b}` looking for an equal key, "
                                "which is O(n*m) comparisons.",
                                f"Index the inner sequence once in a dict/set keyed on the compared value, "
                                f"then look each `{a}` up in O(1).",
                                confidence=0.85 if inner_iter_type in {"list", "tuple", None} else 0.6,
                                outer_var=a, inner_var=b,
                            )
                            return

    # PY011 -----------------------------------------------------------------
    def _rule_py011(self, node: ast.For) -> None:
        it = node.iter
        if isinstance(it, ast.Call) and isinstance(it.func, ast.Attribute) and it.func.attr == "iterrows":
            self._emit(
                "PY011", node,
                "`DataFrame.iterrows()` creates a pandas Series for every row and runs the loop body "
                "in interpreted Python.",
                "Replace the loop with vectorised column operations, `DataFrame.apply` on columns, or at "
                "least `itertuples()`.",
                confidence=0.75,
            )

    # ------------------------------------------------------------ statements
    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        # PY002: s += ... inside a loop where s is a str
        if (
            self._in_loop() and isinstance(node.op, ast.Add) and isinstance(node.target, ast.Name)
            and self.scope.types.get(node.target.id) == "str"
        ):
            self._emit(
                "PY002", node,
                f"`{node.target.id} += ...` inside a loop allocates a new string and copies the existing "
                "content on every iteration (quadratic in the total length).",
                "Collect the pieces in a list and call `''.join(parts)` once, or use an io.StringIO buffer.",
                confidence=0.85, target=node.target.id,
            )
        self.generic_visit(node)

    # ---------------------------------------------------------- expressions
    def visit_Compare(self, node: ast.Compare) -> None:
        # PY001: membership test against a list/tuple
        if len(node.ops) == 1 and isinstance(node.ops[0], (ast.In, ast.NotIn)):
            target = node.comparators[0]
            ttype = self._type_of(target)
            size = None
            if isinstance(target, ast.Name):
                size = self.scope.sizes.get(target.id)
            else:
                size = _literal_len(target)
            in_loop = self._in_loop()
            is_fresh_list = isinstance(target, ast.Call) and _dotted(target.func) == "list"
            if ttype in {"list", "tuple"} and not is_fresh_list and (in_loop or (size is not None and size >= 8)):
                desc = target.id if isinstance(target, ast.Name) else f"a {ttype} literal"
                self._emit(
                    "PY001", node,
                    f"Membership test against {desc} ({ttype}) is a linear scan"
                    + (" and it runs inside a loop, giving O(n*m) total work." if in_loop else "."),
                    "Convert the container to a `set` (or `dict`) once, outside the loop, so each test is O(1).",
                    confidence=0.9 if isinstance(target, (ast.List, ast.Tuple)) or ttype == "list" else 0.7,
                    container=desc, container_type=ttype, in_loop=in_loop, size=size,
                )
            elif (
                isinstance(target, ast.Call) and isinstance(target.func, ast.Attribute)
                and target.func.attr == "keys" and not target.args
            ):
                self._emit(
                    "PY008", node,
                    "`key in d.keys()` is equivalent to `key in d` but builds a view object first.",
                    "Test membership directly on the dictionary: `key in d`.",
                    confidence=0.9, kind="keys_membership",
                )
            elif isinstance(target, ast.Call) and _dotted(target.func) == "list":
                self._emit(
                    "PY008", node,
                    "Membership is tested against a freshly built list; the list is allocated only to be scanned once.",
                    "Test against the original iterable, or build a `set` once if the test repeats.",
                    confidence=0.85, kind="list_membership",
                )
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        # PY007: sorted(x)[0], sorted(x)[-1], sorted(x)[:k], sorted(x)[-k:]
        val = node.value
        if isinstance(val, ast.Call) and _dotted(val.func) == "sorted" and val.args:
            reverse = any(k.arg == "reverse" for k in val.keywords)
            sl = node.slice
            if isinstance(sl, ast.Constant) and sl.value in (0, -1):
                want_last = (sl.value == -1) != reverse
                fn = "max" if want_last else "min"
                self._emit(
                    "PY007", node,
                    "The whole sequence is sorted (O(n log n)) to retrieve a single extreme value.",
                    f"Use `{fn}(...)` (O(n)); pass the same `key=` argument if one is used.",
                    confidence=0.95, slice=sl.value, reverse=reverse,
                )
            elif isinstance(sl, ast.UnaryOp) and isinstance(sl.op, ast.USub) and isinstance(sl.operand, ast.Constant) and sl.operand.value == 1:
                fn = "min" if reverse else "max"
                self._emit(
                    "PY007", node,
                    "The whole sequence is sorted (O(n log n)) to retrieve a single extreme value.",
                    f"Use `{fn}(...)` (O(n)); pass the same `key=` argument if one is used.",
                    confidence=0.95, slice=-1, reverse=reverse,
                )
            elif isinstance(sl, ast.Slice) and sl.step is None and (
                (sl.lower is None and sl.upper is not None)
                or (sl.upper is None and isinstance(sl.lower, ast.UnaryOp))
            ):
                self._emit(
                    "PY007", node,
                    "The whole sequence is sorted to take only the first/last k items.",
                    "Use `heapq.nsmallest(k, ...)` / `heapq.nlargest(k, ...)`, which run in O(n log k).",
                    confidence=0.8, slice="k",
                )
        # PY008: list(x)[0] / list(x)[-1]
        if (
            isinstance(val, ast.Call) and _dotted(val.func) == "list" and len(val.args) == 1
            and isinstance(node.slice, ast.Constant) and node.slice.value in (0, -1)
        ):
            self._emit(
                "PY008", node,
                "A full list is materialised only to read its first/last element.",
                "Use `next(iter(x))` for the first element, or keep a list only where several indexes are needed.",
                confidence=0.8, kind="list_index",
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = _dotted(node.func)
        # PY008: len(list(...)), sum([...]), list(sorted(...)), sorted(list(...)), set(list(...))
        if name == "len" and len(node.args) == 1 and isinstance(node.args[0], ast.Call) and _dotted(node.args[0].func) == "list":
            self._emit(
                "PY008", node,
                "`len(list(iterable))` materialises the whole iterable just to count it.",
                "Use `sum(1 for _ in iterable)` or `len()` on the original container if it already supports it.",
                confidence=0.85, kind="len_list",
            )
        elif name in {"sum", "max", "min", "any", "all", "sorted", "set", "frozenset", "tuple"} and len(node.args) == 1 and isinstance(node.args[0], ast.ListComp):
            self._emit(
                "PY008", node,
                f"`{name}([...])` builds a complete intermediate list in memory before `{name}` consumes it"
                + (" and can't short-circuit." if name in {"any", "all"} else "."),
                f"Pass a generator expression instead: `{name}(x for x in ...)`.",
                confidence=0.9, kind="listcomp_arg", function=name,
            )
        elif name in {"list", "sorted", "set", "tuple", "frozenset"} and len(node.args) == 1 and isinstance(node.args[0], ast.Call) and _dotted(node.args[0].func) in {"list", "sorted", "tuple"} and not (name == "sorted" and _dotted(node.args[0].func) == "sorted"):
            inner = _dotted(node.args[0].func)
            self._emit(
                "PY008", node,
                f"`{name}({inner}(...))` creates an intermediate {inner} that is immediately copied.",
                f"Pass the iterable straight to `{name}(...)`.",
                confidence=0.9, kind="double_wrap", outer=name, inner=inner,
            )
        # PY009: database/network query inside a loop
        if self._in_loop():
            if (isinstance(node.func, ast.Attribute) and node.func.attr in QUERY_METHODS) or name in QUERY_FUNCS:
                callee = name or node.func.attr  # type: ignore[union-attr]
                self._emit(
                    "PY009", node,
                    f"`{callee}(...)` is executed on every loop iteration, issuing one round-trip per item "
                    "(the N+1 pattern). Each round-trip has fixed latency and planning cost.",
                    "Fetch everything in a single query (`WHERE id = ANY(%s)` / `IN (...)` / a JOIN) or use "
                    "`executemany` for writes, then process the rows in memory.",
                    confidence=0.8 if isinstance(node.func, ast.Attribute) and node.func.attr == "execute" else 0.6,
                    callee=callee,
                )
            else:
                self._rule_py005(node, name)
        self.generic_visit(node)

    # PY005 -----------------------------------------------------------------
    def _rule_py005(self, node: ast.Call, name: str | None) -> None:
        is_expensive = False
        label = name
        if name in EXPENSIVE_FUNCS or name in EXPENSIVE_DOTTED:
            is_expensive = True
        elif isinstance(node.func, ast.Attribute) and node.func.attr in EXPENSIVE_METHODS:
            is_expensive = True
            label = f".{node.func.attr}"
        if not is_expensive:
            return
        varying = self._loop_varying_names()
        used = _names_in(node)
        # A call is loop-invariant if nothing it references changes inside any enclosing loop.
        if used & varying:
            return
        # Avoid flagging calls whose result is the loop's own iterable header (`for x in sorted(y)`)
        # unless there's an *outer* loop — in which case it IS repeated.
        innermost = self.loops[-1]
        if isinstance(innermost.node, ast.For) and node is innermost.node.iter and len(self.loops) == 1:
            return
        gens = getattr(innermost.node, "generators", None)
        if gens and node is gens[0].iter and len(self.loops) == 1:
            return
        if not used:
            # e.g. re.compile("literal") — constant args, still repeated.
            pass
        self._emit(
            "PY005", node,
            f"`{label}(...)` does not depend on any loop variable, so the same result is recomputed on "
            "every iteration.",
            "Compute it once before the loop (hoist the call) and reuse the result.",
            confidence=0.75 if used else 0.9, callee=label, depth=len(self.loops),
        )


def analyse_python(source: str) -> list[Finding]:
    tree = ast.parse(source)
    analyser = _PythonAnalyser(source)
    analyser.visit(tree)
    analyser.findings.sort(key=lambda f: (f.line or 0, f.rule_id))
    return analyser.findings


def iter_rules() -> Iterable[RuleInfo]:
    return PYTHON_RULES
