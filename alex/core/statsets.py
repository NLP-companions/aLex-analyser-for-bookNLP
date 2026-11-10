"""Saved sets of the Statistics tab: a whole setup (cases, variables, options) under a name, to run again later.

A set is `{"name", "setup"}` in `library.json` under `stat_sets` (next free number in `next_stat_set`); `setup` is the request the page
sends (`statstab.run`), stored as it is. Like a saved group of entities it names entities by id, so it follows your links and the
selected books, and it travels in the export zip unchanged: an entity that isn't in the books selected when it runs makes a variable
with no values, not an error. The functions take the `Library`, change its state under its lock and save it; `ValueError` means
input that can't be used (a blank or repeated name, a setup that isn't one), `KeyError` an unknown set.
"""
from __future__ import annotations

import json

MAX_SETUP = 200_000                                  # characters of a stored setup, as JSON


def _check_name(lib, name, own=None):
    """The trimmed name, if it is given and not already used by another set."""
    name = str(name or "").strip()[:120]
    if not name:
        raise ValueError("Give the set a name.")
    if any(s["name"].lower() == name.lower() for sid, s in lib.state["stat_sets"].items() if sid != own):
        raise ValueError(f"There is already a set called “{name}”.")
    return name


def _check_setup(setup):
    """The setup, if it is a request the page could send (a dict with variables, not too large)."""
    if not isinstance(setup, dict) or not isinstance(setup.get("rows"), list) or not setup["rows"]:
        raise ValueError("A set needs a setup with at least one variable.")
    if len(json.dumps(setup)) > MAX_SETUP:
        raise ValueError("That setup is too large to save.")
    return setup


def create(lib, name, setup):
    """Save a setup under a name -> its id."""
    setup = _check_setup(setup)
    with lib.lock:
        name = _check_name(lib, name)
        sid = str(lib.state["next_stat_set"])
        lib.state["next_stat_set"] += 1
        lib.state["stat_sets"][sid] = {"name": name, "setup": setup}
        lib.save()
        return sid


def update(lib, sid, name=None, setup=None):
    """Rename a set and/or replace its setup."""
    with lib.lock:
        s = lib.state["stat_sets"][str(sid)]
        if name is not None:
            s["name"] = _check_name(lib, name, own=str(sid))
        if setup is not None:
            s["setup"] = _check_setup(setup)
        lib.save()


def delete(lib, sid):
    """Remove a set."""
    with lib.lock:
        del lib.state["stat_sets"][str(sid)]
        lib.save()


def listing(lib):
    """Every set for the browser, by name: `{id, name, setup}`."""
    return sorted(({"id": sid, "name": s["name"], "setup": s["setup"]} for sid, s in lib.state["stat_sets"].items()),
                  key=lambda s: s["name"].lower())
