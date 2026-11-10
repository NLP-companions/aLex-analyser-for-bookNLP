"use strict";
/* ---------- help ---------- */
/* The help of every page, shown in the side drawer. Each page's texts live in a help-<page>.js file that registers them with `addHelp`;
   the "?" in the top bar opens the help of the page you are on (at its sub-tab, when the help has a section for it), and a "?" beside a
   dense panel or a Statistics variable opens it at that section (`helpButton`). Under every page's own sections come those of the whole
   app ("Everywhere in aLex", help-general.js). tests/test_help.py checks the texts against the options the server knows. */

const HELP = {};                                       // page key -> {title, sections}; "general" is the help of the whole app

/** Register the help of a page: its `title` (as the tab says it) and `sections`, in the order shown. A section has an `id` (a sub-tab's
    own name in the address, or a variable kind, so a "?" or the address can find it), a `title`, `text` (paragraphs), optional `items`
    ([key, name, explanation]: one per option; the key ties it to the option the server knows), `text2` (a paragraph after the items),
    an `example` and `more` (where the maths is). */
function addHelp(page, title, sections) {
  HELP[page] = { title, sections };
}

/** The page you are on, as the help knows pages -> [page key, section]: the tab of the address and its sub-tab; "entity" for a profile,
    at its narrator, group or pooled-page section when it is one of those; on Topics the models list ("home"), a model ("model"), a topic
    ("topic") or a comparison ("map", "pair", "grid"). */
function helpPlace() {
  const [, tab = "entities", raw, third, fourth] = location.hash.split("/"), arg = raw ? decodeURIComponent(raw) : null;
  if (tab === "over") return ["over", arg || "single"];
  if (tab === "topics") return ["topics", !arg ? "home" : third === "compare" ? fourth || "map" : third != null && third !== "" ? "topic" : "model"];
  if (tab !== "entities" || !arg) return [tab, arg];
  const kind = /^(nar|nl):/.test(arg) ? "narrator" : arg === "group" || arg.startsWith("g:") ? "group" : /^(gender|book):/.test(arg) ? "pools" : null;
  return ["entity", kind];
}

/** One section of the help, as shown in the drawer; `key` is what `openHelp` finds it by. */
function helpSection(s, key) {
  return h("section", { class: "svhelp", "data-help": key },
    h("h3", {}, s.title),
    (s.text || []).map(t => h("p", {}, t)),
    s.items ? h("dl", {}, s.items.map(([, name, text]) => [h("dt", {}, name), h("dd", {}, text)])) : null,
    s.text2 ? h("p", {}, s.text2) : null,
    s.example ? h("p", { class: "small" }, h("strong", {}, "Example: "), s.example) : null,
    s.more ? h("p", { class: "small muted" }, "More: " + s.more) : null);
}

/** Open the help of a page in the side drawer: a contents list, the page's sections, then those of the whole app; with `id` (a section of
    the page, if it has one by that id) the drawer scrolls to it, else it starts at the top. A page without help yet says so. */
function openHelp(page, id) {
  const body = $("#drawerBody"), mine = HELP[page], all = HELP.general;
  const go = key => {                                   // scroll the drawer alone (scrollIntoView would move the page behind it too)
    const el = body.querySelector(`[data-help="${key}"]`);
    if (el) body.scrollTop += el.getBoundingClientRect().top - body.getBoundingClientRect().top;
  };
  const toc = (secs, prefix) => secs.map(s => h("button", { type: "button", class: "linkbtn", onclick: () => go(prefix + s.id) }, s.title));
  $("#drawerTitle").replaceChildren(h("h2", { style: { margin: 0 } }, mine ? `${mine.title}: help` : "Help"),
    h("div", { class: "muted small" }, mine ? "What this page shows, and every option on it. The maths is in MEASURES.md." : "How aLex works everywhere."));
  body.replaceChildren(
    h("nav", { class: "svhelp-toc", "aria-label": "Help contents" }, mine ? toc(mine.sections, "") : null,
      all ? [h("span", { class: "small muted" }, "Everywhere:"), toc(all.sections, "general:")] : null),
    mine ? mine.sections.map(s => helpSection(s, s.id)) : h("p", { class: "muted" }, "This page has no help of its own yet."),
    all ? [h("h3", { class: "svhelp-part" }, "Everywhere in aLex"), all.sections.map(s => helpSection(s, "general:" + s.id))] : null);
  $("#drawer").hidden = false;
  body.scrollTop = 0;
  if (id && mine && mine.sections.some(s => s.id === id)) go(id);
}

/** A small "?" button that opens a page's help at a section (`id`); `what` names it for screen readers. */
const helpButton = (page, id, what) => h("button", { class: "btn small", type: "button", title: "Help: " + what, "aria-label": "Help: " + what, onclick: () => openHelp(page, id) }, "?");

/** A panel heading (`tag` h2 or h3) with a small "?" after its text that opens a page's help at a section. The "?" is drawn by the
    style sheet (`.hq::before`), so the heading's text stays its name (for the fold code, the side menu and tests); a click on it,
    being a button, doesn't fold the panel. */
const helpHead = (tag, text, page, id) => h(tag, {}, text, h("button", { class: "hq", type: "button", title: "Help: " + text, "aria-label": "Help: " + text, onclick: () => openHelp(page, id) }));

$("#helpBtn").onclick = () => openHelp(...helpPlace());
