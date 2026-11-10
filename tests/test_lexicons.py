"""Your word lexicons (core/lexicons.py, api/lexicons.py): parsing, storing, editing, and their arcs through the routes."""
from __future__ import annotations

import json

import pytest

from alex.core import lexicons as lx

ALL = ["alpha", "beta", "gamma"]
SEG = {"mode": "slices", "n": 5}
PAIRS = "moor\tnature\t1\nhound\tfear\t1\nhill\tnature\t1\n"


# ---------- parsing ----------
def test_word_and_category_lines_are_read_with_flags_headers_and_comments():
    text = "# a comment\nword\temotion\tassociation\nmoor\tnature\t1\nhound\tnature\t1\nhound\tfear\t1\ngoose\tfear\t0\nbird\tnature\t1\nlonely\tsadness\n"
    assert lx.parse(text, "x") == {"nature": ["bird", "hound", "moor"], "fear": ["hound"], "sadness": ["lonely"]}
    assert lx.parse("", "x") == {} and lx.parse("# only a comment\n", "x") == {}


def test_a_plain_word_list_is_one_category_named_after_the_lexicon():
    assert lx.parse("Moor\nhill\n\n# note\nmoor\n", "Nature words") == {"nature words": ["hill", "moor"]}
    assert lx.parse("﻿moor\r\nhill\r\n", "n") == {"n": ["hill", "moor"]}
    assert lx.parse("moor hill\nhound fear\n", "n") == {"hill": ["moor"], "fear": ["hound"]}     # a second column makes it word + category


def test_csv_and_tsv_files_are_read_with_quotes_semicolons_and_a_header_row():
    nature_fear = {"nature": ["hill", "moor"], "fear": ["hound"]}
    assert lx.parse("word,category\nmoor,nature\nhill,nature\nhound,fear\n", "x") == nature_fear           # a header row is skipped
    assert lx.parse("word;category;flag\nmoor;nature;1\nhill;nature;1\nhound;fear;1\ngoose;fear;0\n", "x") == nature_fear
    assert lx.parse("Term\tCategory\nmoor\tnature\nhill\tnature\nhound\tfear\n", "x") == nature_fear
    assert lx.parse('"moor","nature"\n"hound, big","fear"\n', "x") == {"nature": ["moor"], "fear": ["hound, big"]}     # quotes protect a delimiter
    assert lx.parse("moor,nature\r\nhound,fear\r\n", "x") == {"nature": ["moor"], "fear": ["hound"]}            # a tiny file is long, not wide
    assert lx.parse("word\nmoor\nhill\n", "x") == {"x": ["hill", "moor"]} and lx.parse('"at last"\nmoor\n', "x") == {"x": ["at last", "moor"]}


def test_wide_files_have_a_column_per_category():
    wide = "Nature,Fear\nmoor,hound\nhill,dread\n,fright\nbog,\n"                                    # empty cells are ignored
    assert lx.parse(wide, "x") == {"nature": ["bog", "hill", "moor"], "fear": ["dread", "fright", "hound"]}
    assert lx.parse(wide.replace(",", "\t"), "x") == lx.parse(wide, "x") and lx.parse(wide.replace(",", ";"), "x") == lx.parse(wide, "x")
    assert lx.parse("a,b,c\nx,y,z\n", "x") == {"a": ["x"], "b": ["y"], "c": ["z"]}                         # three words columns: wide, not a flag
    assert lx.parse("a,b,c,d\n1,2,3,4\n", "x") == {"a": ["1"], "b": ["2"], "c": ["3"], "d": ["4"]}
    two = "pos,neg\n" + "".join(f"w{i},n{i}\n" for i in range(5))                                          # two columns, none repeated: wide
    assert lx.parse(two, "x") == {"pos": [f"w{i}" for i in range(5)], "neg": [f"n{i}" for i in range(5)]}
    long = "moor,nature\n" + "".join(f"w{i},{'nature' if i % 2 else 'fear'}\n" for i in range(5))              # a repeated category: long
    assert set(lx.parse(long, "x")) == {"nature", "fear"}
    with pytest.raises(ValueError, match="one column per category"):
        lx.create(__import__("tempfile").mkdtemp(), "Empty", "\n,\n")


