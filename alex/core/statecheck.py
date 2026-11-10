"""Checking a workspace's own files as they are read: `library.json` (`clean_state`) and `annotations.json` (`clean_annotations`).

aLex writes both files itself, but they can also come from elsewhere: an export zip made by another version of aLex or by someone
else (`workspaces.import_zip`), or a file edited by hand. A part with the wrong shape (a group whose members are a number, a chapter
edit that is text) would otherwise break every page that reads it, long after the file was opened. So each part is checked against the
shape aLex writes, entry by entry:

* an entry with the wrong shape is left out (a person whose members can't be read, a book's details that aren't an object…), and what
  can be kept of a damaged entry is kept (a person's readable members, a book's readable details);
* a whole part with the wrong shape (persons that are a list) starts empty, as in a new workspace;
* the rules aLex keeps while you work are restored: an entity belongs to one linked person at most and a narrator role to one narrator
  link at most (the first, by number, keeps it), a person needs a member and a narrator link two, and each `next_…` number is above
  every number in use, so a new group never overwrites an old one;
* settings are laid over the defaults (`merge_settings`); parts and settings aLex doesn't know are kept as they are.

Each function returns the checked data and `notes`: one sentence per kind of thing that was left out, which the Library page shows
(`Library.state_notes`). Nothing is written back: the file changes only when you next change something.
"""
from __future__ import annotations

WHOLE = lambda v, low=0: isinstance(v, int) and not isinstance(v, bool) and v >= low       # a whole number, at least `low`
TEXT = lambda v: isinstance(v, str)
TEXTS = lambda v: isinstance(v, list) and all(isinstance(x, str) for x in v)                # a list of texts
MAYBE_TEXT = lambda v: v is None or isinstance(v, str)
COUNTERS = {"next_person": "persons", "next_collection": "collections", "next_group": "groups", "next_narrator_link": "narrator_links",
            "next_stat_set": "stat_sets"}      # each `next_…` number and the part whose ids it hands out


def merge_settings(defaults: dict, saved) -> dict:
    """The settings of a library.json (`saved`) laid over the `defaults` (`default_state`'s): a saved value is kept only if it has the
    shape aLex writes, so a hand-edited or damaged value (a number for a list, text for a number) falls back to the default instead of
    breaking every page that reads it. Settings aLex doesn't know are kept as they are. (The sound settings are checked in detail where
    they are read, `prosody.config`.)"""
    out = {**defaults}
    saved = saved if isinstance(saved, dict) else {}
    checks = {
        "count_mode": lambda v: v in ("per_book", "combined"),
        "freq_mode": lambda v: v in ("per_book", "combined"),
        "conv_gap": WHOLE,
        "plural": lambda v: isinstance(v, bool),
        "speech_skip": lambda v: isinstance(v, dict) and all(TEXTS(v.get(k, [])) for k in ("verbs", "adverbs")),
        "sound": lambda v: isinstance(v, dict),
    }
    for key, value in saved.items():
        if key == "min":
            given = value if isinstance(value, dict) else {}
            out["min"] = {**defaults["min"], **{t: n for t, n in given.items() if WHOLE(n, 1)}}
        elif key not in checks or checks[key](value):
            out[key] = value
    return out


class _Notes:
    """What was left out, counted by kind, as sentences for the Library page."""

    def __init__(self, file):
        """Notes about one file (its name, as the sentences say it)."""
        self.file, self.counts, self.parts = file, {}, []

    def whole(self, part):
        """A whole part (“persons”) couldn't be read and starts empty."""
        self.parts.append(part)

    def drop(self, what, n=1):
        """`n` more of `what` ("linked persons") were left out."""
        if n:
            self.counts[what] = self.counts.get(what, 0) + n

    def sentences(self):
        """One sentence per kind of thing left out."""
        return ([f"“{part}” in {self.file} couldn't be read and starts empty." for part in self.parts]
                + [f"{n} {what} in {self.file} couldn't be read and {'was' if n == 1 else 'were'} left out." for what, n in self.counts.items()])


