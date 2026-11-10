"""Prosody: rhythm, cadences, sound runs and the sound profile, counted by hand on tiny books whose stresses are set by corrections."""
from __future__ import annotations

import pytest

from alex.core import prosody as P
from alex.core import sound
from fixture import tiny_book

needs_dict = pytest.mark.skipif(not sound.available(), reason="the optional cmudict package isn't installed")


def words(*ws, pos="NOUN"):
    """A sentence of words, all of one class; "," "." and the like are punctuation."""
    return [(w, "PUNCT" if w in P.PAUSES or w in (".", "!") else pos) for w in ws]


def whole(bd):
    """Every sentence of a book as units."""
    return P.sentence_units(bd, 0, bd.n_tokens - 1)


# ---------- no dictionary needed ----------
@pytest.mark.parametrize("syllables,pattern,kind", [("10010", "10010", "planus"), ("0110010", "10010", "planus"),
                                                    ("100100", "100100", "tardus"), ("01000010", "1000010", "velox"),
                                                    ("100010", "100010", "trispondaicus"), ("0101", "101", "other"),
                                                    ("0100", "", None), ("", "", None)])
def test_a_cadence_runs_from_the_last_but_one_stress(syllables, pattern, kind):
    assert P.cadence_of(syllables) == pattern
    if kind:
        assert P.cadence_type(pattern) == kind


def test_the_window_and_boundary_are_checked():
    assert P.check_window(3) == 3 and P.check_window(10 ** 9) == 10 ** 9 and P.check_window(4.0) == 4
    for bad in (0, -1, 2.5, True, "3", None, float("inf"), float("-inf"), float("nan")):
        with pytest.raises(ValueError, match="whole number"):
            P.check_window(bad)
    assert P.config({"sound": {"window": float("inf")}})["window"] == P.DEFAULTS["window"]     # a hand-edited settings file
    assert [P.check_boundary(b) for b in P.BOUNDARIES] == list(P.BOUNDARIES)
    with pytest.raises(ValueError, match="sentence, paragraph or none"):
        P.check_boundary("chapter")


def test_an_empty_tally_has_no_figures_and_tallies_add_up():
    assert set(P.figures(P.empty())) == set(P.FIGURES) and all(v is None for v in P.figures(P.empty()).values())
    a, b = P.empty(), P.empty()
    a["words"], b["words"] = 3, 4
    a["cadences"]["10010"], b["cadences"]["10010"] = 1, 2
    s = P.add(a, b)
    assert s["words"] == 7 and s["cadences"]["10010"] == 3 and a["cadences"]["10010"] == 1


def test_the_fixture_book_is_cut_into_sentence_units(view):
    bd = view.bd["alpha"]
    units = whole(bd)
    assert [t for u in units for t in u] == list(range(bd.n_tokens))
    assert len(units) == len(bd.sent_bounds)
    a, b = bd.sent_bounds[3]
    cut = P.sentence_units(bd, a + 1, b + 2)                              # a part of one sentence and the start of the next
    assert cut[0] == list(range(a + 1, b + 1)) and cut[1] == [b + 1, b + 2]


# ---------- rhythm ----------
STRESS = {"aa": "1", "bb": "1", "cc": "000", "dd": "10", "ee": "0", "ff": "100"}     # each word's stress, set by correction


@needs_dict
def test_rhythm_is_counted_within_a_phrase(tmp_path):
    bd = tiny_book(tmp_path / "b", [words("aa", "bb", "cc", "dd")])         # 1 1 000 10 -> 1100010
    t = P.tally(bd, whole(bd), STRESS)
    assert (t["syllables"], t["stressed"], t["sounded"], t["words"]) == (7, 3, 4, 4)
    assert t["clashes"] == 1 and t["lapses"] == 1
    assert t["gaps"] == {0: 1, 3: 1}                                     # stresses 1 and 4 syllables apart
    assert t["pvi_pairs"] == 1 and t["pvi_sum"] == pytest.approx(3 / 2.5)
    assert t["cadences"] == {"100010": 1} and t["ends"] == {"100010": 1}  # the unit's end is a sentence end
    f = P.figures(t)
    assert f["stressed"] == pytest.approx(300 / 7) and f["syl_word"] == pytest.approx(7 / 4) and f["syl_unit"] == 7
    assert f["clashes"] == pytest.approx(100 / 7) and f["npvi"] == pytest.approx(120)
    assert f["cad_trispondaicus"] == 100 and f["cad_cursus"] == 100 and f["cad_planus"] == 0
    assert f["binary"] == 0 and f["ternary"] == 0 and f["guessed"] == 0


