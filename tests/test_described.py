"""Described as (core/described.py): who describes a target as what.

The answer key is counted straight from the book's quotes and mentions, not through the code under test: whether a mention is inside
a quote (`bd.quotes`), who speaks that quote, and who narrates (the book's narrator, set here to Watson)."""
from __future__ import annotations

import pytest

from alex.core import described as ds
from alex.core import dialogue as dl
from alex.core.view import View


def unit(v, book, coref):
    """The unit id of a book's coreference group."""
    return v.member_unit[(book, coref)]


@pytest.fixture
def told(lib):
    """Alpha only, told by Watson (unit and coref 2); returns (view, Watson's unit id, Holmes's unit id)."""
    v = View(lib, ["alpha"])
    w = unit(v, "alpha", 2)
    lib.ann_book("alpha")["narrator"] = w
    lib.save_ann()
    v = View(lib, ["alpha"])
    return v, w, unit(v, "alpha", 1)


def where(bd, mi):
    """(speaker coref or None, in a quote?) of a mention, from the quotes themselves."""
    tok = bd.mentions[mi][1]
    for q in bd.quotes:
        if q["start"] <= tok <= q["end"]:
            return q["char"], True
    return None, False


def column(t, cid):
    """The column of a table with this id."""
    return next(c for c in t["columns"] if c["id"] == cid)


def cell(t, item, cid):
    """The cell of a table for a word and a column id."""
    row = next(r for r in t["rows"] if r["item"] == item)
    return row["cells"][[c["id"] for c in t["columns"]].index(cid)]


def test_a_narrator_who_is_a_character_is_that_character(told):
    """Holmes's names: said in Watson's narration or in Watson's own quotes, both are "Watson"'s."""
    v, w, h = told
    bd = v.bd["alpha"]
    names = [mi for mi in bd.groups[1].mentions if bd.mentions[mi][3] == "PROP"]
    by_watson = [mi for mi in names if not where(bd, mi)[1] or where(bd, mi)[0] == 2]
    spoken = [mi for mi in by_watson if where(bd, mi)[1]]
    assert spoken and len(spoken) < len(by_watson), "the fixture should have both kinds"
    t = ds.table(v, {"kind": "unit", "id": h}, "name", "entity")
    c = column(t, w)
    assert c["label"] == "Watson" and c["findings"] == len(by_watson) and c["narration"] == len(by_watson) - len(spoken)
    assert [c["id"] for c in t["columns"]] == [w] and t["all"]["findings"] == len(names) == len(by_watson)      # nobody else names him


def test_every_finding_has_one_describer(told):
    """With one describer per finding, the columns add up to the whole, whichever way they are split."""
    v, w, h = told
    for split in ("entity", "gender", "voice", "book"):
        t = ds.table(v, {"kind": "unit", "id": h}, "agent", split, top=30)
        assert sum(c["findings"] for c in t["columns"]) == t["all"]["findings"] == sum(v.bd["alpha"].groups[1].rel["agent"].values())
        assert all(sum(c["n"] for c in r["cells"]) == r["total"] for r in t["rows"])


def test_speech_and_narration_are_told_apart(told):
    v, w, h = told
    bd = v.bd["alpha"]
    t = ds.table(v, {"kind": "unit", "id": h}, "agent", "voice")
    speech = sum(1 for k, mi, hl in bd.groups[1].rel_ev["agent"] if where(bd, mi)[1])
    assert column(t, "speech")["findings"] == speech > 0 and column(t, "narration")["findings"] == t["all"]["findings"] - speech
    assert cell(t, "see", "speech")["n"] > 0 and cell(t, "see", "narration")["n"] == 0        # "I see…" is said, never narrated
    assert cell(t, "see", "speech")["ll"] > 0 > cell(t, "see", "narration")["ll"]              # keyness: typical of speech, not of narration


def test_the_voice_switch_keeps_one_voice(told):
    v, w, h = told
    spec = {"kind": "unit", "id": h}
    both, narr, spoken = (ds.table(v, spec, "agent", "voice", voice=x) for x in ds.VOICES)
    assert narr["all"]["findings"] + spoken["all"]["findings"] == both["all"]["findings"]
    assert [c["id"] for c in narr["columns"]] == ["narration"] and [c["id"] for c in spoken["columns"]] == ["speech"]
    assert narr["all"]["words"] + spoken["all"]["words"] == both["all"]["words"]


