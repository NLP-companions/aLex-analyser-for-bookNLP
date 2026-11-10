"""The R export of the Statistics tab: the cases and variables of a request as plain files R reads without fuss.

`files` measures the page's variables (both lists) in the page's cases and returns the files of the export, `write_zip` puts them in a .zip:

    cases.csv           wide: one row per case, the case's own columns, then one column per variable
    cases_long.csv      long: one row per case and variable (case_id, variable, count, n_words, value), for ggplot2 and mixed models
    variables.csv       one row per variable: its column name, label, kind, unit, the full request (spec) and any note
    dropped.csv         the cases left out (a sample below the minimum, or none at all), and why
    README.txt          what each file and column is, and how the cases were made
    load.R              reads the four tables and makes the grouping columns factors
    analysis_example.R  a few lines of analysis on the first variables (optional: `example`)

Whatever measure the page uses, a variable that **counts** something (words, mentions, supersenses, relations, lexicon words) gets two
columns, `<name>_n` (the raw count) and `<name>` (per 1,000 words of the case's sample, or % of findings in the Described-as sample), so R
can model the counts (a Poisson or negative binomial model with `offset(log(n_words))`) or use the rates. The other variables (attributes,
sentiment, style figures, topics) have only `<name>`. The case's sample size is `n_words` (`n_findings` for findings). A value a case
doesn't have is an empty cell, as in the page (pairwise deletion). Column names are slugs of the labels (`slug`): ASCII letters, digits and
underscores, made unique, so R never has to rename them; `variables.csv` maps each back to its label. The files are UTF-8, comma-separated,
with "." as the decimal mark and a header row.
"""
from __future__ import annotations

import csv
import io
import json
import re
import time
import unicodedata
import zipfile

from . import cases as casemod
from . import described, statstab, variables

MAX_NAME = 40                                        # characters of a variable's column name (before a number that makes it unique)
README = """\
Statistics export of the Analyser - {made}

{cases}.

Files
  cases.csv          one row per case: {fixed}, then the variables
  cases_long.csv     the same values, one row per case and variable: case_id, variable, count, {size}, value
  variables.csv      each variable: name (its column in cases.csv), count_column, label, kind, unit, spec, note
  dropped.csv        cases left out of the study, and why ({dropped})
  load.R             reads the four tables into R (set the working directory to this folder first)
{example}
Columns
  {size}   the size of the case's sample{unit_of_size}.
  <name>_n   the raw count, for a variable that counts something (words, mentions, supersenses, relations, lexicon words).
  <name>     its value: for a count, {rate} (the count divided by the sample); for the other variables (attributes, sentiment,
             style figures, topics), their own figure. See `unit` in variables.csv.
  An empty cell means the case has no value for that variable (it applies to other cases, or the lexicon or model is missing;
  see `note` in variables.csv). Counts can be modelled directly, for example
  glm(<name>_n ~ ... + offset(log({size})), family = poisson, data = cases).

How the cases were made (the request)
{setup}
"""


def slug(text):
    """A column name from a label: ASCII letters, digits and underscores, lower case, at most `MAX_NAME` characters, never empty and never
    starting with a digit (R would rename it)."""
    t = re.sub(r"[^a-z0-9]+", "_", unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()).strip("_")[:MAX_NAME].strip("_")
    return "v_" + t if not t or t[0].isdigit() else t


def column_names(labels, counted, reserved):
    """A unique column name for each label, in order. `counted[i]` says variable i also has a count column `<name>_n`; no name equals
    another's, a count column or one of the `reserved` names. A clash gets a number: `said`, `said_2`."""
    used, names = set(reserved), []
    for text, has_count in zip(labels, counted):
        base, name, k = slug(text), None, 1
        while name is None or name in used or (has_count and name + "_n" in used):
            k += 1
            name = base if k == 2 else f"{base}_{k - 1}"
        used.update((name, name + "_n") if has_count else (name,))
        names.append(name)
    return names


