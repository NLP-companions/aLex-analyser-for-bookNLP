"""The cases of the Statistics tab (core/cases.py): text pieces and participants, their samples and the token lookup.

The answer keys are counted straight from each book's tokens, quotes, sentences and mentions, not through the code under test."""
from __future__ import annotations

import pytest

from alex.core import cases as cs
from alex.core import described as ds
from alex.core.corpus import cindex
from alex.core.narrative import book_segments
from alex.core.view import View

ALL = {"min": 0}                                             # keep every case with a sample


def unit(v, book, coref):
    """The unit id of a book's coreference group."""
    return v.member_unit[(book, coref)]


def words(bd, s, e, keep=lambda i: True):
    """The words between tokens s and e (inclusive) that `keep` accepts."""
    iw = cindex(bd)["isword"]
    return sum(1 for i in range(s, e + 1) if iw[i] and keep(i))


def quote_words(v, uid):
    """The words a unit speaks, from the quotes themselves: every quote whose speaker is one of its groups."""
    return sum(words(v.bd[b], q["start"], q["end"]) for b, c in v.units[uid].members for q in v.bd[b].quotes if q["char"] == c)


@pytest.fixture
def told(lib):
    """Alpha only, told by Watson (unit and coref 2); returns (view, Watson's unit id, Holmes's unit id)."""
    v = View(lib, ["alpha"])
    lib.ann_book("alpha")["narrator"] = unit(v, "alpha", 2)
    lib.save_ann()
    v = View(lib, ["alpha"])
    return v, unit(v, "alpha", 2), unit(v, "alpha", 1)


# ---------- text pieces ----------
def test_books_are_one_case_each_with_all_their_words(view):
    c = cs.build(view, {"kind": "pieces", "piece": "book", **ALL})
    assert [r["id"] for r in c.rows] == view.books and c.dropped == 0
    for r in c.rows:
        bd = view.bd[r["book"]]
        assert r["size"] == words(bd, 0, bd.n_tokens - 1) and r["label"] == view.title(r["book"])


def test_chapters_are_the_books_chapters_and_cover_every_word(view):
    c = cs.build(view, {"kind": "pieces", "piece": "chapter", **ALL})
    for b in view.books:
        segs = book_segments(view, b, {"mode": "chapters"})[0]
        mine = [r for r in c.rows if r["book"] == b]
        assert [(r["start"], r["end"]) for r in mine] == [(s["start"], s["end"]) for s in segs]
        assert sum(r["size"] for r in mine) == words(view.bd[b], 0, view.bd[b].n_tokens - 1)
        assert mine[0]["pos"] == 0 and mine[0]["index"] == 0 and mine[0]["label"].startswith(view.title(b) + " · ")


def test_slices_have_the_count_asked_for(view):
    c = cs.build(view, {"kind": "pieces", "piece": "slice", "n": 4, **ALL})
    assert len(c.rows) == 4 * len(view.books) and c.sample == "slice"


def test_a_token_is_in_the_piece_that_holds_it(view):
    c = cs.build(view, {"kind": "pieces", "piece": "chapter", **ALL})
    for i, r in enumerate(c.rows):
        at = c.at(r["book"])
        assert at(r["start"]) == (i,) and at(r["end"]) == (i,)


def test_a_scope_keeps_only_its_words(view):
    c = cs.build(view, {"kind": "pieces", "piece": "book", "scope": {"kind": "narration"}, **ALL})
    bd = view.bd["alpha"]
    in_quote = cindex(bd)["in_quote"]
    r = next(r for r in c.rows if r["book"] == "alpha")
    assert r["size"] == words(bd, 0, bd.n_tokens - 1, lambda i: not in_quote[i])
    inside = bd.quotes[0]["start"] + 1
    assert c.at("alpha")(inside) == () and c.at("alpha")(next(i for i in range(bd.n_tokens) if not in_quote[i])) == (0,)


def test_small_pieces_are_dropped_and_counted(view):
    c = cs.build(view, {"kind": "pieces", "piece": "slice", "n": 4, "min": 10 ** 6})
    assert c.rows == [] and c.dropped == 4 * len(view.books)
    assert cs.build(view, {"kind": "pieces"}).min == cs.DEFAULT_MIN["words"]


# ---------- participants ----------
def test_speech_is_the_words_of_their_quotes(view):
    c = cs.build(view, {"kind": "participants", "sample": "speech", **ALL})
    assert c.rows and c.unit == "words" and all(r["type"] == "PER" for r in c.rows)
    for r in c.rows:
        assert r["size"] == quote_words(view, r["id"])


