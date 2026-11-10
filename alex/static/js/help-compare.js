"use strict";
/* ---------- help: Compare ---------- */
/* The help of the Compare page (see help.js): choosing the two sides, then each panel. The maths is in MEASURES.md, sections 1–4. */

addHelp("compare", "Compare", [
  { id: "start", title: "How the page works", items: [
    ["sides", "First, Second", "Two entities, groups, tags, genders or books, side by side; a side can be limited to some books. When a group and an entity overlap, the entity is left out of the group so the sides share no mentions."]] },

  { id: "overview", title: "Overview", text: [
    "Entities, mentions, books, mentions per 1,000 words, the shares of names, descriptions and pronouns, and each list per 100 mentions, for both sides."], more: "MEASURES.md 1" },

  { id: "kinds", title: "Kinds of action", text: [
    "Each side's actions by WordNet supersense, as % of its actions with a supersense."], more: "MEASURES.md 1.7" },

  { id: "words", title: "Words", text: [
    "Per list (Actions, Modifiers…): each side's most frequent words, then the words distinctive in either direction, with the comparison settings explained under “What's distinctive: comparing with a reference” below (here the minimum frequency holds on either side)."],
    more: "MEASURES.md 3" },

  { id: "split", title: "Split into characters", text: [
    "When the two sides are two books: every character in either, with their mentions in each (a character linked across the books gets one row)."] },

  { id: "over", title: "Over the book", text: [
    "Both sides along one book, as on the Over the book page: the book holding both, or Side A book and Side B book cut into the same number of slices when no book holds both."], more: "MEASURES.md 16.6" },
]);
