"""Pronunciation for the sound and rhythm figures: the syllables, stresses and sounds of each word of a book.

The source is the CMU Pronouncing Dictionary (about 126,000 words, American English; the data is under a BSD licence), read from the
optional `cmudict` package: `pip install "alex-booknlp-analyser[sound]"`. The package itself is GPL-3.0, which is why aLex doesn't
install it by default. `available` says whether it is there and `MISSING` how to get it; `entries` loads it once, when first needed.

A word's pronunciation (`Pron`) is

* `phones`: its phonemes in ARPAbet, the vowels carrying a stress digit (1 primary, 2 secondary, 0 none), or None when they aren't known;
* `stress`: one character a syllable, "1" stressed (primary or secondary) or "0" unstressed;
* `source`: where it came from: "yours", "dict", "guess", or "joined" for a clitic that belongs to the word before (see below).

`pronounce` finds it for one word, trying in turn

* **yours**: your correction of the word (`overrides`: {word: text}, the text read by `parse_correction`), kept as you typed it;
* **dict**: the dictionary. Of several pronunciations the first, unless they differ in stress and the word class picks one: a noun,
  adjective or name takes the one stressed earliest, a verb the one stressed latest (REcord the noun, reCORD the verb). A word is
  also looked up as the word an abbreviation stands for (`ABBREVIATIONS`: Dr. is "doctor") and in American spelling (`BRITISH`:
  valour, sombre, realised). One that still isn't listed is found as its hyphenated parts in turn (well-known), or as a plural or
  possessive without its apostrophe (Stapletons), when those are listed;
* **guess**: syllables from vowel groups (`guess_syllables`, as for the Flesch scores), the first one stressed, the usual English
  default. A guess has no phonemes, so a guessed word takes part in rhythm but not in the sound figures.

`book_prons` gives every token of a book its pronunciation in context. There the word class decides one-syllable words: a function
word (`FUNCTION`: determiner, preposition, pronoun, auxiliary, conjunction, particle) is unstressed and any other one-syllable word
stressed, whatever the dictionary says ("of" is AH1 V there, and "the" has three entries); a negative contraction (don't, can't) keeps
its stress, and your corrections are never changed. A contraction BookNLP splits (do + n't, Holmes + 's) is looked up joined (don't)
and its first token gets the whole pronunciation; when only the first part is known, the clitic's sounds are added to it (`_attach`:
Holmes's gains a syllable, it's doesn't). The clitic token itself then has the empty pronunciation `JOINED`. Tokens that are not
words, or have no letters (1889), have none (None): they are gaps in the rhythm.
"""
from __future__ import annotations

import re
import sys
import threading
from functools import lru_cache
from typing import NamedTuple

from .corpus import cindex

MISSING = ('Sound and rhythm need the CMU Pronouncing Dictionary, which isn\'t installed. Run pip install "alex-booknlp-analyser[sound]" '
           "(or pip install cmudict) in aLex's environment and start aLex again.")
FUNCTION = {"DET", "ADP", "PRON", "AUX", "CCONJ", "SCONJ", "PART"}   # one-syllable words of these classes are unstressed in context
EARLY = {"NOUN", "ADJ", "PROPN"}                                    # of a word's pronunciations, these classes take the earliest stress
LATE = {"VERB"}                                                     # and verbs the latest
VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"}
CONSONANTS = {"B", "CH", "D", "DH", "F", "G", "HH", "JH", "K", "L", "M", "N", "NG", "P", "R", "S", "SH", "T", "TH", "V", "W", "Y",
              "Z", "ZH"}
SIBILANTS = {"S", "Z", "SH", "ZH", "CH", "JH"}                      # 's after these is a syllable of its own (Holmes's)
VOICELESS = {"P", "T", "K", "F", "TH"}                              # 's after these is S, else Z
CLITICS = {"'s": ("Z",), "n't": ("N", "T"), "'ll": ("L",), "'ve": ("V",), "'d": ("D",), "'re": ("R",), "'m": ("M",)}
ABBREVIATIONS = {"dr.": "doctor", "dr": "doctor", "st.": "saint", "col.": "colonel", "capt.": "captain", "gen.": "general",
                 "prof.": "professor", "rev.": "reverend", "esq.": "esquire", "messrs.": "messieurs", "sq.": "square"}
BRITISH = [(r"our$", "or"), (r"ours$", "ors"), (r"([bt])re$", r"\1er"), (r"([bt])res$", r"\1ers"), (r"is(e|ed|es|ing)$", r"iz\1"),
           (r"ys(e|ed|es|ing)$", r"yz\1"), (r"^gips", "gyps"), (r"ogue$", "og")]   # British spellings -> the dictionary's American
