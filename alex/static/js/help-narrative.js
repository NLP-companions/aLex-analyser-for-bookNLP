"use strict";
/* ---------- help: Style, Stylometry, Arcs, Sentiment, Lexicons ---------- */
/* The help of the pages at #/narrative (Style and Stylometry in the Style area, Arcs, Sentiment and Lexicons in Over time) (see help.js): one section per sub-tab, its id the sub-tab's name in the address (#/narrative/style
   opens the help at "style"), and the chapters-or-slices setting they share ("slices", also used by Sound and rhythm and Over the book).
   The maths is in MEASURES.md, sections 8–10. */

addHelp("narrative", "Style and Over time", [
  { id: "start", title: "How the page works", text: [
    "How things change across the books, and how the books are written: arcs, style figures, stylometry, sentiment and your lexicons. Everything is measured over equal slices of each book or over its chapters (the setting under the tabs)."] },

  { id: "slices", title: "Chapters or slices", items: [
    ["slices", "Measure over: Equal slices", "Each book cut into equal parts: a number per book (5, 10, 20 or 50), or one every so many words (Words per slice; a rest under half a slice joins the last). Slices line up by position, whatever the chapters."],
    ["chapters", "Measure over: Chapters", "Chapters start at headings found by the rules you tick: Heading words and numerals (Chapter, Book, Part…, IV., 12), Lines in capitals, Short lines without closing punctuation. A heading less than the minimum chapter length after the previous one is ignored (tables of contents, signatures). A book with fewer than two headings falls back to slices."],
    ["timeline", "Timeline: Book by book / Whole corpus / Books combined", "With several books: a separate line per book, or one unbroken line across every book (slices are then counted across the corpus, a short book getting fewer), or, on Arcs, Sentiment and Lexicons, Books combined: every book cut into the same number of equal slices and put together slice by slice, each book weighing the same (a slice's value is the mean of the books' own values; a book where a line has no value, such as a character not in it, is left out). Show each book draws every book's own line faintly behind. It needs equal slices by number; with chapters or words per slice it is greyed out. Style shows Book by book."],
    ["check", "Check the chapters found / List the segments", "Every chapter or slice with where it starts and its words. Wrong chapters? The links open each book's chapter editor, where you start, rename or remove them."]],
    more: "MEASURES.md 8.1" },

  { id: "arcs", title: "Arcs", text: ["One line per thing, rising and falling across the chapters or slices; hover a point for its value. The figures are folded under the chart (Numbers per chapter or slice)."],
    items: [["entities", "Characters and places", "Mentions per 1,000 words of the entities you choose: × removes one, the box adds one, Top 5 people and Top 5 places fill the list. An entity of one book has no line in the others (it isn't counted there), and when two you chose share a name, each gets its book: Holmes (alpha), Holmes (beta). A linked entity is counted in every book it is in."],
      ["events", "Events", "Tokens BookNLP marks as actually happening, per 1,000 words."],
      ["supersenses", "Supersenses", "Words of the WordNet supersenses you tick (v. motion, n. body…), per 1,000 words."],
      ["dialogue", "Dialogue", "The share of words inside quotes."],
      ["topics", "Topics", "The share of words of the chosen topics of a topic model (fit one on the Topics page)."]],
    example: "Characters and places, Holmes and Watson over 20 slices: where in the book each one takes over.", more: "MEASURES.md 8.2" },

  { id: "style", title: "Style", text: ["Figures of how each book (One row per: Book) or each chapter or slice is written; Chart picks the figure to draw. Below: parts of speech as % of words, word choice (Show: the key figures, or one section: ratios such as adjectives per verb, dynamic and static verbs, every kind of verb or noun; the Chart select draws any of them under “Word choice”). Sound and rhythm figures are on their own tab, next to this one."],
    items: [["words", "Words, Sentences", "Words (tokens other than punctuation) and BookNLP sentences."],
      ["sent_len", "Sentence length", "Mean words per sentence."], ["sent_sd", "Sentence length SD", "How much sentence length varies."],
      ["word_len", "Word length", "Mean letters per word."], ["mattr", "MATTR", "Vocabulary variety over 100-word windows, independent of length."],
      ["hapax", "Hapaxes %", "Words that occur once."], ["density", "Lexical density %", "Content words among all words."],
      ["dep_dist", "Dependency distance", "Mean distance between a word and the word it depends on: higher is harder to follow."],
      ["depth", "Tree depth", "How deeply sentences nest."], ["subord", "Subordinate clauses per sentence", "Clauses that hang off another (that…, because…)."],
      ["passive", "Passives per 1,000", "Passive constructions."], ["questions", "Questions %", "Sentences with a question mark."],
      ["dialogue", "Dialogue %", "Words inside quotes."], ["flesch", "Flesch Reading Ease", "Higher is easier to read (from sentence and word length)."],
      ["fk_grade", "Flesch–Kincaid grade", "The school grade the text reads at."],
      ["wordchoice", "Word choice", "Which kinds of word the text leans on: the share of words that are adjectives, adverbs, verbs or nouns, adjectives per verb, and the share of verbs that are dynamic (motion, contact, change…) rather than static (cognition, emotion, stative…). The same figures on Dialogue (per speaker) and Statistics (per case)."]],
    more: "MEASURES.md 8.3, 18" },

  { id: "stylometry", title: "Stylometry", text: ["Which texts are written most alike, from the frequencies of their most frequent words (as in Stylo for R)."],
    items: [["texts", "Compare: Texts", "Whole books, or chapters or slices (then the Measure over setting appears beside it, in the same panel). The Method row below sets how they are compared."],
      ["mfw", "Most frequent words", "How many of the corpus's most frequent words to compare (10–2,000)."],
      ["culling", "Culling % of texts", "Keep only words found in at least this share of the texts."],
      ["cosine", "Distance: Cosine Delta", "Burrows's Delta with cosine distance: usually the most reliable."],
      ["classic", "Classic Delta", "The mean absolute difference of the words' z-scores."], ["euclidean", "Euclidean", "Straight-line distance of the z-scores."],
      ["linkage", "Tree: Average, Complete, Ward", "How the cluster tree joins groups."],
      ["scope", "Text", "Everything, narration only or dialogue only."],
      ["color", "Colour by", "Book, author or series: above the charts it colours (it changes nothing in the figures)."], ["pronouns", "Leave out pronouns", "Pronouns follow who narrates more than who writes."],
      ["out", "Cluster tree, Map, Nearest texts, Distances", "The tree joins the closest texts first; the map spreads them on two principal components; then each text's nearest neighbours and every distance."]],
    more: "MEASURES.md 9" },

  { id: "sentiment", title: "Sentiment", text: [
    "VADER's score of each sentence, from −1 (negative) to +1 (positive), averaged over each chapter or slice; Also around adds a line for the sentences that mention chosen entities. The table gives each book's mean and its share of positive (≥ +0.05) and negative (≤ −0.05) sentences. Needs the vaderSentiment package."],
    more: "MEASURES.md 10" },

  { id: "lexicons", title: "Lexicons", text: ["Word lists of your own, in categories (such as the NRC emotion lexicon), each drawn as an arc of its categories per 1,000 words. The same lexicons are variables in Statistics."],
    items: [["emotion", "Load the emotion lexicon…", "Loads a file in the NRC format (word, emotion, 0/1) as the emotion lexicon."],
      ["file", "Load a file…", "A text, .csv or .tsv file: a word per line (one category, named after the lexicon), a word and a category per line (optionally with 1 or 0, as in NRC), or a column per category with the names in the first row. Words match by form, else lemma."],
      ["type", "Type or paste a lexicon…", "The same, typed or pasted into a box."],
      ["panel", "A lexicon's panel", "Its arc, with the categories to draw; Words and categories lists and searches its words; New category, Rename, Delete the category; Replace the words…, Rename, Remove the lexicon."]],
    more: "MEASURES.md 10" },
]);
