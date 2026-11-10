"use strict";
/* ---------- Sound and rhythm ---------- */
/* The Sound and rhythm tab (#/sound/<sub>, core/soundtab.py): the figures of prose rhythm and sound patterning for a part of the text
   (the Corpus scope: everything, narration, dialogue, or someone's speech), in four sub-tabs: Figures (a table and a chart per book or
   per chapter or slice, cut by the shared Measure over setting), Cadences (every pattern found at phrase ends; a row opens its phrases), Runs
   (alliteration, assonance, consonance, rhyme or repetition by what the runs share; a row opens its runs, longest first) and Scansion
   (one chapter or slice word by word, each word with its syllables' stresses above it, the cadences underlined, the runs of one kind
   coloured by what they share, and repetitions outlined), and Pronunciation (the words whose stress is guessed, most frequent first, and
   your corrections, with a form to correct any word: `sndCorrector`, also used on the Settings page). The window, boundary, alliteration
   and repetition settings of runs are the workspace's (Settings → Sound and rhythm); `sndRunBar` shows them where runs are shown (the
   Figures, Runs and Scansion sub-tabs, the Read view's sound layer, the Style page), and a change there is saved and the view counted
   again at once. Without the pronunciation dictionary the tab says how to install it. */

/** What is remembered between visits: the sub-tab, the scope, and each sub-tab's choices. */
S.snd = loadState("analyser.snd", { sub: "figures", scope: { kind: "all" }, by: "book", metric: "stressed", kind: "alliteration", end_only: false,
  book: null, index: 0, colour: "alliteration", every_cadence: false });
/** Remember the Sound and rhythm settings. */
const saveSnd = () => saveState("analyser.snd", S.snd);
/** The groups the sound figures fall in, by key (for the column chooser of the sound tables). */
const sndGroup = k => k === "guessed" ? "Pronunciation" : k.startsWith("cad_") ? "Cadences of phrase ends" : k.startsWith("end_") ? "Cadences of sentence ends"
  : k.endsWith("_runs") ? "Runs per 1,000 words" : k.endsWith("_share") ? "Words in runs" : k.endsWith("_length") ? "Run length" : k.startsWith("class_") ? "Sound profile" : "Stress and rhythm";
const SND_GUESSED_MAX = 10;                       // more guessed pronunciations than this (% of words) marks a row's figures (AL-PRIN-14)
/** Why a row of sound figures is marked: more than SND_GUESSED_MAX % of its words were not in the dictionary, so their stresses and sounds
    are guesses; or null. */
const sndGuessy = r => r.guessed != null && r.guessed > SND_GUESSED_MAX ? `${fmt(r.guessed, 1)}% of the words are guessed (not in the pronunciation dictionary): its sound figures are less certain; correct them under Pronunciation` : null;
/** A sound figure `{k, label, dec}` as a table column, in its group. */
const sndColumn = f => ({ k: f.k, label: f.label, num: true, group: sndGroup(f.k), fmt: v => v == null ? "—" : fmt(v, f.dec) });
/** The sound tables' column chooser: a headline set shown at first; "guessed" (how many pronunciations are guesses) is a warning and stays (AL-PRIN-14). */
const SND_COLUMNS = { id: "sound", show: ["words", "speech_words", "stressed", "npvi", "cad_cursus", "alliteration_runs", "assonance_runs", "rhyme_runs", "repetition_runs", "guessed"], keep: ["label", "guessed"] };
const SND_TABS = [["figures", "Figures"], ["cadences", "Cadences"], ["runs", "Runs"], ["scansion", "Scansion"], ["words", "Pronunciation"]];
const SND_KINDS = [["alliteration", "Alliteration"], ["assonance", "Assonance"], ["consonance", "Consonance"], ["rhyme", "Rhyme"], ["repetition", "Repetition"]];
/** The choices of the run settings, [value, label] (the Settings page uses them too). */
const SND_BOUNDARIES = [["sentence", "Sentence end"], ["paragraph", "Paragraph end"], ["none", "Nowhere"]];
const SND_ALLITERATION = [["stressed", "Stressed syllable"], ["sound", "First sound"], ["letter", "First letter"]];
const SND_REPETITION = [["lemma", "Same lemma"], ["form", "Same word form"], ["all", "Same lemma, all words"]];

