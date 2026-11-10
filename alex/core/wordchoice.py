"""Word-choice figures: which parts of speech and kinds of word a text leans on (vivid adjectives against dynamic verbs, nominal against verbal style).

A **tally** counts a stretch of one book, given as token positions in any order or grouping (a book, a chapter, one speaker's quotes, a
participant's sample), into raw counts: the words, each part of speech, and the supersense spans of nouns and verbs. `add` sums tallies
(neither is changed), so books, quotes and cases pool by adding; `figures` turns one into the figures of `FIGURES`. MEASURES.md section 18
explains each. A caller passes every token once; non-words (punctuation, quotation marks) are never counted as words.

* **Parts of speech** (`POS`, the Style page's profile): the share (%) of words that are each part of speech, as BookNLP tags them.
* **Ratios** (`RATIOS`): adjectives, adverbs or nouns (not proper nouns) per verb (POS VERB; auxiliaries are not verbs here), and modifiers per head,
  (adjectives + adverbs) / (nouns + verbs). None when the divisor is 0.
* **Tables**: `table` gives the figures per book, or per chapter or slice (the Style page), from the tally of each stretch,
  worked out once and kept on the book (`span_tally`).
* **Supersenses** are BookNLP's WordNet categories, which exist for nouns (`noun.*`) and verbs (`verb.*`) only. A span (consecutive tokens
  with the same supersense) is counted once, where it starts, so a span cut by the sample's edge counts only if its first token is in the
  sample, as in the Statistics layer. Three ways to read them: `ss:<category>` per 1,000 words, `verb:<name>` / `noun:<name>` the share (%)
  of the sample's verb (noun) spans, and `verbs:dynamic` / `verbs:static`, the share of verb spans in the groups `DYNAMIC` and `STATIC`
  (every verb category is in one of them, so the two add up to 100%).
"""
from __future__ import annotations

from collections import Counter

from .corpus import cindex

POS = {"NOUN": "Nouns", "PROPN": "Proper nouns", "VERB": "Verbs", "ADJ": "Adjectives", "ADV": "Adverbs", "PRON": "Pronouns", "ADP": "Prepositions",
       "DET": "Determiners", "CCONJ": "Coordinating conjunctions", "SCONJ": "Subordinating conjunctions", "AUX": "Auxiliaries"}
# ratio -> (label, numerator parts of speech, divisor parts of speech)
RATIOS = {"adj_verb": ("Adjectives per verb", ("ADJ",), ("VERB",)),
          "adv_verb": ("Adverbs per verb", ("ADV",), ("VERB",)),
          "noun_verb": ("Nouns per verb", ("NOUN",), ("VERB",)),
          "mod_head": ("Modifiers per head", ("ADJ", "ADV"), ("NOUN", "VERB"))}
VERB_SS = ("body", "change", "cognition", "communication", "competition", "consumption", "contact", "creation", "emotion", "motion",
           "perception", "possession", "social", "stative", "weather")                   # WordNet's verb categories
NOUN_SS = ("Tops", "act", "animal", "artifact", "attribute", "body", "cognition", "communication", "event", "feeling", "food", "group",
           "location", "motive", "object", "person", "phenomenon", "plant", "possession", "process", "quantity", "relation", "shape",
           "state", "substance", "time")                                                   # and its noun categories
DYNAMIC = frozenset({"motion", "contact", "change", "body", "creation", "competition", "consumption", "weather"})
STATIC = frozenset(VERB_SS) - DYNAMIC              # stative, cognition, perception, emotion, possession, social, communication
GROUPS = {"dynamic": DYNAMIC, "static": STATIC}


# the figures in sections, as a page offers them: (section, title, {figure: label})
SECTIONS = (
    ("parts", "Parts of speech", {f"pos:{p}": f"{name} (% of words)" for p, name in POS.items()}),
    ("ratios", "Ratios", {f"ratio:{k}": label for k, (label, _, _) in RATIOS.items()}),
    ("verbgroups", "Dynamic and static verbs", {f"verbs:{g}": f"{g.capitalize()} verbs (% of verbs)" for g in GROUPS}),
    ("verbs", "Verbs by category", {f"verb:{c}": f"Verbs of {c} (% of verbs)" for c in VERB_SS}),
    ("nouns", "Nouns by category", {f"noun:{c}": f"Nouns of {c} (% of nouns)" for c in NOUN_SS}),
    ("ssverbs", "Verb supersenses per 1,000 words", {f"ss:verb.{c}": f"Supersense verb.{c} per 1,000 words" for c in VERB_SS}),
    ("ssnouns", "Noun supersenses per 1,000 words", {f"ss:noun.{c}": f"Supersense noun.{c} per 1,000 words" for c in NOUN_SS}))
FIGURES = {k: label for _, _, figs in SECTIONS for k, label in figs.items()}
# the few figures a table of speakers or books shows by default: vivid adjectives against dynamic verbs, and what surrounds them
HEADLINE = ("pos:ADJ", "pos:ADV", "pos:VERB", "pos:NOUN", "ratio:adj_verb", "verbs:dynamic")
CHOICES = ("", "headline", *(k for k, _, _ in SECTIONS))      # what a table can show: nothing, the headline figures, or one section


