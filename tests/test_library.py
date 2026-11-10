"""Library: finding books, caching them, and keeping your details, tags and links."""
from __future__ import annotations

import json

import pytest

from alex.core import dialogue
from alex.core.library import Library, LibraryError, default_state
from alex.core.view import View


def test_scan_finds_the_three_books_and_their_versions(lib, corpus):
    found, problems = lib.scan()
    assert sorted(found) == ["alpha", "beta", "gamma"] and problems == []
    assert found["alpha"][0]["stamp"] == "20260101-000000" and found["alpha"][0]["exported"]


def test_scan_reports_missing_and_non_folder_sources(lib, tmp_path):
    (tmp_path / "afile").write_text("x")
    lib.state["sources"] = [str(tmp_path / "nowhere"), str(tmp_path / "afile")]
    found, problems = lib.scan()
    assert found == {} and len(problems) == 2


def test_the_newest_export_is_used_unless_one_is_pinned(lib, corpus, tmp_path):
    import shutil
    older = tmp_path / "exports" / "alpha-20250101-000000"
    shutil.copytree(next(corpus[0].glob("alpha-2026*")), older)
    lib.state["sources"] = [str(tmp_path / "exports"), str(corpus[0])]
    found, _ = lib.scan()
    assert [v["stamp"] for v in found["alpha"]] == ["20260101-000000", "20250101-000000"]
    assert lib.folder_for("alpha").name == "alpha-20260101-000000"
    lib.set_meta("alpha", {"pinned": str(older)})
    assert lib.folder_for("alpha") == older
    lib.set_meta("alpha", {"pinned": "/no/such/folder"})
    assert lib.folder_for("alpha").name == "alpha-20260101-000000"     # a pin that no longer exists is ignored


def test_books_are_cached_in_memory_and_on_disk(lib):
    a = lib.book("alpha")
    assert lib.book("alpha") is a
    assert len(list(lib.cache_dir.glob("alpha-*.pkl"))) == 1
    fresh = Library(data_dir=lib.data_dir, sources=lib.state["sources"])
    b = fresh.book("alpha")                                  # from the pickle
    assert b is not a and b.n_tokens == a.n_tokens and len(b.mentions) == len(a.mentions)


def test_a_damaged_cache_file_is_rebuilt(lib):
    lib.book("alpha")
    (pkl,) = lib.cache_dir.glob("alpha-*.pkl")
    pkl.write_bytes(b"not a pickle")
    fresh = Library(data_dir=lib.data_dir, sources=lib.state["sources"])
    assert fresh.book("alpha").n_tokens > 0


def test_changing_a_file_invalidates_the_cache(lib, corpus):
    import os
    before = lib.book("gamma")
    tok = next(corpus[0].glob("gamma-*/gamma.tokens"))
    st = tok.stat()
    os.utime(tok, (st.st_atime, st.st_mtime + 5))
    try:
        assert lib.book("gamma") is not before
    finally:
        os.utime(tok, (st.st_atime, st.st_mtime))


def test_unknown_book_raises_keyerror(lib):
    with pytest.raises(KeyError):
        lib.book("nope")


def test_book_details_persist(lib):
    lib.set_meta("alpha", {"title": "A", "author": "X", "year": 1890, "series": "S", "tags": ["t1"], "bogus": 1})
    again = Library(data_dir=lib.data_dir, sources=lib.state["sources"])
    m = again.meta("alpha")
    assert (m["title"], m["author"], m["year"], m["series"], m["tags"]) == ("A", "X", 1890, "S", ["t1"])
    assert again.meta("beta")["title"] == "beta"          # unset details fall back sensibly


def test_settings_survive_a_partial_settings_file(lib):
    lib.state_path.write_text(json.dumps({"settings": {"min": {"PER": 5}}}), encoding="utf-8")
    again = Library(data_dir=lib.data_dir)
    s = again.state["settings"]
    assert s["min"]["PER"] == 5 and s["min"]["LOC"] == 2 and s["count_mode"] == "per_book" and s["freq_mode"] == "combined" and s["conv_gap"] == 100