/** The workspace's run settings as one compact bar (window, where runs stop, what alliteration compares, what a repetition is), for
    the places that show runs. A change is saved with the workspace's settings (as on the Settings page) and `onChange()` then draws
    the view again, so its runs are counted under the new setting at once. */
function sndRunBar(onChange) {
  const st = sndSettings();
  const save = async patch => {
    try { S.lib = await api("/api/settings", { sound: patch }); } catch { /* api() has said why; the redraw shows what is saved */ }
    onChange();
  };
  const win = sndWindowInput(st.window, n => save({ window: n }), "70px");
  const pick = (label, key, options) => h("label", {}, label, h("select", { "aria-label": label, onchange: e => save({ [key]: e.target.value }) },
    options.map(([v, l]) => h("option", { value: v, selected: v === st[key] }, l))));
  return h("div", { class: "controls snd-runbar", style: { margin: "6px 0 0" } },
    h("label", { title: "How near words must be to make a run: within this many content words of the one before" }, "Run window", win),
    pick("Runs stop at", "boundary", SND_BOUNDARIES), pick("Alliteration by", "alliteration", SND_ALLITERATION), pick("Repetition is", "repetition", SND_REPETITION),
    h("span", { class: "small muted" }, "Saved for this workspace; also under ", h("a", { href: "#/settings" }, "Settings"), "."));
}
/** The workspace's sound settings with the defaults filled in: {window, boundary, alliteration, repetition, corrections}. */
const sndSettings = () => ({ window: 3, boundary: "sentence", alliteration: "stressed", repetition: "lemma", corrections: {}, ...((S.lib.settings || {}).sound || {}) });
/** A number box for the run window (content words, a whole number from 1): a valid number is handed to `onSave(n)`, anything else
    is put back to `value` with a message. */
function sndWindowInput(value, onSave, width) {
  return h("input", { type: "number", min: 1, step: 1, value, "aria-label": "Run window (content words)", style: { width },
    onchange: e => { const n = +e.target.value; if (Number.isInteger(n) && n >= 1) onSave(n); else { e.target.value = value; toast("The window is a whole number, 1 or more.", true); } } });
}
/** A request body for the tab's routes: the selected books, the scope, and `extra`. */
const sndBody = extra => withBooks({ scope: S.snd.scope, ...extra });
/** The scope as words, for headings ("in narration"). */
const sndWhere = () => scopeLabel(S.snd.scope);

/** The Sound and rhythm tab: scope and slicer above the four sub-tabs. */
async function renderSound(main, sub) {
  const N = S.snd;
  if (SND_TABS.some(([k]) => k === sub)) N.sub = sub;
  saveSnd();
  const body = h("div");
  const redraw = () => renderSound(main, N.sub);
  main.replaceChildren(h("section", { class: "panel" },
    h("div", { class: "subtabs", style: { marginBottom: "10px" } }, SND_TABS.map(([k, l]) => h("button", { class: k === N.sub ? "on" : "", onclick: () => (location.hash = "#/sound/" + k) }, l))),
    N.sub === "words" ? null : h("div", { class: "controls" }, scopeControl(N.scope, v => { N.scope = v; saveSnd(); redraw(); }, { label: "Text" })),
    N.sub === "figures" || N.sub === "scansion" ? segControl(redraw, { timeline: false }) : null,
    ["figures", "runs", "scansion"].includes(N.sub) && S.lib.sound ? h("div", { class: "row" }, sndRunBar(redraw), helpButton("sound", "settings", "Settings for runs"))
      : h("p", { class: "small muted", style: { margin: "6px 0 0" } }, "Window, boundary, alliteration and repetition: ", h("a", { href: "#/settings" }, "Settings → Sound and rhythm"), ". ",
        helpButton("sound", "settings", "Settings for runs"))), body);
  if (!S.lib.sound) { body.append(h("section", { class: "panel" }, h("p", { class: "warn" }, S.lib.sound_missing))); return; }
  if (N.sub === "words") { await sndWords(body, redraw); return; }
  if (N.scope.kind === "speech" && !N.scope.speaker) { body.append(h("section", { class: "panel" }, h("p", { class: "muted" }, "Choose whose speech to measure."))); return; }
  await ({ figures: sndFigures, cadences: sndCadences, runs: sndRuns, scansion: sndScansion }[N.sub] || sndFigures)(body, redraw);
}

