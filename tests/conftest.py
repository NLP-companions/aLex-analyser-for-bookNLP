"""Shared fixtures. The synthetic corpus is written once per session; every test that changes
anything gets its own data folder, so tests never touch your real data."""
from __future__ import annotations

import pytest

import fixture
from alex.core import dialogue as dl
from alex.core import folders
from alex.core.library import Library
from alex.core.view import View

BOOKS = ["alpha", "beta", "gamma"]


@pytest.fixture(scope="session")
def corpus(tmp_path_factory):
    """(folder with the exports, {book id: Truth})."""
    exports = tmp_path_factory.mktemp("exports")
    return exports, fixture.build(exports)


@pytest.fixture(scope="session")
def truth(corpus):
    return corpus[1]


@pytest.fixture(autouse=True)
def opened(monkeypatch):
    """The folders a test asked the file browser to show (`folders.launch` is replaced, so no test ever opens a window)."""
    shown = []
    monkeypatch.setattr(folders, "launch", shown.append)
    return shown


@pytest.fixture
def lib(tmp_path, corpus):
    """A library over the synthetic books with its own empty data folder."""
    return Library(data_dir=tmp_path / "data", sources=[corpus[0]])


@pytest.fixture
def view(lib):
    """All three books."""
    return View(lib, BOOKS)


@pytest.fixture
def alpha(lib):
    return lib.book("alpha")


@pytest.fixture
def client(lib):
    """The web API over the synthetic books, as a test client."""
    from fastapi.testclient import TestClient

    from alex import app as app_module
    return TestClient(app_module.build_app(lib), base_url=fixture.LOCAL, raise_server_exceptions=False)


@pytest.fixture
def marked(view):
    """Alpha's first three quotes made a question, an exclamation and a statement said with "ask" (the fixture's quotes carry neither mark
    and every verb is "say"; `bdlg` keeps its records, so the change is seen by later calls and undone afterwards). -> alpha's records."""
    recs = dl.bdlg(view, "alpha")["recs"]
    first, second, third = recs[:3]
    saved = [(r, dict(question=r["question"], exclaim=r["exclaim"], verb=r["verb"])) for r in (first, second, third)]
    first["question"], second["exclaim"], third["verb"] = True, True, "ask"
    yield recs
    for r, old in saved:
        r.update(old)