MAX_SYLLABLES = 20                                                  # in one correction
MAX_PHONES = 60
MAX_CORRECTIONS = 5000                                              # corrections kept in one workspace
MAX_WORD = 60                                                       # characters in a corrected word


class Pron(NamedTuple):
    """How a word sounds: phonemes (a tuple of ARPAbet symbols, or None when unknown), a stress pattern ("1"/"0" a syllable) and
    where it came from ("yours", "dict", "guess" or "joined")."""
    phones: tuple | None
    stress: str
    source: str


JOINED = Pron((), "", "joined")          # a clitic whose sounds went to the word before it

_DICT: dict | None = None
_LOCK = threading.Lock()                 # one thread reads the dictionary; the others wait for it


# ---------- the dictionary ----------
def available():
    """Whether the cmudict package is installed."""
    try:
        import cmudict  # noqa: F401
        return True
    except ImportError:
        return False


def entries():
    """The dictionary, {lowercased word: (pronunciation, …)}, each pronunciation one string of phonemes ("B AE1 S K ER0 V IH2 L") in
    the dictionary's order. Read on first use (under a second) and kept for the life of the process (about 30 MB). RuntimeError
    (`MISSING`) when cmudict isn't installed."""
    global _DICT
    if _DICT is None:
        with _LOCK:
            if _DICT is None:
                _DICT = _read_dictionary()
    return _DICT


def _read_dictionary():
    """The work of `entries`: parse cmudict.dict ("word phones" a line, variants as "word(2)", comments after "#")."""
    try:
        import cmudict
    except ImportError:
        raise RuntimeError(MISSING) from None
    found: dict[str, list[str]] = {}
    with cmudict.dict_stream() as f:
        for raw in f:
            line = raw.decode("utf-8", "replace").split("#", 1)[0].strip()
            word, _, phones = line.partition(" ")
            if phones:
                found.setdefault(word.split("(", 1)[0], []).append(phones.strip())
    return {w: tuple(v) for w, v in found.items()}


# ---------- one word ----------
def norm(word):
    """A word as the dictionary and your corrections list it: lowercased, with curly apostrophes made straight."""
    return word.lower().replace("’", "'").replace("‘", "'")


def guess_syllables(word):
    """A rough syllable count from vowel groups (silent final e discounted); at least 1. Good enough for Flesch scores and for words
    the dictionary doesn't know."""
    w = word.lower()
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith(("le", "ee")) and n > 1:
        n -= 1
    return max(1, n)


def _stress(phones):
    """The stress pattern of a phoneme sequence: "1" for each vowel with stress 1 or 2, "0" for each with 0."""
    return "".join("0" if p[-1] == "0" else "1" for p in phones if p[-1] in "012")


def _primary(phones):
    """The syllable number of the primary stress (else the first secondary, else 0): what `_choose` compares."""
    digits = [p[-1] for p in phones if p[-1] in "012"]
    for mark in "12":
        if mark in digits:
            return digits.index(mark)
    return 0


def _choose(variants, pos):
    """The pronunciation (a tuple of phonemes) to use of a word's dictionary entries, given its word class (see the module notes)."""
    options = [tuple(sys.intern(x) for x in v.split()) for v in variants]       # one string per phoneme, shared by every word
    first = options[0]
    if pos in EARLY or pos in LATE:
        same = [o for o in options if len(_stress(o)) == len(_stress(first))]
        pick = min if pos in EARLY else max
        best = pick(_primary(o) for o in same)
        return next(o for o in same if _primary(o) == best)
    return first


def _forms(word):
    """The spellings to look a word up by, in turn: as it is, without outer apostrophes ('tis), as the abbreviation's word (Dr. is
    read "doctor", not "drive"), and in American spelling (valour, sombre, realise: the dictionary is American)."""
    w = ABBREVIATIONS.get(word, word)
    yield w
    yield w.strip("'")
    for old, new in BRITISH:
        if re.search(old, w):
            yield re.sub(old, new, w)


def _from_dict(word, pos):
    """The dictionary's pronunciation of a normalised word, else None. A word that isn't listed in any of its `_forms` can still be
    found as its hyphenated parts in turn (when all are listed), or as a plural or possessive without its apostrophe (Stapletons:
    stapleton + s, with the ending's sound as for 's)."""
    d = entries()
    for w in _forms(word):
        if w in d:
            phones = _choose(d[w], pos)
            return Pron(phones, _stress(phones), "dict")
    parts = [p for p in word.split("-") if p]
    if len(parts) > 1 and all(p in d for p in parts):
        phones = tuple(x for p in parts for x in _choose(d[p], pos))
        return Pron(phones, _stress(phones), "dict")
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        base = next((d[w] for w in _forms(word[:-1]) if w in d), None)
        if base is not None:
            phones = _choose(base, pos)
            return _attach(Pron(phones, _stress(phones), "dict"), "'s", word[:-1])
    return None


