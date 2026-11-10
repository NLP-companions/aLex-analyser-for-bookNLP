"""The Statistics tab: correlations and descriptive statistics of variables measured over cases.

A request (`run`) names the cases (`core/cases.py`), one or two lists of variables (`core/variables.py`) and the options. One list gives a
correlation **matrix**, every variable against every other (the lower triangle); two lists give a **grid**, each row variable against each
column variable. Every cell is `stats.correlate` (Pearson's r or Spearman's ρ, missing values left out pair by pair) with its p corrected for
the number of tests in the table (`stats.adjust`) and stars for the corrected p. The **descriptives** are `stats.describe` of every variable,
over all cases and, with a `split`, per group of cases: participants by gender, tag, saved group or book, pieces by book. A participant is in
every group they belong to (two tags, two blocks); split by book, a participant is measured again in each book alone (`cases.build` with
`books`), so their values there are that book's. The raw values come back too, for the Data view and the CSV download.
"""
from __future__ import annotations

from . import cases as casemod
from . import entitygroups, stats, variables
from .bookdata import one_of
from .view import gender_label

SPLITS = {"none": "No split", "gender": "Gender", "tag": "Tag", "group": "Saved group", "book": "Book"}
MAX_LIST = 30                                        # variables in one list
NOT_A_PERSON = "_none"                               # the gender group of a participant that is no person (a narrator role, a place)
UNTAGGED = "_untagged"                               # the tag group of a participant without tags
UNGROUPED = "_ungrouped"                             # the saved-group group of a participant in none
NOTES = {
    "correlation": ("Each cell correlates two variables over the cases that have both values. Pearson's r measures a straight-line "
                    "relation; Spearman's ρ is r of the ranks, so it measures any relation that only goes up (or down) and is less "
                    "moved by a few extreme cases. With a 0/1 variable (a gender, a tag) r is the point-biserial correlation. p is "
                    "two-tailed, from t with N − 2 degrees of freedom; the 95% interval comes from Fisher's z. Stars: * p < .05, "
                    "** p < .01, *** p < .001, after the correction."),
    "correction": ("Many cells mean many tests, and about 1 in 20 is 'significant' by chance at .05. Bonferroni multiplies each p by "
                   "the number of tests; Holm does the same step by step from the smallest p and is less strict while still "
                   "guarding against any false finding."),
    "independence": ("Cases from one book are not independent (neighbouring chapters share characters and style; a character's speech "
                     "is shaped by the scenes they are in), so p-values are guides, not proofs. Rates from small samples vary a lot: "
                     "raise the minimum sample if a few small cases drive a result (the Data view shows them)."),
    "descriptives": ("N: cases with a value. M: mean. SD: standard deviation and V: variance, both of a sample (divided by N − 1). "
                     "SE: standard error of the mean (SD ÷ √N); the 95% interval of the mean is from t with N − 1 degrees of freedom. "
                     "Split by a group, a participant is in every group they belong to; split by book, they are measured in each "
                     "book alone."),
}


def check(setup):
    """The request, checked: (cases setup, row specs, column specs, method, correction, split). Raises ValueError."""
    if not isinstance(setup, dict):
        raise ValueError("Say what to compute.")
    rows, cols = setup.get("rows"), setup.get("columns") or []
    if not isinstance(rows, list) or not rows:
        raise ValueError("Add at least one variable.")
    if not isinstance(cols, list) or len(rows) > MAX_LIST or len(cols) > MAX_LIST:
        raise ValueError(f"Use at most {MAX_LIST} variables in each list.")
    method, correction, split = setup.get("method", "pearson"), setup.get("correction", "none"), setup.get("split", "none")
    if not (one_of(method, stats.CORRELATIONS) and one_of(correction, stats.CORRECTIONS) and one_of(split, SPLITS)):
        raise ValueError("Unknown option: " + ("coefficient" if not one_of(method, stats.CORRELATIONS) else
                                               "correction" if not one_of(correction, stats.CORRECTIONS) else "split") + ".")
    return setup.get("cases") or {}, rows, cols, method, correction, split


def run(view, setup, lexicons=None):
    """Everything the Statistics tab shows for a request `setup`: {cases (see `cases.build`), rows (variable specs), columns (a second
    list, for a grid; none for a matrix), method (`stats.CORRELATIONS`), correction (`stats.CORRECTIONS`), split (`SPLITS`)}.
    -> {cases: {summary, rows}, variables (ids v0…, the rows' first), values (per variable, a value per case), correlations, descriptives,
    notes}. `lexicons` are your word lexicons by id (for lexicon variables). Raises ValueError for anything it can't use."""
    case_setup, rows, cols, method, correction, split = check(setup)
    cases = casemod.build(view, case_setup)
    data = variables.table(view, cases, rows + cols, lexicons)
    ids = [v["id"] for v in data["variables"]]
    return {"cases": {**cases.summary(), "rows": cases.rows}, "variables": data["variables"], "values": data["values"],
            "correlations": correlations(data["values"], ids[:len(rows)], ids[len(rows):], method, correction),
            "descriptives": descriptives(view, case_setup, cases, data, split, lexicons), "notes": NOTES}


