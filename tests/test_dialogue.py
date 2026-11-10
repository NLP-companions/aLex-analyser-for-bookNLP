"""Dialogue: quotes, speakers, speech verbs, addressees, conversations, narrators and your corrections."""
from __future__ import annotations

import shutil

import pytest

from alex.core import dialogue as dl
from alex.core import narrative as nar
from alex.core import wordchoice
from alex.core.corpus import cindex
from alex.core.library import Library
from alex.core.view import View

HOLMES = {"alpha": 1, "beta": 5, "gamma": 3}
WATSON = {"alpha": 2, "beta": 6, "gamma": 4}


def unit(view, book, coref):
    return view.member_unit[(book, coref)]


def reference_conversations(bd, gap):
    """Conversation boundaries computed straight from token positions: a new one starts when more than
    `gap` words lie between the end of one quote and the start of the next."""
    ci = cindex(bd)
    word = [1 if w else 0 for w in ci["isword"]]
    prefix = [0]
    for w in word:
        prefix.append(prefix[-1] + w)
    qs = sorted(bd.quotes, key=lambda q: q["start"])
    sizes, cur = [], 1
    for prev, q in zip(qs, qs[1:]):
        if prefix[q["start"]] - prefix[prev["end"] + 1] > gap:
            sizes.append(cur)
            cur = 1
        else:
            cur += 1
    return sizes + [cur]


def test_quotes_and_words_per_speaker_match_the_generator(view, truth):
    for b, t in truth.items():
        d = dl.bdlg(view, b)
        by = {}
        for r in d["recs"]:
            by.setdefault(r["speaker"], []).append(r)
        assert {c: len(v) for c, v in by.items()} == dict(t.quotes)
        assert {c: sum(r["n"] for r in v) for c, v in by.items()} == dict(t.quote_words)
        assert d["dlg_words"] == t.dialogue_words and d["words"] == t.words


def test_every_quote_has_its_speech_verb_from_the_speaker_mention(view):
    for b in view.books:
        for r in dl.bdlg(view, b)["recs"]:
            assert r["verb"] == "say" and r["verb_method"] == "subject" and r["adverbs"] == []


def test_a_verb_the_speaker_is_subject_of_must_be_a_speech_verb(view, monkeypatch):
    bd = view.bd["alpha"]
    quotes = [q for q in bd.quotes if q.get("mstart") is not None]
    assert quotes and all(dl._speech_verb(bd, q)[1] == "subject" for q in quotes)
    monkeypatch.setattr(dl, "SPEECH_VERBS", set())              # "said" is no longer on the list...
    monkeypatch.setattr(bd, "ss", {})                            # ...nor has it the communication supersense: like "Holmes rose."
    assert all(dl._speech_verb(bd, q) == (None, None) for q in quotes)


def test_a_speech_verb_inside_a_quote_never_introduces_one(view):
    bd = view.bd["alpha"]
    q = next(q for q in bd.quotes if q.get("mstart") is not None)
    verb, _ = dl._speech_verb(bd, q)
    assert verb not in bd.quote_at                                # found in the narration...
    bd.quote_at[verb] = 0                                         # ...and not any more once a quote covers it
    try:
        assert dl._speech_verb(bd, q)[0] != verb
    finally:
        del bd.quote_at[verb]


def test_a_speech_verb_introduces_at_most_one_quote(view):
    for b in view.books:
        verbs = [r["verb_tok"] for r in dl.bdlg(view, b)["recs"] if r["verb_tok"] is not None]
        assert len(verbs) == len(set(verbs))
    bd = view.bd["alpha"]
    a, c = bd.quotes[0], bd.quotes[1]
    shared = a["end"] + 1                                          # pretend one verb token was found for two quotes
    answers = {0: (shared, "near"), 1: (shared, "subject")}
    orig = dl._speech_verb
    dl._speech_verb = lambda bd_, q, skip: answers[bd_.quotes.index(q)]
    try:
        assert dl._claim_verbs(bd, [0, 1], frozenset()) == {1: (shared, "subject")}       # "subject" beats "near"
        answers[0] = (shared, "subject")
        assert len(dl._claim_verbs(bd, [0, 1], frozenset())) == 1         # otherwise the closer, then the earlier quote
    finally:
        dl._speech_verb = orig