def _entries(value, what, notes, check):
    """The entries of an object part ({id: entry}) that `check(entry)` keeps; `check` returns the entry to keep (possibly mended) or
    None. A part that isn't an object is counted as one thing left out and starts empty."""
    if not isinstance(value, dict):
        notes.whole(what)
        return {}
    out = {}
    for key, entry in value.items():
        kept = check(entry)
        if kept is None:
            notes.drop(what)
        else:
            out[str(key)] = kept
    return out


def _items(value, what, notes, check):
    """The items of a list part that `check(item)` accepts (as `_entries`, for lists)."""
    if not isinstance(value, list):
        notes.whole(what)
        return []
    out = [x for x in value if check(x)]
    notes.drop(what, len(value) - len(out))
    return out


# ---------- library.json ----------
def _book(m):
    """A book's details, keeping the readable ones (title, author, series and pinned as text, year as text or a number, tags as texts)."""
    if not isinstance(m, dict):
        return None
    ok = {"title": TEXT, "author": TEXT, "series": TEXT, "pinned": MAYBE_TEXT, "tags": TEXTS,
          "year": lambda v: isinstance(v, (str, int)) and not isinstance(v, bool)}
    return {k: v for k, v in m.items() if k not in ok or ok[k](v)}


def _member(m):
    """Whether `m` is a person's member: [book id, coreference number]."""
    return isinstance(m, list) and len(m) == 2 and TEXT(m[0]) and WHOLE(m[1])


def _persons(value, notes):
    """The linked persons: each with readable members, an entity in one person only (the first by number keeps it), tags as texts,
    a name and a note as text; a person left without members is left out."""
    if not isinstance(value, dict):
        notes.whole("persons")
        return {}
    taken, out = set(), {}
    for pid in sorted(value, key=_number):
        p = value[pid]
        members = [m for m in p.get("members", []) if _member(m) and tuple(m) not in taken] if isinstance(p, dict) and isinstance(p.get("members"), list) else []
        if not members:
            notes.drop("linked persons")
            continue
        taken.update(tuple(m) for m in members)
        person = {**p, "members": members, "tags": p.get("tags", []) if TEXTS(p.get("tags", [])) else []}
        for k in ("name", "note"):
            if not MAYBE_TEXT(person.get(k)):
                person.pop(k)
        out[str(pid)] = person
    return out


def _narrator_links(value, notes):
    """The narrator links: each with at least two roles (texts), a role in one link only (the first by number keeps it), a name as text."""
    if not isinstance(value, dict):
        notes.whole("narrator links")
        return {}
    taken, out = set(), {}
    for lid in sorted(value, key=_number):
        link = value[lid]
        members = list(dict.fromkeys(m for m in link.get("members", []) if TEXT(m) and m not in taken)) \
            if isinstance(link, dict) and isinstance(link.get("members"), list) else []
        if len(members) < 2:
            notes.drop("narrator links")
            continue
        taken.update(members)
        out[str(lid)] = {**link, "members": members, "name": link.get("name") if MAYBE_TEXT(link.get("name")) else None}
    return out


def _number(key):
    """A part's id as a number, for ordering ("10" after "9"); ids that aren't numbers come last, in their own order."""
    return (0, int(key), "") if str(key).isdigit() else (1, 0, str(key))