/** Figures: per book or per chapter or slice, a chart of one figure and a table of all of them, with how many words were guessed. */
async function sndFigures(body, redraw) {
  const N = S.snd;
  const out = h("section", { class: "panel" }, loading("Counting…"));
  body.append(out);
  const r = await api("/api/sound/figures", sndBody({ seg: { ...S.nar.seg, scope: "book" }, by: N.by }));
  const fig = r.figures.find(f => f.k === N.metric) || r.figures[0];
  const chart = N.by === "segment"
    ? arcChart(r.rows.map(x => ({ book: x.book, title: x.title, label: x.label, words: x.words })), [{ name: fig.label, values: r.rows.map(x => x[fig.k]) }])
    : hbarChart([{ name: fig.label, color: "#2e4a62", rows: r.rows.map(x => ({ item: x.title, n: x[fig.k] })) }], { max: 60, dec: fig.dec });
  const cols = [{ k: "title", label: "Book", fmt: (v, row) => relNum(v, N.by === "segment" ? null : sndGuessy(row)) },
    ...(N.by === "segment" ? [{ k: "label", label: "Segment", fmt: (v, row) => relNum(v, sndGuessy(row)) }] : []), { k: "words", label: "Words", num: true, fmt: v => fmt(v) },
    ...r.figures.map(sndColumn)];
  out.replaceChildren(
    h("div", { class: "controls" },
      h("div", { class: "fld" }, "One row per", seg([["book", "Book"], ["segment", S.nar.seg.mode === "chapters" ? "Chapter" : "Slice"]], N.by, v => { N.by = v; saveSnd(); redraw(); })),
      h("label", {}, "Chart", h("select", { onchange: e => { N.metric = e.target.value; saveSnd(); redraw(); } }, r.figures.map(f => h("option", { value: f.k, selected: f.k === fig.k }, f.label))))),
    r.rows.length ? chartBox(chart, `sound-${fig.k}`) : h("p", { class: "muted" }, `No words ${sndWhere()}.`),
    table(cols, r.rows, { limit: 200, csvName: `sound ${sndWhere()} by ${N.by}`, columns: SND_COLUMNS }),
    note("How these are calculated", S.lib.narrative_notes.sound, "Only the words of the chosen text count: in narration a sentence that holds a quote gives only its narration; in someone's speech only their quotes. MEASURES.md section 17 has the details."));
}

/** Cadences: the cursus forms and every pattern found at phrase ends, with their shares; a row opens its phrases in the drawer. */
async function sndCadences(body) {
  const N = S.snd;
  const out = h("section", { class: "panel" }, loading("Reading the cadences…"));
  body.append(out);
  const r = await api("/api/sound/cadences", sndBody({}));
  const open = row => openEvidence(`Cadence ${row.marks}`, `${row.type === "other" ? "" : row.type + ", "}phrases ${N.end_only ? "ending a sentence" : "ending"} with it, ${sndWhere()}`,
    { scope: N.scope, pattern: row.pattern, end_only: N.end_only }, "/api/sound/cadences");
  const pct = v => v == null ? "—" : fmt(v, 1);
  const types = Object.entries(r.types).map(([type, x]) => ({ type, ...x, marks: { planus: "/ x x / x", tardus: "/ x x / x x", velox: "/ x x x x / x", trispondaicus: "/ x x x / x" }[type] || "anything else" }));
  out.replaceChildren(
    h("h2", {}, `Cadences ${sndWhere()}`),
    h("p", { class: "small muted" }, `${fmt(r.phrase_ends)} phrase ends with a cadence, ${fmt(r.sentence_ends)} of them sentence ends; ${fmt(r.distinct)} different patterns. / is a stressed syllable, x an unstressed one.`),
    table([{ k: "type", label: "Cursus" }, { k: "marks", label: "Pattern", fmt: v => h("code", {}, v) }, { k: "n", label: "Phrase ends", num: true, fmt: v => fmt(v) }, { k: "pct", label: "%", num: true, fmt: pct },
      { k: "ends", label: "Sentence ends", num: true, fmt: v => fmt(v) }, { k: "end_pct", label: "%", num: true, fmt: pct }], types, { csvName: `cadence types ${sndWhere()}` }),
    h("div", { class: "controls", style: { marginTop: "12px" } }, h("label", { class: "inline", title: "Show only the phrases that end a sentence when a pattern is opened" },
      h("input", { type: "checkbox", checked: N.end_only, onchange: e => { N.end_only = e.target.checked; saveSnd(); } }), "Examples: sentence ends only")),
    table([{ k: "marks", label: "Pattern", fmt: v => h("code", {}, v) }, { k: "type", label: "Cursus", fmt: v => v === "other" ? "" : v },
      { k: "n", label: "Phrase ends", num: true, fmt: v => fmt(v) }, { k: "pct", label: "%", num: true, fmt: pct },
      { k: "ends", label: "Sentence ends", num: true, fmt: v => fmt(v) }, { k: "end_pct", label: "%", num: true, fmt: pct }],
    r.rows, { limit: 100, csvName: `cadences ${sndWhere()}`, onRow: open }),
    note("How this is calculated", "A cadence is a phrase's syllables from its last-but-one stress to the pause that ends it (. ? ! ; : , a dash or a bracket); a phrase with fewer than two stresses has none. Sentence ends are phrases closed by . ? ! … or by the end of the sentence. The four cursus forms are the cadences that classical and medieval prose shaped by rule; the rest are listed by their pattern. Click a pattern for its phrases (the first 100), with the cadence marked and repeated words outlined."));
}

