"""Damaged and unusual files: they must be read when they can be, and refused with a message that says what is wrong when they can't."""
from __future__ import annotations

import shutil

import pytest
from fastapi.testclient import TestClient
from fixture import LOCAL

from alex import app as app_module
from alex.core.bookdata import BookData, ekey, parse_ekey
from alex.core.library import Library
from alex.core.view import View


@pytest.fixture
def folder(tmp_path, corpus):
    """A copy of gamma's files to damage, as a folder of BookNLP files named 'g'."""
    src = next(corpus[0].glob("gamma-*"))
    out = tmp_path / "g"
    out.mkdir()
    for ext in ("tokens", "entities", "quotes", "supersense", "book", "txt"):
        shutil.copy(src / f"gamma.{ext}", out / f"g.{ext}")
    return out


def facts(bd):
    """What a book amounts to, for comparing two readings of the same book."""
    return (bd.n_tokens, bd.n_words, len(bd.mentions), len(bd.quotes), sorted((c, len(g.mentions)) for c, g in bd.groups.items()), bd.problems)


def test_a_byte_order_mark_and_windows_line_endings_make_no_difference(folder):
    plain = facts(BookData("g", folder))
    for ext in ("tokens", "entities", "quotes", "supersense"):
        raw = (folder / f"g.{ext}").read_bytes().replace(b"\n", b"\r\n")
        (folder / f"g.{ext}").write_bytes(b"\xef\xbb\xbf" + raw)
    (folder / "g.book").write_bytes(b"\xef\xbb\xbf" + (folder / "g.book").read_bytes())
    assert facts(BookData("g", folder)) == plain


def test_a_file_that_is_not_utf8_is_refused_with_a_clear_message(folder):
    (folder / "g.tokens").write_bytes((folder / "g.tokens").read_bytes().replace(b"Holmes", b"Holm\xe9s", 1))
    with pytest.raises(ValueError, match=r"g\.tokens isn't UTF-8 text"):
        BookData("g", folder)


def test_optional_columns_may_be_missing(folder):
    lines = (folder / "g.tokens").read_text().splitlines()
    cols = lines[0].split("\t")
    drop = {cols.index(c) for c in ("fine_POS_tag", "event", "byte_onset", "byte_offset")}
    (folder / "g.tokens").write_text("\n".join("\t".join(v for i, v in enumerate(line.split("\t")) if i not in drop) for line in lines) + "\n")
    bd = BookData("g", folder)
    assert bd.n_tokens == len(lines) - 1 and set(bd.tag) == {""} and not any(bd.event) and bd.onset[0] == -1
    assert bd.span_text(0, 5)                                   # without offsets, spacing is guessed


def test_a_number_that_is_not_a_number_is_reported_with_its_line(folder):
    lines = (folder / "g.tokens").read_text().splitlines()
    cols = lines[0].split("\t")
    bad = lines[7].split("\t")
    bad[cols.index("paragraph_ID")] = "three"
    lines[7] = "\t".join(bad)
    (folder / "g.tokens").write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match=r"g\.tokens line 8: paragraph_ID should be a whole number but is “three”"):
        BookData("g", folder)


def test_a_missing_required_column_is_named(folder):
    text = (folder / "g.tokens").read_text().replace("syntactic_head_ID", "head", 1)
    (folder / "g.tokens").write_text(text)
    with pytest.raises(ValueError, match="missing columns: syntactic_head_ID"):
        BookData("g", folder)


def test_a_damaged_character_file_is_a_note_not_a_failure(folder):
    (folder / "g.book").write_text("{ this is not json", encoding="utf-8")
    bd = BookData("g", folder)
    assert any("g.book" in p for p in bd.problems) and bd.groups and all(g.name for g in bd.groups.values())


def test_mentions_and_quotes_outside_the_book_are_skipped_and_noted(folder):
    with open(folder / "g.entities", "a", encoding="utf-8") as f:
        f.write("77\t999999\t999999\tPROP\tPER\tNobody\n77\t5\t3\tPROP\tPER\tBackwards\nx\t1\t1\tPROP\tPER\tNot a number\n")
    with open(folder / "g.quotes", "a", encoding="utf-8") as f:
        f.write("999990\t999999\t1\t1\tx\t1\tFar away\n")
    bd = BookData("g", folder)
    assert 77 not in bd.groups and not any("Far away" == q["text"] for q in bd.quotes)
    assert any("outside the book" in p for p in bd.problems)
    assert "1 line of g.entities couldn't be read and was skipped." in bd.problems          # the row whose number is not a number


def test_one_unreadable_book_does_not_stop_the_others(tmp_path, corpus):
    root = tmp_path / "exports"
    shutil.copytree(next(corpus[0].glob("gamma-*")), root / "gamma-20260103-000000")
    broken = root / "broken-20260101-000000"
    broken.mkdir()
    (broken / "broken.tokens").write_text("this\tis\tnot\ta\tbook\n", encoding="utf-8")
    (broken / "broken.entities").write_text("COREF\tstart_token\tend_token\tprop\tcat\ttext\n", encoding="utf-8")
    lib = Library(data_dir=tmp_path / "data", sources=[root])
    v = View(lib, ["broken", "gamma"])
    assert v.books == ["gamma"] and len(v.problems) == 1 and v.problems[0].startswith("broken:")
    client = TestClient(app_module.build_app(lib), base_url=LOCAL, raise_server_exceptions=False)
    books = {b["id"]: b for b in client.get("/api/library").json()["books"]}
    assert "error" in books["broken"] and "error" not in books["gamma"]
    units = client.post("/api/units", json={"books": ["broken", "gamma"]}).json()
    assert units["rows"] and units["problems"]
    assert client.get("/api/links/suggestions").status_code == 200
    assert client.post("/api/corpus/wordlist", json={"books": ["broken", "gamma"]}).status_code == 200