def clean_state(saved: dict, defaults: dict) -> tuple[dict, list[str]]:
    """A library.json's contents (`saved`, an object) checked part by part over `defaults` (`library.default_state()`) -> (state, notes).
    See the module notes."""
    notes = _Notes("library.json")
    out = {**defaults, **{k: v for k, v in saved.items() if k not in defaults}}            # parts aLex doesn't know stay as they are
    get = lambda key: saved.get(key, defaults[key])
    out["sources"] = _items(get("sources"), "source folders", notes, TEXT)
    out["books"] = _entries(get("books"), "books' details", notes, _book)
    out["settings"] = merge_settings(defaults["settings"], saved.get("settings"))
    out["persons"] = _persons(get("persons"), notes)
    out["entity_tags"] = _entries(get("entity_tags"), "entities' tags", notes, lambda v: v if TEXTS(v) else None)
    out["entity_names"] = _entries(get("entity_names"), "entities' names", notes, lambda v: v if TEXT(v) else None)
    out["entity_notes"] = _entries(get("entity_notes"), "entities' notes", notes, lambda v: v if TEXT(v) else None)
    out["rejected"] = _items(get("rejected"), "rejected link suggestions", notes, lambda v: TEXTS(v) and len(v) == 2)
    out["collections"] = _entries(get("collections"), "collections", notes, lambda c: c if isinstance(c, dict) and TEXT(c.get("name"))
                                  and MAYBE_TEXT(c.get("parent")) and TEXTS(c.get("books", [])) else None)
    out["groups"] = _entries(get("groups"), "saved groups", notes, lambda g: g if isinstance(g, dict) and TEXT(g.get("name")) and TEXTS(g.get("ids")) else None)
    out["plurals"] = _entries(get("plurals"), "plural groups", notes, lambda v: v if TEXTS(v) else None)
    out["plural_rejected"] = _items(get("plural_rejected"), "rejected plural suggestions", notes, TEXT)
    out["narrator_links"] = _narrator_links(get("narrator_links"), notes)
    out["stat_sets"] = _entries(get("stat_sets"), "saved Statistics sets", notes,
                                lambda x: x if isinstance(x, dict) and TEXT(x.get("name")) and isinstance(x.get("setup"), dict) else None)
    for counter, part in COUNTERS.items():           # above every id in use, whatever the file said
        used = [int(k) for k in out[part] if str(k).isdigit()]
        given = saved.get(counter)
        out[counter] = max([given if WHOLE(given, 1) else 1, *(n + 1 for n in used)])
    return out, notes.sentences()


# ---------- annotations.json ----------
BOOK_ANN = {"narrator": None, "para_narrators": {}, "addressees": {}, "splits": [], "merges": [], "participants": {}}     # `Library.ann_book`'s


def _book_ann(ab, notes):
    """One book's corrections, each part checked (see the module notes); None if they aren't an object at all."""
    if not isinstance(ab, dict):
        return None
    out = {**ab}
    if not MAYBE_TEXT(ab.get("narrator")):
        out["narrator"] = None
        notes.drop("books' narrators")
    for part, what in (("para_narrators", "paragraph narrators"), ("chapter_narrators", "chapter narrators")):
        if part in ab:
            out[part] = _entries(ab[part], what, notes, lambda v: v if TEXT(v) else None)
    if "addressees" in ab:
        out["addressees"] = _entries(ab["addressees"], "quotes' addressees", notes, lambda v: v if TEXTS(v) else None)
    for part, what in (("splits", "conversation splits"), ("merges", "conversation merges")):
        if part in ab:
            out[part] = _items(ab[part], what, notes, TEXT)
    if "participants" in ab:
        out["participants"] = _entries(ab["participants"], "conversation participants", notes,
                                       lambda e: e if isinstance(e, dict) and all(TEXTS(e.get(k, [])) for k in ("add", "remove")) else None)
    if "chapters" in ab:
        ch = ab["chapters"]
        if isinstance(ch, dict) and TEXTS(ch.get("add", [])) and TEXTS(ch.get("remove", [])) and isinstance(ch.get("names", {}), dict) \
                and all(TEXT(v) for v in ch.get("names", {}).values()):
            out["chapters"] = {"add": ch.get("add", []), "remove": ch.get("remove", []), "names": ch.get("names", {}), **{k: v for k, v in ch.items() if k not in ("add", "remove", "names")}}
        else:
            del out["chapters"]
            notes.drop("books' chapter edits")
    return out


def clean_annotations(saved: dict) -> tuple[dict, list[str]]:
    """An annotations.json's contents (`saved`, an object) checked book by book -> (annotations, notes). See the module notes."""
    notes = _Notes("annotations.json")
    out = {**saved}
    out["books"] = _entries(saved.get("books", {}), "books' corrections", notes, lambda ab: _book_ann(ab, notes))
    return out, notes.sentences()