def test_left_out_verbs_and_adverbs_never_count(lib, view):
    assert dl.speech_skip({}) == {"verbs": [], "adverbs": []}
    assert dl.speech_skip({"speech_skip": {"verbs": ["b", "a", "a"]}}) == {"verbs": ["a", "b"], "adverbs": []}
    before = dl.verbs(view)
    assert before["with_verb"] == before["quotes"] > 0
    lib.state["settings"]["speech_skip"] = {"verbs": ["say"], "adverbs": ["quietly"]}
    lib.version += 1                                             # what saving the settings does: views are built anew
    after = dl.verbs(View(lib, view.books))
    assert after["with_verb"] == 0 and after["verbs"] == []     # every quote's verb is "say": none is left


def test_stop_adverbs_cover_time_place_and_degree():
    assert {"soon", "presently", "far", "exactly", "perhaps", "very"} <= dl.STOP_ADV and "quietly" not in dl.STOP_ADV


def test_speech_verb_falls_back_to_the_nearest_verb_when_the_speaker_is_unknown(tmp_path, corpus, lib):
    folder = tmp_path / "exports" / "gamma-20260103-000000"
    shutil.copytree(next(corpus[0].glob("gamma-*")), folder)
    q = folder / "gamma.quotes"
    rows = [l.split("\t") for l in q.read_text().splitlines()]
    for r in rows[1:]:
        r[2] = r[3] = ""              # BookNLP found no mention for the speaker
    q.write_text("\n".join("\t".join(r) for r in rows) + "\n", encoding="utf-8")
    lib2 = Library(data_dir=tmp_path / "d2", sources=[tmp_path / "exports"])
    recs = dl.bdlg(View(lib2, ["gamma"]), "gamma")["recs"]
    assert recs and all(r["verb"] == "say" and r["verb_method"] == "near" for r in recs)


def test_conversations_follow_the_narration_gap(view, lib):
    for gap in (0, 20, 100, 10 ** 6):
        lib.state["settings"]["conv_gap"] = gap
        v = View(lib, ["alpha", "beta", "gamma"])
        for b in v.books:
            d = dl.bdlg(v, b)
            assert [len(c) for c in d["convs"]] == reference_conversations(v.bd[b], gap)
    assert len(dl.bdlg(View(lib, ["gamma"]), "gamma")["convs"]) == 1


def test_a_named_addressee_is_found(view, truth):
    for b in view.books:
        recs = dl.bdlg(view, b)["recs"]
        named = [r for r in recs if r["addr_method"] == "named"]
        assert len(named) == sum(v for (sp, other), v in truth[b].vocatives.items())
        for r in named:
            assert r["addressee"] == (WATSON[b] if r["speaker"] == HOLMES[b] else HOLMES[b])


def test_other_quotes_get_reply_continues_or_next_addressees(view):
    for b in view.books:
        for conv in dl.bdlg(view, b)["convs"]:
            for i, r in enumerate(conv):
                if r["addr_method"] == "reply":
                    assert conv[i - 1]["speaker"] not in (None, r["speaker"]) and r["addressee"] == conv[i - 1]["speaker"]
                if r["addr_method"] == "continues":
                    assert conv[i - 1]["speaker"] == r["speaker"] and r["addressee"] == conv[i - 1]["addressee"]
                if r["addr_method"] == "next":
                    assert i == 0 and r["addressee"] in [x["speaker"] for x in conv[1:]]


def test_your_corrections_replace_estimates(lib, truth):
    v = View(lib, ["alpha"])
    r0 = dl.bdlg(v, "alpha")["recs"][0]
    key = r0["key"]
    w = unit(v, "alpha", 2)
    lib.ann_book("alpha")["addressees"][key] = [w]
    lib.save_ann()
    v = View(lib, ["alpha"])
    r = dl.bdlg(v, "alpha")["recs"][0]
    assert dl.addressees(v, "alpha", r) == ([w], "yours")
    lib.ann_book("alpha")["addressees"][key] = ["*"]
    lib.save_ann()
    v = View(lib, ["alpha"])
    ids, meth = dl.addressees(v, "alpha", dl.bdlg(v, "alpha")["recs"][0])
    assert meth == "yours_all" and set(ids) == {u for u in dl.participants(v, "alpha", 0)[0]} - {unit(v, "alpha", r["speaker"])}


