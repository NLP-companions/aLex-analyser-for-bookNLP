"use strict";
/* ---------- help: Narrators ---------- */
/* The help of the Narrators page (see help.js): suggestions from the "I" in each book's narration. The maths is in MEASURES.md,
   sections 6 and 13. */

addHelp("narrators", "Narrators", [
  { id: "start", title: "How the page works", text: [
    "Suggestions from the “I” in each book's narration (outside quotes): who narrates the book, and stretches told by someone else. Third-person books have no “I” and get no suggestions; set their narrator by hand under Library if you want one. Suggestions are only as good as BookNLP's grouping of “I” and its quote marks, so merge a split narrator and fix missing quote marks in the companion editor first."],
    more: "MEASURES.md 6, 13" },

  { id: "book", title: "Each book", items: [
    ["narrator", "Who the “I” in the narration belongs to", "Each candidate with its share of first-person mentions; Make the book's narrator sets it."],
    ["who", "Who is this?", "When BookNLP left the narrator's “I” as a group without a name, link it to a character here (the same links as everywhere)."],
    ["runs", "Paragraphs told by someone else", "Runs of paragraphs whose “I” belongs to another character, with sample sentences: Accept (they become paragraph exceptions), Not right (remembered), or Open in the text."],
    ["accepted", "Accepted", "The runs you accepted, each with Undo."]] },

  { id: "settings", title: "Settings", items: [
    ["max_gap", "Paragraphs without “I” allowed inside a run", "A run continues across up to this many paragraphs in a row with no “I”."],
    ["min_evidence", "Minimum “I” per suggestion", "Runs with fewer first-person mentions are not suggested."]] },
]);
