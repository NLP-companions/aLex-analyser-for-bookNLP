"""How an entity, group or other target changes over one book: the within-book counterpart of `View.by_book`.

The book is cut with the shared Measure over slicer (`narrative.book_segments`: equal slices by number or by words, or chapters with your
edits), and the target's mentions, findings (what it does, what is done to it, how it is described…) and kinds of action are counted
in each slice. A mention or finding belongs to the slice that holds the *first token of its mention*. Per slice we give

* an overview (words, mentions, mentions per 1,000 words, how the target is referred to, each relation per 100 mentions),
* the words of one relation: count and share of that slice's list for each word, with Pearson's chi-squared across the slices
  (`stats.across`, as for books) and a **trend**: the Cochran–Armitage test (`stats.trend`: z, positive when the share rises, and its p,
  from the counts and the slice sizes),
* the same for the kinds of action (WordNet supersenses of the verbs the target is the subject of).

With `sound` (the workspace's sound settings, `prosody.config`) the overview also has the sound and rhythm figures of the target's
speech in each slice (`_sound`: its quotes, each in the slice of its first token) as `snd`, and the curve offers them (`snd:<figure>`).

A slice where the list is empty has no share (None); the trend leaves those slices out. Two targets in one book are compared by calling `table`
twice (the second with the first's members as `exclude`) over the same slices (`report`); two targets in two books by `aligned`.

One target through *all* the selected books is `combined`: every book is cut into the same number of equal slices and, with every book
weighing the same, slice k of all of them is put together (counts added, shares and figures averaged, tests made per book and combined).
`table` is `_count` (the raw numbers of a book) and `_assemble` (the figures from them); `combined` counts each book and puts the counts together.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import Counter

from . import narrative, prosody, stats
from .bookdata import RELATIONS
from .dialogue import bdlg

NOTES = {      # explanations the Over the book page shows (sent to the browser with the library)
    "overview": "Each row is one slice of the book, cut as set above (the shared Measure over setting). A mention is counted in the slice that holds its first word. "
                "Mentions per 1,000 words divide by the words of the slice. Names, descriptions and pronouns are shares of the slice's mentions; each list "
                "is findings per 100 mentions in the slice. A slice without mentions has no shares (—).",
    "words": "Each cell is the word's share of all the words of this list in that slice (its count is in the tooltip), so a word can stay level while "
             "the character acts more. In the heat grid a cell is shaded by that share relative to the word's own highest one, which shows the shape of "
             "each word whatever its frequency; a hatched cell is a slice with nothing in this list, an empty one a slice where the word does not occur. "
             "χ² (Pearson, slices with findings − 1 degrees of freedom) asks whether the share differs between slices more than chance explains, and "
             "Cramér's V is the size of that difference. The trend (Cochran–Armitage test) asks the narrower question whether the share steadily "
             "rises or falls from the start of the book to its end: z is positive for a rise, and its p says how sure that is. It uses the counts and "
             "the sizes of the slices. Words below the minimum frequency are listed without tests. With many slices and few occurrences both tests are "
             "only a guide, so raise the minimum frequency before reading much into them. Click a cell for the sentences of that slice, a row for the "
             "sentences of the whole book.",
    "kinds": "A kind of action is the WordNet supersense of a verb the target is the subject of (cognition, communication, motion…). Each cell is the kind's "
             "share of all the target's actions that have a supersense in that slice; the heat grid, the tests and the sentences work as for words. "
             "The target's own verbs only: what is done to it is under Words.",
    "combined": "Every selected book that has the target is cut into the same number of equal slices, so slice k of n is the same stretch of each book, "
                "whatever its length, and every book weighs the same: a short story counts as much as a novel. A cell is the mean of the books' own shares of "
                "that slice's list (books with nothing in that slice are left out of the mean); counts are added up over the books. The trend asks, in "
                "each book, whether the word's share steadily rises or falls (Cochran–Armitage), and adds the books' z values up with equal weight "
                "(Stouffer): books that agree make a surer trend, books that disagree cancel out. The columns beside it say how many books were used "
                "(a book where the word never occurs, or is in every item, says nothing about it and is left out) and how many of them rise and fall. "
                "χ² is each book's χ² added up (degrees of freedom too): it asks whether the share varies between slices within the books at all, "
                "not whether the books agree, so a word that rises in half the books and falls in the other half can have a large χ² and no trend. "
                "The minimum frequency counts the word over all books together, so a word that is rare in each book can still be tested (Settings → Words can instead count it in each book: only the books where the word reaches the minimum are then tested and combined); the minimum range is the "
                "fewest books the word must occur in (or, counted in each book, reach the minimum in) to be tested, which keeps a trend from resting on one or two books (words below either minimum are listed without tests). "
                "In the heat grid a cell is shaded by that mean share relative to the word's own highest one; a hatched cell is a slice where no book has anything in this list, "
                "an empty one a slice where the word is in none of the books. Click a cell for the sentences of that slice in every book (the first 150, book by book), "
                "a row for those of the whole books.",
    "combined_overview": "Each row is one position in the books: slice k of n of every selected book that has the target. Words and mentions are added up over the books; "
                         "mentions per 1,000 words, the shares of names, descriptions and pronouns, and each list per 100 mentions are the mean of the books' own figures, "
                         "so a short story weighs as much as a novel (a book with no mentions in a slice has no shares there and is left out of that mean).",
    "combined_curve": "One figure along the books: the bold line is the mean of the books' own values at each position, every book weighing the same (a book with nothing to "
                      "take a share of in a slice is left out of that mean; a gap is a slice where no book has anything). With “Show each book” the books' own values are "
                      "drawn faintly behind it, which shows whether the books follow the mean or only a few of them do; hover a faint line for the book's title.",
    "sound": "The sound and rhythm of the target's speech: its quotes in each slice (a quote belongs to the slice of its first word), each read "
             "over its whole span. A slice where the target says nothing has no figures (—). Speech is short, so slices with few words spoken "
             "give unsteady figures; read them together with Words spoken. With the books combined each figure is the mean of the books' own.",
    "curve": "One figure along the book, for one target or for two: choose it from the list. Mentions per 1,000 words, the shares of names, descriptions and "
             "pronouns, and each list per 100 mentions come from the overview; a word's or a kind of action's value is its share of that slice's list. "
             "A gap is a slice where there is nothing to take a share of. With two targets, the second leaves out everything the first includes, as in Compare.",
}
MAX_SLICES = 200       # the most slices a table is made for (the slicer's own largest number of equal slices)
MAX_ROWS = 400         # words listed, most frequent first (as in the book-by-book table)
OVERVIEW_FIELDS = ("per1k", "names", "descriptions", "pronouns")        # the figures of an overview row that are not counts or relations


def slicing(view, book, cfg):
    """The slices of one book of the view, as the Arcs pages cut it -> (segments, info). Each segment is as
    `narrative.segments` makes it plus `pos`, where it starts in the book in %. ValueError if the book isn't in the view or the
    setting would give more than `MAX_SLICES` slices (a book cut every 20 words)."""
    if book not in view.bd:
        raise ValueError("That book isn't in the selection.")
    segs, info = narrative.book_segments(view, book, cfg)
    if len(segs) > MAX_SLICES:
        raise ValueError(f"These settings cut the book into {len(segs)} slices; at most {MAX_SLICES} can be shown. Use fewer slices or more words per slice.")
    n_tokens = max(1, view.bd[book].n_tokens)
    return [{**sg, "pos": round(100 * sg["start"] / n_tokens, 1)} for sg in segs], info


def finder(segs):
    """A function from a token of the book to the index of the slice that holds it (the first slice for anything before it)."""
    starts = [sg["start"] for sg in segs]
    return lambda tok: max(0, bisect_right(starts, tok) - 1)


def _pct(n, total):
    """n as a percentage of total, None if the total is 0 (a slice with nothing to share)."""
    return 100 * n / total if total else None


def _totalled(per_slice):
    """A book's words counted per slice as `_series_books` takes them: (the Counters, the size of each slice's list)."""
    return per_slice, [sum(c.values()) for c in per_slice]


def _mean(values):
    """The mean of the values that are not None, None if there are none."""
    got = [v for v in values if v is not None]
    return sum(got) / len(got) if got else None


def _series(per_slice, totals, min_freq, alpha, bonferroni, limit=None):
    """Rows for items counted per slice: `per_slice` is a Counter of items for each slice, `totals` the size of each slice's list.
    Each row has the item, its total, `counts` and `pcts` per slice, the chi-squared across slices (`stats.across`: chi2, df, p, v, `resid`
    per slice) and the `trend` {z, p, n}; items below `min_freq` are listed without tests. -> (rows, summary)."""
    items = Counter()
    for c in per_slice:
        items.update(c)
    tested = [k for k, n in items.items() if n >= min_freq]
    thresh = alpha / len(tested) if (bonferroni and tested) else alpha
    rows = []
    for k, n in items.most_common(limit):
        cs = [c.get(k, 0) for c in per_slice]
        pcts = [_pct(x, t) for x, t in zip(cs, totals)]
        row = {"item": k, "total": n, "counts": cs, "pcts": pcts, "chi2": None, "df": None, "p": None, "v": None,
               "resid": [None] * len(cs), "trend": None, "sig": False, "trend_sig": False, "tested": False}
        if n >= min_freq:
            a = stats.across(cs, totals)
            t = stats.trend(cs, totals)
            row.update(chi2=a["chi2"], df=a["df"], p=a["p"], v=a["v"], resid=a["resid"], sig=a["p"] < thresh, tested=True,
                       trend=t, trend_sig=t["p"] is not None and t["p"] < thresh)
        rows.append(row)
    summary = {"tested": len(tested), "min_freq": min_freq, "alpha": alpha, "bonferroni": bonferroni, "threshold": thresh,
               "significant": sum(r["sig"] for r in rows), "trending": sum(r["trend_sig"] for r in rows)}
    return rows, summary


def _relations(rel, curve_rel):
    """The relation of the curve's words (default: `rel`), once both relations are known to exist (ValueError if not)."""
    curve_rel = curve_rel or rel
    if rel not in RELATIONS or curve_rel not in RELATIONS:
        raise ValueError("Unknown relation.")
    return curve_rel


