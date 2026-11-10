# Measures: what the analyser shows, and how it is made

Every figure, table column and chart in the analyser is defined here: what it says, how to read it, what it assumes, where the data
comes from, how it is calculated and where in the code. The user guide (guide.md) explains *using* the analyser and DOCUMENTATION.md explains *how it
is built*; this file explains *what the numbers mean*. The same explanations appear, shorter, under the "How this is calculated"
notes in the interface.

**How each entry is written.** *Says*: what the figure tells you. *Read it as*: how to interpret it, and how not to. *Assumes*: what has to
be true for it to be meaningful. *Data*: which BookNLP file or which of your settings it comes from. *Calculation*: the recipe.
*Code*: the file and function (`core/view.py: profile` means the function `profile` in `core/view.py`; look there for the exact recipe).

Contents: 0 Ground rules · 1 Entities and their profiles · 2 Groups of entities · 3 Comparing two sets of words (keyness) ·
4 The same entity in several books · 5 Dialogue · 6 Narrators · 7 The corpus tools · 8 Chapters, arcs and style ·
9 Stylometry · 10 Sentiment and lexicons · 11 Topics · 12 Networks · 13 Suggestions (links and narrators) · 14 Described as · 15 Statistics · 16 Over the book · 17 Sound and rhythm · 18 Word choice

---

## 0. Ground rules

These apply everywhere, so they are stated once.

**Token, word, sentence, paragraph.** BookNLP's `.tokens` file has one row per token (a word, a punctuation mark, a piece such as *n't*).
Everything is addressed by the token's position (0, 1, 2 …). Sentences and paragraphs are BookNLP's own (`sentence_ID`, `paragraph_ID`).
*Words* means tokens that are not punctuation:

* in the **entity pages** ("per 1,000 words") a word is a token whose part of speech is not PUNCT, SPACE, SYM or X
  (`core/bookdata.py: BookData.n_words`);
* in the **corpus tools, dialogue, style and narration** a word is a token that is not PUNCT, SPACE or SYM and not a quotation mark
  (`core/corpus.py: cindex`, key `isword`, which dialogue and the other tools share).

The two counts differ only by tokens tagged X (foreign words, stray symbols), which are few. Where a figure divides by "words", it says
which of the two it uses.

**Per 1,000 words.** A rate: `1000 × count ÷ words`. It lets you compare texts of different lengths. It is a rate of *tokens*, not of
distinct things.

**In scope.** Corpus tools can be restricted to narration, dialogue, or one speaker's or group's quotes. A word is *in scope* when it lies
inside that part of the text (`core/corpus.py: Scope`). "Words in scope" is the denominator of every rate on those pages.

**The selection.** The books chosen at the top right. A `View` (`core/view.py`) is built for exactly those books; every number on a page is
for them, together, unless the page says "per book".

**The minimum.** Entities with fewer mentions than your minimum (Settings → Entities → Minimum mentions) are left out of lists, profiles, comparisons,
networks and groups. It is set per type and can be applied per book or across the selected books combined (`count_mode`).
*Code*: `core/view.py: View._make_unit`.

**The minimum frequency of words.** The Corpus lists, Book by book and Over the book (all books combined) have a *Minimum frequency* of their own. Settings → Words says how it is counted: **across the selected books combined** (the default: a word counts when it occurs that often in all the books together, so a word that is rare in every book can still be listed or tested) or **in each book separately** (a book counts for a word only if the word occurs that often in that book; see each tool below). The keyness comparisons, which set a target against a reference, and the views of a single book are the same either way.
*Code*: `core/stats.py: passes`.

**Entity, unit, member.** BookNLP groups the mentions of one character or place in one book into a *coreference group*. A *unit* is one such
group, or several you have linked across books (`p:<n>`). A *member* is one book's group inside a unit. *Code*: `core/view.py`, module
docstring.

**Significance and effect size.** Several tables give a p-value and an effect size. A p-value says how surprising a difference would be if
only chance were at work; an effect size says how big it is. With small counts effect sizes can be huge and unreliable, and with large
counts tiny differences can be significant. Read both, and prefer the effect size for "how much" and the p-value for "how sure".
Neighbouring passages of a book are not independent observations, so p-values are guides, not proofs.

**What is BookNLP's and what is added.** Mentions, coreference groups, quotes and their speakers, POS tags, the dependency parse,
supersenses and events are BookNLP's output, used as given. Everything derived from them (relations, addressees, conversations, narrators,
chapters, similarities) is computed here, and mistakes in BookNLP's layers carry through. Speakers and mentions are corrected in the editor
(and the books re-exported), not here.

---

## 1. Entities and their profiles

### 1.1 Mentions
* **Says**: how often the entity is referred to.
* **Read it as**: a count of references, not of pages or scenes: "Holmes" and "he" both count when BookNLP grouped them with him.
* **Assumes**: BookNLP's coreference is right. A character split into two groups is counted as two entities (fix it in the editor, or link
  them on the Links page); a merged pair is counted as one.
* **Data**: `.entities`, one row per mention (`COREF`, `start_token`, `end_token`, `prop`, `cat`, `text`).
* **Calculation**: the number of mentions in the unit's groups. A group's *type* is the most common `cat` among its mentions. A unit's
  type is the type with most mentions over its members.
* **Code**: `core/bookdata.py: BookData._entities`; `core/view.py: View._make_unit`.

### 1.2 Share of type (%)
* **Says**: the entity's part of all mentions of its type in the selection ("12% of all mentions of people").
* **Read it as**: a measure of prominence among its own kind. It depends on which entities pass the minimum.
* **Calculation**: `100 × mentions ÷ all mentions of counted units of that type`. Empty for a group of several types.
* **Code**: `core/view.py: Unit.as_row`.

### 1.3 Mentions per 1,000 words
* **Says**: how densely the entity is mentioned.
* **Assumes**: comparable between books of different length; less so between a book and one chapter.
* **Calculation**: `1000 × mentions ÷ words`, where words are those of the books the entity is counted in (each book once).
* **Code**: `core/view.py: View._profile` (`per1k`), `words_in`.

### 1.4 Where it falls (the strip)
* **Says**: where in each book the mentions are.
* **Read it as**: a heat strip from start (left) to end (right); darker means more mentions in that slice.
* **Calculation**: each book's tokens are cut into 100 equal slices; a mention counts in the slice holding its first token. The shade is the
  slice's count relative to the largest slice of that book's strip.
* **Code**: `core/view.py: View._presence`; `static/js/core.js: presenceChart`.

### 1.5 How it is referred to
* **Says**: the mix of names (PROP), descriptions (NOM: "the detective") and pronouns (PRON).
* **Read it as**: a character mostly pronoun-referenced is narrated closely; one mostly named appears in dialogue or lists.
* **Data**: the `prop` column of `.entities`.
* **Calculation**: mentions of each kind, with the most frequent forms of each (pronouns lowercased).
* **Code**: `core/view.py: View._profile` (`by_prop`, `forms`).
* **Pronouns**: the pronoun set BookNLP inferred for the character (`g.argmax` in `.book`), e.g. *he/him/his*. It is BookNLP's
  guess, shown as given, and also used as evidence in link suggestions.

### 1.5a Named or described in dialogue by
* **Says**: which speakers name or describe the entity inside their quotes.
* **Read it as**: who talks *about* it. Pronouns are left out, because inside a quote they mostly mean the speaker or the listener.
* **Calculation**: mentions of kind PROP or NOM lying inside a quote, grouped by the quote's speaker; the entity's own mentions of itself,
  and (for a group) mentions by its members, are not counted.
* **Code**: `core/view.py: View._named_by`.

### 1.6 What they do and what is done to them (relations)
Five lists, each a count of words attached to the entity's mentions by the dependency parse (`.tokens`: `dependency_relation`,
`syntactic_head_ID`):

| List | Says | Rule |
|---|---|---|
| Actions (agent) | verbs the entity does | mention is the subject (nsubj) of a verb, or the "by" agent of a passive |
| Done to them (patient) | verbs done to it | mention is object, indirect object or passive subject |
| Possessions (poss) | things it owns | mention is the possessor of a noun ("his pipe") |
| Modifiers (mod) | how it is described | adjectives attached to it, nouns in apposition, complements of "to be" |
| Prepositions and settings (prep) | "went to London" | mention is the object of a preposition attached to a verb, noun or adjective |

* **Read it as**: a portrait of the character in verbs and nouns, from the text's grammar only. It cannot see what the grammar hides
  (a pronoun BookNLP mislinked, a sentence the parser got wrong).
* **Assumes**: the parse is right. Extensions to BookNLP's rules, all documented in the code: a conjoined mention takes the role of the
  first conjunct ("Holmes and Watson went"); a subject also counts for verbs joined to its verb ("rose and lit" gives *rise* and *light*);
  prepositions are recorded for every type. Counts can therefore exceed those in BookNLP's `.book`.
* **Columns**: *Count* (occurrences), *Per 1,000 words* (rate, see 1.3), *%* (share of the list's total), *Events* (how many of these
  verbs BookNLP marks as EVENT, `event` column), *Supersense* (the most common WordNet supersense BookNLP gave the verb, `.supersense`).
  Clicking a row shows the sentences, so any count can be checked.
* **Code**: `core/bookdata.py: BookData._relations`, `_add`; `core/view.py: View._relation_tables`.

### 1.7 Kinds of action (supersenses)
* **Says**: which kinds of verb the entity does or suffers: communication, cognition, perception, motion…
* **Data**: `.supersense` (WordNet lexical categories per token), attached to the verbs of the agent and patient lists.
* **Calculation**: counts of the supersense of each verb found in 1.6; verbs without one are counted apart and not shown.
* **Code**: `core/view.py: View._supersense_tables`.

### 1.8 Appears with (co-occurrence)
* **Says**: which other entities are mentioned in the same sentence.
* **Read it as**: proximity in the text, not interaction: two people can share a sentence without meeting.
* **Calculation**: the number of sentences that mention both; a sentence counts once per other entity.
* **Code**: `core/view.py: View.cooccurring` (uses `BookData.sent_members`, `group_sents`).
* **The small network** beside it draws the entity with its 15 strongest companions and the links among them (see 12).

### 1.9 What's distinctive
* **Says**: words (from one of the five lists) markedly more typical of this entity than of a comparison group.
* **Calculation**: keyness (section 3) of the entity's list against the same list of everyone else of the same type (or the group you choose),
  with the entity's own mentions excluded from the reference.
* **Code**: `core/view.py: View.distinctive`.

