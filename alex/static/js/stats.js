"use strict";
/* ---------- Statistics ---------- */
/* Correlations and descriptive statistics of variables measured over cases (core/statstab.py, POST /api/stats). The setup panel
   chooses the cases (text pieces or participants) and one or two lists of variables; Run computes, and the results have three views:
   Correlations (a heatmap you can download, and the pairs as a table), Descriptives and Data (the raw values, one row per case). */

const SV_MAX = 30;                                     // variables in one list, as in core/statstab.py
const SV_PIECES = [["slice", "Equal slices"], ["sentence", "Sentences"], ["chapter", "Chapters"], ["book", "Books"]];
const SV_SLICE_BY = [["count", "Number per book"], ["words", "Words per slice"]];
const SV_SAMPLES = [["speech", "What they say"], ["speech_narration", "What they say and narrate"], ["sentences", "Sentences mentioning them"],
  ["findings", "What is said about them (Described as)"]];
const SV_MEASURES = [["per1k", "per 1,000 words"], ["count", "count"], ["present", "present (0/1)"]];
const SV_QUOTE_SHARE = ["pct", "% of quotes"];       // a measure of quotes alone: a speech sentence type, or a speaker's quotes
const SV_PART_ATTRS = [["in", "Is one of (0/1)"], ["mentions", "Mentions"], ["speech", "Words spoken"], ["quotes", "Quotes"], ["books", "Books"]];
const SV_PIECE_ATTRS = [["index", "Number in its book"], ["position", "Position in its book (%)"], ["length", "Length (words)"]];
const SV_SPLITS = [["none", "No split"], ["gender", "Gender"], ["tag", "Tag"], ["group", "Saved group"], ["book", "Book"]];
const SV_CORRECTIONS = [["none", "None"], ["bonferroni", "Bonferroni"], ["holm", "Holm"]];
const SV_KIND_LABEL = { query: "Words", mentions: "Mentions", spoken: "Speech", attribute: "Attribute", supersense: "Supersense", relation: "Relation", sentiment: "Sentiment",
  lexicon: "Lexicon", speech: "Speech type", style: "Style", wordchoice: "Word choice", sound: "Sound", topic: "Topic" };
const SV_KIND_SHORT = { query: "WORDS", mentions: "MENT", spoken: "SPEECH", attribute: "ATTR", supersense: "SS", relation: "REL", sentiment: "SENT", lexicon: "LEX",
  speech: "TYPE", style: "STYLE", wordchoice: "CHOICE", sound: "SOUND", topic: "TOPIC" };                     // the short label on a variable's chip
const SV_LAYERS = [["supersense", "Supersense"], ["relation", "Relation (actions, modifiers…)"], ["sentiment", "Sentiment"],
  ["lexicon", "Lexicon category (emotion…)"], ["speech", "Speech sentence type (questions…)"], ["style", "Style figure"],
  ["wordchoice", "Word choice (parts of speech, verb types…)"],
  ["sound", "Sound and rhythm (stress, cadences, alliteration…)"], ["topic", "Topic (from a topic model)"]];
const SV_TYPES = [["question", "Questions"], ["exclaim", "Exclamations"], ["statement", "Statements"]];   // the sentence types of quotes
const SV_COUNTED = new Set(["query", "mentions", "spoken", "supersense", "relation", "lexicon", "speech"]);     // kinds that count something, so take a measure
let svOptions = { supersenses: [], relations: {}, sentiment: {}, style: {}, wordchoice: [], sound: {}, phonemes: [], lexicons: [], topics: [], vader: true, sound_ready: true };   // from /api/stats/options

/** The entity type a spec stands for, if it has one: a unit's, a group's or tag's when all its entities share one, a type's, or GENDER. */
function specType(t) {
  if (!t) return null;
  if (t.kind === "unit") return t.type || null;
  if (t.kind === "gender") return "GENDER";
  if (t.kind === "group") { const ts = new Set((t.members || []).map(m => m.type)); return ts.size === 1 ? [...ts][0] : null; }
  const ts = t.kind === "type" ? (t.types || [t.type]) : t.kind === "tag" ? [t.type] : [];
  return ts.length === 1 && TC[ts[0]] ? ts[0] : null;
}
/** A variable's chip colour: the entity type of what it is about (mentions, speech, relations of someone, "is one of"), as everywhere in
    aLex (TC); none for words, layers and topics. */
const varColor = v => TC[specType(["mentions", "spoken", "relation"].includes(v.kind) || v.attr === "in" ? v.target : null)] || null;
/** A lexicon of the options by id. */
const svLexicon = id => svOptions.lexicons.find(x => x.id === id);
/** The word-choice section (parts of speech, ratios…) of the options that a figure is in. */
const svWcSection = figure => svOptions.wordchoice.find(s => figure in s.figures);
/** A topic model of the options by id. */
const svModel = id => svOptions.topics.find(x => x.id === id);
const SV_CASES = { kind: "pieces", piece: "slice", slice_by: "count", n: 10, words: 200, scope: { kind: "all" }, population: null, sample: "speech",
  narrators: true, min: null, min_range: 1 };
/** The page's setup and display choices, remembered between visits (per workspace). `editor` is how variables are edited (rows or
    chips) and `example` whether the R export holds an example script (both chosen on the Settings page); `setId` the saved set the
    setup came from, if any. */
S.stats = loadState("analyser.stats", {
  cases: SV_CASES, rows: [], columns: [], two: false, method: "pearson", correction: "none", split: "none",
  show: { p: false, n: false, ci: false }, sub: "corr", editor: "rows", example: true, setId: null,
});
let svEditing = null;                                  // the chip being edited: {list, i}
/** Remember the Statistics setup. */
const saveStats = () => saveState("analyser.stats", S.stats);

/** A number of the tables: one decimal from 100 up, two from 1, three below. */
const fmtStat = v => v == null ? "—" : Math.abs(v) >= 100 ? fmt(v, 1) : Math.abs(v) >= 1 ? fmt(v, 2) : fmt(v, 3);

/** What a variable is called before the server has named it (the server's own label, `variables.label`, is used in results). */
function varLabel(v) {
  if (v.name) return v.name;
  if (v.kind === "supersense") return "Supersense " + (v.value || "…");
  if (v.kind === "relation") return `${svOptions.relations[v.rel] || v.rel} of ${v.target ? svWho(v.target) : "any entity"}` + (v.word ? `: “${v.word}”` : "");
  if (v.kind === "sentiment") return svOptions.sentiment[v.stat] || "Sentiment";
  if (v.kind === "lexicon") return `${(svLexicon(v.lexicon || "emotion") || { name: v.lexicon === "emotion" || !v.lexicon ? "Emotion" : v.lexicon }).name}: ${v.category || "…"}`;
  if (v.kind === "topic") { const m = svModel(v.model); return `Topic ${v.topic + 1}` + (m && m.topics[v.topic] ? ": " + m.topics[v.topic] : ""); }
  if (v.kind === "style") return svOptions.style[v.figure] || v.figure;
  if (v.kind === "wordchoice") return (svWcSection(v.figure) || { figures: {} }).figures[v.figure] || v.figure;
  if (v.kind === "sound") return svOptions.sound[v.figure] || (String(v.figure).startsWith("phone:") ? `Sound ${v.figure.slice(6)} per 1,000 words` : v.figure);
  if (v.kind === "speech") return `${Object.fromEntries(SV_TYPES)[v.type]} in speech` + (v.weigh ? " (speech verb weighed)" : "");
  if (v.kind === "query") return `“${(v.query || "…").split("\n").filter(Boolean).join(" | ")}”` + (v.match === "lemma" && v.mode !== "pattern" ? " (lemma)" : "");
  if (v.kind === "mentions") return "Mentions of " + (v.target ? svWho(v.target) : "…") + (v.prop ? ": " + PROP_NAMES[v.prop].toLowerCase() : "");
  if (v.kind === "spoken") {
    const extra = [v.unit === "quotes" ? "quotes" : "", v.type ? Object.fromEntries(SV_TYPES)[v.type].toLowerCase() + (v.weigh ? " (speech verb weighed)" : "") : ""].filter(Boolean);
    return "Speech of " + (v.target ? svWho(v.target) : "…") + (extra.length ? ": " + extra.join(", ") : "");
  }
  if (v.attr === "in") return !v.target ? "Is one of …" : v.target.kind === "gender" ? "Gender: " + genderLabel(v.target.pron) : "Is " + svWho(v.target);
  return Object.fromEntries([...SV_PART_ATTRS, ...SV_PIECE_ATTRS])[v.attr] || "?";
}