def test_words_are_what_the_describers_produce(told, truth):
    """Per-1,000 rates divide by the words a column speaks and narrates in the books the target is in."""
    v, w, h = told
    from alex.core.corpus import cindex
    narrated = sum(1 for i, isw in enumerate(cindex(v.bd["alpha"])["isword"]) if isw and not cindex(v.bd["alpha"])["in_quote"][i])
    t = ds.table(v, {"kind": "unit", "id": h}, "name", "entity", top=30)
    assert column(t, w)["words"] == narrated + truth["alpha"].quote_words[2]
    row = t["rows"][0]
    c = column(t, w)
    assert row["cells"][[x["id"] for x in t["columns"]].index(w)]["per1k"] == pytest.approx(1000 * row["cells"][[x["id"] for x in t["columns"]].index(w)]["n"] / c["words"])
    assert t["all"]["words"] == narrated + truth["alpha"].dialogue_words


def test_an_unnamed_narrator_stays_a_role(lib):
    v = View(lib, ["beta"])
    t = ds.table(v, {"kind": "unit", "id": unit(v, "beta", 5)}, "agent", "entity")
    assert column(t, "nar:anon:beta")["label"] == "Narrator of beta"
    assert ds.table(v, {"kind": "unit", "id": unit(v, "beta", 5)}, "agent", "gender")["columns"][0]["label"].startswith("Not a person")


def test_split_by_tag_and_gender(told, lib):
    v, w, h = told
    lib.set_tags(w, ["doctor"])
    v = View(lib, ["alpha"])
    t = ds.table(v, {"kind": "unit", "id": w}, "name", "tag")           # Watson is named in his own narration and in Holmes's quotes
    assert {c["id"] for c in t["columns"]} == {"doctor", ds.UNTAGGED}
    assert column(t, "doctor")["findings"] == column(ds.table(v, {"kind": "unit", "id": w}, "name", "entity"), w)["findings"]
    g = ds.table(v, {"kind": "unit", "id": w}, "name", "gender")
    assert v.gender_of(v.units[w]) == v.gender_of(v.units[h]) == "he/him/his"            # two describers of one gender: one column,
    assert [c["id"] for c in g["columns"]] == ["he/him/his"] and g["columns"][0]["findings"] == g["all"]["findings"]   # each finding once


def test_columns_beyond_top_are_gathered(told):
    v, w, h = told
    t = ds.table(v, {"kind": "unit", "id": w}, "name", "entity", top=1)
    full = ds.table(v, {"kind": "unit", "id": w}, "name", "entity", top=30)
    assert len(full["columns"]) >= 2 and [c["id"] for c in t["columns"]] == [full["columns"][0]["id"], ds.REST]
    assert column(t, ds.REST)["findings"] == sum(c["findings"] for c in full["columns"][1:]) and column(t, ds.REST)["label"] == "All others"


def test_columns_with_the_same_name_are_told_apart(view):
    """Watson of each book is its own, unlinked, entity: three columns called Watson would be unreadable."""
    holmes = [unit(view, b, c) for b, c in (("alpha", 1), ("beta", 5), ("gamma", 3))]
    t = ds.table(view, {"kind": "group", "ids": holmes}, "name", "entity", top=30)
    assert [c["label"] for c in t["columns"]] == ["Narrator of alpha", "Narrator of beta", "Narrator of gamma",
                                                  "Watson (alpha)", "Watson (beta)", "Watson (gamma)"]
    one = ds.table(view, {"kind": "unit", "id": holmes[0]}, "name", "entity")
    assert [c["label"] for c in one["columns"]] == ["Narrator of alpha", "Watson"]                  # no clash, no suffix


def test_a_group_pools_its_entities(told):
    v, w, h = told
    solo = [ds.table(v, {"kind": "unit", "id": u}, "agent", "voice")["all"]["findings"] for u in (w, h)]
    both = ds.table(v, {"kind": "group", "ids": [w, h]}, "agent", "voice")
    assert both["all"]["findings"] == sum(solo) and both["target"]


def test_called_as_uses_the_mentions_own_text(told):
    v, w, h = told
    bd = v.bd["alpha"]
    t = ds.table(v, {"kind": "unit", "id": w}, "pron", "voice")
    expected = sum(1 for mi in bd.groups[2].mentions if bd.mentions[mi][3] == "PRON")
    assert t["all"]["findings"] == expected
    assert all(r["item"] == r["item"].lower() for r in t["rows"])
    assert cell(t, "i", "narration")["n"] > 0                                                  # the narrator calls himself "I"


