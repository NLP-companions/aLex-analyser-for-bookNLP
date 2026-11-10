"""Statistics, checked against SciPy where an independent reference exists."""
from __future__ import annotations

import math
import statistics as st

import pytest
from scipy import special
from scipy import stats as sp

from alex.core import stats


@pytest.mark.parametrize("x", [0.0, 0.5, 1.0, 3.84, 10.0, 27.0, 200.0])
def test_p_chi1_matches_scipy(x):
    assert stats.p_chi1(x) == pytest.approx(sp.chi2.sf(x, 1), rel=1e-9, abs=1e-15)


@pytest.mark.parametrize("df", [1, 2, 3, 7, 30])
@pytest.mark.parametrize("x", [0.1, 1.0, 5.0, 12.0, 40.0, 150.0])
def test_p_chi_matches_scipy(x, df):
    assert stats.p_chi(x, df) == pytest.approx(sp.chi2.sf(x, df), rel=1e-6, abs=1e-14)


def test_p_chi_edge_cases():
    assert stats.p_chi(0, 3) == 1.0 and stats.p_chi(5, 0) == 1.0 and stats.p_chi1(-1) == 1.0


def test_compare_log_likelihood_matches_scipy():
    a, b, c, d = 30, 10, 1000, 2000
    r = stats.compare(a, b, c, d)
    expected, _, _, _ = sp.chi2_contingency([[a, c - a], [b, d - b]], correction=False)
    assert r["chi2"] == pytest.approx(expected, rel=1e-9)
    # G² as corpus linguists use it (Rayson & Garside 2000): the item's two cells only, not the four of a full G-test
    e1, e2 = c * (a + b) / (c + d), d * (a + b) / (c + d)
    g = 2 * (a * math.log(a / e1) + b * math.log(b / e2))
    assert r["ll"] == pytest.approx(g, rel=1e-12)
    assert r["p_ll"] == pytest.approx(sp.chi2.sf(g, 1), rel=1e-6)


def test_compare_signs_and_effect_sizes():
    up, down = stats.compare(30, 10, 1000, 1000), stats.compare(10, 30, 1000, 1000)
    assert up["ll"] > 0 > down["ll"] and up["chi2"] > 0 > down["chi2"]
    assert up["ll"] == pytest.approx(-down["ll"])
    assert up["lr"] == pytest.approx(math.log2(3)) and up["or"] > 1 > down["or"]
    assert up["or_lo"] < up["or"] < up["or_hi"]
    assert up["pdiff"] == pytest.approx(200.0)


def test_compare_with_zero_counts_uses_half_counts_and_does_not_fail():
    r = stats.compare(5, 0, 100, 100)
    assert math.isfinite(r["lr"]) and math.isfinite(r["or"]) and r["ll"] > 0
    empty = stats.compare(1, 1, 0, 10)
    assert empty["ll"] == 0 and empty["p_ll"] == 1


def test_across_matches_scipy_chi2():
    counts, totals = [20, 5, 8], [1000, 900, 1200]
    r = stats.across(counts, totals)
    table = [counts, [t - c for c, t in zip(counts, totals)]]
    chi2, p, df, _ = sp.chi2_contingency(table, correction=False)
    assert r["chi2"] == pytest.approx(chi2, rel=1e-9) and r["df"] == df and r["p"] == pytest.approx(p, rel=1e-6)
    assert r["v"] == pytest.approx(math.sqrt(chi2 / sum(totals)))
    assert r["resid"][0] > 1.96 > r["resid"][1]


def test_across_degenerate_inputs():
    assert stats.across([0, 0], [10, 10])["chi2"] == 0
    assert stats.across([5], [10])["df"] == 0
    r = stats.across([3, 0], [10, 0])
    assert r["resid"][1] is None or r["df"] == 0


