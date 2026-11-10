"""The cases of the Statistics tab: what one row of its data is.

Every correlation and every descriptive is computed over cases, one value per case and variable. There are two families:

* **Text pieces** (`kind` "pieces"): equal slices of each book (the default: `n` per book, or, with `slice_by` "words", one every
  `words` words), BookNLP sentences, chapters (your chapter edits apply; a book without headings falls back to slices), or whole books. A piece can be restricted to narration, dialogue or one speaker's quotes (the Corpus
  tools' `Scope`), and its **sample** is then the words of the piece in that scope.
* **Participants** (`kind` "participants"): entities, as people in a study. Who takes part is any spec `View.resolve` takes
  (default: every person above your minimum), and what counts as each one's sample is a choice (`SAMPLES`):
  what they say (their quotes), what they say and narrate (a narrator who is a character is that character, as in Described as;
  an unnamed or linked narrator is a participant of its own, with `narrators`), every sentence that mentions them, or what is
  said about them (their Described-as findings, counted in findings rather than words).

Cases whose sample is smaller than the minimum (`min`: words, or findings) are dropped, and so is any case with an empty sample; participants
who are in fewer than `min_range` of the selected books are dropped too (a setting of its own, apart from the one of Over the book);
`dropped` says how many and `left_out` which (for the R export's dropped.csv). Variables (counted later, by `core/variables.py`) are
measured in each case's sample: `Cases.at(b)` is a lookup from a token of book b to the cases whose sample holds it, made once, so a
variable is counted in one pass over its hits.
"""
from __future__ import annotations

from array import array

from . import described
from .bookdata import one_of
from .corpus import as_scope, cindex
from .dialogue import all_recs, narration_recs, role_unit, speaker_units
from .narrative import SLICE_WORDS, book_segments, word_slices

KINDS = {"pieces": "Text pieces", "participants": "Participants"}
PIECES = {"slice": "Equal slices", "sentence": "Sentences", "chapter": "Chapters", "book": "Books"}
SLICE_BY = {"count": "Slices per book", "words": "Words per slice"}
SAMPLES = {"speech": "What they say", "speech_narration": "What they say and narrate",
           "sentences": "Sentences mentioning them", "findings": "What is said about them (Described as)"}
DEFAULT_MIN = {"words": 100, "findings": 10, "sentence": 1}   # the minimum sample of a case: by what it is counted in; a sentence's own
EVERY_PERSON = {"kind": "type", "type": "PER"}       # the participants when none are chosen
NOTHING = ()                                         # the cases of a token in no case's sample


class Cases:
    """The cases of one request. `rows` are dicts with at least `id`, `label` and `size` (the sample: words, or findings when `unit`
    is "findings"); a piece also has `book`, `index`, `pos` (% into the book), `start` and `end`; a participant has `type` and `books`.
    `dropped` counts the cases left out for a sample below `min` (or empty), `left_out` lists them as {id, size}, a piece also with `book`,
    `index`, `pos`, `start` and `end` (no label: it is only made when someone asks). For a token sample `at(b)` finds the cases a token of book b is in;
    for the findings sample `findings[i]` lists case i's findings instead, as (kind, word, book, mention index). `books` are the books
    the samples are taken from (the view's, or fewer when `build` was asked for some), in the view's order."""

    def __init__(self, kind, sample, rows, left_out, minimum, books, unit="words", lookups=None, findings=None, min_range=1):
        self.kind, self.sample, self.rows, self.left_out, self.min, self.unit = kind, sample, rows, left_out, minimum, unit
        self.min_range = min_range                        # participants in fewer of the selected books were left out (1: no limit)
        self.dropped = len(left_out)
        self.books = books
        self.layer_units = None                           # the samples' units, made by `layers.units` when a layer needs them
        self.topic_words = {}                       # topic model id -> per case, its words in each of the model's documents (`layers.topic`)
        self.sound = {}                             # sound settings (`prosody.signature`) -> per case, its tally (`layers.sound`)
        self.word_choice = None                     # per case, the tally of its sample (`wordchoice.tally`), made once by `layers.word_choice`
        self._lookups = lookups or {}
        self.findings = findings

    def at(self, b):
        """A function telling which cases (a tuple of row indices) token i of book b is in the sample of. Empty for the findings sample."""
        return self._lookups.get(b, lambda i: NOTHING)

    def summary(self):
        """What the page says about the cases: kind, sample, how many, how many were dropped and the minimum."""
        return {"kind": self.kind, "sample": self.sample, "n": len(self.rows), "dropped": self.dropped, "min": self.min, "unit": self.unit, "min_range": self.min_range}


