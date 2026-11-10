"""Narrative: segments, arcs, style, stylometry, sentiment and lexicon arcs."""
from __future__ import annotations

import pytest

from alex.core import narrative as nar
from alex.core import wordchoice
from alex.core.library import Library
from alex.core.view import View

CHAPTERS = {"alpha": 4, "beta": 3, "gamma": 2}
CHAPTER_CFG = {"mode": "chapters", "min_words": 50, "rules": {"numbered": True, "caps": True, "short": False}}
SLICES = {"mode": "slices", "n": 10}


# ---------- segments ----------
def test_slices_divide_each_book_into_equal_token_counts(view):
    segs, info = nar.all_segments(view, SLICES)
    assert len(segs) == 30 and all(i == {"mode": "slices", "fallback": False} for i in info.values())
    for b in view.books:
        mine = [s for s in segs if s["book"] == b]
        assert mine[0]["start"] == 0 and mine[-1]["end"] == view.bd[b].n_tokens - 1
        assert all(a["end"] + 1 == c["start"] for a, c in zip(mine, mine[1:]))
        assert sum(s["words"] for s in mine) == view.bd[b].n_words
        assert max(s["end"] - s["start"] for s in mine) - min(s["end"] - s["start"] for s in mine) <= 1


def test_slices_by_words_cut_every_n_words(view):
    segs, info = nar.all_segments(view, {"mode": "slices", "slice_by": "words", "words": 100})
    assert all(i == {"mode": "slices", "fallback": False} for i in info.values())
    for b in view.books:
        mine = [s for s in segs if s["book"] == b]
        n_words = view.bd[b].n_words
        assert mine[0]["start"] == 0 and mine[-1]["end"] == view.bd[b].n_tokens - 1
        assert all(a["end"] + 1 == c["start"] for a, c in zip(mine, mine[1:]))
        assert sum(s["words"] for s in mine) == n_words
        assert all(s["words"] == 100 for s in mine[:-1])                           # every slice but the last has exactly that many
        assert 50 <= mine[-1]["words"] < 150 or n_words < 100                      # a rest under half joins it, else it stands alone
        assert [s["label"] for s in mine] == [f"{k + 1}/{len(mine)}" for k in range(len(mine))]


