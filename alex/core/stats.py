"""Statistics without SciPy: comparisons of frequencies, as used in corpus linguistics, and correlations and descriptives
(the Statistics tab).

Comparisons (`compare`, `keyness`) work on a 2x2 table:
a = item count in the target, c = all items in the target
b = item count in the reference, d = all items in the reference

Correlations (`correlate`: Pearson's r, Spearman's ρ) and descriptives (`describe`) take lists of numbers, one per case,
with None for a missing value; `adjust` corrects a list of p-values for multiple testing.
"""
import math
import operator

MEASURES = {
    "ll": "Log-likelihood (G²)",
    "chi2": "Chi-squared",
    "lr": "Log ratio",
    "pdiff": "%DIFF",
    "or": "Odds ratio",
}
TESTS = {"ll": "Log-likelihood (G²)", "chi2": "Chi-squared"}

NOTES = {
    "ll": "G² = 2 Σ O ln(O/E) over the target and reference cells, with expected E from the combined proportion (Rayson & Garside 2000). Signed + when the item is relatively more frequent in the target. p from χ² with 1 degree of freedom.",
    "chi2": "Pearson's χ² for the 2×2 table (item vs other items, target vs reference), without Yates' correction. Signed like G². p from χ² with 1 degree of freedom.",
    "lr": "Log ratio = log₂ of (relative frequency in target ÷ relative frequency in reference) (Hardie 2014). 1 means twice as frequent, −1 half as frequent. Zero counts are replaced by 0.5.",
    "pdiff": "%DIFF = (relative frequency in target − in reference) ÷ in reference × 100 (Gabrielatos & Marchi 2012). Zero counts are replaced by 0.5.",
    "or": "Odds ratio = (a ÷ (c − a)) ÷ (b ÷ (d − b)), with a 95% confidence interval from the log odds ratio's standard error. When any cell is zero, 0.5 is added to every cell (Haldane–Anscombe).",
}


def p_chi1(x):
    """Upper-tail p-value of the chi-squared distribution with 1 degree of freedom."""
    if x <= 0:
        return 1.0
    return math.erfc(math.sqrt(x / 2))


def _gammq(a, x):
    """Regularised upper incomplete gamma Q(a, x) (Numerical Recipes)."""
    if x <= 0:
        return 1.0
    if x < a + 1:
        ap, total, delta = a, 1 / a, 1 / a
        for _ in range(1000):
            ap += 1
            delta *= x / ap
            total += delta
            if abs(delta) < abs(total) * 1e-12:
                break
        return max(0.0, 1 - total * math.exp(-x + a * math.log(x) - math.lgamma(a)))
    b, c, d = x + 1 - a, 1 / 1e-300, 1 / (x + 1 - a)
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = 1e-300 if abs(d) < 1e-300 else d
        c = b + an / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-12:
            break
    return min(1.0, math.exp(-x + a * math.log(x) - math.lgamma(a)) * h)


def p_chi(x, df):
    """Upper-tail p-value of chi-squared with df degrees of freedom."""
    return _gammq(df / 2, x / 2) if df > 0 else 1.0


def across(counts, totals):
    """How one item is spread over several parts (books), against how big each part is.
    counts, totals: lists, one per part. Returns chi-squared (item vs rest x parts),
    its p, Cramér's V and each part's adjusted standardised residual."""
    A, N = sum(counts), sum(totals)
    k = sum(1 for t in totals if t > 0)
    if A == 0 or N == 0 or k < 2 or A == N:
        return {"chi2": 0.0, "df": max(0, k - 1), "p": 1.0, "v": 0.0, "resid": [0.0] * len(counts)}
    chi2, resid = 0.0, []
    for o, t in zip(counts, totals):
        if t == 0:
            resid.append(None)
            continue
        e1, e2 = t * A / N, t * (N - A) / N
        chi2 += (o - e1) ** 2 / e1 + ((t - o) - e2) ** 2 / e2
        var = e1 * (1 - t / N) * (1 - A / N)
        resid.append((o - e1) / math.sqrt(var) if var > 0 else 0.0)
    return {"chi2": chi2, "df": k - 1, "p": p_chi(chi2, k - 1), "v": math.sqrt(chi2 / N), "resid": resid}


