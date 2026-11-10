"""Described as: what a target is described and called as, and by whom.

The target is anything `View.resolve` accepts (an entity, a group, a tag, a gender). A **finding** is one thing said about it, at one
of its mentions: a modifier ("desolate"), a name or description it is called by, an action, a possession… (`KINDS`). Every finding is
traced to a **describer**, from the mention's position in the text:

* inside a quote: the quote's speaker (a unit id, as in `dialogue.speaker_units`; `NO_DESCRIBER` for a quote nobody is attributed to);
* anywhere else: the narrator of that paragraph (`dialogue.narrator_of`, your corrections applied). A narrator who is a character is that
  character, so "Watson" is his speech and the narration he tells together; an unnamed narrator, or a linked narrator
  (`nl:<n>`), stays a role id.

The table (`table`) has one row per word (or form) and one column per group of describers, chosen by `split`: each describer (`entity`),
by gender, by tag, by book, or by voice (narration or speech). Each cell has the count, the share of that column's findings, the
rate per 1,000 words the column's describers produce, and the keyness of the word in that column against all other columns.
`findings` and `Describers` are the two halves of the join, kept apart so the sentences behind a cell can be found the same way.

A finding belongs to every describer who counts as its speaker (more than one only for a plural speaker, when plural groups count
for their members), and to a column once however many of its describers fall in it (a describer with two tags is in two columns).
"""
from __future__ import annotations

from collections import Counter, defaultdict

from . import stats
from .bookdata import one_of, parse_ekey
from .dialogue import all_recs, narration_recs, narrator_of, role_name, role_unit, speaker_units, unit_of
from .view import gender_label

KINDS = {"mod": "Modifiers", "name": "Called: names", "desc": "Called: descriptions", "pron": "Called: pronouns",
         "agent": "Actions", "patient": "Done to them", "poss": "Possessions", "prep": "Prepositions and settings"}
CALLED = {"name": "PROP", "desc": "NOM", "pron": "PRON"}       # what a mention is: a name, a description (noun phrase), a pronoun
SPLITS = {"entity": "Describer", "gender": "Gender of the describer", "tag": "Tag of the describer", "book": "Book",
          "voice": "Narration or speech", "custom": "Columns you pick"}
VOICES = ("both", "narration", "speech")
NO_DESCRIBER = "none"                  # the describer of a quote nobody is attributed to
NO_PERSON = "none"                     # the gender column of a describer that is no person (an unnamed narrator, an unattributed quote)
UNTAGGED = "_untagged"                 # the tag column of a describer without tags
REST = "_rest"                         # the column that gathers the columns beyond `top`
MAX_PICKED = 12                        # columns you can pick yourself
NOTES = {
    "describer": ("The describer of a finding is the speaker of the quote it is in. Outside quotes it is the narrator of the paragraph "
                  "(your narrator corrections apply); a narrator who is a character counts as that character, so their speech and "
                  "their narration are one column. A quote with no attributed speaker is its own describer."),
    "measures": ("Share: the word's part of all that column's findings of this kind. Per 1,000: the word's count per 1,000 words the column's "
                 "describers speak or narrate in the books the target appears in. Keyness: log-likelihood (G²) of the word in this column "
                 "against all the other columns together; + means more typical of this column. It ranks; it is not a significance test, "
                 "because the findings are not independent."),
}


class Describers:
    """Who says what is at a mention: `of(book, mention index)`. Builds the paragraph -> narrator lookup once, so make one per request."""

    def __init__(self, view):
        self.view = view
        self.role = {(b, r["para"]): r["role"] for b, r in narration_recs(view)}

    def of(self, b, mi):
        """(voice, describers) of the mention `mi` of book b: ("speech", the quote's speakers) inside a quote, else
        ("narration", the paragraph's narrator). Describers are unit ids, role ids (`role_describer`) or `NO_DESCRIBER`."""
        bd = self.view.bd[b]
        tok = bd.mentions[mi][1]
        qi = bd.quote_at.get(tok)
        if qi is not None:
            speakers = bd.stands_for(bd.quotes[qi]["char"])       # as a quote record's `speakers`
            return "speech", list(dict.fromkeys(unit_of(self.view, b, c) for c in speakers)) or [NO_DESCRIBER]
        pid = bd.para[tok]
        rid = self.role.get((b, pid)) or narrator_of(self.view, b, pid)[0]
        return "narration", [role_describer(rid)]