def test_the_entity_page_counts_the_addressees_you_set(lib):
    """`entity()["corrected"]`: a quote whose addressees you set counts as `spoken` for its speaker and as `heard` for
    the addressee; nothing is counted before any correction."""
    v = View(lib, ["alpha"])
    r0 = dl.bdlg(v, "alpha")["recs"][0]
    speaker = unit(v, "alpha", r0["speaker"])
    other = next(u for u in v.units if u != speaker and u.startswith("e:alpha:") and dl.entity(v, u))
    assert dl.entity(v, speaker)["corrected"] == {"spoken": 0, "heard": 0}
    lib.ann_book("alpha")["addressees"][r0["key"]] = [other]
    lib.save_ann()
    v = View(lib, ["alpha"])
    assert dl.entity(v, speaker)["corrected"] == {"spoken": 1, "heard": 0}
    assert dl.entity(v, other)["corrected"] == {"spoken": 0, "heard": 1}


def test_splitting_and_joining_conversations(lib):
    lib.state["settings"]["conv_gap"] = 20        # short enough for alpha to fall into several conversations
    v = View(lib, ["alpha"])
    d = dl.bdlg(v, "alpha")
    n = len(d["convs"])
    inside = d["convs"][0][1]["key"] if len(d["convs"][0]) > 1 else None
    assert inside, "the first conversation should have at least two quotes"
    lib.ann_book("alpha")["splits"] = [inside]
    lib.save_ann()
    assert len(dl.bdlg(View(lib, ["alpha"]), "alpha")["convs"]) == n + 1
    lib.ann_book("alpha")["splits"] = []
    first_of_second = d["convs"][1][0]["key"]
    lib.ann_book("alpha")["merges"] = [first_of_second]
    lib.save_ann()
    assert len(dl.bdlg(View(lib, ["alpha"]), "alpha")["convs"]) == n - 1


def test_participants_add_and_remove(lib):
    v = View(lib, ["alpha"])
    d = dl.bdlg(v, "alpha")
    first = d["convs"][0][0]["key"]
    lib.ann_book("alpha")["participants"][first] = {"add": ["e:alpha:10"], "remove": [unit(v, "alpha", 2)]}
    v = View(lib, ["alpha"])
    parts, speakers, edit = dl.participants(v, "alpha", 0)
    assert "e:alpha:10" in parts and unit(v, "alpha", 2) not in parts and unit(v, "alpha", 2) in speakers


def test_overview_matches_the_generator(view, truth):
    o = dl.overview(view)
    assert o["dialogue_words"] == sum(t.dialogue_words for t in truth.values())
    assert [b["quotes"] for b in o["books"]] == [sum(truth[b].quotes.values()) for b in ("alpha", "beta", "gamma")]
    assert all(b["attributed"] == 100 for b in o["books"]) and o["unattributed"] == {"quotes": 0, "words": 0}
    holmes_alpha = next(r for r in o["speakers"] if r["name"] == "Holmes" and r["id"] == unit(view, "alpha", 1))
    assert holmes_alpha["quotes"] == truth["alpha"].quotes[1] and holmes_alpha["said"] == 100
    assert sum(r["share"] for r in o["speakers"]) == pytest.approx(100)
    assert len(o["time"][0]["values"]) == 50


def test_style_measures(view, truth):
    pairs = [(b, r) for b, r in dl.all_recs(view) if r["speaker"] == HOLMES[b]]
    s = dl.style(pairs)
    q = sum(truth[b].quotes[HOLMES[b]] for b in truth)
    w = sum(truth[b].quote_words[HOLMES[b]] for b in truth)
    assert s["quotes"] == q and s["words"] == w and s["per_quote"] == pytest.approx(w / q)
    non_voc = sum(t.agent[HOLMES[b]]["see"] for b, t in truth.items())      # "I see the …": one "I" each
    assert s["i"] == pytest.approx(1000 * non_voc / w)
    assert s["questions"] == 0 and s["exclaims"] == 0 and s["you"] == 0
    assert dl.style([])["quotes"] == 0