def test_nothing_found_is_an_empty_table(told):
    v, w, h = told
    t = ds.table(v, {"kind": "unit", "id": h}, "mod", "entity")           # the fixture has no modifiers of a person
    assert t["rows"] == [] and t["columns"] == [] and t["all"]["findings"] == 0 and t["distinct"] == 0


def test_a_single_column_has_no_keyness(told):
    v, w, h = told
    t = ds.table(v, {"kind": "unit", "id": h}, "agent", "book")
    assert len(t["columns"]) == 1 and all(c["ll"] == 0 and c["p"] == 1 for r in t["rows"] for c in r["cells"])


def test_unknown_options_are_refused(told):
    v, w, h = told
    for kw in ({"kind": "x"}, {"split": "x"}, {"voice": "x"}):
        with pytest.raises(ValueError):
            ds.table(v, {"kind": "unit", "id": h}, **kw)


def test_describers_of_a_mention(told):
    """The join itself: a mention inside Holmes's quote is Holmes's, one in the narration is Watson's."""
    v, w, h = told
    bd = v.bd["alpha"]
    who = ds.Describers(v)
    for mi in range(len(bd.mentions)):
        speaker, quoted = where(bd, mi)
        voice, ds_ = who.of("alpha", mi)
        assert voice == ("speech" if quoted else "narration")
        assert ds_ == ([dl.unit_of(v, "alpha", speaker)] if quoted and speaker else [ds.NO_DESCRIBER] if quoted else [w])


# ---------- the sentences behind a cell ----------
def every_cell(view, spec, **opts):
    """Yield (table, row, column index or None for the All column, evidence) for every cell of a table."""
    t = ds.table(view, spec, **opts)
    for row in t["rows"]:
        for i in [None, *range(len(t["columns"]))]:
            col = None if i is None else t["columns"][i]["id"]
            yield t, row, i, ds.evidence(view, spec, row["item"], col, limit=10_000, **opts)


@pytest.mark.parametrize("kind,split,voice,top", [("agent", "entity", "both", 8), ("agent", "entity", "both", 1), ("name", "voice", "both", 8),
                                                  ("pron", "entity", "speech", 2), ("agent", "gender", "both", 8), ("poss", "book", "narration", 8),
                                                  ("name", "tag", "both", 1)])
def test_the_sentences_behind_a_cell_are_exactly_its_count(lib, kind, split, voice, top):
    """Whatever the kind, split, voice and number of columns, a click lists as many sentences as the cell counts, "All others" and
    the All column included. Watson has two tags and Holmes one, so a finding can fall in several columns of the tag split."""
    v = View(lib, ["alpha", "beta", "gamma"])
    lib.set_tags(unit(v, "alpha", 2), ["doctor", "narrator"])
    lib.set_tags(unit(v, "alpha", 1), ["detective"])
    v = View(lib, ["alpha", "beta", "gamma"])
    ids = [unit(v, "alpha", 1), unit(v, "alpha", 2), unit(v, "beta", 5), unit(v, "beta", 6)]
    spec = {"kind": "group", "ids": ids}
    seen = 0
    for t, row, i, ev in every_cell(v, spec, kind=kind, split=split, voice=voice, top=top):
        n = row["total"] if i is None else row["cells"][i]["n"]
        assert ev["total"] == n == len(ev["items"]), (row["item"], i)
        seen += 1
    assert seen >= 4, "the table should have something to check"


def test_a_sentence_says_who_said_it_and_marks_the_word(told):
    v, w, h = told
    spec = {"kind": "unit", "id": h}
    ev = ds.evidence(v, spec, "see", "speech", kind="agent", split="voice")
    assert ev["total"] > 0 and {i["by"] for i in ev["items"]} == {"Holmes (speech)"}
    assert all("\x01m\x02" in i["text"] and "\x01k\x02" in i["text"] for i in ev["items"])             # the mention and the verb are marked
    said = ds.evidence(v, spec, "say", None, kind="agent", split="entity")
    assert {i["by"] for i in said["items"]} == {"Watson (narration)"}                              # "said Holmes" is the narrator's sentence
    assert [(i["book"], i["tok"]) for i in said["items"]] == sorted((i["book"], i["tok"]) for i in said["items"])
    named = ds.evidence(v, {"kind": "unit", "id": w}, "Watson", None, kind="name", split="entity")
    assert named["total"] > 0 and all("\x01k\x02" not in i["text"] for i in named["items"])           # a name is the mention itself: no second mark


