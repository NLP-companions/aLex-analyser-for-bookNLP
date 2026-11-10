"use strict";
/* ---------- Over the book ---------- */
/* One target (an entity, a group, a tag, a gender or a book's people), or two to compare, followed slice by slice through one book
   (core/overbook.py, POST /api/overbook). In this order: the words of one relation and the kinds of action of each target (a line chart, then
   a heat grid or numbers, each row with a test of change, chi-squared, and of trend, Cochran-Armitage), a curve of one figure along the book for
   the one or two targets, and an overview per slice. The slices are the shared Measure over setting (S.nar.seg), always counted per book.
   With "Sound of their speech" on (`S.over.sound`, and the pronunciation dictionary installed) every request asks for the sound and rhythm
   figures of the target's speech per slice too: the curve offers them, and the overview gets a table of them. */

const OVER_VIEWS = [["heat", "Heat grid"], ["numbers", "Numbers"]];
const OVER_ORDERS = [["freq", "Most frequent"], ["rising", "Rising"], ["falling", "Falling"], ["changed", "Most changed"]];
const OVER_COLORS = ["#2e4a62", "#c0843a"];          // the first and the second target, as on the Compare page
const OVER_CHART_ROWS = 8;                            // lines in a words or kinds chart: the first rows of the order chosen
/** What is remembered between visits (the targets and the book are not: a target can be a group of dozens of entities). */
S.over = { ...loadState("analyser.over", { rel: "agent", view: "heat", order: "freq", curve: "ov:per1k", al_n: 20, co_n: 20, co_each: false, co_min_range: 1, book: null, al_b_book: null, curve_by: { figures: "ov:per1k" }, curve_rel: "agent", sound: false, kinds: false }),
  target: null, other: null, asking: false,
  al: { a: { target: null }, b: { same: true, target: null } },       // the two sides of Two books aligned
  co: { target: null } };                                               // the target of Books combined
/** Remember the Over-the-book settings (not the targets or the sides of Two books aligned and Books combined). `S.over.book` is the book you last chose, one for the
    whole feature (the page, the profile's panel, Compare and side A of Two books aligned) and kept when the target changes: a target that isn't in it is
    shown in the first book it is in, without forgetting your choice. `S.over.al_b_book` is the same for side B of Two books aligned. */
const saveOver = () => { const { target, other, asking, al, co, ...settings } = S.over; saveState("analyser.over", settings); };

/** The book you last chose, if it is still among the selected books. */
const overBook = () => S.over.book && selected().includes(S.over.book) ? S.over.book : null;
/** Remember the book (or side B's) a response used, unless you had already chosen one; a choice of yours (`force`) is always remembered. */
function overRemember(key, book, force = false) {
  if (force || !S.over[key]) { S.over[key] = book; saveOver(); }
}

/** The sentence "See Over the book for more details." with "Over the book" a link to that page with `target` (and a second one, and the book)
    already chosen: an entity's or group's own `u.target` on its profile page, or both sides of a comparison. `book` can be a function, asked
    when the link is followed (the book a panel shows now). */
const overLink = (target, other = null, book = null) => h("span", {}, "See ",
  h("a", { href: "#/over", title: "Every word and kind of action slice by slice: heat grids, trends and tests, and the sentences behind each cell",
    onclick: () => { Object.assign(S.over, { target, other, asking: !!other }); const b = typeof book === "function" ? book() : book; if (b) overRemember("book", b, true); } }, "Over the book"),
  " for more details.");

/** The link from Compare to Two books aligned, for two sides each in its own book (`books` = {a, b}): it opens that sub-tab with both sides and
    their books chosen. A side without its `books` limit is the target; if both are the same target, side B is "the same as A". */
function overAlignedLink(a, b, books) {
  const bare = ({ books, ...spec }) => spec, [ta, tb] = [bare(a), bare(b)];
  const same = JSON.stringify(ta) === JSON.stringify(tb);
  return h("a", { href: "#/over/aligned", title: "Each side in its own book, cut into the same number of slices: every word and kind of action, with the tests",
    onclick: () => { S.over.al = { a: { target: ta }, b: { same, target: same ? null : tb } }; if (books.a) overRemember("book", books.a, true); if (books.b) overRemember("al_b_book", books.b, true); } }, "Two books aligned");
}

/** What the shared Measure over slicer is set to, in words. */
function overCutText() {
  const g = S.nar.seg;
  return g.mode === "chapters" ? "chapters" : g.slice_by === "words" ? `slices of ${fmt(g.words)} words` : `${g.n} equal slices`;
}

/** Ask the server for one or two targets over one book (`book` null: the first either is in), cut as the shared Measure over slicer says. */
const overFetch = (target, other, book) => api("/api/overbook", withBooks({ target, other, book, seg: { ...S.nar.seg, scope: "book" }, rel: S.over.rel, curve_rel: S.over.curve_rel, sound: overSound(), ...S.stat }));
/** Whether to ask for the sound and rhythm of the targets' speech: switched on, and the dictionary is there. */
const overSound = () => !!(S.over.sound && S.lib.sound);

/** A `#rrggbb` colour as `rgba(…)` with the given opacity, so a heat cell stays readable on a light or a dark page. */
function hexAlpha(hex, alpha) {
  const [r, g, b] = [1, 3, 5].map(k => parseInt(hex.slice(k, k + 2), 16));
  return `rgba(${r},${g},${b},${alpha})`;
}

/** The names of the targets of a response, told apart if they happen to be called the same. */
function overNames(r) {
  const names = [r.a, r.b].filter(Boolean).map(t => t.label);
  return names.length === 2 && names[0] === names[1] ? [names[0] + " (1)", names[1] + " (2)"] : names;
}

/** What a table is of, in words: its book's title, or for a combined table (no `book`) the books it was made from ("9 books", set by the page as `where`). */
const overTitle = t => t.book ? t.book.title : t.where;

/** The slices of a table as `arcChart` wants its segments (a book and a title for each; a combined table is one "book" of its own). */
const overSegments = t => t.segments.map(sg => ({ ...sg, book: t.book ? t.book.id : "all", title: t.book ? t.book.title : `${t.where} combined` }));

