"""Sound and rhythm figures of prose: stress and its spacing, cadences, sound patterning (alliteration and the like) and a sound profile.

Everything rests on the pronunciations of `core/sound.py` (`sound.book_prons`). It is counted over **units**: lists of token positions of
one book in text order (sentences, or parts of them, quotes, a paragraph's narration: whatever a caller's sample is made of;
`sentence_units` makes them for a stretch of a book). `tally` counts a book's units into a **tally**, a dict of raw counts that `add`
sums over units, books and cases, and `figures` turns a tally into the figures of `FIGURES`. MEASURES.md section 17 explains each.

* **Phrases.** A unit is read phrase by phrase: a phrase ends at a pause (`PAUSES`: . ? ! ; : , dashes, brackets, ellipses; not a
  hyphen) and at the unit's end. A word without letters (1889) is a gap: stress is not followed across it. A clitic said with the
  word before it (`sound.JOINED`) adds nothing; other non-words (quotation marks) are passed over.
* **Rhythm**, in each phrase's string of syllables ("1" stressed, "0" not): stressed syllables, syllables per word and per unit;
  clashes (two stresses side by side) and lapses (three or more unstressed in a row); the gaps between successive stresses (0, 1, 2,
  3 or more unstressed syllables); and how even the spacing is, as the nPVI of the intervals between stresses.
* **Cadences.** At every phrase end, the syllables from the last-but-one stress to the end; named by the English cursus (`CURSUS`)
  or else kept as a pattern ("other"). Phrase ends closed by . ? ! … or by the end of the unit are also counted as sentence ends.
* **Runs** (`RUNS`): words that share something (`_Runs.word`) and lie within `window` content words of each other. A run is a chain
  of such words; it never crosses a `boundary` (`BOUNDARIES`: a sentence end, a paragraph end, or only text outside the sample).
  The four **sound runs** are over content words (nouns, verbs, adjectives, adverbs, names) and share a sound (`_keys`; their
  phonemes must be known, except for alliteration by first letter). **Alliteration** is by the setting `alliteration`
  (`ALLITERATION`): the first consonant of the stressed syllable's onset, the first sound of the word, or its first letter.
  **Repetition** is the fifth kind: the same word again, by the setting `repetition` (`REPETITION`): the same lemma among content
  words, the same word form among content words, or the same lemma among all words. A repeated word (as that setting says) doesn't
  count again in a sound run: it is a repetition, not sound patterning. Consonance also skips a word with the same last vowel as one
  already in the run (that is closer to rhyme).
* **Sound profile**: each phoneme per 1,000 words, and classes of them (`CLASSES`); vowels are counted only when stressed.

The run window, boundary, alliteration and repetition settings and your pronunciation corrections are the workspace's (`config` reads them from its settings). `span_tally`
keeps the tally of a stretch of a book on the book, per setting; `table` gives the figures per book or per chapter or slice (the Style
page); the Statistics layer (`layers.sound`) keeps its cases' tallies on the `Cases`. `value` and `label` read one
figure, which can also be a single phoneme ("phone:S").
"""
from __future__ import annotations

import math
from collections import Counter
from functools import lru_cache

from . import sound
from .corpus import cindex
from .narrative import CONTENT

