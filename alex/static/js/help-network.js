"use strict";
/* ---------- help: Network ---------- */
/* The help of the Network page (see help.js): the kinds of link, which entities and links are drawn, how they look, the measures, a
   node's panel and the downloads. The maths is in MEASURES.md, section 12. */

addHelp("network", "Network", [
  { id: "start", title: "How the page works", text: [
    "Entities as nodes and their links as lines: drag to move, scroll to zoom, click a node for its figures. The line above the network says how many entities and links are shown, the density, connected parts and communities."] },

  { id: "links", title: "Links", items: [
    ["sentence", "Appear in the same sentence", "A link for each sentence that mentions both."],
    ["paragraph", "Appear in the same paragraph", "A link for each paragraph that mentions both."],
    ["dialogue", "Speaker mentions them in a quote", "From a speaker to whom they mention while speaking (directed)."],
    ["addressed", "Speaker talks to them (estimated)", "From a speaker to whom they address (directed; your corrections apply)."]],
    more: "MEASURES.md 12" },

  { id: "filters", title: "Which entities and links", items: [
    ["types", "Types", "The entity types to include."],
    ["min_weight", "Minimum link strength", "Hide weaker links."],
    ["range_link", "Minimum range per link", "Hide links found in fewer of the selected books."],
    ["range_ent", "Minimum range per entity", "Leave out entities in fewer of the selected books."],
    ["max", "Show at most", "Only this many entities, those with the strongest links (default 300, up to 1,000)."],
    ["isolated", "Show unlinked entities", "Keep entities with no link at this setting."]] },

  { id: "look", title: "How it looks", text: ["The row directly above the network: it changes only the picture, never what is counted."], items: [
    ["layout", "Layout", "Force-directed (the default: linked entities pull together, the rest spread out) or Circle, as Gephi's circular layout: every entity on one circle, so no circle hides another and the links show between them."],
    ["order", "Order by (Circle)", "The order around the circle, clockwise from the top: by community (each kept together), by type, by the Size by measure (largest first) or by name."],
    ["color", "Colour by", "Type, community (Louvain), or whether an entity has a tag."],
    ["size", "Size by", "Any measure below, or mentions."],
    ["labels", "Labels", "None, the largest 15, 25 or 50, or all."],
    ["reset", "Reset view", "Back to the whole network."]] },

  { id: "measures", title: "Measures", text: ["A table of every entity with its measures (click a row to pin it), and one of the links by weight."],
    items: [["degree", "Degree", "Number of neighbours."], ["strength", "Strength", "Sum of its links' weights."],
      ["betweenness", "Betweenness", "How often it lies on the shortest paths between others (0–1): a go-between."],
      ["closeness", "Closeness", "How near it is to everyone else (frequent pairs count as close)."],
      ["eigenvector", "Eigenvector", "Linked to entities that are themselves well linked; meaningful within the largest connected part."],
      ["clustering", "Clustering", "How far its neighbours are linked to one another."],
      ["mentions", "Mentions", "Its mentions in the selected books."],
      ["in_strength", "In-strength", "In directed networks (quotes): the weight of the links coming in."], ["out_strength", "Out-strength", "The weight of the links going out."],
      ["in_degree", "In-degree", "How many link to it."], ["out_degree", "Out-degree", "How many it links to."],
      ["community", "Community", "The group the Louvain method puts it in (fixed seed, so results repeat)."]],
    more: "MEASURES.md 12" },

  { id: "node", title: "A node's panel", text: [
    "Click a node (or a row) for its type, tags, every measure, Open profile, and whom it is linked to, strongest first."] },

  { id: "export", title: "Downloads", text: ["The small links right above the network; the table of every link and its weight is folded under Measures."], items: [
    ["svg", "SVG, PNG", "The picture as drawn."], ["gexf", "GEXF, GraphML", "The network as data, for Gephi or other network tools."]] },
]);