def trend(counts, totals):
    """Whether an item's share rises or falls over ordered parts (slices of a book): the Cochran–Armitage test for trend in proportions,
    with the parts' positions 0, 1, 2… as scores. counts, totals: lists, one per part, as for `across`; parts with a total of 0 are left
    out (their position still counts). Returns {z, p, n}: z is positive when the share rises, p is two-tailed (z² against chi-squared
    with one degree of freedom, the 1-df part of the chi-squared `across` gives), n the parts used. z and p are None with fewer than
    two parts, or when the item is in none of them or in all of every part's list."""
    use = [(i, c, t) for i, (c, t) in enumerate(zip(counts, totals)) if t > 0]
    N, A = sum(t for _, _, t in use), sum(c for _, c, _ in use)
    if len(use) < 2 or A == 0 or A == N:
        return {"z": None, "p": None, "n": len(use)}
    q = A / N
    s1, s2 = sum(i * t for i, _, t in use), sum(i * i * t for i, _, t in use)
    var = q * (1 - q) * (s2 - s1 * s1 / N)
    if var <= 0:
        return {"z": None, "p": None, "n": len(use)}
    z = sum(i * (c - t * q) for i, c, t in use) / math.sqrt(var)
    return {"z": z, "p": p_chi1(z * z), "n": len(use)}


def combine_trends(trends):
    """The `trend`s of one item in several independent texts (books) as one, every text weighing the same: Stouffer's method, the sum of the
    z values divided by √(texts). Texts whose z is None (item absent or constant there) are left out.
    Returns {z, p, n, up, down}: p is two-tailed, n the texts used, up and down how many of them rise and fall; z and p are None with no text."""
    zs = [t["z"] for t in trends if t["z"] is not None]
    out = {"z": None, "p": None, "n": len(zs), "up": sum(z > 0 for z in zs), "down": sum(z < 0 for z in zs)}
    if zs:
        out["z"] = sum(zs) / math.sqrt(len(zs))
        out["p"] = p_chi1(out["z"] ** 2)
    return out


def combine_across(results):
    """The `across` results of one item in several independent texts as one: chi-squared and degrees of freedom add up. -> {chi2, df, p}
    (no texts: chi2 0, df 0, p 1). It asks whether the item's share varies between the parts of the texts, not whether they vary alike."""
    chi2, df = sum(r["chi2"] for r in results), sum(r["df"] for r in results)
    return {"chi2": chi2, "df": df, "p": p_chi(chi2, df)}


ACROSS_NOTE = ("For each item, a table of this item against all other items, by book, is tested with Pearson's χ² "
               "(degrees of freedom = books − 1). A small p means the item's share of the list changes between books "
               "more than chance would explain. Cramér's V (0–1) is the size of that change. In each book's column, the "
               "cell is shaded when its adjusted standardised residual is beyond ±1.96: blue when the item is more "
               "frequent in that book than expected from the other books, red when less. With a Bonferroni correction, "
               "the threshold for p is divided by the number of items tested.")


def compare(a, b, c, d):
    """Compare one item's frequency in two texts. a, b: its counts in the target and the reference; c, d: the sizes of each.
    Returns the log-likelihood (G², Rayson & Garside) and chi-squared (both signed + when relatively more frequent in the
    target) with their p-values, log ratio, %DIFF and odds ratio with a 95% interval. Zero counts are replaced by 0.5 where needed."""
    out = {"a": a, "b": b}
    if c <= 0 or d <= 0:
        return {**out, "ll": 0, "chi2": 0, "p_ll": 1, "p_chi2": 1, "lr": 0, "pdiff": 0, "or": 1, "or_lo": 1, "or_hi": 1}
    n = c + d
    e1, e2 = c * (a + b) / n, d * (a + b) / n
    ll = 2 * ((a * math.log(a / e1) if a else 0) + (b * math.log(b / e2) if b else 0))
    more = a / c > b / d
    k = a + b
    denom = k * (n - k) * c * d
    chi2 = n * (a * (d - b) - b * (c - a)) ** 2 / denom if denom else 0
    a5, b5 = (a or 0.5), (b or 0.5)
    lr = math.log2((a5 / c) / (b5 / d))
    pdiff = ((a5 / c) - (b5 / d)) / (b5 / d) * 100
    cells = [a, c - a, b, d - b]
    if min(cells) <= 0:
        cells = [x + 0.5 for x in cells]
    try:
        orr = (cells[0] / cells[1]) / (cells[2] / cells[3])
        se = math.sqrt(sum(1 / x for x in cells))
        lo, hi = math.exp(math.log(orr) - 1.96 * se), math.exp(math.log(orr) + 1.96 * se)
    except (ZeroDivisionError, ValueError):
        orr, lo, hi = 1, 1, 1
    sign = 1 if more else -1
    return {**out, "ll": sign * ll, "chi2": sign * chi2, "p_ll": p_chi1(ll), "p_chi2": p_chi1(chi2),
            "lr": lr, "pdiff": pdiff, "or": orr, "or_lo": lo, "or_hi": hi}