def measured(view, cases, spec, lexicons=None):
    """(counts, values, note) of one checked variable over the cases: for a variable that counts something, its counts and its rates
    (per 1,000 words, or % of findings); for any other, no counts (None) and its own values. A value a case doesn't have is None."""
    if "measure" not in spec:
        vals, note = variables.values(view, cases, spec, lexicons)
        return None, vals, note
    counts, note = variables.values(view, cases, {**spec, "measure": "count"}, lexicons)
    per = 100 if cases.unit == "findings" else 1000
    return counts, [None if n is None else per * n / r["size"] for n, r in zip(counts, cases.rows)], note


def _csv(header, rows):
    """A CSV text (UTF-8, "\\n" line ends): None is an empty cell."""
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return out.getvalue()


def files(view, setup, lexicons=None, example=True):
    """The export of the Statistics `setup` ({cases, rows, columns}: the same request as the page, `statstab.check` says what is
    valid): {file name: text}. Both variable lists are exported, rows first. With `example`, analysis_example.R is included.
    `lexicons` are your word lexicons by id. Raises ValueError for anything the page would refuse."""
    case_setup, rows, cols = statstab.check(setup)[:3]
    cases = casemod.build(view, case_setup)
    specs = [variables.check(s) for s in rows + cols]
    pieces, size = cases.kind == "pieces", "n_findings" if cases.unit == "findings" else "n_words"
    fixed = (["case_id", "book", "book_title", "piece_index", "position_pct", "label"] if pieces
             else ["case_id", "label", "type", "books", "n_books"]) + [size]
    parts = [measured(view, cases, s, lexicons) for s in specs]
    labels = [variables.label(view, s, lexicons) for s in specs]
    names = column_names(labels, [counts is not None for counts, _, _ in parts], fixed)
    header, table = list(fixed), [_case_columns(view, cases, r) for r in cases.rows]
    for name, (counts, vals, _) in zip(names, parts):
        header += [name + "_n", name] if counts is not None else [name]
        for i, line in enumerate(table):
            line += [counts[i], vals[i]] if counts is not None else [vals[i]]
    long = [(r["id"], name, None if counts is None else counts[i], r["size"], vals[i])
            for name, (counts, vals, _) in zip(names, parts) for i, r in enumerate(cases.rows)]
    meta = [(name, name + "_n" if counts is not None else None, label, s["kind"], _unit(cases, s, counts), json.dumps(s, ensure_ascii=False), note)
            for name, label, s, (counts, _, note) in zip(names, labels, specs, parts)]
    out = {"cases.csv": _csv(header, table),
           "cases_long.csv": _csv(["case_id", "variable", "count", size, "value"], long),
           "variables.csv": _csv(["name", "count_column", "label", "kind", "unit", "spec", "note"], meta),
           "dropped.csv": _dropped(view, cases, size),
           "README.txt": _readme(cases, case_setup, fixed, size, example),
           "load.R": _load_script(pieces)}
    if example:
        out["analysis_example.R"] = _example(cases, size, [(n, c is not None, vals) for n, (c, vals, _) in zip(names, parts)], specs)
    return out


def _case_columns(view, cases, r):
    """The case's own cells in cases.csv (see `files`), up to and including its sample size."""
    if cases.kind == "pieces":
        return [r["id"], r["book"], view.title(r["book"]), r["index"], r["pos"], r["label"], r["size"]]
    return [r["id"], r["label"], r["type"], "; ".join(r["books"]), len(r["books"]), r["size"]]


def _unit(cases, spec, counts):
    """What a variable's value is: its rate (per 1,000 words, % of findings) if it counts something, else what `variables.measure_label` says."""
    if counts is None:
        return variables.measure_label(cases, spec)
    return variables.measure_label(cases, {**spec, "measure": "per1k"})


def _dropped(view, cases, size):
    """dropped.csv: the cases left out and why. Participants get their label; a piece its place (book, number, % into the book)."""
    why = lambda n: "empty sample" if n == 0 else f"fewer than {cases.min} {cases.unit}"        # noqa: E731
    if cases.kind == "pieces":
        return _csv(["case_id", "book", "piece_index", "position_pct", size, "reason"],
                    [(x["id"], x["book"], x["index"], x["pos"], x["size"], why(x["size"])) for x in cases.left_out])
    names = described.column_labels(view, "entity", [x["id"] for x in cases.left_out]) if cases.left_out else {}
    return _csv(["case_id", "label", size, "reason"], [(x["id"], names.get(x["id"]), x["size"], why(x["size"])) for x in cases.left_out])