/** The overview panel of one table: a row per slice with its words, mentions, how the target is referred to and each relation per 100 mentions. */
function overOverview(a, name) {
  const cols = [
    { k: "index", label: "Slice", csv: (v, row) => row.label,
      fmt: (v, row) => a.book ? h("a", { href: `#/read/${encodeURIComponent(a.book.id)}/${a.segments[v].start}`, title: "Read this slice" }, row.label) : row.label },       // a combined slice is in every book
    { k: "words", label: "Words", num: true, fmt: v => fmt(v) },
    { k: "mentions", label: "Mentions", num: true, fmt: v => fmt(v) },
    { k: "per1k", label: "Per 1,000 words", num: true, fmt: v => fmt(v, 2) },
    { k: "names", label: "Names %", num: true, fmt: v => fmt(v, 1) },
    { k: "descriptions", label: "Descriptions %", num: true, fmt: v => fmt(v, 1) },
    { k: "pronouns", label: "Pronouns %", num: true, fmt: v => fmt(v, 1) },
    ...S.lib.relations.map(rl => ({ k: "rel_" + rl.id, label: rl.label, num: true, fmt: v => fmt(v, 1), title: `${rl.label} per 100 mentions` })),
  ];
  const sound = a.overview.length && "snd" in a.overview[0];
  const sndRows = sound ? a.overview.map(o => ({ index: o.index, label: o.label, speech_words: o.speech_words, ...(o.snd || {}) })) : [];
  const sndCols = [cols[0], { k: "speech_words", label: "Words spoken", num: true, fmt: v => fmt(v) },
    ...(S.lib.sound_figures || []).map(sndColumn)];
  return h("section", { class: "panel" }, h("h2", {}, name ? `${name}: slice by slice` : "Slice by slice"),
    table(cols, a.overview, { limit: 200, csvName: `${a.label} over ${overTitle(a)}` }),
    note("How this is calculated", S.lib.overbook_notes[a.book ? "overview" : "combined_overview"]),
    sound ? [h("h3", { class: "small muted", style: { marginTop: "14px" } }, "Sound and rhythm of their speech"),
      table(sndCols, sndRows, { limit: 200, csvName: `${a.label} speech sound over ${overTitle(a)}`, columns: { ...SND_COLUMNS, id: "sound-over" } }),
      note("How this is calculated", S.lib.overbook_notes.sound, S.lib.narrative_notes.sound)] : null);
}

/** The rows of a words or kinds table: each item with a count (`b<i>`), share (`p<i>`) and residual (`r<i>`) per slice, its highest share
    (`max`, what the heat shading is relative to) and the trend as flat fields (`tz`, `tp`; for combined books also `tn`, `tup`, `tdown`: books used, rising, falling). */
function overRows(rows) {
  return rows.map(x => {
    const t = x.trend, o = { ...x, tz: t ? t.z : null, tp: t ? t.p : null, tn: t ? t.n : null, tup: t ? t.up : null, tdown: t ? t.down : null, max: Math.max(0, ...x.pcts.filter(p => p != null)) };
    x.counts.forEach((c, i) => { o["b" + i] = c; o["p" + i] = x.pcts[i]; o["r" + i] = x.resid[i]; });
    return o;
  });
}

/** The items in the chosen order: as the server lists them (most frequent first), or the tested ones by trend (rising, falling) or by
    chi-squared, followed by the rest in their own order. */
function overOrder(rows, how) {
  const key = { rising: r => r.tz, falling: r => r.tz == null ? null : -r.tz, changed: r => r.chi2 }[how];
  if (!key) return rows;
  const first = rows.filter(r => r.tested && key(r) != null).sort((x, y) => key(y) - key(x));
  const seen = new Set(first);
  return [...first, ...rows.filter(r => !seen.has(r))];
}

/** One cell of the heat grid: shaded by the item's share in the slice (for combined books the mean of the books' shares) relative to its own highest share; faint when it is absent
    from a slice that has other items, hatched when the slice has nothing in this list. Click for the sentences of that slice. */
function overHeatCell(g, row, i, open) {
  const p = row["p" + i], c = row["b" + i], none = p == null;
  const tip = none ? `${g.segs[i].label}: nothing in this list`
    : g.combined ? `${g.segs[i].label}: mean share ${fmt(p, 1)}% (${fmt(c)} of ${fmt(g.totals[i])} in all the books)`
    : `${g.segs[i].label}: ${fmt(c)} of ${fmt(g.totals[i])} (${fmt(p, 1)}%)` + (row["r" + i] == null ? "" : `, adjusted residual ${fmt(row["r" + i], 2)}`);
  return h("span", { class: "hcell" + (none ? " hn" : c ? "" : " hz"), style: c ? { background: hexAlpha(PALETTE[0], 0.12 + 0.88 * p / row.max) } : null, title: tip,
    onclick: e => { e.stopPropagation(); if (c) open(row, i); } });
}

/** One cell of the number columns: the count with its share of the slice's list, tinted blue or red when the adjusted residual is beyond ±1.96. */
function overNumberCell(row, i) {
  const r = row["r" + i];
  return h("span", { class: r == null ? "" : r >= 1.96 ? "rp" : r <= -1.96 ? "rn" : "", title: r == null ? "" : `adjusted residual ${fmt(r, 2)}` },
    row["b" + i] ? `${fmt(row["b" + i])} (${fmt(row["p" + i], 1)}%)` : "·");
}

/** The columns of a grid: the item, a column per slice (heat cells or numbers), its total, the trend (z and p) and chi-squared (χ², p, V).
    For combined books (`g.combined`) the trend is the books' put together and V is replaced by how many books it is made from and how many of them
    rise and fall. `g` = {segs, totals, combined}; `first` is the first column; `open(row, i)` shows the sentences of a cell. */