def build(view, setup, books=None):
    """The cases a request describes. `setup`: {kind ("pieces" or "participants"), piece (`PIECES`), slice_by (`SLICE_BY`), n (slices per
    book), words (words per slice), scope
    (as the Corpus tools'), population (a spec), sample (`SAMPLES`), narrators (narrator roles that aren't a character take part,
    default true), min (the smallest sample kept), min_range (participants: the fewest of the view's books one must be in, default 1)}. With `books`, samples are taken from those of the view's books only (a participant
    measured in one book: the descriptives split by book). Raises ValueError for an option it doesn't know."""
    setup = setup if isinstance(setup, dict) else {}
    books = [b for b in view.books if books is None or b in books]
    kind = setup.get("kind", "pieces")
    if kind == "pieces":
        return _pieces(view, setup, books)
    if kind == "participants":
        return _participants(view, setup, books)
    raise ValueError("Unknown kind of case: choose text pieces or participants.")


def _minimum(setup, unit):
    """The smallest sample a case may have (`min` of the setup, else the default for the unit); a readable error if it isn't a whole number."""
    value = setup.get("min", DEFAULT_MIN[unit])
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value or not 0 <= value <= 10 ** 7:
        raise ValueError("The minimum sample should be a whole number from 0 up.")
    return int(value)


def _min_range(setup):
    """The fewest books a participant must be in (`min_range` of the setup, default 1); a readable error if it isn't a whole number from 1 up."""
    value = setup.get("min_range", 1)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value or not 1 <= value <= 10 ** 5:
        raise ValueError("The minimum range (number of books) should be a whole number from 1 up.")
    return int(value)


_ONES = {}                                           # number -> (number,), see `_one`


def _one(i):
    """The tuple (i,), made once per number, so a lookup that answers a single case doesn't build a tuple per token."""
    t = _ONES.get(i)
    if t is None:
        t = _ONES[i] = (i,)
    return t


# ---------- text pieces ----------
def _pieces(view, setup, books):
    """Chapters, slices or books of the given books, each in the setup's scope, as cases (see `build`)."""
    piece, slice_by = setup.get("piece", "slice"), setup.get("slice_by", "count")
    if not (one_of(piece, PIECES) and one_of(slice_by, SLICE_BY)):
        raise ValueError("Unknown kind of text piece.")
    cfg = {"mode": "chapters"} if piece == "chapter" else {"mode": "slices", "n": setup.get("n", 10)}
    per = _slice_words(setup) if piece == "slice" and slice_by == "words" else None
    low, sc = _minimum(setup, "sentence" if piece == "sentence" else "words"), as_scope(view, setup.get("scope"))
    rows, left_out = [], []
    for b in books:
        bd = view.bd[b]
        iw, mask = cindex(bd)["isword"], sc.mask(b)
        inside = iw if mask is None else [w and m for w, m in zip(iw, mask)]
        segs = ([{"label": view.title(b), "start": 0, "end": bd.n_tokens - 1}] if piece == "book" else _sentences_of(bd) if piece == "sentence"
                else word_slices(bd, per) if per else book_segments(view, b, cfg)[0])
        for k, sg in enumerate(segs):
            size = sum(inside[sg["start"]:sg["end"] + 1])
            piece_id, pos = b if piece == "book" else f"{b}#{k}", round(100 * sg["start"] / max(1, bd.n_tokens), 1)
            if size == 0 or size < low:
                left_out.append({"id": piece_id, "book": b, "index": None if piece == "book" else k, "pos": pos,
                                 "start": sg["start"], "end": sg["end"], "size": size})
                continue
            rows.append({"id": piece_id, "book": b, "index": None if piece == "book" else k,
                         "label": view.title(b) if piece == "book" else f"{view.title(b)} · {sg['label'] if piece != 'sentence' else _opening(bd, sg)}",
                         "pos": pos, "start": sg["start"], "end": sg["end"], "size": size})
    lookups = {}
    for b in {r["book"] for r in rows}:
        lookups[b] = _piece_lookup(view.bd[b].n_tokens, [(i, r) for i, r in enumerate(rows) if r["book"] == b], sc.mask(b))
    sample = "book" if piece == "book" else piece
    return Cases("pieces", sample, rows, left_out, low, books, lookups=lookups)


