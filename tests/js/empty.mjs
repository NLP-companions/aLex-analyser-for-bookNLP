// Visit every page of a library with no books at all (what a fresh install shows) and report anything that breaks (JSON on the last line).
// usage: node empty.mjs http://127.0.0.1:8766
import { openPage } from "./harness.mjs";

const base = process.argv[2];
const results = { visited: [], problems: [] };
const page = await openPage(base);

const routes = ["#/books", "#/settings", "#/entities", "#/dialogue/speakers", "#/dialogue/verbs", "#/dialogue/voice", "#/dialogue/conversations", "#/dialogue/quotes",
  "#/corpus/kwic", "#/corpus/wordlist", "#/corpus/ngrams", "#/corpus/collocates", "#/corpus/keywords",
  "#/narrative/arcs", "#/narrative/style", "#/narrative/stylometry", "#/narrative/sentiment", "#/narrative/lexicons",
  "#/compare", "#/network", "#/links", "#/narrators", "#/topics"];
for (const hash of routes) {
  try {
    const errs = await page.go(hash);
    results.visited.push(hash);
    errs.concat(page.problems()).forEach(e => results.problems.push(`${hash}: ${e}`));
  } catch (e) { results.problems.push(`${hash}: ${e.message}`); }
}
await page.go("#/books");
if (!/No books found yet/.test(page.text()) || !page.$("#main a[href='#/settings']")) results.problems.push("#/books: the first-run guidance is missing or doesn't lead to Settings");
const openBooks = [...page.$$("#main .empty button")].find(b => b.textContent === "Open books folder");
if (!openBooks) results.problems.push("#/books: no button to open the books folder while there are no books");
else {
  page.click(openBooks);
  for (let i = 0; i < 100 && !/^Opened .*books$/.test(page.$("#toast").textContent); i++) await new Promise(r => setTimeout(r, 50));
  if (!/^Opened .*books$/.test(page.$("#toast").textContent)) results.problems.push("#/books: Open books folder didn't open it: " + page.$("#toast").textContent);
}
await page.go("#/settings");
if (!/Folders/.test(page.text()) || !page.$("input[placeholder='/path/to/folder/with/books']")) results.problems.push("#/settings: the folder form is missing while there are no books");
results.errorsAtEnd = page.errors.slice();
console.log(JSON.stringify(results));
process.exit(0);
