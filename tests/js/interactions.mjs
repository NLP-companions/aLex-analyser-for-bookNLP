// Drive the interface the way a person would (clicks, typing, selects) and check what happens.
// usage: node interactions.mjs http://127.0.0.1:8766
import { readFileSync } from "node:fs";
import { api, openPage, sleep, waitFor } from "./harness.mjs";
const css = readFileSync(new URL("../../alex/static/app.css", import.meta.url), "utf8");     // jsdom does no layout, so scroll rules are checked in the stylesheet

const base = process.argv[2];
const failures = [], passed = [];
const page = await openPage(base);
const w = page.window;
const ALL = ["alpha", "beta", "gamma"];

const $$ = s => page.$$(s);
const byText = (sel, re) => $$(sel).find(e => re.test(e.textContent.trim()));
const button = (re, within = "#main") => byText(`${within} button, ${within} .btn`, re);
/** Choose an entry of the Statistics page's "Add several…" menu (the first list's). */
const several = re => { const s = page.$("#main select[aria-label='Add several variables']"); page.change(s, [...s.options].find(o => re.test(o.textContent)).value); };
const drawerText = () => (page.$("#drawerBody") || {}).textContent || "";
const drawerOpen = () => page.$("#drawer") && !page.$("#drawer").hidden;
async function until(fn, what, ms = 15000) { await waitFor(fn, what, ms); }       // generous: a busy computer must not fail a test
async function scenario(name, fn) {
  const before = page.errors.length;
  try {
    await fn();
    const errs = page.errors.slice(before);
    if (errs.length) throw new Error("script errors: " + errs.join(" | ").slice(0, 400));
    const bad = name.includes("bad query") ? [] : page.problems();
    if (bad.length) throw new Error(bad.join(" | "));
    passed.push(name);
  } catch (e) { failures.push(`${name}: ${e.message}`); }
  await page.settle("end of " + name).catch(() => {});
}
const fmtNum = n => page.eval(`fmt(${n})`);
function expect(cond, message) { if (!cond) throw new Error(message); }

// a fresh start for each scenario
const ORIGINAL_SOURCES = (await api(base, "/api/library")).sources;
async function reset() {
  for (const b of ALL) await api(base, "/api/books/" + b, { title: "", author: "", year: "", series: "", tags: [], pinned: null });
  page.$("#toast").hidden = true;
  for (const c of (await api(base, "/api/library")).collections) await api(base, "/api/collections/delete", { id: c.id });
  for (const g of (await api(base, "/api/library")).groups) await api(base, "/api/groups/delete", { id: g.id });
  for (const x of (await api(base, "/api/stats/sets")).sets) await api(base, "/api/stats/sets/delete", { id: x.id });
  for (const x of (await api(base, "/api/lexicons")).lexicons) await api(base, `/api/lexicons/${x.id}/delete`, {});
  for (const b of ALL) await api(base, "/api/annot/narrator", { book: b, narrator: null });
  for (const b of ALL) await api(base, "/api/narrative/chapters", { book: b, action: "reset" });
  for (const m of (await api(base, "/api/topics/models")).models) await api(base, "/api/topics/delete", { id: m.id });
  await api(base, "/api/settings", { sources: ORIGINAL_SOURCES, min: { PER: 2, LOC: 2, FAC: 2, GPE: 2, VEH: 2, ORG: 2, VAR: 2 }, count_mode: "per_book", freq_mode: "combined", conv_gap: 100 });
  w.localStorage.clear();
  await page.eval("S.sel = null; S.units = null; S.entMulti = false; S.entSel = []; S.entType = 'PER'; S.entQuery = ''; S.cmp = { a: null, b: null, rel: 'agent' }; S.over.target = null; S.over.other = null; S.over.asking = false; S.over.book = null; S.over.al_b_book = null; S.pickedBook = null; S.over.al = { a: { target: null }, b: { same: true, target: null } }; loadLib()");
}

/** Open the book button's panel (the book picker). */
const openBooks = () => { if (page.$("#selPop").hidden) page.click(page.$("#booksBtn")); };

await scenario("books: edit a title and choose books", async () => {
  await reset();
  await page.go("#/books");
  expect($$("#main button").some(b => /Original text/.test(b.textContent)), "download button for a book's original text");
  const card = () => page.$("#main .bookcard");
  page.click(byText("#main .bookcard button", /^Add author, year, series, tags$/));                 // the details form opens in the card
  const title = card().querySelector(".bedit input");
  expect(title && title.value === "alpha", "title input for alpha");
  page.change(title, "Alpha Book");
  await until(() => page.eval("S.lib.books.find(b => b.id === 'alpha').title") === "Alpha Book", "title saved locally");
  expect((await api(base, "/api/library")).books.find(b => b.id === "alpha").title === "Alpha Book", "title saved on the server");
  const tags = card().querySelectorAll(".bedit input")[4];
  page.change(tags, "classic, holmes");
  await until(() => page.eval("S.lib.books.find(b => b.id === 'alpha').tags.join()") === "classic,holmes", "tags saved");
  page.click(byText("#main .bookcard button", /^Done$/));
  expect(card().querySelector(".bn").textContent === "Alpha Book" && [...card().querySelectorAll(".tagchip")].map(t => t.textContent).join() === "classic,holmes", "the card shows the title and tag chips again");
  page.click(card().querySelector(".tagchip"));                                                      // a tag chip searches for the tag
  await until(() => $$("#main .bookcard").length === 1 && page.$("#main .libtools input[type=search]").value === "classic", "a tag chip narrows the cards to the books with that tag");
  page.input(page.$("#main .libtools input[type=search]"), "");
  await until(() => $$("#main .bookcard").length === 3, "an empty search lists every book again");
  const beta = $$("input[type=checkbox][aria-label^='Use']")[1];
  beta.checked = false; page.change(beta);
  expect(JSON.stringify(page.eval("S.sel")) === JSON.stringify(["alpha", "gamma"]), "selection is alpha and gamma");
  expect(/2 of 3 books/.test(page.$("#viewTip").textContent) && page.$("#booksBtn").classList.contains("on"), "the book button says 2 of 3 books and is marked");
});

await scenario("settings: change the minimum, add a bad folder and remove it", async () => {
  await reset();
  await page.go("#/settings");
  expect(page.$$(".stoc a").map(a => a.textContent).join() === "Appearance,Entities,Words,Sound and rhythm,Folders", "the contents list names the sections");
  const per = $$("input[aria-label^='Minimum for']")[0];
  page.change(per, "3");
  await until(() => page.eval("S.lib.settings.min.PER") === 3, "minimum saved");
  await page.settle();
  expect(page.eval("S.lib.settings.freq_mode") === "combined", "word frequencies are counted over the books together to begin with");
  page.click($$("#settings-words .seg button").find(b => /separately/.test(b.textContent)));
  await until(() => page.eval("S.lib.settings.freq_mode") === "per_book", "word frequency mode saved");
  await page.settle();
  page.change(page.$("#settings-sound input[aria-label='Run window (content words)']"), "6");
  await until(() => page.eval("S.lib.settings.sound.window") === 6, "the run window saved");
  await page.settle();
  page.click($$("#settings-sound .seg button").find(b => /Nowhere/.test(b.textContent)));
  await until(() => page.eval("S.lib.settings.sound.boundary") === "none", "the run boundary saved");
  await page.settle();
  page.click($$("#settings-sound .seg button").find(b => /First letter/.test(b.textContent)));
  await until(() => page.eval("S.lib.settings.sound.alliteration") === "letter", "alliteration by first letter saved");
  await page.settle();
  page.click($$("#settings-sound .seg button").find(b => /Same word form/.test(b.textContent)));
  await until(() => page.eval("S.lib.settings.sound.repetition") === "form", "repetition by word form saved");
  await page.settle();
  const src = page.$("input[placeholder='/path/to/folder/with/books']");
  src.value = "/no/such/folder";
  page.click(button(/Add folder/));
  await until(() => /Folder not found/.test(page.text()), "problem shown");
  const row = $$("#main .srcs li").find(r => r.textContent.includes("/no/such/folder"));
  page.click([...row.querySelectorAll("button")].find(b => /Remove/.test(b.textContent)));
  await until(() => !/Folder not found/.test(page.text()), "problem gone");
  const booksRow = $$("#main .srcs li").find(r => /Books folder/.test(r.textContent));
  expect(booksRow && booksRow.querySelector("code").textContent === page.eval("S.lib.books_dir"), "the workspace's books folder is listed");
  page.click([...booksRow.querySelectorAll("button")].find(b => b.textContent === "Open"));
  await until(() => /^Opened .*books$/.test(page.$("#toast").textContent), "Open shows the books folder in the file browser");
  const srcRow = $$("#main .srcs li").find(r => !/Books folder|Data folder/.test(r.textContent));
  page.click([...srcRow.querySelectorAll("button")].find(b => b.textContent === "Open"));
  await until(() => page.$("#toast").textContent === "Opened " + page.eval("S.lib.sources[0]"), "and a source folder");
  page.click(button(/^Dark$/));
  expect(page.eval("document.documentElement.dataset.theme") === "dark", "the theme choice applies");
  page.click(button(/^Auto$/));
});

await scenario("books: the narrator is chosen from a searchable popover on the book's card", async () => {
  await reset();
  await page.go("#/books");
  const watson = (await api(base, "/api/annot/narrator_options?book=alpha")).rows.find(r => r.name === "Watson").id;
  const pick = () => page.$("#main .bookcard .npick");
  await until(() => /Unnamed narrator/.test(pick().textContent), "the button names the narrator (unnamed at first)");
  page.click(pick().querySelector("button"));
  const pop = () => pick().querySelector(".pop");
  await until(() => pop().querySelector(".pop-item"), "the book's people are fetched when the popover first opens");
  expect(!pop().hidden && [...pop().querySelectorAll(".pop-item")][0].textContent === "Unnamed narrator", "the popover lists Unnamed narrator first");
  page.input(pop().querySelector("input"), "wat");
  const items = () => [...pop().querySelectorAll(".pop-item")].map(i => i.textContent);
  expect(items().join() === "Watson", "the search narrows the list to matching people");
  page.click(pop().querySelector(".pop-item"));
  await until(() => pop().hidden && /Watson/.test(pick().textContent), "choosing closes the popover and shows the name");
  expect((await api(base, "/api/annot/narrator_options?book=alpha")).current === watson, "the narrator was saved");
  page.click(pick().querySelector("button"));
  w.document.body.dispatchEvent(new w.MouseEvent("mousedown", { bubbles: true }));
  expect(pop().hidden, "a click outside closes it");
});

await scenario("books: export the selected books as a zip", async () => {
  await reset();
  await page.go("#/books");
  const beta = $$("input[type=checkbox][aria-label^='Use']")[1];
  beta.checked = false; page.change(beta);                                  // alpha and gamma stay selected
  let blob = null, fileName = null;
  const realClick = w.HTMLAnchorElement.prototype.click;
  w.URL.createObjectURL = b => { blob = b; return "blob:test"; };           // catch what would be downloaded (jsdom can't follow the link)
  w.HTMLAnchorElement.prototype.click = function () { fileName = this.download; };
  const btn = button(/Export selected books/);
  expect(btn, "export button on the Library page");
  page.click(btn);
  await until(() => /Exported 2 books/.test(page.$("#toast").textContent), "export done");
  expect(blob && blob.type === "application/zip" && blob.size > 0, "a zip was downloaded");
  const bytes = new Uint8Array(await blob.arrayBuffer());
  expect(bytes[0] === 0x50 && bytes[1] === 0x4b, "it is a zip file");
  expect(/^analyser-export-\d{8}-\d{6}\.zip$/.test(fileName), "the file is named by the server: " + fileName);
  expect(!btn.disabled, "the button is usable again");
  w.URL.createObjectURL = () => "blob:test";
  w.HTMLAnchorElement.prototype.click = realClick;
});

await scenario("workspaces: make, rename, switch, remove, and delete one by typing its name", async () => {
  await reset();
  await page.go("#/books");
  const panelOf = () => $$("#main section.lsec").find(p => /^Workspaces/.test(p.querySelector("h2").textContent));
  const rowOf = name => [...panelOf().querySelectorAll(".coll")].find(r => r.querySelector("strong").textContent === name);
  const rowButton = (name, re) => [...rowOf(name).querySelectorAll("button")].find(b => re.test(b.textContent));
  const listed = async () => (await api(base, "/api/workspaces")).workspaces;
  const menuRows = () => [...page.$$("#wsMenu button")];
  const pickerText = () => menuRows().map(b => b.textContent).join();
  const pickRow = name => page.click(menuRows().find(b => b.textContent === name));
  expect(panelOf() && rowOf("Default"), "a Workspaces section on the Library page lists the Default workspace");
  expect(!rowButton("Default", /Switch|Remove|Delete/), "the workspace in use has no switch, remove or delete button");
  page.click(rowButton("Default", /Open folder/));
  await until(() => page.$("#toast").textContent === "Opened " + page.eval("S.lib.data_dir"), "Open folder shows the workspace's folder");
  expect(pickerText() === "Default" && page.$("#wsVal").textContent === "Default", "the Workspace submenu lists it and the row names it");
  expect(menuRows()[0].classList.contains("on") && page.$("#wsMenu a").getAttribute("href") === "#/books", "it is ticked, and a link leads to the management section");

  const make = async name => {
    panelOf().querySelector("input[aria-label='Name of the new workspace']").value = name;
    page.click(button(/Make a workspace/));
    await until(() => rowOf(name), `${name} is listed`);
  };
  await make("Scratch");
  expect(pickerText() === "Default,Scratch", "the submenu offers the new workspace");
  expect((await listed()).length === 2, "the server has it");

  page.click(rowButton("Scratch", /Rename/));
  page.input(panelOf().querySelector("input[aria-label='Rename']"), "Practice");
  page.click([...panelOf().querySelectorAll("button")].find(b => b.textContent === "OK"));
  await until(() => rowOf("Practice"), "renamed");

  // switching: the server opens the workspace and the page is told to reload (jsdom can't, so the call is replaced)
  page.eval("window.__reloads = 0; reloadPage = () => { window.__reloads++; }");
  pickRow("Practice");                                                  // renaming doesn't change the id ("scratch")
  await until(() => page.eval("window.__reloads") === 1, "the page reloads after switching from the menu");
  expect((await listed()).find(x => x.active).id === "scratch", "the server is in the other workspace");
  await page.eval("loadWorkspaces()");                                   // what the reload would do: redraw the menu from the server
  pickRow("Default");
  await until(() => page.eval("window.__reloads") === 2, "and after switching back");
  expect((await listed()).find(x => x.active).id === "default", "the server is back in Default");
  page.click(rowButton("Practice", /Switch to/));
  await until(() => page.eval("window.__reloads") === 3, "the row's button switches too");
  await api(base, "/api/workspaces/activate", { id: "default" });

  // removing from the list (asks first; the files stay)
  await make("Temp");
  page.click(rowButton("Temp", /Remove from list/));
  await until(() => !rowOf("Temp"), "Temp is gone from the list");

  // deleting needs the name typed out
  page.click(rowButton("Practice", /Delete/));
  const go = [...panelOf().querySelectorAll("button")].find(b => b.textContent === "Delete for good");
  const typed = panelOf().querySelector("input[aria-label^='Type']");
  expect(go.disabled, "Delete for good starts disabled");
  page.input(typed, "practice");
  expect(go.disabled, "a name that differs (even in case) keeps it disabled");
  page.input(typed, "Practice");
  expect(!go.disabled, "the exact name enables it");
  page.click(go);
  await until(() => !rowOf("Practice"), "Practice is deleted");
  expect((await listed()).map(x => x.id).join() === "default" && pickerText() === "Default", "only Default is left, on the server and in the submenu");
  expect(!rowOf("Default").querySelector("button[title^='Delete']"), "Default can't be deleted");
});

await scenario("[...] menu: opens on click, submenus open to the left on hover or click, closes on choosing, outside click and Escape", async () => {
  await reset();
  const menu = page.$("#moreMenu"), theme = page.$("#themeVal").closest(".sub"), themeMenu = theme.querySelector(".menu");
  const fire = (el, type, init = {}) => el.dispatchEvent(new w.MouseEvent(type, { bubbles: true, cancelable: true, ...init }));
  expect(menu.hidden, "closed to start with");
  page.click(page.$("#moreBtn"));
  expect(!menu.hidden && page.$("#moreBtn").getAttribute("aria-expanded") === "true", "opens on click");
  expect(["Entity Links", "Narrators"].every(t => [...menu.querySelectorAll("a.mi")].some(a => a.textContent === t)), "lists the two pages");
  expect(themeMenu.hidden, "a submenu is closed until asked for");
  fire(theme, "mouseover");
  expect(!themeMenu.hidden, "hovering the Theme row opens its submenu");
  fire(menu.querySelector("a.mi"), "mouseover");
  expect(themeMenu.hidden, "hovering another row closes it");
  page.click(theme.querySelector("[aria-haspopup]"));
  expect(!themeMenu.hidden, "clicking the row opens it");
  page.click(theme.querySelector("[aria-haspopup]"));
  expect(!themeMenu.hidden, "clicking it again keeps it open (pointing at the row had opened it already)");
  // choosing a theme applies it, remembers it, marks it and closes the whole menu
  const applied = () => w.document.documentElement.dataset.theme || "auto";
  page.click(theme.querySelector("[aria-haspopup]"));
  const pick = name => page.click(themeMenu.querySelector(`[data-theme=${name}]`));
  pick("dark");
  expect(applied() === "dark" && JSON.parse(w.localStorage.getItem("analyser.theme")) === "dark", "dark applied and saved");
  expect(menu.hidden && themeMenu.hidden, "choosing closes the menu and the submenu");
  expect(page.$("#themeVal").textContent === "Dark" && themeMenu.querySelector("[data-theme=dark]").getAttribute("aria-checked") === "true", "the choice is marked");
  pick("auto");
  expect(applied() === "auto", "auto removes the override");
  // the book button's panel: built when opened, stays open for clicks inside it, closes on Cancel, an outside click and Escape; never open together with the menu
  const booksMenu = page.$("#selPop"), booksBtn = page.$("#booksBtn");
  expect(booksMenu.hidden && booksBtn.getAttribute("aria-expanded") === "false", "closed to start with");
  page.click(page.$("#moreBtn")); page.click(booksBtn);
  expect(!booksMenu.hidden && menu.hidden && booksMenu.querySelectorAll(".books-list label.book").length === 3, "the book button opens the picker (and closes the menu), with every book in its own scrolling list");
  page.click(booksMenu.querySelector("h3")); fire(booksMenu.querySelector("h3"), "mouseover");
  expect(!booksMenu.hidden && booksMenu.querySelectorAll("label.book").length === 3, "clicking or pointing inside it leaves it as it is");
  page.click(page.$("#moreBtn"));
  expect(booksMenu.hidden && !menu.hidden, "opening the menu closes the picker");
  page.click(booksBtn); page.click(byText("#selPop button", /^Cancel$/));
  expect(booksMenu.hidden, "Cancel closes the picker");
  page.click(booksBtn); fire(w.document.body, "mousedown");
  expect(booksMenu.hidden, "a click outside closes it");
  page.click(booksBtn); w.document.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  expect(booksMenu.hidden, "Escape closes it");
  expect(/Viewing/.test(page.$("#viewTip").textContent) && /All 3 books/.test(page.$("#viewTip").textContent), "the tooltip says what is viewed");
  // Plural groups: one setting for every page, saved on the server, ticked in the menu, closing the menu
  const plural = () => page.$("#pluralItem"), serverPlural = async () => (await api(base, "/api/library")).settings.plural;
  expect(!(await serverPlural()) && !plural().classList.contains("on") && page.$("#pluralVal").textContent === "Off", "off to begin with");
  page.click(page.$("#moreBtn")); page.click(plural());
  await until(() => plural().classList.contains("on"), "the row is ticked");
  expect(menu.hidden && page.$("#pluralVal").textContent === "On" && plural().getAttribute("aria-checked") === "true", "choosing it closes the menu and says On");
  expect(await serverPlural() === true && page.eval("pluralMode()") === true, "the server and the page both have it on");
  await page.go("#/compare"); expect(page.eval("pluralMode()") === true, "every page uses it");
  expect(!page.$("#pluralSlot") && !$$("label").some(l => /Include plural-group/.test(l.textContent)), "no per-page checkbox is left");
  page.click(page.$("#moreBtn")); page.click(plural());
  await until(() => !plural().classList.contains("on"), "switched off again");
  expect(await serverPlural() === false, "and off on the server");
  // outside click and Escape
  page.click(page.$("#moreBtn")); fire(w.document.body, "mousedown");
  expect(menu.hidden, "a click outside closes it");
  page.click(page.$("#moreBtn")); w.document.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  expect(menu.hidden, "Escape closes it");
  // a page in the menu is highlighted, and so is the button
  await page.go("#/narrators");
  expect(menu.querySelector("a[data-tab=narrators]").classList.contains("on") && page.$("#moreBtn").classList.contains("on"), "the open page is marked");
  // the top bar: the brand is only a label; the Library is a button of its own, then a gap and the other pages as one segmented control
  expect(page.$(".mark").tagName === "SPAN", "the aLex brand is a plain label, not a link");
  await page.go("#/entities");
  expect(page.$$("#tabs .seg").length === 2 && page.$("#tabs .seg a").dataset.area === "books", "the Library is a segment of its own");
  expect(page.$("#tabs a.on").dataset.area === "entities", "the open area is marked");
});

await scenario("areas: the top bar's eight areas, each page's tabs above it, and an area reopens the page last used in it", async () => {
  await reset();
  const area = id => page.$(`#tabs a[data-area=${id}]`), navTabs = () => $$("#areaNav a").map(a => a.textContent);
  expect($$("#tabs a[data-area]").map(a => a.textContent).join("|") === "Library|Entities|Dialogue|Words|Style|Over time|Statistics|Read", "eight areas, Read last");
  // the old addresses keep working, each in its new area
  for (const [hash, id, tab] of [["#/compare", "entities", "Compare"], ["#/corpus/ngrams", "words", "N-grams"], ["#/topics", "words", "Topics"],
    ["#/narrative/stylometry", "style", "Stylometry"], ["#/sound", "style", "Sound and rhythm"], ["#/narrative/arcs", "time", "Arcs"], ["#/over/aligned", "time", "Over the book"]]) {
    await page.go(hash);
    expect(area(id).classList.contains("on") && byText("#areaNav a.on", new RegExp(`^${tab}$`)), `${hash} opens in ${id} on its ${tab} tab`);
  }
  expect(navTabs().join("|") === "Over the book|Arcs|Sentiment|Lexicons", "Over time's pages: " + navTabs().join("|"));
  expect(!page.$("#main .subtabs a"), "the page draws no tab row of its own for the area's pages");
  // an area of one page, or a page of the [...] menu, has no row
  await page.go("#/stats");
  expect(page.$("#areaNav").hidden && area("stats").classList.contains("on"), "Statistics: no row");
  await page.go("#/settings");
  expect(page.$("#areaNav").hidden && !page.$("#tabs a.on"), "Settings: no area");
  // the chapter editor belongs to Read
  await page.go("#/chapters");
  expect(area("read").classList.contains("on"), "the chapter editor is in Read");
  // an area reopens where you were
  await page.go("#/corpus/collocates");
  await page.go("#/narrative/style");
  expect(area("words").getAttribute("href") === "#/corpus/collocates", "Words now leads back to Collocates");
  page.click(area("words"));
  await until(() => w.location.hash === "#/corpus/collocates" && byText("#areaNav a.on", /^Collocates$/), "and opens it");
  expect(page.eval("loadState('analyser.areas', {}).words") === "#/corpus/collocates", "remembered for the workspace");
  await page.go("#/corpus/kwic");
});