def _count(bd, clusters, segs, rel, curve_rel, skip=None):
    """What one book's `clusters` (the members of a target in it) add up to in each slice of `segs`, before any share or test. `skip` is
    {coref: mentions to leave out of that group} (`View.overlap`: a mention credited to two of the target's groups counts once):
    {mentions: [n per slice], by_prop: [Counter of PROP/NOM/PRON per slice], found: {relation: [findings per slice]}, words: [Counter of the
    words of `rel` per slice], kinds: [Counter of kinds of action per slice], curve: [Counter of the words of `curve_rel` per slice]};
    `curve` stays empty when `curve_rel` is `rel` (the curve then uses `words`)."""
    find, n = finder(segs), len(segs)
    raw = {"mentions": [0] * n, "by_prop": [Counter() for _ in segs], "found": {r: [0] * n for r in RELATIONS},
           "words": [Counter() for _ in segs], "kinds": [Counter() for _ in segs], "curve": [Counter() for _ in segs]}
    skip = skip or {}
    for c in clusters:
        g, drop = bd.groups[c], skip.get(c, ())
        for mi in g.mentions:
            if mi in drop:
                continue
            k = find(bd.mentions[mi][1])
            raw["mentions"][k] += 1
            raw["by_prop"][k][bd.mentions[mi][3]] += 1
        for r in RELATIONS:
            for key, mi, hl in g.rel_ev.get(r, ()):
                if mi in drop:
                    continue
                k = find(bd.mentions[mi][1])
                raw["found"][r][k] += 1
                if r == rel:
                    raw["words"][k][key] += 1
                if r == curve_rel and curve_rel != rel:
                    raw["curve"][k][key] += 1
                if r == "agent" and bd.ss.get(hl[-1], "none") != "none":       # the verb is the last token highlighted (see test_bookdata)
                    raw["kinds"][k][bd.ss[hl[-1]]] += 1
    return raw


