"use strict";
/* ---------- the [...] menu ---------- */
/* The top bar's menu (markup in index.html): pages and settings that don't need a tab of their own. A row with a submenu
   (`.sub`: a trigger button and a `.menu` beside it) opens that submenu to the left, on hover or on click. The menu closes on
   choosing an entry, on a click outside it, and on Escape. Other scripts fill the submenus and handle their entries.
   The book button beside it works the same way on a panel of its own (the book picker); only one of the two is open at a time. */

const moreMenu = $("#moreMenu");

/** Close every submenu; `except` (a `.sub`) is left as it is. */
function closeSubs(except) {
  moreMenu.querySelectorAll(".sub").forEach(sub => { if (sub !== except) setSub(sub, false); });
}

/** Open or close one submenu and keep its trigger's aria-expanded in step. Opening one that is already open does nothing;
    otherwise the submenu's `submenuopen` event fires, for whoever fills it (the book picker is built then). */
function setSub(sub, open) {
  const menu = sub.querySelector(".menu");
  if (menu.hidden === !open) return;
  menu.hidden = !open;
  if (open) sub.dispatchEvent(new Event("submenuopen"));
  sub.querySelector("[aria-haspopup]").setAttribute("aria-expanded", String(open));
}

/** Open or close the menu; closing it closes its submenus too. */
function setMoreMenu(open) {
  moreMenu.hidden = !open;
  if (open) setBooksPanel(false);
  $("#moreBtn").setAttribute("aria-expanded", String(open));
  if (!open) closeSubs();
}

$("#moreBtn").onclick = () => setMoreMenu(moreMenu.hidden);

const booksPanel = $("#selPop");

/** Open or close the book button's panel. Opening it closes the menu and fires `submenuopen` on the panel, for core.js to build the picker. */
function setBooksPanel(open) {
  if (booksPanel.hidden === !open) return;
  booksPanel.hidden = !open;
  $("#booksBtn").setAttribute("aria-expanded", String(open));
  if (open) { setMoreMenu(false); booksPanel.dispatchEvent(new Event("submenuopen")); }
}

$("#booksBtn").onclick = () => setBooksPanel(booksPanel.hidden);

// Hovering a submenu row opens its submenu; hovering any other row closes the open one. A submenu stays open when the
// pointer leaves it (so a slanting move towards it, or a half-ticked list, isn't lost) until another row is touched.
moreMenu.addEventListener("mouseover", e => {
  const row = e.target.closest(".menu > .mi, .menu > .sub");
  if (!row || row.closest(".menu") !== moreMenu) return;       // only rows of the top level count
  const sub = row.classList.contains("sub") ? row : null;
  closeSubs(sub);
  if (sub) setSub(sub, true);
});

// A click on a submenu row opens its submenu (touch, keyboard; it never closes one, as pointing at the row has opened it already);
// a click on any other entry closes the menu.
moreMenu.addEventListener("click", e => {
  const trigger = e.target.closest("[aria-haspopup]");
  if (trigger && trigger.closest(".menu") === moreMenu) {
    const sub = trigger.parentElement;
    closeSubs(sub);
    setSub(sub, true);
  } else if (e.target.closest("[role^=menuitem]")) setMoreMenu(false);
});

document.addEventListener("mousedown", e => {
  if (!moreMenu.hidden && !e.target.closest("#moreWrap")) setMoreMenu(false);
  if (!booksPanel.hidden && !e.target.closest("#booksWrap")) setBooksPanel(false);
});
document.addEventListener("keydown", e => {
  if (e.key === "Escape" && (!moreMenu.hidden || !booksPanel.hidden)) { setMoreMenu(false); setBooksPanel(false); e.stopPropagation(); }
}, true);
