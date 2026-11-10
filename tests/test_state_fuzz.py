"""Random sequences of changes to your work (links, narrator links, plural groups, corrections, tags) must never leave it inconsistent.

Each test makes a few hundred random changes to a library of the generated books and, after every one, checks what the documentation promises:
an entity is in at most one person and a person has two members at least; a narrator link holds two different roles; no correction names a person
that is gone; a plural group is never also a member (or its own member), and every book can still be read with plural groups counted either way.
A change that is refused (`ValueError`, `KeyError`) is fine: it must then have changed nothing that breaks these rules.
"""
from __future__ import annotations

import random

import pytest

from alex.core import plurals
from alex.core.bookdata import ekey, parse_ekey
from alex.core.view import View

BOOKS = ["alpha", "beta", "gamma"]
CHARACTERS = ("holmes", "watson", "street", "place", "ryder", "lestrade")        # keys of fixture.BOOKS that are entities
STEPS = 150


def entities(book_ids=BOOKS):
    """The entity ids of the generated books' recurring characters and places."""
    import fixture
    return [ekey(b, c) for b in book_ids for k, c in fixture.BOOKS[b].items() if k in CHARACTERS]


def units(lib, ents):
    """Every unit there is: the entities and the persons linked so far."""
    return ents + ["p:" + p for p in lib.state["persons"]]


def in_book(lib, ents, book):
    """The units that have a member in a book: what the pickers offer a correction in that book."""
    return [e for e in ents if parse_ekey(e)[0] == book] + ["p:" + p for p, v in lib.state["persons"].items() if any(m[0] == book for m in v["members"])]


def check_links(lib, ents, step):
    """The rules about persons, narrator links and the corrections that name them."""
    seen = {}
    for pid, person in lib.state["persons"].items():
        assert len(person["members"]) >= 2, (step, "a person with fewer than two members", pid)
        for book, coref in person["members"]:
            assert (book, int(coref)) not in seen, (step, "an entity in two persons", book, coref)
            seen[(book, int(coref))] = pid
    valid = set(units(lib, ents)) | {"anon", "*"}
    for book, ab in lib.ann["books"].items():
        named = [ab.get("narrator"), *ab.get("para_narrators", {}).values(), *ab.get("chapter_narrators", {}).values(),
                 *(u for us in ab.get("addressees", {}).values() for u in us),
                 *(u for e in ab.get("participants", {}).values() for side in ("add", "remove") for u in e.get(side, []))]
        assert all(u in valid for u in named if u), (step, "a correction names a unit that no longer exists", book, [u for u in named if u and u not in valid])
    for lid, link in lib.state["narrator_links"].items():
        assert len(set(link["members"])) == len(link["members"]) >= 2, (step, "a narrator link needs two different roles", link)
        assert all(m[4:] in valid for m in link["members"] if m.startswith("nar:") and not m.startswith("nar:anon:")), (step, "a narrator link names a gone unit", link)


@pytest.mark.parametrize("seed", range(4))
def test_links_and_corrections_stay_consistent_under_random_changes(lib, seed):
    rng = random.Random(seed)
    ents = entities(["alpha", "beta", "gamma"])
    for step in range(STEPS):
        op = rng.choice(["link", "link", "unlink", "unlink_all", "narrator_link", "narrator_unlink", "narrator_unlink_all", "narrator", "paragraph",
                         "addressee", "tags", "reject", "reset"] if step % 50 == 49 else
                        ["link", "link", "unlink", "unlink_all", "narrator_link", "narrator_unlink", "narrator_unlink_all", "narrator", "paragraph",
                         "addressee", "tags", "reject"])
        roles = lambda: (["nar:" + u for u in units(lib, ents)] + ["nar:anon:alpha", "nar:anon:beta"] + ["nl:" + n for n in lib.state["narrator_links"]])
        book = rng.choice(BOOKS)
        try:
            if op == "link":
                lib.link(*rng.sample(units(lib, ents), 2), name=rng.choice([None, "Name"]))
            elif op == "unlink" and lib.state["persons"]:
                pid = rng.choice(list(lib.state["persons"]))
                lib.unlink(pid, *rng.choice(lib.state["persons"][pid]["members"]))
            elif op == "unlink_all" and lib.state["persons"]:
                lib.unlink_all(rng.choice(list(lib.state["persons"])))
            elif op == "narrator_link":
                lib.link_narrators(*rng.sample(roles(), 2))
            elif op == "narrator_unlink" and lib.state["narrator_links"]:
                lid = rng.choice(list(lib.state["narrator_links"]))
                lib.unlink_narrator(lid, rng.choice(lib.state["narrator_links"][lid]["members"]))
            elif op == "narrator_unlink_all" and lib.state["narrator_links"]:
                lib.unlink_narrators_all(rng.choice(list(lib.state["narrator_links"])))
            elif op == "narrator":
                lib.ann_book(book)["narrator"] = rng.choice(in_book(lib, ents, book) + ["anon"])
                lib.save_ann()
            elif op == "paragraph":
                lib.ann_book(book)["para_narrators"][f"p{rng.randint(0, 5)}"] = rng.choice(in_book(lib, ents, book) + ["anon"])
                lib.save_ann()
            elif op == "addressee":
                lib.ann_book(book)["addressees"][f"q{rng.randint(0, 5)}"] = rng.sample(in_book(lib, ents, book) + ["*"], 2)
                lib.save_ann()
            elif op == "tags":
                lib.set_tags(rng.choice(units(lib, ents)), rng.sample(["a", "b", "c"], rng.randint(0, 2)))
            elif op == "reject":
                lib.reject(*rng.sample(units(lib, ents), 2))
            elif op == "reset":
                lib.reset_links()
        except (ValueError, KeyError):
            pass
        check_links(lib, ents, (step, op))


@pytest.mark.parametrize("seed", range(4))
def test_plural_groups_stay_consistent_under_random_changes(lib, seed):
    rng = random.Random(100 + seed)
    ents = entities(BOOKS)
    for step in range(STEPS):
        op = rng.choice(["link", "unlink_all", "unlink", "set", "set", "change", "reject"])
        try:
            if op == "link":
                lib.link(*rng.sample(units(lib, ents), 2))
            elif op == "unlink_all" and lib.state["persons"]:
                lib.unlink_all(rng.choice(list(lib.state["persons"])))
            elif op == "unlink" and lib.state["persons"]:
                pid = rng.choice(list(lib.state["persons"]))
                lib.unlink(pid, *rng.choice(lib.state["persons"][pid]["members"]))
            elif op == "set":
                plurals.set_members(lib, rng.choice(units(lib, ents)), rng.sample(units(lib, ents), rng.randint(0, 3)))
            elif op == "change":
                plurals.change_members(lib, rng.choice(units(lib, ents)), add=rng.sample(units(lib, ents), rng.randint(0, 2)), remove=rng.sample(units(lib, ents), rng.randint(0, 2)))
            elif op == "reject":
                plurals.reject(lib, rng.choice(units(lib, ents)))
        except (ValueError, KeyError):
            pass
        for book in BOOKS:
            declared = plurals.book_map(lib, book)
            members = {m for ms in declared.values() for m in ms}
            assert not set(declared) & members, ((step, op), "a plural group is also a member", book, declared)
            assert all(c not in ms for c, ms in declared.items()), ((step, op), "a group is its own member")
            for counted in (False, True):
                bd = lib.book(book, counted)
                assert all(m in bd.groups for g in bd.groups.values() for m in g.members), ((step, op), "a member that is no group")
        View(lib, BOOKS, True)
