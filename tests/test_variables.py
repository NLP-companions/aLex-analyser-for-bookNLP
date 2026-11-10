"""The variables of the Statistics tab (core/variables.py): queries, mentions, speech and attributes, measured in each case's sample.

The answer keys are counted straight from each book's tokens, quotes and mentions, not through the code under test."""
from __future__ import annotations

from collections import Counter

import pytest

from alex.core import cases as cs
from alex.core import dialogue as dl
from alex.core import described as ds
from alex.core import layers
from alex.core import variables as vb
from alex.core.corpus import cindex, items_of
from alex.core.view import View

ALL = {"min": 0}


def unit(v, book, coref):
    """The unit id of a book's coreference group."""
    return v.member_unit[(book, coref)]


def tokens(bd, s, e, test):
    """How many word tokens between s and e (inclusive) pass `test`."""
    iw = cindex(bd)["isword"]
    return sum(1 for i in range(s, e + 1) if iw[i] and test(i))


def run(v, cases, spec):
    """The values (and note) of one variable."""
    return vb.values(v, cases, vb.check(spec))


@pytest.fixture
def told(lib):
    """Alpha only, told by Watson (unit and coref 2); returns (view, Watson's unit id, Holmes's unit id)."""
    v = View(lib, ["alpha"])
    lib.ann_book("alpha")["narrator"] = unit(v, "alpha", 2)
    lib.save_ann()
    v = View(lib, ["alpha"])
    return v, unit(v, "alpha", 2), unit(v, "alpha", 1)


@pytest.fixture
def books(view):
    """Every book as a case."""
    return cs.build(view, {"kind": "pieces", "piece": "book", **ALL})


# ---------- queries ----------
def test_a_word_is_counted_in_each_book(view, books):
    counts, note = run(view, books, {"kind": "query", "query": "moor", "measure": "count"})
    assert note is None
    for r, n in zip(books.rows, counts):
        bd = view.bd[r["book"]]
        lower = cindex(bd)["lower"]
        assert n == tokens(bd, 0, bd.n_tokens - 1, lambda i: lower[i] == "moor")
    assert counts[0] > 0 and counts[1] == 0                                     # only alpha has the moor


def test_measures_are_rates_counts_and_presence(view, books):
    q = {"kind": "query", "query": "moor"}
    counts = run(view, books, {**q, "measure": "count"})[0]
    rates = run(view, books, q)[0]
    present = run(view, books, {**q, "measure": "present"})[0]
    assert rates == pytest.approx([1000 * n / r["size"] for n, r in zip(counts, books.rows)])
    assert present == [int(n > 0) for n in counts]


def test_lemmas_and_phrases(view, books):
    bd = view.bd["alpha"]
    lemma = [x.lower() for x in bd.lemma]
    n = run(view, books, {"kind": "query", "query": "look", "match": "lemma", "measure": "count"})[0][0]
    assert n == tokens(bd, 0, bd.n_tokens - 1, lambda i: lemma[i] == "look") > 0
    stream = [i for i, w in enumerate(cindex(bd)["isword"]) if w]
    low = cindex(bd)["lower"]
    pairs = sum(1 for a, b in zip(stream, stream[1:]) if low[a] == "the" and low[b] == "moor")
    assert run(view, books, {"kind": "query", "query": "the moor", "measure": "count"})[0][0] == pairs > 0
    pattern = run(view, books, {"kind": "query", "query": 'the [lemma="moor"]', "mode": "pattern", "measure": "count"})[0][0]
    assert pattern == pairs


def test_a_scope_counts_only_its_hits(view):
    dialogue = cs.build(view, {"kind": "pieces", "piece": "book", "scope": {"kind": "dialogue"}, **ALL})
    bd = view.bd["alpha"]
    ci = cindex(bd)
    n = run(view, dialogue, {"kind": "query", "query": "said|the", "measure": "count"})[0][0]
    assert n == tokens(bd, 0, bd.n_tokens - 1, lambda i: ci["in_quote"][i] and ci["lower"][i] in ("said", "the"))


def test_a_participant_is_measured_in_their_own_speech(told):
    v, w, h = told
    c = cs.build(v, {"kind": "participants", **ALL})
    bd, i = v.bd["alpha"], [r["id"] for r in c.rows].index(w)
    low = cindex(bd)["lower"]
    expected = sum(tokens(bd, q["start"], q["end"], lambda t: low[t] == "the") for q in bd.quotes if q["char"] == 2)
    assert run(v, c, {"kind": "query", "query": "the", "measure": "count"})[0][i] == expected > 0


