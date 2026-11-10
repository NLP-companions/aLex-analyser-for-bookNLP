"""The R export of the Statistics tab (core/rexport.py): the files, read back and checked against the page's own figures.

The counting is tested in test_variables.py; here the files are read back with the csv module, so what R would read is what is checked."""
from __future__ import annotations

import csv
import io
import json
import zipfile

import pytest

from alex.core import cases as cs
from alex.core import rexport
from alex.core import variables as vb

SLICES = {"kind": "pieces", "piece": "slice", "n": 5, "min": 0}
PEOPLE = {"kind": "participants", "sample": "sentences", "min": 0}
WORDS = [{"kind": "query", "query": q} for q in ("holmes", "said")]
POSITION = {"kind": "attribute", "attr": "position"}


def setup(**kw):
    """A request over the slices with two words, changed by `kw`."""
    return {"cases": SLICES, "rows": WORDS, **kw}


def table(text):
    """A CSV text as a list of dicts, an empty cell as None (what R reads as NA)."""
    return [{k: v or None for k, v in row.items()} for row in csv.DictReader(io.StringIO(text))]


# ---------- the names ----------
def test_slugs_are_safe_for_r():
    assert rexport.slug("“said” (lemma)") == "said_lemma"
    assert rexport.slug("Mentions of Holmes: names") == "mentions_of_holmes_names"
    assert rexport.slug("Gender: she/her") == "gender_she_her"
    assert rexport.slug("Café ünï") == "cafe_uni"
    assert rexport.slug("3rd") == "v_3rd" and rexport.slug("???") == "v_"
    assert len(rexport.slug("x" * 200)) == rexport.MAX_NAME


def test_names_are_unique_and_keep_clear_of_count_columns_and_case_columns():
    names = rexport.column_names(["Said", "said", "SAID!", "label", "x_n", "x"], [True, True, False, False, False, True], ["label"])
    assert names == ["said", "said_2", "said_3", "label_2", "x_n", "x_2"]       # "x" would have made "x_n" twice
    assert len(set(names)) == len(names)


# ---------- the files ----------
def test_cases_csv_has_a_count_and_a_rate_for_a_count_variable(view):
    out = rexport.files(view, setup(rows=WORDS + [POSITION]))
    rows = table(out["cases.csv"])
    cases = cs.build(view, SLICES)
    counts = vb.values(view, cases, {**vb.check(WORDS[0]), "measure": "count"})[0]
    assert list(rows[0]) == ["case_id", "book", "book_title", "piece_index", "position_pct", "label", "n_words",
                             "holmes_n", "holmes", "said_n", "said", "position_in_its_book"]
    assert [int(r["holmes_n"]) for r in rows] == counts
    assert [float(r["holmes"]) for r in rows] == pytest.approx(vb.values(view, cases, vb.check(WORDS[0]))[0])
    assert [r["case_id"] for r in rows] == [c["id"] for c in cases.rows] and [int(r["n_words"]) for r in rows] == [c["size"] for c in cases.rows]
    assert [float(r["position_in_its_book"]) for r in rows] == pytest.approx(vb.values(view, cases, vb.check(POSITION))[0])


def test_the_long_file_holds_every_case_and_variable(view):
    out = rexport.files(view, setup(rows=WORDS + [POSITION]))
    wide, long = table(out["cases.csv"]), table(out["cases_long.csv"])
    assert len(long) == 3 * len(wide) and list(long[0]) == ["case_id", "variable", "count", "n_words", "value"]
    for r in long:
        w = next(x for x in wide if x["case_id"] == r["case_id"])
        assert r["value"] == w[r["variable"]] and r["n_words"] == w["n_words"]
        assert r["count"] == w.get(r["variable"] + "_n")                             # no count column: an empty count
    assert {r["count"] for r in long if r["variable"] == "position_in_its_book"} == {None}


def test_variables_csv_maps_names_to_labels_and_requests(view):
    out = rexport.files(view, setup(rows=WORDS + [POSITION]))
    meta = table(out["variables.csv"])
    assert [m["name"] for m in meta] == ["holmes", "said", "position_in_its_book"]
    assert [m["count_column"] for m in meta] == ["holmes_n", "said_n", None]
    assert [m["label"] for m in meta][0] == "“holmes”" and meta[2]["kind"] == "attribute"
    assert meta[0]["unit"] == "per 1,000 words" and meta[2]["unit"] is None
    assert json.loads(meta[0]["spec"]) == vb.check(WORDS[0])                           # the request, to run it again


