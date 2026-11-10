# aLex design language

The visual and interaction design of aLex (the analyser's browser interface), written down so that new features follow it and companion projects can adopt it.

> **Based on Luna design language, version of 2026-10-09** (`editor/docs/DESIGN.md`, the companion editor). aLex follows that language where a pattern exists there, and records every place where it does not (§2, §13).
> Last verified against the code: 2026-10-09 (`alex/static/app.css`, `index.html`, `js/*.js`, including the uncommitted `#viewBack` rule of that day).

## 0. How to read and use this document

**For people:** read §1 (principles) and §12 (decision log) for the *why*, then look up the component or pattern you need. §14 is the checklist for designing a new feature; §15 is for porting to another project.

**For tools and agents:** every normative statement has a stable ID so it can be cited in a prompt, a review or a commit ("violates AL-COLOR-03"). Wording follows RFC 2119: **MUST** = breaking it is a bug, **SHOULD** = break it only with a reason you can state, **MAY** = optional.

| ID family | Meaning | Defined in |
|---|---|---|
| `AL-<AREA>-<nn>` | A rule of **aLex**. | this file (bold at its definition) |
| `DL-<AREA>-<nn>` | A rule of the **Luna** editor language that aLex inherits, or replaces with an `AL-` rule. | the editor's file; its fate here is in the §2 table |
| `AD-<nn>` | A dated design decision. | §12 |
| `AO-<nn>` | A known deviation or open point. | §13 |

**How to resolve a rule** (in this order): 1. an `AL-` rule that covers the case; 2. the §2 row for the `DL-` rule: *adopted* means apply the editor's text unchanged, *adapted* and *deviates* mean the `AL-` rule named in that row wins, *n/a* means the situation does not exist in aLex; 3. the principles in §1. If two sources disagree, the code is what users see: fix whichever is wrong and record it in §13 (never leave a disagreement unrecorded).

**Machine-readable parts.** The design tokens, the contrast ratios and the layout numbers are one fenced `json tokens` block (§4.1). `tests/test_design.py` compares it with `app.css` and `core.js` and checks the contrast numbers, so that block cannot silently go stale. Everything else is prose and tables; rule IDs are checked for uniqueness and for dangling references.

**Status tags** used throughout:

| Tag | Meaning |
|---|---|
| `[impl]` | Implemented and verified against the code at the date above. |
| `[rule]` | A rule for new work; existing code mostly follows it, exceptions are in §13. |
| `[open]` | Not decided, or not yet consistent; see §13. |
| `[portable]` | Carries over to a companion project unchanged. |
| `[alex]` | Specific to the corpus-analysis domain (entities, books, charts); adapt rather than copy. |

## 1. Principles

Inferred from what was built and from the user's decisions (§12); they are the tie-breakers when a rule is silent.

- **AL-PRIN-01 — Numbers and sentences are the subject; chrome is quiet.** `[portable]` What the corpus says (a table, a chart, the sentences behind a count) is the largest and most contrasted thing on the page. Everything around it is small, grey (`--muted`) and bordered by 1 px lines.
- **AL-PRIN-02 — Colour is categorical, never decorative.** `[alex]` A hue means *which type* (PER, LOC…) or *which series* (book, topic, side of a comparison). Everything else is neutral plus one accent (AL-COLOR-02).
- **AL-PRIN-03 — Every number can be traced and explained.** `[portable]` A count opens the sentences behind it (the evidence drawer); a method has a collapsed "How this is calculated" note; a column header says in its tooltip what it counts. Nothing is a black box.
- **AL-PRIN-04 — A control owns its output.** `[portable]` A control never changes what another control shows. A setting that applies to many panels is drawn **once**, where it visibly governs them, and says so. (A user rule, after two reports; see AD-12.)
- **AL-PRIN-05 — One scope at a time.** `[alex]` The selected books (and the plural-group mode) are the scope of every analysis page; it is global, drawn in the top bar, and each request carries it. The workspace is the unit of remembered state (AL-INT-07).
- **AL-PRIN-06 — A large corpus stays readable.** `[portable]` Results boxes are at most one screen tall and scroll inside themselves; long lists say how many remain; charts degrade gracefully (names become tooltips beyond 12 lines, labels are thinned). Tested over forty and sixty generated books.
- **AL-PRIN-07 — One product with the editor.** `[portable]` Where the editor has a pattern (top bar, `[...]` menu, Settings page, cards, popover) aLex reuses its look and rules instead of inventing a variant. A divergence is a recorded decision, not an accident.
- **AL-PRIN-08 — Plain, calm and local.** `[portable]` System fonts plus one serif, one accent, no gradients, no illustrations, no decorative motion. aLex listens on 127.0.0.1 only; copy says what a control will **not** change ("Its files stay where they are.").

The next six come from the simplification round of 2026-10-26 (AD-27): the interface had grown to sixteen places, with features in two or three of them, and felt overwhelming. They serve a researcher at work and a first-time user with **one** design (no simple/expert mode). They are `[rule]`: the pages are brought in line step by step, and §13 lists what is still to do.

- **AL-PRIN-09 — Organise by question, not by method.** `[portable]` The top bar's areas and their sub-tabs are named after what the user wants to find out (who, what they say, how it is written, how it changes), not after the technique (corpus, stylometry, χ²). Method names live inside the pages. The areas are in §8.3.
- **AL-PRIN-10 — Calm hierarchy.** `[portable]` The result (a table, a chart, the sentences) is the loudest thing on a page. Its controls are grouped in one quiet row above it, and secondary options are smaller and muted. Everything stays visible by default; folding a part away is decided page by page, where it clearly helps, not as a general rule (the Corpus search settings, for example, stay in view).
- **AL-PRIN-11 — Hide controls, never assumptions.** `[portable]` Every setting that changes a number is either visible beside the result or named in a short summary line next to it ("10 slices per book · plural groups off · at least 2 mentions"). A setting that is not at its default is highlighted there, and the line links to where it is changed. Making a page calmer never makes it less clear what was counted.
- **AL-PRIN-12 — Focus: per page or following you, the user's choice.** `[alex]` `[impl]` The subject of a page (an entity, a group, a tag, a gender or a book) is remembered **per page** by default, as before. Under **Settings → Entities** the user can instead choose **one focus for every page** (`focus.js`, kept in the browser per workspace, AL-INT-07): choosing a page's subject, or opening a profile, makes it the focus, and every page's **subject** chooser then opens on it (Over the book's target in its three views, side A of Two books aligned, Described as, Compare's first side, Speech verbs' speaker, How they speak's target, In-Depth Who Speaks' scope). Filters and scopes (Conversations, Quotes, "Speech of…"), references ("Compared with", a second side, Described-as columns) and Statistics never follow, so nothing narrows itself unasked. A chooser that can't take the focus's kind shows its own choice and leaves the focus untouched, silently. A page's own choice set by a link ("Described by whom →", "Compare two books in detail") leads and becomes the focus; a book limit on the same target is kept. The focus is drawn once, as a chip in the top bar (`#focusChip`, × clears it), and each following chooser says "follows the focus" (AL-PRIN-04). Each page keeps what it last showed as its own, so switching back to "each page its own" leaves every page where it was (AD-33).
- **AL-PRIN-13 — One home per feature.** `[portable]` Each analysis has one full page. Elsewhere it appears as a small preview with a link to that page (opening it with the same target and book), never as a second full copy with settings of its own.
- **AL-PRIN-14 — Reliability next to the number.** `[portable]` `[impl]` (AL-FB-05, AD-36) A figure from a small sample, or one that is estimated (addressees, a guessed pronunciation, a topic of low stability), carries a small marker where it is shown, and its tooltip says why. Calmer pages never drop these warnings.

## 2. Relation to the editor's design language

### 2.1 What each editor rule became in aLex `[impl]`

Statuses: **adopted** (apply the editor's text as written; where the table names an `AL-` rule it adds the aLex detail), **adapted** (same intent, aLex's own rule wins), **deviates** (aLex does something different on purpose or by history; the `AL-`/`AO-` entry says what), **n/a** (the situation does not exist in aLex). One row per editor rule (75 rules).