@pytest.mark.parametrize("settings", ["x", [], {"min": 5}, {"min": {"PER": "x", "LOC": 0, "ORG": 7}}, {"speech_skip": ["say"]},
                                      {"speech_skip": {"verbs": 5}}, {"conv_gap": "x"}, {"conv_gap": -1}, {"plural": "yes"},
                                      {"count_mode": 5}, {"freq_mode": []}, {"sound": "x"}])
def test_a_wrongly_shaped_setting_falls_back_to_its_default(lib, settings):
    """A hand-edited (or imported) library.json whose settings have the wrong shape used to stop the start or break every Dialogue page."""
    lib.state_path.write_text(json.dumps({"settings": settings, "sources": lib.state["sources"], "flag": 1}), encoding="utf-8")
    again = Library(data_dir=lib.data_dir)
    s, fresh = again.state["settings"], default_state()["settings"]
    assert again.state["flag"] == 1                                    # the rest of the file is read as it was
    kept = {"ORG": 7} if settings == {"min": {"PER": "x", "LOC": 0, "ORG": 7}} else {}         # the one good minimum is kept
    assert s == {**fresh, "min": {**fresh["min"], **kept}}
    view = View(again, ["alpha"])
    dialogue.bdlg(view, "alpha")                                      # reads conv_gap and speech_skip


def test_settings_aLex_does_not_know_are_kept(lib):
    lib.state_path.write_text(json.dumps({"settings": {"future": {"a": 1}, "conv_gap": 40}}), encoding="utf-8")
    s = Library(data_dir=lib.data_dir).state["settings"]
    assert s["future"] == {"a": 1} and s["conv_gap"] == 40

def test_a_damaged_library_file_is_a_clear_error_and_is_left_alone(lib):
    lib.state_path.write_text("{ not json", encoding="utf-8")
    with pytest.raises(LibraryError, match="can't be read"):
        Library(data_dir=lib.data_dir)
    assert lib.state_path.read_text() == "{ not json"


@pytest.mark.parametrize("text", ["[]", '"x"', "5", "null"])
def test_a_settings_file_that_is_not_an_object_is_a_clear_error_too(lib, text):
    """Valid JSON of the wrong shape used to fail later with an AttributeError instead of saying which file is wrong."""
    lib.state_path.write_text(text, encoding="utf-8")
    with pytest.raises(LibraryError, match="should hold one JSON object"):
        Library(data_dir=lib.data_dir)
    lib.state_path.unlink()
    lib.annot_path.write_text(text, encoding="utf-8")
    with pytest.raises(LibraryError, match="Your corrections file"):
        Library(data_dir=lib.data_dir)


def test_saving_leaves_no_temporary_files(lib):
    lib.set_meta("alpha", {"title": "A"})
    lib.save_ann()
    assert not list(lib.data_dir.glob("*.tmp"))


# ---------- tags and links ----------
def test_tags_are_sorted_deduplicated_and_listed(lib):
    lib.set_tags("e:alpha:1", [" b ", "a", "b", ""])
    assert lib.tags_of("e:alpha:1") == ["a", "b"]
    lib.set_tags("e:alpha:2", ["Z"])
    assert lib.all_tags() == ["a", "b", "Z"]
    lib.set_tags("e:alpha:1", [])
    assert lib.tags_of("e:alpha:1") == []
    with pytest.raises(KeyError):
        lib.set_tags("p:99", ["x"])


def test_linking_merges_members_tags_and_name(lib):
    lib.set_tags("e:alpha:1", ["detective"])
    p = lib.link("e:alpha:1", "e:beta:5", name="Sherlock")
    assert p.startswith("p:") and lib.tags_of(p) == ["detective"]
    assert lib.tags_of("e:alpha:1") == []                          # the tags moved to the person
    assert lib.person_of() == {("alpha", 1): p[2:], ("beta", 5): p[2:]}
    p2 = lib.link(p, "e:gamma:3")
    assert p2 == p and len(lib.state["persons"][p[2:]]["members"]) == 3
    assert lib.state["persons"][p[2:]]["name"] == "Sherlock"


def test_linking_two_persons_absorbs_the_second(lib):
    a = lib.link("e:alpha:1", "e:beta:5")
    b = lib.link("e:alpha:2", "e:beta:6")
    c = lib.link(a, b)
    assert c == a and b[2:] not in lib.state["persons"] and len(lib.state["persons"][a[2:]]["members"]) == 4


