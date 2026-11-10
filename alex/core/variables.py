"""The variables of the Statistics tab: what is measured in each case (`core/cases.py`).

A variable is a dict (a *spec*) with a `kind`:

* **query**: hits of a Corpus query (`query`, `mode` simple or pattern, `match` word or lemma, `case`, `regex`, `wildcards`), counted in
  the case whose sample holds the hit's first token. In the Described-as findings sample a query is one word (or several, one per line,
  or `a|b`), matched against each finding's word, optionally only findings of one kind (`finding`: a key of `described.KINDS`).
* **mentions**: mentions of anything `View.resolve` takes (`target`), optionally only names, descriptions or pronouns (`prop`: PROP, NOM,
  PRON), counted where the mention starts. A participant's mentions of themselves count like any other.
* **spoken**: speech of anything `View.resolve` takes (`target`): the words they speak (`unit` "words", each word counted where it is) or
  their quotes (`unit` "quotes", each counted where its first word is), optionally only quotes of one sentence type (`type`, see
  `dialogue.sentence_type`; `weigh` lets the speech verb decide too). A quote the target says through several of its members counts once.
* **attribute**: a figure of the case itself (`attr`). Participants: `in` (1 when the participant is one of `target`'s entities, else 0:
  a gender, a tag, a saved group…), `mentions`, `speech` (words they speak), `quotes`, `books`. Pieces: `index` (number in its book),
  `position` (% into the book), `length` (words in its sample). Participants' figures are counted in the cases' books (`Cases.books`).

* the linguistic **layers** (`supersense`, `relation`, `sentiment`, `lexicon`, `speech`, `style`, `wordchoice`, `sound`, `topic`) are checked and measured by `core/layers.py`.

A count becomes a value by its `measure` (`MEASURES`): per 1,000 words of the case's sample (for findings: % of the case's findings), the
raw count, or present (1 when the count is above 0). Attributes are their own values. A variable that doesn't apply to the cases (a
piece attribute for participants, mentions or speech among findings) gets no values (None) and a `note` saying why, rather than an error, so a
saved set still runs when the cases change. `table` measures a list of variables; `top_words`, `top_entities`, `top_speakers` and
`attribute_values` make lists of specs for the page's bulk-add buttons.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from . import described, entitygroups, layers
from .bookdata import one_of
from .dialogue import all_recs, said_by, speaker_units
from .corpus import Matcher, QueryError, cindex, items_of, parse_simple, stream_of, token_test, value_matcher
from .view import TYPES, gender_label

KINDS = {"query": "Words or phrases", "mentions": "Mentions", "spoken": "Speech", "attribute": "Attribute", **layers.KINDS}
MEASURES = {"per1k": "per 1,000 words", "count": "count", "present": "present (0/1)", "pct": "% of quotes"}
SPOKEN_UNITS = {"words": "Words spoken", "quotes": "Quotes"}
PROPS = {"": "All mentions", "PROP": "Names", "NOM": "Descriptions", "PRON": "Pronouns"}
PARTICIPANT_ATTRS = {"in": "Is one of", "mentions": "Mentions", "speech": "Words spoken", "quotes": "Quotes", "books": "Books"}
PIECE_ATTRS = {"index": "Number in its book", "position": "Position in its book (%)", "length": "Length (words)"}
MAX_VARIABLES = 60                                   # variables in one request (two lists of 30)
MAX_QUERY = 2000                                     # characters in one query
NO_LIMIT = 10 ** 9                                   # a variable counts every hit, not the Corpus page's first 20,000


class _NotHere(ValueError):
    """A variable that doesn't apply to these cases; its message becomes the variable's note."""


def check(spec):
    """A variable spec, checked and with its defaults filled in. Raises ValueError (saying what is wrong) for one it can't use."""
    if not isinstance(spec, dict):
        raise ValueError("Each variable should be a description of what to count.")
    kind = spec.get("kind")
    if not one_of(kind, KINDS):
        raise ValueError("Unknown kind of variable.")
    out = {"kind": kind, "name": str(spec.get("name") or "").strip()[:120]}
    if kind in ("query", "mentions", "spoken") or kind in layers.COUNTED:
        out["measure"] = spec.get("measure", "per1k")
        if not one_of(out["measure"], MEASURES):
            raise ValueError("Unknown measure: choose per 1,000 words, count, or present.")
        if out["measure"] == "pct" and kind != "speech" and not (kind == "spoken" and spec.get("unit") == "quotes"):
            raise ValueError("“% of quotes” is a measure of quotes only: a speech sentence type, or the quotes of a speaker.")
    if kind == "query":
        q = spec.get("query")
        if not isinstance(q, str) or not q.strip() or len(q) > MAX_QUERY:
            raise ValueError(f"Type a query (at most {MAX_QUERY} characters).")
        out.update(query=q.strip(), mode=spec.get("mode", "simple"), match=spec.get("match", "word"), finding=spec.get("finding") or "",
                   case=bool(spec.get("case")), regex=bool(spec.get("regex")), wildcards=spec.get("wildcards", True) is not False)
        if out["mode"] not in ("simple", "pattern") or out["match"] not in ("word", "lemma") or out["finding"] not in ("", *described.KINDS):
            raise ValueError("Unknown query option.")
    elif kind in layers.KINDS:
        layers.check(spec, out)
    elif kind == "mentions":
        out.update(target=_spec(spec.get("target")), prop=spec.get("prop") or "")
        if not one_of(out["prop"], PROPS):
            raise ValueError("Unknown kind of mention: choose names, descriptions or pronouns.")
    elif kind == "spoken":
        out.update(target=_spec(spec.get("target")), unit=spec.get("unit", "words"), type=spec.get("type") or "", weigh=bool(spec.get("weigh")))
        if not one_of(out["unit"], SPOKEN_UNITS):
            raise ValueError("Count words spoken or quotes.")
        if not (out["type"] == "" or one_of(out["type"], layers.SPEECH_TYPES)):
            raise ValueError("Unknown sentence type: choose questions, exclamations or statements.")
    else:
        out["attr"] = spec.get("attr")
        if not (one_of(out["attr"], PARTICIPANT_ATTRS) or one_of(out["attr"], PIECE_ATTRS)):
            raise ValueError("Unknown attribute.")
        if out["attr"] == "in":
            out["target"] = _spec(spec.get("target"))
    return out


