"""Narrative arc and style.

Sections: segments · arcs · style · stylometry · sentiment · lexicon arcs.

A **segment** is a stretch of one book: an equal slice, or a chapter found from headings
(`segments`). Arcs, style tables, sentiment and the topic tools all measure "per segment", so
they share this one definition; `all_segments` lists the segments of every selected book.
A segment is `{book, title, index, label, start, end, words, pos}`; `start`/`end` are token positions."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from itertools import islice

from .bookdata import QUOTE_MARKS
from .corpus import cindex
from .dialogue import ann_sig, keys, mattr
from .sound import guess_syllables

HEADING_WORDS = r"^(chapter|book|part|adventure|story|section|canto|volume|act|scene|prologue|epilogue|introduction|preface)\b"
NUMERAL = r"^([ivxlcdm]+|\d+)[.:)]?(\s|$)"
CONTENT = {"NOUN", "VERB", "ADJ", "ADV", "PROPN"}
MAX_TEXTS = 400          # the cluster tree is cubic in the number of texts
SUBORD = {"advcl", "ccomp", "xcomp", "acl", "relcl", "csubj", "csubjpass"}
PRONOUNS = {"i", "me", "my", "mine", "myself", "you", "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself",
            "she", "her", "hers", "herself", "it", "its", "itself", "we", "us", "our", "ours", "ourselves", "they", "them",
            "their", "theirs", "themselves", "thee", "thou", "thy", "thine", "ye"}
NOTES = {
    "segments": ("Slices divide each book into equal numbers of tokens, or, with “Words per slice”, are cut at every so many words (a short rest at the end of a book joins the last slice); “Whole corpus” instead divides the total slice count across every selected book by "
                 "its share of the words, so a short book gets fewer slices than a long one instead of the same number. Chapters start at headings: a short paragraph (12 words or fewer, not a quote) that "
                 "begins with a heading word (Chapter, Book, Part, Adventure, Story…) or a numeral (IV., 12), or, if chosen, is written in capitals "
                 "(but isn't initials and a name, as in a letter's signature), "
                 "or has no closing punctuation. A heading directly followed by another heading line (a title) is joined to it. A heading less than the "
                 "minimum length after the previous one is ignored, which removes tables of contents and letters' signatures. Text before the first "
                 "heading becomes an opening segment if it's long enough. Books with fewer than two headings fall back to slices."),
    "arcs": ("Each point is a rate per 1,000 words in that segment: mentions of the entity (any form), tokens BookNLP marks as events, or supersense "
             "tags starting in the segment. Dialogue is the share of the segment's words inside quotes. Segments run in book order; with “Book by book” "
             "(the default) each book's line is separate, so a trend never crosses a book's end; with “Whole corpus” the line runs continuously across every "
             "selected book, to follow a change across or between them, and (with equal slices) each book's slice count follows its share of the words."),
    "style": ("Sentences are BookNLP's; words exclude punctuation and quotation marks. Sentence length is in words. Lexical density is the share of words "
              "that are nouns, proper nouns, verbs, adjectives or adverbs. MATTR is the moving-average type-token ratio over 100-word windows; hapaxes are "
              "words occurring once in the text, as a share of its words. Dependency distance is the mean number of tokens between a word and its head; "
              "tree depth is the mean depth of the deepest word in each sentence. Subordinate clauses count advcl, ccomp, xcomp, acl, relcl and csubj "
              "relations per sentence. Passives count nsubjpass per 1,000 words. Flesch Reading Ease and Flesch–Kincaid grade use syllables estimated from "
              "vowel groups, so treat them as approximate."),
    "wordchoice": ("Shares of the words that are each part of speech, as BookNLP tags them; ratios of adjectives, adverbs or nouns (not proper nouns) "
                   "to verbs (not auxiliaries), and of modifiers (adjectives and adverbs) to heads (nouns and verbs); and the share of verbs, among those "
                   "BookNLP gives a supersense, that are dynamic (motion, contact, change, body, creation, competition, consumption, weather) rather than "
                   "static (stative, cognition, perception, emotion, possession, social, communication), or of one kind. Supersenses exist for nouns and "
                   "verbs only. The same figures as on the Dialogue and Statistics pages."),
    "sound": ("Each word's stresses and sounds come from the CMU Pronouncing Dictionary (American English), or are guessed for a word it lacks "
              "(guessed: the share of words, mostly names; their syllables count, their sounds don't); one-syllable function words count as "
              "unstressed. Stress figures are counted within phrases (between pauses: . ? ! ; : , dashes, brackets). A clash is two stresses side by "
              "side, a lapse three or more unstressed syllables in a row; binary and ternary gaps have one and two unstressed syllables between "
              "stresses; nPVI measures how unevenly the stresses are spaced (0 is perfectly even). A cadence is a phrase's syllables from its "
              "last-but-one stress to the end, named by the English cursus: planus /xx/x, tardus /xx/xx, velox /xxxx/x, trispondaicus /xxx/x. "
              "A run is a chain of nearby content words sharing a sound (alliteration: the stressed syllable's first consonant, the word's first "
              "sound or its first letter, as set; assonance: the stressed vowel; consonance: the final consonants; rhyme: the stressed vowel and all "
              "after it) or the same word (repetition: the same lemma or form, as set; a repeated word doesn't count again in a sound run), within "
              "the window and boundary set under Settings → Sound and rhythm. The sound profile counts consonants and stressed vowels per 1,000 words."),
    "stylo": ("Each text is represented by the relative frequencies of the most frequent words (word forms, lowercased) across all texts, after culling "
              "words that don't occur in at least the chosen share of texts. Frequencies are turned into z-scores across the texts. Classic Delta "
              "(Burrows 2002) is the mean absolute difference of z-scores; Cosine Delta (Smith & Aldridge 2011; Evert et al. 2017) is 1 − the cosine "
              "similarity of the z-score vectors, and is usually the most reliable; Euclidean is the straight-line distance. The tree joins the closest "
              "texts first (average, complete or Ward linkage). The map is a principal component analysis of the z-scores; the words listed weigh most on "
              "each axis. Short texts (under about 2,000 words) give unstable results."),
    "sentiment": ("Sentiment is VADER's compound score (Hutto & Gilbert 2014), from −1 (most negative) to +1 (most positive), for each BookNLP sentence, "
                  "averaged over the sentences that start in a segment. VADER was built for social media text, so read literary results as rough tone, "
                  "not meaning. “Around” an entity averages only sentences that mention it. Positive and negative sentences are those scoring at least "
                  "+0.05 or at most −0.05."),
    "lexicon": ("Lexicon arcs count words (lowercased word forms, falling back to the lemma) listed under each category of a lexicon, per 1,000 "
                "words of the segment. A word can belong to several categories."),
}


# ---------- segments ----------
SLICE_WORDS = (20, 1_000_000)                        # the smallest and largest number of words per slice


def _is_heading(bd, s, e, rules):
    """Whether a paragraph looks like a chapter heading (see NOTES["segments"]); `rules` switch the heading kinds on or off."""
    words = [i for i in range(s, e + 1) if bd.pos[i] not in ("PUNCT", "SPACE", "SYM")]
    if not words or len(words) > 12 or bd.word[s] in QUOTE_MARKS:
        return False
    text = bd.span_text(s, e).strip()
    low = text.lower()
    if rules.get("numbered", True) and (re.match(HEADING_WORDS, low) or re.match(NUMERAL, low)):
        return True
    letters = [c for c in text if c.isalpha()]
    if rules.get("caps", True) and len(letters) >= 3 and all(c.isupper() for c in letters) \
            and not re.match(r"^([A-Z]\.\s*)+[A-Z'’-]*\.?$", text):  # not a signature like "P. HIRSCH" or "G. K. C."
        return True
    if rules.get("short") and text[-1:] not in ".?!,;:\"'”’" and len(words) <= 10:
        return True
    return False


def segments(bd, cfg, edits=None):
    """Split one book into segments -> (segments, info).

    cfg["mode"] "slices" or "chapters". Slices are `n` of equal token counts, or, with cfg["slice_by"] "words", one every
    `words` words (`word_slices`; the slice setting also fills in for a book without chapters). Chapters start at heading paragraphs
    (see NOTES["segments"]); a heading less than `min_words` after the previous one is dropped
    (tables of contents, signatures). A book with fewer than two headings falls back to slices,
    which `info["fallback"]` records.

    `edits` are your changes to the chapters found, `{"add": [paragraph keys], "remove": [...], "names": {key: title}}`
    (`edit_chapters`); with edits, the automatic chapters minus those you removed plus those you added are used, and
    a book needs only one chapter start to be split into chapters (`info["edited"]`). Every chapter segment carries `source`
    ("auto" or "yours") and `head`, the token where its heading paragraph starts (None for slices and an "Opening" part)."""
    cfg = cfg if isinstance(cfg, dict) else {}
    mode = cfg.get("mode", "slices")
    n = _setting(cfg, "n", 10, 2, 200)
    per = _setting(cfg, "words", 200, *SLICE_WORDS) if cfg.get("slice_by") == "words" else None
    iw = cindex(bd)["isword"]
    if mode == "chapters":
        rules = cfg.get("rules") if isinstance(cfg.get("rules"), dict) else {}
        min_words = _setting(cfg, "min_words", 500, 0, 10 ** 6)
        paras = sorted(bd.para_bounds.items())
        heads = []
        for pid, (s, e) in paras:
            if _is_heading(bd, s, e, rules):
                if heads and heads[-1]["last_para"] == pid - 1:
                    heads[-1]["text"] += " " + bd.span_text(s, e).strip()
                    heads[-1]["last_para"] = pid
                    heads[-1]["body"] = e + 1
                else:
                    heads.append({"start": s, "body": e + 1, "text": bd.span_text(s, e).strip(), "last_para": pid})
        wpref = [0]
        for f in iw:
            wpref.append(wpref[-1] + f)
        words_between = lambda a, b: wpref[b] - wpref[a]
        kept = []
        for hd in heads:
            if kept and words_between(kept[-1]["body"], hd["start"]) < min_words:
                continue
            kept.append(hd)
        edited = bool(edits and (edits.get("add") or edits.get("remove") or edits.get("names")))
        if edited:
            starts = _edited_starts(bd, kept, edits)
            if starts:
                segs = [{"label": "Opening", "start": 0, "end": starts[0]["start"] - 1, "source": None, "head": None}] if starts[0]["start"] > 0 else []
                for k, st in enumerate(starts):
                    end = starts[k + 1]["start"] - 1 if k + 1 < len(starts) else bd.n_tokens - 1
                    segs.append({"label": st["label"][:80], "start": st["start"], "end": end, "source": st["source"], "head": st["start"]})
                for sg in segs:
                    sg["words"] = words_between(sg["start"], sg["end"] + 1)
                return segs, {"mode": "chapters", "headings": len(heads), "kept": len(kept), "fallback": False, "edited": True,
                              "yours": sum(st["source"] == "yours" for st in starts)}
        if len(kept) >= 2:
            segs = []
            if kept[0]["start"] > 0 and words_between(0, kept[0]["start"]) >= min_words:
                segs.append({"label": "Opening", "start": 0, "end": kept[0]["start"] - 1, "source": None, "head": None})
            else:                                          # nothing before it, or too short to stand alone: the first chapter takes it in
                kept[0] = {**kept[0], "start": 0, "head": kept[0]["start"]}
            for k, hd in enumerate(kept):
                end = kept[k + 1]["start"] - 1 if k + 1 < len(kept) else bd.n_tokens - 1
                label = re.sub(r"\s+", " ", hd["text"])
                segs.append({"label": label[:80], "start": hd["start"], "end": end, "source": "auto", "head": hd.get("head", hd["start"])})
            for sg in segs:
                sg["words"] = words_between(sg["start"], sg["end"] + 1)
            return segs, {"mode": "chapters", "headings": len(heads), "kept": len(kept), "fallback": False, "edited": False, "yours": 0}
        fallback = {"mode": "slices", "headings": len(heads), "kept": len(kept), "fallback": True, "edited": False}
    else:
        fallback = {"mode": "slices", "fallback": False}
    if per:
        return word_slices(bd, per), fallback
    segs = []
    for k in range(n):
        s, e = k * bd.n_tokens // n, (k + 1) * bd.n_tokens // n - 1
        segs.append({"label": f"{k + 1}/{n}", "start": s, "end": e, "words": sum(iw[s:e + 1]), "source": None, "head": None})
    return segs, fallback


def word_slices(bd, per):
    """A book cut into slices of `per` words each, in text order: each slice runs from its first word to just before the next slice's
    (the first from the book's start, the last to its end). What is left at the end joins the last slice when it is under half a slice,
    and is a slice of its own otherwise. Segments as `segments` makes them, labelled "3/40"."""
    iw = cindex(bd)["isword"]
    words = [i for i, w in enumerate(iw) if w]
    firsts = list(range(0, len(words), per)) or [0]                # index in `words` of each slice's first word
    if len(firsts) > 1 and len(words) - firsts[-1] < per / 2:
        firsts.pop()
    toks = [0] + [words[k] for k in firsts[1:]]
    return [{"label": f"{k + 1}/{len(toks)}", "start": s, "end": toks[k + 1] - 1 if k + 1 < len(toks) else bd.n_tokens - 1,
             "words": (firsts[k + 1] if k + 1 < len(firsts) else len(words)) - firsts[k], "source": None, "head": None}
            for k, s in enumerate(toks)]


def _setting(cfg, key, default, low, high):
    """A whole-number segment setting (`n`, `min_words`), held between low and high; a readable error if it isn't a number."""
    try:
        return max(low, min(high, int(cfg.get(key, default))))
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"The segment setting “{key}” should be a whole number.") from None


