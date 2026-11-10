// The pages in a simulated browser over a library of many books (here: whatever the server has, all selected): nothing may break,
// and the charts and lists must stay a size a browser copes with.
// usage: node many.mjs http://127.0.0.1:8766
import { api, openPage, waitFor } from "./harness.mjs";

const base = process.argv[2];
const failures = [], passed = [];
const page = await openPage(base);
const w = page.window;
const $$ = s => page.$$(s);

async function scenario(name, fn) {
  const before = page.errors.length;
  try {
    await fn();
    const errs = page.errors.slice(before);
    if (errs.length) throw new Error("script errors: " + errs.join(" | ").slice(0, 400));
    const bad = page.problems();
    if (bad.length) throw new Error(bad.join(" | "));
    passed.push(name);
  } catch (e) { failures.push(`${name}: ${e.message}`); }
}
function expect(cond, message) { if (!cond) throw new Error(message); }

/** Wait until the page has finished counting (no loading line or dimmed results). */
const waitForAll = () => waitFor(() => !page.$("#main .loading") && !page.$("#main .busy") && $$("#main h2").some(h => h.textContent === "Slice by slice"), "the combined page is drawn", 60000);

const lib = await api(base, "/api/library");
const books = lib.books.map(b => b.id);
const model = (await api(base, "/api/topics/fit", { books, cfg: { chunk_words: 80, k: 4, min_df: 2, runs: 1, pos: ["NOUN", "VERB", "ADJ"] }, name: "Many" }).catch(() => ({}))).id;

