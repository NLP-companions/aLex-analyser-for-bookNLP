"""The Statistics tab (core/statstab.py, core/statsets.py, api/statistics.py): correlation tables, descriptives, saved sets, routes.

The figures are checked against `stats.correlate` / `stats.describe` of the raw values the run returns, and the raw values against
`variables` measured directly, so each layer is tested on its own (the maths in test_stats.py, the counting in test_variables.py)."""
from __future__ import annotations

import zipfile

import pytest

from alex.core import cases as cs
from alex.core import entitygroups, stats, statsets, statstab
from alex.core import variables as vb
from alex.core.view import View

CHAPTERS = {"kind": "pieces", "piece": "slice", "n": 5, "min": 0}         # 15 pieces of the three books
WORDS = [{"kind": "query", "query": q} for q in ("holmes", "said", "looked", "walked")]


def unit(v, book, coref):
    """The unit id of a book's coreference group."""
    return v.member_unit[(book, coref)]


def setup(**kw):
    """A request over the slices with the four words, changed by `kw`."""
    return {"cases": CHAPTERS, "rows": WORDS, **kw}


# ---------- correlations ----------
def test_one_list_is_a_lower_triangle_matrix(view):
    out = statstab.run(view, setup())
    c = out["correlations"]
    assert c["shape"] == "matrix" and c["rows"] == c["columns"] == ["v0", "v1", "v2", "v3"]
    for i, line in enumerate(c["cells"]):
        for j, cell in enumerate(line):
            if j >= i:
                assert cell is None
            else:
                ref = stats.correlate(out["values"][i], out["values"][j])
                assert cell["r"] == pytest.approx(ref["r"]) and cell["n"] == ref["n"] == len(out["cases"]["rows"])
    assert c["tests"] == 6


def test_two_lists_are_a_grid(view):
    out = statstab.run(view, setup(rows=WORDS[:2], columns=WORDS[2:], method="spearman"))
    c = out["correlations"]
    assert c["shape"] == "grid" and c["rows"] == ["v0", "v1"] and c["columns"] == ["v2", "v3"] and c["tests"] == 4
    assert c["cells"][1][0]["r"] == pytest.approx(stats.correlate(out["values"][1], out["values"][2], "spearman")["r"])


def test_the_correction_counts_every_test_in_the_table(view):
    plain = statstab.run(view, setup())["correlations"]
    bonf = statstab.run(view, setup(correction="bonferroni"))["correlations"]
    for a, b in zip((x for line in plain["cells"] for x in line if x), (x for line in bonf["cells"] for x in line if x)):
        assert b["p_adj"] == pytest.approx(min(1, a["p"] * 6)) and b["stars"] == stats.stars(b["p_adj"])
        assert a["p_adj"] == a["p"]


def test_a_variable_without_values_has_empty_cells(view):
    out = statstab.run(view, setup(rows=WORDS[:2] + [{"kind": "attribute", "attr": "speech"}]))       # not a piece attribute
    assert out["variables"][2]["note"] and out["correlations"]["cells"][2][0]["r"] is None
    assert out["correlations"]["tests"] == 1


# ---------- descriptives ----------
def test_descriptives_of_all_cases(view):
    out = statstab.run(view, setup())
    d = out["descriptives"]
    assert d["split"] == "none" and [g["key"] for g in d["groups"]] == ["all"]
    assert d["groups"][0]["stats"] == [stats.describe(v) for v in out["values"]]


def test_pieces_split_by_book(view):
    out = statstab.run(view, setup(split="book"))
    groups = out["descriptives"]["groups"]
    assert [g["key"] for g in groups] == ["all"] + view.books
    rows = out["cases"]["rows"]
    for g in groups[1:]:
        mine = [i for i, r in enumerate(rows) if r["book"] == g["key"]]
        assert g["n"] == len(mine) and g["stats"][0] == stats.describe([out["values"][0][i] for i in mine])
    with pytest.raises(ValueError, match="only be split by book"):
        statstab.run(view, setup(split="gender"))


def test_participants_split_by_book_are_measured_in_each_book(view, lib):
    lib.link(unit(view, "alpha", 1), unit(view, "beta", 5))                             # Holmes, one person in two books
    view = View(lib, view.books)
    people = {"kind": "participants", "sample": "sentences", "min": 0}
    out = statstab.run(view, setup(cases=people, split="book"))
    for g in out["descriptives"]["groups"][1:]:
        sub = cs.build(view, people, books=[g["key"]])
        vals = vb.table(view, sub, WORDS)["values"]
        assert g["n"] == len(sub.rows) and g["stats"] == [stats.describe(v) for v in vals]
    # a person in several books is in several blocks, each with that book's own sample
    sizes = {g["key"]: g["n"] for g in out["descriptives"]["groups"]}
    assert sum(sizes[b] for b in view.books) > sizes["all"]