def test_mattr():
    assert dl.mattr([]) == (None, False)
    ttr, ok = dl.mattr(["a", "b", "a", "b"])
    assert ttr == 0.5 and ok is False                 # under 100 words: the plain type-token ratio
    words = ["w%d" % (i % 10) for i in range(300)]
    m, ok = dl.mattr(words)
    assert ok and m == pytest.approx(0.1)
    assert dl.mattr(["x"] * 200)[0] == pytest.approx(0.01)


def test_verbs_overall_and_for_one_speaker(view, truth):
    r = dl.verbs(view)
    assert r["verbs"][0]["item"] == "say" and r["verbs"][0]["n"] == sum(sum(t.quotes.values()) for t in truth.values())
    assert r["with_verb"] == r["quotes"] and r["methods"] == {"subject": r["quotes"]}
    h = unit(view, "alpha", 1)
    one = dl.verbs(view, {"kind": "unit", "id": h}, {})
    assert one["target"]["total"] == truth["alpha"].quotes[1] and one["target"]["verbs"][0]["pct"] == 100


def test_voice_compares_a_speaker_with_everyone_else(view):
    h = unit(view, "alpha", 1)
    r = dl.voice(view, {"kind": "unit", "id": h}, {"kind": "others"}, kw={"min_freq": 1, "show_all": True})
    assert r["target"]["quotes"] > 0 and r["reference"]["quotes"] > 0 and r["summary"]["reference"] == "all other speakers"
    words = {x["item"] for x in r["rows"]}
    assert "see" in words or "look" in words
    lem = dl.voice(view, {"kind": "unit", "id": h}, {"kind": "others"}, unit="lemma", kw={"min_freq": 1, "show_all": True})
    assert lem["summary"]["unit"] == "lemma"


def test_style_table_and_min_words(view):
    t = dl.style_table(view, 0)
    assert t["rows"] and t["all"]["quotes"] == sum(r["quotes"] for r in t["rows"])
    assert len(dl.style_table(view, 10 ** 6)["rows"]) == 0


def pos_share(view, pairs, pos):
    """The share (%) of the words of the (book, quote) pairs that have a part of speech, counted straight from the tokens."""
    words = [(b, t) for b, r in pairs for t in r["tokens"]]
    return 100 * sum(view.bd[b].pos[t] == pos for b, t in words) / len(words)


def test_word_choice_columns_are_chosen_and_off_by_default(view):
    t = dl.style_table(view, 0)
    assert t["wc_columns"] == [] and all(r["wc"] == {} for r in t["rows"]) and t["all"]["wc"] == {}
    t = dl.style_table(view, 0, choice="headline")
    assert [c["k"] for c in t["wc_columns"]] == list(wordchoice.HEADLINE) and set(t["rows"][0]["wc"]) == set(wordchoice.HEADLINE)
    t = dl.style_table(view, 0, choice="ratios")
    assert {c["k"] for c in t["wc_columns"]} == {"ratio:adj_verb", "ratio:adv_verb", "ratio:noun_verb", "ratio:mod_head"}
    with pytest.raises(ValueError):
        wordchoice.columns("nonsense")


def test_word_choice_of_a_speaker_is_taken_over_their_quotes(view):
    h = unit(view, "alpha", 1)
    row = next(r for r in dl.style_table(view, 0, choice="headline")["rows"] if r["id"] == h)
    pairs, _ = dl.recs_for(view, {"kind": "unit", "id": h})
    assert row["wc"]["pos:ADJ"] == pytest.approx(pos_share(view, pairs, "ADJ")) and row["wc"]["pos:VERB"] == pytest.approx(pos_share(view, pairs, "VERB"))
    assert row["wc"]["pos:VERB"] > 0


