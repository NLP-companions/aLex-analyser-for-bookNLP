"""What every route needs: the library, the cache of views, the folders for the analyser's own files, and
helpers for reading request bodies."""
from __future__ import annotations

import re
import threading
import unicodedata
from collections import OrderedDict
from urllib.parse import quote

from fastapi import HTTPException

from alex.core.view import View


class Context:
    """Shared state of one running analyser (one per `build_app`)."""

    MAX_VIEWS = 6           # views kept in memory; a view holds the combined entities of a selection of books

    def __init__(self, lib):
        self.lib = lib
        self._views: OrderedDict = OrderedDict()
        self._remembered: OrderedDict = OrderedDict()               # last few concordance searches, so paging doesn't search again
        self._lock = threading.Lock()
        self.refs_dir, self.lexicon_dir = self._folders()

    def _folders(self):
        """The reference-file folder and the lexicon folder of the library's data folder (both made if missing)."""
        refs, lexicons = self.lib.data_dir / "references", self.lib.data_dir / "lexicons"
        refs.mkdir(parents=True, exist_ok=True)
        lexicons.mkdir(parents=True, exist_ok=True)
        return refs, lexicons

    def switch(self, data_dir):
        """Work in another data folder (a workspace): the library re-opens it (`Library.reopen`, which raises `LibraryError` and
        changes nothing if it can't be read), and everything kept from the old folder is dropped. Routes must read `refs_dir` and
        `lexicon_dir` from here on each request, not keep them."""
        self.lib.reopen(data_dir)
        self.refs_dir, self.lexicon_dir = self._folders()
        with self._lock:
            self._views.clear()
            self._remembered.clear()

    def selected(self, books) -> list:
        """The ids in a request's `books` that are in the library, each once, in the order given. A request that names
        no books, or none that exist, is a 400."""
        if not books or not isinstance(books, list):
            raise HTTPException(400, "No books selected")
        found = self.lib.found()
        books = [b for b in dict.fromkeys(books) if b in found]
        if not books:
            raise HTTPException(400, "None of the selected books were found")
        return books

    def view(self, books, plural=None) -> View:
        """The `View` of the given books (unknown ids are ignored), from the cache when nothing has changed since it
        was built: your settings, links and corrections (`lib.version`) and the books' files (`lib.book_key`).
        `plural` (a page's own choice, sent with its requests) overrides your setting for counting plural groups'
        mentions for their members; None uses the setting."""
        books = self.selected(books)
        plural = bool(self.lib.state["settings"].get("plural", False) if plural is None else plural)
        sig = (tuple(books), plural, self.lib.version, tuple(self.lib.book_key(b) for b in books))
        with self._lock:
            if sig in self._views:
                self._views.move_to_end(sig)
                return self._views[sig]
        view = View(self.lib, books, plural)                                # built outside the lock: it can take a while
        with self._lock:
            self._views[sig] = view
            while len(self._views) > self.MAX_VIEWS:
                self._views.popitem(last=False)
        return view

    def of(self, body) -> View:
        """The `View` a request asks about: its `books` and its page's `plural` choice (see `view`; anything but true or false
        there means your setting)."""
        return self.view(body.get("books"), plural_choice(body))

    def each_book(self) -> bool:
        """Whether a minimum word frequency is checked in each book (the Words setting `freq_mode` is "per_book") rather than over the
        selected books together. Read for every request, so a change of the setting applies at once."""
        return self.lib.state["settings"].get("freq_mode") == "per_book"

    @staticmethod
    def signature(view) -> tuple:
        """What a result computed from a view depends on, for keeping results: the view's books and plural setting, your settings,
        links and corrections (`lib.version`), and the books' files."""
        return (tuple(view.books), view.plural, view.lib.version, tuple(view.lib.book_key(b) for b in view.books))

    MAX_REMEMBERED = 4

    def remember(self, key, make):
        """The result `make()` gives for `key`, from the last few kept if there is one (the least recently used is forgotten)."""
        with self._lock:
            if key in self._remembered:
                self._remembered.move_to_end(key)
                return self._remembered[key]
        result = make()                                                       # outside the lock: it can take a while
        with self._lock:
            self._remembered[key] = result
            while len(self._remembered) > self.MAX_REMEMBERED:
                self._remembered.popitem(last=False)
        return result