---

## 2. Groups of entities

You can tick several entities on the Entities page and analyse them together, and use such groups on the Compare page.

* **Says**: the pooled portrait of several entities counted as one.
* **Read it as**: figures for "these entities, together". A group of a hero and a sidekick is not their average: it is their sum.
* **Assumes**: it makes sense to add them. A group of different types has no share of type.
* **Calculation**: the group's members are those of all its entities, so mentions, forms, relations, supersenses, presence and quotes are
  summed. A sentence or quote counts once however many of the group's entities it holds. Entities of the group are never counted as
  outsiders: "named in dialogue by", "talks to", "spoken to by" and "appears with" leave out the group's own members; the Speech section
  adds **Quotes between members** (quotes spoken by one member and addressed to another).
* **The members table**: each entity's *mentions*, *% of the group* (its mentions ÷ the group's) and *per 1,000 words* (its own mentions
  over the words of the books it appears in).
* **Saved groups** store only entity ids and follow the minimum, the selected books and your links (an entity you linked afterwards is
  followed to its person).
* **Code**: `core/view.py: View.group_of`, `group_unit`, `group_profile`, `_profile`; `core/entitygroups.py`;
  `core/dialogue.py: entity`.

---

## 3. Comparing two sets of words (keyness)

Used for: distinctive words of an entity or group, the Compare page, keywords, distinctive speech verbs, a speaker's or narrator's
distinctive vocabulary.

**Setup.** For one item (a word) you have a *target* text and a *reference* text. `a` and `b` are the item's counts in target and
reference; `c` and `d` are the total counts of all items in each (the two text sizes). `Code: core/stats.py: compare, keyness`.

| Measure | Says | Calculation |
|---|---|---|
| **Log-likelihood G²** | how surprising the difference is | `2 Σ O ln(O/E)` over the four cells, with expected counts from the pooled rate (Rayson & Garside 2000). Signed + when the item is relatively more frequent in the target |
| **χ²** | the same, by Pearson's test | for the 2×2 table (item vs other items, target vs reference), without Yates' correction; signed like G² |
| **p** | chance that a difference this large arises by chance | from χ² with 1 degree of freedom (`p_chi1`); for G² and χ² alike |
| **Log ratio** | how many times more frequent, on a log₂ scale | `log₂((a÷c) ÷ (b÷d))` (Hardie 2014): 1 means twice as frequent, −1 half as frequent. Zero counts are replaced by 0.5 |
| **%DIFF** | relative difference in percent | `((a÷c) − (b÷d)) ÷ (b÷d) × 100` (Gabrielatos & Marchi 2012). Zero counts replaced by 0.5 |
| **Odds ratio** | the same as odds | `(a ÷ (c−a)) ÷ (b ÷ (d−b))` with a 95% interval from the log odds ratio's standard error; 0.5 is added to every cell when one is zero (Haldane–Anscombe) |

* **Read it as**: G² or χ² rank by *evidence* (large samples give large values even for small differences); log ratio, %DIFF and the odds
  ratio rank by *size of effect* (rare items give large values on little evidence). Use them together, and check with the
  sentences (every row opens its evidence).
* **Options**: *Minimum frequency* (an item must occur at least this often in the target, or on either side for two-way comparisons);
  *Significance level*; *Bonferroni correction* divides the level by the number of items tested, because testing many items produces
  false alarms; *Show non-significant* lists the rest, dimmed. Tested items are those with at least the minimum frequency.
* **Assumes**: words are independent draws, which they are not (a repeated phrase counts every time). Treat p as a ranking aid.
* **Code**: `core/stats.py: keyness`; used by `View.distinctive`, `corpus.keywords`, `dialogue.voice`, `dialogue.verbs`.

---

## 4. The same entity in several books

Shown on an entity's page when it is counted in two or more of the selected books (a linked entity, or a group).

* **Overview table**: per book, *mentions*, *per 1,000 words of that book*, *% of the type's mentions in that book*, the *names /
  descriptions / pronouns %* of its mentions, each list *per 100 mentions*, and the *most used names*.
* **Words, book by book**: for each word of the chosen list, its count in each book with its share of that book's list. **χ²**, **p** and
  **Cramér's V** test whether the word's share changes across books.
  * **Calculation**: the 2×k table (word vs all other words, by book), Pearson's χ² with k−1 degrees of freedom, p from that, and
    `V = √(χ² ÷ N)` (0 = the share is the same in every book, larger = it changes more). Words below the minimum frequency are listed without a test. With Settings → Words set to *in each book separately*, a word is tested when at least two books have it
    at least that often; the test compares those books only (the other books' cells are not shaded) and the word's counts and shares stay whole.
  * **Adjusted standardised residuals**: each book's cell is shaded when its residual is beyond ±1.96 (blue: more than expected from the
    other books, red: less). `(observed − expected) ÷ √(expected × (1 − book share) × (1 − word share))`.
  * **Code**: `core/stats.py: across`; `core/view.py: View.by_book`.
* **Assumes**: books are comparable in kind. Different-length lists per book are handled by working with shares.

---