def _sound(view, book, clusters, segs, cfg):
    """The sound and rhythm tally of a target's speech in each slice of `segs` (None where it says nothing): its quotes (those whose
    speaker is one of `clusters`, or with plural groups stands for one), each measured over its whole span, punctuation and all, in the
    slice that holds its first token. `cfg` is the workspace's sound settings (`prosody.config`)."""
    mine, find = set(clusters), finder(segs)
    per = [[] for _ in segs]
    for r in bdlg(view, book)["recs"]:
        if mine & set(r["speakers"]):
            per[find(r["start"])].append(list(range(r["start"], r["end"] + 1)))
    bd = view.bd[book]
    tallies = [prosody.count(bd, units, cfg) if units else None for units in per]
    return [t if t and t["words"] else None for t in tallies]


def _overview(raw, segs):
    """The overview rows (one per slice) of a book's `_count`: words, mentions, mentions per 1,000 words, the shares of names (PROP),
    descriptions (NOM) and pronouns (PRON) among the mentions, and each relation's findings per 100 mentions (`rel_<relation>`). When the
    count has the target's speech (`raw["sound"]`, from `_sound`), also the words it speaks there (`speech_words`) and their sound and
    rhythm figures (`snd`: {figure: value}, None where it says nothing)."""
    rows = []
    for k, sg in enumerate(segs):
        m, props = raw["mentions"][k], raw["by_prop"][k]
        row = {"index": k, "label": sg["label"], "words": sg["words"], "mentions": m,
               "per1k": 1000 * m / sg["words"] if sg["words"] else None,
               "names": _pct(props["PROP"], m), "descriptions": _pct(props["NOM"], m), "pronouns": _pct(props["PRON"], m)}
        for r in RELATIONS:
            row["rel_" + r] = _pct(raw["found"][r][k], m)
        if "sound" in raw:
            t = raw["sound"][k]
            row.update(speech_words=t["words"] if t else 0, snd=prosody.figures(t) if t else None)
        rows.append(row)
    return rows


