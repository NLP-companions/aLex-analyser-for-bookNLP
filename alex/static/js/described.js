"use strict";
/* ---------- Described as ---------- */
/* What an entity, group, tag or gender is described and called as, and by whom (core/described.py, POST /api/described).
   One table: a row per word, a column per kind of describer; a cell is how often that describer says it, with the share, the rate per
   1,000 words and the keyness if you ask for them. */

const DESC_KINDS = [["mod", "Modifiers"], ["name", "Called: names"], ["desc", "Called: descriptions"], ["pron", "Called: pronouns"],
  ["agent", "Actions"], ["patient", "Done to them"], ["poss", "Possessions"], ["prep", "Prepositions and settings"]];
const DESC_SPLITS = [["entity", "Each describer"], ["gender", "Gender"], ["tag", "Tag"], ["book", "Book"], ["voice", "Narration or speech"], ["custom", "Columns you pick"]];
const DESC_VOICES = [["both", "Narration and speech"], ["narration", "Narration"], ["speech", "Speech"]];
/** What is remembered between visits (the chosen target and the columns you pick are not: they can be groups of dozens of entities). */
S.desc = { ...loadState("analyser.desc", { kind: "mod", split: "entity", voice: "both", top: 8, show: { share: false, per1k: false, ll: true, p: false } }), target: null, columns: [] };
/** Remember the Described-as settings (not the target or the picked columns). */
const saveDesc = () => { const { target, columns, ...settings } = S.desc; saveState("analyser.desc", settings); };
const MAX_PICKED = 12;          // as in core/described.py

/** A link to the Described-as page with `target` already chosen: an entity's, group's, book's or gender's own `u.target` on its profile page. */
const describedLink = target => h("a", { href: "#/described", title: "What it is described and called as, and by whom", onclick: () => { S.desc.target = target; } }, "Described by whom →");

/** One cell of the table: the count, with the other measures beside it as chosen, tinted blue when the word is markedly typical of
    this column and red when markedly untypical (G² with p < 0.05 against the other columns). Hover for every figure. */
function describedCell(c, show, open) {
  if (!c.n) return h("span", { class: "muted", title: c.ll < 0 && c.p < 0.05 ? `never, though typical of the others (G² ${fmtSig(c.ll)})` : "" }, "·");
  const tint = c.p < 0.05 ? (c.ll > 0 ? "rp" : "rn") : "";
  const extra = [show.share ? `${fmt(c.share, 1)}%` : null, show.per1k ? (c.per1k == null ? "—" : `${fmt(c.per1k, 2)}/1k`) : null, show.ll ? `G² ${fmtSig(c.ll)}` : null, show.p ? `p ${fmtP(c.p)}` : null].filter(Boolean);
  return h("span", { class: "evlink " + tint, onclick: open, title: `${fmt(c.n)} · ${fmt(c.share, 1)}% of this column · ${c.per1k == null ? "—" : fmt(c.per1k, 2)} per 1,000 words · G² ${fmtSig(c.ll)} (p ${fmtP(c.p)}). Click for the sentences.` },
    fmt(c.n), extra.length ? h("small", { class: "muted" }, " · " + extra.join(" · ")) : null);
}

/** The table and notes for one answer of /api/described. */
function describedResult(r, show, open) {
  const kind = DESC_KINDS.find(k => k[0] === r.kind)[1];
  if (!r.all.findings) return h("div", { class: "panel empty" }, `Nothing found: ${r.target} has no ${kind.toLowerCase()} in these books` + (r.voice === "both" ? "." : ` in ${r.voice}.`),
    " Try another kind above, or check that the entities are counted (the minimum mentions are on the Settings page).");
  const cols = [{ k: "item", label: r.kind === "name" || r.kind === "desc" || r.kind === "pron" ? "Form" : "Word" },
    { k: "total", label: `All · ${fmt(r.all.findings)}`, num: true, fmt: (v, row) => h("span", { class: "evlink", onclick: () => open(row.item, null, "all describers") }, fmt(v), h("small", { class: "muted" }, ` · ${fmt(row.share, 1)}%`)), title: `${fmt(r.all.findings)} findings in all, ${fmt(r.all.narration)} told by a narrator` },
    ...r.columns.map((c, i) => ({
      k: "c" + i, label: `${c.label} · ${fmt(c.findings)}`, num: true, fmt: (v, row) => describedCell(row.cells[i], show, () => open(row.item, c.id, c.label)), csv: (v, row) => row.cells[i].n,
      title: `${fmt(c.findings)} findings, ${fmt(c.narration)} told by a narrator; ${fmt(c.words)} words spoken or narrated`,
      sortVal: row => show.ll ? row.cells[i].ll : row.cells[i].n }))];
  const rows = r.rows.map(row => ({ ...row, ...Object.fromEntries(row.cells.map((c, i) => ["c" + i, c.n])) }));
  return h("div", {},
    h("p", { class: "small", style: { margin: "0 0 8px" } }, `${r.target}: ${plural(r.all.findings, "finding")} (${fmt(r.distinct)} different), ${fmt(r.all.narration)} told by a narrator and ${fmt(r.all.findings - r.all.narration)} said in quotes. `,
      r.rows.length < r.distinct ? `The ${fmt(r.rows.length)} most frequent are shown.` : ""),
    table(cols, rows, { limit: 40, sort: "total", csvName: `${r.target} ${kind}` }),
    note("What this shows", r.notes.describer, r.notes.measures,
      "Click a count to read the sentences behind it. Blue cells are markedly typical of that column, red ones markedly untypical (G² with p < 0.05); a dot is zero. The p-value is that of the G² (χ² with one degree of freedom); with many words in the table, some small p-values arise by chance. “All others” gathers the columns beyond the number you asked for."));
}