def test_trend_is_the_cochran_armitage_test():
    """z² equals N·r², r being the correlation between the position and the 0/1 outcome of every single word (an identity of the test)."""
    counts, totals = [2, 5, 4, 9, 14], [100, 120, 90, 110, 100]
    r = stats.trend(counts, totals)
    pos, hit = [], []
    for i, (c, t) in enumerate(zip(counts, totals)):
        pos += [i] * t
        hit += [1] * c + [0] * (t - c)
    rho = sp.pearsonr(pos, hit)[0]
    N = sum(totals)
    assert r["z"] ** 2 == pytest.approx(N * rho ** 2, rel=1e-9) and r["z"] > 0 and r["n"] == 5
    assert r["p"] == pytest.approx(sp.chi2.sf(r["z"] ** 2, 1), rel=1e-9)
    assert stats.trend(counts[::-1], totals[::-1])["z"] < 0                       # the same shares the other way round


def test_trend_leaves_empty_parts_out_and_degenerate_inputs_alone():
    a = stats.trend([2, 0, 6, 9], [50, 0, 50, 50])
    assert a["n"] == 3 and a["z"] > 0
    assert stats.trend([0, 0, 0], [10, 10, 10]) == {"z": None, "p": None, "n": 3}     # never there
    assert stats.trend([10, 10], [10, 10])["z"] is None                               # always there
    assert stats.trend([3, 0], [10, 0])["z"] is None and stats.trend([3], [10])["n"] == 1


def test_trends_of_several_texts_are_combined_with_equal_weight():
    """Stouffer: the z values add up over √(texts); a text without a z is left out; opposite trends cancel."""
    a, b = stats.trend([2, 5, 4, 9, 14], [100] * 5), stats.trend([1, 3, 6, 6, 12], [80] * 5)
    c = stats.combine_trends([a, b, stats.trend([0, 0, 0], [10] * 3)])
    assert c["z"] == pytest.approx((a["z"] + b["z"]) / 2 ** 0.5) and c["n"] == 2 and (c["up"], c["down"]) == (2, 0)
    assert c["p"] == pytest.approx(sp.chi2.sf(c["z"] ** 2, 1), rel=1e-9) and c["z"] > max(a["z"], b["z"]) / 2 ** 0.5     # two like-minded texts are surer
    flat = stats.combine_trends([a, stats.trend([14, 9, 4, 5, 2], [100] * 5)])
    assert flat["z"] == pytest.approx(0) and flat["p"] == pytest.approx(1) and (flat["up"], flat["down"]) == (1, 1)
    assert stats.combine_trends([]) == {"z": None, "p": None, "n": 0, "up": 0, "down": 0}
    assert stats.combine_trends([a])["z"] == a["z"] and stats.combine_trends([a])["p"] == pytest.approx(a["p"])


def test_chi_squared_of_several_texts_adds_up():
    a, b = stats.across([2, 5, 9], [50, 50, 50]), stats.across([8, 3, 1], [40, 40, 40])
    c = stats.combine_across([a, b])
    assert c["chi2"] == pytest.approx(a["chi2"] + b["chi2"]) and c["df"] == 4
    assert c["p"] == pytest.approx(sp.chi2.sf(c["chi2"], 4), rel=1e-9)
    assert stats.combine_across([]) == {"chi2": 0, "df": 0, "p": 1.0}


def test_keyness_ranks_and_filters():
    target = {"moor": 40, "the": 100, "rare": 1}
    reference = {"moor": 2, "the": 105, "goose": 30}
    rows, summary = stats.keyness(target, reference, min_freq=3)
    assert [r["item"] for r in rows] == ["moor"] and summary["tested"] == 2
    both, _ = stats.keyness(target, reference, min_freq=3, direction="both")
    assert {r["item"] for r in both} == {"moor", "goose"}
    # "the" is a little *less* frequent in the target, so it only appears with both directions and non-significant items shown
    everything, _ = stats.keyness(target, reference, min_freq=3, direction="both", show_all=True)
    assert "the" not in {r["item"] for r in both} and "the" in {r["item"] for r in everything}