/** Runs: for one kind, what the runs share and how many there are; a row opens its runs, longest first, with repetitions outlined. */
async function sndRuns(body, redraw) {
  const N = S.snd;
  const out = h("section", { class: "panel" }, loading("Finding the runs…"));
  body.append(out);
  const r = await api("/api/sound/runs", sndBody({ kind: N.kind }));
  const name = SND_KINDS.find(([k]) => k === N.kind)[1];
  const what = { alliteration: { stressed: "Stressed syllable's first consonant", sound: "First sound", letter: "First letter" }[sndSettings().alliteration],
    assonance: "Stressed vowel", consonance: "Final consonants", rhyme: "Stressed vowel and after", repetition: "Word" }[N.kind];
  const open = row => openEvidence(`${name}: ${row.key}`, `${plural(row.runs, "run")} ${sndWhere()}, longest first; repeated words are outlined`, { scope: N.scope, kind: N.kind, key: row.key }, "/api/sound/runs");
  out.replaceChildren(
    h("div", { class: "subtabs", style: { marginBottom: "10px" } }, SND_KINDS.map(([k, l]) => h("button", { class: k === N.kind ? "on" : "", onclick: () => { N.kind = k; saveSnd(); redraw(); } }, l))),
    h("p", { class: "small muted" }, `${plural(r.runs, "run")} of ${fmt(r.words)} words, ${fmt(r.text_words ? 1000 * r.runs / r.text_words : 0, 1)} per 1,000 words; ${fmt(r.eligible ? 100 * r.words / r.eligible : 0, 1)}% of the words that could be in one; ${fmt(r.distinct)} different ${N.kind === "repetition" ? "words" : "sounds"}. Click a row for its runs.`),
    table([{ k: "key", label: what, fmt: v => h("code", {}, v) }, { k: "runs", label: "Runs", num: true, fmt: v => fmt(v) }, { k: "words", label: "Words", num: true, fmt: v => fmt(v) },
      { k: "longest", label: "Longest", num: true, fmt: v => fmt(v) }], r.rows, { limit: 100, csvName: `${N.kind} ${sndWhere()}`, onRow: open }),
    note("How this is calculated", S.lib.narrative_notes.sound, "In the sentences, the run's words are marked; other words that repeat one nearby are outlined, so repetitions stand out inside sound runs. A repeated word never counts again in a sound run: it is a repetition instead."));
}

