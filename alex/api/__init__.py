"""The web API: one router per area, built around a shared `Context`.

    library.py    books, settings, entity list, tags, the export zip
    entities.py   profiles, comparisons, evidence, networks
    overbook.py   a target slice by slice through one book
    described.py  what a target is described and called as, by whom
    statistics.py correlations and descriptives over cases, the R export, saved sets
    dialogue.py   dialogue views and your corrections
    corpus.py     concordance, word lists, n-grams, collocates, keywords, reference files
    narrative.py  arcs, style, stylometry, sentiment; the text view
    sound.py      the Sound and rhythm tab: figures, cadences, runs, scansion
    lexicons.py   your word lexicons (store, edit) and their arcs
    topics.py     topic models
    links.py      linking entities across books
    workspaces.py workspaces: list, create, switch, import a zip, delete

Every route takes and returns JSON. A route that is given something it can't use answers 400 with
`{"detail": "…"}`, which the browser shows as a message (see the handlers in app.py).
"""
from . import context, corpus, described, dialogue, entities, library, lexicons, links, narrative, overbook, sound, statistics
from . import topics as topics_api
from . import workspaces as workspaces_api


def routers(ctx, topics, workspaces):
    """All routers for a running analyser. `topics` is the topic-modelling package, or None if scikit-learn is missing;
    `workspaces` is the core.workspaces.Workspaces list."""
    return [library.router(ctx, topics), entities.router(ctx), overbook.router(ctx), described.router(ctx), statistics.router(ctx), dialogue.router(ctx), corpus.router(ctx),
            narrative.router(ctx, topics), sound.router(ctx), lexicons.router(ctx), topics_api.router(ctx, topics), links.router(ctx),
            workspaces_api.router(ctx, topics, workspaces)]


__all__ = ["context", "routers"]