def test_a_quote_token_belongs_to_its_speaker(told):
    v, w, h = told
    c = cs.build(v, {"kind": "participants", "sample": "speech", **ALL})
    bd, row = v.bd["alpha"], {r["id"]: i for i, r in enumerate(c.rows)}
    q = next(q for q in bd.quotes if q["char"] == 2)
    assert c.at("alpha")(q["start"] + 1) == (row[w],)
    outside = next(i for i in range(bd.n_tokens) if i not in bd.quote_at)
    assert c.at("alpha")(outside) == ()                                   # narration isn't speech


def test_speech_and_narration_joins_a_narrating_character(told):
    v, w, h = told
    c = cs.build(v, {"kind": "participants", "sample": "speech_narration", **ALL})
    bd = v.bd["alpha"]
    in_quote = cindex(bd)["in_quote"]
    row = next(r for r in c.rows if r["id"] == w)
    assert row["size"] == quote_words(v, w) + words(bd, 0, bd.n_tokens - 1, lambda i: not in_quote[i])
    i = c.rows.index(row)
    assert c.at("alpha")(next(t for t in range(bd.n_tokens) if not in_quote[t] and cindex(bd)["isword"][t])) == (i,)
    assert not any(r["type"] == "NARR" for r in c.rows)                   # Watson narrates: no separate role


def test_an_unnamed_narrator_takes_part_unless_left_out(lib):
    v = View(lib, ["beta"])
    c = cs.build(v, {"kind": "participants", "sample": "speech_narration", **ALL})
    role = next(r for r in c.rows if r["type"] == "NARR")
    assert role["id"] == "nar:anon:beta" and role["label"] == "Narrator of beta" and role["books"] == ["beta"]
    off = cs.build(v, {"kind": "participants", "sample": "speech_narration", "narrators": False, **ALL})
    assert not any(r["type"] == "NARR" for r in off.rows)


def test_sentences_mentioning_them(view):
    c = cs.build(view, {"kind": "participants", "sample": "sentences", **ALL})
    for r in c.rows[:4]:
        expected = 0
        for b, coref in view.units[r["id"]].members:
            bd = view.bd[b]
            sids = {bd.sent[bd.mentions[mi][1]] for mi in bd.groups[coref].mentions}
            expected += sum(words(bd, *bd.sent_bounds[s]) for s in sids)
        assert r["size"] == expected


def test_a_sentence_belongs_to_everyone_it_mentions(told):
    v, w, h = told
    c = cs.build(v, {"kind": "participants", "sample": "sentences", **ALL})
    bd, row = v.bd["alpha"], {r["id"]: i for i, r in enumerate(c.rows)}
    sents = [{bd.sent[bd.mentions[mi][1]] for mi in bd.groups[c].mentions} for c in (1, 2)]
    sid = min(sents[0] & sents[1])                                        # a sentence naming both
    assert set(c.at("alpha")(bd.sent_bounds[sid][0])) >= {row[w], row[h]}


def test_findings_are_counted_in_findings(told):
    v, w, h = told
    c = cs.build(v, {"kind": "participants", "sample": "findings", **ALL})
    assert c.unit == "findings" and c.at("alpha")(0) == ()
    i = next(i for i, r in enumerate(c.rows) if r["id"] == h)
    expected = sum(1 for k in ds.KINDS for _ in ds.findings(v, v.units[h].members, k))
    assert c.rows[i]["size"] == len(c.findings[i]) == expected
    assert cs.build(v, {"kind": "participants", "sample": "findings"}).min == cs.DEFAULT_MIN["findings"]


def test_the_population_is_any_spec(told):
    v, w, h = told
    c = cs.build(v, {"kind": "participants", "population": {"kind": "group", "ids": [w, h]}, **ALL})
    assert {r["id"] for r in c.rows} == {w, h}
    places = cs.build(v, {"kind": "participants", "sample": "sentences", "population": {"kind": "type", "type": "LOC"}, **ALL})
    assert places.rows and all(r["type"] == "LOC" for r in places.rows)


def test_dropped_participants_leave_the_lookup(told):
    v, w, h = told
    full = cs.build(v, {"kind": "participants", "sample": "speech", **ALL})
    small = min(full.rows, key=lambda r: r["size"])
    c = cs.build(v, {"kind": "participants", "sample": "speech", "min": small["size"] + 1})
    assert small["id"] not in {r["id"] for r in c.rows} and c.dropped >= 1
    bd = v.bd["alpha"]
    seen = {i for t in range(bd.n_tokens) for i in c.at("alpha")(t)}
    assert seen <= set(range(len(c.rows)))


