"use strict";
/* ---------- help: Corpus ---------- */
/* The help of the Corpus page (see help.js): one section per tool, its id the tool's name in the address (#/corpus/ngrams opens the help at
   "ngrams"), then what the tools share: where to search, the search settings, the two query languages and the word-type filter. The maths
   is in MEASURES.md, section 7. */

addHelp("corpus", "Corpus", [
  { id: "start", title: "How the page works", text: [
    "Corpus tools after AntConc, over the selected books: a concordance, a word list, n-grams, collocates and keywords. The box under the tool tabs says where to search and how words are matched; it applies to every tool."] },

  { id: "kwic", title: "Concordance", text: [
    "Every hit of a word, phrase or pattern with its context, from up to 20,000 hits (500 shown at a time: Show more). Click a line for its paragraph."],
    items: [["plot", "The plot", "A strip per book from start to end, each slice shaded by its hits, with hits and hits per 1,000 words."],
      ["books", "Book, Hits, Per 1,000 words, Dispersion (D)", "Hits per book; D (Juilland) near 1 means spread evenly over the book, near 0 bunched in a few places."],
      ["said", "Said by", "Who speaks the hits that fall inside quotes."],
      ["sort", "Sort 1, 2, 3", "Up to three sort levels: a place (the search term, a word 1–5 to its left L1–L5 or right R1–R5, or the book and position) and what to compare there; the arrow reverses a level."],
      ["word", "Word", "Alphabetical by the word form there."], ["lemma", "Lemma", "Alphabetical by its dictionary form."],
      ["pos", "Word class (POS)", "By its universal part of speech (NOUN, VERB…)."], ["tag", "Fine POS tag", "By its fine tag (NN, VBD…)."],
      ["freq", "Frequency", "How often that word occurs at that place among the hits, most frequent first: patterns stand out."],
      ["context", "Context", "How many tokens to show on each side."],
      ["matched", "Matched", "For a batch search: which line of the batch found each hit."],
      ["ctx", "Search in the context of the hits", "Keep only hits that have (or do not have) a second search within so many words left and right, optionally within the sentence; same syntax as the main search."]],
    example: "said with Sort 1 at R1 by Frequency: which words most often follow “said”.", more: "MEASURES.md 7.1, 7.2, 7.8" },

  { id: "wordlist", title: "Word list", text: ["The most frequent items in scope (up to 5,000), with frequency, per 1,000 words, range (in how many selected books) and dispersion. Click a row for its concordance."],
    items: [["word", "Words", "Word forms, lowercased unless Case sensitive is on."], ["lemma", "Lemmas", "Dictionary forms."],
      ["word_pos", "Word + POS", "A word form with its word class (left NOUN and left ADJ apart)."],
      ["word_pos_lemma", "Word + POS + lemma", "The three in separate columns."], ["pos_list", "POS", "Word classes themselves."],
      ["min", "Minimum frequency, Minimum range", "Leave out items rarer than this, or in fewer books than this."],
      ["filter", "Filter", "Show only items containing what you type."]],
    more: "MEASURES.md 7.3, 7.4" },

  { id: "ngrams", title: "N-grams", text: ["Runs of n consecutive words, most frequent first, like AntConc's clusters."],
    items: [["len", "Shortest, Longest", "The lengths to count, 2 to 8 words."], ["unit", "Count: Words / Lemmas", "Compare word forms or dictionary forms."],
      ["contains", "Containing, Where", "Only n-grams with this word Anywhere, as the First word or as the Last word."],
      ["sentence", "Within sentences", "Runs stop at a sentence end (they always stop at the edge of the scope, a quote say)."]],
    example: "Containing “said”, Where: Last word, 3 words: the phrases that lead into “said”.", more: "MEASURES.md 7.5" },

  { id: "collocates", title: "Collocates", text: ["Words that occur near the search term more than chance would have it, in a window to its left and right."],
    items: [["window", "Words to the left, Words to the right", "The window (0–20 words each side)."],
      ["mi", "MI", "Mutual information: how much more often than expected. Favours rare words."],
      ["t", "T-score", "Confidence that the pair is not chance. Favours frequent words."],
      ["ll", "Log-likelihood", "Evidence of association from a 2×2 table, with a p-value."],
      ["logdice", "logDice", "A balance of the two, comparable across corpora (14 is the maximum)."],
      ["mi3", "MI3", "MI with the observed count cubed, so frequent pairs weigh more."],
      ["n", "Frequency", "Plain count in the window."],
      ["sentence", "Keep windows within a sentence", "The window stops at the sentence's edge."]],
    example: "Collocates of “hound” by logDice: the words that keep its company.", more: "MEASURES.md 7.6" },

  { id: "keywords", title: "Keywords", text: ["Words markedly more frequent in the target (the selected books, in their scope) than in a reference. Click a row for its concordance."],
    items: [["target", "Target text", "Where in the selected books: everywhere, narration, dialogue or someone's speech."],
      ["books", "Reference: Books", "Tick the books to compare with; they may be the target's own books, if you compare different parts (dialogue against narration). Reference text: Same as the target, or another scope."],
      ["file", "Reference: Reference file", "Your own word lists (AntConc's, or any word + frequency list) or plain texts: Load reference files…, Remove."],
      ["count", "Count", "Word forms or lemmas."], ["range", "Minimum range", "Only words in at least this many target books."],
      ["negative", "Show negative keywords", "Also the words markedly less frequent in the target."]],
    text2: "Rank by, the test and the other comparison settings are explained under “What's distinctive: comparing with a reference” below.", more: "MEASURES.md 7.7, 3" },

  { id: "scope", title: "Search in", items: [
    ["all", "Everywhere", "The whole text."], ["narration", "Narration only", "Words outside quotes."], ["dialogue", "Dialogue only", "Words inside quotes."],
    ["speech", "Speech of…", "The quotes of an entity, group, tag or gender."]] },

  { id: "settings", title: "Search settings", items: [
    ["match", "Simple searches match: Word forms / Lemmas", "Whether “say” finds only “say”, or said, says, saying too."],
    ["case", "Case sensitive", "Holmes and holmes are different."],
    ["regex", "Regular expressions", "Each word or value is a full regular expression (s(ai|ay)d)."],
    ["wildcards", "Wildcards", "* any letters, ? one letter, a|b either, # any one word. Off: these are literal characters."],
    ["skip_punct", "Ignore punctuation", "Match and count words only, so “said Holmes” also finds “said, Holmes”."]] },

  { id: "syntax", title: "Simple and Pattern searches", text: [
    "Simple: one or more words, with wildcards (look*, s?ng, said|cried, the # of). Pattern: each token in square brackets with conditions joined by &, such as [lemma=\"say\" & tag=\"VBD\"]; != means not, [] any token. After a token: ? optional, * up to 10, + one to 10, {2} exactly two, {1,3} one to three.",
    "Batch: tick it to list several words, phrases or patterns, one per line; every line is tried and the hits merged (Ctrl/Cmd+Enter searches)."],
    items: [["word", "word", "The word form."], ["lemma", "lemma", "The dictionary form."], ["pos", "pos", "Universal POS (NOUN, VERB…)."], ["tag", "tag", "Fine POS tag (NN, VBD…)."],
      ["dep", "dep", "The dependency relation (nsubj, dobj…)."], ["ent", "ent", "Entity type of a mention covering the token (PER, LOC…)."],
      ["prop", "prop", "PROP, NOM or PRON for a mention covering it."], ["char", "char", "Name of the entity a covering mention refers to: [char=\"Holmes\"]."],
      ["ss", "ss", "Supersense (verb.communication, noun.person…)."], ["event", "event", "yes if BookNLP marks the token as an event."],
      ["quote", "quote", "in or out: inside a quote or not."], ["speaker", "speaker", "Name of the speaker of the quote the token is in."]],
    example: "[char=\"Holmes\"] [lemma=\"look\"]: Holmes (by any name or pronoun) followed by any form of look." },

  { id: "types", title: "Word types", text: [
    "The word list and the collocates can keep only some word classes (POS), entity types (words that are part of a mention of that type) and fine tags. Several choices in one group mean any of them; choices in different groups must all hold. In a word list, rates stay per 1,000 words of the whole text."] },
]);