/** The Described-as page. */
async function renderDescribed(main) {
  await units();
  const d = S.desc, out = h("div"), controls = h("div"), targetOpts = { group: true, gender: true, book: true };
  d.target = followFocus("described", d.target, targetOpts);                       // what to look at follows the focus, if shared (focus.js)
  let latest = 0;
  const run = async () => {
    const mine = ++latest;
    if (!d.target) { out.replaceChildren(h("div", { class: "panel empty" }, "Choose what to look at: an entity, a group of entities (search by name to gather them all), a tag or a gender.")); return; }
    out.replaceChildren(loading("Counting…"));
    const picked = d.columns.filter(Boolean).map(c => ({ ...c, members: undefined }));
    if (d.split === "custom" && !picked.length) { out.replaceChildren(h("div", { class: "panel empty" }, "Pick the columns: each is an entity, a group, a tag or a gender, and counts what they say.")); return; }
    const request = { target: { ...d.target, members: undefined }, kind: d.kind, split: d.split, voice: d.voice, top: d.top, columns: d.split === "custom" ? picked : undefined };
    const r = await api("/api/described", withBooks(request));
    if (mine === latest) out.replaceChildren(describedResult(r, d.show, (item, column, label) =>
      openEvidence(`“${item}”`, `${r.target}, as told by ${label}${r.voice === "both" ? "" : " (" + r.voice + " only)"}`, { ...request, item, column }, "/api/described/evidence")));
  };
  const colsBox = h("div", { class: "pickcols" });
  const drawCols = () => colsBox.replaceChildren(h("div", { class: "muted small" }, "Each column counts what these entities say (an entity can be in several columns). Findings in none of them are only in the All column."),
    d.columns.map((spec, i) => h("div", { class: "pickcol" }, picker(spec, v => { d.columns[i] = v; run(); }, { group: true, gender: true }),
      h("button", { class: "btn small", type: "button", onclick: () => { d.columns.splice(i, 1); drawCols(); run(); } }, "Remove"))),
    d.columns.length < MAX_PICKED ? h("button", { class: "btn small", type: "button", onclick: () => { d.columns.push(null); drawCols(); } }, "Add a column") : null);
  const change = (key, value) => {
    d[key] = value;
    if (key === "split" && value === "custom" && !d.columns.length) d.columns.push(null);
    if (key === "split") drawCols();
    saveDesc(); drawControls(); run();
  };
  const drawControls = () => controls.replaceChildren(
    h("div", { class: "subtabs" }, DESC_KINDS.map(([k, label]) => h("button", { class: k === d.kind ? "on" : "", onclick: () => change("kind", k) }, label))),
    h("div", { class: "controls" },
      h("div", { class: "fld" }, "Split by who says it", seg(DESC_SPLITS, d.split, v => change("split", v))),
      h("div", { class: "fld" }, "Voice", seg(DESC_VOICES, d.voice, v => change("voice", v))),
      d.split === "custom" ? null : h("label", {}, "Columns", h("input", { type: "number", min: 1, max: 30, value: d.top, style: { width: "64px" }, onchange: e => change("top", Math.max(1, Math.min(30, +e.target.value || 8))) })),
      h("div", { class: "fld" }, "Show beside the count", h("div", { class: "row" }, [["share", "Share"], ["per1k", "Per 1,000 words"], ["ll", "Keyness (G²)"], ["p", "p-value of the keyness"]].map(([k, label]) =>
        h("label", { class: "inline" }, h("input", { type: "checkbox", checked: d.show[k], onchange: e => { d.show[k] = e.target.checked; saveDesc(); run(); } }), label)))),
      helpButton("described", "split", "Split, voice and columns")),
    d.split === "custom" ? colsBox : null);
  main.replaceChildren(
    h("section", { class: "panel" }, h("h2", {}, "Described as"),
      h("div", { class: "fld" }, "What to look at", subjectPicker("described", d.target, v => { d.target = v; run(); }, targetOpts)),
      h("p", { class: "small muted", style: { margin: "6px 0 10px" } },
        "What this entity, group, tag or gender is described and called as, and by whom: the speaker of the quote it is in, or the narrator of the paragraph. ",
        "BookNLP often splits one place or person into many entities; under Group, “add every entity named…” gathers them (for the moor in Hound: moor, mire, of type LOC, so that people described by the moor are left out)."),
      controls),
    out);
  drawCols();
  drawControls();
  run();
}