def test_keyness_bonferroni_tightens_the_threshold():
    target = {f"w{i}": 12 for i in range(50)}
    reference = {f"w{i}": 6 for i in range(50)}
    loose, s1 = stats.keyness(target, reference, alpha=0.05)
    strict, s2 = stats.keyness(target, reference, alpha=0.05, bonferroni=True)
    assert s2["threshold"] == pytest.approx(0.05 / 50) and len(strict) <= len(loose)


# ---------- correlations and descriptives ----------
@pytest.mark.parametrize("df", [1, 2, 5, 13, 100, 5000])
@pytest.mark.parametrize("t", [0.0, 0.3, 1.0, 2.0, 4.5, 12.0, -2.5])
def test_p_t_matches_scipy(t, df):
    assert stats.p_t(t, df) == pytest.approx(2 * sp.t.sf(abs(t), df), rel=1e-8, abs=1e-15)


@pytest.mark.parametrize("df", [1, 4, 9, 30, 400])
def test_t_crit_matches_scipy(df):
    assert stats.t_crit(df) == pytest.approx(sp.t.ppf(0.975, df), rel=1e-9)


@pytest.mark.parametrize("a,b,x", [(0.5, 0.5, 0.2), (2, 3, 0.4), (10, 0.5, 0.95), (50, 50, 0.5), (1, 1, 0.0), (3, 2, 1.0)])
def test_betai_matches_scipy(a, b, x):
    assert stats.betai(a, b, x) == pytest.approx(special.betainc(a, b, x), rel=1e-9, abs=1e-15)


def test_ranks_average_ties():
    assert stats.ranks([10, 30, 20, 30, 5]) == [2, 4.5, 3, 4.5, 1]
    assert list(stats.ranks([1, 2, 2, 3])) == list(sp.rankdata([1, 2, 2, 3]))


X = [1.0, 2.5, 3.1, 4.8, 5.0, 7.2, 7.2, 9.9, 0.4, 6.6]
Y = [2.1, 2.0, 4.4, 4.1, 6.3, 6.0, 8.8, 9.0, 1.5, 3.3]


def test_pearson_matches_scipy():
    r = stats.correlate(X, Y, "pearson")
    ref = sp.pearsonr(X, Y)
    assert r["n"] == 10 and r["r"] == pytest.approx(ref[0], rel=1e-12) and r["p"] == pytest.approx(ref[1], rel=1e-8)
    ci = ref.confidence_interval(0.95)                                          # Fisher's z, as here
    assert (r["lo"], r["hi"]) == pytest.approx((ci.low, ci.high), rel=1e-9)


def test_spearman_matches_scipy_with_ties():
    r = stats.correlate(X, Y, "spearman")
    ref = sp.spearmanr(X, Y)
    assert r["r"] == pytest.approx(ref[0], rel=1e-12) and r["p"] == pytest.approx(ref[1], rel=1e-8)
    assert r["lo"] < r["r"] < r["hi"]
    # ρ's interval is a little wider than r's would be for the same value (√1.06)
    assert r["hi"] - r["lo"] > math.tanh(math.atanh(r["r"]) + 1.96 / math.sqrt(7)) - math.tanh(math.atanh(r["r"]) - 1.96 / math.sqrt(7))


def test_a_0_1_variable_gives_the_point_biserial_r():
    group = [0, 0, 0, 1, 1, 1, 1, 0, 1, 0]
    assert stats.correlate(group, Y)["r"] == pytest.approx(sp.pointbiserialr(group, Y)[0], rel=1e-12)


def test_correlate_drops_missing_cases_pairwise():
    x, y = X + [None, 3.0], Y + [1.0, None]
    r = stats.correlate(x, y)
    assert r["n"] == 10 and r["r"] == pytest.approx(stats.correlate(X, Y)["r"])


