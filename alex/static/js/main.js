"use strict";
/* ---------- router ---------- */
/* The address bar decides the page: #/<tab>/<sub>/<more…>. This is the last script to load, so every renderX exists. */

/** Show the page for the current address (below). */
async function renderPage() {
  const [, tab = "entities", arg] = location.hash.split("/");
  drawAreas();                                                          // the open area and its page tabs (areas.js)
  document.querySelectorAll("#moreMenu a[data-tab]").forEach(a => a.classList.toggle("on", a.dataset.tab === tab));
  $("#moreBtn").classList.toggle("on", !!$("#moreMenu a.on"));          // a page that lives in the [...] menu is open
  $("#drawer").hidden = true;
  const main = $("#main");
  try {
    if (!S.lib) await loadLib();
    if (!S.lib.books.length && tab !== "books" && tab !== "settings") { location.hash = "#/books"; return; }
    if (tab === "books") await renderBooks(main);
    else if (tab === "settings") await renderSettings(main, arg);
    else if (tab === "compare") await renderCompare(main);
    else if (tab === "over") await renderOverbook(main, arg);
    else if (tab === "described") await renderDescribed(main);
    else if (tab === "stats") await renderStats(main);
    else if (tab === "network") await renderNetwork(main);
    else if (tab === "links") await renderLinks(main);
    else if (tab === "narrators") await renderNarrators(main);
    else if (tab === "dialogue") await renderDialogue(main, arg);
    else if (tab === "corpus") await renderCorpus(main, arg);
    else if (tab === "narrative") await renderNarrative(main, arg);
    else if (tab === "sound") await renderSound(main, arg);
    else if (tab === "topics") await renderTopics(main, arg, ...location.hash.split("/").slice(3));
    else if (tab === "read") await renderRead(main, arg, location.hash.split("/")[3]);
    else if (tab === "chapters") await renderRead(main, arg, location.hash.split("/")[3], true);
    else await renderEntities(main, arg ? decodeURIComponent(arg) : null);
  } catch (e) {
    if (!e.handled) console.error(e);
    main.replaceChildren(h("div", { class: "panel warn" }, "Something went wrong: " + e.message));
  }
}

/** Re-draw the current page. Renders never overlap: if the address changes while one is still loading, the newest
    request waits for it and then runs, so a slow older page can't overwrite a newer one. */
const render = (() => {
  let running = false, again = false;
  return async function render() {
    if (running) { again = true; return; }
    running = true;
    try {
      do { again = false; await renderPage(); } while (again);
    } finally { running = false; }
  };
})();
window.addEventListener("hashchange", render);
focusStart();                                                           // note each page's own subject; the focus chip (focus.js)
render();
