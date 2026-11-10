"""aLex, a BookNLP analyser: explore the books BookNLP has processed (its output files, or exports from the companion editor).

    alex                       start and open the browser (the same as `python -m alex`)
    alex --books FOLDER        also look for books in FOLDER (kept for next time; can be repeated)
    alex --data FOLDER         keep the analyser's own files in FOLDER (default: `alex-data` in the folder you start it from)
    alex --port 8770           use another port
    alex --no-browser          don't open the browser
    alex --workspace X         open the workspace called X (it is also the one opened next time)
    alex --allow-host NAME     also answer requests for NAME, e.g. a Cloudflare tunnel's abc.trycloudflare.com (for a demo; can be repeated)

This file only wires things together: it builds the web application (`build_app`), turns errors into
readable messages and starts the server. The work is in `core/` (analysis) and `api/` (routes).
"""
from __future__ import annotations

import argparse
import json
import logging
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from alex import api
from alex.api.context import Context
from alex.core.library import Library, LibraryError, data_home
from alex.core.workspaces import DEFAULT_ID, Workspaces
from alex.localonly import LocalOnly, host_name

try:                      # numpy and scikit-learn are only needed for topics; the rest works without them
    from alex.core import topics
    import sklearn  # noqa: F401  (imported only to find out whether it is installed)
except ImportError:
    topics = None

STATIC = Path(__file__).resolve().parent / "static"
log = logging.getLogger("alex")


class NoCacheStaticFiles(StaticFiles):
    """Static files that the browser re-checks on every load, so an updated script or style sheet is never stale."""

    async def get_response(self, path, scope):
        """Serve a file with `Cache-Control: no-cache`."""
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


def build_app(lib: Library, topics_module=topics, workspaces: Workspaces | None = None, allow_hosts=()) -> FastAPI:
    """The web application for a library. `topics_module=None` switches the topic tools off (as if scikit-learn were missing).
    `workspaces`: the list of workspaces `lib` is the active one of (default: a list beside the library's data folder, with that
    folder as the Default workspace, which is what tests want). `allow_hosts`: names answered besides this computer's (`--allow-host`)."""
    if workspaces is None:
        workspaces = Workspaces(lib.data_dir.parent / "workspaces.json", default_data=lib.data_dir)
    if topics_module is not None:
        topics_module.configure(lib.data_dir / "topics")
    ctx = Context(lib)
    app = FastAPI(title="BookNLP analyser")
    app.add_middleware(LocalOnly, extra_hosts=allow_hosts)  # only requests for this computer, and changes only from our own page (see localonly.py)

    # ---------- errors become messages the interface can show ----------
    def error(status, message):
        """A JSON error response with a `detail` message."""
        return JSONResponse({"detail": message}, status_code=status)

    @app.exception_handler(RequestValidationError)
    async def bad_request(request: Request, exc: RequestValidationError):
        """A request that isn't what a route reads at all (no JSON object, a missing query value): FastAPI's own check, said in one line."""
        where = [x for x in (exc.errors()[0]["loc"] if exc.errors() else ()) if isinstance(x, str) and x not in ("body", "query", "path")]
        return error(400, f"The request needs a valid “{where[0]}”." if where else "The request should be a JSON object.")

    @app.exception_handler(ValueError)
    async def bad_value(request: Request, exc: ValueError):
        """Something the user asked can't be done (a bad search, too little text…): the message says why. (Logged at debug level too, since a
        bug can also surface as a `ValueError`.)"""
        log.debug("ValueError in %s %s", request.method, request.url.path, exc_info=True)
        return error(400, str(exc) or "That request can't be carried out.")

    @app.exception_handler(KeyError)
    async def bad_key(request: Request, exc: KeyError):
        """An id or field that doesn't exist (a book that was removed, a missing field). A `KeyError` can also be a bug, so it is logged at debug
        level, with its traceback (switch on with `logging.getLogger("alex").setLevel("DEBUG")`)."""
        log.debug("KeyError in %s %s", request.method, request.url.path, exc_info=True)
        return error(400, f"Not found: {exc.args[0] if exc.args else 'something the request refers to'}.")

    @app.exception_handler(Exception)
    async def crash(request: Request, exc: Exception):
        """A bug: log it in the terminal and tell the interface something went wrong (with the reason, for bug reports)."""
        log.exception("Error in %s %s", request.method, request.url.path)
        return error(500, f"Something went wrong ({type(exc).__name__}: {exc}). Details are in the terminal.")

    for router in api.routers(ctx, topics_module, workspaces):
        app.include_router(router)

    @app.get("/")
    def index():
        """The page itself, with the id of the open workspace written in (the browser keeps its remembered settings per workspace)."""
        html = (STATIC / "index.html").read_text(encoding="utf-8").replace(
            "window.WORKSPACE = null;", f"window.WORKSPACE = {json.dumps(workspaces.active)};", 1)
        return HTMLResponse(html, headers={"Cache-Control": "no-cache"})

    app.mount("/static", NoCacheStaticFiles(directory=STATIC), name="static")
    return app