def test_participants_split_by_tag_gender_and_group(view, lib):
    w, h = unit(view, "alpha", 2), unit(view, "alpha", 1)
    lib.set_tags(w, ["doctor", "narrator"])
    lib.set_tags(h, ["detective"])
    entitygroups.create(lib, "Pair", [w, h])
    v = View(lib, view.books)
    people = {"kind": "participants", "sample": "sentences", "min": 0}
    out = statstab.run(v, setup(cases=people, split="tag"))
    groups = {g["key"]: g for g in out["descriptives"]["groups"]}
    assert groups["doctor"]["n"] == groups["narrator"]["n"] == groups["detective"]["n"] == 1
    assert groups["_untagged"]["n"] == len(out["cases"]["rows"]) - 2
    ids = [r["id"] for r in out["cases"]["rows"]]
    assert groups["doctor"]["stats"][0]["mean"] == pytest.approx(out["values"][0][ids.index(w)])
    gender = statstab.run(v, setup(cases=people, split="gender"))["descriptives"]["groups"][1:]
    assert sum(g["n"] for g in gender) == len(ids)                                       # one gender each
    saved = statstab.run(v, setup(cases=people, split="group"))["descriptives"]["groups"]
    assert [(g["label"], g["n"]) for g in saved[1:]] == [("Pair", 2), ("(in no saved group)", len(ids) - 2)]


def test_bad_requests_are_refused(view):
    for bad in (None, {"rows": []}, setup(rows=WORDS * 8), setup(columns=WORDS * 8), setup(method="kendall"),
                setup(correction="fdr"), setup(split="mood"), setup(cases={"kind": "pages"})):
        with pytest.raises(ValueError):
            statstab.run(view, bad)


# ---------- saved sets ----------
def test_saved_sets_are_kept_renamed_and_removed(lib):
    sid = statsets.create(lib, " Words by chapter ", setup())
    assert statsets.listing(lib) == [{"id": sid, "name": "Words by chapter", "setup": setup()}]
    with pytest.raises(ValueError):
        statsets.create(lib, "words BY chapter", setup())                                 # names are unique, ignoring case
    for bad in ({}, {"rows": []}, "words", {"rows": [{"kind": "query", "query": "x" * statsets.MAX_SETUP}]}):
        with pytest.raises(ValueError):
            statsets.create(lib, "Other", bad)
    statsets.update(lib, sid, name="Chapters", setup=setup(method="spearman"))
    assert statsets.listing(lib)[0]["name"] == "Chapters" and statsets.listing(lib)[0]["setup"]["method"] == "spearman"
    statsets.delete(lib, sid)
    assert statsets.listing(lib) == []
    with pytest.raises(KeyError):
        statsets.delete(lib, sid)


def test_saved_sets_travel_in_the_export(lib):
    from alex.core.export import scoped_state
    statsets.create(lib, "Mine", setup())
    s = scoped_state(lib, {"alpha"})
    assert s["stat_sets"] == lib.state["stat_sets"] and s["next_stat_set"] == lib.state["next_stat_set"] == 2


# ---------- routes ----------
def test_the_route_answers_like_the_core(client, view):
    body = {"books": view.books, "setup": setup()}
    got = client.post("/api/stats", json=body).json()
    assert got["correlations"]["cells"][1][0]["r"] == pytest.approx(statstab.run(view, setup())["correlations"]["cells"][1][0]["r"])
    assert client.post("/api/stats", json={"books": view.books}).status_code == 400
    bad = client.post("/api/stats", json={"books": view.books, "setup": setup(rows=[{"kind": "query", "query": "[x", "mode": "pattern"}])})
    assert bad.status_code == 400 and "“[x”" in bad.json()["detail"]


