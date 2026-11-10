"""Wrong input to any route is a 4xx with a message, never a 500.

For every route of the API, `BODIES` holds a request that is valid. The test sends it, then sends it again once for every field in it
(and every field of the fields that are objects), replacing that one value by something of the wrong kind: nothing, text, a number
that is too big or too small, a list, an object. What comes back may be an answer or an error the user can read (a 4xx with a `detail`),
but never a crash (a 500). A route that is added to the API must be added here too: another test fails until it is.

The requests all run against a library of its own, so what a request changes (settings, links, corrections) never reaches another.
"""
from __future__ import annotations

import io
import json
import re
import zipfile

import pytest

ALL = ["alpha", "beta", "gamma"]
SEG = {"mode": "slices", "n": 3}
STAT = {"measure": "ll", "test": "ll", "min_freq": 1, "alpha": 0.05}
LEXICON = "word,category\nmoor,place\nhound,animal\n"

# What replaces a value: nothing, empty and odd text, numbers that are too small, too big or not whole, true, lists and objects.
JUNK = [None, "", "x", "1", 0, -1, 2 ** 70, 1.5, True, [], [1], ["x"], {}, {"kind": "zzz"}]


def spec(uid):
    """A target (unit) spec."""
    return {"kind": "unit", "id": uid}


U, V = "e:alpha:1", "e:alpha:2"             # Holmes and Watson of the book alpha (see fixture.BOOKS)