def test_unlinking_dissolves_a_person_with_one_member_and_keeps_tags(lib):
    lib.set_tags("e:alpha:1", ["x"])
    p = lib.link("e:alpha:1", "e:beta:5")
    lib.unlink(p[2:], "beta", 5)
    assert p[2:] not in lib.state["persons"]
    assert lib.tags_of("e:alpha:1") == ["x"] and lib.tags_of("e:beta:5") == ["x"]


def test_reset_links_dissolves_persons_and_narrator_links_but_keeps_rejections(lib):
    p = lib.link("e:alpha:1", "e:beta:5", name="Sherlock")
    lib.set_tags(p, ["detective"])
    lib.link_narrators("nar:anon:alpha", "nar:anon:beta")
    lib.reject("e:alpha:2", "e:beta:6")
    assert lib.reset_links() == (1, 1)
    assert not lib.state["persons"] and not lib.state["narrator_links"]
    assert lib.name_of("e:alpha:1") == "Sherlock" and lib.tags_of("e:beta:5") == ["detective"]
    assert lib.is_rejected("e:alpha:2", "e:beta:6")
    assert lib.reset_links() == (0, 0)


def test_unlink_all_dissolves_a_person_of_several_members(lib):
    p = lib.link("e:alpha:1", "e:beta:5", name="Sherlock")
    p = lib.link(p, "e:gamma:3")
    lib.set_tags(p, ["detective"])
    lib.set_note(p, "The detective")
    lib.unlink_all(p[2:])
    assert p[2:] not in lib.state["persons"]
    for uid in ("e:alpha:1", "e:beta:5", "e:gamma:3"):
        assert lib.tags_of(uid) == ["detective"] and lib.name_of(uid) == "Sherlock" and lib.note_of(uid) == "The detective"
    with pytest.raises(KeyError):
        lib.unlink_all("nope")


def test_rename_person(lib):
    p = lib.link("e:alpha:1", "e:beta:5")
    lib.set_name(p, "  Holmes ")
    assert lib.state["persons"][p[2:]]["name"] == "Holmes"
    lib.set_name(p, "  ")
    assert lib.state["persons"][p[2:]]["name"] is None


def test_an_entity_is_never_in_two_persons(lib):
    """Linking an entity that is already part of a person extends that person (it doesn't make a second one holding the same
    entity), and linking two members of one person, or an entity with itself, changes nothing."""
    p = lib.link("e:alpha:1", "e:beta:5")
    assert lib.link("e:alpha:1", "e:gamma:3") == p
    assert sorted(map(tuple, lib.state["persons"][p[2:]]["members"])) == [("alpha", 1), ("beta", 5), ("gamma", 3)]
    assert len(lib.state["persons"]) == 1
    before = json.dumps(lib.state["persons"], sort_keys=True)
    assert lib.link("e:alpha:1", "e:beta:5") == p and lib.link(p, "e:gamma:3") == p
    assert json.dumps(lib.state["persons"], sort_keys=True) == before
    assert lib.link("e:alpha:2", "e:alpha:2") == "e:alpha:2" and len(lib.state["persons"]) == 1
    with pytest.raises(KeyError):
        lib.link("p:999", "e:alpha:2")
    with pytest.raises(KeyError):
        lib.link("nonsense", "e:alpha:2")
    with pytest.raises(KeyError):                         # taking out an entity that isn't a member
        lib.unlink(p[2:], "alpha", 2)


def test_name_and_note_of_an_entity(lib):
    assert lib.name_of("e:alpha:1") is None and lib.note_of("e:alpha:1") == ""
    lib.set_name("e:alpha:1", "  Sherlock  ")
    lib.set_note("e:alpha:1", "  The detective  ")
    assert lib.name_of("e:alpha:1") == "Sherlock" and lib.note_of("e:alpha:1") == "The detective"
    lib.set_name("e:alpha:1", "  ")
    lib.set_note("e:alpha:1", "  ")
    assert lib.name_of("e:alpha:1") is None and lib.note_of("e:alpha:1") == ""
    with pytest.raises(KeyError):
        lib.set_name("p:99", "x")
    with pytest.raises(KeyError):
        lib.set_note("p:99", "x")