# ---------- tallies ----------
def empty():
    """A tally with nothing counted: the words, each part of speech, and the verb and noun supersense spans (category -> count)."""
    return {"words": 0, "pos": Counter(), "verbs": Counter(), "nouns": Counter()}


def add(a, b):
    """Two tallies summed (a new tally; neither is changed)."""
    return {"words": a["words"] + b["words"], "pos": a["pos"] + b["pos"], "verbs": a["verbs"] + b["verbs"], "nouns": a["nouns"] + b["nouns"]}


def tally(bd, tokens):
    """The tally of the given token positions of book `bd`, each counted once."""
    iw, ss = cindex(bd)["isword"], bd.ss
    t = empty()
    for i in tokens:
        if iw[i]:
            t["words"] += 1
            t["pos"][bd.pos[i]] += 1
        cat = ss.get(i)
        if cat and ss.get(i - 1) != cat:                                    # a span counts where it starts
            kind, _, name = cat.partition(".")
            if kind in ("verb", "noun"):
                t[kind + "s"][name] += 1
    return t


# ---------- figures ----------
def _pct(a, b):
    """a as a percentage of b, or None."""
    return 100 * a / b if b else None


def value(t, figure):
    """One figure of a tally (a name in `FIGURES`, see `is_figure`), None when there is nothing to take it of. Works out only that figure,
    so a table of speakers or sentences can ask for a few without taking all of them."""
    kind, _, name = figure.partition(":")
    words, pos = t["words"], t["pos"]
    if kind == "pos":
        return _pct(pos[name], words)
    if kind == "ratio":
        _, top, bottom = RATIOS[name]
        divisor = sum(pos[p] for p in bottom)
        return sum(pos[p] for p in top) / divisor if divisor else None
    if kind == "verbs":
        return _pct(sum(t["verbs"][c] for c in GROUPS[name]), sum(t["verbs"].values()))
    if kind in ("verb", "noun"):
        spans = t[kind + "s"]
        return _pct(spans[name], sum(spans.values()))
    which, _, category = name.partition(".")                                  # ss:verb.motion
    return 1000 * t[which + "s"][category] / words if words else None


def figures(t):
    """The figures of a tally: {name in FIGURES: value, or None when there is nothing to take it of}."""
    return {k: value(t, k) for k in FIGURES}


def choices():
    """What a table can show, for a select: [{id, title}] for each of `CHOICES`."""
    return [{"id": "", "title": "No word choice"}, {"id": "headline", "title": "Key figures"}, *({"id": k, "title": t} for k, t, _ in SECTIONS)]


def columns(choice):
    """The figures a table shows for a `choice` of `CHOICES`, as [{k, label}] in order; none for "" (a ValueError for anything else)."""
    if choice == "":
        return []
    if choice == "headline":
        return [{"k": k, "label": FIGURES[k]} for k in HEADLINE]
    for key, _, figures in SECTIONS:
        if key == choice:
            return [{"k": k, "label": label} for k, label in figures.items()]
    raise ValueError("Unknown word-choice figures: choose one of " + ", ".join(repr(c) for c in CHOICES) + ".")


def span_tally(bd, s, e):
    """The tally of tokens s..e of a book, worked out once per stretch and kept on the book, as `narrative.style_metrics` keeps its figures."""
    return bd.kept("wordchoice", entries=500).get((s, e), lambda: tally(bd, range(s, e + 1)))


def table(view, seg_cfg, by):
    """The figures per book, or per chapter or slice (`by="segment"`, cut by the Measure over setting `seg_cfg`) ->
    {rows: [{book, title, label, (index), words, figures…}], info (with segments), sections: [{id, title, figures: {name: label}}],
    choices: [{id, title}] (what a table can show, `choices`), columns: {choice id: [{k, label}]} (`columns` of each)}. A book or segment without words is left out."""
    from .narrative import all_segments
    rows, info = [], None
    if by == "segment":
        segs, info = all_segments(view, seg_cfg)
        spans = [(sg["book"], sg["start"], sg["end"], sg["title"], sg["label"], sg["index"]) for sg in segs]
    else:
        spans = [(b, 0, view.bd[b].n_tokens - 1, view.title(b), view.title(b), None) for b in view.books]
    for b, s, e, title, label_, index in spans:
        t = span_tally(view.bd[b], s, e)
        if t["words"]:
            rows.append({"book": b, "title": title, "label": label_, **({"index": index} if index is not None else {}), "words": t["words"], **figures(t)})
    return {"rows": rows, "info": info, "sections": [{"id": k, "title": t, "figures": f} for k, t, f in SECTIONS], "choices": choices(),
            "columns": {c["id"]: columns(c["id"]) for c in choices()}}


def is_figure(figure):
    """Whether `figure` names one of `FIGURES`."""
    return isinstance(figure, str) and figure in FIGURES


def label(figure):
    """A figure's name ("Adjectives per verb")."""
    return FIGURES[figure]
