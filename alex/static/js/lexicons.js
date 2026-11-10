"use strict";
/* ---------- Over time → Lexicons ---------- */
/* Your word lexicons (core/lexicons.py, /api/lexicons): lists of words in categories, one file each in the data folder's lexicon folder, so
   the Statistics tab offers their categories as variables too. The page is one collapsible panel per lexicon (the emotion lexicon first,
   always). A panel plots the categories you choose as words per 1,000 across the books (POST /api/narrative/lexicon) and lets you rename,
   replace and remove the lexicon, and browse and edit its words. A collapsed panel loads nothing until it is opened (pagetools.js). */

const LEX_SHOWN = 500;                                  // words of a category listed at once when browsing

/** Draw the Lexicons page again (after a lexicon was added, replaced, renamed or removed). */
const lexRedraw = () => renderNarrative($("#main"), "lexicons");

/** The text of a file: UTF-8, or Windows-1252 when that gives garbled characters (what Excel saves a .csv as). */
async function lexText(file) {
  const bytes = await file.arrayBuffer();
  try { return new TextDecoder("utf-8", { fatal: true }).decode(bytes); } catch (e) { return new TextDecoder("windows-1252").decode(bytes); }
}

/** Ask for a text, .csv or .tsv file and give its name (without the extension) and its text to `use`. */
function lexFile(use) {
  const input = h("input", { type: "file", accept: ".txt,.tsv,.csv,text/plain,text/csv,text/tab-separated-values", onchange: async () => { const f = input.files[0]; if (f) await use(f.name.replace(/\.[^.]+$/, ""), await lexText(f)); } });
  input.click();
}

/** Store a new lexicon from text (`emotion`: as the emotion lexicon), show its panel open, and draw the page again. */
async function lexCreate(name, text, emotion = false) {
  const r = await api("/api/lexicons", { name, text, emotion });
  const x = r.lexicons.find(y => y.id === r.id);
  if (!S.nar.lexSeen.includes(x.id)) S.nar.lexSeen.push(x.id);
  delete cx.saved[cxKey(x.name)];
  saveNar(); cxSave();
  toast(`Loaded ${x.name}: ${plural(Object.keys(x.categories).length, "category", "categories")}.`);
  lexRedraw();
}

/** A lexicon met for the first time starts folded, except the first panel of the page: with many lexicons and books, each open panel costs a
    calculation. Lexicons that are gone are forgotten, so a new one with the same id starts folded again. */
function lexFoldNew(rows) {
  const N = S.nar;
  N.lexSeen = N.lexSeen.filter(id => rows.some(r => r.id === id));
  rows.forEach((r, i) => {
    if (N.lexSeen.includes(r.id)) return;
    N.lexSeen.push(r.id);
    if (i > 0) cx.saved[cxKey(r.name)] = 1;
  });
  saveNar(); cxSave();
}

/** The Lexicons page: what a lexicon is, buttons to add one, and a panel for each. */
async function narLexicons(body) {
  const r = await api("/api/lexicons");
  const rows = r.lexicons.some(x => x.id === "emotion") ? r.lexicons : [{ id: "emotion", name: "Emotion", missing: true, categories: {} }, ...r.lexicons];
  lexFoldNew(rows);
  body.append(lexIntro(), rows.map(lexPanel));
}

/** The first panel: what a lexicon is, and ways to add one (a file, or text typed or pasted into a box). */
function lexIntro() {
  const form = h("div");
  const newForm = () => {
    const name = h("input", { type: "text", placeholder: "Name", "aria-label": "Name of the lexicon" });
    const text = h("textarea", { rows: 8, placeholder: "moor\nhill\nhound\n\nor a word and a category on each line:\nmoor\tnature", "aria-label": "Words of the lexicon" });
    form.replaceChildren(h("div", { class: "lexedit" }, name, text, h("div", { class: "row" },
      h("button", { class: "btn small primary", onclick: () => lexCreate(name.value, text.value) }, "Create"),
      h("button", { class: "btn small", onclick: () => form.replaceChildren() }, "Cancel"))));
    name.focus();
  };
  return h("section", { class: "panel" }, h("h2", {}, "Your lexicons"),
    h("p", { class: "small" }, "A lexicon is a list of words in categories (emotions, colours, archaic words…). Each panel below plots how often the words of its categories occur across the books. ",
      "The same lexicons are offered as variables in ", h("a", { href: "#/stats" }, "Statistics"), "."),
    h("p", { class: "small muted" }, "A text, .csv or .tsv file (or a box) holds a list with one word on each line (the whole list is one category, named after the lexicon), ",
      "a word and a category on each line, optionally with 1 or 0 (as in the NRC Emotion Lexicon), or one column for each category, with the category names in the first row. ",
      "Columns are separated by tabs, commas or semicolons; a header row is skipped. Words match by their form, else by their lemma, in lowercase."),
    h("div", { class: "row" },
      h("button", { class: "btn", onclick: () => lexFile((name, text) => lexCreate(name, text)) }, "Load a file…"),
      h("button", { class: "btn", onclick: newForm }, "Type or paste a lexicon…")),
    form);
}

