"""Workspaces: list, create, rename, switch, import from an export zip, remove from the list, delete; and showing their folders."""
from __future__ import annotations

import os
import tempfile
import threading

from fastapi import APIRouter, Body, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from alex.core import folders
from alex.core.library import LibraryError
from alex.core.workspaces import Workspaces

from .context import Context, choice, need, text, whole


def router(ctx: Context, topics, workspaces: Workspaces) -> APIRouter:
    """Routes for workspaces (core/workspaces.py). `topics` is the topic-modelling package or None: its models folder follows the workspace."""
    r = APIRouter()

    def reply(wid=None):
        """What every workspace route returns: the workspaces as they are now (and the id of the one just made)."""
        return {"workspaces": workspaces.listing(), "id": wid}

    def known(action, *args, **kw):
        """Run a change to the workspaces, turning an unknown id into a 404 (unusable input, a ValueError, is the usual 400)."""
        try:
            return action(*args, **kw)
        except KeyError:
            raise HTTPException(404, "That workspace doesn't exist.") from None

    @r.get("/api/workspaces")
    def listing():
        """The workspaces and which one is in use."""
        return reply()

    @r.post("/api/workspaces")
    def create(body: dict = Body(...)):
        """Make an empty workspace (it is not opened). `sources`: the folders it reads books from (default: none)."""
        sources = body.get("sources")
        if sources is not None and not isinstance(sources, list):
            raise ValueError("“sources” should be a list of folders.")
        return reply(workspaces.create(body.get("name"), sources=[os.path.expanduser(str(s)) for s in sources] if sources else None))

    @r.post("/api/workspaces/activate")
    def activate(body: dict = Body(...)):
        """Switch to a workspace: the library re-opens its folder and everything kept from the old one is dropped. The browser reloads after this."""
        wid = str(need(body, "id"))
        folder = known(workspaces.openable, wid)
        try:
            ctx.switch(folder)
        except LibraryError as e:
            raise ValueError(str(e)) from None                    # a damaged file in that workspace: say which, and stay where we were
        if topics is not None:
            topics.configure(folder / "topics")
        workspaces.activate(wid)
        lib = ctx.lib
        lib.scan()
        threading.Thread(target=lib.warm, daemon=True).start()   # read its books while the page reloads
        return reply(wid)

    @r.post("/api/workspaces/forget")
    def forget(body: dict = Body(...)):
        """Take a workspace off the list; its files stay."""
        known(workspaces.forget, str(need(body, "id")))
        return reply()

    @r.post("/api/workspaces/delete")
    def delete(body: dict = Body(...)):
        """Delete a workspace's folder for good. `name` must be typed exactly as the workspace is called."""
        known(workspaces.delete, str(need(body, "id")), body.get("name"))
        return reply()

    @r.post("/api/workspaces/import")
    async def import_zip(request: Request, name: str = ""):
        """Make a workspace from an export zip sent as the raw request body (`?name=` names it). It is streamed to a temporary file,
        so a large corpus never has to fit in memory; the workspace is not opened."""
        handle, path = tempfile.mkstemp(suffix=".zip")
        try:
            with os.fdopen(handle, "wb") as f:
                async for chunk in request.stream():
                    f.write(chunk)
            wid = await run_in_threadpool(workspaces.import_zip, path, name or None)
        finally:
            os.unlink(path)
        return reply(wid)

    @r.post("/api/folders/open")
    def open_folder(body: dict = Body(...)):
        """Show one of a workspace's folders in the computer's file browser -> its path. `folder`: "books" (its books folder, made if it
        is missing), "data" (its data folder) or "source" (the source folder at `index` in the list of the workspace in use).
        `workspace`: whose (default: the one in use). Only these folders can be opened, never a path the request names."""
        kind = choice(body, "folder", ("books", "data", "source"), None)
        if kind is None:
            raise ValueError("“folder” is missing.")
        wid = text(body, "workspace") or workspaces.active
        data = known(workspaces.folder, wid)
        if kind == "source":
            if wid != workspaces.active:
                raise ValueError("Only the source folders of the workspace in use can be opened.")
            sources = ctx.lib.state["sources"]
            index = whole(body, "index", None)
            if not 0 <= index < len(sources):
                raise ValueError("There is no source folder at that place in the list.")
            return {"path": folders.open_folder(sources[index])}
        if kind == "books" and data.is_dir():
            (data / "books").mkdir(exist_ok=True)
        return {"path": folders.open_folder(data / "books" if kind == "books" else data)}

    @r.post("/api/workspaces/{wid}")
    def rename(wid: str, body: dict = Body(...)):
        """Rename a workspace."""
        known(workspaces.rename, wid, body.get("name"))
        return reply(wid)

    return r