def test_a_query_error_names_the_variable(view, books):
    with pytest.raises(ValueError, match="“\\[oops”"):
        run(view, books, {"kind": "query", "query": "[oops", "mode": "pattern"})


# ---------- mentions ----------
def test_mentions_per_book_and_by_kind(view, books):
    holmes = unit(view, "alpha", 1)
    every = run(view, books, {"kind": "mentions", "target": {"kind": "unit", "id": holmes}, "measure": "count"})[0]
    names = run(view, books, {"kind": "mentions", "target": {"kind": "unit", "id": holmes}, "prop": "PROP", "measure": "count"})[0]
    for r, n, k in zip(books.rows, every, names):
        mine = [mi for b, c in view.units[holmes].members if b == r["book"] for mi in view.bd[b].groups[c].mentions]
        assert n == len(mine) and k == sum(view.bd[r["book"]].mentions[mi][3] == "PROP" for mi in mine)
    assert 0 < sum(names) < sum(every)


def test_mentions_in_a_participants_speech(told):
    v, w, h = told
    c = cs.build(v, {"kind": "participants", **ALL})
    bd, i = v.bd["alpha"], [r["id"] for r in c.rows].index(w)
    starts = [bd.mentions[mi][1] for mi in bd.groups[1].mentions]
    expected = sum(1 for t in starts for q in bd.quotes if q["char"] == 2 and q["start"] <= t <= q["end"])
    assert run(v, c, {"kind": "mentions", "target": {"kind": "unit", "id": h}, "measure": "count"})[0][i] == expected


# ---------- speech ----------
def said(v, target, b, test=lambda r: True):
    """Alpha's (or book b's) quote records spoken by a unit, straight from the speakers of each record."""
    mem = v.units[target].members
    return [r for r in dl.bdlg(v, b)["recs"] if any((b, c) in mem for c in r["speakers"]) and r["tokens"] and test(r)]


def test_speech_per_book_in_words_and_quotes(view, books):
    holmes = unit(view, "alpha", 1)
    target = {"kind": "unit", "id": holmes}
    words = run(view, books, {"kind": "spoken", "target": target, "measure": "count"})[0]
    quotes = run(view, books, {"kind": "spoken", "target": target, "unit": "quotes", "measure": "count"})[0]
    for r, n, q in zip(books.rows, words, quotes):
        mine = said(view, holmes, r["book"])
        assert n == sum(x["n"] for x in mine) and q == len(mine)
    assert 0 < sum(quotes) < sum(words)
    rate = run(view, books, {"kind": "spoken", "target": target})[0]
    assert rate == pytest.approx([1000 * n / r["size"] for n, r in zip(words, books.rows)])


def test_speech_of_one_sentence_type(view, books, marked):
    speaker = next(c for c in marked[0]["speakers"])
    who, a = {"kind": "unit", "id": unit(view, "alpha", speaker)}, [r["book"] for r in books.rows].index("alpha")
    for typ, weigh in (("question", False), ("question", True), ("statement", False)):
        expected = said(view, who["id"], "alpha", lambda r: dl.sentence_type(r, weigh) == typ)
        got = run(view, books, {"kind": "spoken", "target": who, "unit": "quotes", "type": typ, "weigh": weigh, "measure": "count"})[0]
        assert got[a] == len(expected)
    assert run(view, books, {"kind": "spoken", "target": who, "unit": "quotes", "type": "question", "measure": "count"})[0][a] >= 1


def test_speech_as_a_share_of_quotes(view, books):
    holmes = {"kind": "unit", "id": unit(view, "alpha", 1)}
    share = run(view, books, {"kind": "spoken", "target": holmes, "unit": "quotes", "measure": "pct"})[0]
    mine = run(view, books, {"kind": "spoken", "target": holmes, "unit": "quotes", "measure": "count"})[0]
    every = layers.quote_counts(view, books)
    assert share == [100 * n / q if q else None for n, q in zip(mine, every)]
    with pytest.raises(ValueError):                                                        # a share of quotes needs quotes
        vb.check({"kind": "spoken", "target": holmes, "measure": "pct"})


def test_speech_in_sentences_mentioning_a_participant(told):
    v, w, h = told
    c = cs.build(v, {"kind": "participants", "sample": "sentences", **ALL})
    i = [r["id"] for r in c.rows].index(w)
    got = run(v, c, {"kind": "spoken", "target": {"kind": "unit", "id": h}, "measure": "count"})[0][i]
    at = c.at("alpha")
    assert got == sum(1 for r in said(v, h, "alpha") for t in r["tokens"] if i in at(t))


