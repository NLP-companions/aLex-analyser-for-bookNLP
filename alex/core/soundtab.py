"""The Sound and rhythm tab: the figures of `core/prosody.py` over a part of the text, the cadences and runs found there with examples,
and the scansion of a passage.

The part of the text is a Corpus `Scope` (`corpus.Scope`): everything, narration, dialogue, or the quotes of one speaker (an entity, a
group, a tag or a gender). Its **units** (`units`) are the book's sentences, each cut to its tokens in the scope, so a sentence that
mixes narration and a quote gives the narration's words to one scope and the quote's to the other. A stretch's tally under a scope is
kept on the book (`tally_of`, with the positions of its runs and cadences), so the four sub-tabs share it.

* `figures`: per book, or per chapter or slice, the figures of `prosody.FIGURES` (as on the Style page, but for the scope);
* `cadences`: every cadence pattern found at phrase ends, how often, and how often at sentence ends; `cadence_examples` the phrases
  that end with one;
* `runs`: for one kind of run, what the runs share (a sound, a letter, a repeated word) with their numbers; `run_examples` the runs of
  one of them, longest first, each in its sentence;
* `scan`: one chapter or slice of a book, word by word with its syllables' stresses, and its runs and cadences;
* `guessed`: the words whose pronunciation is guessed, most frequent first, and the words you corrected; `lookup` how one word is said,
  as a starting point for correcting it (your corrections are saved with the workspace's settings, `settings.sound.corrections`).

Examples come as text with marks (`BookData.span_text`): `k` the run's or cadence's words, `rep` other repeated words in the sentence
(repetition runs: a word that repeats one nearby), so repetitions stand out wherever sound runs are shown.
"""
from __future__ import annotations

from collections import Counter

from . import narrative, prosody, sound
from .corpus import as_scope, cindex

MAX_ROWS = 500           # patterns or shared sounds listed
MAX_EXAMPLES = 100       # example phrases or runs shown
MAX_SCAN_WORDS = 3000    # words of a chapter or slice scanned at once (the rest is cut off, and the answer says so)
MAX_SPAN = 150           # tokens of text shown around an example
KEPT_SPANS = 4           # the tallies kept for a book cover at most this many times its length (see `tally_of`)


# ---------- a scope's units and tallies ----------
def _scope_key(scope, b):
    """What a scope means in book b, for keeping a tally: its kind, and for one speaker's quotes the groups they stand for there."""
    kind = scope.kind if scope.kind in ("narration", "dialogue", "speech") else "all"
    return (kind, scope.speaker_groups(b)) if kind == "speech" else (kind,)


def units(view, b, s, e, scope):
    """The units of tokens s..e of book b in a scope: each sentence (cut to the stretch) with only its tokens in the scope; empty ones
    are left out."""
    bd, mask = view.bd[b], scope.mask(b)
    out = []
    for u in prosody.sentence_units(bd, s, e):
        mine = u if mask is None else [t for t in u if mask[t]]
        if mine:
            out.append(mine)
    return out


def tally_of(view, b, s, e, scope, cfg):
    """The tally (with positions: `prosody.tally`'s `keep`) of tokens s..e of book b in a scope under the sound settings `cfg`. Worked
    out once per stretch, scope and setting and kept on the book, the most recently used first: a tally that keeps positions takes
    about 40 bytes a token, so what is kept for a book covers at most `KEPT_SPANS` times its length (older ones are dropped)."""
    bd = view.bd[b]
    kept = bd.kept("soundtab", budget=KEPT_SPANS * max(1, bd.n_tokens), cost=lambda key: max(0, key[1] - key[0] + 1))
    return kept.get((s, e, _scope_key(scope, b), prosody.signature(cfg)), lambda: prosody.count(bd, units(view, b, s, e, scope), cfg, keep=True))


def _whole(view, scope, cfg):
    """Each selected book's tally in the scope: [(book, tally)], in the view's order. RuntimeError without the dictionary."""
    if not sound.available():
        raise RuntimeError(sound.MISSING)
    scope = as_scope(view, scope)
    return [(b, tally_of(view, b, 0, view.bd[b].n_tokens - 1, scope, cfg)) for b in view.books]