def make_bodies(u, v):
    """{(method, path): a valid request body} for every route; `u` and `v` are the ids of two entities."""
    unit, other = spec(u), spec(v)
    books = {"books": ALL}
    stats = {"cases": {"kind": "pieces", "piece": "slice", "n": 3, "min": 1}, "rows": [{"kind": "query", "query": "said"}, {"kind": "mentions", "target": unit}],
             "method": "pearson", "correction": "none", "split": "none"}
    b = {
        ("GET", "/api/library"): None, ("GET", "/api/books/{}/text"): None,
        ("POST", "/api/books/{}"): {"title": "T", "author": "A", "year": 1890, "series": "S", "tags": ["a"], "pinned": None},
        ("POST", "/api/export"): books,
        ("POST", "/api/collections"): {"name": "c", "parent": None},
        ("POST", "/api/collections/delete"): {"id": "1"},
        ("POST", "/api/collections/{}"): {"name": "d", "parent": None, "add": ["alpha"], "remove": []},
        ("POST", "/api/settings"): {"min": {"PER": 2}, "conv_gap": 50, "count_mode": "per_book", "freq_mode": "per_book", "plural_default": False, "sources": [],
                                   "sound": {"window": 4, "boundary": "paragraph", "alliteration": "letter", "repetition": "form",
                                             "corrections": {"grimpen": "1 0"}}},
        ("POST", "/api/units"): {**books, "type": "PER"},
        ("POST", "/api/tags"): {"id": u, "tags": ["t"]},
        ("POST", "/api/name"): {"id": u, "name": "N"},
        ("POST", "/api/note"): {"id": u, "note": "n"},
        ("POST", "/api/profile"): {**books, "id": u},
        ("GET", "/api/groups"): None,
        ("POST", "/api/groups"): {"name": "g", "ids": [u, v]},
        ("POST", "/api/groups/delete"): {"id": "1"},
        ("POST", "/api/groups/{}"): {"name": "h", "ids": [u]},
        ("POST", "/api/plurals"): {"id": u, "add": [v], "remove": []},
        ("POST", "/api/plurals/suggestions"): books,
        ("POST", "/api/plurals/reject"): {"id": u},
        ("POST", "/api/distinctive"): {**books, "target": unit, "reference": {"kind": "others"}, "rel": "agent", **STAT},
        ("POST", "/api/compare"): {**books, "a": unit, "b": other, **STAT},
        ("POST", "/api/compare/books"): {**books, "a": "alpha", "b": "beta", "top": 5},
        ("POST", "/api/bybook"): {**books, "target": unit, "rel": "mod", **STAT},
        ("POST", "/api/evidence"): {**books, "target": unit, "kind": "agent", "key": "say", "other": None, "within": [{"book": "alpha", "start": 0, "end": 50}]},
        ("POST", "/api/network"): {**books, "kind": "sentence", "types": ["PER"], "min_weight": 1, "keep_isolated": False, "focus": u, "focus_top": 5, "max_nodes": 20},
        ("POST", "/api/network/export"): {**books, "kind": "sentence", "format": "gexf"},
        ("POST", "/api/overbook"): {**books, "target": unit, "other": other, "book": "alpha", "seg": SEG, "rel": "mod", "curve_rel": "agent", "sound": True, **STAT},
        ("POST", "/api/overbook/compare"): {**books, "target": unit, "other": other, "book": "alpha", "other_book": "beta", "seg": SEG, "n": 4, "rel": "mod", **STAT},
        ("POST", "/api/overbook/combined"): {**books, "target": unit, "n": 4, "rel": "mod", "curve_rel": "agent", "curve": "snd:stressed", "sound": True, **STAT},
        ("POST", "/api/overbook/aligned"): {**books, "target": unit, "other": other, "book": "alpha", "other_book": "beta", "n": 4, "rel": "mod", **STAT},
        ("POST", "/api/described"): {**books, "target": unit, "kind": "mod", "split": "entity", "voice": "both", "top": 4, "limit": 10},
        ("POST", "/api/described/evidence"): {**books, "target": unit, "kind": "mod", "split": "entity", "voice": "both", "item": "dark", "column": None, "limit": 5},
        ("POST", "/api/stats"): {**books, "setup": stats},
        ("POST", "/api/stats/export"): {**books, "setup": stats, "example": True},
        ("POST", "/api/stats/options"): books,
        ("POST", "/api/stats/bulk"): {**books, "what": "words", "n": 3, "unit": "word", "filter": {"pos": ["NOUN"]}, "cases": stats["cases"], "measure": "per1k",
                                      "types": ["question"], "weigh_verb": False, "speech_verbs": False},
        ("GET", "/api/stats/sets"): None,
        ("POST", "/api/stats/sets"): {"name": "s", "setup": stats},
        ("POST", "/api/stats/sets/delete"): {"id": "1"},
        ("POST", "/api/stats/sets/{}"): {"name": "t", "setup": stats},
        ("POST", "/api/dialogue/overview"): books,
        ("POST", "/api/dialogue/verbs"): {**books, "target": unit, "types": ["question"], "weigh_verb": True, **STAT},
        ("POST", "/api/dialogue/voice"): {**books, "target": unit, "reference": {"kind": "others"}, "unit": "word", "types": ["question"], "weigh_verb": False, "wc": "ratios", **STAT},
        ("POST", "/api/dialogue/style"): {**books, "min_words": 5, "types": ["question"], "weigh_verb": False, "wc": "headline"},
        ("POST", "/api/dialogue/conversations"): {**books, "target": unit},
        ("POST", "/api/dialogue/quotes"): {**books, "filter": {"speaker": unit, "q": "the", "book": "alpha", "conv": 0, "attributed": "yes", "addressee": [v], "addr_method": "named",
                                                               "verb": "say", "word": "the", "lemma": "the", "types": ["question"]}, "limit": 10},
        ("POST", "/api/dialogue/entity"): {**books, "id": u, "types": ["question"], "weigh_verb": False},
        ("POST", "/api/dialogue/narrators"): books,
        ("POST", "/api/dialogue/scope"): {**books, "target": unit},
        ("POST", "/api/annot/quote"): {**books, "book": "alpha", "qi": 0},
        ("POST", "/api/annot/addressees"): {**books, "book": "alpha", "qi": 0, "addressees": [v]},
        ("POST", "/api/annot/conversation"): {**books, "book": "alpha", "qi": 1, "action": "split"},
        ("POST", "/api/annot/participants"): {**books, "book": "alpha", "first_qi": 0, "id": v, "action": "add"},
        ("POST", "/api/annot/narrator"): {"book": "alpha", "narrator": u},
        ("POST", "/api/annot/paragraphs"): {"book": "alpha", "pids": [1, 2], "narrator": v},
        ("POST", "/api/annot/chapter_narrator"): {**books, "book": "alpha", "pid": 1, "narrator": v},
        ("GET", "/api/annot/narrator_options"): None,
        ("POST", "/api/narrators/suggestions"): {**books, "max_gap": 2, "min_evidence": 1},
        ("POST", "/api/narrators/reject"): {"book": "alpha", "key": "k"},
        ("POST", "/api/narrators/link"): {"a": "nar:" + u, "b": "nar:" + v, "name": "n"},
        ("POST", "/api/narrators/unlink"): {"id": "nl:1", "role": "nar:" + u},
        ("POST", "/api/narrators/unlink_all"): {"id": "nl:1"},
        ("POST", "/api/corpus/kwic"): {**books, "query": "said", "mode": "simple", "settings": {"match": "word", "case": False}, "scope": {"kind": "dialogue"},
                                       "sort": ["R1", {"pos": "L1", "by": "lemma", "desc": True}], "near": {"item": "the", "left": 3, "right": 3}, "ctx": {"query": "the", "left": 3, "right": 3},
                                       "offset": 0, "limit": 10, "context": 5},
        ("POST", "/api/corpus/context"): {**books, "book": "alpha", "tok": 10, "end": 12},
        ("POST", "/api/corpus/filters"): books,
        ("POST", "/api/corpus/wordlist"): {**books, "unit": "word", "scope": {"kind": "all"}, "settings": {}, "min_freq": 2, "min_range": 1, "filter": {"pos": ["NOUN"]}},
        ("POST", "/api/corpus/ngrams"): {**books, "n_min": 2, "n_max": 3, "scope": {"kind": "all"}, "unit": "word", "settings": {}, "min_freq": 2, "min_range": 1, "contains": "the",
                                         "position": "any", "within_sentence": True},
        ("POST", "/api/corpus/collocates"): {**books, "query": "said", "mode": "simple", "settings": {}, "scope": {"kind": "all"}, "left": 3, "right": 3, "unit": "word", "min_freq": 1,
                                             "min_range": 1, "within_sentence": False, "sort": "mi", "filter": {"pos": ["NOUN"]}},
        ("POST", "/api/corpus/keywords"): {"books": ["alpha"], "reference": {"kind": "books", "books": ["beta"]}, "scope": {"kind": "all"}, "unit": "word", "settings": {},
                                           "negative": True, "min_range": 1, **STAT},
        ("GET", "/api/refs"): None,
        ("POST", "/api/refs"): {"name": "r", "files": [{"name": "a.txt", "text": "the moor and the hound"}]},
        ("POST", "/api/refs/delete"): {"id": "r"},
        ("POST", "/api/narrative/segments"): {**books, "seg": SEG},
        ("POST", "/api/narrative/arcs"): {**books, "seg": SEG, "kind": "entities", "ids": [u], "cats": ["verb.motion"]},
        ("POST", "/api/narrative/style"): {**books, "seg": SEG, "by": "segment"},
        ("POST", "/api/narrative/sound"): {**books, "seg": SEG, "by": "segment"},
        ("POST", "/api/narrative/wordchoice"): {**books, "seg": SEG, "by": "segment"},
        ("POST", "/api/sound/figures"): {**books, "seg": SEG, "by": "segment", "scope": {"kind": "speech", "speaker": unit}},
        ("POST", "/api/sound/cadences"): {**books, "scope": {"kind": "narration"}, "pattern": "10010", "end_only": True},
        ("POST", "/api/sound/runs"): {**books, "scope": {"kind": "dialogue"}, "kind": "repetition", "key": "say"},
        ("POST", "/api/sound/guessed"): {**books},
        ("POST", "/api/sound/lookup"): {"word": "Baskerville", "pos": "PROPN"},
        ("POST", "/api/sound/scan"): {**books, "book": "alpha", "seg": SEG, "index": 1, "scope": {"kind": "all"}},
        ("POST", "/api/narrative/stylometry"): {**books, "seg": SEG, "units": "segments", "mfw": 20, "culling": 0, "measure": "cosine", "linkage": "average", "scope": "all", "exclude_pronouns": True},
        ("POST", "/api/narrative/sentiment"): {**books, "seg": SEG, "ids": [u]},
        ("POST", "/api/read"): {**books, "book": "alpha", "seg": SEG, "index": 0, "tok": 5, "end": 6, "layers": ["entities", "quotes", "sound"], "topics": None, "mark": True,
                               "sound_colour": "rhyme"},
        ("POST", "/api/narrative/chapters"): {"book": "alpha", "action": "add", "pid": 3, "name": "n"},
        ("GET", "/api/lexicons"): None,
        ("POST", "/api/lexicons"): {"name": "lx", "text": LEXICON, "emotion": False},
        ("POST", "/api/lexicons/{}/replace"): {"text": LEXICON},
        ("POST", "/api/lexicons/{}/rename"): {"name": "lx2"},
        ("POST", "/api/lexicons/{}/delete"): None,
        ("GET", "/api/lexicons/{}/words"): None,
        ("POST", "/api/lexicons/{}/category"): {"category": "place", "name": "p", "text": "moor hill"},
        ("POST", "/api/lexicons/{}/category/delete"): {"category": "place"},
        ("POST", "/api/narrative/lexicon"): {**books, "seg": SEG, "lexicon": "lx", "cats": ["place"]},
        ("GET", "/api/topics/models"): None,
        ("POST", "/api/topics/fit"): {**books, "cfg": {"k": 3, "runs": 1, "min_df": 1}, "name": "m"},
        ("POST", "/api/topics/scan"): {**books, "cfg": {"runs": 1, "min_df": 1}, "ks": [2, 3]},
        ("POST", "/api/topics/model"): {"id": "m"},
        ("POST", "/api/topics/page"): {**books, "id": "m", "topic": 0, "part": "where", "seg": SEG, "n": 3, "book": "alpha"},
        ("POST", "/api/topics/compare"): {**books, "id": "m", "part": "pair", "a": 0, "b": 1, "seg": SEG, "by": "book", "kind": "mentions", "types": ["PER"], "min": 1, "limit": 5},
        ("POST", "/api/topics/entity"): {**books, "id": "m", "unit": u, "kind": "mentions"},
        ("POST", "/api/topics/rename"): {"id": "m", "name": "n", "topic": 0, "label": "l"},
        ("POST", "/api/topics/delete"): {"id": "m"},
        ("GET", "/api/links/suggestions"): None,
        ("GET", "/api/links/search"): None,
        ("GET", "/api/links/persons"): None,
        ("GET", "/api/links/narrator_links"): None,
        ("POST", "/api/links/auto"): None,
        ("POST", "/api/links/link"): {"a": u, "b": v, "name": "n"},
        ("POST", "/api/links/reject"): {"a": u, "b": v},
        ("POST", "/api/links/unlink"): {"id": "p:1", "book": "alpha", "coref": 1},
        ("POST", "/api/links/unlink_all"): {"id": "p:1"},
        ("POST", "/api/links/reset"): None,
        ("GET", "/api/workspaces"): None,
        ("POST", "/api/workspaces"): {"name": "w", "sources": []},
        ("POST", "/api/workspaces/activate"): {"id": "default"},
        ("POST", "/api/workspaces/forget"): {"id": "w"},
        ("POST", "/api/workspaces/delete"): {"id": "w", "name": "w"},
        ("POST", "/api/workspaces/import"): None,
        ("POST", "/api/workspaces/{}"): {"name": "w2"},
        ("POST", "/api/folders/open"): {"folder": "source", "index": 0, "workspace": "default"},
    }
    return b