function overCols(g, first, heat, open) {
  const slices = g.segs.map((sg, i) => ({
    k: "b" + i, num: !heat, cls: heat ? "hc" : "nw", label: heat ? String(i + 1) : sg.label.length > 14 ? sg.label.slice(0, 13) + "…" : sg.label, csvLabel: sg.label,
    title: `${sg.label} (${fmt(sg.words)} words)`,
    fmt: (v, row) => heat ? overHeatCell(g, row, i, open) : overNumberCell(row, i),
    csv: heat ? (v, row) => row["p" + i] == null ? "" : Math.round(row["p" + i] * 1e4) / 1e4 : v => v,
    sortVal: row => row["p" + i],
  }));
  return [first, ...slices,
    { k: "total", label: "Total", num: true, fmt: v => fmt(v) },
    { k: "tz", label: "Trend z", num: true, cls: "nw", title: g.combined ? "Cochran–Armitage in each book, put together with equal weight (Stouffer): positive when the share rises through the books, negative when it falls"
        : "Cochran–Armitage: positive when the share rises through the book, negative when it falls",
      fmt: (v, row) => v == null ? "—" : h("span", { class: row.trend_sig ? (v > 0 ? "rp" : "rn") : "" }, (row.trend_sig ? (v > 0 ? "↑ " : "↓ ") : "") + fmt(v, 2)) },
    { k: "tp", label: "Trend p", num: true, fmt: fmtP, sortVal: row => row.tp == null ? -2 : -row.tp },
    { k: "chi2", label: "χ²", num: true, title: g.combined ? "Does the share differ between slices within the books? (each book's χ², added up)" : "Does the share differ between slices?",
      fmt: v => v == null ? "—" : fmtSig(v) },
    { k: "p", label: "χ² p", num: true, fmt: fmtP, sortVal: row => row.p == null ? -2 : -row.p },
    ...(g.combined ? [
      { k: "tn", label: "Books", num: true, title: "Books the trend is made from: those where the item is in the list and not in all of it", fmt: v => v == null ? "—" : fmt(v) },
      { k: "tup", label: "Rising", num: true, title: "Books where the share rises (trend z above 0)", fmt: v => v == null ? "—" : fmt(v) },
      { k: "tdown", label: "Falling", num: true, title: "Books where the share falls (trend z below 0)", fmt: v => v == null ? "—" : fmt(v) }]
      : [{ k: "v", label: "Cramér's V", num: true, fmt: v => v == null ? "—" : fmt(v, 3) }])];
}

/** A line chart of the first rows of a grid (in the order shown): each item's share of the slice's list along the book. */
function overLines(a, rows, g, label) {
  const series = rows.slice(0, OVER_CHART_ROWS).map((x, i) => ({ name: label(x.item), color: PALETTE[i % PALETTE.length], values: x.pcts, counts: x.counts }));
  return series.length ? chartBox(arcChart(overSegments(a), series, { ylabel: "share of the slice's list (%)" }), `${slug(a.label)}-${g.id}-over-${slug(overTitle(a))}`)
    : h("p", { class: "muted small" }, "Nothing to chart at these settings.");
}

/** What a grid panel needs besides the table: for the words of the chosen relation, or for the kinds of action. */
function overSources(a) {
  const rel = S.lib.relations.find(x => x.id === a.rel);
  return {
    words: { id: "words", rows: a.rows, totals: a.totals, summary: a.summary, kind: a.rel, noun: "word", item: "Word", name: x => x, subject: rel.label, note: "words" },
    kinds: { id: "kinds", rows: a.supersenses.rows, totals: a.supersenses.totals, summary: a.supersenses.summary, kind: "supersense", noun: "kind",
      item: "Kind of action", name: x => x.replace(/^(verb|noun)\./, ""), subject: "Actions", note: "kinds" },
  };
}

/** The test settings of a words panel: the shared ones (minimum frequency, level, Bonferroni) and, for combined books, the fewest books a word must
    occur in to be tested (`S.over.co_min_range`, put after the minimum frequency). `rerun` asks again. */
function overTestControls(combined, rerun) {
  const shared = acrossControls(rerun);
  if (combined) shared.splice(1, 0, h("label", { title: "Range: a word is tested only when it occurs in at least this many books" }, "Minimum range for the test",
    h("input", { type: "number", min: 1, value: S.over.co_min_range, onchange: e => { S.over.co_min_range = Math.max(1, Math.round(+e.target.value) || 1); e.target.value = S.over.co_min_range; saveOver(); rerun(); } })));
  return shared;
}

/** The grid section of one target (AD-37): a tab per word list and one for the kinds of action (`S.over.kinds`), then one quiet row of
    controls (view, order, test settings), the summary, the chart, the grid and the explanation. `spec` is the target, `name` its name when
    there are two. `redraw` shows the page again as it is; `rerun` fetches again (a word list is asked of the server; the kinds of action
    come with every answer). */
function overGrid(a, spec, name, redraw, rerun) {
  const set = S.over, src = overSources(a)[set.kinds ? "kinds" : "words"];
  const s = src.summary, heat = set.view === "heat", words = src.id === "words";
  const combined = !a.book, title = overTitle(a);
  const g = { id: src.id, segs: a.segments, totals: src.totals, combined }, last = a.segments[a.segments.length - 1];
  const evidence = (row, within, where) => openEvidence(`${src.subject}: ${src.name(row.item)}`, `${a.label}, ${where} of ${title}`, { target: spec, kind: src.kind, key: row.item, within });
  // the stretch of a slice: in the one book, or (combined) in each of the books; the whole: the whole book, or (combined) no limit at all
  const stretch = i => combined ? a.segments[i].ranges : { book: a.book.id, start: a.segments[i].start, end: a.segments[i].end };
  const open = (row, i) => evidence(row, stretch(i), a.segments[i].label);
  const rows = overOrder(overRows(src.rows), set.order);
  const first = { k: "item", label: src.item, fmt: v => src.name(v), csv: v => v };
  const box = h("section", { class: "panel" }, helpHead("h2", name ? `${name}: ${OVER_GRID_HEADING.toLowerCase()}` : combined ? OVER_GRID_HEADING.replace("the book", "the books") : OVER_GRID_HEADING, "over", "grids"));
  box.append(
    h("div", { class: "subtabs" }, S.lib.relations.map(rl => h("button", { class: !set.kinds && rl.id === a.rel ? "on" : "", onclick: () => { set.kinds = false; set.rel = rl.id; saveOver(); rl.id === a.rel ? redraw() : rerun(); } }, rl.label)),
      h("button", { class: set.kinds ? "on" : "", title: "The verbs it is the subject of, grouped by their WordNet supersense", onclick: () => { set.kinds = true; saveOver(); redraw(); } }, "Kinds of action")),
    h("div", { class: "controls" },
      h("div", { class: "fld" }, "View", seg(OVER_VIEWS, set.view, v => { set.view = v; saveOver(); redraw(); })),
      h("label", {}, "Order", h("select", { onchange: e => { set.order = e.target.value; saveOver(); redraw(); } }, OVER_ORDERS.map(([v, l]) => h("option", { value: v, selected: v === set.order }, l)))),
      overTestControls(combined, rerun)),
    combined ? freqLine() : null);
  box.append(
    h("p", { class: "small muted" }, `${src.subject} in ${plural(a.segments.length, "slice")} of ${combined ? "each of " : ""}${title}: ${fmt(src.totals.reduce((x, y) => x + y, 0))} in all. ` +
      `${plural(words ? a.distinct : src.rows.length, "different " + src.noun)}; ${plural(s.tested, src.noun)} with ${needed(s)} tested: ` +
      `${fmt(s.significant)} differ between slices (χ²), ${fmt(s.trending)} rise or fall steadily (trend).`),
    overLines(a, rows, g, src.name),
    h("div", { class: "hgrid" }, table(overCols(g, first, heat, open), rows,
      { limit: 40, columns: false, csvName: `${a.label} ${words ? a.rel : "kinds of action"} over ${title} ${heat ? "shares" : "counts"}`, rowClass: row => row.tested ? "" : "dim",
        onRow: row => evidence(row, combined ? undefined : { book: a.book.id, start: 0, end: last.end }, "all"), empty: "Nothing in this list at these settings." })),
    note("How this is calculated", ...(combined ? [words ? null : S.lib.overbook_notes.kinds, S.lib.overbook_notes.combined] : [S.lib.overbook_notes[src.note]])));
  return box;
}

