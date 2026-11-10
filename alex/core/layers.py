"""Linguistic layers as variables of the Statistics tab: supersenses, relations, sentiment, lexicon categories, style figures, word choice and topics.

They are measured in each case's sample (`core/cases.py`) like the other variables (`core/variables.py`, which hands these kinds here):

* **supersense**: BookNLP supersense spans (a run of tokens with the same supersense counts once) starting in the sample;
* **relation**: findings of one relation (actions, done to them, modifiers, possessions, prepositions: `described.findings`) of a target's
  mentions (default: every entity), optionally only one word, counted where the mention starts, as mentions are;
* **sentiment**: VADER's compound score of each of the sample's **units**, averaged, or the share of positive or negative units;
* **lexicon**: words of one category of one of your word lexicons (by form, else by lemma): the emotion lexicon, and any other lexicon
  stored beside it (`lexicons.stored`: every `<id>.json` in the lexicon folder);
* **speech**: the sample's quotes of one sentence type (question, exclamation or statement, as `dialogue.sentence_type` decides, optionally
  weighing the speech verb), each counted where its first word is, as a query's hit is;
* **style**: figures of the sample's words (word length, MATTR, hapaxes, lexical density, passives) and of its units (unit length,
  questions, exclamations);
* **wordchoice**: a figure of `core/wordchoice.py` of the sample's words: part-of-speech shares, adjective, adverb and noun per verb ratios,
  dynamic and static verbs, shares of verbs and nouns per supersense category, supersenses per 1,000 words;
* **sound**: a sound and rhythm figure of the sample's units (`prosody.FIGURES`: stress, cadences, sound runs, the sound profile), or
  one phoneme per 1,000 words, under the workspace's sound settings; needs the optional pronunciation dictionary;
* **topic**: one topic of a stored topic model, as its share (%) of the sample's words: each word takes the topic's weight in the model
  document it falls in (each document counts as topic text to the extent of its share, as in Topics), and the value is their mean. Words
  outside the model's documents (books it wasn't fitted on) don't count; a case with none has no value, and the note says how many.

A sample's units (`units`) are what it is made of: BookNLP sentences for text pieces and for "sentences mentioning them" (in a piece, only the
part of a sentence inside the piece and its scope), each quote for speech, each paragraph's narration for narration. None of these apply to
the findings sample, which has no running text.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import chain, groupby

from . import described, prosody, sound as pron, wordchoice
from .bookdata import TYPES, one_of
from .corpus import cindex, value_matcher
from .dialogue import SENTENCE_TYPES, all_recs, mattr, narration_recs, sentence_type
from .lexicons import EMOTION, heading
from .narrative import CONTENT, sentence_scores, vader_available

KINDS = {"supersense": "Supersense", "relation": "Relation", "sentiment": "Sentiment", "lexicon": "Lexicon", "speech": "Speech sentence type",
         "style": "Style", "wordchoice": "Word choice", "sound": "Sound and rhythm", "topic": "Topic"}
RELATIONS = {k: described.KINDS[k] for k in ("agent", "patient", "mod", "poss", "prep")}
SENTIMENT = {"mean": "Sentiment (mean compound)", "positive": "Positive units (%)", "negative": "Negative units (%)"}
STYLE = {"word_length": "Word length (letters)", "mattr": "MATTR", "hapax": "Hapaxes (% of words)", "density": "Lexical density (%)",
         "passives": "Passives per 1,000 words", "unit_length": "Unit length (words)", "questions": "Questions (% of units)",
         "exclaims": "Exclamations (% of units)"}
SPEECH_TYPES = dict(zip(SENTENCE_TYPES, ("Questions", "Exclamations", "Statements")))     # the labels of `dialogue.SENTENCE_TYPES`, in order
SPEECH_SAMPLES = ("speech", "speech_narration")      # the participants' samples that hold quotes
COUNTED = {"supersense", "relation", "lexicon", "speech"}      # kinds that count something (and so take a measure); the others are values
EVERY_ENTITY = {"kind": "type", "types": TYPES, "type": "ALL"}
POSITIVE, NEGATIVE = 0.05, -0.05                     # VADER's usual thresholds, as on the sentiment page


class NotHere(ValueError):
    """A layer that can't be measured in these cases (or without VADER, a lexicon or a topic model); the message becomes the variable's note."""


def check(spec, out):
    """Check a layer variable's own fields into `out` (the checked spec `variables.check` is making). Raises ValueError."""
    kind = out["kind"]
    if kind == "supersense":
        out["value"] = _text(spec.get("value"), "Choose a supersense.")
    elif kind == "relation":
        out.update(rel=spec.get("rel", "agent"), word=str(spec.get("word") or "").strip()[:200], target=spec.get("target") or None)
        if not one_of(out["rel"], RELATIONS):
            raise ValueError("Unknown relation.")
        if out["target"] is not None and (not isinstance(out["target"], dict) or not out["target"].get("kind")):
            raise ValueError("Say whose relations: an entity, a group, a tag, a gender or a type.")
    elif kind == "sentiment":
        out["stat"] = spec.get("stat", "mean")
        if not one_of(out["stat"], SENTIMENT):
            raise ValueError("Unknown sentiment figure.")
    elif kind == "lexicon":
        out["lexicon"] = _text(spec.get("lexicon") or EMOTION, "Choose a lexicon.")
        out["category"] = _text(spec.get("category"), "Choose a category of the lexicon.").lower()
    elif kind == "speech":
        out.update(type=spec.get("type", "question"), weigh=bool(spec.get("weigh")))
        if not one_of(out["type"], SPEECH_TYPES):
            raise ValueError("Unknown sentence type: choose questions, exclamations or statements.")
    elif kind == "topic":
        out["model"] = _text(spec.get("model"), "Choose a topic model.")
        if isinstance(spec.get("topic"), bool) or not isinstance(spec.get("topic"), int) or spec["topic"] < 0:
            raise ValueError("Choose a topic.")
        out["topic"] = spec["topic"]
    elif kind == "style":
        out["figure"] = spec.get("figure")
        if not one_of(out["figure"], STYLE):
            raise ValueError("Unknown style figure.")
    elif kind == "wordchoice":
        out["figure"] = spec.get("figure")
        if not wordchoice.is_figure(out["figure"]):
            raise ValueError("Unknown word-choice figure.")
    elif kind == "sound":
        out["figure"] = spec.get("figure")
        if not prosody.is_figure(out["figure"]):
            raise ValueError("Unknown sound and rhythm figure.")
    return out


