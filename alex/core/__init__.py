"""The analysis code: everything that reads books and computes, with no web code.

    bookdata.py         parse one book's BookNLP files              library.py      books on disk, settings, links, corrections
    bookcache.py        the parsed-book cache (safe pickles)        workspaces.py   separate libraries to switch between
    bookcollections.py  collections of books                        export.py       the export zip
    entitygroups.py     saved groups of entities                    plurals.py      plural groups ("Holmes and Watson")
    view.py             the selected books combined                 stats.py        keyness and other statistics
    corpus.py           concordance, lists, collocates, keywords    dialogue.py     quotes, speakers, addressees, narrators
    narrative.py        segments, arcs, style, stylometry, sentiment  narrators.py  narrator suggestions
    described.py        what an entity is described as, by whom    network.py      entity networks
    links.py            link suggestions across books              reader.py       the text view
    topics/             topic modelling (a package)
"""
