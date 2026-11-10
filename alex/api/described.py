"""Described as: what a target is described and called as, and by whom (analysis in core/described.py)."""
from __future__ import annotations

from fastapi import APIRouter, Body

from alex.core import described

from .context import Context, need, whole


def options(body):
    """What both routes are asked: the `target` spec and the `kind`, `split`, `voice`, number of columns (`top`) and, for the split "custom", the `columns` you picked that decide
    which table it is. Arguments of `described.table` / `described.evidence`; a missing or unusable target is a readable error."""
    target = need(body, "target")
    if not isinstance(target, dict):
        raise ValueError("“target” should say which entities to look at.")
    return target, dict(kind=body.get("kind", "mod"), split=body.get("split", "entity"), voice=body.get("voice", "both"),
                        top=whole(body, "top", 8, 1, 30), columns=body.get("columns"))


def router(ctx: Context) -> APIRouter:
    """The routes of the Described-as view."""
    r = APIRouter()

    @r.post("/api/described")
    def table(body: dict = Body(...)):
        """What a target (an entity, a saved or hand-picked group, a tag or a gender: `target`, as the spec of any comparison) is
        described or called as, split by who says it: `kind` (modifiers, names, actions…), `split` (the describer, their gender or
        tag, the book, or narration vs speech), `voice` (narration, speech or both), at most `top` columns and `limit` words."""
        target, opts = options(body)
        return described.table(ctx.of(body), target, limit=whole(body, "limit", 60, 1, 500), **opts)

    @r.post("/api/described/evidence")
    def evidence(body: dict = Body(...)):
        """The sentences behind one cell of that table: the same body, plus the word or form (`item`) and the column (`column`: its id,
        `_rest` for "All others", or null for the All column). `total` is exactly the cell's count; at most `limit` sentences are
        returned, each with who said it."""
        target, opts = options(body)
        item = need(body, "item")
        return described.evidence(ctx.of(body), target, item, body.get("column"), limit=whole(body, "limit", 150, 1, 1000), **opts)

    return r