PAUSES = {".", "?", "!", ";", ":", ",", "--", "---", "—", "–", "(", ")", "[", "]", "...", "…"}
ENDS = {".", "?", "!", "...", "…"}                                     # a phrase closed by these is also a sentence end
CURSUS = {"10010": "planus", "100100": "tardus", "1000010": "velox", "100010": "trispondaicus"}
SOUND_RUNS = ("alliteration", "assonance", "consonance", "rhyme")
RUNS = (*SOUND_RUNS, "repetition")
BOUNDARIES = ("sentence", "paragraph", "none")
ALLITERATION = ("stressed", "sound", "letter")      # the stressed syllable's onset, the word's first sound, the word's first letter
REPETITION = ("lemma", "form", "all")               # the same lemma or form among content words, the same lemma among all words
CLASSES = {
    "plosives": {"P", "B", "T", "D", "K", "G"},
    "fricatives": {"F", "V", "TH", "DH", "S", "Z", "SH", "ZH", "HH"},
    "sibilants": {"S", "Z", "SH", "ZH", "CH", "JH"},
    "nasals": {"M", "N", "NG"},
    "liquids": {"L", "R"},
    "glides": {"W", "Y"},
    "long_vowels": {"IY", "EY", "AA", "AO", "OW", "UW", "AY", "AW", "OY", "ER"},     # tense vowels and diphthongs, when stressed
    "short_vowels": {"IH", "EH", "AE", "AH", "UH"},                                   # lax vowels, when stressed
}
FIGURES = {
    "stressed": "Stressed syllables (%)", "syl_word": "Syllables per word", "syl_unit": "Syllables per unit",
    "clashes": "Stress clashes per 100 syllables", "lapses": "Stress lapses per 100 syllables",
    "binary": "Binary gaps (% of gaps between stresses)", "ternary": "Ternary gaps (% of gaps between stresses)",
    "npvi": "Stress spacing nPVI (lower is more even)",
    **{f"cad_{n}": f"Cadence {n} (% of phrase ends)" for n in ("cursus", *CURSUS.values())},
    **{f"end_{n}": f"Cadence {n} (% of sentence ends)" for n in ("cursus", *CURSUS.values())},
    **{f"{k}_runs": f"{k.capitalize()} runs per 1,000 words" for k in RUNS},
    **{f"{k}_share": f"{k.capitalize()}: content words in a run (%)" for k in SOUND_RUNS},
    "repetition_share": "Repetition: words in a run (%)",
    **{f"{k}_length": f"{k.capitalize()}: mean run length (words)" for k in RUNS},
    **{f"class_{c}": f"{c.replace('_', ' ').capitalize()} per 1,000 words" for c in CLASSES},
    "guessed": "Guessed pronunciations (% of words)",
}
DECIMALS = {"syl_word": 2, "syl_unit": 1, **{f"{k}_length": 2 for k in RUNS}}     # shown with this many decimals (the rest: 1)
DEFAULTS = {"window": 3, "boundary": "sentence", "alliteration": "stressed", "repetition": "lemma"}
PHONEMES = sorted(sound.VOWELS | sound.CONSONANTS)
_ONSETS2 = {("S", c) for c in ("P", "T", "K", "M", "N", "L", "W", "F")} | \
           {(a, b) for a in ("P", "B", "T", "D", "K", "G", "F", "V", "TH", "SH") for b in ("L", "R", "W", "Y")}


# ---------- settings ----------
def config(settings):
    """The sound settings of a workspace (`settings["sound"]` of its library) with the defaults filled in: {window, boundary,
    alliteration, repetition, corrections}. A value that can't be used (an old or hand-edited file) falls back to the default."""
    given = settings.get("sound") if isinstance(settings, dict) else None
    given = given if isinstance(given, dict) else {}
    try:
        window = check_window(given.get("window", DEFAULTS["window"]))
    except ValueError:
        window = DEFAULTS["window"]
    pick = lambda key, allowed: given.get(key) if given.get(key) in allowed else DEFAULTS[key]
    corrections = given.get("corrections") if isinstance(given.get("corrections"), dict) else {}
    return {"window": window, "boundary": pick("boundary", BOUNDARIES), "alliteration": pick("alliteration", ALLITERATION),
            "repetition": pick("repetition", REPETITION), "corrections": corrections}


def signature(cfg):
    """A hashable key for a `config`: what a kept tally depends on."""
    return (cfg["window"], cfg["boundary"], cfg["alliteration"], cfg["repetition"],
            tuple(sorted((str(k), str(v)) for k, v in cfg["corrections"].items())))