/** A new variable of a kind, with its defaults (an attribute starts as the first one these cases have). */
function newVar(kind) {
  if (kind === "query") return { kind, query: "", mode: "simple", match: "word", measure: "per1k" };
  if (kind === "mentions") return { kind, target: null, prop: "", measure: "per1k" };
  if (kind === "spoken") return { kind, target: null, unit: "words", type: "", weigh: false, measure: "per1k" };
  if (kind === "supersense") return { kind, value: (svOptions.supersenses[0] || {}).value || "", measure: "per1k" };
  if (kind === "relation") return { kind, rel: "agent", word: "", target: null, measure: "per1k" };
  if (kind === "sentiment") return { kind, stat: "mean" };
  if (kind === "lexicon") { const lx = svOptions.lexicons[0]; return { kind, lexicon: lx ? lx.id : "emotion", category: lx ? lx.categories[0] : "", measure: "per1k" }; }
  if (kind === "topic") { const m = svOptions.topics[0]; return { kind, model: m ? m.id : "", topic: 0 }; }
  if (kind === "speech") return { kind, type: "question", weigh: false, measure: "per1k" };
  if (kind === "style") return { kind, figure: "mattr" };
  if (kind === "wordchoice") return { kind, figure: "pos:ADJ" };
  if (kind === "sound") return { kind, figure: "stressed" };
  return { kind, attr: S.stats.cases.kind === "pieces" ? "position" : "in", target: null };
}

/** A small select: options are [value, label]; `onChange(value)`; `title` is also its accessible name. */
function svSelect(options, value, onChange, title) {
  return h("select", { title, "aria-label": title, onchange: e => onChange(e.target.value) }, options.map(([v, l]) => h("option", { value: v, selected: v === value }, l)));
}

/** A target's name in a variable's label: as `specLabel`, with the books added for an entity whose name another entity shares
    (as the server's labels do, `variables.who`). */
function svWho(t) {
  const rows = (S.units && S.units.rows) || [], row = t.kind === "unit" ? rows.find(r => r.id === t.id) : null;
  return row && rows.filter(r => r.name === row.name).length > 1 ? `${specLabel(t)} (${booksLabel(row.books)})` : specLabel(t);
}