def _guess(word):
    """A guessed pronunciation (no phonemes, the first of the guessed syllables stressed), or None for a word without letters."""
    if not re.search(r"[a-z]", word):
        return None
    return Pron(None, "1" + "0" * (guess_syllables(word) - 1), "guess")


def pronounce(word, pos="", overrides=None):
    """A word's pronunciation out of context (`Pron`, see the module notes): your correction, else the dictionary's, else a guess;
    None for a word without letters. `pos` is the word's universal part of speech, which picks between the dictionary's variants;
    `overrides` is {word: correction text}. Needs the dictionary (RuntimeError `MISSING` without it)."""
    w = norm(word)
    return _corrections(overrides).get(w) or _from_dict(w, pos) or _guess(w)


def _attach(base, clitic, word):
    """A word's pronunciation with a clitic's sounds added (Holmes + 's), for contractions the dictionary doesn't list whole. The
    clitic makes a syllable of its own after a consonant (could + n't), and 's only after a hissing sound (Holmes's); 's is S after a
    voiceless consonant. Without phonemes (a guessed word) the spelling decides."""
    last = base.phones[-1].rstrip("012") if base.phones else None
    after_vowel = last in VOWELS if last else word[-1:] in "aeiouy"
    sounds, syllable = CLITICS[clitic], False
    if clitic == "'s":
        if (last in SIBILANTS) if last else word.endswith(("s", "z", "x", "ch", "sh", "ce", "ge")):
            sounds, syllable = ("IH0", "Z"), True
        elif (last in VOICELESS) if last else word.endswith(("p", "t", "k", "f", "th")):
            sounds = ("S",)
    elif clitic not in ("'re", "'m") and not after_vowel:
        sounds, syllable = ("AH0",) + sounds, True
    phones = base.phones + sounds if base.phones else None
    return Pron(phones, base.stress + ("0" if syllable else ""), base.source)


def _joined(word, clitic, pos, corr):
    """The pronunciation of a word and the clitic after it (do + n't): the contraction as one word if you corrected it or the dictionary
    lists it, else the word's own with the clitic's sounds added; None if the word has no letters."""
    whole = word + clitic
    found = corr.get(whole) or _from_dict(whole, pos)
    if found is not None:
        return found
    base = corr.get(word) or _from_dict(word, pos) or _guess(word)
    return _attach(base, clitic, word) if base is not None else None


def _in_context(p, pos, negative=False):
    """A pronunciation as said in running text: a one-syllable word from the dictionary or a guess is unstressed when it is a function
    word (unless it is a negative contraction) and stressed otherwise. Your corrections and longer words are left as they are."""
    if p is None or p.source not in ("dict", "guess") or len(p.stress) != 1:
        return p
    mark = "0" if pos in FUNCTION and not negative else "1"
    return p if p.stress == mark else p._replace(stress=mark)


# ---------- your corrections ----------
def parse_correction(text):
    """Read a correction as you type it -> `Pron` (source "yours"), or ValueError with a readable message. Either phonemes in ARPAbet,
    each vowel with its stress digit ("B AE1 S K ER0 V IH2 L"), or a stress pattern, a character a syllable: 1 or / stressed, 0 or x
    unstressed, 2 (secondary stress) counted as stressed; spaces are allowed between them ("1 0 2", "/x/")."""
    t = " ".join(str(text).split())
    if not t:
        raise ValueError("Type a stress pattern (such as 1 0 2 or /x/) or phonemes (such as B AE1 S K ER0 V IH2 L).")
    if set(t) <= set("012/xX "):
        pattern = "".join("0" if c in "0xX" else "1" for c in t if c != " ")
        if len(pattern) > MAX_SYLLABLES:
            raise ValueError(f"A stress pattern can have at most {MAX_SYLLABLES} syllables.")
        return Pron(None, pattern, "yours")
    phones = tuple(t.upper().split())
    if len(phones) > MAX_PHONES:
        raise ValueError(f"A pronunciation can have at most {MAX_PHONES} phonemes.")
    for p in phones:
        m = re.fullmatch(r"([A-Z]+)([012]?)", p)
        base, digit = m.groups() if m else (p, "")
        if base in VOWELS and not digit:
            raise ValueError(f"The vowel {p} needs a stress digit: {p}1 (stressed), {p}2 (secondary) or {p}0 (unstressed).")
        if base in CONSONANTS and digit:
            raise ValueError(f"{p}: only vowels take a stress digit.")
        if base not in VOWELS and base not in CONSONANTS:
            raise ValueError(f"“{p}” isn't an ARPAbet phoneme. Type phonemes such as B AE1 S K ER0 V IH2 L, "
                             "or a stress pattern such as 1 0 2.")
    stress = _stress(phones)
    if not stress:
        raise ValueError("A pronunciation needs at least one vowel.")
    if len(stress) > MAX_SYLLABLES:
        raise ValueError(f"A pronunciation can have at most {MAX_SYLLABLES} syllables.")
    return Pron(phones, stress, "yours")