def role_describer(rid):
    """The describer a narrator role is: the character's unit id, or the role id when it has no one character (unnamed, linked)."""
    return role_unit(rid) or rid


def findings(view, members, kind):
    """Every finding of one kind for the members' groups: (book, mention index, word or form, tokens to highlight). A relation's words
    are the lemmas the profile shows; a name, description or pronoun is the mention's own text (pronouns in lower case). A mention credited to
    two of the members (a plural group and its member) is counted once (`View.overlap`)."""
    members = list(members)
    skip = view.overlap(members)
    for b, c in members:
        bd, g, drop = view.bd[b], view.bd[b].groups[c], skip.get(b, {}).get(c, ())
        if kind in CALLED:
            for mi in g.mentions:
                m = bd.mentions[mi]
                if m[3] == CALLED[kind] and mi not in drop:
                    yield b, mi, m[5].lower() if kind == "pron" else m[5], range(m[1], m[2] + 1)
        else:
            for key, mi, hl in g.rel_ev.get(kind, []):
                if mi not in drop:
                    yield b, mi, key, hl


def describer_name(view, d):
    """A describer's display name: a unit's name, a narrator role's ("Watson, narrating" for a role with no unit), or a note."""
    if d == NO_DESCRIBER:
        return "Unattributed quote"
    return role_name(view, d) if d.startswith(("nar:", "nl:")) else view.name_of(d)


def picks(view, specs):
    """The columns you picked, from their specs (anything `View.resolve` takes, with an optional `name`): [{id, label, members}], ids
    `c0`, `c1`… in the order given. Raises ValueError if there are none, too many, or one isn't a spec."""
    if not isinstance(specs, list) or not specs:
        raise ValueError("Pick at least one column.")
    if len(specs) > MAX_PICKED:
        raise ValueError(f"Pick at most {MAX_PICKED} columns.")
    out = []
    for i, spec in enumerate(specs):
        if not isinstance(spec, dict):
            raise ValueError("Each column should say which entities it stands for.")
        members, label, _ = view.resolve(spec)
        out.append({"id": f"c{i}", "label": spec.get("name") or label, "members": members})
    return out


def _is_in(view, members, d):
    """Whether describer `d` (a unit id, or the id of a single entity not counted as a unit) is one of the `members` ((book, coref) pairs)."""
    u, key = view.units.get(d), parse_ekey(d)
    return bool(u and members.intersection(u.members) or key and key in members)


def column_keys(view, split, d, voice, book, picked=None):
    """The columns a finding of describer `d` (said in `voice`, in `book`) is counted in, for a `split` (`picked`: the columns you
    chose, see `picks`). For your own columns that is every one the describer belongs to: none, one or several."""
    if split == "custom":
        return [c["id"] for c in picked if _is_in(view, c["members"], d)]
    if split == "entity":
        return [d]
    if split == "voice":
        return [voice]
    if split == "book":
        return [book]
    u = view.units.get(d)
    if split == "gender":
        return [view.gender_of(u) if u and u.type == "PER" else NO_PERSON]
    return list(u.tags) if u and u.tags else [UNTAGGED]


def column_label(view, split, key):
    """The heading of a column."""
    if key == REST:
        return "All others"
    if split == "entity":
        return describer_name(view, key)
    if split == "gender":
        return "Not a person (unnamed narrator, unattributed quote)" if key == NO_PERSON else gender_label(key)
    if split == "tag":
        return "(no tag)" if key == UNTAGGED else key
    if split == "book":
        return view.title(key)
    return {"narration": "Narration", "speech": "Speech"}[key]


