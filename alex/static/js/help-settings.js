"use strict";
/* ---------- help: Settings ---------- */
/* The help of the Settings page (see help.js): one section per section of the page. The settings apply to the workspace in use and save
   as you make them (the theme and the Statistics display choices are kept in the browser). */

addHelp("settings", "Settings", [
  { id: "start", title: "How the page works", text: [
    "One page of settings for the workspace in use, a section per subject (the list on the left jumps to them). Choices save as you make them."] },

  { id: "appearance", title: "Appearance", items: [
    ["theme", "Theme", "Auto (follows your system), Light or Dark; the same in every workspace."],
    ["editor", "Statistics variables", "Show the variables of a Statistics list as one row each or as chips."],
    ["example", "R export: example script", "Whether the Statistics .zip for R holds an example analysis."]] },

  { id: "entities", title: "Entities", items: [
    ["plural", "Plural groups", "Include plural-group mentions (“they”, “Holmes and Watson”) in their members' figures by default, or count own mentions only. Also in the [...] menu."],
    ["min", "Minimum mentions", "Per entity type: entities with fewer mentions are left out of every page (2 matches BookNLP's own rule)."],
    ["count", "Count mentions", "Across the selected books combined, or in each book separately (a book where it falls below is left out)."],
    ["focus", "Focus", "Each page its own (the default): every page remembers what it looks at. One focus for every page: the entity, group, tag, gender or book you choose as a page's subject, or whose page you open, becomes the subject of every page (Over the book, Described as, Compare's first side, Speech verbs, How they speak, In-Depth Who Speaks); it is named at the top right, where × clears it. Filters, “Compared with”, second sides and Statistics keep their own choices, and a page that can't take the focus (a group where only one speaker fits) shows its own. Kept in this browser, for each workspace."]] },

  { id: "words", title: "Words", items: [
    ["freq", "Count word frequency", "Whether a tool's Minimum frequency is checked over the selected books together (default) or in each book separately; the number stays in each tool, and a line beside it says which way it counts."]] },

  { id: "sound", title: "Sound and rhythm", items: [
    ["window", "Window in content words", "How many content words apart words may be and still make a run (default 3)."],
    ["boundary", "Runs stop at", "A sentence end (default), a paragraph end, or nowhere."],
    ["alliteration", "Alliteration by", "The stressed syllable's first consonant (default), the word's first sound, or its first letter as spelled."],
    ["repetition", "Repetition is", "The same lemma among content words (default), the same word form, or the same lemma among all words."],
    ["corrections", "Pronunciations", "Your corrections of words' stress or sounds, with the form to add one (also under Sound and rhythm → Pronunciation)."]],
    text2: "They apply to Statistics, the Style tab, Sound and rhythm and Over the book alike.", more: "MEASURES.md 17" },

  { id: "folders", title: "Folders", items: [
    ["books", "Books folder", "The workspace's own folder of BookNLP output; Open shows it."],
    ["data", "Data folder", "Where the workspace keeps its library, corrections, topic models and lexicons."],
    ["others", "Other folders with books", "Folders to read books from where they lie: Add folder, Remove (the books themselves are never touched). What counts as a folder of books says what aLex looks for."]] },
]);
