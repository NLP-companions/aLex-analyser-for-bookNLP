"""The linguistic layers of the Statistics tab (core/layers.py): supersenses, relations, sentiment, lexicons, style and topics, in each case's sample.

The answer keys come from elsewhere: the book's own supersense spans and relation counts, the style figures and sentiment of Arcs and style
(`narrative.style_metrics`, `narrative.sentiment`) for whole books, and VADER run directly on the quotes."""
from __future__ import annotations

import pytest

from alex.core import cases as cs
from alex.core import dialogue as dl
from alex.core import layers
from alex.core import lexicons
from alex.core import narrative as nr
from alex.core import variables as vb
from alex.core import wordchoice
from alex.core.corpus import cindex
from alex.core.view import View

ALL = {"min": 0}


def unit(v, book, coref):
    """The unit id of a book's coreference group."""
    return v.member_unit[(book, coref)]


def run(v, cases, spec, lexicons=None):
    """The values (and note) of one variable."""
    return vb.values(v, cases, vb.check(spec), lexicons)


@pytest.fixture
def books(view):
    """Every book as a case."""
    return cs.build(view, {"kind": "pieces", "piece": "book", **ALL})


@pytest.fixture
def told(lib):
    """Alpha only, told by Watson (unit and coref 2); returns (view, Watson's unit id, Holmes's unit id)."""
    v = View(lib, ["alpha"])
    lib.ann_book("alpha")["narrator"] = unit(v, "alpha", 2)
    lib.save_ann()
    v = View(lib, ["alpha"])
    return v, unit(v, "alpha", 2), unit(v, "alpha", 1)


# ---------- counted layers ----------
def test_supersense_spans_are_counted_once(view, books):
    bd = view.bd["alpha"]
    cat = "verb.communication"
    starts = sum(1 for i, c in bd.ss.items() if c == cat and bd.ss.get(i - 1) != cat)
    assert run(view, books, {"kind": "supersense", "value": cat, "measure": "count"})[0][0] == starts > 0


def test_relations_of_a_target_and_of_every_entity(view, books):
    holmes = unit(view, "alpha", 1)
    said = run(view, books, {"kind": "relation", "rel": "agent", "word": "say", "target": {"kind": "unit", "id": holmes}, "measure": "count"})[0]
    assert said[0] == view.bd["alpha"].groups[1].rel["agent"]["say"] > 0
    anyone = run(view, books, {"kind": "relation", "rel": "agent", "measure": "count"})[0]
    for r, n in zip(books.rows, anyone):
        b = r["book"]
        assert n == sum(sum(view.bd[b].groups[c].rel["agent"].values()) for bb, c in view.member_unit if bb == b)


def test_lexicon_words_by_form_or_lemma(view, books):
    lexs = {"emotion": {"name": "NRC", "cats": {"gloom": ["moor", "look"]}}, "register": {"name": "Register", "cats": {"formal": ["indeed"]}}}
    n = run(view, books, {"kind": "lexicon", "category": "gloom", "measure": "count"}, lexs)[0][0]   # the emotion lexicon by default
    ci = cindex(view.bd["alpha"])
    assert n == sum(1 for i, w in enumerate(ci["isword"]) if w and (ci["lower"][i] in ("moor", "look") or ci["lemma_lower"][i] in ("moor", "look")))
    assert run(view, books, {"kind": "lexicon", "category": "gloom"})[1]                            # no lexicons stored: a note
    assert "no category" in run(view, books, {"kind": "lexicon", "category": "joy"}, lexs)[1]
    assert "no lexicon" in run(view, books, {"kind": "lexicon", "lexicon": "slang", "category": "x"}, lexs)[1]
    other = vb.table(view, books, [{"kind": "lexicon", "lexicon": "register", "category": "formal"}, {"kind": "lexicon", "category": "gloom"}], lexs)
    assert [x["label"] for x in other["variables"]] == ["Register: formal", "Emotion: gloom"] and not other["variables"][0]["note"]