def port_in_use(port: int) -> bool:
    """Whether something already answers on this computer at `port` (most likely aLex itself, started earlier)."""
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def warm_with_notes(lib: Library, every: float = 15.0):
    """Read every book in the background (`Library.warm`), and say in the terminal how far it is every `every` seconds when it takes that long: the
    first start parses each book, which can take a few minutes for many novels (later starts read the copies aLex keeps)."""
    started, state, finished = time.time(), {"done": 0, "total": 0}, threading.Event()

    def say():
        """Tell how many books are read, until all are."""
        while not finished.wait(every):
            print(f"  still reading your books for the first time: {state['done']} of {state['total'] or '…'} ({time.time() - started:.0f} s)", flush=True)

    threading.Thread(target=say, daemon=True).start()
    lib.warm(lambda done, total: state.update(done=done, total=total))
    finished.set()
    if time.time() - started > every:
        print(f"  all {state['total']} books read ({time.time() - started:.0f} s).", flush=True)


def main():
    """Start the analyser: read the library, then serve it on this computer only (127.0.0.1) and open the browser."""
    parser = argparse.ArgumentParser(prog="alex", description="aLex: explore books processed by BookNLP.")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--books", action="append", default=[], metavar="FOLDER",
                        help="a folder of BookNLP output to look for books in; it is added to the open workspace's folders (repeat for several)")
    parser.add_argument("--workspace", help="open this workspace (its id or name) and keep it as the one to open next time")
    parser.add_argument("--data", metavar="FOLDER", help="keep the analyser's own files here (default: the ALEX_DATA variable, else `alex-data` in the current folder)")
    parser.add_argument("--allow-host", action="append", default=[], metavar="NAME",
                        help="also answer requests for this host name, e.g. a tunnel's abc.trycloudflare.com, to show aLex to someone else (repeat for several)")
    args = parser.parse_args()
    try:
        allow_hosts = [host_name(h) for h in args.allow_host]
    except ValueError as e:
        sys.exit(f"\n--allow-host: {e}\n")
    for folder in args.books:
        if not Path(folder).expanduser().is_dir():
            sys.exit(f"\n--books: “{folder}” is not a folder.\n")
    if port_in_use(args.port):
        sys.exit(f"\nPort {args.port} is already in use. If aLex is running, it is at http://127.0.0.1:{args.port}/ ; otherwise choose another port with --port.\n")
    import uvicorn

    try:
        home = Path(args.data).expanduser().resolve() if args.data else data_home()
        workspaces = Workspaces(home / "workspaces.json", default_data=home)
        if args.workspace:
            wanted = workspaces.find(args.workspace)
            workspaces.openable(wanted)
            workspaces.activate(wanted)
        if workspaces.active != DEFAULT_ID and not workspaces.folder().is_dir():
            print(f"Note: the folder of the workspace “{workspaces.get(workspaces.active)['name']}” is gone; opening Default instead.")
            workspaces.activate(DEFAULT_ID)
        lib = Library(data_dir=workspaces.folder())
    except (LibraryError, ValueError) as e:
        sys.exit(f"\n{e}\n")
    lib.add_sources(args.books)
    found, problems = lib.scan()
    for p in problems:
        print("Note:", p)
    print(f"\nData folder: {home}")
    print(f"Books folder of this workspace: {lib.books_dir}")
    print(f"Workspace “{workspaces.get(workspaces.active)['name']}”: {len(found)} book(s) found. Open http://127.0.0.1:{args.port}/ — press Ctrl+C to stop.\n")
    if not found:
        print("No books yet: put BookNLP output in the books folder above, add a folder of it under Settings → Folders in the browser,"
              " or restart with --books FOLDER.\n")
    for name in allow_hosts:
        print(f"Also answering requests for {name}: anyone who can reach that address can see and change this aLex. Stop it (Ctrl+C) when the demo is over.\n")
    threading.Thread(target=warm_with_notes, args=(lib,), daemon=True).start()          # read the books while the browser opens
    if not args.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}/")).start()
    uvicorn.run(build_app(lib, workspaces=workspaces, allow_hosts=allow_hosts), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