def test_evidence_is_limited_but_still_counts_everything(told):
    v, w, h = told
    full = ds.evidence(v, {"kind": "unit", "id": h}, "say", None, kind="agent")
    short = ds.evidence(v, {"kind": "unit", "id": h}, "say", None, kind="agent", limit=3)
    assert short["total"] == full["total"] > 3 and short["shown"] == len(short["items"]) == 3
    assert ds.evidence(v, {"kind": "unit", "id": h}, "nonsense", None, kind="agent") == {"total": 0, "shown": 0, "items": []}
    with pytest.raises(ValueError):
        ds.evidence(v, {"kind": "unit", "id": h}, "say", None, kind="x")


# ---------- columns you pick ----------
def test_picked_columns_are_the_describers_you_name(told):
    """Columns: Watson, the two of Holmes and Watson together as a group, and nobody (a tag no one has)."""
    v, w, h = told
    cols = [{"kind": "unit", "id": w, "name": "The doctor"}, {"kind": "group", "ids": [w, h]}, {"kind": "tag", "tag": "nobody"}]
    t = ds.table(v, {"kind": "unit", "id": h}, "name", "custom", columns=cols)
    assert [(c["id"], c["label"]) for c in t["columns"]] == [("c0", "The doctor"), ("c1", "Watson, Holmes"), ("c2", "tag “nobody”")]
    by = {c["id"]: c for c in t["columns"]}
    assert by["c0"]["findings"] == t["all"]["findings"] == by["c1"]["findings"]       # Watson says all of them, and so does the pair he is in
    assert by["c2"]["findings"] == 0 and by["c2"]["words"] == 0                       # an empty column is still shown
    assert by["c0"]["words"] > 0


def test_findings_outside_every_picked_column_are_only_in_all(told):
    v, w, h = told
    t = ds.table(v, {"kind": "unit", "id": w}, "name", "custom", columns=[{"kind": "unit", "id": h}])       # only Holmes's part
    named_by_holmes = t["columns"][0]["findings"]
    assert 0 < named_by_holmes < t["all"]["findings"]
    assert all(r["cells"][0]["n"] <= r["total"] for r in t["rows"]) and all(c["ll"] == 0 for r in t["rows"] for c in r["cells"])   # one column: no keyness


def test_a_describer_can_be_in_several_picked_columns(told):
    v, w, h = told
    t = ds.table(v, {"kind": "unit", "id": h}, "name", "custom", columns=[{"kind": "unit", "id": w}, {"kind": "group", "ids": [w, h]}])
    assert sum(c["findings"] for c in t["columns"]) == 2 * t["all"]["findings"]       # counted once in each column it is in


def test_the_sentences_behind_picked_columns_are_exactly_their_count(view):
    ids = [unit(view, "alpha", 1), unit(view, "alpha", 2), unit(view, "beta", 5), unit(view, "beta", 6)]
    cols = [{"kind": "unit", "id": ids[1]}, {"kind": "group", "ids": ids[:2]}, {"kind": "unit", "id": ids[0]}]
    seen = 0
    for kind in ("agent", "name", "pron"):
        for t, row, i, ev in every_cell(view, {"kind": "group", "ids": ids}, kind=kind, split="custom", columns=cols):
            assert ev["total"] == (row["total"] if i is None else row["cells"][i]["n"]) == len(ev["items"])
            seen += 1
    assert seen > 12


def test_picked_columns_are_checked(told):
    v, w, h = told
    spec = {"kind": "unit", "id": h}
    for bad, msg in ((None, "Pick at least one column."), ([], "Pick at least one column."), (["x"], "Each column should say which entities it stands for."),
                     ([{"kind": "unit", "id": w}] * 13, "Pick at most 12 columns.")):
        with pytest.raises(ValueError, match=msg):
            ds.table(v, spec, "name", "custom", columns=bad)
    assert ds.table(v, spec, "name", "entity", columns=["ignored"])["split"] == "entity"          # only the custom split reads them


# ---------- the route ----------
ALL = ["alpha", "beta", "gamma"]


def ask(client, status=200, **body):
    """POST /api/described over all three books, checking the status; returns the JSON."""
    r = client.post("/api/described", json={"books": ALL, **body})
    assert r.status_code == status, r.text[:300]
    return r.json()


