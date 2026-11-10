"""overbook: a target's mentions, findings and kinds of action counted per slice of one book."""
from __future__ import annotations

from collections import Counter

import pytest

from alex.core import overbook as ob
from alex.core import stats
from alex.core.bookdata import RELATIONS
from alex.core.view import View

SLICES = {"mode": "slices", "n": 8}
HOLMES = ("alpha", 1)


def spec_of(view):
    """Holmes of the first book, as a spec."""
    return {"kind": "unit", "id": view.member_unit[HOLMES]}


def test_slices_add_up_to_the_book_by_book_figures(view):
    """One book, cut any way: the per-slice figures sum to what `View.by_book` says for the whole book."""
    spec = spec_of(view)
    whole = view.by_book(spec, "agent", min_freq=1)
    one = next(o for o in whole["overview"] if o["book"] == "alpha")
    for cfg in (SLICES, {"mode": "slices", "slice_by": "words", "words": 300}, {"mode": "chapters", "min_words": 0}):
        t = ob.table(view, spec, "alpha", cfg, "agent", min_freq=1)
        assert sum(o["mentions"] for o in t["overview"]) == one["mentions"]
        assert sum(o["words"] for o in t["overview"]) == view.bd["alpha"].n_words
        assert sum(t["totals"]) == whole["totals"][whole["books"].index(next(b for b in whole["books"] if b["id"] == "alpha"))]
        say = next(r for r in t["rows"] if r["item"] == "say")
        assert sum(say["counts"]) == say["total"] == view.rel_counts([HOLMES], "agent")["say"]


def test_every_relation_adds_up(view):
    spec = spec_of(view)
    for rel in RELATIONS:
        t = ob.table(view, spec, "alpha", SLICES, rel)
        assert sum(t["totals"]) == sum(view.rel_counts([HOLMES], rel).values())
        mentions = sum(o["mentions"] for o in t["overview"])
        assert sum((o["rel_" + rel] or 0) * o["mentions"] / 100 for o in t["overview"]) == pytest.approx(sum(t["totals"]))
        assert mentions == len(view.bd["alpha"].groups[1].mentions)


def test_a_finding_is_in_the_slice_of_its_mention(view):
    """Counted again by brute force: a finding goes to the slice whose range holds the first token of its mention."""
    bd, g = view.bd["alpha"], view.bd["alpha"].groups[1]
    segs, _ = ob.slicing(view, "alpha", SLICES)
    t = ob.table(view, spec_of(view), "alpha", SLICES, "agent", segs=segs)
    want = [Counter() for _ in segs]
    for key, mi, _ in g.rel_ev["agent"]:
        k = next(i for i, sg in enumerate(segs) if sg["start"] <= bd.mentions[mi][1] <= sg["end"])
        want[k][key] += 1
    for r in t["rows"]:
        assert r["counts"] == [w.get(r["item"], 0) for w in want]
    assert [o["mentions"] for o in t["overview"]] == [sum(1 for mi in g.mentions if sg["start"] <= bd.mentions[mi][1] <= sg["end"]) for sg in segs]


def test_kinds_of_action_add_up_to_the_whole_books(view):
    whole = view.by_book(spec_of(view), "agent")
    kinds = next(s for s in whole["supersenses"] if s["book"] == "alpha")
    t = ob.table(view, spec_of(view), "alpha", SLICES, "agent", min_freq=1)
    assert {r["item"]: r["total"] for r in t["supersenses"]["rows"]} == {r["item"]: r["n"] for r in kinds["rows"]}
    assert sum(t["supersenses"]["totals"]) == sum(r["n"] for r in kinds["rows"])


def test_only_the_asked_book_is_counted_for_a_linked_person(lib):
    p = lib.link(lib.link("e:alpha:1", "e:beta:5"), "e:gamma:3")
    v = View(lib, ["alpha", "beta", "gamma"])
    spec = {"kind": "unit", "id": p}
    a = ob.table(v, spec, "alpha", SLICES, "agent", min_freq=1)
    assert sum(o["mentions"] for o in a["overview"]) == len(v.bd["alpha"].groups[1].mentions)
    assert [r for r in a["rows"] if r["item"] == "say"][0]["total"] == v.rel_counts([("alpha", 1)], "agent")["say"]
    assert a["book"] == {"id": "alpha", "title": v.title("alpha")} and a["info"] is not None


def test_a_target_outside_the_book_is_zeros(view):
    spec = {"kind": "unit", "id": view.member_unit[("beta", 5)]}
    t = ob.table(view, spec, "alpha", SLICES, "agent")
    assert len(t["segments"]) == 8 and t["rows"] == [] and sum(t["totals"]) == 0
    assert all(o["mentions"] == 0 and o["per1k"] == 0 and o["names"] is None for o in t["overview"])


def test_the_other_side_of_a_comparison_leaves_the_first_sides_members_out(view):
    spec = spec_of(view)
    a = ob.table(view, spec, "alpha", SLICES, "agent")
    mem = view.resolve(spec)[0]
    b = ob.table(view, {"kind": "type", "types": ["PER"]}, "alpha", SLICES, "agent", exclude=mem, segs=a["segments"])
    both = ob.table(view, {"kind": "type", "types": ["PER"]}, "alpha", SLICES, "agent", segs=a["segments"])
    assert [x + y for x, y in zip((o["mentions"] for o in a["overview"]), (o["mentions"] for o in b["overview"]))] == [o["mentions"] for o in both["overview"]]
    assert b["segments"] is a["segments"] and b["info"] is None


def test_too_many_slices_and_unknown_books_are_refused(view, monkeypatch):
    monkeypatch.setattr(ob, "MAX_SLICES", 5)
    with pytest.raises(ValueError, match="at most 5"):
        ob.slicing(view, "alpha", {"mode": "slices", "n": 6})
    assert len(ob.slicing(view, "alpha", {"mode": "slices", "n": 5})[0]) == 5
    with pytest.raises(ValueError, match="isn't in the selection"):
        ob.slicing(view, "nope", SLICES)
    with pytest.raises(ValueError, match="relation"):
        ob.table(view, spec_of(view), "alpha", {"mode": "slices", "n": 5}, "bogus")