def test_word_choice_of_everyone_counts_each_quote_once(view):
    t = dl.style_table(view, 0, choice="headline")
    everyone = list({(b, r["qi"]): (b, r) for b, r in dl.all_recs(view) if any(u in view.units for u in dl.speaker_units(view, b, r))}.values())
    assert t["all"]["wc"]["pos:NOUN"] == pytest.approx(pos_share(view, everyone, "NOUN"))


def test_voice_has_word_choice_for_both_sides(view):
    h = unit(view, "alpha", 1)
    r = dl.voice(view, {"kind": "unit", "id": h}, {"kind": "others"}, kw={"min_freq": 1, "show_all": True}, choice="headline")
    assert set(r["target"]["wc"]) == set(r["reference"]["wc"]) == set(wordchoice.HEADLINE) and len(r["wc_columns"]) == 6
    assert dl.voice(view, {"kind": "unit", "id": h}, {"kind": "others"})["target"]["wc"] == {}


def test_the_entity_page_has_word_choice_overall_and_per_book(view):
    h = unit(view, "alpha", 1)
    e = dl.entity(view, h)
    assert set(e["wc"]) == set(e["all_wc"]) == set(wordchoice.HEADLINE) and [c["k"] for c in e["wc_columns"]] == list(wordchoice.HEADLINE)
    assert [b["book"] for b in e["per_book"]] == ["alpha"] and e["per_book"][0]["wc"]["pos:ADJ"] == pytest.approx(e["wc"]["pos:ADJ"])
    only_questions = dl.entity(view, h, types=["question"])
    assert only_questions["style"]["quotes"] < e["style"]["quotes"]                       # the filter reaches the figures too
    assert only_questions["wc"] != e["wc"] or only_questions["style"]["quotes"] == 0


def test_conversation_list_filters_by_person(view):
    allc, total = dl.conversations(view)
    assert total == sum(len(dl.bdlg(view, b)["convs"]) for b in view.books)
    ryder_less = dl.conversations(view, {"kind": "unit", "id": unit(view, "alpha", 1)})[0]
    assert ryder_less and {r["book"] for r in ryder_less} == {"alpha"}
    assert all(r["participants"] and r["opening"] for r in allc)


def test_quotes_filters(view, truth):
    h = unit(view, "alpha", 1)
    r = dl.quotes(view, {"speaker": {"kind": "unit", "id": h}})
    assert r["total"] == truth["alpha"].quotes[1] == r["shown"]
    assert all("\x01q\x02" in x["text"] for x in r["items"]) and r["items"][0]["speaker"] == "Holmes"
    assert dl.quotes(view, {"verb": "say"})["total"] == sum(sum(t.quotes.values()) for t in truth.values())
    assert dl.quotes(view, {"verb": "cry"})["total"] == 0
    assert dl.quotes(view, {"q": "watson,"})["total"] == sum(v for t in truth.values() for (sp, other), v in t.vocatives.items() if other == WATSON[next(b for b in truth if truth[b] is t)])
    assert dl.quotes(view, {"word": "see", "book": "beta"})["total"] == truth["beta"].agent[HOLMES["beta"]]["see"] + truth["beta"].agent[WATSON["beta"]]["see"]
    assert dl.quotes(view, {"attributed": "no"})["total"] == 0
    named = dl.quotes(view, {"addr_method": "named"})
    assert named["total"] == sum(v for t in truth.values() for v in t.vocatives.values())
    limited = dl.quotes(view, {}, limit=5)
    assert limited["shown"] == 5 and limited["total"] > 5
    hl = dl.quotes(view, {"word": "see"}, limit=1)["items"][0]["text"]
    assert "\x01o\x02see" in hl


def test_quotes_can_be_filtered_by_conversation(view):
    r = dl.quotes(view, {"book": "alpha", "conv": 0})
    assert r["total"] == len(dl.bdlg(view, "alpha")["convs"][0])


def test_sentence_type_from_punctuation():
    assert dl.sentence_type({"question": True, "exclaim": False, "verb": "say"}) == "question"
    assert dl.sentence_type({"question": False, "exclaim": True, "verb": "say"}) == "exclaim"
    assert dl.sentence_type({"question": False, "exclaim": False, "verb": "say"}) == "statement"