/** What the emotion panel shows until the emotion lexicon is loaded. */
function lexLoadEmotion() {
  return h("div", {}, h("p", { class: "small" }, "Load a word–emotion lexicon to plot emotions. The NRC Emotion Lexicon (Mohammad & Turney) is the usual choice. It's free for research, but can't be included here, so download the word-level file from ",
    h("a", { href: "https://saifmohammad.com/WebPages/NRC-Emotion-Lexicon.htm", target: "_blank", rel: "noopener" }, "its author's site"),
    " and load “NRC-Emotion-Lexicon-Wordlevel”. Any file with a word, a category and optionally 1/0 on each line works too."),
    h("button", { class: "btn", onclick: () => lexFile((name, text) => lexCreate(name, text, true)) }, "Load the emotion lexicon…"));
}

/** A lexicon's panel. `row` is its entry in /api/lexicons ({id, name, source, categories, problem}); the emotion lexicon, if not loaded yet, is a
    `row` with `missing`. The content is drawn when the panel is open (at once, or when it is first expanded). */
function lexPanel(row) {
  const N = S.nar, st = { open: false, cat: null };       // st: the words box, kept when the panel is drawn again
  const inner = h("div");
  const panel = h("section", { class: "panel" }, h("h2", {}, row.name), inner);
  const base = () => "/api/lexicons/" + encodeURIComponent(row.id);
  let filled = false;

  /** The buttons that change the lexicon as a whole. Naming asks in place. */
  const acts = h("div", { class: "row" });
  const drawActs = () => {
    const ask = (label, initial, ok) => {
      const box = h("input", { type: "text", value: initial, "aria-label": label });
      box.onkeydown = e => { if (e.key === "Enter") ok(box.value); if (e.key === "Escape") drawActs(); };
      acts.replaceChildren(box, h("button", { class: "btn small primary", onclick: () => ok(box.value) }, "OK"), h("button", { class: "btn small", onclick: drawActs }, "Cancel"));
      box.focus();
    };
    const rename = async name => {
      const was = !!cx.saved[cxKey(row.name)];
      await api(base() + "/rename", { name });
      delete cx.saved[cxKey(row.name)];
      if (was) cx.saved[cxKey(name.trim())] = 1;           // a panel's fold is remembered by its heading
      cxSave(); toast("Renamed."); lexRedraw();
    };
    acts.replaceChildren(
      row.id === "emotion" ? null : h("button", { class: "btn small", onclick: () => ask("New name", row.name, rename) }, "Rename"),
      h("button", { class: "btn small", title: "Give this lexicon the words of another file; its name stays",
        onclick: () => lexFile((_, text) => api(base() + "/replace", { text }).then(() => { toast("Replaced the words."); lexRedraw(); })) }, "Replace the words…"),
      h("button", { class: "btn small", onclick: () => {
        if (!confirm(`Remove the lexicon “${row.name}”? Its file is deleted. Statistics variables that use it will say it is missing.`)) return;
        api(base() + "/delete", {}).then(() => { toast("Removed."); lexRedraw(); }); } }, "Remove"));
  };

  /** A category was saved or deleted in the words box: take the new lexicon, keep the new category plotted, draw again. */
  const saved = (r, old, name) => {
    row = r.lexicons.find(x => x.id === row.id);
    if (N.lexCats[row.id] || name) N.lexCats[row.id] = [...chosen().filter(c => c !== old), ...(name ? [name] : [])];
    st.cat = name || null;
    saveNar(); draw();
  };

  /** The categories to plot: your choice, else the first eight (leaving out positive and negative, which would swamp the rest). */
  const chosen = () => {
    const cats = Object.keys(row.categories), mine = N.lexCats[row.id];
    if (mine) return mine.filter(c => cats.includes(c));
    const plain = cats.filter(c => !["positive", "negative"].includes(c));
    return (plain.length ? plain : cats).slice(0, 8);
  };

  const draw = () => {
    if (row.missing) { inner.replaceChildren(lexLoadEmotion()); return; }
    drawActs();
    if (row.problem) { inner.replaceChildren(h("p", { class: "warn small" }, row.problem), acts); return; }
    const cats = Object.keys(row.categories);
    const arc = h("div"), chips = h("div", { class: "chips" });
    const drawArc = async () => {
      const picked = chosen();
      if (!picked.length) { arc.replaceChildren(h("p", { class: "muted small" }, "Choose at least one category.")); return; }
      arc.replaceChildren(loading("Counting…"));
      const r = await api("/api/narrative/lexicon", withBooks({ seg: N.seg, lexicon: row.id, cats: picked, each: N.each.lexicons }));
      arc.replaceChildren(combinedControls(r, "lexicons", drawArc), chartBox(arcChart(r.segments, arcLines(r, "lexicons"), { ylabel: "words per 1,000", continuous: N.seg.scope === "corpus" }), "lexicon-" + row.id + "-arc"),
        arcTable(r.segments, r.series, row.name + " arc"), note("How this is calculated", S.lib.narrative_notes.lexicon));
    };
    const drawChips = () => chips.replaceChildren(cats.map(c => {
      const on = chosen().includes(c);
      return h("button", { class: "chip" + (on ? " on" : ""), "aria-pressed": String(on),
        onclick: () => { N.lexCats[row.id] = on ? chosen().filter(x => x !== c) : [...chosen(), c]; saveNar(); drawChips(); drawArc(); } }, c, h("span", { class: "n" }, fmt(row.categories[c])));
    }));
    drawChips();
    const words = Object.values(row.categories).reduce((a, n) => a + n, 0);
    inner.replaceChildren(
      h("p", { class: "small muted" }, `${plural(cats.length, "category", "categories")} · ${plural(words, "word")}` + (row.source ? ` · loaded from ${row.source}` : "")),
      acts, lexWords(row, st, saved), h("div", { class: "row", style: { margin: "8px 0" } }, chips), arc);
    drawArc();
  };

  const fill = () => { if (!filled) { filled = true; draw(); } };
  if (!cx.saved[cxKey(row.name)]) fill();                  // a folded panel waits for its "expand" event
  panel.addEventListener("expand", fill);
  return panel;
}

