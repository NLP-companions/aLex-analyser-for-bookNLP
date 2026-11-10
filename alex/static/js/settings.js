"use strict";
/* ---------- Settings ---------- */
/* The Settings page (#/settings), laid out like the companion editor's: a contents list on the left, sections with an
   UPPERCASE label on the right, one `.fields` row per setting (label, control, a muted hint). Sections: Appearance (the
   theme, how the Statistics page lists its variables), Entities (plural groups, minimum mentions, how to count them), Words (how to count a word's
   minimum frequency), Sound and rhythm (the window and boundary of runs, what alliteration compares, what counts as a repetition, your
   pronunciation corrections, with the form of sound.js) and
   Folders (where to find books: the workspace's own books folder and data folder, each with a button that shows it in the file
   browser, and the other folders it reads). Everything here
   belongs to the workspace in use, except the theme, which is the same in all of them. */

/** The sections in order: [id, label]. The contents list and the section ids come from here. */
const SETTINGS_SECTIONS = [["appearance", "Appearance"], ["entities", "Entities"], ["words", "Words"], ["sound", "Sound and rhythm"], ["folders", "Folders"]];

/** One row of a section: a muted label, the control, and (if given) a hint line under the control. */
function settingRow(label, control, hint) {
  return [h("div", { class: "fl" }, label), h("div", {}, control, hint ? h("div", { class: "hint" }, hint) : null)];
}

/** The Settings page. Choosing something saves it at once and redraws the page. `section` (from #/settings/<section>,
    as the "Based on" lines link) scrolls to that section once drawn. */
