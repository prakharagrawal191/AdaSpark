#!/usr/bin/env python
"""Render project figures from committed analyses. 0 Spark, 0 SC6, read-only.

PLAN s37's Definition of Done asks for visualisations; only the two EXP-009
figures existed. This renders the figures that the ALREADY-COLLECTED data
supports, and nothing beyond it. It executes no Spark, reads only committed
analysis artifacts, and writes only under docs/figures/.

HONESTY CONSTRAINTS BAKED INTO THE FIGURES, not left to the caption writer:

  * EXP-005 is DESCRIPTIVE ONLY. DEC-020 A closed it with H2, H3, SC2, SC3
    and SC4 recorded as UNDECIDED - not failed - because the frozen protocol
    names the statistical procedures but freezes no parameters or
    hypothesis-to-comparison mapping executable for the actual 7-arm,
    unequal-coverage structure. No inferential test was run and none is
    invented here, so the EXP-005 figure carries that status in the plot
    itself and draws the DEC-018 Decision F noise band (within-cell arm gaps
    below ~12% are not independently established effects). A reader must not
    be able to take a ranking from this figure without also taking the
    caveat.

  * Coverage is stated, never implied. The 6-cell panel and the 3-cell B2
    panel are drawn separately because B2 is defined on fewer cells; merging
    them would silently compare different cell sets.

  * F3_rdd|large|s3 failed in all arms (0/5, WinError 32 sort/spill) and is
    excluded upstream; the exclusion is printed on the figure rather than
    left in a JSON field nobody opens.

Stdlib only: the analysis environment deliberately has no numpy/matplotlib.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
FIGDIR = PROJECT / "docs" / "figures"
EXP002 = PROJECT / "results" / "experiments" / "exp-002" / "analysis" / "gate.json"
EXP005 = PROJECT / "results" / "evaluation" / "exp005_analysis.json"
EXP007 = PROJECT / "results" / "evaluation" / "exp007_analysis.json"

# Arm roles, so the figure distinguishes "what kind of thing is this" rather
# than presenting seven equivalent bars.
ROLE = {
    "B0": ("Spark default", "#7f8c8d"),
    "B1": ("static heuristic", "#1e8449"),
    "B2": ("static heuristic", "#148f77"),
    "B4": ("search-derived", "#1f4e79"),
    "RL-s0": ("learned policy", "#b03a2e"),
    "RL-s1": ("learned policy", "#c0562f"),
    "RL-s2": ("learned policy", "#d68910"),
}


def _f(x: float) -> str:
    return ("%.2f" % x).rstrip("0").rstrip(".")


def _open(w: int, h: int, title: str, sub: str, left: int) -> list[str]:
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
         'viewBox="0 0 %d %d" font-family="DejaVu Sans, Arial, sans-serif">'
         % (w, h, w, h),
         '<rect width="%d" height="%d" fill="#ffffff"/>' % (w, h),
         '<text x="%d" y="28" font-size="16" font-weight="bold" fill="#111">'
         '%s</text>' % (left, title)]
    for i, line in enumerate(sub.split("\n")):
        o.append('<text x="%d" y="%d" font-size="11" fill="#555">%s</text>'
                 % (left, 46 + i * 14, line))
    return o


def fig_exp002_sensitivity() -> Path:
    """SC1 evidence: configuration spread per family and scale, vs the gate."""
    g = json.loads(EXP002.read_text(encoding="utf-8"))["gate"]
    fams = g["families"]
    thr = g["criteria"]["min_relative_spread"]
    W, H, L, T, BH, GAP = 900, 430, 110, 96, 26, 16
    o = _open(W, H, "EXP-002: configuration sensitivity per workload family",
              "relative spread of median execution_time_s across the 12-point "
              "configuration grid; log axis.\ngate (SC1): spread must exceed "
              "%.0f%% AND exceed pooled within-configuration noise, on >= 2 "
              "families. Result: PASS (%d of 4)."
              % (thr * 100, g["n_families_sensitive"]), L)
    rows = [(f, s, v) for f, d in fams.items()
            for s, v in sorted(d["spread_by_scale"].items())]
    vmax = max(v for _f_, _s, v in rows) * 1.25
    PW = W - L - 150

    def px(v: float) -> float:
        lo = math.log10(max(thr * 0.5, 1e-3))
        return L + PW * (math.log10(max(v, thr * 0.5)) - lo) / (
            math.log10(vmax) - lo)

    y = T
    for fam, scale, v in rows:
        col = "#1f4e79" if v >= thr else "#b03a2e"
        o.append('<text x="%d" y="%d" font-size="11" fill="#222" '
                 'text-anchor="end">%s|%s</text>' % (L - 8, y + 17, fam, scale))
        o.append('<rect x="%d" y="%d" width="%s" height="%d" fill="%s" '
                 'opacity="0.85"/>' % (L, y, _f(max(px(v) - L, 1)), BH, col))
        o.append('<text x="%s" y="%d" font-size="11" fill="#111">%.0f%%</text>'
                 % (_f(px(v) + 7), y + 17, v * 100))
        y += BH + GAP
    X = px(thr)
    o.append('<line x1="%s" y1="%d" x2="%s" y2="%d" stroke="#d68910" '
             'stroke-width="2" stroke-dasharray="4,3"/>' % (_f(X), T - 8, _f(X), y))
    o.append('<text x="%s" y="%d" font-size="11" fill="#d68910">gate %.0f%%'
             '</text>' % (_f(X + 5), y + 16, thr * 100))
    o.append('<text x="%d" y="%d" font-size="10" fill="#888">source: '
             'results/experiments/exp-002/analysis/gate.json</text>'
             % (L, H - 8))
    o.append("</svg>")
    p = FIGDIR / "exp002_configuration_sensitivity.svg"
    p.write_text("\n".join(o), encoding="utf-8")
    return p


def _arm_panel(o: list[str], data: dict[str, float], x0: int, y0: int,
               pw: int, ph: int, title: str, noise: float) -> None:
    arms = list(data)
    vmax = max(data.values()) * 1.12
    bw = pw / (len(arms) * 1.6)
    best = min(data.values())
    o.append('<text x="%d" y="%d" font-size="12" font-weight="bold" '
             'fill="#111">%s</text>' % (x0, y0 - 10, title))
    o.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" '
             'stroke="#333"/>' % (x0, y0, pw, ph))
    # noise band around the best arm: gaps inside it are not established
    band = best * (1.0 + noise)
    yb = y0 + ph * (1.0 - band / vmax)
    ybest = y0 + ph * (1.0 - best / vmax)
    o.append('<rect x="%d" y="%s" width="%d" height="%s" fill="#d68910" '
             'opacity="0.14"/>' % (x0, _f(yb), pw, _f(max(ybest - yb, 1))))
    o.append('<text x="%d" y="%s" font-size="9" fill="#a06000">within '
             '%.1f%% of best = not an established difference (DEC-018 F)'
             '</text>' % (x0 + 5, _f(yb - 4), noise * 100))
    for i, a in enumerate(arms):
        v = data[a]
        cx = x0 + pw * (i + 0.5) / len(arms) - bw / 2
        bh = ph * v / vmax
        label, col = ROLE.get(a, (a, "#555"))
        o.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" '
                 'opacity="0.88"/>'
                 % (_f(cx), _f(y0 + ph - bh), _f(bw), _f(bh), col))
        o.append('<text x="%s" y="%s" font-size="10" fill="#111" '
                 'text-anchor="middle">%.1f</text>'
                 % (_f(cx + bw / 2), _f(y0 + ph - bh - 5), v))
        o.append('<text x="%s" y="%d" font-size="10" fill="#222" '
                 'text-anchor="middle">%s</text>'
                 % (_f(cx + bw / 2), y0 + ph + 15, a))
        o.append('<text x="%s" y="%d" font-size="8" fill="#777" '
                 'text-anchor="middle">%s</text>'
                 % (_f(cx + bw / 2), y0 + ph + 27, label))


def fig_exp005_arms() -> Path:
    """EXP-005 descriptive comparison. NOT an inferential result."""
    d = json.loads(EXP005.read_text(encoding="utf-8"))
    six = d["descriptive_sum_of_medians_6cell"]
    three = d["descriptive_sum_of_medians_b2_3cell"]
    noise = d["noise_band_cv"]
    W, H, L = 980, 560, 90
    o = _open(W, H,
              "EXP-005: sum of median execution_time_s by arm (DESCRIPTIVE ONLY)",
              "H2, H3, SC2, SC3, SC4 are UNDECIDED - NOT failed - per DEC-020 A: "
              "the frozen protocol names the statistical\nprocedures but freezes "
              "no parameters or hypothesis-to-comparison mapping executable for "
              "this 7-arm, unequal-coverage\nstructure. NO inferential test was "
              "run and none is invented here. Lower is better.", L)
    _arm_panel(o, six, L, 132, 380, 300,
               "6 cells common to all non-B2 arms", noise)
    _arm_panel(o, three, L + 480, 132, 380, 300,
               "3 cells where B2 is also defined", noise)
    o.append('<text x="%d" y="%d" font-size="10" fill="#444">Every tuned arm '
             'beats the Spark default by 3-4.7x. No learned policy (RL-s*) '
             'beats the best static heuristic (B1).</text>' % (L, H - 44))
    o.append('<text x="%d" y="%d" font-size="10" fill="#444">Panels use '
             'DIFFERENT cell sets and are not comparable to each other: B2 is '
             'defined on 3 of the 6 cells.</text>' % (L, H - 30))
    o.append('<text x="%d" y="%d" font-size="9" fill="#888">excluded upstream: '
             '%s | source: results/evaluation/exp005_analysis.json</text>'
             % (L, H - 12, d["excluded_f3_cell"]))
    o.append("</svg>")
    p = FIGDIR / "exp005_arm_comparison.svg"
    p.write_text("\n".join(o), encoding="utf-8")
    return p


def fig_exp007_ablation() -> Path:
    """EXP-007 A1/A2 state ablation: per-run TRAIN episode reward (descriptive).

    Reads ONLY the frozen results/evaluation/exp007_analysis.json; every
    number drawn is that artifact rounded and nothing else. The hypothesis
    status, the Q0 confound, the seed limitation and the TRAIN-only scope
    are printed on the figure itself, so it cannot be read as an
    inferential, causal or TEST result when separated from the report.

    Frozen values drawn (run mean of T_ref-normalized episode reward):
    A1-s0 0.7407, A1-s1 0.6275, A2-s0 0.7622, A2-s1 0.6724,
    FULL-s0 0.7365, FULL-s1 0.6681, FULL-s2 0.7716.
    """
    d = json.loads(EXP007.read_text(encoding="utf-8"))
    runs = d["run_results"]            # dict keyed by label (A1-s0 ... A2-s1)
    ref = d["full_state_reference"]["runs"]
    cov = d["state_coverage"]
    groups = (
        ("A1: context only (state-v1)", "#1f4e79",
         [(k, runs[k]) for k in ("A1-s0", "A1-s1")], "A1"),
        ("A2: feedback only (state-v2)", "#148f77",
         [(k, runs[k]) for k in ("A2-s0", "A2-s1")], "A2"),
        ("full state reference (state-v1.5)", "#7f8c8d",
         [(r["label"], r) for r in ref], "full_state"),
    )
    W, H, L, T, PH = 980, 620, 110, 104, 296
    bottom = T + PH
    vmax = 1.0
    # Horizontal layout (left of the dashed divider; verified against the
    # frozen artifact): 2 A1 bars + 2 A2 bars; the 3 full-state reference
    # bars sit right of the divider. bw/gap sizes keep all 7 bars in-bounds.
    bw, gap_in, gap_ab, gap_div = 62, 30, 70, 100

    def py(v: float) -> float:
        return T + PH * (1.0 - v / vmax)

    o = _open(W, H,
              "EXP-007 state ablation: per-run TRAIN episode reward "
              "(DESCRIPTIVE - no inferential test)",
              "Bar = run mean of T_ref-normalized episode reward "
              "(dimensionless); whisker = +/- 1 sample SD (ddof=1) = "
              "descriptive spread, NOT a CI.\n"
              "TRAIN episodes only: 0 TEST executions. Hypothesis "
              "'context+feedback > context-only' = OBSERVED PATTERN, NOT "
              "ESTABLISHED (DAY36 s11).\n"
              "Q0 CONFOUND (DAY36 s9): A1/A2 neutral q0 0.5 vs reference "
              "EXP-002-derived Q0 + longer horizons - NOT a pure state "
              "effect.\n"
              "2 seeds per ablation (main study: 3; DAY36 s10). No causal "
              "claim, no best-variant ranking, no TEST claim (DAY36 s12).",
              L)
    v = 0.0
    while v <= vmax + 1e-9:
        y = py(v)
        o.append('<line x1="%d" y1="%s" x2="%d" y2="%s" stroke="#eeeeee"/>'
                 % (L, _f(y), W - 30, _f(y)))
        o.append('<text x="%d" y="%s" font-size="11" fill="#444" '
                 'text-anchor="end">%.1f</text>' % (L - 8, _f(y + 4), v))
        v = round(v + 0.2, 10)
    o.append('<text x="20" y="%d" font-size="12" fill="#222" '
             'text-anchor="middle" transform="rotate(-90 20 %d)">mean '
             'episode reward (T_ref-normalized, dimensionless)</text>'
             % (T + PH // 2, T + PH // 2))


    x = L + 60
    divider_x = None
    for gi, (gname, gcol, members, cov_key) in enumerate(groups):
        g0 = x
        for label, r in members:
            mean = float(r["mean_reward"])
            sd = float(r["reward_stdev_sample"])
            eps = int(r["episodes_completed"])
            cx = x + bw / 2.0
            bh = PH * mean / vmax
            o.append('<rect x="%s" y="%s" width="%s" height="%s" '
                     'fill="%s" opacity="0.88"/>'
                     % (_f(x), _f(py(mean)), _f(bw), _f(bh), gcol))
            # value sits above the whisker top so label and bar never overlap
            yhi = py(min(mean + sd, vmax))
            ylo = py(max(mean - sd, 0.0))
            o.append('<text x="%s" y="%s" font-size="11" fill="#111" '
                     'text-anchor="middle">%.4f</text>'
                     % (_f(cx), _f(yhi - 8), mean))
            # whisker: +/- 1 sample SD (ddof=1), descriptive spread only
            o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#333" '
                     'stroke-width="1.4"/>'
                     % (_f(cx), _f(yhi), _f(cx), _f(ylo)))
            for ycap in (yhi, ylo):
                o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" '
                         'stroke="#333" stroke-width="1.4"/>'
                         % (_f(cx - 8), _f(ycap), _f(cx + 8), _f(ycap)))
            o.append('<text x="%s" y="%d" font-size="10" fill="#222" '
                     'text-anchor="middle">%s</text>'
                     % (_f(cx), bottom + 16, label))
            o.append('<text x="%s" y="%d" font-size="9" fill="#666" '
                     'text-anchor="middle">%d eps | sd %.4f</text>'
                     % (_f(cx), bottom + 28, eps, sd))
            if r.get("early_stop_triggered"):
                o.append('<text x="%s" y="%d" font-size="9" fill="#a06000" '
                         'text-anchor="middle">&#8224; early stop</text>'
                         % (_f(cx), bottom + 38))
            x += bw + gap_in
        g1 = x - gap_in
        c = (g0 + g1) / 2.0
        cinfo = cov[cov_key]
        if cov_key == "full_state":
            n_exec = sum(int(r.get("live_executions", 0)) for r in ref)
            tail = "%d/%d states observed | %d exec | 3 seeds (main study)" % (
                cinfo["n_observed_union"], cinfo["possible"], n_exec)
        else:
            vs = d["variant_summaries"][cov_key]
            tail = ("%d/%d states observed | %d exec | "
                    "mean of run-means %.4f" % (
                        cinfo["n_observed_union"], cinfo["possible"],
                        int(vs["total_executions"]),
                        float(vs["mean_of_run_means"])))
        o.append('<text x="%s" y="%d" font-size="11" font-weight="bold" '
                 'fill="#111" text-anchor="middle">%s</text>'
                 % (_f(c), bottom + 58, gname))
        o.append('<text x="%s" y="%d" font-size="9" fill="#666" '
                 'text-anchor="middle">%s</text>' % (_f(c), bottom + 70, tail))
        x += gap_ab if gi == 0 else gap_div
        if gi == 1:
            divider_x = x - gap_div / 2.0
    base = bottom + 88
    if divider_x is not None:
        o.append('<line x1="%s" y1="%d" x2="%s" y2="%d" stroke="#999" '
                 'stroke-dasharray="5,4"/>' % (_f(divider_x), T, _f(divider_x),
                                              base))
    o.append('<text x="%d" y="%d" font-size="9" fill="#666">dashed line '
             'separates frozen ablations (left) from the full-state reference '
             '(right); A1/A2 vs reference is NOT a pure state effect '
             '(Q0 + horizon differ).</text>' % (L, base + 28))
    o.append('<text x="%d" y="%d" font-size="9" fill="#888">'
             'source: results/evaluation/exp007_analysis.json | frozen '
             'analysis SHA256 e010072f..0043b68 | 0 Spark, '
             '0 SC6</text>' % (L, base + 42))
    o.append("</svg>")
    p = FIGDIR / "exp007_ablation.svg"
    p.write_text("\n".join(o), encoding="utf-8")
    return p


def main() -> int:
    FIGDIR.mkdir(parents=True, exist_ok=True)
    for fn in (fig_exp002_sensitivity, fig_exp005_arms, fig_exp007_ablation):
        print("wrote %s" % fn().relative_to(PROJECT))
    print("0 Spark executions, 0 charged to SC6, no result artifact written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