def test_sentence_type_can_weigh_the_speech_verb():
    ask = {"question": False, "exclaim": False, "verb": "ask"}
    assert dl.sentence_type(ask) == "statement"                          # punctuation only: the verb is ignored
    assert dl.sentence_type(ask, weigh_verb=True) == "question"
    cry = {"question": False, "exclaim": False, "verb": "cry"}
    assert dl.sentence_type(cry, weigh_verb=True) == "exclaim"
    both = {"question": True, "exclaim": False, "verb": "cry"}
    assert dl.sentence_type(both, weigh_verb=True) == "question"         # its own punctuation wins over the verb
    narration = {"question": False, "exclaim": False}                    # no "verb" key at all: must not crash
    assert dl.sentence_type(narration, weigh_verb=True) == "statement"


def test_quotes_style_and_entity_can_be_filtered_by_sentence_type(view):
    """The fixture's generated quotes never actually contain "?" or "!", so mark one record directly (`bdlg`'s cache
    means later calls in this test still see the change) to check the filter threads all the way through."""
    recs = dl.bdlg(view, "alpha")["recs"]
    holmes_rec = next(r for r in recs if r["speaker"] == HOLMES["alpha"])
    holmes_rec["question"] = True
    try:
        r = dl.quotes(view, {"book": "alpha", "types": ["question"]})
        assert r["total"] == 1 and r["items"][0]["type"] == "question"
        assert dl.quotes(view, {"book": "alpha", "types": ["statement"]})["total"] == len(recs) - 1
        assert dl.quotes(view, {"book": "alpha"})["total"] == len(recs)          # no filter: unaffected
        st = dl.style_table(view, 0, types=["question"])
        assert sum(row["quotes"] for row in st["rows"]) == 1
        e = dl.entity(view, unit(view, "alpha", HOLMES["alpha"]), types=["question"])
        assert e["style"]["quotes"] == 1
        assert e["verbs"] == [{"item": "say", "n": 1, "pct": 100.0}] and e["adverbs"] == []          # the verbs/adverbs tables respect the filter too
        v = dl.voice(view, {"kind": "unit", "id": unit(view, "alpha", HOLMES["alpha"])}, {"kind": "others"}, types=["question"])
        assert v["target"]["quotes"] == 1
        vb = dl.verbs(view, types=["question"])
        assert vb["quotes"] == 1 and vb["verbs"] == [{"item": "say", "n": 1, "pct": 100.0, "speakers": 1}]
        target = dl.verbs(view, {"kind": "unit", "id": unit(view, "alpha", HOLMES["alpha"])}, types=["question"])["target"]
        assert target["total"] == 1 and target["verbs"][0]["item"] == "say"
    finally:
        holmes_rec["question"] = False


def test_entity_page_data(view, truth):
    h = unit(view, "alpha", 1)
    e = dl.entity(view, h)
    assert e["style"]["quotes"] == truth["alpha"].quotes[1] and e["narrating"] is None
    assert e["talks_to"][0]["name"] == "Watson" and e["addressed_by"][0]["name"] == "Watson"
    assert e["verbs"][0]["item"] == "say" and e["presence"][0]["book"] == "alpha" and len(e["presence"][0]["bins"]) == 100
    assert e["time"][0]["book"] == "alpha" and len(e["time"][0]["values"]) == 50 and all(0 <= v <= 100 for v in e["time"][0]["values"])
    assert dl.entity(view, "e:alpha:999") is None


def test_scoped_time_is_this_scopes_own_share_of_each_slices_words(view):
    """`scoped_time` restricted to one speaker must be a share of the same word denominator as the book's own
    unscoped curve (`bdlg`'s "time"), so it's never bigger than what everybody together speaks in that slice."""
    h = unit(view, "alpha", 1)
    whole = dl.bdlg(view, "alpha")["time"]
    scoped = dl.scoped_time(view, [(b, r) for b, r in dl.all_recs(view) if b == "alpha" and h in dl.speaker_units(view, b, r)])
    assert len(scoped) == 1 and scoped[0]["book"] == "alpha" and len(scoped[0]["values"]) == 50
    assert all(sv <= wv + 1e-9 for sv, wv in zip(scoped[0]["values"], whole))
    assert dl.scoped_time(view, []) == []                                    # nobody speaks: no books at all, not a book of zeroes