def passes(total, in_books, reached, min_freq, min_range, each_book):
    """Whether an item clears the minimum frequency and the minimum range. Over the books together (the default) it needs `total` occurrences
    in all and to occur in `in_books` >= `min_range` books. With `each_book` a book counts for an item only if the item reaches `min_freq`
    there, so it needs `reached` (the books where it does) >= `min_range`, and at least one."""
    if each_book:
        return reached >= max(1, min_range)
    return total >= min_freq and in_books >= min_range


def keyness(target, reference, measure="ll", test="ll", min_freq=3, alpha=0.05,
            bonferroni=False, direction="target", show_all=False):
    """target, reference: Counter of item -> count. Returns rows and a summary."""
    c, d = sum(target.values()), sum(reference.values())
    keys = sorted(set(target) | set(reference))                # in a fixed order, so that items that tie come out in the same order every time
    if direction == "target":
        keys = [k for k in keys if target.get(k, 0) >= min_freq]
    else:
        keys = [k for k in keys if max(target.get(k, 0), reference.get(k, 0)) >= min_freq]
    thresh = alpha / len(keys) if (bonferroni and keys) else alpha
    rows = []
    for k in keys:
        r = compare(target.get(k, 0), reference.get(k, 0), c, d)
        r["item"] = k
        r["pa"] = 100 * r["a"] / c if c else 0
        r["pb"] = 100 * r["b"] / d if d else 0
        r["p"] = r["p_" + test]
        r["sig"] = r["p"] < thresh
        up = r["lr"] > 0
        if direction == "target" and not up:
            continue
        if not show_all and not r["sig"]:
            continue
        rows.append(r)
    key = {"or": lambda r: math.log(r["or"]) if r["or"] > 0 else 0}.get(measure, lambda r: r[measure])
    if direction == "target":
        rows.sort(key=lambda r: (key(r), r["a"]), reverse=True)
    else:
        rows.sort(key=lambda r: (abs(key(r)), r["a"]), reverse=True)
    return rows, {"c": c, "d": d, "tested": len(keys), "alpha": alpha, "threshold": thresh,
                  "measure": measure, "test": test, "bonferroni": bonferroni, "min_freq": min_freq,
                  "direction": direction}


# ---------- correlations and descriptives (the Statistics tab) ----------
Z95 = 1.959963984540054                                    # the normal distribution's two-sided 95% point
CORRELATIONS = {"pearson": "Pearson's r", "spearman": "Spearman's ρ"}
CORRECTIONS = {"none": "None", "bonferroni": "Bonferroni", "holm": "Holm"}


def _betacf(a, b, x):
    """Continued fraction of the incomplete beta function (Numerical Recipes, `betacf`)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (tiny if abs(d) < tiny else d)
    h = d
    for m in range(1, 1000):
        m2 = 2 * m
        for aa in (m * (b - m) * x / ((qam + m2) * (a + m2)), -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))):
            d = 1 + aa * d
            d = 1 / (tiny if abs(d) < tiny else d)
            c = 1 + aa / c
            c = tiny if abs(c) < tiny else c
            h *= d * c
        if abs(d * c - 1) < 1e-14:
            break
    return h


def betai(a, b, x):
    """Regularised incomplete beta I_x(a, b) (Numerical Recipes, `betai`), for 0 <= x <= 1."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x) / a
    return 1 - front * _betacf(b, a, 1 - x) / b


def p_t(t, df):
    """Two-tailed p-value of Student's t with df degrees of freedom."""
    if df <= 0 or math.isnan(t):
        return 1.0
    if math.isinf(t):
        return 0.0
    return min(1.0, betai(df / 2, 0.5, df / (df + t * t)))


def t_crit(df, level=0.95):
    """The t value with a two-tailed p of 1 − level (2.262 for df 9 at 95%), found by halving the interval."""
    lo, hi = 0.0, 1.0
    while p_t(hi, df) > 1 - level:
        hi *= 2
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if p_t(mid, df) > 1 - level else (lo, mid)
        if hi - lo < 1e-12:
            break
    return (lo + hi) / 2


def ranks(values):
    """The rank of each value (1 = smallest), ties given the average of the ranks they span."""
    order = sorted(range(len(values)), key=values.__getitem__)
    out, i = [0.0] * len(values), 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return out


def _pearson_r(x, y):
    """Pearson's r of two equally long lists, or None when either doesn't vary."""
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx, syy = sum((a - mx) ** 2 for a in x), sum((b - my) ** 2 for b in y)
    if sxx <= 0 or syy <= 0:
        return None
    return max(-1.0, min(1.0, sxy / math.sqrt(sxx * syy)))


