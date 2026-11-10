"""The Sound and rhythm tab (core/soundtab.py): figures, cadences and runs of a part of the text, their examples, and the scansion."""
from __future__ import annotations

from collections import Counter

import pytest

from alex.core import prosody as P
from alex.core import sound
from alex.core import soundtab as T
from alex.core.corpus import Scope, cindex

pytestmark = pytest.mark.skipif(not sound.available(), reason="the optional cmudict package isn't installed")

CFG = P.config({})
SLICES = {"mode": "slices", "n": 4}


def whole_tally(view, b, scope=None):
    """Book b's tally in a scope, worked out here without the tab's keeping."""
    bd = view.bd[b]
    return P.count(bd, T.units(view, b, 0, bd.n_tokens - 1, Scope(view, scope)), CFG)


# ---------- units and tallies ----------
def test_narration_and_dialogue_split_the_words(view):
    bd, q = view.bd["alpha"], cindex(view.bd["alpha"])["in_quote"]
    narr = [t for u in T.units(view, "alpha", 0, bd.n_tokens - 1, Scope(view, {"kind": "narration"})) for t in u]
    dial = [t for u in T.units(view, "alpha", 0, bd.n_tokens - 1, Scope(view, {"kind": "dialogue"})) for t in u]
    assert narr and dial and not any(q[t] for t in narr) and all(q[t] for t in dial)
    words = lambda scope: whole_tally(view, "alpha", scope)["words"]
    assert words({"kind": "narration"}) + words({"kind": "dialogue"}) == words(None)


def test_the_kept_tallies_of_a_book_stay_within_their_budget(view):
    """Whole-book tallies under ever new settings: only the most recent few are kept (`KEPT_SPANS` times the book), and the one
    in use is found again without counting."""
    bd, n = view.bd["alpha"], view.bd["alpha"].n_tokens
    everything = Scope(view, None)
    for window in range(1, 3 * T.KEPT_SPANS):
        T.tally_of(view, "alpha", 0, n - 1, everything, {**CFG, "window": window})
    kept = bd.kept("soundtab")
    assert len(kept) == T.KEPT_SPANS and sum(e - s + 1 for s, e, *_ in kept.keys()) <= T.KEPT_SPANS * n
    newest = kept.keys()[-1]
    assert T.tally_of(view, "alpha", 0, n - 1, everything, {**CFG, "window": 3 * T.KEPT_SPANS - 1}) is kept.get(newest, None)

def test_one_speakers_units_are_their_quotes(view):
    holmes = {"kind": "unit", "id": view.member_unit[("alpha", 1)]}
    scope = Scope(view, {"kind": "speech", "speaker": holmes})
    bd, ci = view.bd["alpha"], cindex(view.bd["alpha"])
    toks = [t for u in T.units(view, "alpha", 0, bd.n_tokens - 1, scope) for t in u]
    assert toks and all(1 in bd.stands_for(ci["speaker"][t]) for t in toks)
    assert scope.speaker_groups("alpha") == frozenset({1}) and Scope(view, None).speaker_groups("alpha") == frozenset()


def test_a_stretch_is_tallied_once_per_scope_and_setting(view):
    bd, scope = view.bd["alpha"], Scope(view, {"kind": "narration"})
    t = T.tally_of(view, "alpha", 0, 300, scope, CFG)
    assert T.tally_of(view, "alpha", 0, 300, Scope(view, {"kind": "narration"}), CFG) is t
    assert T.tally_of(view, "alpha", 0, 300, Scope(view, None), CFG) is not t
    assert T.tally_of(view, "alpha", 0, 300, scope, P.config({"sound": {"window": 8}})) is not t
    assert "found" in t and "cadences_at" in t


# ---------- figures ----------
def test_the_whole_text_has_the_style_pages_figures(view):
    mine = T.figures(view, SLICES, "segment", None, CFG)["rows"]
    style = P.table(view, SLICES, "segment", CFG)["rows"]
    assert [(r["book"], r["label"], r["words"]) for r in mine] == [(r["book"], r["label"], r["words"]) for r in style]
    assert all(a["npvi"] == pytest.approx(b["npvi"]) for a, b in zip(mine, style) if a["npvi"] is not None)


def test_figures_of_narration(view):
    rows = T.figures(view, None, "book", {"kind": "narration"}, CFG)["rows"]
    for r in rows:
        assert r["words"] == whole_tally(view, r["book"], {"kind": "narration"})["words"]


# ---------- cadences ----------
def test_cadences_add_up_and_are_named(view):
    r = T.cadences(view, None, CFG)
    every = sum((whole_tally(view, b)["cadences"] for b in view.books), start=Counter())
    assert r["phrase_ends"] == sum(every.values()) and {x["pattern"]: x["n"] for x in r["rows"]} == dict(every)
    assert sum(x["n"] for x in r["types"].values()) == r["phrase_ends"]
    assert T.marks("10010") == "/ x x / x" and all(x["type"] == P.cadence_type(x["pattern"]) for x in r["rows"])


def test_the_phrases_of_a_cadence(view):
    r = T.cadences(view, None, CFG)
    top = r["rows"][0]
    ex = T.cadence_examples(view, None, CFG, top["pattern"])
    assert ex["total"] == top["n"] and ex["shown"] == min(top["n"], T.MAX_EXAMPLES)
    assert T.cadence_examples(view, None, CFG, top["pattern"], end_only=True)["total"] == top["ends"]
    assert all("\x01k\x02" in e["text"] for e in ex["items"])
    for bad in ("", "12", None, "x/x"):
        with pytest.raises(ValueError, match="pattern"):
            T.cadence_examples(view, None, CFG, bad)