/** One variable as an editable row: its own fields (query, entities, attribute), the measure, an optional name, move and remove. */
function varRow(v, i, list, redraw) {
  const set = (k, val, again) => { v[k] = val; saveStats(); if (again) redraw(); };
  const C = S.stats.cases;
  const fields = [];
  if (v.kind === "query") {
    fields.push(h("input", { type: "text", value: v.query, placeholder: v.mode === "pattern" ? '[lemma="say"] [pos="ADV"]' : "word, wo*, a|b, or a phrase", style: { minWidth: "180px" },
      "aria-label": "Query", oninput: e => set("query", e.target.value) }),
    svSelect([["simple", "Simple"], ["pattern", "Pattern"]], v.mode || "simple", m => set("mode", m, true), "Query language, as on the Corpus page"),
    v.mode === "pattern" ? null : svSelect([["word", "Word forms"], ["lemma", "Lemmas"]], v.match || "word", m => set("match", m), "Match word forms or lemmas"),
    C.kind === "participants" && C.sample === "findings" ? svSelect([["", "All findings"], ...DESC_KINDS], v.finding || "", m => set("finding", m), "Only findings of one kind") : null);
  } else if (v.kind === "supersense") {
    const known = svOptions.supersenses.map(x => [x.value, `${x.value} (${fmt(x.n)})`]);
    fields.push(svSelect(known.some(k => k[0] === v.value) || !v.value ? known : [[v.value, v.value], ...known], v.value, x => set("value", x), "BookNLP's supersense"));
  } else if (v.kind === "relation") {
    fields.push(svSelect(Object.entries(svOptions.relations), v.rel, x => set("rel", x, true), "Which relation"),
      h("input", { type: "text", value: v.word || "", placeholder: "any word (or say, wo*, a|b)", "aria-label": "Word", style: { width: "150px" }, oninput: e => set("word", e.target.value.trim()) }),
      v.target ? picker(v.target, t => set("target", t), { group: true, gender: true }) : h("span", { class: "small muted" }, "of any entity"),
      h("button", { class: "btn small", type: "button", onclick: () => set("target", v.target ? null : { kind: "type", type: "PER", types: ["PER"] }, true) }, v.target ? "Any entity" : "Choose whose…"));
  } else if (v.kind === "sentiment") {
    fields.push(svSelect(Object.entries(svOptions.sentiment), v.stat, x => set("stat", x, true)),
      svOptions.vader ? null : h("span", { class: "small warn" }, "needs the vaderSentiment package"));
  } else if (v.kind === "lexicon") {
    const lx = svLexicon(v.lexicon);
    fields.push(svOptions.lexicons.length ? [
      svSelect(svOptions.lexicons.map(x => [x.id, x.name]), v.lexicon, x => { v.category = svLexicon(x).categories[0]; set("lexicon", x, true); }, "Which lexicon"),
      lx ? svSelect(lx.categories.map(c => [c, c]), v.category, x => set("category", x, true), "Which category") : null]
      : h("span", { class: "small muted" }, "No lexicons yet: add one first (Over time → Lexicons)."));
  } else if (v.kind === "topic") {
    const m = svModel(v.model);
    fields.push(svOptions.topics.length ? [
      svSelect(svOptions.topics.map(x => [x.id, x.name + (x.all ? "" : ` (${x.covers.length} of ${selected().length} books)`)]), m ? v.model : "", x => { v.topic = 0; set("model", x, true); }, "Which topic model"),
      m ? svSelect(m.topics.map((name, i) => [String(i), `${i + 1}. ${name}`]), String(v.topic), x => set("topic", +x, true), "Which topic") : null,
      m && !m.all ? h("span", { class: "small warn" }, "Not fitted on every selected book: cases from the others get no value.") : null]
      : h("span", { class: "small muted" }, "No topic model shares books with this selection: fit one on the Topics page."));
  } else if (v.kind === "speech") {
    fields.push(svSelect(SV_TYPES, v.type, x => set("type", x, true), "Sentence type of the quotes"),
      h("label", { class: "inline", title: "A quote's own ? or ! decides its type; this also lets a speech verb like asked or exclaimed decide it when there's no such mark" },
        h("input", { type: "checkbox", checked: !!v.weigh, onchange: e => set("weigh", e.target.checked, true) }), "Weigh the speech verb"));
  } else if (v.kind === "style") {
    fields.push(svSelect(Object.entries(svOptions.style), v.figure, x => set("figure", x, true)));
  } else if (v.kind === "wordchoice") {
    const sec = svWcSection(v.figure) || svOptions.wordchoice[0];
    fields.push(svSelect(svOptions.wordchoice.map(x => [x.id, x.title]), sec ? sec.id : "", x => set("figure", Object.keys(svOptions.wordchoice.find(y => y.id === x).figures)[0], true), "Kind of word-choice figure"),
      sec ? svSelect(Object.entries(sec.figures), v.figure, x => set("figure", x, true), "Word-choice figure") : null);
  } else if (v.kind === "sound") {
    fields.push(svSelect([...Object.entries(svOptions.sound), ...svOptions.phonemes.map(p => ["phone:" + p, `Sound ${p} per 1,000 words`])], v.figure,
      x => set("figure", x, true), "Sound and rhythm figure"),
      svOptions.sound_ready ? null : h("span", { class: "small warn" }, "needs the pronunciation dictionary (see Settings → Sound and rhythm)"));
  } else if (v.kind === "mentions") {
    fields.push(picker(v.target, t => set("target", t), { group: true, gender: true }),
      svSelect([["", "All mentions"], ["PROP", "Names"], ["NOM", "Descriptions"], ["PRON", "Pronouns"]], v.prop || "", m => set("prop", m), "Which mentions count"));
  } else if (v.kind === "spoken") {
    fields.push(picker(v.target, t => set("target", t), { group: true, gender: true }),
      svSelect([["words", "Words spoken"], ["quotes", "Quotes"]], v.unit || "words", u => { if (u === "words" && v.measure === "pct") v.measure = "per1k"; set("unit", u, true); },
        "Count the words they speak, or their quotes"),
      svSelect([["", "Every sentence type"], ...SV_TYPES], v.type || "", x => set("type", x, true), "Only quotes of one sentence type"),
      v.type ? h("label", { class: "inline", title: "A quote's own ? or ! decides its type; this also lets a speech verb like asked or exclaimed decide it when there's no such mark" },
        h("input", { type: "checkbox", checked: !!v.weigh, onchange: e => set("weigh", e.target.checked, true) }), "Weigh the speech verb") : null);
  } else {
    const attrs = C.kind === "pieces" ? SV_PIECE_ATTRS : SV_PART_ATTRS;
    fields.push(svSelect(attrs.some(a => a[0] === v.attr) ? attrs : [[v.attr, varLabel({ ...v, name: "" }) + " (not for these cases)"], ...attrs], v.attr, a => set("attr", a, true)),
      v.attr === "in" ? picker(v.target, t => set("target", t), { group: true, gender: true }) : null);
  }
  const move = d => { list.splice(i, 1); list.splice(i + d, 0, v); saveStats(); redraw(); };
  return h("div", { class: "svar" },
    h("span", { class: "k" }, SV_KIND_LABEL[v.kind]),
    fields,
    SV_COUNTED.has(v.kind) ? svSelect(v.kind === "speech" || (v.kind === "spoken" && v.unit === "quotes") ? [...SV_MEASURES, SV_QUOTE_SHARE] : SV_MEASURES, v.measure || "per1k", m => set("measure", m), "How a count becomes a value") : null,
    h("input", { type: "text", value: v.name || "", placeholder: "Name (optional)", "aria-label": "Name", style: { width: "130px" }, oninput: e => set("name", e.target.value.trim()) }),
    h("span", { class: "svar-tools" },
      helpButton("stats", v.kind, SV_KIND_LABEL[v.kind]),
      h("button", { class: "btn small", type: "button", title: "Move up", disabled: i === 0, onclick: () => move(-1) }, "↑"),
      h("button", { class: "btn small", type: "button", title: "Move down", disabled: i === list.length - 1, onclick: () => move(1) }, "↓"),
      h("button", { class: "btn small", type: "button", title: "Remove", "aria-label": "Remove " + varLabel(v), onclick: () => { list.splice(i, 1); saveStats(); redraw(); } }, "×")));
}

/** Add variables to a list, at most `SV_MAX`; says so if some didn't fit. */
function addVars(list, vars) {
  const room = SV_MAX - list.length;
  list.push(...vars.slice(0, Math.max(0, room)));
  if (vars.length > room) toast(`A list holds at most ${SV_MAX} variables: ${plural(vars.length - Math.max(0, room), "variable")} left out.`, true);
  saveStats();
}

/** The buttons under a list of variables: add one of each kind, and the bulk adds (paste, most frequent words or entities, every
    gender / tag / saved group). A bulk add that needs a choice opens a small form in `box`. */