def _edited_starts(bd, kept, edits):
    """The chapter starts after your edits, in text order: `{start (token), label, source}`. The automatic headings in `kept` minus
    those whose paragraph you removed, plus the paragraphs you made chapter starts (labelled with their opening words), with the titles you gave.
    Edits are found again by the paragraph's opening words (`dialogue.keys`), so a paragraph that changed is quietly ignored."""
    k = keys(bd)
    remove, names = set(edits.get("remove") or ()), edits.get("names") or {}
    starts = []
    for hd in kept:
        key = k["p"].get(bd.para[hd["start"]])
        if key not in remove:
            starts.append({"start": hd["start"], "key": key, "label": re.sub(r"\s+", " ", hd["text"]), "source": "auto"})
    have = {bd.para[st["start"]] for st in starts}
    for key in edits.get("add") or ():
        pid = k["p_rev"].get(key)
        if pid is None or pid in have:
            continue
        s, e = bd.para_bounds[pid]
        starts.append({"start": s, "key": key, "label": re.sub(r"\s+", " ", bd.span_text(s, min(e, s + 12))).strip(), "source": "yours"})
        have.add(pid)
    for st in starts:
        if names.get(st["key"]):
            st["label"] = names[st["key"]]
    return sorted(starts, key=lambda st: st["start"])