def attachment(filename):
    """The `Content-Disposition` header of a file to download. A header can only hold plain characters, so a name with others (a book called
    "Émile") is sent as a plain-text version and as itself (RFC 6266), which browsers read; a plain name is sent as it is."""
    plain = re.sub(r"[^A-Za-z0-9._ -]", "_", unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode())
    stem, dot, extension = plain.rpartition(".")
    plain = f"download.{extension}" if dot and not stem else plain or "download"            # nothing of the name was plain: only its extension is
    if plain == filename:
        return f'attachment; filename="{filename}"'
    return f"attachment; filename=\"{plain}\"; filename*=UTF-8''{quote(filename)}"


# ---------- reading request bodies ----------
def plural_choice(body):
    """A request's own choice of counting plural groups for their members: True or False, else None (use your setting)."""
    plural = body.get("plural")
    return plural if isinstance(plural, bool) else None


def _number(body, key, default, cast, kind, low, high):
    """body[key] (default if absent or null) as a number made by `cast`, held between low and high; a readable error if it isn't a
    finite number of that kind."""
    value = body.get(key)
    if value is None:
        value = default
    try:
        value = cast(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"“{key}” should be {kind}.") from None
    if value != value or value in (float("inf"), float("-inf")):              # NaN and infinity: JSON from Python can carry them
        raise ValueError(f"“{key}” should be {kind}.")
    if low is not None:
        value = max(low, value)
    if high is not None:
        value = min(high, value)
    return value


MAX_BOOKS = 100000      # the largest "minimum range" setting taken (more than there can be books: it then keeps nothing)


def whole(body, key, default, low=None, high=None):
    """body[key] as a whole number (default if absent), held between low and high; a readable error if it isn't a number."""
    return _number(body, key, default, int, "a whole number", low, high)


def real(body, key, default, low=None, high=None):
    """Like `whole`, for numbers with decimals."""
    return _number(body, key, default, float, "a number", low, high)


def maybe_whole(body, key):
    """body[key] as a whole number, or None if it is absent or null (an optional position, say)."""
    return None if body.get(key) is None else whole(body, key, None)


def mapping(body, key):
    """body[key] as an object ({} if absent or null); a readable error if it is something else."""
    value = body.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"“{key}” should be an object.")
    return value


def items(body, key):
    """body[key] as a list ([] if absent or null); a readable error if it is something else, such as a number."""
    value = body.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"“{key}” should be a list.")
    return value


def text(body, key, default=""):
    """body[key] as text (`default` if absent or null); a readable error if it is something else, such as a number or a list."""
    value = body.get(key)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"“{key}” should be text.")
    return value


def choice(body, key, options, default):
    """body[key], which must be one of `options` (`default` if absent or null); a readable error listing them if it is anything else."""
    value = body.get(key)
    if value is None:
        return default
    if not isinstance(value, str) or value not in options:
        raise ValueError(f"“{key}” should be one of: {', '.join(options)}.")
    return value


def need(body, key):
    """body[key], or a readable error saying what is missing."""
    if key not in body or body[key] is None:
        raise ValueError(f"“{key}” is missing.")
    return body[key]


def need_str(body, key):
    """body[key] as text (an id, a name): a readable error if it is missing."""
    return str(need(body, key))


def str_list(body, key):
    """body[key] as a list of strings ([] if absent or null); a readable error if it is something else, such as a single string."""
    return [str(x) for x in items(body, key)]


def is_group(body):
    """Whether a request names several entities (`ids`, or a saved `group`) rather than one (`id`)."""
    return body.get("ids") is not None or bool(body.get("group"))


def unit_target(view, body):
    """The unit (or virtual group unit) a request asks about, or None if it isn't in the selection; a readable error if the body names none."""
    if not is_group(body):
        need(body, "id")
    return view.target_unit(body)