@needs_dict
def test_pauses_end_phrases_and_a_word_without_letters_is_a_gap(tmp_path):
    bd = tiny_book(tmp_path / "b", [words("aa", "dd", ",", "ff", "dd", "!"), words("aa", "ee", "1889", "aa", "bb")])
    t = P.tally(bd, whole(bd), STRESS)
    # first sentence: "110" closed by ",", then "10010" (planus) closed by "!"
    # second sentence: "10" | gap | "11": stress isn't followed across the gap, and the cadence is the last segment's ("11")
    assert t["cadences"] == {"110": 1, "10010": 1, "11": 1}
    assert t["ends"] == {"10010": 1, "11": 1}                             # "," isn't a sentence end
    assert t["clashes"] == 2                                              # aa dd (in "110") and aa bb; not ee . aa across the gap
    assert t["coverage"] == {"yours": 8, "none": 1} and t["words"] == 9


@needs_dict
def test_a_hyphen_doesnt_end_a_phrase_but_a_dash_does(tmp_path):
    bd = tiny_book(tmp_path / "b", [[("aa", "NOUN"), ("-", "PUNCT"), ("ee", "NOUN"), ("aa", "NOUN"), ("--", "PUNCT"), ("aa", "NOUN")]])
    t = P.tally(bd, whole(bd), STRESS)
    assert t["cadences"] == {"101": 1} and t["gaps"] == {1: 1}


@needs_dict
def test_function_words_lose_their_stress_in_the_rhythm(tmp_path):
    bd = tiny_book(tmp_path / "b", [[("The", "DET"), ("dog", "NOUN"), ("of", "ADP"), ("the", "DET"), ("moor", "NOUN")]])
    t = P.tally(bd, whole(bd))
    assert t["cadences"] == {"1001": 1} and t["stressed"] == 2


# ---------- sound runs ----------
@needs_dict
def test_alliteration_chains_words_within_the_window(tmp_path):
    bd = tiny_book(tmp_path / "b", [words("big", "bad", "dog", "bag")])
    t = P.tally(bd, whole(bd), keep=True)
    assert t["alliteration_runs"] == 1 and t["alliteration_words"] == 3 and t["alliteration_eligible"] == 4
    assert [(k, toks) for kind, k, toks in t["found"] if kind == "alliteration"] == [("B", [0, 1, 3])]
    narrow = P.tally(bd, whole(bd), window=1)
    assert narrow["alliteration_runs"] == 1 and narrow["alliteration_words"] == 2          # bag is two content words after bad
    f = P.figures(t)
    assert f["alliteration_runs"] == 250 and f["alliteration_share"] == 75 and f["alliteration_length"] == 3


@needs_dict
def test_function_words_and_repeats_dont_make_runs(tmp_path):
    bd = tiny_book(tmp_path / "b", [[("big", "ADJ"), ("but", "CCONJ"), ("big", "ADJ"), ("dog", "NOUN")]])
    t = P.tally(bd, whole(bd))
    assert t["alliteration_runs"] == 0 and t["alliteration_eligible"] == 3
    assert t["repetition_runs"] == 1 and t["repetition_words"] == 2           # big ... big is a repetition instead


@needs_dict
@pytest.mark.parametrize("boundary,runs,linked", [("sentence", 0, 0), ("paragraph", 1, 2), ("none", 1, 3)])
def test_runs_stop_at_the_chosen_boundary(tmp_path, boundary, runs, linked):
    bd = tiny_book(tmp_path / "b", [words("big", "dog", "."), words("bad", "cat", "."), words("bag", ".")], paras=[0, 0, 1])
    t = P.tally(bd, whole(bd), window=5, boundary=boundary)
    assert t["alliteration_runs"] == runs and t["alliteration_words"] == linked