const OVER_GRID_HEADING = "Words over the book";           // the grid section's heading, whichever list or the kinds of action it shows
const OVER_CATS = [["figures", "Figures"], ["words", "Words"], ["actions", "Actions"], ["sound", "Sound of speech"]];
/** The relation whose words the curve offers: the one the response was asked for (`curve_rel`), which need not be the one of the words panels. */
const overCurveRel = tables => (tables[0].curve_words || tables[0]).rel;
/** The measures the curve can show, by category: {figures, words, actions}, each a list of [value, label]. Figures are the overview's; words are every
    word of the curve's list, and actions every kind of action, either table has; sound the sound and rhythm figures of the targets' speech, when
    they were asked for. A value is `ov:<overview field>`, `rel:<relation>`, `word:<relation>:<word>`, `kind:<supersense>` or `snd:<figure>`. */
function overMeasures(tables) {
  const items = rows => [...new Set(tables.flatMap(rows))];
  const rel = overCurveRel(tables);
  return {
    figures: [["ov:per1k", "Mentions per 1,000 words"], ["ov:names", "Names (% of mentions)"], ["ov:descriptions", "Descriptions (% of mentions)"], ["ov:pronouns", "Pronouns (% of mentions)"],
      ...S.lib.relations.map(rl => ["rel:" + rl.id, `${rl.label} per 100 mentions`])],
    words: items(t => (t.curve_words || t).rows.map(x => x.item)).slice(0, 100).map(w => [`word:${rel}:${w}`, w]),
    actions: items(t => t.supersenses.rows.map(x => x.item)).map(k => ["kind:" + k, k.replace(/^(verb|noun)\./, "")]),
    sound: tables[0].overview.length && "snd" in tables[0].overview[0] ? (S.lib.sound_figures || []).map(f => ["snd:" + f.k, f.label]) : [],
  };
}
/** The category a measure belongs to (a key of `overMeasures`). */
const overCategory = measure => measure.startsWith("word:") ? "words" : measure.startsWith("kind:") ? "actions" : measure.startsWith("snd:") ? "sound" : "figures";

/** One figure of a table along its slices: `measure` as in `overMeasures`. An item the table lacks is 0 where the slice has a list, else a gap (null);
    a word of another relation than the table's curve list is a gap throughout. */
function overValues(t, measure) {
  const i = measure.indexOf(":"), kind = measure.slice(0, i);
  let key = measure.slice(i + 1), src = t.supersenses;
  if (kind === "ov") return t.overview.map(o => o[key]);
  if (kind === "snd") return t.overview.map(o => o.snd ? o.snd[key] : null);
  if (kind === "rel") return t.overview.map(o => o["rel_" + key]);
  if (kind === "word") {
    const j = key.indexOf(":"), rel = key.slice(0, j);
    key = key.slice(j + 1); src = t.curve_words || t;
    if (src.rel !== rel) return t.segments.map(() => null);
  }
  const row = src.rows.find(x => x.item === key);
  return t.segments.map((_, k) => row ? row.pcts[k] : src.totals[k] ? 0 : null);
}

const OVER_FIGURE = /^(ov:\w+|rel:\w+|word:\w+:|kind:.|snd:\w+)/;           // what a figure of the curve looks like (an older saved choice may not)
const OVER_WORDS = 100;                                            // words the curve's Words list holds, as core/overbook.py's MEASURE_WORDS
/** What the Words list of the curve holds, in a sentence: the words of the curve's list (as the tables list them, most frequent first) of one target,
    or of two (the first's, then the second's that aren't the first's), at most `OVER_WORDS` of them. `names` are the targets' names. */
function overWordsNote(tables, names) {
  const list = S.lib.relations.find(x => x.id === overCurveRel(tables)).label;
  return tables.length > 1
    ? `Words in the “${list}” list that ${names[0]} or ${names[1]} has: ${names[0]}'s, most frequent first, then ${names[1]}'s that ${names[0]} doesn't have (the first ${OVER_WORDS}).`
    : `Words in the “${list}” list that ${names[0]} has, most frequent first (the first ${OVER_WORDS}).`;
}

/** How alike two curves are (`similarity` of one figure from the server): Pearson's r and Spearman's rho with p, over the slices with a value on both sides. */
function overSimilarity(s) {
  if (!s) return null;
  const part = (sym, c) => c.r == null ? `${sym} —` : `${sym} = ${fmt(c.r, 2)} (p ${fmtP(c.p)})`;
  return h("p", { class: "small" }, h("b", {}, "How alike the curves are: "), s.pearson.r == null && s.spearman.r == null
    ? `not defined over ${plural(s.pearson.n, "slice")} with a value on both sides (it needs at least 3, and a curve that is not flat).`
    : `Pearson's ${part("r", s.pearson)}, Spearman's ${part("ρ", s.spearman)}, over ${plural(s.pearson.n, "slice")} with a value on both sides.`);
}

/** The contents of the curve: one figure along the book for the one or two targets (a line each), chosen from a category (Figures, Words, Actions) and a
    list, with the numbers beside it. The words come from a list (actions, done to them…) chosen here, apart from the one of the words panels: changing it asks
    again (`opts.rerun`, else just draws again). `opts.aligned`: the two targets are in different books, cut into the same number of slices (Two books aligned):
    no slice opens the text, the chart is titled by position, and the similarity of the two curves (`r.similarity`) is shown under it. `opts.names` are the lines' names.
    `opts.each` (Books combined, where the table has no book): {on, lines, requested, toggle(on), refine(figure)} adds the switch "Show each book", which draws each book's
    own values (`lines`: [{title, values}], asked for the figure `requested`) faintly behind the combined line; with it on, choosing another figure asks again (`rerun`),
    and a figure other than the one asked for (the one chosen is not in these books' lists) is handed to `refine`. */