def test_linking_merges_names_and_descriptions_too(lib):
    lib.set_name("e:alpha:1", "Sherlock")
    lib.set_note("e:beta:5", "The detective")
    p = lib.link("e:alpha:1", "e:beta:5")
    assert lib.name_of("e:alpha:1") is None                        # moved to the person, like tags
    assert lib.state["persons"][p[2:]]["name"] == "Sherlock" and lib.state["persons"][p[2:]]["note"] == "The detective"


def test_unlinking_keeps_name_and_description_too(lib):
    p = lib.link("e:alpha:1", "e:beta:5", name="Sherlock")
    lib.set_note(p, "The detective")
    lib.unlink(p[2:], "beta", 5)
    assert lib.name_of("e:alpha:1") == "Sherlock" and lib.note_of("e:alpha:1") == "The detective"
    assert lib.name_of("e:beta:5") == "Sherlock" and lib.note_of("e:beta:5") == "The detective"


def test_rejection_survives_later_links(lib):
    lib.reject("e:alpha:1", "e:beta:5")
    assert lib.is_rejected("e:alpha:1", "e:beta:5") and lib.is_rejected("e:beta:5", "e:alpha:1")
    p = lib.link("e:alpha:1", "e:gamma:3")
    assert lib.is_rejected(p, "e:beta:5")                          # a member of the person was rejected
    lib.reject(p, "e:beta:5")
    assert len(lib.state["rejected"]) == 2                        # no duplicate pairs, but the new member is recorded


def test_links_persist(lib):
    p = lib.link("e:alpha:1", "e:beta:5", name="H")
    again = Library(data_dir=lib.data_dir, sources=lib.state["sources"])
    assert again.person_of()[("alpha", 1)] == p[2:] and again.state["next_person"] == 2


def test_linking_narrator_roles(lib):
    """Narrator roles (nar:<unit id> / nar:anon:<book>) aren't units, so they go through their own link/unlink
    (link_narrators/unlink_narrator/unlink_narrators_all), separate from link/unlink above — same shape, own store."""
    lid = lib.link_narrators("nar:anon:alpha", "nar:anon:beta", name="Chronicle")
    assert lid == "nl:1"
    assert lib.state["narrator_links"]["1"]["members"] == ["nar:anon:alpha", "nar:anon:beta"]
    assert lib.state["narrator_links"]["1"]["name"] == "Chronicle"
    assert lib.narrator_link_of() == {"nar:anon:alpha": lid, "nar:anon:beta": lid}
    # growing an existing link
    lid2 = lib.link_narrators(lid, "nar:anon:gamma")
    assert lid2 == lid and lib.state["narrator_links"]["1"]["members"] == ["nar:anon:alpha", "nar:anon:beta", "nar:anon:gamma"]
    # renaming via the same unified name store entities and persons use
    lib.set_name(lid, "The Editors")
    assert lib.name_of(lid) == "The Editors"
    with pytest.raises(KeyError):
        lib.set_name("nl:404", "x")


def test_unlinking_a_narrator_role_dissolves_a_link_of_two(lib):
    lid = lib.link_narrators("nar:anon:alpha", "nar:anon:beta")
    lib.unlink_narrator(lid[3:], "nar:anon:beta")
    assert lid[3:] not in lib.state["narrator_links"] and lib.narrator_link_of() == {}


def test_unlink_narrators_all_dissolves_a_link_of_several(lib):
    lid = lib.link_narrators("nar:anon:alpha", "nar:anon:beta")
    lib.link_narrators(lid, "nar:anon:gamma")
    lib.unlink_narrators_all(lid[3:])
    assert lid[3:] not in lib.state["narrator_links"] and lib.narrator_link_of() == {}


def test_a_narrator_role_is_never_in_two_links(lib):
    """A role already in a link stands for that link: linking it again extends the link instead of starting a second one."""
    lid = lib.link_narrators("nar:anon:alpha", "nar:anon:beta")
    assert lib.link_narrators("nar:anon:beta", "nar:anon:gamma") == lid
    assert lib.state["narrator_links"][lid[3:]]["members"] == ["nar:anon:alpha", "nar:anon:beta", "nar:anon:gamma"]
    assert len(lib.state["narrator_links"]) == 1
    assert lib.link_narrators("nar:anon:alpha", lid) == lid                 # already one: nothing changes
    with pytest.raises(KeyError):
        lib.link_narrators("e:alpha:1", "nar:anon:alpha")                 # not a narrator role
    with pytest.raises(KeyError):
        lib.link_narrators("nl:999", "nar:anon:alpha")