def test_unknown_options_are_refused(view):
    for bad in ({"kind": "words"}, {"kind": "pieces", "piece": "page"}, {"kind": "participants", "sample": "mind"},
                {"kind": "pieces", "min": -1}, {"kind": "pieces", "min": "ten"}, {"kind": "pieces", "min": True},
                {"kind": "participants", "population": "everyone"}):
        with pytest.raises(ValueError):
            cs.build(view, bad)


def test_sentences_are_cases_with_a_minimum_of_one_word(view):
    c = cs.build(view, {"kind": "pieces", "piece": "sentence"})
    assert c.min == 1 and c.sample == "sentence"
    bd = view.bd["alpha"]
    mine = [r for r in c.rows if r["book"] == "alpha"]
    with_words = [(s, e) for s, e in sorted(bd.sent_bounds.values()) if words(bd, s, e)]
    assert [(r["start"], r["end"]) for r in mine] == with_words
    assert all(r["size"] == words(bd, r["start"], r["end"]) for r in mine)
    assert mine[0]["label"].startswith(view.title("alpha") + " · ") and mine[0]["index"] == 0
    i = c.rows.index(mine[3])
    assert c.at("alpha")(mine[3]["start"]) == (i,)


def test_sentences_in_a_scope_keep_only_their_words(view):
    c = cs.build(view, {"kind": "pieces", "piece": "sentence", "scope": {"kind": "dialogue"}})
    in_quote = cindex(view.bd["alpha"])["in_quote"]
    for r in (r for r in c.rows if r["book"] == "alpha"):
        assert r["size"] == words(view.bd["alpha"], r["start"], r["end"], lambda i: in_quote[i]) > 0


def test_equal_slices_are_the_default(view):
    c = cs.build(view, {"kind": "pieces", **ALL})
    assert c.sample == "slice" and len(c.rows) == 10 * len(view.books)


def test_slices_of_a_number_of_words(view):
    c = cs.build(view, {"kind": "pieces", "piece": "slice", "slice_by": "words", "words": 200, **ALL})
    for b in view.books:
        bd = view.bd[b]
        mine = [r for r in c.rows if r["book"] == b]
        total = words(bd, 0, bd.n_tokens - 1)
        assert mine[0]["start"] == 0 and mine[-1]["end"] == bd.n_tokens - 1                     # the whole book, without gaps
        assert all(a["end"] + 1 == z["start"] for a, z in zip(mine, mine[1:]))
        assert all(r["size"] == 200 for r in mine[:-1]) and 100 <= mine[-1]["size"] < 300         # the rest joins the last if under half
        assert len(mine) == max(1, total // 200 + (total % 200 >= 100))
        assert mine[0]["label"] == f"{view.title(b)} · 1/{len(mine)}"
    many = cs.build(view, {"kind": "pieces", "slice_by": "words", "words": 20, **ALL})          # more than the 200 slices a book allows by count
    assert len(many.rows) > len(c.rows)
    for bad in (5, 0, "200", True, 2_000_000):
        with pytest.raises(ValueError):
            cs.build(view, {"kind": "pieces", "slice_by": "words", "words": bad})
    with pytest.raises(ValueError):
        cs.build(view, {"kind": "pieces", "slice_by": "lines"})


def test_participants_must_be_in_enough_books(lib):
    """`min_range`: a person is a participant only if in at least that many of the selected books (linked across books, or one book only)."""
    person = lib.link(lib.link("e:alpha:1", "e:beta:5"), "e:gamma:3")
    v = View(lib, ["alpha", "beta", "gamma"])
    setup = {"kind": "participants", "sample": "speech", **ALL}
    every, two = cs.build(v, setup), cs.build(v, {**setup, "min_range": 2})
    assert person in [r["id"] for r in every.rows] and len(every.rows) > 1 and every.min_range == 1
    assert [r["id"] for r in two.rows] == [person] and two.min_range == 2 and two.summary()["min_range"] == 2
    assert two.dropped == every.dropped + len(every.rows) - 1 and {x["id"] for x in two.left_out} >= {r["id"] for r in every.rows} - {person}
    assert [r["size"] for r in two.rows] == [r["size"] for r in every.rows if r["id"] == person]                      # the sample itself is the same
    assert [r["id"] for r in cs.build(v, {**setup, "min_range": 3}, ["alpha"]).rows] == [person]                    # measured in one book, still in three
    assert cs.build(v, {**setup, "min_range": 4}).rows == []
    assert cs.build(v, {"kind": "pieces", "piece": "book", "min_range": 5, **ALL}).rows                          # text pieces don't have it
    for bad in (0, -1, "two", True, 10 ** 6):
        with pytest.raises(ValueError, match="minimum range"):
            cs.build(v, {**setup, "min_range": bad})
