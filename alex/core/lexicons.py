"""Your word lexicons: lists of words in categories, one file each in the lexicon folder of the data folder. They are imported from the text of
a plain, .csv or .tsv file (`parse`: a word list, a word and a category per row, or a column per category).

A lexicon is `<folder>/<id>.json` = `{"name", "cats": {category: [words]}}`, words lowercase and sorted. The id is made from the name when
the lexicon is created (`new_id`) and never changes, so a saved Statistics set that names a lexicon keeps working when it is renamed.
The **emotion lexicon** (id `emotion`, `EMOTION`) is the one special case: it is always headed "Emotion" (`heading`), it keeps the name
of the file it came from as a note, and no other lexicon may take its id or its name.

Both the Lexicons page (Over time area) and the Statistics tab (`layers.py`) read lexicons through `stored`: every readable
`<id>.json` in the folder is a lexicon. The functions that change a lexicon take the folder, check what they are given (a `ValueError`
says what to fix; a `KeyError` is an unknown lexicon or category), and write the file at once.
"""
from __future__ import annotations

import csv
import json
import re
import threading
from collections import defaultdict
from pathlib import Path

EMOTION = "emotion"                                   # the id of the emotion lexicon
MAX_LEXICONS = 50                                     # lexicons in the folder
MAX_CATEGORIES = 200                                  # categories in one lexicon
MAX_PAIRS = 500_000                                   # words in categories of one lexicon (a word in two categories counts twice)
MAX_NAME = 80                                         # characters of a lexicon's or a category's name
_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,59}")
_LOCK = threading.Lock()                              # one change at a time (read, edit, write)


# ---------- reading ----------
def path(folder, lid):
    """The file of lexicon `lid`. An id that couldn't have been made by `new_id` (it may come from a request) is a KeyError."""
    if not _ID.fullmatch(str(lid)):
        raise KeyError(lid)
    return Path(folder) / f"{lid}.json"


def load(file: Path):
    """Read one lexicon file ({name, cats}), or None if it isn't there. A damaged file is a ValueError that says what to do."""
    if not file.exists():
        return None
    try:
        lex = json.loads(file.read_text(encoding="utf-8"))
        if isinstance(lex.get("cats"), dict):
            return lex
    except (OSError, ValueError, AttributeError):
        pass
    raise ValueError(f"The lexicon file {file.name} can't be read. Replace its words with a new upload, or remove it.")


def stored(folder):
    """Every readable lexicon in `folder` -> {id: lexicon}. A file that can't be read is left out (`listing` reports it)."""
    out = {}
    for p in sorted(Path(folder).glob("*.json")) if Path(folder).exists() else []:
        try:
            lex = load(p)
        except ValueError:
            continue
        if lex and _ID.fullmatch(p.stem):
            out[p.stem] = lex
    return out


def heading(lid, lex):
    """What a lexicon is called in headings and pickers: "Emotion" for the emotion lexicon, else the name it was stored with (or its id)."""
    return "Emotion" if lid == EMOTION else (lex or {}).get("name") or lid


def listing(folder):
    """Every lexicon file in `folder` for the page, the emotion lexicon first, then by name: `{id, name, source, categories: {category:
    number of words}, problem}`. `source` is the name the emotion lexicon was stored with (its file's name); `problem` says why a file
    can't be read (it then has no categories)."""
    rows = []
    for p in sorted(Path(folder).glob("*.json")) if Path(folder).exists() else []:
        if not _ID.fullmatch(p.stem):
            continue
        try:
            lex, problem = load(p), None
        except ValueError as e:
            lex, problem = None, str(e)
        rows.append({"id": p.stem, "name": heading(p.stem, lex), "source": (lex or {}).get("name") if p.stem == EMOTION else None,
                     "categories": {c: len(w) for c, w in sorted((lex or {}).get("cats", {}).items())}, "problem": problem})
    return sorted(rows, key=lambda r: (r["id"] != EMOTION, r["name"].lower()))


def get(folder, lid):
    """One readable lexicon. A KeyError if there is none; the ValueError of `load` if its file is damaged."""
    lex = load(path(folder, lid))
    if lex is None:
        raise KeyError(lid)
    return lex


# ---------- parsing ----------
HEADERS = {"word", "words", "term", "terms", "token", "tokens", "lemma", "entry"}       # what a header row's first cell can say (the row is skipped)
NO_WORDS = ("No words found. A file can be a list of words (one on each line), a word and a category on each line (optionally followed by 0 or 1), "
            "or have the category names in its first row and their words underneath (one column per category). Columns are separated by tabs, "
            "commas or semicolons.")