function varAdders(list, redraw) {
  const box = h("div");
  const full = list.length >= SV_MAX;
  const bulk = async body => {
    const r = await api("/api/stats/bulk", withBooks(body));
    addVars(list, r.variables.map(({ label, ...v }) => v));
    redraw();
  };
  const form = (...kids) => box.replaceChildren(h("div", { class: "svbulk" }, kids, h("button", { class: "btn small", type: "button", onclick: () => box.replaceChildren() }, "Cancel")));
  const paste = () => {
    const ta = h("textarea", { rows: 5, placeholder: "One word, phrase or pattern per line", style: { width: "100%" } });
    const mode = svSelect([["simple", "Simple"], ["pattern", "Pattern"]], "simple", () => {}, "Query language");
    const match = svSelect([["word", "Word forms"], ["lemma", "Lemmas"]], "word", () => {}, "Match word forms or lemmas");
    form(h("div", { class: "fld" }, "Paste a list: each line becomes a variable", ta), h("div", { class: "row" }, mode, match,
      h("button", { class: "btn small primary", type: "button", onclick: () => {
        addVars(list, ta.value.split("\n").map(x => x.trim()).filter(Boolean).map(q => ({ ...newVar("query"), query: q, mode: mode.value, match: match.value })));
        redraw();
      } }, "Add")));
  };
  const topWords = () => {
    const n = h("input", { type: "number", min: 1, max: SV_MAX, value: 20, style: { width: "64px" } });
    const unit = svSelect([["word", "Word forms"], ["lemma", "Lemmas"]], "word", () => {}, "Count word forms or lemmas");
    const flt = { pos: [], tag: [], ent: [] };
    const books = h("input", { type: "number", min: 1, value: 1, style: { width: "64px" } });
    const st = { type: "", weigh: false };                              // the sentence type, as the Dialogue tabs' filters keep theirs
    const verbs = h("input", { type: "checkbox" });
    form(h("div", { class: "row" }, h("label", {}, "How many ", n), unit,
      h("label", { title: "Range: only words that occur in at least this many of the selected books" }, "Minimum range ", books),
      h("button", { class: "btn small primary", type: "button", onclick: () => bulk({ what: "words", n: +n.value || 20, unit: unit.value, filter: flt, min_range: Math.max(1, Math.round(+books.value) || 1),
        cases: casesBody(), ...typeArgs(st), speech_verbs: verbs.checked }) }, "Add")),
    h("div", { class: "small muted" }, "The most frequent in the cases' samples, as set above."), typeFilter(flt, () => {}),
    sentenceTypeFilter(st, () => {}),
    h("label", { class: "inline", title: "Only the verbs that introduce quotes (Dialogue → Speech verbs), as lemmas, ranked by the quotes they introduce; the word types then test the verb. The variables count every use of the word, not only as a speech verb." },
      verbs, "Speech verbs only"),
    h("div", { class: "small muted" }, "A sentence type takes only words inside quotes of that type (with speech verbs: the verbs of those quotes); the variables still count the words in the whole sample."));
  };
  const topEntities = () => {
    const n = h("input", { type: "number", min: 1, max: SV_MAX, value: 10, style: { width: "64px" } });
    const typ = svSelect([["ALL", "All types"], ...TYPES.map(t => [t, TYPE_NAMES[t]])], "PER", () => {}, "Entity type");
    form(h("div", { class: "row" }, h("label", {}, "How many ", n), typ,
      h("button", { class: "btn small primary", type: "button", onclick: () => bulk({ what: "entities", n: +n.value || 10, type: typ.value }) }, "Add")),
    h("div", { class: "small muted" }, "The most mentioned in the selected books, as mention variables."));
  };
  const topSpeakers = () => {
    const n = h("input", { type: "number", min: 1, max: SV_MAX, value: 10, style: { width: "64px" } });
    const typ = svSelect([["ALL", "All types"], ...TYPES.map(t => [t, TYPE_NAMES[t]])], "PER", () => {}, "Entity type");
    form(h("div", { class: "row" }, h("label", {}, "How many ", n), typ,
      h("button", { class: "btn small primary", type: "button", onclick: () => bulk({ what: "speakers", n: +n.value || 10, type: typ.value }) }, "Add")),
    h("div", { class: "small muted" }, "Those who speak the most words in the selected books, as speech variables (words spoken)."));
  };
  const everyCategory = () => {
    const lx = svSelect(svOptions.lexicons.map(x => [x.id, `${x.name} (${x.categories.length} categories)`]), svOptions.lexicons[0].id, () => {}, "Lexicon");
    form(h("div", { class: "row" }, lx, h("button", { class: "btn small primary", type: "button", onclick: () => {
      addVars(list, svLexicon(lx.value).categories.map(c => ({ ...newVar("lexicon"), lexicon: lx.value, category: c }))); redraw(); } }, "Add")),
    h("div", { class: "small muted" }, "A variable per category, as words per 1,000."));
  };
  const everyTopic = () => {
    const ms = svSelect(svOptions.topics.map(x => [x.id, `${x.name} (${x.topics.length} topics${x.all ? "" : `, ${x.covers.length} of ${selected().length} books`})`]), svOptions.topics[0].id, () => {}, "Topic model");
    form(h("div", { class: "row" }, ms, h("button", { class: "btn small primary", type: "button", onclick: () => {
      addVars(list, svModel(ms.value).topics.map((_, t) => ({ kind: "topic", model: ms.value, topic: t }))); redraw(); } }, "Add")),
    h("div", { class: "small muted" }, "A variable per topic: its share of each case's words. Models fitted on only some of the selected books leave the other books' cases without a value."));
  };
  const everyWordChoice = () => {
    const sec = svSelect(svOptions.wordchoice.map(x => [x.id, `${x.title} (${Object.keys(x.figures).length})`]), svOptions.wordchoice[0].id, () => {}, "Kind of word-choice figure");
    form(h("div", { class: "row" }, sec, h("button", { class: "btn small primary", type: "button", onclick: () => {
      addVars(list, Object.keys(svOptions.wordchoice.find(x => x.id === sec.value).figures).map(f => ({ ...newVar("wordchoice"), figure: f }))); redraw(); } }, "Add")),
    h("div", { class: "small muted" }, "A variable per figure: part-of-speech shares, ratios such as adjectives per verb, dynamic and static verbs, shares of verbs or nouns per supersense."));
  };
  const part = S.stats.cases.kind === "participants";
  const one = v => { addVars(list, [newVar(v)]); redraw(); };
  // the two menus (AD-36): one variable of a kind, or several at once; each entry is [value, label, what it does]
  const single = [["query", "Words", "A word, lemma, phrase or pattern, as on the Corpus page"], ["mentions", "Mentions", "Mentions of an entity, a group, a tag or a gender"],
    ["spoken", "Speech", "Speech of an entity, a group, a tag or a gender: the words they speak or their quotes"],
    ["attribute", "Attribute", part ? "Gender, tag or group (0/1), mentions, words spoken…" : "Number, position or length of the piece"]];
  const several = [["paste", "Paste a list…", paste], ["words", "Most frequent words…", topWords], ["entities", "Most mentioned entities…", topEntities],
    ["speakers", "Most talkative speakers…", topSpeakers], svOptions.wordchoice.length ? ["wordchoice", "Word choice…", everyWordChoice] : null,
    ["style", "Every style figure", () => { addVars(list, Object.keys(svOptions.style).map(f => ({ ...newVar("style"), figure: f }))); redraw(); }],
    ["sound", "Every sound figure", () => { addVars(list, Object.keys(svOptions.sound).map(f => ({ ...newVar("sound"), figure: f }))); redraw(); }],
    svOptions.lexicons.length ? ["lexicon", "Every category of a lexicon…", everyCategory] : null,
    svOptions.topics.length ? ["topics", "Every topic of a model…", everyTopic] : null,
    ...(part ? [["gender", "Every gender", () => bulk({ what: "attribute", attr: "gender" })], ["tag", "Every tag", () => bulk({ what: "attribute", attr: "tag" })],
      ["group", "Every saved group", () => bulk({ what: "attribute", attr: "group" })]] : [])].filter(Boolean);
  /** A menu that runs the chosen entry and goes back to its label. */
  const menu = (label, aria, options, onPick) => h("select", { class: "svmenu", disabled: full, "aria-label": aria, title: full ? `A list holds at most ${SV_MAX} variables` : null,
    onchange: e => { const v = e.target.value; e.target.value = ""; if (v) onPick(v); } }, h("option", { value: "" }, label), options);
  return h("div", {},
    h("div", { class: "row svadd" },
      menu("+ Add a variable…", "Add a variable", [single.map(([k, l, t]) => h("option", { value: k, title: t }, l)),
        h("optgroup", { label: "Layer" }, SV_LAYERS.map(([k, l]) => h("option", { value: k }, l)))], one),
      menu("Add several…", "Add several variables", several.map(([k, l]) => h("option", { value: k }, l)), v => several.find(x => x[0] === v)[2]())),
    box);
}

/** The variables of a list as chips, in the style of the entity chips (`gtag`): a short kind label, the name, and the entity type's colour
    where the variable is about entities (`varColor`). A click opens the chip's fields in a small editor under them (the "Chips" editor of
    the Settings page). */
