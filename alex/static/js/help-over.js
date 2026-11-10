"use strict";
/* ---------- help: Over the book ---------- */
/* The help of the Over the book page (see help.js): one section per sub-tab ("single" for Within a book, "aligned", "combined"; `helpPlace`
   picks it from the address), then what they share: the words and kinds-of-action grids, the curve and the overview. The maths is in
   MEASURES.md, section 16. */

addHelp("over", "Over the book", [
  { id: "start", title: "How the page works", text: [
    "Follow an entity, group, tag, gender or a book's people through a book slice by slice: how often it appears, and how what it does, what is done to it and how it is described change from start to end. The slices are the shared Measure over setting (equal slices or chapters), always per book."] },

  { id: "single", title: "Within a book", items: [
    ["target", "Target", "An entity, group, tag, gender or book; Book picks which book when it is in several (your choice is kept when the target changes)."],
    ["other", "Compare with…", "A second target drawn beside the first, cut at the same slices; members of the first are left out of the second. Remove drops it."]] },

  { id: "aligned", title: "Two books aligned", items: [
    ["sides", "Side A, Side B", "A target in one book against the same target (Same target as A) or another in another book."],
    ["books", "Side A book, Side B book, Slices per book", "Both books are cut into the same number of equal slices, so slice k of n is the same relative stretch of each, whatever their lengths."]],
    more: "MEASURES.md 16.7" },

  { id: "combined", title: "Books combined", items: [
    ["target", "Target, Slices per book", "One target over every selected book it is in: each book cut into the same number of slices and put together slice by slice, every book weighing the same, to see what holds across books."],
    ["each", "Show each book", "Draws each book's own line faintly behind the combined one."],
    ["range", "Minimum range for the test", "A word is tested only when it occurs in at least this many books."]],
    more: "MEASURES.md 16.8" },

  { id: "grids", title: "Words and kinds of action over the book", text: [
    "One section, after the curve: its tabs choose the words of a list (Actions, Done to them, Possessions, Modifiers, Prepositions and settings) or the Kinds of action (the supersenses of its actions); one row of controls (View, Order, the test settings) applies to whichever is shown. A chart of the first eight rows, then the grid. Click a cell for its sentences."],
    items: [["heat", "View: Heat grid", "Each cell shaded by the word's share of that slice's list, relative to its own highest share (faint: absent; hatched: the slice has nothing in the list)."],
      ["numbers", "View: Numbers", "The counts and shares themselves."],
      ["freq", "Order: Most frequent", "Most frequent first."], ["rising", "Rising", "Steadily rising shares first (trend z above 0)."],
      ["falling", "Falling", "Steadily falling shares first."], ["changed", "Most changed", "Smallest χ² p first: the share differs most between slices."],
      ["tests", "χ², p, Cramér's V, Trend z, p", "χ²: does the share differ between slices at all? Trend (Cochran–Armitage): does it steadily rise (z > 0) or fall? Words below the minimum frequency are listed without tests."]],
    more: "MEASURES.md 16.3, 16.4" },

  { id: "curve", title: "Along the book", items: [
    ["figures", "Show: Figures", "Mentions per 1,000 words, the shares of names, descriptions and pronouns, each list per 100 mentions."],
    ["words", "Words", "One word's share of a list (choose the list and the word)."],
    ["actions", "Actions", "One kind of action's share."],
    ["sound", "Sound of speech", "With Sound of their speech ticked (and the pronunciation dictionary): stress, cadences and runs of what the target says in each slice."]],
    more: "MEASURES.md 16.5" },

  { id: "overview", title: "Slice by slice", text: [
    "Per slice: mentions, mentions per 1,000 words, the names / descriptions / pronouns %, and each list per 100 mentions; a slice links to its text. With Sound of their speech, a table of the sound figures follows."],
    more: "MEASURES.md 16.2" },

  { id: "elsewhere", title: "On a profile and on Compare", text: [
    "An entity's profile has a small Over the book (line charts only), and Compare draws the curve for both sides in the same book. Both use the same slices and the book you chose here."], more: "MEASURES.md 16.6" },
]);
