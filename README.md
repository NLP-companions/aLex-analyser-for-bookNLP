# aLex — BookNLP analyser

aLex lets you explore books that [BookNLP](https://github.com/booknlp/booknlp) has processed, in your browser: who and what is in them (people, places, organisations…), how they are referred to, what they do, who they appear with and speak to, what is distinctive about them, and how they are linked. It runs on your own computer; nothing is uploaded anywhere.

- **Entities:** a profile for every character, place and organisation, linked across books, grouped, tagged and compared.
- **Dialogue:** who speaks, how quotes are introduced, speaking style (with word choice: how many adjectives, adverbs, dynamic verbs a character uses), conversations and estimated addressees.
- **Corpus tools:** concordance (KWIC), word lists, n-grams, collocates and keywords, with pattern queries over BookNLP's layers.
- **Narrative:** arcs, style measures, word choice (parts of speech, adjectives per verb, dynamic against static verbs), sound and rhythm (stress, cadences, alliteration and the like; needs the optional pronunciation dictionary), stylometry, sentiment, your own word lexicons (emotions and more), narrators, and a chapter editor.
- **Topics:** topic models (NMF or LDA) with comparison tools.
- **Sound and rhythm:** prose rhythm and sound patterning (needs the optional pronunciation dictionary): stress and its spacing, the cadences of phrase and sentence ends (the cursus), runs of alliteration, assonance, consonance, rhyme and repetition with their sentences, and the scansion of a passage word by word, for the whole text, narration, dialogue or one character's speech.
- **Over the book:** how an entity, group, tag or gender changes slice by slice through one book: how often it appears, and which words it acts, is described or possessed with, as a heat grid with tests of change and of steady rise or fall, also for kinds of action, and beside a second one; two books can be lined up by relative position, and one target followed through all the selected books at once, every book weighing the same (Books combined).
- **Described as:** what an entity, group, type, tag or gender is described and called as, and by whom: by each speaker or narrator, by gender, by tag or by book.
- **Statistics:** correlation tables (Pearson or Spearman) and descriptive statistics of words, phrases, mentions, speech, attributes, the sentence types of speech and word choice, over chapters, slices or books, or over characters as participants (each with their own sample of text); heatmaps and data to download, also as a .zip of files for R.
- **Networks** of who appears with or speaks to whom, exportable to Gephi.
- **Help on every page:** the **?** in the top bar opens a side panel explaining what the page shows and each of its options, at the tab you are on; a small **?** beside dense settings opens it at that section.
- A **text view** of each book with entities, quotes and topics marked, **collections** of books, and separate **workspaces** for separate corpora.

What each figure means and how it is calculated is in [docs/MEASURES.md](docs/MEASURES.md).

## What you need

- **Python 3.10 or newer.**
- **BookNLP output for your books.** aLex does not run BookNLP and does not need it installed; it reads the files BookNLP writes. For each book it needs `<book>.tokens` and `<book>.entities`, and uses `<book>.quotes`, `<book>.supersense` and `<book>.book` when they are there. Put the files of each book in a folder (several books can share one folder, or each book can have its own).

aLex is developed and tested on macOS.

## Install

In a terminal:

```bash
python3 -m venv alex-env
source alex-env/bin/activate        # on Windows: alex-env\Scripts\activate
python -m pip install --upgrade pip
pip install git+https://github.com/NLP-companions/aLex-analyser-for-bookNLP.git
```

That creates a separate Python environment so aLex doesn't disturb anything else, brings its installer (pip) up to date, and installs aLex and what it needs (FastAPI, uvicorn, networkx, vaderSentiment, scikit-learn). To update later, run the `pip install` line again with `--upgrade`.

For the sound and rhythm figures (stress, cadences, alliteration and the like), also install the optional pronunciation dictionary: `pip install "alex-booknlp-analyser[sound] @ git+https://github.com/NLP-companions/aLex-analyser-for-bookNLP.git"`, or `pip install cmudict` into the same environment. It is optional because the `cmudict` package is under the GPL-3.0 licence (the dictionary data itself is BSD); everything else works without it.

Prefer to work from a copy of the code? Clone the repository and run `pip install .` inside it (or `pip install -e .` if you want to change the code).

## Start it

With the environment active, in the folder where you want aLex to keep its files:

```bash
alex --books /path/to/folder/with/booknlp/output
```

It opens <http://127.0.0.1:8766/> in your browser. aLex answers only your own computer: other computers can't reach it, and neither can other web pages you have open (it refuses requests that don't come from its own page). `--books` is remembered, so next time `alex` alone is enough. Or start with plain `alex` and put your BookNLP output in the workspace's **books folder** (`alex-data/books`): the empty Library page has an **Open books folder** button, and **Settings → Folders** shows the books and data folders with Open buttons and lets you add other folders. Stop it with Ctrl+C.

Other options: `--port` (default 8766; if it is taken, aLex says so, and it may already be running there), `--no-browser`, `--workspace NAME` (open a particular workspace), `--data FOLDER` (see below) and `--allow-host NAME` (see the next section). `python -m alex` does the same as `alex`.

### Showing aLex to someone else

To give a supervisor a live link for a demo, put a tunnel in front of aLex, for example Cloudflare's free quick tunnel (`brew install cloudflared`):

1. Run `cloudflared tunnel --url http://localhost:8766`. It prints an address like `https://abc-def.trycloudflare.com`.
2. In another terminal, start aLex with that name allowed: `alex --allow-host abc-def.trycloudflare.com` (pasting the whole `https://…` address works too).
3. Send the link. It works while both are running; press Ctrl+C in both when the demo is over (a quick tunnel's address is never reused).

Without `--allow-host` aLex refuses the tunnel's requests ("aLex only answers requests addressed to 127.0.0.1 or localhost"). With it, **anyone who has the link can see and change this aLex**, so a separate demo workspace (`--workspace`) with a few books is a good idea. The address changes with every quick tunnel, so start aLex again with the new one.

### Where aLex keeps its files

aLex only reads your books. Its own files (your book details, collections, links, tags, corrections, topic models and a cache that makes the next start fast) are kept in a folder called **`alex-data`**, made in the folder you start aLex from. **Start it from the same folder each time** to find your work again, or choose the place once and for all with `--data FOLDER` or the `ALEX_DATA` environment variable. The start-up message tells you which data folder is in use. The whole of your work, with the books, can be saved as one `.zip` under **Library → Export selected books**, and opened as a workspace on another computer. aLex checks a workspace's files whenever it opens them (also one imported from someone else, or made by another version): anything it can't read is left out and listed on the Library page, instead of breaking a page.

## Next steps

- **[User guide](docs/guide.md):** books and collections, workspaces, and every view in detail.
- **[How the numbers are made](docs/MEASURES.md)** and **[technical documentation](docs/DOCUMENTATION.md)** (how it is built, the web API, how to change it).
- **[Design language](docs/DESIGN.md):** the look and behaviour of the interface (tokens, components, decisions), for anyone changing the pages or building a companion tool.

## Companion editor

aLex works with any BookNLP output. A separate companion editor (link to follow) can be used to clean and correct BookNLP's output before analysis; its dated export folders are read directly, and the newest export of each book is used.

## Development

From a clone of the repository:

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
cd tests/js && npm install     # optional: the browser tests, which need Node
cd ../.. && pytest
```

The tests use their own generated books and temporary folders and never touch your data. They include a check that every web route answers input of the wrong kind with a readable message, never a crash. To see how aLex copes with a large library (speed and memory of every analysis), run `python tests/benchmark.py --sources /path/to/your/books`; `tests/make_corpus.py` can cut real BookNLP output into as many books as you like for that.

## Disclaimer

aLex was vibe-coded: it was written with [Claude](https://www.anthropic.com/claude), an AI model by Anthropic, under my direction. It has been tested, both with an automated test suite and by hand on real BookNLP output. However, **no human has reviewed the code in detail.**

The software is provided **as is**, without warranty of any kind, express or implied. You use it **at your own risk**. Check its results before relying on them, especially in research or publications, and keep backups of your data.

## Licence

[MIT](LICENSE)


