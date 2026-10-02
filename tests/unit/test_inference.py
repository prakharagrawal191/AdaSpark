"""Exact inference (PLAN section 22 family): hand-checkable known values."""
from __future__ import annotations

import math

import pytest

from sparkrl.analysis.inference import (average_ranks, cliffs_delta,
                                        geometric_mean_ratio, holm,
                                        mann_whitney, wilcoxon_signed_rank)

pytestmark = [pytest.mark.unit]


def test_average_ranks_share_ties():
    assert average_ranks([10, 20, 20, 30]) == [1.0, 2.5, 2.5, 4.0]


def test_wilcoxon_all_one_sign_is_one_over_two_to_the_n():
    up = wilcoxon_signed_rank([1, 2, 3, 4, 5, 6], "greater")
    assert up["p"] == pytest.approx(1 / 64)
    assert wilcoxon_signed_rank([-1, -2, -3, -4, -5, -6], "less")["p"] == pytest.approx(1 / 64)
    assert wilcoxon_signed_rank([1, 2, 3, 4, 5, 6], "two-sided")["p"] == pytest.approx(2 / 64)
    assert wilcoxon_signed_rank([1, 2, 3, 4, 5, 6], "less")["p"] == pytest.approx(1.0)


def test_wilcoxon_small_case_enumerated_by_hand():
    # |d| ranks 1,2,3; W+ = 1 + 3 = 4; subset sums of {1,2,3}: 0,1,2,3,3,4,5,6
    r = wilcoxon_signed_rank([1, -2, 3], "greater")
    assert r["w_plus"] == 4 and r["p"] == pytest.approx(3 / 8)
    assert wilcoxon_signed_rank([1, -2, 3], "less")["p"] == pytest.approx(6 / 8)


def test_wilcoxon_ties_and_zeros_stay_exact():
    # three tied |d| -> ranks 2,2,2; W+ = 4 -> P(W+ >= 4) = 4/8
    assert wilcoxon_signed_rank([1, 1, -1], "greater")["p"] == pytest.approx(0.5)
    z = wilcoxon_signed_rank([0, 1, 2], "greater")
    assert z["n"] == 2 and z["zeros_dropped"] == 1 and z["p"] == pytest.approx(0.25)
    assert wilcoxon_signed_rank([0, 0], "less")["p"] == 1.0


def test_mann_whitney_complete_separation_5_vs_5():
    r = mann_whitney([1, 2, 3, 4, 5], [6, 7, 8, 9, 10], "less")
    assert r["u_x"] == 0 and r["p"] == pytest.approx(1 / math.comb(10, 5))
    assert mann_whitney([1, 2, 3, 4, 5], [6, 7, 8, 9, 10], "greater")["p"] == pytest.approx(1.0)
    assert mann_whitney([1, 2, 3, 4, 5], [6, 7, 8, 9, 10], "two-sided")["p"] == pytest.approx(2 / 252)


def test_mann_whitney_all_tied_is_uninformative():
    assert mann_whitney([1, 1], [1, 1], "less")["p"] == pytest.approx(1.0)


def test_mann_whitney_refuses_to_approximate():
    with pytest.raises(ValueError):
        mann_whitney(list(range(20)), list(range(20)))


def test_cliffs_delta_sign_convention():
    assert cliffs_delta([1, 2], [3, 4]) == -1.0
    assert cliffs_delta([3, 4], [1, 2]) == 1.0
    assert cliffs_delta([1, 3], [2, 2]) == 0.0


def test_holm_is_monotone_and_capped():
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert holm([0.5, 0.5]) == [1.0, 1.0]


def test_geometric_mean_ratio_constant_ratio_has_degenerate_ci():
    r = geometric_mean_ratio([math.log(2)] * 6)
    assert r["gmr"] == pytest.approx(2.0)
    assert r["ci95"][0] == pytest.approx(2.0) and r["ci95"][1] == pytest.approx(2.0)


def test_geometric_mean_ratio_is_seed_reproducible():
    vals = [math.log(v) for v in (0.5, 0.9, 1.1, 0.7, 1.3, 0.8)]
    assert geometric_mean_ratio(vals) == geometric_mean_ratio(vals)
