"use strict";
/* BookNLP analyser — browser side. Plain JavaScript, no build step: the scripts listed in index.html run in
   order and share one global scope.

   core.js            shared state and helpers, tables, charts, the evidence drawer, book selection, pickers
   menu.js            the top bar's [...] menu and the book button's panel
   entities.js        the Entities page and an entity's (group's, narrator's, book's, gender's) profile
   network.js         the Network page
   compare.js         compare two entities or groups
   described.js       the Described-as page
   links.js           link the same entity across books
   books.js           the Library page: books, collections
   settings.js        the Settings page
   workspaces.js      workspaces: the [...] submenu and the Library page's section
   dialogue.js        the Dialogue pages, and the Speech section of an entity's page
   corpus.js          concordance, word lists, n-grams, collocates, keywords
   narrative.js       arcs, style, stylometry, sentiment
   lexicons.js        your word lexicons: arcs, words, editing
   reader.js          the text view, quote and narrator editing
   narrators.js       the Narrators page
   topics.js          topic models: fitting, the model overview, topics on an entity's page
   topic-page.js      one topic's page
   topic-compare.js   comparing topics
   pagetools.js       collapsible sections and the side menu on long pages
   main.js            the router; runs last

   Conventions
   - Pages are functions `renderX(main, …)` that build DOM with `h()` and put it in #main. The address is a hash
     route (#/tab/sub/…); `render()` in main.js dispatches on it.
   - `S` holds what the interface remembers; parts of it are saved in localStorage (`loadState` / `saveState`).
   - `api(path, body)` posts JSON to the server; a failure shows a message and throws. Every analysis call
     sends the selected books (`withBooks`), and every post carries the plural-group setting (`pluralMode`). */

const TYPES = ["PER", "LOC", "FAC", "GPE", "VEH", "ORG", "VAR"];       // entity categories, in display order
// NARR is not an entity category: it is the narrator roles ("Watson, narrating"), listed beside the entities, so it is not in TYPES
const TYPE_NAMES = { PER: "People", LOC: "Locations", FAC: "Facilities", GPE: "Geo-political", VEH: "Vehicles", ORG: "Organisations", VAR: "Various", NARR: "Narrators", GENDER: "Gender" };
const TC = { PER: "#3b5ba5", LOC: "#3e7c4a", FAC: "#9a6424", GPE: "#7b4f9e", VEH: "#b5473c", ORG: "#2b8a7e", VAR: "#6d6a75", NARR: "#8a6a3b", GENDER: "#a5477a" };   // a colour per type
const PALETTE = ["#3b5ba5", "#b5473c", "#3e7c4a", "#9a6424", "#7b4f9e", "#2b8a7e", "#c0843a", "#5a7d9a", "#a0527a", "#6b8e23", "#8c6d62", "#4a4a8a"];
const PROP_NAMES = { PROP: "Names", NOM: "Descriptions", PRON: "Pronouns" };                                               // how an entity is referred to
const PROP_COL = { PROP: "#2e4a62", NOM: "#7d9bb3", PRON: "#c9d6e0" };
const SVG_FONT = "Helvetica, Arial, sans-serif";
const MANY_LINES = 12;     // a line chart with more lines than this can't name them at their ends: it gives each a tooltip instead

/** The current theme's value of a CSS custom property (charts are plain SVG text/fill attributes, not stylesheet
    rules, so they read the colour at draw time instead of using var() directly). */
const cssVar = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const LIGHT_INK = "#1d2a2e", LIGHT_MUTED = "#5b686c", LIGHT_FAINT = "#8a9699", LIGHT_PANEL = "#ffffff", LIGHT_PANEL2 = "#f5f7f8";

/* ---------- remembered settings (localStorage) ---------- */
/** Whether a value is a plain object (not null, not an array). */
const isObject = v => v !== null && typeof v === "object" && !Array.isArray(v);

/** The workspace this page belongs to: the server writes its id into index.html. Remembered settings are kept per workspace (a book
    selection or a saved search of one must not leak into another), except for the few in GLOBAL_KEYS. The Default workspace keeps the
    plain key names, so what was saved before workspaces existed is still found. */
const WORKSPACE = window.WORKSPACE || "default";
const GLOBAL_KEYS = new Set(["analyser.theme"]);
/** The localStorage key a setting is kept under for a workspace (see above). */
const storageKey = (key, workspace = WORKSPACE) => (workspace === "default" || GLOBAL_KEYS.has(key) ? key : `${key}@${workspace}`);

/** Read one JSON value from localStorage; `fallback` if it is missing, damaged, or storage is unavailable. */
function loadJSON(key, fallback) {
  try {
    const raw = localStorage.getItem(storageKey(key));
    return raw == null ? fallback : JSON.parse(raw);
  } catch (e) { return fallback; }
}

/** Saved settings laid over defaults, key by key. A saved value is used only when it is the same kind of thing as the
    default (so a damaged or outdated entry can't break a page), and keys the defaults don't know are kept. */
function mergeState(defaults, saved) {
  if (!isObject(defaults) || !isObject(saved)) return defaults;
  const out = {};
  for (const [k, d] of Object.entries(defaults)) {
    const v = saved[k];
    if (v === undefined) out[k] = d;
    else if (isObject(d)) out[k] = mergeState(d, v);
    else if (d === null || d === undefined) out[k] = v;
    else if (Array.isArray(d)) out[k] = Array.isArray(v) ? v : d;
    else out[k] = typeof v === typeof d ? v : d;
  }
  for (const [k, v] of Object.entries(saved)) if (!(k in defaults)) out[k] = v;
  return out;
}

/** Settings object: the defaults with whatever was saved under `key` merged in. */
const loadState = (key, defaults) => mergeState(defaults, loadJSON(key, null));

/** Save settings; silently does nothing if storage is full or blocked (the interface then just forgets them). */
function saveState(key, value) {
  try { localStorage.setItem(storageKey(key), JSON.stringify(value)); } catch (e) { /* private browsing or quota */ }
}

/** What the interface knows and remembers. Other files add their own parts (S.dlg, S.corp, S.nar, S.read, S.top…). */
const S = {
  lib: null,                                   // the library from /api/library: books, settings, option lists, explanatory notes
  sel: (() => { const v = loadJSON("analyser.sel", null); return Array.isArray(v) ? v : null; })(),   // selected book ids; null = all
  selHistory: [],                               // wider selections `bookLink`'s drill-down narrowed from, for the "Back" button (this session only)
  pickedBook: null,                            // the book last chosen in a picker's Book mode, offered again next time the mode is opened
  units: null, unitsKey: "",                   // cached entity list of the selection
  entType: "PER", entQuery: "", entSort: "mentions", entSortRev: false, entLimit: 300,
  entMulti: false, entSel: [],                 // Entities page: "select several" is on, and the unit ids ticked
  profile: null,
  relTab: "agent", ssRel: "agent",
  stat: loadState("analyser.stat", { measure: "ll", test: "ll", min_freq: 3, alpha: 0.05, bonferroni: false, show_all: false }),
  distRel: "agent", distRef: { kind: "others" },
  cmp: { a: null, b: null, rel: "agent" },
  net: loadState("analyser.net", { kind: "sentence", types: ["PER"], min_weight: 2, min_range: 1, min_link_range: 1, keep_isolated: false, max_nodes: 300, color: "type", size: "strength", labels: 25, layout: "force", order: "community" }),
};
/** Save the significance settings (`S.stat`, one set shared by every comparison) and tell the other panels on the page
    that show them — `origin` is the changing panel's own re-run function, which `syncStat` skips. */
const saveStat = origin => {
  saveState("analyser.stat", S.stat);
  document.dispatchEvent(new CustomEvent("statchange", { detail: origin }));
};
/** Keep a panel in step with the shared significance settings: while `el` is on the page, `refresh()` runs whenever
    another panel changes them (`saveStat`), so two panels that show these settings never disagree. `run` is the panel's
    own re-run function, so a change made in this very panel doesn't run it twice. */
function syncStat(el, run, refresh = run) {
  const on = e => {
    if (!el.isConnected) { document.removeEventListener("statchange", on); return; }
    if (e.detail !== run) refresh();
  };
  document.addEventListener("statchange", on);
}

/* ---------- small helpers ---------- */
// Let append/prepend/replaceChildren take nested arrays and skip null/false, like h() does.
for (const name of ["append", "prepend", "replaceChildren"]) {
  const orig = Element.prototype[name];
  Element.prototype[name] = function (...kids) { return orig.apply(this, kids.flat(Infinity).filter(k => k != null && k !== false)); };
}
/** The first element matching a CSS selector (in the document, or inside `el`). */
const $ = (s, el = document) => el.querySelector(s);

/** Build an element: h("div", {class: "x", onclick: fn, style: {…}}, child, [children], "text"…).
    Props starting "on" are event listeners; null/false props and children are skipped; strings become text, never HTML
    (there is deliberately no way to set innerHTML).
    A tag "svg:circle" builds an SVG element. */
function h(tag, props, ...kids) {
  const el = tag.startsWith("svg:") ? document.createElementNS("http://www.w3.org/2000/svg", tag.slice(4)) : document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.setAttribute("class", v);
    else if (k === "style" && typeof v === "object") { for (const [name, value] of Object.entries(v)) name.startsWith("--") ? el.style.setProperty(name, value) : (el.style[name] = value); }   // custom properties need setProperty
    else if (k in el && !(el instanceof SVGElement) && typeof v !== "string") el[k] = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid == null || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}