def test_addressee_edges_for_the_network(view):
    edges = dl.addressee_edges(view)
    h, w = unit(view, "alpha", 1), unit(view, "alpha", 2)
    assert edges[(h, w)] > 0 and edges[(w, h)] > 0
    named_only = dl.addressee_edges(view, methods={"named"})
    assert sum(named_only.values()) <= sum(edges.values())


# ---------- narrators ----------
def test_default_narrator_is_anonymous_and_corrections_change_it(lib, truth):
    v = View(lib, ["alpha"])
    recs = dl.narration_recs(v)
    assert {r["role"] for b, r in recs} == {"nar:anon:alpha"} and dl.role_name(v, "nar:anon:alpha") == "Narrator of alpha"
    w = unit(v, "alpha", 2)
    lib.ann_book("alpha")["narrator"] = w
    lib.save_ann()
    v = View(lib, ["alpha"])
    assert {r["role"] for b, r in dl.narration_recs(v)} == {"nar:" + w} and dl.role_name(v, "nar:" + w) == "Watson, narrating"
    key = dl.keys(v.bd["alpha"])["p"][4]
    lib.ann_book("alpha")["para_narrators"][key] = "anon"
    lib.save_ann()
    v = View(lib, ["alpha"])
    exceptions = [r for b, r in dl.narration_recs(v) if r["exception"]]
    assert len(exceptions) == 1 and exceptions[0]["role"] == "nar:anon:alpha" and exceptions[0]["para"] == 4


def test_chapter_narrator_sits_between_paragraph_exceptions_and_the_books_default(lib, truth):
    """Precedence: a paragraph exception first, then a chapter exception (the whole chapter), then the book's
    default, else anonymous."""
    v = View(lib, ["alpha"])
    bd = v.bd["alpha"]
    segs, info = nar.book_segments(v, "alpha", {"mode": "chapters"})
    assert not info["fallback"] and len(segs) >= 2                    # alpha has real chapters, not a slices fallback
    ch2 = segs[1]
    ch2_start = bd.para[ch2["head"]]
    ch2_key = dl.keys(bd)["p"][ch2_start]
    ch2_pids = set(range(bd.para[ch2["start"]], bd.para[ch2["end"]] + 1))
    w = unit(v, "alpha", WATSON["alpha"])
    lib.ann_book("alpha").setdefault("chapter_narrators", {})[ch2_key] = w
    lib.save_ann()

    v = View(lib, ["alpha"])
    recs = dl.narration_recs(v)
    in_ch2 = [r for b, r in recs if r["para"] in ch2_pids]
    out_ch2 = [r for b, r in recs if r["para"] not in ch2_pids]
    assert in_ch2 and all(r["role"] == "nar:" + w and r["exception"] for r in in_ch2)
    assert out_ch2 and all(r["role"] == "nar:anon:alpha" for r in out_ch2)   # unaffected outside the chapter

    # a paragraph exception inside the chapter still wins over the chapter's own assignment
    h = unit(v, "alpha", HOLMES["alpha"])
    lib.ann_book("alpha")["para_narrators"][ch2_key] = h
    lib.save_ann()
    v = View(lib, ["alpha"])
    rec = next(r for b, r in dl.narration_recs(v) if r["para"] == ch2_start)
    assert rec["role"] == "nar:" + h and rec["exception"]

    # and the book's own default, once set, still only applies where neither exception does
    lib.ann_book("alpha")["narrator"] = w
    lib.save_ann()
    v = View(lib, ["alpha"])
    recs = dl.narration_recs(v)
    assert next(r for b, r in recs if r["para"] == ch2_start)["role"] == "nar:" + h     # paragraph exception, unchanged
    assert all(r["role"] == "nar:" + w for b, r in recs if r["para"] not in ch2_pids)   # now the book default, not anon