function overCurveBody(r, redraw, opts = {}) {
  const tables = [r.a, r.b].filter(Boolean), names = opts.names || overNames(r), cats = overMeasures(tables), aligned = !!opts.aligned, each = opts.each;
  const again = () => (each && each.on ? opts.rerun : redraw)();            // a figure's own books' values are asked for
  const known = Object.values(cats).flat(), set = S.over, intent = overCategory(set.curve), curveRel = overCurveRel(tables);
  const measure = known.some(([v]) => v === set.curve) ? set.curve : intent === "words" && cats.words.length ? cats.words[0][0]
    : intent === "actions" && cats.actions.length ? cats.actions[0][0] : "ov:per1k";
  const noWords = intent === "words" && !cats.words.length;               // the list chosen has no words for these targets: the controls stay, to change it
  const cat = noWords ? "words" : overCategory(measure), listLabel = S.lib.relations.find(x => x.id === curveRel).label;
  // a category (as the entity picker's types) and, for it, a list: each category remembers its own item
  const choose = value => { set.curve = value; set.curve_by[overCategory(value)] = value; saveOver(); again(); };
  const catSeg = seg(OVER_CATS.filter(([k]) => k === "words" || cats[k].length), cat, k => {
    const last = set.curve_by[k];
    if (k === "words" && !cats.words.length) { set.curve = `word:${curveRel}:`; saveOver(); again(); }
    else choose(cats[k].some(([v]) => v === last) ? last : cats[k][0][0]);
  });
  const listPick = cat !== "words" ? null : h("select", { "aria-label": "List", title: "Which list the words are from (apart from the one of Words over the book)",
    onchange: e => { set.curve_rel = e.target.value; set.curve = `word:${e.target.value}:`; set.curve_by.words = null; saveOver(); (opts.rerun || redraw)(); } },
    S.lib.relations.map(rl => h("option", { value: rl.id, selected: rl.id === curveRel }, rl.label)));
  const pick = noWords ? null : h("select", { "aria-label": OVER_CATS.find(([k]) => k === cat)[1], onchange: e => choose(e.target.value) },
    cats[cat].map(([v, l]) => h("option", { value: v, selected: v === measure }, l)));
  const controls = h("div", { class: "controls" }, h("div", { class: "fld" }, "Show", h("div", { class: "picker" }, catSeg, listPick, pick,
    cat === "words" ? h("span", { class: "muted small", style: { flex: "1 1 260px" } }, noWords ? `No words in the “${listLabel}” list for ${names.join(" or ")}.` : overWordsNote(tables, names)) : null)),
    each ? h("label", { class: "inline", title: "Draw each book's own line faintly behind the combined one" },
      h("input", { type: "checkbox", checked: each.on, onchange: e => each.toggle(e.target.checked) }), "Show each book") : null,
    S.lib.sound ? h("label", { class: "inline", title: "Also measure the sound and rhythm of what the target says in each slice (stress, cadences, alliteration…): a Sound of speech list here, and a table under the overview" },
      h("input", { type: "checkbox", checked: !!set.sound, onchange: e => { set.sound = e.target.checked; saveOver(); (opts.rerun || redraw)(); } }), "Sound of their speech") : null);
  if (noWords) return [controls];
  const label = known.find(([v]) => v === measure)[1];
  const pct = /^(ov:(names|descriptions|pronouns)|word|kind)/.test(measure);
  const series = tables.map((t, i) => ({ name: names[i], color: OVER_COLORS[i], values: overValues(t, measure) }));
  // each book's own line, faint and behind: only when they were asked for this very figure (else the page is asked to fetch them)
  const faint = each && each.on && each.lines && each.requested === measure ? each.lines.map(b => ({ name: b.title, color: OVER_COLORS[0], values: b.values, faint: true })) : [];
  if (each && each.on && each.lines && each.requested !== measure) each.refine(measure);
  const read = (v, row) => aligned || !r.a.book ? v : h("a", { href: `#/read/${encodeURIComponent(r.a.book.id)}/${row.start}`, title: "Read this slice" }, v);
  const cols = [{ k: "label", label: "Slice", fmt: read, csv: v => v },
    ...series.map((s, i) => ({ k: "s" + i, label: s.name, num: true, fmt: v => v == null ? "—" : fmt(v, 2) }))];
  const rows = r.a.segments.map((sg, k) => ({ label: sg.label, start: sg.start, ...Object.fromEntries(series.map((s, i) => ["s" + i, s.values[k]])) }));
  const segs = overSegments(r.a).map(sg => aligned ? { ...sg, title: "Position in the book" } : sg);
  const where = aligned ? "" : ` over ${overTitle(r.a)}`;
  return [controls,
    chartBox(arcChart(segs, [...faint, ...series], { ylabel: label + (pct ? " (%)" : "") }), `over-${slug(label)}-${aligned ? "aligned" : slug(overTitle(r.a))}`),
    aligned ? overSimilarity(r.similarity && r.similarity[measure]) : null,
    foldTable("Numbers per slice", table(cols, rows, { limit: 200, csvName: `${names.join(" vs ")} ${label}${where}` })),
    note("How this is calculated", S.lib.overbook_notes[r.a.book ? "curve" : "combined_curve"], aligned ? S.lib.overbook_notes.similarity : null)];
}

/** The curve panel of the page. */
const overCurve = (r, redraw, rerun) => h("section", { class: "panel" }, helpHead("h2", "Along the book", "over", "curve"), overCurveBody(r, redraw, { rerun }));

/** A panel that fetches by itself (the profile's and Compare's): `ask(book)` gives the response, `draw(r, again)` the contents for it, `again(book)`
    asks again. While it asks anew the contents stay on the page, dimmed. */
function overPanel(ask, draw) {
  const out = h("div", {}, loading("Counting slice by slice…"));
  let shown = null;                                  // the book the answer used
  const run = async chosen => {
    if (chosen !== undefined) overRemember("book", chosen, true);
    if (out.querySelector("section, .chart-box")) out.classList.add("busy");
    let r;
    try { r = await ask(overBook()); } catch (e) { out.classList.remove("busy"); throw e; }
    out.classList.remove("busy");
    if (!r.a) { out.replaceChildren(h("p", { class: "muted small" }, "Not in any of the selected books.")); return; }
    shown = r.book;
    overRemember("book", r.book);
    const redraw = () => out.replaceChildren(draw(r, run, redraw));
    redraw();
  };
  run();
  return { out, run, book: () => shown };
}