def test_every_lexicon_file_is_a_lexicon(tmp_path):
    (tmp_path / "emotion.json").write_text('{"name": "NRC", "cats": {"fear": ["moor"]}}', encoding="utf-8")
    (tmp_path / "register.json").write_text('{"name": "Register", "cats": {"formal": ["indeed"]}}', encoding="utf-8")
    (tmp_path / "broken.json").write_text("{ nope", encoding="utf-8")
    assert sorted(lexicons.stored(tmp_path)) == ["emotion", "register"] and lexicons.stored(tmp_path / "missing") == {}


# ---------- units, sentiment and style ----------
@pytest.mark.parametrize("setup", [{"kind": "pieces", "piece": "chapter"}, {"kind": "pieces", "piece": "slice", "n": 4, "scope": {"kind": "dialogue"}},
                                   {"kind": "participants", "sample": "speech"}, {"kind": "participants", "sample": "speech_narration"},
                                   {"kind": "participants", "sample": "sentences"}])
def test_the_units_hold_exactly_the_sample(told, setup):
    v, w, h = told
    c = cs.build(v, {**setup, **ALL})
    for row, us in zip(c.rows, layers.units(v, c)):
        iw = cindex(v.bd["alpha"])["isword"]
        assert sum(sum(1 for t in toks if iw[t]) for b, toks, sid in us) == row["size"]


def test_a_quote_and_its_narration_are_separate_units(told):
    v, w, h = told
    c = cs.build(v, {"kind": "participants", "sample": "speech_narration", **ALL})
    us = layers.units(v, c)[[r["id"] for r in c.rows].index(w)]
    bd = v.bd["alpha"]
    in_quote = cindex(bd)["in_quote"]
    for b, toks, sid in us:
        assert len({in_quote[t] for t in toks}) == 1                                  # all quote, or all narration
        if in_quote[toks[0]]:
            assert len({bd.quote_at.get(t) for t in toks}) == 1


def test_sentiment_of_whole_books_is_that_of_arcs_and_style(view, books):
    means = run(view, books, {"kind": "sentiment"})[0]
    pos = run(view, books, {"kind": "sentiment", "stat": "positive"})[0]
    by_book = {x["book"]: x for x in nr.sentiment(view, {"mode": "slices", "n": 2})["books"]}
    for r, m, p in zip(books.rows, means, pos):
        assert m == pytest.approx(by_book[r["book"]]["mean"]) and p == pytest.approx(by_book[r["book"]]["positive"])


def test_sentiment_of_speech_is_the_mean_of_the_quotes(told):
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    v, w, h = told
    c = cs.build(v, {"kind": "participants", "sample": "speech", **ALL})
    bd, sia = v.bd["alpha"], SentimentIntensityAnalyzer()
    scores = [sia.polarity_scores(bd.span_text(q["start"], q["end"]))["compound"] for q in bd.quotes if q["char"] == 2]
    got = run(v, c, {"kind": "sentiment"})[0][[r["id"] for r in c.rows].index(w)]
    assert got == pytest.approx(sum(scores) / len(scores), abs=0.02)                # a quote's text without its quote marks


@pytest.mark.parametrize("figure,key", [("word_length", "word_len"), ("mattr", "mattr"), ("hapax", "hapax"), ("density", "density"),
                                        ("passives", "passive"), ("unit_length", "sent_len"), ("questions", "questions")])
def test_style_of_whole_books_is_that_of_arcs_and_style(view, books, figure, key):
    got = run(view, books, {"kind": "style", "figure": figure})[0]
    for r, value in zip(books.rows, got):
        bd = view.bd[r["book"]]
        assert value == pytest.approx(nr.style_metrics(bd, 0, bd.n_tokens - 1)[key])


# ---------- word choice ----------
def test_word_choice_of_whole_books_is_the_style_profile(view, books):
    for pos in ("ADJ", "VERB", "NOUN"):
        got = run(view, books, {"kind": "wordchoice", "figure": f"pos:{pos}"})[0]
        for r, value in zip(books.rows, got):
            bd = view.bd[r["book"]]
            assert value == pytest.approx(nr.style_metrics(bd, 0, bd.n_tokens - 1)["pos"][pos])