def _text(value, message):
    """A non-empty string (at most 200 characters), else a ValueError with `message`."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(message)
    return value.strip()[:200]


def label(view, spec, lexicons=None):
    """A layer variable's heading ("Supersense verb.communication", "Actions of Holmes: say", "Emotion: fear", "MATTR",
    "Topic 3: moor · mire · hound")."""
    kind = spec["kind"]
    if kind == "supersense":
        return f"Supersense {spec['value']}"
    if kind == "relation":
        from .variables import who as name_of
        who = name_of(view, spec["target"]) if spec["target"] else "any entity"
        return f"{RELATIONS[spec['rel']]} of {who}" + (f": “{spec['word']}”" if spec["word"] else "")
    if kind == "sentiment":
        return SENTIMENT[spec["stat"]]
    if kind == "lexicon":
        return f"{heading(spec['lexicon'], (lexicons or {}).get(spec['lexicon']))}: {spec['category']}"
    if kind == "speech":
        return f"{SPEECH_TYPES[spec['type']]} in speech" + (" (speech verb weighed)" if spec["weigh"] else "")
    if kind == "topic":
        return topic_name(spec["model"], spec["topic"])
    if kind == "wordchoice":
        return wordchoice.label(spec["figure"])
    if kind == "sound":
        return prosody.label(spec["figure"])
    return STYLE[spec["figure"]]


def _topic_names(T):
    """Every topic of a model as it is called on the Topics page: your label, else its three most distinctive words."""
    from .topics.compare import model_topics
    return [t["label"] or " · ".join(w["w"] for w in t["distinctive"][:3]) for t in model_topics(T)]


def topic_name(mid, t):
    """A topic variable's heading ("Topic 3: moor · mire · hound"), or a plain "Topic 3 of <model>" when the model can't be read."""
    try:
        from .topics.page import Topic
        return f"Topic {t + 1}: {_topic_names(Topic(mid, 0))[t]}"
    except (ImportError, OSError, ValueError, KeyError, IndexError):
        return f"Topic {t + 1} of {mid}"


# ---------- measuring ----------
def _running_text(cases):
    """Refuse the findings sample, which has no running text."""
    if cases.unit == "findings":
        raise NotHere("This needs running text; the Described-as sample is a list of findings.")


def typed_quotes(view, cases, types=None, weigh=False):
    """The (book, quote record) pairs of the cases' books that have words and are of one of the sentence types `types` (any when empty;
    see `dialogue.sentence_type`, `weigh` lets the speech verb decide too)."""
    return [(b, r) for b, r in all_recs(view)
            if b in cases.books and r["tokens"] and (not types or sentence_type(r, weigh) in types)]


def quote_counts(view, cases, types=None, weigh=False):
    """How many quotes of the given sentence types (`typed_quotes`) start in each case's sample: a quote counts where its first word is,
    for each case holding it, so a quote said by two participants counts for both. Needs quotes in the sample: any text piece, or a
    participant's speech (with or without narration)."""
    _running_text(cases)
    if cases.kind == "participants" and cases.sample not in SPEECH_SAMPLES:
        raise NotHere("Sentence types are of quotes: choose “What they say” or “What they say and narrate” as the sample.")
    out = [0] * len(cases.rows)
    for b, r in typed_quotes(view, cases, types, weigh):
        for k in cases.at(b)(r["tokens"][0]):
            out[k] += 1
    return out