def _slice_words(setup):
    """The words per slice asked for (`words`, default 200), or a readable error."""
    value = setup.get("words", 200)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value or not SLICE_WORDS[0] <= value <= SLICE_WORDS[1]:
        raise ValueError(f"Words per slice should be a whole number from {SLICE_WORDS[0]} to {SLICE_WORDS[1]:,}.")
    return int(value)


def _sentences_of(bd):
    """A book's sentences as pieces, in text order: {start, end} (their labels are made only for the sentences kept, `_opening`)."""
    return [{"start": s, "end": e} for s, e in sorted(bd.sent_bounds.values())]


def _opening(bd, sg):
    """A sentence's label: its first words ("It was a dark and stormy…")."""
    end = min(sg["end"], sg["start"] + 9)
    text = bd.span_text(sg["start"], end).strip()
    return text + ("…" if end < sg["end"] else "")


def _piece_lookup(n_tokens, indexed, mask):
    """token -> (case,) for the pieces of one book, `indexed` being (row index, row) pairs; a token outside the scope is in none."""
    owner = array("i", [-1]) * n_tokens
    for i, r in indexed:
        owner[r["start"]:r["end"] + 1] = array("i", [i]) * (r["end"] - r["start"] + 1)
    if mask is None:
        return lambda t: NOTHING if owner[t] < 0 else _one(owner[t])
    return lambda t: NOTHING if owner[t] < 0 or not mask[t] else _one(owner[t])


# ---------- participants ----------
def _population(view, spec):
    """The unit ids of the participants a spec names, in the view's order (only units: entities above your minimum)."""
    if not isinstance(spec, dict):
        raise ValueError("Say who takes part: an entity, a group, a tag, a gender or a type.")
    members = view.resolve(spec)[0]
    chosen = {view.member_unit.get(m) for m in members}
    return [uid for uid in view.units if uid in chosen]


def _participants(view, setup, books):
    """Participants and their samples in the given books, as cases (see `build`)."""
    sample = setup.get("sample", "speech")
    if not one_of(sample, SAMPLES):
        raise ValueError("Unknown sample: choose what they say, what they say and narrate, sentences mentioning them, or what is said about them.")
    unit = "findings" if sample == "findings" else "words"
    low, few = _minimum(setup, unit), _min_range(setup)
    ids, inside = _population(view, setup.get("population") or EVERY_PERSON), set(books)
    index = {uid: i for i, uid in enumerate(ids)}
    size, findings, lookups = [0] * len(ids), None, {}
    if sample in ("speech", "speech_narration"):
        lookups = _speech(view, index, size, sample == "speech_narration", setup.get("narrators", True) is not False, ids, inside)
    elif sample == "sentences":
        lookups = _sentences(view, ids, size, inside)
    else:
        findings = [[(k, key, b, mi) for k in described.KINDS for b, mi, key, _ in described.findings(view, _members(view, uid, inside), k)]
                    for uid in ids]
        size = [len(f) for f in findings]
    in_books = lambda uid: len(view.units[uid].books) if uid in view.units else len(_role_books(view, uid, set(view.books)))     # of all the selected books
    keep = [i for i in range(len(ids)) if size[i] and size[i] >= low and (few <= 1 or in_books(ids[i]) >= few)]
    renumber = {old: new for new, old in enumerate(keep)}
    labels = described.column_labels(view, "entity", [ids[i] for i in keep])
    rows = []
    for i in keep:
        uid = ids[i]
        u = view.units.get(uid)
        rows.append({"id": uid, "label": labels[uid], "type": u.type if u else "NARR", "size": size[i],
                     "books": [b for b in books if b in u.books] if u else _role_books(view, uid, inside)})
    lookups = {b: _renumbered(f, renumber) for b, f in lookups.items()}
    left_out = [{"id": ids[i], "size": size[i]} for i in range(len(ids)) if i not in renumber]
    return Cases("participants", sample, rows, left_out, low, books, unit, lookups,
                 [findings[i] for i in keep] if findings is not None else None, few)