/** The book switch of a response (when the target or targets are in several selected books), or null. */
const overBookPick = (r, again) => r.books.length < 2 ? null :
  h("div", { class: "controls" }, h("label", {}, "Book", h("select", { onchange: e => again(e.target.value) }, r.books.map(b => h("option", { value: b.id, selected: b.id === r.book }, b.title)))));

/** The "Over the book" preview on an entity's, group's, book's or gender's profile (AL-PRIN-13: the page is its one home): how often it is
    mentioned, slice by slice through a book, the book switch, how the book is cut ("Based on", which opens the slicer in place), and a link
    to the Over the book page, where its words and kinds of action are, with the heat grids, trends and tests. */
function overProfile(u) {
  const box = h("section", { class: "panel" }, helpHead("h2", "Over the book", "entity", "over"));
  const cut = h("summary", {}), slicer = h("div");
  let panel;
  const drawSlicer = () => {
    const g = S.nar.seg, changed = g.mode !== "slices" || g.slice_by !== "count" || g.n !== 10;
    cut.replaceChildren(basedOn([{ text: `cut into ${overCutText()}`, set: changed, title: "Click to change how the book is cut (shared with the Style and Over time pages)" }]));
    slicer.replaceChildren(segControl(() => { drawSlicer(); panel.run(); }, { timeline: false }));
  };
  panel = overPanel(book => overFetch(u.target, null, book), (r, again) => {
    const a = r.a;
    return [overBookPick(r, again),
      chartBox(arcChart(overSegments(a), [{ name: u.name, color: OVER_COLORS[0], values: a.overview.map(o => o.per1k) }], { ylabel: "mentions per 1,000 words" }), `${slug(u.name)}-presence-over-${slug(a.book.title)}`)];
  });
  drawSlicer();
  box.append(h("p", { class: "small muted", style: { marginTop: 0 } }, `How often ${u.name} is mentioned, per 1,000 words, from the start of ${u.books.length > 1 ? "a book" : "the book"} to its end (their words and kinds of action are on the page). `,
      overLink(u.target, null, panel.book)),
    h("details", { class: "note", style: { marginTop: 0 } }, cut, slicer), panel.out);
  return box;
}

/** The "Over the book" section of the Compare page: one figure along a book for both sides (a line each, chosen from a list) and the numbers beside
    it, with a link (at the top) to the page that has everything slice by slice. `a` and `b` are the two sides' specs. When some book holds both sides
    they are measured in it (a book switch); when none does (two entities of different books, or sides limited to different books) a book holding
    only one would show the other as nothing, so each is measured in its own book, lined up by relative position, with how alike the curves are. */
function overCompare(a, b) {
  const box = h("section", { class: "panel" }, h("h2", {}, "Over the book"));
  const intro = h("p", { class: "small muted", style: { marginTop: 0 } }), out = h("div", {}, loading("Counting slice by slice…"));
  const st = { book: null, bookB: null };            // the book both are measured in, or side A's and side B's own, as the last answer used them
  const setIntro = mode => intro.replaceChildren(mode === "aligned"
    ? ["No book holds both sides, so each is measured in its own book, lined up by relative position: slice k of n is the same stretch of each. See ", overAlignedLink(a, b, { a: st.book, b: st.bookB }), " for every word and kind of action."]
    : [`Both sides are measured in the same book, chosen here, cut as set under Measure over: ${overCutText()}. `, overLink(a, b, () => st.book)]);
  const same = (r, redraw) => [overBookPick(r, id => { overRemember("book", id, true); run(); }), overCurveBody(r, redraw, { rerun: run })];
  const alone = (r, redraw) => {
    const names = [r.a, r.b].map(t => `${t.label} (${t.book.title})`);
    const pick = (list, now, set) => list.length > 1 ? h("select", { onchange: e => { set(e.target.value); run(); } }, list.map(x => h("option", { value: x.id, selected: x.id === now }, x.title))) : h("b", {}, list[0].title);
    return [h("div", { class: "controls" },
      h("label", {}, "Side A book", pick(r.books_a, r.book_a, v => overRemember("book", v, true))), h("label", {}, "Side B book", pick(r.books_b, r.book_b, v => overRemember("al_b_book", v, true))),
      h("label", { title: "Both books are cut into this many equal slices" }, "Slices per book",
        h("input", { type: "number", min: 2, max: 200, value: S.over.al_n, onchange: e => { S.over.al_n = Math.min(200, Math.max(2, Math.round(+e.target.value) || 20)); e.target.value = S.over.al_n; saveOver(); run(); } }))),
      overCurveBody(r, redraw, { aligned: true, names, rerun: run })];
  };
  const run = async () => {
    if (out.querySelector(".chart-box")) out.classList.add("busy");
    let r;
    try { r = await api("/api/overbook/compare", withBooks({ target: a, other: b, book: overBook(), other_book: S.over.al_b_book, seg: { ...S.nar.seg, scope: "book" }, n: S.over.al_n, rel: S.over.rel, curve_rel: S.over.curve_rel, sound: overSound(), ...S.stat })); }
    catch (e) { out.classList.remove("busy"); throw e; }
    out.classList.remove("busy");
    if (!r.a) { out.replaceChildren(h("p", { class: "muted small" }, "Not in any of the selected books.")); return; }
    Object.assign(st, r.mode === "aligned" ? { book: r.book_a, bookB: r.book_b } : { book: r.book, bookB: null });
    overRemember("book", st.book);
    if (st.bookB) overRemember("al_b_book", st.bookB);
    const redraw = () => out.replaceChildren((r.mode === "aligned" ? alone : same)(r, redraw));
    setIntro(r.mode);
    redraw();
  };
  setIntro("same");
  run();
  box.append(intro, out);
  return box;
}

const OVER_SUBS = [["", "Within a book"], ["aligned", "Two books aligned"], ["combined", "Books combined"]];
/** The sub-tabs of the Over the book page (`sub` is the open one: "", "aligned" or "combined"), each its own address. */
const overTabs = sub => h("div", { class: "subtabs", style: { marginBottom: "10px" } },
  OVER_SUBS.map(([k, label]) => h("button", { class: k === (sub || "") ? "on" : "", onclick: () => { location.hash = "#/over" + (k ? "/" + k : ""); } }, label)));

/** The Over the book page: `sub` "aligned" is Two books aligned, "combined" is Books combined, anything else a target within one book. */
async function renderOverbook(main, sub) {
  await units();
  await ({ aligned: overAligned, combined: overCombined }[sub] || overSingle)(main, overTabs(sub));
}

