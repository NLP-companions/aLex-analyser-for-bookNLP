"use strict";
/* ---------- help: an entity's profile ---------- */
/* The help of a profile on the Entities page (see help.js): an entity's, a group's, a book's or a gender's pooled page, and a narrator's.
   Section ids are the ones the "?" beside a panel opens (relations, bybook, distinctive…). The maths is in MEASURES.md, sections 1–2. */

addHelp("entity", "Entity profile", [
  { id: "start", title: "How the page works", text: [
    "Everything aLex knows about one entity in the selected books, section by section, in the order of the questions they answer: who they are (how they're referred to, who they appear with), what they do, what they say, how they change (book by book, over the book) and what sets them apart (what's distinctive, topics); the side menu lists the sections under these groups. Click a row or a count anywhere for the sentences behind it. The same page serves a group of entities counted as one, a book's or a gender's entities pooled, and a narrator role (each described below)."] },

  { id: "header", title: "Name, tags and description", items: [
    ["name", "The name", "Click it to rename the entity (Enter saves, Escape cancels); the new name is used everywhere. Reset brings back the name found in the books."],
    ["tags", "Add tag", "Labels of your own (detective, servant…): filter the list by them, select by them, compare or count them elsewhere."],
    ["note", "A short description or label", "A note of your own, shown wherever the entity is."],
    ["plural", "+ Plural group / Plural group of", "Make this entity a plural mention of others (“Holmes and Watson”), add or remove members, or Not plural. A member shows the plural groups it belongs to."],
    ["links", "Every mention in the concordance · Described as", "Opens all its mentions on the Corpus page, or what it is described and called on the Described as page."]] },

  { id: "facts", title: "The figures at the top", items: [
    ["mentions", "Mentions", "Every reference BookNLP grouped with it: names, descriptions and pronouns."],
    ["share", "Share of people (or of its type)", "Its mentions as a share of all mentions of its type."],
    ["per1k", "Per 1,000 words", "Mentions per 1,000 words of the books it is counted in."],
    ["books", "Books, Pronouns", "In how many selected books it is counted; the pronouns BookNLP used for it."],
    ["based", "Based on: …", "The settings every figure on the page depends on: the minimum mentions, whether plural groups count for their members, and whether you linked it across books. Tinted words are set by you; each leads to where it is changed."],
    ["strip", "The strip", "Where the mentions fall in each book, start to end in 100 slices; darker means more."],
    ["where", "Where this comes from / In N books", "The coreference groups behind it: book, the name there, BookNLP's group ID, mentions, and whether it reaches the minimum."]],
    more: "MEASURES.md 1.1–1.4" },

  { id: "referred", title: "How they're referred to", items: [
    ["PROP", "Names", "Mentions BookNLP labels as proper names, most frequent first."],
    ["NOM", "Descriptions", "Noun phrases (the doctor, my friend)."],
    ["PRON", "Pronouns", "he, him, I…"],
    ["named", "Named or described in dialogue by", "Names and descriptions inside quotes, by the quote's speaker: who calls them what. Pronouns are left out."]],
    more: "MEASURES.md 1.5" },

  { id: "relations", title: "What they do and what's done to them", text: [
    "Words attached to the entity in the dependency parse, one list per tab; the number on a tab is how many there are. Click a row for the sentences."],
    items: [["agent", "Actions", "Verbs it is the subject of (Holmes said), or the agent of a passive."],
      ["patient", "Done to them", "Verbs it is the object of (they followed Holmes)."],
      ["poss", "Possessions", "Nouns it possesses (his pipe)."],
      ["mod", "Modifiers", "Adjectives, nouns in apposition and complements of “to be” (Brown was small)."],
      ["prep", "Prepositions and settings", "Every “verb or noun + preposition” it is attached to (went to London)."],
      ["cols", "Count, Per 1,000 words, %, Events, Supersense", "How often; per 1,000 words; its share of this list; how many BookNLP marks as actually happening; the most common WordNet supersense of the verb."]],
    more: "MEASURES.md 1.6" },

  { id: "bybook", title: "Book by book", text: [
    "Only for an entity in two or more selected books: how its figures and words change from one book to the next, in the order of the book list."],
    items: [["overview", "The overview table", "Each book on its own: mentions per 1,000 words, the share of names, descriptions and pronouns, and each list per 100 mentions."],
      ["words", "Words, book by book", "Choose a list (Actions, Modifiers…): each word's count and share per book, with χ², p and Cramér's V for whether it changes. Blue/red cells are clearly above/below what is expected (adjusted residual beyond ±1.96)."],
      ["test", "Minimum frequency for the test, Significance level, Bonferroni", "Words rarer than the minimum are listed without a test; the level and correction decide what counts as changing."],
      ["compare", "Compare two books in detail", "Opens the first two books side by side on the Compare page."],
      ["chart", "Chart: Most changed / Most frequent", "Draws the eight words that change most (smallest p) or are most frequent."],
      ["kinds", "Kinds of action, book by book", "Each book's actions by supersense, as % of that book's actions (the eight books with most actions)."]],
    more: "MEASURES.md 4" },

  { id: "over", title: "Over the book", text: [
    "A preview: how often the entity is mentioned, per 1,000 words, slice by slice from the start of a book to its end. Book chooses the book when it is in several; Based on: cut into… opens the setting of how the book is sliced (the shared Measure over setting of the Style and Over time pages; tinted when not 10 equal slices). Its words and kinds of action slice by slice, with heat grids, trends and tests, are on the Over the book page, which the link opens with this entity and book chosen."] },

  { id: "speech", title: "Speech", items: [
    ["type", "Sentence type", "Only questions, exclamations or statements (Weigh the speech verb lets “asked”, “cried” decide too)."],
    ["based", "Based on: …", "What the speech figures depend on: the narration words that end a conversation (set on the Dialogue page; it decides the estimated addressees), the words you left out of the speech verbs, and how many quotes by them or to them have addressees you set. Tinted words are set by you."],
    ["facts", "Quotes, Words spoken, Share of dialogue…", "How much they speak; words per quote, questions and MATTR (vocabulary variety) with all speakers' figure in brackets."],
    ["strip", "Where they speak", "Where their quotes fall in each book."],
    ["verbs", "Speech verbs, Adverbs", "How their quotes are introduced (said, cried; quietly)."],
    ["talks", "Talks to / Spoken to by ≈", "Whom they address and who addresses them, estimated (Found by: named in the quote, a reply, a speaker who continues, the next speaker, or set by you)."],
    ["narr", "Narrates", "When they also narrate: how much, with links to the narrator profile and to a comparison of their narrating and speaking voice."]],
    more: "MEASURES.md 5" },

  { id: "topics", title: "Topics", text: [
    "Which topics of your saved topic models this entity's text belongs to: its share of each topic and how far that is above the topic's average (× lift). Needs a topic model fitted on the Topics page that covers these books."] },

  { id: "kinds", title: "Kinds of action", text: [
    "Under the word table of What they do: its actions (or what is done to it, switched above the chart) grouped by the WordNet supersense BookNLP gave each verb: communication, cognition, perception, motion…"], more: "MEASURES.md 1.7" },

  { id: "with", title: "Appears with", text: [
    "Entities mentioned in the same sentence, most shared sentences first; click a row for those sentences. Beside it, a small network of its 15 most frequent companions (open the Network page for more)."], more: "MEASURES.md 1.8" },

  { id: "distinctive", title: "What's distinctive", text: [
    "Words of a list markedly more typical of this entity than of a comparison. List chooses Actions, Modifiers…; Compared with chooses everyone else (default), an entity, a group, a tag, a book or a gender. The other controls (Rank by, test, minimum frequency, level, Bonferroni, Show non-significant) are explained under “What's distinctive: comparing with a reference” below."],
    example: "Holmes's actions compared with everyone else: the verbs he uses far more than the others come out on top.", more: "MEASURES.md 1.9" },

  { id: "group", title: "A group of entities", text: [
    "Several entities counted as one (ticked on the left, Analyse together, or a saved group). Its entities are listed at the top: × removes one."], more: "MEASURES.md 2",
    items: [["save", "Save as a group…", "Keeps the ticked entities under a name (Saved groups… on the left opens it again)."],
      ["update", "Update “…” / Back to the saved group", "Stores your changes in the saved group, or drops them."],
      ["rename", "Rename, Delete group", "For a saved group; deleting leaves the entities as they are."],
      ["compare", "Compare this group with…", "Opens the Compare page with this group on one side."]] },

  { id: "pools", title: "A book's or a gender's page", text: [
    "A gender (from the Gender chip) or a book pools all its entities as one: the same figures as an entity's page, minus Speech, Topics and Appears with, with a table of the entities it pools."], more: "MEASURES.md 2" },

  { id: "narrator", title: "A narrator's page", items: [
    ["facts", "Words narrated, Paragraphs, Share of all narration", "Narration is every word outside quotes, paragraph by paragraph, given to the book's narrator unless you set a paragraph otherwise (Set by paragraph)."],
    ["voice", "Voice", "Their narration next to all narration and to the same character's dialogue: words per paragraph, questions, I/you/we, word length, MATTR."],
    ["link", "Link with another narrator", "Pools the narration of several roles as one voice (Watson in two books); × unlinks one, Unlink all dissolves the link."],
    ["dist", "What's distinctive", "Words more typical of this narration than of other narration, everyone's dialogue or their own dialogue; click a word for its concordance in narration."]],
    more: "MEASURES.md 6" },
]);
