"use strict";
/* ---------- help: Statistics ---------- */
/* The help of the Statistics page (see help.js): what every part of the page does, every kind of variable with each of its options, the
   measures, the bulk adds and the results, in plain words with an example each. The "?" of a variable opens it at that variable's kind
   (a kind's section has the kind as its id). The maths is in MEASURES.md, section 15 (and 17 for sound and rhythm). Every option the
   server knows has an entry here (tests/test_help.py checks the keys). */

addHelp("stats", "Statistics", [
  { id: "start", title: "How the page works", text: [
    "Statistics measures things you choose (the variables) in pieces of text or in characters (the cases), then shows how the variables go together (correlations), what their values look like (descriptives) and the values themselves (data).",
    "Work through the three steps: 1 Cases (what the rows are), 2 Variables (add them with “+ Add a variable…”, one of a kind, or “Add several…”, many at once), 3 Run (the coefficient, the correction and the split, then Run). Nothing is counted until you run.",
    "A figure from fewer than 30 cases (an r, an N in the descriptives) carries a small ≈: such figures swing a lot, so read them with care. Point at it for why.",
    "Each case has a sample: the words it is measured in. A variable is counted in each case's sample and becomes one number per case."],
    example: "Cases: chapters. Variables: “Mentions of Holmes” and “Speech of Watson”. Run: do chapters with more Holmes have more Watson talking?" },

  { id: "sets", title: "Saved sets", text: [
    "A saved set keeps the whole setup (cases, both lists, coefficient, correction, split) under a name, so you can come back to it. Sets travel in the export zip."],
    items: [["open", "Open a saved set…", "Replaces the page's setup with the set's."],
      ["save", "Save changes", "Stores the setup as it is now in the set you opened."],
      ["revert", "Revert", "Goes back to the set as it was saved."],
      ["rename", "Rename, Delete", "Renames or deletes the set; deleting leaves the page's setup as it is."],
      ["new", "Save as a new set", "Stores the setup under the name you type."]] },

  { id: "cases", title: "Cases", text: [
    "The cases are the rows of the data: every variable gets one value per case. Text pieces are parts of the books; participants are characters taken as people in a study, each with their own sample of text."],
    items: [["pieces", "Text pieces", "Parts of the selected books. Their sample is their words (in the chosen part of the text)."],
      ["participants", "Participants", "Entities (characters, groups, narrators). Their sample is chosen below: what they say, what is said about them…"]],
    more: "MEASURES.md 15.1" },

  { id: "pieces", title: "Text pieces", text: ["What one case is, when the cases are text pieces."],
    items: [["slice", "Equal slices", "Each book cut into equal parts: a number per book (Slices per book, default 10) or one every so many words (Words per slice; a rest under half a slice joins the last). Slices of every book line up by position, whatever the chapters."],
      ["sentence", "Sentences", "Every BookNLP sentence is a case. Thousands of tiny cases: most counts are 0 or 1, so “present (0/1)” is often clearer than a rate, and even tiny correlations come out “significant”."],
      ["chapter", "Chapters", "The chapters as found (your chapter edits apply). A book without headings falls back to slices."],
      ["book", "Books", "Each selected book is one case. Few cases: correlations need at least 3, and many more to mean much."],
      ["scope", "Words counted", "Which part of the text makes up each piece's sample: everywhere, narration only, dialogue only, or the speech of someone you pick (an entity, group, tag or gender)."]],
    example: "Equal slices, 20 per book, dialogue only: each case is the dialogue of one twentieth of a book." },

  { id: "samples", title: "Participants", text: ["Who takes part, and what text each one is measured in."],
    items: [["population", "Who takes part", "Every person above your minimum mentions, or the entities, group, tag or gender you choose. Entities linked across books are one participant."],
      ["speech", "What they say", "The words of every quote they speak (a plural speaker's quotes count for its members when plural groups count for them)."],
      ["speech_narration", "What they say and narrate", "Their quotes plus the narration of every paragraph they narrate (a first-person narrator who is a character is that character)."],
      ["narrators", "Narrators who aren't a character take part", "With “say and narrate”: an unnamed narrator, or narrators you linked, are participants of their own."],
      ["sentences", "Sentences mentioning them", "Every sentence that mentions them, whoever says it. A sentence that mentions two participants counts for both."],
      ["findings", "What is said about them (Described as)", "Their Described-as findings (actions, modifiers, possessions…), counted in findings, not words. Word queries are then matched against each finding's word; rates are % of findings."]],
    example: "Participants: every person, sample “What they say”: one row per character, measured in their own speech." },

  { id: "minimum", title: "Minimum sample and range", items: [
    ["min", "Minimum sample (words)", "Cases with fewer words are left out, and the page says how many. Default 100 (1 for sentences; for the findings sample: Minimum findings, default 10). A rate from a tiny sample swings wildly: three words with one “the” is 333 per 1,000."],
    ["min_range", "Minimum range", "Participants only: those in fewer of the selected books are left out. Default 1 (no limit). Useful with people linked across books."]] },

  { id: "lists", title: "Lists of variables", text: [
    "One list correlates every variable with every other (a matrix). Tick “A second list” to correlate each row variable with each column variable instead (rows × columns). A list holds at most 30 variables.",
    "Each variable has a name box (optional: your name replaces the automatic one in the results), ↑ ↓ to move it, × to remove it and ? for this help. Clear empties a list (after asking). On the Settings page you can show variables as chips instead of rows; a chip about entities has the colour of their type."] },

  { id: "query", title: "Words", text: [
    "Hits of a word, lemma, phrase or pattern, written as on the Corpus page, counted in the case whose sample holds the hit's first word. Every hit counts (no 20,000 limit)."],
    items: [["simple", "Simple", "Words and phrases: holmes, wo* (wildcard), a|b (either), “the moor” (a phrase). Several lines are alternatives."],
      ["pattern", "Pattern", "The Corpus pattern language, token by token: [lemma=\"say\"] [pos=\"ADV\"]."],
      ["word", "Word forms", "Matches the words as written (said, says are different)."],
      ["lemma", "Lemmas", "Matches the dictionary form (say covers said, says, saying)."],
      ["finding", "All findings / one kind", "Only in the findings sample: count only findings of one kind (actions, modifiers…)."]],
    example: "“indeed” per 1,000 words over chapters: how much each chapter uses the word.", more: "MEASURES.md 15.2" },

  { id: "mentions", title: "Mentions", text: [
    "Mentions of an entity, group, tag, gender or type, counted where the mention starts. A participant's mentions of themselves count too (“I” in Watson's speech is a mention of Watson). A mention credited to two of the target's groups counts once."],
    items: [["", "All mentions", "Names, descriptions and pronouns."],
      ["PROP", "Names", "Proper names only (Holmes, Mr. Sherlock Holmes)."],
      ["NOM", "Descriptions", "Noun phrases (the detective, my friend)."],
      ["PRON", "Pronouns", "he, him, I, me…"]],
    example: "Mentions of Holmes: pronouns, per 1,000 words, over slices: where in the book he is referred to as “he”.", more: "MEASURES.md 15.2" },

  { id: "spoken", title: "Speech", text: [
    "Speech of an entity, group, tag or gender: the words they speak or their quotes, in each case's sample. Speakers are as on the Dialogue pages; a quote the target says through several of its members counts once."],
    items: [["words", "Words spoken", "Every word of their quotes, counted in the case that holds it. Per 1,000 words this is their share of the sample (‰)."],
      ["quotes", "Quotes", "How many of their quotes start in the case's sample. Quotes also offer the measure “% of quotes”: their share of all the sample's quotes."],
      ["type", "Every sentence type / Questions / Exclamations / Statements", "Only quotes of one type: a quote with ? is a question, with ! an exclamation, else a statement."],
      ["weigh", "Weigh the speech verb", "Also lets the speech verb decide when the quote has no ? or !: “asked” makes a question, “cried” an exclamation."]],
    example: "Speech of Watson: quotes, questions, % of quotes, over chapters: how much of each chapter's talk is Watson asking.", more: "MEASURES.md 15.2" },

  { id: "attribute", title: "Attribute", text: [
    "A figure of the case itself, not counted in its sample. Participants and text pieces have different attributes; one that doesn't fit the cases gets a note and no values."],
    items: [["in", "Is one of (0/1)", "Participants: 1 if they belong to the entity, group, tag or gender you pick, else 0. One per gender is the usual way to bring gender in; with Pearson it gives the point-biserial correlation."],
      ["mentions", "Mentions", "Participants: all their mentions in the selected books."],
      ["speech", "Words spoken", "Participants: all the words they speak in the selected books, whatever the sample."],
      ["quotes", "Quotes", "Participants: all their quotes in the selected books."],
      ["books", "Books", "Participants: in how many of the selected books they appear."],
      ["index", "Number in its book", "Text pieces: 1 for the first chapter or slice, 2 for the next…"],
      ["position", "Position in its book (%)", "Text pieces: how far into the book the piece starts."],
      ["length", "Length (words)", "Text pieces: the words of its sample."]],
    example: "Gender: she/her (0/1) × “indeed” per 1,000 words over participants: do women say “indeed” more (+) or less (−)?" },

  { id: "supersense", title: "Supersense", text: [
    "BookNLP's broad word senses (noun.person, verb.motion, noun.artifact…), counted as spans: a run of words with one supersense counts once. The list shows how often each occurs in the selected books."],
    example: "verb.communication per 1,000 words over slices: how talk-heavy each stretch is.", more: "MEASURES.md 15.2" },

  { id: "relation", title: "Relation", text: [
    "What is said about an entity (as on Described as), counted where the mention is. Choose whose (any entity, or one you pick) and optionally one word (say, wo*, a|b)."],
    items: [["agent", "Actions", "Verbs the entity does (Holmes said, Holmes ran)."],
      ["patient", "Done to them", "Verbs done to the entity (they followed Holmes)."],
      ["mod", "Modifiers", "Adjectives and the like said of the entity (tall Holmes, Holmes was tired)."],
      ["poss", "Possessions", "What the entity has (Holmes's pipe)."],
      ["prep", "Prepositions and settings", "Places and things the entity is with or at (Holmes in the room)."]],
    example: "Actions of Holmes: “look” per 1,000 words over chapters.", more: "MEASURES.md 1.6, 15.2" },

  { id: "sentiment", title: "Sentiment", text: [
    "VADER's sentiment over the sample's units (sentences; a quote or a paragraph's narration for participants' speech and narration). Needs the vaderSentiment package. Not a count, so no measure."],
    items: [["mean", "Sentiment (mean compound)", "The mean compound score of the units, from −1 (negative) to +1 (positive)."],
      ["positive", "Positive units (%)", "The share of units scoring +0.05 or more."],
      ["negative", "Negative units (%)", "The share of units scoring −0.05 or less."]],
    more: "MEASURES.md 10, 15.2" },

  { id: "lexicon", title: "Lexicon category", text: [
    "Words of one category of one of your lexicons (such as the emotion lexicon), matched by word form, else lemma. Add lexicons under Over time → Lexicons."],
    example: "Emotion: fear per 1,000 words over slices: where the fear words gather." },

  { id: "speech", title: "Speech sentence type", text: [
    "How many of the sample's quotes (everyone's) are questions, exclamations or statements, each counted where its first word is. Needs quotes in the sample: any text piece, or participants' “What they say (and narrate)”. To count one speaker's questions, use Speech with a sentence type instead."],
    items: [["question", "Questions", "Quotes with a ?."], ["exclaim", "Exclamations", "Quotes with a ! (and no ?)."], ["statement", "Statements", "All other quotes."],
      ["weigh", "Weigh the speech verb", "Also lets the speech verb decide when there's no ? or ! (asked, exclaimed…)."]],
    example: "Questions in speech, % of quotes, over chapters: which chapters are full of questions." },

  { id: "style", title: "Style figure", text: ["Figures of how the sample is written, as on the Style page. Not counts, so no measure."],
    items: [["word_length", "Word length (letters)", "The mean letters per word."],
      ["mattr", "MATTR", "Moving-average type-token ratio over 100-word windows: vocabulary variety, independent of length."],
      ["hapax", "Hapaxes (% of words)", "Words that occur once in the sample."],
      ["density", "Lexical density (%)", "Content words (nouns, verbs, adjectives, adverbs) among all words."],
      ["passives", "Passives per 1,000 words", "Passive constructions (was seen, had been told)."],
      ["unit_length", "Unit length (words)", "The mean words per unit (sentence, quote, paragraph's narration)."],
      ["questions", "Questions (% of units)", "Units with a question mark."],
      ["exclaims", "Exclamations (% of units)", "Units with an exclamation mark."]],
    more: "MEASURES.md 8.3, 15.2" },

  { id: "wordchoice", title: "Word choice", text: [
    "Which kinds of word a sample leans on: how many adjectives or dynamic verbs, whether it is nominal or verbal. Figures of the sample's words, as shares or ratios, so no measure. For a character's speech, choose “What they say” as the sample."],
    items: [["parts", "Parts of speech (% of words)", "The share of the sample's words that are nouns, proper nouns, verbs, adjectives, adverbs, pronouns, prepositions, determiners, coordinating or subordinating conjunctions or auxiliaries (NOUN, PROPN, VERB, ADJ, ADV, PRON, ADP, DET, CCONJ, SCONJ, AUX), as BookNLP tags them. The same profile as on the Style page."],
      ["ratios", "Ratios", "Adjectives per verb (adj_verb), adverbs per verb (adv_verb), nouns per verb (noun_verb: common nouns, not names) and modifiers per head (mod_head: adjectives and adverbs per noun and verb). Auxiliaries are not verbs here. No value where the sample has no verb (or no noun or verb)."],
      ["verbgroups", "Dynamic and static verbs (% of verbs)", "Verbs of physical action (dynamic: motion, contact, change, body, creation, competition, consumption, weather) against states and inner or social life (static: stative, cognition, perception, emotion, possession, social, communication), as a share of the verbs that have a supersense. The two add up to 100."],
      ["verbs", "Verbs by category (% of verbs)", "One kind of verb as a share of the sample's verbs: body, change, cognition, communication, competition, consumption, contact, creation, emotion, motion, perception, possession, social, stative, weather. Takes out how many verbs the speaker uses, so it shows their choice of verb."],
      ["nouns", "Nouns by category (% of nouns)", "One kind of noun as a share of the sample's nouns: Tops, act, animal, artifact, attribute, body, cognition, communication, event, feeling, food, group, location, motive, object, person, phenomenon, plant, possession, process, quantity, relation, shape, state, substance, time."],
      ["ssverbs", "Verb supersenses per 1,000 words", "How often a kind of verb (the same categories as above) occurs in the sample: the rate, not the share, as the Supersense variable gives with its per 1,000 measure."],
      ["ssnouns", "Noun supersenses per 1,000 words", "How often a kind of noun occurs: the rate, not the share of nouns."]],
    example: "Adjectives per verb in What they say, over characters: who describes and who acts?", more: "MEASURES.md 18, 15.2" },

  { id: "sound", title: "Sound and rhythm", text: [
    "Stress, cadences, sound runs and the sound profile of the sample, from the pronunciation dictionary (Settings → Sound and rhythm installs it and sets the window and boundary). Not counts, so no measure."],
    items: [["stressed", "Stressed syllables (%)", "How much of the text is stressed."],
      ["syl_word", "Syllables per word", "Longer or shorter words."], ["syl_unit", "Syllables per unit", "Longer or shorter sentences, in syllables."],
      ["clashes", "Stress clashes per 100 syllables", "Two stresses side by side (dark night)."],
      ["lapses", "Stress lapses per 100 syllables", "Three or more unstressed syllables in a row."],
      ["binary", "Binary gaps (%)", "Stresses one unstressed syllable apart (da-DUM, DUM-da)."],
      ["ternary", "Ternary gaps (%)", "Stresses two unstressed syllables apart (DUM-da-da)."],
      ["npvi", "Stress spacing nPVI", "How uneven the spacing of stresses is: 0 is perfectly even."],
      ["cad_", "Cadence … (% of phrase ends)", "How phrases end: cad_cursus (the four together), cad_planus (/ x x / x), cad_tardus (/ x x / x x), cad_velox (/ x x x x / x), cad_trispondaicus (/ x x x / x), as a share of phrase ends."],
      ["end_", "Cadence … (% of sentence ends)", "The same (end_cursus, end_planus, end_tardus, end_velox, end_trispondaicus) at sentence ends only."],
      ["_runs", "… runs per 1,000 words", "Chains of nearby content words sharing a sound: alliteration_runs, assonance_runs, consonance_runs, rhyme_runs, and repetition_runs (the same word again)."],
      ["_share", "…: content words in a run (%)", "The share of words that are in a run: alliteration_share, assonance_share, consonance_share, rhyme_share, repetition_share."],
      ["_length", "…: mean run length (words)", "How long the runs are: alliteration_length, assonance_length, consonance_length, rhyme_length, repetition_length."],
      ["class_", "… per 1,000 words (sound profile)", "Sounds of a class: class_plosives, class_fricatives, class_sibilants, class_nasals, class_liquids, class_glides, class_long_vowels, class_short_vowels."],
      ["phone:", "Sound … per 1,000 words", "One single sound (phoneme) of the dictionary."],
      ["guessed", "Guessed pronunciations (% of words)", "Words not in the dictionary, whose sound was guessed: a check on coverage."]],
    more: "MEASURES.md 17" },

  { id: "topic", title: "Topic", text: [
    "One topic of a stored topic model, as its share (%) of each case's words. A model fitted on only some of the selected books leaves the other books' cases without a value (the page warns). Fit models on the Topics page."],
    example: "Topic 4: crime, police, inspector over chapters × Mentions of Lestrade." },

  { id: "measures", title: "Measures", text: [
    "A variable that counts something becomes a value by its measure. Use rates: raw counts grow with a sample's size, so two counts correlate over pieces of different lengths for that reason alone."],
    items: [["per1k", "per 1,000 words", "The count per 1,000 words of the case's sample (default). In the findings sample: % of findings."],
      ["count", "count", "The raw count."],
      ["present", "present (0/1)", "1 if the count is above 0, else 0. Clearer for sentences."],
      ["pct", "% of quotes", "Speech sentence types and a speaker's quotes only: the share of all the sample's quotes (no value where there are none)."]],
    more: "MEASURES.md 15.2" },

  { id: "bulk", title: "Add several at once (the “Add several…” menu)", items: [
    ["paste", "Paste a list…", "Each line becomes a Words variable (simple or pattern, word forms or lemmas)."],
    ["words", "Most frequent words…", "The N most frequent words or lemmas in the cases' samples, optionally only some word classes, only words in at least so many books (Minimum range), only words inside quotes of a sentence type, or only the speech verbs. The variables count the word everywhere in the sample."],
    ["entities", "Most mentioned entities…", "The N most mentioned entities of a type, as Mentions variables."],
    ["speakers", "Most talkative speakers…", "The N entities of a type who speak the most words, as Speech variables (words spoken)."],
    ["style_all", "Every style figure / Every sound figure", "One variable per figure (sound: everything but the single sounds)."],
    ["wordchoice_all", "Word choice…", "One variable per figure of one section: the parts of speech, the ratios, dynamic and static verbs, verbs or nouns by category, or supersenses per 1,000 words."],
    ["category_all", "Every category of a lexicon…", "One variable per category, as words per 1,000."],
    ["topic_all", "Every topic of a model…", "One variable per topic."],
    ["attribute", "Every gender / tag / saved group", "Participants: one “Is one of” (0/1) variable per value."]] },

  { id: "options", title: "Coefficient, correction and split", items: [
    ["pearson", "Pearson's r", "A straight-line relation, from −1 to +1. Roughly, |r| of .1 is small, .3 medium, .5 large."],
    ["spearman", "Spearman's ρ", "r of the ranks: any relation that only goes one way, less moved by a few extreme cases. Often better for word rates, which are skewed."],
    ["none", "Correction: None", "Each p as it is. With many tests, about one in twenty is “significant” at .05 by chance."],
    ["bonferroni", "Correction: Bonferroni", "Each p multiplied by the number of tests in the table. Strict."],
    ["holm", "Correction: Holm", "Like Bonferroni, step by step from the smallest p: less strict, still guards against any false finding."],
    ["split", "Descriptives split by", "Descriptives for each group too: participants by gender, tag, saved group or book; text pieces by book. Split by book, a participant is measured again in each book alone."]],
    more: "MEASURES.md 15.3, 15.4" },

  { id: "results", title: "Results", text: [
    "Above the results the page says how many cases there are and how many were left out. A variable that doesn't fit the cases shows a note saying why, and has no values."],
    items: [["corr", "Correlations", "A heatmap: blue positive, red negative, stars for significance (* p < .05, ** < .01, *** < .001, after the correction). Tick p, N or the 95% interval to show them in the cells; hover a cell for every figure. Download it as SVG or PNG. Below, every pair as a sortable table (CSV). A dashed cell has no coefficient: fewer than 3 cases, or a variable that doesn't vary."],
      ["desc", "Descriptives", "Per variable (and group): N (cases with a value), M (mean), SD (standard deviation), V (variance), median, min, max, SE (standard error) and the 95% interval of the mean."],
      ["data", "Data", "The values themselves, one row per case. A chapter opens in the text, a participant on their page. Download as CSV, or Download for R (.zip): the cases wide and long with each count and rate, the variables, the cases left out and a script that loads them."]],
    text2: "A correlation is not a cause, and neighbouring chapters are not independent: read p-values as guides.", more: "MEASURES.md 15.3–15.5" },
]);