def _spec(target):
    """An entity spec (anything `View.resolve` takes), or a ValueError."""
    if not isinstance(target, dict) or not target.get("kind"):
        raise ValueError("Say which entities: an entity, a group, a tag, a gender or a type.")
    return target


def label(view, spec, lexicons=None):
    """A variable's heading: its name if you gave one, else what it counts ("crime" (lemma), Mentions of Holmes: names, Gender: she/her)."""
    if spec["name"]:
        return spec["name"]
    if spec["kind"] in layers.KINDS:
        return layers.label(view, spec, lexicons)
    if spec["kind"] == "query":
        q = " | ".join(ln.strip() for ln in spec["query"].split("\n") if ln.strip())
        extra = [x for x in ("lemma" if spec["match"] == "lemma" and spec["mode"] == "simple" else "",
                             described.KINDS.get(spec["finding"], "").lower()) if x]
        return f"“{q}”" + (f" ({', '.join(extra)})" if extra else "")
    if spec["kind"] == "mentions":
        return f"Mentions of {who(view, spec['target'])}" + (f": {PROPS[spec['prop']].lower()}" if spec["prop"] else "")
    if spec["kind"] == "spoken":
        return spoken_label(who(view, spec["target"]), spec)
    if spec["attr"] == "in":
        t = spec["target"]
        if t.get("kind") == "gender":
            return f"Gender: {gender_label(t.get('pron'))}"
        return f"Is {who(view, t)}"
    return PARTICIPANT_ATTRS.get(spec["attr"]) or PIECE_ATTRS[spec["attr"]]


def spoken_label(name, spec):
    """The heading of a speech variable, given the target's name: "Speech of Holmes", "Speech of Holmes: quotes, questions (speech verb weighed)"."""
    extra = ["quotes"] if spec["unit"] == "quotes" else []
    if spec["type"]:
        extra.append(layers.SPEECH_TYPES[spec["type"]].lower() + (" (speech verb weighed)" if spec["weigh"] else ""))
    return f"Speech of {name}" + (f": {', '.join(extra)}" if extra else "")


def who(view, target):
    """The name of a target in a heading: `View.resolve`'s label, with the books added for an entity whose name another entity of the
    selection shares (Holmes in each of three books, not linked), so their variables can be told apart."""
    name = view.resolve(target)[1]
    u = view.units.get(target.get("id")) if target.get("kind") == "unit" else None
    if u and sum(1 for x in view.units.values() if x.name == u.name) > 1:
        name += f" ({view.books_label(u.books)})"
    return name