/** Scansion: one chapter or slice of one book word by word (the first 3,000 words), with stresses, cadences, runs and repetitions. */
async function sndScansion(body, redraw) {
  const N = S.snd, books = selected();
  if (!books.includes(N.book)) N.book = books[0];
  const out = h("section", { class: "panel" }, loading("Scanning…"));
  body.append(out);
  let r;
  try { r = await api("/api/sound/scan", sndBody({ book: N.book, seg: { ...S.nar.seg, scope: "book" }, index: N.index })); }
  catch (e) { N.index = 0; saveSnd(); out.replaceChildren(h("p", { class: "warn" }, e.message, " ", h("button", { class: "btn small", onclick: redraw }, "Start at the first"))); return; }
  const colour = N.colour, keys = [...new Set(r.runs.filter(x => x.kind === colour).map(x => x.key))];
  const runOf = new Map(), repeated = new Set(), cadAt = new Map(), cadEnd = new Map();
  r.runs.forEach(x => { if (x.kind === colour) x.toks.forEach(t => runOf.set(t, x.key)); if (x.kind === "repetition") x.toks.forEach(t => repeated.add(t)); });
  r.cadences.forEach(c => { for (let t = c.first; t <= c.last; t++) cadAt.set(t, c); cadEnd.set(c.last, c); });
  const word = tk => {
    if (!tk.m) return h("span", { class: "sc-p" + (tk.out ? " out" : "") }, tk.w);
    const key = runOf.get(tk.t), found = cadAt.get(tk.t), end = cadEnd.get(tk.t);
    const cad = found && (found.type !== "other" || N.every_cadence) ? found : null;           // other cadences only when asked for
    const cls = ["sc-w", tk.out ? "out" : "", key != null ? "run" : "", repeated.has(tk.t) ? "rep" : "", cad ? "cad" : "", cad && cad.type !== "other" ? "cursus" : "", tk.src === "guess" ? "guess" : ""].filter(Boolean).join(" ");
    const title = [key != null ? `${colour}: ${key}` : null, repeated.has(tk.t) ? "a repetition" : null, cad ? `cadence ${cad.pattern.replace(/1/g, "/").replace(/0/g, "x")}${cad.type !== "other" ? " (" + cad.type + ")" : ""}` : null,
      tk.src === "guess" ? "stress guessed (not in the dictionary)" : tk.src === "yours" ? "your correction" : null].filter(Boolean).join(" · ");
    return [h("span", { class: cls, title: title || null, style: key != null ? { "--c": PALETTE[keys.indexOf(key) % PALETTE.length] } : null },
      h("span", { class: "sc-m" }, [...tk.m].map(c => c === "1" ? "/" : "x").join(" ")), h("span", { class: "sc-t" }, tk.w)),
    end && end.type !== "other" && !tk.out ? h("span", { class: "sc-cad" }, end.type) : null];
  };
  const paras = [];
  r.tokens.forEach(tk => { if (!paras.length || paras[paras.length - 1].pa !== tk.pa) paras.push({ pa: tk.pa, toks: [] }); paras[paras.length - 1].toks.push(tk); });
  const f = r.figures, one = (k, d = 1) => f[k] == null ? "—" : fmt(f[k], d);
  out.replaceChildren(
    h("div", { class: "controls" },
      books.length > 1 ? h("label", {}, "Book", h("select", { onchange: e => { N.book = e.target.value; N.index = 0; saveSnd(); redraw(); } }, books.map(b => h("option", { value: b, selected: b === N.book }, bookTitle(b))))) : null,
      h("label", {}, S.nar.seg.mode === "chapters" ? "Chapter" : "Slice", h("select", { onchange: e => { N.index = +e.target.value; saveSnd(); redraw(); } }, r.segments.map((l, i) => h("option", { value: i, selected: i === r.index }, l)))),
      h("label", {}, "Colour the runs of", h("select", { onchange: e => { N.colour = e.target.value; saveSnd(); redraw(); } }, SND_KINDS.map(([k, l]) => h("option", { value: k, selected: k === colour }, l)))),
      h("label", { class: "inline", title: "Underline every cadence, not only the cursus forms" },
        h("input", { type: "checkbox", checked: N.every_cadence, onchange: e => { N.every_cadence = e.target.checked; saveSnd(); redraw(); } }), "Every cadence")),
    h("p", { class: "small muted" }, `${r.title}, ${r.label}: ${fmt(r.words)} words ${sndWhere()}${r.cut ? " (the first 3,000 words of it)" : ""}. Stressed ${one("stressed")}%, nPVI ${one("npvi")}, cursus at ${one("cad_cursus")}% of phrase ends, `,
      `${one(colour + "_runs")} ${colour} runs per 1,000 words, ${one("repetition_runs")} repetition runs per 1,000 words. `, textLink(r.book, r.start)),
    h("div", { class: "sc-legend small" }, h("span", { class: "sc-w run", style: { "--c": PALETTE[0] } }, h("span", { class: "sc-t" }, `a ${colour} run`)), " (one colour per shared ", colour === "repetition" ? "word" : "sound", ") ",
      h("span", { class: "sc-w rep" }, h("span", { class: "sc-t" }, "a repetition")), " ", h("span", { class: "sc-w cad cursus" }, h("span", { class: "sc-t" }, "a cursus cadence")), " ",
      N.every_cadence ? [h("span", { class: "sc-w cad" }, h("span", { class: "sc-t" }, "another cadence")), " "] : null, h("span", { class: "sc-w guess" }, h("span", { class: "sc-m" }, "/ x"), h("span", { class: "sc-t" }, "guessed stress")),
      N.scope.kind !== "all" ? [" ", h("span", { class: "sc-p out" }, "outside the chosen text")] : null),
    h("div", { class: "scan" }, paras.map(p => h("p", {}, p.toks.map(tk => [tk.sp ? " " : null, word(tk)])))),
    note("How to read this", "Above each word its syllables: / stressed, x unstressed (one-syllable function words are unstressed). A cadence is the syllables from a phrase's last-but-one stress to its pause: a cursus form is underlined and named after it, and with Every cadence the other cadences are underlined lightly too. The runs of the kind chosen are coloured, one colour for each shared sound or word; repetitions are outlined whatever kind is chosen. Hover a word for what it belongs to."));
}