def test_unit_ids_round_trip_and_bad_ones_are_refused():
    assert parse_ekey(ekey("alpha", 12)) == ("alpha", 12)
    assert parse_ekey(ekey("odd:name", 3)) == ("odd:name", 3)         # a book id may contain colons
    for bad in ("p:3", "e:alpha", "e:alpha:x", "e::3", "", None, 5, "alpha:1"):
        assert parse_ekey(bad) is None


# ---------- the same answer every time ----------
def run_with_hash_seed(seed, code):
    """Run `code` in a new Python whose string hashing starts from `seed` (the order of a set of strings differs between seeds) -> its output."""
    import os
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=root, env={**os.environ, "PYTHONHASHSEED": str(seed)}, timeout=300)
    assert done.returncode == 0, done.stderr[-800:]
    return done.stdout.strip().splitlines()[-1]


def test_the_first_of_several_vocatives_is_the_first_in_the_text_whatever_the_hash_seed(tmp_path):
    """A quote that addresses two people (“Holmes, Watson, come here”) has the first named as its addressee. The mentions inside a quote were
    kept in a set, so which came first changed from one run of the program to the next (a quote's estimated addressee and everything counted
    from it: who talks to whom, the addressed network)."""
    folder = tmp_path / "two"
    folder.mkdir()
    header = ("paragraph_ID\tsentence_ID\ttoken_ID_within_document\tword\tlemma\tbyte_onset\tbyte_offset\t"
              "POS_tag\tfine_POS_tag\tdependency_relation\tsyntactic_head_ID\tevent")
    words = ['"', "Holmes", ",", "Watson", ",", "come", ".", '"', "said", "Lestrade", "."]
    marks = {'"', ",", "."}

    def row(i, w):
        """One line of .tokens: punctuation attached to "said" (the root), the names its subjects."""
        pos, dep = ("PUNCT", "punct") if w in marks else ("PROPN", "nsubj") if w[0].isupper() else ("VERB", "ccomp")
        dep = "ROOT" if w == "said" else dep
        return "\t".join(map(str, (0, 0, i, w, w.lower(), i * 2, i * 2 + 1, pos, "X", dep, 8, "O")))

    rows = [row(i, w) for i, w in enumerate(words)]
    (folder / "two.tokens").write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    # the mentions written the other way round, Watson's before Holmes's
    (folder / "two.entities").write_text("COREF\tstart_token\tend_token\tprop\tcat\ttext\n2\t3\t3\tPROP\tPER\tWatson\n3\t9\t9\tPROP\tPER\tLestrade\n1\t1\t1\tPROP\tPER\tHolmes\n", encoding="utf-8")
    (folder / "two.quotes").write_text("quote_start\tquote_end\tmention_start\tmention_end\tmention_phrase\tchar_id\tquote\n0\t7\t9\t9\tLestrade\t3\t\" Holmes , Watson , come . \"\n", encoding="utf-8")
    code = f"""
from pathlib import Path
from alex.core.bookdata import BookData
from alex.core import dialogue
bd = BookData("two", Path({str(folder)!r}))
print(dialogue._vocative(bd, 0, bd.quotes[0]))
"""
    assert {run_with_hash_seed(seed, code) for seed in range(1, 9)} == {"[1, 2]"}


def test_answers_do_not_depend_on_the_hash_seed(corpus, tmp_path):
    """The same books give the same answers in every run: dialogue (addressees and everything counted from them), networks (the layout and the
    communities follow the order of nodes and edges) and a stylometric tree are compared, byte for byte, across several hash seeds."""
    code = f"""
import hashlib, json
from fastapi.testclient import TestClient
from alex import app as app_module
from alex.core.library import Library
lib = Library(data_dir={str(tmp_path / 'data')!r}, sources=[{str(corpus[0])!r}])
c = TestClient(app_module.build_app(lib), base_url="http://127.0.0.1")
B = {{"books": ["alpha", "beta", "gamma"]}}
seg = {{"mode": "slices", "n": 4}}
out = [c.post(p, json={{**B, **b}}).text for p, b in (
    ("/api/dialogue/overview", {{}}), ("/api/dialogue/quotes", {{"filter": {{}}}}), ("/api/dialogue/conversations", {{}}), ("/api/narrators/suggestions", {{}}),
    ("/api/network", {{"kind": "sentence", "types": ["PER", "LOC"]}}), ("/api/network", {{"kind": "dialogue"}}), ("/api/network", {{"kind": "addressed"}}),
    ("/api/network", {{"kind": "paragraph", "types": ["PER", "LOC", "FAC", "GPE", "ORG", "VEH", "VAR"], "focus": "e:alpha:1"}}),
    ("/api/narrative/stylometry", {{"seg": seg, "units": "segments"}}), ("/api/plurals/suggestions", {{}}))]
print(hashlib.sha1("".join(out).encode()).hexdigest())
"""
    assert len({run_with_hash_seed(seed, code) for seed in (1, 2, 3)}) == 1