def test_word_choice_of_speech_is_taken_over_the_speakers_quotes(told):
    v, w, h = told
    c = cs.build(v, {"kind": "participants", "sample": "speech", **ALL})
    bd, iw = v.bd["alpha"], cindex(v.bd["alpha"])["isword"]
    words = [t for q in bd.quotes if q["char"] == 2 for t in range(q["start"], q["end"] + 1) if iw[t]]
    row = [r["id"] for r in c.rows].index(w)
    assert len(words) == c.rows[row]["size"] > 0
    for pos in ("ADJ", "VERB", "PRON"):
        share = 100 * sum(bd.pos[t] == pos for t in words) / len(words)
        assert run(v, c, {"kind": "wordchoice", "figure": f"pos:{pos}"})[0][row] == pytest.approx(share)
    verbs = sum(bd.pos[t] == "VERB" for t in words)
    got = run(v, c, {"kind": "wordchoice", "figure": "ratio:adj_verb"})[0][row]
    assert got == (pytest.approx(sum(bd.pos[t] == "ADJ" for t in words) / verbs) if verbs else None)


def test_word_choice_supersense_shares_of_a_book(view, books):
    bd = view.bd["alpha"]
    starts = [c.partition(".")[2] for i, c in bd.ss.items() if c.startswith("verb.") and bd.ss.get(i - 1) != c]
    row = [r["book"] for r in books.rows].index("alpha")
    share = run(view, books, {"kind": "wordchoice", "figure": "verb:motion"})[0][row]
    assert share == pytest.approx(100 * starts.count("motion") / len(starts))
    dynamic = run(view, books, {"kind": "wordchoice", "figure": "verbs:dynamic"})[0][row]
    static = run(view, books, {"kind": "wordchoice", "figure": "verbs:static"})[0][row]
    assert dynamic + static == pytest.approx(100)


def test_word_choice_is_worked_out_once_per_cases(view, books):
    assert books.word_choice is None
    run(view, books, {"kind": "wordchoice", "figure": "pos:ADJ"})
    kept = books.word_choice
    run(view, books, {"kind": "wordchoice", "figure": "ratio:noun_verb"})
    assert books.word_choice is kept


def test_word_choice_needs_running_text_and_a_known_figure(view):
    c = cs.build(view, {"kind": "participants", "sample": "findings", **ALL})
    vals, note = run(view, c, {"kind": "wordchoice", "figure": "pos:ADJ"})
    assert set(vals) == {None} and note
    with pytest.raises(ValueError):
        vb.check({"kind": "wordchoice", "figure": "pos:XYZ"})
    assert "measure" not in vb.check({"kind": "wordchoice", "figure": "pos:ADJ"})
    assert vb.label(view, vb.check({"kind": "wordchoice", "figure": "ratio:adj_verb"})) == "Adjectives per verb"


def test_the_options_offer_the_word_choice_sections(view):
    sections = layers.options(view)["wordchoice"]
    assert [s["id"] for s in sections] == [k for k, _, _ in wordchoice.SECTIONS]
    assert {k for s in sections for k in s["figures"]} == set(wordchoice.FIGURES)


def test_exclamations_are_a_share_of_units(view, books):
    got = run(view, books, {"kind": "style", "figure": "exclaims"})[0][0]
    bd = view.bd["alpha"]
    sents = [(s, e) for s, e in bd.sent_bounds.values() if any(cindex(bd)["isword"][t] for t in range(s, e + 1))]
    assert got == pytest.approx(100 * sum(any(bd.word[t] == "!" for t in range(s, e + 1)) for s, e in sents) / len(sents))


# ---------- speech sentence type ----------
def types_in(view, cases, weigh=False):
    """Per sentence type, the values (count) of its speech variable over the cases."""
    return {t: run(view, cases, {"kind": "speech", "type": t, "weigh": weigh, "measure": "count"})[0] for t in layers.SPEECH_TYPES}


