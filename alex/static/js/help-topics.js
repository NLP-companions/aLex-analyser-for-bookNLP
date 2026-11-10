"use strict";
/* ---------- help: Topics ---------- */
/* The help of the Topics pages (see help.js): the models list and the fit form ("home", with one section per group of settings), a
   model's overview ("model"), a topic's page ("topic") and comparing topics ("map", "pair", "grid"). `helpPlace` opens the section of the
   page you are on. The maths is in MEASURES.md, section 11. */

addHelp("topics", "Topics", [
  { id: "start", title: "How the pages work", text: [
    "A topic model finds groups of words that tend to occur together and says how much of each document belongs to each group. On fiction, topics are settings, activities and registers rather than themes: a map to explore, not findings. Everything depends on the document size, the words kept and the number of topics."],
    text2: "Needs scikit-learn (pip install scikit-learn)." },

  { id: "home", title: "Models", items: [
    ["list", "Models", "Every model you fitted: its books, method, topics, documents, coherence, diversity and how many topics are stable. Click a name to open it; Delete removes it."],
    ["fit", "Fit a new model", "Fits a model on the selected books with the settings below (change the books at the top right). Fitting and the stability runs can take a minute."],
    ["scan", "Compare numbers of topics from … to …", "Fits one model per number of topics and shows their coherence, diversity and stability; click a row to use that number."]],
    more: "MEASURES.md 11" },

  { id: "documents", title: "Fit: Documents", items: [
    ["unit", "Cut the books into", "Chunks of about N words (ending at a sentence; default 300), groups of N paragraphs, chapters or slices (the shared Measure over setting) or whole books. Smaller documents give more specific topics."],
    ["text", "Text", "Narration and dialogue, or either alone."]] },

  { id: "words", title: "Fit: Words", text: ["Which words, how they are counted and what is removed are always in view; the finer filters (minimum documents, maximum share, minimum letters, general words, also remove) are folded under Fine-tuning, whose line names their values and tints any you changed."], items: [
    ["pos", "Keep", "Which parts of speech count: nouns (default), verbs, adjectives, adverbs, proper nouns."],
    ["form", "Words as", "Lemmas (default) or word forms."],
    ["drop", "Remove", "Drop every token inside names (default), inside all mentions of people, inside all entity mentions, or nothing: otherwise character names make the topics."],
    ["min_df", "Minimum documents", "Words in fewer documents are removed."], ["max_df", "Maximum share of documents (%)", "Words in more than this share of documents are removed."],
    ["min_len", "Minimum letters", "Shorter words are removed."], ["generic", "Remove general words", "Leaves out very general words (thing, way, say, go)."],
    ["extra_stop", "Also remove", "Your own words to leave out, separated by spaces or commas."]] },

  { id: "model-settings", title: "Fit: Model", text: ["Method and number of topics are in view; seed, runs and LDA's alpha and beta are under Fine-tuning."], items: [
    ["nmf", "Method: NMF (tf–idf)", "Non-negative matrix factorisation: the default, usually clearer topics on small corpora."],
    ["lda", "Method: LDA", "Latent Dirichlet allocation; Alpha (lower: documents have fewer topics) and Beta (lower: topics have fewer words) tune it."],
    ["k", "Number of topics", "2–60. Too few merge things; too many split them."],
    ["seed", "Seed", "The random start: the same seed gives the same model."],
    ["runs", "Runs for stability", "Re-fits the model with other seeds to see which topics come back (1 skips the check)."]] },

  { id: "model", title: "A model's overview", items: [
    ["quality", "Coherence, diversity, stability", "Coherence (−1 to 1, higher is better): how often a topic's top words occur together. Diversity: the share of distinct words among all topics' top ten. Recurs: in how many re-runs a similar topic came back."],
    ["table", "Topics", "Each topic's top words, its share of the text, coherence, how often it recurs, and its share in each book."],
    ["cards", "Topic cards", "Per topic: a name of your own (type it in), its distinctive words, its share per book and its most typical passages. Open topic page → goes deeper."],
    ["rename", "Name, Compare topics →", "Rename the model; open the comparison of its topics."]],
    more: "MEASURES.md 11" },

  { id: "topic", title: "A topic's page", items: [
    ["words", "Words", "The topic's words with probability, uses, exclusive share (the part of a word's weight that is this topic's) and relevance. Rank by λ: 1 ranks the most probable words, lower values favour words exclusive to the topic. Click a word for its concordance."],
    ["where", "Where it occurs", "Each document shaded by its share, an arc over the chapters or slices, and a books table comparing each book's documents with the others (Mann–Whitney U)."],
    ["passages", "Passages", "The documents most given to the topic, in one book or all (choose how many)."],
    ["entities", "Entities", "Entities drawn to (or avoiding) the topic: their rate in topic text against elsewhere, as share, lift and score."],
    ["speech", "Speech", "Speakers and narrators drawn to the topic, per 1,000 dialogue or narration words."],
    ["groups", "Book details", "The topic by series, author, year or tag."],
    ["nav", "With another topic, Map of all topics, Grids", "Jump to a comparison."]],
    more: "MEASURES.md 11" },

  { id: "map", title: "Compare: Map of topics", items: [
    ["basis", "Topics are similar when they share words / appear in the same chunks", "Similarity by the cosine of their word weights, or by the correlation of their shares across documents."],
    ["thr", "Draw lines from similarity …", "Only pairs at least this similar are joined in the network."],
    ["views", "Network, Cluster tree, matrix, Pairs", "The same similarities as a network (click a topic or a line), a tree, a matrix and a sorted table."]] },

  { id: "pair", title: "Compare: Side by side", text: [
    "Two topics (First topic, Second topic): their words with each one's weight, their arcs along the books (sliced as set under Measure over), and the entities and speakers each draws."] },

  { id: "grid", title: "Compare: Grids", items: [
    ["groups", "Topic × book", "Each topic's share per book (or series, author, year): Share of the words, or Against all (above or below its average)."],
    ["mentions", "Topic × character", "Each topic's share of each entity's mentions, or against the topic's average (lift); choose types, a minimum and how many to show."],
    ["speakers", "Topic × speaker", "The same for speakers' words."]] },
]);