# ---------- figures ----------
def figures(view, seg_cfg, by, scope, cfg):
    """The figures per book, or per chapter or slice (`by="segment"`), of the text in `scope`: `prosody.table`'s answer."""
    if not sound.available():
        raise RuntimeError(sound.MISSING)
    scope = as_scope(view, scope)
    return prosody.table(view, seg_cfg, by, cfg, lambda b, s, e: tally_of(view, b, s, e, scope, cfg))


# ---------- cadences ----------
def marks(pattern):
    """A stress pattern as / and x ("10010" -> "/ x x / x")."""
    return " ".join("/" if c == "1" else "x" for c in pattern)


def cadences(view, scope, cfg):
    """Every cadence pattern at the phrase ends of the selected books in a scope, most frequent first (at most `MAX_ROWS`): {rows:
    [{pattern, marks, type, n, pct (of phrase ends with a cadence), ends, end_pct (of sentence ends)}], types: {type: {n, pct, ends,
    end_pct}}, phrase_ends, sentence_ends, distinct}."""
    every, ends = Counter(), Counter()
    for _, t in _whole(view, scope, cfg):
        every.update(t["cadences"])
        ends.update(t["ends"])
    n, m = sum(every.values()), sum(ends.values())
    pct = lambda a, b: 100 * a / b if b else None
    rows = [{"pattern": p, "marks": marks(p), "type": prosody.cadence_type(p), "n": c, "pct": pct(c, n), "ends": ends[p],
             "end_pct": pct(ends[p], m)} for p, c in every.most_common(MAX_ROWS)]
    types = {}
    for name in (*prosody.CURSUS.values(), "other"):
        a = sum(c for p, c in every.items() if prosody.cadence_type(p) == name)
        b = sum(c for p, c in ends.items() if prosody.cadence_type(p) == name)
        types[name] = {"n": a, "pct": pct(a, n), "ends": b, "end_pct": pct(b, m)}
    return {"rows": rows, "types": types, "phrase_ends": n, "sentence_ends": m, "distinct": len(every)}


def cadence_examples(view, scope, cfg, pattern, end_only=False):
    """The phrases (in text order, at most `MAX_EXAMPLES`) that end with the cadence `pattern` ("10010"), or only those ending a
    sentence: {total, shown, items: [{book, title, tok, pos, text}]} with the cadence's words marked `k` and repetitions `rep`."""
    if not isinstance(pattern, str) or not pattern or set(pattern) - set("01"):
        raise ValueError("A cadence is a pattern of 1 (stressed) and 0 (unstressed), such as 10010.")
    items, total = [], 0
    for b, t in _whole(view, scope, cfg):
        reps = _repeated(t)
        for p, first, last, end in t["cadences_at"]:
            if p == pattern and (end or not end_only):
                total += 1
                if len(items) < MAX_EXAMPLES:
                    items.append(_example(view, b, first, last, [(first, last, "k")], reps))
    return {"total": total, "shown": len(items), "items": items}


# ---------- runs ----------
def key_text(key):
    """What a run shares, as text: a sound ("S"), a letter, a word, or several sounds ("AW N D")."""
    return " ".join(key) if isinstance(key, tuple) else str(key)


def _kind(kind):
    """`kind` if it is a kind of run (`prosody.RUNS`), else ValueError."""
    if kind not in prosody.RUNS:
        raise ValueError("Unknown kind of run: alliteration, assonance, consonance, rhyme or repetition.")
    return kind