function varChips(list, redraw) {
  const editing = svEditing && svEditing.list === list && list[svEditing.i] ? svEditing.i : null;
  const close = () => { svEditing = null; redraw(); };
  return [
    h("div", { class: "svchips" }, list.map((v, i) => h("span", { class: "gtag svchip" + (i === editing ? " on" : ""), style: { "--c": varColor(v) }, title: SV_KIND_LABEL[v.kind] },
      h("span", { class: "k" }, SV_KIND_SHORT[v.kind]),
      h("button", { type: "button", class: "nm", "aria-expanded": String(i === editing), onclick: () => { svEditing = i === editing ? null : { list, i }; redraw(); } }, varLabel(v)),
      h("button", { type: "button", "aria-label": "Remove " + varLabel(v), title: "Remove", onclick: () => { list.splice(i, 1); svEditing = null; saveStats(); redraw(); } }, "×")))),
    editing == null ? null : h("div", { class: "svbulk" }, varRow(list[editing], editing, list, () => { svEditing = { list, i: Math.min(editing, list.length - 1) }; redraw(); }),
      h("div", {}, h("button", { class: "btn small", type: "button", onclick: close }, "Done")))];
}

/** One list of variables with its adders; `title` heads it. Shown as rows or as chips, as chosen on the Settings page. */
function varList(title, list, hint) {
  const box = h("div", { class: "svlist" });
  const clear = () => { if (confirm(`Remove all ${plural(list.length, "variable")} from “${title}”? Saved sets are not changed.`)) { list.splice(0); svEditing = null; saveStats(); redraw(); } };
  const redraw = () => box.replaceChildren(
    h("div", { class: "svhead" }, h("strong", {}, title), h("span", { class: "muted small" }, ` ${list.length} of ${SV_MAX} `),
      list.length ? h("button", { class: "btn small", type: "button", title: "Remove every variable of this list", onclick: clear }, "Clear") : null,
      hint ? h("div", { class: "small muted" }, hint) : null),
    !list.length ? h("div", { class: "muted small" }, "No variables yet: add some below.")
      : S.stats.editor === "chips" ? varChips(list, redraw) : h("div", { class: "svars" }, list.map((v, i) => varRow(v, i, list, redraw))),
    varAdders(list, redraw));
  redraw();
  return box;
}

/** Take over a saved setup (`statstab.run`'s request) as the page's own; `id` is the set it came from. */
function applySetup(setup, id) {
  const d = S.stats, c = setup.cases || {};
  d.cases = { ...SV_CASES, ...c, scope: c.scope || { kind: "all" }, min: c.min ?? null, min_range: c.min_range ?? 1 };
  d.rows = setup.rows || []; d.columns = setup.columns || []; d.two = d.columns.length > 0;
  Object.assign(d, { method: setup.method || "pearson", correction: setup.correction || "none", split: setup.split || "none", setId: id });
  svEditing = null;
  saveStats();
}

/** The saved sets: open one, save the setup as a new one, or (for the set it came from) save the changes, rename or delete it. */
function setsBar(rerender) {
  const d = S.stats, box = h("div", { class: "row svsets" }, h("span", { class: "muted small" }, "Saved sets…"));
  const reply = r => { d.setId = r.id || null; saveStats(); toast("Saved."); rerender(); };
  api("/api/stats/sets").then(({ sets }) => {
    const cur = sets.find(x => x.id === d.setId);
    const name = h("input", { type: "text", placeholder: "Name for this set", "aria-label": "Name for this set", style: { width: "180px" } });
    box.replaceChildren(
      h("label", {}, "Saved sets ", h("select", { onchange: e => { const x = sets.find(y => y.id === e.target.value); if (x) { applySetup(x.setup, x.id); rerender(); } } },
        h("option", { value: "" }, sets.length ? "Open a saved set…" : "None saved yet"), sets.map(x => h("option", { value: x.id, selected: x.id === d.setId }, x.name)))),
      cur ? [h("button", { class: "btn small", type: "button", title: `Store the setup as it is now in “${cur.name}”`, onclick: async () => reply(await api(`/api/stats/sets/${cur.id}`, { setup: statsSetup() })) }, "Save changes"),
        h("button", { class: "btn small", type: "button", title: "Go back to the setup as it was saved", onclick: () => { applySetup(cur.setup, cur.id); rerender(); } }, "Revert"),
        h("button", { class: "btn small", type: "button", onclick: async () => { const n = prompt("New name for the set", cur.name); if (n && n.trim()) reply(await api(`/api/stats/sets/${cur.id}`, { name: n.trim() })); } }, "Rename"),
        h("button", { class: "btn small", type: "button", onclick: async () => { if (confirm(`Delete the set “${cur.name}”? The page keeps its setup.`)) { await api("/api/stats/sets/delete", { id: cur.id }); d.setId = null; saveStats(); rerender(); } } }, "Delete")] : null,
      name, h("button", { class: "btn small", type: "button", disabled: !d.rows.length, title: d.rows.length ? "" : "Add variables first",
        onclick: async () => { if (name.value.trim()) reply(await api("/api/stats/sets", { name: name.value.trim(), setup: statsSetup() })); else name.focus(); } }, "Save as a new set"));
  });
  return box;
}

/** The cases part of a request, as the server takes it (`cases.build`). */
function casesBody() {
  const C = S.stats.cases;
  const body = { kind: C.kind, min: C.min == null || C.min === "" ? undefined : +C.min };
  const scope = C.scope || { kind: "all" };                       // a speech scope counts only once its speaker is chosen
  if (C.kind === "pieces") Object.assign(body, { piece: C.piece, slice_by: C.slice_by, n: C.n, words: C.words, scope: scope.kind === "speech" && !scope.speaker ? { kind: "all" } : scope });
  else Object.assign(body, { population: C.population || undefined, sample: C.sample, narrators: C.narrators, min_range: C.min_range });
  return body;
}

/** The whole request (`statstab.run`): also what a saved set keeps. */
function statsSetup() {
  const d = S.stats;
  return { cases: casesBody(), rows: d.rows, columns: d.two ? d.columns : [], method: d.method, correction: d.correction, split: d.split };
}

