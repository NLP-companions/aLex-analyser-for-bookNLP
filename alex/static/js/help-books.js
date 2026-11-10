"use strict";
/* ---------- help: Library ---------- */
/* The help of the Library page (see help.js): where books come from, the book cards, collections, search, the export, and the Workspaces
   section below them. */

addHelp("books", "Library", [
  { id: "start", title: "Where books come from", text: [
    "Each workspace has a books folder of its own: put BookNLP output there (Open books folder shows it) and aLex finds new books when you come back to its window. To read books where they already lie, add their folders under Settings → Folders. A new export from the companion editor is picked up the same way."] },

  { id: "cards", title: "A book's card", items: [
    ["use", "The checkbox", "Ticks the book for analysis (the same choice as the book button); a card with an outline is in use."],
    ["details", "Edit details", "Title, author, year, series and tags, saved as you leave each field (tags separated by commas; click a tag chip to search for it). Series decides which books Entity Links suggests matches between."],
    ["narrator", "Narrator", "The book's narrator: a character (search the list) or Unnamed narrator. Narration (text outside quotes) is that narrator's voice."],
    ["export", "Export used", "Which of the book's BookNLP exports to read, when there are several."],
    ["original", "Original text", "Downloads the .txt the export was made from, when it lies beside it (aLex also uses it for the exact spacing between words)."],
    ["title", "The title", "Opens the book's own overview: its facts and, pooling every entity in it, the figures of an entity's page."]] },

  { id: "collections", title: "Collections", items: [
    ["list", "Collections (left)", "All books, In no collection, and your collections; click one to list its books and those of the collections inside it."],
    ["new", "New collection, New sub-collection", "A collection can sit inside another, like a folder; a book can be in several."],
    ["add", "＋ on a card, Add the books shown to a collection", "Files books in a collection; Take out of … removes one."],
    ["edit", "Rename, Move…, Delete", "Deleting a collection never deletes books."]] },

  { id: "find", title: "Search and export", items: [
    ["search", "Search the books", "By title, author, series, tag, year or id."],
    ["group", "Group by", "Series, author or nothing."],
    ["analyse", "Analyse the books shown", "Sets the book selection to whatever is listed."],
    ["zip", "Export selected books (.zip)", "The selected books' BookNLP files and your work on them (links, names, tags, notes, groups, collections, plural groups, narrator links, corrections, settings), with your topic models for those books and your keyword reference files. Import it as a workspace anywhere."]] },

  { id: "workspaces", title: "Workspaces", text: [
    "A workspace is a separate library: its own folders of books, links, groups, collections, corrections, topic models, reference files and settings. Nothing is shared between workspaces. The one in use is on the Workspace row of the [...] menu, which also switches."],
    items: [["make", "Make a workspace", "A name and, optionally, the folder its books are in; then Switch to it."],
      ["open", "Open folder", "Shows the workspace's folder (its books folder is inside)."],
      ["import", "Import", "Makes a workspace from an export zip: the books and everything in the zip are copied in; another workspace is never touched."],
      ["rename", "Rename, Remove from list", "Removing leaves its files where they are."],
      ["delete", "Delete…", "For a workspace aLex made: deletes its folder with everything in it, books included (type its name to confirm). The Default workspace and the one in use can't be removed or deleted."]] },
]);