def _assemble(raw, segs, rel, curve_rel, min_freq, alpha, bonferroni, max_rows=MAX_ROWS):
    """A book's `_count` as the figures of `table`: overview, rel, totals, rows, distinct, summary, supersenses, curve_rel and curve_words
    (see `table`). `max_rows` limits the words listed (None: all of them)."""
    totals = [sum(c.values()) for c in raw["words"]]
    rows, summary = _series(raw["words"], totals, min_freq, alpha, bonferroni, max_rows)
    kind_totals = [sum(c.values()) for c in raw["kinds"]]
    kind_rows, kind_summary = _series(raw["kinds"], kind_totals, min_freq, alpha, bonferroni)
    return {"overview": _overview(raw, segs), "rel": rel, "totals": totals, "rows": rows,
            "distinct": len(set().union(*raw["words"])), "summary": summary,
            "supersenses": {"totals": kind_totals, "rows": kind_rows, "summary": kind_summary},
            "curve_rel": curve_rel, "curve_words": None if curve_rel == rel else _shares([_totalled(raw["curve"])], curve_rel, max_rows)}


def table(view, spec, book, cfg, rel="mod", min_freq=3, alpha=0.05, bonferroni=False, exclude=frozenset(), segs=None, curve_rel=None,
          sound=None):
    """The target `spec` (anything `View.resolve` takes) over the slices of one book. `cfg` is the slicer setting (`S.nar.seg`), `rel` the
    relation whose words are tabled, `exclude` members left out (the other side of a comparison), `segs` slices already cut with `slicing`.
    `curve_rel` is the relation whose words the curve offers, which need not be the one tabled (default: the same). With `sound` (the
    workspace's sound settings) the overview also has the sound and rhythm of the target's speech per slice (see `_overview`).
    -> {label, book, info, segments, overview, rel, totals, rows, distinct, summary, supersenses: {totals, rows, summary}, curve_rel, curve_words}.
    `overview` has a row per slice, `rows` a row per word and `supersenses.rows` a row per kind of action, as `_series` makes them.
    `curve_words` is None when `curve_rel` is `rel` (the curve then uses `rows`), else {rel, totals, rows: [{item, pcts}]} for the words of `curve_rel`:
    shares only, no tests. A target that isn't in the book gives zeros throughout."""
    curve_rel = _relations(rel, curve_rel)
    info = None
    if segs is None:
        segs, info = slicing(view, book, cfg)
    mem, label, _ = view.resolve(spec, exclude)
    clusters = [c for b, c in mem if b == book]
    raw = _count(view.bd[book], clusters, segs, rel, curve_rel, view.overlap(mem).get(book))
    if sound is not None:
        raw["sound"] = _sound(view, book, clusters, segs, sound)
    return {"label": label, "book": {"id": book, "title": view.title(book)}, "info": info, "segments": segs,
            **_assemble(raw, segs, rel, curve_rel, min_freq, alpha, bonferroni)}