def test_the_finder_places_every_token_in_one_slice(view):
    segs, _ = ob.slicing(view, "alpha", {"mode": "slices", "n": 7})
    find = ob.finder(segs)
    for k, sg in enumerate(segs):
        assert find(sg["start"]) == find(sg["end"]) == k
    assert find(-3) == 0


def test_trend_and_chi_squared_of_a_word_that_rises():
    """A word whose share grows slice by slice trends up; one that stays level doesn't; an empty slice is skipped."""
    rising = [Counter({"x": 10 * i, "y": 70 - 10 * i}) for i in range(1, 7)]
    totals = [70] * 6
    rows, summary = ob._series(rising, totals, 3, 0.05, False)
    x = next(r for r in rows if r["item"] == "x")
    assert x["trend"]["n"] == 6 and x["trend"]["z"] > 0 and x["trend_sig"] and x["sig"]
    assert x["trend"]["p"] == stats.trend(x["counts"], totals)["p"]
    y = next(r for r in rows if r["item"] == "y")
    assert y["trend"]["z"] < 0
    a = stats.across(x["counts"], totals)
    assert (x["chi2"], x["p"], x["v"]) == (a["chi2"], a["p"], a["v"]) and x["pcts"][0] == pytest.approx(100 * 10 / 70)
    level = [Counter({"z": 5, "w": 5}) for _ in range(6)]
    z = ob._series(level, [10] * 6, 3, 0.05, False)[0][0]
    assert z["chi2"] == pytest.approx(0) and not z["sig"] and not z["trend_sig"]
    gap = [Counter({"x": 4, "y": 4}), Counter(), Counter({"x": 6, "y": 2}), Counter({"x": 8})]
    g = next(r for r in ob._series(gap, [8, 0, 8, 8], 1, 0.05, False)[0] if r["item"] == "x")
    assert g["pcts"] == [50, None, 75, 100] and g["trend"]["n"] == 3 and g["resid"][1] is None


def test_a_sparse_word_leaning_late_is_a_modest_trend():
    """6 occurrences in 20 slices, leaning late: the test of trend goes by the counts and the slice sizes, so it is far from certain."""
    late = (10, 12, 14, 15, 17, 19)
    per = [Counter({"w": 1 if i in late else 0, "other": 50}) for i in range(20)]
    w = next(r for r in ob._series(per, [51 if i in late else 50 for i in range(20)], 3, 0.05, False)[0] if r["item"] == "w")
    assert w["trend"]["z"] > 0 and 0.01 < w["trend"]["p"] < 0.05 and set(w["trend"]) == {"z", "p", "n"}


def test_rare_words_are_listed_without_tests_and_bonferroni_tightens():
    per = [Counter({"rare": 2 if i == 0 else 0, "x": 8 + i}) for i in range(5)]
    rows, summary = ob._series(per, [sum(c.values()) for c in per], 3, 0.05, True)
    rare = next(r for r in rows if r["item"] == "rare")
    assert not rare["tested"] and rare["trend"] is None and rare["p"] is None
    assert summary["tested"] == 1 and summary["threshold"] == 0.05
    many = [Counter({f"w{i}": 5 for i in range(10)}) for _ in range(3)]
    assert ob._series(many, [50] * 3, 3, 0.05, True)[1]["threshold"] == 0.005


# ---------- the report and its route ----------
def test_report_offers_the_books_a_target_is_in(lib):
    p = lib.link(lib.link("e:alpha:1", "e:beta:5"), "e:gamma:3")
    v = View(lib, ["alpha", "beta", "gamma"])
    spec = {"kind": "unit", "id": p}
    r = ob.report(v, spec, cfg=SLICES)
    assert [b["id"] for b in r["books"]] == ["alpha", "beta", "gamma"] and r["book"] == "alpha" and r["b"] is None
    assert ob.report(v, spec, book="beta", cfg=SLICES)["a"]["book"]["id"] == "beta"
    only_beta = {**spec, "books": ["beta"]}                                  # a target limited to one book is in that book only
    assert [b["id"] for b in ob.report(v, only_beta, cfg=SLICES)["books"]] == ["beta"]
    assert ob.report(v, only_beta, book="alpha", cfg=SLICES)["book"] == "beta"          # a book the target isn't in is only a preference
    assert ob.report(v, spec, book="gamma", cfg=SLICES)["book"] == "gamma"              # and one it is in is kept, whatever the target


def test_report_for_a_target_nowhere_is_empty_and_two_sides_share_the_slices(view):
    nowhere = ob.report(view, {"kind": "unit", "id": "e:alpha:999"}, cfg=SLICES)
    assert nowhere == {"books": [], "book": None, "a": None, "b": None}
    r = ob.report(view, spec_of(view), {"kind": "unit", "id": view.member_unit[("alpha", 2)]}, "alpha", SLICES, "agent")
    assert r["a"]["segments"] is r["b"]["segments"] and r["a"]["label"] != r["b"]["label"]
    assert [b["id"] for b in r["books"]] == ["alpha"]


def test_the_sentences_behind_a_slice_are_exactly_its_count(view):
    """A word's evidence within a slice has as many sentences as the table's cell, and every one lies in the slice; kinds of action too."""
    spec = spec_of(view)
    t = ob.table(view, spec, "alpha", SLICES, "agent", min_freq=1)
    for word in ("say", "look"):
        row = next(r for r in t["rows"] if r["item"] == word)
        for k, sg in enumerate(t["segments"]):
            ev = view.evidence(spec, "agent", word, within=[("alpha", sg["start"], sg["end"])])
            assert ev["total"] == row["counts"][k]
            assert all(sg["start"] <= i["tok"] <= sg["end"] for i in ev["items"])
    for row in t["supersenses"]["rows"]:
        got = [view.evidence(spec, "supersense", row["item"], within=[("alpha", sg["start"], sg["end"])])["total"] for sg in t["segments"]]
        assert got == row["counts"]
        assert view.evidence(spec, "supersense", row["item"])["total"] == row["total"]
    assert view.evidence(spec, "agent", "say", within=[("beta", 0, 10 ** 9)])["total"] == 0          # another book has none of it


