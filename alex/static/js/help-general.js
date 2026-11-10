"use strict";
/* ---------- help: everywhere ---------- */
/* The help of the whole app, shown under every page's own help ("Everywhere in aLex"): the top bar, the books in use, the [...] menu,
   long pages, tables and charts, the evidence drawer and what is remembered. See help.js. */

addHelp("general", "aLex", [
  { id: "bar", title: "The top bar", text: [
    "Library (the books and workspaces themselves) sits apart on the left; after it come the areas that analyse the selected books, each grouping the pages that answer one kind of question: Entities (Entities, Compare, Described as, Network), Dialogue, Words (the Corpus tools and Topics), Style (Style, Stylometry, Sound and rhythm), Over time (Over the book, Arcs, Sentiment, Lexicons), Statistics and Read. An area's pages are the tabs at the top of the page; clicking an area opens the page you last used in it. Pages used now and then (Entity Links, Narrators) and Settings are in the [...] menu. On a narrow window the areas scroll sideways."],
    items: [["help", "?", "This help, for the page you are on."],
      ["books", "Book button", "The small book icon: chooses which books every page analyses. Point at it to see what you are viewing; click it for a search box, filters by collection, series, author, tag or year, and a checkbox per book. Use these books applies the choice. The button is tinted when only some of your books are in use."],
      ["focus", "Focus: …", "Only with “One focus for every page” (Settings → Entities): what every page looks at, set by the last entity, group, tag, gender or book you chose as a page's subject or whose page you opened. × clears it."],
      ["back", "← Back to …", "Appears after you click a book's name in a table or chart that lists several: that narrows the view to the one book, and this button returns to what you saw before."]] },

  { id: "menu", title: "The [...] menu", items: [
    ["links", "Entity Links", "Treat the same person or place in different books as one entity."],
    ["narrators", "Narrators", "Choose and link the narrators of the books."],
    ["workspace", "Workspace", "The separate library you are working in; its submenu switches to another (the page reloads) or leads to Manage workspaces…"],
    ["theme", "Theme", "Auto (follows your system), Light or Dark."],
    ["plural", "Plural groups", "Whether what plural groups (“Holmes and Watson”, “they”) say, do and are called counts for each of their members too, on every page. The same switch is on the Settings page."],
    ["settings", "Settings", "Minimum mentions, how word frequencies are counted, the sound settings, folders and how the pages look."]] },

  { id: "long", title: "Long pages", items: [
    ["toc", "Side menu", "A page with three or more sections gets a sticky menu of them that highlights the one you are reading, with Collapse all and Expand all under it. It is always at the right. The » beside On this page folds it to a thin strip so the page can use the whole window; « opens it again (remembered per page). Hidden on narrow windows."],
    ["fold", "Collapsing", "Click the arrow beside a section heading, or the heading itself, to fold it away. Your choices are remembered by page and heading."]] },

  { id: "tables", title: "Tables and charts", items: [
    ["sort", "Sorting", "Click a column header to sort by it; click again to reverse. Point at a header for what it counts."],
    ["columns", "Columns: n of m", "On a table of seven columns or more: choose which columns to show (grouped where a table has groups; Show all, or Default for the set it opens with). A column of your corrections or of a warning (Set by paragraph, Guessed pronunciations) always shows. Remembered per table; the CSV always has every column."],
    ["rows", "Show all", "Long tables show their first rows; Show all shows the rest."],
    ["csv", "CSV", "The small CSV link under a table downloads it as a spreadsheet file, sorted as shown, every row included."],
    ["scroll", "Scrolling results", "Tables, concordance lines and quote lists are at most one screen tall: scroll over one and it moves first; at its top or bottom the page moves again."],
    ["rel", "≈ (read with care)", "A small ≈ after a figure or heading marks one to read with care: a figure from a small sample (MATTR under 100 words, a statistic from fewer than 30 cases), an estimate (addressees, which BookNLP doesn't record), a topic that came back in fewer than 60% of re-runs, or sound figures of a text with more than 10% of its pronunciations guessed. Point at it for why."],
    ["charts", "Charts", "Point at a line or bar for its figures; the small SVG · PNG links under most charts download them."],
    ["basedon", "Based on: …", "A small line beside some figures that names the settings and corrections they depend on, such as the minimum mentions, plural groups or how a book is cut. Tinted words are set by you: a setting changed from its default, or one of your corrections (links, addressees you set). Click one to go where it is changed."]] },

  { id: "keyness", title: "What's distinctive: comparing with a reference", text: [
    "Several pages (an entity's What's distinctive, speech verbs, a speaker's vocabulary, Compare, Keywords) take two texts, a target (say, Holmes's actions) and a reference (everyone else's actions), and look for the words the target uses markedly more than the reference. They share the controls below, and a change on one page applies to all.",
    "Every word is judged by its share of each text, not its raw count, so a long reference does not swamp a short target. Two different questions can then be asked of each word, and the measures answer one or the other:",
    "1. Is the difference real? Could it be chance, the kind of wobble any two texts show? Log-likelihood and chi-squared answer this: they measure the evidence. They grow with the amount of text, so a frequent word with a small difference can score high.",
    "2. How big is the difference? Twice as common, or ten times? Log ratio, %DIFF and the odds ratio answer this: they measure the size of the effect, however much text it rests on, so a rare word seen three times can score very high.",
    "A good keyword has both: enough evidence and a sizeable difference. That is why the table always shows G² (evidence) and Log ratio (size) beside whatever you rank by."],
    items: [["cols", "Target, %, Reference, %", "The word's count in each text, and its share of all the words (or items) of that text. Comparing the two shares is the heart of it."],
      ["sign", "+ and −", "G² and χ² carry a sign: + when the word is relatively more frequent in the target, − when less. Log ratio is positive or negative the same way."],
      ["p", "p", "How likely a difference at least this big would be if the two texts really used the word equally: the smaller, the less likely it is chance. Treat it as a ranking aid, since words in a text are not independent draws."],
      ["typical", "More typical of", "On Compare, which side the word leans to."],
      ["sigcol", "Significant", "Whether p passes the significance level (after Bonferroni, if ticked)."]],
    more: "MEASURES.md 1.9, 3" },

  { id: "keyness-measures", title: "The measures, one by one", items: [
    ["ll", "Log-likelihood (G²)", "Shows how surprising the difference is. Answers: is this word really used more by the target, or could it be chance? 0 means no difference; about 3.8 is p = .05, 6.6 is p = .01, 10.8 is p = .001; above that, the bigger the surer. The standard keyness measure, and reliable with small counts. Ranks by evidence: frequent words rise to the top."],
    ["chi2", "Chi-squared", "Shows the same as G², by Pearson's older test. Answers the same question. Read it like G²; with large counts the two agree, with small counts G² is the safer one."],
    ["lr", "Log ratio", "Shows how many times more frequent the word is in the target, on a doubling scale. Answers: how big is the difference? 0 means equal, 1 twice as frequent, 2 four times, 3 eight times; −1 half as frequent. Easy to compare across pages and corpora. Ranks by size: rare words can top it on little evidence."],
    ["pdiff", "%DIFF", "Shows the same as log ratio, as a percentage. Answers: by what percentage is the word more frequent in the target? 0% means equal, 100% twice as frequent, 300% four times, −50% half as frequent."],
    ["or", "Odds ratio", "Shows how much better the odds are of meeting the word in the target than in the reference, with a 95% range in brackets. Answers the size question, with a sense of how sure the size is. 1 means equal, 2 about twice, 0.5 about half; a wide range (2–40) means the size is uncertain."],
    ["measure", "Rank by", "Chooses which of these orders the list. G² (the default) or χ² for “which differences are surest”; log ratio, %DIFF or odds ratio for “which differences are biggest”."]],
    text2: "Example, with made-up numbers: a target of 100,000 words against a reference of 400,000. A word 50 times against 50 (0.05% against 0.0125%): log ratio 2 (four times as frequent), %DIFF 300%, odds ratio 4.0, G² 44.6: big and sure. A word 3 times against 0: log ratio 4.6, %DIFF 2,300%, odds ratio 28 but ranging from 1.4 to 542, G² only 9.7: big but resting on three uses. A word 2,000 times against 6,000 (2% against 1.5%): log ratio 0.4, %DIFF 33%, G² 118: very sure, but only a third more frequent. Ranking by G² puts the third first, by log ratio the second; the first is the kind of keyword you are usually after.",
    more: "MEASURES.md 3" },

  { id: "keyness-settings", title: "The comparison settings", items: [
    ["test", "Significance test", "Which test gives the p-value: Log-likelihood (default) or Chi-squared."],
    ["min_freq", "Minimum frequency", "Words rarer than this in the target are not tested (on Compare: on either side). Rare words make unreliable keywords: raise it to keep the size measures from being topped by words seen two or three times."],
    ["alpha", "Significance level", "How small p must be to count as significant: .05, .01, .001 or .0001. Stricter levels keep fewer, surer words."],
    ["bonferroni", "Bonferroni correction", "Divides the level by the number of words tested. Testing hundreds of words, about one in twenty passes .05 by chance alone; this keeps such false alarms rare."],
    ["show_all", "Show non-significant", "Lists the untested and non-significant words too, greyed, so you can see what just missed."]] },

  { id: "evidence", title: "The sentences behind a number", text: [
    "Click a row or a count and the side drawer opens with the sentences behind it, each with its book and place and an Open in the text link, and a CSV link to download them. It closes with × or Escape, and on every change of page."] },

  { id: "remembered", title: "What is remembered", text: [
    "Your choices on a page (a selected book, a view, a setting) stay after a reload and when other things change, until you change them. They are kept for each workspace apart: switching workspace brings back what you chose there."] },
]);
