"use strict";
/* ---------- help: Dialogue ---------- */
/* The help of the Dialogue page (see help.js): one section per sub-tab, its id the sub-tab's name in the address (#/dialogue/verbs opens
   the help at "verbs"), then what the tabs share: the conversation gap, the sentence type, the quote cards and correcting a quote. The
   maths is in MEASURES.md, section 5 (narrators: 6). */

addHelp("dialogue", "Dialogue", [
  { id: "start", title: "How the page works", text: [
    "Everything said inside quotes in the selected books, and who says it, in six tabs. A quote's speaker is BookNLP's attribution (corrected in the companion editor); whom it is addressed to is estimated here, and you can correct it. Click a row almost anywhere for the quotes behind it."] },

  { id: "speakers", title: "Who speaks", items: [
    ["books", "Dialogue in each book", "Per book: words, words in quotes and their share (% dialogue), quotes, how many have a speaker (% attributed) and an addressee, speakers and conversations. The chart shows the share of words in dialogue from start to end of each book (50 slices, smoothed). With more than eight books it draws their average (each book weighing the same), every book a faint line behind it; point at one for its title."],
    ["table", "Speakers", "Every speaker (two of the same name, each in one book, get their book: Holmes (alpha), Holmes (beta)): books, quotes, words and their share of all dialogue, words per quote, how often they are addressed, the share of their quotes introduced with “say”, and their most used speech verbs. Click a row for their quotes."],
    ["narrators", "Narrators", "Narration (every word outside quotes) per narrator: paragraphs, words, share of narration, words per paragraph, questions, I/you/we, MATTR, and what the same character says in quotes. Click a row to compare their narrating voice with their dialogue."]],
    more: "MEASURES.md 5.1, 5.2, 6" },

  { id: "verbs", title: "Speech verbs", items: [
    ["overall", "How speech is introduced", "The verbs (said, cried, whispered), the adverbs (quietly) and the pairs (said quietly) that introduce quotes, with how many quotes and the share of quotes. Click a row for the quotes."],
    ["skip", "Leave out verbs and adverbs", "Words that should never count as a speech verb or manner (look, turn; then, soon), as dictionary forms, kept for this workspace."],
    ["one", "One speaker or group", "Choose a speaker, group, tag or gender: their verbs and adverbs, and the speech verbs distinctive of them compared with all other speakers (with the comparison settings explained under “What's distinctive: comparing with a reference”)."]],
    text2: "A quote's verb is the speech verb whose subject is the mention BookNLP used to attribute the quote (“said Holmes”, “he cried”); otherwise the nearest speech verb within 8 words before or after it, in the narration.",
    more: "MEASURES.md 5.3" },

  { id: "voice", title: "How they speak", items: [
    ["style", "Speaking style", "A row per speaker with at least the chosen number of words, and All speakers: quotes, words, words per quote, questions and exclamations per 100 quotes, I, you, we per 1,000 words, word length and MATTR (vocabulary variety; marked ≈ when the sample is too small to trust). Click a row to look at that speaker below."],
    ["wordchoice", "Word choice", "Columns of Speaking style and of the comparison under it: the share of the words spoken that are adjectives, adverbs, verbs or nouns, adjectives per verb, and the share of verbs that are dynamic (motion, contact, change, body, creation, competition, consumption, weather) rather than static. The select above the table shows the key figures, one section (all parts of speech, the ratios, every kind of verb or noun…) or none. Also on a character's Speech panel, per book. The same figures are variables on the Statistics page (Word choice)."],
    ["target", "Speaker or narrator / Compared with", "Distinctive vocabulary: whose speech (an entity, group, tag, gender, book or a narrator's narration) against whose (everyone else by default)."],
    ["count", "Count: Word forms / Lemmas", "Compare words as written, or dictionary forms."],
    ["words", "Words distinctive of …", "Their style figures side by side, then the words markedly more typical of the target. Click a word for the quotes that hold it."]],
    example: "Watson's speech compared with Holmes's: the words one uses far more than the other.", more: "MEASURES.md 5.6, 3" },

  { id: "conversations", title: "Conversations", items: [
    ["list", "The list", "Runs of quotes that belong together: book, how far through, quotes, words, speakers, who speaks and the opening words. Click a row to read it with speakers and estimated addressees; a row you changed is marked."],
    ["involving", "Only those involving", "Keeps the conversations in which someone (an entity, group, tag or gender) speaks or listens."],
    ["gap", "A conversation ends after N narration words", "Above the tabs: more narration than this between two quotes starts a new conversation (default 100). It also decides addressees."]],
    more: "MEASURES.md 5.4" },

  { id: "quotes", title: "Quotes", text: ["Every quote of the selected books, filtered; the first 400 are shown (narrow the filters to see others)."],
    items: [["speaker", "Speaker", "One speaker, group, tag or gender (Any speaker clears it)."],
      ["book", "Book", "One of the selected books."],
      ["q", "Containing", "Text inside the quote."],
      ["verb", "Speech verb (lemma)", "The verb that introduces it, as a dictionary form (whisper)."],
      ["attributed", "Attributed", "With a speaker, without one, or all."],
      ["named", "Addressee found by: Named in the quote", "Someone named inside it as a form of address (“Watson, come here”)."],
      ["reply", "Reply to the previous speaker", "Answers whoever spoke just before."],
      ["continues", "Speaker keeps talking to the same person", "The speaker's previous quote had that addressee."],
      ["next", "The next speaker (opening line)", "An opening line, addressed to whoever speaks next."],
      ["yours", "Set by you", "You chose the addressees (Correct)."],
      ["yours_all", "Set by you: everyone present", "You set it to everyone in the conversation."]],
    more: "MEASURES.md 5.5" },

  { id: "indepth", title: "In-Depth Who Speaks", text: [
    "Who speaks' three sections (Dialogue in each book, Speakers, Narrators) for a part of the cast, everyone the choice matches pooled as one."],
    items: [["search", "Mode: Search", "Scope chooses an entity, group, type, tag or gender: its own dialogue per book, share-of-dialogue chart, pooled speaker figures and narration. Nothing chosen shows everyone."],
      ["compare", "Mode: Compare", "Target against Compared with: each figure as two bars side by side."]] },

  { id: "type", title: "Sentence type", text: [
    "Several tabs (Quotes, Speaking style, Distinctive vocabulary, both Speech verbs tables) can keep only questions, exclamations or statements. Each place keeps its own choice."],
    items: [["question", "Questions", "Quotes with a ?."], ["exclaim", "Exclamations", "Quotes with a ! (and no ?)."], ["statement", "Statements", "All other quotes."],
      ["weigh", "Weigh the speech verb too", "Also lets the speech verb decide when the quote has no ? or !: asked, inquired make a question; exclaimed, cried an exclamation."]] },

  { id: "correct", title: "Quote cards and corrections", items: [
    ["card", "A quote card", "Speaker → addressee (and how it was found), the speech verb, the book and place, Open in the text, and the quote in its sentence."],
    ["addr", "Correct: Addressed to", "Add or remove addressees, set Everyone present, or go Back to the estimate. Speakers themselves are corrected in the companion editor."],
    ["conv", "Correct: Conversation", "Remove someone from it or put them back, add a listener, Start a new conversation here or Join the previous conversation (and undo either)."]],
    text2: "Your corrections replace the estimates everywhere (addressees, conversations, the network) and are marked as yours." },
]);