def book_segments(view, b, cfg):
    """`segments` of book b in a view, with the chapter edits you made for that book applied."""
    return segments(view.bd[b], cfg, view.lib.ann["books"].get(b, {}).get("chapters"))


OPENING_KEY = "opening"   # chapter_key_of's key for the "Opening" segment (before any chapter start); never collides
                          # with a real paragraph key, which always contains "#" (see dialogue.keys)


def chapter_key_of(view, b, pid):
    """The key of paragraph pid's chapter — its start paragraph's key (`dialogue.keys`), or `OPENING_KEY` for the
    stretch before the first chapter start. For `chapter_narrators` (assigning a narrator to a whole chapter): keyed
    the same way as chapter edits, so it survives a re-export that shifts paragraph numbers. Chapters are always
    resolved with `{"mode": "chapters"}` (your chapter edits applied) regardless of what the current page is
    displaying, since "chapter" should mean one stable thing, not follow the Measure over slices/chapters toggle."""
    bd = view.bd[b]
    sig = ann_sig(view.lib.ann["books"].get(b, {}).get("chapters"))
    return bd.kept("chapter keys", entries=1).get(sig, lambda: _chapter_keys(view, b)).get(pid, OPENING_KEY)


def _chapter_keys(view, b):
    """The work of `chapter_key_of`: paragraph -> its chapter's key, for every paragraph of book b."""
    bd = view.bd[b]
    segs, _ = book_segments(view, b, {"mode": "chapters"})
    pkeys = keys(bd)["p"]
    mapping = {}
    for sg in segs:
        ckey = pkeys.get(bd.para[sg["head"]], OPENING_KEY) if sg["head"] is not None else OPENING_KEY
        for p in range(bd.para[sg["start"]], bd.para[sg["end"]] + 1):
            mapping[p] = ckey
    return mapping