def test_corrections_persist_and_bump_versions(lib):
    v = lib.version
    lib.ann_book("alpha")["narrator"] = "p:1"
    lib.save_ann()
    assert lib.version == v + 1 and lib.ann_version == 1
    again = Library(data_dir=lib.data_dir)
    assert again.ann["books"]["alpha"]["narrator"] == "p:1"


def test_warming_loads_every_book_and_skips_the_ones_that_cannot_be_read(lib, tmp_path):
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "broken.tokens").write_text("not\ta\tbook\n", encoding="utf-8")
    (tmp_path / "x" / "broken.entities").write_text("COREF\n", encoding="utf-8")
    lib.state["sources"].append(str(tmp_path / "x"))
    lib.reset_scan()
    lib.warm()
    assert {key[0] for key in lib._loaded} == {"alpha", "beta", "gamma"}


def test_a_folder_reached_through_two_sources_is_one_version(corpus, tmp_path):
    """Adding a folder and also its parent (or a link to it) must not list the same export twice."""
    exports = corpus[0]
    one = next(exports.glob("alpha-*"))
    lib = Library(data_dir=tmp_path / "data", sources=[exports, one, exports])
    found, _ = lib.scan()
    assert [len(v) for b, v in found.items() if b == "alpha"] == [1]


def test_a_fresh_library_has_no_source_folders_and_finds_no_books(tmp_path):
    """Nothing is assumed about where books are: a new install starts empty and is told to add a folder."""
    fresh = Library(data_dir=tmp_path / "data")
    assert fresh.state["sources"] == [] and fresh.scan() == ({}, [])


def test_add_sources_adds_full_paths_once_and_remembers_them(corpus, tmp_path):
    lib = Library(data_dir=tmp_path / "data")
    added = lib.add_sources([corpus[0], corpus[0], str(corpus[0]) + "/."])                      # the same folder, spelled three ways
    assert added == [str(corpus[0].resolve())] and sorted(lib.scan()[0]) == ["alpha", "beta", "gamma"]
    assert lib.add_sources([corpus[0]]) == [] and lib.add_sources([]) == []                   # nothing new: nothing changes
    assert Library(data_dir=lib.data_dir).state["sources"] == [str(corpus[0].resolve())]      # it was saved


# ---------- corrections follow links ----------
def corrections(lib, narrator, book="alpha"):
    """Give a book one correction of every kind that names a unit, all naming `narrator`; returns the book's annotations."""
    ab = lib.ann_book(book)
    ab["narrator"] = narrator
    ab["para_narrators"] = {"a para#1": narrator, "other#1": "anon"}
    ab["chapter_narrators"] = {"a chapter#1": narrator}
    ab["addressees"] = {"a quote#1": [narrator, "e:alpha:1"], "everyone#1": ["*"]}
    ab["participants"] = {"a quote#1": {"add": [narrator], "remove": []}}
    lib.save_ann()
    return ab


def test_linking_keeps_corrections_on_the_right_unit(lib):
    """A correction that named an entity now names the person it became; "anon" and "*" are left alone."""
    ab = corrections(lib, "e:alpha:2")
    p = lib.link("e:alpha:2", "e:beta:6")
    assert ab["narrator"] == p and ab["para_narrators"] == {"a para#1": p, "other#1": "anon"} and ab["chapter_narrators"] == {"a chapter#1": p}
    assert ab["addressees"] == {"a quote#1": [p, "e:alpha:1"], "everyone#1": ["*"]} and ab["participants"]["a quote#1"]["add"] == [p]


def test_absorbing_a_person_moves_its_corrections_too(lib):
    """The bug: linking two persons dropped the second's id, so a narrator set on it pointed at nobody."""
    a, b = lib.link("e:alpha:1", "e:beta:5"), lib.link("e:alpha:2", "e:beta:6")
    ab = corrections(lib, b)
    ab["addressees"]["a quote#1"] = [a, b]                       # both now one person: named once
    c = lib.link(a, b)
    assert c == a and ab["narrator"] == a and ab["addressees"]["a quote#1"] == [a]