def _readme(cases, case_setup, fixed, size, example):
    """README.txt: the files and columns, and the request the cases were made from."""
    k = cases.summary()
    what = (f"{k['n']} text pieces ({k['sample']})" if k["kind"] == "pieces" else f"{k['n']} participants (sample: {k['sample']})")
    few = f", or in fewer than {k['min_range']} books" if k["kind"] == "participants" and k["min_range"] > 1 else ""
    left = f"; {k['dropped']} left out for a sample below {k['min']} {k['unit']}, or none at all{few}" if k["dropped"] else ""
    findings = cases.unit == "findings"
    return README.format(
        made=time.strftime("%Y-%m-%d %H:%M"), cases=what[0].upper() + what[1:] + left, fixed=", ".join(fixed), size=size,
        dropped=f"{k['dropped']} cases", example="  analysis_example.R   a few lines of analysis on the first variables, to start from\n" if example else "",
        unit_of_size=" (findings: what is said about the participant)" if findings else " (words)",
        rate="% of the case's findings" if findings else "per 1,000 words of the case's sample",
        setup="  " + json.dumps(case_setup, ensure_ascii=False))


def _load_script(pieces):
    """load.R: reads the four tables and makes the grouping columns factors."""
    group = 'cases$book <- factor(cases$book)                 # one level per book' if pieces else 'cases$type <- factor(cases$type)'
    return f"""\
# Reads the Analyser's Statistics export. Set the working directory to this folder first
# (RStudio: Session > Set Working Directory > To Source File Location).
read <- function(file) read.csv(file, encoding = "UTF-8", stringsAsFactors = FALSE)

cases      <- read("cases.csv")        # one row per case; one column per variable (<name>_n = count, <name> = rate or value)
cases_long <- read("cases_long.csv")   # the same, one row per case and variable
variables  <- read("variables.csv")    # column name, label, kind, unit and the request of each variable
dropped    <- read("dropped.csv")      # the cases left out, and why

{group}
cases_long$variable <- factor(cases_long$variable, levels = variables$name)
"""


def _example(cases, size, cols, specs):
    """analysis_example.R: a correlation, a regression and, for participants with a 0/1 attribute, an ANOVA, on the first variables that
    have values. `cols` are (name, counts?, values) of each variable, in order, `specs` their requests."""
    use = [(n, c, s) for (n, c, vals), s in zip(cols, specs) if any(v is not None for v in vals)]
    lines = ['source("load.R")', ""]
    if len(use) >= 2:
        a, b = use[0][0], use[1][0]
        lines += [f"# Do {a} and {b} go together? (Spearman: any relation that only goes up or down)",
                  f'cor.test(cases${a}, cases${b}, method = "spearman")', ""]
    if use:
        a, counted, _ = use[0]
        pieces = cases.kind == "pieces"
        lines += [f"# {a} against " + ("the position in the book" if pieces else "the sample size"),
                  f"summary(lm({a} ~ " + ("position_pct" if pieces else f"log({size})") + ", data = cases))", ""]
        if counted:
            lines += ["# The same on the raw counts, allowing for the sample size (a Poisson model; try MASS::glm.nb if the counts vary more than they should)",
                      f"summary(glm({a}_n ~ " + ("position_pct + " if pieces else "") + f"offset(log({size})), family = poisson, data = cases))", ""]
        groups = [n for n, _, s in use if s["kind"] == "attribute" and s.get("attr") == "in"]
        others = [n for n, _, _ in use if n not in groups]
        if groups and others:
            lines += [f"# Does {others[0]} differ between {groups[0]} = 0 and 1? (a one-way ANOVA)",
                      f"summary(aov({others[0]} ~ factor({groups[0]}), data = cases))", ""]
    return "\n".join(lines)


def write_zip(dest, parts):
    """Write the `files` of an export (a dict of {name: text}) to the path or file `dest` as one .zip."""
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in parts.items():
            z.writestr(name, text)
