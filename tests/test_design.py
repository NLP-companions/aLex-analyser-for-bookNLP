"""docs/DESIGN.md matches the stylesheet and the browser code, and its rule IDs are consistent.

The document's first `json tokens` block (section 4.1) holds the design tokens as data, so that tools and companion
projects can read them; these tests keep that block from drifting away from alex/static/app.css and js/core.js, check
its contrast ratios, and check the rule IDs (defined once, referenced only when defined, one row for every rule of the
companion editor's language). The prose is not checked.
"""
from __future__ import annotations

import json
import re
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOC = (ROOT / "docs" / "DESIGN.md").read_text()
CSS = (ROOT / "alex" / "static" / "app.css").read_text()
CORE = (ROOT / "alex" / "static" / "js" / "core.js").read_text()
EDITOR_DOC = ROOT.parent / "editor" / "docs" / "DESIGN.md"      # the companion editor's file, when it sits beside this project
STATUSES = {"adopted", "adapted", "deviates", "n/a"}
OWN_TOKENS = {"bar-h", "chrome", "serif", "sans", "PER", "LOC", "FAC", "GPE", "VEH", "ORG"}      # custom properties on :root that are not theme colours


def tokens() -> dict:
    """The JSON token block of DESIGN.md."""
    return json.loads(re.search(r"```json tokens\n(.*?)\n```", DOC, re.S).group(1))


def norm(value: str) -> str:
    """A CSS value without spaces and in lower case, so that `rgba(0, 0, 0, .45)` and `rgba(0,0,0,.45)` compare equal."""
    return re.sub(r"\s+", "", value).lower()


def declarations(block: str) -> dict:
    """The `--name: value` declarations of a CSS block as a dict (names without the dashes, values normalised)."""
    return {k: norm(v) for k, v in re.findall(r"--([\w-]+):\s*([^;}]+)", block)}


def blocks() -> tuple[dict, dict, dict]:
    """The light `:root` declarations and the two copies of the dark ones (system preference, explicit choice), from app.css."""
    light = re.search(r"^:root \{(.*?)^\}", CSS, re.S | re.M).group(1)
    media = re.search(r'@media \(prefers-color-scheme: dark\) \{\s*:root:not\(\[data-theme="light"\]\) \{(.*?)\}\s*\}', CSS, re.S).group(1)
    attr = re.search(r':root\[data-theme="dark"\] \{(.*?)\}', CSS, re.S).group(1)
    return declarations(light), declarations(media), declarations(attr)


def js_hex_map(source: str, name: str) -> dict:
    """The `KEY: "#hex"` pairs of a JavaScript object literal `const <name> = {...}` in core.js."""
    body = re.search(rf"const {name} = \{{(.*?)\}};", source, re.S).group(1)
    return {k: v.lower() for k, v in re.findall(r'(\w+):\s*"(#[0-9a-fA-F]{6})"', body)}