def test_speech_labels(view, books):
    holmes = {"kind": "unit", "id": unit(view, "alpha", 1)}
    labels = [x["label"] for x in vb.table(view, books, [{"kind": "spoken", "target": holmes},
                                                          {"kind": "spoken", "target": holmes, "unit": "quotes", "type": "question", "weigh": True}])["variables"]]
    name = vb.who(view, holmes)
    assert labels == [f"Speech of {name}", f"Speech of {name}: quotes, questions (speech verb weighed)"]


# ---------- the findings sample ----------
def test_findings_are_matched_by_their_word(told):
    v, w, h = told
    c = cs.build(v, {"kind": "participants", "sample": "findings", **ALL})
    i = [r["id"] for r in c.rows].index(h)
    agent = [key for b, mi, key, _ in ds.findings(v, v.units[h].members, "agent")]
    word = agent[0]
    every = sum(1 for k in ds.KINDS for b, mi, key, _ in ds.findings(v, v.units[h].members, k) if key.lower() == word.lower())
    assert run(v, c, {"kind": "query", "query": word, "measure": "count"})[0][i] == every
    assert run(v, c, {"kind": "query", "query": word, "finding": "agent", "measure": "count"})[0][i] == agent.count(word)
    rate = run(v, c, {"kind": "query", "query": word, "finding": "agent"})[0][i]
    assert rate == pytest.approx(100 * agent.count(word) / c.rows[i]["size"])
    assert vb.measure_label(c, vb.check({"kind": "query", "query": word})) == "% of findings"


def test_what_findings_cannot_measure_gets_a_note(told):
    v, w, h = told
    c = cs.build(v, {"kind": "participants", "sample": "findings", **ALL})
    for spec in ({"kind": "query", "query": "[]", "mode": "pattern"}, {"kind": "query", "query": "the moor"},
                 {"kind": "mentions", "target": {"kind": "unit", "id": w}}, {"kind": "spoken", "target": {"kind": "unit", "id": w}}):
        vals, note = run(v, c, spec)
        assert note and set(vals) == {None}


# ---------- attributes ----------
def test_piece_attributes(view):
    c = cs.build(view, {"kind": "pieces", "piece": "chapter", **ALL})
    assert run(view, c, {"kind": "attribute", "attr": "length"})[0] == [r["size"] for r in c.rows]
    index = run(view, c, {"kind": "attribute", "attr": "index"})[0]
    assert index[0] == 1 and run(view, c, {"kind": "attribute", "attr": "position"})[0][0] == 0
    books = cs.build(view, {"kind": "pieces", "piece": "book", **ALL})
    assert set(run(view, books, {"kind": "attribute", "attr": "index"})[0]) == {None}
    assert run(view, books, {"kind": "attribute", "attr": "speech"})[1]                 # a participant attribute: a note


def test_participant_attributes(told, lib):
    v, w, h = told
    lib.set_tags(w, ["doctor"])
    v = View(lib, ["alpha"])
    c = cs.build(v, {"kind": "participants", "sample": "speech_narration", **ALL})
    ids = [r["id"] for r in c.rows]
    i = ids.index(w)
    doctor = run(v, c, {"kind": "attribute", "attr": "in", "target": {"kind": "tag", "tag": "doctor"}})[0]
    assert doctor[i] == 1 and sum(doctor) == 1
    pron = v.gender_of(v.units[w])
    gender = run(v, c, {"kind": "attribute", "attr": "in", "target": {"kind": "gender", "pron": pron}})[0]
    assert gender == [int(v.gender_of(v.units[x]) == pron) for x in ids]
    bd = v.bd["alpha"]
    spoken = sum(tokens(bd, q["start"], q["end"], lambda t: True) for q in bd.quotes if q["char"] == 2)
    assert run(v, c, {"kind": "attribute", "attr": "speech"})[0][i] == spoken
    assert run(v, c, {"kind": "attribute", "attr": "quotes"})[0][i] == sum(q["char"] == 2 for q in bd.quotes)
    assert run(v, c, {"kind": "attribute", "attr": "mentions"})[0][i] == v.units[w].mentions
    assert run(v, c, {"kind": "attribute", "attr": "books"})[0][i] == 1
    assert run(v, c, {"kind": "attribute", "attr": "length"})[1]                          # a piece attribute: a note


def test_a_narrator_role_has_no_entity_attributes(lib):
    v = View(lib, ["beta"])
    c = cs.build(v, {"kind": "participants", "sample": "speech_narration", **ALL})
    i = [r["type"] for r in c.rows].index("NARR")
    for attr in ("mentions", "speech", "quotes"):
        assert run(v, c, {"kind": "attribute", "attr": attr})[0][i] is None
    assert run(v, c, {"kind": "attribute", "attr": "in", "target": {"kind": "type", "type": "PER"}})[0][i] is None
    assert run(v, c, {"kind": "attribute", "attr": "books"})[0][i] == 1