def _result(r, n, method):
    """The figures of a correlation r over n cases: {r, n, p, lo, hi}, as `correlate` describes them (r None: none at all)."""
    out = {"r": r, "n": n, "p": None, "lo": None, "hi": None}
    if r is None or n < 3:
        return {**out, "r": None}
    out["p"] = 0.0 if abs(r) >= 1 else p_t(r * math.sqrt((n - 2) / (1 - r * r)), n - 2)
    if n > 3:
        if abs(r) >= 1:
            out["lo"] = out["hi"] = r
        else:
            se = math.sqrt((1.06 if method == "spearman" else 1.0) / (n - 3))
            z = math.atanh(r)
            out["lo"], out["hi"] = math.tanh(z - Z95 * se), math.tanh(z + Z95 * se)
    return out


def centred(values, method="pearson"):
    """A variable made ready to be correlated quickly with others (`correlate_centred`): its values (for ρ, their ranks) minus their mean,
    and the square root of their sum of squares. None when it has a missing value or fewer than 3 cases (then use `correlate`). With
    thousands of cases (sentences) and hundreds of pairs this does the work per variable once instead of once per pair."""
    if len(values) < 3 or any(v is None for v in values):
        return None
    v = ranks(values) if method == "spearman" else values
    m = sum(v) / len(v)
    c = [x - m for x in v]
    return c, math.sqrt(sum(x * x for x in c))


def correlate_centred(a, b, method="pearson"):
    """`correlate` of two variables prepared by `centred` (no missing values, same cases): the same figures, from one sum of products."""
    (ca, sa), (cb, sb) = a, b
    r = None if sa <= 0 or sb <= 0 else max(-1.0, min(1.0, sum(map(operator.mul, ca, cb)) / (sa * sb)))
    return _result(r, len(ca), method)


def correlate(x, y, method="pearson"):
    """The correlation of two variables over the same cases: Pearson's r, or Spearman's ρ (Pearson's r of the ranks,
    ties averaged). A case missing either value (None) is left out (pairwise deletion).
    -> {r, n, p (two-tailed, from t with n − 2 degrees of freedom, as SciPy does for both), lo, hi (95% interval from
    Fisher's z, with standard error 1/√(n−3) for r and √(1.06/(n−3)) for ρ, Fieller, Hartley & Pearson 1957)}.
    r and p are None with fewer than 3 cases or when a variable doesn't vary; lo and hi need 4 cases."""
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    n = len(pairs)
    if n < 3:
        return _result(None, n, method)
    xs, ys = [a for a, _ in pairs], [b for _, b in pairs]
    if method == "spearman":
        xs, ys = ranks(xs), ranks(ys)
    return _result(_pearson_r(xs, ys), n, method)


def adjust(ps, method="none"):
    """p-values corrected for testing many at once: "bonferroni" multiplies each by the number of tests, "holm"
    (Holm 1979) multiplies the k-th smallest by (tests − k + 1) and keeps the order, both capped at 1; "none" leaves them.
    None (a test that couldn't be made) stays None and isn't counted."""
    done = [(i, p) for i, p in enumerate(ps) if p is not None]
    m, out = len(done), list(ps)
    if method == "bonferroni":
        for i, p in done:
            out[i] = min(1.0, p * m)
    elif method == "holm":
        running = 0.0
        for k, (i, p) in enumerate(sorted(done, key=lambda t: t[1])):
            running = max(running, min(1.0, p * (m - k)))
            out[i] = running
    return out


def stars(p):
    """"***" below .001, "**" below .01, "*" below .05, else "" (None too)."""
    if p is None:
        return ""
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""


def describe(values):
    """Descriptive statistics of one variable, missing values (None) left out: n, mean, sd and var (sample, n − 1),
    median, min, max, se (sd/√n) and the 95% interval of the mean (lo, hi, from t with n − 1 degrees of freedom).
    Figures that need more cases than there are (sd needs 2) are None."""
    v = sorted(x for x in values if x is not None)
    n = len(v)
    out = {"n": n, "mean": None, "sd": None, "var": None, "median": None, "min": None, "max": None, "se": None, "lo": None, "hi": None}
    if not n:
        return out
    mean = sum(v) / n
    out.update(mean=mean, min=v[0], max=v[-1], median=(v[(n - 1) // 2] + v[n // 2]) / 2)
    if n > 1:
        var = sum((x - mean) ** 2 for x in v) / (n - 1)
        se = math.sqrt(var / n)
        half = t_crit(n - 1) * se
        out.update(var=var, sd=math.sqrt(var), se=se, lo=mean - half, hi=mean + half)
    return out
