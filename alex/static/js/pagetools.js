"use strict";
/* ---------- Page tools: collapsible sections and a side menu on long pages ---------- */
// Two kinds of section can be collapsed, and the choice is remembered per page and heading:
//  - a panel whose first child is a heading (or that names itself with data-toc), and
//  - a sub-heading (h3) with the content that follows it, up to the next heading.
// Pages with three or more top-level sections get a sticky menu at the right; a section with a `data-group` is listed under that group's label.
// The menu (and the topic page's own one) can be folded to a thin rail, remembered per page; the page then also drops its width cap.
const CX_KEY = "analyser.collapsed";
const cx = { saved: (() => { const v = loadJSON(CX_KEY, {}); return isObject(v) ? v : {}; })() };
/** Remember which sections are folded. */
const cxSave = () => saveState(CX_KEY, cx.saved);
/** The page a fold belongs to: the first part of the address. */
const cxPage = () => location.hash.split("/")[1] || "entities";
/** A panel's heading (or the row marked to fold it by). */
const cxHead = p => p.querySelector(":scope > h2, :scope > h3") || p.querySelector(":scope > [data-cx-head]");
/** The name of a panel: its `data-toc`, else its heading's text. */
const cxLabel = p => (p.dataset.toc || (cxHead(p) ? cxHead(p).textContent : "")).trim();
/** The key a fold is remembered under: page and section name. */
const cxKey = label => cxPage() + "|" + label;
/** Whether a foldable is a sub-heading block (rather than a panel). */
const cxIsBlock = el => el.classList.contains("cx-block");
/** The elements a sub-heading folds: those after it, up to the next heading. */
const cxNodes = hd => { const out = []; for (let n = hd.nextElementSibling; n && !/^H[123]$/.test(n.tagName); n = n.nextElementSibling) out.push(n); return out; };
/** The name of any foldable: a block's heading text or a panel's name. */
const cxLabelOf = el => (cxIsBlock(el) ? el.textContent : cxLabel(el)).trim();
/** Whether a section is folded. */
const cxCollapsed = el => el.classList.contains("collapsed");

const TOC_KEY = "analyser.tocClosed";
const tocs = { closed: (() => { const v = loadJSON(TOC_KEY, {}); return isObject(v) ? v : {}; })() };   // page -> 1 when its menu is folded

/** The button in a side menu's title row that folds the menu to a rail and opens it again. Its arrow is drawn by CSS. */
function tocButton() {
  return h("button", { class: "toc-fold", type: "button", "aria-expanded": "true", title: "Hide the menu", "aria-label": "Hide or show the menu" });
}

/** Show the side menu folded or open, as the user left it on this page. Only a page that has a menu loses its width cap. */
function tocApply() {
  const main = $("#main");
  const closed = !!tocs.closed[cxPage()] && !!main.querySelector(".page-toc, .tp-toc");
  main.classList.toggle("toc-closed", closed);
  main.querySelectorAll(".toc-fold").forEach(b => { b.setAttribute("aria-expanded", String(!closed)); b.title = closed ? "Show the menu" : "Hide the menu"; });
}

/** Fold or open this page's side menu and remember the choice. */
function tocToggle() {
  if (tocs.closed[cxPage()]) delete tocs.closed[cxPage()]; else tocs.closed[cxPage()] = 1;
  saveState(TOC_KEY, tocs.closed);
  tocApply();
}

/** Collapse or expand a section (a panel or a heading block) and, unless told not to, remember the choice. An expanded section
    gets an "expand" event, so a panel can wait to load its content until it is first opened. */
function cxSet(el, collapsed, remember = true) {
  el.classList.toggle("collapsed", collapsed);
  if (!collapsed) el.dispatchEvent(new Event("expand"));
  const hd = cxIsBlock(el) ? el : cxHead(el);
  const b = hd && hd.querySelector(":scope > .cx");
  if (b) { b.setAttribute("aria-expanded", String(!collapsed)); b.title = collapsed ? "Expand" : "Collapse"; }
  if (cxIsBlock(el)) cxNodes(el).forEach(n => n.classList.toggle("cx-hidden", collapsed));
  if (remember) { if (collapsed) cx.saved[cxKey(cxLabelOf(el))] = 1; else delete cx.saved[cxKey(cxLabelOf(el))]; }
  const a = el.id && document.querySelector(`.page-toc a[data-target="${el.id}"]`);
  if (a) a.classList.toggle("collapsed", collapsed);
}

/** The little arrow that folds a section. */
function cxButton() {
  return h("button", { class: "cx", type: "button", "aria-expanded": "true", title: "Collapse", "aria-label": "Collapse or expand this section" });
}

/** Add the collapse arrows and, for pages with three or more top-level sections, the side menu. Safe to run repeatedly:
    it re-applies remembered choices to sections that were drawn later and rebuilds the menu when the sections change. */