def check_window(value):
    """The run window as a whole number of content words, at least 1 (no upper limit), or ValueError (also for NaN and infinity,
    which JSON from Python can carry)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value != int(value) or value < 1:
        raise ValueError("The window is a whole number of content words, 1 or more.")
    return int(value)


def check_boundary(value):
    """Where runs stop (`BOUNDARIES`), or ValueError."""
    if value not in BOUNDARIES:
        raise ValueError("Runs stop at a sentence end, a paragraph end, or nowhere: boundary is sentence, paragraph or none.")
    return value


def check_alliteration(value):
    """What alliteration compares (`ALLITERATION`), or ValueError."""
    if value not in ALLITERATION:
        raise ValueError("Alliteration is by the stressed syllable, the first sound or the first letter: stressed, sound or letter.")
    return value


def check_repetition(value):
    """What counts as a repetition (`REPETITION`), or ValueError."""
    if value not in REPETITION:
        raise ValueError("A repetition is the same lemma, the same word form, or the same lemma among all words: lemma, form or all.")
    return value


# ---------- units ----------
def sentence_units(bd, s, e):
    """Tokens s..e of a book as units: each sentence that overlaps the stretch, cut to the part inside it."""
    out, t = [], max(0, s)
    while t <= e:
        a, b = bd.sent_bounds[bd.sent[t]]
        out.append(list(range(t, min(b, e) + 1)))
        t = min(b, e) + 1
    return out


# ---------- a word's sounds ----------
def _stressed_vowel(phones):
    """Index in `phones` of the vowel with primary stress (else the first with secondary, else the first vowel), or None."""
    vowels = [k for k, p in enumerate(phones) if p[-1] in "012"]
    for mark in "12":
        for k in vowels:
            if phones[k][-1] == mark:
                return k
    return vowels[0] if vowels else None


def _onset(phones, k):
    """The first consonant of the onset of the syllable whose vowel is phones[k] (the consonants before it that can begin an English
    syllable: S + stop, a stop or fricative + liquid or glide, S + stop + liquid/glide, or one consonant), or None if it has none."""
    j = k
    while j > 0 and phones[j - 1][-1] not in "012":
        j -= 1
    cluster = list(phones[j:k])
    while len(cluster) > 1:
        if len(cluster) == 2 and tuple(cluster) in _ONSETS2:
            break
        if len(cluster) == 3 and cluster[0] == "S" and (cluster[1], cluster[2]) in _ONSETS2:
            break
        cluster = cluster[1:]
    return cluster[0] if cluster and cluster[0] != "NG" else None


@lru_cache(maxsize=100_000)
def _keys(p):
    """What a word with known phonemes shares in each sound run: {kind: key or None}, plus "first" (the word's first sound, when it is a
    consonant: alliteration by first sound) and "last_vowel" for consonance. Alliteration: the first consonant of the stressed
    syllable's onset; assonance: the stressed vowel; consonance: the consonants after the last vowel; rhyme: the stressed vowel and
    everything after it (stress digits dropped)."""
    ph = p.phones
    k = _stressed_vowel(ph)
    if k is None:
        return {**dict.fromkeys(SOUND_RUNS), "first": None, "last_vowel": None}
    bare = tuple(x.rstrip("012") for x in ph)
    last = max(j for j, x in enumerate(ph) if x[-1] in "012")
    return {"alliteration": _onset(ph, k), "assonance": bare[k], "consonance": bare[last + 1:] or None, "rhyme": bare[k:],
            "first": bare[0] if bare[0] in sound.CONSONANTS else None, "last_vowel": bare[last]}


# ---------- tallies ----------
def empty():
    """A tally with nothing counted."""
    t = {"words": 0, "units": 0, "syllables": 0, "stressed": 0, "sounded": 0, "clashes": 0, "lapses": 0,
         "gaps": Counter(), "pvi_sum": 0.0, "pvi_pairs": 0, "cadences": Counter(), "ends": Counter(),
         "phones": Counter(), "classes": Counter(), "coverage": Counter()}
    for k in RUNS:
        t[k + "_runs"] = t[k + "_words"] = t[k + "_eligible"] = 0         # runs, words in them, words that could be in one
    return t


def add(a, b):
    """Two tallies summed (a new tally; neither is changed)."""
    return {key: a[key] + b[key] for key in empty()}


def count(bd, units, cfg, keep=False):
    """`tally` under the sound settings `cfg` (`config`)."""
    return tally(bd, units, cfg["corrections"], cfg["window"], cfg["boundary"], keep, cfg["alliteration"], cfg["repetition"])


def tally(bd, units, overrides=None, window=3, boundary="sentence", keep=False, alliteration="stressed", repetition="lemma"):
    """Count a book's units (lists of token positions, in text order) into a tally (see `empty`). `overrides` are your pronunciation
    corrections; `window`, `boundary`, `alliteration` and `repetition` the run settings. With `keep` the tally also holds where things
    are, for listing them: "found", every run as (kind, key, token positions), and "cadences_at", every cadence as (pattern, its first
    token, its last word, whether it ends a sentence). Needs the dictionary (RuntimeError `sound.MISSING` without it)."""
    prons = sound.book_prons(bd, overrides)
    iw = cindex(bd)["isword"]
    t = empty()
    if keep:
        t["cadences_at"] = []
    runner = _Runs(bd, window, boundary, keep, alliteration, repetition)
    said: Counter = Counter()                    # Pron -> how many words had it: what is counted per word is counted at the end
    prev = None                                  # the last token read, to see when the units skip words
    for toks in units:
        if not toks:
            continue
        t["units"] += 1
        prev = _unit(bd, prons, iw, toks, t, runner, prev, said)
    runner.flush()
    for p, n in said.items():
        _words(p, n, t)
    for k in RUNS:
        t[k + "_runs"] = runner.count[k]
        t[k + "_words"] = runner.words[k]
        t[k + "_eligible"] = runner.eligible[k]
    if keep:
        t["found"] = runner.found
    return t


def _unit(bd, prons, iw, toks, t, runner, prev, said):
    """Count one unit into tally `t`: its phrases (rhythm and cadences), its words into the runs, and each word's
    pronunciation into `said` (counted into `t` at the end, by `_words`). `prev` is the last token read before it (None at the start);
    returns the unit's last token. Where the sample skips words (between units or inside one), the runs are closed, and so is the
    phrase inside a unit."""
    phrase, segment = [], []                     # the phrase's finished segments (split at gaps) and the one being read
    for i in toks:
        if prev is not None and i > prev + 1 and any(iw[j] for j in range(prev + 1, i)):
            runner.reset()
            if phrase or segment:
                _phrase(phrase + [segment], t, end=False)
                phrase, segment = [], []
        prev = i
        if not iw[i]:
            if bd.word[i] in PAUSES:
                _phrase(phrase + [segment], t, end=bd.word[i] in ENDS)
                phrase, segment = [], []
            continue
        p = prons[i]
        if p is sound.JOINED:
            continue
        said[p] += 1
        if p is None:
            phrase.append(segment)
            segment = []
            continue
        segment.append((p.stress, i))
        runner.word(i, p, bd.pos[i] in CONTENT)
    _phrase(phrase + [segment], t, end=True)
    return prev


def _phrase(segments, t, end):
    """Count one phrase (its segments: lists of (stress string, token) for its words, split at gaps) into tally `t`: clashes, lapses,
    gaps between stresses, nPVI pairs, and the cadence of its last segment (also as a sentence end when `end`); a tally that keeps
    positions (`cadences_at`) also gets where the cadence is."""
    last, words = "", []
    for seg in segments:
        s = "".join(x for x, _ in seg)
        if not s:
            continue
        last, words = s, seg
        t["clashes"] += sum(1 for a, b in zip(s, s[1:]) if a == b == "1")
        t["lapses"] += sum(1 for run in s.split("1") if len(run) >= 3)
        marks = [k for k, c in enumerate(s) if c == "1"]
        spans = [b - a for a, b in zip(marks, marks[1:])]                  # syllables from one stress to the next
        for d in spans:
            t["gaps"][min(d - 1, 3)] += 1
        for a, b in zip(spans, spans[1:]):
            t["pvi_sum"] += abs(a - b) / ((a + b) / 2)
            t["pvi_pairs"] += 1
    cadence = cadence_of(last)
    if cadence:
        t["cadences"][cadence] += 1
        if end:
            t["ends"][cadence] += 1
        if "cadences_at" in t:
            first, before = words[-1][1], len(last) - len(cadence)        # the word holding the cadence's first syllable
            for stress, tok in words:
                if before < len(stress):
                    first = tok
                    break
                before -= len(stress)
            t["cadences_at"].append((cadence, first, words[-1][1], end))


def cadence_of(syllables):
    """The cadence of a phrase's syllable string: from its last-but-one stress to the end ("10010"), or "" with fewer than two stresses."""
    k = syllables.rfind("1")
    k = syllables.rfind("1", 0, k) if k > 0 else -1
    return syllables[k:] if k >= 0 else ""