# ---------- counting ----------
def _query_counts(view, cases, spec):
    """How many hits of a query each case's sample holds."""
    settings = {"match": spec["match"], "case": spec["case"], "regex": spec["regex"], "wildcards": spec["wildcards"]}
    if cases.unit == "findings":
        return _finding_counts(cases, spec, settings)
    m = Matcher(view, spec["query"], spec["mode"], settings)
    out = [0] * len(cases.rows)
    for b in cases.books:
        at, stream = cases.at(b), stream_of(view, b, settings)
        for j, e, ln in m.hits(b, stream, NO_LIMIT, accept=lambda j, e: bool(at(stream[j]))):
            for i in at(stream[j]):
                out[i] += 1
    return out


def _finding_counts(cases, spec, settings):
    """How many of each participant's findings have a word the query matches (one word per line), of the chosen kind."""
    if spec["mode"] != "simple":
        raise _NotHere("A pattern can't be matched against findings, which are single words: use a simple query.")
    tests = []
    for ln in (x.strip() for x in spec["query"].split("\n")):
        if not ln:
            continue
        items = parse_simple(ln, settings)
        if len(items) != 1 or not items[0][0]:
            raise _NotHere("Findings are single words: write one word per line (wildcards and | work).")
        tests.append(value_matcher(items[0][0][0][2], settings["regex"], settings["case"], settings["wildcards"]))
    return [sum(1 for k, key, b, mi in fs if (not spec["finding"] or k == spec["finding"]) and any(t(key) for t in tests))
            for fs in cases.findings]


def _mention_counts(view, cases, spec):
    """How many mentions of the target (of the chosen kind) start in each case's sample."""
    if cases.unit == "findings":
        raise _NotHere("Mentions can't be counted among findings, which are words said about a participant.")
    out = [0] * len(cases.rows)
    members = view.resolve(spec["target"])[0]
    skip = view.overlap(members)                                   # a mention credited to two of the target's groups counts once
    for b, c in members:
        if b not in cases.books:
            continue
        bd, at, drop = view.bd[b], cases.at(b), skip.get(b, {}).get(c, ())
        for mi in bd.groups[c].mentions:
            m = bd.mentions[mi]
            if mi not in drop and (not spec["prop"] or m[3] == spec["prop"]):
                for i in at(m[1]):
                    out[i] += 1
    return out


def _spoken_counts(view, cases, spec):
    """How many words the target speaks (or how many of its quotes start) in each case's sample, of the chosen sentence type if any."""
    if cases.unit == "findings":
        raise _NotHere("Speech can't be counted among findings, which are words said about a participant.")
    out = [0] * len(cases.rows)
    members = view.resolve(spec["target"])[0]
    for b, r in layers.typed_quotes(view, cases, {spec["type"]} if spec["type"] else None, spec["weigh"]):
        if not said_by(members, b, r):
            continue
        at = cases.at(b)
        for t in (r["tokens"] if spec["unit"] == "words" else r["tokens"][:1]):
            for i in at(t):
                out[i] += 1
    return out


def _attribute(view, cases, spec):
    """The values of an attribute, one per case (None where it doesn't apply, e.g. a narrator role's gender)."""
    attr = spec["attr"]
    if cases.kind == "pieces":
        if attr not in PIECE_ATTRS:
            raise _NotHere("This is an attribute of participants, not of text pieces.")
        if attr == "length":
            return [r["size"] for r in cases.rows]
        key = {"index": lambda r: r["index"] + 1, "position": lambda r: r["pos"]}[attr]
        return [None if r["index"] is None else key(r) for r in cases.rows]
    if attr not in PARTICIPANT_ATTRS:
        raise _NotHere("This is an attribute of text pieces, not of participants.")
    units = [view.units.get(r["id"]) for r in cases.rows]
    if attr == "books":
        return [len(r["books"]) for r in cases.rows]
    if attr == "mentions":
        inside = set(cases.books)
        return [None if u is None else sum(len(view.bd[b].groups[c].mentions) for b, c in u.members if b in inside) for u in units]
    if attr == "in":
        members = view.resolve(spec["target"])[0]
        return [None if u is None else int(bool(members.intersection(u.members))) for u in units]
    words, quotes = _speech_totals(view, set(cases.books))
    return [None if u is None else (words if attr == "speech" else quotes)[u.id] for u in units]


def _speech_totals(view, inside):
    """(words spoken, quotes) per unit id in the books of `inside`, whatever the cases' sample."""
    words, quotes = Counter(), Counter()
    for b, r in all_recs(view):
        if b not in inside:
            continue
        for u in speaker_units(view, b, r):
            words[u] += r["n"]
            quotes[u] += 1
    return words, quotes