def test_the_route(client):
    units = client.post("/api/units", json={"books": ["alpha", "beta", "gamma"]}).json()["rows"]
    holmes = next(r["id"] for r in units if r["name"] == "Holmes" and r["books"] == ["alpha"])
    watson = next(r["id"] for r in units if r["name"] == "Watson" and r["books"] == ["alpha"])
    body = {"books": ["alpha", "beta", "gamma"], "target": {"kind": "unit", "id": holmes}, "seg": SLICES, "rel": "agent", "min_freq": 1}
    r = client.post("/api/overbook", json=body)
    assert r.status_code == 200
    j = r.json()
    assert j["book"] == "alpha" and len(j["a"]["segments"]) == 8 and j["b"] is None and j["a"]["rows"][0]["trend"]["z"] is not None
    two = client.post("/api/overbook", json={**body, "other": {"kind": "unit", "id": watson}}).json()
    assert two["b"]["segments"] == two["a"]["segments"] and two["b"]["label"] == "Watson"
    assert client.post("/api/overbook", json={**body, "book": "beta"}).json()["book"] == "alpha"      # Holmes is in alpha only: a preference, not an error
    for bad in ({"other": "Watson"}, {"rel": "bogus"}, {"target": None}):
        assert client.post("/api/overbook", json={**body, **bad}).status_code == 400, bad
    ev = client.post("/api/evidence", json={"books": ["alpha"], "target": body["target"], "kind": "agent", "key": "say",
                                            "within": {"book": "alpha", "start": 0, "end": 10 ** 9}}).json()
    assert ev["total"] == client.post("/api/evidence", json={"books": ["alpha"], "target": body["target"], "kind": "agent", "key": "say"}).json()["total"]
    assert client.post("/api/evidence", json={"books": ["alpha"], "target": body["target"], "kind": "agent", "key": "say", "within": "x"}).status_code == 400


# ---------- two books aligned ----------
def linked_holmes(lib):
    """Holmes linked across the three books, and a view of them."""
    p = lib.link(lib.link("e:alpha:1", "e:beta:5"), "e:gamma:3")
    return {"kind": "unit", "id": p}, View(lib, ["alpha", "beta", "gamma"])