# ---------- runs ----------
@pytest.mark.parametrize("kind", P.RUNS)
def test_runs_by_what_they_share_add_up(view, kind):
    r = T.runs(view, None, CFG, kind)
    tallies = [whole_tally(view, b) for b in view.books]
    assert r["runs"] == sum(t[kind + "_runs"] for t in tallies) == sum(x["runs"] for x in r["rows"])
    assert r["words"] == sum(t[kind + "_words"] for t in tallies) and r["eligible"] == sum(t[kind + "_eligible"] for t in tallies)
    if r["rows"]:
        top = r["rows"][0]
        ex = T.run_examples(view, None, CFG, kind, top["key"])
        assert ex["total"] == top["runs"]
        lengths = [len(e["words"]) for e in ex["items"]]
        assert lengths == sorted(lengths, reverse=True) and lengths[0] == top["longest"]
        own = "\x01rep\x02" if kind == "repetition" else "\x01k\x02"
        assert all(e["text"].count(own) >= len(e["words"]) for e in ex["items"])


def test_repetitions_are_marked_in_sound_runs(view):
    wide = P.config({"sound": {"window": 12, "boundary": "none"}})
    rows = T.runs(view, None, wide, "alliteration")["rows"]
    marked = [e for r in rows[:5] for e in T.run_examples(view, None, wide, "alliteration", r["key"])["items"]]
    assert any("\x01rep\x02" in e["text"] for e in marked)


def test_unknown_kinds_are_refused(view):
    with pytest.raises(ValueError, match="kind of run"):
        T.runs(view, None, CFG, "metre")


# ---------- scansion ----------
def test_a_slice_word_by_word(view):
    r = T.scan(view, "alpha", SLICES, 1, None, CFG)
    bd = view.bd["alpha"]
    assert r["label"] == "2/4" and len(r["segments"]) == 4 and not r["cut"]
    assert [x["t"] for x in r["tokens"]] == list(range(r["start"], r["end"] + 1))
    prons = sound.book_prons(bd)
    for x in r["tokens"]:
        p = prons[x["t"]]
        assert x.get("m") == (p.stress if p is not None and p is not sound.JOINED and cindex(bd)["isword"][x["t"]] else None)
    assert all(r["start"] <= t <= r["end"] for run in r["runs"] for t in run["toks"])
    assert all(c["first"] <= c["last"] for c in r["cadences"])
    assert r["words"] == T.tally_of(view, "alpha", r["start"], r["end"], Scope(view, None), CFG)["words"]


def test_a_scan_marks_what_is_outside_the_scope_and_is_cut(view, monkeypatch):
    r = T.scan(view, "alpha", SLICES, 0, {"kind": "dialogue"}, CFG)
    q = cindex(view.bd["alpha"])["in_quote"]
    assert all(x.get("out", False) == (not q[x["t"]]) for x in r["tokens"])
    monkeypatch.setattr(T, "MAX_SCAN_WORDS", 50)
    cut = T.scan(view, "alpha", SLICES, 0, None, CFG)
    assert cut["cut"] and sum(cindex(view.bd["alpha"])["isword"][x["t"]] for x in cut["tokens"]) == 50


def test_a_scan_refuses_what_isnt_there(view, monkeypatch):
    with pytest.raises(ValueError, match="4 chapters or slices"):
        T.scan(view, "alpha", SLICES, 9, None, CFG)
    with pytest.raises(ValueError, match="isn't in the selection"):
        T.scan(view, "nowhere", SLICES, 0, None, CFG)
    monkeypatch.setattr(sound, "available", lambda: False)
    with pytest.raises(RuntimeError, match=r"\[sound\]"):
        T.cadences(view, None, CFG)


# ---------- pronunciations ----------
def test_the_guessed_words_most_frequent_first(view):
    r = T.guessed(view, CFG)
    counts = Counter()
    for b in view.books:
        bd = view.bd[b]
        for i, p in enumerate(sound.book_prons(bd)):
            if cindex(bd)["isword"][i] and p is not None and p is not sound.JOINED and p.source == "guess":
                counts[sound.norm(bd.word[i])] += 1
    assert [(x["word"], x["n"]) for x in r["rows"]] == counts.most_common() and r["guessed"] == sum(counts.values())
    assert r["yours"] == [] and r["corrected"] == 0 and r["words"] == sum(view.bd[b].n_words for b in view.books)
    first = r["rows"][0]
    assert view.bd[first["book"]].word[first["tok"]].lower() == first["word"]


def test_a_corrected_word_leaves_the_guessed_list(view):
    word = T.guessed(view, CFG)["rows"][0]
    mine = P.config({"sound": {"corrections": {word["word"]: "0 1"}}})
    r = T.guessed(view, mine)
    assert word["word"] not in [x["word"] for x in r["rows"]]
    assert r["yours"] == [{"word": word["word"], "text": "0 1", "stress": "01", "n": word["n"]}] and r["corrected"] == word["n"]


def test_looking_a_word_up(view):
    r = T.lookup("Baskerville", CFG, "PROPN")
    assert r == {"word": "baskerville", "source": "dict", "stress": "101", "text": "B AE1 S K ER0 V IH2 L", "variants": ["B AE1 S K ER0 V IH2 L"]}
    mine = T.lookup("Grimpen", P.config({"sound": {"corrections": {"grimpen": "x/"}}}))
    assert mine["source"] == "yours" and mine["stress"] == "01" and mine["text"] == "0 1"
    assert T.lookup("Grimpen", CFG)["source"] == "guess" and T.lookup("Grimpen", CFG)["variants"] == []
    with pytest.raises(ValueError, match="one word"):
        T.lookup("two words", CFG)