async function renderSettings(main, section) {
  await loadLib();
  const L = S.lib, st = L.settings;
  const saveSettings = async patch => { S.lib = await api("/api/settings", patch); S.units = null; toast("Saved."); renderSettings(main); };
  /** Save a new list of source folders, drop what was cached from the old one, and redraw. */
  const saveSources = async sources => { S.lib = await api("/api/settings", { sources }); S.units = null; renderSettings(main); };

  // ----- Appearance -----
  const appearance = h("div", { class: "fields" }, settingRow("Theme",
    seg(Object.entries(THEME_LABEL), loadJSON("analyser.theme", "auto"), mode => { setTheme(mode); render(); }),
    "Auto follows your system. The same in every workspace."),
    settingRow("Statistics variables", seg([["rows", "One row each"], ["chips", "Chips"]], S.stats.editor, v => { S.stats.editor = v; saveStats(); render(); }),
      "How the Statistics page lists its variables: every variable's fields in a row of its own, or a compact chip that opens its fields when clicked."),
    settingRow("R export: example script", seg([["on", "Include it"], ["off", "Leave it out"]], S.stats.example ? "on" : "off", v => { S.stats.example = v === "on"; saveStats(); render(); }),
      "Whether the Statistics page's “Download for R” zip holds analysis_example.R, a few commented lines of analysis on the first variables, besides the data files and load.R."));

  // ----- Entities -----
  const minimums = h("div", { class: "mins" }, TYPES.map(t => h("label", { class: "row", style: { gap: "6px" } }, typeChip(t),
    h("input", { type: "number", min: 1, value: st.min[t], "aria-label": "Minimum for " + TYPE_NAMES[t], onchange: e => saveSettings({ min: { [t]: Math.max(1, +e.target.value || 1) } }) }))));
  const entities = [
    h("div", { class: "fields" },
      settingRow("Plural groups", seg([["own", "Own mentions only"], ["all", "Include plural-group mentions"]], st.plural ? "all" : "own", v => saveSettings({ plural_default: v === "all" })),
        "Whether an entity's figures include the mentions of the plural groups it belongs to (“Holmes and Watson”, “they”). The same switch is “Plural groups” in the [...] menu; it applies to every page."),
      settingRow("Minimum mentions", minimums, "Entities with fewer mentions are left out of lists, profiles, comparisons and networks. BookNLP's .book uses 2 for people."),
      settingRow("Count mentions", seg([["per_book", "In each book separately"], ["combined", "Across the selected books combined"]], st.count_mode, v => saveSettings({ count_mode: v })),
        "Whether the minimum is checked in each book, or in the books you have selected taken together."),
      settingRow("Focus", seg([["page", "Each page its own"], ["shared", "One focus for every page"]], S.focus.mode,
        v => { S.focus.mode = v; if (v === "shared") focusStart(); saveFocus(); render(); }),
        "Each page its own: every page remembers what it looks at. One focus: choosing an entity, group, tag, gender or book as a page's subject, or opening its page, makes it the subject of every page (shown at the top right; filters, “Compared with” and Statistics keep their own). Kept in this browser, for this workspace.")),
    note("What these settings mean",
      "A plural group is an entity whose mentions mean several entities together: “Holmes and Watson”, and the “they” and “we” BookNLP linked to it. It is always an entity of its own. Declare plural groups on an entity's page, or accept the suggestions on the Entities page.",
      "Own mentions only: each entity's figures come from its own mentions and quotes. Include plural-group mentions: a plural group's mentions, what it does, who it appears with, its quotes and the quotes addressed to it count for each of its members too; a member named inside a plural mention (“Holmes and Watson walked”) counts once, through its own mention.",
      "In each book separately: an entity counts in a book only if it reaches the minimum in that book. For a linked entity, books where it falls short are left out of its figures.",
      "Across the selected books combined: a linked entity counts if its mentions in all the selected books together reach the minimum, and then every book it appears in is included. Unlinked entities are the same either way.")];

  // ----- Words -----
  const words = [
    h("div", { class: "fields" },
      settingRow("Count word frequency", seg([["combined", "Across the selected books combined"], ["per_book", "In each book separately"]], st.freq_mode, v => saveSettings({ freq_mode: v })),
        "Whether a tool's minimum frequency is checked for a word in the selected books taken together, or in each book. The number itself is set in each tool.")),
    note("What this setting means",
      "Across the selected books combined: a word counts if it occurs at least that often in all the selected books together, so a word that is rare in every book can still be listed or tested.",
      "In each book separately: a book counts for a word only if the word reaches the minimum in that book. The Corpus word list, n-grams and collocates list a word that reaches it in at least one book; By book tests it across the books that reach it (at least two); Over the book, with all the books combined, tests it in each of them and combines the results. “Minimum range” then counts the books that reach the minimum.",
      "Not affected: the comparisons of distinctive words, which set a target's words against a reference, and the views of a single book.")];

  // ----- Sound and rhythm -----
  const snd = sndSettings();
  const windowInput = sndWindowInput(snd.window, n => saveSettings({ sound: { window: n } }), "90px");
  const sound = [
    L.sound ? null : h("p", { class: "warn small" }, L.sound_missing),
    h("div", { class: "fields" },
      settingRow("Window", windowInput, "How near words must be to make a run of alliteration, assonance, consonance or rhyme: within this many content words of the one before. Any whole number, 1 or more; the default is 3."),
      settingRow("Runs stop at", seg(SND_BOUNDARIES, snd.boundary, v => saveSettings({ sound: { boundary: v } })),
        "A run never goes past this, nor over text a sample leaves out (the narration between a character's quotes)."),
      settingRow("Alliteration by", seg(SND_ALLITERATION, snd.alliteration, v => saveSettings({ sound: { alliteration: v } })),
        "Stressed syllable: the first consonant of the stressed syllable (assistance alliterates on S, from -SIS-). First sound: the word's first consonant as said (cat and kill, knight and night). First letter: as spelled (cat and city, but not knight and night); it also works for words whose pronunciation is guessed."),
      settingRow("Repetition is", seg(SND_REPETITION, snd.repetition, v => saveSettings({ sound: { repetition: v } })),
        "The same word again within the window, counted as runs of its own. Same lemma: forms of one word count together (walk, walked). Same word form: only the identical form. Same lemma, all words: function words too (the … the, of … of). A repeated word never counts again in a sound run."),
      settingRow("Pronunciations", h("div", {}, h("div", { class: "small", style: { marginBottom: "6px" } }, `${plural(Object.keys(snd.corrections).length, "word")} corrected. `,
          h("a", { href: "#/sound/words" }, "The guessed words"), " are listed under Sound and rhythm → Pronunciation."),
        L.sound ? sndCorrector(() => renderSettings(main)) : null,
        Object.keys(snd.corrections).length ? sndYours(Object.entries(snd.corrections).map(([word, text]) => ({ word, text, stress: sndStressOf(text) })), () => renderSettings(main)) : null),
        "How words are said that the dictionary lacks or gets wrong: a stress pattern (1 0 2, /x/) or sounds (B AE1 S K ER0 V IH2 L). Kept with this workspace.")),
    note("What these settings mean",
      "A run is a chain of nearby content words (nouns, verbs, adjectives, adverbs, names) that share a sound: the first consonant (alliteration, as chosen above), the stressed vowel (assonance), the final consonants (consonance) or the stressed vowel and all after it (rhyme); or the same word again (repetition). Each word must be within the window of the one before it.",
      "A wider window, or a boundary further out, finds more and longer runs, so compare figures only under the same settings. They apply to the Sound and rhythm tab, the Statistics page and Over the book alike.")];

  // ----- Folders -----
  const newSrc = h("input", { type: "text", placeholder: "/path/to/folder/with/books", "aria-label": "Folder with books", style: { flex: "1 1 280px" } });
  const addSrc = () => { if (newSrc.value.trim()) saveSources([...L.sources, newSrc.value.trim()]); };
  newSrc.onkeydown = e => { if (e.key === "Enter") addSrc(); };
  /** One folder of the workspace in the list: what it is, its path, and its buttons. */
  const folderRow = (label, path, ...buttons) => h("li", {}, label ? h("span", { class: "srcl" }, label) : null, h("code", { title: path }, path), ...buttons);
  const folders = [
    h("ul", { class: "srcs" },
      folderRow("Books folder", L.books_dir, openFolderButton({ folder: "books" })),
      folderRow("Data folder", L.data_dir, openFolderButton({ folder: "data" }))),
    h("p", { class: "hint", style: { marginTop: 0 } }, "Put BookNLP output in the books folder (Open shows it in Finder or your file browser); aLex finds it when you come back to this window. The data folder holds aLex's own files for this workspace: your links, corrections, topic models and the cache."),
    h("div", { class: "srch" }, "Other folders with books"),
    L.sources.length ? h("ul", { class: "srcs" }, L.sources.map((s, i) => folderRow(null, s, openFolderButton({ folder: "source", index: i }),
      h("button", { class: "btn small", onclick: () => saveSources(L.sources.filter((_, j) => j !== i)) }, "Remove")))) : h("p", { class: "empty" }, "None. Add a folder where BookNLP output already is, to read it where it lies."),
    L.problems.length ? h("div", { class: "warn small", style: { marginBottom: "8px" } }, L.problems.map(p => h("div", {}, p))) : null,
    h("div", { class: "row" }, newSrc, h("button", { class: "btn", onclick: addSrc }, "Add folder")),
    note("What counts as a folder of books", "The books folder, or any other folder, can hold BookNLP files directly (houn.tokens, houn.entities and so on), or a folder of exports with one subfolder per export (as the companion editor writes them). Each book needs at least .tokens and .entities; .quotes, .supersense and .book are used when present.")];

  const parts = { appearance, entities, words, sound, folders };
  main.replaceChildren(h("div", { class: "page with-toc" },
    h("nav", { class: "stoc", "aria-label": "Sections on this page" }, SETTINGS_SECTIONS.map(([id, label]) => h("a", { href: "#settings-" + id, "data-target": "settings-" + id }, label))),
    h("div", {},
      h("h1", {}, "Settings"),
      h("p", { class: "lede" }, "For the workspace in use. Choices save as you make them."),
      SETTINGS_SECTIONS.map(([id, label]) => h("section", { class: "lsec", id: "settings-" + id }, h("h2", {}, label), parts[id])))));
  const target = section && document.getElementById("settings-" + section);
  if (target) target.scrollIntoView();
  spySettings();
}

/** Mark, in the contents list, the last section whose top has scrolled under the top bar. */
function spySettings() {
  const links = [...document.querySelectorAll(".stoc a[data-target]")];
  let cur = links[0];
  for (const a of links) { const el = document.getElementById(a.dataset.target); if (el && el.getBoundingClientRect().top <= 110) cur = a; }
  links.forEach(a => a.classList.toggle("on", a === cur));
}
window.addEventListener("scroll", spySettings, { passive: true });

// a click on a contents entry scrolls to its section (the address bar keeps saying #/settings)
document.addEventListener("click", e => {
  const a = e.target.closest(".stoc a[data-target]");
  if (!a) return;
  e.preventDefault();
  document.getElementById(a.dataset.target).scrollIntoView({ behavior: "smooth" });
});