def test_each_side_is_counted_in_its_own_book_and_cut_the_same_way(lib):
    spec, v = linked_holmes(lib)
    r = ob.aligned(v, spec, "alpha", None, "beta", 10, "agent")
    assert (r["book_a"], r["book_b"], r["n"]) == ("alpha", "beta", 10)
    assert r["a"]["book"]["id"] == "alpha" and r["b"]["book"]["id"] == "beta"
    assert sum(o["mentions"] for o in r["a"]["overview"]) == len(v.bd["alpha"].groups[1].mentions)
    assert sum(o["mentions"] for o in r["b"]["overview"]) > 0 and sum(o["mentions"] for o in r["b"]["overview"]) == len(v.bd["beta"].groups[5].mentions)
    for side, book in (("a", "alpha"), ("b", "beta")):
        bd, segs = v.bd[book], r[side]["segments"]
        assert [sg["start"] for sg in segs] == [k * bd.n_tokens // 10 for k in range(10)]                # the same relative stretches
        assert sum(sg["words"] for sg in segs) == bd.n_words


def test_nothing_is_left_out_of_the_second_side(lib):
    """In `report` the second target leaves out the first's members, which for a person linked across both books would empty the second side."""
    spec, v = linked_holmes(lib)
    assert ob.report(v, spec, spec, "alpha", {"mode": "slices", "n": 5})["b"]["overview"][0]["mentions"] == 0
    r = ob.aligned(v, spec, "alpha", spec, "beta", 5)
    assert sum(o["mentions"] for o in r["b"]["overview"]) > 0


def test_the_books_default_to_the_first_and_to_another_one(lib):
    spec, v = linked_holmes(lib)
    r = ob.aligned(v, spec, None, None, None, 5)
    assert (r["book_a"], r["book_b"]) == ("alpha", "beta")
    assert [b["id"] for b in r["books_a"]] == [b["id"] for b in r["books_b"]] == ["alpha", "beta", "gamma"]
    one = {"kind": "unit", "id": v.member_unit[("alpha", 2)]}                                              # Watson of alpha: in one book only
    r = ob.aligned(v, one, None, None, None, 5)
    assert (r["book_a"], r["book_b"]) == ("alpha", "alpha")


def test_different_targets_in_different_books(view):
    holmes, watson = {"kind": "unit", "id": view.member_unit[("alpha", 1)]}, {"kind": "unit", "id": view.member_unit[("beta", 6)]}
    r = ob.aligned(view, holmes, "alpha", watson, "beta", 8, "agent")
    assert r["a"]["label"] == "Holmes" and r["b"]["label"] == view.units[watson["id"]].name
    assert sum(o["mentions"] for o in r["b"]["overview"]) == len(view.bd["beta"].groups[6].mentions)


def test_similarity_is_the_correlation_of_the_two_curves(lib):
    spec, v = linked_holmes(lib)
    r = ob.aligned(v, spec, "alpha", None, "beta", 10, "agent", min_freq=1)
    s = r["similarity"]
    x, y = [o["per1k"] for o in r["a"]["overview"]], [o["per1k"] for o in r["b"]["overview"]]
    for method in ("pearson", "spearman"):
        want = stats.correlate(x, y, method)
        assert s["ov:per1k"][method] == {"r": want["r"], "p": want["p"], "n": want["n"]}
    assert {"ov:names", "ov:pronouns", "rel:agent", "rel:prep", "word:agent:say"} <= set(s) and any(k.startswith("kind:") for k in s)
    assert s["word:agent:say"]["pearson"]["n"] == 10 and ob.curve(r["a"], "word:agent:say") == next(w for w in r["a"]["rows"] if w["item"] == "say")["pcts"]
    same = ob.aligned(v, spec, "alpha", None, "alpha", 10)["similarity"]                                    # a book against itself
    assert same["ov:per1k"]["pearson"]["r"] == pytest.approx(1) and same["ov:per1k"]["spearman"]["r"] == pytest.approx(1)


def test_curve_gives_the_figure_of_a_table_slice_by_slice(view):
    t = ob.table(view, spec_of(view), "alpha", SLICES, "agent", min_freq=1)
    assert ob.curve(t, "ov:names") == [o["names"] for o in t["overview"]] and ob.curve(t, "rel:agent") == [o["rel_agent"] for o in t["overview"]]
    assert ob.curve(t, "word:agent:no-such-word") == [0 if n else None for n in t["totals"]]
    assert ob.curve(t, "word:mod:say") == [None] * len(t["segments"])                    # a word of a relation the curve doesn't offer
    kind = t["supersenses"]["rows"][0]
    assert ob.curve(t, "kind:" + kind["item"]) == kind["pcts"]


def test_aligned_refuses_what_it_cannot_cut_or_find(lib):
    spec, v = linked_holmes(lib)
    for n in (1, 201):
        with pytest.raises(ValueError, match="between 2 and 200"):
            ob.aligned(v, spec, None, None, None, n)
    only_beta = {**spec, "books": ["beta"]}
    r = ob.aligned(v, only_beta, "alpha", None, "gamma", 5)                              # books the targets aren't in are only preferences
    assert (r["book_a"], r["book_b"]) == ("beta", "beta")
    assert ob.aligned(v, spec, "gamma", None, "beta", 5)["book_a"] == "gamma" and ob.aligned(v, spec, "gamma", None, "beta", 5)["book_b"] == "beta"
    nowhere = ob.aligned(v, {"kind": "unit", "id": "e:alpha:999"}, None, None, None, 5)
    assert nowhere["a"] is None and nowhere["b"] is None and nowhere["similarity"] is None and nowhere["books_a"] == []


def test_the_aligned_route(client):
    units = client.post("/api/units", json={"books": ["alpha", "beta", "gamma"]}).json()["rows"]
    holmes = next(r["id"] for r in units if r["name"] == "Holmes" and r["books"] == ["alpha"])
    watson_b = next(r["id"] for r in units if r["name"] == "Watson" and r["books"] == ["beta"])
    body = {"books": ["alpha", "beta", "gamma"], "target": {"kind": "unit", "id": holmes}, "book": "alpha", "other": {"kind": "unit", "id": watson_b}, "other_book": "beta",
            "n": 6, "rel": "agent", "min_freq": 1}
    j = client.post("/api/overbook/aligned", json=body).json()
    assert j["book_a"] == "alpha" and j["book_b"] == "beta" and len(j["a"]["segments"]) == len(j["b"]["segments"]) == 6 and "ov:per1k" in j["similarity"]
    same = client.post("/api/overbook/aligned", json={k: v for k, v in body.items() if k not in ("other", "other_book")}).json()
    assert same["b"]["label"] == "Holmes" and same["book_b"] == "alpha"                                      # Holmes is in alpha only
    assert client.post("/api/overbook/aligned", json={**body, "n": 1}).json()["n"] == 2 and client.post("/api/overbook/aligned", json={**body, "n": 5000}).json()["n"] == 200   # held to 2..200 like the other numbers
    assert client.post("/api/overbook/aligned", json={**body, "book": "beta"}).json()["book_a"] == "alpha"       # a preference, not an error
    for bad in ({"n": "many"}, {"other": "Watson"}, {"rel": "bogus"}, {"target": None}):
        assert client.post("/api/overbook/aligned", json={**body, **bad}).status_code == 400, bad


# ---------- the Compare page's two sides ----------
def test_compare_measures_two_sides_in_their_own_books_when_no_book_holds_both(view):
    """Two entities that live in different books: a book holding only one would show the other as a flat zero."""
    a, b = {"kind": "unit", "id": view.member_unit[("alpha", 1)]}, {"kind": "unit", "id": view.member_unit[("beta", 5)]}
    assert [o["mentions"] for o in ob.report(view, a, b, None, SLICES, "agent")["b"]["overview"]] == [0] * 8        # the problem
    r = ob.compare(view, a, b, None, None, SLICES, 6, "agent")
    assert r["mode"] == "aligned" and (r["book_a"], r["book_b"], r["n"]) == ("alpha", "beta", 6)
    assert sum(o["mentions"] for o in r["a"]["overview"]) > 0 and sum(o["mentions"] for o in r["b"]["overview"]) == len(view.bd["beta"].groups[5].mentions)
    assert "ov:per1k" in r["similarity"]


def test_compare_keeps_one_book_when_a_book_holds_both_and_starts_in_it(lib):
    p = lib.link("e:beta:5", "e:gamma:3")                                   # Holmes of beta and gamma
    v = View(lib, ["alpha", "beta", "gamma"])
    watson_gamma = next(u.id for u in v.units.values() if u.name == "Watson" and u.books == {"gamma"})
    r = ob.compare(v, {"kind": "unit", "id": p}, {"kind": "unit", "id": watson_gamma}, None, None, SLICES, 6)
    assert r["mode"] == "same" and r["book"] == "gamma"                       # not beta, the first of the two sides' books
    assert sum(o["mentions"] for o in r["b"]["overview"]) > 0
    assert ob.compare(v, {"kind": "unit", "id": p}, {"kind": "unit", "id": watson_gamma}, "beta", None, SLICES, 6)["book"] == "beta"     # your choice stands


def test_compare_with_a_side_in_no_book_still_draws_the_other(view):
    """As `report` always did: the page is empty only when neither side is in the selection."""
    one = {"kind": "unit", "id": view.member_unit[("alpha", 1)]}
    r = ob.compare(view, one, {"kind": "unit", "id": "e:alpha:999"}, None, None, SLICES, 6)
    assert r["mode"] == "same" and sum(o["mentions"] for o in r["a"]["overview"]) > 0 and sum(o["mentions"] for o in r["b"]["overview"]) == 0
    assert ob.compare(view, {"kind": "unit", "id": "e:alpha:998"}, {"kind": "unit", "id": "e:alpha:999"}, None, None, SLICES, 6)["a"] is None


def test_the_compare_route(client):
    units = client.post("/api/units", json={"books": ["alpha", "beta", "gamma"]}).json()["rows"]
    ha = next(r["id"] for r in units if r["name"] == "Holmes" and r["books"] == ["alpha"])
    hb = next(r["id"] for r in units if r["name"] == "Holmes" and r["books"] == ["beta"])
    wa = next(r["id"] for r in units if r["name"] == "Watson" and r["books"] == ["alpha"])
    body = {"books": ["alpha", "beta", "gamma"], "target": {"kind": "unit", "id": ha}, "other": {"kind": "unit", "id": hb}, "seg": SLICES, "n": 7, "rel": "agent"}
    j = client.post("/api/overbook/compare", json=body).json()
    assert j["mode"] == "aligned" and j["n"] == 7 and (j["book_a"], j["book_b"]) == ("alpha", "beta") and "similarity" in j
    j = client.post("/api/overbook/compare", json={**body, "other": {"kind": "unit", "id": wa}}).json()
    assert j["mode"] == "same" and j["book"] == "alpha" and len(j["a"]["segments"]) == 8
    for bad in ({"other": None}, {"other": "x"}, {"target": None}, {"n": "many"}):
        assert client.post("/api/overbook/compare", json={**body, **bad}).status_code == 400, bad


# ---------- the curve's own list of words ----------
def test_the_curve_can_offer_the_words_of_another_list_than_the_one_tabled(view):
    spec = spec_of(view)
    own = ob.table(view, spec, "alpha", SLICES, "agent", min_freq=1)
    assert own["curve_rel"] == "agent" and own["curve_words"] is None and ob.curve_words(own) is own          # the same list: the table's own rows
    other = ob.table(view, spec, "alpha", SLICES, "agent", min_freq=1, curve_rel="poss")
    assert other["rel"] == "agent" and other["rows"] == own["rows"]                                          # the tabled words are untouched
    cw = other["curve_words"]
    assert cw["rel"] == "poss" and other["curve_rel"] == "poss" and ob.curve_words(other) is cw
    check = ob.table(view, spec, "alpha", SLICES, "poss", min_freq=1)                                        # counted again as a table of that list
    assert cw["totals"] == check["totals"]
    want = {r["item"]: r["pcts"] for r in check["rows"]}
    assert {r["item"] for r in cw["rows"]} == set(want)
    for r in cw["rows"]:
        assert r["pcts"] == [None if p is None else pytest.approx(p, abs=1e-3) for p in want[r["item"]]]
    some = cw["rows"][0]["item"]
    assert ob.curve(other, f"word:poss:{some}") == [None if p is None else pytest.approx(p, abs=1e-3) for p in want[some]]
    assert ob.curve(other, f"word:agent:{some}") == [None] * 8                                               # not this table's curve list
    with pytest.raises(ValueError, match="relation"):
        ob.table(view, spec, "alpha", SLICES, "agent", curve_rel="bogus")


def test_similarity_follows_the_curves_list(lib):
    spec, v = linked_holmes(lib)
    r = ob.aligned(v, spec, "alpha", None, "beta", 8, "mod", curve_rel="agent")
    s = r["similarity"]
    assert any(k.startswith("word:agent:") for k in s) and not any(k.startswith("word:mod:") for k in s)
    assert "word:agent:say" in s and s["word:agent:say"]["pearson"]["n"] == 8
    r2 = ob.aligned(v, spec, "alpha", None, "beta", 8, "agent")                                              # curve list = tabled list
    assert "word:agent:say" in r2["similarity"] and r2["a"]["curve_words"] is None


def test_the_curve_list_is_asked_for_by_name_in_every_route(client):
    units = client.post("/api/units", json={"books": ["alpha", "beta", "gamma"]}).json()["rows"]
    holmes = next(r["id"] for r in units if r["name"] == "Holmes" and r["books"] == ["alpha"])
    watson = next(r["id"] for r in units if r["name"] == "Watson" and r["books"] == ["alpha"])
    body = {"books": ["alpha", "beta", "gamma"], "target": {"kind": "unit", "id": holmes}, "other": {"kind": "unit", "id": watson}, "seg": SLICES, "rel": "agent", "curve_rel": "poss", "n": 6}
    for path in ("/api/overbook", "/api/overbook/compare"):
        j = client.post(path, json=body).json()
        assert j["a"]["curve_rel"] == "poss" and j["a"]["rel"] == "agent" and j["a"]["curve_words"]["rel"] == "poss", path
        assert client.post(path, json={**body, "curve_rel": "bogus"}).status_code == 400, path
    al = client.post("/api/overbook/aligned", json={**body, "other": None}).json()
    assert al["a"]["curve_words"]["rel"] == "poss"


# ---------- all the books together ----------
def test_books_that_weigh_the_same_are_combined_slice_by_slice():
    """Counts add up, shares are the mean of the books' own, the tests are each book's put together; a book without the word is left out of them."""
    up = [Counter({"x": 10 * i, "y": 70 - 10 * i}) for i in range(1, 7)]               # share of x rises 14% -> 86%
    down = [Counter({"x": 10 * (7 - i), "y": 10 * i}) for i in range(1, 7)]
    none = [Counter({"y": 20}) for _ in range(6)]                                       # x never occurs
    books = [ob._totalled(up), ob._totalled(down), ob._totalled(none)]
    rows, summary = ob._series_books(books, 3, 0.05, False)
    x = next(r for r in rows if r["item"] == "x")
    assert x["total"] == 420 and x["counts"][0] == 10 + 60
    assert x["pcts"][0] == pytest.approx((100 * 10 / 70 + 100 * 60 / 70 + 0) / 3)
    t_up, t_down = stats.trend([c["x"] for c in up], [70] * 6), stats.trend([c["x"] for c in down], [70] * 6)
    assert x["trend"]["n"] == 2 and (x["trend"]["up"], x["trend"]["down"]) == (1, 1)
    assert x["trend"]["z"] == pytest.approx((t_up["z"] + t_down["z"]) / 2 ** 0.5) and x["trend"]["z"] == pytest.approx(0)
    a_up, a_down = stats.across([c["x"] for c in up], [70] * 6), stats.across([c["x"] for c in down], [70] * 6)
    assert x["chi2"] == pytest.approx(a_up["chi2"] + a_down["chi2"]) and x["df"] == 10 and x["v"] is None and x["resid"] == [None] * 6
    assert x["tested"] and not x["trend_sig"] and x["sig"]                              # varies a lot within books, but the books disagree
    assert summary["tested"] == 2 and summary["trending"] == 0
    y = next(r for r in rows if r["item"] == "y")
    assert y["trend"]["n"] == 2 and y["trend"]["z"] == pytest.approx(0)                 # constant in the third book (20 of 20): left out


def test_books_that_agree_make_a_surer_trend_and_a_slice_without_a_list_is_skipped():
    up = [Counter({"x": 10 * i, "y": 70 - 10 * i}) for i in range(1, 7)]
    gap = [Counter({"x": 2 * i, "y": 12 - 2 * i}) for i in range(1, 7)]
    gap[2] = Counter()                                                                  # a slice with nothing in this book's list
    rows, _ = ob._series_books([ob._totalled(up), ob._totalled(gap)], 3, 0.05, False)
    x = next(r for r in rows if r["item"] == "x")
    one = stats.trend([c["x"] for c in up], [70] * 6)
    assert x["trend"]["up"] == 2 and x["trend"]["z"] > one["z"] / 2 ** 0.5 and x["trend"]["p"] < one["p"] and x["trend_sig"]
    assert x["pcts"][2] == pytest.approx(100 * 30 / 70) and x["counts"][2] == 30      # only the first book has a list in slice 3
    assert ob._mean([None, None]) is None


def test_the_minimum_frequency_is_the_total_over_all_books():
    """A word once in each of three books is tested at min_freq 3 (it is in 3 books together); no book has the 3 alone."""
    books = [ob._totalled([Counter({"w": 1 if i == k else 0, "o": 5}) for i in range(4)]) for k in (0, 1, 3)]
    rows, summary = ob._series_books(books, 3, 0.05, False)
    w = next(r for r in rows if r["item"] == "w")
    assert w["tested"] and w["total"] == 3 and summary["tested"] == 2
    assert not next(r for r in ob._series_books(books, 4, 0.05, False)[0] if r["item"] == "w")["tested"]


def test_each_book_tests_an_item_only_in_the_books_that_reach_the_minimum():
    """With `each_book` a book counts for a word only where it occurs `min_freq` times there; the others are neither tested nor combined."""
    book = lambda w: ob._totalled([Counter({"w": n, "o": 5}) for n in w])
    a, b, c = book([0, 1, 1, 2]), book([2, 1, 1, 0]), book([0, 0, 1, 0])               # w: 4, 4 and 1 in the three books
    word = lambda books, **kw: next(r for r in ob._series_books(books, 3, 0.05, False, **kw)[0] if r["item"] == "w")
    together, each = word([a, b, c]), word([a, b, c], each_book=True)
    assert together["tested"] and together["trend"]["n"] == 3
    assert each["tested"] and each["trend"]["n"] == 2                                   # the third book has it once: left out of the test
    assert each["total"] == together["total"] == 9 and each["counts"] == together["counts"]            # the figures stay whole
    own = [stats.across([c.get("w", 0) for c in per_slice], totals) for per_slice, totals in (a, b)]
    assert each["chi2"] == pytest.approx(own[0]["chi2"] + own[1]["chi2"]) and each["df"] == own[0]["df"] + own[1]["df"]
    assert word([a, b, c], min_range=2, each_book=True)["tested"] and not word([a, b, c], min_range=3, each_book=True)["tested"]
    spread = [book(w) for w in ([1, 1, 0, 0], [0, 0, 1, 1], [1, 0, 1, 0])]               # w: 2 in each book, 6 in all, never 3 in one
    assert word(spread)["tested"] and not word(spread, each_book=True)["tested"]


def test_combined_over_one_book_is_that_books_own_table(view):
    """A target in one book only: nothing to combine, so every figure is the book's own (cut into equal slices)."""
    spec = {"kind": "unit", "id": view.member_unit[("alpha", 2)]}                        # Watson of alpha
    c = ob.combined(view, spec, 6, "agent", min_freq=1)
    t = ob.table(view, spec, "alpha", {"mode": "slices", "slice_by": "count", "n": 6}, "agent", min_freq=1)
    assert [b["id"] for b in c["books"]] == ["alpha"] and [b["id"] for b in c["skipped"]] == ["beta", "gamma"]
    a = c["a"]
    assert a["overview"] == t["overview"] and a["totals"] == t["totals"] and a["distinct"] == t["distinct"]
    for mine, own in zip(a["rows"], t["rows"]):
        assert (mine["item"], mine["total"], mine["counts"], mine["pcts"]) == (own["item"], own["total"], own["counts"], own["pcts"])
        assert mine["trend"] is None or (mine["trend"]["z"], mine["trend"]["p"]) == (own["trend"]["z"], own["trend"]["p"])
        assert (mine["chi2"], mine["p"]) == (own["chi2"], own["p"])
    assert a["supersenses"]["totals"] == t["supersenses"]["totals"] and a["curve_words"] is None and a["label"] == t["label"]


def test_combined_adds_up_the_books_and_averages_their_shares(lib):
    spec, v = linked_holmes(lib)
    c = ob.combined(v, spec, 5, "agent", min_freq=1)
    cfg = {"mode": "slices", "slice_by": "count", "n": 5}
    own = [ob.table(v, spec, b, cfg, "agent", min_freq=1) for b in ("alpha", "beta", "gamma")]
    assert [b["id"] for b in c["books"]] == ["alpha", "beta", "gamma"] and c["skipped"] == [] and c["n"] == 5 and c["per_book"] is None
    a = c["a"]
    for k in range(5):
        assert a["overview"][k]["mentions"] == sum(t["overview"][k]["mentions"] for t in own)
        assert a["overview"][k]["words"] == sum(t["overview"][k]["words"] for t in own) == a["segments"][k]["words"]
        assert a["overview"][k]["per1k"] == pytest.approx(sum(t["overview"][k]["per1k"] for t in own) / 3)
        assert [r["book"] for r in a["segments"][k]["ranges"]] == ["alpha", "beta", "gamma"]
        assert a["segments"][k]["ranges"][1] == {"book": "beta", "start": own[1]["segments"][k]["start"], "end": own[1]["segments"][k]["end"]}
    assert a["segments"][2]["pos"] == 40.0 and a["segments"][2]["label"] == "3/5"
    say = next(r for r in a["rows"] if r["item"] == "say")
    mine = [next((r for r in t["rows"] if r["item"] == "say"), None) for t in own]
    assert say["total"] == sum(r["total"] for r in mine if r) and say["counts"] == [sum(r["counts"][k] for r in mine if r) for k in range(5)]
    assert say["trend"]["n"] <= 3 and say["trend"]["up"] + say["trend"]["down"] == say["trend"]["n"]
    assert a["totals"] == [sum(t["totals"][k] for t in own) for k in range(5)]
    assert a["distinct"] == len(set().union(*({r["item"] for r in t["rows"]} for t in own)))


def test_each_books_own_values_come_with_a_figure(lib):
    spec, v = linked_holmes(lib)
    c = ob.combined(v, spec, 5, "agent", measure="word:agent:say")
    cfg = {"mode": "slices", "slice_by": "count", "n": 5}
    assert [b["id"] for b in c["per_book"]] == ["alpha", "beta", "gamma"] and c["per_book"][0]["title"] == v.title("alpha")
    for b in c["per_book"]:
        assert b["values"] == ob.curve(ob.table(v, spec, b["id"], cfg, "agent"), "word:agent:say")
    for m in ("ov:per1k", "rel:agent", "kind:communication"):
        assert len(ob.combined(v, spec, 5, "agent", measure=m)["per_book"][1]["values"]) == 5
    with pytest.raises(ValueError, match="Unknown figure"):
        ob.combined(v, spec, 5, measure="ov:nothing")
    with pytest.raises(ValueError, match="Unknown figure"):
        ob.combined(v, spec, 5, measure="word:nope:say")


def test_combined_words_of_the_curve_list_are_averaged_too(lib):
    spec, v = linked_holmes(lib)
    c = ob.combined(v, spec, 5, "mod", curve_rel="agent", min_freq=1)
    a, cw = c["a"], c["a"]["curve_words"]
    assert a["curve_rel"] == "agent" and cw["rel"] == "agent" and cw["totals"] == ob.combined(v, spec, 5, "agent")["a"]["totals"]
    same = ob.combined(v, spec, 5, "agent", min_freq=1)["a"]
    assert [(r["item"], [None if p is None else round(p, 3) for p in r["pcts"]]) for r in same["rows"]] == [(r["item"], r["pcts"]) for r in cw["rows"]]
    assert ob.curve(a, "word:agent:say") == next(r for r in cw["rows"] if r["item"] == "say")["pcts"]


def test_combined_refuses_and_says_when_nothing_is_there(lib):
    spec, v = linked_holmes(lib)
    for n in (1, 201):
        with pytest.raises(ValueError, match="between 2 and 200"):
            ob.combined(v, spec, n)
    with pytest.raises(ValueError, match="Unknown relation"):
        ob.combined(v, spec, 5, "nope")
    nowhere = ob.combined(v, {"kind": "unit", "id": "e:alpha:999"}, 5, measure="ov:per1k")
    assert nowhere["a"] is None and nowhere["books"] == [] and nowhere["per_book"] is None and len(nowhere["skipped"]) == 3
    only = ob.combined(v, {**spec, "books": ["beta", "gamma"]}, 5)
    assert [b["id"] for b in only["books"]] == ["beta", "gamma"] and [b["id"] for b in only["skipped"]] == ["alpha"]


def test_the_sentences_behind_a_slice_of_all_the_books(lib):
    """`within` takes the same slice of several books: its sentences are those of each book's own slice, counted together."""
    spec, v = linked_holmes(lib)
    c = ob.combined(v, spec, 5, "agent", min_freq=1)["a"]
    for word in ("say", "look"):
        row = next(r for r in c["rows"] if r["item"] == word)
        for k, sg in enumerate(c["segments"]):
            ev = v.evidence(spec, "agent", word, within=[(r["book"], r["start"], r["end"]) for r in sg["ranges"]])
            assert ev["total"] == row["counts"][k]
            assert {i["book"] for i in ev["items"]} <= {"alpha", "beta", "gamma"}
    assert v.evidence(spec, "agent", "say", within=[("alpha", 0, 10 ** 9), ("beta", 0, 10 ** 9), ("gamma", 0, 10 ** 9)])["total"] == v.evidence(spec, "agent", "say")["total"]
    assert v.evidence(spec, "agent", "say", within=[])["total"] == v.evidence(spec, "agent", "say")["total"]       # nothing asked: nothing left out


def test_the_word_frequency_setting_reaches_by_book_and_the_combined_route(lib, client):
    """Both routes read the Words setting on the server and say in their summary which way they counted."""
    spec, _ = linked_holmes(lib)
    body = {"books": ["alpha", "beta", "gamma"], "target": spec, "n": 5, "rel": "agent", "min_freq": 10}
    ask = lambda: (client.post("/api/bybook", json=body).json()["summary"], client.post("/api/overbook/combined", json=body).json()["a"]["summary"])
    together = ask()
    client.post("/api/settings", json={"freq_mode": "per_book"})
    each = ask()
    assert [s["each_book"] for s in together] == [False, False] and [s["each_book"] for s in each] == [True, True]
    assert each[0]["tested"] < together[0]["tested"]                                    # "wait" is 27 in all, but at most 13 in one book


def test_the_combined_route(client):
    books = ["alpha", "beta", "gamma"]
    units = client.post("/api/units", json={"books": books}).json()["rows"]
    holmes = next(r["id"] for r in units if r["name"] == "Holmes" and r["books"] == ["alpha"])
    body = {"books": books, "target": {"kind": "unit", "id": holmes}, "n": 6, "rel": "agent", "min_freq": 1}
    r = client.post("/api/overbook/combined", json=body)
    assert r.status_code == 200
    j = r.json()
    assert [b["id"] for b in j["books"]] == ["alpha"] and [b["id"] for b in j["skipped"]] == ["beta", "gamma"] and j["n"] == 6 and j["per_book"] is None
    assert len(j["a"]["segments"]) == 6 and j["a"]["rows"][0]["trend"]["n"] <= 1 and set(j["a"]["rows"][0]["trend"]) == {"z", "p", "n", "up", "down"}
    assert [b["id"] for b in client.post("/api/overbook/combined", json={**body, "curve": "ov:per1k"}).json()["per_book"]] == ["alpha"]
    assert client.post("/api/overbook/combined", json={k: v for k, v in body.items() if k != "n"}).json()["n"] == 20          # the default
    assert [client.post("/api/overbook/combined", json={**body, "n": n}).json()["n"] for n in (1, 201)] == [2, 200]       # held to 2-200, as elsewhere
    assert client.post("/api/overbook/combined", json={**body, "min_range": 2}).json()["a"]["summary"]["tested"] == 0        # Holmes is in one book only
    assert client.post("/api/overbook/combined", json={**body, "min_range": 0}).json()["a"]["summary"]["min_range"] == 1     # held to at least 1
    assert client.post("/api/overbook/combined", json={**body, "min_range": "two"}).status_code == 400
    for bad in ({"n": "many"}, {"rel": "bogus"}, {"curve_rel": "bogus"}, {"target": None}, {"curve": 3}, {"curve": "ov:nothing"}):
        assert client.post("/api/overbook/combined", json={**body, **bad}).status_code == 400, bad
    ev = {"books": books, "target": body["target"], "kind": "agent", "key": "say"}
    whole_book = client.post("/api/evidence", json=ev).json()["total"]
    both = [{"book": "alpha", "start": 0, "end": 10 ** 9}, {"book": "beta", "start": 0, "end": 10 ** 9}]
    assert client.post("/api/evidence", json={**ev, "within": both}).json()["total"] == whole_book
    for bad in ("x", [3], [{"book": "alpha"}], [{"book": "alpha", "start": 0, "end": 1}] * 501):
        assert client.post("/api/evidence", json={**ev, "within": bad}).status_code == 400, bad


def test_a_word_is_tested_only_in_enough_books():
    """`min_range`: the fewest books a word must occur in to be tested; others are listed without tests and don't count for Bonferroni."""
    a = [Counter({"both": 2 * i + 1, "one": 3, "o": 20}) for i in range(1, 7)]
    b = [Counter({"both": 12 - 2 * i, "o": 20}) for i in range(1, 7)]
    books = [ob._totalled(a), ob._totalled(b)]
    rows, summary = ob._series_books(books, 3, 0.05, True)
    assert {r["item"] for r in rows if r["tested"]} == {"both", "one", "o"} and summary["min_range"] == 1
    rows, summary = ob._series_books(books, 3, 0.05, True, min_range=2)
    assert {r["item"] for r in rows if r["tested"]} == {"both", "o"} and summary["tested"] == 2 and summary["threshold"] == 0.025
    one = next(r for r in rows if r["item"] == "one")
    assert one["trend"] is None and one["chi2"] is None and one["total"] == 18 and one["counts"] == [3] * 6       # listed, with its counts, but not tested
    assert not any(r["tested"] for r in ob._series_books(books, 3, 0.05, False, min_range=3)[0])


def test_combined_takes_the_minimum_number_of_books(lib):
    spec, v = linked_holmes(lib)
    every = ob.combined(v, spec, 5, "agent", min_freq=1)["a"]
    assert every["summary"]["min_range"] == 1 and every["summary"]["tested"] > 0
    three = ob.combined(v, spec, 5, "agent", min_freq=1, min_range=3)["a"]
    cfg = {"mode": "slices", "slice_by": "count", "n": 5}
    words_of = [{r["item"] for r in ob.table(v, spec, b, cfg, "agent")["rows"]} for b in ("alpha", "beta", "gamma")]
    in_all = set.intersection(*words_of)
    assert in_all and {r["item"] for r in three["rows"] if r["tested"]} == in_all                                      # tested exactly the words of every book
    assert three["summary"]["min_range"] == 3 and three["summary"]["tested"] <= every["summary"]["tested"]
    assert ob.combined(v, spec, 5, "agent", min_freq=1, min_range=4)["a"]["summary"]["tested"] == 0
    assert [r["counts"] for r in three["rows"]] == [r["counts"] for r in every["rows"]]                               # only the tests change


# ---------- the sound of the target's speech ----------
needs_dict = pytest.mark.skipif(not __import__("alex.core.sound", fromlist=["sound"]).available(), reason="cmudict isn't installed")


@needs_dict
def test_the_sound_of_speech_is_that_of_the_quotes_in_each_slice(view):
    from alex.core import prosody
    from alex.core.dialogue import bdlg
    cfg = prosody.config({})
    t = ob.table(view, spec_of(view), "alpha", SLICES, "agent", sound=cfg)
    find = ob.finder(t["segments"])
    per = [[] for _ in t["segments"]]
    for r in bdlg(view, "alpha")["recs"]:
        if r["speaker"] == HOLMES[1]:
            per[find(r["start"])].append(list(range(r["start"], r["end"] + 1)))
    bd = view.bd["alpha"]
    for o, units in zip(t["overview"], per):
        want = prosody.tally(bd, units) if units else None
        assert o["speech_words"] == (want["words"] if want else 0)
        assert (o["snd"] is None) == (not want or not want["words"])
        if o["snd"]:
            assert o["snd"]["stressed"] == pytest.approx(prosody.figures(want)["stressed"])
    assert ob.curve(t, "snd:stressed") == [o["snd"]["stressed"] if o["snd"] else None for o in t["overview"]]


@needs_dict
def test_without_sound_the_overview_has_none_and_its_curve_is_empty(view):
    t = ob.table(view, spec_of(view), "alpha", SLICES, "agent")
    assert "snd" not in t["overview"][0] and ob.curve(t, "snd:stressed") == [None] * len(t["segments"])


@needs_dict
def test_the_sound_of_speech_in_books_combined_is_the_mean_of_the_books(view):
    from alex.core import prosody
    cfg = prosody.config({})
    holmes = spec_of(view)
    c = ob.combined(view, holmes, 4, "agent", "snd:stressed", sound=cfg)
    own = {b: ob.table(view, holmes, b, {"mode": "slices", "slice_by": "count", "n": 4}, "agent", sound=cfg) for b in [x["id"] for x in c["books"]]}
    for k, o in enumerate(c["a"]["overview"]):
        got = [t["overview"][k]["snd"]["stressed"] for t in own.values() if t["overview"][k]["snd"]]
        assert o["speech_words"] == sum(t["overview"][k]["speech_words"] for t in own.values())
        assert (o["snd"] is None) == (not got) and (not got or o["snd"]["stressed"] == pytest.approx(sum(got) / len(got)))
    assert c["per_book"][0]["values"] == ob.curve(own[c["books"][0]["id"]], "snd:stressed")
    with pytest.raises(ValueError, match="Unknown figure"):
        ob.combined(view, holmes, 4, "agent", "snd:loudness", sound=cfg)


@needs_dict
def test_two_books_aligned_compare_the_sound_of_speech_too(view):
    from alex.core import prosody
    r = ob.aligned(view, spec_of(view), "alpha", None, None, 4, "agent", sound=prosody.config({}))
    assert "snd:stressed" in r["similarity"] and "snd:stressed" not in ob.aligned(view, spec_of(view), "alpha", None, None, 4, "agent")["similarity"]
