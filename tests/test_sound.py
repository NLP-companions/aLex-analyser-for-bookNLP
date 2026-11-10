"""Sound: pronunciation of words and books from the CMU Pronouncing Dictionary, guesses, your corrections, stress in context."""
from __future__ import annotations

import sys

import pytest

from alex.core import sound
from fixture import tiny_book

needs_dict = pytest.mark.skipif(not sound.available(), reason="the optional cmudict package isn't installed")

# ---------- guesses and corrections (no dictionary needed) ----------
@pytest.mark.parametrize("word,n", [("the", 1), ("candle", 2), ("table", 2), ("stone", 1), ("hound", 1), ("agree", 2), ("fly", 1), ("", 1)])
def test_syllable_estimate(word, n):
    assert sound.guess_syllables(word) == n


@pytest.mark.parametrize("text,stress", [("1 0 2", "101"), ("/x/", "101"), ("x/", "01"), ("  1  ", "1"), ("0X1", "001")])
def test_a_stress_pattern_correction_has_no_phonemes(text, stress):
    assert sound.parse_correction(text) == sound.Pron(None, stress, "yours")


def test_a_phoneme_correction_takes_its_stress_from_the_vowels():
    p = sound.parse_correction("b ae1 s k er0 v ih2 l")
    assert p.phones == ("B", "AE1", "S", "K", "ER0", "V", "IH2", "L") and p.stress == "101" and p.source == "yours"


@pytest.mark.parametrize("text,says", [("", "Type a stress pattern"), ("B AE S", "needs a stress digit"), ("B1 AE1", "only vowels"),
                                       ("Q AE1", "isn't an ARPAbet phoneme"), ("B S", "at least one vowel"), ("1" * 21, "at most 20")])
def test_a_correction_that_cant_be_read_says_why(text, says):
    with pytest.raises(ValueError, match=says):
        sound.parse_correction(text)


def test_without_the_dictionary_it_says_how_to_install_it(monkeypatch):
    monkeypatch.setitem(sys.modules, "cmudict", None)         # makes `import cmudict` fail
    monkeypatch.setattr(sound, "_DICT", None)
    assert sound.available() is False
    with pytest.raises(RuntimeError, match=r"alex-booknlp-analyser\[sound\]"):
        sound.entries()


# ---------- one word ----------
@needs_dict
def test_the_dictionary_is_read_with_its_variants():
    d = sound.entries()
    assert len(d) > 100_000 and d["holmes"][0] == "HH OW1 M Z" and len(d["record"]) == 3
    assert not any("#" in v for vs in d.values() for v in vs)


@needs_dict
def test_the_word_class_picks_between_variants():
    assert sound.pronounce("record", "NOUN").stress == "10"
    assert sound.pronounce("record", "VERB").stress == "01"
    assert sound.pronounce("record").phones == ("R", "AH0", "K", "AO1", "R", "D")      # no class: the first


@needs_dict
@pytest.mark.parametrize("word,stress,first", [("Dr.", "10", "D"), ("valour", "10", "V"), ("sombre", "10", "S"), ("realised", "101", "R"),
                                               ("gipsy", "10", "JH"), ("well-known", "11", "W"), ("Stapletons", "100", "S")])
def test_abbreviations_british_spellings_parts_and_plurals_are_found(word, stress, first):
    p = sound.pronounce(word, "NOUN")
    assert p.source == "dict" and p.stress == stress and p.phones[0] == first


@needs_dict
def test_a_plural_without_apostrophe_ends_as_s_would():
    assert sound.pronounce("Stapletons").phones[-1] == "Z"
    assert sound.pronounce("Grimpens").source == "guess"                     # the base isn't listed either


@needs_dict
def test_unknown_words_are_guessed_and_words_without_letters_have_none():
    assert sound.pronounce("Grimpen") == sound.Pron(None, "10", "guess")
    assert sound.pronounce("1889") is None


@needs_dict
def test_your_correction_comes_first():
    assert sound.pronounce("Grimpen", overrides={"grimpen": "0 1"}) == sound.Pron(None, "01", "yours")
    assert sound.pronounce("holmes", overrides={"Holmes": "HH OW1 L M Z"}).phones == ("HH", "OW1", "L", "M", "Z")
    assert sound.pronounce("Grimpen", overrides={"grimpen": "nonsense!"}).source == "guess"     # an unreadable one is skipped


# ---------- a book ----------
SENTENCES = [[("The", "DET"), ("dog", "NOUN"), ("of", "ADP"), ("Holmes", "PROPN"), ("'s", "PART"), ("friend", "NOUN"),
              ("did", "AUX"), ("n't", "PART"), ("bark", "VERB"), (".", "PUNCT")],
             [("It", "PRON"), ("’s", "AUX"), ("Grimpen", "PROPN"), ("in", "ADP"), ("1889", "NUM"), ("!", "PUNCT")]]