/** The "Words and categories" box of a lexicon: pick a category, search its words, edit it (name and words in a text box), delete it or add
    a new one. `st` ({open, cat}) is kept by the panel; `saved(answer, oldName, newName)` is told when a category was saved or deleted. */
function lexWords(row, st, saved) {
  const cats = Object.keys(row.categories), base = "/api/lexicons/" + encodeURIComponent(row.id);
  const out = h("div");
  let words = [], form = null, started = false;              // form: null, or {cat} while editing (cat null: a new category)

  /** Fetch the words of the chosen category, then draw. */
  const load = async () => { words = (await api(`${base}/words?category=${encodeURIComponent(st.cat)}`)).words; draw(); };
  const start = () => { if (started) return; started = true; st.cat = cats.includes(st.cat) ? st.cat : cats[0]; load(); };

  const draw = () => {
    if (form) { out.replaceChildren(editForm()); return; }
    const list = h("div"), q = h("input", { type: "search", placeholder: "Search the words", "aria-label": "Search the words of this category" });
    const drawList = () => {
      const hits = words.filter(w => w.includes(q.value.trim().toLowerCase()));
      list.replaceChildren(h("div", { class: "lexwords" }, hits.slice(0, LEX_SHOWN).map(w => h("span", {}, w))),
        h("p", { class: "small muted" }, `${plural(hits.length, "word")}` + (hits.length > LEX_SHOWN ? `; the first ${fmt(LEX_SHOWN)} are shown, search to narrow the list.` : ".")));
    };
    q.addEventListener("input", drawList);
    out.replaceChildren(
      h("div", { class: "row", style: { marginBottom: "6px" } },
        h("select", { "aria-label": "Category", onchange: e => { st.cat = e.target.value; load(); } }, cats.map(c => h("option", { value: c, selected: c === st.cat }, `${c} (${fmt(row.categories[c])})`))),
        q, h("button", { class: "btn small", onclick: () => { form = { cat: st.cat }; draw(); } }, "Edit"),
        h("button", { class: "btn small", onclick: () => { form = { cat: null }; draw(); } }, "New category")),
      list);
    drawList();
  };

  /** The form that renames a category and sets its words (or adds a new category), with Save, Cancel and (for an existing one) Delete. */
  const editForm = () => {
    const name = h("input", { type: "text", value: form.cat || "", placeholder: "Category name", "aria-label": "Category name" });
    const text = h("textarea", { rows: 12, "aria-label": "Words of the category", placeholder: "One word on each line" });
    text.value = form.cat ? words.join("\n") : "";
    const old = form.cat;
    return h("div", { class: "lexedit" }, name, text,
      h("p", { class: "small muted" }, "One word on each line (spaces and commas separate words too). Words are matched in lowercase."),
      h("div", { class: "row" },
        h("button", { class: "btn small primary", onclick: () => api(base + "/category", { category: old, name: name.value, text: text.value }).then(r => saved(r, old, name.value.trim().toLowerCase())) }, "Save"),
        h("button", { class: "btn small", onclick: () => { form = null; draw(); } }, "Cancel"),
        old ? h("button", { class: "btn small", onclick: () => {
          if (confirm(`Delete the category “${old}” from this lexicon?`)) api(base + "/category/delete", { category: old }).then(r => saved(r, old, null)); } }, "Delete the category") : null));
  };

  const box = h("details", { class: "note", open: st.open, ontoggle: e => { st.open = e.target.open; if (st.open) start(); } },
    h("summary", {}, "Words and categories"), out);
  if (st.open) start();
  return box;
}
