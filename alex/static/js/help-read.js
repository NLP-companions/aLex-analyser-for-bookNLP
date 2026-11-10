"use strict";
/* ---------- help: Read ---------- */
/* The help of the text view (see help.js): reading, the layers, the side panel and the corrections made there. The chapter editor, which
   shares the view, has its own help (help-chapters.js). */

addHelp("read", "Read", [
  { id: "start", title: "How the page works", text: [
    "The text of a selected book as one scroll: chapters (or slices, as set under Measure over) load as you scroll, each with a heading, every paragraph with its number in the margin. The menus at the top stay frozen above a position bar that shows where you are and jumps between chapters. “Open in the text” links elsewhere land here, at the spot."],
    items: [["book", "Book", "Which selected book to read."], ["legend", "The type legend", "Click a type to hide or show its entities."],
      ["edit", "Edit chapters", "Opens the chapter editor for this book."]] },

  { id: "layers", title: "Show", items: [
    ["entities", "Entities", "Mentions underlined in their type's colour."],
    ["quotes", "Quotes and speakers", "Each quote marked, with speaker → addressees."],
    ["narrators", "Narrators", "Each paragraph's narrator in the margin."],
    ["events", "Events", "Words BookNLP marks as actually happening."],
    ["supersenses", "Supersenses", "WordNet supersenses of nouns and verbs."],
    ["sentences", "Sentence numbers", "Each sentence's number inside the text."],
    ["topics", "Topics", "Bands for the topics of a topic model in each passage (choose the model, all topics or one)."],
    ["sound", "Sound and rhythm", "Each word's stresses above it (/ stressed, x unstressed; red when guessed), the runs of the kind you choose coloured (Colour the runs of), repetitions outlined, cursus cadences named. The run settings beside it (Run window, Runs stop at, Alliteration by, Repetition is) are the workspace's; a change marks the text again at once. Needs the pronunciation dictionary."]] },

  { id: "side", title: "The side panel and corrections", items: [
    ["name", "Click a name", "Its entity and profile; a pronoun or description shows what it is attributed to."],
    ["quote", "Click a quote", "Its speaker and addressees: add or remove addressees, Everyone present, Back to the estimate; the conversation's listeners, Start a new conversation here or Join the previous conversation."],
    ["narr", "Click a narrator label", "Change the paragraph's narrator, also for the next few paragraphs or Apply to this whole chapter (paragraph exceptions, shown as Set by paragraph)."]],
    text2: "Your corrections replace the estimates everywhere and are marked as yours. Speakers and mentions are corrected in the companion editor." },
]);
