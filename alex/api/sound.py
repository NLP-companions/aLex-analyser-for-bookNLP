"""The Sound and rhythm tab: figures, cadences, runs and scansion of a part of the text, and the words whose pronunciation is guessed
(analysis in core/soundtab.py; your corrections are saved with the settings, `/api/settings`)."""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from alex.core import prosody, sound, soundtab

from .context import Context, choice, need_str, text, whole
from .narrative import BY


def router(ctx: Context) -> APIRouter:
    """The routes of the Sound and rhythm tab. Each takes the selected `books` and a `scope` (as the Corpus pages: `{kind: "all" |
    "narration" | "dialogue" | "speech", speaker}`) and uses the workspace's sound settings; without the pronunciation dictionary
    each answers 400 saying how to install it."""
    r = APIRouter()

    def ready():
        """The workspace's sound settings (`prosody.config`); 400 when the pronunciation dictionary isn't installed."""
        if not sound.available():
            raise HTTPException(400, sound.MISSING)
        return prosody.config(ctx.lib.state["settings"])

    @r.post("/api/sound/figures")
    def figures(body: dict = Body(...)):
        """The figures per book, or per chapter or slice (`by`: "book" or "segment", cut as `seg` says): see `soundtab.figures`."""
        cfg = ready()
        return soundtab.figures(ctx.of(body), body.get("seg"), choice(body, "by", BY, "book"), body.get("scope"), cfg)

    @r.post("/api/sound/cadences")
    def cadences(body: dict = Body(...)):
        """Every cadence pattern found, with its numbers (`soundtab.cadences`); with `pattern` ("10010") instead the phrases ending
        with it (`end_only`: only those ending a sentence), see `soundtab.cadence_examples`."""
        cfg, v = ready(), ctx.of(body)
        if body.get("pattern") is not None:
            return soundtab.cadence_examples(v, body.get("scope"), cfg, body["pattern"], body.get("end_only") is True)
        return soundtab.cadences(v, body.get("scope"), cfg)

    @r.post("/api/sound/runs")
    def runs(body: dict = Body(...)):
        """The runs of one `kind` by what they share (`soundtab.runs`); with `key` instead the runs that share it, longest first, each in
        its sentence (`soundtab.run_examples`)."""
        cfg, v = ready(), ctx.of(body)
        kind = choice(body, "kind", prosody.RUNS, "alliteration")
        if body.get("key") is not None:
            return soundtab.run_examples(v, body.get("scope"), cfg, kind, need_str(body, "key"))
        return soundtab.runs(v, body.get("scope"), cfg, kind)

    @r.post("/api/sound/scan")
    def scan(body: dict = Body(...)):
        """One chapter or slice (`index`, cut as `seg` says) of a `book`, word by word: see `soundtab.scan`."""
        cfg = ready()
        return soundtab.scan(ctx.of(body), need_str(body, "book"), body.get("seg"), whole(body, "index", 0, 0), body.get("scope"), cfg)

    @r.post("/api/sound/guessed")
    def guessed(body: dict = Body(...)):
        """The words of the selected books whose pronunciation is guessed, and the words you corrected: see `soundtab.guessed`."""
        cfg = ready()
        return soundtab.guessed(ctx.of(body), cfg)

    @r.post("/api/sound/lookup")
    def lookup(body: dict = Body(...)):
        """How one `word` is said now (with your corrections; `pos`, a part of speech, picks between the dictionary's variants), as a
        starting point for correcting it: see `soundtab.lookup`."""
        cfg = ready()
        return soundtab.lookup(need_str(body, "word"), cfg, text(body, "pos"))

    return r