def test_the_export_route_sends_the_r_files(client, view, tmp_path):
    r = client.post("/api/stats/export", json={"books": view.books, "setup": setup()})
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    assert r.headers["content-disposition"].startswith('attachment; filename="analyser-statistics-')
    (tmp_path / "r.zip").write_bytes(r.content)
    with zipfile.ZipFile(tmp_path / "r.zip") as z:
        assert "analysis_example.R" in z.namelist() and z.read("cases.csv").decode("utf-8").startswith("case_id,book,")
    plain = client.post("/api/stats/export", json={"books": view.books, "setup": setup(), "example": False})
    (tmp_path / "p.zip").write_bytes(plain.content)
    assert "analysis_example.R" not in zipfile.ZipFile(tmp_path / "p.zip").namelist()
    for bad in ({"books": view.books}, {"books": view.books, "setup": {"rows": []}}, {"books": view.books, "setup": setup(cases={"kind": "pages"})}):
        assert client.post("/api/stats/export", json=bad).status_code == 400


def test_the_bulk_route_makes_labelled_variables(client, view):
    words = client.post("/api/stats/bulk", json={"books": view.books, "what": "words", "n": 3, "cases": CHAPTERS}).json()["variables"]
    assert len(words) == 3 and all(w["kind"] == "query" and w["label"].startswith("“") for w in words)
    ents = client.post("/api/stats/bulk", json={"books": view.books, "what": "entities", "n": 2}).json()["variables"]
    assert [e["kind"] for e in ents] == ["mentions"] * 2 and ents[0]["label"].startswith("Mentions of ")
    talk = client.post("/api/stats/bulk", json={"books": view.books, "what": "speakers", "n": 2}).json()["variables"]
    assert [e["kind"] for e in talk] == ["spoken"] * 2 and talk[0]["label"].startswith("Speech of ")
    genders = client.post("/api/stats/bulk", json={"books": view.books, "what": "attribute", "attr": "gender"}).json()["variables"]
    assert genders and all(g["label"].startswith("Gender: ") for g in genders)
    assert client.post("/api/stats/bulk", json={"books": view.books, "what": "feelings"}).status_code == 400
    few = {"books": view.books, "what": "words", "n": 3, "cases": CHAPTERS}
    assert len(client.post("/api/stats/bulk", json={**few, "min_range": 3}).json()["variables"]) == 3
    assert client.post("/api/stats/bulk", json={**few, "min_range": 4}).json()["variables"] == []                     # no word is in four books
    assert client.post("/api/stats/bulk", json={**few, "min_range": "two"}).status_code == 400
    verbs = client.post("/api/stats/bulk", json={**few, "n": 5, "speech_verbs": True}).json()["variables"]
    assert [v["query"] for v in verbs] == ["say"] and verbs[0]["match"] == "lemma"                              # the fixture's quotes are all said
    asked = client.post("/api/stats/bulk", json={**few, "types": ["question"], "weigh_verb": True}).json()["variables"]
    assert asked == []                                                                                          # none is a question
    assert client.post("/api/stats/bulk", json={**few, "types": "question"}).status_code == 400
    assert client.post("/api/stats/bulk", json={**few, "types": ["shout"]}).status_code == 400
    assert client.post("/api/stats/bulk", json={**few, "cases": {"kind": "participants", "min_range": 0}}).status_code == 400


def test_the_set_routes(client):
    made = client.post("/api/stats/sets", json={"name": "Mine", "setup": setup()}).json()
    sid = made["id"]
    assert made["sets"] == [{"id": sid, "name": "Mine", "setup": setup()}] and client.get("/api/stats/sets").json()["sets"] == made["sets"]
    assert client.post(f"/api/stats/sets/{sid}", json={"name": "Ours"}).json()["sets"][0]["name"] == "Ours"
    assert client.post("/api/stats/sets", json={"name": "Ours", "setup": setup()}).status_code == 400
    assert client.post("/api/stats/sets/99", json={"name": "X"}).status_code == 404
    assert client.post("/api/stats/sets/delete", json={"id": sid}).json()["sets"] == []
    assert client.post("/api/stats/sets/delete", json={"id": sid}).status_code == 404


def test_sentences_as_cases_with_missing_and_complete_variables(view):
    out = statstab.run(view, setup(cases={"kind": "pieces", "piece": "sentence"}, rows=WORDS[:2] + [{"kind": "sentiment"}],
                                   method="spearman"))
    n = len(out["cases"]["rows"])
    assert n > 100 and out["descriptives"]["groups"][0]["stats"][0]["n"] == n
    c = out["correlations"]["cells"]
    assert c[1][0]["r"] == pytest.approx(stats.correlate(out["values"][1], out["values"][0], "spearman")["r"])
    assert c[2][0]["r"] == pytest.approx(stats.correlate(out["values"][2], out["values"][0], "spearman")["r"])