def _renumbered(lookup, renumber):
    """A token lookup whose case numbers are those after dropping: cases not kept disappear from its answers."""
    memo = {}

    def at(t):
        """The kept cases of token t."""
        found = lookup(t)
        if not found:
            return NOTHING
        out = memo.get(found)
        if out is None:
            out = memo[found] = tuple(renumber[i] for i in found if i in renumber)
        return out
    return at


def _members(view, uid, inside):
    """A unit's members ((book, coref) pairs) in the books of `inside`."""
    return [m for m in view.units[uid].members if m[0] in inside]


def _speech(view, index, size, narration, narrators, ids, inside):
    """Lookups for the speech samples (and narration, with `narration`), filling `size` with each participant's words. A quote counts
    for each of its speakers (a plural speaker's members too, when plural groups count for them); a paragraph's narration for its
    narrator's character, or, with `narrators`, for a narrator role that is no one character (added to `ids` as a participant)."""
    quotes, paras = {}, {}
    for b, r in all_recs(view):
        if b not in inside:
            continue
        who = tuple(index[u] for u in speaker_units(view, b, r) if u in index)
        if who:
            quotes.setdefault(b, {})[r["qi"]] = who
            for i in who:
                size[i] += r["n"]
    if narration:
        for b, r in narration_recs(view):
            if b not in inside:
                continue
            rid = r["role"]
            uid = role_unit(rid)
            if uid not in index and not (uid is None and narrators):
                continue
            key = uid if uid is not None else rid
            if key not in index:
                index[key] = len(ids)
                ids.append(key)
                size.append(0)
            paras.setdefault(b, {})[r["para"]] = _one(index[key])
            size[index[key]] += r["n"]
    lookups = {}
    for b in set(quotes) | set(paras):
        bd, q, p = view.bd[b], quotes.get(b, {}), paras.get(b, {})
        lookups[b] = _speech_lookup(bd.quote_at, bd.para, cindex(bd)["in_quote"], q, p)
    return lookups


def _speech_lookup(quote_at, para, in_quote, quotes, paras):
    """token -> participants: the speakers of the quote it is in, else the narrator of its paragraph (when narration counts)."""
    def at(t):
        """The participants whose sample holds token t."""
        qi = quote_at.get(t)
        if qi is not None:
            return quotes.get(qi, NOTHING)
        return NOTHING if in_quote[t] else paras.get(para[t], NOTHING)
    return at


def _sentences(view, ids, size, inside):
    """Lookups for the "sentences mentioning them" sample, filling `size` with the words of each participant's sentences."""
    by_sent = {}                                                    # book -> sentence id -> set of participants
    for i, uid in enumerate(ids):
        for b, c in _members(view, uid, inside):
            bd = view.bd[b]
            sents = by_sent.setdefault(b, {})
            for mi in bd.groups[c].mentions:
                sents.setdefault(bd.sent[bd.mentions[mi][1]], set()).add(i)
    lookups = {}
    for b, sents in by_sent.items():
        bd, iw = view.bd[b], cindex(view.bd[b])["isword"]
        frozen = {}
        for sid, who in sents.items():
            s, e = bd.sent_bounds[sid]
            words = sum(iw[s:e + 1])
            for i in who:
                size[i] += words
            frozen[sid] = tuple(sorted(who))
        sent = bd.sent
        lookups[b] = lambda t, frozen=frozen, sent=sent: frozen.get(sent[t], NOTHING)
    return lookups


def _role_books(view, rid, inside):
    """The books of `inside` a narrator role (that is no one unit) narrates in, in the view's order."""
    return list(dict.fromkeys(b for b, r in narration_recs(view) if r["role"] == rid and b in inside))