def column_labels(view, split, ids, picked=None):
    """The headings of columns `ids`. Describers of the same name (one character's separate entity in each book, two speakers
    BookNLP only called "I") get the books they are in, so their columns can be told apart."""
    if split == "custom":
        return {c["id"]: c["label"] for c in picked}
    labels = {k: column_label(view, split, k) for k in ids}
    if split == "entity":
        same = Counter(labels.values())
        for k in ids:
            u, key = view.units.get(k), parse_ekey(k)
            books = u.books if u else {key[0]} if key else set()
            if same[labels[k]] > 1 and books:
                labels[k] += f" ({view.books_label(books)})"
    return labels


def _sources(view, books, voice):
    """The text each describer produces in the given books: (book, voice, describers, words) for every quote and every paragraph's
    narration, restricted to one voice if asked. The denominator of the per-1,000 rates."""
    if voice != "narration":
        for b, r in all_recs(view):
            if b in books:
                yield b, "speech", speaker_units(view, b, r) or [NO_DESCRIBER], r["n"]
    if voice != "speech":
        for b, r in narration_recs(view):
            if b in books:
                yield b, "narration", [role_describer(r["role"])], r["n"]


def check(kind, split, voice):
    """Raise ValueError for a kind, split or voice this module doesn't have."""
    if not (one_of(kind, KINDS) and one_of(split, SPLITS) and one_of(voice, VOICES)):
        raise ValueError(f"Unknown {'kind' if not one_of(kind, KINDS) else 'split' if not one_of(split, SPLITS) else 'voice'}.")


def _classify(view, mem, kind, split, voice, picked=None):
    """Every finding of one kind for the members that the voice allows, with who said it: [(book, mention index, word, tokens to
    highlight, voice, describers, columns)]. `columns` are the raw columns of the split the finding falls in (once each, however many
    of its describers are in one). The one place that decides what belongs where: `table` counts these and `evidence` lists them."""
    who, out = Describers(view), []
    for b, mi, key, hl in findings(view, mem, kind):
        v, ds = who.of(b, mi)
        if voice in ("both", v):
            out.append((b, mi, key, hl, v, ds, {k for d in ds for k in column_keys(view, split, d, v, b, picked)}))
    return out


def _layout(view, split, classified, top, picked=None):
    """Which columns are shown, in order, and the set of those gathered in "All others": the `top` columns with most findings (books in
    reading order). The columns you picked are all shown, as you ordered them, whether or not they have findings."""
    if split == "custom":
        return [c["id"] for c in picked], set()
    found = Counter(k for f in classified for k in f[6])
    ranked = sorted(found, key=lambda k: (-found[k], str(k)))
    keep, tail = ranked[:top], set(ranked[top:])
    if split == "book":
        keep.sort(key=view.books.index)
    return keep, tail


def _shown(columns, tail):
    """The columns a finding is counted in: its own, with those gathered in "All others" becoming that one column (once)."""
    return {REST if k in tail else k for k in columns}


