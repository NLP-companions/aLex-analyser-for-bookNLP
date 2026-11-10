"use strict";
/* ---------- the focus (AL-PRIN-12) ---------- */
/* What a page looks at (an entity, a group, a tag, a gender, a book…) is remembered per page by default. Under Settings → Entities the
   user can choose one focus for every page instead ("shared"): a page's SUBJECT chooser then shows the focus, and choosing there, or
   opening a profile, makes the choice the focus of every page. Filters, scopes, references ("Compared with", a second side) and
   Statistics variables never follow. A subject chooser that can't take the focus's kind (a gender where only an entity fits) shows its
   own choice and leaves the focus as it is. The focus is shown once, as a chip in the top bar (#focusChip). Kept per workspace. */

S.focus = loadState("analyser.focus", { mode: "page", target: null });
const focusSeen = {};                                  // subject chooser -> the choice it showed last (JSON), to notice one set by a link

/** Every page's subject: the key its chooser goes by, and where the page keeps its own choice. */
const FOCUS_SUBJECTS = {
  "dialogue/verbs": () => S.dlg.verbTarget, "dialogue/voice": () => S.dlg.voiceTarget, "dialogue/indepth": () => S.dlg.indTarget,
  "over/single": () => S.over.target, "over/aligned": () => S.over.al.a.target, "over/combined": () => S.over.co.target,
  described: () => S.desc.target, compare: () => S.cmp.a,
};
/** At start (main.js, every script loaded): note each page's own subject, so that one set later by a link, not by its chooser, is
    noticed (it then leads and becomes the focus); and draw the top-bar chip. */
function focusStart() {
  for (const [key, own] of Object.entries(FOCUS_SUBJECTS)) { const v = own(); focusSeen[key] = v ? JSON.stringify(v) : null; }
  drawFocus();
}

/** Whether two target specs name the same thing (a book limit, which belongs to the page, aside). */
const sameTarget = (a, b) => { const bare = ({ books, ...t } = {}) => JSON.stringify(t); return !!a && !!b && bare(a) === bare(b); };

/** Whether one focus is shared by every page (else each page keeps its own). */
const focusShared = () => S.focus.mode === "shared";

/** The shared focus, or null: a target spec of a kind the pickers know. */
const focusTarget = () => focusShared() && isObject(S.focus.target) && typeof S.focus.target.kind === "string" ? S.focus.target : null;

/** Whether a target `spec` can be chosen in a `picker` with options `opts` (the same kinds it offers; never "everyone else"). */
function focusFits(spec, opts = {}) {
  if (!spec) return false;
  const k = spec.kind;
  return k === "unit" || (k === "tag" && !opts.unitOnly) || ((k === "group" || k === "type") && !!opts.group && !opts.unitOnly)
    || (k === "narration" && !!opts.narration) || (k === "book" && !!opts.book) || (k === "gender" && !!opts.gender);
}

/** Save the focus mode and target, and redraw the top-bar chip. */
function saveFocus() {
  saveState("analyser.focus", S.focus);
  drawFocus();
}

/** Make `spec` the shared focus (in shared mode only; a book limit it carries is the page's own and is dropped). */
function setFocus(spec) {
  if (!focusShared() || !spec || spec.kind === "others") return;
  const { books, ...target } = spec;
  if (JSON.stringify(target) === JSON.stringify(S.focus.target)) return;
  S.focus.target = target;
  saveFocus();
}

/** The choice a page's subject chooser `key` should use, given the page's own `own` and its picker options: in shared mode the focus
    when it fits, unless the page's own choice was set since the chooser last showed (by a link from another page, such as "Described
    by whom →"), in which case that choice becomes the focus. Each page keeps the result as its own (so it stays when the mode changes). */
function followFocus(key, own, opts = {}) {
  if (!focusShared()) return own;
  const mine = own ? JSON.stringify(own) : null, focus = focusTarget();
  let out = own;
  if (mine && mine !== focusSeen[key]) setFocus(own);                                          // set by a link since: it leads
  else if (focus && focusFits(focus, opts) && !sameTarget(own, focus)) out = { ...focus };      // (the same, with a book limit: kept)
  focusSeen[key] = out ? JSON.stringify(out) : null;
  return out;
}

/** A page's subject chooser: `picker` showing `value` (already passed through `followFocus` under `key`), whose choice also becomes
    the shared focus; in shared mode a muted "follows the focus" says so. */
function subjectPicker(key, value, onChange, opts = {}) {
  const pick = picker(value, v => { focusSeen[key] = v ? JSON.stringify(v) : null; setFocus(v); onChange(v); }, opts);
  return focusShared() ? h("div", { class: "subject" }, pick,
    h("span", { class: "small muted", title: "One focus for every page (Settings → Entities): choosing here changes it everywhere" }, "follows the focus")) : pick;
}

/** The top-bar chip naming the shared focus, with × to clear it; hidden in "each page its own" mode or without a focus. */
function drawFocus() {
  const chip = $("#focusChip"), t = focusTarget();
  chip.hidden = !t;
  if (!t) { chip.replaceChildren(); return; }
  chip.replaceChildren(h("span", { class: "muted" }, "Focus: "), h("b", {}, t.name || t.tag || t.kind),
    h("button", { type: "button", "aria-label": "Clear the focus", title: "Clear the focus (each page then keeps what it shows now)",
      onclick: () => { S.focus.target = null; saveFocus(); } }, "×"));
  chip.title = "Every page that looks at one entity, group, tag, gender or book opens on this (Settings → Entities)";
}
