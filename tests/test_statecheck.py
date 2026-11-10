"""A workspace's own files with parts of the wrong shape (hand-edited, or imported from someone else's export): what can be read is
kept, the rest is left out with a note on the Library page, and no page breaks."""
from __future__ import annotations

import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient
from fixture import LOCAL

from alex import app as app_module
from alex.core.library import Library, default_state
from alex.core.statecheck import clean_annotations, clean_state
from alex.core.workspaces import Workspaces

GOOD_PERSON = {"members": [["alpha", 1], ["beta", 5]], "tags": ["detective"], "name": "Holmes"}


def checked(**saved):
    """`clean_state` of a library.json holding `saved`."""
    return clean_state(saved, default_state())


# ---------- library.json, part by part ----------
def test_a_good_state_comes_through_unchanged():
    state = {**default_state(), "persons": {"1": GOOD_PERSON}, "next_person": 2, "groups": {"1": {"name": "g", "ids": ["e:alpha:1"]}},
             "next_group": 2, "books": {"alpha": {"title": "T", "year": 1890, "tags": ["a"], "pinned": None}}}
    out, notes = clean_state(json.loads(json.dumps(state)), default_state())
    assert out == state and notes == []


@pytest.mark.parametrize("part", ["persons", "groups", "collections", "books", "narrator_links", "stat_sets", "entity_tags", "plurals"])
def test_a_part_of_the_wrong_shape_starts_empty(part):
    out, notes = checked(**{part: ["not", "an", "object"]})
    assert out[part] == {} and len(notes) == 1 and "starts empty" in notes[0]


def test_unreadable_entries_are_left_out_and_counted():
    out, notes = checked(groups={"1": {"name": "ok", "ids": ["e:alpha:1"]}, "2": {"name": "bad", "ids": 5}, "3": "x"},
                         entity_names={"e:alpha:1": "Sherlock", "e:alpha:2": 7}, rejected=[["a", "b"], "c", ["d"]])
    assert list(out["groups"]) == ["1"] and out["entity_names"] == {"e:alpha:1": "Sherlock"} and out["rejected"] == [["a", "b"]]
    assert "2 saved groups in library.json couldn't be read and were left out." in notes
    assert "1 entities' names in library.json couldn't be read and was left out." in notes


def test_a_person_keeps_its_readable_members_and_an_entity_stays_in_one_person():
    out, notes = checked(persons={"2": {"members": [["alpha", 1], ["gamma", 3]]}, "1": {**GOOD_PERSON, "members": [["alpha", 1], "x", ["beta", True]], "tags": 5},
                                  "3": {"members": []}, "4": {"members": [["alpha", 1]]}})
    assert out["persons"]["1"]["members"] == [["alpha", 1]] and out["persons"]["1"]["tags"] == [] and out["persons"]["1"]["name"] == "Holmes"
    assert out["persons"]["2"]["members"] == [["gamma", 3]]          # alpha 1 already belongs to person 1
    assert set(out["persons"]) == {"1", "2"} and notes == ["2 linked persons in library.json couldn't be read and were left out."]


def test_a_narrator_role_stays_in_one_link_and_a_link_needs_two_roles():
    out, _ = checked(narrator_links={"1": {"members": ["nar:a", "nar:b"], "name": "N"}, "2": {"members": ["nar:a", "nar:c"]},
                                     "3": {"members": ["nar:d", "nar:e"], "name": 5}})
    assert out["narrator_links"] == {"1": {"members": ["nar:a", "nar:b"], "name": "N"}, "3": {"members": ["nar:d", "nar:e"], "name": None}}


def test_the_next_numbers_are_above_every_id_in_use():
    out, _ = checked(groups={"7": {"name": "g", "ids": []}}, next_group=2, next_person="x", stat_sets={"3": {"name": "s", "setup": {}}}, next_stat_set=10)
    assert out["next_group"] == 8 and out["next_person"] == 1 and out["next_stat_set"] == 10


def test_a_book_keeps_its_readable_details():
    out, notes = checked(books={"alpha": {"title": 5, "author": "Doyle", "tags": "x", "year": "1890"}, "beta": []})
    assert out["books"] == {"alpha": {"author": "Doyle", "year": "1890"}} and len(notes) == 1


def test_parts_aLex_does_not_know_are_kept():
    out, notes = checked(future={"x": 1})
    assert out["future"] == {"x": 1} and notes == []