# ---------- the table and its checks ----------
def test_the_table_measures_every_variable(view, books):
    holmes = unit(view, "alpha", 1)
    t = vb.table(view, books, [{"kind": "query", "query": "moor"}, {"kind": "mentions", "target": {"kind": "unit", "id": holmes}, "prop": "PRON"},
                               {"kind": "attribute", "attr": "length", "name": "Words"}])
    assert [x["id"] for x in t["variables"]] == ["v0", "v1", "v2"] and len(t["values"]) == 3
    assert all(len(vals) == len(books.rows) for vals in t["values"])
    assert [x["label"] for x in t["variables"]] == ["“moor”", "Mentions of Holmes (alpha): pronouns", "Words"]
    assert [x["measure"] for x in t["variables"]] == ["per 1,000 words", "per 1,000 words", ""]


def test_bad_variables_are_refused(view, books):
    for bad in ([], "moor", [{"kind": "feeling"}], [{"kind": "query", "query": ""}], [{"kind": "query", "query": "x", "measure": "per2k"}],
                [{"kind": "query", "query": "x", "mode": "regex"}], [{"kind": "mentions"}], [{"kind": "mentions", "target": {"kind": "unit"}, "prop": "X"}],
                [{"kind": "spoken"}], [{"kind": "spoken", "target": {"kind": "unit"}, "unit": "letters"}], [{"kind": "spoken", "target": {"kind": "unit"}, "type": "shout"}],
                [{"kind": "attribute", "attr": "height"}], [{"kind": "attribute", "attr": "in"}],
                [{"kind": "query", "query": "x"}] * (vb.MAX_VARIABLES + 1)):
        with pytest.raises(ValueError):
            vb.table(view, books, bad)


# ---------- bulk add ----------
def test_top_words_are_the_most_frequent_in_the_samples(view):
    dialogue = cs.build(view, {"kind": "pieces", "piece": "book", "scope": {"kind": "dialogue"}, **ALL})
    top = vb.top_words(view, dialogue, 5)
    assert len(top) == 5 and all(s["wildcards"] is False and s["kind"] == "query" for s in top)
    counts = [sum(run(view, dialogue, {**s, "measure": "count"})[0]) for s in top]
    assert counts == sorted(counts, reverse=True)
    nouns = vb.top_words(view, dialogue, 3, "lemma", {"pos": ["NOUN"]})
    assert nouns and all(s["match"] == "lemma" for s in nouns)
    noun_lemmas = {bd.lemma[i].lower() for bd in view.bd.values() for i in range(bd.n_tokens) if bd.pos[i] == "NOUN"}
    assert {s["query"] for s in nouns} <= noun_lemmas


def test_top_words_are_only_those_in_enough_books(view):
    everything = cs.build(view, {"kind": "pieces", "piece": "book", **ALL})
    default = {s["query"] for s in vb.top_words(view, everything, vb.MAX_VARIABLES)}
    in_every_book = set.intersection(*({it(i) for i in range(bd.n_tokens) if cindex(bd)["isword"][i]} for bd in view.bd.values()
                                       for it in [items_of(bd, "word")]))
    three = vb.top_words(view, everything, vb.MAX_VARIABLES, min_range=3)
    assert three and {s["query"] for s in three} <= in_every_book
    assert default - in_every_book and not ({s["query"] for s in three} & (default - in_every_book))          # some words are in fewer books
    assert vb.top_words(view, everything, vb.MAX_VARIABLES, min_range=4) == []


def test_top_words_inside_quotes_of_a_sentence_type(view, marked):
    everything = cs.build(view, {"kind": "pieces", "piece": "book", **ALL})
    bd, item = view.bd["alpha"], items_of(view.bd["alpha"], "word")
    iw = cindex(bd)["isword"]
    asked = {item(t) for t in marked[0]["tokens"] if iw[t]}                                   # the one question
    top = vb.top_words(view, everything, vb.MAX_VARIABLES, types=["question"])
    assert {s["query"] for s in top} == asked
    lower = cindex(bd)["lower"]
    for s in top:                                                                              # the variables count the word anywhere in the sample
        assert run(view, everything, {**s, "measure": "count"})[0][0] == sum(1 for t in range(bd.n_tokens) if lower[t] == s["query"])
    weighed = {s["query"] for s in vb.top_words(view, everything, vb.MAX_VARIABLES, types=["question"], weigh=True)}
    assert weighed >= asked | {item(t) for t in marked[2]["tokens"] if iw[t]}                  # the quote said with "ask" counts as one too
    dialogue = cs.build(view, {"kind": "pieces", "piece": "book", "scope": {"kind": "dialogue"}, **ALL})
    assert vb.top_words(view, everything, vb.MAX_VARIABLES, types=list(layers.SPEECH_TYPES)) == vb.top_words(view, dialogue, vb.MAX_VARIABLES)