def test_speech_types_count_the_quotes_of_each_type(view, books, marked):
    got = types_in(view, books)
    alpha = [r["book"] for r in books.rows].index("alpha")
    n = len([r for r in marked if r["tokens"]])
    assert (got["question"][alpha], got["exclaim"][alpha], got["statement"][alpha]) == (1, 1, n - 2)
    for k, row in enumerate(books.rows):                                                         # every quote has exactly one type
        total = sum(1 for b, r in dl.all_recs(view) if b == row["book"] and r["tokens"])
        assert sum(got[t][k] for t in got) == total
    assert got["question"][1:] == [0, 0] and got["exclaim"][1:] == [0, 0]


def test_speech_types_can_weigh_the_speech_verb(view, books, marked):
    alpha = [r["book"] for r in books.rows].index("alpha")
    plain, weighed = types_in(view, books), types_in(view, books, weigh=True)
    assert weighed["question"][alpha] == plain["question"][alpha] + 1                           # the quote said with "ask"
    assert weighed["statement"][alpha] == plain["statement"][alpha] - 1


def test_speech_type_measures(view, books, marked):
    alpha = [r["book"] for r in books.rows].index("alpha")
    spec = {"kind": "speech", "type": "question"}
    total = sum(1 for r in marked if r["tokens"])
    assert run(view, books, {**spec, "measure": "pct"})[0][alpha] == pytest.approx(100 / total)
    assert run(view, books, {**spec, "measure": "present"})[0][:2] == [1, 0]
    assert run(view, books, spec)[0][alpha] == pytest.approx(1000 / books.rows[alpha]["size"])      # per 1,000 words of the sample
    assert vb.measure_label(books, vb.check({**spec, "measure": "pct"})) == "% of quotes"


def test_speech_types_of_participants_count_their_quotes(told, marked):
    v, w, h = told
    c = cs.build(v, {"kind": "participants", "sample": "speech", **ALL})
    got = {t: dict(zip([r["id"] for r in c.rows], run(v, c, {"kind": "speech", "type": t, "measure": "count"})[0])) for t in layers.SPEECH_TYPES}
    for uid in (w, h):
        coref = 2 if uid == w else 1
        mine = [r for r in marked if r["speaker"] == coref]
        assert got["question"][uid] == sum(r["question"] for r in mine)
        assert sum(got[t][uid] for t in got) == len(mine)
    share = dict(zip([r["id"] for r in c.rows], run(v, c, {"kind": "speech", "type": "question", "measure": "pct"})[0]))
    assert share[h] == pytest.approx(100 * got["question"][h] / sum(got[t][h] for t in got))


def test_speech_types_follow_the_scope_and_the_sample(view, marked):
    narration = cs.build(view, {"kind": "pieces", "piece": "book", "scope": {"kind": "narration"}, **ALL})
    assert set(run(view, narration, {"kind": "speech", "type": "statement", "measure": "count"})[0]) == {0}   # no quote lies in narration
    assert set(run(view, narration, {"kind": "speech", "type": "statement", "measure": "pct"})[0]) == {None}   # and there is no share of none
    for sample in ("sentences", "findings"):
        vals, note = run(view, cs.build(view, {"kind": "participants", "sample": sample, **ALL}), {"kind": "speech", "type": "question"})
        assert note and set(vals) == {None}


# ---------- what doesn't apply, and checks ----------
def test_layers_need_running_text(told):
    v, w, h = told
    c = cs.build(v, {"kind": "participants", "sample": "findings", **ALL})
    for spec in ({"kind": "sentiment"}, {"kind": "style", "figure": "mattr"}, {"kind": "supersense", "value": "verb.motion"},
                 {"kind": "relation", "rel": "mod"}):
        vals, note = run(v, c, spec)
        assert note and set(vals) == {None}


def test_layer_labels_and_measures(view, books):
    holmes = unit(view, "alpha", 1)
    t = vb.table(view, books, [{"kind": "relation", "rel": "agent", "word": "say", "target": {"kind": "unit", "id": holmes}},
                               {"kind": "sentiment"}, {"kind": "style", "figure": "mattr"}, {"kind": "supersense", "value": "verb.motion"}])
    assert [x["label"] for x in t["variables"]] == ["Actions of Holmes (alpha): “say”", "Sentiment (mean compound)", "MATTR",
                                                    "Supersense verb.motion"]
    assert [x["measure"] for x in t["variables"]] == ["per 1,000 words", "", "", "per 1,000 words"]