def test_both_lists_are_exported_rows_first(view):
    out = rexport.files(view, setup(rows=WORDS[:1], columns=WORDS[1:]))
    assert [m["name"] for m in table(out["variables.csv"])] == ["holmes", "said"]


def test_the_measure_of_the_page_does_not_change_the_export(view):
    as_count = [{**w, "measure": "count"} for w in WORDS]
    as_present = [{**w, "measure": "present"} for w in WORDS]
    base = rexport.files(view, setup())
    for rows in (as_count, as_present):
        out = rexport.files(view, setup(rows=rows))
        assert out["cases.csv"] == base["cases.csv"] and out["cases_long.csv"] == base["cases_long.csv"]


def test_a_variable_that_does_not_apply_is_empty_with_its_note(view):
    out = rexport.files(view, setup(rows=WORDS[:1] + [{"kind": "attribute", "attr": "speech"}]))          # a participant attribute, on pieces
    assert {r["words_spoken"] for r in table(out["cases.csv"])} == {None}
    assert table(out["variables.csv"])[1]["note"]


def test_participants_get_their_own_columns_and_a_findings_sample_its_own_size(view):
    out = rexport.files(view, setup(cases=PEOPLE))
    rows = table(out["cases.csv"])
    cases = cs.build(view, PEOPLE)
    assert list(rows[0])[:6] == ["case_id", "label", "type", "books", "n_books", "n_words"] and len(rows) == len(cases.rows)
    assert [int(r["n_books"]) for r in rows] == [len(c["books"]) for c in cases.rows]
    found = rexport.files(view, setup(cases={"kind": "participants", "sample": "findings", "min": 0}, rows=[{"kind": "query", "query": "a"}]))
    assert "n_findings" in table(found["cases.csv"])[0] and table(found["variables.csv"])[0]["unit"] == "% of findings"


def test_dropped_cases_are_listed_with_the_reason(view):
    cases = {**SLICES, "min": 10 ** 6}                                                  # every slice is too small
    out = rexport.files(view, setup(cases=cases))
    dropped = table(out["dropped.csv"])
    assert table(out["cases.csv"]) == [] and len(dropped) == 15
    assert {d["reason"] for d in dropped} == {"fewer than 1000000 words"} and list(dropped[0])[:3] == ["case_id", "book", "piece_index"]
    people = rexport.files(view, setup(cases={**PEOPLE, "min": 10 ** 6}))
    left = table(people["dropped.csv"])
    assert len(left) == len(cs.build(view, {**PEOPLE, "min": 10 ** 6}).left_out) > 0 and left[0]["label"]
    assert table(rexport.files(view, setup())["dropped.csv"]) == []                      # nothing left out: a header only


def test_the_scripts_and_readme(view):
    out = rexport.files(view, setup(rows=WORDS + [POSITION]))
    assert set(out) == {"cases.csv", "cases_long.csv", "variables.csv", "dropped.csv", "README.txt", "load.R", "analysis_example.R"}
    assert 'cases$book <- factor(cases$book)' in out["load.R"] and "cases$type" in rexport.files(view, setup(cases=PEOPLE))["load.R"]
    example = out["analysis_example.R"]
    assert 'cor.test(cases$holmes, cases$said' in example and "holmes ~ position_pct" in example and "offset(log(n_words))" in example
    assert "15 text pieces" in out["README.txt"] and json.dumps(SLICES) in out["README.txt"] and "analysis_example.R" in out["README.txt"]
    plain = rexport.files(view, setup(), example=False)
    assert "analysis_example.R" not in plain and "analysis_example.R" not in plain["README.txt"]


def test_the_example_adds_an_anova_for_a_participant_attribute(view):
    gender = {"kind": "attribute", "attr": "in", "target": {"kind": "gender", "pron": "she/her"}}
    example = rexport.files(view, setup(cases=PEOPLE, rows=[gender] + WORDS))["analysis_example.R"]
    assert "aov(" in example and "factor(gender_" in example and "log(n_words)" in example


def test_bad_requests_are_refused_like_the_page_does(view):
    for bad in (None, {"rows": []}, setup(rows=WORDS * 20), setup(cases={"kind": "pages"}), setup(rows=[{"kind": "nothing"}])):
        with pytest.raises(ValueError):
            rexport.files(view, bad)


def test_the_zip_holds_the_files(view, tmp_path):
    parts = rexport.files(view, setup())
    dest = tmp_path / "r.zip"
    rexport.write_zip(dest, parts)
    with zipfile.ZipFile(dest) as z:
        assert sorted(z.namelist()) == sorted(parts) and z.read("cases.csv").decode("utf-8") == parts["cases.csv"]
