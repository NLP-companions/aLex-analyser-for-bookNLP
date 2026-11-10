# aLex - BookNLP analyser — technical documentation

This file explains how the analyser is built, so you can find your way around the code, change it, and trust it.
The [user guide](guide.md) is for *using* aLex (the README for installing it); this is for *working on* it. Every module, function and script also carries
its own comments; this file is the map that connects them.

Contents: 1 Overview · 2 Folder layout · 3 Data (what is read, what is written) · 4 How a request flows ·
5 The analysis code (`core/`) · 6 Definitions and methods · 7 The web API · 8 The browser code (`static/`) ·
9 Testing · 10 Extending the analyser · 11 Large libraries · 12 Robustness decisions · 13 Troubleshooting

What each figure means, how it is calculated and where in the code: [MEASURES.md](MEASURES.md).

---

## 1. Overview

aLex (the analyser) reads books processed by BookNLP (its output files, or exports from the companion editor) and offers views of them in the browser:
entities (with narrators and groups of entities), dialogue, corpus tools, arcs and style, topics, a text view with a chapter editor,
and tools for linking entities across books. Books can be organised in collections.

* It is a **Python** program (FastAPI + uvicorn) that serves one HTML page and a JSON API on `127.0.0.1` only.
* The browser side is **plain JavaScript** (no build step, no framework): a set of scripts that draw pages from JSON.
* Nothing is written to your books' folders. The analyser writes only under its own data folder, `alex-data` (see section 3).
* Python packages: `fastapi`, `uvicorn`, `networkx`, `vaderSentiment` (sentiment), `scikit-learn` (topics; brings numpy and scipy).
  All of them are installed with the package (`pyproject.toml`); the code still copes if scikit-learn or vaderSentiment is missing: the Topics tab
  and the sentiment page then explain what to install.
* Optional: `cmudict` (the CMU Pronouncing Dictionary, for sound and rhythm), installed with the `sound` extra
  (`pip install "alex-booknlp-analyser[sound]"`). The package is GPL-3.0 (its dictionary data is BSD), so it isn't a default dependency;
  without it `core/sound.py` raises `sound.MISSING`, which says how to install it. CI installs it (`.[dev,sound]`); its tests skip without it.

## 2. Folder layout

```
pyproject.toml         the package: name, version, Python version, dependencies, the `alex` command, test settings
README.md  LICENSE     what it is and how to install it (README); MIT licence
docs/                  the user guide (guide.md), this file, MEASURES.md and DESIGN.md (the design language of the interface)
alex/                  the package (everything below this line in this block is inside it)
  app.py               start-up (`alex` / `python -m alex`): builds the web app, error handling, static files
  localonly.py         middleware: answers only requests for this computer, and changes only from our own page (section 12)
  api/                 the web API: one router per area (routes only; no analysis)
  core/                the analysis: reads books, computes, no web code
    topics/            topic modelling (a package)
  static/              index.html, app.css and js/ (the browser code)
tests/                 the test suite (pytest) and its browser tests (tests/js)
alex-data/             the analyser's own files, made in the folder you start it from (git-ignored; see section 3)
```

Paths such as `core/…`, `api/…` and `static/…` in the rest of this file are inside the `alex/` folder. `core/` never imports
from `api/` or `app.py`, and `api/` contains no analysis: a route validates its input, calls one
function in `core/` and returns the result. That split is what lets the tests exercise the analysis without a web server.

## 3. Data

### What is read (BookNLP files)

A book is a folder with files named after its id (`houn` → `houn.tokens`, …). The editor writes each export in a dated
folder (`houn-20260924-124729`); the newest export of each book is used unless you pin an earlier one.