/** The cases controls: text pieces (which, scope) or participants (who, sample, narrators), and the minimum sample. */
function casesControls(onChange) {
  const C = S.stats.cases, box = h("div");
  const set = (k, v) => { C[k] = v; saveStats(); draw(); onChange(); };
  /** The part of the text whose words count ("Words counted"), with a picker for whose speech; laid out like the number fields beside it. */
  const scopeFields = () => {
    const sc = C.scope || { kind: "all" };
    return [h("label", {}, "Words counted", h("select", { class: "svnum", onchange: e => {
      const k = e.target.value;
      C.scope = k === "speech" ? { kind: "speech", speaker: sc.speaker || null } : { kind: k }; saveStats(); draw();
    } }, SCOPES.map(([k, l]) => h("option", { value: k, selected: sc.kind === k }, l)))),
    sc.kind === "speech" ? h("div", { class: "fld" }, "Whose speech", picker(sc.speaker, v => { C.scope = { kind: "speech", speaker: v }; saveStats(); }, { group: true, gender: true })) : null];
  };
  const draw = () => box.replaceChildren(h("div", { class: "controls" },
    h("div", { class: "fld" }, "Cases", seg([["pieces", "Text pieces"], ["participants", "Participants"]], C.kind, v => set("kind", v))),
    C.kind === "pieces" ? [
      h("div", { class: "fld" }, "Each case is", seg(SV_PIECES, C.piece, v => set("piece", v))),
      C.piece === "slice" ? [
        h("label", {}, "Slices by", h("select", { class: "svnum", onchange: e => set("slice_by", e.target.value) },
          SV_SLICE_BY.map(([v, l]) => h("option", { value: v, selected: v === C.slice_by }, l)))),
        C.slice_by === "words"
          ? h("label", { title: "Each book is cut at every this many words; a rest under half a slice joins the last one" }, "Words per slice",
            h("input", { type: "number", class: "svnum", min: 20, value: C.words, onchange: e => set("words", Math.max(20, Math.round(+e.target.value) || 200)) }))
          : h("label", {}, "Slices per book", h("input", { type: "number", class: "svnum", min: 2, max: 200, value: C.n, onchange: e => set("n", Math.max(2, Math.min(200, +e.target.value || 10))) })),
      ] : null,
      scopeFields(),
      C.piece === "sentence" ? h("div", { class: "small muted", style: { maxWidth: "340px" } },
        "Thousands of short cases: most counts are 0 or 1, so “present (0/1)” is often clearer than a rate per 1,000 words.") : null,
    ] : [
      h("div", { class: "fld" }, "Who takes part", h("div", { class: "row" },
        C.population ? picker(C.population, v => { C.population = v; saveStats(); }, { group: true, gender: true }) : h("span", {}, "Every person above your minimum mentions"),
        h("button", { class: "btn small", type: "button", onclick: () => set("population", C.population ? null : { kind: "type", type: "PER", types: ["PER"] }) }, C.population ? "Back to every person" : "Choose…"))),
      h("div", { class: "fld" }, "Each participant's sample", svSelect(SV_SAMPLES, C.sample, v => set("sample", v))),
      C.sample === "speech_narration" ? h("label", { class: "inline", title: "An unnamed narrator, or narrators you linked, take part as their own participant" },
        h("input", { type: "checkbox", checked: C.narrators, onchange: e => set("narrators", e.target.checked) }), "Narrators who aren't a character take part") : null,
    ],
    h("label", { title: "Cases with a smaller sample are left out (and counted)" }, C.kind === "participants" && C.sample === "findings" ? "Minimum findings" : "Minimum sample (words)",
      h("input", { type: "number", class: "svnum", min: 0, value: C.min ?? "", placeholder: C.kind === "participants" && C.sample === "findings" ? "10" : C.kind === "pieces" && C.piece === "sentence" ? "1" : "100",
        onchange: e => { C.min = e.target.value === "" ? null : Math.max(0, +e.target.value || 0); saveStats(); } })),
    C.kind !== "participants" ? null : h("label", { title: "Range: participants who are in fewer of the selected books are left out (and counted)" }, "Minimum range",
      h("input", { type: "number", class: "svnum", min: 1, value: C.min_range, onchange: e => { C.min_range = Math.max(1, Math.round(+e.target.value) || 1); e.target.value = C.min_range; saveStats(); } }))));
  draw();
  return box;
}

/* ---------- results ---------- */
/** The colour of a correlation: the neutral backdrop at 0, deepening to blue (positive) or red (negative) at ±1. Fixed colours in
    both themes (AL-COLOR-07), so the cell reads the same on screen and in a download. */
function corrColor(r) {
  if (r == null) return "none";
  const to = r > 0 ? PALETTE[0] : PALETTE[1], t = Math.min(1, Math.abs(r));
  const rgb = x => [1, 3, 5].map(k => parseInt(x.slice(k, k + 2), 16));
  const [a, b] = [rgb(LIGHT_PANEL2), rgb(to)];
  return "#" + a.map((v, k) => Math.round(v + (b[k] - v) * t).toString(16).padStart(2, "0")).join("");
}

const FEW_CASES = 30;                                      // a figure from fewer cases than this gets the reliability marker (AL-PRIN-14)
/** Why a figure from `n` cases is marked, or null when there are enough. */
const fewCases = n => n != null && n < FEW_CASES ? `Only ${fmt(n)} cases (fewer than ${FEW_CASES}): a figure from so few swings a lot; read it with care` : null;

/** The correlation heatmap as an SVG: a cell per pair, coloured by r, with r and stars, and p, N or the interval as chosen (≈: fewer than FEW_CASES cases);
    hover a cell for every figure. A matrix shows its lower triangle (rows from the second variable, columns up to the last but one). */
function corrHeatmap(res, show) {
  const C = res.correlations, label = Object.fromEntries(res.variables.map(v => [v.id, v.label]));
  const matrix = C.shape === "matrix";
  const rows = matrix ? C.rows.slice(1) : C.rows, cols = matrix ? C.columns.slice(0, -1) : C.columns;
  const cellOf = (i, j) => C.cells[matrix ? i + 1 : i][j];
  const short = s => s.length > 34 ? s.slice(0, 33) + "…" : s;
  const sym = C.method === "spearman" ? "ρ" : "r";
  const lines = 1 + show.p + show.n + show.ci, cw = show.ci ? 96 : 72, ch = 10 + 14 * lines;
  const labW = Math.min(240, 16 + 6.4 * Math.max(...rows.map(id => short(label[id]).length))), topH = 18 + 4.6 * Math.max(...cols.map(id => short(label[id]).length));
  const W = Math.max(labW + cols.length * cw + 70, labW + 480), legendY = topH + rows.length * ch + 22, H = legendY + 66;   // room for slanted labels and the key
  const g = svg("svg", { viewBox: `0 0 ${W} ${H}`, width: W, "font-family": SVG_FONT, "font-size": 11.5, role: "img", "aria-label": `Correlations (${C.method}) between ${plural(C.rows.length + (matrix ? 0 : C.columns.length), "variable")}` });
  cols.forEach((id, j) => {
    const x = labW + j * cw + cw / 2;
    g.append(svg("text", { x, y: topH - 6, transform: `rotate(-40 ${x} ${topH - 6})`, fill: cssVar("--ink") }, short(label[id]), svg("title", {}, label[id])));
  });
  rows.forEach((rid, i) => {
    const y = topH + i * ch;
    g.append(svg("text", { x: labW - 8, y: y + ch / 2 + 4, "text-anchor": "end", fill: cssVar("--ink") }, short(label[rid]), svg("title", {}, label[rid])));
    cols.forEach((cid, j) => {
      const c = cellOf(i, j), x = labW + j * cw;
      if (!c) return;
      const strong = c.r != null && Math.abs(c.r) > 0.55, ink = strong ? "#ffffff" : LIGHT_INK;
      const text = c.r == null ? ["—"] : [`${fmt(c.r, 2)}${c.stars}${fewCases(c.n) ? "≈" : ""}`, show.p ? `p ${fmtP(C.correction === "none" ? c.p : c.p_adj)}` : null,
        show.n ? `N ${fmt(c.n)}` : null, show.ci && c.lo != null ? `[${fmt(c.lo, 2)}, ${fmt(c.hi, 2)}]` : show.ci ? "[—]" : null].filter(Boolean);
      const tip = c.r == null ? `${label[rid]} × ${label[cid]}: no correlation (N ${fmt(c.n)}; fewer than 3 cases, or a variable that doesn't vary)`
        : `${label[rid]} × ${label[cid]}\n${sym} = ${fmt(c.r, 3)}, 95% CI ${c.lo == null ? "—" : `[${fmt(c.lo, 3)}, ${fmt(c.hi, 3)}]`}\np = ${fmtP(c.p)}` +
          (C.correction === "none" ? "" : `, ${C.correction} p = ${fmtP(c.p_adj)}`) + `\nN = ${fmt(c.n)}` + (fewCases(c.n) ? `\n≈ ${fewCases(c.n)}` : "");
      g.append(svg("g", {}, svg("title", {}, tip),
        svg("rect", { x: x + 1, y: y + 1, width: cw - 2, height: ch - 2, rx: 3, fill: c.r == null ? LIGHT_PANEL : corrColor(c.r), stroke: c.r == null ? LIGHT_FAINT : "none", "stroke-dasharray": c.r == null ? "3 3" : null }),
        text.map((t, k) => svg("text", { x: x + cw / 2, y: y + 5 + 14 * (k + 1) - 2, "text-anchor": "middle", fill: c.r == null ? LIGHT_FAINT : ink, "font-weight": k === 0 ? 600 : 400, "font-size": k === 0 ? 12 : 10.5 }, t))));
    });
  });
  const lx = labW, lw = 160;
  for (let k = 0; k < 40; k++) g.append(svg("rect", { x: lx + k * lw / 40, y: legendY, width: lw / 40 + 0.5, height: 10, fill: corrColor(-1 + 2 * (k + 0.5) / 40) }));
  [["−1", 0], ["0", lw / 2], ["+1", lw]].forEach(([t, dx]) => g.append(svg("text", { x: lx + dx, y: legendY + 24, "text-anchor": "middle", fill: cssVar("--muted"), "font-size": 10.5 }, t)));
  const corr = { none: "no correction", bonferroni: "Bonferroni-corrected", holm: "Holm-corrected" }[C.correction];
  g.append(svg("text", { x: lx, y: legendY + 44, fill: cssVar("--muted"), "font-size": 10.5 },
    `${C.method === "spearman" ? "Spearman's ρ" : "Pearson's r"}; * p < .05, ** p < .01, *** p < .001 (${corr}, ${plural(C.tests, "test")}).`));
  g.append(svg("text", { x: lx, y: legendY + 58, fill: cssVar("--muted"), "font-size": 10.5 },
    `N = ${fmt(res.cases.n)} ${res.cases.kind === "pieces" ? "text pieces" : "participants"}; cases missing a value are left out pair by pair; ≈ fewer than ${FEW_CASES} cases.`));
  return g;
}