BODIES = make_bodies(U, V)
FILLED = {"/api/books/": "alpha", "/api/collections/": "1", "/api/groups/": "1", "/api/stats/sets/": "1", "/api/lexicons/": "lx", "/api/workspaces/": "default"}    # a route's parameter
QUERIES = {"/api/annot/narrator_options": "?book=alpha", "/api/lexicons/{}/words": "?category=place", "/api/links/search": "?q=holmes&type=PER"}


def concrete(path):
    """The address a request for a route is sent to: the route's parameter filled in (the book alpha, group 1, the lexicon lx…) and, for a
    route that takes them, its query."""
    if "{}" in path:
        path = path.replace("{}", next(value for prefix, value in FILLED.items() if path.startswith(prefix)))
    return path + next((q for route, q in QUERIES.items() if re.fullmatch(re.escape(route).replace(r"\{\}", "[^/]+"), path)), "")


def variants(body):
    """The bodies to send for one valid body: the valid one, then one with each value (at the top, or one level in) replaced by each `JUNK`."""
    yield body
    if not isinstance(body, dict):
        return
    for k, value in body.items():
        for junk in JUNK:
            if junk != value:
                yield {**body, k: junk}
        if isinstance(value, dict):
            for k2 in value:
                for junk in JUNK:
                    yield {**body, k: {**value, k2: junk}}