def test_words_of_a_box_are_split_on_anything_and_lowercased():
    assert lx.split_words("Moor, hill;\nhound  moor") == ["hill", "hound", "moor"] and lx.split_words(" \n ") == []


# ---------- storing ----------
def test_create_gives_an_id_from_the_name_and_a_number_when_it_is_taken(tmp_path):
    a = lx.create(tmp_path, "Nature words!", PAIRS)
    assert a == "nature-words" and json.loads((tmp_path / "nature-words.json").read_text())["cats"]["nature"] == ["hill", "moor"]
    assert lx.create(tmp_path, "Other", "moor\nhill\n") == "other"
    assert lx.new_id(tmp_path, "nature words") == "nature-words-2" and lx.new_id(tmp_path, "???") == "lexicon"
    assert lx.new_id(tmp_path, "Emotion") == "emotion-2"                # the emotion id is never given to another lexicon


def test_names_are_checked(tmp_path):
    lx.create(tmp_path, "Nature", PAIRS)
    for name, message in (("", "Give the lexicon a name"), ("nature", "already a lexicon called"), ("Emotion", "already a lexicon called"),
                          ("x" * 81, "at most")):
        with pytest.raises(ValueError, match=message):
            lx.create(tmp_path, name, PAIRS)
    with pytest.raises(ValueError, match="No words found"):
        lx.create(tmp_path, "Empty", "nothing useful here\n")
    assert [r["id"] for r in lx.listing(tmp_path)] == ["nature"]


def test_the_emotion_lexicon_is_special(tmp_path):
    assert lx.create(tmp_path, "NRC-Wordlevel", PAIRS, emotion=True) == "emotion"
    row = lx.listing(tmp_path)[0]
    assert row["id"] == "emotion" and row["name"] == "Emotion" and row["source"] == "NRC-Wordlevel" and row["categories"] == {"fear": 1, "nature": 2}
    assert lx.heading("emotion", lx.get(tmp_path, "emotion")) == "Emotion"
    with pytest.raises(ValueError, match="already loaded"):
        lx.create(tmp_path, "Again", PAIRS, emotion=True)
    with pytest.raises(ValueError, match="always called Emotion"):
        lx.rename(tmp_path, "emotion", "Feelings")
    lx.create(tmp_path, "Aardvark", "moor\n")
    assert [r["id"] for r in lx.listing(tmp_path)] == ["emotion", "aardvark"]            # the emotion lexicon is listed first
    lx.replace(tmp_path, "emotion", "a\tjoy\n")
    assert lx.get(tmp_path, "emotion") == {"name": "NRC-Wordlevel", "cats": {"joy": ["a"]}}


def test_rename_replace_and_remove_keep_the_id(tmp_path):
    lid = lx.create(tmp_path, "Nature", PAIRS)
    other = lx.create(tmp_path, "Other", "moor\n")
    lx.rename(tmp_path, lid, "Landscape")
    assert lx.get(tmp_path, lid)["name"] == "Landscape" and lx.listing(tmp_path)[0]["id"] == lid
    with pytest.raises(ValueError, match="already a lexicon"):
        lx.rename(tmp_path, other, "landscape")
    lx.rename(tmp_path, lid, "LANDSCAPE")                                  # a lexicon may change its own name's case
    lx.replace(tmp_path, lid, "hill\nvale\n")
    assert lx.get(tmp_path, lid) == {"name": "LANDSCAPE", "cats": {"landscape": ["hill", "vale"]}}
    lx.remove(tmp_path, lid)
    assert sorted(lx.stored(tmp_path)) == [other]
    for action in (lambda: lx.remove(tmp_path, lid), lambda: lx.get(tmp_path, lid), lambda: lx.replace(tmp_path, lid, "a\n")):
        with pytest.raises(KeyError):
            action()


def test_an_id_from_a_request_cannot_leave_the_folder(tmp_path):
    for bad in ("../x", "a/b", "", "A", ".hidden", "x" * 61):
        with pytest.raises(KeyError):
            lx.path(tmp_path, bad)