def cadence_type(pattern):
    """The cursus name of a cadence pattern (planus, tardus, velox, trispondaicus), or "other"."""
    return CURSUS.get(pattern, "other")


def _words(p, n, t):
    """Count n words said as p (a Pron, or None for a word without letters) into tally `t`: words, coverage, syllables and stresses,
    and their sounds (`_sounds`)."""
    t["words"] += n
    t["coverage"][p.source if p is not None else "none"] += n
    if p is None:
        return
    t["syllables"] += n * len(p.stress)
    t["stressed"] += n * p.stress.count("1")
    t["sounded"] += n
    if p.phones:
        phones, classes = _sounds(p)
        for x, c in phones:
            t["phones"][x] += n * c
        for x, c in classes:
            t["classes"][x] += n * c


@lru_cache(maxsize=100_000)
def _sounds(p):
    """A pronunciation's sounds for the profile: ((phoneme, count), …), ((class, count), …): every consonant, and the vowels its stress
    pattern marks stressed."""
    phones = Counter()
    marks = iter(p.stress)
    for x in p.phones:
        if x[-1] in "012" and next(marks, "0") != "1":
            continue
        phones[x.rstrip("012")] += 1
    classes = Counter({name: sum(c for x, c in phones.items() if x in members) for name, members in CLASSES.items()})
    return tuple(phones.items()), tuple((k, c) for k, c in classes.items() if c)