await scenario("entities: filter by type and name, open a profile, tabs, evidence, tags", async () => {
  await reset();
  await page.go("#/entities");
  const names = () => $$("#main .ent-item .cnt").map(n => +n.textContent.replace(/,/g, ""));
  const normal = names();
  expect(normal.length > 1 && normal.every((n, i) => i === 0 || n <= normal[i - 1]), "most mentioned first by default");
  const dirBtn = page.$("#main .head button.btn.small");
  expect(dirBtn, "the sort-direction button");
  page.click(dirBtn);
  const reversed = names();
  expect(reversed.join() === normal.slice().reverse().join(), "the reverse button flips the order");
  page.click(dirBtn);
  expect(names().join() === normal.join(), "clicking again restores it");
  page.click(byText("#main .chip", /^LOC/));
  await until(() => $$("#main .ent-item").length > 0 && $$("#main .ent-item .nm").every(n => /Street|street/.test(n.textContent)), "only places listed");
  page.click(byText("#main .chip", /^PER/));
  await page.settle();
  const q = page.$("#main input[type=search]");
  page.input(q, "watson");
  await until(() => $$("#main .ent-item .nm").length > 0 && $$("#main .ent-item .nm").every(n => /Watson/.test(n.textContent)), "filtered by name");
  page.click($$("#main .ent-item")[0]);
  await until(() => /How they're referred to/.test(page.text()), "profile shown");
  expect(/Watson/.test(page.$("#main h1").textContent), "profile is Watson's");
  page.click(byText("#main .subtabs button", /Modifiers|Possessions/));
  page.click(byText("#main .subtabs button", /Actions/));
  const row = $$("#main table.t2 tbody tr.click")[0];
  page.click(row);
  await until(() => drawerOpen() && /sentence/.test(drawerText()) && $$("#drawerBody .ev").length > 0, "evidence sentences");
  page.window.document.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Escape" }));
  expect(!drawerOpen(), "Escape closes the drawer");
  const tag = page.$("#main .tag-edit input");
  tag.value = "narrator";
  tag.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  await until(() => $$("#main .tag-edit .tag").some(t => /narrator/.test(t.textContent)), "tag added");
  expect((await api(base, "/api/library")).tags.includes("narrator"), "tag saved");

  const renameBtn = byText("#main .phead-id button", /^Rename$/);
  expect(renameBtn, "a Rename link next to the name");
  page.click(renameBtn);
  const nameInp = page.$("#main .phead-id input[type=text]");
  nameInp.value = "Doctor Watson";
  nameInp.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  await until(() => (page.$("#main h1") || {}).textContent === "Doctor Watson", "renamed");
  const resetBtn = () => byText("#main .phead-id button", /^Reset$/);
  await until(resetBtn, "a Reset link appears once renamed");
  page.click(resetBtn());
  await until(() => (page.$("#main h1") || {}).textContent === "Watson", "Reset restores the name found in the books");

  const descBtn = byText("#main .phead-id button", /Description/);
  expect(descBtn, "a description link");
  page.click(descBtn);
  const descInp = page.$("#main .phead-id input[type=text]");
  descInp.value = "Loyal friend";
  descInp.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  await until(() => /Loyal friend/.test(page.$("#main .phead-id").textContent), "description saved");
});

await scenario("book by book: several books sort by year, undated last, and the book name drills down to one", async () => {
  await reset();
  await api(base, "/api/books/alpha", { year: 1902 });
  await api(base, "/api/books/beta", { year: 1890 });     // gamma stays undated: it must sort last
  const p1 = await api(base, "/api/links/link", { a: "e:alpha:1", b: "e:beta:5" });
  await api(base, "/api/links/link", { a: p1.id, b: "e:gamma:3" });
  await page.eval("S.units = null; loadLib()");
  await page.go("#/entities/" + encodeURIComponent(p1.id));
  await until(() => /Book by book/.test(page.text()), "profile with a book-by-book section");
  const section = byText("#main h2", /^Book by book$/).closest("section");
  const rows = [...section.querySelectorAll("table.t2 tbody tr")].map(r => r.querySelector("td").textContent.trim());
  expect(rows[0] === "beta" && rows[1] === "alpha" && rows[2] === "gamma", "beta (1890), alpha (1902), then undated gamma: " + rows.join(","));
  const link = [...section.querySelectorAll("a")].find(a => a.title === "Show just this book" && a.textContent.trim() === "beta");
  expect(link, "beta's name is a drill-down link");
  page.click(link);
  await until(() => JSON.stringify(page.eval("S.sel")) === '["beta"]', "selection narrowed to beta alone");
  await until(() => /1 of 3 books/.test(page.$("#viewTip").textContent), "the book button updated");
  await until(() => /Viewing.*beta/.test(page.$("#viewTip").textContent), "the book button's tooltip names the drilled-down book");
  const back = page.$("#viewBack");
  expect(!back.hidden && back.textContent === "← Back to all books" && /click/i.test(back.title), "a Back button appears once narrowed, and says where it goes");
  page.click(back);
  await until(() => JSON.stringify(page.eval("S.sel")) === "null", "Back restores the wider selection");
  await until(() => page.$("#viewBack").hidden, "Back button gone once restored");
});

await scenario("entity page: Book by book and What's distinctive share the significance settings, and both follow a change made in either", async () => {
  await reset();
  const p1 = await api(base, "/api/links/link", { a: "e:alpha:1", b: "e:beta:5" });
  await page.eval("S.units = null; loadLib()");
  try {
    await page.go("#/entities/" + encodeURIComponent(p1.id));
    await until(() => byText("#main h2", /^Book by book$/) && byText("#main h2", /What's distinctive/), "both panels on one profile");
    const minFreq = h2 => { const sec = byText("#main h2", h2).closest("section"); return [...sec.querySelectorAll("label")].find(l => /^Minimum frequency/.test(l.textContent.trim())).querySelector("input"); };
    const setMin = (h2, v) => { const i = minFreq(h2); i.value = String(v); i.dispatchEvent(new w.Event("change", { bubbles: true })); };
    const startVal = minFreq(/^Book by book$/).value;
    expect(minFreq(/What's distinctive/).value === startVal, "both start on the same minimum frequency");
    setMin(/^Book by book$/, 6);
    await until(() => minFreq(/What's distinctive/).value === "6", "What's distinctive follows a change made in Book by book");
    setMin(/What's distinctive/, 9);
    await until(() => minFreq(/^Book by book$/).value === "9", "and Book by book follows one made in What's distinctive");
    // the help: the heading's "?" opens the profile's help at that section, without folding the panel
    page.click(byText("#main h2", /^Book by book$/).querySelector(".hq"));
    expect(!page.$("#drawer").hidden && /^Entity profile: help/.test(page.$("#drawerTitle").textContent) && page.$("#drawerBody [data-help='bybook']"), "the profile's help opens");
    expect(!byText("#main h2", /^Book by book$/).closest("section").classList.contains("collapsed"), "the panel stays open");
    page.click(page.$("#drawerClose"));
  } finally {
    await page.eval("S.stat.min_freq = 3");
    await api(base, "/api/links/unlink_all", { id: p1.id }).catch(() => {});
    await page.eval("S.units = null");
  }
});

await scenario("entity page: “Based on” lines name the settings and your corrections, tinted when set by you, each linking to its place", async () => {
  await reset();
  const q = (await api(base, "/api/dialogue/quotes", { books: ["alpha"], filter: { speaker: { kind: "unit", id: "e:alpha:1" } }, limit: 1 })).items[0];
  await page.go("#/entities/" + encodeURIComponent("e:alpha:1"));
  const head = () => page.$("#main .phead .basedon"), speech = () => byText("#main h2", /^Speech$/) && byText("#main h2", /^Speech$/).closest("section").querySelector(".basedon");
  await until(() => head() && speech(), "the profile and its Speech section have a line");
  expect(/^Based on: at least 2 mentions in a book · plural groups off$/.test(head().textContent) && !head().querySelector(".set"), "at the defaults: " + head().textContent);
  expect(head().querySelector("a[href='#/settings/entities']"), "the mentions link to Settings → Entities");
  expect(/a conversation ends after 100 narration words/.test(speech().textContent) && !speech().querySelector(".set"), "Speech names the conversation gap, not tinted");
  expect(byText("#main h3", /^Talks to/) && byText("#main h3", /^Talks to/).querySelector(".rel[title^='Estimated']"), "the estimated addressees carry the ≈ marker (AL-PRIN-14)");
  try {
    await api(base, "/api/annot/addressees", { book: "alpha", qi: q.qi, addressees: ["*"] });
    await api(base, "/api/settings", { plural_default: true });
    await page.eval("S.units = null; loadLib()");
    await page.go("#/entities");
    await page.go("#/entities/" + encodeURIComponent("e:alpha:1"));
    await until(() => head() && /plural groups count/.test(head().textContent) && speech() && /addressees set by you: 1 quote by them/.test(speech().textContent), "the lines follow");
    expect(byText("#main .phead .bo.set", /plural groups count/), "a setting changed from its default is tinted");
    expect(speech().querySelector("a.bo.set[href='#/dialogue/quotes']"), "a correction is tinted too, and leads to the quotes");
    // the link to a Settings section scrolls there
    page.click(head().querySelector("a[href='#/settings/entities']"));
    await until(() => /#\/settings\/entities/.test(w.location.hash) && page.$("#settings-entities"), "Settings opens");
  } finally {
    await api(base, "/api/annot/addressees", { book: "alpha", qi: q.qi, addressees: null }).catch(() => {});
    await api(base, "/api/settings", { plural_default: false }).catch(() => {});
    await page.eval("S.units = null; loadLib()");
  }
});

await scenario("entity page: sections in the order of their questions, grouped in the side menu; kinds of action inside What they do; quiet downloads", async () => {
  await reset();
  await page.go("#/entities/" + encodeURIComponent("e:alpha:1"));
  const heads = () => $$("#main section.panel > h2").map(x => x.textContent.trim());
  await until(() => heads().length >= 8 && page.$("#main .page-toc .page-toc-group"), "the profile and its side menu");
  expect(heads().join("|") === "How they're referred to|Appears with|What they do and what's done to them|Speech|Book by book|Over the book|What's distinctive|Topics", "order: " + heads().join("|"));
  const toc = $$("#main .page-toc > .page-toc-group, #main .page-toc > a").map(x => (x.classList.contains("page-toc-group") ? "#" : "") + x.textContent.trim());
  expect(toc.join("|") === "#Who they are|How they're referred to|Appears with|#What they do|What they do and what's done to them|#What they say|Speech|#How they change|Book by book|Over the book|#What sets them apart|What's distinctive|Topics",
    "the side menu groups them: " + toc.join("|"));
  const what = byText("#main section.panel > h2", /^What they do/).closest("section");
  expect(byText("#main h3", /^Kinds of action$/).closest("section") === what && what.querySelector(".chart-box svg"), "Kinds of action is a part of What they do");
  expect(!$$("#main .chart-tools .btn, #main .tbl-foot .btn").some(b => /^(SVG|PNG|Download CSV)$/.test(b.textContent)), "no bordered download buttons");
  expect(byText("#main .chart-tools .dl", /^SVG$/) && byText("#main .tbl-foot .dl", /^CSV$/), "but quiet SVG · PNG and CSV links");
});

await scenario("focus: each page its own by default; one focus for every page follows the subjects, never the references, and a link's choice leads", async () => {
  await reset();
  const chip = () => page.$("#focusChip");
  try {
    // each page its own (the default): opening a profile changes nothing elsewhere
    await page.eval(`S.focus = { mode: "page", target: null }; saveFocus(); S.desc.target = null`);
    await page.go("#/entities/" + encodeURIComponent("e:alpha:1"));
    await until(() => page.$("#main .phead"), "a profile");
    expect(chip().hidden && page.eval("S.focus.target") === null, "no focus, no chip");
    await page.go("#/described");
    expect(page.eval("S.desc.target") === null && !page.$("#main .subject"), "Described as keeps its own (none)");
    // one focus for every page, chosen on the Settings page
    await page.go("#/settings/entities");
    page.click(byText("#main button", /^One focus for every page$/));
    await until(() => page.eval("S.focus.mode") === "shared", "the mode is saved");
    await page.go("#/entities/" + encodeURIComponent("e:alpha:1"));
    await until(() => !chip().hidden && /Focus: Holmes/.test(chip().textContent), "opening a profile makes it the focus, named in the top bar");
    await page.go("#/described");
    await until(() => page.$("#main .subject") && page.eval("S.desc.target && S.desc.target.id") === "e:alpha:1", "Described as follows it");
    expect(/follows the focus/.test(page.$("#main .subject").textContent), "and says so");
    page.eval(`S.cmp = { a: null, b: { kind: "unit", id: "e:alpha:2", name: "Watson" }, rel: "agent" }`);
    await page.go("#/compare");
    await until(() => page.eval("S.cmp.a && S.cmp.a.id") === "e:alpha:1", "Compare's first side follows");
    expect(page.eval("S.cmp.b.id") === "e:alpha:2", "its second side keeps its own");
    // a kind a page can't take: a gender focus on Conversations-like pages keeps the page's own; here Speech verbs takes no group
    await page.eval(`S.focus.target = { kind: "group", ids: ["e:alpha:1", "e:alpha:2"], name: "a pair" }; saveFocus(); S.dlg.verbTarget = { kind: "unit", id: "e:alpha:2", name: "Watson" }; focusSeen["dialogue/verbs"] = JSON.stringify(S.dlg.verbTarget)`);
    await page.go("#/dialogue/verbs");
    await until(() => page.$("#main .subject"), "Speech verbs");
    expect(page.eval("S.dlg.verbTarget.id") === "e:alpha:2" && page.eval("S.focus.target.kind") === "group", "a group can't be a speaker there: its own choice shows, the focus stays");
    // a choice set by a link leads and becomes the focus
    await page.eval(`S.desc.target = { kind: "unit", id: "e:beta:5", name: "Holmes" }`);
    await page.go("#/described");
    await until(() => page.eval("S.focus.target.id") === "e:beta:5", "the link's choice becomes the focus");
    // × clears it
    page.click(chip().querySelector("button"));
    expect(chip().hidden && page.eval("S.focus.target") === null, "× clears the focus");
  } finally {
    await page.eval(`S.focus = { mode: "page", target: null }; saveFocus(); S.desc.target = null; S.cmp.a = null; S.dlg.verbTarget = null`);
  }
});

await scenario("book button tooltip: names a single book, a whole collection or series, or several unrelated books", async () => {
  await reset();
  await page.go("#/corpus");
  const label = () => page.$("#viewTip .view-label").textContent;
  await api(base, "/api/books/alpha", { year: 1902 });
  const coll = await api(base, "/api/collections", { name: "Casebook" });
  await api(base, "/api/collections/" + coll.id, { add: ["alpha", "beta"] });
  await page.eval("S.lib = null; loadLib()");
  await page.eval("setSel(['alpha','beta']); render()");
  await until(() => label() === "Casebook", "the whole collection is named: " + label());
  await page.eval("setSel(['alpha']); render()");
  await until(() => label() === "alpha", "a single book's own title (falls back to its id, untitled here): " + label());
  await page.eval("setSel(['alpha','beta','gamma']); render()");
  await until(() => label() === "Various", "unrelated books together: " + label());
});

await scenario("dialogue: quotes drawer and the quote editor", async () => {
  await reset();
  await page.go("#/dialogue/speakers");
  await until(() => $$("#main table.t2 tbody tr.click").length, "Who speaks");
  const speakers = byText("#main section.panel > h2", /^Speakers$/).closest("section");
  expect([...speakers.querySelectorAll("tbody a")].some(a => a.textContent === "Holmes (alpha)") && [...speakers.querySelectorAll("tbody a")].some(a => a.textContent === "Holmes (beta)"),
    "speakers of the same name are told apart by their book (AD-44)");
  page.click($$("#main table.t2 tbody tr.click")[0]);
  await until(() => drawerOpen() && $$("#drawerBody .ev").length > 0, "quotes in the drawer");
  page.click(byText("#drawerBody a", /^Correct$/));
  await until(() => page.$("#drawerBody .qedit .qrow"), "quote editor");
  page.click(byText("#drawerBody .qedit button", /Everyone present/));
  await until(() => /Set by you/.test(page.$("#drawerBody .qedit").textContent), "correction saved");
  page.click(byText("#drawerBody .qedit button", /Back to the estimate/));
  await until(() => /Estimated/.test(page.$("#drawerBody .qedit").textContent), "back to the estimate");
  await page.go("#/dialogue/conversations");
  expect(/conversation/.test(page.text()), "conversations listed");
  await page.go("#/dialogue/quotes");
  const verb = $$("#main input[type=search]").find(i => /whisper/.test(i.placeholder));
  page.change(verb, "say");
  await until(() => /quote/.test(page.text()) && $$("#main .ev").length > 0, "filtered quotes");
});

await scenario("dialogue: sentence-type filter (questions/exclamations/statements) in quotes, style and speaking style; Speech verbs' two filters stay independent; a compact select on an entity's own speech panel", async () => {
  await reset();
  await page.go("#/dialogue/speakers");          // in case the previous scenario already left the hash on #/dialogue/quotes: force a real navigation, not a no-op
  await page.go("#/dialogue/quotes");
  const count = () => +(/^([\d,]+) quote/.exec(page.$("#main .tbl-foot span").textContent) || [0, "0"])[1].replace(",", "");
  await until(() => count() > 0, "quotes loaded");
  const all = count();
  const typeSel = () => [...$$("#main select")].find(s => [...s.options].some(o => o.textContent === "Statements"));
  page.change(typeSel(), "question");
  await until(() => count() === 0, "the fixture never writes a literal ? or !, so no quote is a question");
  page.change(typeSel(), "statement");
  await until(() => count() === all, "every quote is a statement by punctuation, so this is back to all of them");
  page.change(typeSel(), "");
  await until(() => count() === all, "back to no filter");

  await page.go("#/dialogue/voice");
  await until(() => byText("#main label", /Sentence type/), "the same filter appears under Speaking style");
  expect(byText("#main label.inline", /Weigh the speech verb too/), "and the classification-rule checkbox");
  // Speaking style and Distinctive vocabulary each have their own filter, and so does the Quotes page: none changes another
  const voiceSels = () => [...$$("#main select")].filter(s => [...s.options].some(o => o.textContent === "Statements"));
  expect(voiceSels().length === 2, "Speaking style and Distinctive vocabulary each have a Sentence type select");
  page.change(voiceSels()[0], "question");
  await until(() => voiceSels()[0].value === "question", "Speaking style filtered to questions");
  expect(voiceSels()[1].value === "", "Distinctive vocabulary's own filter is unaffected");
  page.change(voiceSels()[1], "exclaim");
  await until(() => voiceSels()[1].value === "exclaim", "Distinctive vocabulary filtered to exclamations");
  expect(voiceSels()[0].value === "question", "and Speaking style's stays on questions");
  await page.go("#/dialogue/quotes");
  await until(() => count() > 0, "Quotes reloaded");
  expect(typeSel().value === "" && count() === all, "Quotes has its own filter: unaffected by How they speak's");
  await page.go("#/dialogue/voice");
  await until(() => voiceSels().length === 2, "How they speak again");
  expect(voiceSels()[0].value === "question" && voiceSels()[1].value === "exclaim", "How they speak remembers each filter separately");
  page.change(voiceSels()[0], "");
  page.change(voiceSels()[1], "");

  await page.go("#/dialogue/verbs");
  await until(() => /How speech is introduced/.test(page.text()) && byText("#main label", /Sentence type/), "and under How speech is introduced");
  const verbsSel = () => [...$$("#main select")].find(s => [...s.options].some(o => o.textContent === "Statements"));
  const verbQuotes = () => +((/of ([\d,]+) quote/.exec(page.text()) || [0, "0"])[1] || "0").toString().replace(/,/g, "");
  const before = verbQuotes();
  page.change(verbsSel(), "question");
  await until(() => /0 of 0 quote/.test(page.text()), "no questions overall either");
  page.change(verbsSel(), "");
  await until(() => verbQuotes() === before, "back to no filter");

  const holmes = (await api(base, "/api/units", { books: ALL })).rows.find(r => r.name === "Holmes" && r.books[0] === "alpha").id;
  const targetSection = byText("#main h2", /One speaker or group/).closest(".panel");
  const speakerBox = targetSection.querySelector("input[type=search]");
  speakerBox.focus();
  page.input(speakerBox, "Holmes");
  await until(() => targetSection.querySelectorAll(".sugg div").length > 0, "suggestions for a speaker");
  targetSection.querySelectorAll(".sugg div")[0].dispatchEvent(new w.MouseEvent("mousedown", { bubbles: true, cancelable: true }));
  await until(() => /quotes with a speech verb/.test(targetSection.textContent), "verbs for Holmes, in “One speaker or group”");
  expect([...targetSection.querySelectorAll("label")].find(l => /Sentence type/.test(l.textContent)), "which has its own Sentence type filter too");
  const targetText = () => targetSection.textContent.match(/Holmes:[^.]+\./)?.[0];
  const targetBefore = targetText();
  const targetSel = () => [...targetSection.querySelectorAll("select")].find(s => [...s.options].some(o => o.textContent === "Statements"));

  // the two filters must be independent: changing "How speech is introduced" leaves "One speaker or group" alone, and back
  page.change(verbsSel(), "question");
  await until(() => /0 of 0 quote/.test(page.text()), "How speech is introduced filters down to nothing");
  expect(targetText() === targetBefore, "but One speaker or group, filtered separately, is untouched by it");
  page.change(verbsSel(), "");
  await until(() => verbQuotes() === before, "How speech is introduced back to no filter");

  page.change(targetSel(), "question");
  await until(() => /: 0 quotes with a speech verb/.test(targetSection.textContent), "no questions for Holmes either");
  expect(verbQuotes() === before, "and How speech is introduced, filtered separately, is untouched by that in turn");
  page.change(targetSel(), "");
  await until(() => /quotes with a speech verb/.test(targetSection.textContent) && !/: 0 quotes with a speech verb/.test(targetSection.textContent), "back to no filter for the target too");

  await page.go("#/entities/" + encodeURIComponent(holmes));
  await until(() => byText("#main label", /Sentence type/), "the entity's own Speech panel has a compact sentence-type select");
  expect(byText("#main label.inline", /^Weigh the speech verb$/) && !byText("#main label.inline", /Weigh the speech verb too/), "with its own compact checkbox, separate from every Dialogue tab's");
  const quotesFact = () => +((/^[\d,]+/.exec(($$("#main .facts-inline div")[0] || {}).textContent || "") || ["0"])[0].replace(/,/g, ""));
  await until(() => quotesFact() > 0, "Holmes has quotes");
  const entSel = () => [...$$("#main select")].find(s => [...s.options].some(o => o.textContent === "Statements"));
  page.change(entSel(), "question");
  await until(() => /No quotes are attributed/.test(page.text()), "no questions for Holmes either, filtered right on the entity page");
  page.change(entSel(), "");
  await until(() => quotesFact() > 0, "back to no filter");
  const verbsHead = byText("#main h3", /Speech verbs/);
  expect(verbsHead, "the Speech verbs section shows too");
  expect(verbsHead.parentElement.textContent.includes("say"), "with a row for “say”, reflecting the earlier fix where this table used to ignore the filter");
});

await scenario("dialogue: verbs for one speaker through the picker", async () => {
  await reset();
  await page.go("#/dialogue/verbs");
  const box = page.$("#main .picker input[type=search]");
  box.focus();
  page.input(box, "Holmes");
  await until(() => $$("#main .picker .sugg div").length > 0, "suggestions");
  $$("#main .picker .sugg div")[0].dispatchEvent(new w.MouseEvent("mousedown", { bubbles: true, cancelable: true }));
  await until(() => /with a speech verb/.test(page.text()), "verbs for the speaker");
  // the top bar's ? opens the Dialogue help at the tab you are on
  page.click(page.$("#helpBtn"));
  const body = page.$("#drawerBody"), at = body.querySelector("[data-help='verbs']");
  expect(/^Dialogue: help/.test(page.$("#drawerTitle").textContent) && at, "the Dialogue help opens, with its Speech verbs section (jsdom has no layout, so the scroll itself is not checked)");
  page.click(page.$("#drawerClose"));
});

await scenario("dialogue: In-Depth Who Speaks scopes and compares by gender, tag, entity or group", async () => {
  await reset();
  await page.go("#/dialogue/indepth");
  await until(() => byText("#main h2", /Dialogue in each book/), "the default view matches Who speaks");
  expect($$("#main table").length && !$$("#main .facts-inline").length, "nothing chosen yet: the whole-selection tables, not pooled facts");

  const seg = txt => [...$$("#main .seg button")].find(b => b.textContent === txt);
  page.click(seg("Gender"));
  await until(() => $$("#main .facts-inline").length > 0, "a pooled Speakers card appears for the gender scope");
  const colQuotes = root => +((/^[\d,]+/.exec((root.querySelector(".facts-inline div") || {}).textContent || "") || ["0"])[0].replace(/,/g, ""));
  const genderQuotes = colQuotes(page.$("#main"));
  expect(genderQuotes > 0, "the gender scope has quotes");

  page.click(seg("Compare"));
  await until(() => /Choose two things to compare/.test(page.text()), "compare mode needs a second side");

  const refFld = byText("#main .fld", /Compared with/);
  const refBox = refFld.querySelector("input[type=search]");
  refBox.focus();
  page.input(refBox, "Holmes");
  await until(() => refFld.querySelectorAll(".sugg div").length > 0, "suggestions for the reference");
  refFld.querySelector(".sugg div").dispatchEvent(new w.MouseEvent("mousedown", { bubbles: true, cancelable: true }));
  await until(() => $$("#main .bar-cell").length > 0, "the compare layout (rows of paired bars, not side-by-side columns) appears");
  expect(!$$("#main .cols2").length, "no more side-by-side columns in Compare mode");
  const quotesLabel = [...$$("#main .small.muted")].find(d => d.textContent.trim() === "Quotes");
  expect(quotesLabel, "a Quotes comparison row");
  const barValue = el => +el.textContent.replace(/[^\d.]/g, "");
  const bars = [...quotesLabel.parentElement.querySelectorAll(".bar-cell")].map(barValue);
  expect(bars.length === 2, "two bars, target above reference");
  expect(bars[0] === genderQuotes, "the target bar still shows the gender scope's figures");
  expect(bars[1] > 0 && bars[1] <= genderQuotes, "the reference bar (Holmes alone) has fewer or equal quotes than the whole gender pool he's part of");
  expect(byText("#main h3", /Share of words in dialogue/), "the dialogue-share chart appears in Compare mode too, one shared graphic");
  expect($$("#main svg").length >= 2, "the paired per-book bar chart and the shared dialogue-share chart both render");
});

await scenario("corpus: concordance search, sorting, context, word list, n-grams", async () => {
  await reset();
  await page.go("#/corpus/kwic");
  const q = page.$("#main input[type=search]");
  q.value = "said";
  q.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  await until(() => $$("#main .kwic .kl").length > 0 && /hits?/.test(page.text()), "hits");
  const total = +(/([\d,]+) hits?/.exec(page.text()) || [])[1].replace(",", "");
  expect(total === 185, `185 hits for "said", got ${total}`);
  page.click(page.$("#main button[aria-label='Help: Simple and Pattern searches']"));
  expect(/^Corpus: help/.test(page.$("#drawerTitle").textContent) && page.$("#drawerBody [data-help='syntax'] dt"), "the search box's ? opens the Corpus help with the syntax");
  page.click(page.$("#drawerClose"));
  expect(page.$("#main .kwic.results-scroll"), "the concordance lines are a scrolling results box");
  expect(byText("#areaNav a.on", /^Concordance$/), "the tool tabs are the Words area's");
  const rule = name => new RegExp(`${name} \\{[^}]*\\}`).exec(css)[0];
  expect(/position: sticky; top: var\(--bar-h\)/.test(rule("#areaNav")) && /margin: 0 max/.test(rule("#areaNav")), "the area's tabs stay under the top bar (sticky, with no margin above that would make them bounce)");
  expect(/overscroll-behavior-y: none/.test(rule("html")), "the page has no elastic overscroll");
  expect(/max-height/.test(rule("\\.tbl-wrap, \\.results-scroll")) && /overflow: auto/.test(rule("\\.tbl-wrap, \\.results-scroll")), "results boxes are one screen tall and scroll inside");
  expect(!/overscroll-behavior/.test(css.match(/\.results-scroll[^{]*\{[^}]*\}/)[0]), "a results box hands scrolling to the page at its end");
  const sort = $$("#main select").find(s => [...s.options].some(o => /Search term/.test(o.textContent)));
  page.change(sort, "key");
  await page.settle();
  page.click($$("#main .kwic .kl")[0]);
  await until(() => drawerOpen() && /Open in the text/.test(drawerText()), "context drawer");
  await page.go("#/corpus/wordlist");
  page.click($$("#main table.t2 tbody tr.click")[0]);
  await until(() => /#\/corpus\/kwic/.test(w.location.hash) && $$("#main .kwic .kl").length > 0, "word list row opens its concordance");
  await page.go("#/corpus/ngrams");
  const contains = $$("#main input[type=search]").find(i => /any word/.test(i.placeholder));
  page.change(contains, "said");
  await until(() => $$("#main table.t2 tbody tr").every(r => /said/.test(r.textContent)), "n-grams contain the word");
  await page.go("#/corpus/collocates");
  await until(() => /hit for the search term|hits for the search term/.test(page.text()), "collocates of the last search");
  expect(/minimum frequency checked over the selected books together/.test(page.text()), "the collocates page reminds of the Words setting");
  await api(base, "/api/settings", { freq_mode: "per_book" });                         // the setting is read when the library loads
  await page.eval("loadLib()");
  await page.go("#/corpus/wordlist");
  await until(() => /minimum frequency checked in each book/.test(page.text()), "the word list says it counts in each book");
  expect(page.$("#main .basedon a.bo.set[href='#/settings/words']"), "and links to the setting, tinted as set by you");
});

await scenario("corpus: sort levels, the context search, word-type filters and the word + POS + lemma list", async () => {
  await reset();
  await page.go("#/corpus/kwic");
  const enter = el => el.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  const hits = () => +(/([\d,]+) hits?/.exec(page.text()) || [0, "0"])[1].replace(",", "");
  page.$("#main input[type=search]").value = "look";
  enter(page.$("#main input[type=search]"));
  await until(() => $$("#main .kwic .kl").length > 0, "hits for look");
  const all = hits();
  // the context search: keep hits with Watson in the three words before them, or without
  const ctx = byText("#main details.note", /Search in the context/);
  ctx.open = true;
  const ctxInput = ctx.querySelector("input[type=search]");
  const numbers = [...ctx.querySelectorAll("input[type=number]")];
  numbers[0].value = "3"; page.change(numbers[0]); numbers[1].value = "0"; page.change(numbers[1]);
  const within = ctx.querySelector("input[type=checkbox]"); within.checked = true; page.change(within);
  ctxInput.value = "watson"; page.change(ctxInput);
  await until(() => hits() > 0 && hits() < all && /with .watson. in their context/.test(page.text()), "hits narrowed by the context search");
  const kept = hits();
  const keep = ctx.querySelector("select");
  page.change(keep, "no");
  await until(() => hits() === all - kept, "the other hits when the search is inverted");
  page.change(keep, "yes");
  await until(() => hits() === kept, "back to the matching hits");
  ctx.querySelector("button").dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  await until(() => hits() === all, "clearing the context search brings every hit back");
  // sort levels: by lemma, reversed
  const by = $$("#main select").find(s => s.getAttribute("aria-label") === "Sort 1: by");
  page.change(by, "lemma");
  const arrow = () => $$("#main .controls button").find(b => /Reversed|Normal order/.test(b.title));
  await until(() => arrow() && hits() === all, "the concordance is redrawn with the lemma sort");
  page.click(arrow());
  await until(() => arrow().getAttribute("aria-pressed") === "true" && hits() === all, "a reversed lemma sort keeps all hits");
  expect(JSON.parse(w.localStorage.getItem("analyser.corp")).sort[0].by === "lemma", "the sort level is remembered");
  // the word list: three columns, and a word-class filter
  await page.go("#/corpus/wordlist");
  page.click(byText("#main .seg button", /Word \+ POS \+ lemma/));
  await until(() => $$("#main table.t2 thead th").some(t => /^POS/.test(t.textContent)) && $$("#main table.t2 thead th").some(t => /^Lemma/.test(t.textContent)), "three columns");
  const total = $$("#main table.t2 tbody tr").length;
  const filter = page.$("#main details.tfilter");
  filter.open = true;
  await until(() => byText("#main .tfilter .chip", /^VERB/), "the word classes are listed");
  page.click(byText("#main .tfilter .chip", /^VERB/));
  await until(() => /Only VERB/.test(page.text()) && $$("#main table.t2 tbody tr").length > 0 && $$("#main table.t2 tbody tr").every(r => r.children[2].textContent === "VERB"), "only verbs");
  page.click(byText("#main .tfilter .chip", /^NOUN/));
  await until(() => $$("#main table.t2 tbody tr").some(r => r.children[2].textContent === "NOUN") && $$("#main table.t2 tbody tr").every(r => ["NOUN", "VERB"].includes(r.children[2].textContent)), "verbs or nouns: several choices in one group");
  page.click(byText("#main .tfilter button", /Clear the filter/));
  await until(() => !/Only /.test(page.text()) && $$("#main table.t2 tbody tr").length === total, "the filter is cleared");
  // collocates take the same filter
  await page.go("#/corpus/collocates");
  await until(() => /for the search term/.test(page.text()), "collocates");
  const tf = page.$("#main details.tfilter");
  tf.open = true;
  await until(() => byText("#main .tfilter .chip", /^PROPN/), "word classes for collocates");
  page.click(byText("#main .tfilter .chip", /^PROPN/));
  await until(() => /only PROPN/.test(page.text()), "collocates limited to proper nouns");
});

await scenario("corpus: a batch search merges several lines into one, with a toggleable Matched column", async () => {
  await reset();
  await page.go("#/corpus/kwic");
  const hits = () => +(/([\d,]+) hits?/.exec(page.text()) || [0, "0"])[1].replace(",", "");
  const search = q => { const inp = page.$("#main input[type=search]"); inp.value = q; inp.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Enter", bubbles: true })); };
  search("said");
  await until(() => hits() > 0, "hits for said");
  const said = hits();
  search("watched");
  await until(() => hits() > 0 && hits() !== said, "hits for watched");
  const watched = hits();
  expect(!byText("#main label.inline", /Matched/), "no Matched toggle for a single-line search");
  page.click(byText("#main label.inline", /^Batch/));
  await until(() => page.$("#main textarea"), "the batch list box appears");
  page.change(page.$("#main textarea"), "said\nwatched");
  page.click(byText("#main button", /^Search$/));
  await until(() => hits() === said + watched, "the batch merges both searches into one");
  await until(() => byText("#main label.inline", /^Matched/), "a Matched toggle appears now it's a batch");
  expect($$("#main .kl-m").length === 0, "the Matched column is hidden until switched on");
  page.click(byText("#main label.inline", /^Matched/).querySelector("input"));
  await until(() => $$("#main .kl-m").length > 0, "the Matched column appears");
  expect($$("#main .kl-m").every(el => el.textContent === "said" || el.textContent === "watched"), "each hit shows which line matched it");
});

await scenario("corpus: wildcards can be turned off to search punctuation literally", async () => {
  await reset();
  await page.go("#/corpus/kwic");
  const hits = () => +(/([\d,]+) hits?/.exec(page.text()) || [0, "0"])[1].replace(",", "");
  const search = q => { const inp = page.$("#main input[type=search]"); inp.value = q; inp.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Enter", bubbles: true })); };
  page.click(byText("#main label.inline", /Ignore punctuation/).querySelector("input"));   // include punctuation in the search
  search("?");
  await until(() => hits() > 0, "“?” is the any-one-letter wildcard by default: matches one-letter words");
  page.click(byText("#main label.inline", /^Wildcards/).querySelector("input"));
  await until(() => hits() === 0, "with wildcards off, “?” is a literal character the fixture never writes");
});

await scenario("corpus: a bad query shows a message, not a crash", async () => {
  await reset();
  await page.go("#/corpus/kwic");
  page.click(byText("#main .seg button", /Pattern/));
  await page.settle();
  const q = page.$("#main input[type=search]");
  q.value = '[lemma="say"';
  q.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  await sleep(600);
  expect(/no matching/.test(page.$("#toast").textContent) && !page.$("#toast").hidden, "error toast shown");
  expect(/no matching/.test(page.$("#main .warn").textContent) && !page.$("#main .loading"), "the message replaces the Searching… line");
  page.$("#toast").hidden = true;
  q.value = ""; page.eval("S.corp.query = ''; S.corp.mode = 'simple'; saveCorp()");
});

await scenario("arcs, style and stylometry controls", async () => {
  await reset();
  // characters of one book: a gap in the other books, and the book beside a name that is chosen twice (AD-43)
  await page.eval(`S.nar.arcKind = "entities"; S.nar.ids = ["e:alpha:1", "e:beta:5"]; S.nar.seg = { ...S.nar.seg, mode: "slices", slice_by: "count", n: 10, scope: "book" }`);
  await page.go("#/narrative/arcs");
  await until(() => page.$("#main svg[role=img] polyline") && $$("#main .tag").length === 2, "two Holmeses drawn");
  expect($$("#main .tag").map(t => t.textContent.replace("×", "").trim()).join("|") === "PER Holmes (alpha)|PER Holmes (beta)", "the chips name each one's book: " + $$("#main .tag").map(t => t.textContent).join("|"));
  expect($$("#main svg[role=img] text").some(t => t.textContent === "Holmes (alpha)") && $$("#main svg[role=img] polyline").length === 2, "so does the legend; one line each, in its own book only");
  page.click(byText("#main .seg button", /Dialogue/));
  await until(() => page.$("#main svg[role=img]"), "dialogue arc");
  const corpusBtn = byText("#main .seg button", /Whole corpus/);
  expect(corpusBtn, "the Timeline scope toggle shows with several books selected");
  page.click(corpusBtn);
  await until(() => page.eval("S.nar.seg.scope") === "corpus", "scope switched to corpus");
  await page.settle();
  expect(page.$("#main svg[role=img] polyline"), "a line is drawn across the whole corpus");
  // Books combined: the books put together slice by slice, each book weighing the same; each book's own line faint behind (AD-45)
  page.click(byText("#main .seg button", /^Books combined$/));
  await until(() => page.eval("S.nar.seg.scope") === "combined" && $$("#main svg[role=img] text").some(t => t.textContent === "All selected books"), "one combined arc for all the books");
  expect($$("#main svg[role=img] polyline").length === 1, "one line: the books' mean");
  page.click(byText("#main label", /Show each book/).querySelector("input"));
  await until(() => $$("#main svg[role=img] polyline").length === 4 && page.eval("S.nar.each.arcs"), "each book's own line, faint, behind it");
  page.click(byText("#main label", /Show each book/).querySelector("input"));
  await until(() => !page.eval("S.nar.each.arcs"), "the tick off again");
  page.click(byText("#main .seg button", /Book by book/));
  await until(() => page.eval("S.nar.seg.scope") === "book", "scope back to book by book");
  page.click(byText("#main .seg button", /Chapters/));
  await page.settle();
  page.click(byText("#main .seg button", /Equal slices/));
  const sliceBy = $$("#main select").find(s => [...s.options].some(o => /Words per slice/.test(o.textContent)));
  expect(sliceBy, "slices can be cut by number or by words");
  page.change(sliceBy, "words");
  await until(() => page.eval("S.nar.seg.slice_by") === "words" && byText("#main label", /^Words per slice/), "a words-per-slice field replaces the slice count");
  expect(!byText("#main label", /^Slices per book/), "and the slice count is gone");
  page.change(byText("#main label", /^Words per slice/).querySelector("input"), "100");
  await until(() => page.eval("S.nar.seg.words") === 100, "the words per slice are kept");
  const cut = (await api(base, "/api/narrative/segments", { books: ALL, seg: page.eval("S.nar.seg") })).segments.filter(sg => sg.book === "alpha");
  expect(cut.length > 1 && cut.slice(0, -1).every(sg => sg.words === 100), "the server cuts every 100th word");
  page.change(byText("#main label", /^Slices by/).querySelector("select"), "count");
  await until(() => byText("#main label", /^Slices per book/), "back to a number of slices");
  page.click(byText("#main .seg button", /Characters and places/));
  await until(() => $$("#main .tag").length > 0, "chosen entities");
  await page.go("#/narrative/style");
  page.click(byText("#main .seg button", /^Slice$|^Chapter$/));
  await until(() => /Segment/.test(page.text()), "style per segment");
  const picker = async re => { await until(() => byText("#main label", re), "the " + re + " control"); return byText("#main label", re).querySelector("select"); };     // the page draws again after each change
  await until(() => [...$$("#main th")].some(t => /^Adjectives per verb/.test(t.textContent)), "the word-choice table with its key figures");
  page.change(await picker(/^Show/), "ratios");
  await until(() => page.eval("S.nar.wcChoice") === "ratios" && [...$$("#main th")].some(t => /^Modifiers per head/.test(t.textContent)), "a section replaces them, and is remembered");
  page.change(await picker(/^Chart/), "wc:verbs:dynamic");
  await until(() => page.eval("S.nar.styleMetric") === "wc:verbs:dynamic" && /Dynamic verbs/.test((page.$("#main svg") || {}).textContent || ""), "the chart draws a word-choice figure");
  page.change(await picker(/^Show/), "headline");
  await until(() => page.eval("S.nar.wcChoice") === "headline", "back to the key figures");
  page.change(await picker(/^Chart/), "sent_len");
  await until(() => page.eval("S.nar.styleMetric") === "sent_len", "and the first chart");
  expect(!byText("#main h3", /^Sound and rhythm$/) && !$$("#main option").some(o => o.value.startsWith("snd:")), "no sound and rhythm on the Style page: it has its own tab (AD-39)");
  await page.go("#/narrative/stylometry");
  const measure = $$("#main select").find(s => [...s.options].some(o => /Euclidean/.test(o.textContent)));
  page.change(measure, "euclidean");
  await until(() => page.$("#main .stylo-charts .chart-box svg") && !page.$("#main .loading"), "stylometry redrawn");
  const panels = () => $$("#main section.panel > h2").map(x => x.textContent.trim());
  expect(panels().join("|") === "Compare|Cluster tree and map|Nearest texts and distances", "what is compared, the charts, the tables (AD-38): " + panels().join("|"));
  const chartsPanel = byText("#main section.panel > h2", /^Cluster tree and map$/).closest("section");
  expect(byText("#main label", /^Colour by/).closest("section") === chartsPanel && chartsPanel.querySelector(".stylo-charts .chart-box svg"), "Colour by sits with the charts it colours");
  page.click(byText("#main .seg button", /^Chapters or slices$/));
  await until(() => byText("#main label", /^Slices by/) && byText("#main label", /^Slices by/).closest("section") === byText("#main section.panel > h2", /^Compare$/).closest("section"), "chapters or slices: the slicer joins the Compare panel");
  page.click(byText("#main .seg button", /^Whole books$/));
  await until(() => /Each selected book is one text/.test(page.text()), "and back to whole books");
});

await scenario("the text view: layers, paging, side panels", async () => {
  await reset();
  await page.go("#/read/alpha");
  await until(() => $$("#main .para").length > 0, "paragraphs");
  page.click($$("#main .read-text mark.q")[0]);
  await until(() => /Quote/.test(page.$(".read-side").textContent) && page.$(".read-side .qedit"), "quote panel");
  page.click($$("#main .read-text mark.e.in")[0]);
  await until(() => page.$(".read-side a[href^='#/entities/']"), "entity panel, linking into a profile");
  const pron = $$("#main .read-text mark.e.in.PRON").find(m => m.textContent === "He");
  expect(pron, "a pronoun mention of Holmes to click");
  page.click(pron);
  await until(() => /Attributed to/.test(page.$(".read-side").textContent) && byText("#main .read-side a", /^Holmes$/), "the pronoun's own entity, not just its literal text");
  page.click(byText("#main .chips .chip", /Events/));
  await until(() => $$("#main .read-text mark.ev").length > 0, "events layer");
  page.click(byText("#main .chips .chip", /Events/));
  await page.settle();
  if (page.eval("S.lib.sound")) {                              // the sound layer (the pronunciation dictionary is optional)
    page.click(byText("#main .chips .chip", /Sound and rhythm/));
    await until(() => $$("#main .read-text mark.sw").length > 20 && $$("#main .read-text mark.sw")[0].dataset.id, "every word with its stresses");
    await until(() => $$("#main .read-text mark.sw.sr").every(m => m.style.getPropertyValue("--c") && /alliteration: /.test(m.title)), "runs coloured and named");
    page.change(byText("#main label", /Colour the runs of/).querySelector("select"), "repetition");
    await until(() => page.eval("S.read.soundColour") === "repetition" && $$("#main .read-text mark.sw.sr").every(m => /repetition: /.test(m.title)), "repetitions coloured instead");
    page.change(byText("#main label", /Colour the runs of/).querySelector("select"), "alliteration");
    await until(() => page.eval("S.read.soundColour") === "alliteration" && $$("#main .read-text mark.sw.sr").length > 0, "alliteration again");
    const coloured = $$("#main .read-text mark.sw.sr").length, wasWindow = page.eval("S.lib.settings.sound.window");
    page.change(page.$(".read-bar input[aria-label='Run window (content words)']"), "1");
    await until(() => page.eval("S.lib.settings.sound.window") === 1 && $$("#main .read-text mark.sw.sr").length < coloured, "a narrower window marks the text again");
    page.change(page.$(".read-bar input[aria-label='Run window (content words)']"), String(wasWindow));
    await until(() => page.eval("S.lib.settings.sound.window") === wasWindow && $$("#main .read-text mark.sw.sr").length > 0, "and back (the view loads chapters as it scrolls, so not the same count)");
    page.click(byText("#main .chips .chip", /Sound and rhythm/));
    await until(() => $$("#main .read-text mark.sw").length === 0, "and off again");
  }
  const before = page.eval("S.read.index");
  page.click(button(/Next/));
  await until(() => page.eval("S.read.index") === before + 1 || /#\/read\//.test(w.location.hash), "next segment");
  page.click(byText("#main .chips .chip", /^Topics$/));
  await until(() => /No topic model includes this book/.test(page.text()), "message when there is no model");
  page.click(byText("#main .chips .chip", /^Topics$/));
  await page.settle();
});

await scenario("topics: fit a model, open a topic, the relevance slider, comparing", async () => {
  await reset();
  for (const m of (await api(base, "/api/topics/models")).models) await api(base, "/api/topics/delete", { id: m.id });
  await page.go("#/topics");
  page.eval("S.top.cfg = Object.assign({}, S.lib.topic_defaults, {chunk_words: 60, k: 4, min_df: 2, runs: 2}); saveTop(); render()");
  await page.settle();
  // the settings most fits leave alone are folded under a summary of their values, a changed one tinted (AD-46)
  const fine = () => page.$("#main details.topic-fine");
  expect(fine() && !fine().open && /^Fine-tuning: min\. 2 documents/.test(fine().querySelector("summary").textContent), "fine-tuning folded, its values named: " + (fine() && fine().querySelector("summary").textContent));
  expect([...fine().querySelectorAll("summary .bo.set")].map(x => x.textContent).join("|") === "min. 2 documents|2 runs", "the values changed from the defaults are tinted");
  expect(!byText("#main section.panel > h2", /^Topics$/) && /^Topics: groups of words/.test(page.$("#main .svtop").textContent), "the intro is a quiet line, not a panel");
  page.click(button(/^Compare$/));
  await until(() => /Coherence/.test(page.text()) && $$("#main table.t2").length > 0, "numbers of topics compared");
  page.click(button(/Fit model/));
  await until(() => /#\/topics\/[a-z0-9-]+$/.test(w.location.hash), "opened the fitted model", 60000);
  await page.settle();
  expect($$("#main section.panel[id^=topic-]").length === 4, "four topic cards");
  page.click($$("#main table.t2 tbody a")[0]);
  await until(() => /#\/topics\/[a-z0-9-]+\/\d+$/.test(w.location.hash) && page.$("#sec-entities .content table"), "topic page filled", 30000);
  const slider = page.$("#sec-words input[type=range]");
  const first = () => page.$("#sec-words tbody tr td").textContent;
  const before = first();
  page.input(slider, "0");
  page.input(slider, "1");
  expect(first().length > 0 && before.length > 0, "words listed at both ends of the slider");
  await until(() => page.$(".tp-toc a.on"), "side menu highlights a section");
  page.click(page.$(".tp-toc .toc-fold"));
  expect(page.$("#main").classList.contains("toc-closed") && JSON.parse(w.localStorage.getItem("analyser.tocClosed")).topics === 1, "topic menu folded and remembered");
  page.click(page.$(".tp-toc .toc-fold"));
  expect(!page.$("#main").classList.contains("toc-closed"), "topic menu open again");
  page.click(page.$("#sec-words .cx"));
  expect(page.$("#sec-words").classList.contains("collapsed"), "section collapsed");
  page.click(page.$("#sec-words .cx"));
  const pick = page.$(".tp-toc select");
  page.change(pick, pick.options[1].value);
  await until(() => /compare\/pair\//.test(w.location.hash) && /Only in/.test(page.text()), "pair comparison", 30000);
  await page.go(w.location.hash.replace(/compare\/pair.*/, "compare/grid"));
  page.click(byText("#main .seg button", /Topic × character/));
  await until(() => $$("#main .heat tbody tr").length > 0, "character grid");
  for (const m of (await api(base, "/api/topics/models")).models) await api(base, "/api/topics/delete", { id: m.id });
});

await scenario("collapsing sections and the side menu on an entity page", async () => {
  await reset();
  const holmes = (await api(base, "/api/units", { books: ALL })).rows.find(u => u.name === "Holmes" && u.books[0] === "alpha").id;
  await page.go("#/entities/" + encodeURIComponent(holmes));
  await until(() => page.$(".page-toc") && page.$$ && $$("#main .cx").length >= 5, "menu and arrows", 15000);
  const panel = byText("#main section.panel > h2", /Book by book|Speech/).parentElement;
  page.click(panel.querySelector(".cx"));
  expect(panel.classList.contains("collapsed") && JSON.stringify(w.localStorage.getItem("analyser.collapsed")).length > 4, "collapsed and remembered");
  const link = $$(".page-toc a").find(a => a.dataset.target === panel.id);
  expect(link.classList.contains("collapsed"), "menu entry marked");
  page.click(byText(".page-toc-tools button", /Expand all/));
  expect(!panel.classList.contains("collapsed"), "expand all");
  page.click(byText(".page-toc-tools button", /Collapse all/));
  expect($$("#main section.panel.cx-panel").every(p => p.classList.contains("collapsed")), "collapse all");
  page.click(byText(".page-toc-tools button", /Expand all/));
  page.click(page.$(".page-toc .toc-fold"));
  expect(page.$("#main").classList.contains("toc-closed") && page.$(".page-toc .toc-fold").getAttribute("aria-expanded") === "false", "menu folded to a rail");
  await page.go("#/dialogue");
  await until(() => page.$(".page-toc"), "dialogue menu");
  expect(!page.$("#main").classList.contains("toc-closed"), "the fold is remembered per page: Dialogue's menu stays open");
  await page.go("#/entities/" + encodeURIComponent(holmes));
  await until(() => page.$(".page-toc") && page.$("#main").classList.contains("toc-closed"), "the entity menu is still folded after coming back");
  page.click(page.$(".page-toc .toc-fold"));
  expect(!page.$("#main").classList.contains("toc-closed"), "menu open again");
});

await scenario("books: collections nest and hold books, search narrows the table, the pop-up filters by collection", async () => {
  await reset();
  await page.go("#/books");
  const rowsShown = () => $$("#main .bookcard").length;
  const node = re => byText("#main .collnav button", re);
  const nameIt = name => { const box = page.$("#main .navfoot input[type=text]"); box.value = name; page.click(byText("#main .navfoot button", /^OK$/)); };
  expect(rowsShown() === 3 && node(/All books/) && node(/In no collection/), "all three books, and the two fixed tree entries");
  // make a collection, then a sub-collection inside it
  page.click(button(/^New collection$/)); nameIt("Holmes");
  await until(() => page.eval("S.lib.collections.length") === 1, "collection made");
  page.click(node(/^Holmes/));
  page.click(button(/^New sub-collection$/)); nameIt("Novels");
  await until(() => page.eval("S.lib.collections.length") === 2, "sub-collection made");
  expect((await api(base, "/api/library")).collections[1].parent === (await api(base, "/api/library")).collections[0].id, "the second collection is inside the first");
  // put a book in Novels (a sub-collection), through the row's ＋ menu (in the list of all books: an empty collection lists nothing)
  page.click(node(/All books/));
  const novels = page.eval("S.lib.collections.find(c => c.name === 'Novels').id");
  const add = $$("#main .bookcard select").find(s => s.getAttribute("aria-label") === "Add alpha to a collection");
  expect(add, "a ＋ menu on the first book");
  page.change(add, novels);
  await until(() => page.eval("S.lib.collections.find(c => c.name === 'Novels').books.length") === 1, "book added");
  // the parent lists it too, the fixed entry no longer does
  page.click(node(/^Holmes/));
  expect(rowsShown() === 1, "the parent collection lists the book of its sub-collection");
  page.click(node(/In no collection/));
  expect(rowsShown() === 2, "the other two books are in no collection");
  // search
  page.click(node(/All books/));
  const search = page.$("#main .libtools input[type=search]");
  page.input(search, "hound");
  await sleep(300);
  expect(rowsShown() === 0, "a search that matches nothing lists nothing");
  page.input(search, "alpha");
  await until(() => rowsShown() === 1, "search by id finds one book");
  // the analysis selection follows the table
  page.click(button(/Analyse the 1 book shown/));
  expect(JSON.stringify(page.eval("S.sel")) === JSON.stringify(["alpha"]), "selection is the shown book");
  // the pop-up filters by collection
  openBooks();
  const popColl = $$("#selPop select").find(s => [...s.options].some(o => o.textContent === "Novels"));
  expect(popColl, "the pop-up has a collection filter");
  page.change(popColl, novels);
  expect($$("#selPop label.book").length === 1, "only the book in that collection is listed");
  page.click(byText("#selPop button", /^Cancel$/));
  // deleting a collection keeps the books and moves the sub-collection up
  page.click(node(/^Holmes/));
  page.click(button(/^Delete$/));
  await until(() => page.eval("S.lib.collections.length") === 1, "collection deleted");
  expect((await api(base, "/api/library")).collections[0].parent === null && page.eval("S.lib.books.length") === 3, "the child moved up and no book was lost");
});

await scenario("selecting books from the pop-up", async () => {
  await reset();
  await page.go("#/entities");
  openBooks();
  expect(!page.$("#selPop").hidden, "the Books flyout is open");
  const boxes = $$("#selPop input[type=checkbox]");
  boxes.forEach(b => { b.checked = false; page.change(b); });
  boxes[0].checked = true; page.change(boxes[0]);
  page.click(byText("#selPop button", /Use these books/));
  await until(() => JSON.stringify(page.eval("S.sel")) === JSON.stringify(["alpha"]), "selection changed");
  await page.settle();
  expect(/1 of 3 books/.test(page.$("#viewTip").textContent), "the book button's tooltip counts them");
  expect(JSON.parse(w.localStorage.getItem("analyser.sel")).length === 1, "selection remembered");
});

await scenario("network: a minimum range for entities and for links", async () => {
  await reset();
  w.localStorage.setItem("analyser.net", JSON.stringify({ kind: "sentence", types: ["PER"], min_weight: 1, keep_isolated: false, color: "type", size: "strength", labels: "0" }));
  await page.eval("S.net = loadState('analyser.net', {})");
  await page.go("#/network");
  await until(() => $$(".net-canvas svg circle").length > 2, "network drawn");
  const filters = byText("#main section.panel > h2", /^Which entities and links$/).closest("section"), drawRow = page.$("#main .net-draw");
  expect(filters.contains(byText("#main label", /^Show at most/)) && drawRow && drawRow.contains(byText("#main label", /^Colour by/)) && !filters.contains(drawRow), "what goes in is one panel; how it's drawn is a row of its own (AD-40)");
  expect(drawRow.compareDocumentPosition(page.$("#main .net-canvas")) & 4, "the drawing row sits right above the network");
  expect(page.$("#main .net .chart-tools .dl") && /^SVG · PNG · GEXF · GraphML$/.test(page.$("#main .net .chart-tools").textContent) && !byText("#main .btn", /^GEXF$/), "the downloads are quiet links");
  expect(page.$("#main .net .chart-tools").compareDocumentPosition(page.$("#main .net-canvas")) & 4, "above the network, not under it (AD-41)");
  expect(page.$("#main details.tfold:not([open]) table") && /^Every link and its weight/.test(page.$("#main details.tfold summary").textContent), "the links table is folded");
  // the circular layout, as in Gephi: every circle at the same distance from the middle, in the order chosen
  page.change(byText("#main label", /^Layout/).querySelector("select"), "circle");
  await until(() => byText("#main label", /^Order by/) && page.eval("S.net.layout") === "circle", "Circle, with an order to choose");
  const dists = $$(".net-canvas svg circle").map(c => Math.hypot(+c.getAttribute("cx") - 500, +c.getAttribute("cy") - 320));
  expect(dists.length > 2 && dists.every(d => Math.abs(d - dists[0]) < 0.01), "every circle on one circle: " + dists.map(d => d.toFixed(1)).join(", "));
  page.change(byText("#main label", /^Order by/).querySelector("select"), "name");
  const angle = c => (Math.atan2(+c.getAttribute("cy") - 320, +c.getAttribute("cx") - 500) + Math.PI / 2 + 2 * Math.PI) % (2 * Math.PI);   // clockwise from the top
  const names = $$(".net-canvas svg circle").sort((a, b) => angle(a) - angle(b)).map(c => c.querySelector("title").textContent.split(" (")[0]);
  expect(page.eval("S.net.order") === "name" && names.join() === [...names].sort((a, b) => a.localeCompare(b)).join(), "ordered by name: " + names.join(", "));
  page.change(byText("#main label", /^Layout/).querySelector("select"), "force");
  await until(() => page.eval("S.net.layout") === "force" && !byText("#main label", /^Order by/), "back to force-directed");
  const before = $$(".net-canvas svg circle").length, labels = $$("#main .controls label").map(l => l.textContent.trim());
  expect(labels.indexOf("Minimum range per link") === labels.indexOf("Minimum link strength") + 1 && labels.includes("Minimum range per entity"), "the two minimums sit beside the link strength: " + labels.join("|"));
  const input = re => byText("#main .controls label", re).querySelector("input");
  page.change(input(/^Minimum range per link$/), "2");                       // no pair is linked in two books when nobody is linked across books
  await until(() => page.eval("S.net.min_link_range") === 2 && $$(".net-canvas svg circle").length === 0, "no link is in two books: nothing is drawn");
  page.change(input(/^Minimum range per link$/), "1");
  await until(() => $$(".net-canvas svg circle").length === before, "back to one: the network is back");
  page.change(input(/^Minimum range per entity$/), "2");
  await until(() => page.eval("S.net.min_range") === 2 && $$(".net-canvas svg circle").length === 0, "no entity is in two books: nothing is drawn");
  expect(JSON.parse(w.localStorage.getItem("analyser.net")).min_range === 2, "remembered");
  page.change(input(/^Minimum range per entity$/), "1");
  await until(() => $$(".net-canvas svg circle").length === before, "and back");
});

await scenario("network: a click pins the focus, empty space releases it, and a hidden name shows while hovered or pinned", async () => {
  await reset();
  w.localStorage.setItem("analyser.net", JSON.stringify({ kind: "sentence", types: ["PER"], min_weight: 1, keep_isolated: false, color: "type", size: "strength", labels: "0" }));
  await page.eval("S.net = loadState('analyser.net', {})");
  await page.go("#/network");
  await until(() => $$(".net-canvas svg circle").length > 2, "network drawn");
  const circle = i => $$(".net-canvas svg circle")[i];
  const label = i => $$(".net-canvas svg text")[i].getAttribute("visibility");
  const mouse = (el, type) => el.dispatchEvent(new w.MouseEvent(type, { bubbles: false }));
  expect(label(0) === "hidden", "with labels off, names are hidden");
  mouse(circle(0), "mouseenter");
  expect(label(0) === "visible", "hovering shows the name");
  mouse(circle(0), "mouseleave");
  expect(label(0) === "hidden", "the name hides again");
  page.click(circle(0));
  mouse(circle(0), "mouseleave");
  expect(label(0) === "visible" && circle(0).getAttribute("stroke") === "#1d2a2e", "a click pins the focus: the name and outline stay");
  expect(/Linked to/.test(page.$(".net-side").textContent), "the side panel shows the pinned entity");
  page.click(page.$(".net-canvas svg"));
  expect(label(0) === "hidden" && circle(0).getAttribute("stroke") === "#ffffff", "clicking empty space releases the focus");
  expect(/release it/.test(page.$(".net-side").textContent), "the side panel goes back to its hint");
});

await scenario("text view: the entity legend switches a type's underlines off and on", async () => {
  await reset();
  await page.go("#/read/alpha");
  const legend = t => $$("#main .legend button").find(b => b.textContent === t);
  const text = () => page.$("#main .read-text");
  expect(legend("PER") && legend("LOC"), "the legend has a button per type");
  page.click(legend("PER"));
  expect(text().classList.contains("hide-PER") && legend("PER").classList.contains("off"), "PER is hidden");
  expect(JSON.parse(w.localStorage.getItem("analyser.read")).hidden.includes("PER"), "the choice is remembered");
  await page.go("#/read/alpha");
  expect(text().classList.contains("hide-PER"), "still hidden after the page is drawn again");
  page.click(legend("PER"));
  expect(!text().classList.contains("hide-PER"), "PER is back");
});

await scenario("entities: narrators have profiles; entities can be ticked, analysed together, saved as a group and reopened", async () => {
  await reset();
  const rows = (await api(base, "/api/units", { books: ALL })).rows;
  const watson = rows.find(r => r.name === "Watson" && r.books[0] === "alpha").id;
  await api(base, "/api/annot/narrator", { book: "alpha", narrator: watson });
  await page.eval("S.units = null");
  await page.go("#/entities");
  // narrators
  page.click(byText("#main .chip", /^Narrators/));
  await until(() => $$("#main .ent-item .nm").some(n => /Watson, narrating/.test(n.textContent)), "the narrating Watson is listed");
  expect($$("#main .ent-item .nm").some(n => /Narrator of/.test(n.textContent)), "unnamed narrators are listed too");
  expect(!page.$("#main .multi-bar input[type=checkbox]"), "narrator roles can't be grouped, so there is no select-several switch");
  page.click($$("#main .ent-item").find(e => /Watson, narrating/.test(e.textContent)));
  await until(() => /Where they narrate/.test(page.text()) && /What's distinctive/.test(page.text()) && $$("#main table.t2 tbody tr").length > 3, "narrator profile");
  expect(/Watson, narrating/.test(page.$("#main h1").textContent) && byText("#main a", /Watson's own profile/), "title and a link to the character");
  // select several
  page.click(byText("#main .chip", /^PER/));
  await until(() => w.location.hash === "#/entities" && page.$("#main .multi-bar input[type=checkbox]"), "back to the list of people");
  const multi = page.$("#main .multi-bar input[type=checkbox]");
  multi.checked = true; page.change(multi);
  await until(() => $$("#main .ent-item.multi").length > 2, "rows get checkboxes");
  page.click($$("#main .ent-item")[0]); page.click($$("#main .ent-item")[1]);
  await until(() => /2 entities selected/.test(page.$("#main .multi-bar").textContent), "two ticked");
  const [a, b] = page.eval("S.entSel").map(id => rows.find(r => r.id === id));
  page.click(byText("#main .multi-bar button", /Analyse together/));
  await until(() => /#\/entities\/group/.test(w.location.hash) && $$("#main .phead .gtag").length === 2 && /Where these come from/.test(page.text()), "group profile", 15000);
  const fact = label => (byText("#main .phead .facts div", new RegExp(label)) || {}).textContent || "";
  expect(fact("Mentions").startsWith(fmtNum(a.mentions + b.mentions)) && /^2/.test(fact("Entities")), "the group's mentions are the two entities' added together");
  expect($$("#main .phead .gtag").every(t => /^(PER)/.test(t.textContent)), "members are shown as tags with their type");
  // remove one with its ×, and tick it again
  page.click($$("#main .phead .gtag button")[0]);
  await until(() => $$("#main .phead .gtag").length === 1 && page.eval("S.entSel.length") === 1, "one member taken out");
  page.click($$("#main .ent-item").find(e => e.textContent.includes(a.name) || e.textContent.includes(b.name)) || $$("#main .ent-item")[0]);
  await until(() => $$("#main .phead .gtag").length === 2, "and ticked again");
  // save, reopen, change, update, delete
  page.click(byText("#main .phead button", /Save as a group/));
  page.$("#main .phead input[type=text]").value = "Duo";
  page.click(byText("#main .phead button", /^OK$/));
  await until(() => /#\/entities\/g:/.test(w.location.hash) && /Duo/.test(page.$("#main h1").textContent), "saved group opened");
  expect((await api(base, "/api/library")).groups.length === 1 && byText("#main .multi-bar option", /Duo/), "the group is saved and listed");
  page.click($$("#main .phead .gtag button")[0]);
  await until(() => /Update “Duo”/.test(page.text()) && $$("#main .phead .gtag").length === 1, "changed ticks are offered as an update");
  page.click(byText("#main .phead button", /Update “Duo”/));
  await until(() => page.eval("S.lib.groups[0].ids.length") === 1, "saved group updated");
  await until(() => byText("#main .phead button", /Delete group/), "back to a plain saved group");
  await page.settle("the saved group's page");          // its panels are still asking about the group: deleting it now would make their requests fail
  page.click(byText("#main .phead button", /Delete group/));
  await until(() => page.eval("S.lib.groups.length") === 0 && !/g:/.test(w.location.hash), "group deleted");
});

await scenario("entities: linking narrator roles pools their narration, and unlinking splits them apart", async () => {
  await reset();
  await page.go("#/entities");
  page.click(byText("#main .chip", /^Narrators/));
  const items = () => $$("#main .ent-item");
  await until(() => items().some(e => /narrating/.test(e.textContent)), "narrator rows shown, not still the people list");
  const before = items().length;
  const find = re => items().find(e => re.test(e.textContent));
  expect(find(/Narrator of beta/) && find(/Narrator of gamma/), "beta and gamma each have an anonymous narrator by default");
  page.click(find(/Narrator of beta/));
  await until(() => /Narrated alone so far/.test(page.text()), "not linked yet");
  const linkRow = () => byText("#main .row", /Link with another narrator/);
  await until(() => linkRow().querySelector("select").options.length > 1, "narrator options loaded");
  const sel = linkRow().querySelector("select");
  const gammaOpt = [...sel.options].find(o => /Narrator of gamma/.test(o.textContent));
  expect(gammaOpt, "gamma's narrator is offered to link with");
  page.change(sel, gammaOpt.value);
  page.click(linkRow().querySelector("button"));
  await until(() => /nl%3A/.test(w.location.hash), "the page follows the fresh linked id");
  await until(() => /Linked narrators/.test(page.text()), "linked narrators page");
  expect(/Narrator of beta/.test(page.text()) && /Narrator of gamma/.test(page.text()), "both members shown, each with their own share");
  await until(() => items().length === before - 1, "the list has one fewer row: the two merged into one");
  // unlink one: a link of just two dissolves, and the page follows the member that's left
  const unlinkBeta = page.$('#main button.linkbtn[title="Unlink Narrator of beta"]');
  expect(unlinkBeta, "an unlink button for beta");
  page.click(unlinkBeta);
  await until(() => /Narrator of gamma/.test((page.$("#main h1") || {}).textContent || ""), "back to gamma's own narrator page");
  expect(/Narrated alone so far/.test(page.text()), "no longer linked");
  await until(() => items().length === before, "the list is back to its original count");
});

await scenario("compare: a group is picked by search, shown as removable tags outside the list, and compared", async () => {
  await reset();
  const rows = (await api(base, "/api/units", { books: ALL })).rows;
  const place = rows.find(r => r.type === "LOC");
  await page.go("#/compare");
  const pick = async (box, text) => {
    const inp = box.querySelector("input[type=search]");
    page.input(inp, text);
    await until(() => box.querySelector(".sugg div"), "suggestions for " + text);
    box.querySelector(".sugg div").dispatchEvent(new w.MouseEvent("mousedown", { bubbles: true, cancelable: true }));
  };
  const first = () => $$("#main .picker")[0], second = () => $$("#main .picker")[1];
  page.click([...first().querySelectorAll(".seg button")].find(b => /^Group$/.test(b.textContent)));
  await pick(first().querySelector(".gpick"), "holmes");
  await pick(first().querySelector(".gpick"), "watson");
  await until(() => first().querySelectorAll(".gbox .gtag").length === 2, "two entities shown as tags");
  await pick(second(), place.name.toLowerCase().slice(0, 5));
  await until(() => /Overview/.test(page.text()) && byText("#main table.t2 tbody tr", /^Entities/), "comparison drawn");
  const entitiesRow = () => byText("#main table.t2 tbody tr", /^Entities/).textContent;
  expect(/^Entities2/.test(entitiesRow()), "the group has two entities");
  page.click(first().querySelector(".gbox .gtag button"));
  await until(() => first().querySelectorAll(".gbox .gtag").length === 1 && /^Entities1/.test(entitiesRow()), "removing a tag updates the comparison");
});

await scenario("pickers: a type drop-down narrows the entity list, and the Type mode picks every entity of the ticked types", async () => {
  await reset();
  const rows = (await api(base, "/api/units", { books: ALL })).rows;
  const TYPE_ORDER = ["PER", "LOC", "FAC", "GPE", "VEH", "ORG", "VAR"];
  const types = TYPE_ORDER.filter(t => rows.some(r => r.type === t));
  expect(types.length >= 2, "the test books have at least two entity types");
  await page.go("#/compare");
  const first = () => $$("#main .picker")[0], second = () => $$("#main .picker")[1];
  const setMode = (box, label) => page.click([...box.querySelectorAll(".seg button")].find(b => new RegExp(`^${label}$`).test(b.textContent)));

  await until(() => /Overview/.test(page.text()), "the page is drawn with the comparison remembered from before");
  page.input(first().querySelector("input[type=search]"), "");                         // the box starts with the remembered entity's name
  const typeSel = first().querySelector("select[aria-label='Only entities of this type']");
  page.change(typeSel, "LOC");
  const shown = () => [...first().querySelectorAll(".sugg div .t")].map(t => t.textContent);
  await until(() => shown().length > 0 && shown().every(t => t === "LOC"), "only entities of the chosen type are listed");

  setMode(second(), "Type");
  await until(() => second().querySelectorAll("button.btn").length === types.length, "one toggle per type present");
  const toggle = t => page.click([...second().querySelectorAll("button.btn")].find(b => b.textContent.startsWith(t + " (")));
  toggle(types[0]);
  await until(() => second().querySelector("button.primary"), "a ticked type is highlighted");
  toggle(types[1]);
  const name = "all " + types.slice(0, 2).join(" + ");
  await until(() => new RegExp(name.replace(/\+/g, "\\+")).test(page.text()), "the comparison names the ticked types: " + name);
  toggle(types[0]); toggle(types[1]);
  await until(() => !second().querySelector("button.primary"), "unticking everything leaves nothing ticked");
});

await scenario("compare: two books split into characters, only while both sides are books", async () => {
  await reset();
  await page.go("#/compare");
  const first = () => $$("#main .picker")[0], second = () => $$("#main .picker")[1];
  const setMode = (box, label) => page.click([...box.querySelectorAll(".seg button")].find(b => new RegExp(`^${label}$`).test(b.textContent)));
  setMode(first(), "Book");
  await until(() => first().querySelector("select"), "a book select appears");
  page.change(first().querySelector("select"), "alpha");
  setMode(second(), "Book");
  await until(() => second().querySelector("select"), "the second book select appears");
  page.change(second().querySelector("select"), "beta");
  await until(() => byText("#main h2", /Split into characters/), "the split grid appears for two books");
  const grid = byText("#main h2", /Split into characters/).parentElement;
  const heads = [...grid.querySelectorAll("th")].map(th => th.textContent);
  expect(heads.some(t => /alpha/.test(t)) && heads.some(t => /beta/.test(t)), "one column per book");
  expect([...grid.querySelectorAll("td a")].find(a => /Holmes/.test(a.textContent)), "a character links to its own profile");
  setMode(second(), "Gender");                          // switching one side away from a book: the split grid goes
  await until(() => !byText("#main h2", /Split into characters/), "no split grid once a side isn't a book");
});

await scenario("entities: a book's and a gender's own overview pages pool every entity in them", async () => {
  await reset();
  await page.go("#/books");
  const overview = page.$("#main .bookcard a.bn");
  expect(overview, "a book card links to the book's own overview");
  page.click(overview);
  await until(() => /#\/entities\/book/.test(w.location.hash) && /Book overview/.test(page.text()), "the book's overview page");
  const heads = () => [...$$("#main h2")].map(h => h.textContent);
  expect(heads().includes("Entities in this book") && heads().includes("What they do and what's done to them"), "the pooled profile sections");
  expect(!heads().includes("Speech") && !heads().includes("Topics"), "speech and topics are left out (they need an id/ids ref a pool doesn't have)");

  await page.go("#/entities");
  page.click(byText("#main .chip", /^Gender/));
  await until(() => $$("#main .ent-item").some(e => /he\/him\/his/.test(e.textContent)), "gender buckets listed");
  page.click($$("#main .ent-item").find(e => /he\/him\/his/.test(e.textContent)));
  await until(() => /Gender overview/.test(page.text()) && heads().includes("Entities of this gender"), "the gender's overview page");
});

await scenario("text view: the book scrolls chapter after chapter with numbers in the margin; sentence numbers; jumping", async () => {
  await reset();
  await page.eval("S.nar.seg = { mode: 'chapters', n: 10, rules: { numbered: true, caps: true, short: false }, min_words: 50 }");
  await page.go("#/read/alpha");
  await until(() => $$("#main .chap").length === 1 && $$("#main .pwrap .pno").length > 2, "the first chapter and its paragraph numbers");
  const nums = () => $$("#main .pno").map(e => +e.textContent);
  const firstNums = nums();
  expect(firstNums[0] === 1 && firstNums.every((n, i) => i === 0 || n === firstNums[i - 1] + 1), "paragraphs are numbered from 1, one after another");
  expect(/^1\. /.test(page.$("#main .seg-head").textContent) && page.$("#main .read-where select"), "a heading per chapter and a jump menu");
  const more = () => byText("#main button.more", /Load the next/);
  page.click(more());
  await until(() => $$("#main .chap").length === 2, "the next chapter is added below");
  const both = nums();
  expect(both[firstNums.length] === firstNums[firstNums.length - 1] + 1, "the numbers carry on into the next chapter");
  expect(/^2\. /.test($$("#main .seg-head")[1].textContent), "with its own heading");
  // sentence numbers are a layer
  page.click(byText("#main .chips .chip", /Sentence numbers/));
  await until(() => $$("#main .read-text mark.sn").length > 3 && page.$("#main .read-text").classList.contains("L-sentences"), "sentence numbers marked");
  const ids = $$("#main .read-text mark.sn").map(m => +m.dataset.id);
  expect(ids.every((n, i) => i === 0 || n === ids[i - 1] + 1), "sentences are numbered one after another");
  page.click(byText("#main .chips .chip", /Sentence numbers/));
  await until(() => $$("#main .read-text mark.sn").length === 0, "and go away again");
  // jumping to the last chapter starts the flow there
  const menu = page.$("#main .read-where select");
  const last = menu.options.length - 1;
  page.change(menu, String(last));
  await until(() => $$("#main .chap").length === 1 && page.$("#main .chap").dataset.index === String(last), "jump to the last chapter");
  expect(byText("#main button.more", /previous/) && !byText("#main button.more", /previous/).hidden, "earlier chapters can still be loaded");
  await page.eval("S.nar.seg = { mode: 'slices', n: 10, rules: { numbered: true, caps: true, short: false }, min_words: 500 }");
});

await scenario("chapter editor: start, rename and remove chapters in the text, and go back to the automatic ones", async () => {
  await reset();
  await page.eval("S.nar.seg = { mode: 'chapters', n: 10, rules: { numbered: true, caps: true, short: false }, min_words: 50 }");
  const cfg = { mode: "chapters", n: 10, rules: { numbered: true, caps: true, short: false }, min_words: 50 };
  const chapters = async () => (await api(base, "/api/read", { books: ALL, book: "alpha", seg: cfg, layers: [] })).segments;
  const auto = (await chapters()).length;
  await page.go("#/chapters/alpha");
  await until(() => $$("#main .seg-head.edit").length === 1 && $$("#main .cstart").length > 1, "the editor shows the first chapter and a start button on its paragraphs");
  expect(/found automatically/.test(page.text()) && byText("#main .seg-head.edit button", /Remove this chapter start/), "chapter titles have their buttons");
  expect(/Back to the automatic chapters/.test(page.text()) && byText("#main button", /Back to the automatic/).disabled, "nothing to undo yet");
  // start a chapter at a paragraph of the first chapter
  page.click($$("#main .cstart")[2]);
  await until(async () => (await chapters()).length === auto + 1, "the new chapter start is saved");
  await until(() => $$("#main .seg-head.edit").some(x => /started by you/.test(x.textContent)), "the editor shows it, at the place it was made");
  expect(!byText("#main button", /Back to the automatic/).disabled, "and offers to go back");
  // rename it
  const mine = $$("#main .seg-head.edit").find(x => /started by you/.test(x.textContent));
  page.click([...mine.querySelectorAll("button")].find(b => /Rename/.test(b.textContent)));
  const title = mine.querySelector("input[type=text]");
  title.value = "My chapter";
  page.click([...mine.querySelectorAll("button")].find(b => /^OK$/.test(b.textContent)));
  await until(async () => (await chapters()).some(s => s.label === "My chapter"), "the title is saved");
  await until(() => $$("#main .seg-head.edit").some(x => /My chapter/.test(x.textContent)), "and shown");
  // the same chapters are used elsewhere
  await api(base, "/api/narrative/segments", { books: ALL, seg: cfg }).then(r => expect(r.segments.some(s => s.label === "My chapter" && s.source === "yours"), "Arcs and style see it too"));
  // remove it again, and an automatic one, then reset
  const start = $$("#main .seg-head.edit").find(x => /My chapter/.test(x.textContent));
  page.click([...start.querySelectorAll("button")].find(b => /Remove this chapter start/.test(b.textContent)));
  await until(async () => (await chapters()).length === auto, "removing your own chapter start gives back the automatic chapters");
  await until(() => !$$("#main .seg-head.edit").some(x => /My chapter/.test(x.textContent)) && byText("#main button", /Back to the automatic/).disabled, "and the editor follows");
  await page.eval("S.nar.seg = { mode: 'slices', n: 10, rules: { numbered: true, caps: true, short: false }, min_words: 500 }");
});

await scenario("the text view: assign a narrator to a whole chapter at once", async () => {
  await reset();
  await page.eval("S.nar.seg = { mode: 'chapters' }; S.read.index = 0;");   // alpha has real chapters at the default settings;
  const cfg = { mode: "chapters" };                                        // force index 0, in case an earlier scenario left the reader on alpha's last chapter
  const watson = (await api(base, "/api/units", { books: ALL })).rows.find(r => r.name === "Watson" && r.books[0] === "alpha").id;
  const read = index => api(base, "/api/read", { books: ALL, book: "alpha", seg: cfg, index, layers: ["narrators"] });
  const first = await read(0);
  expect(first.segments.length > 1 && first.paragraphs.length > 1, "the first chapter has more than one paragraph, and there's a second");
  await page.go("#/read/alpha");
  await until(() => page.eval("S.read.index") === 0 && $$("#main .pn").length > 0, "the first chapter, with a narrator label to click");
  page.click($$("#main .pn")[0]);
  const applyChapter = () => byText("#main .read-side button", /Apply to this whole chapter/);
  await until(() => applyChapter(), "the whole-chapter button");
  const sel = page.$(".read-side select");
  await until(() => [...sel.options].some(o => o.value === watson), "Watson offered as a narrator");
  page.change(sel, watson);
  page.click(applyChapter());
  await until(async () => (await read(0)).paragraphs.every(p => p.exception && p.narrator_id === "nar:" + watson), "every paragraph of the first chapter now belongs to Watson");
  expect((await read(1)).paragraphs.every(p => !p.exception), "the next chapter is unaffected");
  await until(() => $$("#main .pn.exc").length > 0, "the text view shows the exception");
  // clear it again through the same control
  page.click($$("#main .pn")[0]);
  await until(() => page.$(".read-side select"), "the panel reopens");
  page.change(page.$(".read-side select"), "");
  page.click(applyChapter());
  await until(async () => (await read(0)).paragraphs.every(p => !p.exception), "cleared again");
  await page.eval("S.nar.seg = { mode: 'slices', n: 10, rules: { numbered: true, caps: true, short: false }, min_words: 500 }");
});

await scenario("links: auto-link exact name, type and pronoun matches", async () => {
  await reset();
  await page.go("#/links");
  await until(() => byText("#main h2", /Auto-link/), "the Auto-link panel");
  page.click(byText("#main button", /Auto-link exact matches/));
  // a later scenario is not guaranteed to start unlinked (reset() doesn't undo links), so check the end state via the
  // API rather than the toast wording, which differs between "linked just now" and "already linked"
  await until(async () => (await api(base, "/api/links/persons")).rows.some(p => p.name === "Holmes" && p.members.length === 3),
    "Holmes across all three books becomes one linked person");
  await until(() => $$("#main .person-card").length >= 2, "one card per linked character");
  const holmesCard = $$("#main .person-card").find(c => c.querySelector("input[type=text]").value === "Holmes");
  expect(holmesCard, "a card for Holmes");
  expect(holmesCard.querySelectorAll(".appear-row").length === 3, "its three book appearances are listed inside the card");

  // batch unlink: tick the whole card (not one of its appearances), leaving the still-linked Watson card untouched
  page.click(holmesCard.querySelector('input[type="checkbox"]'));
  expect(holmesCard.classList.contains("picked"), "the ticked card is highlighted");
  await until(() => /1 entity selected/.test(page.text()), "the toolbar counts the selection");
  page.click(byText("#main button", /Unlink selected/));
  await until(async () => !(await api(base, "/api/links/persons")).rows.some(p => p.name === "Holmes"), "Holmes was unlinked");
  expect((await api(base, "/api/links/persons")).rows.some(p => p.name === "Watson"), "Watson, not ticked, is still linked");
});

await scenario("links: linked narrators get their own card in Linked entities, with their own Unlink", async () => {
  await reset();
  const lid = (await api(base, "/api/narrators/link", { a: "nar:anon:alpha", b: "nar:anon:beta", name: "The Chronicler" })).id;
  try {
    await page.go("#/entities");          // in case a previous scenario already left the hash on #/links: force a real navigation, not a no-op
    await page.go("#/links");
    await until(() => byText("#main h3", /Linked narrators/), "the Linked narrators heading");
    const card = () => $$("#main .person-card").find(c => (c.querySelector("input[type=text]") || {}).value === "The Chronicler");
    await until(() => card(), "a card for the linked narrator");
    expect(card().querySelectorAll(".appear-row").length === 2, "its two narrator roles are listed");
    expect(card().querySelector(`a[href="#/entities/${encodeURIComponent(lid)}"]`), "links to the narrator link's own profile");
    // unlink one role: a link of two dissolves, so the card disappears entirely
    page.click([...card().querySelectorAll(".appear-row")].find(r => /beta/.test(r.textContent)).querySelector("button"));
    await until(() => !card(), "the dissolved link's card is gone");
    expect(/No narrators linked yet/.test(page.text()), "back to the empty state");
  } finally {
    await api(base, "/api/narrators/unlink_all", { id: lid }).catch(() => {});   // in case the scenario failed before unlinking
  }
});

await scenario("links: the search boxes list entities when clicked and narrow as you type; the read menus are frozen together", async () => {
  await reset();
  await page.go("#/links");
  const box = () => $$("#main .picker input[type=search]")[0];
  const items = () => $$("#main .picker .sugg div").length;
  box().dispatchEvent(new w.Event("focus"));
  await until(() => items() > 2, "entities listed before anything is typed");
  const all = items();
  page.input(box(), "watson");
  await until(() => items() > 0 && items() < all && $$("#main .picker .sugg div").every(d => /Watson/.test(d.textContent)), "the list narrows to the name");
  const narrowed = items();
  $$("#main .picker .sugg div")[0].dispatchEvent(new w.MouseEvent("mousedown", { bubbles: true, cancelable: true }));
  expect(/Watson/.test(box().value), "choosing an entry fills the box");
  // the entity chosen in the first box no longer appears in the second box's list
  const second = $$("#main .picker input[type=search]")[1];
  page.input(second, "watson");
  await until(() => $$("#main .picker")[1].querySelectorAll(".sugg div").length === narrowed - 1, "the chosen entity is hidden from the other list");
  await page.go("#/read/alpha");
  const head = page.$("#main .read-head");
  expect(head && head.children[0].classList.contains("read-bar") && head.children[1].classList.contains("read-where"), "the settings bar sits above the position bar in one frozen block");
  expect(page.$("#main .read-head select") && page.window.document.documentElement.style.getPropertyValue("--read-head") !== "", "the block's height is published for the layout");
});

await scenario("described: entities gathered by name are described by whom, and the table follows the kind, the split and the voice", async () => {
  await reset();
  const rows = (await api(base, "/api/units", { books: ALL })).rows;
  const named = rows.filter(r => /holmes|watson/i.test(r.name)).length;
  await page.go("#/described");
  expect(/Choose what to look at/.test(page.text()), "nothing is counted until something is chosen");
  page.click([...$$("#main .picker .seg button")].find(b => /^Group$/.test(b.textContent)));
  const inp = () => $$("#main .gpick input[type=search]").find(i => /named/.test(i.placeholder));
  page.input(inp(), "holmes, watson");
  await until(() => new RegExp(`${named} entities`).test(page.text()), "a live count of the entities that match the words");
  page.click(button(/^Add them$/));
  await until(() => $$("#main .gbox .gtag").length === named, "every entity that matches is added as a tag");
  const fld = re => byText("#main .fld", re);
  const pressed = (box, label) => page.click([...box.querySelectorAll("button")].find(b => label.test(b.textContent)));
  page.click(button(/^Actions$/));
  await until(() => byText("#main th", /^Narrator of alpha/) && byText("#main td", /^say$/), "actions, one column per describer (an unnamed narrator per book first)");
  expect(byText("#main td", /^see$/), "what Holmes says himself ('I see') is there too");
  pressed(fld(/^Split by who says it/), /^Gender$/);
  await until(() => byText("#main th", /^Not a person/), "split by gender: an unnamed narrator is no person");
  expect(!byText("#main th", /^Narrator of alpha/), "the per-describer columns are gone");
  pressed(fld(/^Voice/), /^Speech$/);
  await until(() => !byText("#main td", /^say$/) && byText("#main td", /^see$/), "speech only: 'said' is narration, 'see' is spoken");
  pressed(fld(/^Voice/), /^Narration$/);
  await until(() => byText("#main td", /^say$/) && !byText("#main td", /^see$/), "narration only");
  // a click on a count lists the sentences behind it: as many as the count, each saying who said it
  const countOf = row => Number(row.querySelector("td:nth-child(2) .evlink").textContent.split(" ")[0].replace(/,/g, ""));
  const sentencesIn = () => Number(((drawerText().match(/(\d[\d,]*) sentences/) || [])[1] || "").replace(/,/g, ""));
  const sayRow = byText("#main tbody tr", /^say/);
  const n = countOf(sayRow);
  page.click(sayRow.querySelector("td:nth-child(2) .evlink"));
  await until(() => drawerOpen() && sentencesIn() === n, `the drawer lists the ${n} sentences of the All cell`);
  expect(/\(narration\)/.test(drawerText()) && /^“say”/.test(page.$("#drawerTitle").textContent), "each sentence says it was told in narration; the title names the word");
  page.click(page.$("#drawerClose"));
  pressed(fld(/^Voice/), /^Speech$/);
  await until(() => byText("#main td", /^see$/) && !byText("#main td", /^say$/), "speech only again");
  const seeRow = byText("#main tbody tr", /^see/);
  const cell = [...seeRow.querySelectorAll("td .evlink")][1];                       // the first describer column after All
  const m = Number(cell.textContent.split(" ")[0].replace(/,/g, ""));
  page.click(cell);
  await until(() => drawerOpen() && sentencesIn() === m && /\(speech\)/.test(drawerText()), `the drawer lists the ${m} sentences of a describer's cell, told in speech`);
  // columns you pick yourself: an entity and a gender, each its own column
  page.click(page.$("#drawerClose"));
  pressed(fld(/^Voice/), /^Narration and speech$/);
  pressed(fld(/^Split by who says it/), /^Columns you pick$/);
  await until(() => $$("#main .pickcol").length === 1 && /Pick the columns/.test(page.text()), "one empty slot, and a note saying to pick the columns");
  expect(!byText("#main label", /^Columns/), "the number of columns doesn't apply to columns you pick");
  const input = page.$("#main .pickcol input[type=search]");
  page.input(input, "watson");
  await until(() => $$("#main .pickcol .sugg div").length > 0, "suggestions for the first column");
  $$("#main .pickcol .sugg div")[0].dispatchEvent(new w.MouseEvent("mousedown", { bubbles: true, cancelable: true }));
  await until(() => byText("#main th", /^Watson/), "a column for Watson");
  page.click(button(/^Add a column$/));
  await until(() => $$("#main .pickcol").length === 2, "a second slot");
  pressed($$("#main .pickcol")[1], /^Gender$/);
  await until(() => $$("#main th").filter(t => /·/.test(t.textContent)).length === 3 || byText("#main th", /^he\/him|^No BookNLP/), "the gender column appears");
  const heads = $$("#main thead th").map(t => t.textContent);
  expect(heads.length === 4 && /^Watson/.test(heads[2]), `the All column and the two columns you picked, in your order (${heads.join(" | ")})`);
  const pickedRow = byText("#main tbody tr", /^see/);
  const mine = Number([...pickedRow.querySelectorAll(".evlink")][1].textContent.split(" ")[0].replace(/,/g, ""));
  page.click([...pickedRow.querySelectorAll(".evlink")][1]);
  await until(() => drawerOpen() && sentencesIn() === mine, `the drawer lists the ${mine} sentences of a picked column's cell`);
  page.click(page.$("#drawerClose"));
  page.click(button(/^Remove$/));
  await until(() => $$("#main .pickcol").length === 1 && $$("#main thead th").length === 3, "removing a column removes it from the table");
});

await scenario("described: the profile pages link to it with their own target chosen", async () => {
  await reset();
  const rows = (await api(base, "/api/units", { books: ALL })).rows;
  const holmes = rows.find(r => r.name === "Holmes" && r.books[0] === "alpha");
  await page.go("#/entities/" + encodeURIComponent(holmes.id));
  page.click(byText("#main a", /^Described by whom/));
  await until(() => /#\/described/.test(w.location.hash) && page.$("#main .picker input[type=search]") && page.$("#main .picker input[type=search]").value === "Holmes", "an entity's link opens the page with that entity chosen");
  await until(() => $$("#main .loading").length === 0 && /Holmes/.test(page.text()), "and it is counted");
  await page.go("#/entities/" + encodeURIComponent("book:alpha"));
  page.click(byText("#main a", /^Described by whom/));
  await until(() => /#\/described/.test(w.location.hash) && byText("#main .picker select", /alpha/) !== undefined && !/Choose what to look at/.test(page.text()), "a book overview's link chooses that book");
  const genders = (await api(base, "/api/units", { books: ALL })).genders;
  await page.go("#/entities/" + encodeURIComponent("gender:" + genders[0].pron));
  page.click(byText("#main a", /^Described by whom/));
  await until(() => /#\/described/.test(w.location.hash) && !/Choose what to look at/.test(page.text()), "a gender page's link chooses that gender");
});

await scenario("over the book: a target slice by slice, heat grid and numbers, the sentences of one slice", async () => {
  await reset();
  const rows = (await api(base, "/api/units", { books: ALL })).rows;
  const holmes = rows.find(r => r.name === "Holmes" && r.books[0] === "alpha");
  await page.go("#/over");
  expect(/Choose an entity, a group, a tag or a gender/.test(page.text()), "nothing is counted until a target is chosen");
  await page.eval(`S.over.target = ${JSON.stringify({ kind: "unit", id: holmes.id, name: "Holmes", type: "PER" })}; S.over.view = "heat"; S.over.order = "freq"; S.over.rel = "agent";
    S.nar.seg = { ...S.nar.seg, mode: "slices", slice_by: "count", n: 10, scope: "corpus" }; render()`);
  await until(() => $$("#main .hgrid thead th.hc").length === 10, "a column per slice, ten, in the one grid (the kinds of action are a tab of it)");
  expect(!byText("#main .fld", /^Timeline/), "no book-by-book / whole-corpus choice on this page");
  expect(/Slices per book/.test(page.text()) && !/across the corpus/.test(page.text()), "slices are always per book, whatever Arcs' timeline says");
  const overview = $$("#main section.panel").find(p => p.querySelector("h2") && p.querySelector("h2").textContent === "Slice by slice");
  expect(overview && [...overview.querySelectorAll("a")].filter(a => /^#\/read\/alpha\/\d+$/.test(a.getAttribute("href"))).length === 10, "the overview has a row per slice, each opening the text");
  expect(page.$("#main .hgrid .hcell") && $$("#main .hgrid .hcell").length >= 10, "the heat grid has cells");
  // the sentences of one slice
  const cell = $$("#main .hgrid tbody tr")[0].querySelectorAll(".hcell")[3];
  page.click(cell);
  await until(() => drawerOpen() && /through/.test(drawerText()), "a cell opens the sentences of its slice");
  const pcts = [...drawerText().matchAll(/([\d.]+)% through/g)].map(m => +m[1]);
  expect(pcts.length > 0 && pcts.every(p => p >= 30 && p <= 40), "all lie in the fourth tenth of the book: " + pcts);
  page.click(page.$("#drawerClose"));
  // each view has its own full CSV: the heat grid's holds the shares, with the slices' own names as column names
  const csvOfDownload = async () => {
    let blob = null;
    const realClick = w.HTMLAnchorElement.prototype.click;
    w.URL.createObjectURL = b => { blob = b; return "blob:test"; };
    w.HTMLAnchorElement.prototype.click = function () {};
    page.click(byText("#main .hgrid .dl", /^CSV$/));
    w.HTMLAnchorElement.prototype.click = realClick;
    return new Promise(res => { const fr = new w.FileReader(); fr.onload = () => res(fr.result.replace(/^\uFEFF/, "").split("\r\n")); fr.readAsText(blob); });
  };
  let lines = await csvOfDownload();
  expect(lines[0].startsWith("Word,1/10,2/10,") && lines[0].endsWith(",Total,Trend z,Trend p,χ²,χ² p,Cramér's V"), "heat grid CSV header: " + lines[0]);
  const say = lines.find(l => l.startsWith("say,"));
  expect(say && say.split(",").length === lines[0].split(",").length, "a CSV row per word with a value per column: " + say);
  // numbers, order, relation, book
  page.click(button(/^Numbers$/));
  await until(() => $$("#main .hgrid thead th.hc").length === 0 && /\(\d+(\.\d)?%\)/.test(page.$("#main .hgrid").textContent), "the numbers view gives count (share%) per slice");
  lines = await csvOfDownload();
  expect(/^(\d+,){9}\d+$/.test(lines.find(l => l.startsWith("say,")).split(",").slice(1, 11).join(",")), "the numbers CSV holds counts: " + lines.find(l => l.startsWith("say,")));
  page.change(byText("#main label", /^Order/).querySelector("select"), "rising");
  await until(() => page.$("#main .hgrid tbody tr"), "ordered by rising trend");
  // changing the list fetches again: the results stay on the page (dimmed) meanwhile, or it would shrink and send the reader back to the top
  await page.eval("window.__api = api; api = (...a) => new Promise(res => setTimeout(res, 500)).then(() => window.__api(...a))");
  const gridBefore = page.$("#main .hgrid");
  page.click(byText("#main .subtabs button", /^Modifiers$/));
  await sleep(150);
  expect(page.$("#main .busy") && page.$("#main .busy .hgrid") === gridBefore && !page.$("#main .loading"), "the old results are still there, marked busy, while the new ones load");
  await page.eval("api = window.__api");
  await until(() => $$("#main .subtabs button.on").some(b => /Modifiers/.test(b.textContent)) && $$("#main .hgrid tbody tr").length >= 0 && !/Something went wrong/.test(page.text()), "another relation");
  expect(page.eval("S.over.rel") === "mod", "the relation is remembered");
  page.change(byText("#main label", /^Slices per book/).querySelector("select"), "5");
  await until(() => /5 slices/.test(page.text()), "five slices when asked for five");
  // the slicer is the Arcs and style one: cutting by words swaps the number of slices for the words per slice, and chapters swap the fields again
  page.change(byText("#main label", /^Slices by/).querySelector("select"), "words");
  await until(() => byText("#main label", /^Words per slice/) && !byText("#main label", /^Slices per book/), "words per slice replaces the number of slices");
  page.change(byText("#main label", /^Words per slice/).querySelector("input"), "400");
  await until(() => page.eval("S.nar.seg.words") === 400 && /slices of alpha|\d+ slices/.test(page.text()) && !/5 slices\./.test(page.text()), "the book is cut every 400 words");
  page.click([...byText("#main .fld", /^Measure over/).querySelectorAll("button")].find(b => /^Chapters$/.test(b.textContent)));
  await until(() => byText("#main label", /^Minimum chapter length/) && !byText("#main label", /^Words per slice/), "chapters bring the chapter settings");
  page.click([...byText("#main .fld", /^Measure over/).querySelectorAll("button")].find(b => /^Equal slices$/.test(b.textContent)));
  await until(() => byText("#main label", /^Words per slice/), "and back");
  await page.eval("S.nar.seg.slice_by = 'count'; S.nar.seg.n = 10");
  // a target outside the selected books
  await page.eval("setSel(['beta']); render()");
  await until(() => /isn't in any of the selected books/.test(page.text()), "a target in no selected book says so");
  await page.eval("S.nar.seg.n = 10; S.nar.seg.scope = 'book'");
});

await scenario("over the book: two targets on one curve, the kinds of action, and taking the second away", async () => {
  await reset();
  const rows = (await api(base, "/api/units", { books: ALL })).rows;
  const holmes = rows.find(r => r.name === "Holmes" && r.books[0] === "alpha"), watson = rows.find(r => r.name === "Watson" && r.books[0] === "alpha");
  const spec = (u) => JSON.stringify({ kind: "unit", id: u.id, name: u.name, type: "PER" });
  await page.go("#/books");
  await page.eval(`S.over.target = ${spec(holmes)}; S.over.other = ${spec(watson)}; S.over.view = "heat"; S.over.order = "freq"; S.over.rel = "agent"; S.over.curve = "ov:per1k";
    S.nar.seg = { ...S.nar.seg, mode: "slices", slice_by: "count", n: 10, scope: "book" }`);
  await page.go("#/over");
  await until(() => $$("#main h2").length >= 6 && !page.$("#main .loading"), "both targets are counted");
  const heads = $$("#main h2").map(e => e.textContent);
  for (const t of ["Holmes: slice by slice", "Holmes: words over the book", "Watson: slice by slice", "Watson: words over the book"])
    expect(heads.includes(t), "a panel “" + t + "”: " + heads.join(" | "));
  expect(/Watson leaves out everything Holmes includes/.test(page.text()), "the page says what the second leaves out");
  const curve = () => $$("#main section.panel").find(p => p.querySelector("h2") && p.querySelector("h2").textContent === "Along the book").querySelector(".chart-box svg");
  const order = $$("#main h2").map(e => e.textContent.replace(/^(Holmes|Watson): /, ""));
  expect(order.join("|") === "Over the book|Along the book|words over the book|words over the book|slice by slice|slice by slice",
    "the curve first, then each target's words (kinds of action are a tab of them), then the overviews (AD-37): " + order.join("|"));
  expect(curve().querySelectorAll("polyline").length === 2, "one line for each target on the curve");
  // choose another figure: a word's share
  const curvePanel = () => $$("#main section.panel").find(p => p.querySelector("h2") && p.querySelector("h2").textContent === "Along the book");
  const fold = () => curvePanel().querySelector("details.tfold");
  expect(fold() && !fold().open && fold().querySelector("table") && /^Numbers per slice$/.test(fold().querySelector("summary").textContent), "the numbers fold away under the chart, folded at first (AL-TBL-07)");
  fold().open = true; fold().dispatchEvent(new w.Event("toggle"));
  const catBtn = re => [...curvePanel().querySelectorAll(".picker .seg button")].find(b => re.test(b.textContent));
  const sel = () => [...curvePanel().querySelectorAll(".picker select")].pop();            // the item list (the last select: Words also has a list of lists before it)
  expect(catBtn(/^Figures$/).classList.contains("on") && catBtn(/^Words$/) && catBtn(/^Actions$/), "a category selector: Figures, Words, Actions");
  expect([...sel().options].some(o => o.value === "ov:per1k") && [...sel().options].every(o => /^(ov|rel):/.test(o.value)), "its list holds the figures only");
  const pickerNote = () => curvePanel().querySelector(".picker .muted");
  expect(!pickerNote(), "no explanation beside the list of figures");
  page.click(catBtn(/^Words$/));
  await until(() => catBtn(/^Words$/).classList.contains("on") && [...sel().options].length > 0 && [...sel().options].every(o => o.value.startsWith("word:")), "Words lists the words");
  page.change(sel(), "word:agent:say");
  expect(pickerNote() && /Words in the “Actions” list that Holmes or Watson has: Holmes's, most frequent first, then Watson's that Holmes doesn't have \(the first 100\)\./.test(pickerNote().textContent), "beside the words: which list, whose words, in what order: " + (pickerNote() && pickerNote().textContent));
  await until(() => page.eval("S.over.curve") === "word:agent:say" && /share of the slice's list|\(%\)/.test(curve().textContent) && byText("#main th", /^Holmes$/), "a word's share is drawn, the numbers beside it");
  expect(fold().open, "a fold opened stays open while the page is drawn again");
  expect(curve().querySelectorAll("polyline").length === 2, "still a line each");
  page.click(catBtn(/^Actions$/));
  await until(() => catBtn(/^Actions$/).classList.contains("on") && [...sel().options].length > 0 && [...sel().options].every(o => o.value.startsWith("kind:")) && page.eval("S.over.curve").startsWith("kind:"), "Actions lists the kinds of action and draws the first");
  page.click(catBtn(/^Words$/));
  await until(() => page.eval("S.over.curve") === "word:agent:say" && sel().value === "word:agent:say", "each category remembers its own choice: back in Words, 'say' again");
  page.click(catBtn(/^Figures$/));
  await until(() => page.eval("S.over.curve") === "ov:per1k", "and Figures too");
  if (page.eval("S.lib.sound")) {                              // the sound of their speech (the pronunciation dictionary is optional)
    const soundBox = () => [...curvePanel().querySelectorAll("label")].find(l => /Sound of their speech/.test(l.textContent)).querySelector("input");
    expect(!catBtn(/^Sound of speech$/) && !soundBox().checked, "no sound until asked for");
    soundBox().checked = true; page.change(soundBox());
    await until(() => catBtn(/^Sound of speech$/) && $$("#main h3").filter(x => x.textContent === "Sound and rhythm of their speech").length === 2, "the sound of each target's speech: a category on the curve, a table under each overview");
    page.click(catBtn(/^Sound of speech$/));
    await until(() => page.eval("S.over.curve") === "snd:stressed" && curve().querySelectorAll("polyline").length === 2, "a sound figure is drawn for both");
    soundBox().checked = false; page.change(soundBox());
    await until(() => !catBtn(/^Sound of speech$/) && page.eval("S.over.curve") === "ov:per1k" || page.eval("S.over.curve") === "snd:stressed" && !catBtn(/^Sound of speech$/), "switched off again");
    page.click(catBtn(/^Figures$/));
    await until(() => page.eval("S.over.curve") === "ov:per1k", "back to the figures");
  }
  // the words come from a list of their own (actions, done to them, possessions…), apart from the one of Words over the book
  page.click(catBtn(/^Words$/));
  const listSel = () => [...curvePanel().querySelectorAll(".picker select")].find(x => [...x.options].map(o => o.value).join() === "agent,patient,poss,mod,prep") || null;
  await until(() => listSel() && [...listSel().options].map(o => o.value).join() === "agent,patient,poss,mod,prep" && listSel().value === "agent", "a list of lists beside the words, on Actions");
  page.change(listSel(), "poss");
  await until(() => page.eval("S.over.curve_rel") === "poss" && sel() && [...sel().options].length > 0 && [...sel().options].every(o => o.value.startsWith("word:poss:")) && /“Possessions” list/.test(curvePanel().textContent), "the words of the Possessions list");
  expect(page.eval("S.over.rel") === "agent" && $$("#main .subtabs button.on").some(b => /^Actions$/.test(b.textContent)), "while the words panels are still on Actions");
  expect(curve().querySelectorAll("polyline").length >= 1, "and the curve is drawn (Watson has no possessions: his line is a gap)");
  page.change(listSel(), "mod");
  await until(() => page.eval("S.over.curve_rel") === "mod" && /No words in the “Modifiers” list for Holmes or Watson/.test(curvePanel().textContent) && listSel(), "a list with no words says so and keeps the list to change");
  page.change(listSel(), "agent");
  await until(() => page.eval("S.over.curve_rel") === "agent" && sel() && [...sel().options].every(o => o.value.startsWith("word:agent:")), "and back to Actions");
  // kinds of action: a tab of the words section, and a cell opens the sentences of that slice
  page.click(byText("#main .subtabs button", /^Kinds of action$/));
  await until(() => page.eval("S.over.kinds") && /Kind of action/.test($$("#main .hgrid")[0].textContent), "the Kinds of action tab shows them, with the same controls");
  const kindsGrid = $$("#main .hgrid")[0];
  expect(kindsGrid.querySelectorAll("thead th.hc").length === 10 && !kindsGrid.parentElement.querySelector(".colpick"), "a heat grid of kinds of action over ten slices, with no column chooser");
  const cell = [...kindsGrid.querySelectorAll(".hcell")].find(c => c.style.background);
  page.click(cell);
  await until(() => drawerOpen() && /through/.test(drawerText()) && /Actions: /.test(page.$("#drawerTitle").textContent), "a kinds cell opens the sentences of its slice");
  page.click(page.$("#drawerClose"));
  page.click(byText("#main .subtabs button", /^Actions$/));
  await until(() => !page.eval("S.over.kinds"), "back to the words");
  // taking the second target away
  page.click(button(/^Remove$/));
  await until(() => !/Watson/.test($$("#main h2").map(e => e.textContent).join("|")) && $$("#main h2").some(e => e.textContent === "Words over the book"), "one target again, with the panels' plain names");
  expect(curve().querySelectorAll("polyline").length === 1, "one line");
  await page.eval("S.over.other = null; S.over.asking = false; S.over.curve = 'ov:per1k'; S.over.curve_rel = 'agent'; S.over.curve_by = { figures: 'ov:per1k' }");
});

await scenario("over the book: the profile preview and the Compare section show it in small, and link to the page", async () => {
  await reset();
  const rows = (await api(base, "/api/units", { books: ALL })).rows;
  const holmes = rows.find(r => r.name === "Holmes" && r.books[0] === "alpha"), watson = rows.find(r => r.name === "Watson" && r.books[0] === "alpha");
  await page.eval(`S.over.rel = "agent"; S.nar.seg = { ...S.nar.seg, mode: "slices", slice_by: "count", n: 10, scope: "book" }`);
  const panelOf = () => $$("#main section.panel").find(p => p.querySelector("h2") && p.querySelector("h2").textContent === "Over the book");
  // an entity's profile
  await page.go("#/entities/" + encodeURIComponent(holmes.id));
  await until(() => panelOf() && panelOf().querySelector(".chart-box svg") && !panelOf().querySelector(".loading"), "the profile has an Over the book preview");
  expect(/Based on: cut into 10 equal slices/.test(panelOf().textContent) && !panelOf().querySelector("summary .bo.set"), "it says how the book is cut, not tinted at the default");
  expect(panelOf().querySelectorAll(".chart-box svg").length === 1 && panelOf().querySelector(".chart-box svg polyline"), "one chart: mentions per 1,000 words (AL-PRIN-13)");
  expect(![...panelOf().querySelectorAll("th")].length && [...panelOf().querySelectorAll(".subtabs, .seg")].every(x => x.closest("details")), "no tables, list tabs or chart choices (only the slicer, in its fold): the page has them");
  const link = () => [...panelOf().querySelectorAll("a")].find(a => /^Over the book$/.test(a.textContent));
  expect(link() && link().closest("p") === panelOf().querySelector("p") && panelOf().querySelector("p").compareDocumentPosition(panelOf().querySelector(".chart-box")) & 4, "the link is in the intro line, above the chart");
  expect(link().parentElement.textContent.endsWith("See Over the book for more details."), "it reads “See Over the book for more details.”: " + link().parentElement.textContent);
  // its slicer is the Arcs one, and changing it draws the panel again
  page.change([...panelOf().querySelectorAll("label")].find(l => /^Slices by/.test(l.textContent)).querySelector("select"), "words");
  await until(() => /cut into slices of \d+ words/.test(panelOf().textContent) && panelOf().querySelector("summary .bo.set") && [...panelOf().querySelectorAll("label")].some(l => /^Words per slice/.test(l.textContent)), "cut by words: the panel and its slicer follow");
  await page.eval("S.nar.seg.slice_by = 'count'; S.nar.seg.n = 10");
  // the link opens the page with this entity chosen
  page.click(link());
  await until(() => /#\/over/.test(w.location.hash) && $$("#main .hgrid").length >= 1, "the link opens the page, counted");
  expect(page.eval("S.over.target.id") === holmes.id && page.eval("S.over.other") === null, "with this entity as the target");
  // a book's own page has it too
  await page.go("#/entities/" + encodeURIComponent("book:alpha"));
  await until(() => panelOf() && panelOf().querySelector(".chart-box svg"), "a book's profile has the preview");
  // the Compare page
  await page.eval(`S.cmp = { a: { kind: "unit", id: ${JSON.stringify(holmes.id)}, name: "Holmes", type: "PER" }, b: { kind: "unit", id: ${JSON.stringify(watson.id)}, name: "Watson", type: "PER" }, rel: "agent" }`);
  await page.go("#/compare");
  await until(() => panelOf() && panelOf().querySelector(".chart-box svg") && !panelOf().querySelector(".loading"), "Compare has an Over the book section");
  expect(panelOf().querySelector(".chart-box svg").querySelectorAll("polyline").length === 2, "a line for each side");
  expect(/Both sides are measured in the same book/.test(panelOf().textContent), "it says the book is shared");
  const cmpLink = [...panelOf().querySelectorAll("a")].find(a => /^Over the book$/.test(a.textContent));
  expect(cmpLink.closest("p") === panelOf().querySelector("p"), "its link is in the intro line at the top");
  page.click(cmpLink);
  await until(() => /#\/over/.test(w.location.hash) && $$("#main h2").some(h => h.textContent === "Watson: words over the book"), "the link opens the page with both sides");
  expect(page.eval("S.over.target.id") === holmes.id && page.eval("S.over.other.id") === watson.id, "Holmes first, Watson second");
  await page.eval("S.over.other = null; S.over.asking = false");
  // each side limited to a different single book: Compare offers Two books aligned, with both sides and their books chosen
  const hb = rows.find(r => r.name === "Holmes" && r.books[0] === "beta");
  await page.eval(`S.cmp = { a: { kind: "unit", id: ${JSON.stringify(holmes.id)}, name: "Holmes", type: "PER", books: ["alpha"] }, b: { kind: "unit", id: ${JSON.stringify(hb.id)}, name: "Holmes", type: "PER", books: ["beta"] }, rel: "agent" }`);
  await page.go("#/compare");
  await until(() => panelOf() && /Two books aligned/.test(panelOf().textContent) && panelOf().querySelector(".chart-box svg"), "Compare offers Two books aligned when the sides are in different single books");
  expect(/No book holds both sides/.test(panelOf().textContent) && /Position in the book/.test(panelOf().textContent), "it says each side is measured in its own book, by position");
  expect(panelOf().querySelectorAll(".chart-box svg polyline").length === 2 && /Side A book/.test(panelOf().textContent) && /Side B book/.test(panelOf().textContent) && /How alike the curves are/.test(panelOf().textContent),
    "two lines (one per side), a book for each side, and the similarity");
  const per = [...panelOf().querySelectorAll(".chart-box svg polyline")].map(pl => new Set(pl.getAttribute("points").split(" ").map(pt => pt.split(",")[1])).size);
  expect(per.every(n => n > 1), "neither line is flat: " + per);
  // two whole books as the sides (everyone in each): each is measured in itself, so both lines have values (in one book the other would be a flat zero)
  await page.eval(`S.cmp = { a: { kind: "book", book: "alpha", name: "alpha" }, b: { kind: "book", book: "beta", name: "beta" }, rel: "agent" }`);
  await page.go("#/books");
  await page.go("#/compare");
  await until(() => panelOf() && /No book holds both sides/.test(panelOf().textContent) && panelOf().querySelectorAll(".chart-box svg polyline").length === 2, "two books as the sides: a line for each");
  const spread = [...panelOf().querySelectorAll(".chart-box svg polyline")].map(pl => new Set(pl.getAttribute("points").split(" ").map(pt => pt.split(",")[1])).size);
  expect(spread.every(n => n > 1), "neither line is flat (a book holding only one side would draw the other at 0): " + spread);
  expect(/alpha \(alpha\)/.test(panelOf().textContent) && /beta \(beta\)/.test(panelOf().textContent), "the lines are named by side and book");
  // two entities of different books, not limited to any book, are measured the same way
  await page.eval(`S.cmp = { a: { kind: "unit", id: ${JSON.stringify(holmes.id)}, name: "Holmes", type: "PER" }, b: { kind: "unit", id: ${JSON.stringify(hb.id)}, name: "Holmes", type: "PER" }, rel: "agent" }`);
  await page.go("#/books");
  await page.go("#/compare");
  await until(() => panelOf() && /No book holds both sides/.test(panelOf().textContent) && panelOf().querySelectorAll(".chart-box svg polyline").length === 2, "the same without any limit: two entities of different books");
  await page.eval(`S.cmp = { a: { kind: "unit", id: ${JSON.stringify(holmes.id)}, name: "Holmes", type: "PER", books: ["alpha"] }, b: { kind: "unit", id: ${JSON.stringify(hb.id)}, name: "Holmes", type: "PER", books: ["beta"] }, rel: "agent" }`);
  await page.go("#/books");
  await page.go("#/compare");
  await until(() => panelOf() && /Two books aligned/.test(panelOf().textContent), "and again with the limits");
  page.click([...panelOf().querySelectorAll("a")].find(a => /^Two books aligned$/.test(a.textContent)));
  await until(() => /#\/over\/aligned/.test(w.location.hash) && $$("#main h2").some(h => h.textContent === "Holmes (beta): words over the book"), "the link opens it with both sides in their own books");
  const al = page.eval("JSON.stringify(S.over.al)");
  expect(page.eval("S.over.book") === "alpha" && page.eval("S.over.al_b_book") === "beta" && JSON.parse(al).b.same === false && !("books" in JSON.parse(al).a.target), "side A in alpha, side B (another entity) in beta, no book limit left on the targets: " + al);
  // the same person on both sides, limited to different books, is "the same as A"
  const person = (await api(base, "/api/links/link", { a: holmes.id, b: hb.id })).id;
  await page.eval(`S.units = null; loadLib(); S.cmp = { a: { kind: "unit", id: ${JSON.stringify(person)}, name: "Holmes", type: "PER", books: ["alpha"] }, b: { kind: "unit", id: ${JSON.stringify(person)}, name: "Holmes", type: "PER", books: ["beta"] }, rel: "agent" }`);
  await page.go("#/books");
  await page.go("#/compare");
  await until(() => panelOf() && /Two books aligned/.test(panelOf().textContent), "also for one linked person");
  page.click([...panelOf().querySelectorAll("a")].find(a => /^Two books aligned$/.test(a.textContent)));
  await until(() => /#\/over\/aligned/.test(w.location.hash) && $$("#main h2").some(h => h.textContent === "Holmes (beta): words over the book"), "opened, each side in its own book");
  expect(page.eval("S.over.al.b.same") === true && page.eval("S.over.book") === "alpha" && page.eval("S.over.al_b_book") === "beta", "the same target on both sides is 'Same target as A'");
  await api(base, "/api/links/reset", {});
  await page.eval("S.units = null; loadLib()");
  // no offer when the sides share a book, or aren't limited to one
  await page.eval(`S.cmp = { a: { kind: "unit", id: ${JSON.stringify(holmes.id)}, name: "Holmes", type: "PER" }, b: { kind: "unit", id: ${JSON.stringify(watson.id)}, name: "Watson", type: "PER" }, rel: "agent" }`);
  await page.go("#/compare");
  await until(() => panelOf() && panelOf().querySelector(".chart-box svg") && !panelOf().querySelector(".loading"), "plain Compare again");
  expect(!/Two books aligned/.test(panelOf().textContent), "no offer when the sides aren't limited to different books");
  await page.eval("S.over.al = { a: { target: null, book: null }, b: { same: true, target: null, book: null } }");
});

await scenario("over the book: two books aligned by relative position", async () => {
  await reset();
  const rows = (await api(base, "/api/units", { books: ALL })).rows;
  const holmesA = rows.find(r => r.name === "Holmes" && r.books[0] === "alpha"), holmesB = rows.find(r => r.name === "Holmes" && r.books[0] === "beta");
  const spec = u => ({ kind: "unit", id: u.id, name: u.name, type: "PER" });
  await page.go("#/books");
  await page.eval(`S.over.al = { a: { target: ${JSON.stringify(spec(holmesA))}, book: null }, b: { same: false, target: ${JSON.stringify(spec(holmesB))}, book: null } }; S.over.al_n = 8; S.over.rel = "agent"; S.over.curve = "ov:per1k"`);
  await page.go("#/over/aligned");
  const heads = () => $$("#main h2").map(e => e.textContent);
  await until(() => heads().includes("Holmes (alpha): words over the book") && heads().includes("Holmes (beta): words over the book") && !page.$("#main .loading"), "both sides are counted, each in its own book");
  expect(heads().join("|") === "Two books aligned|Along the book|Holmes (alpha): words over the book|Holmes (beta): words over the book|Holmes (alpha): slice by slice|Holmes (beta): slice by slice",
    "the curve, then each side's words, then the overviews: " + heads().join("|"));
  const grids = () => $$("#main .hgrid");
  expect(grids().length === 2 && grids().every(g => g.querySelectorAll("thead th.hc").length === 8), "eight slices in each side's grid, the same for both books");
  expect(/^Within a book/.test(page.$("#main .subtabs button").textContent) && byText("#main .subtabs button.on", /^Two books aligned$/), "the sub-tabs, the aligned one open");
  expect(/How alike the curves are: Pearson's r = [-\d.]+ \(p [^)]+\), Spearman's ρ = [-\d.]+ .* over 8 slices/.test(page.text()), "the similarity of the two curves is shown");
  const curve = $$("#main section.panel").find(p => p.querySelector("h2") && p.querySelector("h2").textContent === "Along the book");
  expect(curve.querySelectorAll(".chart-box svg polyline").length === 2 && /Position in the book/.test(curve.textContent) && !curve.querySelector("tbody a"), "a line for each side, titled by position, with no per-slice links into one book");
  // a cell of the second side opens sentences of ITS book
  const cell = [...grids()[1].querySelectorAll(".hcell")].find(c => c.style.background);
  page.click(cell);
  await until(() => drawerOpen() && /beta, [\d.]+% through/.test(drawerText()), "a cell of side B shows sentences of the second book");
  page.click(page.$("#drawerClose"));
  // the number of slices is its own, and leaves the Arcs setting alone
  const arcsN = page.eval("S.nar.seg.n");
  page.change(byText("#main label", /^Slices per book/).querySelector("input"), "5");
  await until(() => grids().length === 2 && grids().every(g => g.querySelectorAll("thead th.hc").length === 5), "five slices when asked for five");
  expect(page.eval("S.nar.seg.n") === arcsN && page.eval("S.over.al_n") === 5, "the Arcs and style setting is untouched");
  // the same target on both sides: a book against itself
  const same = byText("#main label", /^Same target as A$/).querySelector("input");
  same.checked = true; page.change(same);
  const sameBox = () => byText("#main label", /^Same target as A$/).closest(".fld");
  await until(() => !sameBox().querySelector(".picker") && /Pearson's r = 1\.00/.test(page.text()), "ticking Same target as A drops side B's picker; Holmes of alpha against itself is perfectly alike");
  // the other sub-tab, and back
  page.click(byText("#main .subtabs button", /^Within a book$/));
  await until(() => /#\/over$/.test(w.location.hash) && heads().includes("Over the book"), "Within a book is its own address");
  page.click(byText("#main .subtabs button", /^Two books aligned$/));
  await until(() => /#\/over\/aligned/.test(w.location.hash) && heads().includes("Two books aligned"), "and Two books aligned too");
  await page.eval("S.over.al_n = 20; S.over.al = { a: { target: null, book: null }, b: { same: true, target: null, book: null } }");
});

await scenario("over the book: all the books combined, every book weighing the same", async () => {
  await reset();
  const p1 = await api(base, "/api/links/link", { a: "e:alpha:1", b: "e:beta:5" });
  const person = (await api(base, "/api/links/link", { a: p1.id, b: "e:gamma:3" })).id;
  await page.eval(`S.units = null; loadLib(); S.over.co = { target: ${JSON.stringify({ kind: "unit", id: person, name: "Holmes", type: "PER" })} }; S.over.co_n = 6; S.over.co_each = false; S.over.rel = "agent"; S.over.curve = "ov:per1k"`);
  await page.go("#/books");
  await page.go("#/over/combined");
  const heads = () => $$("#main h2").map(e => e.textContent), grids = () => $$("#main .hgrid");
  await until(() => heads().includes("Slice by slice") && !page.$("#main .loading"), "Holmes is counted through the three books");
  expect(heads().join("|") === "Books combined|Along the books|Words over the books|Slice by slice", "the panels: " + heads().join("|"));
  expect(byText("#main .subtabs button.on", /^Books combined$/) && page.$("#main .subtabs").querySelectorAll("button").length === 3, "the third sub-tab, open");
  expect(/Holmes is in 3 of the 3 selected books, each cut into 6 slices/.test(page.text()), "how many books and slices are used");
  expect(grids().length === 1 && grids().every(g => g.querySelectorAll("thead th.hc").length === 6), "six slices in the grid");
  const heading = g => [...g.querySelectorAll("thead th")].map(t => t.textContent.trim());
  expect(["Books", "Rising", "Falling", "Trend z", "χ²"].every(c => heading(grids()[0]).includes(c)) && !heading(grids()[0]).includes("Cramér's V"), "the agreement columns replace Cramér's V: " + heading(grids()[0]).join("|"));
  const row = grids()[0].querySelector("tbody tr"), cells = [...row.querySelectorAll("td")].map(c => c.textContent.trim());
  expect(/^[1-3]$/.test(cells[cells.length - 3]) && Number(cells[cells.length - 2]) + Number(cells[cells.length - 1]) === Number(cells[cells.length - 3]), "books used = rising + falling: " + cells.join("|"));
  // the fewest books a word must occur in to be tested, next to the minimum frequency
  const minRange = () => byText("#main label", /^Minimum range for the test$/).querySelector("input"), labels = $$("#main .controls label").map(l => l.textContent.trim());
  expect(labels.indexOf("Minimum range for the test") === labels.indexOf("Minimum frequency for the test") + 1, "the control sits next to the minimum frequency");
  const testedWords = () => Number(/(\d+) words? with at least/.exec($$("#main .hgrid")[0].parentElement.textContent)[1]);
  const before = testedWords();
  page.change(minRange(), "4");
  await until(() => page.eval("S.over.co_min_range") === 4 && /with at least \d+ occurrences in at least 4 books tested/.test(page.text()) && testedWords() === 0, "no word is in four books when there are three: none is tested");
  expect(JSON.parse(w.localStorage.getItem("analyser.over")).co_min_range === 4 && before > 0, "remembered; before it some words were tested (" + before + ")");
  page.change(minRange(), "1");
  await until(() => testedWords() === before && !/in at least \d+ books tested/.test(page.text()), "and back to one");
  // a row opens the sentences of the whole books, a cell those of its slice in every book
  page.click(row);
  await until(() => drawerOpen() && /alpha, [\d.]+% through/.test(drawerText()) && /beta, [\d.]+% through/.test(drawerText()) && /gamma, [\d.]+% through/.test(drawerText()), "a row shows sentences of every book");
  page.click(page.$("#drawerClose"));
  const heat = [...row.querySelectorAll(".hcell")].find(c => c.style.background), count = Number(/(\d+) of \d+ in all the books/.exec(heat.title)[1]);
  page.click(heat);
  await until(() => drawerOpen() && new RegExp(`^${count} sentence`).test(drawerText()), "a cell shows exactly its count of sentences: " + heat.title);
  page.click(page.$("#drawerClose"));
  // the curve: the combined line, then each book's own faintly behind it, kept when the figure changes
  const curve = () => $$("#main section.panel").find(x => x.querySelector("h2") && x.querySelector("h2").textContent === "Along the books");
  expect(curve().querySelectorAll(".chart-box svg polyline").length === 1 && !curve().querySelector("tbody a"), "one line, and no per-slice links into one book");
  const each = () => byText("#main label", /^Show each book$/).querySelector("input"), faint = () => curve().querySelectorAll("svg polyline[stroke-opacity]");
  each().checked = true; page.change(each());
  await until(() => faint().length === 3 && [...faint()].map(l => l.textContent).join() === "alpha,beta,gamma", "each book's own line, named by a tooltip");
  expect(JSON.parse(w.localStorage.getItem("analyser.over")).co_each === true, "and the choice is remembered");
  const figure = () => $$("#main select").find(s => [...s.options].some(o => o.value === "ov:names"));
  page.change(figure(), "ov:names");
  await until(() => page.eval("S.over.curve") === "ov:names" && faint().length === 3 && /Names/.test(curve().textContent), "choosing another figure keeps the books' lines, now of that figure");
  each().checked = false; page.change(each());
  await until(() => faint().length === 0, "switched off again");
  // the slices per book are the page's own
  const arcsN = page.eval("S.nar.seg.n");
  page.change(byText("#main label", /^Slices per book/).querySelector("input"), "4");
  await until(() => grids().length === 1 && grids().every(g => g.querySelectorAll("thead th.hc").length === 4), "four slices when asked for four");
  expect(page.eval("S.nar.seg.n") === arcsN && page.eval("S.over.co_n") === 4, "the Arcs and style setting is untouched");
  await api(base, "/api/links/reset", {});
  await page.eval("S.units = null; loadLib(); S.over.co = { target: null }; S.over.co_n = 20; S.over.co_each = false; S.over.co_min_range = 1; S.over.curve = \"ov:per1k\"");
});

await scenario("over the book: the chosen book is remembered, whatever else changes", async () => {
  await reset();
  const rows = (await api(base, "/api/units", { books: ALL })).rows;
  const watsonA = rows.find(r => r.name === "Watson" && r.books[0] === "alpha");
  const p1 = await api(base, "/api/links/link", { a: "e:alpha:1", b: "e:beta:5" });
  const person = (await api(base, "/api/links/link", { a: p1.id, b: "e:gamma:3" })).id;
  await page.eval(`S.units = null; loadLib(); S.over.target = ${JSON.stringify({ kind: "unit", id: person, name: "Holmes", type: "PER" })}; S.nar.seg = { ...S.nar.seg, mode: "slices", slice_by: "count", n: 5, scope: "book" }`);
  await page.go("#/books");
  await page.go("#/over");
  const bookSelect = () => $$("#main select").find(s => [...s.options].map(o => o.value).join() === "alpha,beta,gamma");
  await until(() => bookSelect() && bookSelect().value === "alpha" && $$("#main .hgrid").length >= 1, "a person in three books starts in the first");
  page.change(bookSelect(), "beta");
  await until(() => page.eval("S.over.book") === "beta" && bookSelect() && bookSelect().value === "beta" && /Holmes: 5 slices/.test(page.text()), "you choose the second book");
  // another target, found through the picker, in alpha only: it is shown in alpha, but the choice is not forgotten
  const search = () => page.$("#main .picker input[type=search]");
  const pickByName = async (text, books) => {
    page.input(search(), text);
    await until(() => $$("#main .picker .sugg div").some(d => d.textContent.includes(text) && d.textContent.includes(books)), "the picker offers " + text + " in " + books + " (it offered: " + JSON.stringify($$("#main .picker .sugg div").map(d => d.textContent)) + ", input: " + JSON.stringify(search() && search().value) + ")");
    const row = $$("#main .picker .sugg div").find(d => d.textContent.includes(text) && d.textContent.includes(books));
    row.dispatchEvent(new w.MouseEvent("mousedown", { bubbles: true, cancelable: true }));
  };
  await pickByName("Watson", "alpha ·");
  await until(() => page.eval("S.over.target.id") === watsonA.id && /Watson: 5 slices/.test(page.text()) && $$("#main section.panel b").some(b => b.textContent === "alpha"), "Watson (alpha only) is shown in alpha");
  expect(page.eval("S.over.book") === "beta", "while the remembered book is still beta");
  await pickByName("Holmes", "alpha + beta + gamma");
  await until(() => page.eval("S.over.target.id") === person && bookSelect() && bookSelect().value === "beta", "back to the person in three books: shown in beta again");
  expect(JSON.parse(w.localStorage.getItem("analyser.over")).book === "beta", "and remembered for the next visit");
  // the other places that show a book
  await page.go("#/entities/" + encodeURIComponent(person));
  await until(() => { const p = $$("#main section.panel").find(x => x.querySelector("h2") && x.querySelector("h2").textContent === "Over the book"); return p && [...p.querySelectorAll("select")].some(s => s.value === "beta") && p.querySelector(".chart-box svg"); }, "the profile's panel is in beta");
  await page.go("#/over/aligned");
  await page.eval(`S.over.al.a.target = ${JSON.stringify({ kind: "unit", id: person, name: "Holmes", type: "PER" })}; render()`);
  await until(() => $$("#main select").some(s => s.value === "beta" && [...s.options].length === 3), "side A of Two books aligned is in beta too");
  // the Book mode of a picker offers the book last chosen in any picker
  await page.go("#/over");
  page.click(byText("#main .picker .seg button", /^Book$/));
  const pickerBook = () => $$("#main .picker select").find(s => [...s.options].map(o => o.value).join() === "alpha,beta,gamma");
  await until(() => pickerBook(), "the Book mode lists the books");
  page.change(pickerBook(), "gamma");
  await until(() => page.eval("S.pickedBook") === "gamma", "gamma chosen");
  page.click(byText("#main .picker .seg button", /^Entity$/));
  page.click(byText("#main .picker .seg button", /^Book$/));
  await until(() => pickerBook() && pickerBook().value === "gamma", "opening the Book mode again offers gamma, not the first book");
  await api(base, "/api/links/reset", {});
  await page.eval("S.units = null; loadLib(); S.over.book = null; S.over.al_b_book = null; S.pickedBook = null");
});

await scenario("statistics: words over slices, then participants, a saved set and the chip editor", async () => {
  await reset();
  await page.go("#/stats");
  expect(/Choose the cases and add variables/.test(page.text()), "nothing is computed until Run");
  const fld = re => byText("#main .fld", re);
  page.click([...fld(/^Each case is/).querySelectorAll("button")].find(b => /^Equal slices$/.test(b.textContent)));
  page.change(byText("#main label", /^Slices per book/).querySelector("input"), "5");
  page.change(byText("#main label", /^Minimum sample/).querySelector("input"), "0");
  expect(!byText("#main label", /^Minimum range$/), "text pieces have no minimum range");
  several(/^Most frequent words…$/);
  page.change(byText("#main .svbulk label", /^How many/).querySelector("input"), "4");
  // a minimum range for the words: no word is in four of the three books, so nothing is added
  page.change(byText("#main .svbulk label", /^Minimum range/).querySelector("input"), "4");
  page.click(button(/^Add$/));
  await sleep(300); await page.settle("no words in four books");
  expect($$("#main .svar").length === 0, "a word must be in at least that many books: none are added for four");
  several(/^Most frequent words…$/);
  page.change(byText("#main .svbulk label", /^How many/).querySelector("input"), "4");
  page.change(byText("#main .svbulk label", /^Minimum range/).querySelector("input"), "3");
  page.click(button(/^Add$/));
  await until(() => $$("#main .svar").length === 4, "four word variables, one row each (words in all three books)");
  page.click(button(/^Run$/));
  await until(() => page.$("#main .hm-wrap svg") && /15 slices\./.test(page.text()), "a heatmap over the 15 slices of the three books");
  expect($$("#main .hm-wrap svg rect[rx]").length === 6, "a matrix of four variables has six cells (below the diagonal)");
  expect(/6 rows/.test(page.text()), "every pair as a table row");
  const showN = byText("#main label", /^N$/).querySelector("input");
  showN.checked = true; page.change(showN);
  await until(() => $$("#main .hm-wrap svg text").some(t => t.textContent === "N 15"), "N shown in each cell");
  page.click(button(/^Descriptives$/));
  await until(() => byText("#main th", /^SD$/) && $$("#main tbody tr").length === 4, "a row of descriptives per variable");
  page.click(button(/^Data$/));
  await until(() => byText("#main th", /^Text piece$/) && $$("#main tbody tr").length === 15, "the raw data: a row per slice");
  expect($$("#main tbody tr a")[0].getAttribute("href").startsWith("#/read/alpha/"), "a slice opens in the text");
  // the files for R: a zip from the server, with or without the example script as the Settings page says
  let blob = null, fileName = null;
  const realClick = w.HTMLAnchorElement.prototype.click;
  w.URL.createObjectURL = b => { blob = b; return "blob:test"; };
  w.HTMLAnchorElement.prototype.click = function () { fileName = this.download; };
  const zipNames = async () => new TextDecoder("latin1").decode(new Uint8Array(await blob.arrayBuffer()));      // file names are stored as they are
  page.click(button(/^Download for R \(\.zip\)$/));
  await until(() => /Downloaded the files for R/.test(page.$("#toast").textContent) && blob, "the R files were downloaded");
  const withExample = await zipNames();
  expect(blob.type === "application/zip" && /^analyser-statistics-\d{8}-\d{6}\.zip$/.test(fileName), "a zip named by the server: " + fileName);
  expect(["cases.csv", "cases_long.csv", "variables.csv", "dropped.csv", "load.R", "analysis_example.R"].every(f => withExample.includes(f)), "it holds the data files and the example script");
  await page.go("#/settings");
  page.click(button(/^Leave it out$/));
  await page.go("#/stats");
  page.click(button(/^Run$/));
  await until(() => $$("#main tbody tr").length === 15 && button(/^Download for R/), "the same run again (the Data view stays open)");
  blob = null;
  page.click(button(/^Download for R \(\.zip\)$/));
  await until(() => blob, "the R files without the script");
  const without = await zipNames();
  expect(without.includes("cases.csv") && !without.includes("analysis_example.R"), "the Settings toggle leaves the example script out");
  await page.go("#/settings");
  page.click(button(/^Include it$/));
  w.URL.createObjectURL = () => "blob:test";
  w.HTMLAnchorElement.prototype.click = realClick;
  await page.go("#/stats");
  // participants, with a 0/1 variable per gender
  page.click([...fld(/^Cases/).querySelectorAll("button")].find(b => /^Participants$/.test(b.textContent)));
  several(/^Every gender$/);
  await until(() => $$("#main .svar").length === 5, "a variable per gender is added");
  page.change(byText("#main label", /^Minimum sample/).querySelector("input"), "0");
  page.click(button(/^Run$/));
  await until(() => /\d+ participants?\./.test(page.text()) && byText("#main th", /^Participant$/), "participants as cases (the Data view stays open)");
  // participants have a minimum range of their own: nobody is in two books when no person is linked
  const minRange = () => byText("#main label", /^Minimum range$/).querySelector("input");
  page.change(minRange(), "2");
  page.click(button(/^Run$/));
  await until(() => /0 participants; \d+ left out \(fewer than [\d,]+ words, or none at all, or in fewer than 2 books\)/.test(page.text()), "participants in too few books are left out and counted");
  expect(page.eval("S.stats.cases.min_range") === 2, "remembered with the setup");
  page.change(minRange(), "1");
  page.click(button(/^Run$/));
  await until(() => /\d+ participants?\./.test(page.text()) && !/in fewer than/.test(page.text()), "and back to one");
  // a saved set, and the chips editor
  page.input(page.$("#main input[placeholder='Name for this set']"), "Speech");
  page.click(button(/^Save as a new set$/));
  await until(() => button(/^Save changes$/), "the set is now the open one");
  const sets = (await api(base, "/api/stats/sets")).sets;
  expect(sets.length === 1 && sets[0].name === "Speech" && sets[0].setup.cases.kind === "participants" && sets[0].setup.rows.length === 5, "the set keeps the whole setup");
  await page.go("#/settings");
  page.click(button(/^Chips$/));
  await page.go("#/stats");
  await until(() => $$("#main .svchip").length === 5 && !$$("#main .svar").length, "the chips editor lists the variables as chips");
  page.click($$("#main .svchip button")[0]);
  await until(() => $$("#main .svar").length === 1, "a chip opens its fields");
  page.click(button(/^Done$/));
  await until(() => !$$("#main .svar").length, "Done closes them");
  const chipOf = re => $$("#main .svchip").find(c => re.test(c.textContent));
  expect(chipOf(/^ATTRGender:/).style.getPropertyValue("--c") === page.eval("TC.GENDER"), "a gender variable's chip has the gender colour, as entity chips do");
  expect(!chipOf(/^WORDS/).style.getPropertyValue("--c"), "a word variable's chip has none");
  page.click(button(/^Clear$/));
  await until(() => !$$("#main .svchip").length && /No variables yet/.test(page.text()), "Clear empties the list (after a confirm)");
});

await scenario("statistics: linguistic layers (sentiment and every style figure) over books", async () => {
  await reset();
  await page.go("#/settings");
  page.click(button(/^One row each$/));                                              // the previous scenario chose chips
  await page.go("#/stats");
  page.click([...byText("#main .fld", /^Cases/).querySelectorAll("button")].find(b => /^Text pieces$/.test(b.textContent)));
  for (const x of $$("#main .svar-tools button[aria-label^='Remove']").reverse()) page.click(x);
  await until(() => byText("#main .fld", /^Each case is/) && !$$("#main .svar").length, "text pieces, and no variables left");
  page.click([...byText("#main .fld", /^Each case is/).querySelectorAll("button")].find(b => /^Books$/.test(b.textContent)));
  page.change(page.$("#main select[aria-label='Add a variable']"), "sentiment");
  await until(() => $$("#main .svar").length === 1 && /SENTIMENT/i.test($$("#main .svar .k")[0].textContent), "a sentiment variable");
  several(/^Every style figure$/);
  await until(() => $$("#main .svar").length === 9, "and the eight style figures");
  page.click(button(/^Run$/));
  await until(() => /3 books\./.test(page.text()) && button(/^Correlations$/), "the three books as cases");
  page.click(button(/^Correlations$/));                                             // the view last chosen stays open
  await until(() => page.$("#main .hm-wrap svg"), "a heatmap of the layers");
  page.click(button(/^Descriptives$/));
  await until(() => byText("#main td", /^MATTR$/) && byText("#main td", /^Sentiment \(mean compound\)$/), "descriptives of the layers");
  expect(byText("#main td", /^3/) && $$("#main td .rel").some(m => /Only 3 cases/.test(m.title)), "three cases: the N carries the ≈ marker, its tooltip says why (AL-PRIN-14)");
  expect($$("#main section.svstep > h2").map(x => x.textContent.replace(/^\d/, "")).join("|") === "Cases|Variables|Run", "the setup is three steps");
  expect(page.$("#main select[aria-label='Add several variables']") && !button(/^Every sound figure$/), "the bulk adders are a menu, not a row of buttons");
  page.click([...byText("#main .fld", /^Each case is/).querySelectorAll("button")].find(b => /^Sentences$/.test(b.textContent)));
  expect(/present \(0\/1\)” is often clearer/.test(page.text()) && byText("#main label", /^Minimum sample/).querySelector("input").placeholder === "1", "sentences: a hint, and a minimum of one word");
  page.click(button(/^Run$/));
  await until(() => /\d{3,} sentences\./.test(page.text()), "every sentence of the three books is a case");
});

await scenario("dialogue: word choice columns in Speaking style and the comparison, and facts on an entity's speech", async () => {
  await reset();
  await page.go("#/dialogue/speakers");
  await page.go("#/dialogue/voice");
  const choice = () => [...$$("#main select")].find(s => [...s.options].some(o => o.textContent === "Key figures"));
  const headers = () => [...$$("#main th")].map(t => t.textContent);
  await until(() => choice() && headers().some(t => /^Adjectives \(% of words\)/.test(t)), "the key figures are columns of Speaking style");
  expect(choice().value === "headline" && headers().some(t => /^Adjectives per verb/.test(t)) && headers().some(t => /^Dynamic verbs/.test(t)), "adjectives per verb and dynamic verbs among them");
  page.change(choice(), "ratios");
  await until(() => headers().some(t => /^Modifiers per head/.test(t)) && !headers().some(t => /^Adjectives \(% of words\)/.test(t)), "a section replaces the key figures");
  page.change(choice(), "");
  await until(() => !headers().some(t => /per verb/.test(t)), "and none takes them away");
  page.change(choice(), "headline");
  await until(() => headers().some(t => /per verb/.test(t)), "back to the key figures");
  // a speaker's row opens the comparison, whose two rows carry the same columns
  page.click(byText("#main td", /Holmes$/).closest("tr"));
  await until(() => $$("#main table").length >= 3 && [...$$("#main table")[1].querySelectorAll("th")].some(t => /per verb/.test(t.textContent)), "the comparison has them too");
  // the entity page's speech panel
  const holmes = (await api(base, "/api/units", { books: ALL })).rows.find(r => r.name === "Holmes" && r.books[0] === "alpha").id;
  await page.go("#/entities/" + encodeURIComponent(holmes));
  await until(() => byText("#main .facts-inline div", /Adjectives per verb/) && byText("#main .facts-inline div", /Dynamic verbs \(% of verbs\)/), "the entity's speech shows the two facts");
  expect(/\(all: /.test(byText("#main .facts-inline div", /Dynamic verbs/).textContent), "each beside everyone's figure");
});

await scenario("statistics: word choice, one variable and a whole section at once", async () => {
  await reset();
  await page.go("#/settings");
  page.click(button(/^One row each$/));
  await page.go("#/stats");
  page.click([...byText("#main .fld", /^Cases/).querySelectorAll("button")].find(b => /^Text pieces$/.test(b.textContent)));
  for (const x of $$("#main .svar-tools button[aria-label^='Remove']").reverse()) page.click(x);
  await until(() => byText("#main .fld", /^Each case is/) && !$$("#main .svar").length, "text pieces, and no variables left");
  page.click([...byText("#main .fld", /^Each case is/).querySelectorAll("button")].find(b => /^Books$/.test(b.textContent)));
  page.change(page.$("#main select[aria-label='Add a variable']"), "wordchoice");
  await until(() => $$("#main .svar").length === 1 && /CHOICE|Word choice/i.test($$("#main .svar .k")[0].textContent), "a word-choice variable");
  const kind = () => page.$("#main .svar select[aria-label='Kind of word-choice figure']"), figure = () => page.$("#main .svar select[aria-label='Word-choice figure']");
  expect(figure().value === "pos:ADJ" && !page.$("#main .svar select[aria-label='How a count becomes a value']"), "it starts as adjectives, and takes no measure");
  page.change(kind(), "ratios");
  await until(() => figure().value === "ratio:adj_verb", "a new kind of figure starts at its first figure");
  expect(page.eval("varLabel(S.stats.rows[0])") === "Adjectives per verb", "named by what it is");
  several(/^Word choice…$/);
  page.change(page.$("#main .svbulk select"), "verbgroups");
  page.click(byText("#main .svbulk button", /^Add$/));
  await until(() => $$("#main .svar").length === 3, "and the two verb groups");
  page.click(button(/^Run$/));
  await until(() => /3 books\./.test(page.text()) && button(/^Descriptives$/), "the three books as cases");
  page.click(button(/^Descriptives$/));
  await until(() => byText("#main td", /^Adjectives per verb$/) && byText("#main td", /^Dynamic verbs \(% of verbs\)$/) && byText("#main td", /^Static verbs \(% of verbs\)$/), "descriptives of the figures");
});

await scenario("statistics: speech sentence type, and sentence type and speech verbs in the most frequent words", async () => {
  await reset();
  await page.go("#/settings");
  page.click(button(/^One row each$/));
  await page.go("#/stats");
  page.click([...byText("#main .fld", /^Cases/).querySelectorAll("button")].find(b => /^Text pieces$/.test(b.textContent)));
  for (const x of $$("#main .svar-tools button[aria-label^='Remove']").reverse()) page.click(x);
  await until(() => byText("#main .fld", /^Each case is/) && !$$("#main .svar").length, "text pieces, and no variables left");
  page.click([...byText("#main .fld", /^Each case is/).querySelectorAll("button")].find(b => /^Books$/.test(b.textContent)));
  // the layer: a quote type, its own fields and the share of quotes as a measure
  page.change(page.$("#main select[aria-label='Add a variable']"), "speech");
  await until(() => $$("#main .svar").length === 1 && /TYPE|SPEECH/i.test($$("#main .svar .k")[0].textContent), "a speech sentence type variable");
  const measure = () => page.$("#main .svar select[aria-label='How a count becomes a value']");
  expect([...measure().options].some(o => o.value === "pct"), "its measures include the share of quotes");
  page.change(page.$("#main .svar select[aria-label='Sentence type of the quotes']"), "statement");
  page.change(measure(), "pct");
  const weigh = byText("#main .svar label", /^Weigh the speech verb/).querySelector("input");
  weigh.checked = true; page.change(weigh);
  page.change(page.$("#main select[aria-label='Add a variable']"), "speech");
  await until(() => $$("#main .svar").length === 2, "and a second one");
  page.click(button(/^Run$/));
  await until(() => /3 books\./.test(page.text()) && button(/^Descriptives$/), "the three books as cases");
  page.click(button(/^Descriptives$/));
  await until(() => byText("#main td", /^Statements in speech \(speech verb weighed\)$/) && byText("#main td", /^Questions in speech$/), "the variables are named by what they count");
  const cells = re => [...byText("#main td", re).closest("tr").querySelectorAll("td")].map(c => c.textContent);   // name, measure, N, M…
  expect(cells(/^Statements in speech/)[3] === "100.0" && cells(/^Questions in speech$/)[3] === "0.000", "the fixture's quotes are all statements: a mean of 100% and none");
  // the bulk add: words of statements only, then the speech verbs
  for (const x of $$("#main .svar-tools button[aria-label^='Remove']").reverse()) page.click(x);
  await until(() => !$$("#main .svar").length, "no variables left");
  several(/^Most frequent words…$/);
  page.change(byText("#main .svbulk label", /^How many/).querySelector("input"), "3");
  page.change(byText("#main .svbulk label", /^Sentence type/).querySelector("select"), "question");
  page.click(button(/^Add$/));
  await sleep(300); await page.settle("no words in questions");
  expect($$("#main .svar").length === 0, "no quote is a question: no words are added");
  several(/^Most frequent words…$/);
  page.change(byText("#main .svbulk label", /^How many/).querySelector("input"), "3");
  page.change(byText("#main .svbulk label", /^Sentence type/).querySelector("select"), "statement");
  page.click(button(/^Add$/));
  await until(() => $$("#main .svar").length === 3, "the three most frequent words of statements");
  for (const x of $$("#main .svar-tools button[aria-label^='Remove']").reverse()) page.click(x);
  several(/^Most frequent words…$/);
  const verbs = byText("#main .svbulk label", /^Speech verbs only/).querySelector("input");
  verbs.checked = true; page.change(verbs);
  page.click(button(/^Add$/));
  await until(() => $$("#main .svar").length === 1 && $$("#main .svar input[aria-label='Query']")[0].value === "say", "the one speech verb of the fixture, as a word");
});

await scenario("statistics: speech of a speaker, in words and quotes, and the most talkative speakers", async () => {
  await reset();
  await page.go("#/settings");
  page.click(button(/^One row each$/));
  await page.go("#/stats");
  page.click([...byText("#main .fld", /^Cases/).querySelectorAll("button")].find(b => /^Text pieces$/.test(b.textContent)));
  for (const x of $$("#main .svar-tools button[aria-label^='Remove']").reverse()) page.click(x);
  await until(() => byText("#main .fld", /^Each case is/) && !$$("#main .svar").length, "text pieces, and no variables left");
  page.click([...byText("#main .fld", /^Each case is/).querySelectorAll("button")].find(b => /^Books$/.test(b.textContent)));
  // the bulk add: the speakers who say the most, as speech variables
  several(/^Most talkative speakers…$/);
  page.change(byText("#main .svbulk label", /^How many/).querySelector("input"), "2");
  page.click(button(/^Add$/));
  await until(() => $$("#main .svar").length === 2 && $$("#main .svar .k").every(k => k.textContent === "Speech"), "two speech variables");
  const measure = () => page.$("#main .svar select[aria-label='How a count becomes a value']");
  expect(![...measure().options].some(o => o.value === "pct"), "words spoken have no share of quotes");
  page.change(page.$("#main .svar select[aria-label='Count the words they speak, or their quotes']"), "quotes");
  await until(() => [...measure().options].some(o => o.value === "pct"), "quotes may be a share of quotes");
  page.change(measure(), "pct");
  page.change(page.$("#main .svar select[aria-label='Only quotes of one sentence type']"), "statement");
  await until(() => byText("#main .svar label", /^Weigh the speech verb/), "a sentence type offers to weigh the speech verb");
  page.change(page.$("#main .svar select[aria-label='Count the words they speak, or their quotes']"), "words");
  await until(() => measure().value === "per1k", "back to words: the share of quotes gives way to per 1,000 words");
  page.click(button(/^Run$/));
  await until(() => /3 books\./.test(page.text()) && button(/^Descriptives$/), "the three books as cases");
  page.click(button(/^Descriptives$/));
  await until(() => byText("#main td", /^Speech of .+: statements$/) && byText("#main td", /^Speech of [^:]+$/), "the variables are named by whose speech they count");
  // the help: a variable's "?" opens the drawer at its kind, the Help button at the top
  page.click(page.$("#main .svar button[aria-label='Help: Speech']"));
  const drawer = page.$("#drawer"), helpBody = page.$("#drawerBody");
  expect(!drawer.hidden && /^Statistics: help/.test(page.$("#drawerTitle").textContent), "the help opens in the drawer");
  expect(helpBody.querySelector("[data-help='spoken'] h3").textContent === "Speech" && byText("#drawerBody dt", /^Words spoken$/), "with the Speech section and its options");
  expect(helpBody.querySelectorAll(".svhelp-toc button").length === helpBody.querySelectorAll("section.svhelp").length, "a contents entry per section");
  expect(helpBody.querySelector("[data-help='general:bar']") && byText("#drawerBody h3", /^Everywhere in aLex$/), "and, below, the help of the whole app");
  page.click(page.$("#drawerClose"));
  page.click(page.$("#helpBtn"));
  expect(!drawer.hidden && /^Statistics: help/.test(page.$("#drawerTitle").textContent) && helpBody.scrollTop === 0, "the top bar's ? opens this page's help at the top");
  page.click(page.$("#drawerClose"));
});

await scenario("lexicons: load the emotion lexicon, add one by pasting, fold, rename, edit words, remove", async () => {
  await reset();
  await page.go("#/narrative/lexicons");
  expect(byText("#main h2", /^Your lexicons$/) && byText("#main h2", /^Emotion$/) && button(/^Load the emotion lexicon…$/), "the emotion panel waits for its lexicon");
  await api(base, "/api/lexicons", { name: "NRC", text: "moor\tnature\t1\nhound\tfear\t1\nhill\tnature\t1\n", emotion: true });
  await api(base, "/api/lexicons", { name: "Archaic", text: "thou\nthee\nhast\n" });           // met for the first time: folded
  await page.eval("lexRedraw()");
  await page.settle("the lexicons");
  const panel = name => byText("#main section.panel", new RegExp("^" + name));
  await until(() => panel("Emotion").querySelector("svg[role=img]"), "the emotion arc is drawn (the first panel is open)");
  expect(/loaded from NRC/.test(panel("Emotion").textContent) && byText("#main .chip", /^nature/), "the emotion lexicon's source and its categories");
  expect(panel("Archaic").classList.contains("collapsed") && !panel("Archaic").querySelector("svg[role=img]"), "a lexicon met for the first time starts folded and loads nothing");
  page.click(panel("Archaic").querySelector(".cx"));
  await until(() => panel("Archaic").querySelector("svg[role=img]"), "expanding it draws its arc");
  // a lexicon typed into the box is shown open at once
  page.click(button(/^Type or paste a lexicon…$/));
  const box = page.$("#main .lexedit");
  box.querySelector("input").value = "Colours";
  box.querySelector("textarea").value = "red\nblue\nholmes\n";
  page.click(byText("#main .lexedit button", /^Create$/));
  await until(() => panel("Colours") && panel("Colours").querySelector("svg[role=img]") && !panel("Colours").classList.contains("collapsed"), "the new lexicon is open with its arc");
  // browse and edit the words
  const words = () => [...panel("Colours").querySelectorAll("details.note")].find(d => /^Words and categories/.test(d.textContent));
  words().open = true;
  await until(() => $$("#main .lexwords span").map(e => e.textContent).join() === "blue,holmes,red", "the words of the category are listed");
  page.input(panel("Colours").querySelector("input[type=search]"), "ho");
  expect($$("#main .lexwords span").map(e => e.textContent).join() === "holmes", "the search narrows the list");
  const inPanel = (name, re) => [...panel(name).querySelectorAll("button")].find(b => re.test(b.textContent.trim()));
  page.click(inPanel("Colours", /^Edit$/));
  await until(() => panel("Colours").querySelector(".lexedit textarea"), "the edit form");
  const edit = panel("Colours").querySelector(".lexedit");
  edit.querySelector("input").value = "Hues";
  edit.querySelector("textarea").value = "red\nblue\ngreen";
  page.click(byText("#main .lexedit button", /^Save$/));
  await until(() => byText("#main .chip", /^hues/) && !byText("#main .chip", /^colours/), "the category is renamed and plotted");
  expect((await api(base, "/api/lexicons")).lexicons.find(x => x.id === "colours").categories.hues === 3, "and saved with its three words");
  // rename the lexicon, then remove it
  page.click(inPanel("Colours", /^Rename$/));
  const ask = panel("Colours").querySelector("input[type=text]");
  ask.value = "Palette";
  page.click(inPanel("Colours", /^OK$/));
  await until(() => panel("Palette") && !panel("Colours"), "the lexicon has a new name");
  expect((await api(base, "/api/lexicons")).lexicons.some(x => x.id === "colours" && x.name === "Palette"), "its id stays");
  page.click(inPanel("Palette", /^Remove$/));
  await until(async () => (await api(base, "/api/lexicons")).lexicons.map(x => x.id).join() === "emotion,archaic", "a lexicon is removed (after a confirm)");
  const opts = await api(base, "/api/stats/options", { books: ALL });
  expect(opts.lexicons.map(x => x.name).join() === "Emotion,Archaic", "Statistics offers the remaining lexicons");
});

await scenario("damaged remembered settings don't break the page", async () => {
  w.localStorage.setItem("analyser.corp", "{ nope");
  w.localStorage.setItem("analyser.nar", JSON.stringify({ seg: "not an object", stylo: 5, arcKind: 7 }));
  w.localStorage.setItem("analyser.read", "[]");
  w.localStorage.setItem("analyser.collapsed", "42");
  await page.eval("S.sel = null");
  const state = page.eval(`(() => ({ corp: loadState("analyser.corp", {a: {b: 1}}), nar: loadState("analyser.nar", {seg: {mode: "slices"}, stylo: {x: 1}, arcKind: "entities"}) }))()`);
  expect(state.corp.a.b === 1 && state.nar.seg.mode === "slices" && state.nar.stylo.x === 1 && state.nar.arcKind === "entities", "damaged values fall back to defaults");
  await page.go("#/corpus/kwic");
  await page.go("#/narrative/arcs");
  await page.go("#/read/alpha");
  w.localStorage.clear();
});

await scenario("dialogue: 'Leave out verbs and adverbs' removes a verb from the Speech verbs tables and is kept in the settings", async () => {
  await page.go("#/dialogue/verbs");
  await until(() => byText("#main summary", /Leave out verbs and adverbs/) && /\d+ of \d+ quote/.test(page.text()), "the Speech verbs tab with its Leave-out box");
  expect(!/(?<!\d)0 of \d+ quote/.test(page.text()), "quotes have speech verbs to begin with");
  const field = label => byText("#main label.fld", new RegExp("^" + label)).querySelector("input");
  field("Verbs").value = " Say ";
  button(/^Save$/).click();
  await until(() => /(?<!\d)0 of \d+ quote/.test(page.text()), "no quote has a speech verb once “say” is left out");
  expect(JSON.stringify(page.eval("S.lib.settings.speech_skip")) === '{"verbs":["say"],"adverbs":[]}', "the list is saved, tidied");
  field("Verbs").value = "";
  button(/^Save$/).click();
  await until(() => !/(?<!\d)0 of \d+ quote/.test(page.text()), "the verbs are back once the list is empty");
});

await scenario("sound and rhythm: runs of repetitions in the drawer, a slice scanned, every cadence on and off", async () => {
  if (!page.eval("S.lib.sound")) return;                         // the pronunciation dictionary is optional
  await page.go("#/sound/runs");
  await until(() => byText("#main .subtabs button", /^Repetition$/) && page.$("#main table tbody tr"), "the runs of the first kind");
  const summary = () => (byText("#main p", /runs? of [\d,]+ words/) || {}).textContent;
  const was = summary(), wasWindow = page.eval("S.lib.settings.sound.window");
  page.change(page.$("input[aria-label='Run window (content words)']"), "1");
  await until(() => page.eval("S.lib.settings.sound.window") === 1 && summary() && summary() !== was, "a narrower window, saved and counted again at once");
  page.change(page.$("input[aria-label='Run window (content words)']"), String(wasWindow));
  await until(() => page.eval("S.lib.settings.sound.window") === wasWindow && summary() === was, "and back");
  page.click(byText("#main .subtabs button", /^Repetition$/));
  await until(() => page.eval("S.snd.kind") === "repetition" && byText("#main th", /^Word$/), "repetitions, listed by word");
  page.click(page.$("#main table tbody tr"));
  await until(() => drawerOpen() && $$("#drawerBody mark.rep").length > 1, "a repeated word's runs, the repetitions outlined");
  page.$("#drawerClose").click();
  await page.go("#/sound/scansion");
  await until(() => $$("#main .scan .sc-w").length > 20 && $$("#main .scan .sc-m").length > 20, "a slice word by word, the stresses above");
  const plain = $$("#main .scan .sc-w.cad").length;
  const every = () => byText("#main label", /Every cadence/).querySelector("input");
  every().checked = true; page.change(every());
  await until(() => $$("#main .scan .sc-w.cad").length > plain, "every cadence underlined when asked for");
  every().checked = false; page.change(every());
  await until(() => $$("#main .scan .sc-w.cad").length === plain, "and only the cursus again");
  await page.go("#/sound/words");
  await until(() => /have a guessed pronunciation/.test(page.text()) && page.$("input[aria-label='Word to correct']"), "the guessed words and the form");
  page.$("input[aria-label='Word to correct']").value = "Baskerville";
  page.click(button(/^Look up$/));
  await until(() => /from the dictionary/.test(page.text()) && page.$("input[aria-label='Pronunciation']").value === "B AE1 S K ER0 V IH2 L", "a word looked up, its sounds to start from");
  page.$("input[aria-label='Pronunciation']").value = "1 0 0";
  page.click(button(/^Save$/));
  await until(() => page.eval("S.lib.settings.sound.corrections.baskerville") === "1 0 0" && /Your corrections \(1 word\)/.test(page.text()), "a correction saved and listed");
  await page.go("#/settings");
  await until(() => $$("#settings-sound table tbody tr").length === 1, "Settings lists it too");
  page.click([...page.$("#settings-sound table tbody tr").querySelectorAll("button")].find(b => /Remove/.test(b.textContent)));
  await until(() => Object.keys(page.eval("S.lib.settings.sound.corrections")).length === 0, "and removes it");
});

console.log(JSON.stringify({ passed, failures, errorsAtEnd: page.errors }));
process.exit(0);
