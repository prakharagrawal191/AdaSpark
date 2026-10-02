"""Exact nonparametric inference: the frozen PLAN section 22 test family.

PLAN section 22 names the statistics for every comparison in this project:
paired Wilcoxon signed-rank (paired by workload instance), Mann-Whitney U
where unpaired, Cliff's delta, and Holm-Bonferroni correction. No analysis
before EXP-013 ran them (EXP-005 had six common cells, DAY34 section 5), so
they are implemented here for the first time.

Exact null distributions only: the samples in this repository (5-repetition
cells, a few dozen workload instances) are far too small for normal
approximations. Ties are kept exact by enumerating over (doubled) average
ranks. Standard library only, like every analyzer in this repository.
"""
from __future__ import annotations

import itertools
import math
import random
from typing import Sequence

_ALTERNATIVES = ("less", "greater", "two-sided")


def average_ranks(values: Sequence[float]) -> list[float]:
    """1-based ranks; tied values share the mean of the ranks they span."""
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def _tail(p_le: float, p_ge: float, alternative: str) -> float:
    if alternative == "less":
        return p_le
    if alternative == "greater":
        return p_ge
    if alternative == "two-sided":
        return min(1.0, 2.0 * min(p_le, p_ge))
    raise ValueError(f"alternative must be one of {_ALTERNATIVES}, got {alternative!r}")


def wilcoxon_signed_rank(d: Sequence[float], alternative: str = "less") -> dict:
    """Exact Wilcoxon signed-rank test of H0: the differences are symmetric about 0.

    Zero differences are dropped (Wilcoxon's convention); tied |d| take average
    ranks and the null distribution of W+ is enumerated exactly over doubled
    ranks. ``alternative='less'`` tests median(d) < 0.
    """
    nz = [float(x) for x in d if x != 0]
    n = len(nz)
    if n == 0:
        return {"n": 0, "w_plus": 0.0, "p": 1.0, "zeros_dropped": len(d)}
    ranks = average_ranks([abs(x) for x in nz])
    w_plus = sum(r for r, x in zip(ranks, nz) if x > 0)
    doubled = [int(round(2 * r)) for r in ranks]
    total = sum(doubled)
    count = [0] * (total + 1)       # count[s]: sign assignments with 2*W+ == s
    count[0] = 1
    for v in doubled:
        for s in range(total, v - 1, -1):
            count[s] += count[s - v]
    w2 = int(round(2 * w_plus))
    denom = float(2 ** n)
    p = _tail(sum(count[:w2 + 1]) / denom, sum(count[w2:]) / denom, alternative)
    return {"n": n, "w_plus": w_plus, "p": p, "zeros_dropped": len(d) - n}


MAX_EXACT_SPLITS = 200_000


def mann_whitney(x: Sequence[float], y: Sequence[float], alternative: str = "less") -> dict:
    """Exact Mann-Whitney U test from the permutation distribution of x's rank sum.

    Exact under ties (average ranks, every split enumerated). ``'less'`` tests
    that x tends to be smaller than y. Refuses samples too large to enumerate
    rather than silently switching to an approximation.
    """
    m, n = len(x), len(y)
    if m == 0 or n == 0:
        raise ValueError("both samples must be non-empty")
    if math.comb(m + n, m) > MAX_EXACT_SPLITS:
        raise ValueError(f"C({m + n},{m}) splits exceeds the exact-enumeration cap")
    ranks = average_ranks(list(x) + list(y))
    r_x = sum(ranks[:m])
    le = ge = total = 0
    for idx in itertools.combinations(range(m + n), m):
        s = sum(ranks[i] for i in idx)
        total += 1
        le += s <= r_x + 1e-9
        ge += s >= r_x - 1e-9
    return {"m": m, "n": n, "u_x": r_x - m * (m + 1) / 2,
            "p": _tail(le / total, ge / total, alternative)}


def cliffs_delta(x: Sequence[float], y: Sequence[float]) -> float:
    """P(x > y) - P(x < y); negative means x tends to be smaller (faster)."""
    gt = sum(1 for a in x for b in y if a > b)
    lt = sum(1 for a in x for b in y if a < b)
    return (gt - lt) / (len(x) * len(y))


def holm(pvals: Sequence[float]) -> list[float]:
    """Holm-Bonferroni adjusted p-values, monotone, capped at 1, input order kept."""
    m = len(pvals)
    adjusted = [0.0] * m
    running = 0.0
    for k, i in enumerate(sorted(range(m), key=pvals.__getitem__)):
        running = max(running, min(1.0, (m - k) * pvals[i]))
        adjusted[i] = running
    return adjusted


def geometric_mean_ratio(log_ratios: Sequence[float], resamples: int = 4000,
                         seed: int = 0) -> dict:
    """exp(mean log-ratio) with a 95% percentile bootstrap CI over the units.

    Same resample count, seed and percentile indexing as analyze_exp009.py, so
    every interval in the repository is computed one way.
    """
    vals = list(log_ratios)
    n = len(vals)
    if n == 0:
        return {"n": 0, "gmr": None, "ci95": None}
    rng = random.Random(seed)
    draws = sorted(math.exp(sum(vals[rng.randrange(n)] for _ in range(n)) / n)
                   for _ in range(resamples))
    return {"n": n, "gmr": math.exp(sum(vals) / n),
            "ci95": (draws[int(0.025 * resamples)],
                     draws[min(int(0.975 * resamples), resamples - 1)])}