def edit_chapters(lib, b, action, pid=None, name=None):
    """Change the chapters of book b (`chapters` in your corrections), returning True if any edits remain.
    `action`: "add" makes paragraph `pid` a chapter start (or takes back a removal of it), "remove" drops the chapter starting there
    (or an addition of yours), "rename" gives the chapter starting there a title (blank: back to the found one), "reset" clears all
    of them. Paragraphs are remembered by their opening words, so the edits survive a re-export that shifts token numbers."""
    bd = lib.book(b)
    if action not in ("add", "remove", "rename", "reset"):
        raise ValueError("Unknown action.")
    with lib.lock:
        ab = lib.ann_book(b)
        if action == "reset":
            ab.pop("chapters", None)
        else:
            key = keys(bd)["p"].get(pid)
            if key is None:
                raise ValueError("That paragraph isn't in the book.")
            ed = ab.setdefault("chapters", {"add": [], "remove": [], "names": {}})
            for k in ("add", "remove", "names"):
                ed.setdefault(k, [] if k != "names" else {})
            if action == "add":
                if key in ed["remove"]:
                    ed["remove"].remove(key)
                elif key not in ed["add"]:
                    ed["add"].append(key)
            elif action == "remove":
                if key in ed["add"]:
                    ed["add"].remove(key)
                elif key not in ed["remove"]:
                    ed["remove"].append(key)
                ed["names"].pop(key, None)
            elif name and name.strip():
                ed["names"][key] = name.strip()
            else:
                ed["names"].pop(key, None)
            if not (ed["add"] or ed["remove"] or ed["names"]):
                ab.pop("chapters", None)
        lib.save_ann()
        return "chapters" in ab


def all_segments(view, cfg):
    """Segments of every book in the view, in book order, each with its book, title, index and position (% into the book)
    -> (segments, {book: info}). With `cfg["scope"] == "corpus"` and equal slices, `cfg["n"]` is the slice count across the
    *whole selection* rather than per book (not when slices are cut by words): each book's share of it is proportional to its words (rounded, at least one),
    so a short book isn't given the same resolution as a long one. Chapters are always found per book regardless of scope;
    there, corpus scope only changes how a chart joins the segments (see `arcChart` in narrative.js), not how they're found."""
    cfg = cfg if isinstance(cfg, dict) else {}
    out, info = [], {}
    corpus = cfg.get("scope") == "corpus" and cfg.get("mode", "slices") == "slices" and cfg.get("slice_by") != "words" and len(view.books) > 1
    n_per_book = {}
    if corpus:
        n_total = _setting(cfg, "n", 10, 2, 400)
        words = {b: view.bd[b].n_words for b in view.books}
        grand = sum(words.values()) or 1
        n_per_book = {b: max(1, round(n_total * words[b] / grand)) for b in view.books}
    for b in view.books:
        segs, inf = book_segments(view, b, {**cfg, "n": n_per_book[b]} if corpus else cfg)
        info[b] = inf
        for k, sg in enumerate(segs):
            out.append({"book": b, "title": view.title(b), "index": k, **sg,
                        "pos": round(100 * sg["start"] / max(1, view.bd[b].n_tokens), 1)})
    return out, info


def combinable(cfg):
    """Whether the books can be put together slice by slice ("Books combined"): only when each is cut into the same number of
    equal slices, so that slice k of n is the same stretch of every book (not chapters, nor slices of so many words)."""
    cfg = cfg if isinstance(cfg, dict) else {}
    return cfg.get("mode", "slices") == "slices" and cfg.get("slice_by") != "words"


