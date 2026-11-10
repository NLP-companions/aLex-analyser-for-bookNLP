"""The Statistics tab: correlations and descriptives over cases (analysis in core/statstab.py), lists of variables for the bulk-add
buttons, the R export (core/rexport.py) and saved sets (core/statsets.py)."""
from __future__ import annotations

import io
import time

from fastapi import APIRouter, Body, HTTPException, Response

from alex.core import cases, layers, lexicons, rexport, statsets, statstab, variables

from .context import MAX_BOOKS, Context, attachment, need, need_str, whole


def router(ctx: Context) -> APIRouter:
    """The routes of the Statistics tab."""
    r = APIRouter()
    lib = ctx.lib

    def your_lexicons():
        """Your word lexicons by id (the emotion lexicon and any stored beside it); one that can't be read is left out."""
        return lexicons.stored(ctx.lexicon_dir)

    @r.post("/api/stats")
    def run(body: dict = Body(...)):
        """Correlations, descriptives and the raw data for `setup`: {cases, rows, columns, method, correction, split} (see
        `statstab.run`), over the selected `books`."""
        return statstab.run(ctx.of(body), need(body, "setup"), your_lexicons())

    @r.post("/api/stats/export")
    def export(body: dict = Body(...)):
        """The cases and variables of `setup` (as `/api/stats`) as a .zip of files for R, for download (see core/rexport.py). `example`
        (default true) adds analysis_example.R."""
        zipped = io.BytesIO()
        rexport.write_zip(zipped, rexport.files(ctx.of(body), need(body, "setup"), your_lexicons(), body.get("example", True) is not False))
        return Response(zipped.getvalue(), media_type="application/zip",
                        headers={"Content-Disposition": attachment(time.strftime("analyser-statistics-%Y%m%d-%H%M%S.zip"))})

    @r.post("/api/stats/options")
    def options(body: dict = Body(...)):
        """What the layer variables can be, for the selected `books`: supersenses found, relations, sentiment, style and word-choice figures,
        your lexicons and their categories, the topic models sharing books with the selection, and whether VADER is installed."""
        return layers.options(ctx.of(body), your_lexicons())

    @r.post("/api/stats/bulk")
    def bulk(body: dict = Body(...)):
        """Variables to add in one go, each with its label: `what` "words" (the `n` most frequent words or lemmas, `unit`, in the samples
        of `cases`, optionally through a word-type `filter`, and only words in at least `min_range` of the books; `types` (sentence types) and
        `weigh_verb` take only words inside quotes of those types, `speech_verbs` the verbs that introduce quotes instead), "entities" (the `n` most mentioned of a `type`), "speakers" (the `n` of a `type` who speak the most words) or "attribute" (one 0/1
        variable per gender, tag or saved group: `attr`). `measure` is the new variables' measure."""
        view, what, measure = ctx.of(body), need_str(body, "what"), body.get("measure", "per1k")
        n = whole(body, "n", 20, 1, variables.MAX_VARIABLES)
        if what == "words":
            specs = variables.top_words(view, cases.build(view, body.get("cases")), n, body.get("unit", "word"), body.get("filter"), measure,
                                        whole(body, "min_range", 1, 1, MAX_BOOKS), body.get("types"), body.get("weigh_verb") is True,
                                        body.get("speech_verbs") is True)
        elif what == "entities":
            specs = variables.top_entities(view, n, body.get("type", "PER"), measure)
        elif what == "speakers":
            specs = variables.top_speakers(view, n, body.get("type", "PER"), measure)
        elif what == "attribute":
            specs = variables.attribute_values(view, need_str(body, "attr"))
        else:
            raise ValueError("Choose words, entities, speakers or an attribute.")
        return {"variables": [{**s, "label": variables.label(view, variables.check(s), your_lexicons())} for s in specs]}

    # ---------- saved sets ----------
    def set_reply(sid=None):
        """What every set route returns: the saved sets as they are now (and the id of the one just made or changed)."""
        return {"sets": statsets.listing(lib), "id": sid}

    def in_set(action, *args, **kw):
        """Run a change to saved sets, turning an unknown id into a 404 (unusable input is a ValueError, hence a 400)."""
        try:
            return action(lib, *args, **kw)
        except KeyError:
            raise HTTPException(404, "That set doesn't exist.") from None

    @r.get("/api/stats/sets")
    def sets():
        """The saved Statistics sets."""
        return set_reply()

    @r.post("/api/stats/sets")
    def set_new(body: dict = Body(...)):
        """Save the page's setup under a name."""
        return set_reply(in_set(statsets.create, body.get("name"), body.get("setup")))

    @r.post("/api/stats/sets/delete")
    def set_delete(body: dict = Body(...)):
        """Delete a saved set."""
        in_set(statsets.delete, need_str(body, "id"))
        return set_reply()

    @r.post("/api/stats/sets/{sid}")
    def set_change(sid: str, body: dict = Body(...)):
        """Rename a saved set or replace its setup."""
        in_set(statsets.update, sid, **{k: body[k] for k in ("name", "setup") if k in body})
        return set_reply(sid)

    return r