@needs_dict
def test_runs_stop_where_the_sample_skips_words(tmp_path):
    bd = tiny_book(tmp_path / "b", [words("big", "dog", "bad")])
    assert P.tally(bd, [[0, 1, 2]])["alliteration_runs"] == 1
    assert P.tally(bd, [[0], [2]])["alliteration_runs"] == 0              # "dog" is left out of the sample between them
    assert P.tally(bd, [[0, 2]])["alliteration_runs"] == 0


@needs_dict
def test_rhyme_assonance_and_consonance(tmp_path):
    bd = tiny_book(tmp_path / "b", [words("sound", "round", "."), words("man", "town", "."), words("cat", "lamp", ".")])
    t = P.tally(bd, whole(bd), keep=True)
    found = {(kind, toks[0]) for kind, _, toks in t["found"]}
    assert ("rhyme", 0) in found and ("assonance", 0) in found
    assert ("consonance", 0) not in found                                 # the same last vowel: closer to rhyme
    assert ("consonance", 3) in found and ("rhyme", 3) not in found       # man, town: N after different vowels
    assert ("assonance", 6) in found and ("rhyme", 6) not in found        # cat, lamp: AE


@needs_dict
@pytest.mark.parametrize("how,runs", [("stressed", [("G", ["begin", "gold"])]), ("sound", [("B", ["begin", "bag"])]),
                                      ("letter", [("b", ["begin", "bag"])])])
def test_alliteration_by_the_stressed_syllable_the_first_sound_or_the_first_letter(tmp_path, how, runs):
    bd = tiny_book(tmp_path / "b", [words("begin", "bag", "gold")])             # beGIN: stressed on G, begins with B
    t = P.tally(bd, whole(bd), keep=True, alliteration=how)
    assert [(k, [bd.word[i] for i in toks]) for kind, k, toks in t["found"] if kind == "alliteration"] == runs


@needs_dict
def test_alliteration_by_sound_and_by_letter_differ(tmp_path):
    bd = tiny_book(tmp_path / "b", [words("cat", "city", "."), words("knight", "night", "."), words("Grimpen", "grim", ".")])
    found = lambda how: sorted(k for kind, k, _ in P.tally(bd, whole(bd), keep=True, alliteration=how)["found"] if kind == "alliteration")
    assert found("sound") == ["N"]                          # knight, night (cat/city: K/S; Grimpen is guessed, so has no sound)
    assert found("letter") == ["c", "g"]                    # cat, city; Grimpen, grim (a guessed word has letters)
    letter = P.tally(bd, whole(bd), alliteration="letter")
    assert letter["alliteration_eligible"] == 6 and P.tally(bd, whole(bd))["alliteration_eligible"] == 5


WALKS = [[("walk", "VERB"), ("walked", "VERB", "walk"), ("the", "DET"), ("dog", "NOUN"), ("the", "DET")]]


@needs_dict
@pytest.mark.parametrize("how,repeats,alliteration", [("lemma", [["walk", "walked"]], 0), ("form", [], 1),
                                                       ("all", [["the", "the"], ["walk", "walked"]], 0)])
def test_repetition_is_the_same_lemma_form_or_word(tmp_path, how, repeats, alliteration):
    bd = tiny_book(tmp_path / "b", WALKS)
    t = P.tally(bd, whole(bd), keep=True, repetition=how)
    assert sorted([bd.word[i] for i in toks] for kind, _, toks in t["found"] if kind == "repetition") == repeats
    assert t["repetition_eligible"] == (5 if how == "all" else 3)
    # a repeat (as the setting says) is not alliteration: walk, walked alliterate only when they count as different words
    assert t["alliteration_runs"] == alliteration
    f = P.figures(t)
    assert f["repetition_runs"] == 1000 * len(repeats) / 5 and f["repetition_share"] == pytest.approx(100 * 2 * len(repeats) / t["repetition_eligible"])


@needs_dict
@pytest.mark.parametrize("word,onset", [("street", "S"), ("assistance", "S"), ("explain", "S"), ("begin", "G"), ("about", "B"),
                                        ("apple", None), ("Holmes", "HH")])
def test_alliteration_is_on_the_stressed_syllable(word, onset):
    assert P._keys(sound.pronounce(word, "NOUN"))["alliteration"] == onset