class _Runs:
    """The runs being followed through a book's units: for each kind, the open run of each key, closed when a word with that key is
    more than `window` content words further on, at a `boundary`, at a gap in the sample, or at the end. `alliteration` and
    `repetition` are the settings of those kinds (`ALLITERATION`, `REPETITION`)."""

    def __init__(self, bd, window, boundary, keep, alliteration="stressed", repetition="lemma"):
        """Start with no runs. `bd` gives sentences, paragraphs, words and lemmas; `keep` keeps the finished runs in `found`."""
        self.bd, self.window, self.boundary, self.keep = bd, window, boundary, keep
        self.alliteration, self.repetition = alliteration, repetition
        ci = cindex(bd)
        self.same = ci["lower"] if repetition == "form" else ci["lemma_lower"]     # what makes a word the same as another
        self.lower = ci["lower"]
        self.region_of = bd.sent if boundary == "sentence" else bd.para if boundary == "paragraph" else None
        self.open = {k: {} for k in RUNS}
        self.count, self.words, self.eligible = Counter(), Counter(), Counter()
        self.found: list = []
        self.n = 0                                  # content words seen (the distance between words is counted in these)
        self.region = None                          # the sentence or paragraph of the last word

    def word(self, i, p, content):
        """A word at token i with pronunciation p (`content`: a noun, verb, adjective, adverb or name). It joins or starts a repetition
        run (a content word, or any word when repetitions are counted among all words) and, a content word, a run of each sound it has
        a key for. A word that repeats one in a sound run (what counts as the same word is the repetition setting's) is left out of it."""
        region = self.region_of[i] if self.region_of is not None else None
        if region != self.region:
            self.reset()
            self.region = region
        if content:
            self.n += 1
        same = self.same[i]
        if content or self.repetition == "all":
            self.eligible["repetition"] += 1
            self._join("repetition", same, i, same, None, repeat_ok=True)
        if not content:
            return
        keys = _keys(p) if p.phones else None
        if self.alliteration == "letter":
            letter = next((c for c in self.lower[i] if c.isalpha()), None)
            if letter:
                self.eligible["alliteration"] += 1
                self._join("alliteration", letter, i, same, None)
        elif keys is not None:
            self.eligible["alliteration"] += 1
            key = keys["alliteration"] if self.alliteration == "stressed" else keys["first"]
            if key is not None:
                self._join("alliteration", key, i, same, None)
        if keys is None:
            return
        for kind in ("assonance", "consonance", "rhyme"):
            self.eligible[kind] += 1
            if keys[kind] is not None:
                self._join(kind, keys[kind], i, same, keys["last_vowel"] if kind == "consonance" else None)

    def _join(self, kind, key, i, same, vowel, repeat_ok=False):
        """Token i, with this `key` for `kind`, joins the open run of that key if it is within the window (unless it repeats a word of the
        run, or for consonance a last vowel, and `repeat_ok` is off); else it starts a new one, and the old one is closed."""
        run = self.open[kind].get(key)
        if run is not None and self.n - run["last"] <= self.window:
            if not repeat_ok and (same in run["same"] or (vowel is not None and vowel in run["vowels"])):
                return
            run["toks"].append(i)
            run["same"].add(same)
            run["vowels"].add(vowel)
            run["last"] = self.n
            return
        if run is not None:
            self._close(kind, key, run)
        self.open[kind][key] = {"toks": [i], "same": {same}, "vowels": {vowel}, "last": self.n}

    def reset(self):
        """Close every open run (a boundary, or text outside the sample)."""
        self.flush()
        self.open = {k: {} for k in RUNS}

    def flush(self):
        """Count the open runs of two or more words as found."""
        for kind, runs in self.open.items():
            for key, run in runs.items():
                self._close(kind, key, run)
            runs.clear()

    def _close(self, kind, key, run):
        """Count one finished run if it has two or more words."""
        if len(run["toks"]) >= 2:
            self.count[kind] += 1
            self.words[kind] += len(run["toks"])
            if self.keep:
                self.found.append((kind, key, run["toks"]))


