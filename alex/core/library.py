"""The analyser's own state, and the books it reads.

Two things live here:

* **Where the books are.** `Library.scan()` looks through the workspace's own books folder (`books/` in the data folder,
  always read, so there is always a place to put books) and the source folders you add for BookNLP exports; `Library.book()` loads one (parsing is slow, so the result is saved in the
  cache folder (`bookcache.py`) and reused until the files change). The book folders are only ever read.
* **What you have added.** Book details, collections of books (`bookcollections.py`), tags, links between entities of different
  books ("persons"), saved groups of entities (`entitygroups.py`), saved Statistics sets (`statsets.py`), plural groups (`plurals.py`), settings and rejected link
  suggestions are kept in `library.json`; your
  corrections to narrators, addressees and conversations are kept in `annotations.json`.
  Both files are written atomically (write a temporary file, then rename it).

Everything is stored under one data folder (`alex-data` in the folder the analyser is started from unless another is given, or the
`ALEX_DATA` environment variable is set), so tests and experiments can use a separate one.

Entity ids ("units") used across the analyser:

* `e:<book>:<coref>`  one BookNLP coreference group in one book;
* `p:<n>`             a person/place you linked across books (see `Library.link`).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from . import bookcache, plurals
from .bookdata import TYPES, BookData, ekey, parse_ekey
from .statecheck import clean_annotations, clean_state

STAMP = re.compile(r"-(\d{8}-\d{6})$")                            # "<book>-20260924-201753": the editor's export folders
EXTS = ("tokens", "entities", "quotes", "supersense", "book", "txt")     # the files that make up a book
CACHE_VERSION = 13   # bump when BookData's structure changes, so old caches are ignored


def data_home() -> Path:
    """The analyser's data folder: `ALEX_DATA` if that is set, else `alex-data` in the current folder (as a full path)."""
    return Path(os.environ.get("ALEX_DATA") or "alex-data").expanduser().resolve()


class LibraryError(Exception):
    """The analyser's own files can't be read (for example a damaged library.json)."""


def default_state():
    """A fresh library.json: no source folders, book details, links, tags or collections (folders are added on the Library page or with `--books`)."""
    return {
        "sources": [],
        "books": {},
        "settings": {"min": {t: 2 for t in TYPES}, "count_mode": "per_book", "freq_mode": "combined", "conv_gap": 100,
                     "plural": False, "speech_skip": {"verbs": [], "adverbs": []},
                     "sound": {"window": 3, "boundary": "sentence", "alliteration": "stressed", "repetition": "lemma", "corrections": {}}},
        "persons": {},
        "entity_tags": {},
        "entity_names": {},
        "entity_notes": {},
        "rejected": [],
        "next_person": 1,
        "collections": {},
        "next_collection": 1,
        "groups": {},
        "next_group": 1,
        "plurals": {},
        "plural_rejected": [],
        "narrator_links": {},
        "next_narrator_link": 1,
        "stat_sets": {},
        "next_stat_set": 1,
    }


def read_json(path: Path, what: str) -> dict:
    """Read a JSON file that holds an object, turning a damaged, unreadable or differently shaped one into a `LibraryError` that says which
    file and why."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("it should hold one JSON object")
        return data
    except (ValueError, OSError) as e:
        raise LibraryError(f"{what} ({path}) can't be read: {e}. Fix or move the file and start again; nothing has been changed.") from e


def write_json(path: Path, data):
    """Write JSON so that a crash never leaves a half-written file: write beside it, then rename."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