def books_combined(result, cfg, each=False):
    """An arc answer (`{segments, series, info}`, cut book by book) put together across the books, slice by slice (the Timeline
    "Books combined", AD-45): segment k is slice k of every book; a series' value there is the mean of the books' own values (every
    book weighs the same; a book where the series has no value, None, is left out of its mean), its count the sum. With `each`, every
    series also carries `each`: [{book, title, values}], each book's own line. When the books can't be lined up (`combinable` is False)
    the answer is returned as it is, with `info["combined"] = None`; otherwise `info["combined"] = {n, books}`."""
    if not combinable(cfg):
        return {**result, "info": {**result.get("info", {}), "combined": None}}
    segs = result["segments"]
    books = list(dict.fromkeys(sg["book"] for sg in segs))
    n = max((sg["index"] for sg in segs), default=-1) + 1
    at = {(sg["book"], sg["index"]): k for k, sg in enumerate(segs)}
    titles = {sg["book"]: sg["title"] for sg in segs}
    out = [{"book": "", "title": "All selected books", "index": i, "label": f"{i + 1}/{n}", "pos": round(100 * i / n, 1) if n else 0,
            "words": sum(segs[at[b, i]]["words"] for b in books if (b, i) in at)} for i in range(n)]
    series = []
    for s in result["series"]:
        values, counts, own = [], [], {b: [] for b in books}
        for i in range(n):
            vs = [(s["values"][at[b, i]], s["counts"][at[b, i]] if s.get("counts") else None) for b in books if (b, i) in at]
            have = [(v, c) for v, c in vs if v is not None]
            values.append(sum(v for v, _ in have) / len(have) if have else None)
            counts.append(sum(c or 0 for _, c in have) if have else None)
            for b in books:
                own[b].append(s["values"][at[b, i]] if (b, i) in at else None)
        series.append({**s, "values": values, "counts": counts,
                       **({"each": [{"book": b, "title": titles[b], "values": own[b]} for b in books if any(v is not None for v in own[b])]} if each else {})})
    return {**result, "segments": out, "series": series, "info": {**result.get("info", {}), "combined": {"n": n, "books": books}}}


def timeline(result, cfg, each=False):
    """An arc answer as the Timeline asks: put together across the books (`books_combined`) when `cfg["scope"]` is "combined",
    else as it is. Every arc route (arcs, topics, sentiment, lexicons) answers through this."""
    return books_combined(result, cfg, each) if isinstance(cfg, dict) and cfg.get("scope") == "combined" else result


# ---------- arcs ----------
def segment_index(segs):
    """book -> sorted list of (start token, segment index), for `locate`."""
    idx = defaultdict(list)
    for k, sg in enumerate(segs):
        idx[sg["book"]].append((sg["start"], k))
    return idx


def locate(idx, b, tok):
    """The segment index holding token tok of book b (binary search over `segment_index`), or None."""
    lst = idx[b]
    lo, hi = 0, len(lst) - 1
    ans = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if lst[mid][0] <= tok:
            ans = lst[mid][1]
            lo = mid + 1
        else:
            hi = mid - 1
    return ans


def arcs(view, cfg, kind, ids=None, cats=None):
    """Something counted per segment. kind "entities" (mentions of the units in `ids`), "events" (tokens
    BookNLP marks as events), "supersenses" (the categories `cats`, else the five most common verb ones) or
    "dialogue" (share of words in quotes). Values are per 1,000 words (a percentage for dialogue); `counts` are the raw numbers.
    An entity's value and count are None in the segments of books it isn't in (a gap in the chart, not a 0: it isn't counted there).
    -> {segments, series: [{name, values, counts}], info}"""
    segs, info = all_segments(view, cfg)
    idx = segment_index(segs)
    series = []
    per1k = lambda counts: [1000 * counts[k] / sg["words"] if sg["words"] else 0 for k, sg in enumerate(segs)]
    if kind == "entities":
        for uid in ids or []:
            u = view.units.get(uid)
            if not u:
                continue
            c = Counter()
            for b, co in u.members:
                bd = view.bd[b]
                for mi in bd.groups[co].mentions:
                    k = locate(idx, b, bd.mentions[mi][1])
                    if k is not None:
                        c[k] += 1
            mine = [sg["book"] in u.books for sg in segs]                  # its own books' segments; elsewhere it isn't counted
            series.append({"id": uid, "name": u.name, "type": u.type, "books": sorted(u.books),
                           "values": [v if m else None for v, m in zip(per1k(c), mine)], "counts": [c[k] if mine[k] else None for k in range(len(segs))]})
    elif kind == "events":
        c = Counter()
        for b in view.books:
            for i, e in enumerate(view.bd[b].event):
                if e:
                    k = locate(idx, b, i)
                    if k is not None:
                        c[k] += 1
        series.append({"name": "Events", "values": per1k(c), "counts": [c[k] for k in range(len(segs))]})
    elif kind == "supersenses":
        per = defaultdict(Counter)
        totals = Counter()
        for b in view.books:
            bd = view.bd[b]
            prev = None
            for i in sorted(bd.ss):
                cat = bd.ss[i]
                if prev is not None and prev[0] == i - 1 and prev[1] == cat:
                    prev = (i, cat)
                    continue
                prev = (i, cat)
                k = locate(idx, b, i)
                if k is not None:
                    per[cat][k] += 1
                    totals[cat] += 1
        chosen = cats or [c for c, _ in totals.most_common() if c.startswith("verb.")][:5]
        for cat in chosen:
            series.append({"name": cat, "values": per1k(per[cat]), "counts": [per[cat][k] for k in range(len(segs))]})
        info["available"] = [{"item": c, "n": n} for c, n in totals.most_common()]
    elif kind == "dialogue":
        c = Counter()
        for b in view.books:
            ci = cindex(view.bd[b])
            for i, (w, q) in enumerate(zip(ci["isword"], ci["in_quote"])):
                if w and q:
                    k = locate(idx, b, i)
                    if k is not None:
                        c[k] += 1
        series.append({"name": "Dialogue (% of words)", "values": [100 * c[k] / sg["words"] if sg["words"] else 0 for k, sg in enumerate(segs)],
                       "counts": [c[k] for k in range(len(segs))]})
    return {"segments": segs, "series": series, "info": info}


