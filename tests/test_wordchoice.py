"""Word-choice figures (core/wordchoice.py): tallies of parts of speech and noun and verb supersenses, and the figures taken from them.

The answer keys are the Style page's POS profile (`narrative.style_metrics`), the book's own supersense spans, and hand-made tallies."""
from __future__ import annotations

from collections import Counter

import pytest

from alex.core import narrative as nr
from alex.core import wordchoice as wc
from alex.core.corpus import cindex


def made(words=0, pos=(), verbs=(), nouns=()):
    """A tally made by hand: the words, and {part of speech: n}, {verb category: n}, {noun category: n} pairs."""
    t = wc.empty()
    t["words"] = words
    t["pos"].update(dict(pos))
    t["verbs"].update(dict(verbs))
    t["nouns"].update(dict(nouns))
    return t


def span_starts(bd, kind):
    """Span starts of one kind ("verb" or "noun") straight from the book: {category name: count}."""
    return Counter(c.partition(".")[2] for i, c in bd.ss.items() if c.startswith(kind + ".") and bd.ss.get(i - 1) != c)


def whole(bd):
    """The tally of every token of a book."""
    return wc.tally(bd, range(bd.n_tokens))


# ---------- tallies ----------
def test_parts_of_speech_equal_the_style_profile(view):
    for b in view.books:
        bd = view.bd[b]
        profile = nr.style_metrics(bd, 0, bd.n_tokens - 1)["pos"]
        out = wc.figures(whole(bd))
        for p in profile:
            assert out[f"pos:{p}"] == pytest.approx(profile[p])


def test_only_words_are_counted_as_words(view):
    bd = view.bd["alpha"]
    t = whole(bd)
    assert t["words"] == cindex(bd)["n_words"] < bd.n_tokens
    assert sum(t["pos"].values()) == t["words"]


def test_supersense_spans_are_counted_once_where_they_start(view):
    bd = view.bd["alpha"]
    t = whole(bd)
    for kind, found in (("verb", t["verbs"]), ("noun", t["nouns"])):
        assert found == span_starts(bd, kind) and sum(found.values()) > 0


def test_a_span_counts_only_if_it_starts_in_the_sample(view):
    bd = view.bd["alpha"]
    start = next(i for i, c in bd.ss.items() if bd.ss.get(i - 1) != c)
    assert sum(wc.tally(bd, [start])["verbs"].values()) + sum(wc.tally(bd, [start])["nouns"].values()) == 1
    follower = next((i for i, c in bd.ss.items() if bd.ss.get(i - 1) == c), None)      # a span's later token starts nothing
    if follower is not None:
        t = wc.tally(bd, [follower])
        assert not t["verbs"] and not t["nouns"]


def test_tallies_add_up(view):
    bd = view.bd["alpha"]
    half = bd.n_tokens // 2
    a, b = wc.tally(bd, range(half)), wc.tally(bd, range(half, bd.n_tokens))
    both = wc.add(a, b)
    assert both == whole(bd)
    assert a == wc.tally(bd, range(half))                     # adding changed neither


def test_an_empty_sample_has_no_figures(view):
    t = wc.tally(view.bd["alpha"], [])
    assert t == wc.empty()
    assert set(wc.figures(t).values()) == {None}


# ---------- figures ----------
def test_parts_of_speech_are_shares_of_words():
    out = wc.figures(made(50, pos={"ADJ": 5, "VERB": 10}))
    assert out["pos:ADJ"] == 10 and out["pos:VERB"] == 20 and out["pos:NOUN"] == 0


def test_ratios():
    out = wc.figures(made(100, pos={"ADJ": 6, "ADV": 2, "NOUN": 20, "PROPN": 9, "VERB": 4, "AUX": 7}))
    assert out["ratio:adj_verb"] == 1.5 and out["ratio:adv_verb"] == 0.5
    assert out["ratio:noun_verb"] == 5                          # proper nouns and auxiliaries are not counted
    assert out["ratio:mod_head"] == pytest.approx(8 / 24)


def test_a_ratio_without_its_divisor_is_none():
    out = wc.figures(made(10, pos={"ADJ": 3}))
    assert out["ratio:adj_verb"] is None and out["ratio:noun_verb"] is None and out["ratio:mod_head"] is None
    assert wc.figures(made(10, pos={"ADJ": 3, "NOUN": 1}))["ratio:mod_head"] == 3     # one divisor part is enough


def test_verb_groups_cover_every_verb_category_once():
    assert wc.DYNAMIC | wc.STATIC == set(wc.VERB_SS) and not wc.DYNAMIC & wc.STATIC
    assert wc.DYNAMIC == {"motion", "contact", "change", "body", "creation", "competition", "consumption", "weather"}


def test_dynamic_and_static_verbs_add_up_to_everything():
    out = wc.figures(made(100, verbs={"motion": 3, "contact": 1, "stative": 4, "cognition": 2}))
    assert out["verbs:dynamic"] == 40 and out["verbs:static"] == 60
    assert out["verb:motion"] == 30 and out["verb:stative"] == 40 and out["verb:weather"] == 0


def test_supersenses_per_thousand_words_and_shares_of_nouns():
    out = wc.figures(made(200, nouns={"person": 6, "artifact": 2}, verbs={"motion": 1}))
    assert out["ss:noun.person"] == 30 and out["ss:verb.motion"] == 5
    assert out["noun:person"] == 75 and out["noun:artifact"] == 25


def test_shares_of_verbs_and_nouns_are_none_without_any():
    out = wc.figures(made(100, pos={"ADJ": 1}))
    assert out["verbs:dynamic"] is None and out["verb:motion"] is None and out["noun:person"] is None
    assert out["ss:verb.motion"] == 0 and out["pos:ADJ"] == 1


def test_figure_names():
    assert wc.is_figure("ratio:adj_verb") and wc.is_figure("ss:noun.Tops") and wc.is_figure("verbs:static")
    assert not wc.is_figure("pos:XYZ") and not wc.is_figure(None) and not wc.is_figure(["pos:ADJ"])
    assert set(wc.figures(wc.empty())) == set(wc.FIGURES)
    assert wc.label("ratio:adj_verb") == "Adjectives per verb" and wc.value(made(4, pos={"ADJ": 1}), "pos:ADJ") == 25
    assert len(wc.FIGURES) == len(set(wc.FIGURES))


def test_one_figure_is_the_same_as_taking_them_all(view):
    t = whole(view.bd["alpha"])
    out = wc.figures(t)
    assert set(out) == set(wc.FIGURES) and any(v is not None and v > 0 for v in out.values())
    assert all(wc.value(t, k) == v for k, v in out.items())