> **Mentions are counted once.** With plural groups on, a plural group's mention ("Holmes and Watson", "they") also counts for its members. A target made
> of several entities (all people, a gender, a book, a group you picked) may hold the plural group and its members, so the same mention could be added up
> two or three times; every count of a target (mentions, how it is referred to, the words of each relation, kinds of action, the sentences behind a
> count, the Over the book grids) leaves the copies out and counts each mention once. One entity alone keeps the mentions credited to it. (Entity lists
> and "share of its type" still add up each entity's own count, so shares there can add to more than 100% when plural groups are on.)

## 5. Dialogue

BookNLP's `.quotes` gives each quote's start and end, the mention used to attribute it (`mention_start/end`) and the speaker (`char_id`).
Quotes with no speaker are counted but not attributed.

### 5.1 Words spoken, share of dialogue, quotes
* **Says**: how much a speaker says.
* **Calculation**: *quotes* = the speaker's quotes; *words spoken* = words inside them (not punctuation or quotation marks);
  *share of dialogue* = words spoken ÷ all words inside quotes in the selected books (including unattributed quotes).
* **Assumes**: BookNLP's quote boundaries and attributions are right; a missing quotation mark or a wrongly attributed speaker changes these
  counts (fix in the editor).
* **Code**: `core/dialogue.py: book_dialogue`, `overview`, `entity`.

### 5.2 Dialogue share along a book
* **Calculation**: the share of words inside quotes in each fiftieth of a book, lightly smoothed with its neighbours in the chart.
* **Code**: `core/dialogue.py: book_dialogue` (`time`).

### 5.3 Speech verbs and adverbs
* **Says**: how quotes are introduced ("said quietly").
* **Calculation**: the verb of the quote is the verb the attributing mention is the subject of ("said Holmes", "he cried", method
  *subject*, only if it is a speech verb), else the nearest speech verb (method *near*). A speech verb is one of a built-in list of 87, or any
  verb BookNLP gives the communication supersense, in the narration (never inside a quote), and not one you left out. One verb token introduces at most one quote: when two quotes find the same one, *subject* beats *near*, then the closer quote, then the earlier wins, and the other has no verb (Speech verbs tab, kept per workspace). The *near* search looks
  within 8 tokens after the quote or before it, in the same paragraph. Adverbs are the manner adverbs attached to that verb (not words of
  time, place or degree such as *then, soon, very*, nor any you left out; they stand in the narration, never inside a quote).
  *% "said"* is the share of a speaker's quotes introduced by *say*.
* **Distinctive verbs** use keyness (section 3) of the speaker's verbs against all other speakers'.
* **Code**: `core/dialogue.py: _speech_verb`, `verbs`.

### 5.4 Conversations
* **Says**: runs of quotes that belong together.
* **Calculation**: a new conversation starts when more than `conv_gap` narration words (default 100, Dialogue page) lie between one quote and
  the next, unless you split or joined there. Participants are the speakers plus listeners you add minus those you remove.
* **Code**: `core/dialogue.py: book_dialogue`, `participants`.

### 5.5 Addressees (estimated)
* **Says**: whom a quote is spoken to. BookNLP does not record this, so it is *estimated*, and every estimate keeps its method.
* **Calculation**, in this order: (1) *named*: a person named inside the quote as a form of address, a name at the start, after a comma, or
  after *my / dear / O* ("Watson, come here"), or a description after *my / dear / O* or closing the quote after a comma ("My dear
  fellow, …"); (2) *reply*: the previous speaker in the same conversation, if someone else; (3) *continues*: the same person as the
  speaker's previous quote; (4) *next*: for an opening line, the next speaker. Otherwise none. Your corrections replace the estimate
  (*set by you*, or *everyone present*).
* **Read it as**: a good guess in two-person exchanges, weaker in crowds. Networks and "talks to" tables inherit its errors.
* **Code**: `core/dialogue.py: _vocative`, `book_dialogue`, `addressees`.
* **Addressed** (in the speaker table): quotes estimated to be addressed to the person.

### 5.6 Speaking style
| Column | Calculation |
|---|---|
| Words per quote | mean words per quote (also the median in the data) |
| Questions, Exclamations | quotes containing `?` (or `!`), per 100 quotes |
| I / You / We | words from the sets *I, me, my, mine, myself* / *you, your…, thee, thou…* / *we, us, our…*, per 1,000 words spoken |
| Word length | mean letters per word |
| MATTR | moving-average type–token ratio over windows of 100 words (Covington & McFall 2010): the mean over every window of (different words ÷ 100). Unlike the plain ratio it does not fall as more is said. Under 100 words the plain type–token ratio is shown, marked ≈ (read with care) |

* **Word choice columns** (a select above the table; also in the voice comparison and, as key figures, on a character's Speech panel per book): the figures of section 18 over the words of the speaker's quotes (every token of the quotes that is a word), pooled over the selected books. A quote said by two speakers counts for both; "All speakers" counts each quote once.
* **Code**: `core/dialogue.py: style`, `mattr`, `style_table`, `word_choice`.

---

## 6. Narrators

Narration is every word outside quotes, paragraph by paragraph. Each paragraph belongs to a *narrator role*: the book's narrator (chosen
under Library or in the text view, else an "unnamed narrator" of that book) unless you gave that paragraph to someone else.
*Code*: `core/dialogue.py: narrator_of`, `narration_recs`.

A **narrator's profile** (Entities → Narrators) shows:

| Figure | Calculation |
|---|---|
| Words narrated | narration words in the paragraphs of the role |
| Paragraphs | paragraphs of the role that contain narration |
| Share of all narration | words narrated ÷ all narration words in the selection |
| Per 1,000 words | words narrated ÷ all words of the books the role narrates in, × 1,000 |
| Set by paragraph | paragraphs you assigned to this role as exceptions |
| Where they narrate | paragraphs of the role in each 1% of the book (like the strip in 1.4) |
| Voice | the style figures of 5.6 for the role's narration (a "quote" is a paragraph: *questions* is the share of paragraphs with a `?`), next to all narration and next to the same character's dialogue |
| Book by book | paragraphs, words, share of the book's narration, words per paragraph |
| What's distinctive | keyness (section 3) of the role's words against other narration, everyone's dialogue, or the same character's dialogue |

* **Read it as**: "voice" figures compare *how the story is told*; they say nothing about mentions. The character's own profile (mentions,
  relations, dialogue) is separate.
* **Code**: `core/dialogue.py: narrator_rows`, `narrator_profile`, `voice`.

---

## 7. The corpus tools

All tools work on the words of the selected books in scope. Searches are *simple* (words, `*`, `?`, `a|b`, `#` any word) or *pattern*
(`[lemma="say"] [pos="ADV"]` over word, lemma, pos, tag, dep, ent, prop, char, ss, event, quote, speaker). *Code*:
`core/corpus.py` (`parse_simple`, `parse_pattern`, `Matcher`).

### 7.1 Hits, per 1,000 words, per book
* **Calculation**: hits are non-overlapping matches, leftmost first, lying wholly inside the scope. Per 1,000 words = hits ÷ words in scope × 1,000.
  A search stops at 20,000 hits. A candidate that is outside the scope, or lacks the near word or the context you asked for, is not a hit
  and does not count towards that limit (so a common word searched in dialogue only still reaches the later books), and it does not
  block the text it covers from being part of a later hit.
* **The plot**: each book is divided into 200 equal slices; a slice is shaded by its number of hits (the darkest slice of the book is the
  darkest shade). It is drawn from these counts, never from single hits, so a word with tens of thousands of hits draws as quickly as a rare one.
* **Code**: `core/corpus.py: kwic_search` (finds, filters and sorts the hits), `kwic_lines` (the text of the lines shown), `kwic` (both),
  `Matcher.hits`.

### 7.2 Dispersion (Juilland's D)
* **Says**: how evenly something is spread through the text.
* **Read it as**: 1 = perfectly even, 0 = all in one place. A frequent word can be badly dispersed (a character's name in one chapter).
* **Calculation**: `D = 1 − V ÷ √(parts − 1)`, V the coefficient of variation of the counts in ten equal parts (of a book for the
  concordance, of the selected text taken in book order for lists).
* **Code**: `core/corpus.py: juilland`.

### 7.3 Range
* The number of selected books an item occurs in.

### 7.4 Word list
* **Says**: how often each word, lemma, word+POS, word+POS+lemma or POS occurs.
* **Minimum frequency and range**: a word is listed when it occurs at least that often over the selected books together and in at least the minimum range of books. With Settings → Words
  set to *in each book separately* it is listed when it occurs that often in at least one book, and the minimum range counts the books where it does. The same holds for n-grams and collocates (7.5, 7.6).
* **Columns**: *Frequency*, *Per 1,000* (÷ words in scope), *Range* (7.3), *Dispersion* (7.2). *Types* are the distinct items; the
  *type/token ratio* is types ÷ tokens counted.
* **Word forms** are lowercased unless *Case sensitive* is on; lemmas are lowercased. A **word+POS+lemma** row is one combination of form,
  word class and lemma, so the same word as noun and as verb, or with two lemmas, is two rows.
* **Word-type filter**: only tokens of the chosen POS, fine tags and entity types are counted (a token is in an entity type when a mention
  of that kind covers it; several values of one kind mean *any*; different kinds must *all* hold). Rates and dispersion still refer to all
  words in scope ("nouns per 1,000 words"); the type/token ratio then compares the counted types with the counted tokens.
* **Code**: `core/corpus.py: counts`, `wordlist`, `token_test`, `filter_options`, `item_of`.

### 7.5 N-grams
* **Says**: recurrent runs of n consecutive words.
* **Calculation**: runs of the chosen lengths, not crossing a sentence end (if chosen) or a gap in the scope; *containing* keeps runs with
  a matching word anywhere, first or last. Frequency, per 1,000, range.
* **Size**: every different n-gram is held while the list is made, so a long range of lengths over many books needs much more memory than a
  short one: 2–5-grams over sixty books (about 700,000 words, a million different n-grams) take about three seconds and 170 MB, 1–8-grams
  about six seconds and 350 MB. At most the 5,000 most frequent are listed (the page says how many qualified).
* **Code**: `core/corpus.py: ngrams`.

### 7.6 Collocates
* **Says**: words that occur near the search term more (or less) often than chance.
* **Definitions**: *O* (Freq) = occurrences of the collocate in the windows (`L`/`R` split by side); *E* = expected count =
  `hits × collocate frequency in the corpus × window size ÷ tokens`; window = the chosen words left and right, stopping at the scope's edge and (if chosen) the sentence's.
* **Measures**: MI = `log₂(O/E)`; T-score = `(O − E) ÷ √O`; MI3 = `log₂(O³/E)`; logDice = `14 + log₂(2O ÷ (hits + collocate frequency))`;
  **log-likelihood** from the 2×2 table (collocate inside vs outside the windows), signed + when more frequent than expected, with p from χ²(1).
* **Read it as**: MI favours rare, exclusive partners; T-score favours frequent ones; logDice sits between and does not depend on corpus size.
  Rank by more than one and look at the concordance.
* **Word-type filter**: only decides which collocates are listed; windows and hit counts are unchanged; a collocate's corpus frequency
  counts only its own tokens of the chosen types, so a word is compared with its uses as that word class.
* **Code**: `core/corpus.py: collocates`, `_window`, `_ll4`.

### 7.7 Keywords
* **Says**: words more (or, optionally, less) frequent in the target than in a reference: other books (with their own scope) or a reference
  file (a word list or text you load; word forms only).
* **Calculation**: keyness (section 3) per word; *Range* = target books it occurs in.
* **Code**: `core/corpus.py: keywords`; reference files: `make_reference`, `parse_wordlist`.

### 7.8 Concordance sorting and the context search
* **Sorting**: up to three levels; each has a position (the hit, the 1st–5th word to its left or right, or the book) and something to
  compare: the word (A–Z), its lemma, its POS, its fine tag, or *frequency* (how often that word occurs at that position among these hits,
  most frequent first). An arrow reverses a level. Hits that tie on every level keep the order of the text.
* **Context search**: a second search (simple or pattern) in the window around each hit (words to the left and right, not counting the hit;
  stopping at the scope's edge and, if chosen, the sentence's); hits are kept when a match lies wholly inside the window, or, inverted,
  when none does. Matches of the second search are found over the whole book first (leftmost, non-overlapping).
* **Code**: `core/corpus.py: _sort_levels`, `_sort_hits`, `_ctx_filter`.

---

## 8. Chapters, arcs and style

### 8.1 Segments: slices and chapters
* **Says**: how books are divided for anything measured "per segment".
* **Slices**: n equal token counts per book, or (*Words per slice*, as in Statistics) a cut at every 200th word, say, so that every slice has exactly
  that many words; a rest at the end of a book under half a slice joins the last slice, and a longer one stands alone (the number of slices
  per book then varies with its length, and the corpus timeline's shared slice count does not apply). **Chapters**: start at heading paragraphs: 12 words or fewer, not a quote, beginning with
  a heading word (Chapter, Book, Part, Adventure…) or a numeral, or written in capitals (not initials and a name), or (if chosen) short
  lines without closing punctuation. Consecutive heading lines are joined; a heading closer than the *minimum chapter length* (words) to
  the previous one is ignored (tables of contents, signatures); text before the first chapter is an *Opening* if long enough; a book with
  fewer than two headings is cut into slices.
* **Your edits** (Edit chapters): headings you removed are dropped, paragraphs you start chapters at are added (your starts ignore the
  minimum length), titles you give replace the found ones; the text before the first start is an "Opening". Edits name paragraphs by
  their opening words and apply everywhere chapters do.
* **Code**: `core/narrative.py: segments`, `_is_heading`, `_edited_starts`, `book_segments`, `edit_chapters`.

### 8.2 Arcs
* **Says**: how something rises and falls through the books.
* **Calculation**, per segment: *entities*: mentions per 1,000 words; *events*: tokens BookNLP marks as EVENT per 1,000 words;
  *supersenses*: supersense tags starting in the segment per 1,000 words (runs of one supersense count once); *dialogue*: the share (%) of
  the segment's words inside quotes; *topics*: see 11.
* **Books combined** (the Timeline of Arcs, Sentiment and Lexicons): every book is cut into the same *n* equal slices; slice *k* of
  the combined arc is slice *k* of every book, its value the **mean of the books' own values** there (every book weighs the same,
  whatever its length), leaving out a book where the line has no value (a character not in it); its count is the books' counts added
  up. Only with equal slices by number: chapters and slices of so many words don't line up.
* **Code**: `core/narrative.py: arcs`, `books_combined` (through `timeline`, which every arc route uses).

### 8.3 Style figures
Per book, chapter or slice. Only sentences that start inside the span count as sentences.

| Figure | Calculation |
|---|---|
| Sentence length | mean words per sentence (and standard deviation, median) |
| Word length | mean letters per word |
| MATTR | as in 5.6 (windows of 100 words) |
| Hapaxes | words occurring once in the text, as a share of its words |
| Lexical density | share of words that are nouns, proper nouns, verbs, adjectives or adverbs |
| Dependency distance | mean number of tokens between a word and its syntactic head |
| Tree depth | mean, over sentences, of the depth of the deepest word in the dependency tree |
| Subordinate clauses | relations advcl, ccomp, xcomp, acl, relcl, csubj per sentence |
| Passives | passive subjects (nsubjpass) per 1,000 words |
| Questions | sentences containing `?`, per 100 sentences |
| Dialogue share | share of words inside quotes |
| Flesch Reading Ease, Flesch–Kincaid grade | `206.835 − 1.015 × sentence length − 84.6 × syllables per word`; `0.39 × sentence length + 11.8 × syllables per word − 15.59`; syllables are estimated from vowel groups, so treat both as approximate |
| POS profile | share of words that are each part of speech |
| Word choice | ratios of adjectives, adverbs and nouns to verbs, dynamic and static verbs, shares of verbs and nouns by supersense category, supersenses per 1,000 words: section 18 (its own table below the POS profile, and a group of the chart's figures) |

* **Code**: `core/narrative.py: style_metrics`, `style`; word choice: `core/wordchoice.py: span_tally`, `table`.

---

## 9. Stylometry

* **Says**: which texts (books, chapters or slices) are written most alike, judged by how often they use the most frequent words.
* **Calculation**: each text's relative frequency of each of the *n* most frequent words (word forms, lowercased; optionally without pronouns;
  words missing from too many texts are culled), turned into z-scores across the texts. **Classic Delta** (Burrows 2002) is the mean absolute
  difference of two texts' z-scores; **Cosine Delta** (Smith & Aldridge 2011) is 1 − the cosine of their z-score vectors, usually the most
  reliable; **Euclidean** is the straight-line distance. The **cluster tree** joins the closest texts first (average, complete or Ward
  linkage). The **map** is a principal component analysis of the z-scores (two axes, with the share of variance each keeps and the words that
  weigh most). **Nearest texts** lists each text's three closest.
* **Read it as**: small distance = similar frequent-word habits (author, genre, period). Short texts (under about 2,000 words) give
  unstable results; at most 400 texts are compared.
* **Code**: `core/narrative.py: stylometry`, `cluster`.

---

## 10. Sentiment and lexicons

* **Sentiment**: VADER's *compound* score (−1 most negative to +1 most positive; Hutto & Gilbert 2014) for each BookNLP sentence, averaged
  over the sentences that start in a segment. "Around an entity" averages only sentences that mention it. *Positive* / *negative* sentences
  score at least +0.05 / at most −0.05.
  * **Read it as**: rough tone. VADER was built for social media; literary irony, archaic wording and negation are handled badly.
  * **Code**: `core/narrative.py: sentence_scores`, `sentiment`.
* **Lexicons**: with a word lexicon you load (the emotion lexicon, such as the NRC Emotion Lexicon, or any list of words of your own, with or
  without categories), the words of each category per 1,000 words of a segment; a word counts by its form, else by its lemma, and may belong
  to several categories. A file with one word on each line is one category, named after the lexicon. A .csv or .tsv file (tabs, commas or semicolons, with quotes and a header row) may list a word and a category per row, optionally with 1 or 0, or have a column per category with the names in its first row. Only single words are matched (no phrases
  or stems). **Code**: `core/narrative.py: lexicon_arc`, `core/lexicons.py`.

---

## 11. Topics

A topic model finds groups of words that tend to occur together and says how much of each document belongs to each group. Topics on
fiction are settings, activities and registers rather than themes: a map to explore, not findings. Everything depends on the document
size, the words kept and the number of topics.

* **Documents**: chunks of about N words ending at a sentence, groups of paragraphs, chapters or slices, or whole books; narration and
  dialogue, or either alone. **Words** kept: chosen parts of speech, as lemmas or forms; tokens inside name (or person, or any entity)
  mentions are dropped using BookNLP's mentions; general words and your stop-words removed; words in too few or too many documents removed.
  The one function that decides which words count is `core/topics/model.py: kept_tokens`.
* **Fit**: NMF on tf–idf (default) or batch LDA, with a fixed seed. Each document gets shares of each topic that sum to 1.
* **Share of the text (topic size)**: the topic's average weight over documents, weighted by the words kept in each.
* **Coherence** (−1 to 1, higher is better): the mean normalised PMI of the co-occurrence, in documents, of the ten top words of the topic.
  **Diversity**: the share of distinct words among all topics' top ten. **Stability**: the model is re-fitted with other seeds and a topic
  *recurs* when a re-run has a topic (matched one to one) sharing at least 40% of its top 20 words; shown as "recurs in x of n runs".
  * **Read them as**: with few documents expect low stability; a topic that recurs in few runs may not be a robust pattern.
  * **Code**: `core/topics/model.py: npmi_coherence`, `diversity`, `match`, `stability`.
* **Relevance** (Sievert & Shirley 2014; the slider): `λ × log p(w|topic) + (1 − λ) × log(p(w|topic) ÷ p(w))`. λ = 1 ranks the most
  probable words, lower values favour words exclusive to the topic. **Exclusive share**: the part of a word's weight in the model that
  belongs to this topic. *Code*: `relevance`; `core/topics/page.py: part_words`.
* **Where it occurs**: each document shaded by its share; the **arc** puts each document in the chapter or slice holding its middle and
  shows the topic's share of the words there; the **books table** compares a book's documents' shares with the other books' with a
  **Mann–Whitney U** test (two-sided; needs at least five documents on each side; documents next to each other are not independent, so p is a guide).
  *Code*: `part_where`, `arc_of`, `group_rows`, `mann_whitney`.
* **Entities and speech** (also the Topics section of an entity's page): each document counts as topic text to the extent of its share
  (30% share = 30% topic text, 70% elsewhere). An entity's rate per 1,000 words in topic text is compared with its rate elsewhere: *share*
  (part of its mentions falling in the topic's text), *lift* (that share ÷ the topic's share of the whole model), *score* (a signed
  log-likelihood). The score ranks; it is not a significance test, because the weights are not independent observations. For speakers the
  rate is per 1,000 dialogue words, for narrators per 1,000 narration words. *Code*: `assoc`; `core/topics/uses.py: entity_topics`.
* **Compare topics**: *similarity by shared words* is the cosine of their word weights (0–1); *by appearing together* is the correlation of
  their document shares (−1 to 1); the map is classical multidimensional scaling of 1 − similarity (nearer = more similar; two axes keep
  only part of the picture), the tree is average linkage. *Code*: `core/topics/compare.py`.
* **Grids**: each cell is the item's (book's, character's, speaker's) share of mentions or words in each topic's text, or that against the
  topic's average ("× 2" = twice as much as usual).

---

## 12. Networks

Nodes are entities of the types you choose; an edge's **weight** is:

| Links by | Says | Weight |
|---|---|---|
| Same sentence / paragraph | mentioned together (undirected) | number of shared sentences / paragraphs |
| Speaker mentions them in a quote | who talks about whom (directed, speaker → mentioned) | quotes; speakers mentioning themselves are not counted |
| Speaker talks to them | who talks to whom (directed, speaker → estimated addressee) | quotes; inherits the addressee estimate (5.5) |

Two minimum ranges (the range of an item is the number of books it is in, as on the Corpus pages) keep what holds across the selected books (each its own setting, apart from the one of Over the book): **Minimum range per entity** leaves out
entities that are in fewer of the books (an entity that is not linked across books is in one, so this mostly concerns linked persons and groups), and **Minimum range per link**
drops edges found in fewer books (a pair counts for a book when it is linked there at least once; for "talks to" the book is the one the estimated quote is in). Both default to 1, no limit; the weights themselves are
unchanged, still summed over all the selected books. Edges weaker than the *minimum link strength* are dropped, and unlinked entities too unless you show them. A network of a whole library can
have thousands of entities, more than anyone can read and more than the measures and the layout can work out in a useful time, so at most
*Show at most* entities are kept (300 by default, 1,000 at most): those with the greatest strength (the sum of their edge weights), then the
most mentions. The page says how many entities there were. Measures are those of the network that is shown, not of the whole library, so a
shown entity's strength or community can differ from what it would be among all of them; raise the minimum link strength to thin a network
out evenly instead.

| Measure | Says | Calculation |
|---|---|---|
| Degree | number of neighbours | edges at the node (undirected version for directed networks) |
| Strength | how much it is linked | sum of edge weights |
| In-/out-degree, in-/out-strength | (directed only) incoming and outgoing edges | counted separately |
| Betweenness | how often it lies on the shortest paths between others (a broker) | normalised 0–1, with distance = 1 ÷ weight so frequent pairs are close |
| Closeness | how near it is to everyone else | with distance = 1 ÷ weight; can exceed 1; compare within one network only |
| Eigenvector | linked to well-linked entities | weighted, on the undirected graph; meaningful within a connected part, near zero outside the largest |
| Clustering | how much its neighbours are linked to each other | weighted clustering coefficient, undirected |
| Community | a tightly linked group | Louvain method on weights, seed 42 so results repeat |
| Density, components, communities | of the whole network | edges ÷ possible edges; connected parts; number of communities |

* **Read it as**: measures describe the *network you built*; they change with the link kind, types and minimum strength. Circle size is one
  chosen measure; the layout is a spring layout (positions carry no meaning beyond nearness within a connected part).
* **Focus**: hovering or clicking a circle highlights it and its neighbours; this is display only.
* **Code**: `core/network.py: build` (including the limit), `measures`, `layout`, `export`.

---

## 13. Suggestions (links and narrators)

### 13.1 Link suggestions
* **Says**: pairs of entities in different books that may be the same person or place.
* **Data**: names (PROP mentions), BookNLP's pronouns, entity type, and the *series* of each book (Library).
* **Calculation**: only entities with at least one proper name and two mentions, of the same type, in different books **that share a series**
  (compared case-insensitively; books without a series get none). Titles (Mr, Dr, Father…) are set aside. Score, strongest evidence
  first: the same full name 1.0; the same single name 0.85; for people the same last name 0.6; spellings at least 85% alike (`0.7 × similarity`);
  a shared word 0.35. For people, agreeing pronouns add 0.05 and different pronouns subtract 0.4. Scores of 0.2 or less are dropped.
* **Read it as**: an ordering of what to check, not a probability. "Not the same" is remembered.
* **Code**: `core/links.py: suggest`.

### 13.2 Narrator suggestions
* **Says**: who narrates a book, and which stretches are told by someone else.
* **Data**: first-person pronouns (I, me, my, mine, myself) outside quotes, each belonging to the coreference group BookNLP put it in.
* **Calculation**: the suggested narrator is the character behind most of them. A *run* is a stretch of paragraphs whose "I" belongs to
  someone else (paragraphs without an "I" can sit inside it, up to a set number in a row); *evidence* is the number of "I" in the run
  that belong to that character, *strength* their share of all "I" in the run. Runs with too little evidence and runs you rejected are
  left out. "We" is not counted, and third-person books give no suggestions.
* **Code**: `core/narrators.py: book_suggestions`.

---

## 14. Described as

What a target (an entity, group, tag or gender) is described and called as, and by whom. The words are those of the entity profile (section 1);
what is new is *who says them*.

### 14.1 Findings and describers

*Says*: each row is a word (or form), each column a kind of describer, each cell how often that describer says it of the target.
*Read it as*: a **finding** is one thing said about the target at one of its mentions: a **modifier** (adjective, apposition, "is desolate"), an
**action** (it is the subject of a verb), something **done to it**, a **possession**, a **preposition and setting** (section 1.6), or a way it is **called**:
the exact text of a mention that is a **name**, a **description** (a noun phrase such as "the great Mire") or a **pronoun** (lower-cased; section 1.5).
The **describer** is the speaker of the quote the mention is in; outside quotes it is the narrator of that paragraph. *Assumes*: BookNLP's speaker
attribution for quotes, and the narrators you have set (Narrators page; a book with none set has an unnamed narrator, "Narrator of <book>").
A narrator who is a character is that character: Watson's speech and the narration he tells are one describer. A quote with no attributed speaker is
its own describer ("Unattributed quote"). A pronoun inside a quote often means the speaker or listener, so "Called: pronouns" is least informative in speech.
*Data*: `.tokens`, `.entities`, `.quotes`, your narrator corrections and your links. *Calculation*: the finding's mention token decides: inside a
quote (`quote_at`) the speaker, otherwise the paragraph's narrator (`dialogue.narrator_of`). *Code*: `core/described.py: findings, Describers.of`.

### 14.2 Columns

*Says*: which describers are grouped together. **Each describer**: the top *n* (default 8) with most findings, the rest in "All others". **Gender**: the
describer's BookNLP-predicted pronouns (section 2); a describer that is no person (an unnamed narrator, an unattributed quote) is its own column.
**Tag**: the describer's tags; a describer with two tags is in both columns, one without is "(no tag)". **Book**: where the mention is. **Narration or
speech**. **Columns you pick**: up to twelve specs of your own (any entity, group, tag or gender); a describer can be in several. *Read it as*: where
describers overlap, one finding counts once in each column it is in, so the columns can add up to more than the All column; findings in none of your picked
columns are only in All. Same-named columns (one character's entity in each of several books) show their book. *Code*: `core/described.py: column_keys, picks, _layout, _shown`.

### 14.3 The numbers in a cell

* **Count**: findings of that word credited to that column. **Share**: the count as a percentage of all the column's findings of that kind.
* **Per 1,000 words**: the count divided by the words that column's describers speak or narrate in the books the target appears in, times 1,000
  (`core/described.py: _sources`: the words of every quote and of every paragraph's narration). *Read it as*: the fair way to compare a describer who
  says much (a narrator) with one who says little.
* **Keyness (G²)**: the log-likelihood (section 3, `stats.compare`) of the word in this column against all the other columns together, with the
  column's total findings as its size. Signed: **+** means more typical of this column than of the others, **−** less. **p-value**: that of the G²
  (chi-squared, one degree of freedom). *Read it as*: a ranking, not a test: findings are not independent observations (one sentence can
  hold several), and a table of many words will show some small p-values by chance; no multiple-comparison correction is applied. With one column,
  keyness is not defined (shown as 0). Blue cells are those with G² > 0 and p < 0.05, red G² < 0 and p < 0.05.
* **Sentences**: clicking a count lists the sentences; there are exactly as many as the count (`core/described.py: evidence`, which uses the same
  classification the table is counted from).

*Code*: `core/described.py: table`.

---

## 15. Statistics

Correlations and descriptive statistics of **variables** measured over **cases** (the Statistics tab). Every figure is computed from the table
in the Data view: one row per case, one value per variable. Download it to check any figure, or to go on in R, SPSS, JASP or a spreadsheet.

### 15.1 Cases and samples

*Says*: what one row of the data is, and which text its values are measured in (its **sample**).
*Read it as*: **text pieces** are equal slices of each book (the default: a number per book, cut by token count, or one every so many words, such
as 200: each book is cut at every 200th word, and a rest under half a slice joins the last slice), BookNLP's sentences, chapters (your chapter
edits apply; a book without headings is cut into slices), or whole books; their sample is their words in the chosen part of the text (everywhere, narration, dialogue, or someone's speech, as in the Corpus tools).
**Participants** are entities taken as people in a study (default: every person above your minimum mentions; any entity, group, tag, gender or type).
Their sample is one of: **what they say** (the words of their quotes; with plural groups on, a plural speaker's quotes count for its members),
**what they say and narrate** (plus the narration of every paragraph whose narrator is that character; an unnamed narrator, or narrators you linked,
take part as their own participant unless you turn that off), **sentences mentioning them** (every sentence with one of their mentions, whoever says
it; a sentence naming two participants counts for both), or **what is said about them** (their Described-as findings, section 14: counted in
findings, not words). *Assumes*: BookNLP's quote attribution and coreference, and the narrators you set. A case whose sample is empty or smaller
than the **minimum sample** (default 100 words, 1 for sentences, or 10 findings) is left out, and so is a participant who is in fewer of the selected books than the **minimum range** (the number of books, as on the Corpus pages; default 1, no limit; its own setting, counted in all the selected books even when a split by book measures them in one), and the page says how many: a rate from a very small sample swings
wildly (someone with three words has 333 "the" per 1,000). With **sentences** most counts are 0 or 1, so a rate per 1,000 words mostly
mirrors sentence length: "present (0/1)" is usually the clearer measure, and with thousands of cases even tiny correlations are "significant". Split by book (15.4), a participant is measured again in each book alone, and the
minimum applies there. *Code*: `core/cases.py: build`.

### 15.2 Variables

*Says*: what is measured in each case's sample.
* **Words or phrases**: hits of a Corpus query (simple or pattern, word forms or lemmas, several lines as alternatives), every hit counted (no
  20,000 limit), in the case that holds the hit's first word. In the findings sample a query is one word per line, matched against each
  finding's word, optionally only findings of one kind.
* **Mentions** of an entity, group, tag, gender or type, all or only names, descriptions or pronouns, counted where the mention starts. A
  participant's mentions of themselves count too ("I" in Watson's speech is a mention of Watson).
* **Speech** of an entity, group, tag, gender or type: the **words they speak** (each word of their quotes counted in the case that holds it) or
  their **quotes** (each counted in the case that holds its first word), optionally only quotes of one sentence type (questions, exclamations,
  statements, with or without weighing the speech verb, as below). Speakers are as on the Dialogue pages (a plural speaker counts for its
  members when plural groups count for them); a quote the target says through several of its members counts once. Per 1,000 words, words spoken
  is the target's share of the sample in words (‰); quotes also have **% of quotes** (of all the sample's quotes). Not in the findings sample.
* **Attributes**: of a participant, **is one of** (1 if they belong to an entity, group, tag or gender, else 0: one such variable per gender is the
  usual way to bring gender in), mentions, words spoken, quotes and books (counted in the selected books, or in one book when split by book; a
  narrator role that is no entity has none). Of a text piece, its number in its book, its position (% into the book) and its length (words).
* **Layers**: **supersenses** (BookNLP spans, a run of tokens with one supersense counted once), **relations** (actions, done to them, modifiers,
  possessions, prepositions, section 1.6, of a target or of any entity, optionally one word, where the mention is), **lexicon categories** (words
  of a category of one of your lexicons, such as the emotion lexicon, by form, else lemma), **speech sentence types**, **sentiment**, **style**,
  **word choice** (parts of speech, adjective, adverb and noun per verb ratios, dynamic and static verbs, shares of verbs and nouns per supersense;
  figures of the sample's words, not counts, so no measure; section 18), **sound and rhythm** (below), and **topics**.
* **Speech sentence type**: how many of the sample's quotes are questions, exclamations or statements. A quote is a question or an exclamation
  if it contains `?` or `!` (a question wins if it has both), else a statement; with **weigh the speech verb**, a quote without either mark still
  counts as a question when its speech verb implies one (*asked*, *inquired*…) or as an exclamation (*exclaimed*, *cried*…), as on the Dialogue
  tabs. Each quote counts once, in the case that holds its first word (a quote said by two participants counts for both). *Assumes*: the sample
  holds quotes: any text piece (in narration scope there are none), or a participant's speech, with or without narration; for the other samples the
  variable has no values and says why. A quote counts as one however many sentences it has, so this is not the "Questions" style figure, which
  is the share of sentences or other units with a `?`.
* **Topics**: one topic of a stored topic model, as its share (%) of the sample's words. Each word in a model document counts as topic text to the
  extent of that document's share (as in section 11), and the value is the mean over the sample's words that lie in the model's documents.
  *Assumes*: the model was fitted on the cases' books. Cases from books it wasn't fitted on (or with no word in its documents) have no value; the
  page warns and says how many. A topic's value depends on the model's document size and settings, like everything about topics.
* **Units** (for sentiment and style): sentences for text pieces and for "sentences mentioning them" (a sentence cut by a piece's edge or its scope
  is the part inside), each quote for speech, each paragraph's narration for narration. **Sentiment**: the mean VADER compound score of the units
  (section 10), or the share of units at or above +0.05 (positive) or at or below −0.05 (negative). **Style**: word length, MATTR, hapaxes, lexical
  density and passives per 1,000 words over the sample's words, as in section 8.3; unit length (words per unit) and the share of units with a
  question or exclamation mark over its units. For a whole book these are the figures of the Style page. **Sound and rhythm**: any figure of
  section 17 (stress, cadences, sound runs, the sound profile, coverage), or one phoneme per 1,000 words, over the sample's units, under the
  workspace's window and boundary; for a whole book these are the figures of the Style page. Without the pronunciation dictionary the variable
  has no values and says how to install it.

*Measures*: a count becomes a value **per 1,000 words** of the case's sample (default; in the findings sample **% of findings**), stays a **count**,
or becomes **present** (1 if above 0); a speech sentence type and a speaker's quotes also have **% of quotes** (of all the sample's quotes; no value where the sample has
none). Use rates: raw counts grow with a sample's size, so two counts correlate over pieces of different lengths
for that reason alone. A variable that doesn't fit the cases (a piece attribute for participants, mentions or speech among findings, sentiment without
vaderSentiment, a lexicon category without that lexicon, a topic of a model no longer stored) has no values and says why. *Code*: `core/variables.py`, `core/layers.py`.

### 15.3 Correlations

* **Says**: how closely two variables go together over the cases.
* **Read it as**: **Pearson's r** (−1 to +1) measures a straight-line relation; with a 0/1 variable (a gender, a tag) it is the point-biserial
  correlation, so "she/her × rate of *indeed*" says whether women say *indeed* more (+) or less (−) than the rest. **Spearman's ρ** is r of the
  ranks (ties get their average rank): it measures any relation that only goes one way and is less moved by a few extreme cases, which word
  rates often have. Roughly, |r| of .1 is small, .3 medium, .5 large. A correlation is not a cause: two words that both belong to dialogue
  correlate over chapters because dialogue comes and goes.
* **p**: two-tailed, from t = r·√((N−2)/(1−r²)) with N − 2 degrees of freedom (also for ρ, as SciPy and most packages report it).
  **95% interval**: from Fisher's z, with standard error 1/√(N−3) for r and √(1.06/(N−3)) for ρ (Fieller, Hartley & Pearson 1957).
  **Stars**: * p < .05, ** p < .01, *** p < .001, after the correction. **N**: the cases where both values exist (missing values are left out pair by
  pair, so N can differ between cells). With fewer than 3 cases, or a variable that doesn't vary, there is no coefficient (a dashed cell).
* **Correction**: a matrix of 20 variables makes 190 tests, and about one in twenty is "significant" at .05 by chance. **Bonferroni** multiplies
  each p by the number of tests in the table; **Holm** (1979) multiplies the smallest by the number of tests, the next by one fewer, and so on,
  never letting a later p fall below an earlier one: it is less strict than Bonferroni and still guards against any false finding.
* **Assumes**: independent cases. Neighbouring chapters share characters, scenes and style, and a character's speech is shaped by the scenes they
  are in, so p-values are guides, not proofs. Pearson's p also assumes roughly normal values; prefer Spearman for skewed rates.
* **Shape**: one list of variables gives a matrix (each pair once, below the diagonal); two lists give each row variable against each column
  variable. The heatmap shades r from grey (0) to blue (+1) and red (−1).
* **Code**: `core/stats.py: correlate, adjust, stars`; `core/statstab.py: correlations`.

### 15.4 Descriptive statistics

* **N**: cases with a value. **M**: the mean. **SD**: the standard deviation and **V**: the variance, both of a sample (divided by N − 1, as SPSS,
  R and JASP do). **Mdn**: the median; **Min**, **Max**. **SE**: the standard error of the mean, SD ÷ √N. **95% CI**: the interval of the mean, M ± t × SE
  with t for N − 1 degrees of freedom.
* **Split by**: participants by gender (BookNLP's prediction; a narrator role or a non-person is "Not a person"), tag, saved group or book; text
  pieces by book. A participant is in every group they belong to (two tags, two blocks; "(no tag)" and "(in no saved group)" gather the rest).
  Split by book, each participant is measured again in that book alone, so their value there is that book's, and the minimum sample applies in
  that book.
* **Code**: `core/stats.py: describe`; `core/statstab.py: descriptives`.

### 15.5 The files for R

The Data view's **Download for R (.zip)** gives the cases and variables of the last run as plain files, for the tests the page does not do
(regression, ANOVA, mixed models, diagnostics, plots).

* **cases.csv**: a row per case, a column per variable. A variable that counts something (words, mentions, supersenses, relations, lexicon
  words) has two columns whatever its measure on the page: `<name>_n`, the raw count, and `<name>`, the count per 1,000 words of the case's
  sample (% of findings in the Described-as sample). The other variables (attributes, sentiment, style figures, topics) have `<name>` only.
  `n_words` (or `n_findings`) is the size of the sample; with it a count can be modelled as such, for example
  `glm(said_n ~ position_pct + offset(log(n_words)), family = poisson)`. An empty cell is a value the case does not have.
* **cases_long.csv**: the same values, a row per case and variable (`case_id, variable, count, n_words, value`).
* **variables.csv**: each column name, its label, kind, unit and the complete request (`spec`); **dropped.csv**: the cases left out, and why.
* **load.R** reads the tables; **analysis_example.R** (the Settings page can leave it out) is a correlation, a regression and, for a 0/1
  participant attribute, an ANOVA on the first variables. Column names are the labels as plain ASCII (`“said” (lemma)` → `said_lemma`),
  numbered if two clash.
* **Code**: `core/rexport.py`.

---

## 16. Over the book

Shown on the Over the book page: one target (an entity, group, tag or gender) followed through the slices of one book. The within-book counterpart of section 4.

### 16.1 Slices and what belongs to one

* **Says**: where in the book each figure is. The book is cut exactly as set under Measure over (section 8.1): equal slices, by number or by words, or chapters with your edits, always per book, at most 200 slices.
* **Calculation**: a mention, and each finding of it (what it does, what is done to it, a modifier…), is counted in the slice that holds the **first word of the mention**. Words of a slice are its words, as in section 8.1.
* **Code**: `core/overbook.py: slicing, table`.

### 16.2 Overview per slice

* **Says**: per slice, the mentions, *mentions per 1,000 words of the slice*, the *names / descriptions / pronouns %* of its mentions and each list *per 100 mentions*.
* **Read it as**: how present the target is, and how it is spoken of, along the book. A slice without mentions has no percentages (—).
* **Code**: `core/overbook.py: table` (`overview`).

### 16.3 Words over the book

* **Says**: for each word of the chosen list, its count in each slice and its **share of that slice's list**. A word can stay level while the character acts more, because shares are of the list, not of the book.
* **Heat grid**: each cell is shaded by the share relative to the word's own highest share, so each word shows its own shape whatever its frequency. Faint: the word is absent from a slice that has other words. Hatched: the slice has nothing in the list.
* **χ², p, Cramér's V**: as in section 4, with the slices in place of the books (degrees of freedom: slices with findings − 1). Is the share different between slices at all?
* **Trend z, p**: the **Cochran–Armitage test for trend in proportions**, the narrower question whether the share steadily rises or falls from the first slice to the last. With a word's count *xᵢ* in slice *i* of size *nᵢ* (the list's size), position scores *tᵢ* = 0, 1, 2…, overall share *q* = Σxᵢ ÷ Σnᵢ and *N* = Σnᵢ:
  `z = Σ tᵢ(xᵢ − nᵢq) ÷ √( q(1 − q) · (Σnᵢtᵢ² − (Σnᵢtᵢ)² ÷ N) )`, two-tailed p from z² against χ² with one degree of freedom. z is positive when the share rises. Slices with an empty list are left out (their position still counts). Because it works from counts and slice sizes, a rare word that happens to sit late is not made to look like a strong trend, as a correlation of the shares with the slice number would.
* **Assumes**: enough expected occurrences in each slice. With many slices and few occurrences both tests are only a guide; raise the minimum frequency. Words below it are listed without tests. Occurrences are not independent draws (a repeated phrase counts every time), so treat p as a ranking aid, as in section 3.
* **Code**: `core/stats.py: across, trend`; `core/overbook.py: _series, table`.

### 16.4 Kinds of action over the book

* **Says**: which kinds of action (WordNet supersenses: cognition, communication, motion…) the target performs in each slice. Only the verbs the target is the subject of count (section 1.7); what is done to it is under words.
* **Calculation**: a cell is the kind's share of all the target's actions that have a supersense in that slice. The verb of a finding is the last token it highlights, so each action is placed in the slice of its mention. χ², Cramér's V and the trend are as for words (16.3).
* **Code**: `core/overbook.py: table` (`supersenses`).

### 16.5 The curve, and two targets

* **Says**: one figure along the book, for one target or two. The figures: mentions per 1,000 words, the shares of names, descriptions and pronouns, each list per 100 mentions (all from 16.2), or one word's or one kind of action's share (16.3, 16.4). The page offers them as three categories, Figures, Words and Actions, each with its own list. The words listed are those of the list chosen for them (actions, done to them, possessions…; the curve has its own choice, apart from the list of the word tables) that the target has, in the order the word tables give them (most frequent first); with two targets the first's, then the second's that the first doesn't have, up to 100 (`MEASURE_WORDS`). A gap is a slice with nothing to take a share of; a word the table does not list is 0 in a slice that has a list.
* **Two targets**: as on the Compare page the second target leaves out every member of the first (an entity inside a group of the first is not counted twice), and both are cut at the same slices. Nothing is tested between the two: the tests of 16.3 and 16.4 are each target's own change over the book.
* **Code**: `core/overbook.py: report`.

### 16.6 In the profile and on the Compare page

* **In a profile**: line charts only. Mentions per 1,000 words per slice; the words of the chosen list and the kinds of action, each line one item's share of the slice's list, for the eight most frequent, or the eight most changed (the tested items with the largest χ², as in section 4's chart; the choice is **Charts**). No tests are shown in the profile; the page has them. The book is the first one the target is in unless you choose another.
* **On the Compare page**: the curve of 16.5 for the two sides, measured in the same book. Limiting a side to some books there decides which books it is in, not which book is drawn; when **no book holds both sides** (two whole books as the sides, two entities of different books, sides limited to different books) a book holding only one would show the other as nothing, so each side is measured in its own book and lined up by relative position as in 16.7, with the slices per book and the similarity of the curves; the section says so and links to 16.7's page.
* **Code**: `static/js/overbook.js: overProfile, overCompare`; the figures are the page's (`core/overbook.py: report`).

### 16.7 Two books aligned

* **Says**: a target in one book against the same or another target in another book, compared stretch by stretch, so that the books' different lengths don't matter.
* **Calculation**: each book is cut into the same number *n* of equal slices (token counts, as in section 8.1; *n* is the page's own, 2 to 200), so slice *k* of *n* is the same relative stretch of each. Each side is counted only in its own book, with nothing left out of side B (unlike 16.5, where both are in one book and the second leaves out what the first includes). Everything else on a side is 16.2–16.4.
* **How alike the curves are**: for the figure shown, Pearson's *r* between side A's values and side B's, slice by slice, and Spearman's *ρ* (Pearson's r of the ranks); p from *t* with *N* − 2 degrees of freedom, *N* = the slices with a value on both sides (as in 15.3). *r* asks whether the two rise and fall together, *ρ* whether they rank the slices the same way; a flat curve has none (—), and so does *N* < 3.
* **Assumes**: that slices are independent cases. Neighbouring slices of a book are not (a scene runs over a boundary), so p is optimistic; use *r* and *ρ* as the size. Two books of very different length compare unevenly: a slice of a long book holds far more words, so a rare word's share is steadier there.
* **Code**: `core/overbook.py: aligned, curve, similarity`.

### 16.8 Books combined

* **Says**: what a target does over the course of *all* the selected books together: the same figures as 16.2–16.5, but across books, so that the result is a trend of the target in general rather than of one story.
* **Calculation**: each book that has the target is cut into the same number *n* of equal slices (as in 16.7), so slice *k* of *n* is the same relative stretch of each. **Every book weighs the same.** For slice *k*: counts (words, mentions, findings, a word's or kind's count) are **added** over the books; a share or rate (mentions per 1,000 words, names, descriptions and pronouns, each list per 100 mentions, a word's share of the slice's list) is the **mean of the books' own** values, a book with nothing to take it of in that slice (no mentions, no list) being left out of that mean and a book whose list lacks the word counting as 0 %. A short story therefore weighs as much as a novel, which the sum of counts would not give.
* **The trend**: in each book, the Cochran–Armitage z of the word's counts against the slice sizes (as in 16.3). The books' z values are put together with equal weight, **Stouffer's method**: *Z* = Σ *z*ᵢ / √*m* for the *m* books that have a z, and p from *Z*² against χ² with one degree of freedom (two-tailed). A book where the word is absent or fills the whole list has no z and is left out for that word (**Books** says *m*); **Rising** and **Falling** count the books with *z* > 0 and *z* < 0, significant or not. Two books that rise alike give a larger |Z| than either alone; one that rises and one that falls cancel.
* **χ²**: each book's Pearson χ² across its slices (16.3), added up over the same books, with the degrees of freedom added up and p from that. It asks whether the share varies between slices *within* the books at all, **not** whether the books agree: a word that rises in half the books and falls in the other half has a large χ² and no trend. Cramér's V (the sum of the books' V has no clear meaning) and the residuals are not given.
* **Minimum frequency, minimum range and Bonferroni**: a word is tested when it occurs at least the minimum frequency **in all the books together** (Settings → Words, *in each book separately*: a book counts for a word only where the word reaches the minimum, those books are the ones tested and combined, and there must be as many as the minimum range) and in at least the **minimum range** (the number of books, as on the Corpus pages; default 1: no limit; the page's own setting, beside the minimum frequency), which keeps a trend from resting on one or two books; the others are listed with their counts but without tests. The level is divided by the number of words tested, as in 16.3.
* **The curve**: the bold line is the mean of the books' own values at each position (as above); **Show each book** draws every book's own values faintly behind it, to show whether the books follow the mean or only a few of them do.
* **Assumes**: that the books are independent texts and that the target is comparable between them (a gender or a type across a whole library pools many different characters; an entity linked across books is the same person). Within a book the slices are not independent (16.7), so p is optimistic.
* **Code**: `core/overbook.py: combined, _series_books`; `core/stats.py: combine_trends, combine_across`.

---

## 17. Sound and rhythm

Prose rhythm and sound patterning, worked out from how each word is pronounced (17.1). All of it needs the optional CMU Pronouncing
Dictionary (`pip install "alex-booknlp-analyser[sound]"`). The figures are counted over **units** (17.2) and added up over a
sample's units before they are divided, so a long sentence weighs more than a short one. They are shown on the Style page of Arcs and
style (per book, chapter or slice), as Statistics variables (15.2) and for a target's speech in Over the book (17.7). The run
**window**, **boundary**, **alliteration** and **repetition** settings (17.5) are set once for the workspace, under Settings → Sound and rhythm.

### 17.1 Pronunciation

* **Says**: for every word of a book, its syllables, which of them are stressed, and (where known) its sounds.
* **Data**: BookNLP's words and parts of speech; the CMU Pronouncing Dictionary (about 126,000 words with 135,000 pronunciations,
  American English of today, in ARPAbet phonemes with each vowel's stress: 1 primary, 2 secondary, 0 none); your corrections.
* **Calculation**, for each word, the first that applies:
  1. **Your correction** of the word, as you typed it: a stress pattern (1 or / stressed, 0 or x unstressed) or phonemes. Corrections
     are made under Sound and rhythm → Pronunciation (which lists the guessed words, most frequent first) or Settings → Sound and
     rhythm, and kept with the workspace (they travel in its export).
  2. **The dictionary**: the word as it is; else the word an abbreviation stands for (Dr. → doctor, St. → saint, Col., Capt.,
     Gen., Prof., Rev., Esq., Messrs., Sq.); else the American spelling (-our → -or, -re → -er after b or t, -ise → -ize,
     -yse → -yze, gips- → gyps-, -ogue → -og); else its hyphenated parts in turn; else, for a word ending in s, the word without it
     plus the ending's sound (Stapletons). Of several pronunciations the first, except that a noun, adjective or name takes the one
     stressed earliest and a verb the one stressed latest (REcord, reCORD), among those with as many syllables as the first.
  3. **A guess**: syllables from vowel groups (a silent final e not counted), the first stressed. A guess has no phonemes.
  4. **None** for a word without letters (1889): a gap in the rhythm.
* **Stress** is two-level: primary and secondary stress both count as stressed. In running text a one-syllable word is
  **unstressed** if it is a function word (determiner, preposition, pronoun, auxiliary, conjunction, particle: *the, of, he, was,
  and, to, not*) and **stressed** otherwise, whatever the dictionary says (it lists *of* as stressed); a negative contraction
  (*don't*, *can't*) stays stressed. Longer words keep the dictionary's pattern, and your corrections are never changed.
* **Contractions** that BookNLP splits (*do + n't*, *Holmes + 's*) are looked up as one word (*don't*). When only the first part is
  listed, the ending's sounds are added: 's is a syllable of its own after a hissing sound (*Holmes's*), S after a voiceless
  consonant (*it's*) and Z otherwise; n't, 'll, 've and 'd are a syllable after a consonant (*could-n't*). The clitic itself then has no
  syllables of its own.
* **Coverage**: how many of a stretch's words came from your corrections, the dictionary, a guess, or had none. In *The Hound of
  the Baskervilles* 99.3 % of words are in the dictionary; most guesses are names and places (Grimpen, Merripit, Lestrade), which
  are the ones worth correcting.
* **Assumes**: that a modern American dictionary is close enough to the text's own pronunciation to compare texts with each other
  (it isn't a reconstruction of how they sounded); that word class is a fair guide to which monosyllables are stressed (emphasis,
  contrast and sentence stress aren't seen); that BookNLP's parts of speech are right.
* **Code**: `core/sound.py: pronounce, book_prons, coverage, parse_correction`.


### 17.2 Units, phrases and gaps

* **Units** are what a sample is made of, as for the style layer (15.2): sentences (a sentence cut by a slice's or chapter's edge is the
  part inside), a quote, a paragraph's narration. A unit is read phrase by phrase: a **phrase** ends at a pause (. ? ! ; : , a dash
  -- — –, a bracket, an ellipsis) and at the unit's end. A hyphen (*well-known*) is not a pause.
* A word without letters (*1889*) is a **gap**: stress isn't followed across it (no clash, lapse or interval spans it). Quotation marks
  and other non-words are passed over.
* **Code**: `core/prosody.py: sentence_units, tally, _unit`.

### 17.3 Rhythm

* **Says**: how much of the text is stressed, and how the stresses are spaced: crowded together, alternating, in threes, even or
  uneven.
* **Calculation**, over each phrase's string of syllables (stressed or not, as in 17.1), summed over the sample:

| Figure | Calculation |
|---|---|
| Stressed syllables (%) | stressed syllables ÷ syllables |
| Syllables per word, per unit | syllables ÷ words with a pronunciation; syllables ÷ units |
| Stress clashes per 100 syllables | pairs of stressed syllables side by side (*dark night*; three in a row are two clashes) |
| Stress lapses per 100 syllables | runs of three or more unstressed syllables (*memory of the victim* has one: -ry of the) |
| Binary, ternary gaps (%) | of the gaps between one stress and the next, the share with exactly one unstressed syllable between them (the alternation of iambs and trochees) and with exactly two (dactyls and anapaests) |
| Stress spacing nPVI | the normalised Pairwise Variability Index of the intervals between stresses (in syllables, *d*): 100 × the mean over successive pairs of \|*d*ₖ − *d*ₖ₊₁\| ÷ ((*d*ₖ + *d*ₖ₊₁) / 2). 0 is perfectly even spacing; the more the intervals vary, the higher. |

* **Read it as**: these figures differ only a little between prose texts: *The Hound of the Baskervilles*, *The Blue Carbuncle* and
  *Emma* all have 38–40 % stressed syllables, about 37 % binary and 22–24 % ternary gaps and an nPVI of about 50. Compare
  passages, speakers or narration and dialogue rather than expecting large differences between whole books.
* **Assumes**: the stresses of 17.1; that syllables are a fair stand-in for time (the nPVI of speech research is measured on
  durations, here on syllable counts).
* **Code**: `core/prosody.py: _phrase, figures`.

### 17.4 Cadences

* **Says**: how phrases end: the rhythm of the last few syllables before a pause, which classical and medieval prose shaped by rule
  (the *cursus*) and English prose often follows by ear.
* **Calculation**: at every phrase end, the syllables from the **last-but-one stress** to the end (a phrase with fewer than two stresses
  has no cadence). Patterns are named by the English cursus (/ stressed, x unstressed):

| Name | Pattern | Example |
|---|---|---|
| planus | / x x / x | *vóice of the píper* |
| tardus | / x x / x x | *wánting in cháracter* |
| velox | / x x x x / x | *mémory of the víctim* |
| trispondaicus | / x x x / x | *sérvants of the cóuntry* |

  Anything else is "other" and kept as its pattern. Each name is given as a share of all phrase ends with a cadence, and of
  **sentence ends** only (phrases closed by . ? ! … or by the end of the unit), with **cursus** the four together.
* **Read it as**: the four cursus forms make up 15–18 % of phrase ends in the books above, slightly more at sentence ends. The
  most frequent patterns overall are short ones (/ x /, / /, / x / x).
* **Assumes**: the stresses of 17.1 (a wrongly stressed final word changes the cadence); BookNLP's sentences and punctuation.
* **Code**: `core/prosody.py: cadence_of, cadence_type, CURSUS`.

### 17.5 Runs: alliteration, assonance, consonance, rhyme, repetition

* **Says**: how often nearby words share a sound, or are the same word again.
* **Data**: content words (nouns, verbs, adjectives, adverbs, names) with known phonemes (a guessed word has none; your correction can
  give them). Function words never take part, but nothing stops a run from passing over them.
* **What is shared**:
  * **alliteration**, by the setting *Alliteration by* (Settings → Sound and rhythm):
    * *stressed syllable* (the default): the first consonant of the onset of the word's stressed syllable (*polished, plated, pot*;
      *assistance* counts with S, its stressed syllable being -SIS-). The onset is the consonants before the stressed vowel that can
      begin an English syllable (S + stop, a stop or fricative + L, R, W or Y, S + stop + L/R/W/Y, or one consonant). A stressed
      syllable with no consonant before it doesn't alliterate;
    * *first sound*: the word's first sound, when it is a consonant (*cat, kill*; *knight, night*; not *cat, city*); a word
      beginning with a vowel sound doesn't alliterate;
    * *first letter*: the word's first letter as spelled, vowels included (*cat, city*; *apple, angle*; not *knight, night*). It
      needs no pronunciation, so guessed words take part too;
  * **assonance**: the stressed vowel (*late, save, occasions*);
  * **consonance**: the consonants after the word's last vowel, when that vowel differs (*man, town*); a word ending in a vowel has
    none;
  * **rhyme**: the stressed vowel and everything after it (*sound, round, found*);
  * **repetition**: the same word again, by the setting *Repetition is*: the *same lemma* among content words (the default: *walk,
    walked*), the *same word form* among content words (*walked, walked* only), or the *same lemma among all words* (function words
    too: *the … the*, *of … of*). The window is still counted in content words.
* **Calculation**: a **run** is a chain of words sharing the sound, each within **window** content words of the one before (default 3;
  any whole number, no upper limit), counted when it has two or more words. A run never crosses the **boundary** you choose: a
  sentence end (default), a paragraph end, or nothing; and never text left out of the sample (in a character's speech, the narration
  between two quotes). A word that repeats one already in a sound run (the same word as the repetition setting says) doesn't count again
  there: it is counted as a repetition instead, since repetition isn't sound patterning. In consonance neither does a word with the same
  last vowel as one already in the run. Each kind gives **runs per 1,000 words**,
  the **share of words in a run** (of those that could be in one: content words with known phonemes, or with letters for alliteration
  by first letter; for repetition the content words, or all words), and the **mean run length** in words.
* **Read it as**: with the default window, alliteration and assonance are common by chance alone (in the books above, about 40
  alliteration and 60 assonance runs per 1,000 words, a fifth to a third of content words); rhyme is rare (1–2 per 1,000). The
  figures mean most as comparisons between parts of the same corpus, under the same settings. A wider window finds more runs and
  longer ones.
* **Assumes**: the dictionary's (American) sounds; that a sound shared by chance and one placed by the writer look the same.
* **Code**: `core/prosody.py: _keys, _onset, _Runs`.

### 17.6 Sound profile

* **Says**: which sounds a text is made of: hissing, hard, nasal, liquid, long or short vowels.
* **Calculation**: every phoneme of the words with known phonemes, per 1,000 words, and classes of them: plosives (P B T D K G),
  fricatives (F V TH DH S Z SH ZH HH), sibilants (S Z SH ZH CH JH), nasals (M N NG), liquids (L R), glides (W Y), and, counting only
  stressed vowels (most unstressed ones are the same neutral vowel), long vowels and diphthongs (IY EY AA AO OW UW AY AW OY ER) and
  short vowels (IH EH AE AH UH). A sound can be in two classes (S is a fricative and a sibilant).
* **Coverage**: beside the figures, the share of words whose pronunciation was guessed (17.1): those count in rhythm and cadences but
  not in runs or the profile.
* **Code**: `core/prosody.py: _profile, phoneme_rates, CLASSES`.

### 17.7 Where the figures appear

* **Sound and rhythm** (its own tab): the same figures for a part of the text (everything, narration, dialogue, or someone's speech:
  each sentence keeps only its words in that part), per book or per chapter or slice; every cadence pattern with its share of phrase
  and sentence ends; the runs of each kind by what they share; and the **scansion** of a chapter or slice (its first 3,000 words):
  each word's stresses, the cadences, the runs of one kind, and the repetitions.
* **Read** (the text view), with the layer *Sound and rhythm*: every word with its stresses above it, the runs of the kind chosen
  coloured by what they share, repetitions outlined, and the last word of each cursus cadence named; counted chapter by chapter (or
  slice by slice) as they load, so a run never crosses from one into the next there.
* **Statistics** (15.2): the layer *Sound and rhythm* is any figure, or one phoneme per 1,000 words, of each case's sample. The units
  are the sample's (15.1): sentences of a text piece, a participant's quotes, their narration paragraph by paragraph. All sound
  variables of a table share one count of the text per setting.
* **Over the book** (16), with *Sound of their speech* on: the target's quotes in each slice (a quote in the slice of its first word,
  measured over its whole span, punctuation and all), as a table under the overview and as the curve's *Sound of speech* figures. A
  slice where the target says nothing has none. With the books combined each figure is the mean of the books' own (every book
  weighing the same, as in 16.8), and words spoken are added up. Speech in a slice is short, so read the figures with the words spoken.
* **Code**: `core/prosody.py: table, span_tally`; `core/soundtab.py`; `core/layers.py: sound`; `core/overbook.py: _sound`.

---

## 18. Word choice

Which kinds of word a text leans on: a heavy use of adjectives or of verbs of action, a nominal or a verbal style. The figures are counted
over a **sample's words** (18.1) and added up before they are divided, so every word weighs the same whichever sentence or quote it is in.
One definition serves every page that shows them (18.5), so the same text gives the same figure on the Style page, on Dialogue and in
Statistics.

### 18.1 What is counted

* **Says**: for a stretch of text (a book, a chapter, a slice, a speaker's quotes, a participant's sample) how many of its words are of
  each part of speech, and how many of its nouns and verbs are of each kind.
* **Data**: BookNLP's part-of-speech tags (`.tokens`) and supersenses (`.supersense`, WordNet's lexical categories, `verb.motion`,
  `noun.person`…), as BookNLP gives them: neither is corrected here, so a mis-tagged word is a mis-counted one.
* **Calculation**: a **tally** counts the sample's words, how many have each part of speech, and the supersense spans of nouns and
  verbs. A span (consecutive tokens with the same supersense) is counted once, where it starts: a span that starts before the sample's
  edge is not counted for it, as in Statistics' supersense variable (15.2). Tallies are added over books, quotes and cases before any
  figure is taken. A *word* is as in section 0: not punctuation, not a quotation mark.
* **Assumes**: a sample large enough for a share to mean something. A speaker with 200 words has about 10 adjectives, so a difference of
  two adjectives moves the share by 1 point; read the words next to the figures.
* **Code**: `core/wordchoice.py: tally, add, value, figures`.

### 18.2 Parts of speech

* **Says**: the share (%) of the sample's words that are each part of speech: nouns, proper nouns, verbs, adjectives, adverbs, pronouns,
  prepositions, determiners, coordinating and subordinating conjunctions and auxiliaries (BookNLP's NOUN, PROPN, VERB, ADJ, ADV, PRON,
  ADP, DET, CCONJ, SCONJ, AUX).
* **Read it as**: a profile of how the text is built. The same shares as the "Parts of speech" table of the Style page (8.3).
* **Calculation**: `100 × words with the part of speech ÷ words`.

### 18.3 Ratios

* **Says**: how many modifiers a text has for what they modify: **adjectives per verb**, **adverbs per verb**, **nouns per verb** (a
  nominal against a verbal style) and **modifiers per head**, (adjectives + adverbs) ÷ (nouns + verbs).
* **Read it as**: above 1, more adjectives than verbs (more description than action), and so on. Ratios are steadier than shares when
  texts differ in how many function words they use, but they say nothing about *which* adjectives: a stock "old" and a vivid "gaunt"
  count alike (BookNLP has no supersenses for adjectives or adverbs, so there is nothing finer to count).
* **Calculation**: counts of words by part of speech: *verbs* are the tokens tagged VERB, so auxiliaries (*was, had, would*) are not
  verbs here; *nouns* are tagged NOUN, so names are not nouns. No value where the divisor is 0 (a sample with no verb).
* **Assumes**: the tagger's verb and adjective decisions (a participle can be either).

### 18.4 Kinds of noun and verb (supersenses)

* **Says**: which kinds of thing and action a text names: nouns of person, artifact, location, time…; verbs of motion, contact,
  cognition, communication…
* **Calculation**, three ways to read the same spans:
  * **per 1,000 words** (`ss:verb.motion`): `1000 × spans of the category ÷ words`; the rate of Statistics' supersense variable.
  * **share of the verbs (or nouns)** (`verb:motion`, `noun:person`): `100 × spans of the category ÷ all verb (noun) spans`. This takes
    out how many verbs the sample has, so it shows the *choice* of verb rather than how verbal the text is. The base is the verbs
    BookNLP gives a supersense (every kind of verb counts, but a verb without a span is not in it), which is not the VERB tokens of
    18.3, so the two counts of verbs differ a little.
  * **dynamic and static verbs** (`verbs:dynamic`, `verbs:static`): the share of verb spans in a group. *Dynamic*: motion, contact, change,
    body, creation, competition, consumption, weather (verbs of something physical happening). *Static*: stative, cognition, perception,
    emotion, possession, social, communication (states, minds, senses, relations and talk). Every verb category is in exactly one group,
    so the two add up to 100.
* **Read it as**: the groups are an interpretive choice, fixed here, not a finding of linguistics: someone who counts communication
  verbs as action would draw the line elsewhere (the single categories are always available, so any other grouping can be made from them,
  in Statistics with one variable per category). In a speaker's own speech communication verbs are mostly the speaker saying things
  about saying things; in narration they mostly introduce quotes.
* **Assumes**: BookNLP's supersense tagger, which is a model's guess: a verb's category is the category of that use of the word.

### 18.5 Where the figures appear

* **Style → Style**: a table below the parts of speech, per book or per chapter or slice, showing the key figures or one section
  (parts of speech, ratios, dynamic and static verbs, verbs by category, nouns by category, verb and noun supersenses per 1,000 words);
  the chart draws any of them (per book as bars, per chapter or slice as a line, for example the course of adjectives per verb). A
  stretch's tally is kept on the book.
* **Dialogue → How they speak**: columns of the Speaking style table, and of the comparison under it, over the words of each speaker's
  quotes (a quote said by two speakers counts for both; "All speakers" counts each quote once, whoever said it); a character's **Speech**
  panel shows adjectives per verb and dynamic verbs against everyone's, and the key figures book by book.
* **Statistics**: the layer *Word choice* is any of the figures, per case, over the case's sample; a case with no words has no value,
  one without verbs has none for the figures that need a verb. A table of such variables tallies each case's sample once.
* **Code**: `core/wordchoice.py: span_tally, table` (Style), `core/dialogue.py: word_choice`, `core/layers.py: word_choice`.