/* ----- pronunciations: your corrections ----- */
/** Your corrections as saved with the workspace's settings: {word: pronunciation}. */
const sndCorrections = () => ({ ...sndSettings().corrections });
/** Save a new set of corrections (it replaces the saved one) and tell the page; the server checks every one. */
async function sndSaveCorrections(map) {
  S.lib = await api("/api/settings", { sound: { corrections: map } });
  toast("Saved.");
}
/** The stresses of a correction as typed ("1 0 2", "/x/", or phonemes with stress digits) as "1"/"0" a syllable, as the server reads it. */
const sndStressOf = text => /^[012\/xX\s]+$/.test(text) ? [...text.replace(/\s/g, "")].map(c => "0xX".includes(c) ? "0" : "1").join("")
  : text.split(/\s+/).filter(p => /[012]$/.test(p)).map(p => p.endsWith("0") ? "0" : "1").join("");
/** Stress digits as marks ("100" -> "/ x x"). */
const sndMarks = stress => [...stress].map(c => c === "1" ? "/" : "x").join(" ");

/** A form to correct one word: the word, a Look up button (what it is now, and the dictionary's variants to start from), the
    pronunciation to type (phonemes such as B AE1 S K ER0 V IH2 L, or a stress pattern such as 1 0 2 or /x/), Save and Remove.
    `fill(word, text)` puts a word in it from outside (a row clicked); `onSaved()` runs after a change is saved. */
function sndCorrector(onSaved) {
  const word = h("input", { type: "text", placeholder: "Word", "aria-label": "Word to correct", style: { width: "150px" } });
  const said = h("input", { type: "text", placeholder: "1 0 2, /x/, or B AE1 S K ER0 V IH2 L", "aria-label": "Pronunciation", style: { width: "260px" } });
  const info = h("div", { class: "small muted", style: { marginTop: "4px" } });
  const look = async () => {
    if (!word.value.trim()) return;
    let r;
    try { r = await api("/api/sound/lookup", { word: word.value.trim() }); } catch (e) { info.replaceChildren(h("span", { class: "warn" }, e.message)); return; }
    word.value = r.word;
    if (!said.value.trim()) said.value = r.text;
    info.replaceChildren(`Now: ${sndMarks(r.stress)} (${{ yours: "your correction", dict: "from the dictionary", guess: "guessed" }[r.source]}). `,
      r.variants.length ? ["The dictionary has: ", r.variants.map((v, i) => [i ? " · " : "", h("button", { class: "linkbtn", type: "button", title: "Start from this one", onclick: () => { said.value = v; } }, v)])] : "The dictionary doesn't have it.");
  };
  const save = async () => {
    const w = word.value.trim(), t = said.value.trim();
    if (!w || !t) { toast("Give a word and how it is said.", true); return; }
    try { await sndSaveCorrections({ ...sndCorrections(), [w]: t }); } catch (e) { info.replaceChildren(h("span", { class: "warn" }, e.message)); return; }
    onSaved();
  };
  word.onkeydown = e => { if (e.key === "Enter") look(); };
  said.onkeydown = e => { if (e.key === "Enter") save(); };
  const box = h("div", {}, h("div", { class: "row" }, word, h("button", { class: "btn small", type: "button", onclick: look }, "Look up"), said,
    h("button", { class: "btn small primary", type: "button", onclick: save }, "Save")), info);
  box.fill = (w, t) => { word.value = w; said.value = t || ""; info.replaceChildren(); look(); said.focus(); };
  return box;
}