@needs_dict
def test_a_book_gets_stress_in_context(tmp_path):
    bd = tiny_book(tmp_path / "b", SENTENCES)
    pr = sound.book_prons(bd)
    assert len(pr) == bd.n_tokens
    marks = [p.stress if p is not None else None for p in pr]
    # function words unstressed (the dictionary has "of" stressed), content words stressed; Holmes's gains a syllable; didn't keeps
    # its stress (a negative); the clitics are joined to the word before; punctuation and 1889 have no pronunciation
    assert marks == ["0", "1", "0", "10", "", "1", "10", "", "1", None, "0", "", "10", "0", None, None]
    assert pr[4] is sound.JOINED and pr[11] is sound.JOINED
    assert pr[3].phones[-2:] == ("IH0", "Z") and pr[10].phones[-1] == "S"     # Holmes's, it's (curly apostrophe)
    assert sound.coverage(bd, pr, 0, len(pr) - 1) == {"words": 11, "yours": 0, "dict": 9, "guess": 1, "none": 1}


@needs_dict
def test_a_book_is_worked_out_once_per_set_of_corrections(tmp_path):
    bd = tiny_book(tmp_path / "b", SENTENCES)
    plain = sound.book_prons(bd)
    assert sound.book_prons(bd) is plain
    mine = sound.book_prons(bd, {"grimpen": "x/"})
    assert mine is not plain and mine[12] == sound.Pron(None, "01", "yours")
    assert sound.book_prons(bd, {"grimpen": "x/"}) is mine
    assert sound.coverage(bd, mine, 0, len(mine) - 1)["yours"] == 1


@needs_dict
def test_the_same_word_shares_one_pronunciation(tmp_path):
    bd = tiny_book(tmp_path / "b", [[("dog", "NOUN"), ("dog", "NOUN"), ("dog", "VERB")]])
    pr = sound.book_prons(bd)
    assert pr[0] is pr[1] and pr[0] == pr[2]


@needs_dict
def test_the_fixture_books_are_almost_all_in_the_dictionary(view):
    for b in view.books:
        bd = view.bd[b]
        c = sound.coverage(bd, sound.book_prons(bd), 0, bd.n_tokens - 1)
        assert c["words"] == bd.n_words and c["dict"] / c["words"] > 0.9


# ---------- saving corrections ----------
@pytest.mark.parametrize("word,kept", [("Baskerville", "baskerville"), ("  Grimpen ", "grimpen"), ("o’clock", "o'clock"), ("well-known", "well-known")])
def test_a_corrected_word_is_kept_normalised(word, kept):
    assert sound.check_word(word) == kept


@pytest.mark.parametrize("word", ["", "two words", "1889", "x" * 61, "!!"])
def test_a_corrected_word_must_be_one_word_with_letters(word):
    with pytest.raises(ValueError, match="can't be corrected"):
        sound.check_word(word)


def test_corrections_are_checked_tidied_and_sorted(monkeypatch):
    assert sound.check_corrections({"Grimpen": " 1  0 ", "baskerville": "b ae1 s k er0 v ih2 l"}) == \
        {"baskerville": "b ae1 s k er0 v ih2 l", "grimpen": "1 0"}
    with pytest.raises(ValueError, match="grimpen: .*ARPAbet"):
        sound.check_corrections({"Grimpen": "Q AE1"})
    with pytest.raises(ValueError, match="list of words"):
        sound.check_corrections(["grimpen"])
    with pytest.raises(ValueError):
        sound.check_corrections({"grimpen": 3})
    monkeypatch.setattr(sound, "MAX_CORRECTIONS", 1)
    with pytest.raises(ValueError, match="At most 1"):
        sound.check_corrections({"a": "1", "b": "1"})


def test_a_pronunciation_as_you_would_type_it():
    assert sound.as_text(sound.Pron(("B", "AE1", "T"), "1", "dict")) == "B AE1 T"
    assert sound.as_text(sound.Pron(None, "100", "guess")) == "1 0 0"


def test_a_set_of_corrections_is_read_once():
    """Every book of a request asks for the corrections: the same set (in any order) is read once; a bad one is left out."""
    given = {"Grimpen": "1 0", "tor": "T AO1 R", "bad": "Q Q"}
    read = sound._corrections(given)
    assert read is sound._corrections(dict(reversed(list(given.items()))))
    assert set(read) == {"grimpen", "tor"} and read["tor"].phones == ("T", "AO1", "R")