/** The Correlations view: the heatmap (SVG/PNG download), the display toggles, and every pair as a sortable table (CSV download). */
function corrView(res, redraw) {
  const d = S.stats, C = res.correlations, label = Object.fromEntries(res.variables.map(v => [v.id, v.label]));
  if (C.shape === "matrix" && C.rows.length < 2) return h("div", { class: "panel empty" }, "Add a second variable to correlate (or a second list).");
  const few = res.cases.n < 3 ? h("div", { class: "panel warn small" }, `A correlation needs at least 3 cases with values; there ${res.cases.n === 1 ? "is" : "are"} ${fmt(res.cases.n)}. Lower the minimum sample, choose more participants or smaller pieces.`) : null;
  const pairs = [];
  C.cells.forEach((line, i) => line.forEach((c, j) => { if (c) pairs.push({ a: label[C.rows[i]], b: label[C.columns[j]], ...c }); }));
  const sym = C.method === "spearman" ? "ρ" : "r";
  const cols = [{ k: "a", label: "Variable" }, { k: "b", label: "with" },
    { k: "r", label: sym, num: true, fmt: (v, row) => v == null ? "—" : h("span", { class: v > 0 && row.p_adj < 0.05 ? "rp" : v < 0 && row.p_adj < 0.05 ? "rn" : "" }, fmt(v, 3) + row.stars, fewCases(row.n) ? relMark(fewCases(row.n)) : null), sortVal: row => row.r == null ? -Infinity : Math.abs(row.r) },
    { k: "lo", label: "95% CI from", num: true, fmt: v => v == null ? "—" : fmt(v, 3) }, { k: "hi", label: "to", num: true, fmt: v => v == null ? "—" : fmt(v, 3) },
    { k: "p", label: "p", num: true, fmt: fmtP, sortVal: row => row.p == null ? -Infinity : -row.p },
    C.correction === "none" ? null : { k: "p_adj", label: `p (${C.correction})`, num: true, fmt: fmtP, sortVal: row => row.p_adj == null ? -Infinity : -row.p_adj },
    { k: "n", label: "N", num: true, fmt: v => relNum(fmt(v), fewCases(v)) }].filter(Boolean);
  const toggle = (k, label) => h("label", { class: "inline" }, h("input", { type: "checkbox", checked: d.show[k], onchange: e => { d.show[k] = e.target.checked; saveStats(); redraw(); } }), label);
  return h("div", {}, few,
    h("div", { class: "controls" }, h("div", { class: "fld" }, "Show in each cell", h("div", { class: "row" }, toggle("p", "p-value"), toggle("n", "N"), toggle("ci", "95% interval")))),
    h("div", { class: "hm-wrap" }, chartBox(corrHeatmap(res, d.show), `correlations-${C.method}`)),
    h("h3", {}, "Every pair"),
    table(cols, pairs, { limit: 40, sort: "r", csvName: `correlations ${C.method}` }),
    note("How this is calculated", res.notes.correlation, res.notes.correction, res.notes.independence));
}

/** The Descriptives view: N, M, SD, V, median, min, max, SE and the 95% interval of the mean of every variable, per group when split. */
function descView(res) {
  const D = res.descriptives, split = D.split !== "none";
  const rows = D.groups.flatMap(g => g.stats.map((s, i) => ({ ...s, group: g.label, variable: res.variables[i].label, measure: res.variables[i].measure })));
  const num = (k, label, title) => ({ k, label, num: true, fmt: fmtStat, title });
  const cols = [split ? { k: "group", label: "Group", title: "The cases in this group (a participant can be in several)" } : null,
    { k: "variable", label: "Variable" }, { k: "measure", label: "Measure" },
    { k: "n", label: "N", num: true, fmt: v => relNum(fmt(v), fewCases(v)), title: "Cases with a value" }, num("mean", "M", "Mean"), num("sd", "SD", "Standard deviation (sample, N − 1)"),
    num("var", "V", "Variance (sample, N − 1)"), num("median", "Mdn", "Median"), num("min", "Min"), num("max", "Max"),
    num("se", "SE", "Standard error of the mean"), num("lo", "95% CI from", "Interval of the mean, from t"), num("hi", "to")].filter(Boolean);
  return h("div", {},
    split ? h("p", { class: "small muted" }, `Split by ${SV_SPLITS.find(s => s[0] === D.split)[1].toLowerCase()}: ` + D.groups.slice(1).map(g => `${g.label} (${fmt(g.n)})`).join(", ") + ".") : null,
    table(cols, rows, { limit: 100, csvName: "descriptives" + (split ? " by " + D.split : "") }),
    note("How this is calculated", res.notes.descriptives));
}

/** Download the cases and variables of a run as a .zip of files for R (the server builds it, see core/rexport.py). `setup` is the request
    the run was made from, so the files hold what the tables show even if the page's setup was changed since. */
