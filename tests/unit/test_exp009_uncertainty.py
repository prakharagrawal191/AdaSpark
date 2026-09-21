"""EXP-009 uncertainty layer: the gate is adjudicated by INTERVAL, not point.

The defect these tests pin: a point estimate compared against SC6 clause 2's
5% gate asserts a precision the n=5 design does not have. Run-to-run CV of
execution_time_s on this stack is 2.6-13.6%, so the sampling error of a
difference of medians is the same order as the gate. A verdict may therefore
be returned ONLY when the whole interval lies on one side of it.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PROJECT = Path(__file__).resolve().parents[2]


def _mod():
    spec = importlib.util.spec_from_file_location(
        "analyze_exp009", PROJECT / "scripts" / "analyze_exp009.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_straddling_interval_is_inconclusive_in_both_directions():
    """The core rule. Neither a softened FAIL nor a rescued PASS."""
    m = _mod()
    assert m.adjudicate(6.7, (-6.4, 14.8), 5.0) == "INCONCLUSIVE"
    assert m.adjudicate(1.2, (-11.2, 16.6), 5.0) == "INCONCLUSIVE"
    # straddles 5 from below -> still undecided, even though the point passes
    assert m.adjudicate(2.0, (-1.0, 9.0), 5.0) == "INCONCLUSIVE"


def test_verdict_returned_only_when_interval_clears_the_gate():
    m = _mod()
    assert m.adjudicate(1.0, (0.2, 3.9), 5.0) == "PASS"      # wholly below
    assert m.adjudicate(9.0, (6.1, 12.0), 5.0) == "FAIL"     # wholly above
    assert m.adjudicate(5.0, (1.0, 5.0), 5.0) == "PASS"      # hi == gate
    assert m.adjudicate(None, None, 5.0) == "INCONCLUSIVE"   # missing data


def test_bootstrap_is_deterministic():
    """Seeded: the analyzer must reproduce byte-identically (Day-28/29 norm)."""
    m = _mod()
    a = [10.0, 10.5, 9.8, 10.2, 10.1]
    b = [9.9, 10.1, 9.7, 10.0, 9.95]
    assert m.bootstrap_ci(a, b) == m.bootstrap_ci(a, b)


def test_bootstrap_widens_with_noise_and_needs_more_reps():
    """A noisier cell must produce a wider interval and demand more reps."""
    m = _mod()
    tight_a = [10.0, 10.1, 10.0, 10.05, 10.0]
    tight_b = [9.9, 9.95, 9.9, 9.92, 9.9]
    noisy_a = [10.0, 13.0, 7.5, 11.5, 8.0]
    noisy_b = [9.9, 12.0, 7.0, 11.0, 8.5]
    t_lo, t_hi = m.bootstrap_ci(tight_a, tight_b)
    n_lo, n_hi = m.bootstrap_ci(noisy_a, noisy_b)
    assert (n_hi - n_lo) > (t_hi - t_lo)
    assert m.required_n(noisy_a, noisy_b, 5.0) > m.required_n(tight_a, tight_b, 5.0)


def test_too_few_samples_yields_no_interval_not_a_fake_one():
    m = _mod()
    assert m.bootstrap_ci([1.0], [1.0]) is None
    assert m.bootstrap_ci([], []) is None
    # a zero baseline must not divide
    assert m.bootstrap_ci([1.0, 2.0], [0.0, 0.0]) is None


def test_live_artifact_reports_intervals_and_an_honest_verdict():
    """The committed artifact must carry intervals and must not claim a
    verdict the intervals cannot support."""
    import json
    art = PROJECT / "results" / "evaluation" / "exp009_analysis.json"
    if not art.exists():
        pytest.skip("EXP-009 analysis artifact not present")
    d = json.loads(art.read_text(encoding="utf-8"))
    assert d["uncertainty"]["interval"].startswith("95% percentile bootstrap")
    for c in d["cells"]:
        assert c["sysmon_ci95_pct"] is not None
        lo, hi = c["sysmon_ci95_pct"]
        assert lo <= c["overhead_sysmon_pct"] <= hi
        # no cell may claim PASS/FAIL while its interval straddles the gate
        if lo < d["threshold_pct"] < hi:
            assert c["sysmon_verdict"] == "INCONCLUSIVE"
