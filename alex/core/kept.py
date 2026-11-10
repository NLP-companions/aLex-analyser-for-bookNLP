"""What is worked out from a book once and kept on it: lookup tables, results per setting, figures per stretch of text.

Every module that keeps something derived from a book asks the book for its own `Kept` (`BookData.kept(owner, …)`) and gets a result
with `get(key, make)`: the result kept under `key`, else `make()`'s, which is then kept. The key is everything the result depends on
(a setting, your corrections, a stretch of tokens), so a change of any of them is a new key and an old result is never used by
mistake. What is kept is limited, so a long session can't fill the memory:

* by **entries**: at most that many results (a lookup table the book has one of: 1; results per setting: a few; figures per chapter
  or slice: a few hundred);
* or by **budget**: the results' `cost` added up (for tallies that keep every run's position, the tokens they cover) stays within it.

Past the limit the result used least recently goes. A `Kept` is safe to use from several requests at once: a result being made is
not locked (two requests may make the same one; the second is kept), so a slow result never holds up the others. It lives as long as
the book does in memory and is never saved with it, nor copied into its plural copy (`BookData.plural_copy`).
"""
from __future__ import annotations

import threading
from collections import OrderedDict


class Kept:
    """Results kept by key, the most recently used last, within `entries` or within `budget` (the sum of `cost(key)`)."""

    def __init__(self, entries=None, budget=None, cost=None):
        """Keep at most `entries` results or, with a `budget`, results whose `cost(key)` adds up to at most that (always the newest)."""
        if (entries is None) == (budget is None) or (budget is not None and cost is None):
            raise ValueError("A Kept needs a number of entries, or a budget with a cost.")
        self.entries, self.budget, self.cost = entries, budget, cost
        self._results: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key, make):
        """The result kept under `key`, else `make()`'s, kept from now on (and the least recently used ones dropped past the limit)."""
        with self._lock:
            if key in self._results:
                self._results.move_to_end(key)
                return self._results[key]
        result = make()                                  # outside the lock: it can take a while
        with self._lock:
            self._results[key] = result
            self._results.move_to_end(key)
            while len(self._results) > 1 and self._over():
                self._results.popitem(last=False)
        return result

    def _over(self):
        """Whether more is kept than the limit allows."""
        if self.budget is None:
            return len(self._results) > self.entries
        return sum(self.cost(k) for k in self._results) > self.budget

    def keys(self):
        """The keys kept, the least recently used first."""
        with self._lock:
            return list(self._results)

    def __len__(self):
        """How many results are kept."""
        return len(self._results)

    def clear(self):
        """Forget everything kept."""
        with self._lock:
            self._results.clear()