def check_word(word):
    """A word as a correction is kept under (`norm`, trimmed), or ValueError: it must be one word with a letter in it."""
    w = norm(str(word)).strip()
    if not w or len(w) > MAX_WORD or any(c.isspace() for c in w) or not re.search(r"[a-z]", w):
        raise ValueError(f"“{str(word)[:MAX_WORD]}” can't be corrected: give one word (with letters, no spaces, at most {MAX_WORD} characters).")
    return w


def check_corrections(given):
    """Your corrections as they are saved: {word (`check_word`): text, tidied}, every text readable (`parse_correction`), at most
    `MAX_CORRECTIONS`. ValueError naming the first word that isn't."""
    if not isinstance(given, dict):
        raise ValueError("Corrections should be a list of words with their pronunciations.")
    if len(given) > MAX_CORRECTIONS:
        raise ValueError(f"At most {MAX_CORRECTIONS} words can be corrected.")
    out = {}
    for word, text in given.items():
        w = check_word(word)
        try:
            parse_correction(text if isinstance(text, str) else "")
        except ValueError as e:
            raise ValueError(f"{w}: {e}") from None
        out[w] = " ".join(text.split())
    return dict(sorted(out.items()))


def as_text(p):
    """A pronunciation as you would type it to correct it: its phonemes ("B AE1 S K ER0 V IH2 L"), or without them its stress pattern
    ("1 0 0")."""
    return " ".join(p.phones) if p.phones else " ".join(p.stress)


def _corrections(overrides):
    """Your corrections, read: {normalised word: Pron}. One that can't be read is left out (the page checks them as you save them).
    Read once per set of corrections (`_read_corrections`): every book of a request asks for them."""
    return _read_corrections(tuple(sorted((str(w), str(t)) for w, t in (overrides or {}).items())))


@lru_cache(maxsize=8)
def _read_corrections(pairs):
    """The work of `_corrections`, for its (word, text) pairs. Don't change the dict it returns: it is shared."""
    out = {}
    for word, text in pairs:
        try:
            out[norm(word).strip()] = parse_correction(text)
        except ValueError:
            continue
    return out


# ---------- a book ----------
def book_prons(bd, overrides=None):
    """The pronunciation in context of every token of a book: a list as long as the book, each a `Pron`, `JOINED` (a clitic said
    with the word before it) or None (not a word, or no letters). Worked out once per set of corrections and kept on the book."""
    corr = _corrections(overrides)
    sig = tuple(sorted((w, p.phones, p.stress) for w, p in corr.items()))
    return bd.kept("sound", entries=4).get(sig, lambda: _book_prons(bd, corr))


def _book_prons(bd, corr):
    """The work of `book_prons`. One `Pron` object is shared by every token of the same word, clitic and class."""
    iw = cindex(bd)["isword"]
    n = len(bd.word)
    out: list = [None] * n
    seen: dict = {}
    for i in range(n):
        if not iw[i] or out[i] is not None:
            continue
        w, pos = norm(bd.word[i]), bd.pos[i]
        if w in CLITICS:                                 # a clitic with no word before it in the sentence: said with what precedes
            out[i] = JOINED
            continue
        nxt = norm(bd.word[i + 1]) if i + 1 < n and iw[i + 1] and bd.sent[i + 1] == bd.sent[i] else ""
        clitic = nxt if nxt in CLITICS else ""
        key = (w, clitic, pos)
        if key not in seen:
            p = _joined(w, clitic, pos, corr) if clitic else corr.get(w) or _from_dict(w, pos) or _guess(w)
            seen[key] = _in_context(p, pos, negative=clitic == "n't")
        out[i] = seen[key]
        if clitic:
            out[i + 1] = JOINED
    return out


def coverage(bd, prons, s, e):
    """Where the pronunciations of the words of tokens s..e came from: {"words", "yours", "dict", "guess", "none"} (none: no letters).
    A clitic said with the word before it isn't a word of its own here."""
    iw = cindex(bd)["isword"]
    out = {"words": 0, "yours": 0, "dict": 0, "guess": 0, "none": 0}
    for i in range(max(0, s), min(e, len(prons) - 1) + 1):
        p = prons[i]
        if not iw[i] or p is JOINED:
            continue
        out["words"] += 1
        out[p.source if p is not None else "none"] += 1
    return out
