"""Your word lexicons (storage and editing in core/lexicons.py) and their arcs (core/narrative.py): the Lexicons page (Over time area)."""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from alex.core import lexicons, narrative

from .context import Context, need_str, str_list


def router(ctx: Context) -> APIRouter:
    """The routes of the Lexicons sub-tab. Every change answers with the lexicons as they are now (and the id of a new one)."""
    r = APIRouter()

    def reply(lid=None):
        """What every route returns: all lexicons with their category sizes (`lexicons.listing`) and the id just made, if any."""
        return {"lexicons": lexicons.listing(ctx.lexicon_dir), "id": lid}

    def change(action, *args):
        """Run a change to a lexicon, turning an unknown lexicon or category into a 404 (unusable input is a ValueError, hence a 400)."""
        try:
            return action(ctx.lexicon_dir, *args)
        except KeyError as e:
            raise HTTPException(404, "That lexicon or category doesn't exist.") from e

    @r.get("/api/lexicons")
    def listing():
        """Your lexicons: `{id, name, source, categories: {category: words}, problem}`, the emotion lexicon first."""
        return reply()

    @r.post("/api/lexicons")
    def create(body: dict = Body(...)):
        """Store a new lexicon from the text of a file or box (`name`, `text`); `emotion` makes it the emotion lexicon."""
        return reply(change(lexicons.create, need_str(body, "name"), need_str(body, "text"), body.get("emotion") is True))

    @r.post("/api/lexicons/{lid}/replace")
    def replace(lid: str, body: dict = Body(...)):
        """Give a lexicon the words of new text; it keeps its id and name."""
        change(lexicons.replace, lid, need_str(body, "text"))
        return reply(lid)

    @r.post("/api/lexicons/{lid}/rename")
    def rename(lid: str, body: dict = Body(...)):
        """Change the name a lexicon is shown by."""
        change(lexicons.rename, lid, need_str(body, "name"))
        return reply(lid)

    @r.post("/api/lexicons/{lid}/delete")
    def delete(lid: str):
        """Remove a lexicon."""
        change(lexicons.remove, lid)
        return reply()

    @r.get("/api/lexicons/{lid}/words")
    def words(lid: str, category: str):
        """The words of one category of a lexicon."""
        try:
            return {"category": category, "words": lexicons.get(ctx.lexicon_dir, lid)["cats"][category]}
        except KeyError as e:
            raise HTTPException(404, "That lexicon or category doesn't exist.") from e

    @r.post("/api/lexicons/{lid}/category")
    def save_category(lid: str, body: dict = Body(...)):
        """Save a category: `category` is the one to change (null: add a new one), `name` its name now, `text` its words."""
        old = body.get("category")
        change(lexicons.save_category, lid, None if old is None else str(old), need_str(body, "name"), need_str(body, "text"))
        return reply(lid)

    @r.post("/api/lexicons/{lid}/category/delete")
    def delete_category(lid: str, body: dict = Body(...)):
        """Remove a category from a lexicon."""
        change(lexicons.delete_category, lid, need_str(body, "category"))
        return reply(lid)

    @r.post("/api/narrative/lexicon")
    def arc(body: dict = Body(...)):
        """Words per 1,000 in each of the `cats` of lexicon `lexicon` (default: all its categories) per segment; with the Timeline
        "combined", put together across the books (`each`: every book's own line too)."""
        try:
            lex = lexicons.get(ctx.lexicon_dir, need_str(body, "lexicon"))
        except KeyError as e:
            raise HTTPException(404, "That lexicon doesn't exist.") from e
        return narrative.timeline(narrative.lexicon_arc(ctx.of(body), body.get("seg"), lex, str_list(body, "cats") or None), body.get("seg"), bool(body.get("each")))

    return r