def test_correlate_degenerate_inputs():
    assert stats.correlate([1, 2], [3, 4])["r"] is None                         # fewer than 3 cases
    flat = stats.correlate([1, 1, 1, 1], [1, 2, 3, 4])
    assert flat["r"] is None and flat["p"] is None and flat["n"] == 4         # a constant doesn't correlate
    three = stats.correlate([1, 2, 3], [2, 1, 3])
    assert three["r"] is not None and three["lo"] is None                     # no interval with 3 cases
    perfect = stats.correlate([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
    assert perfect["r"] == pytest.approx(1) and perfect["p"] == 0 and perfect["lo"] == perfect["hi"] == perfect["r"]


def test_adjust_bonferroni_and_holm():
    ps = [0.01, 0.04, None, 0.03, 0.5]
    assert stats.adjust(ps, "none") == ps
    bonf = stats.adjust(ps, "bonferroni")                                        # 4 tests: the None isn't one
    assert bonf[2] is None and [bonf[i] for i in (0, 1, 3, 4)] == pytest.approx([0.04, 0.16, 0.12, 1.0])
    holm = stats.adjust(ps, "holm")
    # sorted 0.01, 0.03, 0.04, 0.5 times 4, 3, 2, 1 = 0.04, 0.09, 0.08 -> 0.09 (kept in order), 0.5
    assert holm[2] is None and [holm[i] for i in (0, 3, 1, 4)] == pytest.approx([0.04, 0.09, 0.09, 0.5])


def test_stars():
    assert [stats.stars(p) for p in (0.0005, 0.005, 0.03, 0.05, None)] == ["***", "**", "*", "", ""]


def test_describe_matches_the_standard_library_and_scipy():
    d = stats.describe(X + [None])
    assert d["n"] == 10 and d["mean"] == pytest.approx(st.mean(X)) and d["median"] == pytest.approx(st.median(X))
    assert d["sd"] == pytest.approx(st.stdev(X)) and d["var"] == pytest.approx(st.variance(X))
    assert (d["min"], d["max"]) == (min(X), max(X)) and d["se"] == pytest.approx(sp.sem(X))
    lo, hi = sp.t.interval(0.95, 9, loc=st.mean(X), scale=sp.sem(X))
    assert (d["lo"], d["hi"]) == pytest.approx((lo, hi), rel=1e-9)


def test_describe_small_samples():
    assert stats.describe([])["mean"] is None and stats.describe([None])["n"] == 0
    one = stats.describe([4])
    assert one["mean"] == one["median"] == 4 and one["sd"] is None and one["lo"] is None
    assert stats.describe([1, 2, 3, 10])["median"] == 2.5


@pytest.mark.parametrize("method", ["pearson", "spearman"])
def test_correlating_prepared_variables_gives_the_same_figures(method):
    fast = stats.correlate_centred(stats.centred(X, method), stats.centred(Y, method), method)
    slow = stats.correlate(X, Y, method)
    assert fast.keys() == slow.keys() and all(fast[k] == pytest.approx(slow[k], rel=1e-12) for k in ("r", "p", "lo", "hi")) and fast["n"] == 10


def test_only_complete_variables_are_prepared():
    assert stats.centred(X + [None]) is None and stats.centred([1, 2]) is None
    flat = stats.correlate_centred(stats.centred([1, 1, 1, 1]), stats.centred([1, 2, 3, 4]))
    assert flat["r"] is None and flat["p"] is None and flat["n"] == 4


def test_keywords_that_tie_come_out_in_alphabetical_order():
    """Items with the same count and the same figures were ordered by the arrival order of a set of strings, which differs between runs."""
    from collections import Counter
    rows, _ = stats.keyness(Counter({"pear": 9, "apple": 9, "fig": 9, "kiwi": 9}), Counter({"other": 90}), min_freq=1)
    assert [r["item"] for r in rows] == ["apple", "fig", "kiwi", "pear"]
