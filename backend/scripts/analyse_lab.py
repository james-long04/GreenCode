#!/usr/bin/env python3
"""Turn lab.csv (scripts/run_tpch.py --export) into the tables and figures for the report.

    python scripts\\analyse_lab.py lab.csv --out lab-analysis

Writes into --out:
  wp1_baseline.csv / .md     per-query medians over passes, net J per execution, mean W, J per 1000 rows
  wp2_overhead.csv / .md     time ratio of each meter to 'none' per query; geomean, median, paired Wilcoxon
  wp2_energy_methods.md      RAPL (LHM) vs CodeCarbon energy per query
  wp3_power_modes.csv / .md  per plan label: time and energy ratio to the reference plan (when wp3 exists)
  wp4_complex.md             complex-query table (when wp4 exists)
  summary.md                 the headline numbers (TPC-Energy-style totals per pass, groups)
  figures/*.png              if matplotlib is installed

Only completed rows at the dominant scale factor are used.
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

try:
    from scipy import stats as _st  # type: ignore
except Exception:  # pragma: no cover
    _st = None


def fnum(v):  # type: ignore[no-untyped-def]
    try:
        return float(v) if v not in (None, "", "None") else None
    except ValueError:
        return None


def geomean(xs):  # type: ignore[no-untyped-def]
    xs = [x for x in xs if x and x > 0]
    return math.exp(sum(map(math.log, xs)) / len(xs)) if xs else None


def _fmt(x: float) -> str:
    a = abs(x)
    return f"{x:,.0f}" if a >= 100 else (f"{x:.1f}" if a >= 10 else f"{x:.2f}")


def md_table(headers, rows):  # type: ignore[no-untyped-def]
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join("" if c is None else (_fmt(c) if isinstance(c, float) else str(c)) for c in r) + " |")
    return "\n".join(out)


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    print("  wrote", path)


def load(path: Path):  # type: ignore[no-untyped-def]
    rows = [r for r in csv.DictReader(open(path, encoding="utf-8")) if r.get("status") == "completed"]
    sfs = Counter(r.get("scale_factor") for r in rows)
    sf = sfs.most_common(1)[0][0] if sfs else None
    rows = [r for r in rows if r.get("scale_factor") == sf]
    for r in rows:
        r["_median"] = fnum(r["median_ms"]); r["_net"] = fnum(r["energy_joules_net"]); r["_reps"] = int(r["repetitions"])
        r["_w"] = fnum(r.get("mean_watts")); r["_rows"] = fnum(r.get("rows_returned")); r["_exec"] = fnum(r.get("pg_execution_ms"))
        r["_par"] = fnum(r.get("pg_parallel_workers")); r["_cc"] = fnum(r.get("energy_estimate_joules"))
        r["_jpe"] = (r["_net"] / r["_reps"]) if r["_net"] is not None and r["_reps"] else None
    return rows, sf


def per_query_median(rows, key):  # type: ignore[no-untyped-def]
    by = defaultdict(list)
    for r in rows:
        if r[key] is not None:
            by[r["query_id"]].append(r[key])
    return {q: st.median(v) for q, v in by.items()}


def wp1(rows, out: Path, figs: Path):  # type: ignore[no-untyped-def]
    rs = [r for r in rows if r["work_package"] == "wp1"]
    if not rs:
        return None
    # The baseline is the standard mode (plan=balanced) when present; other labelled runs are reported separately.
    labels = sorted({r["condition"].split("plan=")[-1] if "plan=" in r["condition"] else "(unlabelled: best-efficiency on 3 Nov 2026)" for r in rs})
    std = "balanced" if "balanced" in labels else labels[0]
    rs = [r for r in rs if (r["condition"].split("plan=")[-1] if "plan=" in r["condition"] else labels[0]) == std]
    print(f"  WP1 baseline mode: {std} (others present: {[l for l in labels if l != std]})")
    qs = sorted({r["query_id"] for r in rs})
    med = per_query_median(rs, "_median"); jpe = per_query_median(rs, "_jpe"); w = per_query_median(rs, "_w")
    ex = per_query_median(rs, "_exec"); par = per_query_median(rs, "_par") if any(r["_par"] is not None for r in rs) else {}
    nrows = {r["query_id"]: r["_rows"] for r in rs}
    passes = Counter(r["query_id"] for r in rs)
    table = []
    for q in qs:
        j1k = (jpe[q] / nrows[q] * 1000) if jpe.get(q) is not None and nrows.get(q) else None
        slow = (med[q] / ex[q]) if ex.get(q) else None
        table.append([q, passes[q], med[q], ex.get(q), slow, w.get(q), jpe.get(q), j1k, int(nrows[q]) if nrows.get(q) else None,
                      (int(par[q]) if par.get(q) is not None else None)])
    hdr = ["query", "passes", "median ms", "EXPLAIN exec ms", "client/exec", "mean W", "net J / exec", "J per 1000 rows", "rows", "parallel workers"]
    with open(out / "wp1_baseline.csv", "w", newline="") as fh:
        cw = csv.writer(fh); cw.writerow(hdr); cw.writerows(table)
    total_ms = sum(med[q] for q in qs); total_j = sum(jpe[q] for q in qs if jpe.get(q) is not None)
    low = [q for q in qs if w.get(q) is not None and w[q] < 10]; high = [q for q in qs if w.get(q) is not None and w[q] >= 10]
    md = [f"# WP1 — baseline (TPC-H-derived, SF 1, hot cache, Windows power mode: {std})", "",
          md_table(hdr, table), "",
          f"**One pass over the 22 queries:** {total_ms / 1000:.1f} s of query time, {total_j:.0f} J net "
          f"(TPC-Energy-style energy per query set), {total_j / (total_ms / 1000):.1f} W average net power.", "",
          f"**Power groups:** {len(high)} queries at ≥10 W mean ({', '.join(high)}); {len(low)} queries below 10 W "
          f"({', '.join(low)}). The low-power group's client time exceeds its own EXPLAIN ANALYZE time by "
          f"{geomean([med[q] / ex[q] for q in low if ex.get(q)]) or 0:.2f}× on average versus "
          f"{geomean([med[q] / ex[q] for q in high if ex.get(q)]) or 0:.2f}× for the rest.", ""]
    write(out / "wp1_baseline.md", "\n".join(md))
    _bar(figs / "wp1_energy_per_exec.png", qs, [jpe.get(q) or 0 for q in qs], "Net energy per execution (J)", "WP1 — energy per query execution")
    _bar(figs / "wp1_mean_watts.png", qs, [w.get(q) or 0 for q in qs], "Mean package power (W)", "WP1 — mean power during the query loop")
    return {"total_ms": total_ms, "total_j": total_j, "low": low, "high": high}


def wp2(rows, out: Path, figs: Path):  # type: ignore[no-untyped-def]
    rs = [r for r in rows if r["work_package"] == "wp2"]
    if not rs:
        return None
    by = defaultdict(dict)
    for r in rs:
        by[r["query_id"]][r["condition"].split(";")[0]] = r
    base = "meter=none"
    conds = sorted({c for d in by.values() for c in d if c != base})
    qs = sorted(q for q in by if base in by[q])
    table = []; ratios = defaultdict(list)
    for q in qs:
        b = by[q][base]["_median"]
        row = [q, b]
        for c in conds:
            r = by[q].get(c)
            ratio = (r["_median"] / b) if r and b else None
            row.append(ratio)
            if ratio: ratios[c].append(ratio)
        table.append(row)
    hdr = ["query", "none ms"] + [c.replace("meter=", "") + " ÷ none" for c in conds]
    with open(out / "wp2_overhead.csv", "w", newline="") as fh:
        cw = csv.writer(fh); cw.writerow(hdr); cw.writerows(table)
    summ = []
    for c in conds:
        p = None
        if _st is not None and len(ratios[c]) >= 5:
            try:
                p = float(_st.wilcoxon([math.log(x) for x in ratios[c]]).pvalue)  # H0: log ratio = 0
            except ValueError:
                p = None
        summ.append([c.replace("meter=", ""), len(ratios[c]), geomean(ratios[c]), st.median(ratios[c]),
                     min(ratios[c]), max(ratios[c]), p])
    md = ["# WP2 — does measuring change the measurement?", "",
          "Median client time of each query under each meter, divided by the same query with no meter.", "",
          md_table(hdr, table), "", "## Summary", "",
          md_table(["meter", "queries", "geomean ratio", "median ratio", "min", "max", "Wilcoxon p (vs 1.0)"], summ), "",
          "A ratio of 1.00 means no overhead. The Wilcoxon test asks whether the paired log-ratios differ from zero across the 22 queries.", ""]
    # energy methods
    e_rows = []
    for q in qs:
        a = by[q].get("meter=lhm@0.1"); b5 = by[q].get("meter=lhm@0.5"); c = by[q].get("meter=codecarbon")
        if a and a["_jpe"] is not None:
            e_rows.append([q, a["_jpe"], b5["_jpe"] if b5 else None, c["_jpe"] if c else None,
                           (c["_jpe"] / a["_jpe"]) if c and a["_jpe"] else None, a["_w"]])
    md2 = ["# WP2 — energy by method (J per execution)", "",
           md_table(["query", "RAPL/LHM 0.1 s", "RAPL/LHM 0.5 s", "CodeCarbon", "CodeCarbon ÷ RAPL", "mean W (RAPL)"], e_rows), "",
           f"CodeCarbon ÷ RAPL geomean: {geomean([r[4] for r in e_rows if r[4]]) or 0:.2f}. On Windows CodeCarbon has no RAPL access and estimates "
           "from TDP × CPU load with no idle subtraction, so it cannot see the low-power group at all.", ""]
    write(out / "wp2_overhead.md", "\n".join(md)); write(out / "wp2_energy_methods.md", "\n".join(md2))
    _bar(figs / "wp2_overhead.png", [c.replace("meter=", "") for c in conds], [geomean(ratios[c]) or 0 for c in conds],
         "Geomean time ratio vs no meter", "WP2 — measurement overhead", ref=1.0)
    return {c: geomean(ratios[c]) for c in conds}


def wp3(rows, out: Path, figs: Path):  # type: ignore[no-untyped-def]
    rs = [r for r in rows if r["work_package"] == "wp3"]
    if not rs:
        return None
    plans = sorted({r["condition"].split("plan=")[-1] for r in rs if "plan=" in r["condition"]})
    by = defaultdict(lambda: defaultdict(list))
    for r in rs:
        plan = r["condition"].split("plan=")[-1]
        by[r["query_id"]][plan].append(r)
    ref = "best-efficiency" if "best-efficiency" in plans else ("balanced" if "balanced" in plans else plans[0])
    qs = sorted(q for q in by if ref in by[q])
    table = []; tr = defaultdict(list); er = defaultdict(list)
    for q in qs:
        bt = st.median([r["_median"] for r in by[q][ref]]); be = st.median([r["_jpe"] for r in by[q][ref] if r["_jpe"] is not None] or [0])
        row = [q, bt, be]
        for p in plans:
            if p == ref or p not in by[q]:
                row += [None, None]; continue
            t = st.median([r["_median"] for r in by[q][p]]); e = st.median([r["_jpe"] for r in by[q][p] if r["_jpe"] is not None] or [0])
            row += [t / bt if bt else None, e / be if be else None]
            if bt: tr[p].append(t / bt)
            if be and e: er[p].append(e / be)
        table.append(row)
    hdr = ["query", f"{ref} ms", f"{ref} J/exec"] + [x for p in plans if p != ref for x in (f"{p} time ÷", f"{p} energy ÷")]
    with open(out / "wp3_power_modes.csv", "w", newline="") as fh:
        cw = csv.writer(fh); cw.writerow(hdr); cw.writerows(table)
    summ = [[p, len(tr[p]), geomean(tr[p]), geomean(er[p])] for p in plans if p != ref]
    md = ["# WP3 — power management", "", f"Reference plan: **{ref}**. Ratios < 1 are faster / lower energy than the reference.", "",
          md_table(hdr, table), "", "## Summary (geometric means across queries)", "",
          md_table(["plan", "queries", "time ÷ ref", "energy ÷ ref"], summ), ""]
    # totals per pass and the serial (<10 W under the reference) group
    totals = []
    for p in plans:
        t = sum(st.median([r["_median"] for r in by[q][p]]) for q in qs if p in by[q]) / 1000
        e = sum(st.median([r["_jpe"] for r in by[q][p] if r["_jpe"] is not None] or [0]) for q in qs if p in by[q])
        totals.append([p, t, e, e / t if t else None])
    serial = [q for q in qs if st.median([r["_w"] for r in by[q][ref] if r["_w"] is not None] or [99]) < 10]
    srows = []
    for p in plans:
        if p == ref: continue
        tt = [st.median([r["_median"] for r in by[q][p]]) / st.median([r["_median"] for r in by[q][ref]]) for q in serial if p in by[q]]
        ee = [st.median([r["_jpe"] for r in by[q][p]]) / st.median([r["_jpe"] for r in by[q][ref]]) for q in serial if p in by[q]]
        srows.append([p, len(tt), geomean(tt), geomean(ee)])
    md += ["## One pass over the query set", "", md_table(["plan", "query time (s)", "net energy (J)", "avg net W"], totals), "",
           f"## Serial (<10 W under {ref}) queries only: {', '.join(serial)}", "", md_table(["plan", "queries", "time ÷ ref", "energy ÷ ref"], srows), ""]
    write(out / "wp3_power_modes.md", "\n".join(md))
    _grouped(figs / "wp3_time_ratio.png", qs, {p: [ (st.median([r["_median"] for r in by[q][p]]) / st.median([r["_median"] for r in by[q][ref]])) if p in by[q] else 0 for q in qs] for p in plans if p != ref},
             f"Median time ÷ {ref}", "WP3 — time by power mode", ref=1.0)
    _grouped(figs / "wp3_energy_ratio.png", qs, {p: [ (st.median([r["_jpe"] for r in by[q][p]]) / st.median([r["_jpe"] for r in by[q][ref]])) if p in by[q] else 0 for q in qs] for p in plans if p != ref},
             f"Net J per execution ÷ {ref}", "WP3 — energy by power mode", ref=1.0)
    return summ


def wp4(rows, out: Path):  # type: ignore[no-untyped-def]
    rs = [r for r in rows if r["work_package"] == "wp4"]
    if not rs:
        return None
    qs = sorted({r["query_id"] for r in rs})
    med = per_query_median(rs, "_median"); jpe = per_query_median(rs, "_jpe"); w = per_query_median(rs, "_w"); ex = per_query_median(rs, "_exec")
    table = [[q, med[q], ex.get(q), w.get(q), jpe.get(q)] for q in qs]
    write(out / "wp4_complex.md", "\n".join(["# WP4 — complex queries", "", md_table(["query", "median ms", "EXPLAIN exec ms", "mean W", "net J / exec"], table), ""]))
    return table


def _grouped(path: Path, labels, series: dict, ylabel, title, ref=None):  # type: ignore[no-untyped-def]
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    n = len(series); width = 0.8 / max(n, 1)
    fig, ax = plt.subplots(figsize=(max(6, 0.5 * len(labels) + 2), 3.8))
    colours = ["#2E8B57", "#C65A00", "#2F6DB5", "#6A3FB5"]
    for i, (name, vals) in enumerate(series.items()):
        ax.bar([x + (i - (n - 1) / 2) * width for x in range(len(labels))], vals, width, label=name, color=colours[i % len(colours)])
    if ref is not None:
        ax.axhline(ref, color="#555", linewidth=1, linestyle="--")
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=60, fontsize=8)
    ax.set_ylabel(ylabel); ax.set_title(title); ax.legend(frameon=False)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)
    print("  wrote", path)


def _bar(path: Path, labels, values, ylabel, title, ref=None):  # type: ignore[no-untyped-def]
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    fig, ax = plt.subplots(figsize=(max(6, 0.42 * len(labels) + 2), 3.6))
    ax.bar(labels, values, color="#2E8B57")
    if ref is not None:
        ax.axhline(ref, color="#555", linewidth=1, linestyle="--")
    ax.set_ylabel(ylabel); ax.set_title(title); ax.tick_params(axis="x", rotation=60, labelsize=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)
    print("  wrote", path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv"); ap.add_argument("--out", default="lab-analysis")
    a = ap.parse_args()
    out = Path(a.out); figs = out / "figures"; figs.mkdir(parents=True, exist_ok=True)
    rows, sf = load(Path(a.csv))
    print(f"{len(rows)} completed rows at scale factor {sf}")
    s1 = wp1(rows, out, figs); s2 = wp2(rows, out, figs); s3 = wp3(rows, out, figs); s4 = wp4(rows, out)
    lines = [f"# Laboratory summary (scale factor {sf})", ""]
    if s2:
        lines += ["## WP2 measurement overhead (geomean time ratio vs no meter)", ""] + [f"- {c.replace('meter=', '')}: {v:.3f}" for c, v in s2.items()] + [""]
    if s1:
        lines += ["## WP1 baseline", "", f"- one pass: {s1['total_ms'] / 1000:.1f} s, {s1['total_j']:.0f} J net",
                  f"- ≥10 W group: {', '.join(s1['high'])}", f"- <10 W group: {', '.join(s1['low'])}", ""]
    if s3:
        lines += ["## WP3 power modes (geomean vs reference)", ""] + [f"- {p}: time {t:.3f}, energy {e:.3f}" for p, n, t, e in s3] + [""]
    if s4:
        lines += [f"## WP4: {len(s4)} complex queries analysed", ""]
    write(out / "summary.md", "\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