def test_bad_layers_are_refused(view, books):
    for bad in ({"kind": "supersense"}, {"kind": "relation", "rel": "loves"}, {"kind": "relation", "target": "Holmes"},
                {"kind": "sentiment", "stat": "median"}, {"kind": "lexicon"}, {"kind": "style", "figure": "beauty"},
                {"kind": "speech", "type": "shout"}, {"kind": "query", "query": "a", "measure": "pct"}, {"kind": "topic"}, {"kind": "topic", "model": "m"}, {"kind": "topic", "model": "m", "topic": -1}, {"kind": "topic", "model": "m", "topic": True}):
        with pytest.raises(ValueError):
            vb.table(view, books, [bad])


def test_the_options_route(client, view):
    o = client.post("/api/stats/options", json={"books": view.books}).json()
    assert o["vader"] is True and o["lexicons"] == [] and o["topics"] == [] and set(o["relations"]) == {"agent", "patient", "mod", "poss", "prep"}
    assert o["supersenses"][0]["n"] >= o["supersenses"][-1]["n"] and any(s["value"] == "verb.communication" for s in o["supersenses"])


# ---------- topics ----------
@pytest.fixture
def model(lib, tmp_path):
    """A topic model fitted on alpha and beta only (so gamma is outside it), in this test's own models folder."""
    from alex.core import topics
    topics.configure(tmp_path / "topics")
    m = topics.build(View(lib, ["alpha", "beta"]), topics.clean_cfg({"unit": "chunk", "chunk_words": 60, "k": 3, "min_df": 2, "runs": 1}), "Two books")
    yield m
    topics.configure(lib.data_dir / "topics")


def test_a_topic_is_its_share_of_the_samples_words(view, books, model):
    from alex.core.topics.page import Topic
    T = Topic(model["id"], 0)
    vals, note = run(view, books, {"kind": "topic", "model": model["id"], "topic": 1})
    for r, value in zip(books.rows, vals):
        if r["book"] == "gamma":
            assert value is None
            continue
        iw, num, den = cindex(view.bd[r["book"]])["isword"], 0.0, 0
        for i in T.by_book[r["book"]]:
            d = T.docs[i]
            n = sum(iw[d["start"]:d["end"] + 1])
            num, den = num + n * T.theta[i, 1], den + n
        assert value == pytest.approx(100 * num / den)
    assert "covers 2 of the 3 books (not gamma)" in note and "1 of 3 cases" in note


def test_the_topics_of_a_book_add_up_to_all_its_words(view, books, model):
    total = [sum(run(view, books, {"kind": "topic", "model": model["id"], "topic": t})[0][0] for t in range(3))]
    assert total[0] == pytest.approx(100, abs=0.1)                                         # a document's shares sum to 1 (rounded in storage)


def test_a_topic_variable_in_participants_and_its_label(told, model):
    v, w, h = told
    c = cs.build(v, {"kind": "participants", "sample": "speech", **ALL})
    vals, note = run(v, c, {"kind": "topic", "model": model["id"], "topic": 0})
    assert note is None and all(x is not None for x in vals)                              # alpha only: the model covers it
    t = vb.table(v, c, [{"kind": "topic", "model": model["id"], "topic": 0}])["variables"][0]
    assert t["label"].startswith("Topic 1: ") and t["measure"] == "% of words"


def test_a_missing_model_or_topic_says_so(view, books, model):
    assert "no longer exists" in run(view, books, {"kind": "topic", "model": "gone-123", "topic": 0})[1]
    assert "has 3 topics" in run(view, books, {"kind": "topic", "model": model["id"], "topic": 7})[1]


def test_the_options_list_models_sharing_books(client, view, model):
    o = client.post("/api/stats/options", json={"books": view.books}).json()
    m = next(x for x in o["topics"] if x["id"] == model["id"])
    assert m["covers"] == ["alpha", "beta"] and m["all"] is False and len(m["topics"]) == 3
    assert client.post("/api/stats/options", json={"books": ["gamma"]}).json()["topics"] == []


