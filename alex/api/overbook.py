"""Over the book: a target's figures and words slice by slice through one book (analysis in core/overbook.py)."""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from alex.core import overbook, prosody, sound

from .context import MAX_BOOKS, Context, need, whole
from .entities import stat_options


def router(ctx: Context) -> APIRouter:
    """The routes of the Over the book page (within one book, two books aligned, and all the books combined)."""
    r = APIRouter()

    def sound_of(body):
        """The workspace's sound settings when the request asks for the sound of the target's speech (`sound`: true), else None;
        400 when the pronunciation dictionary isn't installed."""
        if body.get("sound") is not True:
            return None
        if not sound.available():
            raise HTTPException(400, sound.MISSING)
        return prosody.config(ctx.lib.state["settings"])

    @r.post("/api/overbook")
    def over(body: dict = Body(...)):
        """A `target` (and optionally `other`, to compare with) over the slices of one `book` cut as `seg` says (the Measure over
        setting): see `overbook.report`. Uses the shared statistics options (minimum frequency, level, Bonferroni). `sound`: true adds the sound
        and rhythm of the target's speech per slice (under the workspace's sound settings), on every route of this page."""
        kw = stat_options(body)
        other = body.get("other")
        if other is not None and not isinstance(other, dict):
            raise ValueError("“other” should be a target.")
        return overbook.report(ctx.of(body), need(body, "target"), other, body.get("book"), body.get("seg"), body.get("rel", "mod"),
                               min_freq=kw["min_freq"], alpha=kw["alpha"], bonferroni=kw["bonferroni"], curve_rel=body.get("curve_rel"), sound=sound_of(body))

    @r.post("/api/overbook/compare")
    def compare(body: dict = Body(...)):
        """The two sides `target` and `other` of the Compare page: over one `book` cut as `seg` says when some book holds both, else each in its
        own book (`book`, `other_book`) cut into `n` equal slices and lined up by position; `mode` says which: see `overbook.compare`."""
        kw = stat_options(body)
        other = body.get("other")
        if not isinstance(other, dict):
            raise ValueError("“other” should be a target.")
        return overbook.compare(ctx.of(body), need(body, "target"), other, body.get("book"), body.get("other_book"), body.get("seg"),
                                whole(body, "n", 20, 2, overbook.MAX_SLICES), body.get("rel", "mod"), min_freq=kw["min_freq"], alpha=kw["alpha"], bonferroni=kw["bonferroni"], curve_rel=body.get("curve_rel"), sound=sound_of(body))

    @r.post("/api/overbook/aligned")
    def aligned(body: dict = Body(...)):
        """A `target` in one `book` and a second target `other` (None: the same one) in `other_book`, cut into the same `n` equal slices so
        that they line up by relative position, with how alike their curves are: see `overbook.aligned`."""
        kw = stat_options(body)
        other = body.get("other")
        if other is not None and not isinstance(other, dict):
            raise ValueError("“other” should be a target.")
        return overbook.aligned(ctx.of(body), need(body, "target"), body.get("book"), other, body.get("other_book"), whole(body, "n", 20, 2, overbook.MAX_SLICES),
                                body.get("rel", "mod"), min_freq=kw["min_freq"], alpha=kw["alpha"], bonferroni=kw["bonferroni"], curve_rel=body.get("curve_rel"), sound=sound_of(body))

    @r.post("/api/overbook/combined")
    def combined(body: dict = Body(...)):
        """A `target` through every selected book that holds it, each cut into the same `n` equal slices (held to 2–200) and every book
        weighing the same, for the relation `rel` with the shared statistics options and `min_range` (the fewest books a word must occur in to be tested, default 1). `curve` (a figure of the curve, see `overbook.curve`;
        not the statistics `measure`) also asks for each book's own values of it: see `overbook.combined`."""
        kw = stat_options(body)
        measure = body.get("curve")
        if measure is not None and not isinstance(measure, str):
            raise ValueError("“curve” should be a figure of the curve.")
        return overbook.combined(ctx.of(body), need(body, "target"), whole(body, "n", 20, 2, overbook.MAX_SLICES), body.get("rel", "mod"), measure,
                                 body.get("curve_rel"), min_freq=kw["min_freq"], alpha=kw["alpha"], bonferroni=kw["bonferroni"],
                                 min_range=whole(body, "min_range", 1, 1, MAX_BOOKS), each_book=ctx.each_book(), sound=sound_of(body))

    return r
