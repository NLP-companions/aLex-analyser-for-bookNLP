"""What is kept on a book (core/kept.py): results by key, the least recently used dropped past a number of entries or a budget, safe
across threads, and never saved with the book or copied into its plural copy."""
from __future__ import annotations

import threading

import pytest

from alex.core.kept import Kept


def test_a_result_is_made_once_and_then_found():
    k, made = Kept(entries=2), []
    make = lambda: made.append(1) or len(made)
    assert k.get("a", make) == 1 and k.get("a", make) == 1 and made == [1]


def test_past_the_entries_the_least_recently_used_goes():
    k = Kept(entries=2)
    k.get("a", lambda: 1)
    k.get("b", lambda: 2)
    k.get("a", lambda: 0)                 # used again: now b is the oldest
    k.get("c", lambda: 3)
    assert k.keys() == ["a", "c"]


def test_a_budget_keeps_the_newest_within_it_and_always_the_newest():
    k = Kept(budget=10, cost=lambda key: key)
    for n in (4, 5, 3):
        k.get(n, lambda: None)
    assert k.keys() == [5, 3]             # 4 + 5 + 3 is over 10
    k.get(50, lambda: None)               # on its own over the budget: still kept, alone
    assert k.keys() == [50]


def test_a_limit_must_be_given():
    for bad in ({}, {"entries": 2, "budget": 5, "cost": len}, {"budget": 5}):
        with pytest.raises(ValueError):
            Kept(**bad)


def test_many_threads_at_once_stay_within_the_limit():
    k, errors = Kept(entries=5), []

    def work(t):
        try:
            for i in range(300):
                assert k.get((t + i) % 9, lambda i=i: i) is not None
        except Exception as e:  # noqa: BLE001 - collected for the assertion below
            errors.append(e)
    threads = [threading.Thread(target=work, args=(t,)) for t in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors and len(k) <= 5


def test_a_book_keeps_one_kept_per_owner_and_its_plural_copy_none(lib):
    bd = lib.book("alpha")
    first = bd.kept("test", entries=3)
    assert bd.kept("test", entries=99) is first and first.entries == 3      # the first call's limits stay
    first.get("x", lambda: 1)
    assert "_kept_test" not in bd.plural_copy().__dict__