def parse(text, plain):
    """Read a lexicon's text -> {category: sorted words}. Words and categories are lowercased; `#` lines and blank lines are skipped.

    Three layouts are recognised (`_rows` finds the columns: tabs, commas or semicolons, with quotes as in CSV files):
    a **word list** (one word on each line) becomes one category called `plain`; **long** (a word and a category on each line, optionally
    followed by 1 or 0, which drops the word when it is 0; the NRC Emotion Lexicon's word-level file) and **wide** (the category names in
    the first row, their words underneath; empty cells are ignored). A header row of a word list or a long file ("word, category") is skipped.
    Which layout a file has is judged from its shape (`_is_wide`)."""
    lines = [ln for ln in text.lstrip("\ufeff").splitlines() if ln.strip() and not ln.strip().startswith("#")]     # (a tab at the start is an empty cell)
    rows, spaced = _rows(lines)
    if not rows:
        return {}
    if max(len(r) for r in rows) == 1:
        words = [r[0] for r in rows if r[0]]
        if words and words[0].lower() in HEADERS and len(words) > 1:
            words = words[1:]
        return {plain.strip().lower(): sorted({w.lower() for w in words})}
    cats = defaultdict(set)
    if not spaced and _is_wide(rows):
        head = [c.lower() for c in rows[0]]
        for row in rows[1:]:
            for c, cell in zip(head, row):
                if c and cell:
                    cats[c].add(cell.lower())
    else:
        for k, row in enumerate(rows):
            if len(row) < 2 or not row[0] or not row[1] or (k == 0 and row[0].lower() in HEADERS):
                continue
            if len(row) >= 3 and row[2]:
                try:
                    if float(row[2]) <= 0:
                        continue
                except ValueError:
                    continue                                       # a header row
            cats[row[1].lower()].add(row[0].lower())
    return {c: sorted(ws) for c, ws in cats.items() if ws}


def _rows(lines):
    """The cells of each line -> (rows of stripped cells, whether they were split at spaces). The delimiter (tab, comma or semicolon) is the
    one that leaves most lines with two or more cells; quotes work as in CSV files. With none, a line is one cell, unless some line has
    spaces in it: then every line is split at its spaces (a word and its category, in a plain text file)."""
    best, most = None, 0
    for d in "\t,;":
        try:
            rows = [[c.strip() for c in r] for r in csv.reader(lines, delimiter=d)]
        except csv.Error:
            continue
        n = sum(len(r) >= 2 for r in rows)
        if n > most:
            best, most = rows, n
    if best:
        return best, False
    try:
        single = [[c.strip() for c in r] for r in csv.reader(lines, delimiter="\t")]
    except csv.Error:
        single = [[ln] for ln in lines]
    if any(re.search(r"\s", ln) for ln in lines if '"' not in ln):
        return [ln.split() for ln in lines], True
    return single, False


def _is_wide(rows):
    """Whether delimited rows are one column per category (category names in the first row) rather than a word and a category per row.
    Four or more columns are wide, and so are three where some row's third cell is not a number (a long file's is 1 or 0). Two columns are long
    when the first cell of the first row says "word"/"term"…, or a category repeats in the second column, or the file is tiny; wide when the
    second column is all different, or a row misses a cell."""
    cols = max(len(r) for r in rows)
    body = rows[1:]
    if cols >= 4:
        return True
    if cols == 3:
        return any(len(r) >= 3 and r[2] and not _number(r[2]) for r in body)
    if rows[0][0].lower() in HEADERS:
        return False
    if any(len(r) < 2 or not r[0] or not r[1] for r in rows):
        return True
    seconds = [r[1].lower() for r in body]
    return len(body) >= 4 and len(set(seconds)) == len(seconds)


def _number(text):
    """Whether a cell is a number."""
    try:
        float(text)
        return True
    except ValueError:
        return False


def split_words(text):
    """The words of a box of text (separated by lines, spaces, commas or semicolons) -> sorted, lowercase, each once."""
    return sorted({w for w in re.split(r"[\s,;]+", text.lower()) if w})


# ---------- changing ----------
def _check(cats):
    """The categories, if there is at least one and they are within the limits; else a ValueError saying what is wrong."""
    if not cats:
        raise ValueError(NO_WORDS)
    if len(cats) > MAX_CATEGORIES:
        raise ValueError(f"A lexicon can have at most {MAX_CATEGORIES:,} categories; this one has {len(cats):,}.")
    if sum(len(w) for w in cats.values()) > MAX_PAIRS:
        raise ValueError(f"A lexicon can hold at most {MAX_PAIRS:,} words in categories.")
    if any(len(c) > MAX_NAME for c in cats):
        raise ValueError(f"A category name can have at most {MAX_NAME} characters.")
    return cats