def runs(view, scope, cfg, kind):
    """The runs of one kind in the selected books in a scope, by what they share (most runs first, at most `MAX_ROWS`): {kind, rows:
    [{key, runs, words, longest}], runs, words (in runs), eligible (words that could be in one), text_words, distinct}."""
    _kind(kind)
    by_key, longest = Counter(), Counter()
    words_in = Counter()
    eligible = text_words = 0
    for _, t in _whole(view, scope, cfg):
        eligible += t[kind + "_eligible"]
        text_words += t["words"]
        for k, key, toks in t["found"]:
            if k == kind:
                key = key_text(key)
                by_key[key] += 1
                words_in[key] += len(toks)
                longest[key] = max(longest[key], len(toks))
    rows = [{"key": key, "runs": n, "words": words_in[key], "longest": longest[key]} for key, n in by_key.most_common(MAX_ROWS)]
    return {"kind": kind, "rows": rows, "runs": sum(by_key.values()), "words": sum(words_in.values()), "eligible": eligible,
            "text_words": text_words, "distinct": len(by_key)}


def run_examples(view, scope, cfg, kind, key):
    """The runs of one kind that share `key` (as `key_text` writes it), longest first (then in text order; at most `MAX_EXAMPLES`):
    {total, shown, items: [{book, title, tok, pos, text, words}]}, the run's words marked `k` (`rep` for a repetition run) and the
    sentence's other repeated words `rep`."""
    _kind(kind)
    found = []
    order = {b: n for n, b in enumerate(view.books)}
    tallies = dict(_whole(view, scope, cfg))
    for b, t in tallies.items():
        found += [(b, toks) for k, kk, toks in t["found"] if k == kind and key_text(kk) == str(key)]
    found.sort(key=lambda x: (-len(x[1]), order[x[0]], x[1][0]))
    items = []
    for b, toks in found[:MAX_EXAMPLES]:
        bd = view.bd[b]
        cls = "rep" if kind == "repetition" else "k"
        item = _example(view, b, toks[0], toks[-1], [(t, t, cls) for t in toks], _repeated(tallies[b]))
        items.append({**item, "words": [bd.word[t] for t in toks]})
    return {"total": len(found), "shown": len(items), "items": items}


def _repeated(t):
    """The tokens of a tally's repetition runs (words that repeat one nearby)."""
    return {tok for k, _, toks in t["found"] if k == "repetition" for tok in toks}


def _example(view, b, first, last, own, repeated):
    """An example: the sentences from `first` to `last` (at most `MAX_SPAN` tokens, cut after `last` if needed) as text with marks
    `own` and the repeated words in it marked `rep` -> {book, title, tok, pos, text}."""
    bd = view.bd[b]
    s = bd.sent_bounds[bd.sent[first]][0]
    e = max(last, min(bd.sent_bounds[bd.sent[last]][1], s + MAX_SPAN))
    mine = {a for a, _, _ in own}
    reps = [(t, t, "rep") for t in range(s, e + 1) if t in repeated and t not in mine]
    return {"book": b, "title": view.title(b), "tok": first, "pos": round(100 * first / max(1, bd.n_tokens), 1),
            "text": bd.span_text(s, e, sorted(own + reps))}


# ---------- scansion ----------
def scan(view, book, seg_cfg, index, scope, cfg):
    """One chapter or slice of a book (the `index`th, cut by the Measure over setting `seg_cfg`; its first `MAX_SCAN_WORDS` words)
    word by word: {book, title, segments: [labels], index, label, start, end, cut, tokens, runs, cadences, figures, words}. Each token
    is {t (position), w (word), sp (a space before it), pa (paragraph), and for a word with a pronunciation m (its stresses, "1"/"0" a
    syllable) and src (yours, dict or guess); out: outside the scope}. `runs` are [{kind, key, toks}] and `cadences` [{pattern, type,
    first, last, end}] of the text in the scope; `figures` its figures."""
    if not sound.available():
        raise RuntimeError(sound.MISSING)
    if book not in view.bd:
        raise ValueError("That book isn't in the selection.")
    scope = as_scope(view, scope)
    segs, _ = narrative.book_segments(view, book, seg_cfg)
    if not 0 <= index < len(segs):
        raise ValueError(f"The book has {len(segs)} chapters or slices.")
    bd = view.bd[book]
    iw = cindex(bd)["isword"]
    s, end = segs[index]["start"], segs[index]["end"]
    e, n = s, 0
    while e <= end and n < MAX_SCAN_WORDS:                   # cut after the first MAX_SCAN_WORDS words
        n += iw[e]
        e += 1
    e -= 1
    t = tally_of(view, book, s, e, scope, cfg)
    prons, mask = sound.book_prons(bd, cfg["corrections"]), scope.mask(book)
    tokens = []
    for i in range(s, e + 1):
        item = {"t": i, "w": bd.word[i], "sp": _space_before(bd, i) if i > s else False, "pa": bd.para[i]}
        p = prons[i]
        if iw[i] and p is not None and p is not sound.JOINED:
            item.update(m=p.stress, src=p.source)
        if mask is not None and not mask[i]:
            item["out"] = True
        tokens.append(item)
    return {"book": book, "title": view.title(book), "segments": [sg["label"] for sg in segs], "index": index, "label": segs[index]["label"],
            "start": s, "end": e, "cut": e < end, "tokens": tokens, "words": t["words"], "figures": prosody.figures(t),
            "runs": [{"kind": k, "key": key_text(key), "toks": toks} for k, key, toks in t["found"]],
            "cadences": [{"pattern": p, "type": prosody.cadence_type(p), "first": a, "last": z, "end": end_}
                         for p, a, z, end_ in t["cadences_at"]]}