def counts(view, cases, spec, lexicons=None):
    """How many of the counted thing (supersense spans, relation findings, lexicon words, quotes of a sentence type) each case's sample holds. `lexicons` are
    your word lexicons by id (`lexicons.stored`)."""
    if spec["kind"] == "speech":
        return quote_counts(view, cases, {spec["type"]}, spec["weigh"])
    _running_text(cases)
    out = [0] * len(cases.rows)
    if spec["kind"] == "supersense":
        for b in cases.books:
            ss, at = view.bd[b].ss, cases.at(b)
            for i, cat in ss.items():
                if cat == spec["value"] and ss.get(i - 1) != cat:
                    for k in at(i):
                        out[k] += 1
    elif spec["kind"] == "relation":
        test = value_matcher(spec["word"]) if spec["word"] else None
        inside = set(cases.books)
        members = [m for m in view.resolve(spec["target"] or EVERY_ENTITY)[0] if m[0] in inside]
        for b, mi, key, _ in described.findings(view, members, spec["rel"]):
            if test is None or test(key):
                for k in cases.at(b)(view.bd[b].mentions[mi][1]):
                    out[k] += 1
    else:
        lexicon = (lexicons or {}).get(spec["lexicon"])
        if not lexicon:
            raise NotHere("Load the emotion lexicon first (Over time → Lexicons)." if spec["lexicon"] == EMOTION
                          else f"There is no lexicon “{spec['lexicon']}” in this workspace.")
        words = set(lexicon["cats"].get(spec["category"], ()))
        if not words:
            raise NotHere(f"The lexicon “{heading(spec['lexicon'], lexicon)}” has no category “{spec['category']}”.")
        for b in cases.books:
            bd, at = view.bd[b], cases.at(b)
            ci = cindex(bd)
            for i, w in enumerate(ci["isword"]):
                if w and (ci["lower"][i] in words or ci["lemma_lower"][i] in words):
                    for k in at(i):
                        out[k] += 1
    return out


def units(view, cases):
    """The units of every case's sample: per case, a list of (book, token positions in the sample, whole sentence id or None), in text
    order. Made once per `Cases` (kept on it)."""
    if cases.layer_units is not None:
        return cases.layer_units
    _running_text(cases)
    out = [[] for _ in cases.rows]
    spans = defaultdict(list)                       # book -> (first, last, sentence id or None, which of its tokens belong)
    if cases.sample in ("speech", "speech_narration"):
        for b, r in all_recs(view):                 # a quote: its own tokens
            if b in cases.books:
                spans[b].append((r["start"], r["end"], None, lambda t, b=b, qi=r["qi"]: view.bd[b].quote_at.get(t) == qi))
        for b, r in narration_recs(view):           # a paragraph's narration: its tokens outside quotes
            if b in cases.books:
                spans[b].append((r["start"], r["end"], None, lambda t, q=cindex(view.bd[b])["in_quote"]: not q[t]))
    else:
        for b in cases.books:
            spans[b] = [(s, e, sid, None) for sid, (s, e) in view.bd[b].sent_bounds.items()]
    for b in cases.books:
        at = cases.at(b)
        for s, e, sid, own in sorted(spans[b], key=lambda x: x[0]):
            by_case = defaultdict(list)
            for t in range(s, e + 1):
                if own is None or own(t):
                    for k in at(t):
                        by_case[k].append(t)
            for k, toks in by_case.items():
                out[k].append((b, toks, sid if sid is not None and len(toks) == e - s + 1 else None))
    cases.layer_units = out
    return out