def _series_books(books, min_freq, alpha, bonferroni, limit=None, tests=True, min_range=1, each_book=False):
    """Rows for items counted per slice in several books that weigh the same (as `_series` does for one). `books` has a `_totalled` pair for each
    book, all cut into the same number of slices. Each row has the item, its `total` over all books, its `counts` per slice added up over
    the books and its `pcts` per slice: the mean of the books' own shares of that slice's list (a book with no list there is left out of
    the mean, None if none has one). The tests (unless `tests` is False) are made in each book and then put together: `trend` is
    `stats.combine_trends` (z, p, books used, up, down), `chi2`, `df` and `p` are `stats.combine_across`; a book where the item is absent or
    constant is left out of both. `v` and `resid` are None. An item is tested when it occurs `min_freq` times in all and in at least
    `min_range` of the books (the rest are listed without tests). With `each_book` only the books where the item occurs `min_freq` times
    count for it: they are the ones tested and combined, and there must be `min_range` of them (see `stats.passes`). -> (rows, summary)."""
    items, in_books, reached = Counter(), Counter(), Counter()
    for per_slice, _ in books:
        here = Counter()                                                           # this book's counts, over its slices
        for c in per_slice:
            here.update(c)
        items.update(here)
        in_books.update(here.keys())                                               # once for each book the item occurs in
        if each_book:
            reached.update(k for k, n in here.items() if n >= min_freq)
    ok = lambda k: stats.passes(items[k], in_books[k], reached[k], min_freq, min_range, each_book)
    size = len(books[0][1]) if books else 0
    tested = [k for k in items if ok(k)] if tests else []
    thresh = alpha / len(tested) if (bonferroni and tested) else alpha
    rows = []
    for k, n in items.most_common(limit):
        per = [[c.get(k, 0) for c in per_slice] for per_slice, _ in books]           # counts per book, per slice
        row = {"item": k, "total": n, "counts": [sum(col) for col in zip(*per)],
               "pcts": [_mean(_pct(cs[j], t[j]) for cs, (_, t) in zip(per, books)) for j in range(size)],
               "chi2": None, "df": None, "p": None, "v": None, "resid": [None] * size, "trend": None, "sig": False, "trend_sig": False, "tested": False}
        if tests and ok(k):
            use = [i for i, cs in enumerate(per) if not each_book or sum(cs) >= min_freq]          # the books that count for this item
            trends = [stats.trend(per[i], books[i][1]) for i in use]
            used = [i for i, tr in zip(use, trends) if tr["z"] is not None]
            a, tr = stats.combine_across([stats.across(per[i], books[i][1]) for i in used]), stats.combine_trends(trends)
            row.update(chi2=a["chi2"], df=a["df"], p=a["p"], sig=a["p"] < thresh, tested=True, trend=tr,
                       trend_sig=tr["p"] is not None and tr["p"] < thresh)
        rows.append(row)
    summary = {"tested": len(tested), "min_freq": min_freq, "min_range": min_range, "each_book": each_book, "alpha": alpha,
               "bonferroni": bonferroni, "threshold": thresh,
               "significant": sum(r["sig"] for r in rows), "trending": sum(r["trend_sig"] for r in rows)}
    return rows, summary


def _shares(books, rel, limit=MAX_ROWS):
    """The words of one relation counted per slice (`books`: a `_totalled` pair for each book) as {rel, totals, rows: [{item, pcts}]}: each word's
    share of the slice's list, rounded (mean over the books), None where no book has a list; the `limit` most frequent words."""
    rows, _ = _series_books(books, 0, 0.05, False, limit, tests=False)
    return {"rel": rel, "totals": [sum(col) for col in zip(*(t for _, t in books))],
            "rows": [{"item": r["item"], "pcts": [None if p is None else round(p, 3) for p in r["pcts"]]} for r in rows]}