# ---------- annotations.json ----------
def test_a_books_corrections_keep_what_can_be_read():
    ann = {"books": {"alpha": {"narrator": 5, "splits": ["q1", 2], "addressees": {"q1": ["e:alpha:1"], "q2": "x"},
                               "participants": {"q1": {"add": ["e:alpha:2"]}, "q2": {"add": 5}}, "chapters": {"add": 5},
                               "para_narrators": {"p1": "nar:x", "p2": None}},
                     "beta": "x"}, "other": 1}
    out, notes = clean_annotations(ann)
    a = out["books"]["alpha"]
    assert a["narrator"] is None and a["splits"] == ["q1"] and a["addressees"] == {"q1": ["e:alpha:1"]} and "chapters" not in a
    assert a["participants"] == {"q1": {"add": ["e:alpha:2"]}} and a["para_narrators"] == {"p1": "nar:x"}
    assert "beta" not in out["books"] and out["other"] == 1 and len(notes) == 7


def test_good_chapter_edits_come_through():
    ch = {"add": ["p#1"], "remove": [], "names": {"p#1": "One"}}
    out, notes = clean_annotations({"books": {"alpha": {"chapters": ch}}})
    assert out["books"]["alpha"]["chapters"] == ch and notes == []


# ---------- end to end ----------
DAMAGED_STATE = {"persons": {"1": {"members": 5}}, "groups": [1, 2], "collections": {"1": {"name": "c", "books": "alpha"}},
                 "narrator_links": {"1": {"members": "x"}}, "stat_sets": {"1": {"name": "s", "setup": 5}}, "plurals": {"e:alpha:1": 5},
                 "books": {"alpha": {"tags": 5}}, "entity_tags": {"e:alpha:1": "x"}}
DAMAGED_ANN = {"books": {"alpha": {"splits": 5, "merges": [1], "addressees": [], "participants": {"x": 1}, "chapters": {"names": 5},
                                   "chapter_narrators": 3, "narrator": []}}}


def every_page(client):
    """Ask what the main pages ask for over the fixture's books -> the requests that went wrong."""
    B = {"books": ["alpha", "beta", "gamma"]}
    asks = [("GET", "/api/library", None), ("POST", "/api/units", B), ("POST", "/api/profile", {**B, "id": "e:alpha:1"}),
            ("POST", "/api/dialogue/overview", B), ("POST", "/api/dialogue/conversations", B), ("POST", "/api/dialogue/narrators", B),
            ("POST", "/api/narrative/segments", {**B, "seg": {"mode": "chapters"}}), ("POST", "/api/read", {**B, "book": "alpha", "index": 0}),
            ("GET", "/api/groups", None), ("GET", "/api/stats/sets", None), ("GET", "/api/links/persons", None),
            ("GET", "/api/links/narrator_links", None), ("POST", "/api/network", {**B, "kind": "dialogue"}),
            ("POST", "/api/plurals/suggestions", B), ("GET", "/api/links/suggestions", None)]
    bad = []
    for method, path, body in asks:
        r = client.get(path) if method == "GET" else client.post(path, json=body)
        if r.status_code != 200:
            bad.append(f"{path} {r.status_code} {r.text[:150]}")
    return bad


def test_a_damaged_workspace_opens_and_every_page_works(lib):
    lib.state_path.write_text(json.dumps({**DAMAGED_STATE, "sources": lib.state["sources"]}), encoding="utf-8")
    lib.annot_path.write_text(json.dumps(DAMAGED_ANN), encoding="utf-8")
    again = Library(data_dir=lib.data_dir)
    client = TestClient(app_module.build_app(again), base_url=LOCAL, raise_server_exceptions=False)
    assert every_page(client) == []
    notes = client.get("/api/library").json()["state_notes"]
    assert any("“saved groups” in library.json" in n for n in notes) and any("annotations.json" in n for n in notes)
    assert again.state["groups"] == {} and again.state["persons"] == {}


def test_an_imported_export_with_damaged_parts_works(lib, tmp_path):
    """An export from another aLex (or edited by hand) is imported as it is and checked when the workspace opens."""
    client = TestClient(app_module.build_app(lib), base_url=LOCAL, raise_server_exceptions=False)
    exported = client.post("/api/export", json={"books": ["alpha", "beta", "gamma"]}).content
    damaged = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(exported)) as src, zipfile.ZipFile(damaged, "w") as dst:
        for name in src.namelist():
            data = src.read(name)
            if name == "state/library.json":
                data = json.dumps({**json.loads(data), **DAMAGED_STATE}).encode()
            elif name == "state/annotations.json":
                data = json.dumps(DAMAGED_ANN).encode()
            dst.writestr(name, data)
    zip_path = tmp_path / "damaged.zip"
    zip_path.write_bytes(damaged.getvalue())
    spaces = Workspaces(tmp_path / "spaces.json", default_data=lib.data_dir)
    wid = spaces.import_zip(zip_path)
    imported = Library(data_dir=spaces.folder(wid))
    assert sorted(imported.scan()[0]) == ["alpha", "beta", "gamma"] and imported.state_notes
    assert every_page(TestClient(app_module.build_app(imported), base_url=LOCAL, raise_server_exceptions=False)) == []