def _score(view, b, toks, sid, sia, memo):
    """VADER's compound score of one unit: a whole sentence's from the book's own cache, else of the unit's text."""
    if sid is not None:
        return sentence_scores(view.bd[b])[sid]
    key = (b, toks[0], toks[-1], len(toks))
    if key not in memo:
        bd = view.bd[b]
        text = bd.span_text(toks[0], toks[-1]) if toks[-1] - toks[0] + 1 == len(toks) else " ".join(bd.word[t] for t in toks)
        memo[key] = sia.polarity_scores(text)["compound"]
    return memo[key]


def sentiment(view, cases, stat):
    """Per case: the mean compound score of its units, or the share (%) of positive or negative ones; None without units."""
    if not vader_available():
        raise NotHere("Sentiment needs the vaderSentiment package (pip install vaderSentiment).")
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    sia, memo, out = SentimentIntensityAnalyzer(), {}, []
    for us in units(view, cases):
        scores = [_score(view, b, toks, sid, sia, memo) for b, toks, sid in us]
        if not scores:
            out.append(None)
        elif stat == "mean":
            out.append(sum(scores) / len(scores))
        else:
            out.append(100 * sum(v >= POSITIVE if stat == "positive" else v <= NEGATIVE for v in scores) / len(scores))
    return out


def style(view, cases, figure):
    """Per case: one style figure of its sample (see `STYLE`); None when it has no words."""
    out = []
    for us in units(view, cases):
        words, lengths, marks = [], [], Counter()
        for b, toks, _ in us:
            bd, iw = view.bd[b], cindex(view.bd[b])["isword"]
            mine = [(b, t) for t in toks if iw[t]]
            if not mine:
                continue
            words += mine
            lengths.append(len(mine))
            marks["?"] += any(bd.word[t] == "?" for t in toks)
            marks["!"] += any(bd.word[t] == "!" for t in toks)
        out.append(_figure(view, figure, words, lengths, marks) if words else None)
    return out


def _figure(view, figure, words, lengths, marks):
    """One style figure of a sample's words ((book, token) pairs), its units' word counts and how many units have ? or !."""
    n = len(words)
    if figure == "unit_length":
        return n / len(lengths)
    if figure in ("questions", "exclaims"):
        return 100 * marks["?" if figure == "questions" else "!"] / len(lengths)
    if figure == "word_length":
        return sum(len(view.bd[b].word[t]) for b, t in words) / n
    if figure == "passives":
        return 1000 * sum(view.bd[b].dep[t] == "nsubjpass" for b, t in words) / n
    if figure == "density":
        return 100 * sum(view.bd[b].pos[t] in CONTENT for b, t in words) / n
    lower = [cindex(view.bd[b])["lower"][t] for b, t in words]
    if figure == "hapax":
        return 100 * sum(1 for c in Counter(lower).values() if c == 1) / n
    return mattr(lower)[0]


def sound(view, cases, figure):
    """Per case: one sound and rhythm figure of its sample (`prosody.value`); None when it has no words. The cases' tallies are
    counted once per sound setting (the workspace's window, boundary and corrections) and kept on the `Cases`, so every sound
    variable of a table shares them."""
    if not pron.available():
        raise NotHere(pron.MISSING)
    cfg = prosody.config(view.lib.state["settings"])
    key = prosody.signature(cfg)
    if key not in cases.sound:
        tallies = []
        for us in units(view, cases):
            t = prosody.empty()
            for b, group in groupby(us, key=lambda u: u[0]):          # a case's units come book by book
                t = prosody.add(t, prosody.count(view.bd[b], [toks for _, toks, _ in group], cfg))
            tallies.append(t if t["words"] else None)
        cases.sound[key] = tallies
    return [prosody.value(t, figure) if t else None for t in cases.sound[key]]


def word_choice(view, cases, figure):
    """Per case: one word-choice figure of its sample (`wordchoice.value`); None when it has no words. A case's tally is taken book by
    book once and kept on the `Cases` (tallies are small; the figures are worked out per variable), so a table of thirty such variables
    counts the text once."""
    if cases.word_choice is None:
        cases.word_choice = []
        for us in units(view, cases):
            t = wordchoice.empty()
            for b, group in groupby(us, key=lambda u: u[0]):          # a case's units come book by book
                t = wordchoice.add(t, wordchoice.tally(view.bd[b], chain.from_iterable(toks for _, toks, _ in group)))
            cases.word_choice.append(t if t["words"] else None)
    return [wordchoice.value(t, figure) if t else None for t in cases.word_choice]