def _space_before(bd, i):
    """Whether the text has a space before token i: from the offsets as `BookData.span_text` reads them; without offsets, a space
    unless the token is punctuation."""
    if bd.onset[i] >= 0 and bd.offset[i - 1] >= 0:
        gap = bd.onset[i] - bd.offset[i - 1]
        return gap > 0 or (gap < 0 and bd.pos[i] != "PUNCT")
    return bd.pos[i] != "PUNCT"


# ---------- pronunciations: the words guessed, and one word ----------
MAX_GUESSED = 1000       # guessed words listed


def guessed(view, cfg):
    """The words of the selected books whose pronunciation is guessed (not in the dictionary, not corrected), most frequent first (at
    most `MAX_GUESSED`), and the words you corrected: {rows: [{word, n, books, guess (stress), book, tok (where it first occurs)}],
    yours: [{word, text, stress, n}], words, guessed (words guessed in all), corrected (words said as you corrected them)}."""
    if not sound.available():
        raise RuntimeError(sound.MISSING)
    counts, books, first, stress = Counter(), {}, {}, {}
    said_yours = Counter()
    words = 0
    for b in view.books:
        bd = view.bd[b]
        iw = cindex(bd)["isword"]
        for i, p in enumerate(sound.book_prons(bd, cfg["corrections"])):
            if not iw[i] or p is sound.JOINED:
                continue
            words += 1
            if p is None or p.source not in ("guess", "yours"):
                continue
            w = sound.norm(bd.word[i])
            if p.source == "yours":
                said_yours[w] += 1
                continue
            counts[w] += 1
            books.setdefault(w, set()).add(b)
            first.setdefault(w, (b, i))
            stress.setdefault(w, p.stress)
    rows = [{"word": w, "n": n, "books": len(books[w]), "guess": stress[w], "book": first[w][0], "tok": first[w][1]}
            for w, n in counts.most_common(MAX_GUESSED)]
    yours = []
    for w, text in sorted(cfg["corrections"].items()):
        try:
            p = sound.parse_correction(text)
        except ValueError:
            continue
        yours.append({"word": w, "text": text, "stress": p.stress, "n": said_yours[sound.norm(w)]})
    return {"rows": rows, "yours": yours, "words": words, "guessed": sum(counts.values()), "corrected": sum(said_yours.values())}


def lookup(word, cfg, pos=""):
    """How one word is said out of context (`sound.pronounce`, with your corrections), as a starting point for correcting it:
    {word (as kept), source, stress, text (to edit: phonemes, or the stress pattern), variants (the dictionary's, if any)}. ValueError
    for something that isn't one word."""
    if not sound.available():
        raise RuntimeError(sound.MISSING)
    w = sound.check_word(word)
    p = sound.pronounce(w, pos, cfg["corrections"])
    variants = list(sound.entries().get(w, ()))
    return {"word": w, "source": p.source, "stress": p.stress, "text": sound.as_text(p), "variants": variants}