/** Within a book: one target, or two to compare, slice by slice through one book. */
async function overSingle(main, tabs) {
  const o = S.over, out = h("div"), targetOpts = { group: true, book: true, gender: true };
  o.target = followFocus("over/single", o.target, targetOpts);                    // the target follows the focus, if shared (focus.js)
  const show = r => {
    const pick = h("select", { onchange: e => { overRemember("book", e.target.value, true); run(); } }, r.books.map(b => h("option", { value: b.id, selected: b.id === r.book }, b.title)));
    const two = !!r.b, specs = [o.target, o.other], names = overNames(r), redraw = () => show(r);
    out.replaceChildren(
      h("section", { class: "panel" }, h("div", { class: "controls" },
        r.books.length > 1 ? h("label", {}, "Book", pick) : h("span", {}, h("b", {}, r.a.book.title)),
        h("span", { class: "muted small" }, `${names.join(" and ")}: ${plural(r.a.segments.length, r.a.info && r.a.info.mode === "chapters" ? "chapter" : "slice")}.`)),
        r.a.info && r.a.info.fallback ? h("p", { class: "warn small" }, "No chapters were found in this book, so it is cut into slices (see the setting above).") : null,
        two ? h("p", { class: "small muted", style: { margin: "4px 0 0" } }, `${names[1]} leaves out everything ${names[0]} includes, as in Compare.`) : null),
      overCurve(r, redraw, run),                                        // the curve first: the quickest answer (AD-37)
      [r.a, r.b].filter(Boolean).map((t, i) => overGrid(t, specs[i], two ? names[i] : null, redraw, run)),
      [r.a, r.b].filter(Boolean).map((t, i) => overOverview(t, two ? names[i] : null)));
    out.classList.remove("busy");
  };
  const run = async () => {
    if (!o.target) { out.classList.remove("busy"); out.replaceChildren(h("div", { class: "panel empty" }, "Choose an entity, a group, a tag or a gender to follow through a book.")); return; }
    const [target, other] = [o.target, o.other];
    // What is on the page stays (dimmed) until the new answer replaces it: emptying it would shorten the page and send the reader back to the top.
    if (out.querySelector("section")) out.classList.add("busy"); else out.replaceChildren(loading("Counting slice by slice…"));
    let r;
    try { r = await overFetch(target, other, overBook()); }
    catch (e) { out.classList.remove("busy"); throw e; }
    if (o.target !== target || o.other !== other) return;            // a newer pick is already on its way
    if (!r.a) { out.classList.remove("busy"); out.replaceChildren(h("div", { class: "panel warn" }, `${specLabel(target)} isn't in any of the selected books.`)); return; }
    overRemember("book", r.book);
    show(r);
  };
  // the slicer changes its own fields (Slices by words shows the words per slice), so it is drawn again with every change, as the Arcs pages do
  const slicer = h("div");
  const drawSlicer = () => slicer.replaceChildren(segControl(() => { drawSlicer(); run(); }, { timeline: false }));
  drawSlicer();
  // the optional second target
  const second = h("div", { class: "fld" });
  const drawSecond = () => second.replaceChildren(o.other || o.asking
    ? [h("span", {}, "Compare with"), picker(o.other, v => { o.other = v; run(); }, { group: true, book: true, gender: true }),
      h("button", { class: "btn small", style: { alignSelf: "flex-start" }, onclick: () => { o.other = null; o.asking = false; drawSecond(); run(); } }, "Remove")]
    : h("button", { class: "btn small", title: "Draw a second entity, group, tag or gender beside the first", onclick: () => { o.asking = true; drawSecond(); } }, "Compare with…"));
  drawSecond();
  main.replaceChildren(
    h("section", { class: "panel" }, tabs, h("h2", {}, "Over the book"),
      h("p", { class: "small muted", style: { marginTop: 0 } }, "Follow an entity, group, tag or gender through one book, slice by slice: how often it appears, and how what it does, " +
        "what is done to it and how it is described change from the start of the book to its end. Add a second one to compare them. The slices are the ones set under Measure over (shared with Style and Arcs)."),
      h("div", { class: "controls" }, h("div", { class: "fld" }, "Target", subjectPicker("over/single", o.target, v => { o.target = v; run(); }, targetOpts)), second),
      slicer),
    out);
  run();
}

/** Two books aligned: a target in one book against the same or another target in another book, cut into the same number of equal slices so that
    slice k of n is the same relative stretch of each (`/api/overbook/aligned`). The sides are `S.over.al`; the number of slices is the page's own. */