def books_with(view, *specs):
    """The books of the view (in its order) that any of the specs has members in: the books worth choosing between."""
    got = {b for spec in specs for b, _ in view.resolve(spec)[0]}
    return [b for b in view.books if b in got]


def _common(view, books, spec, other):
    """The books to start with: those both targets are in, if there are any, else all of `books` (the books either is in)."""
    if other:
        both = [b for b in books if b in set(books_with(view, spec)) & set(books_with(view, other))]
        if both:
            return both
    return books


def report(view, spec, other=None, book=None, cfg=None, rel="mod", **stat):
    """What the Over the book page asks for: the target `spec` and, if given, a second target `other` (without the first's members, as
    in Compare) over the slices of `book`, which is what you last chose: if neither target is in it (or none was named) the first book both are
    in, else the first either is in, is used instead. `stat`: min_freq, alpha, bonferroni.
    -> {books: [{id, title}], book (the one used), a, b}, a and b being `table`s over the same slices; all None when neither target is in the view."""
    books = books_with(view, spec, *([other] if other else []))
    out = {"books": [{"id": b, "title": view.title(b)} for b in books], "book": None, "a": None, "b": None}
    if not books:
        return out
    if book not in books:
        book = _common(view, books, spec, other)[0]
    a = table(view, spec, book, cfg, rel, **stat)
    b = table(view, other, book, cfg, rel, exclude=frozenset(view.resolve(spec)[0]), segs=a["segments"], **stat) if other else None
    return {**out, "book": book, "a": a, "b": b}


MEASURE_WORDS = 100    # words offered as curve figures: the first this many of the two tables' words (the page lists the same number)


def curve_words(t):
    """The words table the curve offers for a `table`: its own `rows` when the curve's relation is the one tabled, else `curve_words`. Either way
    {rel, totals, rows} with `item` and `pcts` in each row."""
    return t["curve_words"] or t


def curve(t, measure):
    """One figure of a `table` along its slices. `measure`: `ov:<overview field>` (per1k, names, descriptions, pronouns), `rel:<relation>`
    (that list per 100 mentions), `word:<relation>:<word>` or `kind:<supersense>` (its share of the slice's list; 0 where the table lacks it but
    the slice has a list, None where the slice has none; a word of another relation than the curve's is None throughout), or `snd:<figure>`
    (a sound and rhythm figure of the target's speech; None where it says nothing, or throughout for a table made without sound). The same
    as the browser's `overValues`."""
    kind, _, key = measure.partition(":")
    if kind == "ov":
        return [o[key] for o in t["overview"]]
    if kind == "snd":
        return [o["snd"][key] if o.get("snd") else None for o in t["overview"]]
    if kind == "rel":
        return [o["rel_" + key] for o in t["overview"]]
    if kind == "word":
        rel, _, key = key.partition(":")
        src = curve_words(t)
        if src["rel"] != rel:
            return [None] * len(t["segments"])
    else:
        src = t["supersenses"]
    row = next((x for x in src["rows"] if x["item"] == key), None)
    return [row["pcts"][i] if row else (0 if src["totals"][i] else None) for i in range(len(t["segments"]))]


def similarity(a, b):
    """How alike two tables' curves are, for every figure the curve offers (as `curve` names them): Pearson's r and Spearman's rho between
    the two sides' values slice by slice, each with p and N (`stats.correlate`: slices without a value on both sides are left out). The
    tables are cut into the same number of slices, so slice k of one is the same relative stretch of the other."""
    rel = curve_words(a)["rel"]
    words = list(dict.fromkeys([x["item"] for x in curve_words(a)["rows"]] + [x["item"] for x in curve_words(b)["rows"]]))[:MEASURE_WORDS]
    kinds = list(dict.fromkeys([x["item"] for x in a["supersenses"]["rows"]] + [x["item"] for x in b["supersenses"]["rows"]]))
    measures = (["ov:" + k for k in OVERVIEW_FIELDS] + ["rel:" + r for r in RELATIONS]
                + [f"word:{rel}:{w}" for w in words] + ["kind:" + k for k in kinds]
                + (["snd:" + f for f in prosody.FIGURES] if "snd" in (a["overview"] or [{}])[0] else []))
    out = {}
    for m in measures:
        x, y = curve(a, m), curve(b, m)
        out[m] = {method: {k: c[k] for k in ("r", "p", "n")} for method in ("pearson", "spearman") for c in [stats.correlate(x, y, method)]}
    return out