# ---------- sound and rhythm ----------
needs_dict = pytest.mark.skipif(not __import__("alex.core.sound", fromlist=["sound"]).available(), reason="cmudict isn't installed")


@needs_dict
@pytest.mark.parametrize("figure", ["stressed", "npvi", "cad_cursus", "alliteration_runs", "class_sibilants"])
def test_sound_of_whole_books_is_that_of_arcs_and_style(view, books, figure):
    from alex.core import prosody
    got = run(view, books, {"kind": "sound", "figure": figure})[0]
    cfg = prosody.config(view.lib.state["settings"])
    for r, value in zip(books.rows, got):
        bd = view.bd[r["book"]]
        assert value == pytest.approx(prosody.figures(prosody.span_tally(bd, 0, bd.n_tokens - 1, cfg))[figure])


@needs_dict
def test_a_sound_figure_can_be_one_phoneme(view, books):
    from alex.core import prosody
    got = run(view, books, {"kind": "sound", "figure": "phone:S"})[0]
    bd = view.bd["alpha"]
    t = prosody.span_tally(bd, 0, bd.n_tokens - 1, prosody.config({}))
    assert got[0] == pytest.approx(1000 * t["phones"]["S"] / t["words"]) and vb.label(view, vb.check({"kind": "sound", "figure": "phone:S"})) == "Sound S per 1,000 words"


@needs_dict
def test_sound_of_speech_is_that_of_the_quotes(told):
    from alex.core import prosody
    v, w, h = told
    c = cs.build(v, {"kind": "participants", "sample": "speech", **ALL})
    got = dict(zip((r["id"] for r in c.rows), run(v, c, {"kind": "sound", "figure": "stressed"})[0]))
    bd = v.bd["alpha"]
    mine = [[t for t in range(r["start"], r["end"] + 1) if bd.quote_at.get(t) == r["qi"]]       # a quote's span, punctuation and all
            for r in dl.bdlg(v, "alpha")["recs"] if r["speaker"] == 1]
    t = prosody.tally(bd, mine)
    assert got[h] == pytest.approx(prosody.figures(t)["stressed"])


@needs_dict
def test_the_cases_tallies_are_counted_once_per_setting(view, books, monkeypatch):
    from alex.core import prosody
    calls = []
    real = prosody.tally
    monkeypatch.setattr(prosody, "tally", lambda *a, **k: calls.append(1) or real(*a, **k))
    run(view, books, {"kind": "sound", "figure": "stressed"})
    n = len(calls)
    run(view, books, {"kind": "sound", "figure": "npvi"})
    assert len(calls) == n == len(view.books)                 # one tally per book, shared by the second variable
    narrow = run(view, books, {"kind": "sound", "figure": "alliteration_share"})[0]
    view.lib.state["settings"]["sound"] = {"window": 20, "boundary": "none"}          # a new setting: counted again
    wide = run(view, books, {"kind": "sound", "figure": "alliteration_share"})[0]
    assert len(calls) == 2 * n and narrow != wide


def test_sound_figures_are_checked_and_need_running_text(view):
    with pytest.raises(ValueError, match="Unknown sound"):
        vb.check({"kind": "sound", "figure": "loudness"})
    with pytest.raises(ValueError, match="Unknown sound"):
        vb.check({"kind": "sound", "figure": "phone:Q"})
    found = cs.build(view, {"kind": "participants", "sample": "findings", **ALL})
    values, note = run(view, found, {"kind": "sound", "figure": "stressed"})
    assert set(values) == {None} and "running text" in note


def test_sound_without_the_dictionary_says_how_to_install_it(view, books, monkeypatch):
    from alex.core import sound
    monkeypatch.setattr(sound, "available", lambda: False)
    values, note = run(view, books, {"kind": "sound", "figure": "stressed"})
    assert set(values) == {None} and "alex-booknlp-analyser[sound]" in note
    assert layers.options(view)["sound_ready"] is False and "stressed" in layers.options(view)["sound"]
