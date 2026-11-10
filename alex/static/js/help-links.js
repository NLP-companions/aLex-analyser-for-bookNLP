"use strict";
/* ---------- help: Entity Links ---------- */
/* The help of the Entity Links page (see help.js): linking the same person or place across books, by rule, by suggestion or by hand,
   and undoing it. The maths of the suggestions is in MEASURES.md, section 13. */

addHelp("links", "Entity Links", [
  { id: "start", title: "How the page works", text: [
    "BookNLP knows each book alone, so Holmes in one book and Holmes in another are two entities. Linking them makes one entity of them everywhere: its profile, Book by book, counts across books."] },

  { id: "auto", title: "Auto-link", text: [
    "Auto-link exact matches links, across your whole library, entities of different books that agree exactly on name, type and (for people) BookNLP's pronouns. Two of one book are left for you; so are places and things, which have no pronouns to check. Undo it like any other link."] },

  { id: "suggested", title: "Suggested links", items: [
    ["link", "Link", "Accepts a likely match found from the names. Suggestions are made only between books of the same series (set under Library)."],
    ["not", "Not the same", "Rejects it for good (kept even when links are reset)."]],
    more: "MEASURES.md 13" },

  { id: "hand", title: "Link by hand", text: [
    "Click either box to list the entities of every book (most mentioned first), type to narrow it or pick a type beside it, then Link these."] },

  { id: "linked", title: "Linked entities", items: [
    ["card", "A card", "One per linked entity, its book appearances inside: rename it (the name used in every view), tag it, Open profile, Unlink one appearance or Unlink all."],
    ["selected", "Unlink selected", "Tick several cards' own checkboxes to dissolve them at once."],
    ["reset", "Reset all links", "Dissolves every link, people and narrators alike."],
    ["narrators", "Linked narrators", "Narrator roles linked into one voice (on a narrator's page), listed the same way."]] },
]);