def table(view, spec, kind="mod", split="entity", voice="both", top=8, limit=60, columns=None):
    """Who describes the target (`spec`, anything `View.resolve` takes) as what. `kind` is one of `KINDS`, `split` one of `SPLITS`,
    `voice` one of `VOICES`. At most `top` columns (the ones with most findings; the rest are gathered in "All others") and the `limit`
    most frequent words. -> {target, kind, split, voice, columns, all, rows, distinct, notes}; a column has `id`, `label`, `findings`,
    `narration` (how many of those were told by a narrator) and `words`; a row has `item`, `total`, `share` and `cells`, one per column
    ({n, share, per1k, ll, p}; `ll` is signed, + when the word is more typical of that column). Raises ValueError for an unknown option.
    With `split` "custom", `columns` are the specs of the columns you pick (`picks`): `top` doesn't apply, a describer can be in
    several, and findings in none are only in the All column (keyness compares the picked columns with each other)."""
    check(kind, split, voice)
    picked = picks(view, columns) if split == "custom" else None
    mem, label, _ = view.resolve(spec)
    books = {b for b, c in mem}
    classified = _classify(view, mem, kind, split, voice, picked)
    keep, tail = _layout(view, split, classified, top, picked)
    counts, found, narrated = defaultdict(Counter), Counter(), Counter()      # column -> word -> n; column -> findings; ... told by a narrator
    total = Counter()
    for b, mi, key, hl, v, ds, cols in classified:
        total[key] += 1
        for ck in _shown(cols, tail):
            counts[ck][key] += 1
            found[ck] += 1
            narrated[ck] += v == "narration"
    words, all_words = Counter(), 0
    for b, v, ds, n in _sources(view, books, voice):
        all_words += n
        for ck in _shown({k for d in ds for k in column_keys(view, split, d, v, b, picked)}, tail):
            words[ck] += n
    ids = keep + ([REST] if tail else [])
    labels = column_labels(view, split, ids, picked)
    n_found = len(classified)
    rows = []
    for item, n in sorted(total.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]:
        cells = []
        for k in ids:
            a, c = counts[k][item], found[k]
            rest_a, rest_c = sum(counts[o][item] for o in ids if o != k), sum(found[o] for o in ids if o != k)
            cmp = stats.compare(a, rest_a, c, rest_c)
            cells.append({"n": a, "share": 100 * a / c if c else 0, "per1k": 1000 * a / words[k] if words[k] else None,
                          "ll": cmp["ll"] if len(ids) > 1 else 0, "p": cmp["p_ll"] if len(ids) > 1 else 1})
        rows.append({"item": item, "total": n, "share": 100 * n / n_found, "per1k": 1000 * n / all_words if all_words else None, "cells": cells})
    return {"target": label, "kind": kind, "kind_label": KINDS[kind], "split": split, "voice": voice,
            "columns": [{"id": k, "label": labels[k], "findings": found[k], "narration": narrated[k], "words": words[k]} for k in ids],
            "all": {"findings": n_found, "narration": sum(f[4] == "narration" for f in classified), "words": all_words},
            "rows": rows, "distinct": len(total), "notes": NOTES}


def evidence(view, spec, item, column, kind="mod", split="entity", voice="both", top=8, limit=150, columns=None):
    """The sentences behind one cell of `table` (the same arguments, so the same columns): every finding of the word or form `item` in
    `column` (a column id, `REST` for "All others", or None for the All column). -> {total, shown, items: [{book, title, pos, tok, text,
    by}]} like `View.evidence` (text carries marks: m = the target's mention, k = the word), `by` saying who said it ("Watson (narration)").
    `total` is exactly the cell's count. Raises ValueError for an unknown option."""
    check(kind, split, voice)
    picked = picks(view, columns) if split == "custom" else None
    mem, _, _ = view.resolve(spec)
    classified = _classify(view, mem, kind, split, voice, picked)
    keep, tail = _layout(view, split, classified, top, picked)
    hits = [f for f in classified if f[2] == item and (column is None or column in _shown(f[6], tail))]
    order = {b: n for n, b in enumerate(view.books)}
    hits.sort(key=lambda f: (order[f[0]], view.bd[f[0]].mentions[f[1]][1], f[1]))
    items = []
    for b, mi, key, hl, v, ds, cols in hits[:limit]:
        bd = view.bd[b]
        m = bd.mentions[mi]
        marks = [(m[1], m[2], "m")] + ([(t, t, "k") for t in hl] if kind not in CALLED else [])
        s, e = bd.sentence_of(m[1])
        by = ", ".join(describer_name(view, d) for d in ds)
        items.append({"book": b, "title": view.title(b), "pos": round(100 * m[1] / max(1, bd.n_tokens), 1), "tok": m[1],
                      "text": bd.span_text(s, e, marks), "by": f"{by} ({v})"})
    return {"total": len(hits), "shown": len(items), "items": items}