# ---------- the sound profile ----------
@needs_dict
def test_the_profile_counts_consonants_and_stressed_vowels(tmp_path):
    bd = tiny_book(tmp_path / "b", [[("the", "DET"), ("cat", "NOUN"), ("sees", "VERB")]])
    t = P.tally(bd, whole(bd))
    # the: DH (its vowel unstressed in context); cat: K AE1 T; sees: S IY1 Z
    assert t["phones"] == {"DH": 1, "K": 1, "AE": 1, "T": 1, "S": 1, "IY": 1, "Z": 1}
    assert t["classes"] == {"fricatives": 3, "sibilants": 2, "plosives": 2, "short_vowels": 1, "long_vowels": 1}
    assert P.figures(t)["class_plosives"] == pytest.approx(2000 / 3)
    assert P.phoneme_rates(t)[0][1] == pytest.approx(1000 / 3)


@needs_dict
def test_the_fixture_books_have_every_figure(view):
    for b in view.books:
        bd = view.bd[b]
        f = P.figures(P.tally(bd, whole(bd)))
        assert all(v is not None for k, v in f.items() if not k.endswith("_length")), b
        assert 0 < f["stressed"] < 100 and f["syl_word"] >= 1


# ---------- settings, kept tallies and the table ----------
def test_the_workspace_settings_fill_in_the_defaults():
    assert P.config({}) == {"window": 3, "boundary": "sentence", "alliteration": "stressed", "repetition": "lemma", "corrections": {}}
    given = {"window": 7, "boundary": "none", "alliteration": "letter", "repetition": "all", "corrections": {"grimpen": "01"}}
    assert P.config({"sound": given}) == given
    damaged = {"window": 0, "boundary": "chapter", "alliteration": "rhyme", "repetition": 3, "corrections": []}
    assert P.config({"sound": damaged}) == P.config({})                                                   # damaged: the defaults
    assert P.config({"sound": "loud"}) == P.config(None) == P.config({})
    assert len({P.signature(P.config({"sound": x})) for x in ({}, {"window": 4}, {"alliteration": "letter"}, {"repetition": "form"})}) == 4
    for check, bad in ((P.check_alliteration, "first"), (P.check_repetition, "word")):
        with pytest.raises(ValueError):
            check(bad)


def test_figures_are_named_and_read_one_by_one():
    assert P.is_figure("npvi") and P.is_figure("phone:S") and not P.is_figure("phone:Q") and not P.is_figure(3)
    assert P.label("npvi") == P.FIGURES["npvi"] and P.label("phone:ZH") == "Sound ZH per 1,000 words"
    assert [f["k"] for f in P.figure_list()] == list(P.FIGURES) and P.figure_list()[1]["dec"] == 2
    t = P.empty()
    assert P.value(t, "npvi") is None and P.value(t, "phone:S") is None


@needs_dict
def test_a_stretch_is_tallied_once_per_setting(view):
    bd, cfg = view.bd["alpha"], P.config({})
    t = P.span_tally(bd, 0, 200, cfg)
    assert P.span_tally(bd, 0, 200, cfg) is t
    assert t == P.tally(bd, P.sentence_units(bd, 0, 200))
    assert P.span_tally(bd, 0, 200, P.config({"sound": {"window": 9}})) is not t


@needs_dict
def test_the_table_has_a_row_per_book_or_segment(view):
    cfg = P.config({})
    books = P.table(view, None, "book", cfg)
    assert [r["book"] for r in books["rows"]] == view.books and books["figures"] == P.figure_list()
    whole = P.span_tally(view.bd["alpha"], 0, view.bd["alpha"].n_tokens - 1, cfg)
    assert books["rows"][0]["words"] == whole["words"] and books["rows"][0]["npvi"] == pytest.approx(P.figures(whole)["npvi"])
    segs = P.table(view, {"mode": "slices", "n": 4}, "segment", cfg)
    assert len(segs["rows"]) == 4 * len(view.books) and segs["info"]
    assert sum(r["words"] for r in segs["rows"] if r["book"] == "alpha") == whole["words"]


def test_the_table_needs_the_dictionary(view, monkeypatch):
    monkeypatch.setattr(sound, "available", lambda: False)
    with pytest.raises(RuntimeError, match=r"\[sound\]"):
        P.table(view, None, "book", P.config({}))