| Editor rule | Status | aLex |
|---|---|---|
| DL-PRIN-01 | adapted | AL-PRIN-01: numbers and sentences instead of the book text. |
| DL-PRIN-02 | adapted | AL-COLOR-05: colour per entity *type*, not per entity. |
| DL-PRIN-03 | adapted | Saved at once (AL-INT-01), but there is **no undo or history**; destructive actions are confirmed (AL-INT-03). No save badge; a toast says "Saved.". |
| DL-PRIN-04 | n/a | aLex is not a repeated-entry tool; keyboard rules are AL-INT-05. |
| DL-PRIN-05 | adopted | New pages reuse one of the layouts in §8.2. |
| DL-PRIN-06 | adopted | AL-PRIN-03, AL-FB-03. |
| DL-PRIN-07 | adopted | AL-PRIN-08; base size differs (AL-TYPE-01). |
| DL-PRIN-08 | adopted | AL-PRIN-08. |
| DL-ARCH-01 | adapted | AL-ARCH-02: markup is built with `h()` (text nodes only), not template literals plus `esc()`. |
| DL-ARCH-02 | adapted | AL-ARCH-03: one `app.css` for **every** page (there is no second stylesheet). |
| DL-ARCH-03 | deviates | AL-ARCH-04: listeners are attached by `h()` props; delegation only for cross-cutting UI. |
| DL-ARCH-04 | adopted | A `/** … */` comment above every function (a one-line arrow function may carry it at the end of its line); `tests/test_docs.py` enforces it, and a docstring on every Python function. |
| DL-ARCH-05 | adapted | AL-INT-07: prefix `analyser.`, per-workspace suffix, theme global. |
| DL-ARCH-06 | adapted | AL-ARCH-05: one page, hash router, every view inside the same persistent shell. |
| DL-TOK-01 | adopted | AL-TOK-01; literals still present are in AO-05. |
| DL-TOK-02 | adopted | AL-TOK-02. |
| DL-TOK-03 | adapted | AL-TOK-03: inline script before the stylesheet, key `analyser.theme`, control in `[...]` → Theme and Settings → Appearance. |
| DL-TOK-04 | adopted | `color-scheme` is set in each theme block. |
| DL-COLOR-01 | adapted | Same layering with aLex names: `--bg` → `--panel` → `--panel-2` (§5.1). |
| DL-COLOR-02 | adopted | 1 px `--rule` around, `--rule-soft` between; 3 px inset shadow marks identity or state on a left edge. |
| DL-COLOR-03 | adopted | AL-COLOR-03. |
| DL-COLOR-04 | adopted | AL-COLOR-02 (one accent). |
| DL-COLOR-05 | adopted | White on solid type colours; contrast in §4.1 (ORG is short of AA, AO-03). |
| DL-HUE-01 | n/a | No per-entity hue (see DL-PRIN-02). |
| DL-HUE-02 | n/a | aLex has no dashed-suggestion idiom; suggestions are rows with actions (AL-INT-04). |
| DL-HUE-03 | adapted | AL-COLOR-05: fixed colour per kind (type), through JS constant `TC` and CSS variables. |
| DL-HUE-04 | adapted | AL-COLOR-05: the swatch is a 4 px bar (`.sw`), a 3 px inset bar (`.gtag`), a 10 px legend square, or the `.t` chip. |
| DL-TYPE-01 | deviates | AL-TYPE-01: base is **14 px**, not 13 px. |
| DL-TYPE-02 | adapted | AL-TYPE-02: aLex's own scale. |
| DL-TYPE-03 | adopted | Section label `.lsec h2`; variants in AO-11. |
| DL-TYPE-04 | adopted | `font-variant-numeric: tabular-nums` on counts, `.num`, `.n`. |
| DL-TYPE-05 | adopted | Weights 400, 500, 600, 700 (profile `h1` 500). |
| DL-TYPE-06 | adopted | Italic is used only for folded entries in the page menu. |
| DL-TYPE-07 | adopted | AL-COPY-04. |
| DL-SPACE-01 | adopted | §7.1. |
| DL-SPACE-02 | adapted | AL-SPACE-02: inputs 4, `.panel` 6, new cards 10. |
| DL-SPACE-03 | adopted | Only floating things have a shadow; `.bookcard.current` uses border plus 1 px ring. |
| DL-SPACE-04 | adapted | AL-SPACE-04: aLex's own role scale. |
| DL-SPACE-05 | deviates | AL-SPACE-05: the **document scrolls** in aLex. |
| DL-LAY-01 | adapted | AL-BAR-01. |
| DL-LAY-02 | adapted | AL-BAR-02 and AL-TAB-02 (sub-views are underline tabs, `.subtabs`, not `.enav` pills). |
| DL-LAY-03 | n/a | No global side panel; page-specific side columns (§8.2). |
| DL-LAY-04 | n/a | No review progress. |
| DL-LAY-05 | adapted | AL-SET-01 and §8.2 pattern C (`.page`). |
| DL-LAY-06 | adopted | AL-LAY-01. |
| DL-LAY-07 | adapted | AL-LAY-02: own breakpoints. |
| DL-BTN-01 | adopted | AL-BTN-05. |
| DL-BTN-02 | n/a | No multi-action quick-pick controls. |
| DL-BTN-03 | adopted | Icon-only controls carry `aria-label` and a `title` or tooltip. |
| DL-INP-01 | adapted | AL-CTRL-04: inline "ask" rows instead of modals. |
| DL-INP-02 | adapted | AL-SET-01: `.fields` with a **150 px** label column. |
| DL-TAB-01 | adopted | `seg()` and toggle buttons carry `aria-pressed`; exceptions in AO-08. |
| DL-CHIP-01 | adapted | AL-COLOR-05 and AL-TAB-03. |
| DL-CHIP-02 | n/a | No group chips. |
| DL-FLOAT-01 | adapted | AL-FB-04: anchored by CSS under the trigger, focus goes to the search field; not clamped to the viewport (AO-14). |
| DL-FLOAT-02 | adapted | AL-FB-01 (toast) and AL-INT-03 (confirm policy differs). |
| DL-KEY-01 | n/a | No global shortcuts. |
| DL-KEY-02 | n/a | No global shortcuts. |
| DL-KEY-03 | n/a | No choice keys. |
| DL-KEY-04 | n/a | No number keys. |
| DL-KEY-05 | adopted | AL-INT-05 (focus ring offset is 2 px). |
| DL-INT-01 | n/a | No history. |
| DL-INT-02 | adopted | AL-INT-01. |
| DL-INT-03 | adapted | A corrected row is marked with a 3 px accent inset (AL-TBL-05). |
| DL-INT-04 | adopted | AL-INT-04. |
| DL-INT-05 | deviates | AL-INT-03: there is no undo, so destructive actions **are** confirmed. |
| DL-INT-06 | adopted | `← Back to …` after a drill-down (AL-BOOK-03), "Show in text" links. |
| DL-INT-07 | n/a | No queue-walking tools. |
| DL-INT-08 | n/a | No one-item-at-a-time queues. In the same spirit, the concordance pages through a kept search with `offset` ("Show more") rather than one capped list. |
| DL-INT-09 | deviates | No `whenIdle`: extras (plural suggestions on the Entities page, the small network on a profile) are asked for with the page and fill in when they come; pickers that would ask per item (the Library's narrator popover) fetch their list only when opened. |
| DL-COPY-01 | adapted | AL-COPY-01 (full stops differ). |
| DL-COPY-02 | adopted | AL-COPY-02. |
| DL-COPY-03 | adapted | AL-COPY-03: aLex's own nouns. |
| DL-COPY-04 | adopted | Tooltips say what the control does; a disabled control says why. |
| DL-COPY-05 | adopted | AL-COPY-06. |
| DL-COPY-06 | adopted | AL-COPY-05. |
| DL-COPY-07 | adopted | `api()` shows the server's message verbatim in a toast. |

### 2.2 Name mapping (editor → aLex) `[impl]`

Needed when moving code or CSS between the projects. Same name in both = the same thing unless a note says otherwise.

| Editor | aLex | Note |
|---|---|---|
| `--surface` | `--panel` | raised surface |
| `--sunk` | `--panel-2` | hover rows, secondary cards; lighter than `--panel` in dark |
| `--line`, `--line2` | `--rule`, `--rule-soft` | |
| `--accent-bg` | `--accent-soft` | |
| `--warn` (attention, orange) and `--danger` (error, red) | `--warn` (brick red) | **one colour for both**; aLex has no `--danger`, `--ok`, `--mono` |
| `--ui`, `--read`, `--mono` | `--sans`, `--serif`, none | mono is a literal stack (AO-05) |
| `--h` (group hue) | `--c` (an element's own colour) | set inline, e.g. `.gtag` |
| `.btn.sm` | `.btn.small` | |
| `.badge` | `.n` (a count inside a chip, tab or row) | |
| `.enav` | `.subtabs` | underline tabs |
| `.tg` | `.chip` (filter pill), `label.inline` (checkbox) | |
| `.chip` (a mention) | `.t` (type chip) | `.chip` in aLex is the filter pill |
| `.sub` (muted summary) | `.sub` (submenu wrapper) | **same name, different thing** (AO-09) |
| `.sugg` (suggestion) | `.sugg` (entity-search dropdown) | **same name, different thing** (AO-09) |
| `.pop` | `.pop` | editor: `position: fixed`, aLex: absolute under its trigger |
| `.toast.on` | `#toast[hidden]` plus `.err` | |
| `.fields` | `.fields` | label column 96 px there, 150 px here |
| `.stoc` | `.stoc` | 190 px there, 170 px here |
| `.menu`, `.seg`, `.btn.ico`, `.bookcard`, `.lsec`, `.menulbl` | same | `.menulbl` is not used in aLex |

### 2.3 What aLex has that the editor does not `[portable]`

Candidates to port back to the editor: results boxes (AL-TBL-02), the collapsed `note()` explanation and one-line `.hint` (AL-FB-03), collapsible panels with a page menu (AL-FOLD-01), per-workspace remembered state (AL-INT-07), the chart conventions (§9.10), composite entity pickers (AL-CTRL-03), the toast with an error style (AL-FB-01), the tooltip `.tip` shown from a sibling selector (AL-BOOK-01).

## 3. Architecture constraints that shape the design `[impl]`

- **AL-ARCH-01 — No framework, no build step.** Scripts listed in `index.html` run in order and share one global scope; the router (`main.js`) loads last. A page is a function `renderX(main, …)` that fills `#main`.
- **AL-ARCH-02 — Markup is built with `h()` only.** `h(tag, props, ...children)` makes elements; strings become text nodes; props starting `on` are listeners; `style` takes an object (keys starting `--` are custom properties); `svg:name` makes SVG. Code MUST NOT use `innerHTML`, `outerHTML` or `insertAdjacentHTML` (a test checks this). Server text with highlights passes through `markup()`, which reads control characters, never HTML.
- **AL-ARCH-03 — One stylesheet, `app.css`, for every page.** Tokens, base elements and every component, under comment banners in page order (the list is at the top of the file). A new component's CSS goes in the section of the page it belongs to; shared components go near the generic controls.
- **AL-ARCH-04 — Listeners are attached where the element is built.** Document-level listeners exist only for cross-cutting behaviour: the `[...]` menu and book panel (`menu.js`), the contents lists and fold arrows (`pagetools.js`, `settings.js`), Escape for the drawer.
- **AL-ARCH-05 — One page, one shell.** The top bar, `#main`, the drawer and the toast live in `index.html` and never reload; the address (`#/<tab>/<sub>/<id>`) says which page fills `#main`. Switching workspace reloads the whole page.
- **AL-ARCH-06 — Pages never overlap.** `render()` serialises renders (a newer request waits for the running one); requests that can be superseded keep a counter so only the newest fills the page.
- **AL-ARCH-07 — Charts are plain SVG built in JS** and cannot use `var()`; they read theme colours with `cssVar()` at draw time (AL-CHART-01).

## 4. Tokens

### 4.1 Machine-readable token set `[impl]`

Source of truth is `app.css` (`:root`, the `prefers-color-scheme: dark` block, and `:root[data-theme="dark"]`) and, for the categorical colours, `core.js` (`TC`, `PALETTE`, `PROP_COL`, `LIGHT_*`). This block is checked against them by `tests/test_design.py`; edit both together. `color` holds the theme-dependent custom properties; `fixed` and `type-color` are the same in both themes. Entries in `contrast` are WCAG 2 ratios of `fg/bg` (a name is a token of that theme, `white`, a `#hex`, or a `type-color` name), rounded to two decimals; ratios under 4.5 for text are listed in §13.

```json tokens
{
  "color": {
    "light": {
      "bg": "#eef1f0", "panel": "#ffffff", "panel-2": "#f5f7f8", "ink": "#1d2a2e", "muted": "#5b686c", "faint": "#8a9699",
      "rule": "#d5dcda", "rule-soft": "#edf0ef", "accent": "#2e4a62", "accent-ink": "#ffffff", "accent-soft": "#e3eaf0", "warn": "#9b3b2f",
      "shadow-sm": "rgba(20, 35, 40, .12)", "shadow-lg": "rgba(20, 35, 40, .18)", "exc": "#c0843a",
      "tint-mention-bg": "#e6ecf6", "tint-other-bg": "#efe6f4", "tint-key-bg": "#fbefd9", "tint-quote-bg": "#eef2f6", "tint-quote-bg-hover": "#e2e9f0",
      "tint-pos-bg": "#dfe8f5", "tint-neg-bg": "#f6e0dc", "tint-hit-bg": "#fffbe8", "tint-mark-bg": "#fff1b8", "tint-topic-bg": "#fdf0c4", "tint-topic-rule": "#d9b84a"
    },
    "dark": {
      "bg": "#14181a", "panel": "#1c2226", "panel-2": "#242b2f", "ink": "#e7ecec", "muted": "#9aa7aa", "faint": "#6d7a7d",
      "rule": "#333d41", "rule-soft": "#2a3236", "accent": "#5f8fb4", "accent-ink": "#0e1a24", "accent-soft": "#23303c", "warn": "#c85a49",
      "shadow-sm": "rgba(0, 0, 0, .45)", "shadow-lg": "rgba(0, 0, 0, .55)", "exc": "#d99a4e",
      "tint-mention-bg": "#223247", "tint-other-bg": "#2c2438", "tint-key-bg": "#3a3220", "tint-quote-bg": "#212a30", "tint-quote-bg-hover": "#283640",
      "tint-pos-bg": "#1f3247", "tint-neg-bg": "#402a22", "tint-hit-bg": "#3a3419", "tint-mark-bg": "#4a3c14", "tint-topic-bg": "#3a3018", "tint-topic-rule": "#8a6c2c"
    }
  },
  "fixed": { "chrome": "#1d2a2e", "on-chrome-muted": "#b8c4c7", "on-solid": "#ffffff", "bar-h": "46px" },
  "type-color": {
    "PER": "#3b5ba5", "LOC": "#3e7c4a", "FAC": "#9a6424", "GPE": "#7b4f9e", "VEH": "#b5473c", "ORG": "#2b8a7e",
    "VAR": "#6d6a75", "NARR": "#8a6a3b", "GENDER": "#a5477a"
  },
  "prop-color": { "PROP": "#2e4a62", "NOM": "#7d9bb3", "PRON": "#c9d6e0" },
  "palette": ["#3b5ba5", "#b5473c", "#3e7c4a", "#9a6424", "#7b4f9e", "#2b8a7e", "#c0843a", "#5a7d9a", "#a0527a", "#6b8e23", "#8c6d62", "#4a4a8a"],
  "font": {
    "sans": "-apple-system, BlinkMacSystemFont, \"Segoe UI\", \"Helvetica Neue\", Arial, sans-serif",
    "serif": "\"Iowan Old Style\", \"Charter\", \"Palatino Linotype\", Palatino, Georgia, serif",
    "mono-literal": "ui-monospace, Menlo, Consolas, monospace",
    "svg": "Helvetica, Arial, sans-serif",
    "base-size": "14px", "base-line-height": "1.45"
  },
  "radius": { "bar": "1px", "mark": "2px", "chip": "3px", "input": "4px", "control": "6px", "panel": "6px", "seg": "7px", "small-card": "8px", "card": "10px", "filter-pill": "14px", "pill": "999px" },
  "z": { "table-head": 1, "read-head": 10, "search-list": 15, "books-menu": 16, "top-bar": 20, "drawer": 25, "popover": 30, "menu": 40, "toast": 40, "tooltip": 41 },
  "breakpoint": [700, 720, 820, 980, 1200],
  "layout": {
    "main-max": "1500px", "page-max": "1040px", "page-with-toc-max": "1260px", "settings-toc": "170px", "entity-list": "300px", "entity-toc": "170px",
    "read-side": "340px", "topic-toc": "190px", "network-side": "300px", "page-toc": "180px", "drawer": "min(620px, 100vw)", "library-nav": "200px",
    "fields-label": "150px", "books-panel": "min(460px, calc(100vw - 32px))", "popover": "280px", "menu-min": "170px"
  },
  "contrast": {
    "light": {
      "ink/panel": 14.76, "ink/bg": 12.98, "muted/panel": 5.77, "muted/bg": 5.07, "faint/panel": 3.04, "faint/bg": 2.68,
      "accent/panel": 9.24, "accent/accent-soft": 7.61, "accent-ink/accent": 9.24, "warn/panel": 6.86, "warn/bg": 6.04, "white/warn": 6.86
    },
    "dark": {
      "ink/panel": 13.48, "ink/bg": 14.98, "muted/panel": 6.49, "muted/bg": 7.22, "faint/panel": 3.62, "faint/bg": 4.02,
      "accent/panel": 4.65, "accent/accent-soft": 3.9, "accent-ink/accent": 5.1, "warn/panel": 3.84, "warn/bg": 4.27, "white/warn": 4.19,
      "PER/panel": 2.47, "LOC/panel": 3.21, "FAC/panel": 3.23, "GPE/panel": 2.64, "VEH/panel": 3.01, "ORG/panel": 3.86, "VAR/panel": 3.04, "NARR/panel": 3.22, "GENDER/panel": 2.9
    },
    "fixed": {
      "white/chrome": 14.76, "#b8c4c7/chrome": 8.26,
      "white/PER": 6.51, "white/LOC": 5.02, "white/FAC": 4.97, "white/GPE": 6.08, "white/VEH": 5.34, "white/ORG": 4.17, "white/VAR": 5.29, "white/NARR": 4.99, "white/GENDER": 5.55
    }
  }
}
```

The dark palette is defined **twice** in `app.css` (under the media query for "Auto", and under `[data-theme="dark"]` for an explicit choice) because CSS cannot share a rule between two conditions; the test checks both copies equal this block. `--chrome` is defined only in `:root`: it is dark in both themes on purpose.

### 4.2 Using tokens

- **AL-TOK-01 — MUST** use the colour variables, never literals, for neutrals, the accent and `--warn`. Literals are allowed only for the `fixed` entries and the categorical colours (§5.3); where they are still scattered, AO-05 lists them.
- **AL-TOK-02 — MUST** work in both themes. A new theme-dependent colour is added as a variable with a light and a dark value in all three places in `app.css` and in §4.1; a new categorical colour is added to `TC`/`PALETTE` and §4.1 and checked against both `--panel` values (AO-04).
- **AL-TOK-03 — Theme** is `auto` (follows the system) / `light` / `dark`. An inline script in `<head>`, **before** the stylesheet link, reads `analyser.theme` and sets `html[data-theme]`, so the page never flashes the wrong theme; `auto` leaves no attribute. The control is the Theme submenu of `[...]` and the segmented control on Settings → Appearance; both call `setTheme()` and re-render the page, because charts read colours at draw time.
- **AL-TOK-04 —** The top bar height is `--bar-h`. Anything that sticks below the bar, or scrolls under it, MUST be placed with `var(--bar-h)`, not with a literal (existing literals: AO-10).

## 5. Colour

### 5.1 Neutrals `[impl]`

| Token | Role |
|---|---|
| `--bg` | Page background; the sticky strip under the top bar in the text view (`.read-head`); the empty part of small bars. |
| `--panel` | Everything raised above `--bg`: top bar, panels, cards, inputs, buttons, menus, popovers, table header, the reading text. |
| `--panel-2` | One step off `--panel`: hover rows and links, secondary cards (`.link-card`, `.person-card`), the drawer, the plural-group box, dashed holding boxes (`.gbox`, `.pickcol`), `.tagchip`. Slightly grey in light, slightly lighter in dark; never a page background. |
| `--ink` | Text. |
| `--muted` | Secondary text, labels, icons, inactive tabs. Meets AA on `--panel`, `--bg` and `--panel-2` in both themes. |
| `--faint` | Third-level text: counts beside a label, paragraph numbers, axis labels, dimmed rows. **Does not meet AA** (AO-01); see AL-COLOR-01. |
| `--rule` | Borders of controls, cards, panels. |
| `--rule-soft` | Hairlines between rows inside a container. |

### 5.2 Semantic colours `[impl]`

| Colour | Means | Used for | Never for |
|---|---|---|---|
| `--accent` (+ `--accent-soft`, `--accent-ink`) | **Current / selected / primary / interactive** | open tab and active segment (accent fill), primary button, links, focus ring, selected row (`--accent-soft`), `.on` toggles, `.current` cards (border plus 1 px ring), user tags, keyword in a concordance line, corrected-row bar | the identity of a type or series |
| `--warn` | **Problem, error or missing** | `.warn` text (a failed request, "folder missing", problems found when loading books, a destructive-action warning), the error toast `.toast.err` | "negative" sentiment (that is `--tint-neg-bg`), decoration |
| `--chrome` | **Always-dark surface with white text** | the toast, tooltips (`.tip`, `.net-tip`), the active filter chip, the quote label `.ql` | anything that must follow the theme |
| `--exc` | **A narrator exception on a paragraph** | the 3 px mark on `.para.exc` | anything else |
| type colours (§5.3) | **Which type** | `.t` chip, list bars, entity underlines, network nodes, chart series by type | state |
| `--tint-*` | **Highlight of a span of text** (below) | marks inside evidence sentences and the text view | UI chrome |

Highlight tints (`.ev mark`, `.read-text mark`): `--tint-mention-bg` a counted mention (`mark.m`, with a 2 px `--PER` underline), `--tint-other-bg` another entity (`mark.o`, `--GPE` underline), `--tint-key-bg` the key word (`mark.k`, bold, `--FAC` underline), `--tint-quote-bg` (+ `-hover`) a quote, `--tint-pos-bg` / `--tint-neg-bg` positive and negative sentiment words (`.rp`, `.rn`), `--tint-hit-bg` a paragraph that matched a search, `--tint-mark-bg` a matched word, `--tint-topic-bg` (+ `--tint-topic-rule`) a topic's word in an evidence sentence.

- **AL-COLOR-01 —** Text that must be read MUST meet 4.5:1 against its background in both themes. `--faint` MAY carry only information that is repeated elsewhere (a count beside its label, a tick, a decorative separator); existing breaches are AO-01 and AO-02.
- **AL-COLOR-02 — One accent.** No second brand colour; extra emphasis uses `--ink`, weight, or an outline. `--chrome` and `--exc` are surfaces/markers, not accents.
- **AL-COLOR-03 — Colour is never the only carrier.** A type is named in text (`PER`; the full name is the tooltip); a series is named in a legend, an end label or a tooltip; a counted entity mark is underlined solid and an uncounted one dotted.
- **AL-COLOR-04 — `--warn` is for problems only.** A neutral "no result" is `.muted`; an empty state is `.empty`.
- **AL-COLOR-05 — Type colours are fixed per type**, one per entity type in `TYPES` order (PER, LOC, FAC, GPE, VEH, ORG, VAR) plus NARR (narrator roles) and GENDER, and the same everywhere: the `.t` chip (11 px/600, white text, radius 3), the 4 px bar `.sw` at the left of an entity row, the 3 px inset bar of `.gtag`, the 2 px underline of an entity mark in the text view, network nodes coloured "by type". The values exist in three places that MUST agree (CSS variables `--PER…--ORG`, CSS literals for VAR/NARR, the JS constant `TC`; the test checks them). Adding a type means: a colour here and in all three places, a `.t.X` rule, the `.L-entities` rules, and a name in `TYPE_NAMES`.
- **AL-COLOR-06 — Series colours are chosen by index**, `PALETTE[i % 12]`: books in a chart, topics (by topic id, `topicColor`), network communities. In a two-sided comparison the target takes one colour and the reference another **on every panel of that page** (Dialogue's compare mode uses `PALETTE[0]` and `PALETTE[1]`; the Compare page still uses two literals, AO-21). A series colour MUST NOT also stand for a type in the same view (the network offers "colour by type" **or** "by community", never both).
- **AL-COLOR-07 — Categorical colours do not change with the theme** and are not re-tuned for dark mode (AO-04). A downloaded chart always uses light-theme colours on white (AL-CHART-04).

### 5.3 Categorical colours `[alex]` `[impl]`

| Name | Meaning | Colour | White text on it |
|---|---|---|---|
| PER | People | `#3b5ba5` | 6.51 |
| LOC | Locations | `#3e7c4a` | 5.02 |
| FAC | Facilities | `#9a6424` | 4.97 |
| GPE | Geo-political | `#7b4f9e` | 6.08 |
| VEH | Vehicles | `#b5473c` | 5.34 |
| ORG | Organisations | `#2b8a7e` | **4.17** |
| VAR | Various (unclassified) | `#6d6a75` | 5.29 |
| NARR | Narrator roles ("Watson, narrating"); not an entity type | `#8a6a3b` | 4.99 |
| GENDER | A gender bucket in the Entities list; not an entity type | `#a5477a` | 5.55 |

`PROP_COL` colours the three ways of referring to an entity in one stacked bar: names `#2e4a62`, descriptions `#7d9bb3`, pronouns `#c9d6e0`. `PALETTE` is the 12-colour series list in §4.1.

## 6. Typography `[impl]`

Three roles, two real families:

| Family | Token | Job |
|---|---|---|
| UI sans | `--sans` | chrome, labels, buttons, numbers, tables, chart text (charts use Helvetica/Arial, `SVG_FONT`) |
| Serif | `--serif` | **anything that is the books' own text or a name from them**: entity names (`.ent-item .nm`, `.link-card .nm`, profile `h1`), book titles (`.bhead .bn`), evidence sentences, the reading text, concordance lines, and the page title `h1` of the editor-style pages |
| Monospace | none (literal `ui-monospace, Menlo, Consolas, monospace`, twice in `app.css`) | **identifiers and paths**: book ids (`.bid`), workspace and export folders (`.coll code`, `.bmore code`); other `code` elements (`.srcs code`) use the browser's monospace at 12 px |

- **AL-TYPE-01 —** Base is **14 px / 1.45** in `--sans` on `body` (the editor uses 13 px). Do not set another `font-size` on `body` or on a page; a component sets its own.
- **AL-TYPE-02 — Scale** (px; use these, add none): `9` sentence id superscript · `10.5` quote label, chart micro text · `11` section labels, `.t`, `.bid`, `.pno`, small captions · `11.5` concordance meta, text-view labels, topic bands · `12` control captions, `.basedon`, `.score`, `.tip` · `12.5` `.small`, hints, tags, table footers, notes · `13` tables, filter chips, the contents lists · `14` body, the brand · `14.5` concordance lines · `15` entity names in lists, the book panel's title, chapter heads in the text view · `16` evidence sentences, link cards · `17` panel `h2`, reading text, fact numbers in `.facts-inline` · `18` fact numbers in `.phead` · `19` book title in a card · `22` close glyph · `26` page title (`.page h1`) · `34` profile name (`.phead h1`). `10.5`, `11.5`, `12.5` and `14.5` are half steps; do not add more.
- **AL-TYPE-03 — Section label:** `font: 600 11px var(--sans); text-transform: uppercase; letter-spacing: .04em; color: var(--muted)` (`.lsec h2`, `.plural-title`). This and column headers are the only uses of uppercase besides the `.coll .now` marker ("In use"). Variants exist (AO-11).
- **AL-TYPE-04 —** Numbers that change or align use `font-variant-numeric: tabular-nums` (`.num`, `.n`, counts, facts, scores).
- **AL-TYPE-05 —** Weights: 400 body, 500 buttons/nav/menu rows, 600 headings, labels and names, 700 only the brand `.mark` and the keyword in a concordance line. `h1` of a profile is 500 (large serif).
- **AL-TYPE-06 —** Page titles: `.page h1` (serif 600/26, letter-spacing −.01em) on the editor-style pages; the entity name in a profile (serif 500/34). Analysis pages have no `h1`; the open tab is their title.

## 7. Space, shape, depth

### 7.1 Spacing `[impl]`

Eyeballed to a 2 px grid. Steps in use: `2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26`. `main` pads `20px 24px 60px`; `.panel` pads `16px 18px` with 16 below; cards pad `10px 14px` with 8 between; a `.row` has a gap of 10; control rows `10px 16px`; sections of an editor-style page start 26 px apart; the top bar pads `0 14px` with a 14 px gap. Prefer `gap` over margins.

### 7.2 Radius `[impl]`

- **AL-SPACE-02 — Radius:** `1` in-cell bars · `2` text marks, stacked proportion bars · `3` type chip, tag, tooltip of a chart · `4` inputs, selects, toast, `.sugg`, `.qedit` · `6` buttons, **`.panel`** and `.phead`, the plural-group box, popover items, contents-list links, the `.tip` tooltip · `7` segmented control, collection list rows · `8` secondary cards (`.link-card`, `.person-card`), source rows · `10` **cards, menus, popovers, the book panel** · `14` filter pill (`.chip`) · `999` pills (`.gtag`, `.tagchip`) · `50%` dots. **New cards MUST use 10** (editor rule DL-SPACE-02); `.panel` stays 6 until the pages are redone (AO-06).

### 7.3 Elevation and layers `[impl]`

- **AL-SPACE-03 — Elevation exists only for things that float:** menu, popover, book panel (`0 14px 34px -14px var(--shadow-lg)`); drawer (`-8px 0 24px var(--shadow-sm)`); the entity-search list and the book chooser menu (`0 6px 18px var(--shadow-sm)`). Cards and panels are flat: border plus `--panel`.
- **AL-SPACE-04 — z-index by role**, never by number: table header (1) < text-view header (10) < entity-search list (15) < book chooser menu (16) < top bar (20) < drawer (25) < popover (30) < menu and toast (40) < tooltip (41). A new floating element picks a role from this list. (The menu and the toast share 40 because they are never needed together; AO-12.)

### 7.4 Scrolling `[impl]`

- **AL-SPACE-05 — The document scrolls** (the editor never does). The top bar is `position: sticky`. Long data lives in **results boxes** that scroll inside themselves (AL-TBL-02). Sticky sidebars and headers are offset from `--bar-h`. A flex or grid child that must scroll inside its parent MUST have `min-height: 0` (see the `.ent-list .items` note in `docs/DOCUMENTATION.md` §8).
- **AL-SPACE-06 — Scroll chaining is deliberate.** A results box lets the page take over when it reaches its top or bottom (no `overscroll-behavior`); a list inside a floating panel (the book list, the popover list) is `overscroll-behavior: contain`, so the page behind stays put.

## 8. Layout

### 8.1 The shell `[impl]`

```
┌─ header.top (sticky, --bar-h) ─────────────────────────────────────────────────────────┐
│ aLex │ [Library] │ [Entities│Dialogue│Words│Style│Over time│Statistics│Read] ……… [← Back to …] (book) (?) (⋯) │
├─ nav#areaNav.subtabs (the open area's pages; hidden for an area of one page) ──────────┤
│  Concordance  Word list  N-grams  Collocates  Keywords  Topics                         │
├─ main#main (page content) ─────────────────────────────────────────────────────────────┤
│  one of the layouts in §8.2                                                            │
└────────────────────────────────────────────────────────────────────────────────────────┘
 aside#drawer (fixed, right, below the bar)         div#toast (fixed, bottom centre)
```

- **AL-LAY-01 — A new page SHOULD be one of the §8.2 layouts.** If it needs a new one, add it here with its CSS home (DL-LAY-06).
- **AL-LAY-02 — Responsive:** designed for a desktop window of 1000 px or more; remains usable (no horizontal page scroll; wide things scroll inside their own box) as far as it has been checked (AO-13). Breakpoints (max-width): `1200` (the Entities page menu is hidden), `980` (every two-column layout stacks; the topic menu becomes a row; the top bar tightens), `820` (editor-style pages: contents list becomes a strip, library nav becomes a strip, `.fields` stack), `720` (submenus open under their row), `700` (workspace cards stack).

### 8.2 Page layouts `[impl]` `[portable]`

| Pattern | Structure | CSS home | Used by |
|---|---|---|---|
| **A. Analysis page** | `main` (max 1500, centred) holding stacked `.panel` sections; a controls panel first; foldable, with a sticky "On this page" menu from three sections up (AL-FOLD-01) | `main`, `.panel`, `.page-toc` | Dialogue, Corpus, the Style and Over time pages, Topics, Compare, Described as, an entity's profile |
| **B. List + detail** | `.ent`: 300 px sticky list (`.head` for search and filters, `.items` scrolling) + detail; page menu on the right in windows wider than 1200 px | `.ent`, `.ent-list` | Entities |
| **C. Editor-style page** | `.page` (max 1040, centred) with a serif `h1`, `.lede`, sections `.lsec`; with `.with-toc` a 170 px contents list on the left (`.stoc`); sections hold `.fields` rows or cards | `.page`, `.lsec`, `.fields`, `.stoc`, `.libgrid` | Settings, Library |
| **D. Reading page** | `.read`: the text (serif, wide left margin for labels) + a 340 px sticky side panel; a frozen `.read-head` (settings above, position below) whose height is published as `--read-head` | `.read`, `.read-head`, `.read-side` | Read, chapter editor |
| **E. Topic page** | `.tp-layout`: 190 px sticky section list + sections | `.tp-layout`, `.tp-toc` | one topic's page |
| **F. Network** | `.net`: an SVG canvas (640 px high) + a 300 px side column | `.net` | Network |
| **G. Drawer** | fixed overlay on the right, below the bar, `min(620px, 100vw)` | `.drawer` | the sentences behind a count (`openEvidence`); the help of every page (`openHelp`) |

### 8.3 Areas `[impl]`

Agreed on 2026-10-26 (AD-27), built the same day (AD-29; `areas.js`). The top bar holds **eight areas** instead of Library plus twelve tabs; each area groups the pages that answer one kind of question (AL-PRIN-09) and shows them as tabs in `#areaNav`, a `.subtabs` row between the top bar and `#main`, lined up with `main`'s content and sticky under the bar (AL-AREA-04). The router (`drawAreas`) draws it on every page change, so a page never draws a tab row for its area's pages itself. A click on an area opens the page last used in it (`S.areaLast`, `analyser.areas`, per workspace); an area never used opens its first page.

- **AL-AREA-01 — The areas, left to right:** Library · Entities · Dialogue · Words · Style · Over time · Statistics · Read. Read is last: a tool reached from everywhere ("Open in the text") rather than an analysis. Entity Links, Narrators, the chapter editor, Workspace, Theme, Plural groups and Settings stay in `[...]` (AL-BAR-02).
- **AL-AREA-02 — Addresses do not change.** Every page keeps its address (`#/compare`, `#/narrative/style`, `#/corpus/kwic`…); the area is derived from the address, so saved links and the "Open in…" links between pages keep working and need no redirect. Help keeps opening by address (AD-25).
- **AL-AREA-04 — The area tabs stay in view and never move.** `#areaNav` is sticky under the top bar from the start (`top: var(--bar-h)`, no margin above it, so scrolling never shifts or resizes it), `--area-h` (45 px, with 8 px padding above the tabs) tall on `--bg`, with a band of `--area-gap` (10 px) of `--bg` below its line (a `box-shadow`), so content vanishes before it reaches the tabs. The page has no elastic overscroll (`overscroll-behavior-y: none` on `html`), so the bars don't bounce at the top or bottom. Everything else that sticks or scrolls to a heading stops under it: `--sticky-top` (on `html`) is `--bar-h`, plus `--area-h` and `--area-gap` while the tabs show (AD-31, AD-32).
- **AL-AREA-03 — An area of one page has no sub-tab row.** Library, Statistics and Read are single pages; Dialogue's own sub-tabs are its pages. The chapter editor (`#/chapters`) belongs to Read; the pages of `[...]` belong to no area (no row, no area marked). A page that has sub-views of its own inside an area (Sound and rhythm, Over the book) keeps them as an inner `.subtabs` row (AL-TAB-02).

| Area | Sub-tabs | Address (unchanged) | Today |
|---|---|---|---|
| **Library** | — | `#/books` | Library |
| **Entities** | Entities · Compare · Described as · Network | `#/entities`, `#/compare`, `#/described`, `#/network` | four tabs |
| **Dialogue** | Who speaks · Speech verbs · How they speak · Conversations · Quotes | `#/dialogue/speakers` … `#/dialogue/quotes` | Dialogue; In-Depth Who Speaks (`#/dialogue/indepth`) is to become a filter on Who speaks (AL-PRIN-13) |
| **Words** | Concordance · Word list · N-grams · Collocates · Keywords · Topics | `#/corpus/kwic` … `#/corpus/keywords`, `#/topics` | Corpus's tools and the Topics tab |
| **Style** | Style · Stylometry · Sound and rhythm | `#/narrative/style`, `#/narrative/stylometry`, `#/sound` (inner tabs `#/sound/<sub>`) | parts of Arcs and style, and the Sound and rhythm tab |
| **Over time** | Over the book · Arcs · Sentiment · Lexicons | `#/over` (inner tabs Within a book, Two books aligned, Books combined), `#/narrative/arcs`, `#/narrative/sentiment`, `#/narrative/lexicons` | the Over the book tab and parts of Arcs and style |
| **Statistics** | — | `#/stats` | Statistics |
| **Read** | — | `#/read` | Read |

## 9. Components `[impl]`

Class names are the stable handles; all CSS is in `app.css`.

### 9.1 Top bar

- **AL-BAR-01 — Order, left to right:** brand `.mark` (a plain label, 14 px/700, not a link) · **Library** (its own `.seg` of one link) · the **areas** (one `.seg` of links, `data-area`: Entities, Dialogue, Words, Style, Over time, Statistics, Read; §8.3) · `.top-end` pushed right with `margin-left: auto`: `← Back to …` (only after a drill-down), the focus chip (only with one focus for every page, AL-PRIN-12), the book button, the `?` button (help for the page you are on, in the drawer; `.btn.ico` with a bold "?"), the `[...]` button. The strip of areas scrolls sideways (scrollbar hidden) on a narrow window so the buttons stay in view. The bar is `--panel`, 1 px `--rule` below, `--bar-h` tall.
- **AL-BAR-02 — What is an area.** A group of pages that analyse the selected books and answer one kind of question is an area (§8.3); a page is one of its tabs in `#areaNav`. Library (the books and workspaces themselves) is an area of its own, visually apart. Pages used occasionally (Entity Links, Narrators) and Settings live in `[...]`. The router marks the open area with `.on` and `aria-current="page"` on its link (accent fill in the bar) and the open page in `#areaNav` the same way; a page of the menu tints the `[...]` button instead.
- **AL-BAR-03 —** The bar holds navigation and the global scope only. No page-specific control goes in it. The `?` (help) is the one exception that looks page-specific: it is the same button everywhere and only its content follows the page (AD-25).

### 9.2 The `[...]` menu

Same look as the editor's menu: a small `.menu` panel (radius 10, padding 6, gap 4, min width 170, popover shadow) of bordered `.mi` rows (radius 6, weight 500); the current choice is `.on` (`--accent-soft` + accent border); a value on the row is `.mi-val` (muted, right-aligned).

- **AL-MENU-01 — Entry kinds and ARIA:** a page link `<a class="mi" role="menuitem" data-tab>`; a submenu trigger `<button class="mi" aria-haspopup="menu" aria-expanded>` (with a `‹` marker) beside its `.menu`; a choice from a list `role="menuitemradio"` with `aria-checked` (Theme, Workspace); an on/off row `role="menuitemcheckbox"` with `aria-checked` and the state as its value ("On"/"Off": Plural groups).
- **AL-MENU-02 — Submenus open to the left** of their row, on hover or click, and stay open until another top-level row is touched (so a slanting move is not lost). A click on a trigger only opens, never closes. At 720 px and below a submenu opens under its row with a `⌄` marker.
- **AL-MENU-03 — The menu closes** on choosing an entry, on a mousedown outside it, and on Escape. Escape is handled in the capture phase and stops propagation, so one press closes only the menu (not the drawer behind it). Only one of the menu and the book panel is open at a time.
- **AL-MENU-04 — What belongs in the menu:** pages not needed constantly, and workspace-wide settings whose current value is worth showing on the row (Workspace → name, Theme → choice, Plural groups → On/Off). A submenu that needs more than a list of choices is a page, not a submenu. A page entry carries `data-tab` so the router can mark it open.

### 9.3 Book button and book panel

- **AL-BOOK-01 — The book button** (`#booksBtn`, a 16 px stroked icon, `.btn.ico`) sits left of `[...]`. It is tinted (`.on`) when fewer than all books are selected. Its tooltip `.tip` (`--chrome`, white 12 px) appears on hover or keyboard focus (a CSS sibling rule, hidden while the panel is open) and says `Viewing <label>` plus the count (`All 3 books`, `2 of 3 books`, `No books yet`). The label is the book's title, a collection's or series' name when the selection is exactly that, `Various for “X”` or `Various`.
- **AL-BOOK-02 — The book panel** (`#selPop`, `.menu.books-fly`, built each time it opens) holds: a search box, filters (collection, series, author, tag, from-year, to-year), *Select shown / All / None*, one checkbox per book, and *Cancel* + primary *Use these books*. Only the list scrolls. Nothing applies until *Use these books*; an empty choice is refused with a toast. (This is the one place where choices are gathered and applied together, AL-INT-01.)
- **AL-BOOK-03 — Drill-down and back.** A book name in a multi-book table or chart is a link (`bookLink`) that narrows the selection to that book and pushes the wider one; `← Back to <target>` (`#viewBack`, ellipsised at 30 ch, the tooltip has the full sentence) returns to it. The target is named in words: "all books", "3 books", a book, a collection or a series.

### 9.4 Buttons and links

| Component | Class | Notes |
|---|---|---|
| Button | `.btn` | panel fill, 1 px `--rule`, radius 6, padding `5px 11px` (`4px 9px` in the top bar), weight 500, `white-space: nowrap`; hover darkens the border to `--muted`; disabled 50 % opacity |
| Primary | `.btn.primary` | accent fill, `--accent-ink` text |
| Small | `.btn.small` | padding `2px 8px`, 12.5 px; for rows, cards, toolbars inside content |
| Toggle on | `.btn.on` | `--accent-soft` + accent border (`aria-pressed` when it is a toggle) |
| Icon | `.btn.ico` | 16 px SVG, padding `4px 7px`; the `[...]` glyph is filled, all others stroked (2 px, round) |
| Link-styled button | `.linkbtn` | 12 px, accent, underlined; actions inside a card or a menu ("Edit details", "Original text", "Collapse all") |
| Link | `a` | accent, underlined; `a.btn` for a link that looks like a button |

- **AL-BTN-01 —** At most one `.btn.primary` per region, and it is the region's main forward action (*Use these books*, *OK*, *Move*, *Done*, *Switch to*). It is **not** a selected-state style: a toggle uses `.on` (existing exceptions: AO-07).
- **AL-BTN-02 —** There is no filled red button. A destructive action is a plain `.btn` that asks first (AL-INT-03); `.warn` colours text only. (A `.btn.danger` text style is proposed, AO-07.)
- **AL-BTN-03 —** Every icon-only control has an `aria-label`, and a `title` or tooltip that names the action.
- **AL-BTN-04 —** A disabled control says why in its `title` where the reason is not obvious.
- **AL-BTN-05 — Labels** are the **verb**, sentence case: `Use these books`, `Make a workspace`, `Add folder`, `Remove`. A control that opens a picker or asks for more ends in `…` (`Move…`, `Delete…`, `Manage workspaces…`).
- **AL-BTN-06 — Downloads are quiet links** (`dlButton(label, onclick, title)` in core.js, `.dl`): 12 px `--muted` text with a dotted `--faint` underline, no border or fill, ink on hover; the title says what is downloaded. Under a chart `SVG · PNG` (`.chart-tools`, right-aligned; on the Network page `SVG · PNG · GEXF · GraphML` sit above the network instead, AD-41), under a table or list `CSV` (in `.tbl-foot`). A download is never a `.btn` beside the results it belongs to; a download that *is* the page's action (Export selected books, Download for R) stays a button (AD-30).

### 9.5 Inputs and control rows

- **AL-CTRL-01 — Inputs** (text, number, search, select, textarea): `--panel`, 1 px `--rule`, radius **4**, padding `5px 8px`, font inherited. A number input is 72 px wide (58 in `.mins`). Checkboxes are native with `accent-color: var(--accent)`; their labels are clickable.
- **AL-CTRL-02 — A row of controls** on an analysis page is `.controls` (flex-wrap, gap `10px 16px`, aligned to the bottom edge). Each control is a `label` with a 12 px muted caption above it (grid, gap 2) or a `.fld`; checkbox labels are `label.inline` (13 px, `--ink`). Four or more filters use `.filters-grid` (auto-fill columns of 200 px; `min-width: 0` on its children, or one long option widens every row).
- **AL-CTRL-03 — Choosing what to look at** always goes through the composite pickers in `core.js` (`picker`, `unitSearch`, `groupPicker`, `typePicker`, `booksChooser`). A choice is a **spec** `{kind: unit | group | type | tag | narration | book | gender | others, …}` that the server's `View.resolve` accepts, so a new page needs no new plumbing. Do not build another entity picker.
- **AL-CTRL-04 — Naming and renaming happen in place:** the buttons are replaced by a text field, a primary small *OK* and a *Cancel*; Enter confirms, Escape cancels (`ask()` in `books.js` and `workspaces.js`, the name editor on a profile). There are no modals and no `prompt()`.

### 9.6 Segmented control, tabs, chips

- **AL-TAB-01 — `.seg`** (radius 7, one border, active = accent fill with `--accent-ink`) is for mutually exclusive, always-visible choices of equal weight: the page tabs, Auto/Light/Dark, Search/Compare, Group by. Build it with `seg(options, value, onChange)`, which sets `aria-pressed` on every button; the tab links use `.on`.
- **AL-TAB-02 — `.subtabs`** (underline tabs: muted text, a 2 px `--ink` underline on the active one, an optional faint count `.n`) are the pages of an area (`#areaNav`, links) and the sub-views **inside** a page (Sound and rhythm, Over the book, Compare, Described as; buttons). The tab bar of a page MUST NOT move when its content changes.
- **AL-TAB-03 — `.chip`** (a pill, radius 14, 13 px; active = `--chrome` fill, white text) with a faint count `.n` is a **filter with counts**: the entity-type filter. `.legend button` (strikethrough and 45 % opacity when off) switches a chart series; `.btn.small` + `aria-pressed` is a state button (the sort-direction arrow `reverseBtn`).
- **AL-TAB-04 —** Tags: `.tag` (`--accent-soft`, accent text, radius 3, 12.5 px, an `×` button to remove) are the user's own labels on an entity; `.tagchip` (pill, `--panel-2`) is a clickable tag on a book card that fills the search box; `.gtag` (pill with a 3 px type-colour bar, the type code, the name, an optional book label, `×`) is one entity inside a group.

### 9.7 Cards and panels

- **AL-CARD-01 — Two families.** The **panel** `.panel` (`--panel`, 1 px `--rule`, radius 6, padding `16px 18px`, 16 below) is a section of an analysis page; it is foldable (AL-FOLD-01). The **card** (`.bookcard`, `.coll`: radius **10**, padding `10px 14px`, 8 between) is one thing in a list; `.current` = accent border plus a 1 px accent ring (the books being analysed, the open workspace). New list items use cards.
- **AL-CARD-02 — Secondary cards** sit on `--panel-2` (`.link-card`, `.person-card`, radius 8, padding `10px 12px`/`12px 14px`); `.picked` = accent border + `--accent-soft`. A dashed `--panel-2` box (`.gbox`, `.pickcol`) is a holding area for items the user has chosen (and empty text when there are none).
- **AL-CARD-03 — A profile header** (`.phead`) holds, top to bottom: the type chip and name of the type, the serif `h1`, the tags and actions, the facts row (`.facts`: a 12.5 px muted label under an 18 px/600 tabular number), and the presence strips.
- **AL-CARD-04 — Inside a card**, in this order: title (serif) · muted meta line · counts at the right (tabular, `.bcount`) · tags · secondary rows (`.bmore`, `.bcoll`, 12.5 px muted) · actions at the right (`.acts`).

### 9.8 Settings and editor-style pages

- **AL-SET-01 — A page in the editor's layout** is `.page` (centred, max 1040; `.with-toc` adds a 170 px `.stoc` contents list on the left, 28 px gap) with a serif `h1`, a muted `.lede`, and sections `.lsec` (26 px above, UPPERCASE `h2`). A setting is a `.fields` row: a 150 px muted label column and a control column with an optional `.hint` under the control (12.5 px muted, max 80 ch). Long explanations follow the rows in a collapsed `note()`. The contents list scrolls to its section (smooth, address bar unchanged) and marks the last section whose top has passed 110 px from the top.
- **AL-SET-02 — A setting saves when it is chosen** (toast "Saved.", page redrawn); there is no Apply button. A page says whose settings they are ("For the workspace in use. Choices save as you make them."); the exception is marked on its row ("The same in every workspace.", the theme).
- **AL-SET-03 —** A setting that also has a control elsewhere says so in its hint ("The same switch is “Plural groups” in the [...] menu") and both controls change the same stored value.

### 9.9 Tables and results boxes

- **AL-TBL-01 —** Tables are made by `table(cols, rows, opts)`: `.t2`, 13 px; headers 600 muted, click to sort (`↓`/`↑` after the name; numbers start descending, text ascending); cells padded `4px 8px` with `--rule-soft` separators; clickable rows hover `--panel-2`; numbers are `.num` (right-aligned, tabular). It shows 60 rows, then a footer with the row count, *Show all* and *Download CSV* (`.btn.small`).
- **AL-TBL-02 — Results boxes.** Every table (`.tbl-wrap`), the concordance lines and the Dialogue quote list (`.results-scroll`) are at most one screen tall (`100vh − --bar-h − 24px`) and scroll inside themselves. Headers are sticky inside the box (an inset shadow replaces the border a sticky cell loses). Footers, *Show all* and *Show more* sit **outside** the box. `overscroll-behavior` is left unset so the page takes over at the box's edge (AL-SPACE-06). Short tables keep their natural height.
- **AL-TBL-03 —** A bar inside a cell (`.bar-cell i`: 7 px high, accent at 55 %) is scaled to the column maximum (`barFmt`) and always sits beside the printed number.
- **AL-TBL-04 —** Concordance lines (`.kwic`, `.kl`) are serif 14.5 px, one line each, the keyword accent and bold; the left context is right-aligned.
- **AL-TBL-05 —** A row the user corrected has a 3 px accent inset on its first cell (`tr.edited`); a row outside the current scope is dimmed with `--faint` (`tr.dim`).
- **AL-TBL-07 — The numbers under a chart fold away.** A table that gives, slice by slice or chapter by chapter, the numbers a chart above it draws (Along the book on Over the book and Compare, the arcs of Arcs, Sentiment and Lexicons, a topic's arc) sits in `foldTable(summary, table)`: a `<details class="tfold">` with a quiet summary (*Numbers per slice*, *Numbers per chapter or slice*), **folded by default**; one opened stays open while the page is redrawn on this visit (`tableFolds`, not stored). A page's own data table (Style, Sound → Figures, Slice by slice) is not folded (AD-39).
- **AL-TBL-06 — Column chooser.** A table of 7 columns or more (`COLS_CHOOSER_MIN`) has a quiet *Columns: n of m* link beside its CSV link (`.tbl-tools`) that opens a list of checkboxes above it (`.colpop`, the popover look: `--panel`, radius 10, popover shadow; grouped by a column's `group`, with *Show all* and *Default*); it closes on a click outside or Escape. The first column, and any column of corrections or warnings (`keep`: *Set by paragraph*, *Guessed pronunciations*), can't be hidden (AL-PRIN-11, AL-PRIN-14). The widest tables open on a headline set (`show`: style, sound, speaking style, narrators, Book by book's overview, speech per book, network measures); others show every column until you hide some. The choice is kept per table and workspace (`analyser.columns`; a named table, such as the sound table on Style and on Sound, shares one choice). **The CSV always has every column** (AD-34).

### 9.10 Charts

- **AL-CHART-01 —** A chart is an `<svg>` with a `viewBox`, `role="img"` and an `aria-label` (or `<title>` children). Its text is 10.5–12 px in `SVG_FONT` (titles 13 px). Colours that follow the theme (text, gridlines, backdrops) are read with `cssVar("--ink")` and the like **at draw time**; changing the theme re-renders the page so charts pick the new values up.
- **AL-CHART-02 —** Marks: lines 2 px with 3.5 px points that have `<title>` tooltips; horizontal bars 12 px high in a 14 px row, the value printed at the end; presence strips use one colour with opacity from 0.15 to 1 by count; gridlines `--rule-soft`; axis text `--faint`/`--muted`. At most about sixteen x labels; end labels are nudged at least 13 px apart; beyond 12 lines the labels become tooltips (`MANY_LINES`).
- **AL-CHART-03 —** Max widths: bar charts 760 px, line charts 900 px, the network canvas 640 px high. Hovering a network node highlights it and its neighbours; a click pins that focus; a click on empty space releases it.
- **AL-CHART-04 — Every chart is wrapped in `chartBox()`** (SVG and PNG download buttons). A downloaded file has no theme: `prepSvg` swaps the theme's `--ink`, `--muted`, `--faint`, `--panel`, `--panel-2` back to the light constants `LIGHT_*` (a test keeps them equal to the light tokens) and adds a white backing rectangle.
- **AL-CHART-05 —** Series colours follow AL-COLOR-06; categorical colours in a chart are not tuned per theme.

### 9.11 Evidence, drawer and text

- **AL-TEXT-01 — An evidence sentence** (`.ev`) has a source line (`.src`, 12 px muted: `Title, 12.3% through · speaker · link to the text`) above the sentence in serif 16 px/1.55 (max 70 ch) with highlight marks (§5.2). Text from the server reaches the page through `markup()`.
- **AL-TEXT-02 — The drawer** (`.drawer`, `--panel-2`, 1 px left rule, small shadow) opens from any count (`openEvidence`, the quote lists), shows "Finding sentences…" while loading, a count line with *Download CSV*, then the sentences. It closes with `×` or Escape and on every page change. The help reuses it (`openHelp`, from the top bar's `?`: `.svhelp-toc` contents of `.linkbtn`s, `.svhelp` sections with a two-column `dl` of option and explanation, then "Everywhere in aLex" under an `.svhelp-part` rule); a "?" opens it at a section: on a Statistics variable `.btn small`, in a dense panel's heading `.hq` (`helpHead`: 18 px round, `--rule` border, muted, accent on hover, its "?" drawn by `::before` so the heading text is unchanged).
- **AL-TEXT-03 — The text view** (`.read-text`, serif 17 px/1.7 on `--panel`, 210 px left margin for chapter and paragraph labels in 11–11.5 px, paragraphs max 68 ch). Layers: entities underlined 2 px in the type colour (dotted when below the minimum), quotes tinted (`--tint-quote-bg`, with a `.ql` speaker label), events dotted underline in `--VEH`, supersenses wavy in `--GPE`, topics tinted by `color-mix` at 14 % of the topic colour with a 3 px left bar. Narrower than 980 px the narrator and chapter-start labels stack above the paragraph.

### 9.12 Feedback, floating UI and states

- **AL-FB-01 — Toast** (`#toast`, fixed, bottom 20 px, centred, `--chrome` with white text, radius 4, padding `8px 16px`, z 40): states what happened ("Saved.", "Exported 3 books.", "Narrator saved."). 2.5 s; an error (`.toast.err`, `--warn` fill) 6 s. One at a time; no action button; never `alert()`.
- **AL-FB-02 — States.** *Loading:* `loading("Finding sentences…")`, a muted line with a verb; if the request fails, `api()` replaces it with a `.warn.small` message and shows a toast. *Empty:* `.empty` (centred, muted, 32 px padding) says what is missing **and what to do next** ("No folders yet. Add the folder where your BookNLP output is."). *Problem:* `.warn` or `.warn.small` lines. Never leave a panel blank.
- **AL-FB-03 — Explanation has three sizes.** A tooltip (`title`) for a label or column; a `.hint` / `.muted.small` line for one sentence under a control; a collapsed `note(summary, …paragraphs)` (`<details class="note">`, 12.5 px muted, max 80 ch) for method and background ("How this is calculated", "About these cards"). Do not open a note by default.
- **AL-BASED-01 — "Based on" line** (`basedOn(items)` in core.js, `.basedon`: 12 px `--muted`, 4 px above and below; the way AL-PRIN-11 is drawn). "Based on: " then the items joined by " · "; an item is a link (`a.bo`, dotted `--faint` underline) to where it is changed, or plain text. An item that is a setting changed from its default (compared with the server's `default_settings`), or one of your corrections, is `.bo.set`: `--accent-soft` fill, `--ink` text, radius 3 (one meaning, "set by you"; no colour per kind). The shared items are `BASED.mentions/plural/freq/convGap/speechSkip`; a panel adds its own (a link across books, addressees you set). One line under a page's header for what every figure depends on, and one at the top of a panel for what only it depends on; a line inside a `<summary>` opens the setting in place (Over the book on a profile). `minLine()` and `freqLine()` are one-item lines. Settings sections are reached as `#/settings/<section>`.
- **AL-FB-05 — "Read with care" marker** (`relMark(why)` / `relNum(text, why)` in core.js, `.rel`: a superscript "≈", 10.5 px `--muted`, `cursor: help`, the reason as its tooltip and in its `aria-label`; a column takes it in its header with `rel`). One sign for every figure to trust less: a small sample (MATTR under 100 words, `MATTR_SHORT`; a statistic from fewer than 30 cases, `FEW_CASES`), an estimate (addressees, `ADDR_ESTIMATED`), an unstable topic (under 60% recurrence, `topicUnstable`), sound figures with more than 10% guessed pronunciations (`SND_GUESSED_MAX`, `sndGuessy`). It replaces brackets and "(estimated)" in headings. The figure is never hidden, and the CSV keeps the plain value (AD-36).
- **AL-FB-04 — Popover** (`.pop`, used by `narratorSelect`): absolutely positioned under its button (`top: 100% + 4px`, left edge aligned), 280 px, `--panel`, 1 px `--rule`, radius 10, popover shadow; a search field and a list (`.pop-list`, max 240 px, scroll contained; `.pop-item`, current `.on` = `--accent-soft`, 600). The button shows the choice and `▾`, with `aria-haspopup="listbox"` and `aria-expanded`; items are `role="option"`. Focus moves to the search field; it closes on a choice, a mousedown outside, or Escape (focus returns to the button).

### 9.13 Folding and the page menu

- **AL-FOLD-01 —** `pagetools.js` watches `#main`. A `section.panel` with a heading (or `data-toc="Label"`), and an `h3` with the content after it, get a fold arrow `.cx`; the choice is remembered per page and heading (`analyser.collapsed`). A page with three or more such sections gets a sticky "On this page" menu, **always at the right** (`.page-toc`, 180 px, drawn after the content; the topic page's `.tp-toc` too; AD-31) with *Collapse all* / *Expand all*; the current section is marked as the page scrolls. A « / » button in the menu's title row (`.toc-fold`, also on the topic page's `.tp-toc`) folds the menu to a 28 px sticky rail, remembered per page (`analyser.tocClosed`); `main.toc-closed` then drops the 1500 px cap so the content takes the whole window (AD-26). A panel with `data-group` is listed under that group's label (`.page-toc-group`: 11 px, 600, uppercase, `--muted`), shown once where the group starts; the entity profile groups its sections by question (AD-30). Topic, reading and network pages have their own navigation and no menu. An element that must not fold sits inside one of the excluded containers or is not a `section.panel`.

## 10. Interaction and state

- **AL-INT-01 — Saved at once.** Edits to data (tags, names, links, corrections) and settings are written when the user leaves the field or chooses the value, and answered by a toast. The exception is a picker that gathers several choices and has an explicit *Use* / *Cancel* (the book panel).
- **AL-INT-02 — The scope is global and explicit.** `S.sel` (selected book ids; `null` = all) and the plural-group mode go with every analysis request (`withBooks`, `pluralMode`). Changing them re-renders the current page. Removing a book from the library drops it from the selection and the *Back* history (`pruneSel`).
- **AL-INT-03 — Confirmation policy (there is no undo).** `confirm()` is used when removing structure that took effort to make — a collection, a saved group, a topic model, a narrator or entity link, *Reset all links*, the chapters made by hand, a workspace from the list — and the sentence says what **stays** ("Its books stay in the library."). Deleting data on disk (a workspace's folder) additionally needs its name typed before *Delete for good* enables, and the server checks the name too. No confirmation for anything that can be re-entered (a rename, a tag, a selection).
- **AL-INT-04 — Automatic proposals are suggestions.** Suggested links, plural groups and narrators are listed with the reason (`.why`, a score) and applied only by a click; "Not the same" decisions are remembered. Nothing is applied silently.
- **AL-INT-05 — Keyboard.** aLex has no application-wide shortcuts. It MUST be possible to reach every control with Tab; Enter confirms a one-field edit and activates a custom row (`role="button"`, `tabindex="0"`); Escape cancels or closes the innermost thing — the open menu or book panel first, then the drawer; inline editors and popovers handle their own Escape. Ctrl/⌘+Enter submits a multi-line query. The focus ring is `outline: 2px solid var(--accent); outline-offset: 2px`.
- **AL-INT-06 — The address is the page.** `#/<tab>/<sub>/<id>`; every page is linkable; an entity profile is `#/entities/<id>`; with no books every page except Library and Settings redirects to `#/books`. A drill-down or jump always leaves a way back (AL-BOOK-03, "Show in text").
- **AL-INT-07 — Persistence.** A personal view preference goes to `localStorage` under `analyser.<name>` through `loadState`/`saveState` (defaults merged key by key, a value of the wrong kind ignored), **per workspace** (suffix `@<id>`, the Default workspace keeps the plain key) except the theme (`GLOBAL_KEYS`). Everything is wrapped in try/catch with a fallback. What belongs to the library (settings, links, groups, collections, corrections) is stored by the server through `/api/*`. Never store book data in `localStorage`.
- **AL-INT-08 — Independent controls.** Two panels that read one state is a bug; a documented global setting drawn once is intended (AL-PRIN-04). The intended globals: the book selection and plural mode (top bar), the Corpus scope and search settings (drawn once at the top of the five Corpus tools), the slice/chapter setting of Arcs and style, the significance settings (`S.stat`, with `syncStat` keeping panels that show them equal), and the way a minimum word frequency is counted (Settings → Words, shown beside each minimum by `freqLine()`).
- **AL-INT-09 — Motion** is functional and almost absent: the fold arrow turns in 0.12 s, a section menu click scrolls smoothly. `prefers-reduced-motion` switches CSS transitions off (smooth scrolling is not covered, AO-14). No decorative animation.

## 11. Content and copy

- **AL-COPY-01 — Language and case.** British English in UI text, comments and docs (organisations, colour); sentence case everywhere. **Full stops:** toasts, hints, notes, empty states and errors are sentences and end with one; buttons, tab names, column headers and single-sentence tooltips that name an action do not. (The editor's rule leaves the full stop off single-sentence hints, and its toasts have none; aLex's do.)
- **AL-COPY-02 — Voice:** direct, second person, present tense, no exclamation marks, no apology, no "please". Say what will happen **and** what will not ("Remove “X” from the list? Its files stay where they are.").
- **AL-COPY-03 — Names.** Use the product's nouns consistently: *book*, *library* (all books found), *collection* (nests; a book can be in several), *workspace* (a separate library), *entity* (one BookNLP coreference cluster that reaches the minimum mentions), *type* (PER, LOC, FAC, GPE, VEH, ORG, VAR), *group* (entities picked by hand), *plural group* (an entity standing for several: "Holmes and Watson", "they"), *link* / *linked entity* (the same entity across books), *narrator*, *mention*, *quote*, *speaker*, *addressee*, *topic*, *export*, *source folder*. Pages: Library, Entities, Dialogue, Read, Corpus, Arcs and style, Topics, Compare, Described as, Network; in the menu: Entity Links, Narrators, Workspace, Theme, Plural groups, Settings. **Entity Links** is the one title-cased name, chosen on purpose (AD-14).
- **AL-COPY-04 — Characters.** `…` (not `...`) on controls that open something or need more; `“ ”` around quoted names; `’` apostrophes; `·` as a metadata separator ("Author · 1902 · Series"); `←` `↑` `↓` as arrows; `×` to remove; `＋` (full-width) as the label of an add-to select; `—` for a missing number (`fmt`). No emoji.
- **AL-COPY-05 — Placeholders** show the format by example (`/path/to/folder/with/books`, `Find by name…`, `or add every entity named… (moor, mire)`).
- **AL-COPY-06 — Numbers.** `fmt()` formats with `en-GB` grouping (`1,234.5`); `plural(n, one, many)` gives "1 book", "3 books"; a share of a set is "3 of 4 books"; p-values use `fmtP` (`< 0.0001`). A figure that is partly missing says so ("(publication date missing)").
- **AL-COPY-07 — Errors** come from the server's `detail` verbatim, in a toast and, where a "Loading…" line was waiting, in its place. The one message the browser writes itself is "Can't reach the analyser. Is it still running?".

## 12. Decision log

Dated, with the reason and the evidence. Add new decisions here; never rewrite an old one (supersede it with a new line). "by" means the first commit that contains it; the earlier rounds were not dated more precisely.

| ID | Date | Decision | Why / source |
|---|---|---|---|
| AD-01 | by 2026-10-04 (`a85abaa`) | One stylesheet with custom properties on `:root`; dark values in two blocks (system and explicit); `--chrome` stays dark in both themes. | One place to change colours; toast and tooltips need no dark variant. |
| AD-02 | by 2026-10-04 (`a85abaa`) | Charts are SVG that read theme colours at draw time; downloads always use light colours on white. | A saved file has no theme. |
| AD-03 | by 2026-10-04 (`a85abaa`) | Remembered UI state is per workspace; only the theme is shared. | A selection or search from one corpus must not leak into another. |
| AD-04 | by 2026-10-04 (`a85abaa`) | Deleting a workspace's folder needs its name typed; removing from the list needs a confirm. | Irreversible; no undo in aLex. |
| AD-05 | 2026-10-09 (`9543e72`) | aLex adopts the editor's design language. It keeps its own token names (`--panel`, `--rule`, …) and adds `--accent-ink` and `--bar-h`; token **values**, base size and serif are aLex's own. | User wants aLex and the editor to feel like one product. Whether the values should converge is open (AO-15). |
| AD-06 | 2026-10-09 (`9543e72`) | Top bar: light `--panel` bar, brand label on the left, Library as its own segment, the nine pages as one `.seg` of links, actions on the right. | The editor's header; the brand is a plain label (the redesign plan had made it a link; Library has its own tab). |
| AD-07 | 2026-10-09 (`b1bba9b`) | Entity Links, Narrators, Workspace, Theme and Settings go into a `[...]` menu in the editor's look; submenus open to the left on hover or click and stay open until another row is touched; at ≤ 720 px they open under their row. | A calmer top bar. |
| AD-08 | 2026-10-09 (`b1bba9b`) | Theme and Workspace are radio lists (Workspace adds "Manage workspaces…"); the open choice is shown on the row. | The editor's menu rows; the value is visible without opening the submenu. |
| AD-09 | 2026-10-09 (`9543e72`) | "Include plural-group mentions" is **one** setting of the workspace: a Plural groups On/Off row in `[...]` and a switch on Settings; the per-page checkboxes were removed. | The same switch had been drawn on many pages; now one setting is drawn once (AL-PRIN-04). |
| AD-10 | 2026-10-09 (`9543e72`) | The "Viewing …" bar and the Books submenu became a book button with a hover tooltip and a click-open picker panel; `← Back` appears only after a drill-down; the button is tinted when the selection is partial. | The count and the label moved out of the bar; the picker is the same list in a panel. |
| AD-11 | 2026-10-09 (`9543e72`) | Settings page in the editor's layout: contents list left, `.lsec` sections (Appearance, Entities, Words, Folders), `.fields` rows with a short muted hint; long explanations stay in a collapsed `note()`. Narrator suggestion limits stay on the Narrators page. | The editor's Settings; hints short, background optional. |
| AD-12 | by 2026-10-04 (`a85abaa`) | **Independent controls:** a control must never change what another shows; shared state is drawn once and says so. | A user rule, after two reports (Speech verbs' two filters; Book by book / What's distinctive's significance settings). |
| AD-13 | 2026-10-09 (`9543e72`) | Library: collections in a list on the left, a **card per book** (`.bookcard`, tick to analyse, details form in place, narrator popover, export used), Workspaces as cards (`.coll`), a footer link to Settings. | Fixes the blank space of the table's narrator column; same cards as the editor's library. |
| AD-14 | 2026-09-30 (`a8f664f`) | "Links" was renamed **Entity Links**; the name is kept as it is, title-cased (AL-COPY-03). | Reason not recorded. |
| AD-15 | 2026-10-04 (`3babc2b`) | "Books" was renamed **Library**. | Reason not recorded; the page now holds the collections, the book cards and the workspaces. |
| AD-16 | 2026-10-09 (`df30a4f`) | Results boxes: at most one screen tall, scroll inside first, the page takes over at the edges (no overscroll containment); footers outside. A floating list (book panel, popover) is contained. | A box that traps the wheel feels broken; a floating list must not scroll the page behind it. |
| AD-17 | 2026-10-09 | Design record: `docs/DESIGN.md` written, pinned to the editor's file of 2026-10-09; `tests/test_design.py` guards the tokens. | Reference for redesigning aLex and for companion projects. |
| AD-18 | 2026-10-11 | The correlation heatmap (Statistics) is a diverging scale: `LIGHT_PANEL2` at r = 0, deepening to `PALETTE[0]` (blue, positive) and `PALETTE[1]` (red, negative) at ±1, the same two hues as the keyness tints `.rp`/`.rn`; cell colours are fixed in both themes (AL-COLOR-07), text in a cell is `LIGHT_INK`, or white beyond \|r\| 0.55; a cell without a coefficient is a dashed outline with a dash. | Two hues and a neutral midpoint, never a rainbow; one reading on screen and in a download. |
| AD-19 | 2026-10-11 | The Statistics variable lists offer two editors, rows (default) and chips that open their fields in place; the choice is a Settings row (Appearance), remembered per workspace. | The user asked for both, with the choice in Settings. |
| AD-20 | 2026-10-11 | Statistics variable chips use the entity-chip look (`.gtag`: a short kind label, the inset colour bar): the bar is the type colour (`TC`) of the entities a variable is about (mentions, speech, relations of someone, "is one of"; a gender is `TC.GENDER`; a group or tag only when all its entities share a type); words, layers and topics have no bar. No colour per variable kind, so a colour always means a type (AL-COLOR-06). | The user asked for the analyser's entity-type chip scheme. |
| AD-21 | 2026-10-11 | The Lexicons sub-tab of Arcs and style is one collapsible panel per lexicon (the existing panel fold of `pagetools.js`, remembered per heading), the emotion lexicon always first. A lexicon met for the first time starts folded (except the first panel) and a folded panel loads nothing until it is opened (`expand` event). Words are browsed and edited in a text box, one word per line. | Several lexicons on one page each cost an arc over every selected book; the user asked for one section per lexicon on a shared page, with the emotion lexicon kept special. |
| AD-22 | 2026-10-13 | The Over the book heat grid is an ordinary `table()` whose slice columns are narrow cells (`.hcell`, 14 × 22 px, header = the slice number with the slice's name as tooltip), so sorting, CSV, row click and the sticky word column come for free. A cell is `PALETTE[0]` at an opacity of 0.12–1 relative to the word's **own** highest share (an opacity, so it reads on both themes); a faint `--rule-soft` cell is a slice with other words but not this one, a hatched one a slice with nothing in the list. The Numbers view uses the `.rp`/`.rn` residual tints of Book by book. | The shape of each word over the book is what matters, not how common it is; a table keeps every view exportable. |
| AD-23 | 2026-10-15 | A chart of one combined line with many lines behind it (Books combined, “Show each book”) draws the background lines as a `faint` series of `arcChart`: 1.2 px, `--muted` at 55 % opacity, no points, no legend entry, the book's name as hover title; the combined line keeps its colour, points and legend. | The reader should see the spread of the books without a legend of dozens of entries; `--muted` reads on both themes where the line's own dark blue did not. |
| AD-24 | 2026-10-15 | How a minimum word frequency is counted (over the selected books together, or in each book) is **one** workspace setting, Settings → Words, a new section between Entities and Folders. The number stays in each tool; a `.minline` with a *Change* link (`freqLine()`) shows the setting beside it. | The same split as mentions: the amount belongs to the tool, the way of counting to the workspace (AL-INT-08). |
| AD-25 | 2026-10-22 | Every page's help opens from one `?` in the top bar (before `[...]`), in the evidence drawer, at the page's sub-tab when its help has that section; texts are one `help-<page>.js` per page registered with `addHelp`, short entries per option with an example, and "Everywhere in aLex" under each. Extra `?` buttons only beside dense panels and Statistics variables. | The user asked for a help drawer on every page, opened the same way everywhere. |
| AD-26 | 2026-10-23 | The side menus (`.page-toc`, `.tp-toc`) fold to a 28 px rail with a « / » button in their title row, mirrored on the Entities page's right-hand menu; the choice is remembered per page, and a folded menu lifts `main`'s 1500 px cap. Under 980 px the menu is hidden anyway, so there is no rail. | The user wanted more width for wide tables and charts; a rail keeps the menu one click away. |
| AD-27 | 2026-10-26 | **Simplification round:** principles AL-PRIN-09…14 and the eight areas of §8.3. One design for researcher and first-time user (no simple/expert mode); a calm hierarchy with everything visible, folding chosen page by page; the focus is per page by default, or one focus for every page, chosen under Settings → Entities, per workspace; Entity Links, Narrators and the chapter editor stay in `[...]`; the entity area keeps the name *Entities*. | The user found the interface overwhelming: sixteen places, features in two or three of them (Over the book, sound, word choice, Who speaks), an entity profile of twenty sections. The user chose each point. |
| AD-28 | 2026-10-26 | The **"Based on" line** (AL-BASED-01), first on the entity profile: a line under the header (minimum mentions, plural groups, linked across books) and one per panel (Book by book: how the minimum frequency is counted; Over the book: how the book is cut; Speech: the conversation gap, words left out of the speech verbs, quotes by or to them whose addressees you set). Settings changed from their default and your corrections share one tint; every item links to its own place. `minLine`/`freqLine` became one-item lines, so the Entities list and the Corpus tools show the same look. | Simplification step 2 (AL-PRIN-11). The user chose the profile as pilot, lines both page-wide and per panel, the label "Based on:", one tint for "set by you", links to each item's place, and corrections counted for the entity itself (the server's `corrected` counts). |
| AD-29 | 2026-10-26 | **The areas are built** (§8.3, `areas.js`): the top bar's links are the eight areas; the open area's pages are underline tabs in `#areaNav` above the page (not a second sticky bar), replacing the first tab row that Dialogue, Corpus and Arcs and style drew themselves (the Corpus tool tabs no longer join the settings panel, `.corp-tabs` is gone; Dialogue's conversation gap sits in a line of its own, right-aligned above its pages). Clicking an area opens the page last used in it, per workspace. The chapter editor belongs to Read. "Arcs and style" is no longer a name in the interface: its shared slicer is called by its label, *Measure over*. | Simplification step 3. The user chose tabs at the top of the page over a second bar, the last page used over the first, and Read for the chapter editor. |
| AD-30 | 2026-10-26 | **Entity profile, calmer** (simplification step 4): its sections follow the questions they answer, grouped in the side menu — *Who they are* (How they're referred to, Appears with) · *What they do* (What they do and what's done to them, with Kinds of action now a part of it under the word table) · *What they say* (Speech) · *How they change* (Book by book, Over the book) · *What sets them apart* (What's distinctive, Topics). The profile's Over the book is a preview (mentions per 1,000 words, the book switch, the Based on line, the link), its words and kinds of action only on the page (AL-PRIN-13). Downloads everywhere are quiet links (AL-BTN-06). The profile went from 10 sections and about 5,800 px to 9 sections and about 4,900 px (Holmes linked across two fixture books). | The user chose all four: reorder with group labels, join Kinds of action, a small preview, quiet text links. |
| AD-31 | 2026-10-26 | The side menu ("On this page") is **always at the right**, on every page including the topic pages; its fold button shows » (fold away to the right) and « on the rail. The **area tabs are sticky** under the top bar (AL-AREA-04), and every sticky offset and scroll margin now uses `--sticky-top` instead of literals. Supersedes the "scroll away" part of AD-29 and the left-hand menu of AD-26. | The user: the menu must not switch sides between pages, and the area tabs should stay in view. |
| AD-32 | 2026-10-26 | The area tabs no longer bounce: they sit directly under the top bar from the start (the 14 px margin above them, which scrolled away before they stuck, is padding inside them now), keep one height, and have a fixed 10 px band of page background below, so the content scrolls out of sight with a gap before it reaches them; the page's elastic overscroll is switched off. | The user saw the tab bar move and grow or shrink while scrolling and asked for it to stay put, with a small gap above the content. |
| AD-33 | 2026-10-26 | **The focus is built** (AL-PRIN-12, `focus.js`): only a page's subject follows; opening an entity's, group's, book's or gender's profile sets the focus; it is shown as a top-bar chip with ×, and each following chooser says so; a chooser that can't take it says nothing and shows its own. The mode is a browser setting per workspace (like the Statistics editor, AD-19), not a library setting. | Simplification step 5. The user chose subjects only, profiles setting the focus, the chip plus the note, and silence on a mismatch. |
| AD-34 | 2026-10-26 | **Column choosers** (AL-TBL-06, simplification step 6): every table of 7+ columns, a footer link that opens grouped checkboxes, headline defaults for the seven widest (the sound table opens on 10 of its 44 columns, style and speaking style on 8 of 17), corrections and warnings never hidden, CSV always complete. | The user chose the footer link with a list, a headline default set, every column in the CSV, and the chooser on every table of 7+ columns. |
| AD-35 | 2026-10-26 | **One home for the sound figures** (AL-PRIN-13, simplification step 7): the Style page's sound and rhythm table and its run-settings bar are gone; a line links to Sound and rhythm → Figures (the same figures with Text: Everywhere). Style's Chart can still draw a sound figure, with a "Based on" line naming how runs are found and your pronunciation corrections (`sndBasedOn`). In-Depth Who Speaks and Compare's Over the book section stay as they are. | Of the three duplicates offered (In-Depth into Who speaks, Style's sound table, Compare's Over the book), the user chose only this one. |
| AD-36 | 2026-10-26 | **Statistics in three steps and the ≈ marker** (simplification step 8): Statistics is a quiet top line (intro, saved sets) and three sections, 1 Cases · 2 Variables · 3 Run; the five "+ kind" buttons and the layer select became one "+ Add a variable…" menu, the bulk adders one "Add several…" menu. AL-PRIN-14 is built as one marker, ≈ (AL-FB-05), on short-sample MATTR, statistics from fewer than 30 cases, estimated addressees, unstable topics and sound rows with more than 10% guessed pronunciations. | The user chose the three steps, the two menus, ≈ over a dimmed number, and all four places. The thresholds (30 cases, 10% guessed) are mine and stated where they apply. |
| AD-37 | 2026-10-26 | **Over the book, calmer** (page-by-page pass): in all three views the curve (*Along the book*) comes first; *Kinds of action* is a tab of the words section (`S.over.kinds`), so each target has one grid section with one row of controls (View · Order, now a select · the test settings); tables whose columns are slices, books or texts (heat grids, Book by book's word matrix, Stylometry's distances) have no column chooser (`table(…, { columns: false })`). | The user chose the curve first, the kinds as a tab, and one quiet row of controls. The page loses a section per target (about 700 px each) and 4 order buttons. |
| AD-38 | 2026-10-26 | **Stylometry, calmer** (page-by-page pass): three panels, *Compare* (Texts, with the Measure over slicer beside it when chapters or slices are compared, replacing the near-empty note panel; then a labelled *Method* row), *Cluster tree and map* (Colour by above them; the two side by side on a wide window, drawn at 560 px so their text keeps its size, `STYLO_CHART_W`), *Nearest texts and distances*. | The user chose What · Method · Colour and the charts side by side. |
| AD-39 | 2026-10-26 | **Numbers under charts fold; Style without sound.** The per-slice tables under slice charts are folded by default (AL-TBL-07). The Style page has no sound and rhythm at all any more: no section, no link, no sound figures in its Chart (supersedes the link and chart part of AD-35); the Sound and rhythm tab next to it is their one home. | The user's request: a neater page, and the tab is enough on its own. |
| AD-40 | 2026-10-26 | **Network, calmer** (page-by-page pass): a panel *Which entities and links* (links, types, the minimums, Show at most, unlinked, the count line), a drawing row right above the network (Colour by, Size by, Labels, Reset view, the legend; it changes only the picture), SVG · PNG · GEXF · GraphML as quiet links under the network (AL-BTN-06), and the table of every link folded under Measures (AL-TBL-07). | The user chose all three proposals. |
| AD-41 | 2026-10-26 | The Network page's downloads (SVG · PNG · GEXF · GraphML) sit right above the network, not under it (supersedes that part of AD-40). | The user's request. |
| AD-42 | 2026-10-26 | **A circular layout for the network**, as Gephi's: *Layout* (Force-directed, the default, or Circle) and, for the circle, *Order by* (community, type, the size measure, name) in the drawing row. The circle is laid out in the browser from the network already loaded (`circlePositions`), clockwise from the top, with room for labels, which point outwards on the left half. Kept with the page's other drawing choices (`S.net.layout`, `S.net.order`). | The user's request. Community is the default order so that communities sit together, as in Gephi's usual use. |
| AD-43 | 2026-10-26 | **Arcs: no false zeros, no anonymous twins** (page-by-page pass): an entity is drawn only in the books it is in, a gap elsewhere (the server sends null there, `narrative.arcs`), instead of a line of zeros; when chosen entities share a name, the chips, the legend and the table add the book (`namesWithBooks`; a linked entity keeps its name). The shared slicer stays an open panel. | The user chose the gap and the book in the name, and kept the slicer panel open. A zero claimed "not mentioned here" where the entity simply belongs to another book. |
| AD-44 | 2026-10-26 | **Who speaks at scale** (page-by-page pass): speakers and narrators of the same name in different books get their book in the tables (`namesWithBooks`, now in core.js); the dialogue-share curve of more than eight books (`TIME_AVERAGE_FROM`) draws their average as the named line, each book faint behind it (as AD-23), on Who speaks and its In-Depth scope. | The user chose both. Sixty lines of one curve were a tangle, and three "Holmes" rows said nothing. |
| AD-45 | 2026-10-27 | **Books combined on Arcs, Sentiment and Lexicons**, as on Over the book: a third Timeline option (greyed out, with its reason in the title, unless the books are cut into equal slices by number; `seg()` options may now be disabled), each book weighing the same (the mean of the books' own values, a book without a value left out), and a per-page *Show each book* tick drawing every book's own line faintly (the `faint` series of AD-23). The combining is one server step (`narrative.books_combined` through `timeline`) used by every arc route, topics included. Style keeps Book by book. | The user's request; the user chose the third Timeline option, equal weight per book, the tick, and equal slices only. |
| AD-46 | 2026-10-27 | **Topics, calmer** (page-by-page pass, the last page): the intro panel became a quiet line (`.svtop`), and the fitting form folds its fine-tuning (minimum documents, maximum share, minimum letters, general words, also remove, seed, runs, alpha, beta) under a summary that names every value and tints those changed from the server's defaults (`basedOn(items, label)`), so a fit never runs on a hidden change (AL-PRIN-11). The form stays open when models exist. | The user chose all three. |

## 13. Known deviations and open points `[open]`

Recorded so nobody has to rediscover them. Fixing one is welcome; update this table when you do. Ratios are from §4.1.

| ID | Where | Issue | Suggested resolution |
|---|---|---|---|
| AO-01 | `--faint` | 3.04:1 on `--panel` and 2.68:1 on `--bg` in light; 3.62 / 4.02 in dark. Used for counts, paragraph numbers, axis text, `.t2 tr.dim`, `.tp-toc-sep`, `.pno`, `.cx`. | Darken light `--faint` to ≥ 4.5 on `--panel`, or limit it to redundant information (AL-COLOR-01) and use `--muted` elsewhere. |
| AO-02 | Dark theme text | `--warn` text 3.84 on `--panel`, 4.27 on `--bg`; error toast (white on `--warn`) 4.19; `.tag` accent on `--accent-soft` 3.90; `--accent` link on `--panel` 4.65 (passes). | Lighten the dark `--warn`; make `.tag` text `--ink` or lighten the dark accent. |
| AO-03 | `.t.ORG` | White 11 px/600 text on `#2b8a7e` is 4.17:1. | Darken ORG a little (all three places, AL-COLOR-05). |
| AO-04 | Categorical colours in dark mode | Not tuned: against the dark `--panel`, PER 2.47, GPE 2.64, GENDER 2.90, VEH 3.01, VAR 3.04, LOC 3.21, FAC 3.23, NARR 3.22, ORG 3.86 (graphical marks should reach 3:1). | Add dark variants of the type colours (CSS variables read by JS via `cssVar`) or lighten them slightly for both themes. |
| AO-05 | Literals | `#fff` ×6 and `#b8c4c7` ×2 in `app.css`; `#6d6a75` ×2 and `#8a6a3b` ×1 in CSS plus `TC`; `#999` fallbacks ×2; `#2e4a62` `#c0843a` `#b5473c` in `compare.js`, `narrative.js`, `dialogue.js`; greys `#b7c0c2` `#9aa6aa` `#7b878b` `#e6eae9` in `network.js`, `narrative.js`; the mono stack ×2; the radius, shadow and z values are not variables. | Add `--on-solid`, `--on-chrome-muted`, `--type-VAR`, `--type-NARR`, `--mono`; read chart colours with `cssVar`. |
| AO-06 | Radius | `.panel` and `.phead` are 6, cards 10; inputs 4, buttons 6. | Raise panels to 10 when the analysis pages are redone (AL-SPACE-02). |
| AO-07 | Buttons | No `--danger` and no `.btn.danger`; *Delete for good* is a `.btn.primary`; `typePicker` uses `.primary` for "on" (should be `.on`). | Add a text-only danger style; move toggles to `.on`. |
| AO-08 | ARIA | The area links and `#areaNav` tabs carry `aria-current="page"` (since AD-29); `.subtabs` buttons and the entity-type `.chip`s have no `aria-pressed`; custom clickable rows are inconsistent (`role="button"` and `tabindex` appear only in `corpus.js` and `entities.js`). | Add `aria-current` in `renderPage`, `aria-pressed` in the builders, a shared helper for clickable rows. |
| AO-09 | Class names | `.sub` (submenu) and `.sugg` (entity search list) mean other things in the editor; `.chip` is a filter pill here and a mention chip there. | Rename on the next touch; keep §2.2 current. |
| AO-10 | Offsets | **Mostly resolved 2026-10-26 (AD-31):** sticky offsets and scroll margins use `calc(var(--sticky-top) + N)`. Left: the text view's `calc(var(--read-head) + 60px)`, and `cxSpy`/`spySettings` in JS use a 110 px threshold. | Read the threshold from `--sticky-top` in JS. |
| AO-11 | Section labels | Variants of AL-TYPE-03 exist: `.page-toc-title` and `.tp-toc-sep` use `.05em` and `--faint`; `.coll .now` uses `.03em` in accent. | Align to the one recipe or declare a second label style. |
| AO-12 | z-index | The menu and the toast share 40; there is no layer for a modal (none exists; `confirm()` is native). | Give the toast its own value if a modal is ever added. |
| AO-13 | Responsive | While writing this file only a 1024 px window was looked at: Library, the menu and the book panel (dark), Entities and a profile (light). Not checked: widths under 700 px, Library and Settings in a narrow window, the reading page narrow, light and dark for every page. | Test at 600–900 px in both themes and record. |
| AO-14 | Popover and motion | `.pop` is not clamped to the viewport (it may overflow when its button is near the right edge); smooth `scrollIntoView` ignores `prefers-reduced-motion`. | Flip the popover to the right edge when it would overflow; use `behavior: auto` under reduced motion. |
| AO-15 | Palette and size | aLex's neutrals, accent, serif and 14 px base differ from the editor's (`#2A54C6` accent, 13 px, "New York"). Decision AD-05 records that aLex keeps its own values, but no reason for the **values** is recorded. | Ask the user whether to converge (changing `app.css`, `core.js`'s `LIGHT_*`, the doc and the test together) or to record the palette as intentional. |
| AO-16 | Inline styles | 245 `style: { … }` objects in the JS set margins, widths and flex in the markup builders. Dynamic values (a bar's width, `--c`) belong there; static layout does not. | Move static ones to classes when a page is next edited. |
| AO-17 | Routing | An empty address lands on Entities, but "no books" redirects to Library. | Decide the front door (Library when empty is already so). |
| AO-18 | Names | `.empty` is a plain centred muted block, not the editor's dashed box; dashed boxes in aLex mean "holding area" (`.gbox`, `.pickcol`), not "suggestion". | Keep; record the difference when porting. |
| AO-19 | Brand | The plan for the 2026-10-09 redesign had the brand link to Library; the markup and `docs/DOCUMENTATION.md` §8 have a plain label. | The code is the record (AD-06); no change needed. |
| AO-20 | Enforcement | **Resolved 2026-10-09:** `tests/test_docs.py` (like the editor's) checks the comment-above-every-function convention (DL-ARCH-04) and Python docstrings. | — |
| AO-21 | Comparison colours | The Compare page draws its two sides with the literals `#2e4a62` and `#c0843a`; Dialogue's compare mode uses `PALETTE[0]` and `PALETTE[1]` (AL-COLOR-06). | One pair for every comparison: take the two palette entries. |
| AO-22 | Simplification round | Of AL-PRIN-09…14 (AD-27) the areas are built (AD-29); AL-PRIN-11's line exists on the entity profile only (AD-28), not yet on a group's, book's, gender's or narrator's page or on the analysis pages; the profile is regrouped (AD-30); AL-PRIN-12 is built (AD-33); column choosers exist (AD-34); AL-PRIN-14 is built (AD-36); AL-PRIN-13 for the profile's Over the book and the Style page's sound table (AD-35); the user keeps In-Depth Who Speaks and Compare's Over the book as they are. | Build in steps: the settings summary line (AL-PRIN-11) on one page first, then the areas (rewrite AL-BAR-01 and §8.1), the entity profile, the focus setting (AL-PRIN-12), column choosers, merging the duplicates (AL-PRIN-13), a pass over every page. |

## 14. Checklist for designing or redesigning a feature

1. **Which layout?** Pick one from §8.2; reuse its CSS (an analysis page is `.panel` sections; a list of things is cards; a settings-like page is `.page` + `.fields`).
2. **Where does it live?** A tab only if it is a place that analyses the selected books (AL-BAR-02); otherwise a sub-tab, a section of Library or Settings, or an entry in `[...]`. Once the areas are built (§8.3), a new analysis joins the area whose question it answers as a sub-tab, and has one home (AL-PRIN-13). Which of its settings change the numbers, and does a summary line name them (AL-PRIN-11)?
3. **Scope.** Does it use the book selection and plural mode? Send `withBooks(...)`; do not read other state.
4. **Choosing things.** Use the composite pickers (AL-CTRL-03); a new kind of choice becomes a new `kind` of spec, handled by the server's `View.resolve`.
5. **Colour.** Type → type colour; series → `PALETTE[i]`; state → accent or `--warn` with a non-colour cue (AL-COLOR-03); a new colour needs light and dark values and a contrast check (AL-TOK-02).
6. **Type.** Names from the books and page titles in `--serif`, numbers and chrome in `--sans`, sizes from AL-TYPE-02, `tabular-nums` on numbers.
7. **Numbers.** Sortable `table()` in a results box; a chart in `chartBox()`; a count that opens `openEvidence`; a `note()` that says how it is calculated (AL-PRIN-03).
8. **Independence.** Does any control change another panel's output? If so it must be a drawn-once global (AL-INT-08).
9. **Feedback and confirmation.** A toast that names the result; a confirm only for removing structure, with what stays (AL-INT-03); empty, loading and error states with a next step (AL-FB-02).
10. **Copy.** Verbs, sentence case, `…` for dialogs, the product's nouns (AL-COPY-03), a full stop on sentences.
11. **Persistence.** Personal view preference → `analyser.*` through `loadState`/`saveState`; library data → the server.
12. **States and sizes.** Both themes, 980 px and 700 px, sixty books, a single book, no books.
13. **Code.** `h()` only; a comment above every function; CSS in the right banner using tokens; routes only validate and call `core/`.
14. **Docs and tests.** A line in `docs/guide.md` (what the user can do), `docs/DOCUMENTATION.md` (how it is built), a row in §12 here if you decided something, a test in `tests/js` for behaviour, and `tests/test_design.py` stays green.

## 15. Transferring to a companion project

aLex is the **second** reference implementation of the Luna language, so there are two sources: the editor's `DESIGN.md` (the root) and this file (what the root looks like for an analysis tool). Take, in order:

1. **From the editor's file:** the principles, the colour semantics, the type roles and the component rules marked `[portable]` there. Where this file says *adopted*, nothing here changes them.
2. **From this file** — what an analysis or reading tool needs on top: the token JSON (§4.1; `color.*` → CSS variables or your framework's theme, `font`, `radius`, `z`, `layout` likewise); the `h()` builder (AL-ARCH-02); the top bar, `[...]` menu and book/scope button (§9.1–9.3); editor-style pages and the Settings layout (§9.8); results boxes, `table()` and chart conventions (§9.9–9.10); `note()`/`.hint`/states (§9.12); folding and the page menu (§9.13); per-workspace persistence (AL-INT-07); the confirmation policy when there is no undo (AL-INT-03).
3. **Keep identical across the projects** so users move between them without relearning: the semantic meaning of accent, selected and problem colours; the three type roles; segmented controls, cards and menus; header order (brand, views, actions right, `[...]` for the rare); toast feedback; Escape/Enter meanings; British sentence-case copy; a prefixed `localStorage` key scheme (use your own prefix, same pattern).
4. **Adapt per project:** categorical colour (type colours here, group hue in the editor; if a companion has neither, do not invent decorative colour), the page list, and every `[alex]` item.
5. **Record divergences.** A companion keeps its own `docs/DESIGN.md` beginning "Based on aLex design language, version of <date>" (and the Luna date if it also reads the root), with the §2.1-style table of every rule ID it changes and why. Rule IDs are stable: never reuse an ID for a different rule; mark a removed rule `withdrawn` instead of deleting it.
6. **Test for drift.** Copy `tests/test_design.py`, point it at the companion's stylesheet and script constants.

When this file and the editor's file are both open and a rule appears in both, the **companion's own** statement wins for that companion; the root wins only where the companion's file says *adopted*.

## 16. Maintaining this document

- Treat this file like code: change it in the same commit as the CSS or JS it describes.
- `tests/test_design.py` fails when the §4.1 block and `app.css` / `core.js` disagree (light and both dark copies, the type colours in all three places, the palette, `LIGHT_*`, fonts, `--bar-h`, the breakpoints and z-index values in use), when a contrast ratio no longer matches its colours, when a rule ID is defined twice or referenced but not defined, when a row of §2.1 is missing or repeated, and when `innerHTML` appears in `static/`. If `../editor/docs/DESIGN.md` exists beside the project it also checks that every editor rule has a row in §2.1, and warns when the editor's verification date is newer than the pin at the top. It does **not** check prose; re-verify §5–§11 when you change a component.
- Add a decision to §12 when you decide something; add a deviation to §13 when you knowingly break a rule; remove it from §13 when fixed.
- The date at the top is the last full verification against the code; the "Based on" date is the version of the editor's file this one was reconciled with. Companion projects pin both.
