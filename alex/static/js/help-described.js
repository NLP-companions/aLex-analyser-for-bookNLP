"use strict";
/* ---------- help: Described as ---------- */
/* The help of the Described as page (see help.js): what to look at, the lists (one per kind of finding), how the columns split who says
   it, the voice, and what a cell can show. The maths is in MEASURES.md, section 14. */

addHelp("described", "Described as", [
  { id: "start", title: "How the page works", text: [
    "What an entity, group, tag, gender or book is described and called as, and by whom: each finding's describer is the speaker of the quote it is in, or the narrator of the paragraph (a narrator who is a character is that character). Click a cell for its sentences."],
    items: [["target", "What to look at", "The target. BookNLP often splits one place or person into many entities: Group's “add every entity named…” gathers them."]],
    more: "MEASURES.md 14.1" },

  { id: "kinds", title: "The lists", items: [
    ["mod", "Modifiers", "Adjectives, appositions and complements of “to be” (the old house, Brown was small)."],
    ["name", "Called: names", "The names used for it."], ["desc", "Called: descriptions", "The noun phrases used for it (the doctor)."],
    ["pron", "Called: pronouns", "The pronouns used for it."], ["agent", "Actions", "What it does."], ["patient", "Done to them", "What is done to it."],
    ["poss", "Possessions", "What it has."], ["prep", "Prepositions and settings", "Where and with what it is (in the room)."]] },

  { id: "split", title: "Split by who says it", items: [
    ["entity", "Each describer", "A column per describer, most findings first (Columns: how many; the rest are gathered in one)."],
    ["gender", "Gender", "A column per gender of the describer."], ["tag", "Tag", "A column per tag of the describer (and the untagged)."],
    ["book", "Book", "A column per book."], ["voice", "Narration or speech", "Two columns: in narration, in quotes."],
    ["custom", "Columns you pick", "Each column an entity, group, tag or gender of your choice (Add a column, Remove); findings in none of them are only in All."]],
    more: "MEASURES.md 14.2" },

  { id: "voices", title: "Voice", items: [
    ["both", "Narration and speech", "Every finding."], ["narration", "Narration", "Only findings outside quotes."], ["speech", "Speech", "Only findings inside quotes."]] },

  { id: "cells", title: "Show beside the count", items: [
    ["share", "Share", "The word's part of all that column's findings of this kind."],
    ["per1k", "Per 1,000 words", "Per 1,000 words the column's describers speak or narrate in the books the target is in."],
    ["ll", "Keyness (G²)", "Log-likelihood of the word in this column against all the other columns together; + is more typical of this column (a markedly typical cell is tinted)."],
    ["p", "p-value of the keyness", "The p of that G². It ranks rather than tests: findings are not independent."]],
    more: "MEASURES.md 14.3" },
]);