def test_the_route_answers_like_the_core(client, view):
    h = unit(view, "alpha", 1)
    got = ask(client, target={"kind": "unit", "id": h}, kind="agent", split="voice")
    assert got == ds.table(view, {"kind": "unit", "id": h}, "agent", "voice")                # same figures, through JSON
    assert [c["id"] for c in got["columns"]] == ["narration", "speech"]


def test_the_route_has_defaults_and_takes_every_kind_of_target(client, view):
    h = unit(view, "alpha", 1)
    default = ask(client, target={"kind": "unit", "id": h})
    assert default["kind"] == "mod" and default["split"] == "entity" and default["voice"] == "both" and default["rows"] == []
    for target in ({"kind": "group", "ids": [h, unit(view, "alpha", 2)]}, {"kind": "tag", "tag": "none"}, {"kind": "gender", "pron": "he/him/his"},
                   {"kind": "unit", "id": "e:alpha:999"}):
        got = ask(client, target=target, kind="name")
        assert set(got) >= {"target", "columns", "rows", "all"}
    assert ask(client, target={"kind": "unit", "id": "e:alpha:999"})["rows"] == []                # not in the selection: nothing, not an error


def test_the_route_limits_columns_and_rows(client, view):
    w = unit(view, "alpha", 2)
    got = ask(client, target={"kind": "unit", "id": w}, kind="name", top=1, limit=1)
    assert len(got["columns"]) <= 2 and len(got["rows"]) == 1 and got["distinct"] >= 1
    assert len(ask(client, target={"kind": "unit", "id": w}, kind="name", top=0)["columns"]) <= 2          # held between 1 and 30, not refused


def test_the_route_explains_what_it_cannot_use(client, view):
    t = {"kind": "unit", "id": unit(view, "alpha", 1)}
    assert ask(client, 400, kind="mod")["detail"] == "“target” is missing."
    assert ask(client, 400, target="Holmes")["detail"] == "“target” should say which entities to look at."
    assert ask(client, 400, target=t, kind="nope")["detail"] == "Unknown kind."
    assert ask(client, 400, target=t, split="nope")["detail"] == "Unknown split."
    assert ask(client, 400, target=t, voice="nope")["detail"] == "Unknown voice."
    assert ask(client, 400, target=t, top="x")["detail"] == "“top” should be a whole number."
    assert client.post("/api/described", json={"target": t}).status_code == 400                          # no books


def test_the_evidence_route_lists_exactly_the_cells_sentences(client, view):
    h = unit(view, "alpha", 1)
    body = {"target": {"kind": "unit", "id": h}, "kind": "agent", "split": "voice"}
    t = ask(client, **body)
    row = next(r for r in t["rows"] if r["item"] == "see")
    for i, col in enumerate(t["columns"]):
        got = client.post("/api/described/evidence", json={"books": ALL, **body, "item": "see", "column": col["id"]}).json()
        assert got["total"] == row["cells"][i]["n"] == len(got["items"])
    allcol = client.post("/api/described/evidence", json={"books": ALL, **body, "item": "see", "column": None}).json()
    assert allcol["total"] == row["total"] and {"book", "title", "pos", "tok", "text", "by"} <= set(allcol["items"][0])
    assert client.post("/api/described/evidence", json={"books": ALL, **body, "item": "see", "column": None, "limit": 2}).json()["shown"] == 2


def test_the_evidence_route_explains_what_it_cannot_use(client, view):
    t = {"kind": "unit", "id": unit(view, "alpha", 1)}
    bad = lambda **b: client.post("/api/described/evidence", json={"books": ALL, **b})
    assert bad(target=t, kind="agent").json()["detail"] == "“item” is missing."
    assert bad(item="see").json()["detail"] == "“target” is missing."
    assert bad(target=t, item="see", kind="nope").json()["detail"] == "Unknown kind."


def test_the_routes_take_picked_columns(client, view):
    h, w = unit(view, "alpha", 1), unit(view, "alpha", 2)
    body = {"target": {"kind": "unit", "id": h}, "kind": "name", "split": "custom", "columns": [{"kind": "unit", "id": w, "name": "The doctor"}]}
    t = ask(client, **body)
    assert [c["label"] for c in t["columns"]] == ["The doctor"] and t["columns"][0]["findings"] > 0
    ev = client.post("/api/described/evidence", json={"books": ALL, **body, "item": t["rows"][0]["item"], "column": "c0"}).json()
    assert ev["total"] == t["rows"][0]["cells"][0]["n"]
    assert ask(client, 400, **{**body, "columns": []})["detail"] == "Pick at least one column."
