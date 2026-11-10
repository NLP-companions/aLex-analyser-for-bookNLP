"""Every function is described: a docstring in Python, a comment above it (or beside it, for a one-line helper) in JavaScript.

This keeps the convention of the code base (docs/DESIGN.md, DL-ARCH-04; docs/DOCUMENTATION.md, section 10) from slipping when
features are added. It is the same check as the companion editor's `tests/test_docs.py`, adapted to aLex's style: an `__init__`
is described by its class's docstring, and a one-line arrow function may carry its comment at the end of its line.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "alex"
# a function declaration, or a constant holding an arrow function, at the top level of a script
DECL = re.compile(r"^(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(|^const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>")


def test_every_module_class_and_function_has_a_docstring():
    missing = []
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT.parent)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if not ast.get_docstring(tree):
            missing.append(f"{rel}: module docstring")
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not ast.get_docstring(node):
                if node.name == "__init__" and _class_of(tree, node) is not None and ast.get_docstring(_class_of(tree, node)):
                    continue                                       # a class's docstring describes how to make one
                missing.append(f"{rel}:{node.lineno} {node.name}")
    assert missing == [], "add a docstring saying what it does: " + ", ".join(missing)


def _class_of(tree, func):
    """The class whose body holds `func`, or None."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and func in node.body:
            return node
    return None


def test_every_top_level_function_in_the_browser_code_has_a_comment():
    missing = []
    for path in sorted((ROOT / "static" / "js").glob("*.js")):
        lines = path.read_text(encoding="utf-8").split("\n")
        for i, line in enumerate(lines):
            m = DECL.match(line)
            if not m:
                continue
            j = i - 1
            while j >= 0 and not lines[j].strip():
                j -= 1
            above = lines[j].strip() if j >= 0 else ""
            beside = re.search(r"\s//\s", line) is not None              # a one-liner's comment at the end of its line
            described = (above.startswith(("/*", "//", "*")) or above.endswith("*/")) and not above.startswith("/* ----")
            if not (described or beside):
                missing.append(f"{path.name}:{i + 1} {m.group(1) or m.group(2)}")
    assert missing == [], "add a comment saying what it does: " + ", ".join(missing)


def test_every_script_starts_with_a_description():
    for path in sorted((ROOT / "static" / "js").glob("*.js")):
        head = path.read_text(encoding="utf-8").split("\n")[:4]
        assert any(line.startswith(("/*", "//")) for line in head), f"{path.name} needs a header comment"


DOCS = Path(__file__).resolve().parent.parent / "docs" / "DOCUMENTATION.md"


def test_the_route_table_lists_exactly_the_routes_there_are(client):
    """Section 7 of docs/DOCUMENTATION.md has one row per route (a query written after the path, `?category=`, is only a hint)."""
    paths = client.get("/openapi.json").json()["paths"]
    real = {(m.upper(), p) for p, methods in paths.items() for m in methods if p.startswith("/api/")}
    rows = re.findall(r"^\| (GET|POST) \| `([^`?]+)(?:\?[^`]*)?` \|", DOCS.read_text(encoding="utf-8"), re.M)
    listed = {(m, p) for m, p in rows if p.startswith("/api/")}
    assert real == listed, f"add to the table: {sorted(real - listed)}; remove from it: {sorted(listed - real)}"


def test_the_documentation_names_every_test_file():
    """The table in section 9 says what each test file covers; a file that is added must be added there."""
    text = DOCS.read_text(encoding="utf-8")
    missing = [p.name for p in sorted(Path(__file__).parent.glob("test_*.py")) if f"`{p.name}`" not in text]
    assert not missing, f"describe these in section 9 of docs/DOCUMENTATION.md: {missing}"