def aligned(view, spec_a, book_a, spec_b, book_b, n, rel="mod", **stat):
    """Two targets, each in its own book, cut into the same number of equal slices so that slice k of n is the same relative stretch of
    both books. Side B's target is side A's if `spec_b` is None. A side's book is what you last chose; if its target isn't in it (or none was named) it is
    the first one its target is in (side B's: the first other than A's, when its target is in another), so a choice made for one target
    survives a change of target. Nothing is left out of the second side (unlike `report`: its book may be
    another, and a person linked across both books must count in each). `stat`: min_freq, alpha, bonferroni.
    -> {books_a, books_b: [{id, title}], book_a, book_b, n, a, b, similarity}: a and b are `table`s, `similarity` is `similarity(a, b)`;
    a, b and similarity are None when either target is in no book of the view. ValueError for n outside 2..MAX_SLICES."""
    if not 2 <= n <= MAX_SLICES:
        raise ValueError(f"Cut each book into between 2 and {MAX_SLICES} slices.")
    spec_b = spec_b or spec_a
    lists = [books_with(view, spec_a), books_with(view, spec_b)]
    listed = [[{"id": b, "title": view.title(b)} for b in books] for books in lists]
    out = {"books_a": listed[0], "books_b": listed[1], "book_a": None, "book_b": None, "n": n, "a": None, "b": None, "similarity": None}
    if not lists[0] or not lists[1]:
        return out
    if book_a not in lists[0]:
        book_a = lists[0][0]
    if book_b not in lists[1]:
        book_b = next((b for b in lists[1] if b != book_a), lists[1][0])
    cfg = {"mode": "slices", "slice_by": "count", "n": n}
    a = table(view, spec_a, book_a, cfg, rel, **stat)
    b = table(view, spec_b, book_b, cfg, rel, **stat)
    return {**out, "book_a": book_a, "book_b": book_b, "a": a, "b": b, "similarity": similarity(a, b)}


def compare(view, spec_a, spec_b, book=None, book_b=None, cfg=None, n=20, rel="mod", **stat):
    """The two sides of the Compare page over a book: in one book (`report`, `mode` "same") when some book holds both, else, since a book
    holding only one side would show the other as nothing, each side in its own book lined up by relative position (`aligned`, `mode` "aligned":
    `n` slices per book, `book` side A's, `book_b` side B's). The answer is that function's, with `mode` added."""
    la, lb = books_with(view, spec_a), books_with(view, spec_b)
    if la and lb and not set(la) & set(lb):
        return {**aligned(view, spec_a, book, spec_b, book_b, n, rel, **stat), "mode": "aligned"}
    return {**report(view, spec_a, spec_b, book, cfg, rel, **stat), "mode": "same"}


def _check_measure(measure):
    """ValueError unless `measure` is a figure `curve` knows (`ov:<field>`, `rel:<relation>`, `word:<relation>:<word>`, `kind:<kind>`,
    `snd:<figure>`)."""
    kind, _, key = measure.partition(":")
    ok = (key in OVERVIEW_FIELDS if kind == "ov" else key in RELATIONS if kind == "rel" else key.partition(":")[0] in RELATIONS if kind == "word"
          else key in prosody.FIGURES if kind == "snd" else kind == "kind" and bool(key))
    if not ok:
        raise ValueError("Unknown figure.")


