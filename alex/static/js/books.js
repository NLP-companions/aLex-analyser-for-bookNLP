"use strict";
/* ---------- Library ---------- */
/* The Library page (#/books), laid out like the companion editor's: collections in a list on the left, and a card per book
   (title, details, collections, narrator, export) on the right; below them the Workspaces section (workspaces.js). */
/** Which collection the Library page shows ("all", "none" = in no collection, or a collection id) and how its table is grouped. */
S.libView = loadState("analyser.libview", { coll: "all", group: "none" });
/** Remember which collection the Library page shows and how it groups the books. */
const saveLibView = () => saveState("analyser.libview", S.libView);

/** The Library page: your library (collections, search and a card per book) and the workspaces. Settings are on their own page (settings.js). */
async function renderBooks(main) {
  await loadLib();
  const L = S.lib, cur = new Set(selected()), V = S.libView;
  let query = "", editing = null;      // editing: the id of the book whose details form is open
  const collById = () => Object.fromEntries(L.collections.map(c => [c.id, c]));
  if (!["all", "none"].includes(V.coll) && !collById()[V.coll]) V.coll = "all";        // the collection was deleted
  const saveBook = async (id, patch) => {
    await api("/api/books/" + encodeURIComponent(id), patch);
    Object.assign(L.books.find(b => b.id === id), patch);
    toast("Saved.");
  };
  /** A labelled text field for one detail of a book (tags are a comma-separated list); it saves when you leave it. */
  const field = (b, k, label, w) => h("label", {}, label, h("input", { type: "text", value: k === "tags" ? (b.tags || []).join(", ") : (b[k] ?? ""), style: { width: w },
    onchange: e => saveBook(b.id, { [k]: k === "tags" ? e.target.value.split(",").map(t => t.trim()).filter(Boolean) : e.target.value }) }));

  // ----- collections: a list on the left (nested ones indented); what it holds decides which books the cards show -----
  const treeBox = h("nav", { class: "collnav", "aria-label": "Collections" }), actionBox = h("div", { class: "navfoot" });
  const pathOf = c => c.parent ? pathOf(collById()[c.parent]) + " / " + c.name : c.name;
  const depthOf = c => c.parent ? 1 + depthOf(collById()[c.parent]) : 0;
  /** Send a change to the collections, keep the server's list, and redraw. Returns the reply. */
  const changeColl = async (path, body) => {
    const r = await api(path, body);
    L.collections = r.collections;
    if (!["all", "none"].includes(V.coll) && !collById()[V.coll]) V.coll = "all";
    drawTree(); drawTable();
    return r;
  };
  const anyCollection = () => new Set(L.collections.flatMap(c => c.books));
  /** The books the table shows: those in the open collection (and the collections inside it) that match the search. */
  const shownBooks = () => {
    const open = V.coll === "all" || V.coll === "none" ? null : new Set(collById()[V.coll].deep), unfiled = V.coll === "none" ? anyCollection() : null;
    return L.books.filter(b => bookMatchesQuery(b, query) && (open ? open.has(b.id) : unfiled ? !unfiled.has(b.id) : true));
  };
  function drawTree() {
    const open = id => { V.coll = id; saveLibView(); drawTree(); drawTable(); };
    const node = (id, label, n, depth, title) => h("button", { type: "button", "aria-pressed": String(V.coll === id), class: V.coll === id ? "on" : "", title, style: { paddingLeft: 10 + 14 * depth + "px" }, onclick: () => open(id) },
      h("span", {}, label), h("span", { class: "n" }, fmt(n)));
    treeBox.replaceChildren(node("all", "All books", L.books.length, 0), ...L.collections.map(c => node(c.id, c.name, c.deep.length, depthOf(c), pathOf(c))),
      node("none", "In no collection", L.books.length - anyCollection().size, 0));
    drawActions();
  }
  /** The buttons under the tree: make a collection, and (for the open one) rename, move, delete. Naming asks in place. */
  function drawActions() {
    const c = collById()[V.coll];
    const ask = (label, initial, ok) => {
      const box = h("input", { type: "text", value: initial, placeholder: "Name", "aria-label": label });
      const go = () => ok(box.value).then(drawActions, () => {});
      box.onkeydown = e => { if (e.key === "Enter") go(); if (e.key === "Escape") drawActions(); };
      actionBox.replaceChildren(box, h("button", { class: "btn small primary", onclick: go }, "OK"), h("button", { class: "btn small", onclick: drawActions }, "Cancel"));
      box.focus();
    };
    /** Ids of a collection and the collections nested in it (the ones it can't be moved into). */
    const descendantIds = id => new Set([id, ...L.collections.filter(x => x.parent === id).flatMap(x => [...descendantIds(x.id)])]);
    const moveTo = () => {
      const blocked = descendantIds(c.id);
      const pick = h("select", { "aria-label": "Move to" }, h("option", { value: "" }, "Top level"),
        L.collections.filter(x => !blocked.has(x.id)).map(x => h("option", { value: x.id, selected: x.id === c.parent }, "— ".repeat(depthOf(x)) + x.name)));
      actionBox.replaceChildren(pick, h("button", { class: "btn small primary", onclick: () => changeColl("/api/collections/" + c.id, { parent: pick.value || null }).then(drawActions, () => {}) }, "Move"),
        h("button", { class: "btn small", onclick: drawActions }, "Cancel"));
    };
    actionBox.replaceChildren(
      h("button", { class: "btn small", onclick: () => ask("New collection", "", name => changeColl("/api/collections", { name, parent: c ? c.id : null })) },
        c ? "New sub-collection" : "New collection"),
      c ? [h("button", { class: "btn small", onclick: () => ask("Rename", c.name, name => changeColl("/api/collections/" + c.id, { name })) }, "Rename"),
        h("button", { class: "btn small", onclick: moveTo }, "Move…"),
        h("button", { class: "btn small", onclick: () => { if (confirm(`Delete the collection “${c.name}”? Its books stay in the library.`)) changeColl("/api/collections/delete", { id: c.id }); } }, "Delete")] : null);
  }

  // ----- the book cards -----
  const tableBox = h("div"), toolbar = h("div", { class: "libtools" });
  let search;                                                              // the search box (filled in below); a tag chip puts its tag in it
  /** Download the selected books and your work on them as one .zip (the server builds it, see core/export.py). */
  const exportZip = async button => {
    const ids = selected();
    button.disabled = true;
    try {
      const r = await api("/api/export", { books: ids }, true);
      download((/filename="(.+?)"/.exec(r.headers.get("content-disposition") || "") || [])[1] || "analyser-export.zip", await r.blob());
      toast(`Exported ${plural(ids.length, "book")}.`);
    } finally { button.disabled = false; }
  };
  const downloadText = async b => download(b.id + ".txt", await (await api("/api/books/" + encodeURIComponent(b.id) + "/text", undefined, true)).blob());
  /** The collections a book is in (each can be left with its ×) and a drop-down to add it to another. */
  const collChips = b => {
    const mine = L.collections.filter(c => c.books.includes(b.id)), others = L.collections.filter(c => !c.books.includes(b.id));
    if (!L.collections.length) return null;                                // nothing to file it in yet: make a collection on the left
    return h("div", { class: "bcoll" }, "Collections", mine.map(c => h("span", { class: "tag", title: pathOf(c) }, c.name,
      h("button", { title: "Take out of " + c.name, onclick: () => changeColl("/api/collections/" + c.id, { remove: [b.id] }) }, "×"))),
      others.length ? h("select", { "aria-label": "Add " + b.title + " to a collection", onchange: e => { if (e.target.value) changeColl("/api/collections/" + e.target.value, { add: [b.id] }); } },
        h("option", { value: "" }, "＋"), others.map(c => h("option", { value: c.id }, pathOf(c)))) : null);
  };
  /** The export a book is read from: the newest, or an earlier one you pin; its folder and, when there is one, the original text. */
  const exportUsed = b => h("div", {}, "Export used",
    h("select", { "aria-label": "Export used for " + b.title, onchange: e => saveBook(b.id, { pinned: e.target.value || null }).then(() => { S.units = null; renderBooks(main); }) },
      h("option", { value: "" }, `Newest (${b.versions[0].stamp})`),
      b.versions.map(v => h("option", { value: v.folder, selected: b.pinned === v.folder }, v.stamp))),
    h("code", { title: b.folder }, b.folder.split(/[\\/]/).pop()),
    b.has_text ? h("button", { class: "linkbtn", title: "Download the original text this export was made from", onclick: () => downloadText(b) }, "Original text") : null);
  /** One book: a tick to analyse it, its title (opens its overview), details and tags (or the form to change them), collections,
      narrator and export. Redrawn on its own when the details form opens or closes. */
  const bookCard = b => {
    const card = h("article", { class: "bookcard" + (cur.has(b.id) ? " current" : ""), "data-book": b.id });
    const redraw = () => card.replaceWith(bookCard(b));
    const byline = [b.author, b.year, b.series].filter(x => x != null && x !== "").join(" · ");
    const use = h("input", { type: "checkbox", checked: cur.has(b.id), "aria-label": "Use " + b.title, title: "Analyse this book",
      onchange: e => {
        e.target.checked ? cur.add(b.id) : cur.delete(b.id);
        if (!cur.size) { e.target.checked = true; cur.add(b.id); return toast("Keep at least one book.", true); }
        card.classList.toggle("current", cur.has(b.id));
        setSel(L.books.map(x => x.id).filter(x => cur.has(x)));
      } });
    card.append(
      h("div", { class: "bhead" }, use,
        h("a", { class: "bn", href: "#/entities/" + encodeURIComponent("book:" + b.id), title: "Open the book's overview" }, b.title),
        b.title !== b.id ? h("span", { class: "bid" }, b.id) : null,
        byline ? h("span", { class: "bmeta" }, byline) : null,
        h("span", { class: "grow" }),
        b.error ? h("span", { class: "warn small" }, b.error) : h("span", { class: "bcount" }, `${fmt(b.words)} words · ${fmt(b.groups)} entities · ${fmt(b.quotes)} quotes`)),
      editing === b.id
        ? h("div", { class: "bedit" }, field(b, "title", "Title", "220px"), field(b, "author", "Author", "150px"), field(b, "year", "Year", "64px"), field(b, "series", "Series", "130px"),
          field(b, "tags", "Tags", "180px"), h("button", { class: "btn small primary", onclick: () => { editing = null; redraw(); } }, "Done"),
          h("span", { class: "hint" }, "Saved as you leave each field. Tags are separated by commas."))
        : h("div", { class: "btags" }, (b.tags || []).map(t => h("button", { class: "tagchip", title: `Show the books tagged “${t}”`, onclick: () => { search.value = query = t; drawTable(); } }, t)),
          h("button", { class: "linkbtn", onclick: () => { editing = b.id; redraw(); } }, byline || (b.tags || []).length ? "Edit details" : "Add author, year, series, tags")),
      collChips(b),
      h("div", { class: "bmore" }, h("div", {}, "Narrator", narratorSelect(b.id, null, b.narrator || null)), exportUsed(b)));
    return card;
  };
  /** Redraw the cards (grouped by series or author if chosen) and the "Analyse the books shown" button. */
  function drawTable() {
    const books = shownBooks(), key = { series: b => b.series || "(no series)", author: b => b.author || "(no author)" }[V.group];
    const groups = key ? [...new Set(books.map(key))].sort((x, y) => x.localeCompare(y)) : [null];
    const cards = groups.flatMap(g => {
      const inGroup = key ? books.filter(b => key(b) === g) : books;
      return [key ? h("div", { class: "lgroup" }, g, h("span", { class: "n" }, fmt(inGroup.length))) : null, ...inGroup.map(bookCard)];
    });
    tableBox.replaceChildren(books.length ? h("div", { class: "bcards" }, cards)
      : h("div", { class: "empty" }, !L.books.length ? h("div", {}, h("p", {}, "No books found yet. Put BookNLP output (a .tokens and an .entities file for each book) in this workspace's books folder, or add a folder where it already is under ",
          h("a", { href: "#/settings" }, "Settings → Folders"), ". aLex finds new books when you come back to this window."),
        h("div", { class: "row", style: { justifyContent: "center", flexWrap: "wrap" } }, h("code", { title: L.books_dir }, L.books_dir), openFolderButton({ folder: "books" }, "Open books folder", "btn primary")))
        : V.coll !== "all" && V.coll !== "none" && !query ? "No books in this collection yet. Open “All books” and add some with the ＋ on a book, or search and use “Add the books shown to…”."
        : "No books match."));
    // what can be done with the books listed: analyse just those, or file them all in a collection
    const filtered = books.length < L.books.length, targets = L.collections.filter(c => books.some(b => !c.books.includes(b.id)));
    useBox.replaceChildren(
      filtered ? h("button", { class: "btn small", title: "Set the books to analyse (top right) to the books listed here", disabled: !books.length,
        onclick: () => { const ids = books.map(b => b.id); cur.clear(); ids.forEach(i => cur.add(i)); setSel(ids); toast(`Analysing ${plural(ids.length, "book")}.`); drawTable(); } },
        `Analyse the ${plural(books.length, "book")} shown`) : null,
      books.length && targets.length ? h("select", { "aria-label": "Add the books shown to a collection", onchange: e => { if (e.target.value) changeColl("/api/collections/" + e.target.value, { add: books.map(b => b.id) }); } },
        h("option", { value: "" }, `Add the ${plural(books.length, "book")} shown to…`), targets.map(c => h("option", { value: c.id }, pathOf(c)))) : null);
  }
  const groupBox = h("div", { class: "fld" }), useBox = h("div", { class: "row" });
  const drawGroup = () => groupBox.replaceChildren("Group by", seg([["none", "Nothing"], ["series", "Series"], ["author", "Author"]], V.group, v => { V.group = v; saveLibView(); drawGroup(); drawTable(); }));
  let searchTimer;
  search = h("input", { type: "search", placeholder: "Title, author, series, tag, year or id", "aria-label": "Search the books",
    oninput: e => { query = e.target.value; clearTimeout(searchTimer); searchTimer = setTimeout(drawTable, 150); } });
  toolbar.append(h("label", { style: { flex: "1 1 240px" } }, "Search", search), groupBox, useBox,
    h("button", { class: "btn small", title: "Download the books ticked under Use (and the ones chosen at the top right) with your links, groups, collections and corrections as one .zip",
      onclick: e => exportZip(e.currentTarget) }, "Export selected books (.zip)"));
  drawGroup(); drawTree(); drawTable();
  const problems = [...L.problems, ...(L.state_notes || []), ...L.books.flatMap(b => (b.problems || []).map(p => `${b.title}: ${p}`))];
  const workspaces = await workspacePanel();
  main.replaceChildren(h("div", { class: "page" },
    h("h1", {}, "Library"),
    h("p", { class: "lede" }, "Your books, how they are grouped, and the workspaces they live in."),
    h("section", { class: "lsec" }, h("h2", {}, "Books"),
      h("div", { class: "libgrid" }, h("div", {}, treeBox, actionBox), h("div", {}, toolbar, tableBox,
        problems.length ? h("div", { class: "warn small", style: { marginTop: "8px" } }, problems.map(p => h("div", {}, p))) : null,
        note("About these cards", "Tick a book to analyse it (the tick is the same as in the Books menu at the top right); a card with an outline is in use. Changes save as soon as you leave a field.",
          "Collections work like folders that nest, except that a book can be in several at once: make one on the left, then add books to it with the ＋ on a book. Click a collection to list its books (and those of the collections inside it). Deleting a collection never deletes books. Search looks in title, author, series, tags, year and id; “Analyse the books shown” sets the book selection to whatever is listed.",
          "If you export from the companion editor, each export goes in its own dated folder. The newest is used unless you choose an earlier one under Export used. When you export again, the analyser picks it up next time you return to this window.")))),
    workspaces,
    h("p", { class: "libfoot" }, "Where to find books, minimum mentions and plural groups are in ", h("a", { href: "#/settings" }, "Settings"), ".")));
}
