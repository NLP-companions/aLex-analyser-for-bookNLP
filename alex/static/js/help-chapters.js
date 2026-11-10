"use strict";
/* ---------- help: the chapter editor ---------- */
/* The help of the chapter editor (#/chapters/<book>, see help.js): the text view without layers, where chapter starts are set. */

addHelp("chapters", "Chapter editor", [
  { id: "start", title: "How the page works", text: [
    "The book as one scroll, with the chapters found automatically and your changes. Chapters decide every page that measures over chapters (Style, Arcs, Statistics, Over the book, topic documents)."],
    items: [["start", "Start a new chapter at this paragraph", "Makes the paragraph the first of a chapter."],
      ["rename", "Rename (Chapter title)", "Gives a chapter start its own title."],
      ["remove", "Remove this chapter start", "Its text joins the chapter before it."],
      ["reset", "Back to the automatic chapters", "Drops every change to this book's chapters."],
      ["done", "Done", "Back to reading."]],
    text2: "The automatic chapters follow the rules ticked under Measure over: Chapters (above the Style and Arcs pages).", more: "MEASURES.md 8.1" },
]);
