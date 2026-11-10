"use strict";
/* ---------- help: Entities ---------- */
/* The help of the Entities page with no profile open (see help.js): the list on the left, choosing several, saved groups and the
   plural-group suggestions. An open profile has its own help (help-entity.js). */

addHelp("entities", "Entities", [
  { id: "start", title: "How the page works", text: [
    "Every person, place, organisation and so on that BookNLP found in the selected books, with at least the minimum mentions. Choose one on the left to open its profile on the right; or choose several and analyse them together."],
    example: "Click Holmes: his mentions, names, actions, speech and companions open on the right." },

  { id: "list", title: "The list", items: [
    ["types", "All, PER, LOC, FAC, GPE, VEH, ORG, VAR", "Show one entity type: people, locations, facilities (buildings, rooms), geo-political entities (countries, cities), vehicles, organisations, and Various (things coded by hand in the companion editor). The number is how many there are."],
    ["NARR", "Narrators", "One row per narrator role (“Watson, narrating”, “Narrator of …”): opens the narrator's profile, how much and how they narrate."],
    ["GENDER", "Gender", "One row per BookNLP-predicted gender (he/him, she/her, they/them…, and “No BookNLP gender prediction”): opens everyone of that gender pooled as one."],
    ["filter", "Filter by name or tag", "Keeps only the rows whose name or one of whose tags contains what you type."],
    ["sort", "Most mentioned / Name / Most books", "The order of the list; the arrow beside it reverses it."],
    ["row", "A row", "Name, the book it is in (or “linked · N books” for an entity linked across books), its tags, and its mentions on the right (words narrated, for a narrator)."],
    ["min", "Based on: at least N mentions…", "Entities below the minimum mentions are left out of every page. The link leads to Settings → Entities, where it is set per type; it is tinted when you changed it from the default."],
    ["more", "Show more", "The list shows 300 rows at first; this adds 500 more."]] },

  { id: "several", title: "Several entities as a group", text: [
    "Tick entities to analyse them together: one profile for all of them, their figures added up (a sentence or quote shared by two of them counts once)."],
    items: [["multi", "Select several", "Adds a checkbox to every row; click a row or its box to tick it."],
      ["shown", "Select shown", "Ticks everything that matches the type and the filter, not only the rows listed so far."],
      ["tag", "Select by tag…", "Adds every entity with that tag."],
      ["clear", "Clear", "Unticks everything."],
      ["together", "Analyse together →", "Opens the profile of the ticked entities counted as one."],
      ["plural", "Make plural group of the others…", "With two or more ticked: choose the entity that stands for the others together (“Holmes and Watson”); its mentions then count for them when Plural groups is on."],
      ["groups", "Saved groups…", "Opens a group you saved from a group's profile (Save as a group…)."]],
    example: "Tick Holmes, Watson and Lestrade, Analyse together: how the three investigators are referred to, act and speak as one." },

  { id: "plurals", title: "Possible plural groups", text: [
    "Shown when nothing is open: entities named after other people (“Holmes and Watson”), whose mentions and the “they” linked to them may mean those people together."],
    items: [["make", "Make plural group", "Makes it a plural group of the people named: with Plural groups on (in the [...] menu), what it says, does and is called counts for each of them too."],
      ["not", "Not plural", "Dismisses the suggestion for good."]] },
]);