async function downloadForR(button, setup) {
  button.disabled = true;
  try {
    const r = await api("/api/stats/export", withBooks({ setup, example: S.stats.example }), true);
    download((/filename="(.+?)"/.exec(r.headers.get("content-disposition") || "") || [])[1] || "analyser-statistics.zip", await r.blob());
    toast("Downloaded the files for R.");
  } finally { button.disabled = false; }
}

/** The Data view: one row per case with its sample and every variable's value; a case opens in the text (a piece) or its profile (a participant). */
function dataView(res, setup) {
  const K = res.cases, pieces = K.kind === "pieces";
  const rows = K.rows.map((r, i) => ({ ...r, ...Object.fromEntries(res.variables.map((v, k) => [v.id, res.values[k][i]])) }));
  const cols = [
    { k: "label", label: pieces ? "Text piece" : "Participant", fmt: (v, r) => h("a", { href: pieces ? `#/read/${encodeURIComponent(r.book)}/${r.start}` : "#/entities/" + encodeURIComponent(r.id) }, v), csv: v => v },
    pieces ? { k: "book", label: "Book", fmt: v => bookTitle(v), csv: v => bookTitle(v) } : { k: "type", label: "Type" },
    pieces ? null : { k: "books", label: "Books", fmt: v => booksLabel(v), csv: v => v.map(bookTitle).join("; "), sortVal: r => r.books.length },
    { k: "size", label: K.unit === "findings" ? "Findings" : "Words", num: true, fmt: v => fmt(v), title: "The case's sample" },
    ...res.variables.map(v => ({ k: v.id, label: v.label + (v.measure ? ` (${v.measure})` : ""), num: true, fmt: fmtStat, title: v.note || v.measure })),
  ].filter(Boolean);
  return h("div", {},
    h("p", { class: "small muted" }, "The values every figure is computed from. Download them (CSV) to work on them in SPSS, JASP or a spreadsheet, or as files for R:"),
    h("div", { class: "row", style: { marginBottom: "8px" } },
      h("button", { class: "btn small", type: "button", title: "A .zip with the cases (wide and long), the variables, the cases left out, and a script that loads them",
        onclick: e => downloadForR(e.currentTarget, setup) }, "Download for R (.zip)"),
      h("span", { class: "small muted" }, "Counts and rates side by side, ready for lm, glm, aov or lme4.")),
    table(cols, rows, { limit: 60, csvName: "statistics data" }));
}

/** What the cases came to: how many, and how many were left out for a small sample. */
function casesSummary(res) {
  const K = res.cases, what = K.kind === "pieces" ? { sentence: "sentence", chapter: "chapter", slice: "slice", book: "book" }[K.sample] : "participant";
  const unit = K.unit === "findings" ? "findings" : "words";
  return `${plural(K.n, what)}` + (K.dropped ? `; ${fmt(K.dropped)} left out (fewer than ${fmt(Math.max(1, K.min))} ${unit}${K.kind === "participants" ? ", or none at all" : ""}${K.kind === "participants" && K.min_range > 1 ? `, or in fewer than ${fmt(K.min_range)} books` : ""})` : "") + ".";
}

/** The variables' notes, one per distinct note, each with the variables it is about ("Topic 1, Topic 2: …"; "6 variables (Topic 1, …)"). */
function svNotes(vars) {
  const by = new Map();
  vars.filter(v => v.note).forEach(v => by.set(v.note, [...(by.get(v.note) || []), v.label]));
  return [...by].map(([note, labels]) => [labels.length > 3 ? `${labels.length} variables (${labels[0]}, …)` : labels.join("; "), note]);
}

/** The results: the summary, notes on variables that don't apply (or have no value in some cases), and the three views. */
function statsResult(res, setup) {
  const d = S.stats, box = h("div");
  const draw = () => box.replaceChildren(
    h("p", { class: "small" }, casesSummary(res)),
    svNotes(res.variables).map(([labels, note]) => h("div", { class: "panel warn small" }, `${labels}: ${note}`)),
    h("div", { class: "subtabs" }, [["corr", "Correlations"], ["desc", "Descriptives"], ["data", "Data"]].map(([k, l]) =>
      h("button", { class: d.sub === k ? "on" : "", onclick: () => { d.sub = k; saveStats(); draw(); } }, l))),
    d.sub === "desc" ? descView(res) : d.sub === "data" ? dataView(res, setup) : corrView(res, draw));
  draw();
  return box;
}

/** The Statistics page. */
async function renderStats(main) {
  await units();
  svOptions = await api("/api/stats/options", withBooks({}));
  const d = S.stats, out = h("div", { class: "panel" }, h("div", { class: "empty" }, "Choose the cases and add variables, then Run."));
  const lists = h("div"), options = h("div");
  const drawLists = () => lists.replaceChildren(
    varList(d.two ? "Rows" : "Variables", d.rows, d.two ? "Each row variable is correlated with each column variable." : "Every variable is correlated with every other."),
    h("label", { class: "inline", style: { margin: "8px 0" } }, h("input", { type: "checkbox", checked: d.two, onchange: e => { d.two = e.target.checked; saveStats(); drawLists(); } }),
      "A second list (rows × columns instead of everything against everything)"),
    d.two ? varList("Columns", d.columns) : null);
  let latest = 0;
  const run = async () => {
    const mine = ++latest;
    if (!d.rows.length) { out.replaceChildren(h("div", { class: "empty" }, "Add at least one variable.")); return; }
    out.replaceChildren(loading("Counting…"));
    const setup = statsSetup(), res = await api("/api/stats", withBooks({ setup }));
    if (mine === latest) out.replaceChildren(statsResult(res, setup));
  };
  const pieceSplit = () => d.cases.kind !== "pieces" || ["none", "book"].includes(d.split);   // text pieces split only by book
  const drawOptions = () => options.replaceChildren(h("div", { class: "controls" },
    h("div", { class: "fld" }, "Coefficient", seg([["pearson", "Pearson's r"], ["spearman", "Spearman's ρ"]], d.method, v => { d.method = v; saveStats(); drawOptions(); })),
    h("label", {}, "Correction for many tests", svSelect(SV_CORRECTIONS, d.correction, v => { d.correction = v; saveStats(); })),
    h("label", {}, "Descriptives split by", svSelect(d.cases.kind === "pieces" ? SV_SPLITS.filter(s => ["none", "book"].includes(s[0])) : SV_SPLITS,
      pieceSplit() ? d.split : "none", v => { d.split = v; saveStats(); })),
    h("button", { class: "btn primary", type: "button", onclick: () => { if (!pieceSplit()) d.split = "none"; run(); } }, "Run")));
  // the setup in three steps, each its own section (AD-36): what the cases are, what is measured in them, and how they are tested
  const step = (n, title, ...kids) => h("section", { class: "panel svstep", "data-toc": title }, h("h2", {}, h("span", { class: "svstep-n" }, n), title), ...kids);
  main.replaceChildren(
    h("div", { class: "svtop" },
      h("p", { class: "small muted" }, "Correlations and descriptive statistics of words, phrases, mentions, speech and attributes, measured in text pieces (chapters, slices, books) or in participants (entities, each with their own sample of text)."),
      setsBar(() => renderStats(main))),
    step("1", "Cases", casesControls(() => { drawLists(); drawOptions(); })),
    step("2", "Variables", lists),
    step("3", "Run", options),
    out);
  drawLists();
  drawOptions();
}
