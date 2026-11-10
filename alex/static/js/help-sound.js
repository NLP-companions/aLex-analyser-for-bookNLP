"use strict";
/* ---------- help: Sound and rhythm ---------- */
/* The help of the Sound and rhythm page (see help.js): one section per sub-tab, its id the sub-tab's name in the address (#/sound/runs opens
   the help at "runs"), then the run kinds and the run settings (the bar above Figures, Runs and Scansion, and the Settings page). The figures themselves are explained in the
   Statistics help's "sound" section and MEASURES.md section 17. */

addHelp("sound", "Sound and rhythm", [
  { id: "start", title: "How the page works", text: [
    "The rhythm and sound patterning of prose, from the CMU pronouncing dictionary: which syllables are stressed, how phrases end (cadences), and nearby words that share a sound (runs). Text chooses everything, narration, dialogue or someone's speech; Figures and Scansion are also cut into chapters or slices as set under Measure over."],
    text2: "Needs the pronunciation dictionary (Settings → Sound and rhythm says how to install it)." },

  { id: "figures", title: "Figures", text: ["Every figure per book (One row per: Book) or per chapter or slice, with a chart of the one you pick (Chart)."],
    items: [["rhythm", "Stressed syllables, syllables per word and unit, clashes, lapses, binary and ternary gaps, nPVI", "How much is stressed and how the stresses are spaced: crowded (clashes), with long unstressed stretches (lapses), alternating (binary), in threes (ternary), evenly or not (nPVI, 0 is even)."],
      ["cadence", "Cadence … (% of phrase or sentence ends)", "How phrases end: the four cursus forms (planus / x x / x, tardus / x x / x x, velox / x x x x / x, trispondaicus / x x x / x) and all four together."],
      ["runs", "… runs per 1,000 words, words in a run (%), mean run length", "For each run kind below."],
      ["profile", "Plosives, fricatives, sibilants… per 1,000 words", "The sound profile: which kinds of sound the text is made of."],
      ["guessed", "Guessed pronunciations (% of words)", "Words not in the dictionary, whose stress was guessed: correct them under Pronunciation."]],
    more: "MEASURES.md 17.3–17.6" },

  { id: "cadences", title: "Cadences", text: [
    "Every pattern found at phrase ends (/ stressed, x unstressed, from the last-but-one stress to the pause), with the cursus forms named, as counts and shares. Click a row for its phrases; Examples: sentence ends only opens only the phrases that end a sentence."],
    more: "MEASURES.md 17.4" },

  { id: "runs", title: "Runs", text: ["Pick a kind: each row is what the runs share (a sound, or a word), with how many runs and words. Click a row for its runs, longest first; repetitions inside sound runs are outlined."],
    items: [["alliteration", "Alliteration", "The same first consonant of the stressed syllable (or of the word, or its first letter, as set in Settings)."],
      ["assonance", "Assonance", "The same stressed vowel."], ["consonance", "Consonance", "The same consonants after a different last vowel."],
      ["rhyme", "Rhyme", "The stressed vowel and everything after it."], ["repetition", "Repetition", "The same word again (lemma, form, or any word, as set in Settings)."]],
    text2: "A run is a chain of content words, each within the window (3 by default) of the one before, not crossing the boundary (a sentence end by default).",
    more: "MEASURES.md 17.5" },

  { id: "scansion", title: "Scansion", text: [
    "One chapter or slice word by word, each word with its stresses above it. Book and Chapter/Slice choose the text; Colour the runs of picks the kind of run to colour (by what they share); repetitions are outlined; cursus cadences are underlined and named (Every cadence underlines all of them); guessed stresses are in the warning colour; words outside the chosen text are faded."] },

  { id: "words", title: "Pronunciation", items: [
    ["correct", "Correct a word", "Look up a word, then type its stress (1 or / stressed, 0 or x unstressed, 2 secondary) or its sounds in ARPAbet, and Save. Corrections count everywhere and belong to this workspace."],
    ["guessed", "Guessed words", "Words the dictionary doesn't know, most frequent first: click one to fill the form."],
    ["yours", "Your corrections", "What you have corrected; Remove brings back the dictionary's or the guess."]],
    more: "MEASURES.md 17.1" },

  { id: "settings", title: "Settings for runs", text: [
    "In the bar above Figures, Runs and Scansion (and on the Settings page, Sound and rhythm): the Run window (how many content words apart words may be in a run), where runs stop (a sentence end, a paragraph end or nowhere), what alliteration compares (the stressed syllable, the first sound or the first letter) and what counts as a repetition (the same lemma, the same form, or the same lemma among all words).",
    "A change is saved for the workspace and the page is counted again at once. The same settings apply here, in Statistics (run the table again), on the Style tab, in the Read view and in Over the book."] },
]);