def values(view, cases, spec):
    """(values, note) of a non-counting layer (sentiment, style, word choice, sound, topic), one value per case; the note says how many cases a
    topic model doesn't cover (None when all are)."""
    _running_text(cases)
    if spec["kind"] == "topic":
        return topic(view, cases, spec["model"], spec["topic"])
    if spec["kind"] == "wordchoice":
        return word_choice(view, cases, spec["figure"]), None
    if spec["kind"] == "sound":
        return sound(view, cases, spec["figure"]), None
    return (sentiment(view, cases, spec["stat"]) if spec["kind"] == "sentiment" else style(view, cases, spec["figure"])), None


def _topic_model(view, mid):
    """The stored model as a `Topic` checked against the view (its selected books unchanged), or NotHere saying why not."""
    try:
        from .topics.errors import TopicError
        from .topics.page import Topic
    except ImportError:
        raise NotHere("Topics need scikit-learn and numpy.") from None
    try:
        return Topic(mid, 0, view, strict=False)
    except TopicError as e:
        raise NotHere(str(e)) from None
    except (OSError, ValueError, KeyError):
        raise NotHere("That topic model no longer exists, or can't be read.") from None


def topic(view, cases, mid, t):
    """(values, note): per case, topic t's share (%) of the sample's words that fall in the model's documents; None for a case with
    none. The words of each case in each document are counted once per model and kept on the `Cases`."""
    T = _topic_model(view, mid)
    if t >= T.k:
        raise NotHere(f"The model has {T.k} topics.")
    memo = cases.topic_words
    if mid not in memo:
        per = [defaultdict(int) for _ in cases.rows]       # case -> document -> words of its sample in that document
        for b in cases.books:
            if b not in T.by_book:
                continue
            at, iw = cases.at(b), cindex(view.bd[b])["isword"]
            for i in T.by_book[b]:
                d = T.docs[i]
                for tok in range(d["start"], d["end"] + 1):
                    if iw[tok]:
                        for k in at(tok):
                            per[k][i] += 1
        memo[mid] = per
    out = []
    for docs in memo[mid]:
        n = sum(docs.values())
        out.append(100 * sum(c * T.theta[i, t] for i, c in docs.items()) / n if n else None)
    missing = sum(v is None for v in out)
    outside = [view.title(b) for b in cases.books if b not in T.by_book]
    note = None
    if missing:
        note = (f"The model “{T.m['name'] or mid}” covers {len(cases.books) - len(outside)} of the {len(cases.books)} books"
                + (f" (not {', '.join(outside)})" if outside else "") + f": {missing} of {len(out)} cases have no value and are left out.")
    return out, note


def options(view, lexicons=None):
    """What the page offers for the layers: the supersenses found in the selected books (most frequent first), the relations, the
    sentiment, style, word-choice (in sections) and sound figures (and the phonemes a sound figure can be), your lexicons with their categories, the topic models
    sharing books with the selection (with their topics, and which of the selected books they cover), and whether VADER and the
    pronunciation dictionary are installed."""
    found = Counter()
    for b in view.books:
        ss = view.bd[b].ss
        found.update(cat for i, cat in ss.items() if ss.get(i - 1) != cat)
    lex = sorted(({"id": lid, "name": heading(lid, x), "categories": sorted(x["cats"])} for lid, x in (lexicons or {}).items()),
                 key=lambda x: (x["id"] != EMOTION, x["name"].lower()))
    return {"supersenses": [{"value": c, "n": n} for c, n in found.most_common()], "relations": RELATIONS, "sentiment": SENTIMENT,
            "style": STYLE, "wordchoice": [{"id": k, "title": t, "figures": f} for k, t, f in wordchoice.SECTIONS], "sound": prosody.FIGURES, "phonemes": prosody.PHONEMES, "lexicons": lex, "topics": _topic_models(view),
            "vader": vader_available(), "sound_ready": pron.available()}


def _topic_models(view):
    """The stored topic models fitted on at least one selected book: {id, name, covers (selected books it was fitted on), all (it covers
    every selected book), topics: [names]}. A model that can't be read, or whose books changed, is left out."""
    try:
        from .topics import store
        from .topics.page import Topic
    except ImportError:
        return []
    out = []
    for m in store.list_models():
        covers = [b for b in view.books if b in m["books"]]
        if not covers:
            continue
        try:
            names = _topic_names(Topic(m["id"], 0, view, strict=False))
        except (OSError, ValueError, KeyError):
            continue
        out.append({"id": m["id"], "name": m["name"] or m["id"], "covers": covers, "all": len(covers) == len(view.books), "topics": names})
    return out