def correlations(values, row_ids, col_ids, method="pearson", correction="none"):
    """The correlation table. `values` are the variables' values in id order (`row_ids` then `col_ids`, ids "v<k>" = their position).
    No `col_ids`: a matrix of the rows (cells below the diagonal; the others None). -> {shape, rows, columns, cells (row by column:
    {r, n, p, p_adj, lo, hi, stars} or None), tests (how many p-values the correction counted), method, correction}."""
    at = lambda vid: values[int(vid[1:])]          # noqa: E731
    grid = bool(col_ids)
    cols = col_ids if grid else row_ids
    ready = {vid: stats.centred(at(vid), method) for vid in dict.fromkeys(row_ids + cols)}      # complete variables, prepared once

    def cell(a, b):
        """One pair: from the prepared variables when both are complete, else with pairwise deletion."""
        if ready[a] is not None and ready[b] is not None:
            return stats.correlate_centred(ready[a], ready[b], method)
        return stats.correlate(at(a), at(b), method)
    cells = [[cell(a, b) if grid or j < i else None for j, b in enumerate(cols)] for i, a in enumerate(row_ids)]
    flat = [c for line in cells for c in line if c is not None]
    for c, p in zip(flat, stats.adjust([c["p"] for c in flat], correction)):
        c["p_adj"], c["stars"] = p, stats.stars(p)
    return {"shape": "grid" if grid else "matrix", "rows": row_ids, "columns": cols, "cells": cells,
            "tests": sum(c["p"] is not None for c in flat), "method": method, "correction": correction}


def descriptives(view, case_setup, cases, data, split="none", lexicons=None):
    """`stats.describe` of every variable, over all cases and, with a `split`, per group of cases -> {split, groups: [{key, label, n (cases),
    stats (one per variable, in order)}]}, the first group being all cases. Raises ValueError for a split the cases don't have."""
    groups = [{"key": "all", "label": "All cases", "n": len(cases.rows), "stats": [stats.describe(v) for v in data["values"]]}]
    if split == "none":
        return {"split": split, "groups": groups}
    if cases.kind == "pieces" and split != "book":
        raise ValueError("Text pieces can only be split by book.")
    if split == "book" and cases.kind == "participants":
        specs = [v["spec"] for v in data["variables"]]
        for b in view.books:
            sub = casemod.build(view, case_setup, books=[b])
            if sub.rows:
                values = variables.table(view, sub, specs, lexicons)["values"]
                groups.append({"key": b, "label": view.title(b), "n": len(sub.rows), "stats": [stats.describe(v) for v in values]})
        return {"split": split, "groups": groups}
    for key, label, members in _groups(view, cases, split):
        values = [[vals[i] for i in members] for vals in data["values"]]
        groups.append({"key": key, "label": label, "n": len(members), "stats": [stats.describe(v) for v in values]})
    return {"split": split, "groups": groups}


def _groups(view, cases, split):
    """The groups of cases for a split (not participants by book): [(key, label, row indices)], groups without cases left out."""
    if split == "book":
        return [(b, view.title(b), [i for i, r in enumerate(cases.rows) if r["book"] == b]) for b in view.books]
    units = [view.units.get(r["id"]) for r in cases.rows]
    if split == "gender":
        keys = [[view.gender_of(u)] if u and u.type == "PER" else [NOT_A_PERSON] for u in units]
        order = [g["pron"] for g in view.genders()] + [NOT_A_PERSON]
        label = lambda k: "Not a person" if k == NOT_A_PERSON else gender_label(k)        # noqa: E731
    elif split == "tag":
        keys = [list(u.tags) if u and u.tags else [UNTAGGED] for u in units]
        order = sorted({k for ks in keys for k in ks if k != UNTAGGED}, key=str.lower) + [UNTAGGED]
        label = lambda k: "(no tag)" if k == UNTAGGED else k                               # noqa: E731
    else:
        saved = entitygroups.listing(view.lib)
        inside = {g["id"]: {u.id for u in view.group_of({"group": g["id"]})[0]} for g in saved}
        keys = [[g["id"] for g in saved if u and u.id in inside[g["id"]]] or [UNGROUPED] for u in units]
        names = {g["id"]: g["name"] for g in saved}
        order = [g["id"] for g in saved] + [UNGROUPED]
        label = lambda k: "(in no saved group)" if k == UNGROUPED else names[k]            # noqa: E731
    out = []
    for k in order:
        members = [i for i, ks in enumerate(keys) if k in ks]
        if members:
            out.append((k, label(k), members))
    return out

