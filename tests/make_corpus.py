"""Cut real BookNLP output into many smaller books, to test the analyser on a large library (`benchmark.py --sources` reads the result).

    python tests/make_corpus.py --from ../output/* --out /tmp/corpus --books 60
    python tests/make_corpus.py --from ../output/* --out /tmp/corpus --books 60 --copies 4      # four times as much text

Each folder given with `--from` holds one book's files (`<id>.tokens`, `.entities`, `.quotes`, `.supersense`). The books are cut at
paragraph boundaries into as many pieces as are needed for `--books` in all (the longest books give the most pieces), and every piece
is written as a book of its own, `<id>-<number>`, with its token, sentence and mention numbers counted again from 0 (so it is a
complete, ordinary export: entities and quotes that lie inside the piece are kept). `--copies N` writes each piece N times under
different ids, to try a corpus N times as large. Nothing in the source folders is changed.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def read(path: Path):
    """A tab-separated file -> (header, rows); ([], []) when the file is missing."""
    if not path.exists():
        return [], []
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
    return (rows[0], rows[1:]) if rows else ([], [])


def write(path: Path, header, rows):
    """Write a tab-separated file."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_NONE, quotechar=None, escapechar=None, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def paragraph_cuts(tokens, header, pieces):
    """The token positions where a book is cut into `pieces` parts of about the same size: the paragraph starts nearest to equal shares."""
    para = header.index("paragraph_ID")
    starts = [0] + [i for i in range(1, len(tokens)) if tokens[i][para] != tokens[i - 1][para]]
    cuts = [0]
    for k in range(1, pieces):
        want = k * len(tokens) // pieces
        cut = min(starts, key=lambda s: abs(s - want))
        if cut > cuts[-1]:
            cuts.append(cut)
    return cuts + [len(tokens)]


def piece(src: Path, book: str, a: int, b: int, out: Path, name: str, tokens, th, entities, eh, quotes, qh, supers, sh):
    """Write tokens [a, b) of a book, and what lies inside them, as the book `name` in the folder `out`."""
    col = {c: i for i, c in enumerate(th)}
    first_sent, first_para = int(tokens[a][col["sentence_ID"]]), int(tokens[a][col["paragraph_ID"]])
    first_byte = int(tokens[a][col["byte_onset"]])
    new = []
    for i in range(a, b):
        r = list(tokens[i])
        r[col["token_ID_within_document"]] = str(i - a)
        r[col["sentence_ID"]] = str(int(r[col["sentence_ID"]]) - first_sent)
        r[col["paragraph_ID"]] = str(int(r[col["paragraph_ID"]]) - first_para)
        head = int(r[col["syntactic_head_ID"]]) - a
        r[col["syntactic_head_ID"]] = str(head if 0 <= head < b - a else i - a)
        r[col["byte_onset"]] = str(int(r[col["byte_onset"]]) - first_byte)
        r[col["byte_offset"]] = str(int(r[col["byte_offset"]]) - first_byte)
        new.append(r)
    out.mkdir(parents=True, exist_ok=True)
    write(out / f"{name}.tokens", th, new)

    def inside(s, e):
        return a <= s <= e < b

    ec = {c: i for i, c in enumerate(eh)}
    write(out / f"{name}.entities", eh, [[*r[:ec["start_token"]], str(int(r[ec["start_token"]]) - a), str(int(r[ec["end_token"]]) - a), *r[ec["end_token"] + 1:]]
                                          for r in entities if inside(int(r[ec["start_token"]]), int(r[ec["end_token"]]))])
    if qh:
        qc = {c: i for i, c in enumerate(qh)}
        kept = []
        for r in quotes:
            if not inside(int(r[qc["quote_start"]]), int(r[qc["quote_end"]])):
                continue
            r = list(r)
            ms, me = int(r[qc["mention_start"]]), int(r[qc["mention_end"]])
            keep = inside(ms, me)
            r[qc["quote_start"]], r[qc["quote_end"]] = str(int(r[qc["quote_start"]]) - a), str(int(r[qc["quote_end"]]) - a)
            r[qc["mention_start"]], r[qc["mention_end"]] = (str(ms - a), str(me - a)) if keep else ("-1", "-1")
            kept.append(r)
        write(out / f"{name}.quotes", qh, kept)
    if sh:
        sc = {c: i for i, c in enumerate(sh)}
        write(out / f"{name}.supersense", sh, [[str(int(r[sc["start_token"]]) - a), str(int(r[sc["end_token"]]) - a), *r[2:]]
                                               for r in supers if inside(int(r[sc["start_token"]]), int(r[sc["end_token"]]))])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="sources", nargs="+", required=True, help="folders of BookNLP output, one per book")
    parser.add_argument("--out", required=True, help="where the pieces are written (one folder per piece)")
    parser.add_argument("--books", type=int, default=60, help="how many books to make in all (before --copies)")
    parser.add_argument("--copies", type=int, default=1, help="write every piece this many times, under different ids")
    args = parser.parse_args()

    sources = []
    for folder in map(Path, args.sources):
        found = sorted(folder.glob("*.tokens"))
        if found:
            sources.append((folder, found[0].stem))
    if not sources:
        sys.exit("No BookNLP output (.tokens files) found in the folders given.")
    data = {}
    for folder, book in sources:
        th, tokens = read(folder / f"{book}.tokens")
        data[book] = (folder, th, tokens, *read(folder / f"{book}.entities"), *read(folder / f"{book}.quotes"), *read(folder / f"{book}.supersense"))
    total = sum(len(d[2]) for d in data.values())
    shares = {b: max(1, round(args.books * len(d[2]) / total)) for b, d in data.items()}
    while sum(shares.values()) > args.books and max(shares.values()) > 1:     # rounding: take a piece from the book with the most
        shares[max(shares, key=shares.get)] -= 1
    while sum(shares.values()) < args.books:                                  # or give one to the book whose pieces are longest
        shares[max(shares, key=lambda b: len(data[b][2]) / shares[b])] += 1
    out, made, tokens_made = Path(args.out), 0, 0
    for book, (folder, th, tokens, eh, entities, qh, quotes, sh, supers) in data.items():
        cuts = paragraph_cuts(tokens, th, shares[book])
        for k, (a, b) in enumerate(zip(cuts, cuts[1:]), 1):
            for copy in range(args.copies):
                name = f"{book}-{k:02d}" + (f"c{copy + 1}" if args.copies > 1 else "")
                piece(folder, book, a, b, out / name, name, tokens, th, entities, eh, quotes, qh, supers, sh)
                made += 1
                tokens_made += b - a
    print(f"{made} books ({tokens_made:,} tokens) written to {out}")


if __name__ == "__main__":
    main()