def test_every_route_has_a_valid_request_here(client):
    """The routes of the API as its OpenAPI schema lists them (parameters written `{}`; the page and the static files are not API)."""
    schema = client.get("/openapi.json").json()["paths"]
    listed = {(m.upper(), re.sub(r"\{[^}]*\}", "{}", p)) for p, methods in schema.items() for m in methods if p.startswith("/api/")}
    assert listed == set(BODIES), f"BODIES in test_api_fuzz.py and the API differ: add {sorted(listed - set(BODIES))}, remove {sorted(set(BODIES) - listed)}"


def send(client, method, path, body):
    """One request; a raw body (the zip import) is sent as it is."""
    if path == "/api/workspaces/import":
        return client.post(path, content=body or b"not a zip", headers={"content-type": "application/zip"})
    if method == "GET":
        return client.get(path)
    return client.post(path, json=body) if body is not None else client.post(path)


def problem(r, method, path, body):
    """What is wrong with the answer to a request, if anything: a crash (500), or an error without a message to read."""
    where = f"{method} {path} {json.dumps(body, default=str)[:200] if body is not None else ''}"
    if r.status_code >= 500:
        return f"{where} -> {r.status_code} {r.text[:160]}"
    if r.status_code >= 400 and not (r.headers["content-type"].startswith("application/json") and isinstance(r.json().get("detail"), str)):
        return f"{where} -> {r.status_code} without a message: {r.text[:100]}"
    return None


