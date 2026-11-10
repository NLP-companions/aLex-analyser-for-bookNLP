"""Books, settings, the entity list, tags and the export zip."""
from __future__ import annotations

import hashlib
import os
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, Body, HTTPException, Response
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from alex.core import bookcollections, corpus, dialogue, entitygroups, export, links, narrative, network, overbook, prosody, sound, stats
from alex.core.bookdata import RELATIONS, TYPES
from alex.core.library import default_state
from alex.core.view import REL_LABELS

from .context import Context, attachment, mapping, need_str, str_list, whole

MAX_SKIPPED = 500          # most speech verbs (and, separately, adverbs) you can leave out


def library_info(ctx: Context, topics):
    """The whole library page: books with their details and sizes, settings, and the explanatory texts and option lists
    the browser needs (sent once, so the interface never has to hard-code them)."""
    lib = ctx.lib
    found, problems = lib.scan()
    order = lambda b: (lib.meta(b)["series"].lower(), str(lib.meta(b)["year"]), lib.meta(b)["title"].lower())
    books = []
    for bid in sorted(found, key=order):
        row = {"id": bid, **lib.meta(bid), "folder": str(lib.folder_for(bid)), "versions": found[bid], "narrator": narrator_of(lib, bid)}
        try:
            bd = lib.book(bid)
            row.update(tokens=bd.n_tokens, words=bd.n_words, sentences=bd.n_sents, paragraphs=bd.n_paras, mentions=len(bd.mentions),
                       groups=len(bd.groups), quotes=len(bd.quotes), problems=bd.problems, has_text=bd.has_original,
                       signature=hashlib.sha1(repr(lib.book_key(bid)).encode()).hexdigest()[:12])   # changes when a new export arrives
        except Exception as e:  # noqa: BLE001 - show the book with its error instead of failing the whole page
            row.update(error=str(e))
        books.append(row)
    topic_notes = {}
    if topics:
        topic_notes = {**topics.NOTES, **{"page_" + k: v for k, v in topics.PAGE_NOTES.items()},
                       **{"cmp_" + k: v for k, v in topics.COMPARE_NOTES.items()}}
    return {"books": books, "collections": bookcollections.listing(lib), "groups": entitygroups.listing(lib), "sources": lib.state["sources"], "problems": problems,
            "state_notes": lib.state_notes,
            "books_dir": str(lib.books_dir), "data_dir": str(lib.data_dir),
            "settings": lib.state["settings"], "default_settings": default_state()["settings"], "types": TYPES, "tags": lib.all_tags(),
            "relations": [{"id": r, "label": REL_LABELS[r]} for r in RELATIONS],
            "measures": stats.MEASURES, "tests": stats.TESTS, "stat_notes": stats.NOTES, "across_note": stats.ACROSS_NOTE,
            "network_kinds": network.KINDS, "network_notes": network.NOTES,
            "dialogue_notes": dialogue.NOTES, "addr_methods": dialogue.ADDR_METHODS, "verb_methods": dialogue.VERB_METHODS,
            "corpus_attrs": corpus.ATTRS, "sort_by": corpus.SORT_BY, "coll_measures": corpus.COLL_MEASURES, "coll_note": corpus.COLL_NOTE,
            "narrative_notes": narrative.NOTES, "overbook_notes": overbook.NOTES, "vader": narrative.vader_available(),
            "sound": sound.available(), "sound_missing": sound.MISSING, "sound_figures": prosody.figure_list(),
            "topics_ready": topics is not None, "topic_notes": topic_notes, "topic_defaults": topics.DEFAULTS if topics else {}}


def narrator_of(lib, bid):
    """The narrator you chose for a book as {id, name} (None: an unnamed narrator), so a page can name it without asking for the
    book's whole list of people."""
    uid = lib.ann["books"].get(bid, {}).get("narrator")
    if not uid:
        return None
    try:
        return {"id": uid, "name": links.unit_name(lib, uid)}
    except Exception:  # noqa: BLE001 - a damaged id or an unreadable book: still show the id
        return {"id": uid, "name": uid}