await scenario(`${books.length} books are selected and the Library page lists them all`, async () => {
  await page.go("#/books");
  expect($$("#main .bookcard").length >= books.length, "a card per book");
});
await scenario("the network is cut to the strongest entities and says so", async () => {
  w.eval(`S.net.min_weight = 1; S.net.max_nodes = 10; S.net.types = ["PER"]; S.net.kind = "sentence"`);
  await page.go("#/network");
  const circles = $$("#main .net-canvas svg circle").length;
  expect(circles > 0 && circles <= 10, `${circles} circles`);
  expect(/most strongly linked of/.test(page.text()), "a note says how many there were");
});
await api(base, "/api/links/auto", {});                              // from here on, every Holmes (and Watson) is one person across all the books
w.eval("S.units = null");
await scenario("the entity list opens a person linked across every book, whose charts stay readable", async () => {
  const units = (await api(base, "/api/units", { books })).rows;
  const holmes = units.find(u => u.name === "Holmes" && u.linked);
  expect(holmes && holmes.books.length === books.length, `Holmes is linked across all ${books.length} books`);
  await page.go("#/entities");
  await page.go("#/entities/" + encodeURIComponent(holmes.id));
  expect(/Book by book/.test(page.text()), "the book-by-book section");
  expect(new RegExp(`The 8 books with most actions of ${books.length}`).test(page.text()), "the kinds-of-action chart shows only the biggest books and says so");
  expect($$("#main h2").some(h => h.textContent === "Over the book"), "the profile has its Over the book panel");
  expect($$("#main svg").every(svg => svg.querySelectorAll("*").length < 5000), "no chart has thousands of elements");
});
await scenario("over the book: a person linked across every book offers each book, and the grid stays a size a browser copes with", async () => {
  const units = (await api(base, "/api/units", { books })).rows;
  const holmes = units.find(u => u.name === "Holmes" && u.linked);
  w.eval(`S.over.target = ${JSON.stringify({ kind: "unit", id: holmes.id, name: "Holmes", type: "PER" })}; S.over.book = null; S.over.view = "heat"; S.nar.seg = { ...S.nar.seg, mode: "slices", slice_by: "count", n: 50 }`);
  await page.go("#/over");
  const pick = () => $$("#main select").find(s => [...s.options].some(o => o.textContent === lib.books[0].title));
  expect(pick() && pick().options.length === books.length, "a book switch with every book Holmes is in");
  expect($$("#main .hgrid thead th.hc").length === 50, "a column per slice in the one grid (the kinds of action are a tab of it)");
  expect($$("#main .hgrid .hcell").length <= 2 * 50 * 40, "at most 40 rows in each grid, so at most 4,000 cells");
  expect($$("#main svg").every(svg => svg.querySelectorAll("*").length < 5000), "no chart has thousands of elements");
  w.eval("S.nar.seg.n = 10");
});
await scenario("over the book: all the books combined, with a line for every book", async () => {
  w.eval(`S.over.co = { target: { kind: "type", type: "PER" } }; S.over.co_n = 20; S.over.co_each = true; S.over.curve = "ov:per1k"; S.over.rel = "agent"`);
  await page.go("#/over/combined");
  await waitForAll();
  expect($$("#main .hgrid").length === 1 && $$("#main .hgrid thead th.hc").length === 20, "one grid, 20 slices");
  expect(/is in \d+ of the \d+ selected books/.test(page.text()), "the books used are counted");
  const curve = $$("#main section.panel").find(p => p.querySelector("h2") && p.querySelector("h2").textContent === "Along the books");
  const lines = curve.querySelectorAll("svg polyline[stroke-opacity]").length;
  expect(lines > 1 && lines <= books.length, `a faint line for each book (${lines} of ${books.length})`);
  expect($$("#main svg").every(svg => svg.querySelectorAll("*").length < 5000), "no chart has thousands of elements");
  w.eval(`S.over.co = { target: null }; S.over.co_each = false`);
});
await scenario("dialogue across all books", async () => {
  await page.go("#/dialogue/speakers");
  expect(/Dialogue in each book/.test(page.text()), "the per-book table");
  const chart = $$("#main svg").find(svg => svg.querySelectorAll("polyline").length >= books.length);
  expect(chart && chart.querySelectorAll("polyline title").length === books.length + 1, "a faint line per book, each named by a tooltip, and their average");
  expect([...chart.querySelectorAll("text")].some(t => t.textContent === `Average of ${books.length} books`), "the average is the one named line (AD-44)");
});
await scenario("a concordance of a common word draws a bounded plot", async () => {
  w.eval(`S.corp.query = "the"; S.corp.mode = "simple"; S.corp.scope = { kind: "all" }; S.corp.near = null; S.corp.ctx.query = "";`);
  await page.go("#/corpus/kwic");
  const plot = $$("#main svg").find(svg => svg.getAttribute("aria-label") === "Concordance plot");
  expect(plot, "the plot");
  expect(plot.querySelectorAll("rect").length <= books.length * 201 + 5, "at most one shaded slice per 200th of each book");
  expect($$("#main .kwic .kl").length === 500, "the first page of lines");
});
await scenario("word lists, n-grams and keywords", async () => {
  await page.go("#/corpus/wordlist");
  await page.go("#/corpus/ngrams");
  await page.go("#/corpus/keywords");
});
await scenario("arcs, style and stylometry", async () => {
  await page.go("#/narrative/arcs");
  const chart = $$("#main svg").find(svg => svg.querySelectorAll("polyline").length);
  expect(chart, "an arc chart");
  await page.go("#/narrative/style");
  await page.go("#/narrative/stylometry");
  await waitFor(() => page.$("#main .stylo-charts .chart-box svg"), "the cluster tree", 60000);      // (under load the page can settle before the tree is drawn)
});
await scenario("link suggestions, narrators and the text view", async () => {
  await page.go("#/links");
  await page.go("#/narrators");
  await page.go("#/read/" + encodeURIComponent(books[0]));
});
if (model) await scenario("topics over all the books", async () => {
  await page.go("#/topics/" + encodeURIComponent(model));
  expect(/Most probable words/.test(page.text()), "the model overview");
  await page.go(`#/topics/${encodeURIComponent(model)}/0`);
});

console.log(JSON.stringify({ passed, failures, errorsAtEnd: page.errors }));
process.exit(0);
