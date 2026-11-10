"""Arcs, style, sound and rhythm, stylometry and sentiment; and the text view (lexicon arcs are in lexicons.py)."""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from alex.core import narrative, prosody, reader, sound, wordchoice

from .context import Context, choice, items, mapping, maybe_whole, need_str, plural_choice, real, str_list, whole

BY = ("book", "segment")           # a style or sound table has a row per book, or per chapter or slice


def router(ctx: Context, topics) -> APIRouter:
    """Routes for arcs, style, sound and rhythm, stylometry, sentiment and the text view."""
    r = APIRouter()

    @r.post("/api/narrative/segments")
    def segments(body: dict = Body(...)):
        """The chapters or slices of the selected books."""
        segs, info = narrative.all_segments(ctx.of(body), body.get("seg"))
        return {"segments": segs, "info": info}

    @r.post("/api/narrative/arcs")
    def arcs(body: dict = Body(...)):
        """Something counted per segment: entities, events, supersenses, dialogue or topics; with the Timeline "combined", put together
        across the books (`each`: every book's own line too)."""
        v, each = ctx.of(body), bool(body.get("each"))
        if body.get("kind") == "topics":
            if topics is None:
                raise HTTPException(400, "Topic modelling needs scikit-learn. Run: pip install scikit-learn")
            return narrative.timeline(topics.arc_series(v, body.get("model"), [whole({"id": i}, "id", None) for i in items(body, "ids")], body.get("seg")), body.get("seg"), each)
        return narrative.timeline(narrative.arcs(v, body.get("seg"), body.get("kind", "entities"), str_list(body, "ids"), str_list(body, "cats") or None), body.get("seg"), each)

    @r.post("/api/narrative/style")
    def style(body: dict = Body(...)):
        """Style figures per book or per segment."""
        return narrative.style(ctx.of(body), body.get("seg"), choice(body, "by", BY, "book"))

    @r.post("/api/narrative/sound")
    def sound_figures(body: dict = Body(...)):
        """Sound and rhythm figures per book or per segment, under the workspace's sound settings."""
        if not sound.available():
            raise HTTPException(400, sound.MISSING)
        return prosody.table(ctx.of(body), body.get("seg"), choice(body, "by", BY, "book"), prosody.config(ctx.lib.state["settings"]))

    @r.post("/api/narrative/wordchoice")
    def word_choice(body: dict = Body(...)):
        """Word-choice figures (parts of speech, ratios, verb and noun kinds) per book or per segment: `wordchoice.table`."""
        return wordchoice.table(ctx.of(body), body.get("seg"), choice(body, "by", BY, "book"))

    @r.post("/api/narrative/stylometry")
    def stylometry(body: dict = Body(...)):
        """Distances between texts, cluster tree and map."""
        return narrative.stylometry(ctx.of(body), body.get("seg"), body.get("units", "books"), whole(body, "mfw", 100, 2, 5000),
                                    real(body, "culling", 0, 0, 100), body.get("measure", "cosine"), body.get("linkage", "average"),
                                    body.get("scope", "all"), bool(body.get("exclude_pronouns")))

    # ---------- sentiment ----------
    @r.post("/api/narrative/sentiment")
    def sentiment(body: dict = Body(...)):
        """VADER sentiment per segment (with the Timeline "combined", put together across the books)."""
        if not narrative.vader_available():
            raise HTTPException(400, "Sentiment needs the vaderSentiment package: pip install vaderSentiment")
        return narrative.timeline(narrative.sentiment(ctx.of(body), body.get("seg"), str_list(body, "ids")), body.get("seg"), bool(body.get("each")))

    # ---------- the text view ----------
    @r.post("/api/read")
    def read(body: dict = Body(...)):
        """One chapter or slice of a book, with the layers asked for (the "sound" layer colours the runs of `sound_colour`, under the
        workspace's sound settings). The book may lie outside the selection."""
        books = body.get("books") if isinstance(body.get("books"), list) else []
        b = need_str(body, "book")
        if b not in ctx.lib.found():
            raise HTTPException(404, "That book isn't available.")
        v = ctx.view(books if b in books else books + [b], plural_choice(body))
        if b not in v.bd:
            raise HTTPException(404, "That book isn't available.")
        layers = str_list(body, "layers") if body.get("layers") is not None else None            # none given: the default layers; [] is plain text
        colour = choice(body, "sound_colour", prosody.RUNS, "alliteration")
        return reader.read(v, b, body.get("seg"), maybe_whole(body, "index"), maybe_whole(body, "tok"), maybe_whole(body, "end"),
                           layers, mapping(body, "topics"), mark=bool(body.get("mark", True)),
                           sound={"cfg": prosody.config(ctx.lib.state["settings"]), "colour": colour})

    @r.post("/api/narrative/chapters")
    def chapters(body: dict = Body(...)):
        """Edit a book's chapters: start one at a paragraph, remove or rename one, or go back to the ones found automatically."""
        b = need_str(body, "book")
        if b not in ctx.lib.found():
            raise HTTPException(404, "That book isn't in the library.")
        action = need_str(body, "action")
        pid = whole(body, "pid", None) if action != "reset" else None
        name = body.get("name")
        return {"edited": narrative.edit_chapters(ctx.lib, b, action, pid, str(name) if name is not None else None)}

    return r