def _name(folder, name, own=None):
    """The trimmed name of a lexicon, if it is given, not too long and not already used (by another lexicon, or by the emotion lexicon)."""
    name = str(name or "").strip()
    if not name:
        raise ValueError("Give the lexicon a name.")
    if len(name) > MAX_NAME:
        raise ValueError(f"A lexicon's name can have at most {MAX_NAME} characters.")
    if name.lower() == "emotion" or any(heading(lid, x).lower() == name.lower() for lid, x in stored(folder).items() if lid != own):
        raise ValueError(f"There is already a lexicon called “{name}”.")
    return name


def new_id(folder, name):
    """An id for a new lexicon: the name as a slug, with a number if it is taken (`emotion` is always taken)."""
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40].strip("-") or "lexicon"
    lid, n = base, 1
    while lid == EMOTION or path(folder, lid).exists():
        n += 1
        lid = f"{base}-{n}"
    return lid


def _write(folder, lid, name, cats):
    """Store a lexicon (through a temporary file, so a failed write leaves the old one)."""
    file = path(folder, lid)
    file.parent.mkdir(parents=True, exist_ok=True)
    tmp = file.with_suffix(".tmp")
    tmp.write_text(json.dumps({"name": name, "cats": cats}, ensure_ascii=False), encoding="utf-8")
    tmp.replace(file)


def create(folder, name, text, emotion=False):
    """Store a new lexicon from text (see `parse`) -> its id. With `emotion=True` it becomes the emotion lexicon (`name` is then only
    a note of where it came from, and it can't be there already)."""
    with _LOCK:
        if emotion:
            if path(folder, EMOTION).exists():
                raise ValueError("The emotion lexicon is already loaded. Replace its words instead.")
            lid, name = EMOTION, str(name or "").strip()[:MAX_NAME] or "Emotion lexicon"
        else:
            name = _name(folder, name)
            lid = new_id(folder, name)
        if len(list(Path(folder).glob("*.json"))) >= MAX_LEXICONS:
            raise ValueError(f"You can keep at most {MAX_LEXICONS} lexicons. Remove one first.")
        _write(folder, lid, name, _check(parse(text, heading(lid, {"name": name}))))
        return lid


def replace(folder, lid, text):
    """Give a lexicon the words of new text (see `parse`); it keeps its id and name. Also repairs a damaged file."""
    with _LOCK:
        file = path(folder, lid)
        if not file.exists():
            raise KeyError(lid)
        try:
            name = load(file)["name"]
        except (ValueError, KeyError):
            name = lid
        _write(folder, lid, name, _check(parse(text, heading(lid, {"name": name}))))


def rename(folder, lid, name):
    """Change the name a lexicon is shown by (the id stays). The emotion lexicon is always "Emotion"."""
    with _LOCK:
        if lid == EMOTION:
            raise ValueError("The emotion lexicon is always called Emotion.")
        lex = get(folder, lid)
        _write(folder, lid, _name(folder, name, own=lid), lex["cats"])


def remove(folder, lid):
    """Delete a lexicon (also one whose file is damaged)."""
    with _LOCK:
        file = path(folder, lid)
        if not file.exists():
            raise KeyError(lid)
        file.unlink()


def save_category(folder, lid, cat, name, text):
    """Give category `cat` of a lexicon the name `name` and the words of `text` (see `split_words`). `cat=None` adds a new category."""
    with _LOCK:
        lex = get(folder, lid)
        cats, name = lex["cats"], str(name or "").strip().lower()
        if not name:
            raise ValueError("Give the category a name.")
        if cat is not None and cat not in cats:
            raise KeyError(cat)
        if name != cat and name in cats:
            raise ValueError(f"This lexicon already has a category “{name}”.")
        words = split_words(text)
        if not words:
            raise ValueError("A category needs at least one word. To get rid of it, delete the category.")
        cats.pop(cat, None)
        cats[name] = words
        _write(folder, lid, lex.get("name") or lid, _check(cats))


def delete_category(folder, lid, cat):
    """Remove a category from a lexicon. A lexicon keeps at least one category (remove the lexicon instead)."""
    with _LOCK:
        lex = get(folder, lid)
        if cat not in lex["cats"]:
            raise KeyError(cat)
        if len(lex["cats"]) == 1:
            raise ValueError("A lexicon needs at least one category. To get rid of it, remove the lexicon.")
        del lex["cats"][cat]
        _write(folder, lid, lex.get("name") or lid, lex["cats"])