@pytest.mark.parametrize("route", [pytest.param(r, id=f"{r[0]} {r[1]}") for r in sorted(BODIES)])
def test_wrong_input_is_never_a_crash(route, client):
    method, path = route
    body, url = BODIES[route], concrete(path)
    found = []
    for variant in variants(body):
        found.append(problem(send(client, method, url, variant), method, url, variant))
    if method == "POST" and path != "/api/workspaces/import":                # a body that isn't a JSON object at all
        for raw in (b"[]", b'"x"', b"5", b"null", b"{not json", b""):
            found.append(problem(client.post(url, content=raw, headers={"content-type": "application/json"}), method, url, raw.decode()))
    if method == "GET" and path in QUERIES:                                    # a required value of the query missing
        found.append(problem(client.get(url.split("?")[0]), method, url, None))
    if path == "/api/workspaces/import":                                  # an actual zip that is not an export, and an empty one
        for raw in (b"", _zip({"x.txt": "y"}), _zip({"manifest.json": "[]", "state/library.json": "{}"})):
            found.append(problem(send(client, "POST", url, raw), method, url, None))
    found = [f for f in found if f]
    assert not found, f"{len(found)} requests went wrong:\n" + "\n".join(found[:12])


def _zip(files):
    """A zip file's bytes holding the given {name: text}."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
    return buf.getvalue()