def values(view, cases, spec, lexicons=None):
    """(values, note) of one checked variable over the cases: a number per case, or None where it has none (all None, with a note
    saying why, when the variable doesn't apply to these cases; a topic model that covers only some cases' books gives those None and
    a note too). `lexicons` are your word lexicons by id (for lexicon variables).
    Raises ValueError for a query that can't be read."""
    kind = spec["kind"]
    try:
        if kind == "attribute":
            return _attribute(view, cases, spec), None
        if kind in layers.KINDS and kind not in layers.COUNTED:
            return layers.values(view, cases, spec)
        counts = (_query_counts(view, cases, spec) if kind == "query" else _mention_counts(view, cases, spec) if kind == "mentions"
                  else _spoken_counts(view, cases, spec) if kind == "spoken" else layers.counts(view, cases, spec, lexicons))
    except (_NotHere, layers.NotHere) as e:
        return [None] * len(cases.rows), str(e)
    except QueryError as e:
        raise ValueError(f"{label(view, spec)}: {e}") from None
    if spec["measure"] == "count":
        return counts, None
    if spec["measure"] == "present":
        return [int(n > 0) for n in counts], None
    if spec["measure"] == "pct":
        try:
            quotes = layers.quote_counts(view, cases)
        except layers.NotHere as e:
            return [None] * len(cases.rows), str(e)
        return [100 * n / q if q else None for n, q in zip(counts, quotes)], None
    per = 100 if cases.unit == "findings" else 1000
    return [per * n / r["size"] for n, r in zip(counts, cases.rows)], None


def measure_label(cases, spec):
    """What a variable's numbers are, for its heading: "per 1,000 words", "% of findings", "count", "present (0/1)", or "" for one that
    isn't a count (an attribute, sentiment, a style figure)."""
    if spec["kind"] == "topic":
        return "% of words"
    if "measure" not in spec:
        return ""
    if spec["measure"] == "per1k" and cases.unit == "findings":
        return "% of findings"
    return MEASURES[spec["measure"]]


def table(view, cases, specs, lexicons=None):
    """The data of the Statistics tab: every variable measured in every case. `specs` are checked here (at most `MAX_VARIABLES`);
    `lexicons` are your word lexicons by id.
    -> {variables: [{id ("v0"…), label, measure, kind, note, spec}], values: [one list per variable, a value per case]}."""
    if not isinstance(specs, list) or not specs:
        raise ValueError("Add at least one variable.")
    if len(specs) > MAX_VARIABLES:
        raise ValueError(f"Use at most {MAX_VARIABLES} variables.")
    checked = [check(s) for s in specs]
    out = {"variables": [], "values": []}
    for k, spec in enumerate(checked):
        vals, note = values(view, cases, spec, lexicons)
        out["variables"].append({"id": f"v{k}", "label": label(view, spec, lexicons), "measure": measure_label(cases, spec),
                                 "kind": spec["kind"], "note": note, "spec": spec})
        out["values"].append(vals)
    return out


# ---------- lists of variables (the bulk-add buttons) ----------
def top_words(view, cases, n=20, unit="word", flt=None, measure="per1k", min_range=1, types=None, weigh=False, speech_verbs=False):
    """Query variables for the `n` most frequent words (or lemmas) in the cases' samples, optionally only those passing a word-type
    filter (`corpus.token_test`) and only those found in at least `min_range` of the cases' books. In the findings sample: the most frequent finding
    words. Wildcards are off in them, so a word is itself.
    `types` (sentence types, see `dialogue.sentence_type`; `weigh` lets the speech verb decide too) takes only words inside quotes of those
    types. With `speech_verbs` the words are instead the verbs that introduce quotes (Dialogue → Speech verbs, your leave-out list
    applied), as lemmas whatever `unit` says, ranked by the quotes of the cases' samples each introduces (of those `types`); the word-type
    filter then tests the verb. The variables themselves count every occurrence of the word in the sample, not only as a speech verb."""
    if unit not in ("word", "lemma"):
        raise ValueError("Count words or lemmas.")
    if not isinstance(types, (list, tuple, type(None))) or not all(one_of(t, layers.SPEECH_TYPES) for t in types or ()):
        raise ValueError("Unknown sentence type: choose questions, exclamations or statements.")
    if cases.unit == "findings" and (types or speech_verbs):
        raise ValueError("Sentence types and speech verbs need running text; the Described-as sample is a list of findings.")
    if speech_verbs:
        unit = "lemma"
        freq, books_of = _speech_verbs(view, cases, flt, types, weigh)
    elif cases.unit == "findings":
        freq, books_of = _finding_words(cases)
    else:
        freq, books_of = _words(view, cases, unit, flt, types, weigh)
    kept = [(w, c) for w, c in freq.items() if len(books_of[w]) >= min_range]
    return [{"kind": "query", "query": w, "mode": "simple", "match": unit, "wildcards": False, "measure": measure}
            for w, _ in sorted(kept, key=lambda kv: (-kv[1], kv[0]))[:max(1, min(int(n), MAX_VARIABLES))]]