class Library:
    """The analyser's books and your own settings, under one data folder.
    `state` is library.json (see default_state), `ann` is annotations.json; both are saved on every change.
    Books are found by `scan`, loaded by `book`, and described by `meta`. One lock guards the files and the tables of loaded books; parsing a book
    happens outside it (`_load`)."""
    def __init__(self, data_dir=None, sources=None):
        self.lock = threading.RLock()          # guards the two json files and the tables of loaded books (not the parsing of a book)
        self.version = 0         # bumped on every change to either file (and by `reopen`, so nothing cached for another folder is reused)
        self.ann_version = 0     # bumped when corrections change, so cached results that depend on them are rebuilt
        self._generation = 0     # bumped by `reopen`, so a `warm` still running for the old folder stops
        self._batch = 0          # how many `batch` blocks are open: while one is, `save` and `save_ann` only note what to write
        self._unsaved = set()    # what a `batch` has to write when it ends: "state", "ann"
        self._open(data_dir, sources)

    def _open(self, data_dir, sources):
        """Read a data folder into this library. Everything is read before anything is replaced, so a folder that can't be read
        (`LibraryError`) leaves the library as it was."""
        data_dir = Path(data_dir) if data_dir else data_home()
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "cache").mkdir(exist_ok=True)
        books_dir = data_dir / "books"
        books_dir.mkdir(exist_ok=True)
        state_path, annot_path = data_dir / "library.json", data_dir / "annotations.json"
        state, notes = default_state(), []
        if state_path.exists():
            state, notes = clean_state(read_json(state_path, "The analyser's settings file"), state)
        if sources is not None:
            state["sources"] = [str(s) for s in sources]
        state["sources"] = [s for s in state["sources"] if Path(s).expanduser().resolve() != books_dir.resolve()]   # always read anyway (older imports listed it)
        ann = {"books": {}}
        if annot_path.exists():
            ann, ann_notes = clean_annotations(read_json(annot_path, "Your corrections file"))
            notes += ann_notes
        with self.lock:
            self.data_dir = data_dir
            self.cache_dir = data_dir / "cache"
            self.books_dir = books_dir                     # the workspace's own books folder, read before the sources
            self.state_path, self.annot_path = state_path, annot_path
            self.state, self.ann = state, ann
            self.state_notes = notes                       # what `statecheck` left out of the two files, for the Library page
            self._loaded: dict[tuple, BookData] = {}       # book key -> the parsed book
            self._plural: dict[tuple, BookData] = {}       # (book key, declarations applied) -> its plural_copy
            self._found: dict = {}
            self._parsing: dict[tuple, threading.Lock] = {}  # book key -> the lock of the thread reading it (see `_load`)
            self.link_units: dict = {}                     # links.py's per-entity summaries of the whole library: minimum mentions -> (stamp, units)

    def reopen(self, data_dir, sources=None):
        """Switch to another data folder (a workspace, see workspaces.py) without making a new `Library`, so everything that holds
        this one sees the new folder. Raises `LibraryError` and changes nothing if the folder's files can't be read. Callers
        should also drop what they cached from the old folder (the API `Context` does)."""
        with self.lock:
            self._open(data_dir, sources)
            self._generation += 1
            self.version += 1
            self.ann_version += 1

    # ---------- persistence ----------
    def save(self):
        """Write library.json (at the end of the `batch` block, if one is open)."""
        with self.lock:
            if self._batch:
                self._unsaved.add("state")
                return
            write_json(self.state_path, self.state)
            self.version += 1

    @contextmanager
    def batch(self):
        """A block of many changes that writes each file once, at its end, instead of after every change (auto-linking hundreds of
        entities, dissolving every link). Holds the lock throughout; blocks may be nested."""
        with self.lock:
            self._batch += 1
            try:
                yield self
            finally:
                self._batch -= 1
                if not self._batch:
                    unsaved, self._unsaved = self._unsaved, set()
                    if "state" in unsaved:
                        self.save()
                    if "ann" in unsaved:
                        self.save_ann()

    def ann_book(self, bid):
        """One book's corrections, created empty on first use."""
        return self.ann["books"].setdefault(bid, {"narrator": None, "para_narrators": {}, "addressees": {},
                                                  "splits": [], "merges": [], "participants": {}})

    def save_ann(self):
        """Write annotations.json (at the end of the `batch` block, if one is open)."""
        with self.lock:
            if self._batch:
                self._unsaved.add("ann")
                return
            write_json(self.annot_path, self.ann)
            self.ann_version += 1
            self.version += 1

    # ---------- discovery ----------
    def scan(self):
        """Find every book in the books folder and the source folders -> ({book id: [versions, newest first]}, [problems]).

        The books folder, like a source, can be a folder of exports (one dated subfolder per export) or a folder that
        holds BookNLP files directly. A book needs at least `.tokens` and `.entities`."""
        found, problems, seen = {}, [], set()
        for src in [self.books_dir, *self.state["sources"]]:
            root = Path(src).expanduser()
            if root == self.books_dir and not root.is_dir():        # deleted while the analyser runs: nothing to report
                continue
            if not root.is_dir():
                problems.append(f"Folder not found: {root}")
                continue
            try:
                folders = [root] + sorted(p for p in root.iterdir() if p.is_dir())
            except OSError as e:                                     # no permission to list it, say
                problems.append(f"Folder can't be read: {root} ({e.strerror or e})")
                continue
            for folder in folders:
                try:
                    tokens = sorted(folder.glob("*.tokens"))
                except OSError:                                      # one unreadable export folder must not hide the rest
                    problems.append(f"Folder can't be read: {folder}")
                    continue
                for tok in tokens:
                    bid = tok.stem
                    if not (folder / f"{bid}.entities").exists():
                        continue
                    if (bid, os.path.realpath(folder)) in seen:       # the same folder reached through two sources (a folder and its parent)
                        continue
                    seen.add((bid, os.path.realpath(folder)))
                    m = STAMP.search(folder.name)
                    stamp = m.group(1) if m else time.strftime("%Y%m%d-%H%M%S", time.localtime(tok.stat().st_mtime))
                    found.setdefault(bid, []).append({"folder": str(folder), "stamp": stamp, "exported": bool(m)})
        for versions in found.values():
            versions.sort(key=lambda v: v["stamp"], reverse=True)
        self._found = found
        return found, problems

    def add_sources(self, folders) -> list[str]:
        """Add folders to look for books in (full paths; ones already listed are skipped) and save -> the folders that were added."""
        with self.lock:
            new = []
            for folder in folders:
                path = str(Path(folder).expanduser().resolve())
                if path not in self.state["sources"] and path not in new:
                    new.append(path)
            if new:
                self.state["sources"] += new
                self.reset_scan()
                self.save()
            return new

    def reset_scan(self):
        """Forget the last scan (after the source folders changed)."""
        self._found = {}

    def found(self):
        """The books found by the last scan, scanning first if there hasn't been one."""
        return self._found or self.scan()[0]

    def folder_for(self, bid):
        """The folder of the export used for a book: the one you pinned, else the newest."""
        versions = self._found.get(bid) or self.scan()[0].get(bid)
        if not versions:
            return None
        pinned = self.state["books"].get(bid, {}).get("pinned")
        if pinned and any(v["folder"] == pinned for v in versions):
            return Path(pinned)
        return Path(versions[0]["folder"])

    # ---------- loading ----------
    def _signature(self, bid, folder):
        """Modification times of a book's files: changes whenever a new export replaces them."""
        return tuple((folder / f"{bid}.{e}").stat().st_mtime if (folder / f"{bid}.{e}").exists() else 0 for e in EXTS)

    def book_key(self, bid):
        """Identifies the current version of a book's data; changes when the export used or its files change."""
        folder = self.folder_for(bid)
        if folder is None:
            raise KeyError(bid)
        return (bid, str(folder), self._signature(bid, folder))

    def book(self, bid, plural=False) -> BookData:
        """Load a book (from memory, else from the cache, else by parsing its files), with your plural-group declarations
        applied (plurals.py). `plural`: the book counted the "include plural-group mentions" way, made from the parsed book
        (`BookData.plural_copy`) and kept in memory until the declarations or the files change."""
        key = self.book_key(bid)
        with self.lock:
            bd = self._loaded.get(key)
        if bd is None:
            bd = self._load(bid, key)
        with self.lock:
            bd.set_members(plurals.book_map(self, bid))
            if not plural:
                return bd
            pk = (key, bd.members_sig)
            if pk not in self._plural:
                self._plural = {k: v for k, v in self._plural.items() if k[0] != key}
                self._plural[pk] = bd.plural_copy()
            return self._plural[pk]

    def _load(self, bid, key) -> BookData:
        """The parsed book for `key` (see `book_key`), read from the cache or its files. Parsing a novel takes seconds, so it happens
        *outside* the library lock, which would otherwise hold up every other request (and every save) meanwhile: a lock of the book's own
        makes the threads that want the same book wait for the one parsing it, and the rest carry on."""
        with self.lock:
            gate, generation = self._parsing.setdefault(key, threading.Lock()), self._generation
        with gate:
            with self.lock:
                bd = self._loaded.get(key)
            if bd is None:
                bd = self._parsed(bid, Path(key[1]), key)
                with self.lock:
                    if generation == self._generation:                                  # (not switched to another folder meanwhile)
                        for k in [k for k in self._loaded if k[0] == bid]:              # the book's files changed
                            del self._loaded[k]
                        self._plural = {k: v for k, v in self._plural.items() if k[0][0] != bid}
                        self._loaded[key] = bd
        with self.lock:
            self._parsing.pop(key, None)
        return bd

    def warm(self, progress=None):
        """Load every book now (from the cache, else by parsing it), so the first page doesn't have to wait for them. A book that can't
        be read is skipped here and reported by the page that needs it. `progress(done, total)`, if given, is called after each book."""
        generation, books = self._generation, list(self.found())
        for done, bid in enumerate(books, 1):
            if generation != self._generation:         # the library was switched to another folder meanwhile
                return
            try:
                self.book(bid)
            except Exception:  # noqa: BLE001
                pass
            if progress:
                progress(done, len(books))

    def _parsed(self, bid, folder, key):
        """The parsed book from the cache, else parsed from its files and cached (outdated caches of it are removed)."""
        digest, cache_dir = hashlib.sha1(repr((CACHE_VERSION,) + key).encode()).hexdigest()[:16], self.cache_dir
        cache_file = cache_dir / f"{bid}-{digest}.pkl"
        if cache_file.exists():
            try:
                return bookcache.loads(cache_file.read_bytes())
            except Exception:  # noqa: BLE001 - a damaged, outdated or unexpected cache is simply rebuilt
                pass
        bd = BookData(bid, folder)
        try:
            for old in cache_dir.glob(f"{bid}-*.pkl"):     # not another book whose id starts "<bid>-"
                if re.fullmatch(re.escape(bid) + r"-[0-9a-f]{16}(-p)?\.pkl", old.name):
                    old.unlink(missing_ok=True)
            tmp = cache_file.with_suffix(".tmp")
            tmp.write_bytes(bookcache.dumps(bd))
            tmp.replace(cache_file)
        except OSError:          # a full disk or a read-only data folder: the book still opens, it is just parsed again next time
            pass
        return bd

    def meta(self, bid):
        """A book's details as shown in the interface (title falls back to the id)."""
        m = self.state["books"].get(bid, {})
        return {"title": m.get("title") or bid, "author": m.get("author", ""), "year": m.get("year", ""),
                "series": m.get("series", ""), "tags": m.get("tags", []), "pinned": m.get("pinned")}

    def set_meta(self, bid, patch):
        """Change some of a book's details (title, author, year, series, tags, pinned)."""
        with self.lock:
            m = self.state["books"].setdefault(bid, {})
            for k in ("title", "author", "year", "series", "tags", "pinned"):
                if k in patch:
                    m[k] = patch[k]
            self.save()

    # ---------- units: entities and the persons you link across books ----------
    ekey = staticmethod(ekey)      # the unit id of one coreference group in one book (see bookdata.ekey)

    def person_of(self):
        """(book, coref) -> person id, for every entity you have linked."""
        return {(bid, int(c)): pid for pid, p in self.state["persons"].items() for bid, c in p["members"]}

    def tags_of(self, uid):
        """Tags of an entity or linked person."""
        if uid.startswith("p:"):
            return self.state["persons"].get(uid[2:], {}).get("tags", [])
        return self.state["entity_tags"].get(uid, [])

    def set_tags(self, uid, tags):
        """Replace an entity's or person's tags (sorted, blanks dropped)."""
        tags = sorted({t.strip() for t in tags if t.strip()})
        with self.lock:
            if uid.startswith("p:"):
                if uid[2:] not in self.state["persons"]:
                    raise KeyError(uid)
                self.state["persons"][uid[2:]]["tags"] = tags
            elif tags:
                self.state["entity_tags"][uid] = tags
            else:
                self.state["entity_tags"].pop(uid, None)
            self.save()

    def name_of(self, uid):
        """Your name for an entity, linked person or narrator link, if you gave one; else None (the page falls back to
        the name found in the books, or, for a narrator link, to its members' own names)."""
        if uid.startswith("p:"):
            return self.state["persons"].get(uid[2:], {}).get("name")
        if uid.startswith("nl:"):
            return self.state["narrator_links"].get(uid[3:], {}).get("name")
        return self.state["entity_names"].get(uid)

    def set_name(self, uid, name):
        """Give an entity, linked person or narrator link a name (blank goes back to the one found in the books)."""
        name = name.strip() or None
        with self.lock:
            if uid.startswith("p:"):
                if uid[2:] not in self.state["persons"]:
                    raise KeyError(uid)
                self.state["persons"][uid[2:]]["name"] = name
            elif uid.startswith("nl:"):
                if uid[3:] not in self.state["narrator_links"]:
                    raise KeyError(uid)
                self.state["narrator_links"][uid[3:]]["name"] = name
            elif name:
                self.state["entity_names"][uid] = name
            else:
                self.state["entity_names"].pop(uid, None)
            self.save()

    def note_of(self, uid):
        """Your short description of an entity or linked person, or ""."""
        if uid.startswith("p:"):
            return self.state["persons"].get(uid[2:], {}).get("note") or ""
        return self.state["entity_notes"].get(uid, "")

    def set_note(self, uid, note):
        """Give an entity or linked person a short free-text description (blank clears it)."""
        note = note.strip()
        with self.lock:
            if uid.startswith("p:"):
                if uid[2:] not in self.state["persons"]:
                    raise KeyError(uid)
                if note:
                    self.state["persons"][uid[2:]]["note"] = note
                else:
                    self.state["persons"][uid[2:]].pop("note", None)
            elif note:
                self.state["entity_notes"][uid] = note
            else:
                self.state["entity_notes"].pop(uid, None)
            self.save()

    def all_tags(self):
        """Every tag in use, case-insensitively sorted."""
        tags = set()
        for p in self.state["persons"].values():
            tags.update(p.get("tags", []))
        for t in self.state["entity_tags"].values():
            tags.update(t)
        return sorted(tags, key=str.lower)

    def unit_of_entity(self, uid):
        """The unit an id stands for now: a single entity's `e:` id becomes the `p:` id of the person it was linked into (if it
        was); anything else is returned as it is."""
        key = parse_ekey(uid)
        pid = self.person_of().get(key) if key else None
        return "p:" + pid if pid else uid

    def link(self, a, b, name=None):
        """Treat two units (entity or person ids) as the same. Their members, tags, name and description are merged into one
        person, which is returned as `p:<n>`. An entity already linked into a person stands for that person, so an entity is
        never in two persons; linking two ids that are already one person changes nothing. KeyError for an id that names no
        entity or person."""
        with self.lock:
            persons = self.state["persons"]
            a, b = self.unit_of_entity(str(a)), self.unit_of_entity(str(b))
            for u in (a, b):
                if u.startswith("p:") and u[2:] not in persons or not u.startswith("p:") and parse_ekey(u) is None:
                    raise KeyError(u)
            if a == b:                            # already one (an entity with itself, or two members of one person)
                return a

            def parts(u):
                """A unit's (members, tags, name, note); a single entity's tags, name and note move with it, taken
                out of `entity_tags` / `entity_names` / `entity_notes`."""
                if u.startswith("p:"):
                    p = persons[u[2:]]
                    return list(p["members"]), list(p.get("tags", [])), p.get("name"), p.get("note")
                bid, c = parse_ekey(u)
                return ([[bid, c]], self.state["entity_tags"].pop(u, []),
                        self.state["entity_names"].pop(u, None), self.state["entity_notes"].pop(u, None))

            ma, ta, na, oa = parts(a)
            mb, tb, nb, ob = parts(b)
            pid = a[2:] if a.startswith("p:") else b[2:] if b.startswith("p:") else self._new_person()
            for u in (a, b):                      # a person that is absorbed disappears
                if u.startswith("p:") and u[2:] != pid:
                    persons.pop(u[2:], None)
            person = persons[pid]
            person["members"] = [list(m) for m in dict.fromkeys(tuple(m) for m in ma + mb)]
            person["tags"] = sorted(set(ta) | set(tb) | set(person.get("tags", [])))
            person["name"] = name or person.get("name") or na or nb
            note = person.get("note") or oa or ob
            if note:
                person["note"] = note
            merged = "p:" + pid
            moved = self._retarget(lambda bid, u: merged if u in (a, b) else u, {a: [merged], b: [merged]})
            self.save()
            if moved:
                self.save_ann()
            return merged

    def _new_person(self):
        """A fresh, empty person -> its number (as a string)."""
        pid = str(self.state["next_person"])
        self.state["next_person"] += 1
        self.state["persons"][pid] = {"members": [], "tags": [], "name": None}
        return pid

    def _give_details(self, members, tags, name, note):
        """Give each of the `members` ((book, coref)) a copy of a dissolving person's tags, name and description, as a single entity."""
        for bid, c in members:
            key = self.ekey(bid, c)
            for store, value in (("entity_tags", tags), ("entity_names", name), ("entity_notes", note)):
                if value:
                    self.state[store][key] = list(value) if store == "entity_tags" else value

    def unlink(self, pid, bid, coref):
        """Take one book's entity out of a linked person, taking a copy of the person's tags, name and description
        with it. A person left with one member dissolves the same way. KeyError if that entity isn't one of its members."""
        with self.lock:
            p = self.state["persons"][pid]
            before = list(p["members"])
            p["members"] = [m for m in p["members"] if not (m[0] == bid and int(m[1]) == int(coref))]
            if len(p["members"]) == len(before):
                raise KeyError(self.ekey(bid, coref))
            details = list(p.get("tags") or []), p.get("name"), p.get("note")
            self._give_details([(bid, coref)], *details)
            if len(p["members"]) <= 1:
                self._give_details(p["members"], *details)
                del self.state["persons"][pid]
            moved = self._released(pid, before)
            self.save()
            if moved:
                self.save_ann()

    def unlink_all(self, pid):
        """Dissolve a linked person entirely: every member becomes its own entity again, each taking a copy of the
        person's tags, name and description, the same way one member does when taken out with `unlink`."""
        with self.lock:
            p = self.state["persons"][pid]
            members = list(p["members"])
            self._give_details(members, list(p.get("tags") or []), p.get("name"), p.get("note"))
            del self.state["persons"][pid]
            moved = self._released(pid, members)
            self.save()
            if moved:
                self.save_ann()

    def reset_links(self):
        """Dissolve every link at once: each linked person as `unlink_all` does (members keep copies of its tags, name and
        description) and every narrator link. Rejected suggestions ("Not the same") are kept: they aren't links.
        -> (persons dissolved, narrator links dissolved)."""
        with self.batch():
            pids = list(self.state["persons"])
            for pid in pids:
                self.unlink_all(pid)
            lids = list(self.state["narrator_links"])       # taken after the persons: dissolving them may have dissolved some
            for lid in lids:
                self.unlink_narrators_all(lid)
            return len(pids), len(lids)

    def _retarget(self, resolve, roles):
        """After linking or unlinking changed which unit ids exist, make your corrections name units that still do: the book's
        narrator, paragraph and chapter narrators, addressees and added or removed participants (annotations.json; the caller saves
        it when this returns True) and the `nar:<unit id>` members of narrator links (library.json). `resolve(book, unit id)` gives the
        id a correction of that book should use now, the same id if nothing changed; `roles` maps a unit id to the unit ids its
        narrator-link members become. Without this a correction kept the id of a person that no longer exists."""
        before = json.dumps(self.ann["books"], sort_keys=True)
        for bid, ab in self.ann["books"].items():
            def one(u):
                """A correction's id: "anon" (an unnamed narrator) and "*" (everyone present) are not units."""
                return u if u in ("anon", "*") else resolve(bid, u)
            if ab.get("narrator"):
                ab["narrator"] = one(ab["narrator"])
            for field in ("para_narrators", "chapter_narrators"):
                for key, u in ab.get(field, {}).items():
                    ab[field][key] = one(u)
            for key, us in ab.get("addressees", {}).items():
                if us:
                    ab["addressees"][key] = list(dict.fromkeys(one(u) for u in us))
            for edit in ab.get("participants", {}).values():
                for side in ("add", "remove"):
                    if side in edit:
                        edit[side] = list(dict.fromkeys(one(u) for u in edit[side]))
        for lid, link in list(self.state["narrator_links"].items()):
            members = []
            for m in link["members"]:
                uid = m[4:] if m.startswith("nar:") else None
                members += ["nar:" + u for u in roles[uid]] if uid in roles else [m]
            if members != link["members"]:
                link["members"] = list(dict.fromkeys(members))
                if len(link["members"]) < 2:             # linked roles that became one are no link any more
                    del self.state["narrator_links"][lid]
        return json.dumps(self.ann["books"], sort_keys=True) != before

    def _released(self, pid, old_members):
        """`_retarget` for a person that lost members (`old_members` is the list it had before). A book's corrections are about that
        book, so where the person has no member left a correction naming it names the book's own entity instead; if the person is
        gone, a narrator link's member for it becomes one for each entity it had."""
        person = self.state["persons"].get(pid)
        still = {m[0] for m in person["members"]} if person else set()
        own = {}
        for bid, c in old_members:
            own.setdefault(bid, self.ekey(bid, c))
        uid = "p:" + pid
        return self._retarget(lambda bid, u: own[bid] if u == uid and bid in own and bid not in still else u,
                              {} if person else {uid: list(own.values())})

    # ---------- linking narrator roles ----------
    # A narrator role (nar:<unit id> or nar:anon:<book>, see dialogue.py) isn't a unit, so it can't go through
    # `link`/`unlink` above (those expect a (book, coref) member); this is the same idea, kept separate, for roles.
    # A narrator link pools narration only — the underlying characters (if any), their mentions, relations, tags
    # and so on stay exactly as they were; only which role a paragraph's narration counts as "the same narrator" changes.
    def link_narrators(self, a, b, name=None):
        """Treat two narrator roles (`nar:…`, or a narrator link `nl:<n>`) as the same narrator, merged into one narrator link,
        returned as `nl:<n>`. A role already in a link stands for that link, so a role is never in two links; two ids that are
        already one change nothing. KeyError for an id that is neither a role nor an existing link."""
        with self.lock:
            links = self.state["narrator_links"]
            link_of = self.narrator_link_of()
            a, b = (link_of.get(str(u), str(u)) for u in (a, b))
            for u in (a, b):
                if not (u.startswith("nar:") or u.startswith("nl:") and u[3:] in links):
                    raise KeyError(u)
            if a == b:
                return a

            def parts(u):
                """A role's or link's (members, name)."""
                if u.startswith("nl:"):
                    link = links[u[3:]]
                    return list(link["members"]), link.get("name")
                return [u], None

            ma, na = parts(a)
            mb, nb = parts(b)
            if a.startswith("nl:"):
                lid = a[3:]
            elif b.startswith("nl:"):
                lid = b[3:]
            else:
                lid = str(self.state["next_narrator_link"])
                self.state["next_narrator_link"] += 1
                links[lid] = {"members": [], "name": None}
            for u in (a, b):                      # a narrator link that is absorbed disappears
                if u.startswith("nl:") and u[3:] != lid:
                    links.pop(u[3:], None)
            link = links[lid]
            link["members"] = list(dict.fromkeys(ma + mb))
            link["name"] = name or link.get("name") or na or nb
            self.save()
            return "nl:" + lid

    def unlink_narrator(self, lid, role):
        """Take one narrator role out of a narrator link. A link left with one member dissolves."""
        with self.lock:
            link = self.state["narrator_links"][lid]
            link["members"] = [m for m in link["members"] if m != role]
            if len(link["members"]) <= 1:
                del self.state["narrator_links"][lid]
            self.save()

    def unlink_narrators_all(self, lid):
        """Dissolve a narrator link entirely: every role becomes its own narrator again."""
        with self.lock:
            del self.state["narrator_links"][lid]
            self.save()

    def narrator_link_of(self):
        """Narrator role id -> its narrator-link id (`nl:<n>`), for every role you've linked."""
        return {role: "nl:" + lid for lid, link in self.state["narrator_links"].items() for role in link["members"]}

    # ---------- rejected link suggestions ----------
    def entity_keys(self, u):
        """The single-book entity ids inside a unit (a person's members, or the entity itself)."""
        if u.startswith("p:"):
            return [self.ekey(b, c) for b, c in self.state["persons"].get(u[2:], {}).get("members", [])]
        return [u]

    def rejected_set(self):
        """The rejected pairs as a set of sorted tuples: pass it to `is_rejected` when checking many pairs in a row."""
        return {tuple(p) for p in self.state["rejected"]}

    def is_rejected(self, a, b, rejected=None):
        """Whether you said a and b are different (checked member by member, so it survives later links).
        `rejected`: the result of `rejected_set()`, if the caller already has it (it is rebuilt from the list otherwise)."""
        rejected = self.rejected_set() if rejected is None else rejected
        return any(tuple(sorted((x, y))) in rejected for x in self.entity_keys(a) for y in self.entity_keys(b))

    def reject(self, a, b):
        """Remember that a and b are different, as pairs of single-book entities."""
        with self.lock:
            rejected = self.rejected_set()
            for x in self.entity_keys(a):
                for y in self.entity_keys(b):
                    pair = tuple(sorted((x, y)))
                    if pair not in rejected:
                        self.state["rejected"].append(list(pair))
                        rejected.add(pair)
            self.save()