# ---------- kept tallies ----------
def span_tally(bd, s, e, cfg):
    """The tally of tokens s..e of a book (its sentences, cut to the stretch: `sentence_units`) under the settings `cfg` (`config`).
    Worked out once per stretch and setting and kept on the book, as `narrative.style_metrics` keeps its figures."""
    return bd.kept("prosody", entries=500).get((s, e, signature(cfg)), lambda: count(bd, sentence_units(bd, s, e), cfg))


def table(view, seg_cfg, by, cfg, tally_of=None):
    """The figures per book, or per chapter or slice (`by="segment"`, cut by the Measure over setting `seg_cfg`), under the sound
    settings `cfg` -> {rows: [{book, title, label, (index), words, coverage, figures…}], info (with segments), figures: [{k, label,
    dec}]}. `tally_of(book, start, end)` gives a stretch's tally (default: `span_tally`, the whole text; the Sound and rhythm tab
    passes one for a part of it). A book or segment without words is left out. RuntimeError (`sound.MISSING`) without the dictionary."""
    from .narrative import all_segments
    if not sound.available():
        raise RuntimeError(sound.MISSING)
    rows, info = [], None
    if by == "segment":
        segs, info = all_segments(view, seg_cfg)
        spans = [(sg["book"], sg["start"], sg["end"], sg["title"], sg["label"], sg["index"]) for sg in segs]
    else:
        spans = [(b, 0, view.bd[b].n_tokens - 1, view.title(b), view.title(b), None) for b in view.books]
    for b, s, e, title, label_, index in spans:
        t = tally_of(b, s, e) if tally_of else span_tally(view.bd[b], s, e, cfg)
        if t["words"]:
            rows.append({"book": b, "title": title, "label": label_, **({"index": index} if index is not None else {}),
                         "words": t["words"], "coverage": dict(t["coverage"]), **figures(t)})
    return {"rows": rows, "info": info, "figures": figure_list()}


