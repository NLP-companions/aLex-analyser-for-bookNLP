"""The help drawer's texts (static/js/help-*.js, registered with `addHelp` in help.js) keep up with the app: every help file registers
one page, section ids are unique within a page, and the Statistics help (help-stats.js) has a section per variable kind and an entry per
option the server knows (measures, mention kinds, attributes, relations, sentiment, style and sound figures, cases, samples,
coefficients, corrections, splits). A new option without a help entry fails here."""
from __future__ import annotations

import re
from pathlib import Path

from alex.core import cases, corpus, described, dialogue, network, layers, prosody, stats, statstab, variables
from alex.core.bookdata import RELATIONS
from alex.core.view import PROPS, TYPES

JS = Path(__file__).resolve().parent.parent / "alex" / "static" / "js"
HELP = (JS / "help-stats.js").read_text(encoding="utf-8")
SECTIONS = set(re.findall(r'\{ id: "(\w+)"', HELP))
ITEMS = set(re.findall(r'\["([^"]*)", "', HELP))          # the key of each [key, name, explanation] entry


def items(name):
    """The keys of the [key, name, explanation] entries of one help file."""
    return set(re.findall(r'\["([^"]*)", "', (JS / name).read_text(encoding="utf-8")))


def sections(text):
    """The section ids of a help file, in order."""
    return re.findall(r'\{ id: "([\w-]+)"', text)


def test_every_help_file_registers_one_page_with_unique_sections():
    files = sorted(JS.glob("help-*.js"))
    assert {"help-general.js", "help-stats.js"} <= {f.name for f in files}
    pages = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        pages += re.findall(r'^addHelp\("(\w+)"', text, re.M)
        ids = sections(text)
        assert ids and len(ids) == len(set(ids)), f"{f.name}: section ids must be unique"
    assert len(pages) == len(files) == len(set(pages)), "one addHelp per file, one file per page"
    html = (JS.parent / "index.html").read_text(encoding="utf-8")
    assert html.index("js/help.js") < min(html.index(f"js/{f.name}") for f in files), "help.js loads before the texts"


def test_every_variable_kind_has_a_section():
    assert set(variables.KINDS) - SECTIONS == set()
    assert {"cases", "pieces", "samples", "measures", "bulk", "options", "results"} <= SECTIONS


def test_every_option_has_an_entry():
    keys = [*variables.MEASURES, *variables.PROPS, *variables.PARTICIPANT_ATTRS, *variables.PIECE_ATTRS, *variables.SPOKEN_UNITS,
            *layers.RELATIONS, *layers.SENTIMENT, *layers.STYLE, *layers.SPEECH_TYPES, *cases.KINDS, *cases.PIECES, *cases.SAMPLES,
            *stats.CORRELATIONS, *stats.CORRECTIONS]
    assert [k for k in keys if k not in ITEMS] == []


def test_every_word_choice_section_and_figure_is_explained():
    """A section is an entry; its figures (adj_verb, motion, ADJ, dynamic…) are named in its text (the per 1,000 words sections share the
    categories of the verbs and nouns ones, which their text points to)."""
    from alex.core import wordchoice
    text = {k: t for k, t in re.findall(r'\["(\w+)", "[^"]*", "([^"]*)"\]', HELP)}
    assert [k for k, _, _ in wordchoice.SECTIONS if k not in text] == []
    for key, _, figures in wordchoice.SECTIONS:
        for f in figures:
            name = f.partition(":")[2].split(".")[-1]
            name = name.upper() if key == "parts" else name
            where = {"ssverbs": "verbs", "ssnouns": "nouns"}.get(key, key)
            assert re.search(rf"\b{re.escape(name)}\b", text[where]), f"{f} is not named in the {where} entry"
    assert "wordchoice_all" in ITEMS


def test_every_sound_figure_is_explained():
    """A sound figure is an entry of its own or named in its family's entry (cad_planus in "Cadence … (% of phrase ends)")."""
    assert [k for k in prosody.FIGURES if k not in ITEMS and not re.search(rf"\b{k}\b", HELP)] == []


def test_every_split_is_named():
    split = next(t for k, _, t in re.findall(r'\["(\w+)", "([^"]*)", "([^"]*)"\]', HELP) if k == "split")
    assert [v for k, v in statstab.SPLITS.items() if k != "none" and v.lower() not in split.lower()] == []


def test_the_general_help_explains_every_keyness_setting():
    keys = items("help-general.js")
    assert [k for k in [*stats.MEASURES, *stats.TESTS, "min_freq", "alpha", "bonferroni", "show_all"] if k not in keys] == []


def test_the_entity_help_explains_every_list_type_and_form():
    text = (JS / "help-entities.js").read_text(encoding="utf-8")
    types = next(n for k, n in re.findall(r'\["(\w+)", "([^"]*)"', text) if k == "types")
    assert [t for t in TYPES if t not in types] == [] and {"NARR", "GENDER"} <= items("help-entities.js")
    assert [k for k in [*RELATIONS, *PROPS] if k not in items("help-entity.js")] == []


def area_pages(tab):
    """The sub-pages of a page as the areas list them (areas.js): the <sub> of every `#/<tab>/<sub>` address."""
    return re.findall(rf'\["#/{tab}/(\w+)"', (JS / "areas.js").read_text(encoding="utf-8"))