def router(ctx: Context, topics) -> APIRouter:
    """Routes for the library: books, settings, the entity list and tags."""
    r = APIRouter()
    lib = ctx.lib

    @r.get("/api/library")
    def library():
        """The library page's data."""
        return library_info(ctx, topics)

    @r.post("/api/books/{bid}")
    def set_book(bid: str, body: dict = Body(...)):
        """Change a book's title, author, year, series, tags or pinned export."""
        if bid not in lib.found():
            raise HTTPException(404, "That book isn't in the library.")
        patch = {k: str(body[k] or "").strip() for k in ("title", "author", "series") if k in body}
        if "year" in body:
            patch["year"] = "" if body["year"] in ("", None) else whole(body, "year", None)
        if "tags" in body:
            patch["tags"] = sorted({t.strip() for t in str_list(body, "tags") if t.strip()})
        if "pinned" in body:
            patch["pinned"] = str(body["pinned"]) if body["pinned"] else None
        lib.set_meta(bid, patch)
        return lib.meta(bid)

    @r.get("/api/books/{bid}/text")
    def book_text(bid: str):
        """The original .txt the book was exported from, for download; 404 if none was found next to its other files."""
        if bid not in lib.found():
            raise HTTPException(404, "That book isn't in the library.")
        bd = lib.book(bid)
        if not bd.has_original:
            raise HTTPException(404, "No original text file was found for this book.")
        return Response(bd.raw_bytes, media_type="text/plain; charset=utf-8",
                         headers={"Content-Disposition": attachment(f"{bid}.txt")})

    @r.post("/api/export")
    def export_zip(body: dict = Body(...)):
        """The selected books and your work on them as one .zip, for download (see core/export.py for what it holds)."""
        books = ctx.selected(body.get("books"))
        handle, path = tempfile.mkstemp(suffix=".zip")
        os.close(handle)
        try:
            export.write_zip(lib, books, path)
        except BaseException:
            os.unlink(path)
            raise
        return FileResponse(path, media_type="application/zip", filename=time.strftime("analyser-export-%Y%m%d-%H%M%S.zip"),
                            background=BackgroundTask(os.unlink, path))          # the temporary file goes once it has been sent

    def collection_reply(cid=None):
        """What every collection route returns: the collections as they are now (and the id of the one just made)."""
        return {"collections": bookcollections.listing(lib), "id": cid}

    def in_collection(action, *args, **kw):
        """Run a change to collections, turning an unknown id into a 404 and unusable input (ValueError) into the usual 400."""
        try:
            return action(lib, *args, **kw)
        except KeyError:
            raise HTTPException(404, "That collection doesn't exist.") from None

    @r.post("/api/collections")
    def collection_new(body: dict = Body(...)):
        """Make a collection, at the top level or inside another."""
        parent = body.get("parent")
        return collection_reply(in_collection(bookcollections.create, body.get("name"), str(parent) if parent is not None else None))

    @r.post("/api/collections/delete")
    def collection_delete(body: dict = Body(...)):
        """Remove a collection (its books stay; its sub-collections move up)."""
        in_collection(bookcollections.delete, need_str(body, "id"))
        return collection_reply()

    @r.post("/api/collections/{cid}")
    def collection_change(cid: str, body: dict = Body(...)):
        """Rename a collection, move it, or add and remove its books."""
        kw = {k: str_list(body, k) for k in ("add", "remove") if k in body}
        if "name" in body:
            kw["name"] = body["name"]
        if "parent" in body:
            kw["parent"] = str(body["parent"]) if body["parent"] is not None else None
        in_collection(bookcollections.update, cid, **kw)
        return collection_reply(cid)

    @r.post("/api/settings")
    def settings(body: dict = Body(...)):
        """Minimum mentions, how to count them (`count_mode`), how to count word frequencies (`freq_mode`: "combined" over the selected books
        or "per_book"), whether plural groups' mentions count for their members, the conversation gap,
        the speech verbs and adverbs to leave out (`speech_skip`: `{"verbs": [...], "adverbs": [...]}`, a list you send replaces the saved one),
        the sound and rhythm settings (`sound`: `{"window": n, "boundary": "sentence" | "paragraph" | "none", "alliteration": "stressed" |
        "sound" | "letter", "repetition": "lemma" | "form" | "all", "corrections": {word: pronunciation}}`, any of them; corrections sent
        replace the saved ones, each checked by `sound.check_corrections`)
        and the source folders. Everything is checked first, so a request with one bad value changes nothing."""
        mins = {t: whole({"n": n}, "n", 2, 1) for t, n in mapping(body, "min").items() if t in TYPES}
        gap = whole(body, "conv_gap", 100, 0) if "conv_gap" in body else None
        skip = None
        if "speech_skip" in body:
            given = mapping(body, "speech_skip")
            skip = {k: sorted({w.strip().lower() for w in str_list(given, k) if w.strip()}) for k in ("verbs", "adverbs")}
            if any(len(v) > MAX_SKIPPED for v in skip.values()):
                raise ValueError(f"At most {MAX_SKIPPED} verbs and {MAX_SKIPPED} adverbs can be left out.")
        snd = {}
        if "sound" in body:
            given = mapping(body, "sound")
            if "window" in given:
                snd["window"] = prosody.check_window(given["window"])
            if "boundary" in given:
                snd["boundary"] = prosody.check_boundary(given["boundary"])
            if "alliteration" in given:
                snd["alliteration"] = prosody.check_alliteration(given["alliteration"])
            if "repetition" in given:
                snd["repetition"] = prosody.check_repetition(given["repetition"])
            if "corrections" in given:
                snd["corrections"] = sound.check_corrections(given["corrections"])
        sources = None
        if "sources" in body:
            if not isinstance(body["sources"], list):
                raise ValueError("“sources” should be a list of folders.")
            sources = list(dict.fromkeys(str(Path(str(x)).expanduser()) for x in body["sources"] if str(x).strip()))
        with lib.lock:
            s = lib.state["settings"]
            s["min"].update(mins)
            if gap is not None:
                s["conv_gap"] = gap
            if body.get("count_mode") in ("per_book", "combined"):
                s["count_mode"] = body["count_mode"]
            if body.get("freq_mode") in ("per_book", "combined"):
                s["freq_mode"] = body["freq_mode"]
            if isinstance(body.get("plural_default"), bool):     # not "plural": every request carries that (a page's own choice)
                s["plural"] = body["plural_default"]
            if skip is not None:
                s["speech_skip"] = skip
            if snd:
                s["sound"] = {**prosody.config(s), **snd}
            if sources is not None:
                lib.state["sources"] = sources
                lib.reset_scan()
            lib.save()
        return library_info(ctx, topics)

    @r.post("/api/units")
    def units(body: dict = Body(...)):
        """The entity list of the selected books."""
        v = ctx.of(body)
        return {"rows": v.unit_rows(body.get("type")), "type_counts": v.type_counts(), "narrators": dialogue.narrator_rows(v),
                "genders": v.genders(), "problems": v.problems, "words": sum(bd.n_words for bd in v.bd.values())}

    @r.post("/api/tags")
    def tags(body: dict = Body(...)):
        """Replace an entity's or linked person's tags."""
        uid = need_str(body, "id")
        try:
            lib.set_tags(uid, str_list(body, "tags"))
        except KeyError:
            raise HTTPException(404, "That entity or person doesn't exist.") from None
        return {"tags": lib.tags_of(uid), "all": lib.all_tags()}

    @r.post("/api/name")
    def name(body: dict = Body(...)):
        """Rename an entity or linked person (blank goes back to the name found in the books)."""
        uid = need_str(body, "id")
        try:
            lib.set_name(uid, str(body.get("name") or ""))
        except KeyError:
            raise HTTPException(404, "That entity or person doesn't exist.") from None
        return {"name": lib.name_of(uid)}

    @r.post("/api/note")
    def note(body: dict = Body(...)):
        """Give an entity or linked person a short free-text description (blank clears it)."""
        uid = need_str(body, "id")
        try:
            lib.set_note(uid, str(body.get("note") or ""))
        except KeyError:
            raise HTTPException(404, "That entity or person doesn't exist.") from None
        return {"note": lib.note_of(uid)}

    return r