/** The table of your corrections (word, as typed, stresses, how often said in the selected books when `counts` are given), each with
    Remove; a row clicked is handed to `onPick(word, text)`. */
function sndYours(rows, onChange, onPick) {
  return table([{ k: "word", label: "Word" }, { k: "text", label: "Pronunciation", fmt: v => h("code", {}, v) }, { k: "stress", label: "Stress", fmt: v => h("code", {}, sndMarks(v)) },
    ...(rows.length && rows[0].n != null ? [{ k: "n", label: "In the selected books", num: true, fmt: v => fmt(v) }] : []),
    { k: "word", label: "", fmt: w => h("button", { class: "btn small", type: "button", onclick: async e => { e.stopPropagation(); const m = sndCorrections(); delete m[w]; await sndSaveCorrections(m); onChange(); } }, "Remove") }],
  rows, { limit: 100, csvName: "pronunciation corrections", onRow: onPick ? r => onPick(r.word, r.text) : null });
}

/** Pronunciation: the form, the words whose stress is guessed (most frequent first; a row puts the word in the form, starting from its
    guess) and your corrections. */
async function sndWords(body, redraw) {
  const out = h("section", { class: "panel" }, loading("Listing the guessed words…"));
  body.append(out);
  const r = await api("/api/sound/guessed", withBooks({}));
  const form = sndCorrector(redraw);
  out.replaceChildren(
    helpHead("h2", "Pronunciation", "sound", "words"),
    h("p", { class: "small muted" }, `${fmt(r.guessed)} of ${fmt(r.words)} words (${fmt(r.words ? 100 * r.guessed / r.words : 0, 1)}%) in the selected books have a guessed pronunciation; ${fmt(r.corrected)} are said as you corrected them. A guessed word has its first syllable stressed and no sounds, so it counts in rhythm and cadences but not in sound runs.`),
    h("h3", { class: "small muted" }, "Correct a word"), form,
    h("h3", { class: "small muted", style: { marginTop: "14px" } }, `Guessed words (${plural(r.rows.length, "word")})`),
    r.rows.length ? table([{ k: "word", label: "Word" }, { k: "n", label: "Times", num: true, fmt: v => fmt(v) }, { k: "books", label: "Books", num: true, fmt: v => fmt(v) },
      { k: "guess", label: "Guessed stress", fmt: v => h("code", {}, sndMarks(v)) }, { k: "tok", label: "", fmt: (t, row) => textLink(row.book, t) }],
    r.rows, { limit: 100, csvName: "guessed words", onRow: row => form.fill(row.word, [...row.guess].join(" ")) }) : h("p", { class: "muted" }, "No word is guessed."),
    h("h3", { class: "small muted", style: { marginTop: "14px" } }, `Your corrections (${plural(r.yours.length, "word")})`),
    r.yours.length ? sndYours(r.yours, redraw, (w, t) => form.fill(w, t)) : h("p", { class: "muted small" }, "None yet."),
    note("How to correct a word", "Type its stress pattern, one mark a syllable (1 or / stressed, 0 or x unstressed, 2 secondary stress, counted as stressed), or its sounds in ARPAbet as the dictionary writes them, each vowel with its stress (B AE1 S K ER0 V IH2 L); Look up starts you from the dictionary's. With sounds the word also takes part in alliteration, assonance, consonance and rhyme. A correction counts everywhere, as you typed it (one-syllable function words are not made unstressed), and is kept with this workspace (Settings → Sound and rhythm lists them too)."));
}