def test_linking_narrator_roles_pools_their_narration(lib, truth):
    """Linking two narrator roles (here two anonymous ones, which have no underlying entity to link instead) pools
    their narration under one role id, everywhere narration is grouped by role."""
    lid = lib.link_narrators("nar:anon:alpha", "nar:anon:beta")
    assert lid == "nl:1"
    v = View(lib, ["alpha", "beta"])
    by = dl._by_role(v)
    assert lid in by and "nar:anon:alpha" not in by and "nar:anon:beta" not in by
    assert dl.role_name(v, lid) == "2 narrators, linked"
    rows = dl.narrator_rows(v)
    row = next(r for r in rows if r["id"] == lid)
    assert row["linked"] is True and set(row["books"]) == {"alpha", "beta"}
    prof = dl.narrator_profile(v, lid)
    assert prof["role"]["linked"] is True and prof["role"]["anonymous"] is False and prof["role"]["unit"] is None
    assert {m["id"] for m in prof["role"]["members"]} == {"nar:anon:alpha", "nar:anon:beta"}

    lib.set_name(lid, "The Chronicler")
    assert lib.name_of(lid) == "The Chronicler"
    assert dl.role_name(View(lib, ["alpha", "beta"]), lid) == "The Chronicler"

    lib.unlink_narrator(lid[3:], "nar:anon:beta")            # one member left: the link dissolves
    v = View(lib, ["alpha", "beta"])
    by = dl._by_role(v)
    assert "nar:anon:alpha" in by and "nar:anon:beta" in by and lid not in by


def test_linking_named_narrators_carries_book_by_book_figures(lib, truth):
    """Two named characters' narrator roles, linked the same way, pool the same way (role_unit is None for a link,
    so the "what they say in dialogue" comparison — which needs one character — is skipped, unlike a plain role)."""
    v = View(lib, ["alpha", "beta"])
    h, w = unit(v, "alpha", HOLMES["alpha"]), unit(v, "beta", WATSON["beta"])
    lib.ann_book("alpha")["narrator"], lib.ann_book("beta")["narrator"] = h, w
    lib.save_ann()
    lid = lib.link_narrators("nar:" + h, "nar:" + w, name="Chronicle")
    v = View(lib, ["alpha", "beta"])
    assert dl.role_name(v, lid) == "Chronicle" and dl.role_unit(lid) is None
    prof = dl.narrator_profile(v, lid)
    assert prof is not None and prof["spoken"] is None         # no single character to compare with their own dialogue

    lib.unlink_narrators_all(lid[3:])
    v = View(lib, ["alpha", "beta"])
    by = dl._by_role(v)
    assert ("nar:" + h) in by and ("nar:" + w) in by and lid not in by


def test_narration_words_are_the_words_outside_quotes(view, truth):
    n = dl.narrators(view)
    assert n["narration_words"] == sum(t.words - t.dialogue_words for t in truth.values())
    assert sum(r["share"] for r in n["rows"]) == pytest.approx(100)


def test_keys_survive_token_renumbering(view):
    bd = view.bd["alpha"]
    k = dl.keys(bd)
    assert set(k["q"].values()) == set(k["q_rev"]) and len(k["q"]) == len(bd.quotes)
    assert all(v.endswith("#1") or "#" in v for v in k["p"].values()) and len(k["p_rev"]) == len(k["p"])


def test_unattributed_quotes_are_handled(tmp_path, corpus):
    folder = tmp_path / "exports" / "gamma-20260103-000000"
    shutil.copytree(next(corpus[0].glob("gamma-*")), folder)
    q = folder / "gamma.quotes"
    rows = [l.split("\t") for l in q.read_text().splitlines()]
    for r in rows[1:4]:
        r[5] = "-1"
    rows[4][5] = "None"
    q.write_text("\n".join("\t".join(r) for r in rows) + "\n", encoding="utf-8")
    lib2 = Library(data_dir=tmp_path / "d2", sources=[tmp_path / "exports"])
    v = View(lib2, ["gamma"])
    o = dl.overview(v)
    assert o["unattributed"]["quotes"] == 4 and o["books"][0]["attributed"] < 100
    assert dl.quotes(v, {"attributed": "no"})["total"] == 4
    dl.voice(v, {"kind": "unit", "id": unit(v, "gamma", 3)}, {"kind": "others"})
    dl.entity(v, unit(v, "gamma", 3))