function enhancePage() {
  const main = $("#main");
  const host = main.querySelector(":scope > .ent") || main;
  // panels
  const panels = [...main.querySelectorAll("section.panel")].filter(p => !p.parentElement.closest("section.panel") && cxLabel(p));
  panels.forEach((p, i) => {
    const head = cxHead(p), label = cxLabel(p);
    p.classList.add("cx-panel");
    if (!p.id) p.id = "px-" + i;
    if (head) { head.classList.add("cx-head"); if (!head.querySelector(":scope > .cx")) head.prepend(cxButton()); }
    if (p.dataset.cxLabel !== label) { p.dataset.cxLabel = label; cxSet(p, !!cx.saved[cxKey(label)], false); }
  });
  // sub-headings with their content
  let n = 0;
  [...main.querySelectorAll("h3")].forEach(hd => {
    const direct = hd.parentElement.matches("section.panel") && cxHead(hd.parentElement) === hd;
    if (direct || hd.parentElement.closest(".cols2, .cols3, .controls, .row, .books-fly, .drawer, .tp-toc, .page-toc, .read-side, .ev, details")) return;
    if (!hd.textContent.trim() || !hd.nextElementSibling || /^H[123]$/.test(hd.nextElementSibling.tagName)) return;
    hd.classList.add("cx-head", "cx-block");
    if (!hd.id) hd.id = "hx-" + (n++);
    if (!hd.querySelector(":scope > .cx")) hd.prepend(cxButton());
    const label = hd.textContent.trim();
    if (hd.dataset.cxLabel !== label) { hd.dataset.cxLabel = label; cxSet(hd, !!cx.saved[cxKey(label)], false); }
    else if (cxCollapsed(hd)) cxNodes(hd).forEach(x => x.classList.add("cx-hidden"));     // content added after it was collapsed
  });
  // the menu lists top-level sections in reading order: labelled panels, and sub-headings that sit outside any of them
  const loose = [...main.querySelectorAll("h3.cx-block")].filter(hd => !hd.closest(".cx-panel"));
  const items = [...panels, ...loose].sort((x, y) => (x.compareDocumentPosition(y) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1))
    .map(el => ({ el, id: el.id, label: cxLabelOf(el), collapsed: cxCollapsed(el), group: el.dataset.group || "" }));
  const wanted = items.length >= 3 && !main.querySelector(".tp-layout, .read, .net");
  let toc = main.querySelector(".page-toc");
  if (!wanted) {
    if (toc) toc.remove();
    main.classList.remove("has-toc"); host.classList.remove("has-toc");
    return;
  }
  const sig = items.map(x => x.id + "\u0001" + x.label + "\u0001" + x.group).join("\u0002");
  if (toc && toc.dataset.sig === sig && toc.parentElement === host) return;
  if (toc) toc.remove();
  main.classList.remove("has-toc");
  toc = h("nav", { class: "page-toc", "data-sig": sig, "aria-label": "On this page" },
    h("div", { class: "page-toc-title" }, h("span", null, "On this page"), tocButton()),
    items.map((x, i) => [x.group && x.group !== (items[i - 1] || {}).group ? h("div", { class: "page-toc-group" }, x.group) : null,   // a section's group (data-group), once
      h("a", { href: "#" + x.id, "data-target": x.id, class: x.collapsed ? "collapsed" : "", title: x.label }, x.label)]),
    h("div", { class: "page-toc-tools" },
      h("button", { type: "button", class: "linkbtn", onclick: () => { items.forEach(x => cxSet(x.el, true)); cxSave(); } }, "Collapse all"),
      h("button", { type: "button", class: "linkbtn", onclick: () => { items.forEach(x => cxSet(x.el, false)); cxSave(); } }, "Expand all")));
  host.classList.add("has-toc");
  host.append(toc);                                   // after the content: the menu is always at the right (AL-FOLD-01)
  cxSpy();
}

/** Highlight, in the side menu, the last section whose top has scrolled under the header. */
function cxSpy() {
  const links = [...document.querySelectorAll(".page-toc a[data-target]")];
  if (!links.length) return;
  let cur = links[0];
  for (const a of links) { const el = document.getElementById(a.dataset.target); if (el && el.getBoundingClientRect().top <= 110) cur = a; }
  links.forEach(a => a.classList.toggle("on", a === cur));
}

document.addEventListener("click", e => {
  if (e.target.closest(".toc-fold")) { tocToggle(); return; }
  const toc = e.target.closest(".page-toc a[data-target]");
  if (toc) {
    e.preventDefault();
    const el = document.getElementById(toc.dataset.target);
    if (el) { if (cxCollapsed(el)) { cxSet(el, false); cxSave(); } el.scrollIntoView({ behavior: "smooth" }); }
    return;
  }
  const btn = e.target.closest(".cx");
  const head = e.target.closest("h2.cx-head, h3.cx-head");
  if (!btn && !(head && !e.target.closest("a, button, input, select, textarea, label, summary"))) return;
  const hd = btn ? btn.closest(".cx-head") : head;
  const el = hd && (cxIsBlock(hd) ? hd : hd.closest("section.panel"));
  if (el) { cxSet(el, !cxCollapsed(el)); cxSave(); }
});
window.addEventListener("scroll", cxSpy, { passive: true });
{
  const mainEl = $("#main");
  let queued = false;
  const obs = new MutationObserver(() => {
    if (queued) return;
    queued = true;
    setTimeout(() => {
      queued = false;
      obs.disconnect();
      try { enhancePage(); tocApply(); } catch (e) { console.error(e); }
      obs.observe(mainEl, { childList: true, subtree: true });
    }, 30);
  });
  obs.observe(mainEl, { childList: true, subtree: true });
}