def luminance(hex_colour: str) -> float:
    """WCAG relative luminance of a `#rrggbb` colour."""
    rgb = [int(hex_colour.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a: str, b: str) -> float:
    """WCAG contrast ratio of two `#rrggbb` colours."""
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_theme_colours_match_the_stylesheet():
    """Every colour of the token block is in :root (light) and in both copies of the dark block, and nothing is missing from the block."""
    light, media, attr = blocks()
    t = tokens()["color"]
    assert media == attr, "the two dark blocks of app.css differ"
    for theme, css in (("light", light), ("dark", media)):
        for name, value in t[theme].items():
            assert css.get(name) == norm(value), f"{theme} --{name}"
    assert set(t["light"]) == set(light) - OWN_TOKENS, "a colour of :root is not in the token block (or the reverse)"
    assert set(t["dark"]) == set(media), "a colour of the dark block is not in the token block (or the reverse)"


def test_fixed_colours_fonts_and_bar_height_match_the_stylesheet():
    """--chrome, --bar-h, the two font stacks, the base size and the muted-on-chrome grey are as documented."""
    light, _, _ = blocks()
    t = tokens()
    assert light["chrome"] == norm(t["fixed"]["chrome"])
    assert light["bar-h"] == norm(t["fixed"]["bar-h"])
    assert t["fixed"]["on-chrome-muted"] in CSS
    assert light["sans"] == norm(t["font"]["sans"]) and light["serif"] == norm(t["font"]["serif"])
    size, line = re.search(r"body \{[^}]*font: (\d+px)/([\d.]+) var\(--sans\)", CSS).groups()
    assert (size, line) == (t["font"]["base-size"], t["font"]["base-line-height"])


def test_type_colours_agree_in_the_stylesheet_and_core_js():
    """The type colours exist as CSS variables (six), CSS literals (VAR, NARR) and the JS constant TC; all must equal the token block."""
    light, _, _ = blocks()
    documented = {k: v.lower() for k, v in tokens()["type-color"].items()}
    assert js_hex_map(CORE, "TC") == documented
    for name in ("PER", "LOC", "FAC", "GPE", "VEH", "ORG"):
        assert light[name] == documented[name], f"--{name}"
    for name in ("VAR", "NARR"):
        assert re.search(rf"\.t\.{name} \{{ background: ({documented[name]});", CSS, re.I), f".t.{name}"


def test_palette_and_property_colours_agree_with_core_js():
    """PALETTE (series colours) and PROP_COL (names, descriptions, pronouns) are as documented."""
    t = tokens()
    palette = re.search(r"const PALETTE = \[(.*?)\];", CORE, re.S).group(1)
    assert re.findall(r'"(#[0-9a-fA-F]{6})"', palette) == [c.lower() for c in t["palette"]]
    assert js_hex_map(CORE, "PROP_COL") == {k: v.lower() for k, v in t["prop-color"].items()}


def test_chart_export_colours_are_the_light_tokens():
    """prepSvg swaps a chart's theme colours back to the LIGHT_* constants, so those must be the light-theme tokens."""
    light = tokens()["color"]["light"]
    names = {"INK": "ink", "MUTED": "muted", "FAINT": "faint", "PANEL": "panel", "PANEL2": "panel-2"}
    found = {k: v.lower() for k, v in re.findall(r'LIGHT_(\w+) = "(#[0-9a-fA-F]{6})"', CORE)}
    assert set(found) == set(names)
    for key, token in names.items():
        assert found[key] == light[token].lower(), f"LIGHT_{key}"


def test_breakpoints_z_indexes_radii_and_widths_in_use_are_documented():
    """Every max-width breakpoint, z-index and plain px radius in app.css is in the token block, and the other way round."""
    t = tokens()
    assert {int(n) for n in re.findall(r"@media \(max-width: (\d+)px\)", CSS)} == set(t["breakpoint"])
    assert {int(n) for n in re.findall(r"z-index: (\d+)", CSS)} == set(t["z"].values())
    css_radii = set(re.findall(r"border-radius: (\d+px)\b(?!\s+\d)", CSS))
    assert css_radii == set(t["radius"].values()), "radius values in use differ from the token block"
    layout = t["layout"]
    assert re.search(rf"^main \{{[^}}]*max-width: {layout['main-max']}", CSS, re.M)
    assert re.search(rf"^\.page \{{ max-width: {layout['page-max']}", CSS, re.M)
    assert re.search(rf"^\.page\.with-toc \{{ max-width: {layout['page-with-toc-max']}", CSS, re.M)


def test_contrast_ratios_match_the_colours():
    """Each `fg/bg` entry of the contrast block is the WCAG ratio of those two colours (to two decimals)."""
    t = tokens()

    def colour(name: str, theme: str) -> str:
        """The `#rrggbb` a name stands for: white, a #hex, a token of the theme, chrome, or a type colour."""
        if name == "white":
            return "#ffffff"
        if name.startswith("#"):
            return name
        if theme in t["color"] and name in t["color"][theme]:
            return t["color"][theme][name]
        return t["fixed"].get(name) or t["type-color"][name]

    for theme, entries in t["contrast"].items():
        for pair, expected in entries.items():
            fg, bg = pair.split("/")
            assert abs(ratio(colour(fg, theme), colour(bg, theme)) - expected) <= 0.011, f"{theme} {pair}"


def test_rule_ids_are_defined_once_and_every_reference_is_defined():
    """AL- rules are defined once in bold; AD- and AO- rows once in their tables; no AL-, AD-, AO- or DL- ID is mentioned without a definition."""
    al = re.findall(r"\*\*(AL-[A-Z]+-\d\d)\b", DOC)
    assert len(al) == len(set(al)), sorted({i for i in al if al.count(i) > 1})
    ad = re.findall(r"^\| (AD-\d\d) \|", DOC, re.M)
    ao = re.findall(r"^\| (AO-\d\d) \|", DOC, re.M)
    assert len(ad) == len(set(ad)) and len(ao) == len(set(ao))
    assert set(re.findall(r"\bAL-[A-Z]+-\d\d\b", DOC)) <= set(al), "an AL- rule is used but never defined"
    assert set(re.findall(r"\bAD-\d\d\b", DOC)) <= set(ad), "an AD- decision is used but never defined"
    assert set(re.findall(r"\bAO-\d\d\b", DOC)) <= set(ao), "an AO- open point is used but never defined"
    assert set(re.findall(r"\bDL-[A-Z]+-\d\d\b", DOC)) <= set(editor_rows()), "an editor rule is mentioned that has no row in the table of section 2.1"


def editor_rows() -> dict:
    """The rows of the section 2.1 table: editor rule ID -> status."""
    return dict(re.findall(r"^\| (DL-[A-Z]+-\d\d) \| ([^|]+?) \|", DOC, re.M))


def test_every_editor_rule_has_one_row_with_a_valid_status():
    """Section 2.1 lists each editor rule once, with a status from the fixed vocabulary; with the editor beside this project, its rules are exactly these."""
    ids = re.findall(r"^\| (DL-[A-Z]+-\d\d) \|", DOC, re.M)
    assert len(ids) == len(set(ids)), sorted({i for i in ids if ids.count(i) > 1})
    assert set(editor_rows().values()) <= STATUSES
    if not EDITOR_DOC.exists():
        pytest.skip("the editor's DESIGN.md is not beside this project")
    theirs = set(re.findall(r"\*\*(DL-[A-Z]+-\d\d)\b", EDITOR_DOC.read_text()))
    assert set(ids) == theirs, f"missing rows: {sorted(theirs - set(ids))}; rows for rules the editor no longer has: {sorted(set(ids) - theirs)}"


def test_the_pin_to_the_editors_version_is_there_and_not_stale():
    """The document names the version of the editor's language it is based on; a newer editor file only raises a warning."""
    pin = re.search(r"Based on Luna design language, version of (\d{4}-\d\d-\d\d)", DOC)
    assert pin, "the 'Based on Luna design language, version of <date>' line is missing"
    assert re.search(r"Last verified against the code: \d{4}-\d\d-\d\d", DOC)
    if EDITOR_DOC.exists():
        theirs = re.search(r"Last verified against the code: (\d{4}-\d\d-\d\d)", EDITOR_DOC.read_text())
        if theirs and theirs.group(1) > pin.group(1):
            warnings.warn(f"the editor's DESIGN.md was verified on {theirs.group(1)}, after the version this file is pinned to ({pin.group(1)}): review it and re-pin", stacklevel=1)


def test_the_browser_code_never_sets_html():
    """AL-ARCH-02: no innerHTML, outerHTML or insertAdjacentHTML anywhere in static/."""
    offenders = []
    for path in (ROOT / "alex" / "static").rglob("*"):
        if path.suffix in {".js", ".html"}:
            for n, line in enumerate(path.read_text().splitlines(), 1):
                if re.search(r"\.(innerHTML|outerHTML)\b|insertAdjacentHTML\(", line):
                    offenders.append(f"{path.name}:{n}")
    assert not offenders, offenders