def test_top_words_can_be_the_speech_verbs(view, marked):
    everything = cs.build(view, {"kind": "pieces", "piece": "book", **ALL})
    top = vb.top_words(view, everything, vb.MAX_VARIABLES, "word", speech_verbs=True)
    introduced = Counter(r["verb"] for b, r in dl.all_recs(view) if r["verb"] and r["tokens"])
    assert [s["query"] for s in top] == [v for v, _ in sorted(introduced.items(), key=lambda kv: (-kv[1], kv[0]))]
    assert all(s["match"] == "lemma" and s["wildcards"] is False for s in top) and {"ask", "say"} <= {s["query"] for s in top}
    assert [s["query"] for s in vb.top_words(view, everything, 5, speech_verbs=True, types=["question"])] == ["say"]
    assert [s["query"] for s in vb.top_words(view, everything, 5, speech_verbs=True, types=["question"], weigh=True)] == ["ask", "say"]
    assert vb.top_words(view, everything, 5, speech_verbs=True, flt={"pos": ["NOUN"]}) == []            # the filter tests the verb
    assert vb.top_words(view, everything, 5, speech_verbs=True, min_range=4) == []


def test_top_words_in_speech_samples_of_participants(view, marked):
    speakers = cs.build(view, {"kind": "participants", "sample": "speech", **ALL})
    assert {s["query"] for s in vb.top_words(view, speakers, 5, speech_verbs=True)} == {"say", "ask"}


def test_top_words_refuse_bad_sentence_options(view, told):
    everything = cs.build(view, {"kind": "pieces", "piece": "book", **ALL})
    for bad in ("question", ["shout"], [["question"]], [1]):
        with pytest.raises(ValueError):
            vb.top_words(view, everything, 3, types=bad)
    v, w, h = told
    findings = cs.build(v, {"kind": "participants", "sample": "findings", **ALL})
    for kw in ({"types": ["question"]}, {"speech_verbs": True}):
        with pytest.raises(ValueError):
            vb.top_words(v, findings, 3, **kw)


def test_top_words_of_findings(told):
    v, w, h = told
    c = cs.build(v, {"kind": "participants", "sample": "findings", **ALL})
    top = vb.top_words(v, c, 3)
    assert top and all(sum(run(v, c, {**s, "measure": "count"})[0]) > 0 for s in top)


def test_top_entities_and_attribute_values(view, lib):
    top = vb.top_entities(view, 3, "PER")
    ments = [view.units[s["target"]["id"]].mentions for s in top]
    assert len(top) == 3 and ments == sorted(ments, reverse=True)
    genders = vb.attribute_values(view, "gender")
    assert [s["target"]["pron"] for s in genders] == [g["pron"] for g in view.genders()]
    lib.set_tags(unit(view, "alpha", 2), ["doctor"])
    assert [s["target"]["tag"] for s in vb.attribute_values(View(lib, view.books), "tag")] == ["doctor"]
    with pytest.raises(ValueError):
        vb.attribute_values(view, "height")
    with pytest.raises(ValueError):
        vb.top_entities(view, 3, "ALIEN")


def test_top_speakers_speak_the_most_words(view):
    top = vb.top_speakers(view, vb.MAX_VARIABLES, "PER")
    words = vb._speech_totals(view, set(view.books))[0]
    spoken = [words[s["target"]["id"]] for s in top]
    assert top and all(s["kind"] == "spoken" and s["unit"] == "words" for s in top)
    assert spoken == sorted(spoken, reverse=True) and all(spoken)
    assert len(top) == sum(1 for u in view.units.values() if u.type == "PER" and words[u.id])
    assert len(vb.top_speakers(view, 1, "ALL")) == 1
    with pytest.raises(ValueError):
        vb.top_speakers(view, 3, "ALIEN")


def test_entities_of_the_same_name_are_told_apart_by_their_books(view, books):
    holmes = [u for u in view.units.values() if u.name == "Holmes"]
    assert len(holmes) == 3                                                          # one per book, not linked
    labels = [x["label"] for x in vb.table(view, books, [{"kind": "mentions", "target": {"kind": "unit", "id": u.id}} for u in holmes])["variables"]]
    assert labels == [f"Mentions of Holmes ({view.title(next(iter(u.books)))})" for u in holmes]