def test_the_number_of_lexicons_and_categories_is_limited(tmp_path, monkeypatch):
    monkeypatch.setattr(lx, "MAX_LEXICONS", 2)
    lx.create(tmp_path, "One", "a\n")
    lx.create(tmp_path, "Two", "a\n")
    with pytest.raises(ValueError, match="at most 2 lexicons"):
        lx.create(tmp_path, "Three", "a\n")
    monkeypatch.setattr(lx, "MAX_CATEGORIES", 1)
    with pytest.raises(ValueError, match="at most 1 categories"):
        lx.replace(tmp_path, "one", "a\tx\nb\ty\n")
    monkeypatch.setattr(lx, "MAX_PAIRS", 1)
    with pytest.raises(ValueError, match="at most 1 words"):
        lx.replace(tmp_path, "one", "a\nb\n")
    assert lx.get(tmp_path, "one")["cats"] == {"one": ["a"]}               # a refused change leaves the lexicon as it was


def test_damaged_files_are_reported_and_can_be_replaced_or_removed(tmp_path):
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    lx.create(tmp_path, "Fine", "a\n")
    assert lx.stored(tmp_path).keys() == {"fine"} and lx.stored(tmp_path / "missing") == {}
    broken = next(r for r in lx.listing(tmp_path) if r["id"] == "broken")
    assert "can't be read" in broken["problem"] and broken["categories"] == {}
    with pytest.raises(ValueError, match="can't be read"):
        lx.get(tmp_path, "broken")
    lx.replace(tmp_path, "broken", "moor\nhill\n")
    assert lx.get(tmp_path, "broken") == {"name": "broken", "cats": {"broken": ["hill", "moor"]}}
    (tmp_path / "broken.json").write_text("[1]", encoding="utf-8")
    lx.remove(tmp_path, "broken")
    assert not (tmp_path / "broken.json").exists()


# ---------- categories ----------
def test_a_category_can_be_rewritten_renamed_added_and_deleted(tmp_path):
    lid = lx.create(tmp_path, "Mood", "a\tjoy\nb\tjoy\nc\tfear\n")
    lx.save_category(tmp_path, lid, "joy", "Delight", "B, c\nd")
    assert lx.get(tmp_path, lid)["cats"] == {"fear": ["c"], "delight": ["b", "c", "d"]}
    lx.save_category(tmp_path, lid, None, "calm", "e")
    assert lx.get(tmp_path, lid)["cats"]["calm"] == ["e"]
    for args, message in (((None, "fear", "x"), "already has a category"), (("fear", " ", "x"), "Give the category a name"),
                          (("fear", "fear", " , "), "at least one word")):
        with pytest.raises(ValueError, match=message):
            lx.save_category(tmp_path, lid, *args)
    with pytest.raises(KeyError):
        lx.save_category(tmp_path, lid, "missing", "x", "y")
    lx.delete_category(tmp_path, lid, "calm")
    lx.delete_category(tmp_path, lid, "fear")
    with pytest.raises(ValueError, match="at least one category"):
        lx.delete_category(tmp_path, lid, "delight")
    with pytest.raises(KeyError):
        lx.delete_category(tmp_path, lid, "fear")


# ---------- the routes ----------
def test_lexicon_workflow_through_the_routes(client):
    assert client.get("/api/lexicons").json() == {"lexicons": [], "id": None}
    assert "No words found" in client.post("/api/lexicons", json={"name": "Bad", "text": "nothing useful here"}).json()["detail"]
    assert "“name” is missing" in client.post("/api/lexicons", json={"text": "a"}).json()["detail"]
    r = client.post("/api/lexicons", json={"name": "Tiny", "text": PAIRS}).json()
    assert r["id"] == "tiny" and r["lexicons"] == [{"id": "tiny", "name": "Tiny", "source": None, "categories": {"fear": 1, "nature": 2}, "problem": None}]
    e = client.post("/api/narrative/lexicon", json={"books": ALL, "seg": SEG, "lexicon": "tiny", "cats": ["nature"]}).json()
    assert [s["name"] for s in e["series"]] == ["nature"] and sum(e["series"][0]["counts"]) > 0
    every = client.post("/api/narrative/lexicon", json={"books": ALL, "seg": SEG, "lexicon": "tiny"}).json()
    assert [s["name"] for s in every["series"]] == ["fear", "nature"]
    assert client.get("/api/lexicons/tiny/words", params={"category": "nature"}).json() == {"category": "nature", "words": ["hill", "moor"]}
    client.post("/api/lexicons/tiny/rename", json={"name": "Landscape"})
    client.post("/api/lexicons/tiny/replace", json={"text": "hound\nmoor\n"})
    client.post("/api/lexicons/tiny/category", json={"category": None, "name": "extra", "text": "hill"})
    r = client.post("/api/lexicons/tiny/category/delete", json={"category": "landscape"}).json()
    assert r["lexicons"][0]["name"] == "Landscape" and r["lexicons"][0]["categories"] == {"extra": 1}
    assert client.post("/api/lexicons/tiny/delete").json()["lexicons"] == []