def subtabs(script, var="tabs"):
    """The sub-tab keys a page script lists as [key, label] pairs in `const <var> = [...]`."""
    text = (JS / script).read_text(encoding="utf-8")
    block = re.search(rf"const {var} = \[(.*?)\];", text, re.S).group(1)
    return re.findall(r'\["(\w+)", "', block)


def test_the_dialogue_help_has_every_tab_addressee_method_and_sentence_type():
    ids = set(sections((JS / "help-dialogue.js").read_text(encoding="utf-8")))
    assert set(area_pages("dialogue")) - ids == set()
    assert [k for k in [*dialogue.ADDR_METHODS, *dialogue.SENTENCE_TYPES] if k not in items("help-dialogue.js")] == []


def test_the_corpus_help_has_every_tool_attribute_sort_and_measure():
    ids = set(sections((JS / "help-corpus.js").read_text(encoding="utf-8")))
    assert set(area_pages("corpus")) - ids == set()
    keys = items("help-corpus.js")
    assert [k for k in [*corpus.ATTRS, *corpus.SORT_BY, *corpus.COLL_MEASURES, "match", "case", "regex", "wildcards", "skip_punct"] if k not in keys] == []


def js_keys(script, var):
    """The keys of a [key, label…] list a page script declares as `const <var> = [...]`."""
    return subtabs(script, var)


def test_the_arcs_and_sound_help_have_every_tab_style_figure_and_run_kind():
    nar = (JS / "help-narrative.js").read_text(encoding="utf-8")
    assert set(area_pages("narrative")) - set(sections(nar)) == set()
    assert [k for k in js_keys("narrative.js", "STYLE_COLS") if k not in items("help-narrative.js") and not re.search(rf"\b{k}\b", nar)] == []
    snd = (JS / "help-sound.js").read_text(encoding="utf-8")
    assert set(js_keys("sound.js", "SND_TABS")) - set(sections(snd)) == set()
    assert [k for k in prosody.RUNS if k not in items("help-sound.js")] == []


def test_the_topics_help_explains_every_fit_setting_and_comparison():
    from alex.core.topics.model import DEFAULTS
    ids = set(sections((JS / "help-topics.js").read_text(encoding="utf-8")))
    assert {"home", "model", "topic", *subtabs("topic-compare.js")} <= ids
    keys = items("help-topics.js")
    assert [k for k in DEFAULTS if k not in keys and k not in ("chunk_words", "paras", "seg", "alpha", "beta", "method")] == []
    assert {"nmf", "lda", *subtabs("topic-compare.js", "kinds")} <= keys


def test_over_described_compare_and_network_help_explain_every_option():
    over = set(sections((JS / "help-over.js").read_text(encoding="utf-8")))
    assert {"single", *[k for k in subtabs("overbook.js", "OVER_SUBS") if k]} <= over
    assert {*subtabs("overbook.js", "OVER_VIEWS"), *subtabs("overbook.js", "OVER_ORDERS"), *subtabs("overbook.js", "OVER_CATS")} <= items("help-over.js")
    assert {*described.KINDS, *described.SPLITS, *described.VOICES} <= items("help-described.js")
    net = (JS / "network.js").read_text(encoding="utf-8")
    labels = re.search(r"const MEASURE_LABELS = \{(.*?)\};", net, re.S).group(1)
    keys = items("help-network.js")
    assert [k for k in [*network.KINDS, *re.findall(r"(\w+): \"", labels)] if k not in keys and not re.search(rf"\b{k}\b", (JS / "help-network.js").read_text(encoding="utf-8"))] == []
    assert {"start", "overview", "words"} <= set(sections((JS / "help-compare.js").read_text(encoding="utf-8")))


def test_every_page_has_its_help():
    """Every page of an area (the first part of its address in areas.js), every page of the [...] menu (their `data-tab`), the
    chapter editor and an entity's profile have a help file."""
    html = (JS.parent / "index.html").read_text(encoding="utf-8")
    areas = re.search(r"const AREAS = \[(.*?)\n\];", (JS / "areas.js").read_text(encoding="utf-8"), re.S).group(1)
    pages = set(re.findall(r'\["#/(\w+)', areas)) | set(re.findall(r'data-tab="(\w+)"', html)) | {"chapters", "entity"}
    assert {"entities", "compare", "corpus", "topics", "narrative", "sound", "over", "stats", "read", "links"} <= pages
    registered = {p for f in JS.glob("help-*.js") for p in re.findall(r'^addHelp\("(\w+)"', f.read_text(encoding="utf-8"), re.M)}
    assert pages - registered == set()
    assert [p for p in registered - {"general"} if f'js/help-{p}.js' not in html] == []


def test_the_settings_and_read_help_explain_every_section_and_layer():
    settings = (JS / "settings.js").read_text(encoding="utf-8")
    assert {"appearance", "entities", "words", "sound", "folders"} <= set(sections((JS / "help-settings.js").read_text(encoding="utf-8")))
    reader = (JS / "reader.js").read_text(encoding="utf-8")
    layers = set(re.findall(r'\["(\w+)", "[^"]+"\]', re.search(r'"Show", h\("div", \{ class: "chips" \}, (.*?)\.map', reader).group(1)))
    assert layers and layers <= items("help-read.js")
    assert "settingRow" in settings