def _finding_words(cases):
    """(count of each finding word, the books it is in) over the participants' findings."""
    freq, books_of = Counter(), defaultdict(set)
    for fs in cases.findings:
        for k, key, b, mi in fs:
            freq[key] += 1
            books_of[key].add(b)
    return freq, books_of


def _words(view, cases, unit, flt, types, weigh):
    """(count of each word or lemma, the books it is in) over the words of the cases' samples that pass the word-type filter and, with
    `types`, lie inside a quote of one of those sentence types."""
    freq, books_of = Counter(), defaultdict(set)
    inside = defaultdict(set)                                           # book -> tokens of the quotes of the chosen types
    for b, r in (layers.typed_quotes(view, cases, types, weigh) if types else ()):
        inside[b].update(r["tokens"])
    for b in cases.books:
        bd, at = view.bd[b], cases.at(b)
        item, ok, iw = items_of(bd, unit), token_test(bd, flt), cindex(bd)["isword"]
        for i in range(bd.n_tokens):
            if iw[i] and at(i) and (ok is None or ok(i)) and (not types or i in inside[b]):
                freq[item(i)] += 1
                books_of[item(i)].add(b)
    return freq, books_of


def _speech_verbs(view, cases, flt, types, weigh):
    """(quotes each speech verb introduces, the books it is in) over the quotes of the cases' samples, of the given sentence types, whose
    verb passes the word-type filter."""
    freq, books_of = Counter(), defaultdict(set)
    for b, r in layers.typed_quotes(view, cases, types, weigh):
        ok = token_test(view.bd[b], flt)
        if r["verb"] and cases.at(b)(r["tokens"][0]) and (ok is None or ok(r["verb_tok"])):
            freq[r["verb"]] += 1
            books_of[r["verb"]].add(b)
    return freq, books_of


def top_entities(view, n=10, typ="PER", measure="per1k"):
    """Mention variables for the `n` most mentioned entities of a type (all types with "ALL"), their targets named as the pickers name them."""
    if typ != "ALL" and typ not in TYPES:
        raise ValueError("Unknown entity type.")
    units = sorted((u for u in view.units.values() if typ in ("ALL", u.type)), key=lambda u: (-u.mentions, u.name))
    return [{"kind": "mentions", "target": {"kind": "unit", "id": u.id, "name": u.name, "type": u.type}, "measure": measure}
            for u in units[:max(1, min(int(n), MAX_VARIABLES))]]


def top_speakers(view, n=10, typ="PER", measure="per1k"):
    """Speech variables (words spoken) for the `n` entities of a type (all types with "ALL") who speak the most words in the selected
    books, their targets named as the pickers name them. Entities who never speak are left out."""
    if typ != "ALL" and typ not in TYPES:
        raise ValueError("Unknown entity type.")
    words = _speech_totals(view, set(view.books))[0]
    units = sorted((u for u in view.units.values() if typ in ("ALL", u.type) and words[u.id]), key=lambda u: (-words[u.id], u.name))
    return [{"kind": "spoken", "target": {"kind": "unit", "id": u.id, "name": u.name, "type": u.type}, "unit": "words", "measure": measure}
            for u in units[:max(1, min(int(n), MAX_VARIABLES))]]


def attribute_values(view, attr):
    """One "is one of" (0/1) variable per value of a participant attribute: every gender (`attr` "gender"), every tag ("tag") or every
    saved group ("group") in the selection."""
    if attr == "gender":
        targets = [{"kind": "gender", "pron": g["pron"], "name": gender_label(g["pron"])} for g in view.genders()]
    elif attr == "tag":
        targets = [{"kind": "tag", "tag": t} for t in sorted({t for u in view.units.values() for t in u.tags}, key=str.lower)]
    elif attr == "group":
        targets = [{"kind": "group", "group": g["id"], "name": g["name"]} for g in entitygroups.listing(view.lib)]
    else:
        raise ValueError("Choose gender, tag or group.")
    return [{"kind": "attribute", "attr": "in", "target": t} for t in targets]