def test_a_csv_file_is_stored_through_the_route(client):
    r = client.post("/api/lexicons", json={"name": "Moods", "text": "\ufeffword;category;flag\r\nmoor;nature;1\r\n\"hound\";fear;1\r\nhill;nature;0\r\n"}).json()
    assert r["lexicons"][0]["categories"] == {"fear": 1, "nature": 1}
    wide = client.post("/api/lexicons", json={"name": "Wide", "text": "joy\tgloom\nglad\tdull\nmerry\t\n"}).json()
    assert wide["lexicons"][1]["categories"] == {"gloom": 1, "joy": 2}
    assert "one column per category" in client.post("/api/lexicons", json={"name": "Nothing", "text": ",,\n"}).json()["detail"]


def test_the_routes_refuse_what_does_not_exist(client):
    assert client.post("/api/lexicons/nope/delete").status_code == 404
    assert client.get("/api/lexicons/nope/words", params={"category": "x"}).status_code == 404
    assert client.post("/api/narrative/lexicon", json={"books": ALL, "seg": SEG, "lexicon": "nope"}).status_code == 404
    client.post("/api/lexicons", json={"name": "Tiny", "text": PAIRS})
    assert client.post("/api/lexicons/tiny/category/delete", json={"category": "nope"}).status_code == 404
    assert client.get("/api/lexicons/tiny/words", params={"category": "nope"}).status_code == 404
    assert client.post("/api/lexicons/..%2Fx/delete").status_code in (404, 405)


def test_the_emotion_lexicon_is_loaded_through_the_same_routes(client, lib):
    r = client.post("/api/lexicons", json={"name": "NRC", "text": PAIRS, "emotion": True}).json()
    assert r["id"] == "emotion" and r["lexicons"][0]["name"] == "Emotion" and r["lexicons"][0]["source"] == "NRC"
    assert (lib.data_dir / "lexicons" / "emotion.json").exists()
    assert "already loaded" in client.post("/api/lexicons", json={"name": "NRC", "text": PAIRS, "emotion": True}).json()["detail"]
    assert "always called Emotion" in client.post("/api/lexicons/emotion/rename", json={"name": "Feelings"}).json()["detail"]


def test_a_damaged_lexicon_is_reported_by_the_page_route_and_can_be_replaced(client, lib):
    (lib.data_dir / "lexicons" / "emotion.json").write_text("{not json", encoding="utf-8")
    row = client.get("/api/lexicons").json()["lexicons"][0]
    assert row["id"] == "emotion" and "can't be read" in row["problem"]
    assert "can't be read" in client.post("/api/narrative/lexicon", json={"books": ALL, "seg": SEG, "lexicon": "emotion"}).json()["detail"]
    assert client.post("/api/lexicons/emotion/replace", json={"text": "moor\tnature\n"}).json()["lexicons"][0]["problem"] is None


def test_statistics_options_list_every_lexicon(client):
    client.post("/api/lexicons", json={"name": "NRC", "text": PAIRS, "emotion": True})
    client.post("/api/lexicons", json={"name": "Colours", "text": "red\ngreen\n"})
    o = client.post("/api/stats/options", json={"books": ALL}).json()["lexicons"]
    assert o == [{"id": "emotion", "name": "Emotion", "categories": ["fear", "nature"]}, {"id": "colours", "name": "Colours", "categories": ["colours"]}]