/** Build an SVG element: `h` with the svg: prefix. */
const svg = (tag, props, ...kids) => h("svg:" + tag, props, ...kids);
let lastLoading = null;      // the most recent placeholder: the request made next is the one that will fill it
/** A "Loading…" line. Put it inside a container; never give the container itself the class (it would stay muted).
    If the request that follows fails, `api` replaces the line with the error message. */
const loading = text => (lastLoading = h("div", { class: "loading" }, text));

/* ---------- formatting ---------- */
const fmt = (n, d = 0) => n == null || Number.isNaN(n) ? "—" : Number(n).toLocaleString("en-GB", { minimumFractionDigits: d, maximumFractionDigits: d });   // 1,234.5
const fmtP = p => p == null ? "—" : p < 0.0001 ? "< 0.0001" : fmt(p, 4);                                   // a p-value
const fmtSig = v => Math.abs(v) >= 100 ? fmt(v, 0) : Math.abs(v) >= 10 ? fmt(v, 1) : fmt(v, 2);            // a statistic with sensible decimals
const plural = (n, one, many) => `${fmt(n)} ${n === 1 ? one : (many || one + "s")}`;                       // "1 book", "3 books"
/** A small coloured label naming an entity type (PER, LOC…). */
const typeChip = t => h("span", { class: "t " + t, title: TYPE_NAMES[t] || t }, t);
const selected = () => S.sel || (S.lib ? S.lib.books.map(b => b.id) : []);             // ids of the selected books
/** A book's title from its id (the id itself if the book is unknown). */
const bookTitle = id => (S.lib.books.find(b => b.id === id) || {}).title || id;
/** A gender bucket's display name (as `view.gender_label` on the server). */
const genderLabel = pron => pron === "unknown" ? "No BookNLP gender prediction" : pron || "?";
/** A book's display title for a list of several books together (which the server orders by year, see `View.books`):
    flags one with no publication date, since that is why it sorts last there. */
const bookLabel = id => { const b = S.lib.books.find(x => x.id === id); return !b ? id : b.year ? b.title : b.title + " (publication date missing)"; };
/** A book's title as a link, for a table or chart that shows several books together: click to "drill down" into just
    that book (sets the selection to it alone and redraws the current page, as the Library page's own book list does).
    The wider selection it narrowed from is remembered, for the "Back" button (`drawViewing`). */
const bookLink = (id, label) => h("a", { href: "#", title: "Show just this book", onclick: e => {
  e.preventDefault();
  const cur = selected();
  if (cur.length !== 1 || cur[0] !== id) { S.selHistory.push(cur); setSel([id]); render(); }
} }, label ?? bookLabel(id));

/** What the current book selection amounts to, for `drawViewing()`: a single book's title; a whole collection's or
    series' name when the selection is exactly that; "Various for “X”" for several books all from one collection or
    series but not all of it (the smallest such collection wins, if more than one nests around the selection); else
    "Various". Of the books `ids` instead of the current selection, if given. */
function viewingLabel(ids = selected()) {
  if (!S.lib || !S.lib.books.length) return null;
  const sel = new Set(ids);
  if (sel.size === 1) return bookTitle(ids[0]);
  const eqSet = (arr, set) => arr.length === set.size && arr.every(x => set.has(x));
  const exactColl = S.lib.collections.find(c => eqSet(c.deep, sel));
  if (exactColl) return exactColl.name;
  const seriesOf = id => (S.lib.books.find(b => b.id === id) || {}).series;
  const commonSeries = seriesOf(ids[0]) && ids.every(id => seriesOf(id) === seriesOf(ids[0])) ? seriesOf(ids[0]) : null;
  if (commonSeries && eqSet(S.lib.books.filter(b => b.series === commonSeries).map(b => b.id), sel)) return commonSeries;
  const containing = S.lib.collections.filter(c => ids.every(id => c.deep.includes(id))).sort((a, b) => a.deep.length - b.deep.length)[0];
  if (containing) return `Various for “${containing.name}”`;
  if (commonSeries) return `Various for “${commonSeries}”`;
  return "Various";
}
/** Show what is selected on the book button in the top bar: its tooltip names it (`viewingLabel`) and counts the books ("2 of 3
    books"), the button is marked when the selection is narrower than the whole library, and once a book link has narrowed the
    selection a "← Back" button beside it returns to the wider one. Called whenever the library or the selection changes. */
function drawViewing() {
  const label = viewingLabel(), n = selected().length, all = S.lib ? S.lib.books.length : 0;
  $("#viewTip").replaceChildren(
    label ? h("div", {}, "Viewing ", h("b", { class: "view-label" }, label)) : null,
    h("div", { class: "view-count" }, all ? (n === all ? `All ${plural(all, "book")}` : `${fmt(n)} of ${plural(all, "book")}`) : "No books yet"));
  $("#booksBtn").classList.toggle("on", !!all && n < all);
  const back = $("#viewBack"), prev = S.selHistory[S.selHistory.length - 1];
  back.hidden = !prev;
  if (prev) {
    back.textContent = "← Back to " + backTarget(prev);
    back.title = `You narrowed the view by clicking a book's name. Click to see ${backTarget(prev)} again.`;
  }
}
/** What the "Back" button returns to, in words: "all books", "3 books" (also for a "Various for …" selection, which would read
    badly after "Back to"), a single book's title, or the collection's or series' name (`viewingLabel`). */
function backTarget(ids) {
  const label = viewingLabel(ids);
  if (ids.length === S.lib.books.length) return "all books";
  return !label || label.startsWith("Various") ? plural(ids.length, "book") : label;
}
$("#viewBack").onclick = () => { setSel(S.selHistory.pop()); render(); };

/** A short message at the bottom of the window (red if `err`). */
function toast(msg, err) {
  const t = $("#toast");
  t.textContent = msg; t.className = "toast" + (err ? " err" : ""); t.hidden = false;
  clearTimeout(toast.tm); toast.tm = setTimeout(() => (t.hidden = true), err ? 6000 : 2500);
}

/** Reload the page (after switching workspace). A function of its own so that tests can replace it. */
function reloadPage() { location.reload(); }

/** Call the server: GET with no body, otherwise POST the body as JSON (a file, such as an export zip, is sent as it is) -> parsed JSON (or the Response if `raw`).
    A failure (an error from the server, or no answer at all) shows the message as a toast, replaces the "Loading…" line
    this request was going to fill with the message, and throws. The error is marked `handled` so callers that don't catch it stay quiet. */