def combined(view, spec, n=20, rel="mod", measure=None, curve_rel=None, min_freq=3, alpha=0.05, bonferroni=False, min_range=1, each_book=False,
             sound=None):
    """One target through all the selected books that hold it, every book weighing the same. Each book is cut into `n` equal slices (as in
    `aligned`), so slice k of n is the same relative stretch of each, and the books' figures for slice k are put together: counts are added up;
    a share or a figure per 1,000 words or per 100 mentions is the mean of the books' own (a book with nothing to take it of in that slice
    is left out); the tests are made in each book and combined (`_series_books`; `min_freq` counts the item over all books, or with `each_book` in each book, `min_range` is the
    fewest books it must occur in, or with `each_book` reach `min_freq` in, to be tested).
    `measure` (a figure as `curve` names it) also gives each book's own values of it, for drawing beside the combined ones. With `sound`
    (the workspace's sound settings) each slice also has the sound and rhythm of the target's speech: words spoken added up, each figure
    the mean of the books' own (a book where the target says nothing in that slice is left out).
    -> {label, n, books, skipped: [{id, title}], a, per_book}. `books` are the books used, `skipped` the selected books without the target.
    `a` is a table as `table` makes it, except that `book` and `info` are absent, each segment lists its `ranges` ({book, start, end}) and
    `pos`, the rows' `trend` carries n (books used), up and down, and chi2 / df / p are the books' added up; it is None when the target
    is in none of the books. `per_book` is [{id, title, values}] when a measure was asked for, else None."""
    curve_rel = _relations(rel, curve_rel)
    if not 2 <= n <= MAX_SLICES:
        raise ValueError(f"Cut each book into between 2 and {MAX_SLICES} slices.")
    if measure:
        _check_measure(measure)
    mem, label, _ = view.resolve(spec)
    clusters = {}
    for b, c in mem:
        clusters.setdefault(b, []).append(c)
    books = [b for b in view.books if b in clusters]
    listed = lambda ids: [{"id": b, "title": view.title(b)} for b in ids]
    out = {"label": label, "n": n, "books": listed(books), "skipped": listed(b for b in view.books if b not in clusters), "a": None, "per_book": None}
    if not books:
        return out
    cfg = {"mode": "slices", "slice_by": "count", "n": n}
    segs = {b: slicing(view, b, cfg)[0] for b in books}
    skip = view.overlap(mem)
    raw = {b: _count(view.bd[b], clusters[b], segs[b], rel, curve_rel, skip.get(b)) for b in books}
    if sound is not None:
        for b in books:
            raw[b]["sound"] = _sound(view, b, clusters[b], segs[b], sound)
    each = lambda key: [_totalled(raw[b][key]) for b in books]
    rows, summary = _series_books(each("words"), min_freq, alpha, bonferroni, MAX_ROWS, min_range=min_range, each_book=each_book)
    kind_rows, kind_summary = _series_books(each("kinds"), min_freq, alpha, bonferroni, min_range=min_range, each_book=each_book)
    overviews = [_overview(raw[b], segs[b]) for b in books]
    overview = []
    for k in range(n):
        got = [o[k] for o in overviews]
        overview.append({"index": k, "label": f"{k + 1}/{n}", "words": sum(o["words"] for o in got), "mentions": sum(o["mentions"] for o in got),
                         **{f: _mean(o[f] for o in got) for f in (*OVERVIEW_FIELDS, *("rel_" + r for r in RELATIONS))}})
        if sound is not None:
            said = [o["snd"] for o in got if o["snd"]]
            overview[-1].update(speech_words=sum(o["speech_words"] for o in got),
                                snd={f: _mean(x[f] for x in said) for f in prosody.FIGURES} if said else None)
    segments = [{"index": k, "label": f"{k + 1}/{n}", "pos": round(100 * k / n, 1), "words": overview[k]["words"],
                 "ranges": [{"book": b, "start": segs[b][k]["start"], "end": segs[b][k]["end"]} for b in books]} for k in range(n)]
    a = {"label": label, "segments": segments, "overview": overview, "rel": rel, "totals": [sum(col) for col in zip(*(t for _, t in each("words")))],
         "rows": rows, "distinct": len(set().union(*(c for b in books for c in raw[b]["words"]))), "summary": summary,
         "supersenses": {"totals": [sum(col) for col in zip(*(t for _, t in each("kinds")))], "rows": kind_rows, "summary": kind_summary},
         "curve_rel": curve_rel, "curve_words": None if curve_rel == rel else _shares(each("curve"), curve_rel)}
    out["a"] = a
    if measure:
        # a book's own table without tests: its values of any figure, as `curve` reads them
        own = lambda b: {"segments": segs[b], **_assemble(raw[b], segs[b], rel, curve_rel, float("inf"), 0.05, False, None)}
        out["per_book"] = [{**listed([b])[0], "values": curve(own(b), measure)} for b in books]
    return out