async function overAligned(main, tabs) {
  const o = S.over, al = o.al, out = h("div");
  al.a.target = followFocus("over/aligned", al.a.target, { group: true, book: true, gender: true });     // side A follows the focus, if shared
  let ticket = 0;
  const specs = () => [al.a.target, al.b.same ? al.a.target : al.b.target];
  const show = r => {
    const names = [r.a, r.b].map(t => `${t.label} (${t.book.title})`), redraw = () => show(r), sides = specs();
    const bookPick = (list, now, onPick) => list.length > 1 ? h("select", { onchange: e => onPick(e.target.value) }, list.map(b => h("option", { value: b.id, selected: b.id === now }, b.title))) : h("b", {}, list[0].title);
    out.replaceChildren(
      h("section", { class: "panel" }, h("div", { class: "controls" },
        h("label", {}, "Side A book", bookPick(r.books_a, r.book_a, v => { overRemember("book", v, true); run(); })),
        h("label", {}, "Side B book", bookPick(r.books_b, r.book_b, v => { overRemember("al_b_book", v, true); run(); }))),
        h("p", { class: "small muted", style: { margin: "4px 0 0" } }, `${names[0]} against ${names[1]}, each book cut into ${plural(r.n, "slice")}.`),
        note("How the books are aligned", S.lib.overbook_notes.aligned)),
      h("section", { class: "panel" }, h("h2", {}, "Along the book"), overCurveBody(r, redraw, { aligned: true, names, rerun: run })),
      [r.a, r.b].map((t, i) => overGrid(t, sides[i], names[i], redraw, run)),
      [r.a, r.b].map((t, i) => overOverview(t, names[i])));
    out.classList.remove("busy");
  };
  const say = (text, cls = "panel empty") => { out.classList.remove("busy"); out.replaceChildren(h("div", { class: cls }, text)); };
  const run = async () => {
    const [ta, tb] = specs();
    if (!ta) { say("Choose an entity, a group, a tag or a gender for side A."); return; }
    if (!tb) { say("Choose a target for side B, or tick “Same target as A”."); return; }
    const mine = ++ticket;
    if (out.querySelector("section")) out.classList.add("busy"); else out.replaceChildren(loading("Counting slice by slice…"));
    let r;
    try { r = await api("/api/overbook/aligned", withBooks({ target: ta, book: overBook(), other: al.b.same ? null : tb, other_book: o.al_b_book, n: o.al_n, rel: o.rel, curve_rel: o.curve_rel, sound: overSound(), ...S.stat })); }
    catch (e) { if (mine === ticket) out.classList.remove("busy"); throw e; }
    if (mine !== ticket) return;                                     // a newer request is already on its way
    if (!r.a) { say(`${specLabel(r.books_a.length ? tb : ta)} isn't in any of the selected books.`, "panel warn"); return; }
    overRemember("book", r.book_a); overRemember("al_b_book", r.book_b);
    show(r);
  };
  const pickers = { group: true, book: true, gender: true };
  const sideB = h("div", { class: "fld" });
  const drawB = () => sideB.replaceChildren(h("span", {}, "Side B"),
    h("label", { class: "inline" }, h("input", { type: "checkbox", checked: al.b.same, onchange: e => { al.b.same = e.target.checked; drawB(); run(); } }), "Same target as A"),
    al.b.same ? null : picker(al.b.target, v => { al.b.target = v; run(); }, pickers));
  drawB();
  main.replaceChildren(
    h("section", { class: "panel" }, tabs, h("h2", {}, "Two books aligned"),
      h("p", { class: "small muted", style: { marginTop: 0 } }, "Compare a target in one book with the same target, or another, in another book, lined up by relative position: slice k of n is the same " +
        "stretch of each book, whatever its length. Choose the target of each side, then each side's book below."),
      h("div", { class: "controls" },
        h("div", { class: "fld" }, "Side A", subjectPicker("over/aligned", al.a.target, v => { al.a.target = v; run(); }, pickers)), sideB,
        h("label", { title: "Both books are cut into this many equal slices" }, "Slices per book",
          h("input", { type: "number", min: 2, max: 200, value: o.al_n, onchange: e => { o.al_n = Math.min(200, Math.max(2, Math.round(+e.target.value) || 20)); e.target.value = o.al_n; saveOver(); run(); } })))),
    out);
  run();
}

/** Books combined: one target through every selected book that holds it, each cut into the same number of equal slices and every book weighing the same
    (`/api/overbook/combined`): its words and kinds of action with the books' trends put together, one figure along the books (with each book's own line on
    request) and an overview. The target is `S.over.co`; the number of slices per book is the page's own (`S.over.co_n`). */
async function overCombined(main, tabs) {
  const o = S.over, co = o.co, out = h("div"), targetOpts = { group: true, book: true, gender: true };
  co.target = followFocus("over/combined", co.target, targetOpts);               // the target follows the focus, if shared (focus.js)
  let ticket = 0, asked = null;                       // the newest request; the figure the last answer holds each book's own values of
  const show = r => {
    const a = r.a, redraw = () => show(r), titles = list => list.map(b => b.title).join(", ");
    a.where = plural(r.books.length, "book");
    const each = { on: o.co_each, lines: r.per_book, requested: asked, toggle: on => { o.co_each = on; saveOver(); on ? run() : redraw(); }, refine: figure => ask(figure) };
    out.replaceChildren(
      h("section", { class: "panel" },
        h("p", { class: "small", style: { margin: 0 } }, `${a.label} is in ${r.books.length} of the ${selected().length} selected books, each cut into ${plural(r.n, "slice")}; every book weighs the same.`),
        h("details", { class: "note", style: { marginTop: "6px" } }, h("summary", {}, "Books used" + (r.skipped.length ? ` and left out (${r.skipped.length})` : "")),
          h("p", {}, titles(r.books)), r.skipped.length ? h("p", { class: "muted" }, `Not in: ${titles(r.skipped)}`) : null)),
      h("section", { class: "panel" }, h("h2", {}, "Along the books"), overCurveBody(r, redraw, { rerun: run, each })),
      overGrid(a, co.target, null, redraw, run),
      overOverview(a, null));
    out.classList.remove("busy");
  };
  const say = (text, cls = "panel empty") => { out.classList.remove("busy"); out.replaceChildren(h("div", { class: cls }, text)); };
  /** Ask for the target through the books; `figure` is the one whose books' own values are wanted (only asked for while they are shown). */
  const ask = async figure => {
    const target = co.target;
    if (!target) { say("Choose an entity, a group, a tag or a gender to follow through all the selected books."); return; }
    const mine = ++ticket, want = OVER_FIGURE.test(figure) ? figure : "ov:per1k";
    if (out.querySelector("section")) out.classList.add("busy"); else out.replaceChildren(loading("Counting slice by slice…"));
    let r;
    try { r = await api("/api/overbook/combined", withBooks({ target, n: o.co_n, rel: o.rel, curve_rel: o.curve_rel, curve: o.co_each ? want : null, min_range: o.co_min_range, sound: overSound(), ...S.stat })); }
    catch (e) { if (mine === ticket) out.classList.remove("busy"); throw e; }
    if (mine !== ticket) return;                      // a newer request is already on its way
    if (!r.a) { say(`${specLabel(target)} isn't in any of the selected books.`, "panel warn"); return; }
    asked = o.co_each ? want : null;
    show(r);
  };
  const run = () => ask(o.curve);
  main.replaceChildren(
    h("section", { class: "panel" }, tabs, h("h2", {}, "Books combined"),
      h("p", { class: "small muted", style: { marginTop: 0 } }, "Follow an entity, group, tag or gender through all the selected books at once, to see what holds across them: every book is cut into the same number of " +
        "equal slices, so slice k of n is the same stretch of each whatever its length, and the books are put together slice by slice, each weighing the same. " +
        "The books it is in are used; change the selection above to use others."),
      h("div", { class: "controls" }, h("div", { class: "fld" }, "Target", subjectPicker("over/combined", co.target, v => { co.target = v; run(); }, targetOpts)),
        h("label", { title: "Every book is cut into this many equal slices" }, "Slices per book",
          h("input", { type: "number", min: 2, max: 200, value: o.co_n, onchange: e => { o.co_n = Math.min(200, Math.max(2, Math.round(+e.target.value) || 20)); e.target.value = o.co_n; saveOver(); run(); } })))),
    out);
  run();
}