async function api(path, body, raw) {
  const placeholder = lastLoading;
  const fail = msg => {
    toast(msg, true);
    if (placeholder && placeholder.parentNode) placeholder.replaceWith(h("div", { class: "warn small" }, msg));
    const err = new Error(msg);
    err.handled = true;
    return err;
  };
  const upload = typeof Blob !== "undefined" && body instanceof Blob;
  if (isObject(body) && !upload && !("plural" in body)) body = { ...body, plural: pluralMode() };
  let r;
  try {
    r = await fetch(path, body === undefined ? {} : upload ? { method: "POST", headers: { "Content-Type": "application/zip" }, body }
      : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  } catch (e) {
    throw fail("Can't reach the analyser. Is it still running?");
  }
  if (!r.ok) {
    let msg = r.statusText || `Error ${r.status}`;
    try { msg = (await r.json()).detail || msg; } catch (e) { /* not JSON */ }
    throw fail(msg);
  }
  return raw ? r : r.json();
}
window.addEventListener("unhandledrejection", e => { if (e.reason && e.reason.handled) e.preventDefault(); });   // already shown as a toast
const withBooks = body => Object.assign({ books: selected() }, body);         // add the selected books to a request body

/** Offer a Blob as a file download. */
function download(name, blob) {
  const a = h("a", { href: URL.createObjectURL(blob), download: name });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
const slug = s => String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60) || "export";      // a file-name-safe version of a title
/** Comma-separated text for a header row and rows (fields quoted when needed). */
function csvOf(header, rows) {
  const q = v => { const s = v == null ? "" : String(v); return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  return [header, ...rows].map(r => r.map(q).join(",")).join("\r\n");
}
const downloadCsv = (name, header, rows) => download(name + ".csv", new Blob(["﻿" + csvOf(header, rows)], { type: "text/csv" }));     // BOM so Excel reads UTF-8

/** A collapsed "How this is calculated" box: a summary line and paragraphs. */
function note(summary, ...paras) {
  return h("details", { class: "note" }, h("summary", {}, summary), paras.filter(Boolean).map(p => h("p", {}, p)));
}
/** A segmented button group: options are [value, label] or [value, label, {disabled, title}] (a greyed-out choice says why in its
    title); `onChange(value)` when one is clicked. */
function seg(options, value, onChange) {
  return h("div", { class: "seg", role: "group" }, options.map(([v, label, o = {}]) =>
    h("button", { class: v === value ? "on" : "", type: "button", "aria-pressed": String(v === value), disabled: o.disabled || null, title: o.title || null, onclick: () => onChange(v) }, label)));
}

/** A button that reverses a sort order, next to a "most/least" style dropdown that has no direction of its own
    (matching the concordance sort's own reverse arrow: ↓ for the normal order, ↑ once reversed). `titleFor(reversed)`
    describes what a click would give, given the current state. */
function reverseBtn(reversed, titleFor, onToggle) {
  return h("button", { class: "btn small", type: "button", "aria-pressed": String(reversed), title: titleFor(reversed), onclick: onToggle }, reversed ? "↑" : "↓");
}

/* ---------- tables ---------- */
const tableFolds = new Set();     // the chart tables opened on this visit (page|summary): a redraw keeps them open, a reload folds them again

/** The table of the figures behind a chart, slice by slice or chapter by chapter, folded away under `summary` until opened (AL-TBL-07):
    the chart is the answer, the table its numbers. Folded by default; one opened stays open while the page is redrawn. */
function foldTable(summary, tbl) {
  const key = (location.hash.split("/")[1] || "") + "|" + summary;
  const d = h("details", { class: "tfold", open: tableFolds.has(key) || null }, h("summary", {}, summary), tbl);
  d.addEventListener("toggle", () => { if (d.open) tableFolds.add(key); else tableFolds.delete(key); });
  return d;
}
const COLS_CHOOSER_MIN = 7;                                 // a table with this many columns or more gets a column chooser (AL-TBL-06)
S.colsHidden = loadState("analyser.columns", {});           // table id -> the keys of the columns you hid (per workspace)

/** A sortable table with a row count, "Show all" and CSV download.
    cols: [{k: key, label, num?, fmt?(value,row), csv?(value,row), sortVal?(row), title?, cls?, csvLabel?, group?}];  rows: objects.
    `cls` is an extra class for the column's header and cells; `csvLabel` is the column's name in the CSV when it differs from `label`;
    `group` names the column's group in the column chooser; `rel` (a sentence) puts the reliability marker on its header (AL-PRIN-14).
    opts: sort (initial column key, descending first), limit (rows shown, default 60), onRow(row) makes rows clickable,
    rowClass(row), csvName, csv: false to hide the download, empty: text when there are no rows, columns: {id, show, keep} for the
    column chooser that a table of COLS_CHOOSER_MIN columns or more gets: `show` the keys shown by default (all if absent), `keep` keys
    that can't be hidden (the first column never can; nor a column of corrections or warnings), `id` the name the choice is kept under,
    the same on every page that shows the table (default: the page and the column keys); `columns: false` for a table whose columns are
    slices, books or texts, which a chooser would only break up. The CSV always holds every column. */
function table(cols, rows, opts = {}) {
  let sortK = opts.sort || null, asc = false, limit = opts.limit || 60, colsOpen = false;
  const wrap = h("div");
  const co = opts.columns || {}, chooser = cols.length >= COLS_CHOOSER_MIN && opts.columns !== false;
  const tid = co.id || (location.hash.split("/")[1] || "entities") + ":" + cols.map(c => c.k).join(",");    // a named table's choice holds on every page
  const keep = new Set([cols[0].k, ...(co.keep || [])]);
  const byDefault = () => cols.filter(c => co.show && !co.show.includes(c.k) && !keep.has(c.k)).map(c => c.k);
  const hidden = () => new Set(chooser ? (Array.isArray(S.colsHidden[tid]) ? S.colsHidden[tid] : byDefault()).filter(k => !keep.has(k)) : []);
  /** Hide or show columns: `keys` (null = the default set again), saved for this table. */
  const setHidden = keys => { if (keys) S.colsHidden[tid] = keys; else delete S.colsHidden[tid]; saveState("analyser.columns", S.colsHidden); draw(); };
  /** The "Columns: n of m" link and, when open, the list of checkboxes (by group) with Show all and Default. */
  function colPicker(shownCols) {
    const hid = hidden(), groups = [...new Set(cols.map(c => c.group || ""))];
    const box = c => h("label", { class: "inline" + (keep.has(c.k) ? " muted" : ""), title: keep.has(c.k) ? "Always shown" : c.title || null },
      h("input", { type: "checkbox", checked: !hid.has(c.k), disabled: keep.has(c.k),
        onchange: e => { const next = new Set(hid); if (e.target.checked) next.delete(c.k); else next.add(c.k); setHidden([...next]); } }), c.label);
    const el = h("div", { class: "colpick" + (colsOpen ? " open" : "") },
      dlButton(`Columns: ${shownCols.length} of ${cols.length}`, () => { colsOpen = !colsOpen; draw(); }, "Choose which columns to show (the CSV always has them all)"),
      colsOpen ? h("div", { class: "colpop", role: "dialog", "aria-label": "Columns to show" },
        groups.map(g => [g ? h("div", { class: "colpop-group" }, g) : null, cols.filter(c => (c.group || "") === g).map(box)]),
        h("div", { class: "colpop-tools" }, h("button", { type: "button", class: "linkbtn", onclick: () => setHidden([]) }, "Show all"),
          h("button", { type: "button", class: "linkbtn", onclick: () => setHidden(null) }, "Default"))) : null);
    el.addEventListener("close", () => { colsOpen = false; draw(); });
    return el;
  }
  function draw() {
    const hid = hidden(), shownCols = cols.filter(c => !hid.has(c.k));
    let data = rows.slice();
    if (sortK) {
      const col = cols.find(c => c.k === sortK);
      const val = (col && col.sortVal) || (r => r[sortK]);
      data.sort((a, b) => { const x = val(a), y = val(b); const r = typeof x === "string" ? x.localeCompare(y) : (x ?? -Infinity) - (y ?? -Infinity); return asc ? r : -r; });
    }
    const shown = data.slice(0, limit);
    const t = h("table", { class: "t2" },
      h("thead", {}, h("tr", {}, shownCols.map(c => h("th", {
        class: (c.num ? "num " : "") + (c.cls ? c.cls + " " : "") + (c.k === sortK ? "sorted" + (asc ? " asc" : "") : ""), title: c.title || null,
        onclick: () => { if (sortK === c.k) asc = !asc; else { sortK = c.k; asc = !c.num; } draw(); },
      }, c.label, c.rel ? relMark(c.rel) : null)))),
      h("tbody", {}, shown.map(r => h("tr", {
        class: (opts.onRow ? "click " : "") + (opts.rowClass ? opts.rowClass(r) : ""),
        onclick: opts.onRow ? () => opts.onRow(r) : null,
      }, shownCols.map(c => h("td", { class: (c.num ? "num " : "") + (c.cls || "") }, c.fmt ? c.fmt(r[c.k], r) : (r[c.k] ?? "")))))));
    const foot = h("div", { class: "tbl-foot" },
      h("span", {}, rows.length > shown.length ? `${fmt(shown.length)} of ${fmt(rows.length)} rows ` : plural(rows.length, "row"),
        rows.length > shown.length ? h("button", { class: "btn small", onclick: () => { limit = Infinity; draw(); } }, "Show all") : null),
      h("span", { class: "tbl-tools" }, chooser ? colPicker(shownCols) : null, chooser && opts.csv !== false ? " · " : null,
        opts.csv !== false ? dlButton("CSV", () => downloadCsv(slug(opts.csvName || "table"), cols.map(c => c.csvLabel || c.label),
          data.map(r => cols.map(c => c.csv ? c.csv(r[c.k], r) : r[c.k]))), "Download this table as CSV (every row and every column, sorted as shown)") : null));
    wrap.replaceChildren(rows.length ? h("div", { class: "tbl-wrap" }, t) : h("div", { class: "muted small" }, opts.empty || "Nothing to show."), rows.length ? foot : null);
  }
  draw();
  return wrap;
}
/** A cell formatter that draws a small bar (scaled to `max`) beside the number. */
const barFmt = (max, d = 0) => v => h("div", { class: "bar-cell" }, h("i", { style: { width: Math.max(1, 60 * v / (max || 1)) + "px" } }), fmt(v, d));

/* ---------- charts (SVG, exportable) ---------- */
/** Download a chart (an <svg> element) as an SVG file, on a white background. */
function exportSvg(el, name) {
  const s = new XMLSerializer().serializeToString(prepSvg(el));
  download(name + ".svg", new Blob([s], { type: "image/svg+xml" }));
}
/** A copy of an SVG prepared for export: namespace, explicit size, white background rectangle. A downloaded file has
    no theme of its own, so any of the current theme's colours a chart used for its text and backdrops (read live via
    `cssVar`, since charts are plain attributes, not stylesheet rules) are swapped back to their light-theme values,
    which stay readable against the white backing rectangle even when the screen is in dark mode. */
function prepSvg(el) {
  const c = el.cloneNode(true);
  c.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  const vb = el.viewBox.baseVal;
  c.setAttribute("width", vb.width); c.setAttribute("height", vb.height);
  const swap = { [cssVar("--ink")]: LIGHT_INK, [cssVar("--muted")]: LIGHT_MUTED, [cssVar("--faint")]: LIGHT_FAINT,
    [cssVar("--panel")]: LIGHT_PANEL, [cssVar("--panel-2")]: LIGHT_PANEL2 };
  c.querySelectorAll("[fill],[stroke]").forEach(node => {
    for (const attr of ["fill", "stroke"]) {
      const v = node.getAttribute(attr);
      if (v && swap[v]) node.setAttribute(attr, swap[v]);
    }
  });
  c.insertBefore(svg("rect", { x: vb.x, y: vb.y, width: vb.width, height: vb.height, fill: "#ffffff" }), c.firstChild);
  return c;
}
/** Download a chart as a PNG (drawn at twice the size): serialise the SVG, load it as an image, draw it on a canvas. */
function exportPng(el, name) {
  const c = prepSvg(el), vb = el.viewBox.baseVal, scale = 2;
  const img = new Image();
  img.onload = () => {
    const cv = h("canvas", { width: vb.width * scale, height: vb.height * scale });
    const ctx = cv.getContext("2d"); ctx.scale(scale, scale); ctx.drawImage(img, 0, 0);
    cv.toBlob(b => download(name + ".png", b));
  };
  img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(new XMLSerializer().serializeToString(c));
}
// an open column chooser closes on a click outside it or on Escape (table() above)
document.addEventListener("mousedown", e => document.querySelectorAll(".colpick.open").forEach(p => { if (!p.contains(e.target)) p.dispatchEvent(new Event("close")); }));
document.addEventListener("keydown", e => { if (e.key === "Escape") document.querySelectorAll(".colpick.open").forEach(p => p.dispatchEvent(new Event("close"))); });
/** A reliability marker (AL-PRIN-14): a small "≈" after a figure, its tooltip saying why to read the figure with care. One sign
    for every such case: a small sample, an estimate, a guess. */
const relMark = why => h("sup", { class: "rel", title: why, "aria-label": "Read with care: " + why }, "≈");
/** A figure with its marker when `why` is given (`text` alone otherwise). */
const relNum = (text, why) => why ? h("span", {}, text, relMark(why)) : text;
const MATTR_SHORT = "Fewer than 100 words: this is the plain type-token ratio, not a moving average, so it can't be compared with the others";
/** Why a topic is marked: it came back in fewer than 60% of the re-runs with other seeds (`stability` {recurs, of}), or null. */
const topicUnstable = st => st && st.of > 1 && st.recurs / st.of < 0.6 ? `Came back in only ${st.recurs} of ${st.of} re-runs with other seeds (under 60%): it may not be a robust pattern` : null;
const ADDR_ESTIMATED = "Estimated: BookNLP doesn't record whom a quote is addressed to, so aLex works it out (a name in the quote, a reply, the next speaker…), unless you set it";
/** A quiet download link (AL-BTN-06): small muted text without a border, so that downloads never compete with the results. */
const dlButton = (label, onclick, title) => h("button", { class: "dl", type: "button", title, onclick }, label);
/** Wrap a chart with SVG and PNG download links. */
function chartBox(el, name) {
  return h("div", { class: "chart-box" }, el, h("div", { class: "chart-tools" },
    dlButton("SVG", () => exportSvg(el, name), "Download the chart as SVG"), " · ",
    dlButton("PNG", () => exportPng(el, name), "Download the chart as PNG")));
}

const PRESENCE_DETAIL = 30;    // books up to which every slice of a presence strip has its own tooltip
/** A strip per book showing where something occurs, in 100 slices; darker = more. presence: [{title, bins[100]}]. Each slice answers a hover with
    its count, except over many books (`PRESENCE_DETAIL`), where a chart would have tens of thousands of elements: then a hover gives the book's total. */
function presenceChart(presence, color, title) {
  const W = 900, rowH = 26, top = title ? 26 : 6, labW = 190, H = top + presence.length * rowH + 18;
  const g = svg("svg", { viewBox: `0 0 ${W} ${H}`, "font-family": SVG_FONT, "font-size": 12, role: "img", "aria-label": "Where mentions occur in each book" });
  if (title) g.append(svg("text", { x: 0, y: 16, "font-size": 13, "font-weight": 600, fill: cssVar("--ink") }, title));
  presence.forEach((p, i) => {
    const y = top + i * rowH, max = Math.max(...p.bins, 1), bw = (W - labW) / p.bins.length;
    g.append(svg("text", { x: labW - 10, y: y + 15, "text-anchor": "end", fill: cssVar("--muted") }, p.title.length > 28 ? p.title.slice(0, 27) + "…" : p.title));
    const detail = presence.length <= PRESENCE_DETAIL;
    g.append(svg("rect", { x: labW, y: y + 3, width: W - labW, height: 18, fill: cssVar("--panel-2") }, detail ? null : svg("title", {}, `${p.bins.reduce((a, b) => a + b, 0)} mentions in ${p.title}`)));
    p.bins.forEach((n, j) => {
      if (n) g.append(svg("rect", { x: labW + j * bw, y: y + 3, width: bw + 0.3, height: 18, fill: color, "fill-opacity": 0.15 + 0.85 * n / max }, detail ? svg("title", {}, `${n} mentions at ${j}–${j + 1}%`) : null));
    });
  });
  const y = top + presence.length * rowH + 12;
  g.append(svg("text", { x: labW, y, fill: cssVar("--faint"), "font-size": 10.5 }, "start of book"));
  g.append(svg("text", { x: W, y, fill: cssVar("--faint"), "font-size": 10.5, "text-anchor": "end" }, "end"));
  return g;
}

/** Horizontal bars for one or more series of {item, n}; with opts.pct, values are % of each series' total. */
function hbarChart(series, opts = {}) {
  // series: [{name, color, rows:[{item,n}]}]; values shown as % of each series' total if opts.pct
  const items = [...new Set(series.flatMap(s => s.rows.map(r => r.item)))].slice(0, opts.max || 20);
  const val = (s, it) => { const r = s.rows.find(x => x.item === it); const tot = s.rows.reduce((a, b) => a + b.n, 0) || 1; return r ? (opts.pct ? 100 * r.n / tot : r.n) : 0; };
  const W = 640, labW = 170, barH = 14, gap = 8, grpH = series.length * barH + gap;
  const legRows = Math.ceil(series.length / 3), top = series.length > 1 ? 8 + legRows * 16 : 6;
  const H = top + items.length * grpH + 6;
  const max = Math.max(1e-9, ...items.flatMap(it => series.map(s => val(s, it))));
  const g = svg("svg", { viewBox: `0 0 ${W} ${H}`, "font-family": SVG_FONT, "font-size": 12, role: "img", style: "max-width:760px" });
  if (series.length > 1) series.forEach((s, i) => {
    const lx = labW + (i % 3) * 155, ly = 4 + Math.floor(i / 3) * 16;
    g.append(svg("rect", { x: lx, y: ly, width: 10, height: 10, fill: s.color }));
    g.append(svg("text", { x: lx + 15, y: ly + 9, fill: cssVar("--ink") }, s.name.length > 20 ? s.name.slice(0, 19) + "…" : s.name));
  });
  items.forEach((it, i) => {
    const y = top + i * grpH;
    g.append(svg("text", { x: labW - 8, y: y + series.length * barH / 2 + 4, "text-anchor": "end", fill: cssVar("--ink") }, it.replace(/^(verb|noun)\./, "")));
    series.forEach((s, j) => {
      const v = val(s, it), w = (W - labW - 60) * v / max;
      g.append(svg("rect", { x: labW, y: y + j * barH, width: Math.max(0.5, w), height: barH - 2, fill: s.color }));
      g.append(svg("text", { x: labW + w + 5, y: y + j * barH + barH - 4, fill: cssVar("--muted"), "font-size": 11 }, opts.pct ? fmt(v, 1) + "%" : fmt(v, opts.dec || 0)));
    });
  });
  return g;
}

/** A simple line chart: one value per x label for each series [{name, color, values}] (values are percentages). */
function lineChart(xLabels, series, opts = {}) {
  // series: [{name, color, values}] with one value per x label (percentages)
  const W = 760, left = 46, right = 170, top = 14, bottom = 58, H = opts.height || 300;
  const pw = W - left - right, ph = H - top - bottom;
  const max = Math.max(1e-9, ...series.flatMap(s => s.values)) * 1.08;
  const x = i => left + (xLabels.length === 1 ? pw / 2 : i * pw / (xLabels.length - 1));
  const y = v => top + ph - ph * v / max;
  const g = svg("svg", { viewBox: `0 0 ${W} ${H}`, "font-family": SVG_FONT, "font-size": 11.5, role: "img", style: "max-width:900px" });
  const step = [1, 2, 5, 10, 20, 25, 50].find(st => max / st <= 6) || 100;
  for (let v = 0; v <= max; v += step) {
    g.append(svg("line", { x1: left, x2: left + pw, y1: y(v), y2: y(v), stroke: cssVar("--rule-soft") }));
    g.append(svg("text", { x: left - 6, y: y(v) + 4, "text-anchor": "end", fill: cssVar("--faint") }, fmt(v, 0) + "%"));
  }
  const every = Math.ceil(xLabels.length / 16);                  // at most about sixteen labels along the axis, whatever the number of points
  xLabels.forEach((l, i) => {
    if (i % every) return;
    const t = svg("text", { x: x(i), y: top + ph + 16, "text-anchor": xLabels.length > 4 ? "end" : "middle", fill: cssVar("--muted"),
      transform: xLabels.length > 4 ? `rotate(-30 ${x(i)} ${top + ph + 16})` : null }, l.length > 24 ? l.slice(0, 23) + "…" : l);
    g.append(t);
  });
  const ends = [];
  series.forEach(s => {
    const pts = s.values.map((v, i) => `${x(i)},${y(v)}`).join(" ");
    g.append(svg("polyline", { points: pts, fill: "none", stroke: s.color, "stroke-width": 2 }));
    s.values.forEach((v, i) => g.append(svg("circle", { cx: x(i), cy: y(v), r: 3.5, fill: s.color }, svg("title", {}, `${s.name}, ${xLabels[i]}: ${fmt(v, 1)}%`))));
    ends.push([y(s.values[s.values.length - 1]), s]);
  });
  // labels at the right, nudged apart
  ends.sort((a, b) => a[0] - b[0]);
  let last = -Infinity;
  for (const e of ends) { e[0] = Math.max(e[0], last + 13); last = e[0]; }
  for (const [ly, s] of ends) g.append(svg("text", { x: left + pw + 10, y: ly + 4, fill: s.color, "font-weight": 600 }, s.name.length > 22 ? s.name.slice(0, 21) + "…" : s.name));
  return g;
}

/** A stacked bar of how an entity is referred to: names, descriptions, pronouns. */
function propChart(byProp) {
  const tot = Object.values(byProp).reduce((a, b) => a + b, 0) || 1;
  const W = 640, H = 44;
  const g = svg("svg", { viewBox: `0 0 ${W} ${H}`, "font-family": SVG_FONT, "font-size": 12, role: "img", "aria-label": "Names, descriptions and pronouns", style: "max-width:760px" });
  let x = 0;
  for (const k of ["PROP", "NOM", "PRON"]) {
    const w = W * (byProp[k] || 0) / tot;
    g.append(svg("rect", { x, y: 0, width: w, height: 16, fill: PROP_COL[k] }, svg("title", {}, `${PROP_NAMES[k]}: ${byProp[k]}`)));
    x += w;
  }
  x = 0;
  for (const k of ["PROP", "NOM", "PRON"]) {
    g.append(svg("rect", { x, y: 26, width: 10, height: 10, fill: PROP_COL[k] }));
    const label = `${PROP_NAMES[k]} ${fmt(byProp[k] || 0)} (${fmt(100 * (byProp[k] || 0) / tot, 0)}%)`;
    g.append(svg("text", { x: x + 15, y: 35, fill: cssVar("--ink") }, label));
    x += 30 + label.length * 6.4;
  }
  return g;
}

/* ---------- evidence drawer ---------- */
/** Turn server text with marks into a <p> of nested <mark> elements. The server marks text with control characters:
    \x01class|data\x02 opens a mark (class and optional data id) and \x03 closes one; everything else is plain text, never HTML. */
function markup(text) {
  let i = 0; const stack = [];
  let cur = h("p");
  const root = cur;
  while (i < text.length) {
    const c = text[i];
    if (c === "\x01") {
      const j = text.indexOf("\x02", i);
      if (j < 0) break;                                  // a mark that never opens properly: stop rather than loop
      const [cls, data] = text.slice(i + 1, j).split("|");
      const m = h("mark", { class: cls });
      if (data) { m.dataset.id = data; if (cls === "ss") m.title = data.replace(".", ": "); }
      if (cls === "ev") m.title = "event";
      cur.append(m); stack.push(cur); cur = m; i = j + 1;
    } else if (c === "\x03") { cur = stack.pop() || root; i++; }
    else {
      let j = i; while (j < text.length && !"\x01\x03".includes(text[j])) j++;
      cur.append(text.slice(i, j)); i = j;
    }
  }
  return root;
}
/** Open the side drawer with the sentences behind a count (from /api/evidence, or another route that answers the same way: `path`),
    with a CSV download. A sentence that comes with `by` (who said it) shows it. */
async function openEvidence(title, subtitle, body, path = "/api/evidence") {
  const d = $("#drawer");
  $("#drawerTitle").replaceChildren(h("h2", { style: { margin: 0 } }, title), subtitle ? h("div", { class: "muted small" }, subtitle) : null);
  $("#drawerBody").replaceChildren(loading("Finding sentences…"));
  d.hidden = false;
  const r = await api(path, withBooks(body));
  const plain = t => t.replace(/[\x01][^\x02]*\x02|\x03/g, "");
  $("#drawerBody").replaceChildren(
    h("div", { class: "tbl-foot" }, h("span", {}, r.total > r.shown ? `First ${fmt(r.shown)} of ${fmt(r.total)} sentences` : plural(r.total, "sentence")),
      dlButton("CSV", () => downloadCsv(slug(title), ["book", "position_percent", "sentence"], r.items.map(e => [e.title, e.pos, plain(e.text)])), "Download these sentences as CSV")),
    r.items.length ? r.items.map(e => h("div", { class: "ev" }, h("div", { class: "src" }, `${e.title}, ${fmt(e.pos, 1)}% through · `, e.by ? `${e.by} · ` : null, textLink(e.book, e.tok)), markup(e.text)))
      : h("div", { class: "empty" }, "No sentences found."));
}
$("#drawerClose").onclick = () => ($("#drawer").hidden = true);
document.addEventListener("keydown", e => { if (e.key === "Escape") $("#drawer").hidden = true; });

/* ---------- theme (light/dark/auto) ---------- */
const THEME_LABEL = { auto: "Auto", light: "Light", dark: "Dark" };
/** Apply a theme choice to the page (index.html's inline script does the same, before this file loads, to avoid a flash),
    remember it, and show it in the [...] menu's Theme submenu (a check on the choice, its name on the Theme row).
    "auto" follows the system (prefers-color-scheme), set in app.css. */
function setTheme(mode) {
  if (mode === "light" || mode === "dark") document.documentElement.dataset.theme = mode;
  else document.documentElement.removeAttribute("data-theme");
  saveState("analyser.theme", mode);
  $("#themeVal").textContent = THEME_LABEL[mode];
  document.querySelectorAll("#moreMenu [data-theme]").forEach(b => { b.classList.toggle("on", b.dataset.theme === mode); b.setAttribute("aria-checked", String(b.dataset.theme === mode)); });
}
setTheme(loadJSON("analyser.theme", "auto"));
document.querySelectorAll("#moreMenu [data-theme]").forEach(b => b.onclick = () => {
  setTheme(b.dataset.theme);
  if (typeof render === "function") render();     // redraw the page so its charts (plain SVG, not CSS) pick up the new colours
});

/* ---------- book selection ---------- */
/** Remember which books are selected (null means all) and clear the cached entity list. */
function setSel(ids) {
  const all = S.lib.books.map(b => b.id);
  const next = ids.length === all.length ? null : ids;
  S.sel = next;
  saveState("analyser.sel", S.sel);
  S.units = null;
  drawViewing();
}
/** Whether a book matches a search: every word typed must occur in its title, author, series, year, tags or id (any case). */
function bookMatchesQuery(b, q) {
  const hay = [b.title, b.author, b.series, b.year, b.id, ...(b.tags || [])].join(" ").toLowerCase();
  return q.toLowerCase().split(/\s+/).filter(Boolean).every(w => hay.includes(w));
}
/** Build the book picker in the book button's panel (it is built each time the panel opens): a search box and filters by collection, series, author, tag and year, and one checkbox per book. */
function renderSelPop() {
  const pop = $("#selPop"), books = S.lib.books, colls = S.lib.collections;
  const uniq = k => [...new Set(books.map(b => b[k]).filter(Boolean))].sort();
  const tags = [...new Set(books.flatMap(b => b.tags || []))].sort();
  const f = { q: "", coll: "", series: "", author: "", tag: "", from: "", to: "" };
  const cur = new Set(selected());
  const list = h("div", { class: "books-list" });
  const match = b => bookMatchesQuery(b, f.q) && (!f.coll || colls.find(c => c.id === f.coll).deep.includes(b.id)) && (!f.series || b.series === f.series) && (!f.author || b.author === f.author)
    && (!f.tag || (b.tags || []).includes(f.tag)) && (!f.from || (b.year && b.year >= +f.from)) && (!f.to || (b.year && b.year <= +f.to));
  /** The list shows the books matching the search and filters; ticks on hidden books are kept. */
  const drawList = () => list.replaceChildren(...books.filter(match).map(b => h("label", { class: "book" },
    h("input", { type: "checkbox", checked: cur.has(b.id), onchange: e => { e.target.checked ? cur.add(b.id) : cur.delete(b.id); } }),
    h("span", {}, b.title, " ", h("small", {}, [b.author, b.year, b.series].filter(Boolean).join(", "))))));
  drawList();
  const sel = (k, opts, label) => h("select", { onchange: e => { f[k] = e.target.value; drawList(); } }, h("option", { value: "" }, label),
    opts.map(o => Array.isArray(o) ? h("option", { value: o[0] }, o[1]) : h("option", { value: o }, o)));
  pop.replaceChildren(
    h("h3", {}, "Books to analyse"),
    h("input", { type: "search", placeholder: "Search title, author, series, tag…", style: { width: "100%", marginBottom: "8px" }, oninput: e => { f.q = e.target.value; drawList(); } }),
    h("div", { class: "filters" },
      colls.length ? sel("coll", colls.map(c => [c.id, c.name]), "Any collection") : null,
      sel("series", uniq("series"), "Any series"), sel("author", uniq("author"), "Any author"), sel("tag", tags, "Any tag"),
      h("div", { class: "row" }, h("input", { type: "number", placeholder: "From year", oninput: e => { f.from = e.target.value; drawList(); } }),
        h("input", { type: "number", placeholder: "to", oninput: e => { f.to = e.target.value; drawList(); } }))),
    h("div", { class: "row", style: { marginBottom: "8px" } },
      h("button", { class: "btn small", onclick: () => { cur.clear(); books.filter(match).forEach(b => cur.add(b.id)); drawList(); } }, "Select shown"),
      h("button", { class: "btn small", onclick: () => { books.forEach(b => cur.add(b.id)); drawList(); } }, "All"),
      h("button", { class: "btn small", onclick: () => { cur.clear(); drawList(); } }, "None")),
    list,
    h("div", { class: "row", style: { marginTop: "12px", justifyContent: "flex-end" } },
      h("button", { class: "btn", onclick: () => setBooksPanel(false) }, "Cancel"),
      h("button", { class: "btn primary", onclick: () => {
        if (!cur.size) return toast("Choose at least one book.", true);
        setSel(books.map(b => b.id).filter(id => cur.has(id))); setBooksPanel(false); render();
      } }, "Use these books")));
}
$("#selPop").addEventListener("submenuopen", () => { if (S.lib) renderSelPop(); });

/* ---------- data loading ---------- */
/** Drop book ids that no longer exist from the selection and from the "Back" history (a selection left empty means all). */
function pruneSel() {
  const ids = new Set(S.lib.books.map(b => b.id));
  if (S.sel) {
    S.sel = S.sel.filter(id => ids.has(id));
    if (!S.sel.length) S.sel = null;
  }
  S.selHistory = S.selHistory.map(sel => sel.filter(id => ids.has(id))).filter(sel => sel.length);
}
/** Load the library (books, settings, notes) from the server and drop selected ids that no longer exist. */
async function loadLib() {
  S.lib = await api("/api/library");
  pruneSel();
  drawViewing(); drawPluralItem();
}
/** A signature of the books on disk (id, folder, file version): changes when a new export arrives. */
const libSig = lib => JSON.stringify(lib.books.map(b => [b.id, b.folder, b.signature]));
/** When the window regains focus, reload everything if the books on disk changed (a new export). */
async function refreshIfChanged() {
  if (!S.lib) return;
  let lib;
  try {                                     // a background check: stay quiet if the server is busy, gone or answers with an error
    const r = await fetch("/api/library");
    if (!r.ok) return;
    lib = await r.json();
  } catch (e) { return; }
  if (libSig(lib) !== libSig(S.lib)) {
    S.lib = lib; S.units = null; pruneSel(); drawViewing(); drawPluralItem();
    toast("Books reloaded from new exports.");
    render();
  }
}
window.addEventListener("focus", refreshIfChanged);

/** A button that shows one of a workspace's folders in Finder or the computer's file browser (POST /api/folders/open). `spec`:
    {folder: "books" | "data" | "source", workspace (default: the one in use), index (of a source folder)}. Books put there are
    found when you come back to this window (refreshIfChanged). */
function openFolderButton(spec, label = "Open", cls = "btn small") {
  return h("button", { class: cls, title: "Show this folder in Finder or your file browser",
    onclick: () => api("/api/folders/open", spec).then(r => toast("Opened " + r.path), () => {}) }, label);
}

/** The entity list of the selected books, fetched once per selection and settings. */
async function units() {
  const key = JSON.stringify([selected(), S.lib.settings, pluralMode()]);
  if (!S.units || S.unitsKey !== key) {
    S.units = await api("/api/units", withBooks({}));
    S.unitsKey = key;
  }
  return S.units;
}
/* ---------- plural groups: do their mentions count for their members? ---------- */
// A plural group ("Holmes and Watson", "they") is an entity you declared to stand for its members together (plurals.py).
// Whether its mentions, quotes and addressees also count for them is one setting for every page: `settings.plural` of the
// workspace in use, set from the [...] menu (`#pluralItem`) or the Settings page.

/** Whether plural groups' mentions count for their members: the workspace's setting. */
function pluralMode() {
  return !!(S.lib && S.lib.settings.plural);
}

/** Show the setting on the [...] menu's "Plural groups" row (On/Off, ticked when on). Called whenever the library is (re)loaded. */
function drawPluralItem() {
  const on = pluralMode(), item = $("#pluralItem");
  item.classList.toggle("on", on);
  item.setAttribute("aria-checked", String(on));
  $("#pluralVal").textContent = on ? "On" : "Off";
}

/** Switch the setting for the whole workspace: save it, drop what was counted the old way, and redraw the page. */
async function togglePlural() {
  S.lib = await api("/api/settings", { plural_default: !pluralMode() });
  S.units = null;
  drawPluralItem();
  render();
}
$("#pluralItem").onclick = () => togglePlural().catch(() => {});

/** A "Based on:" line (AL-PRIN-11): the settings and corrections the figures beside it depend on, so that nothing that
    changes a number is hidden. Each item is `{ text, set, href, title }`: `set` (a setting changed from its default, or
    a correction of yours) tints it; `href` leads to where it is changed. Null items are left out; none left, no line. `label` replaces
    "Based on: " (the topic form's fold says "Fine-tuning: "). */
function basedOn(items, label = "Based on: ") {
  items = items.filter(Boolean);
  if (!items.length) return null;
  return h("div", { class: "basedon" }, label, items.map((it, i) => [i ? " · " : null,
    h(it.href ? "a" : "span", { class: it.set ? "bo set" : "bo", href: it.href, title: it.title || (it.set ? "Set by you" : null) }, it.text)]));
}

/** Whether workspace setting `key` differs from its default (the server's `default_settings`). */
const settingChanged = key => JSON.stringify(S.lib.settings[key]) !== JSON.stringify(S.lib.default_settings[key]);

/** The items `basedOn` lines are made of, one per setting that changes numbers on many pages. */
const BASED = {
  /** The minimum mentions per type, and whether they're counted per book or over the selected books. */
  mentions() {
    const st = S.lib.settings, mins = TYPES.map(t => st.min[t]), same = mins.every(m => m === mins[0]);
    const where = st.count_mode === "combined" ? "across the selected books" : "in a book";
    return { text: same ? `at least ${mins[0]} mentions ${where}` : `minimum mentions ${where}, by type`,
      set: settingChanged("min") || settingChanged("count_mode"), href: "#/settings/entities" };
  },
  /** Whether plural groups' mentions count for their members too (the [...] menu's Plural groups). */
  plural: () => ({ text: pluralMode() ? "plural groups count for their members" : "plural groups off", set: settingChanged("plural"), href: "#/settings/entities" }),
  /** How a minimum word frequency is checked: over the selected books together, or in each book. */
  freq: () => ({ text: S.lib.settings.freq_mode === "per_book" ? "minimum frequency checked in each book" : "minimum frequency checked over the selected books together",
    set: settingChanged("freq_mode"), href: "#/settings/words" }),
  /** How many narration words without a quote end a conversation (it decides the estimated addressees). */
  convGap: () => ({ text: `a conversation ends after ${fmt(S.lib.settings.conv_gap ?? 100)} narration words`, set: settingChanged("conv_gap"),
    href: "#/dialogue/speakers", title: "Set on the Dialogue page; it decides the conversations and the estimated addressees" }),
  /** The words you left out of the speech verbs and adverbs (Dialogue → Speech verbs); null when there are none. */
  speechSkip() {
    const sk = S.lib.settings.speech_skip || {}, n = (sk.verbs || []).length + (sk.adverbs || []).length;
    return n ? { text: `${plural(n, "word")} left out of the speech verbs`, set: true, href: "#/dialogue/verbs" } : null;
  },
};

/** The names of chosen entities (`rows`: {id, name, books}), with the book added to a name that occurs more than once among them
    and belongs to an entity of one book ("Holmes (alpha)"); a linked entity keeps its plain name -> {id: label} (AD-43). */
function namesWithBooks(rows) {
  const n = {};
  rows.forEach(r => (n[r.name] = (n[r.name] || 0) + 1));
  return Object.fromEntries(rows.map(r => [r.id, n[r.name] > 1 && r.books && r.books.length === 1 ? `${r.name} (${bookTitle(r.books[0])})` : r.name]));
}

/** A one-line reminder of the minimum-mentions setting, with a link to change it. */
const minLine = () => basedOn([BASED.mentions()]);
/** A one-line reminder of the Words setting (how a minimum frequency is counted), with a link to change it. */
const freqLine = () => basedOn([BASED.freq()]);

/** A drop-down to narrow a list of entities to one type ("" = any type); `onChange(type)` when it changes. */
function typeSelect(value, onChange) {
  return h("select", { "aria-label": "Only entities of this type", onchange: e => onChange(e.target.value) },
    h("option", { value: "" }, "any type"), TYPES.map(t => h("option", { value: t, selected: t === value }, t)));
}

/** The "add all by name" row of a group picker: every entity of the selected books whose name contains any of some comma-separated
    words (any case), optionally of one type, with a live count. BookNLP often splits one place or person into dozens of entities
    ("the moor", "the great Grimpen Mire"…), and this gathers them in one go. `onAdd(rows)` gets the matching rows of `units()`. */
function poolByName(onAdd) {
  const inp = h("input", { type: "search", placeholder: "or add every entity named… (moor, mire)", style: { width: "270px" } });
  const type = typeSelect("", () => refresh());
  const info = h("span", { class: "muted small" }), btn = h("button", { class: "btn small", type: "button", disabled: true }, "Add them");
  let found = [], latest = 0;
  const refresh = async () => {
    const mine = ++latest, words = inp.value.toLowerCase().split(",").map(w => w.trim()).filter(Boolean);
    const rows = !words.length ? [] : (await units()).rows.filter(r => (!type.value || r.type === type.value) && words.some(w => r.name.toLowerCase().includes(w)));
    if (mine !== latest) return;                               // a newer keystroke is already counting
    found = rows;
    btn.disabled = !rows.length;
    info.textContent = !words.length ? "" : rows.length ? `${plural(rows.length, "entity", "entities")}, ${plural(rows.reduce((n, r) => n + r.mentions, 0), "mention")}` : "No entity by that name.";
  };
  inp.addEventListener("input", refresh);
  btn.addEventListener("click", () => { onAdd(found); inp.value = ""; refresh(); });
  return h("div", { class: "row" }, inp, type, btn, info);
}

/* ---------- picker: an entity, a group of entities, a tag group, or everyone else ---------- */
/** Choosing several entities as one group: search and click to add, × to remove, or start from a saved group or from the entities
    ticked on the Entities page. The chosen ones are shown as tags outside the search list.
    value: the current group spec; onChange(spec) with `{kind: "group", ids | group, name, members: [{id, name, type}]}`, or null when the group is empty. */
function groupPicker(value, onChange) {
  let members = value && value.kind === "group" ? [...(value.members || [])] : [];
  let saved = value && value.kind === "group" && value.group ? { id: value.group, name: value.name } : null;    // set while the group is exactly a saved one
  const box = h("div", { class: "gpick" }), chips = h("div", { class: "gbox" }), tools = h("div", { class: "row" });
  const spec = () => !members.length ? null : saved ? { kind: "group", group: saved.id, name: saved.name, members }
    : { kind: "group", ids: members.map(m => m.id), name: members.length <= 3 ? members.map(m => m.name).join(", ") : `${members.length} entities`, members };
  const set = (next, from) => { members = next; saved = from || null; drawChips(); onChange(spec()); };
  /** Set the group from unit ids (those not in the selection are skipped). */
  const setIds = async (ids, from) => {
    const byId = Object.fromEntries((await units()).rows.map(r => [r.id, r]));
    set(ids.filter(i => byId[i]).map(i => ({ id: byId[i].id, name: byId[i].name, type: byId[i].type, books: byId[i].books })), from);
  };
  const search = unitSearch({ exclude: () => members.map(m => m.id), onPick: r => set([...members, { id: r.id, name: r.name, type: r.type, books: r.books }]) });
  const pool = poolByName(rows => { const have = new Set(members.map(m => m.id)); set([...members, ...rows.filter(r => !have.has(r.id)).map(r => ({ id: r.id, name: r.name, type: r.type, books: r.books }))]); });
  function drawChips() {
    chips.replaceChildren(members.length ? members.map(m => gtag(m, () => set(members.filter(x => x.id !== m.id))))
      : h("span", { class: "muted small" }, "No entities yet. Search above to add some."));
    tools.replaceChildren(
      S.lib.groups.length ? h("select", { "aria-label": "Use a saved group", onchange: e => { const g = S.lib.groups.find(x => x.id === e.target.value); if (g) setIds(g.ids, { id: g.id, name: g.name }); } },
        h("option", { value: "" }, "Use a saved group…"), S.lib.groups.map(g => h("option", { value: g.id, selected: saved && saved.id === g.id }, g.name))) : null,
      S.entSel && S.entSel.length ? h("button", { class: "btn small", title: "The entities ticked on the Entities page", onclick: () => setIds(S.entSel) }, `Use my selection (${S.entSel.length})`) : null,
      members.length ? h("button", { class: "btn small", onclick: () => set([]) }, "Clear") : null);
  }
  drawChips();
  box.append(h("div", { class: "row" }, search, tools), pool, chips);
  return box;
}

/** A search box with a type drop-down and a scrolling list of the selected books' entities (most mentioned first, narrowed as you
    type and by the type, like the entity boxes on the Arcs page); clicking one calls onPick(row). `exclude()` gives the ids not to
    offer, `only(row)` can narrow the list further. `value` is the text the box starts with and `keepName` leaves a picked
    entity's name in the box (a picker that shows what it holds). */
function unitSearch({ exclude = () => [], only = () => true, onPick, placeholder = "Add an entity by name…", value = "", keepName = false }) {
  const inp = h("input", { type: "search", placeholder, value, style: { width: "220px" } });
  const list = h("div", { class: "sugg", hidden: true });
  const type = typeSelect("", () => show());
  const show = async () => {
    const U = await units(), q = inp.value.toLowerCase().trim(), have = new Set(exclude());
    const rows = U.rows.filter(r => !have.has(r.id) && (!type.value || r.type === type.value) && only(r) && (!q || r.name.toLowerCase().includes(q))).slice(0, 200);
    list.replaceChildren(...(rows.length ? rows.map(r => h("div", { onmousedown: e => { e.preventDefault(); inp.value = keepName ? r.name : ""; onPick(r); list.hidden = true; } },
      typeChip(r.type), " ", r.name, h("span", { class: "muted small" }, ` ${booksLabel(r.books)} · ${fmt(r.mentions)}`)))
      : [h("div", { class: "muted small" }, "No entity by that name.")]));
    list.hidden = false;
  };
  inp.addEventListener("input", show); inp.addEventListener("focus", show);
  inp.addEventListener("keydown", e => { if (e.key === "Escape") { list.hidden = true; inp.blur(); } });
  inp.addEventListener("blur", () => setTimeout(() => (list.hidden = true), 150));
  return h("div", { class: "row" }, h("div", { style: { position: "relative" } }, inp, list), type);
}

/** Choosing entities by type: a toggle per type present in the selected books, with its entity count; the chosen types together
    are one group (every entity of those types). `types`: the ones ticked to begin with; onChange(spec) with
    `{kind: "type", types, name}`, or null when none is ticked. */
function typePicker(types, onChange) {
  const have = new Set(types), row = h("div", { class: "row" }, h("span", { class: "muted small" }, "Loading…"));
  const fire = () => {
    const ticked = TYPES.filter(t => have.has(t));
    onChange(ticked.length ? { kind: "type", types: ticked, name: "all " + ticked.join(" + ") } : null);
  };
  units().then(U => {
    const n = {};
    U.rows.forEach(r => (n[r.type] = (n[r.type] || 0) + 1));
    const draw = () => row.replaceChildren(...TYPES.filter(t => n[t]).map(t => h("button", { type: "button", class: "btn small" + (have.has(t) ? " primary" : ""),
      "aria-pressed": String(have.has(t)), title: `${TYPE_NAMES[t]}: ${plural(n[t], "entity", "entities")}`,
      onclick: () => { have.has(t) ? have.delete(t) : have.add(t); draw(); fire(); } }, `${t} (${fmt(n[t])})`)));
    draw();
  });
  return row;
}

/** A control for choosing what to look at: one entity, a group of entities, a tag group, "everyone else", a narrator,
    a book or a gender, and optionally which books.
    value: the current spec; onChangeRaw(spec) is called when it changes (with null when a group is emptied).
    opts: unitOnly, others, narration, group, book, gender, books. */
function picker(value, onChangeRaw, opts = {}) {
  const box = h("div", { class: "picker" });
  let mode = value ? value.kind : "unit";
  let books = (value && value.books) || [];
  let last = value;
  const onChange = v => { last = v; onChangeRaw(v && opts.books && v.kind !== "others" ? { ...v, books } : v); };
  function draw() {
    const modes = [["unit", "Entity"], ...(opts.group ? [["group", "Group"], ["type", "Type"]] : []), ["tag", "Tag"]];
    if (opts.narration) modes.push(["narration", "Narrator"]);
    if (opts.book) modes.push(["book", "Book"]);
    if (opts.gender) modes.push(["gender", "Gender"]);
    if (opts.others) modes.unshift(["others", "Everyone else"]);
    const kids = opts.unitOnly ? [] : [seg(modes, mode, m => { mode = m; if (m === "others") onChange({ kind: "others" }); draw(); })];
    if (opts.unitOnly) mode = "unit";
    if (mode === "unit") {
      kids.push(unitSearch({ placeholder: "Find by name…", value: value && value.kind === "unit" ? value.name : "", keepName: true,
        onPick: r => onChange({ kind: "unit", id: r.id, name: r.name, type: r.type }) }));
    } else if (mode === "group") {
      kids.push(groupPicker(value, onChange));
    } else if (mode === "type") {
      kids.push(typePicker(value && value.kind === "type" ? value.types || [value.type] : [], onChange));
    } else if (mode === "narration") {
      const sel = h("select", {}, h("option", { value: "" }, "Loading…"));
      api("/api/dialogue/narrators", withBooks({})).then(r => {
        const cur = value && value.kind === "narration" ? value.id : "";
        sel.replaceChildren(h("option", { value: "all" }, "All narration"), r.rows.map(x => h("option", { value: x.id, selected: x.id === cur }, x.name)));
        if (!cur) sel.value = r.rows[0] ? r.rows[0].id : "all";
        const fire = () => onChange({ kind: "narration", id: sel.value, name: sel.value === "all" ? "all narration" : sel.selectedOptions[0].textContent });
        sel.onchange = fire;
        if (!value || value.kind !== "narration") fire();
      });
      kids.push(sel);
    } else if (mode === "tag") {
      const tags = S.lib.tags;
      if (!tags.length) kids.push(h("span", { class: "muted small" }, "No tags yet. Add tags on an entity's page."));
      else {
        const v = value && value.kind === "tag" ? value : { kind: "tag", tag: tags[0], type: "" };
        const tagSel = h("select", {}, tags.map(t => h("option", { value: t, selected: t === v.tag }, t)));
        const typeSel = typeSelect(v.type, () => fire());
        const fire = () => onChange({ kind: "tag", tag: tagSel.value, type: typeSel.value });
        tagSel.onchange = fire;
        kids.push(tagSel, typeSel);
        if (!value || value.kind !== "tag") setTimeout(fire);
      }
    } else if (mode === "book") {
      const own = value && value.kind === "book";                                              // a book is already chosen here, else the last one chosen in any picker
      const cur = own ? value.book : selected().includes(S.pickedBook) ? S.pickedBook : "";
      const sel = h("select", {}, selected().map(b => h("option", { value: b, selected: b === cur }, bookTitle(b))));
      const fire = () => { S.pickedBook = sel.value; onChange({ kind: "book", book: sel.value, name: bookTitle(sel.value) }); };
      sel.onchange = fire;
      if (!own) setTimeout(fire);
      kids.push(sel);
    } else if (mode === "gender") {
      const sel = h("select", {}, h("option", { value: "" }, "Loading…"));
      units().then(U => {
        const cur = value && value.kind === "gender" ? value.pron : "";
        sel.replaceChildren(U.genders.map(g => h("option", { value: g.pron, selected: g.pron === cur }, `${genderLabel(g.pron)} (${fmt(g.entities)})`)));
        if (!cur) sel.value = U.genders[0] ? U.genders[0].pron : "";
        const fire = () => onChange({ kind: "gender", pron: sel.value, name: genderLabel(sel.value) });
        sel.onchange = fire;
        if (!value || value.kind !== "gender") fire();
      });
      kids.push(sel);
    }
    if (opts.books && mode !== "others" && selected().length > 1)
      kids.push(booksChooser(books, b => { books = b; if (last && last.kind === mode) onChange(last); }));
    box.replaceChildren(...kids);
  }
  draw();
  return box;
}
/** "Title", "A + B" or "5 books" for a list of book ids. */
const booksLabel = ids => { const t = ids.map(bookTitle); return t.length === 1 ? t[0] : t.length > 3 ? `${t.length} books` : t.join(" + "); };
/** A compact chip for one entity of a group (the group/compare picker's chosen list, a group profile's members):
    its type as a short label and a colour bar rather than a separate badge, so it reads as one pill. `link`: make
    the name open the entity's profile (a group profile does this; the picker doesn't, since picking is the point there). */
function gtag(m, onRemove, link) {
  return h("span", { class: "gtag", style: { "--c": TC[m.type] }, title: m.books ? booksLabel(m.books) : "" },
    h("span", { class: "k" }, m.type),
    link ? h("a", { href: "#/entities/" + encodeURIComponent(m.id) }, m.name) : m.name,
    m.books ? h("small", { class: "muted" }, booksLabel(m.books)) : null,
    h("button", { title: "Remove " + m.name, "aria-label": "Remove " + m.name, onclick: onRemove }, "×"));
}
/** A readable name for a spec {kind: unit|group|type|tag|narration|book|gender|others, …}. */
const specLabel = s => {
  if (!s) return "?";
  const base = ["narration", "unit", "group", "book", "gender"].includes(s.kind) ? s.name : s.kind === "type" ? s.name || "all " + (s.types || [s.type]).join(" + ") : s.kind === "tag" ? `tag “${s.tag}”${s.type ? " (" + s.type + ")" : ""}` : "everyone else";
  return s.books && s.books.length ? `${base} in ${booksLabel(s.books)}` : base;
};

/* choose some of the selected books; [] means all of them */
/** A drop-down to choose some of the selected books ([] = all of them); onChange(ids) when it changes. */
function booksChooser(value, onChange) {
  const cur = new Set(value || []);
  const ids = selected();
  const summary = h("summary", { class: "btn small" });
  const setSummary = () => (summary.textContent = cur.size ? `In ${booksLabel(ids.filter(id => cur.has(id)))}` : "In all selected books");
  setSummary();
  const fire = () => { setSummary(); onChange(ids.filter(id => cur.has(id))); };
  return h("details", { class: "books-pick" }, summary,
    h("div", { class: "books-menu" },
      h("label", { class: "book" }, h("input", { type: "checkbox", checked: !cur.size, onchange: e => { if (e.target.checked) { cur.clear(); e.target.closest(".books-menu").querySelectorAll("input[data-b]").forEach(i => (i.checked = false)); fire(); } else e.target.checked = true; } }), "All selected books"),
      ids.map(id => h("label", { class: "book" }, h("input", { type: "checkbox", "data-b": id, checked: cur.has(id),
        onchange: e => { e.target.checked ? cur.add(id) : cur.delete(id); if (cur.size === ids.length) cur.clear(); const all = e.target.closest(".books-menu").querySelector("input:not([data-b])"); all.checked = !cur.size; fire(); } }), bookTitle(id)))));
}

/* ---------- statistics controls ---------- */
/** The controls every keyness comparison shares (measure, test, minimum frequency, significance, Bonferroni); saved in S.stat. */
function statControls(onChange, opts = {}) {
  const st = S.stat, save = () => { saveStat(onChange); onChange(); };
  const lab = (text, el, title) => h("label", { title }, text, el);
  const sel = (k, options, cast = x => x) => h("select", { onchange: e => { st[k] = cast(e.target.value); save(); } },
    Object.entries(options).map(([v, l]) => h("option", { value: v, selected: String(st[k]) === String(v) }, l)));
  return h("div", { class: "controls" },
    opts.pre || null,
    lab("Rank by", sel("measure", S.lib.measures)),
    lab("Significance test", sel("test", S.lib.tests)),
    lab("Minimum frequency", h("input", { type: "number", min: 1, value: st.min_freq, onchange: e => { st.min_freq = Math.max(1, +e.target.value || 1); save(); } }),
      opts.both ? "Items must occur at least this often on one side" : "Items must occur at least this often in the target"),
    lab("Significance level", sel("alpha", { 0.05: "p < 0.05", 0.01: "p < 0.01", 0.001: "p < 0.001", 0.0001: "p < 0.0001" }, Number)),
    h("label", { class: "inline" }, h("input", { type: "checkbox", checked: st.bonferroni, onchange: e => { st.bonferroni = e.target.checked; save(); } }), "Bonferroni correction"),
    h("label", { class: "inline" }, h("input", { type: "checkbox", checked: st.show_all, onchange: e => { st.show_all = e.target.checked; save(); } }), "Show non-significant"));
}
/** The settings of a chi-squared test across books or slices (minimum frequency, significance level, Bonferroni): three labelled controls
    for a `.controls` row, saved in S.stat like the other comparisons'; `onChange` re-runs the panel that shows them. */
function acrossControls(onChange) {
  const st = S.stat, save = () => { saveStat(onChange); onChange(); };
  return [
    h("label", {}, "Minimum frequency for the test", h("input", { type: "number", min: 1, value: st.min_freq, onchange: e => { st.min_freq = Math.max(1, +e.target.value || 1); save(); } })),
    h("label", {}, "Significance level", h("select", { onchange: e => { st.alpha = +e.target.value; save(); } },
      [0.05, 0.01, 0.001, 0.0001].map(a => h("option", { value: a, selected: st.alpha === a }, "p < " + a)))),
    h("label", { class: "inline" }, h("input", { type: "checkbox", checked: st.bonferroni, onchange: e => { st.bonferroni = e.target.checked; save(); } }), "Bonferroni correction")];
}
/** What a word needs to be tested, as a test's `summary` says: "at least 3 occurrences", with its `min_range` ("… in at least 2 books"), or, with
    `each_book` (the Words setting), in each of at least `fewest` books (default `min_range`, else one). */
function needed(summary, fewest = summary.min_range || 1) {
  const n = `at least ${summary.min_freq} occurrence${summary.min_freq === 1 ? "" : "s"}`;
  if (summary.each_book) return fewest > 1 ? `${n} in each of at least ${fewest} books` : `${n} in at least one book`;
  return summary.min_range > 1 ? `${n} in at least ${summary.min_range} books` : n;
}
/** The "How these numbers are calculated" box for a comparison's summary. */
function statNote(summary) {
  const n = S.lib.stat_notes;
  return note("How these numbers are calculated",
    `Each item is compared with a 2×2 table: its count in the target (a) against all other items in the target (c − a), and the same for the reference (b, d − b). Here c = ${fmt(summary.c)} and d = ${fmt(summary.d)}.`,
    n[summary.measure] ? `Ranked by ${S.lib.measures[summary.measure]}: ${n[summary.measure]}` : null,
    summary.measure !== summary.test ? `Significance: ${n[summary.test]}` : null,
    `${plural(summary.tested, "item")} had at least ${summary.min_freq} occurrence${summary.min_freq === 1 ? "" : "s"} and were tested. ` +
      (summary.bonferroni ? `With the Bonferroni correction, an item counts as significant when p < ${summary.alpha} ÷ ${summary.tested} = ${summary.threshold.toExponential(2)}.` : `An item counts as significant when p < ${summary.alpha}.`),
    "Log ratio, %DIFF and the odds ratio are effect sizes: they say how big a difference is, while p says how confident you can be that it isn't chance. With small counts, large effect sizes are common and unreliable, so read them together.");
}
/** The table columns for a keyness result (counts, percentages, the chosen measure, G², log ratio, p…). */
function statCols(summary, both, names) {
  const m = summary.measure;
  const cols = [
    { k: "item", label: "Item" },
    { k: "a", label: both ? names[0] : "Target", num: true, fmt: v => fmt(v), title: "Count in the target" },
    { k: "pa", label: "%", num: true, fmt: v => fmt(v, 2), title: "Share of the target's items" },
    { k: "b", label: both ? names[1] : "Reference", num: true, fmt: v => fmt(v), title: "Count in the reference" },
    { k: "pb", label: "% ", num: true, fmt: v => fmt(v, 2), title: "Share of the reference's items" },
  ];
  const meas = {
    ll: { k: "ll", label: "G²", num: true, fmt: fmtSig },
    chi2: { k: "chi2", label: "χ²", num: true, fmt: fmtSig },
    lr: { k: "lr", label: "Log ratio", num: true, fmt: v => fmt(v, 2) },
    pdiff: { k: "pdiff", label: "%DIFF", num: true, fmt: v => fmt(v, 0) },
    or: { k: "or", label: "Odds ratio", num: true, fmt: (v, r) => `${fmt(v, 2)} (${fmt(r.or_lo, 2)}–${fmt(r.or_hi, 2)})`, csv: v => v },
  };
  cols.push(meas[m]);
  for (const k of ["ll", "lr"]) if (k !== m) cols.push(meas[k]);
  cols.push({ k: "p", label: "p", num: true, fmt: fmtP, title: `p from ${S.lib.tests[summary.test]}` });
  if (both) cols.push({ k: "lr", label: "More typical of", sortVal: r => r.lr, fmt: v => v > 0 ? names[0] : names[1], csv: v => v > 0 ? names[0] : names[1] });
  if (summary.bonferroni || S.stat.show_all) cols.push({ k: "sig", label: "Significant", fmt: v => v ? "yes" : "no", sortVal: r => r.sig ? 1 : 0 });
  return cols;
}
