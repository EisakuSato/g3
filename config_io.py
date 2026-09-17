"""Safely parse a saved-config block (as produced by app.py) back into a
plain dict of values, so the GUI can restore a previously saved graph.

The config text is plain Python assignments (SERIES = {...}, XLABEL = ...,
etc.). Rather than exec()'ing arbitrary pasted text (a real code-execution
risk once this app is deployed somewhere with untrusted input), this only
walks the parsed AST and evaluates literal values with ast.literal_eval, plus
one special-cased pattern for PALETTE = PALETTES["name"]. Anything else
raises ConfigParseError instead of running.
"""

import ast
import re

CONFIG_HEADER_RE = re.compile(r"#\s*g3 config:\s*chart_type=(\w+)")

# Matches a raw PDF dictionary entry, e.g. '/Subject (# g3 config: ...\nSERIES = {...})',
# as it looks when copied straight out of a PDF's bytes (a text editor, `strings`, `pdftk
# dump_data`, ...) instead of through a PDF-aware tool. Those tools return the string already
# decoded; a raw copy still has the PDF wrapper and PDF string escapes (\n, \(, \), \\).
_PDF_RAW_FIELD_RE = re.compile(r"^/\w+\s*\((?P<content>.*)\)\s*(>>.*)?$", re.DOTALL)
_PDF_ESCAPE_RE = re.compile(r"\\n|\\r|\\t|\\\(|\\\)|\\\\")
_PDF_ESCAPES = {r"\n": "\n", r"\r": "\r", r"\t": "\t", r"\(": "(", r"\)": ")", r"\\": "\\"}


def _unescape_pdf_string(text: str) -> str:
    return _PDF_ESCAPE_RE.sub(lambda m: _PDF_ESCAPES[m.group(0)], text)


def normalize_pasted_text(text: str) -> str:
    """If `text` is a raw PDF dictionary entry ('/Key (...)'), strip that
    wrapper and un-escape the PDF string syntax inside it. Text that doesn't
    match this shape is returned unchanged (the '/Key (' / ')' wrapper is
    optional -- see parse_config_text, which also handles someone copying
    just the inside of the parentheses, escapes and all, without it).
    """
    match = _PDF_RAW_FIELD_RE.match(text.strip())
    if not match:
        return text
    return _unescape_pdf_string(match.group("content"))

# Top-level names we know how to restore. Anything else in the pasted text is
# ignored (e.g. a stray comment or unrelated assignment from a hand-edited paste).
KNOWN_KEYS = {
    "SERIES", "XLABEL", "YLABEL", "XMIN", "XMAX", "YMIN", "YMAX", "XSCALE", "YSCALE",
    "STYLE", "PALETTE", "LEGEND_LOC", "LEGEND_NCOL", "LEGEND_OUTSIDE",
    "WIDTH_RATIO", "HEIGHT_RATIO", "GRID", "AXIS_LABEL_FONTSIZE", "TICK_FONTSIZE", "LEGEND_FONTSIZE",
    "DPI", "N_BINS", "SHOW_VALUES", "VALUE_FMT", "VALUE_LABEL_FONTSIZE", "STACKED",
}


class ConfigParseError(ValueError):
    pass


def _eval_value(node: ast.expr, palettes: dict):
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "PALETTES":
        try:
            key = ast.literal_eval(node.slice)
        except (ValueError, SyntaxError) as e:
            raise ConfigParseError(f"Could not read the PALETTE preset name: {e}") from e
        if key not in palettes:
            raise ConfigParseError(f"Unknown palette preset: {key!r}")
        return key
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError) as e:
        raise ConfigParseError(f"Unsupported value in config: {ast.dump(node)} ({e})") from e


def _parse_assignments(text: str, palettes: dict) -> tuple:
    header_match = CONFIG_HEADER_RE.search(text)
    chart_type_key = header_match.group(1) if header_match else None

    try:
        tree = ast.parse(text, mode="exec")
    except SyntaxError as e:
        raise ConfigParseError(f"Could not parse this as Python: {e}") from e

    values = {}
    for stmt in tree.body:
        if not isinstance(stmt, ast.Assign):
            continue

        names = []
        for target in stmt.targets:
            if isinstance(target, ast.Name):
                names.append(target.id)
            elif isinstance(target, ast.Tuple):
                names.extend(elt.id for elt in target.elts if isinstance(elt, ast.Name))
            else:
                raise ConfigParseError(f"Unsupported assignment target: {ast.dump(target)}")

        if len(names) == 1:
            name = names[0]
            if name in KNOWN_KEYS:
                values[name] = _eval_value(stmt.value, palettes)
        elif isinstance(stmt.value, ast.Tuple) and len(stmt.value.elts) == len(names):
            for name, sub in zip(names, stmt.value.elts):
                if name in KNOWN_KEYS:
                    values[name] = _eval_value(sub, palettes)
        # A tuple-target assignment whose shape we don't recognize is silently
        # skipped rather than rejected outright, so unrelated hand-edits to a
        # pasted script don't block loading the settings we do understand.

    if not values:
        raise ConfigParseError("No recognized settings found in the pasted text.")

    return chart_type_key, values


def parse_config_text(text: str, palettes: dict) -> tuple:
    """Return (chart_type_key_or_None, values). values maps KNOWN_KEYS entries
    present in the text to their parsed Python value. PALETTE, when set from
    a PALETTES[...] lookup, is returned as the preset name (a string); a
    literal PALETTE = None stays None.

    Accepts plain config text (as app.py generates it, or as a PDF-aware tool
    like pdfinfo/pypdf returns it), a full raw PDF dictionary entry copied out
    of a PDF's bytes ('/Subject (...)'), or just the inside of that entry
    copied without the wrapper -- in the last two cases the PDF string escapes
    (\\n, \\(, \\), \\\\) are undone automatically.

    Raises ConfigParseError if the text isn't parseable, or uses anything
    beyond plain literals and the one PALETTES[...] pattern.
    """
    text = normalize_pasted_text(text)
    try:
        return _parse_assignments(text, palettes)
    except ConfigParseError:
        unescaped = _unescape_pdf_string(text)
        if unescaped == text:
            raise
        return _parse_assignments(unescaped, palettes)
