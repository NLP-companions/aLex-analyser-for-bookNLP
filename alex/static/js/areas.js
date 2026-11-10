"use strict";
/* ---------- areas ---------- */
/* The top bar holds eight areas, each grouping the pages that answer one kind of question (docs/DESIGN.md §8.3, AL-AREA-01..03).
   Every page keeps its own address; the area is worked out from the address, so old links still work. An area with more than one
   page shows them as a row of tabs (#areaNav, above #main), drawn by the router on every page change; a click on an area in the
   top bar opens the page last used in it (remembered per workspace). Pages of the [...] menu belong to no area. */

/** The areas in top-bar order: id, label, and its pages as [address, label]. The first page is where an area starts. */
const AREAS = [
  { id: "books", label: "Library", pages: [["#/books", "Library"]] },
  { id: "entities", label: "Entities", pages: [["#/entities", "Entities"], ["#/compare", "Compare"], ["#/described", "Described as"], ["#/network", "Network"]] },
  { id: "dialogue", label: "Dialogue", pages: [["#/dialogue/speakers", "Who speaks"], ["#/dialogue/verbs", "Speech verbs"], ["#/dialogue/voice", "How they speak"],
    ["#/dialogue/conversations", "Conversations"], ["#/dialogue/quotes", "Quotes"], ["#/dialogue/indepth", "In-Depth Who Speaks"]] },
  { id: "words", label: "Words", pages: [["#/corpus/kwic", "Concordance"], ["#/corpus/wordlist", "Word list"], ["#/corpus/ngrams", "N-grams"],
    ["#/corpus/collocates", "Collocates"], ["#/corpus/keywords", "Keywords"], ["#/topics", "Topics"]] },
  { id: "style", label: "Style", pages: [["#/narrative/style", "Style"], ["#/narrative/stylometry", "Stylometry"], ["#/sound", "Sound and rhythm"]] },
  { id: "time", label: "Over time", pages: [["#/over", "Over the book"], ["#/narrative/arcs", "Arcs"], ["#/narrative/sentiment", "Sentiment"], ["#/narrative/lexicons", "Lexicons"]] },
  { id: "stats", label: "Statistics", pages: [["#/stats", "Statistics"]] },
  { id: "read", label: "Read", pages: [["#/read", "Read"]] },
];
S.areaLast = loadState("analyser.areas", {});     // area id -> the address of the page last used in it

/** The page the current address shows, as the address of one of AREAS' pages -> { area, page }; both null for a page of the
    [...] menu. A page with sub-tabs of its own (Dialogue, Corpus, Arcs…) that has none in the address is the one it remembers. */
function areaPlace(hash = location.hash) {
  const [, tab = "entities", sub] = hash.split("/");
  const own = { dialogue: S.dlg.sub, corpus: S.corp.sub, narrative: S.nar.sub };
  const key = tab === "chapters" ? "#/read" : tab in own ? `#/${tab}/${sub || own[tab]}` : "#/" + tab;
  for (const a of AREAS) for (const [page] of a.pages) if (page === key) return { area: a, page };
  return { area: null, page: null };
}

/** Mark the open area in the top bar, point each area at the page last used in it, and draw the open area's page tabs
    (none for an area of one page, or a page of the [...] menu). Called by the router before each page is drawn. */
function drawAreas() {
  const { area, page } = areaPlace();
  if (area && S.areaLast[area.id] !== page) { S.areaLast[area.id] = page; saveState("analyser.areas", S.areaLast); }
  document.querySelectorAll("#tabs a[data-area]").forEach(a => {
    const ar = AREAS.find(x => x.id === a.dataset.area), last = S.areaLast[ar.id];
    a.href = ar.pages.some(([p]) => p === last) ? last : ar.pages[0][0];
    a.classList.toggle("on", ar === area);
    if (ar === area) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  const nav = $("#areaNav");
  nav.hidden = !area || area.pages.length < 2;
  nav.replaceChildren(...(nav.hidden ? [] : area.pages.map(([p, label]) =>
    h("a", { href: p, class: p === page ? "on" : null, "aria-current": p === page ? "page" : null }, label))));
}