def test_a_short_rest_joins_the_last_slice_and_a_long_one_stands_alone(view):
    bd = view.bd["alpha"]
    n = bd.n_words
    for per in (n // 3 + 1, n // 3 - 1, n + 5):                                    # rests of different sizes, and a slice longer than the book
        segs = nar.word_slices(bd, per)
        rest = n - per * (n // per)
        expected = max(1, n // per + (1 if rest >= per / 2 else 0)) if n >= per else 1
        assert len(segs) == expected and sum(s["words"] for s in segs) == n
    assert len(nar.word_slices(bd, n + 5)) == 1


def test_word_slices_are_the_same_in_statistics_and_arcs(view):
    from alex.core import cases as cs
    built = cs.build(view, {"kind": "pieces", "piece": "slice", "slice_by": "words", "words": 100, "min": 0})
    mine = [r for r in built.rows if r["book"] == "alpha"]
    segs = nar.word_slices(view.bd["alpha"], 100)
    assert [(r["start"], r["end"]) for r in mine] == [(s["start"], s["end"]) for s in segs]


def test_word_slices_ignore_the_corpus_share_and_serve_a_book_without_chapters(view):
    a, _ = nar.all_segments(view, {"mode": "slices", "slice_by": "words", "words": 100, "scope": "corpus", "n": 12})
    b, _ = nar.all_segments(view, {"mode": "slices", "slice_by": "words", "words": 100})
    assert [(s["book"], s["start"]) for s in a] == [(s["book"], s["start"]) for s in b]
    cfg = {"mode": "chapters", "min_words": 10 ** 6, "slice_by": "words", "words": 100}   # no chapter is long enough: slices of 100 words instead
    segs, info = nar.all_segments(view, cfg)
    assert all(i["fallback"] for i in info.values()) and all(s["words"] == 100 for s in segs if s["book"] == "alpha" and s["index"] == 0)
    with pytest.raises(ValueError, match="whole number"):
        nar.all_segments(view, {"slice_by": "words", "words": "many"})
    assert nar.all_segments(view, {"slice_by": "words", "words": 1})[0][0]["words"] == 20      # held to the smallest allowed


def test_corpus_scope_shares_slices_by_each_books_words(view):
    """"Whole corpus" timeline: the slice count is a total shared out by each book's words, not repeated per book."""
    segs, info = nar.all_segments(view, {**SLICES, "scope": "corpus", "n": 12})
    assert all(i == {"mode": "slices", "fallback": False} for i in info.values())
    counts = {b: len([s for s in segs if s["book"] == b]) for b in view.books}
    assert abs(sum(counts.values()) - 12) <= len(view.books)   # rounding each book's share may add or drop a couple
    assert all(n >= 1 for n in counts.values())
    words = {b: view.bd[b].n_words for b in view.books}
    longest = max(words, key=words.get)
    assert counts[longest] == max(counts.values())             # the longest book gets no fewer slices than any other
    for b in view.books:
        mine = [s for s in segs if s["book"] == b]
        assert sum(s["words"] for s in mine) == view.bd[b].n_words    # still covers the whole book


def test_corpus_scope_has_no_effect_on_one_book_or_on_chapters(view, lib):
    one = View(lib, ["alpha"])
    assert len(nar.all_segments(one, {**SLICES, "scope": "corpus"})[0]) == 10        # one book: same as "book" scope
    with_scope, _ = nar.all_segments(view, {**CHAPTER_CFG, "scope": "corpus"})
    without, _ = nar.all_segments(view, CHAPTER_CFG)
    assert [s["start"] for s in with_scope] == [s["start"] for s in without]         # chapters aren't found differently


def test_chapters_start_at_headings(view, truth):
    segs, info = nar.all_segments(view, CHAPTER_CFG)
    for b, n in CHAPTERS.items():
        mine = [s for s in segs if s["book"] == b]
        assert len(mine) == n and info[b]["mode"] == "chapters" and not info[b]["fallback"]
        assert mine[0]["label"].startswith("CHAPTER") and mine[0]["start"] == 0
        assert mine[-1]["end"] == view.bd[b].n_tokens - 1
        assert sum(s["words"] for s in mine) == view.bd[b].n_words


def test_short_chapters_are_ignored_and_books_fall_back_to_slices(view):
    segs, info = nar.all_segments(view, {**CHAPTER_CFG, "min_words": 5000, "n": 5})
    assert all(i["fallback"] for i in info.values()) and len(segs) == 15


def test_heading_rules_can_be_switched_off(view):
    segs, info = nar.all_segments(view, {**CHAPTER_CFG, "rules": {"numbered": False, "caps": False, "short": False}, "n": 4})
    assert all(i["fallback"] for i in info.values())


def test_locate_finds_the_segment_of_a_token(view):
    segs, _ = nar.all_segments(view, SLICES)
    idx = nar.segment_index(segs)
    for k, s in enumerate(segs):
        assert nar.locate(idx, s["book"], s["start"]) == k and nar.locate(idx, s["book"], s["end"]) == k
    assert nar.locate(idx, "alpha", -5) is None


# ---------- arcs ----------
def test_entity_arcs_add_up_to_the_mentions(view, truth):
    h = view.member_unit[("alpha", 1)]
    r = nar.arcs(view, SLICES, "entities", [h, "bogus"])
    (s,) = r["series"]
    assert sum(s["counts"][:10]) == truth["alpha"].mentions[(1, "PROP")] + truth["alpha"].mentions[(1, "PRON")]
    assert s["counts"][10:] == [None] * 20 and s["values"][10:] == [None] * 20 and s["books"] == ["alpha"]   # other books: a gap, not 0
    assert all(v == pytest.approx(1000 * c / seg["words"]) for v, c, seg in zip(s["values"][:10], s["counts"][:10], r["segments"]))


def test_event_supersense_and_dialogue_arcs(view, truth):
    ev = nar.arcs(view, SLICES, "events")["series"][0]
    assert sum(ev["counts"]) == sum(sum(view.bd[b].event) for b in view.books)
    ss = nar.arcs(view, SLICES, "supersenses")
    assert ss["series"] and {x["item"] for x in ss["info"]["available"]} >= {"verb.communication", "noun.artifact"}
    said = nar.arcs(view, SLICES, "supersenses", cats=["verb.communication"])["series"][0]
    assert sum(said["counts"]) == sum(sum(t.quotes.values()) for t in truth.values())
    dia = nar.arcs(view, SLICES, "dialogue")["series"][0]
    assert sum(dia["counts"]) == sum(t.dialogue_words for t in truth.values())
    assert all(0 <= v <= 100 for v in dia["values"])


def test_books_combined_puts_the_books_together_slice_by_slice(view):
    """Timeline "Books combined": slice k of every book together, each book weighing the same (the mean of their own values);
    a series with no value in a book (an entity of another book) leaves that book out; counts add up; `each` keeps every book's line."""
    cfg = {**SLICES, "scope": "combined"}
    by_book = nar.arcs(view, cfg, "dialogue")
    comb = nar.timeline(by_book, cfg, each=True)
    assert len(comb["segments"]) == 10 and comb["info"]["combined"] == {"n": 10, "books": list(view.books)}
    assert [sg["label"] for sg in comb["segments"][:2]] == ["1/10", "2/10"] and comb["segments"][0]["words"] == sum(sg["words"] for sg in by_book["segments"] if sg["index"] == 0)
    s0, c0 = by_book["series"][0], comb["series"][0]
    for k in range(10):
        own = [s0["values"][i] for i, sg in enumerate(by_book["segments"]) if sg["index"] == k]
        assert c0["values"][k] == pytest.approx(sum(own) / len(own))                     # every book weighs the same
    assert sum(c0["counts"]) == sum(s0["counts"])
    assert [e["book"] for e in c0["each"]] == list(view.books) and len(c0["each"][0]["values"]) == 10
    h = view.member_unit[("alpha", 1)]
    ent = nar.timeline(nar.arcs(view, cfg, "entities", [h]), cfg)["series"][0]
    alone = nar.arcs(view, SLICES, "entities", [h])["series"][0]
    assert ent["values"] == pytest.approx(alone["values"][:10]) and "each" not in ent      # only its own book: the others are left out
    chapters = nar.arcs(view, {**CHAPTER_CFG, "scope": "combined"}, "dialogue")
    same = nar.timeline(chapters, {**CHAPTER_CFG, "scope": "combined"})
    assert same["info"]["combined"] is None and same["segments"] == chapters["segments"]   # chapters can't be lined up
    assert nar.timeline(by_book, SLICES) is by_book                                          # other timelines: untouched


def test_unknown_arc_kind_is_empty(view):
    assert nar.arcs(view, SLICES, "nonsense")["series"] == []


# ---------- style ----------
def test_style_metrics_match_the_generator(view, truth):
    rows = {r["book"]: r for r in nar.style(view, SLICES)["rows"]}
    for b, t in truth.items():
        r = rows[b]
        assert r["words"] == t.words and r["sentences"] == t.sentences
        assert r["sent_len"] == pytest.approx(t.words / t.sentences)
        assert r["dialogue"] == pytest.approx(100 * t.dialogue_words / t.words)
        assert r["questions"] == 0 and r["passive"] == 0
        assert r["mattr_ok"] and 0 < r["mattr"] < 1 and 0 <= r["hapax"] <= 100
        assert sum(r["pos"].values()) <= 100 + 1e-9
        assert r["flesch"] == pytest.approx(206.835 - 1.015 * r["sent_len"] - 84.6 * (r["flesch"] and (206.835 - 1.015 * r["sent_len"] - r["flesch"]) / 84.6))


def test_style_by_segment_has_one_row_per_segment(view):
    r = nar.style(view, CHAPTER_CFG, by="segment")
    assert len(r["rows"]) == 9 and {x["label"][:7] for x in r["rows"]} == {"CHAPTER"}
    assert sum(x["words"] for x in r["rows"]) == sum(view.bd[b].n_words for b in view.books)


def test_word_choice_per_book_is_the_style_profile_and_the_statistics_tabs(view):
    from alex.core import cases as cs
    from alex.core import layers
    t = wordchoice.table(view, SLICES, "book")
    style = {r["book"]: r for r in nar.style(view, SLICES)["rows"]}
    books = cs.build(view, {"kind": "pieces", "piece": "book", "min": 0})
    stats = {r["book"]: v for r, v in zip(books.rows, layers.word_choice(view, books, "ratio:adj_verb"))}
    assert [r["book"] for r in t["rows"]] == view.books
    for r in t["rows"]:
        for pos, share in style[r["book"]]["pos"].items():
            assert r[f"pos:{pos}"] == pytest.approx(share)
        assert r["ratio:adj_verb"] == stats[r["book"]] and r["words"] == style[r["book"]]["words"]
        assert r["verbs:dynamic"] + r["verbs:static"] == pytest.approx(100)
    assert {c["id"] for c in t["choices"]} >= {"", "headline", "ratios"} and [s["id"] for s in t["sections"]][0] == "parts"


def test_word_choice_by_segment_has_one_row_per_segment_and_adds_up(view):
    t = wordchoice.table(view, CHAPTER_CFG, "segment")
    assert len(t["rows"]) == 9 and sum(x["words"] for x in t["rows"]) == sum(view.bd[b].n_words for b in view.books)
    whole = {r["book"]: r for r in wordchoice.table(view, CHAPTER_CFG, "book")["rows"]}
    for b in view.books:       # a book's adjective share is its chapters' shares weighted by their words
        rows = [r for r in t["rows"] if r["book"] == b]
        mixed = sum(r["pos:ADJ"] * r["words"] for r in rows) / sum(r["words"] for r in rows)
        assert whole[b]["pos:ADJ"] == pytest.approx(mixed)
    assert wordchoice.table(view, CHAPTER_CFG, "segment")["rows"][0]["index"] is not None


# ---------- stylometry ----------
def test_stylometry_of_whole_books(view):
    r = nar.stylometry(view, SLICES, "books", mfw=30)
    assert [t["book"] for t in r["texts"]] == ["alpha", "beta", "gamma"]
    D = r["matrix"]
    assert all(D[i][i] == 0 for i in range(3)) and all(D[i][j] == D[j][i] for i in range(3) for j in range(3))
    leaves = []
    walk = lambda t: [walk(c) for c in t["children"]] if "children" in t else leaves.append(t["leaf"])
    walk(r["tree"])
    assert sorted(leaves) == [0, 1, 2] and r["tree"]["size"] == 3
    assert 0 < r["variance"][0] <= 1 and len(r["loadings"]) == 2 and len(r["nearest"]) == 3
    assert all(len(n["nearest"]) == 2 for n in r["nearest"])


@pytest.mark.parametrize("measure", ["cosine", "classic", "euclidean"])
@pytest.mark.parametrize("linkage", ["average", "complete", "ward"])
def test_stylometry_measures_and_linkages_run(view, measure, linkage):
    r = nar.stylometry(view, SLICES, "books", mfw=20, measure=measure, linkage=linkage)
    assert "error" not in r and all(d >= 0 for row in r["matrix"] for d in row)


def test_stylometry_scope_and_pronoun_options(view):
    narr = nar.stylometry(view, SLICES, "books", mfw=40, scope="narration", exclude_pronouns=True)
    assert not ({"he", "i"} & set(narr["words"]))
    dia = nar.stylometry(view, SLICES, "books", mfw=40, scope="dialogue")
    assert "said" not in dia["words"] and set(dia["words"]) & {"see", "look"}


def test_stylometry_needs_three_texts(lib):
    r = nar.stylometry(View(lib, ["alpha", "beta"]), SLICES)
    assert "at least three" in r["error"]
    seg = nar.stylometry(View(lib, ["alpha", "beta"]), CHAPTER_CFG, "segments", mfw=20)
    assert "error" not in seg and len(seg["texts"]) == 7


def test_stylometry_needs_enough_words(view):
    r = nar.stylometry(view, SLICES, "books", mfw=0)
    assert "texts" in r and r["mfw"] == 2                       # too small a request is raised to two words
    r = nar.stylometry(view, SLICES, "books", mfw=20, culling=100)
    assert "texts" in r and r["mfw"] > 0


def test_stylometry_refuses_an_unmanageable_number_of_texts(view, monkeypatch):
    monkeypatch.setattr(nar, "MAX_TEXTS", 2)
    assert "at most 2 texts" in nar.stylometry(view, SLICES, "books")["error"]


def test_cluster_orders_merges_by_distance():
    D = [[0, 1, 5, 6], [1, 0, 5, 6], [5, 5, 0, 2], [6, 6, 2, 0]]
    for linkage in ("average", "complete", "ward"):
        tree = nar.cluster(D, linkage)
        first_pair = sorted(sorted(c["leaf"] for c in t["children"]) for t in _nodes(tree) if all("leaf" in c for c in t["children"]))
        assert first_pair == [[0, 1], [2, 3]]
        assert tree["size"] == 4 and tree["height"] > 0
    avg = nar.cluster(D, "average")
    assert avg["height"] == pytest.approx((5 + 5 + 6 + 6) / 4)
    assert nar.cluster(D, "complete")["height"] == 6


def _nodes(t):
    if "children" in t:
        yield t
        for c in t["children"]:
            yield from _nodes(c)


# ---------- sentiment and lexicon arcs ----------
def test_sentiment_scores_every_sentence(view):
    assert nar.vader_available()
    r = nar.sentiment(view, SLICES)
    assert [b["sentences"] for b in r["books"]] == [view.bd[b].n_sents for b in ("alpha", "beta", "gamma")]
    whole = r["series"][0]
    assert sum(whole["counts"]) == sum(view.bd[b].n_sents for b in view.books)
    assert all(-1 <= v <= 1 for v in whole["values"] if v is not None)
    h = view.member_unit[("alpha", 1)]
    around = nar.sentiment(view, SLICES, [h])["series"]
    assert len(around) == 2 and around[1]["name"] == "Around Holmes" and sum(around[1]["counts"]) == len(view.bd["alpha"].group_sents[1])


def test_lexicon_arcs_count_lexicon_words(view):
    lex = {"cats": {"nature": ["moor", "hill"], "fear": ["hound"]}}
    r = nar.lexicon_arc(view, SLICES, lex)
    by = {s["name"]: s for s in r["series"]}
    words = {w: sum(1 for b in view.books for i, x in enumerate(view.bd[b].word) if x.lower() == w) for w in ("moor", "hill", "hound")}
    assert sum(by["nature"]["counts"]) == words["moor"] + words["hill"] and sum(by["fear"]["counts"]) == words["hound"]
    only = nar.lexicon_arc(view, SLICES, lex, cats=["fear"])
    assert [s["name"] for s in only["series"]] == ["fear"]
    lem = nar.lexicon_arc(view, SLICES, {"cats": {"look": ["look"]}})            # the lemma also counts ("looked")
    assert sum(lem["series"][0]["counts"]) >= sum(1 for b in view.bd for l in view.bd[b].lemma if l == "look")


# ---------- your chapter edits ----------
def edited(lib, book="alpha", cfg=CHAPTER_CFG):
    """(segments, info, bd) of a book with your edits applied, through a fresh view."""
    v = View(lib, [book])
    segs, info = nar.book_segments(v, book, cfg)
    return segs, info, v.bd[book]


def test_chapters_can_be_removed_started_renamed_and_reset(lib):
    auto, info, bd = edited(lib)
    n = len(auto)
    assert not info["edited"] and n >= 3 and all(s["source"] == "auto" for s in auto if s["label"] != "Opening")
    assert nar.edit_chapters(lib, "alpha", "remove", bd.para[auto[1]["head"]]) is True                         # drop the second chapter's start
    segs, info, _ = edited(lib)
    assert len(segs) == n - 1 and info["edited"] and sum(s["words"] for s in segs) == sum(s["words"] for s in auto)   # its text joins the chapter before
    assert all(a["end"] + 1 == b["start"] for a, b in zip(segs, segs[1:])) and segs[0]["start"] == 0 and segs[-1]["end"] == bd.n_tokens - 1
    # start a chapter at a paragraph in the middle of the book: it is yours, and named by its opening words
    heads = {bd.para[s["head"]] for s in auto if s["head"] is not None}
    mid = next(p for p in sorted(bd.para_bounds)[len(bd.para_bounds) // 2:] if p not in heads)
    nar.edit_chapters(lib, "alpha", "add", mid)
    segs, info, _ = edited(lib)
    yours = [s for s in segs if s["source"] == "yours"]
    assert len(segs) == n and len(yours) == 1 and info["yours"] == 1 and yours[0]["start"] == bd.para_bounds[mid][0]
    assert yours[0]["label"] == bd.span_text(yours[0]["start"], min(bd.para_bounds[mid][1], yours[0]["start"] + 12)).strip()
    nar.edit_chapters(lib, "alpha", "rename", mid, "  The turn  ")
    assert next(s for s in edited(lib)[0] if s["source"] == "yours")["label"] == "The turn"
    nar.edit_chapters(lib, "alpha", "rename", mid, "")
    assert next(s for s in edited(lib)[0] if s["source"] == "yours")["label"] != "The turn"
    # a start you added can be taken away again, a removed one brought back: nothing is left over
    assert nar.edit_chapters(lib, "alpha", "remove", mid) is True
    assert nar.edit_chapters(lib, "alpha", "add", bd.para[auto[1]["head"]]) is False
    assert edited(lib)[0] == auto and lib.ann["books"]["alpha"].get("chapters") is None
    nar.edit_chapters(lib, "alpha", "remove", bd.para[auto[1]["head"]])
    assert nar.edit_chapters(lib, "alpha", "reset") is False and edited(lib)[0] == auto


def test_a_chapter_can_be_renamed_and_a_book_without_headings_can_be_split_by_hand(lib):
    none = {"mode": "chapters", "min_words": 10 ** 6, "rules": {}}
    segs, info, bd = edited(lib, cfg=none)
    assert info["fallback"] and all(s["source"] is None for s in segs)                                       # one heading kept is not enough: slices
    pid = sorted(bd.para_bounds)[len(bd.para_bounds) // 3]
    nar.edit_chapters(lib, "alpha", "add", pid)
    segs, info, _ = edited(lib, cfg=none)
    assert [s["source"] for s in segs] == ["auto", "yours"] and info["mode"] == "chapters" and not info["fallback"]      # the book's first heading plus yours
    nar.edit_chapters(lib, "alpha", "rename", pid, "Part two")
    assert edited(lib, cfg=none)[0][1]["label"] == "Part two"


def test_chapter_edits_reach_arcs_and_are_remembered_by_opening_words(lib):
    v0 = View(lib, ["alpha", "beta"])
    before = nar.arcs(v0, CHAPTER_CFG, "dialogue")
    auto, _, bd = edited(lib)
    nar.edit_chapters(lib, "alpha", "remove", bd.para[auto[1]["head"]])
    v1 = View(lib, ["alpha", "beta"])
    after = nar.arcs(v1, CHAPTER_CFG, "dialogue")
    assert len(after["segments"]) == len(before["segments"]) - 1
    assert lib.ann["books"]["alpha"]["chapters"]["remove"][0].endswith("#1")                                    # a key from the paragraph's words, not a number


def test_bad_chapter_edits_are_errors(lib):
    for action, pid in (("add", 10 ** 6), ("colour", 1)):
        with pytest.raises(ValueError):
            nar.edit_chapters(lib, "alpha", action, pid)


def test_stylometry_of_identical_texts_says_so_instead_of_failing(tmp_path, corpus):
    """Three copies of one book (two exports of the same book, say) differ in no word: the answer is a message, not a numerical error
    ("SVD did not converge") caused by rounding noise in a word that is exactly as frequent everywhere."""
    import shutil
    root = tmp_path / "copies"
    for name in ("one", "two", "three"):
        folder = root / name
        folder.mkdir(parents=True)
        for ext in ("tokens", "entities", "quotes", "supersense", "book", "txt"):
            shutil.copy(next(corpus[0].glob("gamma-*")) / f"gamma.{ext}", folder / f"{name}.{ext}")
    r = nar.stylometry(View(Library(data_dir=tmp_path / "data", sources=[root]), ["one", "two", "three"]), SLICES, "books", mfw=50)
    assert "error" in r and "texts" not in r


@pytest.mark.parametrize("min_words", [0, 1, 50, 500])
def test_chapters_always_tile_the_book_with_no_empty_segment(view, min_words):
    """A heading at the very first token has nothing before it to make an "Opening" of, whatever the minimum length: the segments are
    contiguous, start at 0, end at the last token and none is empty (min_words 0 used to give an Opening that ended before it began)."""
    for b in view.books:
        segs, _ = nar.book_segments(view, b, {"mode": "chapters", "min_words": min_words})
        assert segs[0]["start"] == 0 and segs[-1]["end"] == view.bd[b].n_tokens - 1
        assert all(s["start"] <= s["end"] and s["end"] + 1 == t["start"] for s, t in zip(segs, segs[1:])) and segs[-1]["start"] <= segs[-1]["end"]
        assert sum(s["words"] for s in segs) == view.bd[b].n_words
