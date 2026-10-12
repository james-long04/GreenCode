"""Descriptive and comparative statistics for benchmark samples."""

from __future__ import annotations

import math
import statistics
from dataclasses import asdict, dataclass
from typing import Any, Sequence

try:  # scipy gives exact t critical values and Mann-Whitney U; fall back gracefully.
    from scipy import stats as _scipy_stats  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    _scipy_stats = None


@dataclass
class Summary:
    n: int
    mean: float
    median: float
    stdev: float
    min: float
    max: float
    ci95_low: float
    ci95_high: float
    cv: float  # coefficient of variation (stdev / mean)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarise(samples: Sequence[float]) -> Summary:
    xs = [float(x) for x in samples]
    n = len(xs)
    if n == 0:
        raise ValueError("no samples")
    mean = statistics.fmean(xs)
    median = statistics.median(xs)
    stdev = statistics.stdev(xs) if n > 1 else 0.0
    if n > 1:
        if _scipy_stats is not None:
            t = float(_scipy_stats.t.ppf(0.975, n - 1))
        else:
            t = 1.96
        half = t * stdev / math.sqrt(n)
    else:
        half = 0.0
    return Summary(n=n, mean=mean, median=median, stdev=stdev, min=min(xs), max=max(xs),
                   ci95_low=mean - half, ci95_high=mean + half, cv=(stdev / mean) if mean else 0.0)


def cliffs_delta(a: Sequence[float], b: Sequence[float]) -> float:
    """Effect size in [-1, 1]: positive when values in ``a`` tend to be larger than ``b``."""
    if not a or not b:
        return 0.0
    more = less = 0
    for x in a:
        for y in b:
            if x > y:
                more += 1
            elif x < y:
                less += 1
    return (more - less) / (len(a) * len(b))


def compare(original: Sequence[float], candidate: Sequence[float]) -> dict[str, Any]:
    """Compare two timing distributions (lower is better).

    Returns speed-up (original/candidate medians), percentage change, Cliff's delta
    and a Mann–Whitney U p-value when scipy is available.
    """
    o, c = summarise(original), summarise(candidate)
    speedup = (o.median / c.median) if c.median else float("inf")
    pct = ((c.median - o.median) / o.median * 100) if o.median else 0.0
    out: dict[str, Any] = {
        "original_median": o.median,
        "candidate_median": c.median,
        "speedup": speedup,
        "percent_change": pct,
        "cliffs_delta": cliffs_delta(list(original), list(candidate)),
        "ci_overlap": not (o.ci95_high < c.ci95_low or c.ci95_high < o.ci95_low),
    }
    if _scipy_stats is not None and len(original) > 1 and len(candidate) > 1:
        try:
            u = _scipy_stats.mannwhitneyu(original, candidate, alternative="two-sided")
            out["mann_whitney_p"] = float(u.pvalue)
        except ValueError:
            out["mann_whitney_p"] = None
    else:
        out["mann_whitney_p"] = None
    p = out["mann_whitney_p"]
    out["significant"] = (p is not None and p < 0.05)
    out["verdict"] = (
        "faster" if speedup > 1.0 and out["significant"] else
        "slower" if speedup < 1.0 and out["significant"] else "no_significant_change"
    )
    return out


def wilcoxon_paired(a: Sequence[float], b: Sequence[float]) -> float | None:
    """Paired test across cases (e.g. per-case speed-ups under two conditions)."""
    if _scipy_stats is None or len(a) < 5 or len(a) != len(b):
        return None
    try:
        return float(_scipy_stats.wilcoxon(a, b).pvalue)
    except ValueError:
        return None