def figure_list():
    """The figures as the pages list them: [{k, label, dec}] in `FIGURES` order."""
    return [{"k": k, "label": v, "dec": DECIMALS.get(k, 1)} for k, v in FIGURES.items()]


# ---------- figures ----------
def figures(t):
    """The figures of a tally: {name in FIGURES: value, or None when there is nothing to take it of}."""
    def pct(a, b):
        """a as a percentage of b, or None."""
        return 100 * a / b if b else None

    gaps = sum(t["gaps"].values())
    n_cad, n_end = sum(t["cadences"].values()), sum(t["ends"].values())
    out = {
        "stressed": pct(t["stressed"], t["syllables"]),
        "syl_word": t["syllables"] / t["sounded"] if t["sounded"] else None,
        "syl_unit": t["syllables"] / t["units"] if t["units"] else None,
        "clashes": pct(t["clashes"], t["syllables"]), "lapses": pct(t["lapses"], t["syllables"]),
        "binary": pct(t["gaps"][1], gaps), "ternary": pct(t["gaps"][2], gaps),
        "npvi": 100 * t["pvi_sum"] / t["pvi_pairs"] if t["pvi_pairs"] else None,
        "guessed": pct(t["coverage"]["guess"], t["words"]),
    }
    for prefix, counts, n in (("cad", t["cadences"], n_cad), ("end", t["ends"], n_end)):
        by_type = Counter()
        for pattern, c in counts.items():
            by_type[cadence_type(pattern)] += c
        out[f"{prefix}_cursus"] = pct(n - by_type["other"], n)
        for name in CURSUS.values():
            out[f"{prefix}_{name}"] = pct(by_type[name], n)
    for k in RUNS:
        runs, words = t[k + "_runs"], t[k + "_words"]
        out[k + "_runs"] = 1000 * runs / t["words"] if t["words"] else None
        out[k + "_share"] = pct(words, t[k + "_eligible"])
        out[k + "_length"] = words / runs if runs else None
    for c in CLASSES:
        out["class_" + c] = 1000 * t["classes"][c] / t["words"] if t["words"] else None
    return out


def is_figure(figure):
    """Whether `figure` names a figure: one of `FIGURES`, or "phone:<ARPAbet phoneme>"."""
    if not isinstance(figure, str):
        return False
    kind, _, ph = figure.partition(":")
    return figure in FIGURES or (kind == "phone" and ph in PHONEMES)


def label(figure):
    """A figure's name ("Stressed syllables (%)", "Sound S per 1,000 words")."""
    return FIGURES[figure] if figure in FIGURES else f"Sound {figure.partition(':')[2]} per 1,000 words"


def value(t, figure):
    """One figure of a tally (see `is_figure`), None when there is nothing to take it of."""
    if figure in FIGURES:
        return figures(t)[figure]
    return 1000 * t["phones"][figure.partition(":")[2]] / t["words"] if t["words"] else None


def phoneme_rates(t):
    """Each phoneme per 1,000 words of a tally, most frequent first: [(phoneme, rate)]."""
    return [(p, 1000 * c / t["words"]) for p, c in t["phones"].most_common()] if t["words"] else []