# ---------- style ----------
def style_metrics(bd, s, e):
    """Style figures for tokens s..e of a book (see NOTES["style"]): sentence and word length, MATTR, hapaxes, lexical
    density, dependency distance and tree depth, subordinate clauses, passives, questions, dialogue share, Flesch scores and a
    parts-of-speech profile. Only sentences that start inside the span count as sentences. None if it has no words.
    Worked out once per span and kept on the book (a page asks for every book and segment each time it is drawn)."""
    return bd.kept("style", entries=500).get((s, e), lambda: _style_metrics(bd, s, e))


def _style_metrics(bd, s, e):
    """The work of `style_metrics`."""
    iw = cindex(bd)["isword"]
    iq = cindex(bd)["in_quote"]
    words = [i for i in range(s, e + 1) if iw[i]]
    nw = len(words)
    if not nw:
        return None
    sents = sorted({bd.sent[i] for i in range(s, e + 1) if bd.sent_bounds[bd.sent[i]][0] >= s})
    lens, depths, subs = [], [], []
    questions = 0
    for sid in sents:
        a, b = bd.sent_bounds[sid]
        sw = [i for i in range(a, b + 1) if iw[i]]
        if not sw:
            continue
        lens.append(len(sw))
        subs.append(sum(1 for i in range(a, b + 1) if bd.dep[i] in SUBORD))
        if any(bd.word[i] == "?" for i in range(a, b + 1)):
            questions += 1
        best = 0
        for i in range(a, b + 1):
            d, x = 0, i
            while bd.head[x] != x and d < 60:
                x = bd.head[x]
                d += 1
            best = max(best, d)
        depths.append(best)
    lw = [bd.word[i].lower() for i in words]
    wc = Counter(lw)
    dist = [abs(i - bd.head[i]) for i in words if bd.head[i] != i]
    syl = sum(guess_syllables(bd.word[i]) for i in words)
    ns = len(lens) or 1
    mean_len = sum(lens) / ns
    sd_len = math.sqrt(sum((x - mean_len) ** 2 for x in lens) / ns) if lens else 0
    m, ok = mattr(lw)
    pos = Counter(bd.pos[i] for i in words)
    return {
        "words": nw, "sentences": len(lens), "sent_len": mean_len, "sent_sd": sd_len,
        "sent_median": sorted(lens)[len(lens) // 2] if lens else 0,
        "word_len": sum(len(bd.word[i]) for i in words) / nw,
        "mattr": m, "mattr_ok": ok, "hapax": 100 * sum(1 for c in wc.values() if c == 1) / nw,
        "density": 100 * sum(pos[p] for p in CONTENT) / nw,
        "dep_dist": sum(dist) / len(dist) if dist else 0, "depth": sum(depths) / len(depths) if depths else 0,
        "subord": sum(subs) / ns, "passive": 1000 * sum(1 for i in range(s, e + 1) if bd.dep[i] == "nsubjpass") / nw,
        "questions": 100 * questions / ns, "dialogue": 100 * sum(1 for i in words if iq[i]) / nw,
        "flesch": 206.835 - 1.015 * mean_len - 84.6 * syl / nw, "fk_grade": 0.39 * mean_len + 11.8 * syl / nw - 15.59,
        "pos": {p: 100 * pos.get(p, 0) / nw for p in ("NOUN", "PROPN", "VERB", "ADJ", "ADV", "PRON", "ADP", "DET", "CCONJ", "SCONJ", "AUX")},
    }


def style(view, cfg, by="book"):
    """Style figures per book, or per segment (`by="segment"`) -> {rows}."""
    rows = []
    if by == "segment":
        segs, info = all_segments(view, cfg)
        for sg in segs:
            m = style_metrics(view.bd[sg["book"]], sg["start"], sg["end"])
            if m:
                rows.append({"book": sg["book"], "title": sg["title"], "label": sg["label"], "index": sg["index"], **m})
        return {"rows": rows, "info": info}
    for b in view.books:
        bd = view.bd[b]
        m = style_metrics(bd, 0, bd.n_tokens - 1)
        if m:
            rows.append({"book": b, "title": view.title(b), "label": view.title(b), **m})
    return {"rows": rows}


# ---------- stylometry ----------
def stylometry(view, cfg, units="books", mfw=100, culling=0, measure="cosine", linkage="average", scope="all",
               exclude_pronouns=False):
    """Burrows-style stylometry (see NOTES["stylo"]): distances between texts (whole books or segments) from the
    z-scores of their most frequent words, a cluster tree, a principal-component map and each text's nearest neighbours.
    Returns {"error": …} when there are too few texts or words to compare."""
    import numpy as np

    mfw = max(2, int(mfw))

    texts = []
    if units == "segments":
        segs, _ = all_segments(view, cfg)
        spans = [(sg["book"], sg["start"], sg["end"], f"{sg['title']}: {sg['label']}") for sg in segs]
    else:
        spans = [(b, 0, view.bd[b].n_tokens - 1, view.title(b)) for b in view.books]
    for b, s, e, label in spans:
        bd = view.bd[b]
        ci = cindex(bd)
        c = Counter()
        for i in range(s, e + 1):
            if not ci["isword"][i]:
                continue
            if scope == "narration" and ci["in_quote"][i] or scope == "dialogue" and not ci["in_quote"][i]:
                continue
            w = bd.word[i].lower()
            if exclude_pronouns and w in PRONOUNS:
                continue
            c[w] += 1
        n = sum(c.values())
        if n:
            texts.append({"book": b, "label": label, "counts": c, "words": n})
    if len(texts) < 3:
        return {"error": "Stylometry needs at least three texts. Select more books, or compare chapters or slices."}
    if len(texts) > MAX_TEXTS:
        return {"error": f"Stylometry compares at most {MAX_TEXTS} texts; there are {len(texts)}. Compare whole books, or use fewer slices."}
    total = Counter()
    for t in texts:
        total.update(t["counts"])
    need = math.ceil(culling / 100 * len(texts))
    vocab = list(islice((w for w, _ in total.most_common() if sum(1 for t in texts if w in t["counts"]) >= need), mfw))     # the most frequent words found in enough texts
    X = np.array([[t["counts"].get(w, 0) / t["words"] for w in vocab] for t in texts])
    sd = X.std(axis=0)
    keep = sd > 1e-12                               # a word every text uses equally often says nothing (rounding must not make it count)
    X, vocab = X[:, keep], [w for w, k in zip(vocab, keep) if k]
    if len(vocab) < 2:
        return {"error": "Too few words are used differently in these texts to compare them. Raise the number of words or lower the culling."}
    Z = (X - X.mean(axis=0)) / X.std(axis=0)
    n = len(texts)
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            a, b = Z[i], Z[j]
            if measure == "classic":
                d = float(np.mean(np.abs(a - b)))
            elif measure == "euclidean":
                d = float(np.sqrt(np.sum((a - b) ** 2)))
            else:
                na, nb = np.linalg.norm(a), np.linalg.norm(b)
                d = float(1 - a @ b / (na * nb)) if na and nb else 1.0
            D[i, j] = D[j, i] = d
    tree = cluster(D.tolist(), linkage)
    # PCA
    try:
        U, Sv, Vt = np.linalg.svd(Z - Z.mean(axis=0), full_matrices=False)
    except np.linalg.LinAlgError:
        return {"error": "These texts are too alike to place on a map. Choose more different books, or compare chapters or slices."}
    coords = U[:, :2] * Sv[:2]
    var = (Sv ** 2) / max(1e-12, (Sv ** 2).sum())
    loads = []
    for k in range(min(2, Vt.shape[0])):
        order = np.argsort(Vt[k])
        loads.append({"neg": [vocab[i] for i in order[:8]], "pos": [vocab[i] for i in order[::-1][:8]]})
    nearest = []
    for i in range(n):
        o = [j for j in np.argsort(D[i]) if j != i][:3]
        nearest.append({"label": texts[i]["label"], "nearest": [{"label": texts[j]["label"], "d": float(D[i, j])} for j in o]})
    meta = [view.lib.meta(t["book"]) for t in texts]
    return {"texts": [{"label": t["label"], "book": t["book"], "words": t["words"], "author": m["author"], "series": m["series"],
                       "year": m["year"], "x": float(coords[i, 0]) if coords.shape[1] > 0 else 0.0,
                       "y": float(coords[i, 1]) if coords.shape[1] > 1 else 0.0} for i, (t, m) in enumerate(zip(texts, meta))],
            "matrix": D.round(4).tolist(), "tree": tree, "mfw": len(vocab), "words": vocab[:50],
            "variance": [float(v) for v in var[:2]], "loadings": loads, "nearest": nearest}


def cluster(D, linkage):
    """Agglomerative clustering of a distance matrix (Lance–Williams updates) -> a nested tree of
    {"leaf", "size", "height"} and {"children": [a, b], "size", "height"} nodes. linkage: average, complete or ward.
    Cubic in the number of items; stylometry allows at most MAX_TEXTS."""
    n = len(D)
    clusters = {i: {"leaf": i, "size": 1, "height": 0.0} for i in range(n)}
    dist = {(i, j): D[i][j] for i in range(n) for j in range(i + 1, n)}
    nxt = n
    while len(clusters) > 1:
        (a, b), d = min(dist.items(), key=lambda kv: kv[1])
        ca, cb = clusters.pop(a), clusters.pop(b)
        new = {"children": [ca, cb], "size": ca["size"] + cb["size"], "height": d}
        for k in list(clusters):
            dak = dist.pop((min(a, k), max(a, k)))
            dbk = dist.pop((min(b, k), max(b, k)))
            na, nb, nk = ca["size"], cb["size"], clusters[k]["size"]
            if linkage == "complete":
                nd = max(dak, dbk)
            elif linkage == "ward":
                nd = math.sqrt(max(0.0, ((na + nk) * dak ** 2 + (nb + nk) * dbk ** 2 - nk * d ** 2) / (na + nb + nk)))
            else:
                nd = (na * dak + nb * dbk) / (na + nb)
            dist[(min(k, nxt), max(k, nxt))] = nd
        dist.pop((a, b), None)
        clusters[nxt] = new
        nxt += 1
    return next(iter(clusters.values()))


# ---------- sentiment and lexicons ----------
def vader_available():
    """Whether the vaderSentiment package is installed."""
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # noqa: F401
        return True
    except ImportError:
        return False


def sentence_scores(bd):
    """VADER compound score (−1…+1) of each sentence of a book, cached on the book: sentence id -> score."""
    def score():
        """Score every sentence (VADER is imported only now: it is optional)."""
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        sia = SentimentIntensityAnalyzer()
        return {sid: sia.polarity_scores(bd.span_text(a, b))["compound"] for sid, (a, b) in bd.sent_bounds.items()}
    return bd.kept("sentiment", entries=1).get("scores", score)


def sentiment(view, cfg, ids=None):
    """Mean sentence sentiment per segment for the whole text and, for each unit in `ids`, for the sentences that mention it -> {segments, series, books, info}."""
    segs, info = all_segments(view, cfg)
    idx = segment_index(segs)
    whole = [[] for _ in segs]
    around = {uid: [[] for _ in segs] for uid in (ids or []) if uid in view.units}
    books = []
    for b in view.books:
        bd = view.bd[b]
        sc = sentence_scores(bd)
        for sid, v in sc.items():
            k = locate(idx, b, bd.sent_bounds[sid][0])
            if k is not None:
                whole[k].append(v)
        vals = list(sc.values())
        books.append({"book": b, "title": view.title(b), "sentences": len(vals), "mean": sum(vals) / len(vals) if vals else 0,
                      "positive": 100 * sum(v >= 0.05 for v in vals) / len(vals) if vals else 0,
                      "negative": 100 * sum(v <= -0.05 for v in vals) / len(vals) if vals else 0})
        for uid in around:
            u = view.units[uid]
            sids = set()
            for bb, co in u.members:
                if bb == b:
                    sids |= bd.group_sents.get(co, set())
            for sid in sids:
                k = locate(idx, b, bd.sent_bounds[sid][0])
                if k is not None:
                    around[uid][k].append(sc[sid])
    mean = lambda xs: sum(xs) / len(xs) if xs else None
    series = [{"name": "Whole text", "values": [mean(x) for x in whole], "counts": [len(x) for x in whole]}]
    for uid, lst in around.items():
        series.append({"id": uid, "name": f"Around {view.units[uid].name}", "values": [mean(x) for x in lst], "counts": [len(x) for x in lst]})
    return {"segments": segs, "series": series, "books": books, "info": info}


def lexicon_arc(view, cfg, lex, cats=None):
    """Words per 1,000 in each category of a lexicon (`lexicons.py`) per segment (a word counts by its form, else by its lemma);
    `cats` limits it to some categories -> {segments, series, info}."""
    segs, info = all_segments(view, cfg)
    idx = segment_index(segs)
    cats = cats or sorted(lex["cats"])
    word_cats = defaultdict(list)
    for c in cats:
        for w in lex["cats"].get(c, []):
            word_cats[w].append(c)
    per = defaultdict(Counter)
    for b in view.books:
        bd = view.bd[b]
        iw = cindex(bd)["isword"]
        for i in range(bd.n_tokens):
            if not iw[i]:
                continue
            w = bd.word[i].lower()
            hits = word_cats.get(w) or word_cats.get(bd.lemma[i].lower())
            if hits:
                k = locate(idx, b, i)
                if k is not None:
                    for c in hits:
                        per[c][k] += 1
    series = [{"name": c, "values": [1000 * per[c][k] / sg["words"] if sg["words"] else 0 for k, sg in enumerate(segs)],
               "counts": [per[c][k] for k in range(len(segs))]} for c in cats]
    return {"segments": segs, "series": series, "info": info}