| File | One row per | Columns used |
|---|---|---|
| `.tokens` (required) | token | `paragraph_ID`, `sentence_ID`, `token_ID_within_document`, `word`, `lemma`, `byte_onset`, `byte_offset`, `POS_tag`, `fine_POS_tag`, `dependency_relation`, `syntactic_head_ID`, `event` |
| `.entities` (required) | mention | `COREF` (the group), `start_token`, `end_token`, `prop` (PROP name / NOM description / PRON pronoun), `cat` (PER, LOC…), `text` |
| `.quotes` | quote | `quote_start`, `quote_end`, `mention_start`, `mention_end` (the mention BookNLP used to attribute it), `char_id` (speaker's group), `quote` |
| `.supersense` | span | `start_token`, `end_token`, `supersense_category` |
| `.book` | (JSON) | `characters[].id / name / g.argmax` (BookNLP's names and pronouns) |
| `.txt` | (the whole text) | optional; the original text the export was made from. Found the same way as the other optional files (in the book's own folder), not in a BookNLP input folder. Used for exact inter-token spacing in `BookData.span_text` (falls back to a single-space guess without it) and offered for download on the Library page (`/api/books/{bid}/text`). |

Everything in the analyser addresses tokens by their **position** in `.tokens` (0, 1, 2 …). A parse problem is reported by
name, file and line; mentions or quotes outside the book are skipped with a note on the Library page, and so are lines of `.entities`, `.quotes`
or `.supersense` that can't be read at all (a missing field, a number that isn't one: the note says how many). A byte-order mark and Windows
line endings are fine; a file that isn't UTF-8 text is refused with a message that says so. Optional columns of `.tokens` (`fine_POS_tag`,
`event`, `byte_onset`, `byte_offset`) may be missing.

`byte_onset`/`byte_offset`, despite the name, are **character offsets** into the original text (Unicode codepoints), not true UTF-8 byte offsets: a
multi-byte character (curly quotes, em dashes, £…) is one unit there but two or three bytes in a UTF-8 file. `BookData._original_text` decodes `.txt`
once to a `str` (`raw_text`) for exactly this reason, so `span_text` indexes it by character position; slicing the raw bytes instead corrupts every
token after the first multi-byte character in the book (a real bug this project hit once — see `test_span_text_handles_multibyte_characters_in_the_original_text`).

### What is written (`alex-data/`)

| Path | Contents |
|---|---|
| `books/` | the workspace's own books folder: always read, before the `sources`, and made when the data folder is opened, so there is always a place to put BookNLP output (the "Open" buttons show it in the file browser). It holds books as a source does (files directly, or one subfolder per book or export). `Workspaces.delete` removes it with the workspace |
| `library.json` | your settings and work: `sources` (other folders to read books from, where they lie; none in a fresh library, see below; the books folder is never listed, and an entry for it is dropped on opening), `books` (title, author, year, series, tags, pinned export), `settings` (`min` per type, `count_mode`, `freq_mode`: `combined` (the default) or `per_book`, how a minimum word frequency is counted, `conv_gap`, `plural`: count plural groups' mentions for their members by default, `speech_skip`: `{verbs, adverbs}`, lemmas that never count as a quote's speech verb or manner, `sound`: `{window, boundary, alliteration, repetition, corrections}`, the sound and rhythm settings, read through `prosody.config`, which fills in what is missing), `persons` (entities you linked: `{id: {members: [[book, coref]], tags, name, note}}`), `entity_tags`, `entity_names` (a name you gave a single, unlinked entity) and `entity_notes` (its description), `rejected` (pairs you said are different), `next_person`, `collections` (`{id: {name, parent, books}}`, nested; a book may be in several) and `next_collection`, `groups` (saved groups of entities: `{id: {name, ids}}`) and `next_group`, `plurals` (plural groups: `{unit id: [member unit ids]}`) and `plural_rejected` (suggestions you dismissed), `narrator_links` (narrator roles linked into one: `{id: {members: [role id, ...], name}}`) and `next_narrator_link`, `stat_sets` (saved Statistics sets: `{id: {name, setup}}`, the setup as `/api/stats` takes it) and `next_stat_set` |
| `annotations.json` | your corrections, per book: `narrator`, `para_narrators` (paragraph key → unit or `"anon"`), `chapter_narrators` (chapter key, or `narrative.OPENING_KEY`, → unit or `"anon"`; see below), `addressees` (quote key → units or `["*"]`), `splits`, `merges`, `participants` (`add`/`remove`), `narr_rejected`, `chapters` (`add` / `remove`: paragraph keys, `names`: paragraph key → title) |
| `cache/<book>-<hash>.pkl` | a parsed book (parsing takes seconds; the hash covers the files' modification times and `CACHE_VERSION`; the file is about twice the size of the book's own files). Safe to delete. Opened only by `bookcache.loads`, which refuses code in a pickle (a copied-in cache folder can't run anything). (The way with plural groups counted for their members is made from it in memory, see below.) |
| `topics/<id>.json` | one fitted topic model (settings, documents, vocabulary, topic–word and document–topic matrices, quality figures, your labels) |
| `references/<id>.json` | a reference file for keywords: `{name, files, kinds, tokens, types, counts}` |
| `lexicons/<id>.json` | one word lexicon `{name, cats: {category: [words]}}`; `emotion.json` is the emotion lexicon. Every file in the folder is a lexicon, for the Lexicons page and for the Statistics tab (`core/lexicons.py`) |

All JSON is written atomically (a temporary file, then a rename). A damaged `library.json` or `annotations.json` stops start-up
with a message naming the file, and is never overwritten. The data folder is `alex-data` in the folder you start the analyser from, unless `--data FOLDER`, the `ALEX_DATA`
environment variable (`library.data_home`) or `Library(data_dir=…)` says otherwise; start-up prints which one is in use.

A fresh library has **no source folders** and an empty books folder. The Library page then says so, shows the books folder with an
**Open books folder** button (`POST /api/folders/open`, which asks Finder, Explorer or `xdg-open` to show it: `core/folders.py`) and links to
Settings → Folders, which lists the books folder and the data folder (each with Open) and the other source folders (Open, Remove), and where a
folder is added. Books dropped into a folder are found when the window regains focus (`refreshIfChanged`). Start-up prints the books folder too. A folder can also be added with
`alex --books FOLDER` (`Library.add_sources`: full paths, repeats skipped, saved; a path that
isn't a folder stops start-up with a message), or in a new workspace's folder box.

Your corrections (including chapter edits) are keyed by the *opening words* of a quote or paragraph (`dialogue.keys`), not by token
numbers, so they survive a re-export that shifts positions. The units they name follow your links (`Library._retarget`): `link` rewrites an id that
ceases to exist (an entity that joins a person, a person absorbed by another) to the new person; `unlink` / `unlink_all` give a book that has no member
left in the person its own entity (`_released`; corrections are per book, so this is exact), and a narrator link's `nar:<unit>` member for a dissolved
person becomes one per entity it had. `annotations.json` is rewritten only when a correction actually changed. Collections and saved groups store only book and entity ids: a group
follows your minimum, your links and the selected books, because `View.group_of` looks its entities up again each time.

### Identifiers

* **Book id**: the file stem (`houn`).  **Coref**: BookNLP's group number, unique within a book.
* **Unit id**: an entity of the selection: `e:<book>:<coref>` for one book's group, or `p:<n>` for a person you linked. `bookdata.ekey` makes
  the first kind and `bookdata.parse_ekey` reads it back (the coref is what follows the *last* colon, and a damaged id gives `None` rather than an error).
* **Member**: `(book, coref)`. A unit has one or more members (a linked person has one per book). An entity is never in two persons:
  `Library.link` treats an entity already linked as the person it is in (`unit_of_entity`), so linking it again extends that person,
  and `Library.link_narrators` does the same for a narrator role already in a narrator link.
* **Spec**: how the API names a set of units: `{"kind": "unit", "id"}`, `{"kind": "group", "ids"}` or `{"kind": "group", "group"}` (a saved group),
  `{"kind": "tag", "tag", "type"}`, `{"kind": "type", "types"}` (every entity of those types; `"type"` names just one), `{"kind": "others", "types"}`, `{"kind": "book", "book"}` (everyone counted in one
  book) or `{"kind": "gender", "pron"}` (every PER entity of one BookNLP-predicted gender, `UNKNOWN_GENDER` for none predicted), optionally with
  `"books"`; dialogue also accepts `{"kind": "narration", "id"}`.
* **Group**: several units analysed as one. `View.group_unit` makes a virtual `Unit` (id `"group"`, its `parts` are the real unit ids), so profiles,
  speech and topics work on it exactly as on one entity. A request names it with `ids` (a temporary group) or `group` (a saved one).
  `book_profile` and `gender_profile` pool a book's or a gender's own units the same way (`View._pooled_profile`), for their own pages
  (`book:<id>` / `gender:<pron>`, addressed like a narrator role) — everyone counted in a book, or every PER entity BookNLP predicted a
  gender for, as one page: mentions, relations, dialogue style, kinds of action, what's distinctive. Speech and Topics are left out there
  (they need an `id`/`ids`/`group` ref a pool doesn't have), and so is Appears with (a pool already contains almost everyone who could
  "appear with" it). `View.book_grid` compares two books "split into characters": every PER entity in either, with its mentions in each.
  `View.pool_unit(spec)` is the general form of this for unit/group/tag/type/gender specs: a `group_unit` pooling everyone a spec matches (None
  if it matches nobody), for a view that needs a real `Unit`'s worth of figures for a scope — `dialogue.entity()`'s per-book breakdown and
  narrating figures, via `/api/dialogue/scope` — rather than just `resolve`'s flat member set. It doesn't handle `book`/`others`/`narration`
  (not needed by that route) or apply a spec's own `"books"` (the view is already scoped to your book selection).
* **Plural group**: an entity whose mentions ("Holmes and Watson", "they") stand for several entities together, declared in the analyser
  (`plurals.py`: `library.json → plurals`, keyed by unit id, so a linked entity's declaration applies in all its books; one made on a
  group before you linked it counts as the linked entity's, and the checks go by group). Pages change a declaration by adding and removing
  members (`change_members`), so members a page doesn't show (other books, below the minimum) are kept. `.entities` gives
  the mentions to the plural group only. `Library.book` applies the declarations to each book (`BookData.set_members`: `Group.members`,
  `Group.member_of`; cheap, nothing is recounted). Whether the mentions also count for the members is the **plural setting**:
  `settings.plural` is the one switch for every page (the interface sends it as `plural` with each request, and a request may carry its own true/false), which `Context.view` passes to
  `View(lib, books, plural)`. It is set from the `[...]` menu's *Plural groups* row (`togglePlural` in core.js, via `/api/settings` `plural_default`) or the Settings page. With plural on, `Library.book(bid, True)` gives
  `BookData.plural_copy()`, made in memory from the parsed book and kept until the declarations or files change, which credits a plural mention to each member not named inside it (`credit`, `mention_groups`: mentions, forms, relations, co-occurrence), and
  a plural speaker or addressee stands for its members too (`stands_for`; dialogue records carry `speakers`, see `dialogue.speaker_units` /
  `said_by`). Off, every group has only its own. A plural group and its own members are never counted as appearing with each other
  (`BookData.plural_pair`: networks, "appears with"); the plural group always keeps its own profile. A target of several groups (a type, a gender,
  a book's people, a group you picked, a tag) can hold a plural group and its members, and a mention credited to more than one of them would be added
  up once for each. `View.overlap(members)` says which of those copies to leave out ({book: {coref: mention indexes}}: a mention is kept in the first
  group by number that holds it), and everything that adds up a target's mentions, findings or words uses it (`rel_counts`, `supersense_counts`,
  `prop_counts`, `mention_total`, the profile's forms and presence, `evidence`, `overbook._count`, `described.findings` and the Statistics mention
  variable), so each mention counts once whichever page is asked; a single entity keeps the mentions credited to it.
* **Narrator role**: `nar:<unit id>` (a character narrating) or `nar:anon:<book>` (an unnamed narrator). Roles are listed on the Entities page
  as type `NARR` and have their own profile; they are not units and never appear in `View.units`. A paragraph's role
  (`dialogue.narrator_of`) is, in order: a paragraph exception (`para_narrators`), else a chapter exception (`chapter_narrators`,
  found by `narrative.chapter_key_of` from any paragraph in it — always the book's real chapters at the default detection settings
  plus your chapter edits, `{"mode": "chapters"}`, regardless of what the current page happens to be showing, so "chapter" means one
  stable thing), else the book's own narrator, else anonymous. **Linking narrator roles** (`nl:<n>`, `library.json → narrator_links`,
  `Library.link_narrators` / `unlink_narrator` / `unlink_narrators_all`, mirroring `link`/`unlink` for persons but as its own store,
  since a role isn't `(book, coref)`-shaped and an anonymous one has no unit at all) pools two or more roles' narration into one —
  Watson narrating one book and Watson narrating another as a single voice, or two anonymous narrators, or a mix. Unlike linking
  entities, nothing else about them merges. `View.narrator_link_of` (a role id → its link id, built once per view) is substituted
  in inside `narrator_of`, so every other narrator function (`narrator_rows`, `narrator_profile`, `narrators`, `narration_recs`) only
  ever sees the already-canonical id. Unlinking down to one member dissolves the link and that member goes back to its own id.

### Workspaces

A **workspace** is one data folder, the unit you switch between (`core/workspaces.py`; no merging, no links across workspaces). The
**Default** workspace is the data folder itself (`alex-data`). Every workspace reads its own `books/` folder and the source folders it points
at. A workspace you **create** (`POST /api/workspaces`) gets a folder under `alex-data/workspaces/` and the source folders you give it; one you **import** from an
export zip gets a folder with a copy of the books in `books/` and no other source. Each workspace card has an **Open folder** button (its data folder). The list and the active workspace are in
`alex-data/workspaces.json`, so a separate data folder (`--data`, tests, experiments) never touches the real list. `app.py` opens the active
workspace at start (Default, with a note, if its folder has gone).

Switching (`POST /api/workspaces/activate`, `Context.switch`) re-opens the data folder **in place**: `Library.reopen` replaces the library's
state and annotations (reading both first, so a damaged file leaves the current workspace open and the error names the file), bumps
`version` (nothing cached for the old folder can be hit again) and stops a running `Library.warm`; `Context` drops its cached views and
remembered searches, and its reference-file folder and lexicon folder follow, so routes read `ctx.refs_dir` / `ctx.lexicon_dir` on every
request rather than keeping them. `topics.configure` points the topics store at the new folder. The browser reloads after a switch (`reloadPage()`). Each workspace has its own settings,
links, groups, collections, corrections, topic models, reference files, lexicon and parse cache. A request still running while you switch may
end with an error message (it was started on the other workspace); `test_switching_while_the_analyser_is_in_use` checks the analyser serves
the right workspace afterwards.

**In the browser.** The server writes the open workspace's id into the page it serves (`window.WORKSPACE`, in `index()` in `app.py`), so the
page always agrees with the server and no reload can loop. `core.js` keeps remembered settings (`localStorage`) per workspace: the Default
workspace keeps the plain key names (so what was saved before workspaces existed is still found), another gets `key@<id>`, and the theme is
shared (`storageKey`, `GLOBAL_KEYS`). The Workspace submenu of the top bar's `[...]` menu and the Library page's *Workspaces* section are in `static/js/workspaces.js`;
an import sends the zip as the raw request body (`api()` passes a `Blob` or `File` through unchanged). `alex --workspace NAME`
opens a workspace by id or name (`Workspaces.find`) and keeps it as the one opened next time.

**Deleting** (`Workspaces.delete`) removes a workspace's whole folder, including the books copied in by an import, and is guarded three ways:
only folders the analyser made (`owns`: inside `workspaces/`, after resolving links), never the active workspace or Default, and only when the
exact name of the workspace is typed. *Forget* just takes it off the list. Books in folders a workspace merely points at are never touched.

### The export zip

The Library page's *Export selected books (.zip)* button (`POST /api/export`, `core/export.py`) packs the selected books and your work on them:

```
manifest.json            format (export.FORMAT, now 1), when it was made, the export folder each book came from
books/<book>/<book>.*    the BookNLP files of the export in use: .tokens .entities .quotes .supersense .book .txt (those that exist)
state/library.json       library.json cut down to the selected books
state/annotations.json   annotations.json for the selected books
topics/<id>.json         topic models whose documents all come from the selected books
references/<id>.json     the keyword reference files (they belong to no book, so all of them)
```

`scoped_state` is a plain filter: nothing is renamed or merged, so an id in the zip means what it meant in the library. Details that matter:
`sources` and each book's `pinned` export are left out (the zip holds only the export in use); a linked person or narrator link keeps only its
members in the selected books and **stays even with one member left**, so ids that corrections refer to (`p:17`) stay valid (it goes only when
no member is left); tags, names, notes, saved groups, plural groups, rejected pairs and `plural_rejected` keep what touches a selected book
(a unit touches the books of its groups, a linked person those of all its members); a collection stays if it, or one inside it, holds a
selected book, and lists only the selected books; the `next_*` counters are kept. Lexicons are not included. The zip is written
to a temporary file (deleted after it is sent), so a large corpus never has to fit in memory twice. The zip can be unpacked and read with
the analyser as it is: `books/` is a source folder (`Library(sources=[…/books])`), or, unpacked as a data folder, its books folder.

## 4. How a request flows

0. `LocalOnly` (`localonly.py`) looks at every request first: wrong `Host`, or a change that names another `Origin`, is refused with 403 (section 12).
1. The browser (`static/js/*.js`) calls `api("/api/…", body)`; every analysis call carries `books` (the selected book ids).
2. A route in `api/` asks the shared `Context` for a **`View`** of those books. Views are cached (six at a time), keyed by the books,
   the library's `version` (bumped by every change to your settings, links or corrections) and each book's file signature,
   so a view is rebuilt exactly when something it depends on changed. `Context.signature(view)` is the same idea for results kept
   outside a view: a concordance search is kept (`Context.remember`, the last four) so that "Show more" pages through it without searching again.
3. The route calls a function in `core/` and returns its dict as JSON.
4. Errors: a `ValueError` (something the user asked can't be done) becomes `400 {"detail": message}`, a missing id or field
   `400`, a body that isn't a JSON object (or a missing query value) `400` too (`RequestValidationError`, so `detail` is always one line of text),
   `HTTPException` its own status, and anything else `500` with the exception's name, logged in the terminal.
   The browser shows `detail` as a message and replaces the "Loading…" line that was waiting for that request.
   A route reads what the browser sent through the helpers in `api/context.py` (section 12), so input of the wrong kind is a 400 and never reaches the analysis.

## 5. The analysis code (`core/`)

| Module | Job |
|---|---|
| `bookdata.py` | `BookData`: parses one book and builds its indexes: tokens, sentences and paragraphs, mentions, coreference `Group`s, quotes, supersenses, each group's grammatical relations (section 6), and the original `.txt` if there is one. `span_text` rebuilds text with marks, using the original text for exact spacing when available. To keep a book small in memory equal strings are shared (`shared`) and whole-number columns are arrays; a token's dependents are two flat arrays (`kid_start`, `kid_list`, read with `dependents(i)`); `BookData.cache(owner)` is where other modules keep what they derive from a book; `plural_copy` shares the tokens with the book and copies only the groups. `ekey` / `parse_ekey` build and read unit ids; `one_of(value, table)` asks "is this one of the names in the table?" without crashing on a list or object where a name was expected. |
| `library.py` | `Library`: the books on disk (`scan`, `book` with the cache), your book details, tags, links ("persons") and corrections; both JSON files. `scan` reads the data folder's `books/` (`books_dir`) and then the source folders. `reopen` switches it to another data folder in place (workspaces). `batch()` is a block of many changes that writes each file once at its end (auto-linking, resetting every link). Both files are checked as they are read (`statecheck.py`); what was left out is in `state_notes`. |
| `kept.py` | `Kept`: what is worked out from a book once and kept on it (`BookData.kept`): `get(key, make)` gives the result kept under the key or makes and keeps it; at most `entries` results, or results whose `cost` adds up to a `budget`, the least recently used dropped first; safe for several requests at once (a result is made outside the lock). |
| `statecheck.py` | Checks a workspace's `library.json` (`clean_state`) and `annotations.json` (`clean_annotations`) as they are read, so a part with the wrong shape (from an import made by another version, or a hand edit) can't break the pages: entries of the wrong shape are left out, what can be kept of a damaged one is kept, a whole part of the wrong shape starts empty; an entity stays in one linked person and a narrator role in one narrator link, every `next_…` number is above the ids in use; settings are laid over the defaults (`merge_settings`). Parts and settings it doesn't know are kept. Returns notes (one sentence per kind of thing left out) that the Library page shows. Nothing is written back. |
| `bookcache.py` | Saving and opening the parsed-book cache. It is a pickle, so `loads` accepts only the classes in `ALLOWED` (a parsed book's own) and refuses anything else, which `Library` treats as a damaged cache and rebuilds. |
| `bookcollections.py` | Collections of books: nested, a book may be in several (`create`, `update`, `delete`, `listing`). Named so as not to shadow Python's `collections`. |
| `export.py` | The export zip: `write_zip` writes the selected books' files and your state cut down to them (`scoped_state`, `scoped_annotations`), plus topic models and reference files (section 3). |
| `workspaces.py` | Workspaces: separate libraries (each one data folder) you switch between. `Workspaces` keeps the list and the active one in `workspaces.json`, and can `create`, `rename`, `activate`, `forget` (never deletes files) and `import_zip` (an export zip becomes a workspace with its own copy of the books). Wired to the web by `api/workspaces.py` (section 7); see "Workspaces" in section 3. |
| `folders.py` | `open_folder`: show a folder in Finder, Explorer or the desktop's file manager (`launch`, replaced in tests); a missing folder or no file browser is a `ValueError` naming the path. Used by `POST /api/folders/open`, which opens only folders the analyser knows. |
| `entitygroups.py` | Saved groups of entities (`create`, `update`, `delete`, `get`, `listing`). |
| `statsets.py` | Saved Statistics sets: a whole setup under a name (`create`, `update`, `delete`, `listing`), kept whole in the export zip. |
| `plurals.py` | Plural groups: declaring them (`set_members`, checked; `change_members` adds and removes, keeping the rest), what they mean in one book (`book_map`), suggestions from names (`suggestions`, `reject`). |
| `view.py` | `View`: the selected books combined. Applies your minimum-mentions rule, merges linked entities into units, and computes profiles (of one unit or of a group), distinctive words, group summaries, book-by-book tables and evidence sentences. `group_of` / `group_unit` / `target_unit` turn a request's `ids` or `group` into a virtual unit. `check_spec` is the one check every spec passes (`resolve`, `pool_unit`, `group_of`, `target_unit`): an object whose fields hold plain values where values go and lists where lists go, else a readable `ValueError`. `self.books` is ordered by publication year ascending (undated books last, by title), regardless of the order requested, so every "several books together" view (book by book, stylometry, arcs, network) is consistent; a unit's own `books` (`Unit.as_row`) follows the same order. |
| `stats.py` | Keyness and other statistics: log-likelihood, chi-squared, log ratio, %DIFF, odds ratio, `across` (chi-squared over several books), `trend` (Cochran–Armitage test for a rise or fall over ordered parts), `combine_trends` / `combine_across` (the trends and χ² of several independent texts as one), with their own p-values (no SciPy needed). For the Statistics tab: `correlate` (Pearson's r, Spearman's ρ, with p, N and a 95% interval; `centred` / `correlate_centred` the same for complete variables, prepared once), `adjust` (Bonferroni, Holm), `stars` and `describe` (N, mean, SD, variance, median, min, max, SE, interval of the mean), on top of `p_t` / `t_crit` (Student's t) and `betai` (the incomplete beta function). |
| `corpus.py` | Concordance (KWIC, with sort levels and a context search: `kwic_search` finds, filters and sorts the hits, `kwic_lines` makes the text of the lines shown, `kwic` does both), word lists (also word+POS+lemma), n-grams, collocates, keywords, reference files; the word-type filter (`token_test`, `filter_options`); `cindex`, the per-book lookup tables (with shared lower-case word and lemma tables), and `items_of`, what a token counts as in a list; the query language (simple and pattern), including batch queries (`Matcher`, below); `Scope`, the part of the text a tool may use; `clean_settings` turns a request's search settings into the dict the tools read (and refuses what isn't one). |
| `dialogue.py` | Per-book quote records, speech verbs and adverbs, vocatives, conversations, estimated addressees, speaking style, speaker/narrator tables; your corrections applied. Also narrators as entities: `narrator_rows`, `narrator_profile`. `word_choice` takes the word-choice figures (`core/wordchoice.py`) of any pairs of books and quotes, for the Speaking style table (`style_table`, `choice`), the voice comparison (`voice`) and the entity's Speech panel (`entity`: headline figures overall, of everyone, per book). `sentence_type` classifies a quote (or a narration paragraph) as a question, exclamation or statement, optionally weighing in its speech verb; `quotes`, `style_table`, `voice` and `entity` all take `types`/`weigh_verb` to filter or scope by it. |
| `overbook.py` | A target (entity, group, tag, gender…) over the slices of one book, the within-book counterpart of `View.by_book`: `slicing` (the shared Measure over slicer, at most 200 slices), `table` (per slice an overview, with `curve_rel` the relation whose words the curve offers when it isn't the tabled one: `curve_words`, shares only; the words of one relation and the kinds of action, with χ² and trend; `exclude` for the other side of a comparison), `report` (one or two targets in one book), `compare` (the Compare page's two sides: `report` if a book holds both, else `aligned`), `combined` (one target through all the selected books, every book weighing the same: see the methods paragraph; `table` is `_count` of the raw numbers and `_assemble` of the figures, `combined` counts each book and puts the counts together with `_series_books`), `aligned` (two targets, each in its own book, cut into the same number of equal slices so that slice k of n is the same relative stretch; `curve` is one figure of a table along its slices and `similarity` the Pearson and Spearman correlation of the two sides' curves for every figure; a figure is `ov:…`, `rel:…`, `word:<relation>:<word>`, `kind:…` or `snd:<figure>`). With `sound` (the workspace's sound settings) every one of these also measures the target's speech per slice (`_sound`: its quotes, whole spans, in the slice of their first token, through `prosody.tally`): each overview row gets `speech_words` and `snd` (the `prosody.FIGURES`, None where it says nothing); combined takes the books' mean. |
| `narrative.py` | Segments (slices by number or by words, or chapters, with your chapter edits: `book_segments`, `word_slices`, `edit_chapters`), arcs, style figures, stylometry (Delta, tree, PCA), sentiment (VADER), lexicon arcs (`lexicon_arc`). `all_segments` combines every selected book's segments in book order; with equal slices and `cfg["scope"] == "corpus"` it shares one total slice count across the books by their words, instead of giving each book the same count (the "Whole corpus" timeline). |
| `sound.py` | Pronunciation for sound and rhythm, from the CMU Pronouncing Dictionary (optional, `available`): `entries` reads it once; `pronounce` gives a word's `Pron` (phonemes, stress pattern "1"/"0" a syllable, source) from your correction, the dictionary (variants picked by word class, abbreviations, British spellings, hyphenated parts, plurals) or a guess (`guess_syllables`, also used for the Flesch scores); `book_prons` gives every token its pronunciation in context (one-syllable function words unstressed, contractions joined: the clitic gets `JOINED`), cached on the book per set of corrections (the corrections themselves are read once per set, `_read_corrections`, since every book of a request asks for them); `coverage` counts where a span's pronunciations came from; `parse_correction` reads a correction (a stress pattern or ARPAbet phonemes); `check_word` / `check_corrections` check them as they are saved (one word with letters; at most `MAX_CORRECTIONS`), `as_text` writes a pronunciation as you would type it. See MEASURES.md section 17. |
| `prosody.py` | Sound and rhythm figures over **units** (lists of token positions of one book; `sentence_units` makes them for a stretch): `tally` counts a book's units into an additive dict of raw counts (rhythm per phrase, cadences at phrase and sentence ends, sound and repetition runs followed by `_Runs` with a window, a boundary and the alliteration and repetition settings (each kind with its own count of words that could be in a run, `<kind>_eligible`), the sound profile, coverage; `keep_runs` also lists the runs found), `add` sums tallies, `figures` turns one into the figures of `FIGURES`; `cadence_of` / `cadence_type` read a cadence, `check_window` / `check_boundary` the run settings. `config` reads the workspace's sound settings (window, boundary, alliteration, repetition, corrections; `signature` is their key; `count` is `tally` under them), `span_tally` keeps a stretch's tally on the book per setting, `table` gives the figures per book or segment (the Style page), `is_figure` / `label` / `value` read one figure (also a single phoneme, `phone:S`). See MEASURES.md 17.2–17.7. |
| `soundtab.py` | The Sound and rhythm tab over a Corpus `Scope` (everything, narration, dialogue, one speaker's quotes): `units` cuts each sentence to its tokens in the scope, `tally_of` keeps a stretch's tally per scope and setting on the book (with positions: `prosody.tally`'s `keep`; about 40 bytes a token, so the most recently used are kept up to `KEPT_SPANS` times the book's length), `figures` (as `prosody.table` gives them, for the scope), `cadences` / `cadence_examples` (every pattern at phrase ends, the phrases ending with one), `runs` / `run_examples` (one kind's runs by what they share, the runs of one, longest first), `scan` (a chapter or slice word by word with stresses, runs and cadences, at most `MAX_SCAN_WORDS`), `guessed` (the words whose pronunciation is guessed, most frequent first, and your corrections with how often they are said), `lookup` (how one word is said now, with the dictionary's variants). Examples are `span_text` with marks `k` (the run or cadence) and `rep` (repeated words). |
| `wordchoice.py` | Word-choice figures: a **tally** counts token positions of one book into the words, each part of speech and the noun and verb supersense spans (`tally`, `add`, `empty`); `figures` / `value` turn one into the figures of `FIGURES`: part-of-speech shares (`pos:<POS>`), the ratios of `RATIOS` (adjectives, adverbs or nouns per verb, modifiers per head), the dynamic and static verb groups (`DYNAMIC`, `STATIC`), a share of the verbs or nouns per supersense (`verb:<name>`, `noun:<name>`) and supersenses per 1,000 words (`ss:<category>`). `SECTIONS` groups the figures as the Statistics page offers them; `HEADLINE`, `CHOICES`, `choices` and `columns` say what a table of speakers or books shows; `span_tally` keeps a stretch's tally on the book and `table` gives the figures per book, chapter or slice (the Style page). Meant for any sample (a book, a segment, a speaker's quotes); MEASURES.md section 18 (to be written with the pages that use it). |
| `narrators.py` | Suggests each book's narrator and stretches narrated by someone else, from the "I" outside quotes. |
| `described.py` | "Described as": what a target is described and called as, and by whom (section 6). `findings` lists the things said about a target, `Describers.of` traces a mention to its speaker or narrator, `table` splits the findings into columns with counts, shares, rates per 1,000 words and keyness. |
| `cases.py` | The cases of the Statistics tab, one row of its data each: text pieces (chapters, slices or books, in a Corpus scope) or participants (entities, with a sample: their speech, their speech and narration, the sentences mentioning them, or their Described-as findings). `build` makes a `Cases`; `Cases.at(b)` is the lookup from a token to the cases whose sample holds it (section 6). `Cases.left_out` lists the cases dropped for a small or empty sample. A `Cases` keeps what its layers count once for all its variables: `layer_units`, `topic_words` and `sound` (each case's sound tally, per sound setting). |
| `rexport.py` | The R export of the Statistics tab: `files` measures the page's variables in its cases and returns `cases.csv` (wide), `cases_long.csv`, `variables.csv`, `dropped.csv`, `README.txt`, `load.R` and optionally `analysis_example.R`; `write_zip` zips them. A variable that counts something has a raw count column `<name>_n` and a rate `<name>` whatever its measure; column names are slugs of the labels (`slug`, `column_names`). |
| `statstab.py` | The Statistics tab: `run` builds the cases and measures the variables, then the correlation table (`correlations`: a matrix of one list or a grid of two, with corrected p-values) and the descriptives (`descriptives`, split by gender, tag, saved group or book). |
| `lexicons.py` | Your word lexicons: one `<id>.json` each in the lexicon folder (`{name, cats}`; the id comes from the name and never changes, so renaming keeps saved Statistics sets working). `stored` reads them all (what Statistics and the arcs use), `listing` describes them for the page (also files that can't be read: `problem`); `parse` reads a file's text (plain, .csv or .tsv: tabs, commas or semicolons with CSV quoting; a word list, a word and a category per row optionally with 0/1, or a column per category, judged from its shape by `_is_wide`; a header row is skipped); `create`, `replace`, `rename`, `remove`, `save_category`, `delete_category` change them and check limits (50 lexicons, 200 categories, 500,000 words). The emotion lexicon (`EMOTION`, id `emotion`) is special: always headed "Emotion", not renamable, its id reserved. |
| `layers.py` | The linguistic layers as Statistics variables: supersense spans, relation findings of a target, words of a lexicon category (`counts`), quotes of a sentence type (`quote_counts`, `typed_quotes`), sentiment of the sample's units, style figures, word-choice figures (`word_choice`, through `wordchoice`: each case's tally is worked out once and every figure of it kept on `Cases.word_choice`), sound and rhythm figures (`sound`, through `prosody`) and topics (`values`, `topic`); `units` splits each case's sample into sentences, quotes or paragraphs' narration; `options` lists what the page can offer. |
| `variables.py` | The variables of the Statistics tab: what is measured in each case. `check` reads a variable spec (query, mentions, speech or attribute), `values` measures one over the cases (per 1,000 words, count or present; a variable that doesn't fit the cases gets a note instead of values), `table` measures a list; `top_words` (optionally only words inside quotes of a sentence type, or only speech verbs), `top_entities`, `top_speakers` (the speakers with the most words, as speech variables) and `attribute_values` make lists of variables for the bulk-add buttons. |
| `network.py` | Entity networks (networkx), measures, layout, GEXF/GraphML export. A network keeps the `max_nodes` (300; at most 1,000) entities with the strongest links and says how many there were (`G.graph["total_nodes"]`). |
| `links.py` | Suggests entities of different books of the same series that may be the same (`suggest`), and `auto_link`, which links exact name/type/pronoun matches of different books across the whole library outright. `unit_name` names a unit without a `View`. Both start from `_units`, one summary per entity of the whole library, which is kept on the `Library` until something it depends on changes. |
| `reader.py` | The text view: one segment as paragraphs (with their numbers) with marks for entities, quotes, narrators, events, supersenses, sentence numbers, topics and sound (`_sound_marks`: one mark per word with a pronunciation, `sw` with its stresses as data, `sr sk<n>` in a run of the chosen kind with n its shared sound in `sound_layer.keys`, `srep` a repetition, `sg` guessed, `c<cursus>` the last word of a cursus cadence; single-word marks, so they always nest inside the others; from `soundtab.tally_of` of the segment). |
| `topics/` | Topic modelling (below). |

**`core/topics/`**: `model.py` (settings, documents, words, NMF/LDA fit, quality figures, `build`), `store.py` (models on disk),
`page.py` (model overview; `Topic`; the parts of a topic's page), `compare.py` (map, side by side, grids), `uses.py` (topics in Arcs,
on entity pages and in the text view), `notes.py` (explanatory texts), `errors.py` (`TopicError`).

Layers of memory: a parsed book lives in the library (and the pickle cache); per-book lookup tables (`cindex`, dialogue records,
quote keys, style figures, sentence sentiment, pronunciations, sound tallies) are built on first use and kept on the `BookData`
(`BookData.kept(owner, …)`, a `kept.Kept` per owner: results by key, the least recently used dropped past a number of entries or a size
budget; they are never saved with the book or copied into its plural copy). Each owner's limit:

| Owner | Kept | Limit |
|---|---|---|
| `index` (`corpus.cindex`), `keys` (`dialogue.keys`), `sentiment` | the book's lookup tables, quote and paragraph keys, VADER score of every sentence | 1 |
| `narration`, `chapter keys` | narration records, chapter of each paragraph (per set of narrator and chapter corrections) | 1 |
| `dialogue` (`dialogue.book_dialogue`) | quote records and conversations, per gap, corrections and speech-verb settings | 3 |
| `sound` (`sound.book_prons`) | every token's pronunciation, per set of pronunciation corrections | 4 |
| `style`, `prosody` | style figures and sound tallies of a stretch (a book, a chapter or slice), per setting | 500 |
| `soundtab` (`soundtab.tally_of`) | sound tallies with every run's and cadence's position (about 40 bytes a token), per stretch, scope and setting | `KEPT_SPANS` (4) times the book's length in tokens |
 a `View` is cached by the API context (six at a time;
a view itself is light, it points into the books). At start-up `Library.warm` reads every book in the background so that the first page
doesn't wait for them.

## 6. Definitions and methods

**Mentions and entities.** BookNLP groups mentions of the same thing into a coreference group. A group's *type* is its most
common category. It is *counted* if it reaches your minimum for that type, in each book separately or across the selected
books combined (`count_mode`). Linked groups form one unit; its name is the one you gave, else the most frequent name. Any
unit — linked or not — can be renamed and given a short description from its profile (`Library.name_of`/`set_name`,
`note_of`/`set_note`; `/api/name`, `/api/note`); a linked person's live in `persons[pid]`, a single entity's in
`entity_names`/`entity_notes`, keyed like `entity_tags`. Linking or unlinking carries a plain entity's name, note and tags
along with it the same way (`Library.link`/`unlink`).

**Minimum word frequency.** Each tool that has a *Minimum frequency* keeps its own number; *how* it is counted is one setting of the workspace, Settings → Words (`settings.freq_mode`, `Context.each_book()` in `api/context.py`; the server reads it on every request, so no page sends it). `combined` (the default, and what every tool did before the setting) checks a word over all the selected books together. `per_book` lets a book count for a word only if the word reaches the minimum *in that book*, as for mentions: the Corpus word list, n-grams and collocates list a word that reaches it in some book (`corpus.books_reaching`; their figures stay whole), Book by book (`View.by_book`) tests it across the books that reach it, which must be at least two (the others' residuals are None), and Over the book with all books combined (`overbook._series_books`) tests and combines the books that reach it. A *minimum range* then counts those books, not the books where the word merely occurs (`stats.passes` holds the rule; the *Range* column still shows the books where it occurs). Not affected: the keyness comparisons (distinctive words, keywords, speech verbs: a target against a reference, pooled), and Over the book in one book or two books aligned (one book per side). The summaries of By book and Over the book carry `each_book` so the page says which way it counted (`needed()` in core.js), and `freqLine()` shows the setting as a "Based on" line (see below) beside the minimum in the tools it applies to.

**Relations** (`BookData._relations`), from the dependency parse, per mention head: subject of a verb → *agent*; object,
indirect object or passive subject → *patient*; possessor → *poss*; adjective modifier, apposition or complement of "to be" →
*mod*; object of a preposition → *prep* ("went to"). Extensions to BookNLP's rules: a conjoined mention takes the first
conjunct's role, a subject is also the agent of verbs coordinated with its verb, and *prep* is recorded for every type. Each
finding keeps the tokens to highlight, which is where "click a row for the sentences" comes from. A finding also has a place in the text: `Group.rel_ev` holds (word, mention index, tokens) for it, and for the verb relations (agent, patient) the last
token is the verb, so its supersense (`BookData.ss`) is the one `rel_ss` counted; a count can therefore be cut at any token, such as per slice of a book.

**Keyness** (`stats.compare`): for an item with counts *a* (target) and *b* (reference) in texts of size *c* and *d*, log-likelihood
G² = 2(a·ln(a/E₁) + b·ln(b/E₂)) with E from the pooled rate (Rayson & Garside 2000), chi-squared for the 2×2 table, log ratio,
%DIFF and odds ratio; p from chi-squared with 1 degree of freedom. `across` tests one item over several books. Bonferroni divides
the level by the number of items tested.

**Over the book** (`overbook.table`). The book is cut by the shared Measure over slicer (`narrative.book_segments`, so equal slices by number or words, or chapters
with your edits; at most 200 slices). A mention, and each finding of it (`Group.rel_ev`; a kind of action is the supersense of the verb it highlights), belongs to the slice
that holds the mention's first token. Per slice: the words, mentions, mentions per 1,000 words, the shares of names, descriptions and pronouns and each relation
per 100 mentions; for the chosen relation each word's count and its **share of that slice's list** (None where the list is empty), and the same for
the kinds of action of the verbs the target is the subject of. Each word and kind gets `across`'s χ², p, Cramér's V and residuals (the slices in place of
books) and a **trend**: `stats.trend`, the Cochran–Armitage test of the word's counts against the slice sizes with the slice position as score (z is positive
when the share rises, its p is what the table calls significant). It uses the counts and the slice sizes, so a rare word that happens to lean late is not made to look
like a strong trend (a correlation of the shares against the slice position would treat every slice as a case whatever its size). Words under the minimum frequency are listed without tests, as in Book by book (the Words setting does not change this within one book). Both tests assume enough
expected occurrences in each slice; with many slices and few occurrences they are only a guide, so raise the minimum frequency before reading much into them.

**All the books together** (`overbook.combined`). One target through every selected book that holds it, each book cut into the same number of equal slices (as in
Two books aligned, so slice k of n is the same relative stretch of each) and **every book weighing the same**, whatever its length. For slice k the counts (mentions,
words, findings, and each word's or kind's count) are added over the books, and a figure that is a share or a rate (mentions per 1,000 words, names, descriptions and pronouns,
each relation per 100 mentions, a word's share of the slice's list) is the **mean of the books' own** values, a book with nothing to take it of in that slice
being left out of the mean (a book where the word is not in the slice's list counts as 0%). The tests are made in each book and then combined: `stats.combine_trends` adds the books' Cochran–Armitage z with
equal weight and divides by √(books used) (Stouffer), so books that agree make a surer trend and books that disagree cancel out, and also counts the books that rise
and fall (`trend`: z, p, n books, up, down); `stats.combine_across` adds the books' χ² and degrees of freedom (no V or residuals). A book where the word is absent or
constant (its own trend has no z) is left out of both. χ² asks whether the share varies between slices within the books, not whether the books agree. The minimum frequency
counts the word over all books together (or, with the Words setting `per_book`, in each book: see *Minimum word frequency* in section 6), and `min_range` is the fewest books it must occur in to be tested (both below: listed without tests). With a `measure` the answer also holds each book's own values of that figure (`per_book`) for drawing beside the combined ones.

**Correlations and descriptives** (`stats.correlate`, `stats.describe`). A variable is a list of numbers, one per case, None where it has no value. `correlate` leaves out a case missing either value (pairwise deletion), then computes Pearson's r, or Spearman's ρ as Pearson's r of the ranks (ties get their average rank). Both get a two-tailed p from t = r·√((n−2)/(1−r²)) with n−2 degrees of freedom (what SciPy reports for both), through the regularised incomplete beta function (`betai`, Numerical Recipes). The 95% interval comes from Fisher's z, with standard error 1/√(n−3) for r and √(1.06/(n−3)) for ρ (Fieller, Hartley & Pearson 1957). Below 3 cases, or when a variable doesn't vary, there is no coefficient; the interval needs 4. `adjust` corrects a list of p-values: Bonferroni multiplies by the number of tests, Holm (1979) multiplies the k-th smallest by (tests − k + 1) and keeps the order. `describe` uses the sample SD and variance (n − 1) and a t-based interval of the mean. `tests/test_stats.py` checks all of it against SciPy.

**Cases** (`cases.build`). The Statistics tab measures every variable in each case's *sample*. A text piece's sample is its words in the chosen scope (`corpus.Scope`); pieces are equal slices (the default: `n` per book through `narrative.book_segments`, or with `slice_by` "words" one every `words` words, `narrative.word_slices`, which has no 200-slice limit and lets a rest under half a slice join the last one), BookNLP sentences (labelled with their first words; minimum sample 1 word by default), chapters (`narrative.book_segments` with your edits), or whole books. A participant is a unit of the chosen population (any spec `View.resolve` takes; default every person above your minimum). Their sample is *speech* (the words of every quote they count as speaker of, plural speakers' members included when plural groups count for them), *speech and narration* (plus the narration of every paragraph whose narrator is their character, `role_unit`; a narrator role that is no one character is a participant of its own, unless `narrators` is off), *sentences* (every sentence holding one of their mentions, whoever says it; sentences shared by two participants count for both) or *findings* (their Described-as findings of every kind, counted in findings, not words). A case with an empty sample or one below the minimum (default 100 words or 10 findings) is dropped, and the count of those is reported (`Cases.left_out` says which, for the R export). Participants who are in fewer of the selected books than `min_range` (default 1) are dropped too, counted over all the view's books, not only the ones a split by book measures. `Cases.at(b)` answers, for a token of book b, the cases whose sample holds it (an array per book for pieces, quote and paragraph tables for speech, a sentence table for sentences), so a variable is counted with one pass over its hits.

**Variables** (`variables.py`). A *query* variable counts the hits of a Corpus query (simple or pattern, word or lemma, batch lines) with `corpus.Matcher`, without the Corpus page's 20,000-hit limit; a hit belongs to the case whose sample holds its first token (`Cases.at`), and a candidate in no case's sample is turned down before it can block the text it covers (the `accept` of `Matcher.hits`). A *mentions* variable counts the mentions of a spec's entities (all, or only names, descriptions or pronouns) where they start, a participant's mentions of themselves included. A *spoken* ("Speech of …") variable counts the words a spec's entities speak, each where it lies, or their quotes, each where its first word lies (`unit`), optionally only quotes of one sentence type (`type`, `weigh`; `layers.typed_quotes`); a quote counts once when said through several of the spec's members (`dialogue.said_by`), and its quotes may also be a % of all the sample's quotes. In the findings sample a query is matched against each finding's word, one word per line (patterns and phrases get a note), optionally only findings of one kind; mentions and speech don't apply there. Counts become values per 1,000 words of the case's sample (per 100 findings, "% of findings", in the findings sample), stay counts, or become 1/0 for present/absent. *Attributes* are values of the case itself: for participants `in` (1 when the participant is one of a spec's entities: a gender, a tag, a saved group), mentions, words spoken, quotes and books (None for a narrator role that is no entity); for pieces their number in the book, position (%) and length. A variable that doesn't fit the cases (a piece attribute for participants) gets all-None values and a `note`, so a saved set still runs.

**Layers** (`layers.py`). A sample's *units* are what it is made of: BookNLP sentences for text pieces and for "sentences mentioning them" (a sentence cut by a piece's edge or its scope is the part inside), each quote for speech (its own tokens), each paragraph's narration (the tokens outside quotes) for narration. *Sentiment* is VADER's compound score per unit (a whole sentence's comes from `narrative.sentence_scores`, the cache the sentiment page uses; other units are scored on their own text), averaged, or the share of units at or above +0.05 / at or below −0.05. *Style* figures are those of `narrative.style_metrics`, over the sample's words (word length, MATTR, hapaxes, lexical density, passives per 1,000) and units (words per unit, % of units with ? or !); for a whole book they equal the Style page's. *Sound and rhythm* figures (`layers.sound`) are those of `prosody.figures`, or one phoneme per 1,000 words (`phone:S`), over the sample's units under the workspace's sound settings: each case's units are tallied book by book with `prosody.tally` and the tallies added, once per `Cases` and setting (kept in `Cases.sound`), so a table of thirty sound variables counts the text once; for a whole book they equal the Style page's. Without the pronunciation dictionary they say so in their note. *Speech sentence type* variables count quotes of one `dialogue.sentence_type` (question, exclamation, statement; `weigh` lets the speech verb decide too, as on the Dialogue tabs) where the quote's first word lies in a case's sample (`layers.quote_counts`), so a quote said by two participants counts for both; they need quotes in the sample (any text piece, or a participant's speech with or without narration) and say so in their note otherwise, and the measure "% of quotes" (`pct`, for this kind only) divides by all the sample's quotes. *Supersenses* count spans (consecutive tokens with the same supersense count once) where they start; *relations* count `described.findings` of one relation of a target (default every entity), optionally one word, where the mention starts; *lexicon* variables count words of a lexicon category by form, else lemma; every `<id>.json` in the lexicon folder is a lexicon (`narrative.lexicons`; today the emotion lexicon, `emotion.json`, and any lexicon stored there later), so a new kind of lexicon needs no change here. A *topic* variable is one topic of a stored model (`topics.page.Topic`, its books checked as the Arcs topic lines check them): each word of the sample that lies in a model document takes that document's weight for the topic, and the value is their mean in %; the words of each case per document are counted once per model (`Cases._topic_words`). Cases from books the model wasn't fitted on get no value, and the variable's note says how many. None of them apply to the findings sample; sentiment needs vaderSentiment, a lexicon variable a stored lexicon and a topic a stored model fitted on some of the selected books, and each says so in its note instead of failing.

**The Statistics tab** (`statstab.run`). One list of variables gives a correlation matrix (each pair once, below the diagonal), two lists a grid (rows against columns). Variables without a missing value are prepared once (`stats.centred`: values or ranks minus their mean) so each pair is one sum of products (`stats.correlate_centred`, the same figures as `correlate`); with thousands of sentences this keeps a 30-variable matrix to about a second. The correction counts every p-value in the table (cells whose variable has no values aren't tests). Descriptives are given for all cases and, with a split, per group: participants by gender (`View.gender_of`; a narrator role or a non-person is "Not a person"), tag, saved group (in every group they belong to, the rest in "(no tag)" / "(in no saved group)") or book; pieces only by book. Split by book, participants are built and measured again per book (`cases.build(..., books=[b])`), so a person's value in a book is from that book alone and the minimum sample applies there too. Saved sets (`statsets.py`) store the setup as sent and travel in the export zip whole.

**Dialogue** (`dialogue.py`). Each quote becomes a record. The *speech verb* is the verb the attributing mention is the subject of, else
the nearest speech verb within 8 tokens; either way it must be a speech verb (`SPEECH_VERBS` or the communication supersense) in the narration, outside every quote, so a verb like
"rose" is passed over, and a lemma in the workspace's `speech_skip` (Speech verbs tab, *Leave out verbs and adverbs*) is never one. Adverbs
skip `STOP_ADV` (time, place, degree) and `speech_skip`'s adverbs. A verb token introduces one quote only (`_claim_verbs`: *subject* before *near*, then closer, then earlier); adverbs must be outside every quote. `book_dialogue` caches per (gap, corrections, skip). *Vocatives* are people named as a form of address inside the quote. *Conversations* are runs of
quotes with at most `conv_gap` narration words between them (unless you split or join). *Addressees* are estimated in this order: a
named person, the previous speaker, the same person as before, the next speaker (for an opening line); your corrections replace the
estimate. MATTR is the moving-average type–token ratio over 100-word windows. *Sentence type* (`dialogue.sentence_type`) is question,
exclaim or statement, from the record's own `?`/`!` (also true for a narration paragraph: see `narration_recs`); with `weigh_verb`, a
speech verb in `QUESTION_VERBS`/`EXCLAIM_VERBS` (asked, exclaimed…) decides it instead when the record's own punctuation doesn't already.
`book_dialogue`'s "time" (the whole book's dialogue-share curve, 50 slices) exposes its per-slice word count as `bins_w` alongside the
ratio itself, so `scoped_time(view, pairs)` can reuse the exact same denominator for one scope's own curve — the given pairs' own words,
sliced the same way, as a share of each slice's total words — rather than recomputing it from scratch or (wrongly) reusing `bdlg`'s
dialogue-word bins as the denominator, which would be everyone's dialogue, not the whole slice.

**Segments** (`narrative.segments`): equal slices by token count, or (`slice_by` "words") one slice every `words` words (`narrative.word_slices`, the same cut Statistics uses: a rest under half a slice joins the last one; with it the corpus timeline's shared slice count does not apply, and a book without chapters is cut the same way), or chapters found from heading paragraphs (12 words or fewer, starting
with a heading word or numeral, optionally in capitals or without closing punctuation); a heading too close to the previous one is ignored;
fewer than two headings falls back to slices. The text view shows a paragraph in the segment where it *starts*. Across several books
(`narrative.all_segments`), the Arcs, Sentiment and Lexicons pages offer two timelines: "Book by book" (each book's own slices or chapters, plotted as its own line) and
"Whole corpus" (one continuous line over every selected book; with equal slices, the slice count is shared across the books by their words, so a
short book gets fewer than a long one, rather than the same count each).
**Your chapter edits** (`narrative.edit_chapters`, stored per book in `annotations.json`) sit on top of the automatic chapters: the found
headings minus those you removed, plus paragraphs you made chapter starts, with the titles you gave; the text before the first start becomes an
"Opening". With edits a book needs only one start to be split into chapters, and the minimum-length rule no longer drops your starts. Edits name
paragraphs by their opening words. Every place that uses chapters (Style, Arcs, topic documents, the text view) goes through `book_segments`,
so they all see your chapters.

**Stylometry**: z-scores of the most frequent words' relative frequencies; Burrows' Delta, Cosine Delta or Euclidean distance;
average/complete/Ward linkage; a principal-component map. At most 400 texts.

**Topics** (`core/topics`). 1) *Documents*: chunks of about N words ending at sentence boundaries, groups of paragraphs, chapters or
slices, or whole books. 2) *Words*: the chosen parts of speech, as lemmas or forms; tokens inside proper-name (or person, or any entity)
mentions are dropped using BookNLP's mentions; general words and your own stop-words are removed; words in too few or too many
documents are removed. 3) *Fit*: NMF on tf–idf (default; random start with a fixed seed) or batch LDA. 4) *Quality*: NPMI coherence of
each topic's ten top words over documents, diversity of top words, and *stability*: re-fit with other seeds and count how often each topic
returns (a re-run's matched topic shares at least 40% of its top 20 words). 5) *Topic page*: relevance ranking of words
(Sievert & Shirley 2014), where the topic occurs, its strongest passages, and *association*: each document counts as topic text to the
extent of its share, and an entity's (or speaker's) rate per 1,000 words in topic text is compared with its rate elsewhere with a
log-likelihood. That ranks; it is not a significance test, because the weights are not independent observations. Book and group
comparisons use Mann–Whitney U on documents. 6) *Compare*: similarity by shared words (cosine) or appearing together (correlation of
document shares), classical multidimensional scaling for the map, average-linkage tree.
The one function that decides which words a model counts is `model.kept_tokens`; passages and the text view use it too, so a
highlighted word is always a counted word.

**Groups and narrators as entities.** A group counts several entities as one: its members are all their coreference groups, so mentions,
forms, relations, supersenses and presence add up. A sentence counts once for a group however many of its entities it holds (co-occurrence,
"appears with"), members are never counted as outsiders (who names the group in dialogue, who it talks to), and the Speech section adds the
quotes between members. Groups of mixed types have no "share of type". A narrator role has no mentions or relations: its profile (`dialogue.narrator_profile`)
is the words outside quotes that belong to it, with style figures against all narration and against the same character's dialogue, a row per book, and
vocabulary distinctive of its narration (`dialogue.voice` with a narration target).

**Described as** (`described.py`). A *finding* is one thing said about the target at one of its mentions: a relation (modifier, action, done-to, possession,
preposition: the same findings, with the same evidence, as the profile's tables) or a way it is *called* (the text of a name, a description or a
pronoun mention). Each finding is traced to its **describer** from the mention's first token: inside a quote it is the quote's speaker
(`dialogue.unit_of`; `stands_for` when plural groups count for their members; `NO_DESCRIBER` for an unattributed quote), anywhere else the narrator of
the paragraph (`dialogue.narrator_of`, so your narrator and chapter corrections apply). A narrator who is a character is that character's unit
(`role_unit`), so a character's speech and narration are one describer; an unnamed or linked narrator stays a role. `table` then puts each
finding in the column(s) its describer belongs to for the chosen `split` (the describer, the describer's BookNLP gender, tag, the book, or narration
vs speech; a finding counts once per column), keeps the `top` columns with most findings and gathers the rest in "All others". Per cell: the
count; its share of the column's findings of this kind; its rate per 1,000 words the column's describers produce (`_sources`: every quote and
every paragraph's narration in the books the target appears in); and keyness, the signed log-likelihood (`stats.compare`) of the word in the column
against all other displayed columns together. Keyness ranks, it does not test: findings are not independent observations.
**Columns you pick** (`split: "custom"`, `described.picks`). Each column is a spec (anything `View.resolve` takes: entity, group, tag, gender) and a describer is in it when its unit is one of the spec's members (`_is_in`; a single uncounted entity is matched by its id). Several columns can hold the same describer (Watson, and "all men", and "everyone in the first book"): a finding is counted once in each column it is in, as with tags. `_layout` shows every picked column, in your order, with or without findings (`top` doesn't apply, and there is no "All others"); findings in none of them are only in the All column, and keyness compares the picked columns with each other. The sentences behind a cell use the same `columns`.

**The sentences behind a cell** (`described.evidence`, `/api/described/evidence`) are listed from the same two functions the table is counted from, so a click shows exactly as many sentences as the cell says. `_classify` lists every finding with its describers and raw columns, `_layout` decides which columns are shown (the `top` with most findings; the rest become "All others"), and `_shown` maps a finding's columns to the shown ones *once*: a finding whose describer has two tags, or several describers in the tail, is one finding in "All others", not two. `table` counts and `evidence` filters those; the evidence request therefore carries the same `kind`, `split`, `voice` and `top` as the table. `test_the_sentences_behind_a_cell_are_exactly_its_count` checks every cell of tables of every kind of split, tag split with two tags included. The drawer is `openEvidence` (core.js) with the route as its optional `path`; a sentence that has `by` shows who said it ("Watson (narration)", "Holmes (speech)").

**Word-type filters** (`corpus.token_test`): a filter is `{pos, tag, ent}`; a token passes when it matches one value of every non-empty list
(POS: BookNLP's universal tags, tag: fine tags, ent: the category of a mention covering the token). In a word list only passing tokens are counted while
the total, per-1,000 rates and the tenths used for dispersion still refer to all words in scope. In collocates the filter only decides which collocates
are listed: windows and hit counts are unchanged, and a collocate's corpus frequency counts only its passing tokens.

**Concordance sorting and context search** (`corpus.kwic`): up to three sort levels, each a position (the hit, one of five words left or right,
the book) and a `by` (word, lemma, POS, fine tag, or frequency of that word among the hits), optionally reversed; each level is one stable sort applied
from the least to the most important, ties keep the order of the text. The context search (`_ctx_test`) runs a second query (simple or pattern) over the
book (all its matches, however many) and keeps the hits with a match wholly inside their window (left/right words, not counting the hit; stopping at the
scope's edge and, if chosen, the sentence's), or, inverted, those without. **Limits apply last**: the scope, the near-word filter and the context
search reach `Matcher.hits` as its `accept` function, so a candidate they turn down is neither counted towards the 20,000-hit limit nor blocks
the text it covers; searching a common word in dialogue only therefore still reaches the later books. A pattern starts only where it can match: up to as many positions before a token its first required
part accepts as the optional parts before that part can cover (`[]? []? "zzz"` tries only the places near a "zzz"). A pattern with repeated parts (`[]* []*
"x"`) remembers the outcome of each (line, item, position) it has tried, which cannot change, so it costs no more than its length times the
repeat limit (without that, a few `[]*` could take minutes). The search and the lines are made apart (`kwic_search`, `kwic_lines`) so a page of
500 lines only builds those 500; the plot gets 200 counts per book (`bins`), not a position per hit.

**Networks** (`network.py`). Nodes are the units of the chosen types; an edge counts shared sentences or paragraphs, a speaker mentioning
someone in a quote, or a speaker talking to someone (directed). Entities in fewer than `min_range` of the books are not nodes at all, and edges found in fewer than `min_link_range` books go (`build` notes the books each link was found in; `addressee_edges` fills them for "talks to"). Edges below the minimum strength go, then unlinked nodes (unless shown), then,
if more than `max_nodes` remain, all but the strongest (the greatest sum of edge weights, then the most mentions); measures and layout are of
what is left. Without that cut a network of a whole library (thousands of people) took a minute to build and was unreadable.

**Batch queries** (`corpus.Matcher`): a query string may hold several complete queries, one per line ("say", "ask" and "shout" each on their own line,
or a pattern per line), each parsed independently. `Matcher.hits` tries every line's parsed items at each candidate position, in the order given, and
takes the first that matches, so the lines behave as alternatives (unlike `a|b` inside one simple word, a batch line can be a whole multi-token pattern).
Each hit carries the line that matched it (`"matched"` in `kwic`'s output; `collocates` just pools every line's hits). `kwic`'s result also carries
`"batch"` (more than one line), which the browser uses to decide whether to offer the "Matched" column at all.

**Link suggestions** (`links.suggest`) are only made between books that share a series (compared case-insensitively; books without a series get none).
Candidates come from names that share a word or a three-letter start (no group of more than 400 is compared with itself, so a name like
"Holmes" in sixty books is still tried: 60 entities), and the per-entity summaries they are made from are kept (`links._units`) until your
settings, links or the books change.
**Auto-link** (`links.auto_link`, the "Auto-link exact matches" button) instead links outright, across the whole library, whenever two entities of different books agree
exactly on name (titles set aside), type, and — the safeguard against merging two different same-named people — BookNLP's pronouns; an entity with
no pronoun evidence (almost everything that isn't a person) is never auto-linked this way, and a pair you've rejected never is either. It's an
ordinary link once made, so it shows on the Links page and undoes like any other. Two entities of one book are never auto-linked with each
other (BookNLP keeping them apart is a reason to look, not to merge): of those, the most mentioned joins the person. All the links are written
to `library.json` once (`Library.batch`).

**Marks in text.** Anywhere the server returns text with highlighting, it uses control characters instead of HTML:
`\x01class|data\x02 … \x03` (see `BookData.span_text`); `markup()` in `core.js` turns them into `<mark>` elements (sentence numbers are marks `sn|<n>`
shown with CSS). Text is never
inserted as HTML, and the browser code has no way to set `innerHTML`.

## 7. The web API

All routes take and return JSON (`POST` unless noted). Bodies carry `books` (selected book ids) wherever a route analyses text.
Generated from the running application:

| Method | Path | What it does |
|---|---|---|
| GET | `/` | The page itself. |
| POST | `/api/annot/addressees` | Set a quote's addressees (["*"] = everyone present), or clear your correction (null). |
| POST | `/api/annot/chapter_narrator` | Assign a narrator to a whole chapter (found from any paragraph in it), or, with no `pid`, the Opening. |
| POST | `/api/annot/conversation` | Start a new conversation at a quote ("split"), join it to the previous one ("merge"), or undo either. |
| POST | `/api/annot/narrator` | Set (or clear) a book's narrator. |
| GET | `/api/annot/narrator_options` | People and things that can be a book's narrator (its PER and VAR entities). Made from a view of that book alone, outside the view cache. |
| POST | `/api/annot/paragraphs` | Give paragraphs to a narrator other than the book's (or, with no narrator, take the exception away). |
| POST | `/api/annot/participants` | Add a listener to a conversation, remove a participant, or put one back. |
| POST | `/api/annot/quote` | Everything the quote editor shows: speaker, addressees (yours or estimated), conversation and its participants. |
| POST | `/api/books/{bid}` | Change a book's title, author, year, series, tags or pinned export. |
| GET | `/api/books/{bid}/text` | The original `.txt` the book was exported from, for download; 404 if none was found. |
| POST | `/api/bybook` | How a target's figures and words change from book to book. |
| POST | `/api/overbook` | A `target` (and optionally `other`, compared as in Compare) slice by slice through one `book` (and `curve_rel`, the relation whose words the curve offers, default `rel`; all three overbook routes take it) (a preference: if neither target is in it, or none is given, the first book both are in, else the first either is in; `book` in the answer is the one used), cut as `seg` says (the shared Measure over setting; 400 above 200 slices), for the relation `rel`, with the shared statistics options (`min_freq`, `alpha`, `bonferroni`). `{books: [{id, title}] the target is in, book, a, b}`; a and b (null without `other`) are `overbook.table`s: `segments`, `overview` (a row per slice), `rows` (a row per word: `counts`, `pcts`, χ², `trend`) and `supersenses`. All null when neither target is in the selection. `sound`: true (on all four overbook routes) adds the sound and rhythm of the targets' speech per slice to each overview row (`speech_words`, `snd`), under the workspace's sound settings; 400 without the pronunciation dictionary. |
| POST | `/api/collections` | Make a collection, at the top level or inside another. |
| POST | `/api/collections/delete` | Remove a collection (its books stay; its sub-collections move up). |
| POST | `/api/collections/{cid}` | Rename a collection, move it, or add and remove its books. |
| POST | `/api/compare` | Two entities or groups side by side. |
| POST | `/api/compare/books` | Two books split into characters: every PER entity in either, with its mentions in each. |
| POST | `/api/corpus/collocates` | Collocates of a search, with association measures, optionally only of some word types. |
| POST | `/api/corpus/context` | The paragraph around a concordance hit. |
| POST | `/api/corpus/filters` | The word classes, fine tags and entity types a word-type filter can choose from, with their counts. |
| POST | `/api/corpus/keywords` | Keywords of the selected books against other books or a reference file. |
| POST | `/api/corpus/kwic` | A concordance. The search is kept, so paging ("Show more") doesn't search again; `offset` and `limit` page it and only the lines of that page are made; `context` is the number of tokens each side. |
| POST | `/api/corpus/ngrams` | N-grams, optionally containing a word. |
| POST | `/api/corpus/wordlist` | A frequency list of words, lemmas, word+POS, word+POS+lemma or POS, optionally only of some word types. |
| POST | `/api/described` | What a target (`target`: an entity, saved or hand-picked group, tag or gender) is described or called as, split by who says it: `kind` (`mod`, `name`, `desc`, `pron`, `agent`, `patient`, `poss`, `prep`), `split` (`entity`, `gender`, `tag`, `book`, `voice`, or `custom` with `columns`: up to 12 specs, each an entity, group, tag or gender, with an optional `name`; column ids are then `c0`, `c1`…), `voice` (`both`, `narration`, `speech`), `top` columns (1–30, default 8), `limit` words (default 60). Section 6, "Described as". |
| POST | `/api/stats` | The Statistics tab: `setup` = {`cases` (`kind` pieces or participants, `piece`, `n`, `scope`, `population`, `sample`, `narrators`, `min`, `min_range`: participants in fewer of the selected books are left out), `rows` (up to 30 variable specs), `columns` (a second list for a grid), `method` (`pearson`, `spearman`), `correction` (`none`, `bonferroni`, `holm`), `split` (`none`, `gender`, `tag`, `group`, `book`)}. Returns the cases, the variables with their raw values, the correlation table and the descriptives. Section 6, "Cases", "Variables", "Correlations and descriptives". |
| POST | `/api/stats/bulk` | Variables to add in one go, labelled: `what` `words` (`n` most frequent words or lemmas, `unit`, in the samples of `cases`, optional word-type `filter`, and `min_range`: only words in at least that many of the books, default 1; `types` (a list of sentence types) with `weigh_verb` takes only words inside quotes of those types, and `speech_verbs` makes the words the verbs that introduce quotes in the cases' samples (lemmas, your leave-out list applied; the word-type `filter` then tests the verb; with `types`, the verbs of quotes of those types), neither for the Described-as sample), `entities` (`n` most mentioned of a `type`), `speakers` (the `n` of a `type` who speak the most words, as speech variables) or `attribute` (one 0/1 variable per value of `attr`: `gender`, `tag`, `group`); `measure`. |
| POST | `/api/stats/export` | The cases and variables of a Statistics `setup` (as `/api/stats`, both lists) as a .zip for R, for download: `cases.csv`, `cases_long.csv`, `variables.csv`, `dropped.csv`, `README.txt`, `load.R`, and `analysis_example.R` unless `example` is false (`core/rexport.py`). |
| POST | `/api/stats/options` | What layer variables can be for the selected `books`: supersenses found (with counts), relations, sentiment and style figures, the word-choice figures in sections (`wordchoice`: `{id, title, figures}`), your lexicons (`{id, name, categories}`), the topic models fitted on any selected book (`{id, name, covers, all, topics}`), whether VADER is installed. |
| GET | `/api/stats/sets` | The saved Statistics sets. |
| POST | `/api/stats/sets` | Save a setup (`setup`) under a `name`. |
| POST | `/api/stats/sets/delete` | Delete a saved set (`id`). |
| POST | `/api/stats/sets/{sid}` | Rename a saved set or replace its setup. |
| POST | `/api/described/evidence` | The sentences behind one cell of that table: the same body plus `item` (the word or form) and `column` (a column id, `_rest` for "All others", or null for the All column), `limit` (default 150). `total` is exactly the cell's count; each sentence says who said it (`by`). |
| POST | `/api/dialogue/conversations` | The conversations, optionally only those involving someone. |
| POST | `/api/dialogue/entity` | The Speech section of an entity's page. `wc`, `all_wc` and each `per_book` row's `wc` are the headline word-choice figures of the entity's speech, of everyone's, and of each book's share of it (`wc_columns` names them). `corrected` counts the quotes whose addressees you set: `spoken` by the entity, `heard` by others to it. |
| POST | `/api/dialogue/narrators` | Narration per narrator role. |
| POST | `/api/dialogue/overview` | Dialogue per book and a row per speaker. |
| POST | `/api/dialogue/quotes` | Quotes matching a filter. |
| POST | `/api/dialogue/scope` | Dialogue-in-each-book, speaking and narrating figures pooled for a scope (entity, group, tag or gender); In-Depth Who Speaks. |
| POST | `/api/dialogue/style` | Speaking-style figures for every speaker. `wc` ("", "headline" or a word-choice section id, `wordchoice.CHOICES`; 400 otherwise) adds word-choice figures to every row and to `all` as `wc`, with `wc_columns` and `wc_choices` (for the select). |
| POST | `/api/dialogue/verbs` | Speech verbs and adverbs, overall or for one speaker or group; `types`/`weigh_verb` filter by sentence type. |
| POST | `/api/dialogue/voice` | Speaking style and distinctive vocabulary of a target against a reference. `wc` as for the style table adds `wc` to both sides (and `wc_columns`). |
| POST | `/api/distinctive` | Words markedly more typical of a target than of a reference. |
| POST | `/api/overbook/compare` | The two sides `target` and `other` of the Compare page: over one `book` cut as `seg` says when some book holds both (`mode` "same": the answer of `/api/overbook`, which starts in a book both are in), else, because a book holding only one side would show the other as nothing, each in its own book (`book`, `other_book`) cut into `n` equal slices (`mode` "aligned": the answer of `/api/overbook/aligned`). |
| POST | `/api/overbook/aligned` | A `target` in one `book` and a second target `other` (null: the same) in `other_book`, cut into the same `n` equal slices (held to 2–200) so that they line up by relative position, for the relation `rel` with the shared statistics options. `book` and `other_book` are preferences: a book the target isn't in is replaced by the first it is in (side B: the first other than A's), and the answer says which were used. `{books_a, books_b, book_a, book_b, n, a, b, similarity}`: a and b are `overbook.table`s; `similarity` maps each figure of the curve (`ov:per1k`, `rel:agent`, `word:say`, `kind:verb.motion`…) to `{pearson, spearman}`, each `{r, p, n}`. Nothing is left out of the second side. a, b and similarity are null when either target is in none of the selected books. |
| POST | `/api/overbook/combined` | A `target` through every selected book that holds it, each cut into the same `n` equal slices (held to 2–200, default 20) so that slice k of n is the same relative stretch of each, every book weighing the same, for the relation `rel` with the shared statistics options, `min_range` (the fewest books a word must occur in to be tested, default 1) and `curve_rel`. `curve` (a figure of the curve: `ov:…`, `rel:…`, `word:<relation>:<word>`, `kind:…`; not the statistics `measure`) also asks for each book's own values of it. `{label, n, books, skipped, a, per_book}`: `books` are the books used, `skipped` the selected books without the target; `a` is an `overbook.table`-like answer (no `book`; each segment has `pos` and `ranges`, the `{book, start, end}` of that slice in every book, for `/api/evidence`'s `within`; the rows' `trend` is `{z, p, n, up, down}` with the books' trends combined, χ² and p the books' added up, no V or residuals) and null when the target is in none of the books; `per_book` is `[{id, title, values}]` when `curve` was given, else null. |
| POST | `/api/evidence` | The sentences behind a count: `target`, `kind` (a relation, `supersense`, `form`, `cooc`, `named`), `key`, `other`; `within` = `{book, start, end}`, or a list of up to 500 of them (all three required), keeps only those stretches: a slice of one book, or the same slice of several books (Over the book). |
| POST | `/api/export` | The selected books and your work on them as one `.zip`, for download (`core/export.py`; section 3). |
| GET | `/api/groups` | The saved groups of entities. |
| POST | `/api/groups` | Save a group of entities under a name. |
| POST | `/api/plurals` | Declare an entity a plural group: `add` / `remove` members (keeping the others), or `members` to replace them all (none: an ordinary entity again). |
| POST | `/api/plurals/suggestions` | Entities named after two or more others ("Holmes and Watson"), with the members found. |
| POST | `/api/plurals/reject` | Don't suggest this plural group again. |
| POST | `/api/groups/delete` | Delete a saved group (the entities stay). |
| POST | `/api/groups/{gid}` | Rename a saved group or replace its entities. |
| GET | `/api/lexicons` | Your lexicons, the emotion lexicon first: `{id, name, source, categories: {category: number of words}, problem}` (`problem` says why a file can't be read). Every change below answers the same, plus the `id` just made. |
| POST | `/api/lexicons` | Store a new lexicon from `text` under `name` (a word list, word–category rows or a column per category, see `lexicons.parse`); `emotion: true` makes it the emotion lexicon. |
| POST | `/api/lexicons/{lid}/replace` | Give a lexicon the words of new `text` (it keeps its id and name; also repairs a file that can't be read). |
| POST | `/api/lexicons/{lid}/rename` | Change the `name` a lexicon is shown by (not the emotion lexicon's). |
| POST | `/api/lexicons/{lid}/delete` | Remove a lexicon. |
| GET | `/api/lexicons/{lid}/words?category=` | The words of one category. |
| POST | `/api/lexicons/{lid}/category` | Save a category: `category` (null: a new one), its `name` now, its words as `text`. |
| POST | `/api/lexicons/{lid}/category/delete` | Remove a `category` (a lexicon keeps at least one). |
| GET | `/api/library` | The library page's data; each book carries the narrator you chose for it (`narrator`: id and name, or null). `default_settings` are the settings a new workspace starts with, so a page can tell which ones you changed. |
| POST | `/api/links/auto` | Automatically link entities of different books with an exact name, type and (for people) pronoun match, across the whole library. |
| POST | `/api/links/link` | Link two entities (or a person and an entity) as one. |
| GET | `/api/links/narrator_links` | The narrator roles linked so far (see `/api/narrators/link` etc. for changing them). |
| GET | `/api/links/persons` | The persons linked so far. |
| POST | `/api/links/reset` | Dissolve every link (linked persons and narrator links); rejected suggestions are kept. |
| POST | `/api/links/reject` | Remember that two entities are not the same. |
| GET | `/api/links/search` | Find entities by name in every book, for linking by hand (with no name: the most mentioned ones); `type` keeps one entity type. |
| GET | `/api/links/suggestions` | Possible matches between books, best first. |
| POST | `/api/links/unlink` | Take one book's entity out of a linked person. |
| POST | `/api/links/unlink_all` | Dissolve a linked person entirely: every member becomes its own entity again. |
| POST | `/api/name` | Rename an entity, linked person or narrator link (blank goes back to the name found in the books, or, for a narrator link, to its members' own names). |
| POST | `/api/note` | Give an entity or linked person a short free-text description (blank clears it). |
| POST | `/api/narrative/arcs` | Something counted per segment: entities, events, supersenses, dialogue or topics. With `seg.scope` "combined" (and equal slices by number) the books are put together slice by slice (`narrative.books_combined`; `each`: true adds every book's own line); the same holds for `/api/narrative/sentiment` and `/api/narrative/lexicon`. An entity's series carries its `books`; its values and counts are null in the segments of other books (a gap, not 0). |
| POST | `/api/narrative/chapters` | Edit a book's chapters: start one at a paragraph, remove or rename one, or go back to the ones found automatically. |
| POST | `/api/narrative/lexicon` | Words per 1,000 in each of the `cats` of lexicon `lexicon` (default: all its categories) per segment. |
| POST | `/api/narrative/segments` | The chapters or slices of the selected books. |
| POST | `/api/narrative/sentiment` | VADER sentiment per segment. |
| POST | `/api/narrative/style` | Style figures per book or per segment. |
| POST | `/api/narrative/wordchoice` | Word-choice figures per book or per segment (`by`), as the Style page shows them: `wordchoice.table` (`{rows, info, sections, choices, columns}`; a row holds every figure of `wordchoice.FIGURES` under its own name). |
| POST | `/api/narrative/sound` | (No page asks for it since the Style page dropped its sound table, AD-39; kept as an API, and the tests use it to check that the sound figures agree everywhere.) Sound and rhythm figures per book or per segment (`by`), under the workspace's sound settings: `prosody.table` (`{rows, info, figures: [{k, label, dec}]}`). 400 with `sound.MISSING` without the pronunciation dictionary. |
| POST | `/api/sound/figures` | The Sound and rhythm tab's figures per book or segment (`by`, `seg`) of the text in `scope` (as the Corpus routes take it): `soundtab.figures`. All four `/api/sound/` routes use the workspace's sound settings and answer 400 with `sound.MISSING` without the pronunciation dictionary. |
| POST | `/api/sound/cadences` | Every cadence pattern in `scope` (`soundtab.cadences`: rows, types, phrase and sentence ends); with `pattern` ("10010"; `end_only`) the phrases ending with it (`{total, shown, items}`, as `/api/evidence` answers, the cadence marked `k`). |
| POST | `/api/sound/runs` | The runs of one `kind` (alliteration, assonance, consonance, rhyme, repetition) in `scope` by what they share (`soundtab.runs`); with `key` the runs that share it, longest first (`{total, shown, items}` with `words`; the run marked `k`, or `rep` for repetitions, other repeated words `rep`). |
| POST | `/api/sound/guessed` | The words of the selected books whose pronunciation is guessed, most frequent first, and your corrections: `soundtab.guessed`. |
| POST | `/api/sound/lookup` | How one `word` is said now (`pos` optional), as a starting point for correcting it: `soundtab.lookup`. |
| POST | `/api/sound/scan` | One chapter or slice (`index`, cut as `seg` says) of a `book` word by word, with stresses, runs and cadences of the text in `scope`: `soundtab.scan`. |
| POST | `/api/narrative/stylometry` | Distances between texts, cluster tree and map. |
| POST | `/api/narrators/link` | Link two narrator roles (or a narrator link and a role) as one narrator; pools their narration only. |
| POST | `/api/narrators/reject` | Hide a suggested stretch told by someone else. |
| POST | `/api/narrators/suggestions` | Suggested narrators, from the "I" in the narration. |
| POST | `/api/narrators/unlink` | Take one narrator role out of a narrator link. |
| POST | `/api/narrators/unlink_all` | Dissolve a narrator link entirely: every role becomes its own narrator again. |
| POST | `/api/network` | A network as JSON (nodes with positions and measures, edges); `min_range` (entities in fewer of the books are left out) and `min_link_range` (links found in fewer books are dropped), both default 1; `max_nodes` (10–1000, default 300) keeps the most strongly linked entities and `info.total_nodes` says how many there were. |
| POST | `/api/network/export` | A network as a GEXF or GraphML file (also limited by `max_nodes`, and by `min_range` and `min_link_range`). |
| POST | `/api/profile` | An entity's, narrator role's or narrator link's profile, a book's (`book:<id>`) or a gender's (`gender:<pron>`), or a group's (`ids`, or a saved `group`) as one; 404 if it isn't in the selection. |
| POST | `/api/read` | One chapter or slice of a book, with the layers asked for (`sound` among them: the runs of `sound_colour`, one of alliteration, assonance, consonance, rhyme, repetition, are coloured, under the workspace's sound settings; `sound_layer` says if the dictionary is missing). The book may lie outside the selection. |
| GET | `/api/refs` | The stored reference files (damaged ones are skipped). |
| POST | `/api/refs` | Store uploaded files (word lists or texts) as a reference for keywords. |
| POST | `/api/refs/delete` | Delete a reference file. |
| POST | `/api/settings` | Minimum mentions, how to count them (`count_mode`), how to count word frequencies (`freq_mode`), the conversation gap, the speech verbs and adverbs to leave out (`speech_skip`, at most 500 of each), the sound settings (`sound`: `{window, boundary, alliteration, repetition}`, any of them alone; `window` a whole number from 1, `boundary` sentence, paragraph or none, `alliteration` stressed, sound or letter, `repetition` lemma, form or all, `corrections` a `{word: pronunciation}` that replaces the saved one, every one checked by `sound.check_corrections`, 400 naming the first that can't be read) and the source folders. |
| POST | `/api/tags` | Replace an entity's or linked person's tags. |
| POST | `/api/topics/compare` | Comparisons between the topics of one model: map, pair, groups (topic × book etc.) or items (topic × character/speaker). |
| POST | `/api/topics/delete` | Delete a model. |
| POST | `/api/topics/entity` | The topics of one entity's (or a group's) mentions or speech, for the entity page. |
| POST | `/api/topics/fit` | Fit a model of the selected books and store it -> its id. |
| POST | `/api/topics/model` | A model's overview. |
| GET | `/api/topics/models` | The stored models. |
| POST | `/api/topics/page` | One part of a topic's page: words, where, groups, passages, entities or speech. |
| POST | `/api/topics/rename` | Rename a model or one of its topics. |
| POST | `/api/topics/scan` | Fit one model per number of topics and report quality, to help choosing how many. |
| POST | `/api/units` | The entity list of the selected books, and the gender buckets among its PER entities (`genders`). |
| GET | `/api/workspaces` | The workspaces and which one is in use. |
| POST | `/api/workspaces` | Make an empty workspace (not opened), reading books from `sources`. |
| POST | `/api/workspaces/activate` | Switch to a workspace: the library re-opens its folder, caches are dropped, the topics folder follows. The browser reloads after it. |
| POST | `/api/workspaces/delete` | Delete a workspace's folder for good; `name` must be typed exactly. Only folders the analyser made; never Default or the one in use. |
| POST | `/api/workspaces/forget` | Take a workspace off the list; its files stay. |
| POST | `/api/workspaces/import` | Make a workspace from an export zip sent as the raw request body (`?name=`), streamed to a temporary file; not opened. |
| POST | `/api/workspaces/{wid}` | Rename a workspace. |
| POST | `/api/folders/open` | Show a folder in the computer's file browser -> `{path}`. `folder`: `books` (made if missing), `data` or `source` (with `index`, a place in the list of sources of the workspace in use); `workspace`: whose (default: the one in use; 404 if unknown). Never a path the request names. |

FastAPI also serves its interactive description of these routes at `/docs` while the analyser runs.

## 8. The browser code (`static/`)

`index.html` loads `app.css` and the scripts in `static/js/` **in order**; they share one global scope (no modules, no build).

| File | Contents |
|---|---|
| `core.js` | shared state `S`, `h()` (the element builder), formatting, remembered settings (`loadState`/`saveState`, kept per workspace: `storageKey`), `api()`, `openFolderButton()` (shows a workspace's folder in the file browser), `foldTable(summary, table)` (the numbers under a slice chart, folded by default, AL-TBL-07), `table()` (with the column chooser of a table of 7+ columns, `opts.columns` {id, show, keep}, `S.colsHidden` / `analyser.columns`; the CSV has every column), charts, `dlButton()` (the quiet SVG · PNG and CSV download links), `relMark`/`relNum` (the ≈ "read with care" marker, AL-FB-05; `MATTR_SHORT`, `ADDR_ESTIMATED`, `topicUnstable`; a table column's `rel`), the evidence drawer, the book picker (`renderSelPop`, built each time the Books submenu opens), `picker()` (its Book mode offers the book last chosen in any picker, `S.pickedBook`), statistics controls, the "Based on" lines (`basedOn(items)`, the shared items `BASED.*`, `settingChanged(key)` against the server's `default_settings`; `minLine`/`freqLine` are one-item lines; docs/DESIGN.md AL-BASED-01) |
| `entities.js`, `network.js`, `compare.js`, `links.js`, `books.js` | those pages (Network: the filters panel, a drawing row `.net-draw` above the canvas (with *Layout*: force-directed from the server, or a circle laid out in the browser by `circlePositions`, ordered by community, type, size or name), quiet downloads right above it (AD-41), the links table folded, AD-40; Entities also holds group, narrator, book and gender profiles: `profileBody` draws a profile's sections in the order of their questions, each tagged with `data-group` (Who they are, What they do, What they say, How they change, What sets them apart; `appearsWithPanel`; Kinds of action sits inside What they do); Library a card per book (`bookCard`: use tick, title, details form, collections, narrator, export used) with the collections list and the export button; the details form and the narrator popover redraw only their own card). Compare adds a "Split into characters" section (`/api/compare/books`) when both sides are a book: every character in either, with mentions in each — for comparing two whole books without losing who's in them. |
| `described.js` | the Described-as page (`describedLink` is the "Described by whom →" link on entity, group, book and gender profiles: it sets `S.desc.target` to the profile's own `u.target`): target picker, kind (modifiers, names, actions…), split (describer, gender, tag, book, voice), voice switch, measures shown beside the count; the table of words by describer, cells tinted by keyness |
| `overbook.js` | the Over the book page (`#/over`): target picker with an optional second ("Compare with…", in the Compare colours), the book switch (when a target is in several selected books), the shared Measure over slicer (`segControl(…, {timeline: false})`, always per book, redrawn by the page with every change), then, in this order, for each target the words of one relation and the kinds of action (`overGrid`: summary, line chart of the first eight rows of the order chosen, then the heat grid or number columns with `overCols`: slice columns, total, trend z and p, χ², p, V; `overOrder`: frequency, rising, falling, change), a curve of one figure along the book for one or two targets (`overCurve`, `overMeasures`: a category selector, Figures | Words | Actions, as the entity picker has for types, and a list for the one chosen: the overview's figures, the words, the kinds of action; each category remembers its own item in `S.over.curve_by`; Words has a list of lists of its own (actions, done to them, possessions…, `S.over.curve_rel`, apart from `S.over.rel` of the words panels; changing it asks again), and beside it `overWordsNote` says which list, whose words and in what order, matching `MEASURE_WORDS`; drawn with Arcs' `arcChart`), and an overview per slice for each target. A new request keeps the current results on the page, dimmed (`.busy`), until the answer replaces them, so the page keeps its height and the reader's place. A cell opens the sentences of its slice (`/api/evidence` with `within`; kinds of action use kind `supersense`), a row those of the whole book; every table has its own CSV (the heat grid's holds the shares and names its columns by the slices' own names). The page has two sub-tabs (`overTabs`, `#/over` and `#/over/aligned`; `renderOverbook(main, sub)`): *Within a book* is `overSingle`, *Two books aligned* is `overAligned` (the two sides in `S.over.al`: side A's target and book, side B's "same target" tick, target and book; its own `S.over.al_n` slices per book, saved; the same panels as the first, named by target and book, with the curve in `overCurveBody(r, redraw, {aligned: true, names})`: no per-slice links, titled by position, and `overSimilarity` showing the server's Pearson and Spearman figures for the figure chosen). `overLink(target, other, book)` is the sentence “See Over the book for more details.” with its link. The same file builds the small versions: `overProfile(u)`, the Over the book preview of every profile (`profileBody`, after Book by book: a line chart of mentions per 1,000 words, a book switch, the slicer in a fold behind its "Based on" line, and the link in the intro line; the words and kinds of action are only on the page, AL-PRIN-13), and `overCompare(a, b)`, the Compare page's section (the curve for both sides with its table and a link to the page with both preset; it asks `/api/overbook/compare`: when some book holds both sides they are measured in it, with a book switch; when none does, for example two whole books as the sides, each is measured in its own book, lined up by relative position with side A's and side B's book, the slices per book and the similarity of the curves, and its link, `overAlignedLink`, opens Two books aligned with both sides and their books preset, the targets without their book limits, and side B "same target" when they are the same); both fetch by themselves with `overPanel`, keeping their contents, dimmed, while they ask again. Settings are remembered (`S.over`: relation, view, order, curve, slices per book, `sound`, and **the book**; not the targets). The switch *Sound of their speech* beside the curve (`S.over.sound`, shown when the pronunciation dictionary is installed; `overSound`) adds `sound: true` to every overbook request: the curve then offers a *Sound of speech* category (`snd:<figure>`) and `overOverview` adds a table of the speech's sound figures per slice. The book is one choice for the whole feature (`S.over.book`, with `S.over.al_b_book` for side B of Two books aligned; `overBook`, `overRemember`): the page, the profile's panel, Compare and side A of Two books aligned all use it, a change of target does not clear it, and a target that isn't in it is shown in the first book it is in (the server treats `book` as a preference) without the choice being forgotten; only you change it (a book select, or following a link that carries a book). The third sub-tab, *Books combined* (`#/over/combined`, `overCombined`), follows one target (`S.over.co.target`, not saved) through every selected book that holds it (`/api/overbook/combined`; its own `S.over.co_n` slices per book, `S.over.co_each` and `S.over.co_min_range` (the control “Minimum range for the test” beside the minimum frequency, `overTestControls`), saved): a panel of the books used and left out, the same `overGrid` panels (a table without a `book`: `overTitle` names it by its books, evidence uses each segment's `ranges`, the columns Books, Rising and Falling replace Cramér's V), the curve with the switch “Show each book” (`opts.each` of `overCurveBody`: the books' own values are asked for for the figure chosen, so with it on a new figure asks again, and a figure that differs from the one asked for is handed back to the page, `refine`; `arcChart` draws a `faint` series as a thin muted line with its book as hover title) and the overview. The page's sections: the curve first, then per target one grid section (`overGrid(a, spec, name, redraw, rerun)`: tabs for each word list and *Kinds of action*, `S.over.kinds`; one controls row: View, Order select, test settings), then the overview (AD-37). |
| `help.js` | the help drawer of every page: `HELP` (page key -> {title, sections}), `addHelp(page, title, sections)` (each help-*.js file registers one page; a section has an `id`, which is a sub-tab's name in the address or a Statistics variable kind, a `title`, paragraphs, `[key, name, explanation]` entries per option, an example and where the maths is), `helpPlace()` (the page of the address: its tab and its sub-tab; "entity" for a profile, at its `narrator`, `group` or `pools` section for those; on Topics `home`, `model`, `topic` or a comparison tab; on Over the book `single`, `aligned` or `combined`; tested in tests/js/units.mjs), `openHelp(page, id)` (fills the evidence drawer with a contents list, the page's sections and then "Everywhere in aLex", scrolling the drawer alone to `id` when the page has that section), `helpButton(page, id, what)` (a "?" opening it at a section), `helpHead(tag, text, page, id)` (a panel heading with a small round "?", `.hq`, drawn by CSS so the heading's text stays its name). The top bar's `#helpBtn` opens the help of the page you are on. Loaded after `menu.js`, before the help texts |
| `help-general.js` | the help of the whole app, under every page's own ("general"): the top bar and book button, the `[...]` menu, long pages, tables and charts, the keyness controls every "What's distinctive" shares, the evidence drawer, what is remembered |
| `help-entities.js` | the help of the Entities page with nothing open ("entities"): the list (type chips, filter, order, minimum), choosing several, saved groups, plural suggestions |
| `help-entity.js` | the help of a profile ("entity"): header, figures, how referred to, relations, Book by book, Over the book, Speech, Topics, kinds of action, Appears with, What's distinctive, a group, a book's or gender's pool, a narrator; its "?" headings (`helpHead`) are on relations, Book by book, Speech and What's distinctive |
| `help-dialogue.js` | the help of the Dialogue page ("dialogue"): a section per sub-tab (its id the tab's name in the address), the sentence type, quote cards and corrections; "?" headings on How speech is introduced, Speaking style, Distinctive vocabulary and Quotes |
| `help-corpus.js` | the help of the Corpus page ("corpus"): a section per tool (its id the tool's name in the address), where to search, the search settings, Simple and Pattern syntax (every pattern attribute), word types; a "?" (`helpButton`) beside the Search button and in the search settings |
| `help-narrative.js` | the help of the `#/narrative` pages, Style, Stylometry, Arcs, Sentiment and Lexicons ("narrative", titled "Style and Over time"): the chapters-or-slices setting ("slices"; its "?" sits in `segControl`, so it also shows on Sound and rhythm and Over the book), a section per sub-tab (every style figure), lexicons; "?" also on Stylometry's controls and the Sentiment heading |
| `help-sound.js` | the help of Sound and rhythm ("sound"): a section per sub-tab, the run kinds, the settings for runs; "?" beside the Settings line and on the Pronunciation heading |
| `help-topics.js` | the help of the Topics pages ("topics"): models and fitting ("home"; the fit form's Documents, Words and Model headings carry a "?"), a model's overview ("model"), a topic's page ("topic"), comparing ("map", "pair", "grid"); `helpPlace` picks the section from the address |
| `help-over.js` | the help of Over the book ("over"): Within a book (`single`), Two books aligned, Books combined, the grids (views, orders, tests), the curve, the overview; "?" on each grid's and the curve's heading |
| `help-described.js` | the help of Described as ("described"): the lists, the splits, the voice, what a cell shows; a "?" beside the controls |
| `help-compare.js` | the help of Compare ("compare"): the sides, overview, kinds of action, words, split into characters, Over the book; "?" on the Words heading |
| `help-network.js` | the help of Network ("network"): the kinds of link, filters, how it looks, every measure, a node's panel, downloads; "?" beside the filters and on the Measures heading |
| `help-books.js` | the help of the Library ("books"): where books come from, a book's card, collections, search and export, Workspaces ("?" on its heading) |
| `help-read.js` | the help of the text view ("read"): reading, the layers (every one), the side panel and corrections |
| `help-chapters.js` | the help of the chapter editor ("chapters", #/chapters/<book>) |
| `help-links.js` | the help of Entity Links ("links"): auto-link, suggestions, linking by hand, linked entities |
| `help-narrators.js` | the help of the Narrators page ("narrators"): each book's suggestions and the page's two settings |
| `help-settings.js` | the help of the Settings page ("settings"): a section per section of the page |
| `help-stats.js` | the help of the Statistics page ("stats"): the cases, every variable kind (its section id is the kind) with each option, measures, bulk adds, coefficient, correction, split and results; `tests/test_help.py` checks every option has an entry |
| `stats.js` | the Statistics page (`#/stats`), a quiet top line (intro, saved sets) and three steps, `svstep` panels 1 Cases · 2 Variables · 3 Run (variables are added from two menus, `varAdders`: "+ Add a variable…" and "Add several…"; figures from fewer than `FEW_CASES` (30) cases carry the ≈ marker, `fewCases`): saved sets (open, save, revert, rename, delete), the cases (text pieces: chapters, slices or books in a scope; participants: who, their sample, narrators, the minimum), one or two lists of variables (each with a Clear button) edited as rows (`varRow`, each with a "?" opening its kind's help) or chips (`varChips`, entity-chip style with the type colour of what the variable is about, `varColor`; chosen on the Settings page as `S.stats.editor`) with the bulk adds (`varAdders`: paste, most frequent words (with the Dialogue tabs' `sentenceTypeFilter` and a "Speech verbs only" box under its word types), most mentioned entities, most talkative speakers, every gender/tag/group via `/api/stats/bulk`; every style figure, every category of a lexicon, every topic of a model, from `svOptions`, the answer of `/api/stats/options`), the `+ Layer…` menu (Word choice: a kind-of-figure select and a figure select; the bulk “Word choice…” adds a whole section), coefficient, correction and split; Run posts `statsSetup()` to `/api/stats`. Results: Correlations (`corrHeatmap`, an SVG coloured by `corrColor` with SVG/PNG download, display toggles for p, N and the interval, and every pair as a table), Descriptives and Data (the raw values, CSV, and `downloadForR`: the files of `/api/stats/export` for the setup the run was made from, with or without the example script as `S.stats.example` says) |
| `dialogue.js`, `corpus.js`, `narrative.js` | those page groups (`dialogue.js`'s `timeChart(series, {average})` draws the average of more than `TIME_AVERAGE_FROM` books with each faint, AD-44; `narrative.js` draws the `#/narrative` pages: each but Stylometry starts with the Measure over slicer, `segControl` (with `{combined: true}` on Arcs, Sentiment and Lexicons its Timeline offers Books combined; `arcLines` and `combinedControls` draw the faint books and the Show each book tick, AD-45); Stylometry, `narStylo`, has its own Compare panel with the slicer beside Texts, a Method row, and the tree beside the map, AD-38) |
| `sound.js` | the Sound and rhythm tab (`#/sound/<sub>`, `renderSound`): the Corpus `scopeControl` (labelled Text) and the Arcs slicer above four sub-tabs, `S.snd` remembered: *Figures* (`sndFigures`: one row per book or segment, a chart of one figure, the table), *Cadences* (`sndCadences`: the cursus forms and every pattern; a row opens its phrases in the evidence drawer, `/api/sound/cadences` with `pattern`), *Runs* (`sndRuns`: a kind's shared sounds or words; a row opens its runs), *Scansion* (`sndScansion`: book, chapter or slice, which kind's runs to colour (`PALETTE` by shared sound), *Every cadence*; each word an inline column of its stress marks over the word (`.scan .sc-w`), runs coloured, repetitions outlined (`.rep`), cursus cadences underlined and named, guessed stresses in the warning colour, words outside the scope faded), *Pronunciation* (`sndWords`: the guessed words, most frequent first, a row filling the form; your corrections, `sndYours`, with Remove). `sndRunBar(onChange)` is the workspace's run settings as one bar (window, where runs stop, alliteration, repetition; the choices `SND_BOUNDARIES`, `SND_ALLITERATION`, `SND_REPETITION`, which the Settings page uses too): a change is saved with `POST /api/settings` and `onChange` draws the view again, so its runs are counted under the new setting at once (every kept tally is keyed by the settings, `prosody.signature`, so nothing old is reused); it stands above Figures, Runs and Scansion, and beside the Read view's sound layer (the Style page has no sound table since 2026-10-26: a link to Figures, and `sndBasedOn()`'s "Based on" line under its chart when it draws a sound figure). `sndCorrector` is the form to correct one word (Look up, `/api/sound/lookup`, then the pronunciation to type, Save), used here and on the Settings page; corrections are saved whole with `POST /api/settings` (`sndSaveCorrections`). The repetition style `mark.rep` also outlines repeated words in the drawer's sentences. |
| `lexicons.js` | the Lexicons page of the Over time area (`#/narrative/lexicons`): an intro panel (load a file, or type or paste a lexicon), then one collapsible panel per lexicon, the emotion lexicon first (`lexPanel`: rename, replace the words, remove, category chips with an arc and table, `lexWords` to browse, search and edit categories). A lexicon seen for the first time starts folded, except the first panel; a folded panel loads nothing until `pagetools.js` sends it an `expand` event. |
| `reader.js`, `narrators.js` | the text view (a continuous scroll, with the quote and narrator editors, and the chapter editor; the layer chip *Sound and rhythm*, shown with the pronunciation dictionary, adds a *Colour the runs of* choice, `S.read.soundColour`, and each segment's `mark.sw` get their colour, `--c` from `PALETTE` by `sk<n>`, and a title of what they belong to; the stresses are the marks' `::before`, placed above the word) and the Narrators page |
| `topics.js`, `topic-page.js`, `topic-compare.js` | topic models: fit (`topicForm`: the finer settings folded under *Fine-tuning*, its summary a `basedOn(items, "Fine-tuning: ")` line tinting values changed from `S.lib.topic_defaults`, AD-46), overview, a topic's page, comparisons |
| `menu.js` | the top bar's `[...]` menu (markup in `index.html`): Entity Links, Narrators, Plural groups, Settings and submenus (Workspace, Theme) that open to the left on hover or click (under their row on a narrow window); closes on choosing an entry, a click outside or Escape. The book button beside it (`#booksBtn`, `setBooksPanel`) opens the book picker in a panel of its own (`#selPop`; its book list `.books-list` is the only part that scrolls, with `overscroll-behavior: contain` so the page behind stays put); the panel fires `submenuopen` when it opens, which is when `renderSelPop` builds the picker. Only one of menu and panel is open at a time. Other scripts fill and handle the entries |
| `settings.js` | the Settings page (`#/settings`, reached from the `[...]` menu; `#/settings/<section>` scrolls to a section, as the "Based on" lines link): a contents list (`.stoc`, highlights the section under the top bar) and sections Appearance (theme; the Statistics variable editor, rows or chips, and whether the R export holds an example script, both kept in the browser), Entities (plural default, minimum mentions per type, how to count), Words (`freq_mode`: how a minimum word frequency is counted), Sound and rhythm (the run window and boundary, what alliteration compares and what counts as a repetition, your pronunciation corrections with the form and table of sound.js, `sound`) and Folders (the books folder and data folder of the workspace, each with Open; the other source folders with Open and Remove, and their problems). Rows are `.fields` (label, control, hint); choices save at once through `POST /api/settings` and redraw the page |
| `workspaces.js` | the Workspace submenu of the `[...]` menu and the Library page's Workspaces section (a card per workspace; make, import by upload, rename, switch, open its folder, remove from the list, delete by typing the name); switching reloads the page |
| `pagetools.js` | collapsible sections and the side menu, always at the right (appended after the content; a panel's `data-group` is listed under that group's label, `.page-toc-group`) |
| `focus.js` | the focus (docs/DESIGN.md AL-PRIN-12): `S.focus` ({mode: "page" or "shared", target}, `analyser.focus`, per workspace), `focusFits(spec, opts)` (whether a picker with `opts` offers the target's kind), `followFocus(key, own, opts)` (what a page's subject chooser uses: in shared mode the focus when it fits, unless the page's own choice was set since by a link, which then leads), `subjectPicker(key, …)` (a `picker` whose choice also sets the focus, with "follows the focus"), `setFocus`, `focusStart` (notes each page's own subject at start, `FOCUS_SUBJECTS`), `drawFocus` (the top-bar chip `#focusChip`). Opening a profile calls `setFocus` (entities.js) |
| `areas.js` | the eight areas of the top bar (`AREAS`: id, label, pages as [address, label]; docs/DESIGN.md §8.3): `areaPlace()` (the area and page of an address; the chapter editor is Read's, pages of `[...]` have none), `drawAreas()` (marks the open area, points each area link at the page last used in it, `S.areaLast` / `analyser.areas` per workspace, and draws the open area's pages as tabs in `#areaNav`, above `#main`, for areas of more than one page). Pages keep their addresses, so no page draws a tab row for its area itself |
| `main.js` | the router (calls `drawAreas()` before each page); must load last |

**Pages.** A page is `renderX(main, …)`: it builds DOM with `h()` and puts it in `#main`. The address is a hash route,
`#/<tab>/<sub>/…` (`#/entities/<unit id>`, `#/dialogue/verbs`, `#/read/<book>/<token>`, `#/topics/<model>/<topic>`,
`#/topics/<model>/compare/pair/<a>/<b>`). `render()` (in `main.js`) dispatches; renders never overlap (a newer request waits for the
running one).

**The text view** (`reader.js`) shows a book as one scroll. It asks `/api/read` for one chapter (or slice) at a time and adds the next or previous
one when you scroll near it (an `IntersectionObserver`, with "Load…" buttons as fallback); quotes, paragraphs and topic documents of the loaded chapters are kept
in small registries for the side panels. The settings bar (book, layers, legend) and, under it, the position bar are frozen together in `.read-head`; its height is published as the CSS variable `--read-head` (a `ResizeObserver` keeps it current) so jumps and the side panel stay clear of it. The position bar shows the chapter and paragraph at the top of the window (worked out from element positions on scroll)
and jumps between chapters. Paragraph numbers are `no` from the server (1-based reading order). The chapter editor (`#/chapters/<book>`) is the same page
with `edit` set: no layers, a "start a chapter here" button per paragraph and rename/remove buttons on chapter titles; after each edit the page reloads at the
paragraph. Take care with class names: `.seg` is the segmented button group, so chapters use `.chap`. Clicking a paragraph's narrator
pill (`.pn`) opens `narrPanel`: "Apply" corrects this paragraph (and optionally the next few), "Apply to this whole chapter" instead
posts to `/api/annot/chapter_narrator` with this paragraph's `pid` — the server works out which chapter it's in, so the panel needs
no chapter boundary of its own. Clicking a counted entity mark (`entPanel`) shows the mention's own text as a heading, then, once
`units()` resolves (the same cached `/api/units` call every entity list uses), "Attributed to `<name>`" linking to that entity's page
whenever its canonical name differs from what's actually on the page ("he" → Holmes, "the detective" → Holmes, or "Sherlock Holmes" →
Holmes) — "Open profile" instead when it doesn't (a mention that already reads as the canonical name). An uncounted mark (below the
minimum) never got a `units()` row, so it keeps the plain "no profile" message.

**Narrator profiles** (`entities.js`, `narratorProfileView`): a role or narrator-link page (`isNarr` in `renderEntities` also treats
an `nl:` id as a narrator page, matching `/api/profile`'s own check). `narratorLinkBox` shows the current members (each linked to its
own character's profile when it has one, via `role.members[].unit`, since the role id itself no longer resolves once linked — see
below) with an Unlink each and "Unlink all", and always a picker to link with another narrator role. Linking or unlinking can move
this role to a different id (a fresh `nl:…`, or, once a link of two dissolves, a member's own original id), so those actions navigate
there (`location.hash`) rather than just re-rendering — except when the id doesn't change, where a same-value hash assignment
wouldn't fire `hashchange`, so it calls `render()` directly instead.

**Network focus** (`networkSvg`): hovering a circle highlights it and its neighbours; a click pins that focus (`o.pinned`, `el.setPinned`, `o.onPin`), a click on
empty space releases it (a drag doesn't); a circle without a label gets one while hovered or pinned.

**Book and gender profiles** (`entities.js`): `bookProfileView` and `genderProfileView` are their own pages (`isBook`/`isGender` in
`renderEntities`, matching `/api/profile`'s `book:`/`gender:` dispatch), each with its own simple header (a book's facts; a gender's just
its name) plus the entities pooled into it (`poolTable`, read-only — no ticking or editing, unlike a hand-picked group) and, shared with an
entity's or a hand-picked group's page, `profileBody` (`profileView`'s relations/how-referred-to/book-by-book/kinds-of-action/appears-with/
distinctive sections, extracted so both can use them; `opts.noSpeechTopics` and `opts.noCooccur` turn off the two that a pool can't support).
A gender bucket is its own row in the Entities list (type `"GENDER"`, built client-side from `/api/units`'s `genders`, since it isn't a real
entity type); a book's page is linked from its row on the Library page ("Overview"), not from the Entities list.

`.ent-list` (`app.css`) is a sticky flex column (`.head` for the search/filter controls, `.items` for the scrolling rows). `.items` needs
`min-height: 0` (with `.head` set to `flex: 0 0 auto`): without it, a flex child with `overflow: auto` won't shrink below its content's own
intrinsic height, so a `.head` that grows tall (many selected-entity chips, wrapped over several lines) pushed `.items` past `.ent-list`'s
bottom border instead of scrolling inside it.

`.filters-grid` (Quotes, `dialogue.js`) has the same class of gotcha for CSS Grid: `grid-template-columns: repeat(auto-fill, minmax(200px,
1fr))` sizes every column from the widest content ever placed in it, across every row, because a grid item's default `min-width: auto`
lets its own unbreakable content (a `<select>`'s longest option string) inflate the *track*, not just overflow past its own cell. One
field with a long option — "Addressee found by", from `dialogue.ADDR_METHODS`'s "Speaker keeps talking to the same person" — was enough
to widen column 1 past 200px, squeezing the other columns in the row above it and pushing "Book" to overlap "Containing". Fixed with
`min-width: 0` on `.filters-grid label` and its `select`/`input`, so a track never grows past its `minmax()`; an over-long selected value
just clips inside its own box (native `<select>` behaviour) instead of resizing the grid.

**Gathering entities by name** (`poolByName`, core.js): the group picker has a row "or add every entity named…": comma-separated words, optionally one entity type, a live count of the entities and mentions that match (a case-insensitive part of the entity's name; `units()` rows), and a button adding them all to the group. BookNLP often splits one place into dozens of entities (the moor in Hound: "the moor", "the great Grimpen Mire"…), and this gathers them without picking each; the chips can still be removed one by one. The Compare page's group pickers have it too. The type matters: a name search for "moor" without a type also finds people described by the moor ("the man upon the moor").

**Type filter in entity searches.** Every entity search list has an "any type" drop-down (`typeSelect`, core.js) that narrows it to one type (PER, LOC, GPE…): the Entity mode of `picker()` and the group picker's search (both are `unitSearch`, which also serves the Arcs and Reader entity boxes), and the Links page's two boxes (`/api/links/search?type=`, filtered on the server before the 40-row limit). The "add every entity named…" row and the Tag mode use the same drop-down.

**Pickers.** `picker()` chooses an entity, a group (`groupPicker`: search, chosen entities shown as removable tags outside the list, saved groups, the Entities
selection), every entity of some types (**Type**, `typePicker`: a toggle per type present in the books, with its entity count; shown wherever `opts.group` is; the spec is `{kind: "type", types, name}`, `null` when none is ticked), a tag group, "everyone else", a narrator, a book or a gender (`opts.book`/`opts.gender`; the same spec kinds `View.resolve` accepts,
so Compare, Dialogue's speaker/narrator pickers and an entity's "Compared with" all take one without further plumbing). `typeFilter()` (corpus.js) is the word-type filter. Requests that can be superseded by a newer one
(corpus searches) keep a counter so only the newest may fill the page. A chosen entity is drawn by `gtag()`: a compact pill (`.gtag`) with its type as small
text and a colour bar (an inset box-shadow) rather than a separate badge, so it reads as one shape; used by `groupPicker` (including on the Compare page) and a
group profile's member list (`entities.js`'s `groupHeader`). Its book label (`booksLabel`) is truncated with an ellipsis (`.gtag small`, 90px) to keep the chip
compact; the full label is the chip's own `title`, so it shows on hover.

**Results boxes** (`app.css`). Every results table (`.tbl-wrap`, made by `table()` and the topic heat table), the concordance lines
(`.kwic.results-scroll`) and the Dialogue quotes list (`.results-scroll`) share one rule: at most one screen tall (`100vh` minus the top bar),
`overflow: auto`. Wheel or touch scrolling over a box moves the box first; at its top or bottom the page takes over, because no
`overscroll-behavior` is set (do not add `contain`). Table headers are sticky inside the box (a shadow replaces the border, which a sticky
cell loses). Footers ("N rows", Show all, CSV) and "Show more" sit outside the box. The side drawer is its own scroller and is left alone;
short tables keep their natural height. `tests/js/interactions.mjs` checks the rules in the stylesheet (jsdom does no layout).

**Many books.** Charts and lists that draw one thing per book stay readable and light with sixty: a line chart with more than `MANY_LINES`
(12) lines names them by tooltip instead of at their right-hand ends (`timeChart`), x-axis labels are thinned to about sixteen (`lineChart`), book
titles over an arc chart are left out beyond twelve books, "Kinds of action, book by book" shows the eight books with most actions and says
so, the strips of where something occurs (`presenceChart`) give each slice its own tooltip only up to `PRESENCE_DETAIL` (30) books and a book's total beyond
(each slice is a rectangle and a tooltip: sixty-four books would be over ten thousand elements), the concordance plot is drawn from 200 counts per book
(`plotChart`), and the Network page's "Show at most" box sends `max_nodes`. Entities
remembered from an earlier visit (Arcs, Sentiment) are dropped if they no longer exist (linked since, or below the minimum now) rather
than leaving an empty chart. `tests/js/many.mjs` opens the pages over sixty-four books to keep it so.

**Corpus tools** (`corpus.js`). The tool tabs are the Words area's (`#areaNav`), which stay in view under the top bar (`--sticky-top`). Search
settings (word forms/lemmas, case, regex, wildcards, ignore punctuation) are always shown, not behind a collapsed `<details>`. Wildcards
(`S.corp.settings.wildcards`, default on) is disabled whenever regex is on (regex already gives you the same power); switching it off makes
`*`, `?`, `|` and `#` literal characters instead of Simple/Pattern search wildcards, so you can search for punctuation like `?` or `!` —
`corpus.value_matcher`'s new `wildcards` param does `re.escape()` instead of interpreting them when off, and `parse_simple`'s `#` (any
word) marker is likewise only special when wildcards are on. `queryBar` swaps
between a single-line `<input>` and a `<textarea>` (`S.corp.batch`) for a batch query — one term or pattern per line, Ctrl/Cmd+Enter to
search since Enter alone adds a line — passed to the server as-is (a batch is just a multi-line query string: see `corpus.Matcher`).
`corpKwic` shows a "Matched" checkbox (`S.corp.showMatch`) only when the result says `batch: true`; on, each `kwicLine` gets a `.kl-m`
column naming which line matched (`.kl.with-match` changes the row's grid columns to fit it).

**Independent controls.** A control must never change what another one shows (a user rule, after two reports: Speech verbs' two filters,
and Book by book / What's distinctive's significance settings). Two kinds of sharing exist, and only the second is allowed to stay:
(1) *same-page coupling* — two panels on one page reading one state — is a bug; (2) *a documented global setting* that is drawn once
and visibly applies to a whole page or tool group is intended. The intended ones: the Corpus scope, search settings and query (drawn once
at the top of the five Corpus tools, `S.corp`); the Arcs-and-style slice/chapter timeline setting (`S.nar.seg`, shared by Arcs, Style,
Stylometry, Sentiment and the topic pages); the book selection and the conversation-gap setting; the significance settings (below).

**Sentence type** (`dialogue.js`, `sentenceTypeFilter(st, onChange, compact)`): a "Sentence type" select (All/Questions/Exclamations/Statements)
and a "Weigh the speech verb too" checkbox, for filtering or scoping by `dialogue.sentence_type`. Every place that shows it has its own
state object `{type, weigh}` in `S.dlg.sf` (`quotes`, `verbs` = "How speech is introduced", `verbsTarget` = "One speaker or group",
`style` = Speaking style, `voice` = Distinctive vocabulary) and the entity Speech panel keeps one local to the panel, so changing one
changes nothing else, on that page or any other. `typeArgs(st)` turns a state into the request's `types`/`weigh_verb`. The entity Speech
panel (`speechPanel`) uses the same function in its compact form: the same control on one small line. `entity()`'s `vb = verbs(view, spec, None, types,
weigh_verb)` call used to pass `None` for `types`/`weigh_verb` even when the caller asked for a filter, so the entity Speech panel's
Speech-verbs/Adverbs tables silently ignored it while the other figures (from `style(pairs)`) obeyed it — fixed by threading the same
`types`/`weigh_verb` through.

**Significance settings** (`S.stat`: ranking measure, test, minimum frequency, p-level, Bonferroni, show non-significant; `statControls`)
are one global set, saved in localStorage and used by every comparison panel (entity Book by book and What's distinctive, Compare,
Corpus Keywords, Speech verbs' distinctive verbs, Distinctive vocabulary, narrator vocabulary). Because an entity's page shows two of
those panels at once, `saveStat(origin)` announces a change with a `statchange` event and `syncStat(el, run, refresh)` makes a panel
re-run (and, for What's distinctive, rebuild its controls) when the *other* one changes them, so the two never disagree; `origin` is the
changing panel's own re-run function, which `syncStat` skips.

**In-Depth Who Speaks** (`dialogue.js`'s sixth Dialogue tab, `dlgIndepth`): "Who speaks"'s three sections — "Dialogue in each book",
"Speakers", "Narrators" — filterable and comparable by entity, group, tag or gender. `wholeSpeakersPanels()` (the first two sections'
markup, extracted from `dlgSpeakers` so both share it) and `narratorsPanel()` give the unfiltered, whole-selection view when Search mode
has nothing chosen — the same content "Who speaks" shows. Choosing a scope pools everyone it matches into one `/api/dialogue/scope` call
(`scopedSpeakerPanels(spec)`): "Dialogue in each book" becomes that pool's own `entity()`-style per-book breakdown plus its own dialogue-
share-over-time chart (`E.time`, from `dialogue.scoped_time`), "Speakers" its pooled `style()` figures as a `.facts-inline` card (mirroring
`speechPanel`'s), "Narrators" its pooled `narrating` figures if any of it narrates. A `seg()` (Search/Compare, mirroring Corpus's Simple/
Pattern toggle) chooses one scope or two. The scope picker uses `picker(value, onChange, {group: true, gender: true})`, which is Entity +
Group + Tag (always) + Gender — no `book`/`narration`/`others` modes, since those aren't among the four axes asked for. Because switching
Search/Compare must also show or hide the "Compared with" field and relabel "Scope" to "Target", `drawControls()` rebuilds the whole
controls row on every change (mode, target or reference) — simpler and more robust than patching it in place, and cheap since `picker()`'s
`onChange` only fires on a completed selection, not per keystroke. `core.view.View.pool_unit(spec)` is the server-side piece: see the
Group entry above.

Compare mode (`compareSpeakerPanels`) stacks target and reference as rows rather than two side-by-side columns, one colour per side
(`PALETTE[0]`/`PALETTE[1]`) throughout, on the reasoning that a reader compares figures more easily aligned than split left/right:
"Dialogue in each book" becomes one `hbarChart` of quotes per book, a paired bar (target's colour above reference's) for each book,
rather than two tables; its dialogue-share chart becomes one `timeChart` combining both sides' `E.time` series (each book's line still its
own name/colour pair, `"<book> · <side>"`, since it's the side — not the book — that carries the meaningful colour here); "Speakers"
becomes a `cmpRow` per figure — a label and two small `.bar-cell` bars, sized relative to whichever side is larger, reusing the same class
`barFmt` uses in tables but with an explicit two-colour `background` (its default CSS only sets one, `var(--accent)`); "Narrators" becomes
two coloured-left-border lines instead of two `.facts-inline` cards. Two independent `/api/dialogue/scope` calls via `Promise.all`, not a
single merged endpoint — each side's figures come back in exactly the shape `scopedSpeakerPanels` already uses, so Compare only has to
pick a different way to lay them out, not recompute them differently.

**The Links page** (`links.js`) shows one card per character throughout: `.link-card` for each side of a suggested pair (`sideView`), and `.person-card`
(laid out several to a row by `.people-grid`, filled the same `--panel-2` as a suggestion card) for each already-linked person, with every book appearance
it was made from listed inside the card (`personCard`), each with its own Unlink. A card's head has its type (`typeChip`, from `links.persons`'s
`type`: its members' most-mentioned category) and name on the left, "Open profile" and a checkbox (unrelated to its appearances) on the right, for
batch work: the toolbar above the grid dissolves every ticked person at once, one `/api/links/unlink_all` call per card (`Library.unlink_all`, which — like
`unlink` taking one member out — gives every departing member a copy of the tags, name and description the linked person had).
"Reset all links", beside "Unlink selected", asks once and calls `/api/links/reset` (`Library.reset_links`): every person is dissolved the `unlink_all` way and
every narrator link too; "Not the same" decisions stay.

Linked narrators (the same narrator role linked across books, e.g. an anonymous narrator carried from one book to the next) get their own
"Linked narrators" subsection below the people grid, in their own `narratorLinkCard`s — the same shape as `personCard` but for narrator roles:
no book appearances or tags (a role isn't an entity), each member its own possibly-anonymous role with its own Unlink, and "Unlink all" to
dissolve the whole link. They're kept out of the person batch-unlink toolbar and use `/api/narrators/*` (not `/api/links/*`) since it's a
different kind of link. `core.links.narrator_links`/`_unit_name` resolve a narrator link's members and display name directly from `lib.state`,
mirroring `persons`'s own View-free pattern (this listing has to work library-wide, regardless of which books are selected or the minimum-mentions
setting) rather than reusing the View-dependent `dialogue.role_name`. Both iterate a `list(...)` snapshot of `lib.state`'s dict, not the
dict itself: FastAPI runs each request in its own thread pool worker, so a concurrent request that mutates `lib.state["persons"]` or
`["narrator_links"]` (an unlink, say) while one of these is mid-loop would otherwise raise "dictionary changed size during iteration".

**Sort direction.** A "most/least" style sort `<select>` that has no direction of its own gets a `reverseBtn()` beside it: ↓ for the normal order, ↑ once
reversed, matching the concordance sort's own reverse arrow. It flips whatever the current sort key's normal order is (most-first for a count, A–Z for a
name), rather than meaning "ascending" globally. Used by the Entities list (`entSort` / `entSortRev`) so far.

**Several books together.** `bookLabel(id)` names a book for a list of several (the server already orders these by year, see `view.py`); it adds "(publication
date missing)" for one with no year, since that is why it sorts last. `bookLink(id, label?)` wraps that in a link that "drills down": clicking sets the
selection to just that book (`setSel([id])`) and redraws the current page, so a table or chart of several books can jump to any one of them (the "Book by book"
overview table on an entity's page does this for its Book column; add it to a page's own book-labelled cells the same way as they are touched). It also
pushes the wider selection it narrowed from onto `S.selHistory`, for `drawViewing()`'s "Back" button.

**What is being viewed** (the book button in the top bar, `#booksBtn`; `drawViewing()` in core.js, called whenever the library or the selection changes). Its tooltip (`#viewTip`, shown on hover or focus) names the selection
with `viewingLabel()` — a single book's title; a whole collection's or series' name when the selection is exactly that; `Various for "X"` for several books all from one
collection or series but not all of it (the smallest enclosing collection wins over a series, if both match); else `Various` — and counts the books ("2 of 3 books"). The button is tinted when the selection is narrower than the library.
`#viewBack` (beside it) shows when `S.selHistory` isn't empty, popping it and restoring that wider selection; its text names the target in words (`backTarget`: "all books", "3 books", or the collection's or series' name) and its tooltip explains why it is there.

**State.** `S` holds what the interface remembers. Parts are saved in `localStorage` under `analyser.*` keys through
`loadState(key, defaults)` (defaults merged with what was saved, key by key, and only if the saved value is the same kind of thing) and
`saveState`. (Keys include `analyser.libview` for the Library page, `analyser.read`, `analyser.corp`, `analyser.nar`, `analyser.net`, and
and `analyser.theme`: "auto" (the default, follows the system), "light" or "dark", set from the Theme submenu of the `[...]` menu at the top right (`setTheme`, the `data-theme` buttons) as `<html data-theme>`, which `app.css`'s custom properties key off. `index.html` sets it from storage in a small inline script before the stylesheet loads, so there is no flash of the wrong theme.) Damaged or unavailable storage falls back to defaults and never stops a page.

**Talking to the server.** `api(path, body)` posts JSON, adding the workspace's plural-group setting (`plural`, from `pluralMode`) unless the body sets it. On failure it shows a message, replaces the "Loading…" line that request was
going to fill (see `loading()`), and throws an error marked `handled`, so an unawaited call doesn't add console noise.

**Building DOM.** `h(tag, props, ...children)`: props starting `on` are listeners, `class`, `style` (object); children may be nested
arrays; `null`/`false` are skipped; strings are text. `svg:circle` builds SVG; style keys starting `--` are set with `setProperty` (custom properties). Charts are functions returning `<svg>`; `chartBox()`
adds SVG/PNG download buttons; `table()` gives sortable, limited, CSV-exportable tables. A chart's own text, axis lines and halos are plain SVG attributes, not stylesheet rules, so they can't pick up
`app.css`'s custom properties through CSS alone: they read the current theme's colour at draw time with `cssVar("--ink")` and the like. Downloaded SVG/PNG charts always use the light-theme colours on a white
backing rectangle regardless of the screen's theme (`prepSvg` swaps them back), since a saved file has no theme of its own. Categorical colours (entity types, series, topics) don't change with the theme.

**Page tools** (`pagetools.js`). A MutationObserver watches `#main`; after any change `enhancePage()` adds a fold arrow to every
top-level panel with a heading (or a `data-toc` label) and to `h3` sub-headings (the heading plus what follows it up to the next heading),
re-applies remembered folds (`analyser.collapsed`, keyed by page and heading), and builds the sticky menu when there are three or more
top-level sections (on the right for the Entities page, where the list takes the left; topic pages have their own menu).
Both kinds of menu have a « / » button (`tocButton()`) that folds them to a thin rail; `tocApply()` sets `main.toc-closed`
(which also lifts the page's 1500 px width cap) from `analyser.tocClosed`, one entry per page.
Give a panel `data-toc="Label"` to name it in the menu when it has no heading; put `data-cx-head` on a row to fold by it.

**Styling.** One `app.css`; colours and fonts are custom properties on `:root`. Light is the default; dark values are set in a
`@media (prefers-color-scheme: dark)` block (for "Auto") and again under `:root[data-theme="dark"]` (for the toggle's explicit
"Dark", which also blocks the media query from applying when it is explicitly "Light"). `--chrome` is a surface that stays dark
in both themes (the toast and tooltips), since it always carries white text.

**Look.** The design language (principles, tokens, components, decisions, known deviations, and how to carry it to another project) is
written down in [DESIGN.md](DESIGN.md); read it before redesigning or adding a page. It is based on the companion editor's language
(`editor/docs/DESIGN.md`) and says, rule by rule, where aLex differs. The buttons (`.btn`), segmented control (`.seg`), `[...]` menu and top bar follow that language
(radius 6/7, weight 500, hover darkens the border, `--accent-ink` for text on an accent fill). The top bar
(`.top`, `--bar-h` tall, which the drawer and the text view's sticky header use as their offset) is a light `--panel` bar: the brand
(a plain label, not a link), the Library as a button of its own, then a gap and the other areas as one `.seg` of links (`data-area`; the open one has class `on`; they scroll sideways on a narrow window; the open area's pages are tabs in `#areaNav` under the bar, see `areas.js`), and the
`[...]` button last. Pages in the editor's layout (Settings, Library) use `.page` (centred column, serif `h1`, `.lede`), sections `.lsec` under an UPPERCASE `h2`, cards `.bookcard` / `.coll` (outlined when `.current`) and the popover `.pop` (the narrator picker in `reader.js`: `narratorSelect`, a button naming the narrator that opens a searchable list; it closes on a choice, a click outside or Escape. Given the narrator the page already knows (the Library's `narrator` per book, the Narrators page's `current`), it names it at once and fetches the book's people only when first opened, so sixty cards ask the server for nothing up front).

## 9. Testing

Setup, once (from the project folder, with your environment active):

```
pip install -e ".[dev]"                    # the package itself (editable), pytest and httpx
cd tests/js && npm install                 # jsdom, for the browser tests (needs Node); optional
```

Run:

```
pytest                       # everything (Python tests, and the browser tests if Node and jsdom are installed)
pytest tests/test_view.py    # one file
pytest -k topics             # by name
```

The suite never touches your real data: every test uses a generated corpus and its own temporary data folder.

**Continuous integration.** `.github/workflows/tests.yml` runs the whole suite (browser tests included) on every push and pull request, on Ubuntu and
macOS with Python 3.10 and 3.13, from a fresh `pip install -e ".[dev]"` and `npm ci --prefix tests/js`, so the newest library versions are tried
as well as the oldest supported Python. A failure there that you can't see locally is usually a newer library: reproduce it in a new virtual environment.

**A large library** is tested two ways. `tests/test_scale.py` generates sixty small books (`fixture.build_many`: each its own mix of themes
and characters) and checks figures and limits; it runs in a few seconds. `tests/benchmark.py` times every analysis over a whole library of
real books, and `tests/make_corpus.py` makes such a library out of a few real books by cutting them into pieces (at paragraph boundaries,
each piece a complete export with its numbers counted again from 0; `--copies N` writes everything N times for a corpus N times as large):

```
python tests/benchmark.py                                   # sixty generated books
python tests/benchmark.py --sources /path/to/your/books # your own books (only read); add --data some/folder to keep the parsed-book cache
python tests/make_corpus.py --from output/* --out /tmp/corpus --books 60    # sixty books cut from real BookNLP output
python tests/benchmark.py --sources /tmp/corpus
```

It prints each request's time and size, marks anything slower than `--slow` seconds (default 2) and any rise of peak memory, and ends with the
peak memory in use. `python tests/serve_fixture.py --many 60` serves sixty generated books in a browser.

**The test corpus** (`tests/fixture.py`) generates three small "books" in BookNLP's file layout, from a seeded random generator, with
hand-written dependency parses, entities and quotes, a first-person narrator (alpha), chapter headings and four vocabulary themes
(moor, goose, room, case). While generating, it counts the truth: mentions per character, quotes and words per speaker, the verbs a
character does, possessions, prepositions, vocatives. Tests compare the analyser's numbers with these counts, so they check
*correctness*, not just that code runs. `tests/serve_fixture.py` serves the same corpus in a browser.

| File | What it covers |
|---|---|
| `test_bookdata.py` | parsing against the truth; damaged and partial files; spacing and marks in rebuilt text |
| `test_library.py` | scanning, versions and pinning, the pickle cache, atomic saving, tags, links (entities and narrator roles), rejections, corrections; settings files of the wrong shape; a book being parsed not blocking the library; warm-up progress |
| `test_stats.py` | p-values and effect sizes against SciPy and by hand; keyness filtering; the trend test against the correlation identity; the trends and χ² of several texts combined |
| `test_plural.py` | plural groups: what can be declared and what is refused, declarations on linked entities, suggestions, the group counted with and without its members' credit (mentions, forms, relations, who appears with whom, speech, addressees), the plural copy sharing the tokens, the setting and the per-request choice |
| `test_cases.py` | the cases of the Statistics tab, counted straight from the books: text pieces (slices by number or by words, sentences, chapters, books, in a scope) and participants with each kind of sample, the minimum, what is left out, the token lookup |
| `test_variables.py` | the variables of the Statistics tab: queries, mentions, speech (words, quotes, a sentence type, % of quotes) and attributes in each case's sample, the three measures, variables that don't fit the cases (a note, not an error), the bulk lists (also by sentence type and as speech verbs; the most talkative speakers) |
| `test_layers.py` | the linguistic layers as variables (supersenses, relations, sentiment, lexicon categories, speech sentence types, style figures, word choice (equal to the Style profile for whole books, to a count over a speaker's quotes, shares of verbs, computed once per cases), sound and rhythm figures, topics), against the figures the Style page gives for whole books; sound of speech against a tally of the quotes, one tally per setting shared by every sound variable, the dictionary missing |
| `test_help.py` | the help drawer's texts (`static/js/help-*.js`): one page per file, unique section ids, `help.js` loaded first; the keyness settings, entity types, relations and mention kinds have entries; every Dialogue tab has a section, every addressee method and sentence type an entry; every Corpus tool a section, every pattern attribute, sort key, collocation measure and search setting an entry; every `#/narrative` page and Sound tab a section, every style figure and run kind an entry; every topic fit setting, method, comparison tab and grid an entry; every Over the book tab, view, order and curve category, every Described-as list, split and voice, every network link kind and measure an entry; every tab and [...] page (`data-tab` in index.html), the chapter editor and the profile have a help file loaded by index.html; every Settings section and text-view layer has an entry; the Statistics help keeps up with the server: a section per variable kind, an entry per option (measures, mention kinds, attributes, relations, sentiment, style and sound figures, word-choice sections and the figures named in them, cases, samples, coefficients, corrections, splits) |
| `test_statstab.py` | the Statistics tab: correlation matrices and grids, corrected p-values, descriptives and splits, saved sets, the routes |
| `test_rexport.py` | the R export: the files read back with `csv` and checked against the page's own figures, column names, the long file, what was dropped |
| `test_described.py` | Described as: who describes a target as what, counted straight from the quotes and mentions; every split, voice and kind, the evidence behind a cell, your own columns |
| `test_overbook.py` | the Compare page's two sides (one book when a book holds both, else each in its own, e.g. two whole books); two books aligned (each side in its own book, the same relative slices, nothing left out of the second side, defaults, similarity against `stats.correlate`, `curve`); per-slice figures add up to the book-by-book ones for every slicer setting; a finding is in the slice of its mention (counted again by brute force); kinds of action; a linked person counts only the asked book; all the books together (combining by the book: counts added, shares averaged, Stouffer trend and added χ² against hand-made data, one book equals its own table, each book's own values, refusals); the other side of a comparison; the slice limit; χ² and trend of rising, level, rare and gappy words; the sound of the target's speech per slice (against a tally of its quotes), in the curve, books combined (the mean of the books) and two books aligned |
| `test_view.py` | minimums and counting modes, linking, profiles, distinctiveness, evidence, book by book, book and gender pools |
| `test_corpus.py` | the query languages, batch queries (merging, the matched line, patterns too), concordance counts against the truth, scopes, near-word filter, sort levels, context search, lists, word-type filters (counted straight from the files), collocates, keywords, reference files |
| `test_dialogue.py` | quotes, verbs, conversations (against an independent count), addressees, your corrections, style, narrators, sentence type (by punctuation and by speech verb) and its filter in quotes/style/voice/entity |
| `test_narrative.py` | segments, your chapter edits, arcs adding up to the totals, style figures, stylometry, sentiment, lexicon arcs |
| `test_sound.py` | pronunciation: the syllable guess, reading corrections (and refusing bad ones), the dictionary missing, variants by word class, abbreviations, British spellings, hyphens and plurals, guesses, your corrections first, stress in context and joined contractions in a small book, the cache per set of corrections, coverage of the fixture books (dictionary tests skip without `cmudict`) |
| `test_soundtab.py` | the Sound and rhythm tab: the guessed words (counted straight from the pronunciations), a corrected word leaving that list, looking a word up; narration and dialogue split the words, one speaker's quotes, tallies kept per scope and setting (and only the most recent within a budget per book), figures equal to the Style page's for the whole text, cadences and runs adding up to the tallies, their examples (totals, longest first, marks, repetitions outlined in sound runs), refusals, the scansion (tokens, stresses, outside the scope, cut after the most words) |
| `test_prosody.py` | sound and rhythm figures on tiny hand-made books (`fixture.tiny_book`) with stresses set by corrections: clashes, lapses, gaps and nPVI, phrases at pauses and gaps (not hyphens), cadences and cursus names, function words, alliteration chains and the window, alliteration by stressed syllable, first sound or first letter, repetition by lemma, form or all words (and repeats kept out of sound runs), repeats and function words, each boundary, a sample that skips words, rhyme / assonance / consonance, the stressed syllable's onset, the profile, tallies adding up, settings refused (skips without `cmudict`) |
| `test_wordchoice.py` | word-choice tallies and figures: part-of-speech shares equal the Style profile, supersense spans counted where they start, tallies adding up, the ratios and verb groups on hand-made tallies, figures without a divisor |
| `test_lexicons.py` | parsing (word lists and word–category lines), storing, ids, names, the emotion lexicon, limits, damaged files, editing categories, and the routes |
| `test_narrators_network_links.py` | narrator suggestions (including a stretch told by someone else), networks and exports, link suggestions |
| `test_reader.py` | the text view: balanced marks, layers, jumping to a token, narrators, topics, paragraph and sentence numbers, finding a place without marking it; the sound layer (a mark for every word with a pronunciation, its stresses, runs, repetitions and cursus ends against the segment's tally; the dictionary missing) |
| `test_export.py` | the export zip: what goes in, the state cut down to the selected books (persons, collections, groups, plurals, narrator links), topic models and references, the books readable again |
| `test_localonly.py` | Host and Origin checks: foreign names, forged and null origins, other ports, our own page, scripts, reading; `--allow-host` (the tunnel's name and its https page allowed, nothing else; what the option accepts); and the start-up helpers of `app.py` (a port already taken, progress notes while the books are read) |
| `test_kept.py` | what is kept on a book: made once, the least recently used dropped past the entries or the budget (the newest always kept), a limit required, many threads at once, one per owner, not in the plural copy |
| `test_statecheck.py` | a workspace's files with parts of the wrong shape: a good file unchanged, a whole part starting empty, entries left out and counted, a person's readable members kept and an entity in one person, a narrator role in one link, `next_…` numbers above the ids in use, book details, unknown parts kept, damaged corrections; a damaged workspace and an imported export with damaged parts open and every main page works, with notes for the Library page |
| `test_bookcache.py` | the cache round trip, a real cache fully allowed, code in a cache refused and not run, a poisoned cache rebuilt |
| `test_workspaces.py` | the list of workspaces and the active one, creating/renaming/forgetting, deleting (the typed name, only folders the analyser made), importing an export zip (and refusing bad ones without leaving anything), the books folder (always read, made again, an old import's entry dropped), opening folders (only known ones; a missing one or no file browser names the path), and the routes: switching between workspaces keeps their work apart, a damaged one is refused, switching under load |
| `test_bookcollections.py` | collections: nesting, several per book, names, moving without cycles, deleting, saving, routes |
| `test_groups.py` | groups pooled against the entities' figures, members not counted as outsiders, saved groups following links and the selection, narrators as entities, group and narrator routes |
| `test_topics.py` | settings, documents, words, fitting and its reproducibility, recovery of the four themes, storage, every part of a topic's page, comparisons, uses elsewhere |
| `test_edge_cases.py` | books with no quotes, no entities, or one sentence, through every analysis (Statistics with every kind of case and layer, Described as, sound and rhythm in every scope, Books combined cut into more slices than a book has tokens); book ids full of characters that mean something in files, addresses and headers (colon, `#`, `%`, accents, Japanese) through the main routes and the download names |
| `test_robustness.py` | damaged and unusual files: byte-order marks, Windows line endings, other encodings, missing columns, numbers that aren't numbers, lines outside the book, an unreadable book among good ones; the same answers whatever the hash seed (a quote that addresses two people, networks, dialogue, stylometry) |
| `test_scale.py` | sixty generated books: the right figures over many books, a limited search still reaching the later books, a network cut to the strongest entities, link suggestions and patterns in good time, strings shared |
| `test_api.py` | every route (the export download included), its errors, your corrections end to end, paging, concurrent requests, topics switched off |
| `test_state_fuzz.py` | random sequences of changes to your work (linking and unlinking entities and narrator roles, corrections, tags, rejections, resetting every link, plural-group declarations), checking after every change that an entity is in one person at most, no correction names a person that is gone, narrator links keep two roles, a plural group is never a member, and every book reads with plural groups counted either way |
| `test_api_fuzz.py` | every route is sent a valid request, then the same with each field (and each field of an object field) replaced by something of the wrong kind (nothing, text, huge or fractional numbers, lists, objects), and bodies that aren't JSON objects: never a 500, always a message. A route without an entry in `BODIES` fails the test, so a new route can't be forgotten |
| `test_frontend.py` | runs `tests/js` (below) against a live server: the three-book corpus, sixty-four generated books, and a library with no books |
| `test_docs.py` | every module, class and function has a docstring, every top-level browser function a comment (above it, or at the end of a one-line helper's line), every script a header comment |
| `test_design.py` | `docs/DESIGN.md` against the code: its token block equals `app.css` and `core.js` (colours in both themes, type colours, palette, fonts, breakpoints, z-indexes, radii), its contrast ratios are right, rule IDs are unique and defined, every rule of the editor's language has a row (when the editor sits beside this project), and `static/` never sets HTML |

**Browser tests** (`tests/js`, Node + jsdom; the page is loaded from a live server in a simulated browser): `smoke.mjs` visits every
page; `interactions.mjs` clicks and types through the main features (editing books, collections and search, exporting a zip, workspaces (make, rename, switch, remove, delete by typing the name), filtering, narrators (including
linking them and assigning one to a whole chapter), select several and groups, Compare groups and two books split into characters, book and
gender overview pages, opening profiles, correcting a quote, searching with sort levels, a context search, word-type filters and a batch
query with its Matched column, the sentence-type filter in Quotes/How they speak/an entity's Speech, the scrolling
text view and the chapter editor, the network focus, fitting a topic model, folding sections…); `units.mjs` tests the helper functions;
`many.mjs` opens the main pages over many books and checks that charts stay a bounded size; `empty.mjs` opens every page of a library with no
books (a new install) and checks that none breaks and that the Library page points to Settings, where the folder form is.
`harness.mjs` holds the shared helpers. `page.go(hash)` waits for the new page to start drawing before it waits for it to settle (else, under load, it could settle on the page before it and a check would see the old page).
Run one by hand against a server:

```
python tests/serve_fixture.py --port 8799 &
cd tests/js && node smoke.mjs http://127.0.0.1:8799
```

## 10. Extending the analyser

*A new analysis.* 1) Write the function in a `core/` module, taking a `View` (or `Library`) and plain arguments, returning a dict of
JSON-friendly values, raising `ValueError` (or a subclass) with a helpful message for input that can't be used. 2) Add a route in the
matching `api/` router: read the body with the helpers of `api/context.py` (`whole`, `real`, `need`, `need_str`, `text`, `choice`, `mapping`,
`items`, `str_list`: they give readable errors), call the function, return it; give the route a one-line docstring (it appears in the table above)
and a row in the table of section 7 (`test_docs.py` compares it with the real routes). 3) Add a `renderX` page or a section in the matching `static/js` file; use
`api()`, `withBooks()`, `table()`, `note()`. 4) If it is a new page, add it to its area in `AREAS` (`areas.js`) and to the router in `main.js`.
5) Add tests: the function against the fixture (add a counted truth to `tests/fixture.py` if you need one), the route in `test_api.py`,
a valid request for it in `BODIES` of `test_api_fuzz.py` (which then sends it wrong input too), the page in `tests/js/smoke.mjs` (and
`interactions.mjs` if it has controls).

*A new kind of value in `BookData`* (a class other than a list, set, dict, tuple, `Counter`, `defaultdict`, `array`, `Path`, `BookData`, `Group`): add it to
`bookcache.ALLOWED`, or the cache silently stops working (`test_bookcache.py` catches it) and every start re-parses the books.

*A new part of a topic's page.* Add `part_x` in `core/topics/page.py` (use `Topic`, `assoc`, `group_rows`), a branch in `api/topics.py`'s
`page` route, a section in `static/js/topic-page.js`, and its explanatory text in `notes.py`.

*A new explanatory note.* Put the text next to the code it describes (`NOTES` dictionaries); `api/library.py` sends them to the browser.

## 11. Large libraries

Measured on real BookNLP output (the novels and stories in the author's `output` folders), cut by `tests/make_corpus.py` into **60 books**
(418,000 tokens, 4,700 entities at the default minimum of two mentions), and into **180 books** (the same pieces three times: 1.25 million tokens,
14,000 entities). The corpus used before 2026-10-14 was 60 whole and cloned books of 760,000 tokens; its figures are in the git history. `tests/benchmark.py`
reproduces the figures on any set of books. Memory is the main cost of size; time is mostly spent once, the first time something is asked. Last
measured 2026-10-14 (Python 3.10, macOS): every page's requests together (60 requests) take 12 s for 60 books and 30 s for 180.

| | 60 books (418,000 tokens) | 180 books (1.25 million tokens) |
|---|---|---|
| Reading every book the first time | 2.9 s (parsing) | 8.5 s |
| Reading them again, from the cache | 0.5 s | about 2 s |
| Memory with every book loaded | 400 MB (about 480 bytes a token) | 770 MB |
| Memory after using every page | 810 MB at the most | 1.5 GB at the most |
| A page of results | under 0.4 s for most; the slowest first-time requests (sentiment, the entity network, n-grams of up to five words) take 1–1.3 s | the slowest (sentiment 3.9 s, n-grams 2.7 s, style per book or slice 2.3 s) are those that read every token once |
| The cache folder | about twice the size of the books' own files | |

Re-measured 2026-10-23 on the same 60 books with the benchmark's 77 requests (now also Described as, Statistics with every kind of
variable, and every sound and rhythm request): 44–59 s in all (44 s and 680 MB at the most after `kept.Kept` replaced the caches that
emptied themselves when full), books read again from the cache in 0.8–2.7 s (first parse 9.5 s on a busier machine), 370–400 MB with
every book loaded and 780 MB at the most. The slowest first-time requests are the sound and rhythm figures, which
pronounce and scan every word once per setting: the sound figures for all 60 books take 6–10 s (Sound → Figures, or a sound figure on Style's chart), the cadences or the figures of
one scope 2–4 s; after that they are kept (`prosody.span_tally`, `soundtab.tally_of`, the latter within a budget per book) and come back at once.

Re-measured 2026-10-24 on the same 60 books after word choice (`wordchoice.py`) was added, with the benchmark's 83 requests: 37 s in all, 794 MB at
the most, books read from the cache in 0.8 s. The word-choice requests are all quick: the Style page's table 0.2 s per book and 0.4 s per slice (a
1.8 MB answer: every figure of 600 slices), Dialogue's Speaking style with the key figures 0.6 s (0.4 s without), the voice comparison 0.3 s, a
character's Speech panel 0.3 s (the tally of everyone's 199,000 spoken words in it takes 0.09 s), Statistics with seven word-choice variables
over slices 0.4 s and over speakers 0.6 s. Over every sentence of the 60 books (25,000 cases) seven word-choice variables take 1.8 s and 33 MB:
a case keeps its tally and each variable takes only its own figure (`wordchoice.value`), where keeping every figure of every case cost 280 MB.

Stylometry of slices refuses more than 400 texts (a message, not a failure); with 180 books ask for books, or fewer slices.

What keeps it that way, and what to keep doing when adding something:

* **Cut before you count.** Anything that pairs things up across the whole library (a network, link suggestions, n-grams) has a limit that is
  applied early: `network.build`'s `max_nodes`, link candidates only from shared name parts, n-gram rows made only for the ones shown (`heapq.nlargest`).
  Lists returned to the browser are cut to a size a page can show (5,000 word-list and n-gram rows, 20,000 concordance hits and 500 lines a page, 300 link suggestions).
* **Never rebuild a whole structure inside a loop** (`set(G)` per quote made a dialogue network take three seconds instead of a tenth).
* **Keep what is derived from a book on the book** (`BookData.kept(owner, …)`), keyed by everything it depends on, with a limit
  (a number of entries, or a size budget for large results); see the table in section 5.
* **Share, don't copy, per-token values**: a list of words made from a book takes them from `cindex`'s shared `lower`/`lemma_lower`
  tables (a pointer a word, not a new string), and a per-token index is a flat array (`dependents`), not a dict of lists.
* **Keep dense matrices out of topics**: documents × words are sparse (`npmi_coherence` takes a sparse matrix; a dense one for thousands of documents would run to gigabytes).
* **Memoise what cannot change within a call** (`Matcher.hits` for repeated pattern parts) and **read only what is shown**
  (`kwic_lines`, rows of lists).
* **Write a test with many books** (`tests/test_scale.py`) when a new feature compares or combines books.

## 12. Robustness decisions

* **No crash on bad input.** Everything the browser sends is read through `api/context.py`: numbers with `whole`/`real`/`maybe_whole` (a readable
  400 if they aren't numbers, or are infinite or NaN, which Python's JSON accepts), ids with `need_str`, text with `text`, a name from a
  fixed set with `choice` (it lists the names), objects with `mapping` (`{}` if absent), lists with `items` / `str_list` (a single string where a list belongs is
  refused, not split into letters), the plural choice with `plural_choice` (only true or false). A target (spec) passes `view.check_spec`, the
  search settings `corpus.clean_settings`, a word-type filter `corpus.token_test`, and a name looked up in a table `bookdata.one_of`, so a list
  or an object where a plain value belongs is a message, not a `TypeError` from a dictionary lookup. Searches that can't run (`QueryError`) and
  topic requests that can't be met (`TopicError`) say why. A route that changes several things (`/api/settings`) checks every value first, so a request
  with one bad value changes nothing. `test_api_fuzz.py` enforces all of this on every route; `test_input_of_the_wrong_kind_is_a_readable_error` is the readable-message check.
* **Downloads with any name.** A header can only hold plain characters, so `api/context.attachment` sends a file name with others (a book
  called "Émile", a Japanese title) as a plain-text version and as itself (RFC 6266); it used to be a crash.
* **Books are read defensively**: blank lines skipped, missing optional files and columns fine, byte-order marks and Windows line endings fine, a file that
  isn't UTF-8 refused with a message, out-of-range positions and unreadable lines skipped and reported (a supersense span can't run past the
  book), and one unreadable book never stops the others (`View.problems`, the Library page).
* **Limits protect the server**: a pattern search can't blow up (memoised repeats); a network, a list or a search that could grow without bound is cut and says so.
* **Settings files must be objects.** `library.json`, `annotations.json` and `workspaces.json` that hold valid JSON of another shape (a list, a number) are
  reported with the file's name, like damaged ones, and never overwritten.
* **A workspace's files are checked part by part** (`statecheck.py`) when they are opened, whether written by this aLex, edited by hand or
  imported from someone else's export: an entry of the wrong shape is left out, a damaged one keeps what can be read, the rules of linking
  are restored and the `next_…` numbers can't overwrite a saved group; the Library page lists what was left out. The file is not rewritten
  until you change something.
* **Sources and ids from the browser are checked**: a correction to a book that doesn't exist is a 404 and invents nothing; statistics options
  that don't exist are refused with the list of those that do; `sources` must be a list; a damaged unit id is "not found", not a crash.
* **Writes are atomic**; a damaged settings file is reported, never replaced. A parsed-book cache that can't be written (a full disk, a read-only
  data folder) is skipped: the book still opens. A source folder that can't be listed is reported on the Library page, not a crash. A stored
  lexicon that can't be read is reported (`problem`) and can be replaced or removed.
* **Links stay consistent**: an entity is in at most one person and a narrator role in at most one narrator link (section 3, Identifiers).
* **The same answer every time.** Python orders a set of strings differently in every run (hash randomisation), so nothing may take "the first" of a
  set, or build a graph, from one: sort first (`_vocative` takes the mentions in a quote in reading order; `network.build` sorts the sources
  and targets it pairs and `network._subgraph` keeps a fixed node order, because `G.subgraph` goes through a set and the layout and the communities
  follow the order; floating-point measures of a network are rounded to ten decimals, since a sum over a set differs in its last digits). Topic
  models, patterns and statistics are deterministic (fixed seeds). `test_robustness.py` runs the same requests in several Pythons with different `PYTHONHASHSEED`s
  and compares the answers byte for byte.
* **Concurrency**: requests run in a thread pool. The view cache and the file writes are locked; what is kept on a book (`kept.Kept`)
  is locked while it is looked up or stored, but not while a result is made (two requests may make the same one; both get a correct answer); corrections take the library lock. Parsing a book (seconds for a novel) happens *outside* that lock, with a lock of the
  book's own (`Library._load`): a save or a request for another book is never held up by it, and two threads that want the same book parse it once.
  `Library.warm` (at start-up, and after switching workspace) reads every book in the background; at start-up the terminal says how far it is
  every 15 seconds when it takes that long (`app.warm_with_notes`).
* **Overlapping requests**: pages whose settings change quickly (corpus searches) let only the newest request fill the page.
* **Stale files**: browsers are told never to cache the scripts and style sheet (`Cache-Control: no-cache`), so an update shows at once.
* **Topic models** record each book's token count; a book that changed afterwards is flagged and passages are withheld rather than shown wrongly.
* **Text safety**: server text never becomes HTML in the browser.
* **Only you can reach it** (`localonly.py`). The server listens on 127.0.0.1, but a web page in your browser can still talk to it, so two things
  are checked on every request: `Host` must be `127.0.0.1` or `localhost` (otherwise a page on another domain could reach it by "DNS rebinding"), and a
  request that changes something (anything but GET/HEAD/OPTIONS) that carries an `Origin` must carry exactly our own (`http://<Host>`), so a form or
  script on another site, or a program on another local port, can't make your browser change your library. Requests with no `Origin`
  (`curl`, scripts) are allowed; reading requests are checked for `Host` only, since no CORS headers are sent. Test clients must therefore use
  `base_url="http://127.0.0.1"` (`fixture.LOCAL`). **For a demo**, `alex --allow-host NAME` (`build_app(allow_hosts=…)`, `LocalOnly(extra_hosts=…)`)
  also answers one exact public name, e.g. a Cloudflare tunnel's `abc.trycloudflare.com`, and accepts changes whose `Origin` is `http://` or
  `https://` that name (a tunnel serves https). `localonly.host_name` checks the option: a bare name or a pasted URL, no port, path or wildcard.
  It is off unless given, and the start-up message warns that anyone with the link can change things.
* **The cache can't run code.** A pickle can execute anything when opened, so `bookcache.loads` accepts only a parsed book's classes. When a
  new kind of value goes into `BookData`, add its class to `bookcache.ALLOWED`: `test_bookcache.py` opens a real cache and fails until you do.
* **Newer libraries**: the tests run in CI on Python 3.10 and 3.13 with the newest versions pip finds, which has caught real breaks (a GEXF export that newer
  networkx refused because of mixed number types, a Mann–Whitney `nan`, Python 3.13 pickling `Path` under another name).

## 13. Troubleshooting

* *"Something went wrong (…)" on a page*: the message names the error; the terminal has the traceback. Re-run with the failing action
  and look for a line starting `Error in POST /api/…`.
* *A book doesn't appear*: it needs `.tokens` and `.entities` in a folder listed under Settings → Folders.
* *Numbers look stale after re-exporting*: switch to the window (the analyser re-checks on focus) or reload; the parsed-book cache is keyed by
  file modification times, and deleting `alex-data/cache` is always safe.
* *Topics tab asks for scikit-learn*: `pip install -e .` again (or `pip install scikit-learn`), then restart.
* *Browser tests are skipped*: install Node, then `cd tests/js && npm install`.
* *Slow or heavy with many books*: the first start parses every book (a few seconds each for a novel; later starts read the cache). Run
  `python tests/benchmark.py --sources <your folder>` to see which request is slow and how much memory the books take, and see section 11. A network
  shows at most 300 entities (raise "Show at most", or raise the minimum link strength); the concordance stops at 20,000 hits.