def test_unlinking_gives_a_book_its_own_entity_back(lib):
    """In a book where the person has no member left, a correction names that book's entity; elsewhere it stays on the person."""
    p = lib.link("e:alpha:2", "e:beta:6")
    p = lib.link(p, "e:gamma:4")
    alpha, beta = corrections(lib, p, "alpha"), corrections(lib, p, "beta")
    lib.unlink(p[2:], "alpha", 2)
    assert alpha["narrator"] == "e:alpha:2" and alpha["addressees"]["a quote#1"] == ["e:alpha:2", "e:alpha:1"]
    assert beta["narrator"] == p, "the person is still in beta"
    lib.unlink(p[2:], "beta", 6)                                  # one member left: the person dissolves
    assert p[2:] not in lib.state["persons"] and beta["narrator"] == "e:beta:6"


def test_dissolving_a_person_returns_every_book_to_its_entity(lib):
    p = lib.link(lib.link("e:alpha:2", "e:beta:6"), "e:gamma:4")
    alpha, gamma = corrections(lib, p, "alpha"), corrections(lib, p, "gamma")
    lib.unlink_all(p[2:])
    assert alpha["narrator"] == "e:alpha:2" and gamma["narrator"] == "e:gamma:4" and gamma["participants"]["a quote#1"]["add"] == ["e:gamma:4"]


def test_narrator_links_follow_the_units_they_name(lib):
    a = lib.link("e:alpha:2", "e:beta:6")
    lid = lib.link_narrators("nar:" + a, "nar:anon:gamma")
    b = lib.link(a, "e:gamma:4")
    assert b == a and lib.state["narrator_links"][lid[3:]]["members"] == ["nar:" + a, "nar:anon:gamma"]
    lib.unlink_all(a[2:])                                         # the person is gone: its role becomes a role per entity
    assert lib.state["narrator_links"][lid[3:]]["members"] == ["nar:e:alpha:2", "nar:e:beta:6", "nar:e:gamma:4", "nar:anon:gamma"]


def test_linked_narrator_roles_that_become_one_are_no_link(lib):
    """Two roles of the same character, linked, then the character linked: one role is left, so there is nothing to link."""
    lid = lib.link_narrators("nar:e:alpha:2", "nar:e:beta:6")
    lib.link("e:alpha:2", "e:beta:6")
    assert lid[3:] not in lib.state["narrator_links"]


def test_linking_does_not_rewrite_corrections_it_did_not_change(lib):
    corrections(lib, "e:gamma:4")
    version = lib.ann_version
    lib.link("e:beta:5", "e:gamma:3")                           # nothing in the corrections names either
    assert lib.ann_version == version


def test_a_book_being_parsed_does_not_block_the_library(lib, monkeypatch):
    """Parsing a novel takes seconds. It happens outside the library lock, so a save (or a request for another book) goes through meanwhile,
    and two threads that want the same book parse it once."""
    import threading
    from alex.core import library as library_module
    started, release, parses = threading.Event(), threading.Event(), []
    real = library_module.BookData

    def slow(bid, folder):
        parses.append(bid)
        started.set()
        release.wait(5)
        return real(bid, folder)

    monkeypatch.setattr(library_module, "BookData", slow)
    loaded = []
    threads = [threading.Thread(target=lambda: loaded.append(lib.book("alpha"))) for _ in range(2)]
    for t in threads:
        t.start()
    assert started.wait(5)
    done = threading.Event()
    saver = threading.Thread(target=lambda: (lib.set_meta("beta", {"title": "While alpha is read"}), done.set()))
    saver.start()
    assert done.wait(2), "a save waited for the book being parsed"
    release.set()
    for t in threads + [saver]:
        t.join(5)
    assert parses == ["alpha"] and len(loaded) == 2 and loaded[0] is loaded[1]


def test_warming_reports_its_progress(lib):
    seen = []
    lib.warm(lambda done, total: seen.append((done, total)))
    assert seen == [(1, 3), (2, 3), (3, 3)]
